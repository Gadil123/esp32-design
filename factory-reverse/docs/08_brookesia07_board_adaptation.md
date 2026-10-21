# 08 · Brookesia 0.7 板级适配：从 Factory BIN 到 board package

> 结论等级：**板级常量高置信；Brookesia 0.7 映射为草案，未编译、未刷写。**
> 目标：把 factory / OTA 的硬件事实落成 ESP-Brookesia `release/v0.7` 的
> `board_info.yaml`、`board_devices.yaml`、`board_peripherals.yaml`、
> `setup_device.c`、`sdkconfig.defaults.board`。
> 草案目录：[`board-draft/esp32_c5_touch_lcd_2_8`](../board-draft/esp32_c5_touch_lcd_2_8/README.md)。

## 1. 为什么以 0.7 为基线

Brookesia 0.7 的 `brookesia_hal_boards`（v0.7.5）已经把板级硬件抽象成：

```text
board_info.yaml        chip / manufacturer / version
board_peripherals.yaml I2C / I2S / SPI / GPIO / ADC / LEDC ...
board_devices.yaml     display / touch / audio_codec / fs / power / gpio_expander
setup_device.c         原厂初始化钩子（factory entry）
sdkconfig.defaults.board
```

这正好对应 factory BIN 里能恢复的 `bsp_*_init()` 调用链。0.8 的动态 Runtime
不是本阶段目标；先用 0.7 的静态 board package 跑通屏幕、触摸和音频。

## 2. 证据优先级

| 等级 | 来源 | 用途 |
| --- | --- | --- |
| A | factory BIN 反编译常量/调用序列 | 引脚、地址、复位时序、mask |
| A | OTA Xiaozhi `Es8311AudioCodec` ctor | 交叉验证 I2S 方向/采样率 |
| B | 公共 Waveshare BSP | 补齐 SPI/SD/传感器地址、面板参数 |
| B | Brookesia 0.7 参考板 YAML | 字段名和 HAL 能力边界 |
| C | 设计推断 | 采样率、方向、缺失功能的处理方式 |

冲突时 A > B；B 与 A 冲突的地方必须显式记录，不能静默取一个。

## 3. 板级常量

### 3.1 总线

| 项目 | 值 | 证据 |
| --- | --- | --- |
| I2C port | `0` | factory `bsp_i2c_init` |
| I2C SDA / SCL | `0` / `1` | factory 反编译 |
| I2C glitch ignore | `7` | factory 反编译 |
| I2C internal pull-up | `true` | factory 反编译 |
| LCD SPI host | `SPI2_HOST` | 公共 BSP `BSP_LCD_SPI_NUM` |
| SPI SCLK / MOSI / MISO | `6` / `7` / `8` | factory `bsp_spi_init` |
| LCD CS / DC | `10` / `9` | factory `bsp_display_new` |
| SD CS | `23` | 公共 BSP |

### 3.2 CH32V003 IO expander

| 项目 | 值 |
| --- | --- |
| I2C 地址 | `0x24` |
| 方向 mask | `0xb` = pin 0/1/3 输出 |
| 初始 level | pin 0/1/3 高 |
| pin 0 | LCD/touch reset |
| pin 1 | LCD reset |
| pin 3 | power amplifier enable |
| PWM | 寄存器 `0x05`，值 `0..255` |

注意：factory 的 `esp_io_expander_set_level(handle, 2, ...)` / `(handle, 1, ...)`
中的 `2`、`1` 是**引脚 mask**，不是引脚编号。`0xb` 同理。

### 3.3 显示与触摸

| 项目 | 值 |
| --- | --- |
| 面板 | ST7789，240x320，RGB565 |
| SPI mode / pclk | `0`；factory/公共 BSP `80 MHz`，ota_0 `40 MHz` |
| cmd / param bits | `8` / `8` |
| queue depth | `10` |
| invert color | `true` |
| panel reset | `-1`（由 expander pin 1 控制） |
| LCD reset 时序 | 低 200 ms → 高 200 ms |
| 触摸 | CST3530，`0x58`，400 kHz |
| 触摸 INT | GPIO `5` |
| 触摸 reset | expander pin 0 |
| 触摸 reset 时序 | 低 10 ms → 高 10 ms |

`esp_lcd_touch_config_t` 的 `x_max=240, y_max=320, int_gpio_num=5` 可从 factory
栈上的初始化结构直接读出；`rst_gpio_num=-1` 因为复位走 expander。

> 显示时钟以 40 MHz 作为 bring-up 基线：ota_0 的 `CustomBoard` 明确使用
> 40 MHz（`0x42021a4e`），factory/公共 BSP 使用 80 MHz。80 MHz 是否稳定
> 取决于排线/面板批次，需实测。ota_0 **没有** CST3530 触摸初始化，触摸
> 证据只能来自 factory `0x420245b2` 和公共 BSP。

### 3.4 音频

| 项目 | 值 |
| --- | --- |
| ES8311 | `0x30`，400 kHz |
| MCLK | `NC` |
| BCLK / WS | `24` / `25` |
| MCU TX / DOUT | `26` |
| MCU RX / DIN | `27` |
| PA | expander pin 3，`pa_pin=-1` |
| Factory BSP | 22050 Hz mono |
| OTA Xiaozhi | 24000 Hz duplex |
| 0.7 草案 | 16000 Hz stereo，便于与 recorder/player 默认对齐 |

**I2S 方向是工作假设，不是已闭环硬件事实**：

- OTA `GetAudioCodec()`（`0x42021876`）调 `Es8311AudioCodec` ctor：
  `mclk=-1, bclk=0x18, ws=0x19, dout=0x1a(26), din=0x1b(27)`。
- V5 实板观察：`.din=27` 录音正常；`.din=26` 时 PCM 全 0。
- factory `0x423c1a24` 结构体含 `24,25,26,27`，但字段顺序未从类型信息
  确认，不能单独当作方向证据。

公共 BSP 源码里的 `.dout = BSP_I2S_DSIN(27)` / `.din = BSP_I2S_DOUT(26)`
与 OTA/V5 相反；原理图网名 `GPIO26=I2S_ASDOUT`、`GPIO27=I2S_DSDIN` 也
指向相反方向。三方冲突未静态解决，迁移时暂按 **TX26/RX27**，并保留
[原理图交叉核对](12_schematic_crosscheck.md) 中的 A/B 测试要求。

### 3.5 存储与传感器

| 设备 | 值 | 0.7 支持 |
| --- | --- | --- |
| microSD | SPI：SCLK 6 / MOSI 7 / MISO 8 / CS 23 | 内置 `fs_fat` 示例是 SDMMC；需自定义 sdspi |
| QMI8658 | `0x6A` 或 `0x6B`（公共 BSP 用 high） | HAL 无 IMU 接口 |
| PCF85063A | `0x51` | HAL 无 RTC 接口 |
| SHTC3 | `0x70` | HAL 无温湿度接口 |
| 电池 | CH32 `PC4/EXIO_ADC`；`BAT_ADC` 经 200K/100K 分压 | 0.7 标准 battery ADC 不支持 CH32；草案关闭 |
| Flash/PSRAM | 模块 32 MB Flash / 8 MB PSRAM；factory 分区只用 16 MB | 草案保持 16 MB 分区 |

## 4. 0.7 board package 映射

| Factory/BSP 概念 | 0.7 文件 | 说明 |
| --- | --- | --- |
| `bsp_i2c_init` | `board_peripherals.yaml` | `type: i2c`, port 0, sda 0, scl 1 |
| `bsp_spi_init` | `board_peripherals.yaml` | `spi_display` 共享 MISO 8 |
| `bsp_audio_init` | `i2s_audio_out` / `i2s_audio_in` | 同一组 pins，`std-out` / `std-in` |
| `bsp_io_expander_init` | `gpio_expander` device | `chip: ch32v003` + 本地 component |
| `bsp_display_new` | `display_lcd` + `lcd_panel_factory_entry_t` | ST7789 + expander reset |
| `bsp_touch_new` | `lcd_touch` + `lcd_touch_factory_entry_t` | CST3530 + expander reset |
| `bsp_audio_codec_speaker_init` | `audio_dac` | `dac_enabled: true`, `mclk_enabled: false` |
| 录音 | `audio_adc` | 同一 ES8311 duplex，`adc_enabled: true` |
| `bsp_display_brightness_set` | 无标准 device | CH32 PWM，需 custom backlight |
| `bsp_io_expander_init` + battery | 无标准 device | CH32 ADC `0x06`，需 custom `PowerBatteryIface` |
| PA enable | expander 初始化 | pin 3 常高，无 `gpio_pa_control` |
| SD/传感器 | 应用层 | 不放进第一版 board YAML |

## 5. 与参考板的差异

选择 `waveshare/esp32_s3_touch_amoled_1_8` 作为 ES8311 模板，但有三处不同：

| 项目 | 1.8 参考板 | 本板 |
| --- | --- | --- |
| IO expander | TCA9554 `0x40` | CH32V003 `0x24` |
| 背光 | LEDC / 自定义 | CH32 PWM，寄存器 `0x05` |
| 触摸 | FT5x06 | CST3530，32-bit command |
| I2S MCLK | GPIO 16 | 未连接 |
| PA | GPIO 46 | expander pin 3 |

因此不能直接复制 1.8 的 `lcd_brightness` 或 `gpio_pa_control`；必须走
`setup_device.c` + CH32 component。

## 6. 已知风险

1. CST3530 的 `io_i2c_config`（`lcd_cmd_bits=32`、
   `disable_control_phase=true`）是否被 0.7.5 的 YAML 解析器完整接受，未验证。
2. `adc_channel_labels: ["M"]` 是否合法，未验证；可先删掉让 HAL 用默认。
3. `audio_dac` 与 `audio_adc` 同时初始化同一个 ES8311，参考 1.8 可行，但
   duplex 时钟/通道仍需实测。
4. 16 kHz 是迁移选择，不是 factory/OTA 的原值。
5. 背光只做了“常亮”兜底，没有运行时亮度。
6. SD 卡与 LCD 共用 SPI，DMA/总线互斥需要在应用层验证。
7. 电池 ADC 在 CH32 上；0.7 的 `battery_adc_impl` 只支持 ESP32 ADC，
   直接打开 power device 不会读到电池。需要 custom `PowerBatteryIface`。
8. 模块物理 32 MB Flash，但 factory 分区表只到 `0xf10000`；不要只因
   模块型号就把 board draft 改成 32 MB。
9. ota_0 `CustomBoard` 未包含 CST3530 触摸，也未提供可调背光；不要把它
   当作完整板级实现。详见 [显示与触摸](13_display_touch.md) 和
   [ota_0 CustomBoard](15_ota_custom_board.md)。

## 7. Bring-up 验收

按顺序，任一步失败就停：

```text
1. YAML parse + build
2. I2C probe: 0x24 / 0x30 / 0x58 / 0x51 / 0x6A / 0x70
3. LCD reset waveform + ST7789 init + 纯色填充
4. Touch coordinates + INT 5
5. Speaker 1 kHz tone
6. Mic loopback, check non-zero RMS and 1 kHz peak
7. CH32 ADC `0x06`: compare raw value with multimeter at 2–3 battery voltages
8. Runtime brightness via custom backlight
9. SD mount via sdspi
10. Sensors as app-level components
```

## 8. 相关文件

- [板级草案](../board-draft/esp32_c5_touch_lcd_2_8/README.md)
- [音频与 I2S](03_audio_i2s.md)
- [Brookesia 多 APP](04_brookesia_reuse.md)
- [Ghidra 发现](09_ghidra_findings.md)
- 机器可读数据：[`data/board-esp32-c5-touch-lcd-2.8.json`](../data/board-esp32-c5-touch-lcd-2.8.json)
