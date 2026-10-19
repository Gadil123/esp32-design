# Pocket Pi / Pocket OS — ESP32 便携多 APP 终端

> 状态：**G-V1 首版 CAD 候选已冻结 / 待实物测量与 MIC1 声路确认 / 尚未批准下单打印**  
> 更新：2026-10-17。当前基线为 PR #3 的 `ee8ec9d`；[冻结记录及下阶段交接](docs/29_g_v1_design_freeze_and_hardware_handoff.md) · [到货后实测清单 Issue #4](https://github.com/Gadil123/esp32-design/issues/4)。仓库区分设计决定、名义CAD检查和实物验证；旧 A～G 记录保留为历史证据。

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
| 实体按键 | **G-V1：** BAT_PWR 为前壳一体 L 形 PA12 弹片，BOOT 为前壳一体圆角矩形弹片，RESET Ø2.2mm 卡针孔；不新增独立键帽或额外开关 | 真实触发行程、按力与累积公差下触达尚待实物；BOOT 可复用为应用键 |
| USB-C | 直接保留原生插口，不使用延长件 | 前提为顶部接口插拔空间满足 |
| 麦克风 | 唯一原厂 MIC1，优先短直声路；T0 未盲目开孔 | 进声方向/PCB 声学孔及装壳录音待核，ES8311 是 codec |
| 扬声器 | G-V1 右侧扩展仓下部、FRONT 正面格栅 | 到货主体30×20×6.5mm、线长约40mm；出声口/端子及承托待确认，见报告30 |
| 电池 | 到货主体42.26×29.49×7.61mm；采用X29.49/Y42.26方向评估 | 保护板、接头、出线/安全余量及极性仍待确认；主体尺寸不是完整安装包络，见报告30 |
| 外壳 | **G-V1 候选：** 深前壳、齐平屏幕、两浅卡扣后盖、四颗候选 M2.5×4 机螺丝从后方固定原厂 PCB 金属安装件 | 99.60×77.86×12.3695mm 为名义CAD包络；MJF PA12 DFM、声孔及实物配合仍待确认 |

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
- [**29 · G-V1 当前候选冻结及到货后实测交接（最新硬件CAD入口）**](docs/29_g_v1_design_freeze_and_hardware_handoff.md)
- [**27 · BOOT 圆角矩形修改、原生CAD验证**](docs/27_t0_g_v1_boot_rectangular_key_revision.md)
- [**28 · 完整装配 STEP 下载和 FreeCAD 分解查看**](docs/28_g_v1_private_download_freecad.md)
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
7. 当前没有完成实物装配、声学、按键寿命和 PA12 厂商工艺验证。**已交付可查看的前后壳 STEP/STL，仅为候选，不能视为打印已放行。**

## 官方入口

- [Waveshare 产品文档](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/)
- [硬件原理图、尺寸和示例索引](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Resources-And-Documents/)
- [官方 GitHub（含 dimensions / schematic）](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8)

**仓库用途是决策和可追溯设计资料；当前保存可复现的 G-V1 CAD 候选与精确查看文件，但仍不是已获制造/实物功能批准的成品。**

## G-V1 当前冻结候选（Task26，优先阅读）

**当前首版基线：** `ee8ec9d`，仅 BOOT 更新为圆角长方形一体弹片；BAT_PWR 为 L 形，RESET 卡针孔。深前壳、前后壳两处浅卡扣、原厂四处 M2.5 金属安装件及后盖不再改动。完整 STEP 739/739 有效实体，名义最大厚度 **12.3695mm**；`BLOCKED_CONDITIONAL_PRINT_FIT` 以及 MIC1 实际声路、电池/喇叭包络、MJF 工艺仍待实测/审核。**用户本轮认可停止纯 CAD 优化，等待到货后再小改；不等于授权打印或结案这些风险。**

- [候选冻结及复测交接](docs/29_g_v1_design_freeze_and_hardware_handoff.md) · [实物到货后待办 Issue #4](https://github.com/Gadil123/esp32-design/issues/4)
- [新版前壳 STEP/STL、检查与真实CAD局部对比](deliverables/t0-g-v1-boot-rect/README.md) · [共用不变的后盖](deliverables/t0-g-v1/README.md)
- [完整723原厂实体装配 ZIP 的私有授权下载、FreeCAD 隐藏/视觉分解说明](docs/28_g_v1_private_download_freecad.md)；Draft Release 的普通网页会404，**不要用旧标签页面链接**。

以下 T0 A～G 为**历史设计/审查过程**，具体结论保留供追溯，**不替代以上 G-V1 最新候选**。

## T0 Ultra-Thin 独立 CAD 研究

[T0 工程、复现命令与验收门槛](docs/11_cad_t0.md) · [模型/图/报告](deliverables/t0/README.md)。本分支从 main 独立开发，未合并/变基 P0/P1 PR；Pocket OS 软件架构保留。12mm 名义几何不等于加工、实际接线或录音通过，不批准打印。

T0 Review 后的 A 纯卡扣修订、B 对照和准确 CAD 图纸见 [修订说明](docs/13_t0_snap_revision.md)。两版均等待 Reviewer，不批准打印。

T0 C 的四安装位装入闸门、双 M2.5 局部对照和独立 PA12 小样见 [C 可行性报告](docs/15_t0_c_pa12_feasibility.md)。首选装配路径被阻挡，未完成/放行整机。

T0 D 仿 AI Passport 的一次局部短齿/浅窝研究见 [D 闸门报告](docs/16_t0_d_local_passport_study.md)：浅窝缺少 PCB 向 FRONT 的保持约束，停止整壳推进；旧版本保留，不合并、不打印。

T0 E 采用三处原 A PCB 夹位与四浅窝，完成名义装入/止退验证和短齿整壳，见 [E 装配报告](docs/17_t0_e_three_clip_assembly.md) 及 [模型/图纸](deliverables/t0-e/README.md)。12.4mm 名义完整包络不等于 PA12 制造或实物功能通过；等待复审，不合并、不打印。

T0 G 与 E 并列保留：深前壳、屏幕下沉0.5、四颗原厂位 M2.5 锁后盖、四隐藏短舌，完整名义包络12.9mm。见 [G 装配与风险报告](docs/19_t0_g_recessed_assembly.md) 及 [模型、剖面、E/G 同尺度对照](deliverables/t0-g/README.md)。**定位容差未通过**：螺孔0.15游隙可耗尽侧键停靠约0.074mm间隙；0.8mm螺钉座、薄片保持拆卸亦未获实物/PA12放行。不合并、不打印。

### 到货后第一轮空间评估（2026-10-19）

[实测主体、MIC声路核查、缩宽敏感性与实物闸门](docs/30_g_v1_hardware_arrival_space_and_mic_assessment.md) · [真实CAD剖面和检查](deliverables/g-v1-hardware-assessment/README.md)。机械基线仍为 `ee8ec9d`，未修改冻结按键/壳体；单孔声口及完整接线证据不足，暂不发布修改后的打印文件。
