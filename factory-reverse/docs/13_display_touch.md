# 13 · 显示与触摸：factory / ota_0 / 公共 BSP 对照

> 证据等级：factory 与 ota_0 为 **反编译 + 常量可复查**；公共 BSP 为
> **源码可复查**。函数名是按字符串和调用序列命名的语义名，不是恢复出的
> C++ 符号。
>
> 结论：三套实现的**面板和引脚相同**，但 SPI 时钟、SPI bus 参数、触摸是
> 否存在、背光控制方式不同。不要用 ota_0 的 `CustomBoard` 反推触摸初始化。

## 1. 共同硬件

| 项目 | 值 | 证据 |
| --- | --- | --- |
| LCD 控制器 | ST7789 | 公共 BSP、factory `0x42047346`、OTA `0x420a73b4` 调用点 |
| 分辨率 | 240 × 320 | factory display ctor 参数 `0xf0/0x140`；OTA 同 |
| 色深 | 16 bpp | panel config `bits_per_pixel=0x10` |
| SPI host | 1 | `spi_bus_initialize(1, ...)` |
| SCLK | GPIO 6 | 三套一致 |
| MOSI | GPIO 7 | 三套一致 |
| MISO | GPIO 8 | factory/公共 BSP；OTA bus 设为 `-1` |
| LCD CS | GPIO 10 | 三套一致 |
| LCD DC | GPIO 9 | 三套一致 |
| LCD reset | CH32 `EXIO1` / pin 1 | 低有效；不是 ESP32 GPIO |
| 触摸 reset | CH32 `EXIO0` / pin 0 | 低有效；不是 ESP32 GPIO |
| 触摸 INT | GPIO 5 | factory `esp_lcd_touch_config_t.int_gpio_num=5` |
| 触摸控制器 | CST3530，I2C 7-bit `0x58`（YAML `0xB0`） | factory 与公共 BSP |
| 背光 | CH32 PWM，寄存器 `0x05`，0–255 | 公共 BSP / factory / OTA 写同一寄存器 |

CH32 方向 mask 为 `0xb`，即 pin 0、1、3 输出；pin 3 是 `PA_CTRL`/功放使能。
CH32 的 7-bit I2C 地址是 `0x24`；Board Manager YAML 使用左移后的 `0x48`。
触摸同理：7-bit `0x58` 在 YAML 中写 `0xB0`。详见
[电池与 CH32](10_battery_ch32_adc.md)。

## 2. Factory 实现

### 2.1 显示

入口：`bsp_display_new` @ `0x420243f2`。

```text
bsp_display_new
├─ bsp_io_expander_init()                 0x42023858
├─ set_level(EXIO1=1, 0); delay 200 ms
├─ set_level(EXIO1=1, 1); delay 200 ms
├─ bsp_spi_init()                         0x420238fc
│  └─ spi_bus_initialize(host=1,
│        mosi=7, miso=8, sclk=6,
│        quadwp=-1, quadhd=-1,
│        max_transfer_sz=0, dma=3)
├─ esp_lcd_new_panel_io_spi(host=1,
│        dc=9, cs=10, pclk=80 MHz,
│        cmd_bits=8, param_bits=8,
│        trans_queue_depth=10)
├─ esp_lcd_new_panel_st7789(reset=-1, 16 bpp)
├─ esp_lcd_panel_init()
├─ esp_lcd_panel_invert_color(true)
└─ esp_lcd_panel_disp_on_off(true)
```

关键点：

- `reset_gpio_num=-1`，因为复位由 CH32 完成；panel 驱动不再操作 GPIO。
- SPI panel 时钟 **80 MHz**。
- SPI bus 没有设置 `max_transfer_sz`，即使用 IDF 默认值；这与 OTA 不同。
- 面板初始化使用 IDF 标准 ST7789 驱动，未发现厂商自定义 gamma/init 表。
- 反色打开；显示打开。旋转/镜像不在 panel 层设置，交给上层
  `SpiLcdDisplay`/LVGL。

### 2.2 触摸

入口：`bsp_touch_new` @ `0x420245b2`。

```text
bsp_touch_new
├─ set_level(EXIO0=1, 0); delay 10 ms
├─ set_level(EXIO0=1, 1); delay 10 ms
├─ esp_lcd_new_panel_io_i2c(bus0,
│        dev_addr=0x58 (7-bit), scl=400 kHz,
│        CST3530 32-bit command)
├─ esp_lcd_touch_new_i2c_cst3530(io, cfg)
└─ esp_lcd_touch_register_interrupt_callback(...)
```

`esp_lcd_touch_config_t` 的静态值：

| 字段 | 值 |
| --- | --- |
| `x_max` | 240 |
| `y_max` | 320 |
| `rst_gpio_num` | `-1`（外部 CH32 复位） |
| `int_gpio_num` | 5 |
| `levels.reset` | 0（低有效） |
| `levels.interrupt` | 0（低有效） |
| `flags.swap_xy / mirror_x / mirror_y` | 0 / 0 / 0 |
| `user_data` | I2C bus handle |

触摸 IO 的精确结构体字段排布仍受 Ghidra 栈变量影响；可确认的是
I2C 地址 `0x58`、400 kHz、CST3530 的 32 位命令模式，以及复位/中断脚。
board draft 里的 `lcd_cmd_bits=32`、`lcd_param_bits=8`、
`disable_control_phase=true` 来自公共 BSP 的
`ESP_LCD_TOUCH_IO_I2C_CST3530_CONFIG()`，不是从 factory 栈完全恢复。
公共 BSP 还在 `esp_lcd_touch_config_t.user_data` 里传 I2C bus handle，让
CST3530 驱动自己创建设备，避免依赖 `esp_lcd_panel_io` 的私有结构体布局；
draft 的 `lcd_touch_factory_entry_t` 同样设置了这个字段。代价是驱动会在固定
7-bit `0x58`、400 kHz 下再建一个 I2C device，而 `dev_lcd_touch` 的 panel IO
device 仍然存在；驱动的 `del` 只清空静态 handle，不调用
`i2c_master_bus_rm_device`。单次 bring-up 可接受，重复 init/deinit 需要
自行清理。

## 3. ota_0 `CustomBoard` 实现

### 3.1 构造顺序

入口：`CustomBoard` 构造函数 @ `0x42021c2c`，对象大小 `0xac`，
vtable `0x421b8888`。调用链和细节见
[OTA CustomBoard](15_ota_custom_board.md)。

```text
CustomBoard::CustomBoard
├─ WifiBoard 基类构造                 0x42020d7a
├─ i2c_new_master_bus(port 0, sda 0, scl 1)
├─ custom_io_expander_ch32v003_create(bus, 0x24)
├─ set_dir(0xb, OUTPUT)
├─ set_level(0x3, 1)   // EXIO0 + EXIO1 同时高
├─ delay 1 tick
├─ set_level(0x3, 0)   // 两路同时低
├─ delay 1 tick
├─ set_level(0x3, 1)   // 两路同时高
├─ delay 1 tick
├─ set_level(0x8, 1)   // EXIO3 / PA_CTRL 高
├─ spi_bus_initialize(host=1,
│     sclk=6, mosi=7, miso=-1,
│     quadwp=-1, quadhd=-1,
│     max_transfer_sz=0x25800, dma=3)
├─ InitializeSt7789Display()          0x42021a4e
├─ 注册 WiFi/应用回调
└─ 创建 CustomBacklight（vptr 0x421b887c）
```

`0x25800` = 153600 = `240 × 320 × 2`，即一整屏 16 bpp 的字节数。这说明
OTA 的 SPI bus 允许一次传输整屏；是否真的整屏刷新还取决于 LVGL 缓冲和
`draw_bitmap` 的分块，不能只凭这个常量下结论。

### 3.2 OTA 显示

`CustomBoard::InitializeSt7789Display` @ `0x42021a4e`：

| 参数 | 值 |
| --- | --- |
| panel IO | `esp_lcd_new_panel_io_spi(host=1)` |
| DC / CS | 9 / 10 |
| `pclk_hz` | **40 MHz** |
| `trans_queue_depth` | 10 |
| `lcd_cmd_bits` / `lcd_param_bits` | 8 / 8 |
| panel reset | `-1`（CH32 已完成复位） |
| `bits_per_pixel` | 0x10（16） |
| `swap_xy` | 0 |
| `mirror_x` / `mirror_y` | 0 / 0 |
| `invert_color` | true |
| `disp_on_off` | true |
| `SpiLcdDisplay` 尺寸 | 240 × 320 |

与 factory 的差异：

- OTA **40 MHz**，factory 和公共 BSP **80 MHz**。
- OTA SPI bus 的 MISO 为 `-1`，且 `max_transfer_sz=0x25800`；factory 使用
  MISO 8、默认 max transfer。
- OTA 仍用 IDF 标准 ST7789 驱动，无自定义 init 表；它显式调用
  `reset → init → swap_xy(0) → mirror(0,0) → invert_color(1) →
  disp_on_off(1)`，反色和开显示与 factory 相同。

40 MHz 更保守，适合作为 bring-up 基线；80 MHz 是否能稳定工作取决于
排线、面板批次和 PCB，必须实测。不能把 OTA 的 40 MHz 当作硬件上限。

### 3.3 OTA 背光

`CustomBacklight` 的方法 @ `0x4202186c`：

```c
uint8_t buf[2] = {0x05, 0xff};
i2c_master_transmit(ch32_i2c_handle, buf, 2, 1000);
```

- 固定写 CH32 PWM 寄存器 `0x05` 为 `0xff`。
- 反编译中该函数没有使用亮度参数；OTA 静态代码只看到“全亮”。
- 这不代表面板不能调光：factory 和公共 BSP 都会按百分比写 `0x05`。
  Brookesia 若需要调光，应实现 custom `DisplayBacklightIface`，不要照抄
  OTA 的固定 0xff。

### 3.4 OTA 没有触摸初始化

静态证据：

- ota_0 的字符串和符号中没有 `CST3530`、`esp_lcd_touch`、
  `esp_lcd_touch_new_i2c_cst3530`。
- `CustomBoard` 构造函数只创建显示和背光，没有 touch object、INT 回调或
  I2C `0x58` 访问。
- OTA 字符串中只有网页 CSS 的 `touchstart`，不是触摸驱动。

因此 **ota_0 的 board class 不能作为本板触摸初始化的参考**。触摸参数应
以 factory `0x420245b2` 和公共 BSP `bsp_touch_new` 为准。OTA 运行时是否
通过其他未识别路径访问触摸，仍不能仅凭“没有字符串”绝对否定；但在这份
镜像里没有可复用的 CST3530 代码。

## 4. 三套实现对照

| 项目 | factory | ota_0 `CustomBoard` | 公共 BSP |
| --- | --- | --- | --- |
| ST7789 240×320 | 是 | 是 | 是 |
| SPI host / SCLK / MOSI | 1 / 6 / 7 | 1 / 6 / 7 | 1 / 6 / 7 |
| MISO | 8 | `-1` | 8（SD 共用） |
| CS / DC | 10 / 9 | 10 / 9 | 10 / 9 |
| panel pclk | 80 MHz | **40 MHz** | 80 MHz |
| SPI bus max transfer | 默认 | `0x25800` | 默认 |
| panel reset | CH32 EXIO1，200/200 ms | CH32 EXIO1，构造时 1 tick 脉冲 | CH32 EXIO1，200/200 ms |
| touch | CST3530 `0x58` | **未发现** | CST3530 `0x58` |
| touch reset | CH32 EXIO0，10/10 ms | 构造时与 LCD 一起脉冲 | CH32 EXIO0，10/10 ms |
| touch INT | GPIO 5 | 未发现 | GPIO 5 |
| backlight | CH32 PWM `0x05` | 固定 `0x05=0xff` | CH32 PWM `0x05` |
| PA enable | CH32 EXIO3 | CH32 EXIO3 | CH32 EXIO3 |

## 5. 对 Brookesia 0.7 板级的含义

1. **显示参数先按 40 MHz 起步**，验证通过后再试 80 MHz；不要把 80 MHz
   写死为“官方值”，因为 ota_0 明确用了 40 MHz。
2. **SPI bus 的 `max_transfer_sz` 不要盲抄 0x25800**。0.7 的 LVGL 适配层
   有自己的 draw buffer 配置；如果使用整屏缓冲，再设置整屏大小，否则会
   浪费 DMA 内存。
3. **触摸必须单独实现**。可以复用公共 BSP/`esp_lcd_touch_cst3530`，但不能
   从 ota_0 `CustomBoard` 找到 touch 初始化。
4. **背光必须走 CH32 PWM**。0.7 的 stock `DisplayBacklightIface` 通常操作
   ESP32 LEDC/GPIO；本板需要自定义 iface 写 I2C `{0x05, value}`。
5. **复位顺序**：factory 是 LCD 先复位、触摸后复位；OTA 在构造时把两路
   一起脉冲。Bring-up 建议采用 factory 的分离顺序，便于定位是显示还是
   触摸失败。
6. **PA 使能**：EXIO3 高有效。factory 的 `bsp_io_expander_init` 在初始化
   expander 时就把 EXIO3 拉高，OTA 也在构造末尾直接拉高；当前 board draft
   按 factory 保持常高。若实测有上电爆音，可改成初始化时保持低，并在
   codec 就绪后通过自定义音频钩子拉高。

## 6. 验证清单

- [ ] 逻辑分析仪测 SPI SCLK：确认 40 MHz / 80 MHz 实际频率和 CS 时序。
- [ ] 读 ST7789 ID，确认面板批次和初始化命令无差异。
- [ ] 检查 240×320 方向、RGB/BGR、反色是否符合预期。
- [ ] 触摸 I2C 7-bit `0x58` 探测；读取 CST3530 数据并核对坐标范围。
- [ ] 测 INT5 中断和复位脉冲宽度。
- [ ] 用示波器/逻辑分析仪确认 CH32 `0x05` PWM 与背光亮度关系。
- [ ] 测 EXIO3 拉高时的 PA 爆音/底噪。
- [ ] 在 80 MHz 下做长时间刷新/触摸压力测试，再决定最终时钟。

## 7. 地址索引

| 地址 | 语义 |
| --- | --- |
| `0x420237ec` | factory `bsp_i2c_init` |
| `0x42023858` | factory `bsp_io_expander_init` |
| `0x420238fc` | factory `bsp_spi_init` |
| `0x420243f2` | factory `bsp_display_new` |
| `0x420245b2` | factory `bsp_touch_new` |
| `0x42024718` | factory `bsp_display_indev_init` |
| `0x42024368` | factory `bsp_display_brightness_set` |
| `0x42046b2c` | factory CH32 `set_pwm` |
| `0x42021c2c` | OTA `CustomBoard` 构造函数 |
| `0x42021a4e` | OTA `InitializeSt7789Display` |
| `0x4202186c` | OTA `CustomBacklight` 写 PWM |
| `0x42021876` | OTA `GetAudioCodec` |

## 8. 相关文档

- [OTA CustomBoard](15_ota_custom_board.md)
- [音频与 I2S](03_audio_i2s.md)
- [Brookesia 0.7 板级适配](08_brookesia07_board_adaptation.md)
- [Ghidra 发现](09_ghidra_findings.md)
- [证据账本](../reference/evidence-ledger.md)
