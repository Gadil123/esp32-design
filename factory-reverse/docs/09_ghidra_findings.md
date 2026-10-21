# 09 · Ghidra 发现：双 code range、BSP 函数图与 OTA 音频

> 结论等级：**反编译可复查；函数名是按调用序列/字符串的语义命名，不是符号表。**
> 工程目录：`/tmp/factory-reverse/ghidra_work2`（factory）、`/tmp/factory-reverse/ghidra_ota`（ota_0）。
> 工具：Ghidra `12.1.4` + JDK `21.0.12.1+1`；PyGhidra 未启用，只用 Java GhidraScript。

## 1. 之前为什么找不到字符串 XREF

第一轮只把 IRAM `0x40800000-0x40822e70` 当成代码段，漏掉了 IROM：

```text
factory IROM text: 0x42000020 - 0x42235a00
ota_0   IROM text: 0x42000020 - 0x4218955c
```

ESP32-C5 的 flash text 通过 `lui/addi` 形成绝对地址（例如
`lui a5,0x42249; addi a5,a5,...`），如果 `0x42000000` 段没有反汇编，Ghidra
自然看不到这些引用。修正后新增 `SetupAnalysis2.java`，显式创建：

```text
entry
code1  0x40800000 .. 0x4081c3a8 / 0x40822e70
code2  0x42000020 .. 0x4218955c / 0x42235a00
data   0x42190020 / 0x42240020
```

再对两个 code range 做 LinearDisasm，`factory_code2.dis` / `ota_code2.dis`
里才出现真实的字符串和常量引用。

## 2. 段布局

### factory

| 虚拟地址 | 大小 | 内容 |
| --- | ---: | --- |
| `0x42240020` | `0x272684` | DROM / rodata |
| `0x40800000` | `0xd96c` | IRAM text/vector |
| `0x42000020` | `0x2359e0` | IROM text |
| `0x4080d96c` | `0xf128` | IRAM data |
| `0x4081cb00` | `0x6370` | DRAM data |

### ota_0

| 虚拟地址 | 大小 | 内容 |
| --- | ---: | --- |
| `0x42190020` | `0xbc718` | DROM / rodata |
| `0x40800000` | `0x38d8` | IRAM text/vector |
| `0x42000020` | `0x18953c` | IROM text |
| `0x408038d8` | `0x12ca0` | IRAM data |
| `0x40816580` | `0x5e28` | DRAM data |

OTA entry：`0x408003a6`。

线性反汇编规模：

| 镜像 | 结果 |
| --- | --- |
| factory code2 | `805365` instructions，`9295` functions，`805495` total |
| ota_0 code1 | `39197` instructions，`612` functions |
| ota_0 code2 | `567197` instructions，`9010` functions，`606394` total |

这些是线性扫描的**上界**，包含少量误判函数；关键函数均经过调用者/被调用者
和常量交叉检查。

## 3. Factory BSP 函数图

| 地址 | 语义名 | 关键证据 |
| --- | --- | --- |
| `0x420237ec` | `bsp_i2c_init` | SDA 0 / SCL 1 / port 0 / glitch 7 / pull-up 1 |
| `0x42023858` | `bsp_io_expander_init` | I2C `0x24`，set_dir `0xb`，set_level `3`/`8` |
| `0x420238fc` | `bsp_spi_init` | host 1，mosi 7 / miso 8 / sclk 6 / dma 3 |
| `0x42023e06` | `bsp_audio_init` | I2S 22050 mono，24/25/26/27，MCLK -1 |
| `0x42024064` | `bsp_audio_codec_speaker_init` | ES8311 `0x30`，DAC mode，PA -1 |
| `0x420243f2` | `bsp_display_new` | ST7789，CS 10 / DC 9 / pclk 80M |
| `0x420245b2` | `bsp_touch_new` | CST3530 `0x58`，INT 5，reset mask 1 |
| `0x42024718` | `bsp_display_indev_init` | 调 display_new + touch_new |
| `0x42024368` | `bsp_display_brightness_set` | 调 `0x42046b2c` PWM wrapper |
| `0x42046950` | `custom_io_expander_new_i2c_ch32v003` wrapper | 地址 `0x24` |
| `0x4204890c` | `esp_io_expander_set_dir` | mask 参数 |
| `0x42048b14` | `esp_io_expander_set_level` | mask 参数 |
| `0x420241a8` | `qmi_init`（近似） | 接在 audio 初始化后的传感器链 |
| `0x42024254` | `pcf_init` | PCF85063A |
| `0x420242ca` | `shtc3_init` | SHTC3 |

### 调用链

```text
bsp_display_start
└─ bsp_display_new
   ├─ bsp_io_expander_init
   │  ├─ bsp_i2c_init (if needed)
   │  └─ set_dir(0xb); set_level(0x3, 0x8)
   ├─ spi init
   ├─ expander pin 1 low 200ms / high 200ms
   ├─ esp_lcd_new_panel_io_spi
   ├─ esp_lcd_new_panel_st7789
   ├─ panel_init / invert_color(true) / disp_on_off(true)
   └─ bsp_touch_new
      ├─ bsp_i2c_init
      ├─ expander pin 0 low 10ms / high 10ms
      ├─ esp_lcd_new_panel_io_i2c (32-bit command)
      └─ esp_lcd_touch_new_i2c_cst3530
```

`bsp_audio_init` 在没有外部 I2S data interface 时会先创建 TX/RX 通道；speaker
初始化再创建 ES8311 codec device。factory app 只做 speaker，麦克风路径不完整；
录音参考 OTA 的 duplex codec。

## 4. OTA Xiaozhi 音频

`Es8311AudioCodec` 相关函数：

| 地址 | 语义 |
| --- | --- |
| `0x4200bcdc` | `Es8311AudioCodec::Write` |
| `0x4200bd22` | `Es8311AudioCodec::Read` |
| `0x4200bdd0` | `UpdateDeviceState` |
| `0x4200bee0` | `CreateDuplexChannels` |
| `0x4200c072` | 构造函数 |
| `0x4200c28c` | `SetOutputVolume` |

`GetAudioCodec()` 位于 `0x42021876`，对 ctor 的调用可还原为：

```c
FUN_ram_4200c072(
    this,
    i2c_handle,
    0,          /* i2c port */
    24000,      /* input sample rate */
    24000,      /* output sample rate */
    -1,         /* MCLK */
    0x18,       /* BCLK = 24 */
    0x19,       /* WS   = 25 */
    0x1a,       /* DOUT = 26 */
    0x1b,       /* DIN  = 27 */
    -1,         /* PA pin */
    0x30,       /* ES8311 address */
    0,          /* use MCLK */
    0           /* PA inverted */
);
```

与 `xiaozhi-v2.2.6/main/audio/codecs/es8311_audio_codec.cc` 的构造签名逐项
一致。这是 I2S 方向的第二个独立证据。

## 5. XREF 方法与限制

Ghidra 的 `FindRefs.java` 对未定义的 data/string 仍返回 0；当前用文本管线：

1. `strings -t x factory_combined.bin` → 文件偏移。
2. 地址 = `0x40800000 + offset`（combined 以 `0x40800000` 为 base）。
3. 在 `factory_code2.dis` 中匹配 `lui`/`addi` 立即数组合。
4. 得到字符串地址 → 引用函数地址。

factory 约 `19457` 个 LUI/ADDI pair，ota 约 `14631` 个。这个方法能恢复
字符串和常量引用，但：

- 不能替代真正的数据类型/结构体恢复。
- 编译器可能用 `lui + load`、`auipc` 或常量池，纯文本匹配会漏。
- 函数边界来自线性扫描，少量 thunk/对齐数据会被误判。

因此文档中的函数名都是“语义名”，地址和参数字节才是证据。

## 6. 复现

```bash
# 1. 生成 combined image（每个 segment 按 vaddr - 0x40800000 放置）
# 2. 用 SetupAnalysis2.java 建立 entry + code1 + code2 + data
# 3. LinearDisasm 两个 code range
# 4. 反编译关键地址
```

脚本：

- `SetupAnalysis2.java`
- `LinearDisasm.java`
- `DecompileAt.java`
- `DumpDisasm.java`
- `FindRefs.java`（当前对 string 无效，保留作对照）

## 7. 相关文档

- [逆向方法](07_reverse_method.md)
- [音频与 I2S](03_audio_i2s.md)
- [Brookesia 0.7 适配](08_brookesia07_board_adaptation.md)
- [完整静态分析](../reference/full-static-analysis.md)
