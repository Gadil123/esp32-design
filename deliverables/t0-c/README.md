# T0 C 可行性闸门与独立 PA12 小样

**状态：`BLOCKED_FIXED_STOP_INSERTION`，没有完成可装配的 C 整壳。** [工程结论与复现](../../docs/15_t0_c_pa12_feasibility.md) · [本轮任务书](../../docs/14_t0_pa12_simple_assembly_task.md) · [A 保留](../t0-a) · [B 保留](../t0)。

首选“四个固定前环台 + 后盖定位窝”最终位姿无碰撞，但原厂显示/PCB 从后方直线放入时被环台挡住。按任务书阶段闸门停止整壳重写，没有把静态模型标成可装配、没有自动恢复 PCB 弹性夹位。

| 文件 | 含义 |
| --- | --- |
| `C1_four_mount_static_BLOCKED.step` | 原始 PCB/显示/四金属件及局部支承；用于查看失败，不是打印件 |
| `C2_two_native_M2_5_REAR_local_ONLY.step` | 两颗低头 M2.5 与后盖局部承座比较；局部 Z 包络 12.4mm，承座仅约 0.8mm，制造未放行；不是完整前后壳 |
| `mount_assembly_sections.png` | 最终静态、被挡住的中间位置及低头螺钉局部剖面 |
| `mount_orthographic.png` | 实际原板/局部定位件 FRONT/LEFT/REAR；不是完整 C 外观 |
| `four_latch_release_plan.png` | 四扣位置与局部开盖建议；完整薄盖依次拆卸尚未证明 |
| `USB_two_side_ribs_local.step` / `usb_local.png` | 不改孔、不加厚整机的两侧局部加强；0.880mm 薄边风险仍在 |
| `key_fixture_*_context_NOT_PRINT.step` / `RESET_2_2_fixture_context_NOT_PRINT.step` | 指定原始坐标下的局部配合，含原厂开关参考；用于看装配，不直接打印这个多实体文件 |
| `key_sample_sections.png` | 独立活动帽/内凹 RESET 与固定导向的局部剖面 |
| `checks.json` | 原始 STEP 核对、装入反例、局部比较、开盖/USB/按键代理风险和逐件 STL 有效性 |

**打印候选仅在 `coupons/`，每个 STL 一实体。没有打印或下单批准。** 所有 STL 单位 mm，仅平移到非负位置，配合坐标变换在报告中；同名 STEP 是同一独立件。需要看原始配对位置时使用上面的 context STEP。

- 卡扣：`shell_snap_FRONT_receiver`、`shell_snap_REAR_beam`，共 2 件；一处入口与接收窗，梁强度/回弹/3mm 局部开缝需实物验证。
- 安装位：`native_mount_female_nest`，1 件；试原厂金属件外周配合，中央避空不插入螺纹孔，不得用 PCB 强压试配。
- 侧键：`key_guide_0_2/0_3/0_4_FRONT/REAR` 共 6 件 + `key_cap_COMMON` 1 件；共用一个帽。对齐平面并按 context 保持 0.15mm 接缝，记录装夹/尺寸；**先做离板空载滑动**。报告已有框体代理交叠风险，不得据此强压原板开关。
- RESET：`RESET_hole_2_0/2_2/2_5`，3 件 + `RESET_recessed_pusher_candidate` 1 件；主候选孔径暂 2.2mm，推杆凹入 1mm。孔缩、清粉、误操作及工具伸入尚待实物。

共 14 个独立 STL。它们关闭的是材料/局部配合风险，不能关闭 C 整体装入、四扣薄盖变形、M2.5 承座强度、真实线束、TF 插拔或 MIC1 收音门槛。两颗后盖固定螺丝会使 PCB 随盖移动，不等于已接受该装拆方案。

A/B 文件保留不覆盖。C 仅供同一 Draft PR #3 复审，不合并、不下单、不批准整机打印。
