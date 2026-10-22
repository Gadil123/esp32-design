# ESP32-C5-Touch-LCD-2.8 → ESP-Brookesia 0.7：最终板级适配与开发交接指南

> **用途**：给新的固件开发 Agent 使用；这是优先入口，不是已编译/已实测的官方 BSP。
>
> **研究状态**：Factory/OTA V1.1 静态逆向结束；板级草案已经用 ESP Board Manager 0.5.15 生成器解析，**尚未完成 ESP-IDF 编译、烧录或本轮实机验证**。
>
> **软件路线**：优先 ESP-Brookesia release/v0.7 的组件化 HAL + Agent/Chatbot 示例。暂不使用 0.8 的动态 Runtime；也不要假定 0.7 仍包含 0.6 Phone 的完整桌面/APP registry。
>
> **开发代码应在固件仓库实施**：https://github.com/Gadil123/pocketpi-esp32-c5-touch-lcd-2.8 。本仓库仅作为逆向证据与适配参考；勿直接覆盖或合并固件中的原有实验结果。

## 0. 阅读入口与证据等级

- [可用于试编译的 Board Manager 板级草案](board-draft/esp32_c5_touch_lcd_2_8/README.md)
- [静态逆向证据账本](reference/evidence-ledger.md)
- [Factory / OTA 显示触摸差异](docs/13_display_touch.md)
- [OTA Xiaozhi CustomBoard 函数级逆向](docs/15_ota_custom_board.md)
- [I2S 三方冲突及实机验证方案](docs/12_schematic_crosscheck.md)
- [CH32 电池检测](docs/10_battery_ch32_adc.md)
- [Flash/PSRAM 审计](docs/11_flash_capacity_audit.md)
- [Bootloader/分区结构](docs/14_bootloader_memory_map.md)
- [Brookesia 0.7 板级映射](docs/08_brookesia07_board_adaptation.md)
- [机器可读板级参数](data/board-esp32-c5-touch-lcd-2.8.json)

证据状态：**S=静态/源码/原理图可核对，P=仅 Board Manager parser 通过，H=需要实机验证，B=需要完整编译验证**。S 不意味着实机可用；P 不意味着能链接、上电或运行。

## 1. 建议锁定的技术基线

- 硬件：Waveshare ESP32-C5-Touch-LCD-2.8，ESP32-C5-WROOM-1-N32R8，**物理 Flash 32 MB + PSRAM 8 MB**（S）。
- FactoryApp V1.1：Factory/Brookesia 桌面镜像与 ota_0/Xiaozhi v2.2.6 是两个 APP（S）。原厂 AIChats 主要是切换启动镜像的启动器；**不建议照搬双分区切换作为 Pocket OS 默认架构**。
- ESP-Brookesia：官方 [release/v0.7](https://github.com/espressif/esp-brookesia/tree/release/v0.7)，使用组件化 HAL、Service、Agent、Expression 与 [Chatbot 示例](https://github.com/espressif/esp-brookesia/tree/release/v0.7/examples/agent/chatbot)。
- ESP Board Manager：逆向草案用 **0.5.15** 进行 parser 验证；正式构建应固定所使用的精确组件版本/commit，禁止无意漂移到不同的 API。
- ESP-IDF：优先从 **5.5.x** 的 C5 兼容工具链起步（原厂二进制为 5.5.4）；Brookesia 0.7 另支持至 6.0。不得直接把 0.8/IDF 6.1 的工程当成 0.7 配方。实际组合以干净编译为准。
- 目标：在**单个应用镜像**中先实现语音闭环、触屏显示、基础设置与表情；相册/儿童模式在基础硬件稳定后实现。不把旧 0.6 Phone 桌面移植作为最初的必要条件。

## 2. 引脚与设备事实

### 2.1 总线和 GPIO（S，除另注明）

| 子系统 | 事实/候选值 | 注意事项 |
| --- | --- | --- |
| ESP I2C | I2C0；SDA GPIO0 / SCL GPIO1；400 kHz 常用 | Factory glitch_ignore=7、内部 pull-up=true；OTA 构造中此项配置不同 |
| LCD SPI | SPI2_HOST（IDF host index 1）；SCLK 6、MOSI 7、MISO 8 | microSD 与 LCD 共享同一 SPI 总线 |
| LCD | ST7789 240×320 RGB565；CS10、DC9 | CH32 EXIO1 外部复位；IDF panel reset_gpio=-1 |
| microSD | SDSPI，CS23、SCLK6/MOSI7/MISO8 | 不能配置成 SDMMC 原生引脚模式 |
| 触摸 | CST3530；GPIO5 INT；I2C 7-bit 0x58 | CH32 EXIO0 复位；需触摸驱动及可能的独立 I2C handle |
| 音频 | ES8311 I2C 7-bit 0x30；BCLK24、WS25、MCLK=-1 | TX/RX 26/27 存在原理图冲突，见第4节 |
| IO 扩展 MCU | CH32V003，I2C 7-bit 0x24 | EXIO0=触摸 reset，EXIO1=LCD reset，EXIO3=功放 enable |
| IMU | QMI8658，7-bit 0x6A 或 0x6B（需探测） | 功能非首轮移植阻断项 |
| RTC | PCF85063A，7-bit 0x51 | 功能非首轮移植阻断项 |
| 温湿度 | SHTC3，7-bit 0x70 | 功能非首轮移植阻断项 |

**必须区分 I2C 地址格式（S/P）**：Board Manager 0.5.15 的 gpio_expander 和 lcd_touch 设备 YAML 配置接收 **8-bit 左移地址**；audio_codec 配置接收 **7-bit 原始地址**：

| 设备 | I2C 实际 7-bit 地址 | Board Manager YAML 字段 |
| --- | --- | --- |
| CH32V003 | 0x24 | gpio_expander peripherals[].i2c_addr: [0x48] |
| CST3530 | 0x58 | lcd_touch peripherals[].i2c_addr: [0xB0] |
| ES8311 | 0x30 | audio_adc / audio_dac peripherals[].address: 0x30 |

运行时 I2C probe 使用 7-bit 地址；不可把上述所有 YAML 地址一律左移。CST3530 的 io_i2c_config.dev_addr 由 Manager 填充，不要在 YAML 再手动设置。当前草案生成器已接受这些配置（P）。

### 2.2 CH32 特殊功能（S）

- I2C 7-bit 0x24；GPIO expander 的 mask 是位掩码而非引脚号。方向 mask=0x0B 对应 EXIO0/1/3 为输出。
- EXIO0：触摸 reset；EXIO1：LCD reset；EXIO3：PA_CTRL 功放使能。
- 背光：CH32 PWM register **0x05**，参数 **0–255**；复用公开驱动 custom_io_expander_set_pwm(handle, value)。**不支持直接用 ESP32 LEDC 代替**。
- 电池：VBAT → 200K/100K 分压 (理论约 1/3) → CH32 PC4/EXIO_ADC；通过公开驱动 custom_io_expander_get_adc() 读 register **0x06**，返回标称 10-bit、两字节小端原始 ADC（S）。Vref、误差和百分比曲线未经实测，不要硬编码准确电量。
- 功放电源：原厂把 EXIO3 设置为高；第一轮开发可先保持关闭，在音频 codec 就绪后开启，避免上电爆音；这是**设计建议，不是原厂行为的复制**。
- 0.7 默认的 DisplayBacklightIface/PowerBatteryIface 不能直接覆盖这些 CH32 功能；后续分别实现 CH32 PWM 后端、CH32 ADC 后端。首轮可背光固定值、暂不启用电池 UI。
- 原厂 Factory 的当前静态调用路径**未发现** CH32 ADC 读取；不能由此断言硬件不具备 ADC 功能。

## 3. 上电/初始化顺序与显示触摸差异

**建议 bring-up 顺序（综合 Factory/BSP 与故障定位需求，需 H）**：

1. 启动 NVS、基础系统及 I2C0 (SDA0/SCL1)，探测 CH32 0x24；不要先通过可疑 GPIO 控制电源。
2. 创建 CH32 expander，设置 EXIO0/1 输出；建议保持 PA EXIO3 低直到 codec 就绪（避免上电爆音）。
3. LCD：EXIO1 低 **200ms** → 高 **200ms**（Factory 的复位序列）；初始化 SPI2_HOST，ST7789 panel IO (CS10/DC9)、RGB565、invert=true、240×320。
4. LCD 时钟**先 40 MHz**（OTA Xiaozhi CustomBoard 已使用），屏幕稳定后才尝试 Factory/BSP 的 **80 MHz**；两者都不是本板长期稳定性保证。
5. Touch：EXIO0 低 **10ms** → 高 **10ms**；创建 CST3530 I2C 配置，触摸地址 0x58、INT GPIO5、240×320，验证旋转/镜像和坐标。
6. ES8311 / I2S 初始化，先验证扬声器、后验证麦克风，再测双工/半双工和录音。
7. 依次启用 CH32 PWM 背光动态控制、CH32 ADC、电源/存储/其他传感器。

**Factory 与 OTA 差异（S）**：

| 项目 | Factory | ota_0 Xiaozhi |
| --- | --- | --- |
| ST7789 SPI pclk | 80 MHz | 40 MHz |
| SPI MISO | GPIO8 | -1（显示用途） |
| SPI max transfer | 驱动默认 | 0x25800 = 153600 字节（整屏 RGB565） |
| LCD/Touch reset | 分离进行，200/200ms、10/10ms | EXIO0/1 同时脉冲，每段 1 tick |
| CST3530 touch init | 有 | OTA CustomBoard 链路未发现 |
| Backlight | CH32 PWM 百分比 | CustomBacklight 静态实现固定 0xFF |

注意：153600 是最大 SPI 传输设置，**不是**已证明使用整屏 DMA 缓冲。当前草案暂用 153600，构建/测试时按 LCD flush buffer/内存限制调整。Touch 的开源 CST3530 driver 可能另建 I2C device，Board Manager 又创建 panel-IO device，重复 init/deinit 时须关注清理和资源泄漏（B/H）。

## 4. ES8311：最高优先级的硬件未决项

OTA Xiaozhi 反编译的 GetAudioCodec() → Es8311AudioCodec 构造参数（S）：

| 参数 | 取值 |
| --- | --- |
| I2C port/address | 0 / 0x30 |
| 输入/输出采样率 | 24000 / 24000 Hz |
| MCLK | -1 (未连) |
| BCLK / WS | GPIO24 / GPIO25 |
| **MCU DOUT / TX** | **GPIO26（软件构造值）** |
| **MCU DIN / RX** | **GPIO27（软件构造值）** |
| PA pin / inversion | -1 / false（PA 经 CH32） |

**不可忽略的冲突**：硬件原理图的网络名 GPIO26=ASDOUT、GPIO27=DSDIN 以及公开 BSP 指向 **RX26/TX27**；反编译的 OTA 构造与此前 V5 录音观察指向 **TX26/RX27**。目前 V5 已记录 RX27 工作、RX26 录音全零，但**没有新的扬声器 A/B 或逻辑分析仪证据**。因此首轮固件配置可以临时采用 **TX26/RX27**，并要求实际比较扬声器与麦克风，不得称冲突已解决或静默改变两路。

另外：
- Factory 音频 BSP 22.05 kHz mono；OTA Xiaozhi **24 kHz duplex**；现有 0.7 草案采用 **16 kHz I2S stereo**，录音服务又是 **1 channel**。这是迁移选择而非 Factory 参数，需重点核对 ES8311、esp_codec_dev 对 I2S slot/声道的重配与重采样。
- 第一轮音频电气 smoke test 可以采用 OTA 的 **24 kHz duplex** 作为参考；待确认能双向收发后再按 0.7 Chatbot 服务的输入要求决定是否切为 16 kHz。
- 先单独验证播放 1 kHz 正弦波（按 TX26 与 TX27 做受控 A/B），再验证录音 PCM 非零 RMS 与音频内容，最后验证说话→ASR→LLM→TTS 的端到端闭环。
- 0.7 的 audio_adc/audio_dac 同为 ES8311，需确认共用一个物理 codec 时的生命周期与 I2S channel 竞争。不要因为 YAML 解析通过就假设 duplex 能工作。

## 5. microSD / Flash / PSRAM

- **microSD**：SPI2_HOST 与 LCD 共用，SD CS=23。ESP Board Manager 已支持 **fs_fat + sub_type: spi**，无需默认从零写 SDSPI HAL。基于 0.5.15 精确源码/生成器对可选配置做验证，再解决共享 SPI bus 的互斥、初始化一次、卡拔插、卸载与 SD 访问期间 LCD 刷新等问题（B/H）。首轮禁用 SD，并将其作为后续可选里程碑。
- **Flash**：模块物理 32 MB（S）；Factory image header 使用 16 MB，OTA image header 使用 32 MB，Factory 分区表只到 0xF10000。现有 board draft 有意保留 16 MB 分区配置供首次构建；**未来若用满 32 MB 必须设计新 partition CSV 与 OTA/回退机制**，不能只改一个 sdkconfig 位。
- **PSRAM**：模块 8 MB（S），目前配置源自公开示例；实际可分配内存、DMA 内部内存、LVGL frame buffer、I2S buffer/Wi-Fi 并发全部需要 B/H。
- **ESP32-C5 单主核**：Brookesia 0.7 Chatbot 示例可能有 Core1 固定任务/亲和性假设；移植前查找并修正。不要从 C5 的 PSRAM 容量推断有足够 DMA-capable 内部 RAM。

## 6. 现成资源与必须定制部分

**优先复用**：
- 官方 Brookesia 0.7 的 Chatbot、Agent/Service/Expression 与 HAL；不会默认拥有旧 Phone 完整桌面。
- [Brookesia 0.7 官方板级结构](https://github.com/espressif/esp-brookesia/tree/release/v0.7/hal/brookesia_hal_boards)：board_info.yaml、board_devices.yaml、board_peripherals.yaml、setup_device.c、sdkconfig.defaults.board。
- ESP Board Manager 原生的 SPI LCD、I2C touch、ES8311、fs_fat/spi。
- Waveshare 官方 ESP-IDF BSP、CST3530 驱动与 custom_io_expander_ch32v003 1.x 驱动（锁定版本，核对许可和依赖）。
- 本仓库已经 parser-validated 的 [board draft](board-draft/esp32_c5_touch_lcd_2_8/README.md) 作为**初始代码草案**，不是可直接烧录成品。

**必须实现或验证的本板工作**：
- CH32V003 与 Board Manager device factory 的挂接，C 头文件/符号/链接。
- CST3530 touch factory + I2C 总线、双 handle 清理策略。
- ES8311 duplex GPIO 冲突、采样率、声道/slot、PA 时序及共用物理 codec 的初始化。
- CH32 PWM DisplayBacklightIface（首轮可固定 PWM 后再接 UI）。
- CH32 ADC PowerBatteryIface（等实测电压标定后再实现百分比）。
- 0.7 Chatbot C5 单核及任务栈配置、LVGL/音频/Wi-Fi 共存。
- SDSPI 与 LCD 共享总线（后续阶段，不是第一步阻断项）。

## 7. 给新开发 Agent 的执行路线与验收

**强制按门槛推进；开发发生在固件仓库，不在本研究仓库。**

### Phase A：在没有硬件访问的环境中先完成编译

1. 盘点固件仓库当前代码/PR 和既有录音失败日志，不直接覆盖现有成果；建立新的开发分支。
2. 固定 ESP-IDF 5.5.x + Brookesia release/v0.7 组件版本 + Board Manager 0.5.15；从官方 Chatbot 示例和板级框架建立最小工程。严格核对依赖版本组合，不把不同主线 API 拼在一起。
3. 迁入本仓库 board-draft，复用官方 components；解决生成器、sdkconfig、组件依赖、C hook、I2C 地址、Core1 假设。
4. 编译最小项目；以 **idf.py build 成功、无未解析符号、内存/Flash 使用合理** 为 Phase A 验收。无 IDF 工具链时必须明确阻塞，不能用 parser 成功冒充编译成功。
5. 不创建任何真实 Wi-Fi 凭据文件、不提交密钥。

### Phase B：实机硬件 smoke test（必须由用户明确批准刷写）

1. 先备份可恢复所需的分区信息及当前固件/配置（不泄漏凭据），记录串口启动日志；确认固件恢复方案。
2. I2C probe：CH32 0x24、ES8311 0x30、CST3530 0x58，以及独立传感器；失败时先停在对应外设。
3. LCD 40 MHz 纯色填充、正确方向与刷新；Touch INT/坐标。
4. ES8311 播放 1 kHz → 麦克风 RMS/录音 → 必要时对 GPIO26/27 做单维度 A/B；记录实际运行证据。
5. CH32 PWM 亮度阶梯、电池 ADC 原始值、PA 上电爆音；不要先把 ADC 原始值换算成精确百分比。
6. SD (SDSPI) 与 LCD 并发及传感器，作为可选后续项。

### Phase C：最小 Pocket OS / AI 闭环

- 单固件中运行 0.7 Agent/Chatbot：联网、麦克风、ASR/小智服务、LLM/TTS 播放、表情。
- 再增加简洁 LVGL 页面切换、照片浏览、儿童/普通模式切换；先以稳定性与响应速度为优先。
- 对每阶段记载成功现象、串口日志、最大/剩余堆、PSRAM、任务栈、CPU/音频延迟及已知风险；避免无限制增长的日志文件。

## 8. 红线与验收出口

- **不做** 0.8 动态系统、Factory 全源码重建、0.6 Phone 整体合并、双 OTA slot 默认架构，也不为不影响 MVP 的传感器/照片提前阻塞语音。
- **不做** 无授权刷机、擦除或重建分区；不覆盖已保存的 Wi-Fi/OTA 凭据。
- **不做** SHA 校验、传播密钥或提交 Factory BIN。
- **不把** parser 通过、静态推断、V5 的单次录音观察等同于板级功能已经确认。
- 构建错误或硬件测试发现的新现象应先与本资料交叉比对；只有遇到无法解释的具体固件行为，才考虑有目标地重开 Factory 函数级逆向。

**研究项目的合理退出判断**：可进入 Brookesia 0.7 移植开发（CONDITIONAL GO），但本研究**不批准将板级草案直接认定为编译/实机验证完成的驱动**。

## 9. 原始参考

- [官方 Waveshare BSP/原理图](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8)
- [ESP-Brookesia 0.7](https://github.com/espressif/esp-brookesia/tree/release/v0.7)
- [ESP Board Manager](https://github.com/espressif/esp-board-manager)
- [Xiaozhi 上游](https://github.com/78/xiaozhi-esp32)
