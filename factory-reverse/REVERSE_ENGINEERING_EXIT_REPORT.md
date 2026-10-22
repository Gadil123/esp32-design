# Factory V1.1 静态逆向结项报告

> **结论**：STATIC REVERSE ENGINEERING = CLOSED；BROOKESIA 0.7 PORTING = CONDITIONAL GO。
>
> 时间基线：2026-10；分析对象 Waveshare ESP32-C5-Touch-LCD-2.8 FactoryApp V1.1（factory + ota_0 Xiaozhi v2.2.6）。此处“结项”只表示继续**大范围静态逆向**的边际收益低；**不表示板级驱动已编译或硬件已通过测试**。

## 1. 核心研究成果

| 模块 | 原厂 / 逆向所得结论 | 新开发行动 |
| --- | --- | --- |
| 启动/镜像 | Factory 是桌面/启动器；AIChats 指向独立 ota_0 Xiaozhi；分区表 0x8000，bootloader 0x2000，factory/ota_0 独立 | 不照搬双 APP 默认设计，0.7 优先单固件 |
| MCU/存储 | ESP32-C5-WROOM-1-N32R8；32 MB Flash+8 MB PSRAM；原厂分区使用前 16 MB | 16MB 布局可作为首版 bring-up 起点，未来再讨论 32MB 与 OTA |
| OTA 板级类 | 恢复 CustomBoard 构造、GetAudioCodec、InitializeSt7789Display、CustomBacklight 主要调用链 | 不再猜音频/显示初始化的特殊参数 |
| I2C/CH32 | I2C0 SDA0/SCL1；CH32 7-bit 0x24，EXIO0/1 为 Touch/LCD reset、EXIO3 为功放；PWM reg 0x05、ADC reg 0x06 | CH32 背光、电池适配需自定义 HAL |
| LCD | ST7789，240×320 RGB565；Factory 80MHz，OTA 40MHz；OTA 最大 SPI transfer 153600、无 MISO；Factory/MICROSD 共用 MISO8 | 先 40MHz、分离复位，编译/实机再调优 |
| Touch | Factory 有 CST3530 7-bit 0x58/INT5/CH32 reset；OTA CustomBoard 未发现 touch 初始化 | 复用 Factory+公开 BSP 的 CST3530，不照抄 OTA |
| Audio | OTA ES8311 24kHz duplex、BCLK24/WS25、构造参数 TX26/RX27、MCLK NC、PA 由 CH32 | 受控扬声器/录音 A/B、检查 0.7 I2S slot/codec 复用 |
| microSD | SDSPI SCLK6/MOSI7/MISO8/CS23，与 LCD 同总线 | Board Manager 已有 fs_fat/spi，先验证现成设备管理及 SPI 共享，不默认造新 HAL |
| 电池 | VBAT 经 200K/100K 分压到 CH32 PC4；公开驱动可读 ADC 0x06 | 记录原始 ADC 实测/万用表标定，再做电量百分比 |

原始细节和证据分别见 [主指南](FINAL_BOARD_ADAPTATION_GUIDE.md)、[证据账本](reference/evidence-ledger.md)、[OTA 板级逆向](docs/15_ota_custom_board.md)、[显示触摸](docs/13_display_touch.md)、[音频冲突](docs/12_schematic_crosscheck.md)。

## 2. 与公开 BSP 相比，真正新增的价值

- 证实原厂 AIChats 与独立 Xiaozhi 镜像的边界，不把 Factory 桌面误当可复用完整语音实现。
- 恢复 OTA 厂商定制 CustomBoard 的函数级配置：40MHz ST7789（公开 BSP 80MHz）、153600 的 SPI bus 最大传输、单独创建 Backlight、无需触摸的 OTA 路线、以及 ES8311 ctor 24kHz/26/27。
- 找到 Factory 和 OTA 的 CH32 Reset/PA 生命周期差异，可作为初次 Bring-up 的替代/对照方案。
- 对照原理图与实际测试，暴露出 I2S GPIO26/27 方向的三方冲突，避免直接复制看似正确的公共 BSP。
- 分清物理 32 MB Flash 与原厂 16 MB 分区；明确电池 ADC 在 CH32 而非 C5。
- 实际用 ESP Board Manager 0.5.15 的生成器验证 4 peripherals / 5 devices 的板级 YAML（**不是编译**），并修正 CH32/CST3530 的 8-bit YAML I2C 地址与 ES8311 7-bit 地址的差别。

## 3. 状态与合理停止条件

| 研究模块 | 静态逆向状态 | 剩余验证 |
| --- | --- | --- |
| Bootloader、镜像和分区 | CLOSED | 真实烧录/恢复前需复核目标分区与备份 |
| Flash、PSRAM 物理容量 | CLOSED | 实际可用堆、DMA、是否扩大分区：BUILD/HARDWARE |
| Factory/OTA CustomBoard | CLOSED | App 初始化运行路径：HARDWARE |
| I2C 与 CH32 GPIO/PWM 协议 | CLOSED | 亮度/功放上电行为：HARDWARE |
| 电池硬件 ADC 路径 | CLOSED | Vref、分压及百分比标定：HARDWARE |
| ST7789/CST3530 基础配置 | CLOSED | 40/80MHz、触摸坐标/中断、驱动资源：BUILD/HARDWARE |
| ES8311 基础参数/构造 | CLOSED | GPIO26/27 物理冲突、slot/sample/duplex：HARDWARE |
| microSD/SPI 共享 | CLOSED（硬件已知） | fs_fat/spi 精确版本、共享 SPI 生命周期：BUILD/HARDWARE |
| C5 单核/PSRAM/I2S DMA | ACCEPTED RISK | 开发时结合真实编译及日志确认 |
| 重力球 95%/AI 初始化循环 | ACCEPTED RISK | 原固件串口与运行日志；不阻塞新固件 |
| 0.7 board YAML | PARSER VALIDATED | 尚缺完整组件编译/硬件验证 |
| Ghidra 自制扫描器 | ACCEPTED RISK | scan_refs2.py/scan_calls.py 有部分指令语义及控制流覆盖限制，不对“没有命中”作绝对否证 |

## 4. 不得抹掉的风险标签

1. **I2S：TX26/RX27 只是当前软件/早期 RX27 实测支持的工作基线**。原理图和公开 BSP 指向相反方向；扬声器 TX 尚未 A/B 验证。不要把 Factory 连续 GPIO 常量当成已证明的结构体字段方向。
2. **CH32 ADC：公开 helper 和硬件路径已知**，但 Factory 当前被检查路径未发现读取。否定结论受反编译/调用扫描覆盖限制；ADC 值与真实 VBAT、电量百分比均未验证。
3. **Parser≠编译≠实机**：当前 Board Manager 生成器接受 YAML；完整 ESP-IDF 构建、C hook、CH32/CST3530 组件及 I2S duplex 均未验证。
4. **0.7 ≠ 0.6 Phone**：Brookesia 0.7 组件化 HAL/Chatbot 与旧 Phone 桌面不是完全等价；不应一开始恢复旧桌面。
5. **SDSPI**：Board Manager 中存在 fs_fat/spi，开发前需要在固定 0.5.15 环境解析候选配置，验证与 LCD 的 SPI 总线共享；研究仓库当前没有声称挂载通过。
6. **C5 单核**：涉及原 Chatbot 中可能的 Core1 配置与任务栈大小，需在正式构建时清查；静态逆向没有证明无调度问题。
7. **SD/音频/CH32 的动态生命周期**：YAML 设置正确不等于资源共享或释放正确；应以实测日志和失败路径定位。

## 5. 下阶段建议及验收门槛

**GO：启动 Brookesia release/v0.7 开发；NO-GO：直接将本草案当成量产驱动或刷机即用版本。**

开发应在 https://github.com/Gadil123/pocketpi-esp32-c5-touch-lcd-2.8 单独分支进行，优先参阅 [FINAL_BOARD_ADAPTATION_GUIDE.md](FINAL_BOARD_ADAPTATION_GUIDE.md)。

1. **BUILD GATE**：固定 ESP-IDF 5.5.x、Brookesia 0.7、Board Manager 0.5.15；核对 Chatbot/Core1、HAL、外部组件，完成最小 build。无需通过屏幕/音频实测即可先做这一步。
2. **HARDWARE GATE**（刷写前需用户批准）：串口备份/恢复计划 → I2C probes → LCD 40MHz → Touch → 扬声器与麦克风 A/B → PA/背光 → 电池 ADC → SDSPI。
3. **VOICE GATE**：单固件实现完整语音输入/联网/大模型/播报，并监控堆、PSRAM、CPU、录音/播放延迟。
4. **EXPERIENCE GATE**：简单 LVGL 页、表情、照片/儿童模式按价值渐进加入。

当构建或实机验证遇到**明确指向原厂定制实现**、且公开 BSP 无答案的问题时，可以按地址在 PR #9 的 Ghidra 分析中定向补查；不自动重启大规模固件逆向。

## 6. 最终验收判断

- **STATIC REVERSE ENGINEERING: CLOSED** —— 关键板级引脚、初始化、协议与固件架构已经提供足够移植参考；剩余高价值未知主要是编译和实机验证。
- **BROOKESIA 0.7 PORTING: CONDITIONAL GO** —— 可以开始开发、建分支、试编译；硬件验证/刷写需要用户批准，已有草案不是已运行成品。
- **PR #9: 可作为研究资料 PR 待独立合并评审**；不能将其中 board draft 状态提升为“build-tested”或“hardware-tested”。
