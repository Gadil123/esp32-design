# Pocket Pi V1 — P1 Review 文件

**不批准打印，不代表实物功能通过。** 电池/扬声器与最终厚度未定；开关实际行程、回弹、夹紧强度、打印公差和实物插头坐底均待验证。

优先打开 [轻量 STEP 装配](assembly_light.step) 或 [GLB 装配](assembly_light.glb)。精确保留 PCB/原厂螺母；其他原板元件标为 `ENVELOPE_NOT_DETAIL`，不可用它们定接触面。所有几何检查仍读取完整原始 STEP solids。Mac 查看器兼容性未实测。

| 结构件 | STEP | STL（mm，仅检查） |
| --- | --- | --- |
| FRONT 前壳与托臂 | [STEP](front_shell.step) | [STL](front_shell.stl) |
| REAR 后盖与支承 | [STEP](rear_shell.step) | [STL](rear_shell.stl) |
| KEY1 / BAT_PWR 键帽 | [STEP](key1_cap.step) | [STL](key1_cap.stl) |
| KEY2 / BOOT 键帽 | [STEP](key2_cap.step) | [STL](key2_cap.stl) |
| KEY3 / RESET 隐藏推杆 | [STEP](key3_cap.step) | [STL](key3_cap.stl) |
| 局部试样 FRONT 导向 | [STEP](coupon_front_guide.step) | [STL](coupon_front_guide.stl) |
| 局部试样 REAR 导向 | [STEP](coupon_rear_guide.step) | [STL](coupon_rear_guide.stl) |
| 局部试样 KEY1（与正式帽相同） | [STEP](coupon_key1_cap.step) | [STL](coupon_key1_cap.stl) |

[FRONT](front.png) · [REAR](rear.png) · [SIDE / FRONT 右、REAR 左](side.png) · [ISO FRONT](iso_front.png) · [连接/侧键/USB 剖视](structure_sections.png) · [ISO FRONT 爆炸图](assembly_exploded.png) · [键帽尺寸/局部试样](key_manufacturing.png)

[检查报告](checks.json) 含几何干涉、支承孔轴/叠层/接触距离、连续保守装入包络、离散合盖/螺钉姿态、局部最小特征与条件公差预算及十个负向夹具。`status=PASS` 仅表示所列几何检查通过；`functional_actuation_status=UNVERIFIED` 表示真实触发未验证。`manufacturing_status=manufacturing_unverified`：候选 SLA 供应商/韧性树脂及试样未确认，FDM 对比不合格；小样也未批准打印。

[候选工艺、最小特征、公差预算、试样验收和软件整合保护](../../docs/10_p1_manufacturability_review.md)。

[复现、结构决定、来源与全部边界](../../docs/09_cad_p1.md)。安装后使用 `./scripts/generate-p1.sh` 从原始 STEP 完整再生成。P1 PR 等待 Reviewer，不合并、不进入 P2。
