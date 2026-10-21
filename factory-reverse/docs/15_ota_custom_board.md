# 15 · ota_0 `CustomBoard` 逆向

> 证据等级：**反编译 + 字符串 + vtable 交叉可复查**；不是恢复出的完整源码。
> 对象：`ota_0`，Xiaozhi `2.2.6`，偏移 `0x910000`。
>
> 核心结论：ota_0 的厂商板级类是 `CustomBoard`，源码路径为
> `./main/boards/waveshare/esp32-c5-touch-lcd-2.8/esp32-c5-touch-lcd-2.8.cc`。
> 它实现了 I2C、CH32、SPI、ST7789、背光和 ES8311，但**没有发现触摸初始化**。
> 因此它可以作为音频/显示/背光参考，不能作为完整板级支持包。

## 1. 字符串证据

ota_0 的 rodata 中直接保留了方法名和源码路径：

```text
void CustomBoard::InitializeSt7789Display()     0x42198f6c
void CustomBoard::InitializeI2c()               0x42199154
void CustomBoard::InitializeSpi()               0x421991b0
CustomBacklight                                 0x421b87d2
CustomBoard                                     0x421b87f2 / 0x421b8810 / 0x421b8844
CustomBoard::InitializeButtons()                0x421b881d / 0x421b8851
./main/boards/waveshare/esp32-c5-touch-lcd-2.8/esp32-c5-touch-lcd-2.8.cc  0x42198f98
esp_lcd_new_panel_st7789(panel_io, &panel_config, &panel)
esp_lcd_panel_invert_color(panel, DISPLAY_INVERT_COLOR)
esp_lcd_panel_swap_xy(panel, DISPLAY_SWAP_XY)
esp_lcd_panel_mirror(panel, DISPLAY_MIRROR_X, DISPLAY_MIRROR_Y)
```

说明：

- 这些是**静态字符串**，证明厂商 board 源文件参与了编译，不能证明当前运行
  路径一定执行到每个函数。
- `InitializeButtons` 只看到 lambda/typeinfo 字符串，未找到一个独立的
  按钮初始化函数体；不要因为字符串存在就断言本板有可用按钮。
- `CustomBoard` 的方法是 C++ 类方法，Ghidra 没有符号表，地址来自字符串
  XREF、vtable 和调用者交叉。
- 日志点还保留了源码行号：I2C 初始化 `0x4b`、SPI 初始化 `0x67`、显示
  初始化 `0x77`；这些行号与上面的方法字符串一起出现，可用来区分内联后
  的构造顺序。

## 2. 类与对象布局

`CustomBoard` 由 `new` 包装函数 `0x42021df6` 创建：

```c
void *GetBoardInstance(void)
{
    void *p = malloc(0xac);
    CustomBoard::CustomBoard(p);
    return p;
}
```

该函数被多处调用；调用者用初始化 guard 控制只构造一次，因此可视为
board 单例的构造入口，但它本身不检查 guard，也不是 `app_main`。

对象布局（由构造函数的字段写入恢复）：

| 偏移 | 内容 | 证据 |
| ---: | --- | --- |
| `+0x00` | vptr `0x421b8888` | 构造函数 `*param_1 = 0x421b8888` |
| `+0x9c` | I2C master bus handle | `i2c_new_master_bus(..., param+0x27)` |
| `+0xa0` | `Display` / `SpiLcdDisplay` 对象 | `GetDisplay` @ `0x42021820` 返回 `this+0xa0` |
| `+0xa4` | CH32 IO expander handle | `custom_io_expander_create(..., param+0x29)` |
| `+0xa8` | `CustomBacklight` 对象 | 构造函数分配 0x10 字节后写入 |

对象大小 `0xac` 与字段布局一致。

### 2.1 vtable 中的关键方法

vptr 指向 `0x421b8888`。已确认的条目：

| 地址 | 语义 | 证据 |
| --- | --- | --- |
| `0x42021826` | `CustomBoard` 析构 | 写回多个基类 vptr，释放字段 |
| `0x4202184c` | deleting destructor | 调 `0x42021826` 后 `free(this, 0xac)` |
| `0x42021820` | `GetDisplay()` | `return *(this+0xa0)` |
| `0x42021876` | `GetAudioCodec()` | 构造/返回 ES8311 单例 |
| `0x42021a4e` | `InitializeSt7789Display()` | 字符串 XREF `0x42198f6c` |
| `0x42021c2c` | 构造函数 | 写 vptr、初始化 I2C/SPI/显示/背光 |

`CustomBacklight` 的 vptr 为 `0x421b887c`，其虚方法 `0x4202186c` 写 CH32
PWM。`0x421b887c` 是 Itanium ABI 的“首虚函数指针”位置；offset-to-top 和
typeinfo 指针分别位于 `0x421b8874` / `0x421b8878`。

## 3. 构造函数 `0x42021c2c`

反编译的调用顺序（去掉编译器噪声）：

```c
CustomBoard::CustomBoard(this)
{
    WifiBoard::WifiBoard(this);                 // 0x42020d7a
    this->vptr = 0x421b8888;
    init_some_member(this + 0x34, 0x1c, 0, 0, 0, 0);

    i2c_master_bus_config_t cfg = {0};
    cfg.scl_io_num = 1;                         // SDA 保持 0
    cfg.clk_source = 0x10;
    i2c_new_master_bus(&cfg, &this->i2c_bus);   // this+0x9c

    custom_io_expander_new_i2c_ch32v003(
        this->i2c_bus, 0x24, &this->expander);  // this+0xa4

    esp_io_expander_set_dir(this->expander, 0xb, OUTPUT);
    esp_io_expander_set_level(this->expander, 0x3, 1);
    vTaskDelay(1);
    esp_io_expander_set_level(this->expander, 0x3, 0);
    vTaskDelay(1);
    esp_io_expander_set_level(this->expander, 0x3, 1);
    vTaskDelay(1);
    esp_io_expander_set_level(this->expander, 0x8, 1);  // PA_CTRL

    spi_bus_config_t bus = {0};
    bus.sclk_io_num = 6;
    bus.mosi_io_num = 7;
    bus.miso_io_num = -1;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = 0x25800;              // 240*320*2
    spi_bus_initialize(1, &bus, 3);

    register_callbacks(this + 0x34, ...);
    InitializeSt7789Display(this);
}
```

### 3.1 I2C 配置

根据 factory 的同结构布局对照，OTA 的栈配置为：

```text
port            0
sda_io_num      0
scl_io_num      1
clk_source      0x10
glitch_ignore_cnt 0
internal_pullup   0
```

factory 和公共 BSP 都使用 SDA 0 / SCL 1，但会设置 `glitch_ignore_cnt=7`
和 internal pull-up。OTA 构造函数把配置区清零后只写了 SCL 和时钟源，
静态上**没有启用 glitch filter 或内部上拉**；板上是否有外部上拉需要看
原理图。这个差异不影响地址，但影响 bring-up 时的 I2C 稳定性判断。

> 置信度：引脚和 port 为高置信；`glitch_ignore_cnt/internal_pullup=0`
> 来自栈清零和结构布局推断，仍需对照 OTA 使用的 IDF 头文件确认字段偏移。

### 3.2 CH32 复位与功放

`set_level(0x3, ...)` 的 mask `0x3` 同时覆盖：

- bit 0 = `EXIO0` / 触摸复位
- bit 1 = `EXIO1` / LCD 复位

序列是“两路一起高 → 低 → 高”，每次 `vTaskDelay(1)`。`vTaskDelay(1)`
是 1 个 tick，不是硬编码 1 ms；tick rate 未在本镜像中确认。

随后 `set_level(0x8, 1)` 拉高 bit 3 = `EXIO3` / `PA_CTRL`。也就是说
OTA 在构造阶段就把功放使能打开，而不是等音频 codec 初始化完成。这可能
导致上电/复位时的 PA 爆音；Brookesia bring-up 不应盲抄这个顺序，建议
先保持 PA 低，显示和 codec 就绪后再拉高。

### 3.3 SPI bus

| 字段 | 值 |
| --- | --- |
| host | 1 (`SPI2_HOST`) |
| SCLK | 6 |
| MOSI | 7 |
| MISO | `-1` |
| quadwp / quadhd | `-1` / `-1` |
| `max_transfer_sz` | `0x25800` = 153600 |
| DMA | 3 (`SPI_DMA_CH_AUTO`) |

`0x25800` 正好是一整屏 16 bpp 的字节数。它说明 bus 允许整屏传输，但
LVGL 实际是否使用整屏 DMA 缓冲，要看 `SpiLcdDisplay` 的 buffer 配置，
不能只凭这个常量判断。

## 4. `InitializeSt7789Display` `0x42021a4e`

```c
void CustomBoard::InitializeSt7789Display(this)
{
    esp_lcd_panel_io_spi_config_t io = {0};
    io.dc_gpio_num = 9;
    io.cs_gpio_num = 10;
    io.pclk_hz = 40000000;          // 40 MHz
    io.trans_queue_depth = 10;
    io.lcd_cmd_bits = 8;
    io.lcd_param_bits = 8;
    esp_lcd_new_panel_io_spi(1, &io, &panel_io);

    esp_lcd_panel_dev_config_t panel = {0};
    panel.reset_gpio_num = -1;      // CH32 已完成复位
    panel.bits_per_pixel = 0x10;    // 16 bpp
    esp_lcd_new_panel_st7789(panel_io, &panel, &panel_handle);

    esp_lcd_panel_reset(panel_handle);
    esp_lcd_panel_init(panel_handle);
    esp_lcd_panel_swap_xy(panel_handle, 0);
    esp_lcd_panel_mirror(panel_handle, 0, 0);
    esp_lcd_panel_invert_color(panel_handle, 1);
    esp_lcd_panel_disp_on_off(panel_handle, 1);

    this->display = new SpiLcdDisplay(
        panel_io, panel_handle, 240, 320, 0, 0, 0, 0, 0);

    this->backlight = new CustomBacklight();
    this->backlight->i2c_bus = this->i2c_bus;
}
```

关键差异：

- **40 MHz**，不是 factory/公共 BSP 的 80 MHz。
- SPI bus 的 MISO 是 `-1`；factory 用 GPIO 8，公共 BSP 与 SD 共用 GPIO 8。
- 显式 `swap_xy(0)`、`mirror(0,0)`；factory 主要由上层 LVGL/display
  config 处理方向。
- 无自定义 ST7789 init 表；使用 IDF 标准驱动 + 反色。
- 没有调用任何 CST3530/touch API。

## 5. `CustomBacklight`

`CustomBoard` 分配 0x10 字节对象，vptr 设为 `0x421b887c`，保存 I2C bus
handle，然后 `InitializeSt7789Display` 末尾把它挂到 `this+0xa8`。

虚方法 `0x4202186c`：

```c
int CustomBacklight::set(this)
{
    uint8_t cmd[2] = {0x05, 0xff};
    int err = i2c_master_transmit(this->i2c_bus, cmd, 2, 1000);
    if (err != 0) {
        log_error(...);
    }
    return err;
}
```

- 固定写 CH32 PWM 寄存器 `0x05` 为 `0xff`。
- 反编译中没有看到亮度参数参与计算。
- 结论：**OTA 静态路径只支持全亮**；factory/公共 BSP 才支持 0–255 PWM。
  若 Brookesia 需要调光，必须自定义 backlight iface，不能照抄 OTA。

## 6. `GetAudioCodec` `0x42021876`

第一次调用时创建 ES8311 单例，后续返回同一对象：

```c
Es8311AudioCodec(
    g_codec,         // 全局单例存储 @ 0x4081d2b8
    this->i2c_bus,   // +0x9c
    0,               // i2c port
    24000,           // input sample rate
    24000,           // output sample rate
    -1,              // MCLK
    0x18,            // BCLK 24
    0x19,            // WS 25
    0x1a,            // DOUT 26
    0x1b,            // DIN 27
    -1,              // PA pin
    0x30,            // ES8311 I2C address
    0,               // use MCLK = false
    0                // PA inverted = false
);
```

第一个参数 `0x4081d2b8` 是函数内静态/全局的 codec 存储，不是 board 对象；
`0x40823f28` 是只初始化一次的 guard。参数列表与 Xiaozhi `2.2.6` 的
`Es8311AudioCodec` 构造签名逐项一致。这再次支持
**DOUT/TX=26、DIN/RX=27**，但原理图网名和公共 BSP 仍指向相反方向；
详见 [音频与 I2S](03_audio_i2s.md) 和
[原理图交叉核对](12_schematic_crosscheck.md)。

## 7. 没有触摸初始化

静态检查结果：

- `CustomBoard` 构造函数、`InitializeSt7789Display`、`GetAudioCodec` 都没有
  touch handle 或 `esp_lcd_touch` 调用。
- ota_0 中没有 `CST3530`、`esp_lcd_touch_new_i2c_cst3530`、
  `esp_lcd_touch_read_data`、`esp_lcd_touch_register_interrupt_callback`
  等字符串/符号。
- 没有 I2C 地址 `0x58` 的 touch 初始化调用链。

因此：

**ota_0 是“显示 + 背光 + 音频”的语音应用板级类，不包含本板触摸支持。**

这可能是厂商在语音 app 中不需要触摸，也可能是触摸由其他未识别路径处理；
但在这份镜像里没有可复用的 CST3530 实现。Brookesia 的触摸适配必须以
factory `0x420245b2` 和公共 BSP `bsp_touch_new` 为证据。

## 8. 与 factory / 公共 BSP 的取舍

| 项目 | 采用建议 |
| --- | --- |
| 显示引脚、240×320、ST7789 | 三套一致，可直接采用 |
| SPI 时钟 | 先 40 MHz（OTA）做 bring-up，再验证 80 MHz |
| SPI bus max transfer | 按 Brookesia LVGL buffer 决定，不盲抄 0x25800 |
| CH32 复位/PA | 采用 factory 的分离复位；PA 延后拉高 |
| 背光 | 采用 factory/公共 BSP 的 PWM 0–255；不要用 OTA 固定 0xff |
| 触摸 | 采用 factory/公共 BSP；OTA 无参考价值 |
| 音频 | 采用 OTA `GetAudioCodec` 的 24 kHz duplex + 26/27 基线 |
| 按钮 | 字符串不足以证明有按钮；按实际硬件/原理图处理 |

## 9. 复现

```bash
cd /tmp/factory-reverse
export JAVA_HOME=/tmp/factory-reverse/jdk/jdk-21.0.12.1+1

# 字符串地址
python3 - <<'PY'
from pathlib import Path
b = Path('ota_combined.bin').read_bytes()
base = 0x40800000
for s in [b'void CustomBoard::InitializeSt7789Display()',
          b'void CustomBoard::InitializeI2c()',
          b'void CustomBoard::InitializeSpi()']:
    i = b.find(s)
    print(s.decode(), hex(base + i))
PY

# 反编译构造函数 / 显示 / 背光 / codec
$GHIDRA/support/analyzeHeadless /tmp/factory-reverse/ghidra_ota ota \
  -process ota_combined.bin -noanalysis \
  -scriptPath /home/gadil/local-agent/clones/esp32-design/factory-reverse/tools \
  -postScript DecompileAt.java \
  0x42021c2c 0x42021a4e 0x4202186c 0x42021876
```

## 10. 相关文档

- [显示与触摸对照](13_display_touch.md)
- [音频与 I2S](03_audio_i2s.md)
- [Ghidra 发现](09_ghidra_findings.md)
- [证据账本](../reference/evidence-ledger.md)
