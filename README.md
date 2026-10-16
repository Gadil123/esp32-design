# Pocket Pi / Pocket OS — ESP32 便携多 APP 终端

> 状态：**硬件方案 V1 定义中 / 未采购验证 / 未进入可打印 CAD 阶段**  
> 更新：2026-10-16。仓库保存硬件、CAD 与软件选型的设计事实、取舍、来源和待验证项，防止将概念图或尚未实测的兼容性误当成已完成结果。

## 项目目标

自制一台接近卡片尺寸的语音优先、触屏多 APP 小终端，以 ESP32 负责联网、屏幕、麦克风、按钮、音频和电池；ASR/LLM/TTS 及 Pi Coding Agent 等较重的任务主要运行在家用 Linux 服务器或外部 API 上。Pi 会话只是可选 APP 之一，终端还规划家庭照片、日语练习、儿童故事、Home Assistant 和本地 GB 游戏等。

- 预算目标：**整机人民币 200 元以内**，如果报价超出需先明确偏差；价格仅规划，不是已确认订单。
- 生产方式：淘宝/第三方单件 3D 打印；没有自有打印机，**减少返工**优先于极致手感与花哨结构。
- 使用预期：V1 主要验证约半年；不为按钮追求超长期寿命，不接受明显不可靠的装配。
- 风格：克制的黑色工业设计，参考早前 Vibe Coding 设备草图与 FoloToy AI Passport；不以渲染图代替工程验证。

## 当前 V1 方向（已决策 vs 待验证）

| 主题 | V1 决定 | 注意 |
| --- | --- | --- |
| 主板 | Waveshare **ESP32-C5-Touch-LCD-2.8** | 2.8 寸 240×320 触摸屏；板载音频、充电管理 |
| PCB 方向 | 相对早前竖屏方案旋转 180°，**原生 USB-C 在机身顶部** | 方向基准见 [02](docs/02_hardware_orientation.md)，切勿混淆正面/背面 |
| 方向勘误 | **对官方横向板载资源图顺时针旋转 90°：USB-C 上，麦克风左，三颗按键右** | 这是官方图视角的方向描述；前后视图须镜像核验 |
| 实体按键 | V1 不加开关/洞洞板/接线；**沿用板载三键**，外壳做直接触发的短键帽或维护开孔 | BOOT 可用于语音；BAT_PWR 电源；RESET 复位不可任意重映射 |
| USB-C | 直接保留原生插口，不使用延长件 | 前提为顶部接口插拔空间满足 |
| 麦克风 | 唯一原厂 MIC1，优先短直声路；T0 未盲目开孔 | 进声方向/PCB 声学孔及装壳录音待核，ES8311 是 codec |
| 扬声器 | T0 改为右侧扩展仓下部、FRONT 正面格栅 | 30×20×6.8mm 临时包络，出声口/端子待实测 |
| 电池 | 3.7V MX1.25 接口，容量、长宽厚、保护及极性**待客服答复** | 未取得最终电池尺寸前不得锁定厚度 |
| 外壳 | T0：齐平前框、周边扣 + 右舱两 M2，PCB 独立夹位 | 12mm 完整名义包络；制造/实际连接未放行，见 T0 工程 |

### V2（明确后置）

正面两颗有手感的实体按键（可参考 Adafruit Pocket PiGRRL：普通轻触开关、洞洞板、独立键帽）；可能涉及扩展机身长度与接口避让。**不进入 V1 BOM 和结构范围**。

## 软件路线（2026-10-16 已明确方向；尚未实机验证）

- **长期系统：ESP-IDF + 微雪 BSP + ESP-Brookesia / LVGL**，自研多 APP 桌面；小智主固件不作为长期 APP 平台，但尽量复用其语音组件与开源服务器端。
- **可复现起点：微雪 `08_bookesia`（Brookesia Core 0.6.0-beta2）**。最新 0.8 的动态 APP / Codex 插件能力尚未在此 C5 板上完成移植，不能直接假定可安装 `.bpk`。
- **首批场景**：Pocket Chat 语音问答；随后是家庭照片与日语练习、儿童互动、Home Assistant；原版 GB 游戏作为独立离线模拟器实验。V1 不因游戏新增实体 A/B/方向键。
- **语音后端**：家庭 i5-6600K 服务器优先尝试小智精简 Server + 本地 ASR/VAD，LLM 可使用 DeepSeek API，TTS 先复用现成服务；性能、时延与内存均待测试。
- 决策、证据分级、完整场景列表与 PoC 退出标准见 **[08 · Pocket OS 软件架构与 APP 路线](docs/08_software_architecture_and_app_roadmap.md)**。

## 文档导航

- [01 · 需求、决策与历史勘误](docs/01_scope_decisions.md)
- [02 · 微雪官方硬件事实、视角与机械方向](docs/02_hardware_orientation.md)
- [03 · V1 外壳/三键/麦克风/扬声器结构方案](docs/03_mechanical_v1.md)
- [04 · 已研究的硬件及开源案例](docs/04_references.md)
- [05 · 下单和一次打样前验收清单](docs/05_validation_checklist.md)
- [06 · 微雪官方完整资料、规格、原理图、STEP、接口与疑点索引](docs/06_official_board_reference.md)
- [07 · 官方 STEP **实际解析**：侧键、USB-C、MIC 的尺寸与坐标](docs/07_cad_measurements.md)
- [08 · Pocket OS 软件选型、语音服务端、APP 场景和验证路线](docs/08_software_architecture_and_app_roadmap.md)
- [STEP 元件外包络机读数据 CSV](data/step_component_bounds.csv)
- [方向简图：官方 PCB 背面与屏幕正面镜像（非尺寸图）](assets/orientation_diagram.svg)
- [官方板载图顺时针旋转 90° 在线查看器](assets/official_board_rotated_viewer.html)（下载 HTML 后用浏览器打开；需联网加载原图）

## **防幻觉规则 / 后续协作规则**

1. 区分四种状态：**官方可证、用户明确决定、设计建议、待实物/STEP 验证**；不得把后一类写成“已经确认”。
2. 先统一视角：**PCB 背面、屏幕正面、官方原图及机身外观**不能互换左右。所有位置必须写明观察方向。
3. 概念效果图、AI 爆炸图不能作为孔位、接口、电池或 BOM 的依据；**不得根据渲染图开模/发打印**。
4. 任何接触实际部件的几何必须以微雪原始 STEP/DXF、选定电池/扬声器和实物尺寸确认；**无尺寸不定孔**。
5. V1 优先复用原生硬件，新增设计必须证明收益足以抵消成本和返工风险。
6. 不在仓库提交 API Key、Wi-Fi 密码、服务端凭证；远程控制 Pi 必须通过可信认证网关。
7. 当前无固件、无真实装配验证、无可生产 STL；不要给人“已完成设计”的误解。

## 官方入口

- [Waveshare 产品文档](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/)
- [硬件原理图、尺寸和示例索引](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Resources-And-Documents/)
- [官方 GitHub（含 dimensions / schematic）](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8)

**仓库用途是决策和可追溯设计资料；目前不是已可打印的 CAD 成品仓库。**

## T0 Ultra-Thin 独立 CAD 研究

[T0 工程、复现命令与验收门槛](docs/11_cad_t0.md) · [模型/图/报告](deliverables/t0/README.md)。本分支从 main 独立开发，未合并/变基 P0/P1 PR；Pocket OS 软件架构保留。12mm 名义几何不等于加工、实际接线或录音通过，不批准打印。

T0 Review 后的 A 纯卡扣修订、B 对照和准确 CAD 图纸见 [修订说明](docs/13_t0_snap_revision.md)。两版均等待 Reviewer，不批准打印。

T0 C 的四安装位装入闸门、双 M2.5 局部对照和独立 PA12 小样见 [C 可行性报告](docs/15_t0_c_pa12_feasibility.md)。首选装配路径被阻挡，未完成/放行整机。

T0 D 仿 AI Passport 的一次局部短齿/浅窝研究见 [D 闸门报告](docs/16_t0_d_local_passport_study.md)：浅窝缺少 PCB 向 FRONT 的保持约束，停止整壳推进；旧版本保留，不合并、不打印。

T0 E 采用三处原 A PCB 夹位与四浅窝，完成名义装入/止退验证和短齿整壳，见 [E 装配报告](docs/17_t0_e_three_clip_assembly.md) 及 [模型/图纸](deliverables/t0-e/README.md)。12.4mm 名义完整包络不等于 PA12 制造或实物功能通过；等待复审，不合并、不打印。
