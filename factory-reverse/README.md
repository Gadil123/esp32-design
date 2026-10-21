# Factory 固件逆向：双 APP、音频引脚与可复用设计

> 状态：**官方 FactoryApp V1.1 的静态逆向笔记；未恢复完整源码，未刷写验证，不批准直接照搬。**  
> 分析对象：Waveshare `ESP32-C5-Touch-LCD-2.8` 官方 FactoryApp V1.1 BIN。  
> 本文把逆向结果整理成**可复用设计、板级常量、排查经验和验证清单**；原始证据见 [完整静态分析](reference/full-static-analysis.md)。

## 这个子项目回答什么

官方 FactoryApp 可以正常使用 AI，但公开仓库只有示例和 BIN，没有完整出厂源码。本次逆向要回答四个问题：

1. **能不能从 BIN 恢复完整源码？** 不能。可以恢复镜像结构、板级常量、启动链、字符串和部分逻辑，但不能得到可编译的 factory 工程。
2. **官方 AI 为什么能用？** factory app 里的 `AIChats` 是**启动器**：它把 `ota_0` 设为启动分区并重启，完整 Xiaozhi 语音栈在 `ota_0`，不在 factory app。
3. **本板 ES8311 I2S 到底怎么接？** factory BIN 的 BSP 配置使用 **TX/DOUT=26、RX/DIN=27**；当前公共 BSP 的“修正版”写成 27/26，方向很可能反了。
4. **多 APP、重力球 95%、AI 初始化循环能复用/借鉴什么？** 可复用 Brookesia 的 app registry/生命周期/资源管理；重力球和 AI 循环目前只有假设，必须先拿串口日志，不能从字符串直接定因。

## 关键结论

| 问题 | 结论 | 证据等级 |
| --- | --- | --- |
| 完整官方源码 | **NO-GO**：factory 的 `main.cpp`、自定义 app、2.8 板 Xiaozhi board profile 未公开 | 高 |
| 官方 AI 路径 | factory `AIChats` → 设置 `ota_0` 启动 → 重启 → Xiaozhi v2.2.6 | 高置信推断 |
| I2S 数据脚 | **TX=26、RX=27**；公共 BSP 当前 27/26 很可能反了 | 高；仍需实板复核 |
| 出厂镜像布局 | 双 app：`01_factory` + `xiaozhi 2.2.6`；初始 `otadata` 全 FF，默认 factory | 已确认 |
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
| [完整静态分析](reference/full-static-analysis.md) | 全部地址、分区、字符串、Ghidra 记录和原始结论 |

机器可读数据：

- [`data/firmware-layout.json`](data/firmware-layout.json)：分区、app、assets 摘要
- [`data/audio-pin-evidence.json`](data/audio-pin-evidence.json)：factory BSP 配置地址和字节

## 对 Pocket OS 的直接建议

### 应该复用

1. **双 APP 边界的思路**：UI 桌面和完整语音应用解耦，避免把 Xiaozhi 的全部协议/音频栈塞进 Brookesia 桌面。
2. **音频引脚事实**：本板 BSP 采用 `BCLK=24`、`WS=25`、`TX=26`、`RX=27`、`MCLK=NC`；先用这组值做录音 bring-up。
3. **Brookesia 的 app registry/生命周期**：公开 `08_bookesia` 已提供 Phone、registry、LvLock、app install/uninstall、最近任务和资源回收，适合作为 Pocket OS 的多 APP 基线。
4. **启动/初始化可观测性**：AIChats 的“找不到分区/设置启动分区失败”与 Xiaozhi 的 OTA/激活重试都说明：每一步要有明确状态和错误，不要静默循环。

### 不应该直接复制

1. **公共 BSP 当前的 `.dout=DSIN(27)/.din=DOUT(26)`**：与 factory BIN 和 V5 实测冲突；直接复制很可能再次得到 RX26 全 0。
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
