# Factory 固件逆向：双 APP、音频引脚与可复用设计

> **新开发 Agent 请先看**：
> - [FINAL_BOARD_ADAPTATION_GUIDE.md](FINAL_BOARD_ADAPTATION_GUIDE.md)：ESP32-C5 的引脚、时序、CH32、I2S 争议、Brookesia 0.7 的开发与验收步骤。
> - [REVERSE_ENGINEERING_EXIT_REPORT.md](REVERSE_ENGINEERING_EXIT_REPORT.md)：静态逆向结项、已确认与未验证的边界。
> - [board-draft](board-draft/esp32_c5_touch_lcd_2_8/README.md)：Board Manager 0.5.15 parser 通过、**未编译且未实机验证**的初始草案。


> 状态：**官方 FactoryApp V1.1 的静态逆向笔记；未恢复完整源码，未刷写验证，不批准直接照搬。**  
> 分析对象：Waveshare `ESP32-C5-Touch-LCD-2.8` 官方 FactoryApp V1.1 BIN。  
> 本文把逆向结果整理成**可复用设计、板级常量、排查经验和验证清单**；原始证据见 [完整静态分析](reference/full-static-analysis.md)。

## 这个子项目回答什么

官方 FactoryApp 可以正常使用 AI，但公开仓库只有示例和 BIN，没有完整出厂源码。本次逆向要回答四个问题：

1. **能不能从 BIN 恢复完整源码？** 不能。可以恢复镜像结构、板级常量、启动链、字符串和部分逻辑，但不能得到可编译的 factory 工程。
2. **官方 AI 为什么能用？** factory app 里的 `AIChats` 是**启动器**：它把 `ota_0` 设为启动分区并重启，完整 Xiaozhi 语音栈在 `ota_0`，不在 factory app。
3. **本板 ES8311 I2S 到底怎么接？** V5 实测和 OTA 配置支持 **TX/DOUT=26、RX/DIN=27**；但原理图网名 `GPIO26=ASDOUT/GPIO27=DSDIN` 与公共 BSP 指向相反方向。当前把 26/27 作为工作基线，冲突未静态闭环，见 [原理图交叉核对](docs/12_schematic_crosscheck.md)。
4. **电池和 Flash 到底是多少？** 模块是 32 MB Flash + 8 MB PSRAM；factory 镜像/分区按 16 MB，电池 ADC 在 CH32 `PC4` 而不是 ESP32。
5. **显示/触摸在 factory 和 AI app 里是否一致？** 面板、引脚一致；factory 用 80 MHz + CST3530 触摸，ota_0 `CustomBoard` 用 40 MHz 且未链接触摸驱动。
6. **多 APP、重力球 95%、AI 初始化循环能复用/借鉴什么？** 可复用 Brookesia 的 app registry/生命周期/资源管理；重力球和 AI 循环目前只有假设，必须先拿串口日志，不能从字符串直接定因。

## 关键结论

| 问题 | 结论 | 证据等级 |
| --- | --- | --- |
| 完整官方源码 | **NO-GO**：factory 的 `main.cpp`、自定义 app、2.8 板 Xiaozhi board profile 未公开 | 高 |
| 官方 AI 路径 | factory `AIChats` → 设置 `ota_0` 启动 → 重启 → Xiaozhi v2.2.6 | 高置信推断 |
| I2S 数据脚 | **TX=26、RX=27** 为工作基线；原理图网名/公共 BSP 指向相反方向，三方冲突未闭环 | 中高；V5 RX27 实测 |
| 电池检测 | `BAT_ADC` 经 200K/100K 分压到 CH32 `PC4`；factory 未发现 ADC 读取；0.7 需 custom `PowerBatteryIface` | 硬件路径高；软件未用高置信 |
| Flash/PSRAM | 模块 32 MB Flash + 8 MB PSRAM；factory 镜像头 16 MB、ota_0 32 MB，分区表只到 `0xf10000` | 已确认 |
| 出厂镜像布局 | 双 app：`01_factory` + `xiaozhi 2.2.6`；初始 `otadata` 全 FF，默认 factory；分区表在 `0x8000`，`nvs` 在 `0x9000` | 已确认 |
| 显示/触摸差异 | factory/公共 BSP：ST7789 80 MHz + CST3530；ota_0：40 MHz、无触摸驱动 | 静态高置信 |
| ota_0 板级类 | `CustomBoard` 源码路径已恢复；构造时初始化 I2C/CH32/SPI/ST7789/背光，ES8311 由 `GetAudioCodec` 懒加载 | 静态高置信 |
| Assets | 24 个文件，`index.json` version 1，`srmodels.bin` 存在 | 已确认 |
| 重力球 95% | 校准不稳定/重试/进度未刷新等候选，未定因 | 未证明 |
| AI 初始化循环 | 优先查无 SSID/配网、OTA 重试、激活；assets 本镜像有效 | 未证明 |
| Ghidra | raw segment 可导入、入口可反汇编；Java 脚本可用，PyGhidra 未启用 | 已确认 |

## 可复用输出

| 文档 | 可复用什么 |
| --- | --- |
| [01 · 固件清单](docs/01_firmware_inventory.md) | 分区表、双 app、assets/storage、可复现的镜像事实 |
| [02 · 双 APP 与启动链](docs/02_dual_app_boot.md) | “UI shell + 独立语音 app”启动器模式、otadata 切换、回退风险 |
| [03 · 音频与 I2S](docs/03_audio_i2s.md) | 本板 ES8311/I2S 引脚、BSP 配置、麦克风初始化边界与验证方法 |
| [04 · Brookesia 多 APP](docs/04_brookesia_reuse.md) | app registry、生命周期、LVGL 锁、最近任务/资源回收、迁移取舍 |
| [05 · 重力球校准](docs/05_gravity_ball_calibration.md) | 校准状态机设计、超时/重试/UI 进度建议、串口排查清单 |
| [06 · AI 启动与网络](docs/06_ai_bringup.md) | Xiaozhi 初始化链、配网/OTA/激活失败矩阵、bring-up checklist |
| [07 · 逆向方法](docs/07_reverse_method.md) | 官方 BIN 获取、Ghidra/objdump 工作流、证据边界、工具限制 |
| [08 · Brookesia 0.7 板级适配](docs/08_brookesia07_board_adaptation.md) | 从 BIN 到 board YAML/setup_device 的映射、缺口与 bring-up 顺序 |
| [09 · Ghidra 发现](docs/09_ghidra_findings.md) | 双 code range、BSP 函数图、OTA ES8311 ctor、XREF 方法 |
| [10 · 电池检测](docs/10_battery_ch32_adc.md) | `BAT_ADC` → CH32 `PC4`、ADC 寄存器 `0x06`、factory 未读 ADC 的证据 |
| [11 · Flash 容量审计](docs/11_flash_capacity_audit.md) | 32 MB 模块 / 16 MB factory 分区 / OTA 32 MB 头的分层结论 |
| [12 · 原理图交叉核对](docs/12_schematic_crosscheck.md) | 网表、I2S 三方冲突、电池/PSRAM/Flash 的图面事实 |
| [13 · 显示与触摸对照](docs/13_display_touch.md) | factory / ota_0 / 公共 BSP 的 SPI、ST7789、CST3530、背光差异 |
| [14 · Bootloader 与分区表](docs/14_bootloader_memory_map.md) | 修正 `0x8000` 分区表、`0x2000` bootloader 真实边界 |
| [15 · ota_0 CustomBoard](docs/15_ota_custom_board.md) | 厂商板级类、构造顺序、CH32/SPI/显示/背光/ES8311 证据 |
| [板级草案](board-draft/esp32_c5_touch_lcd_2_8/README.md) | 可直接放进 `brookesia_hal_boards` 的 0.7 草案（YAML parser 已验证，未编译/未实机） |
| [完整静态分析](reference/full-static-analysis.md) | 全部地址、分区、字符串、Ghidra 记录和原始结论 |
| [证据账本](reference/evidence-ledger.md) | 每条主要结论的证据、置信度和未决状态 |

机器可读数据：

- [`data/firmware-layout.json`](data/firmware-layout.json)：分区、app、assets 摘要
- [`data/audio-pin-evidence.json`](data/audio-pin-evidence.json)：factory BSP 配置地址、字节和 OTA ctor 交叉证据
- [`data/board-esp32-c5-touch-lcd-2.8.json`](data/board-esp32-c5-touch-lcd-2.8.json)：完整引脚、设备、Brookesia 0.7 映射

## 对 Pocket OS 的直接建议

### 应该复用

1. **双 APP 边界的思路**：UI 桌面和完整语音应用解耦，避免把 Xiaozhi 的全部协议/音频栈塞进 Brookesia 桌面。
2. **音频引脚事实**：本板 BSP 和 OTA codec 都采用 `BCLK=24`、`WS=25`、`TX=26`、`RX=27`、`MCLK=NC`；先用这组值做录音 bring-up。
3. **Brookesia 0.7 的 HAL board package + app registry/生命周期**：板级初始化走 `brookesia_hal_boards`，app 层继续复用 registry/LvLock/资源回收；公开 `08_bookesia` 可参考 Phone 行为。
4. **启动/初始化可观测性**：AIChats 的“找不到分区/设置启动分区失败”与 Xiaozhi 的 OTA/激活重试都说明：每一步要有明确状态和错误，不要静默循环。

### 不应该直接复制

1. **公共 BSP 当前的 `.dout=DSIN(27)/.din=DOUT(26)`**：与 OTA 配置和 V5 实测冲突；在完成扬声器 A/B 或逻辑分析仪验证前，不要静默采用任一方。
2. **把 factory app 当成 Xiaozhi 源码库**：factory 内没有完整语音栈；要研究 AI，应分析 `ota_0` 的 Xiaozhi。
3. **把双 APP 当默认架构**：双 slot 切换会增加 otadata、回退、分区维护和调试复杂度；Pocket OS 若能在单 app 内完成桌面 + 语音组件，优先单 app。
4. **把 95%/初始化循环的字符串当根因**：这些只是线索；没有串口日志不能定因。

## 证据口径

本子项目沿用仓库的防幻觉规则，明确区分：

- **官方可证**：BIN 头、分区表、app descriptor、字符串、BSP 字段。
- **高置信推断**：由字符串 + 镜像结构 + 公共源码交叉得到，例如 AIChats 启动器。
- **待实机验证**：引脚、录音、启动切换、校准 95%、AI 循环。
- **设计建议**：本文给出的复用方式，不是已验证实现。

## 范围与非目标

**范围内：**

- 官方 BIN 的静态结构、双 app、音频常量、Brookesia/factory 交互证据
- 对 Pocket OS 的复用建议和 bring-up 清单
- 可复现的 Ghidra/objdump 方法

**非目标：**

- 恢复完整官方源码或重新编译 FactoryApp
- 修改/刷写设备，或声称硬件功能已通过
- 提供商业固件、密钥或私有服务器凭据
- 把逆向结论当作供应商保证

## 来源

- 官方 release（BIN 不纳入本仓库）：  
  <https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/releases/tag/v1.1.0>
- 官方源码/示例：  
  <https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8>
- 上游 Xiaozhi：  
  <https://github.com/78/xiaozhi-esp32>
- 分析对象 SHA256：  
  `92d0f25d7b8c43900c8882e2ca9cee1ca7c8a9338504bd392567f3d1e8cdf174`
