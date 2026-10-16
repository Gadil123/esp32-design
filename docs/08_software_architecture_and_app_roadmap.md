# 08 · Pocket OS 软件选型、架构与 APP 场景

> 更新：2026-10-16  
> 阶段：**架构方向已讨论确定；尚无设备端固件移植、实机性能或服务器部署验证**。  
> 范围：本文记录软件路线与可选应用，不改变 [01 V1 硬件决策](01_scope_decisions.md)、[07 STEP 机械基准](07_cad_measurements.md) 和采购/打印验收门槛。  
> 状态口径：**用户已决定** / **官方或源码可证** / **工程建议** / **待实机验证**。不可把“可编译”“官方示例存在”“能够移植”写成“本项目已跑通”。

## 1. 产品定位与已达成的方向

**用户已决定**：Pocket Pi 不应局限于单一 Pi Coding Agent 控制器；定位为以触屏为主、语音优先的 **Pocket OS / 轻量无线多 APP 终端**。本机主要负责按键、触摸、麦克风采集、音频播放、显示、无线通信、简单缓存和设备管理；**ASR、LLM、TTS、个人业务逻辑优先交由家庭服务器或云端完成**。Game Boy 等轻量小游戏可完全离线在 C5 本地运行。

- 主硬件继续用 **Waveshare ESP32-C5-Touch-LCD-2.8**，240×320 触摸屏，保留原生 USB-C、BOOT、RESET、BAT_PWR、ES8311 音频、TF 卡、六轴传感器等能力（具体能力以厂商 BSP/实物为准）。
- **固件长期主线选择 ESP-IDF + 微雪 BSP + ESP-Brookesia（以下简称 Brookesia）**，而不是围绕独立的小智主固件搭建多 APP 桌面。
- **语音尽可能复用小智协议/语音组件 + xiaozhi-esp32-server**，不从零重写网络音频、ASR/TTS 服务。小智主固件作为技术与 UI 参考，不是当前长期主线。
- 先以微雪公开的 `08_bookesia` 工程为 **板级触摸桌面基线**；新版 Brookesia 0.8 是否可用，必须单独 PoC 验证。**选择 Brookesia ≠ 已决定立刻全量升级 0.8**。
- 产品初期可以一个固件只做一个功能，**但长期希望同一固件可切换多个 APP**；仅在硬件/协议冲突或实验隔离时使用独立固件。
- **V1 不加额外实体游戏按键**：沿用原板三键，其中 BOOT 是软件交互键候选，RESET/BAT_PWR 保留物理功能。早先“增加两颗正面按钮”已经明确后置至 V2，不能因为研究 GB 模拟器而悄悄改 BOM。
- 机身概念仍为克制的黑色工业设计，USB-C 顶部的朝向及 MIC/侧键前后视角需沿用 02/07 的机械勘误。屏幕软件旋转 180°与触控映射仍待实机验证。

### 软件 ADR（2026-10-16）

| ID | 决策/意向 | 状态 | 原因与边界 |
| --- | --- | --- | --- |
| S-001 | Brookesia 为长期多 APP 系统框架；LVGL 用于屏幕交互 | **用户已决定** | 相册、日语练习、儿童游戏、问答都需要独立交互界面 |
| S-002 | 用微雪 BSP/公开 `08_bookesia` 建立可复现的 C5 基线 | **工程执行选择** | 厂商已提供触摸/显示/Phone 示例，避免从通用 HAL 白手起家 |
| S-003 | 优先使用小智现成音频组件与第三方开源服务端 | **工程方向；兼容性待验证** | 不必重造 Opus/WebSocket、ASR/TTS 轮子 |
| S-004 | ASR/VAD 优先在家庭 Linux 服务器；LLM 可用 DeepSeek API；TTS 先求最少维护 | **用户方向 + 工程建议** | C5 作为薄终端，减少推理压力 |
| S-005 | 新版 Brookesia 0.8 动态 APP / Codex 插件是候选能力 | **待 PoC；未决版本选择** | 0.8 与微雪现成 0.6 集成存在实际迁移成本 |
| S-006 | 游戏优先测试原版 GB（DMG）模拟器，而不是承诺 GBA | **功能意向，待性能验证** | C99 开源内核可用，但 C5 + 屏幕 + 音频未实测 |
| S-007 | 所有带权限的 Pi / HA 操作经认证服务器网关和白名单 | **安全设计约束** | 随身设备及儿童模式不能直接获得家庭控制或任意 Shell 权限 |

## 2. 当前官方支持边界：不要混淆三件事

| 层次 | 已有证据 | 能直接复用什么 | 不能据此宣称什么 |
| --- | --- | --- | --- |
| **FactoryApp V1.1（预编译 BIN）** | 微雪出厂多 APP 固件已在这款板运行，含小智、相册、2048 等 | 外观、交互与功能验收参考；保留恢复途径 | **不能**认为完整出厂多 APP 源码已公开、可直接修改重新编译 |
| **微雪公开 `examples/esp-idf/08_bookesia`** | `main.cpp` 创建 `Phone`、安装 Registry APP / DrawingBoard，使用 240×320 深色 LVGL 主题；本地 `brookesia_core` 标注 **0.6.0-beta2** | 可读、可修改的触摸桌面起点与 BSP | **不是**完整 FactoryApp；不自带 0.8 动态 APP Runtime |
| **乐鑫 ESP-Brookesia 新架构（主线 v0.8）** | 官方组件有 HAL、GUI、Runtime、System Super、JS/Lua/WASM/ELF 和 PC 模拟器；有 Codex App Dev Plugin | 潜在更高效的动态 APP 研发和独立打包 | **未找到这块具体 C5 板的官方现成 0.8 HAL/固件**；`.bpk` 不是在旧版 08_bookesia 上直接安装 |

微雪仓库兼容性文档称 **ESP-IDF 5.5.5 / 6.1 的 8 个示例通过 CI 编译**；这只证明示例构建通过，**不是**触控+音频+系统多 APP 并行通过实机验证。微雪的本地 `brookesia_core` 为 0.6.0-beta2，不等于 0.8 已移植。

### 已知本板硬件/图形基础

- 显示：ST7789、240×320、LVGL 9；触摸：CST3530。微雪 BSP/示例已集成图形与触摸通路。
- 音频：ES8311 + I2S，连接方式与功放使能涉及 CH32V003 扩展；**硬件 BSP 已有实现，语音组件联合运行仍需验证**。
- 资源：ESP32-C5 单核 240MHz RISC-V，板型规格中有 8MB PSRAM、32MB Flash、TF 卡；这些只是开发前提，不代表可无限装应用或可流畅模拟任何游戏。
- 无线：2.4/5GHz Wi-Fi 足以传送语音；高层传输选 Wi-Fi 为主。C5 仅 BLE，不具备传统 Bluetooth Classic 音频 HFP；不能默认将它作为 Windows 普通蓝牙话筒。
- 触控：有 LVGL 输入不等于已经有我们自己的日语/相册/游戏页面；这部分仍需编写 APP 逻辑。

## 3. 建议的系统与服务端分层

```text
ESP32-C5 Pocket OS
├─ Brookesia / LVGL：桌面、状态栏、触控、多 APP 生命周期
├─ APP：问答、故事、家庭照片、日语、GB 模拟器、工具
├─ 共用服务：按键、音频 I/O、Wi-Fi、音量、电源、SD/缓存、配置
├─ 小智兼容语音客户端（优先复用现成组件）
└─ 微雪 BSP：ST7789 / CST3530 / ES8311 / CH32V003 / QMI8658
                       │ Wi-Fi：音频、文本、图片、操作请求
                       ▼
家庭 Linux 服务器 · Voice / App Gateway
├─ VAD：Silero（服务端）
├─ ASR：FunASR / SenseVoiceSmall；备选 Sherpa-ONNX INT8
├─ 意图/模式路由：chat / kid / jp / home / note / pi
├─ LLM：先 DeepSeek API（可按模式换模型）
├─ TTS：先低成本现成实现，如 EdgeTTS（在线）；本地方案另测
├─ APP API：NAS 照片、N2 题库、备忘、通知
└─ 受控能力：Home Assistant Conversation API / Pi SDK or RPC
```

**工程原则**：
1. 小智服务器的 VAD、ASR、TTS 和通信已经有开源实现，不再把完整语音链当自研项目；但具体 Brookesia 组件如何与自建服务器通信要对齐协议版本。
2. **ESP32 不运行完整 ASR、LLM、TTS**。设备端只做音频采样/编解码/播放、录音状态；本地唤醒词/VAD 可选，首版默认按键触发。
3. 先从“按一下开始、再按一下结束并发送”的批量录音闭环做起；语音流式上传、边生成边播报属于第二步。验证录音总耗时、首次文字出现、TTS 首音延迟，之后再优化。
4. 客户端和模式切换界面应尽量少绑定某一 LLM：业务模式与权限由服务器配置，新增纯问答 Profile 尽量不需要重刷固件。
5. **服务端不直接授予设备任意 Pi 编程工具能力**：Pi 只读/执行分级，执行需明确确认；家庭控制设备设置实体范围白名单，儿童模式不可调用高权限接口。
6. 不提交 API Key、Wi-Fi 密码、私有照片或儿童录音；本地缓存和录音保留策略需明确，尽量短暂保存与按需删除。远程使用依赖手机热点、VPN 或可信网关的网络可达性验证。

### 家庭服务器性能假设及验证

既有 Linux 主机 CPU 为 **i5-6600K**；以单设备、低并发为目标，理论上可承担 Silero VAD 和本地 FunASR / SenseVoiceSmall 的 CPU 推理，LLM 使用外部 API，TTS 初期用在线服务。开源 `xiaozhi-esp32-server` 官方精简配置对本地 FunASR 提示 2 核 / 4GB 内存，完整部署需求更高。

**这仅代表部署可行性判断，不是本机已实测**。需要验证主机可用内存、ASR 对 5s/15s 中文/日语音频的耗时、峰值内存、TTS 首音与端到端延迟。若 CPU 不足再试 Sherpa-ONNX INT8 或将高质量本地 TTS 转到 Windows GPU；无需一开始依赖 GPU。

## 4. 应用目录、意图与优先级

优先级是**建议开发次序**，不是承诺首版一次全上。

| APP / 模式 | 用户设想及交互 | 计算所在 | 可复用的基础 | 优先级 |
| --- | --- | --- | --- | --- |
| **Pocket Chat** | 物理键或触屏开始录音，回答文字打字机效果 + 语音播报，日常随问随答 | ASR/LLM/TTS 在服务端 | 小智语音链、LVGL | **P1 核心闭环** |
| **儿童故事与互动** | 故事、猜动物、提问、按选项分支推进；独立安全 Profile | 服务端 | 语音链+内容约束+故事 UI | **P2 值得做** |
| **家庭相册/回忆** | 服务器从 NAS/影像档案选图，推送缩图、日期、简介；触摸翻页，可朗读回忆 | 图片预处理/元数据在服务端 | 微雪 SD 图库示例+LVGL | **P2 已认可** |
| **日语练习** | N2/N3 题目、听力/口语、触屏选择、错题反馈；复用现有语法/错题项目 | 题库/SRS/ASR/判题在服务端 | LVGL+语音+既有题库 | **P2 已认可** |
| **Home Assistant** | 口述灯光/场景/设备状态，返回文字/语音确认 | HA 服务端 | HA Conversation API + 权限路由 | P2 / P3 |
| **Game Boy 游戏** | 原版 GB 俄罗斯方块、马力欧医生、宝可梦红/蓝/黄；本地模拟 | **本机 C5** | Peanut-GB C99 内核 + SD 卡 | **实验性 P2** |
| **语音便签** | 口述灵感，服务器归类成备忘、待办或 Markdown | 服务端 | ASR+文档存储接口 | P2 / P3 |
| **Pocket Pi Session** | 查询现有 Pi 会话/任务状态，后续可发起受控请求 | Pi 运行在服务器 | Pi SDK/RPC + 认证网关 | P3；权限复杂 |
| **Windows 语音输入** | Wi-Fi 传音 → 服务器转文字 → Windows Companion 写入文本框 | 服务端+PC Companion | ASR+局域网通信 | P3；不等于 BLE 麦克风 |
| **其他工具** | 温湿度、Wi-Fi 状态/漫游、咖啡记录、AI API 额度、完成通知、体感游戏 | 本机/服务端混合 | 已有传感器与 LAN 项目 | 候选，不扩大当前范围 |

**已有官方/开源示例与自研边界**：

- 微雪出厂固件展示：小智 AI、相册、2048、重力小球、画板、音乐、天气、传感器、设置等；可参考产品交互。
- 微雪公开独立例程：`02_2048`、`03_sd_lvgl`、`04_sd_music`、`06_wifi_weather`、`07_Ball_qmi`、`08_bookesia`；**需要重新集成到统一桌面**，不是完整 FactoryApp 可重建源码。
- 自研照片 APP 需实现 NAS API、图片尺寸/格式预处理、触摸翻页、缓存和失败占位；不在 C5 上跑图像大模型。
- 自研日语 APP 需复用已有 N2 题库/错题/SRS 的服务接口，不把完整学习数据库或判题模型移到 ESP32；音频朗读也可复用服务端 TTS。
- GB 模拟优先 [Peanut-GB](https://github.com/deltabeard/peanut-gb)（MIT，原版 DMG）；**C5 实机性能、音频、MBC/电池存档、游戏兼容性均未验证**。先从公开测试 ROM 入手，不在仓库提交商业游戏 ROM。GBC/NES 视性能单独评估，GBA 不列入目标。
- **游戏控制限制**：V1 并没有新增 A/B/方向实体键，先测试触摸虚拟方向键 + 可复用的 BOOT；若操作体验不好，不可未经新一轮硬件 ADR 就把 V2 按键塞回 V1。

## 5. Brookesia / 小智路线的取舍

| 候选 | 优点 | 局限 | 当前决定 |
| --- | --- | --- | --- |
| 小智主固件 Fork | 语音录放、Opus、联网、问答流程成熟 | 不是通用多 APP 桌面；本 2.8in C5 版型没有已确认主线即用适配 | **不作为长期主固件**；保留参考 |
| 微雪 BSP + `08_bookesia`（0.6） | 本板源码/屏幕/触摸集成现成；可作 C++ 原生 APP 基线 | 旧版，完整 FactoryApp 源码不可据此重建，缺新动态 Runtime | **首个可复现设备端基线** |
| Brookesia v0.8 + C5 HAL | 动态 APP、JSON UI、JS/Lua/WASM、PC 仿真、Codex App Dev Plugin | 本板 HAL、内存、动态安装与语音并行均需适配实测 | **单独受控 PoC，不能预设成功** |
| 自己从 LVGL/ESP-IDF 从零搭 OS | 完全灵活 | 桌面、状态栏、APP 生命周期等需重复造轮子 | **不优先** |

乐鑫新版 [App Dev Plugin](https://docs.espressif.com/projects/esp-brookesia/zh_CN/latest/plugin.html) 能连接 Codex/Toolkit，在 PC 上设计/模拟/打包 `.bpk`；**它是主机侧开发工具，不能让 0.6 微雪固件自动获得动态 APP 安装能力**。若 0.8 移植成本或 RAM 不合适，继续用经过测试的 0.6 原生 C++ APP，并不偏离长期 Brookesia 选型。

## 6. 验证路线与退出条件（与采购/机械并行但相互独立）

| 阶段 | 最小范围 | 验收证据 | 阻塞/回退 |
| --- | --- | --- | --- |
| **SW-G0 基线保全** | 保存微雪 FactoryApp 可恢复 BIN/烧录步骤；用板级示例编译 `08_bookesia` | 固件来源、构建版本、启动日志 | 设备未到手只能验证构建，不能报告实机通过 |
| **SW-G1 触控桌面** | 240×320 Phone、时钟/状态栏、画板、触控、按钮/屏幕旋转 | 实机照片/录屏、可用 SRAM/PSRAM、页面切换 | 遇问题先固定微雪 BSP/当前版本 |
| **SW-G2 服务端语音** | Linux 小智精简 Server：本地 VAD/ASR、DeepSeek API、初期在线 TTS；浏览器音频测试 | 5s/15s ASR/峰值 RAM/首音/整轮延迟和出错记录 | CPU 不足先调整 ASR，不着急换硬件 |
| **SW-G3 设备语音闭环** | C5 录音→服务端问答→屏幕文字→扬声器播放；验证可中断/超时 | 至少一轮完整人机交互；触摸与音频并行资源占用 | 小智组件不兼容则评估最小协议适配，避免重写 ASR/TTS |
| **SW-G4 多 APP 骨架** | 至少新增一个轻量原生 APP，支持返回桌面和保留状态 | 切换、内存释放、无卡死 | 不追求“一次全装” |
| **SW-G5 0.8 可行性** | 独立分支/PoC：HAL、System Super、内存、动态 `.bpk` 安装 | **实机**安装/启动/切换一个最小 APP + 稳定性数据 | 未通过就保留 0.6 原生 APP，暂停 0.8 迁移 |
| **SW-G6 个性化 APP** | 先相册或日语，再试 GB 公开 ROM / 触屏手感 | 数据与交互闭环，分别记录性能和体验 | 新的实体按键诉求只开 V2 ADR |

保持 **GitHub 代码与文档 → Codex 开发 → Reviewer 独立审查 → 决策/合并** 的流程。严禁依据 AI 概念图推导硬件尺寸；没有实机结果不标“通过”。不要求/不执行 SHA 校验。

## 7. 待澄清问题（不是阻止记录架构的理由）

1. 设备是否到手、FactoryApp 的具体实机稳定性、SD 卡/扬声器实际安装。
2. 08_bookesia 在目标 ESP-IDF 环境里的**本机编译结果**，真实占用/触控/屏幕旋转行为。
3. Brookesia 0.8 在单核 C5 + 8MB PSRAM 下能否运行 System Super、动态 APP 和小智音频。
4. `brookesia_agent_xiaozhi` 对这块 ES8311/CH32V003 板型的适配难点、与自建小智后端协议是否兼容。
5. i5-6600K 的实际 ASR 和 TTS 首音延迟、儿童/日语内容安全及隐私留存设置。
6. GB 模拟器在 C5 上的 FPS/音频延迟、触控可用性和宝可梦存档可靠性。
7. 手机热点时通过家中 WireGuard 访问服务器的可达路径；不能假设手机 VPN 会自动分享给热点终端。

## 8. 核心源码与官方依据

- [微雪板型、资源与出厂说明](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/)
- [微雪 C5 2.8in 源码](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8)
- [微雪 `08_bookesia/main.cpp`](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/examples/esp-idf/08_bookesia/main/main.cpp)
- [微雪 Brookesia Core 0.6.0-beta2 组件定义](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/examples/esp-idf/08_bookesia/components/brookesia_core/idf_component.yml)
- [微雪 SDK 兼容性说明](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/docs/compatibility.md)
- [乐鑫 ESP-Brookesia 版本/架构](https://github.com/espressif/esp-brookesia)
- [Brookesia Codex APP 开发插件](https://docs.espressif.com/projects/esp-brookesia/zh_CN/latest/plugin.html)
- [Brookesia 小智 Agent 组件](https://components.espressif.com/components/espressif/brookesia_agent_xiaozhi)
- [小智设备端主仓库](https://github.com/78/xiaozhi-esp32)
- [第三方小智开源 Server / 配置与性能工具](https://github.com/xinnan-tech/xiaozhi-esp32-server)
- [Peanut-GB 模拟器](https://github.com/deltabeard/peanut-gb)
- [Pi SDK/RPC 参考](https://github.com/badlogic/pi-mono)

**文档定位**：记录用户意图、目前技术证据与下一步验证；**不等同于 PRD、实机兼容报告或已交付固件**。
