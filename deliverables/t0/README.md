# T0 Review 文件

**不批准打印，不代表真实接线/拾音/材料已经验证。** 12mm 是包括全部已建模实体的名义最大包络。电池、扬声器、保护板、插头和线束均为 unverified 候选；MIC 没有盲目开孔。

12.4mm 对照：[轻量 GLB](assembly_light_12_4mm.glb) · [检查报告](checks_12_4mm.json)。USB 下边材料从约 0.480 增至 0.880mm；未获得制造/实物放行。

优先查看 [轻量 STEP](assembly_light.step) / [GLB](assembly_light.glb)，适合先在 8GB Mac 查看；Mac 实机查看性能未测试。轻量装配保留精确 PCB、原厂螺母、TF 和两座连接器，其余被简化的原板件明确标 `ENVELOPE_NOT_DETAIL`。所有工程干涉检查仍用完整原始 STEP solids。

| 单件 | STEP | STL（mm，仅 Review） |
| --- | --- | --- |
| FRONT 齐平前壳 | [STEP](front_shell.step) | [STL](front_shell.stl) |
| REAR 1.2mm 主体后盖 | [STEP](rear_shell.step) | [STL](rear_shell.stl) |
| KEY1 BAT_PWR | [STEP](key1_cap.step) | [STL](key1_cap.stl) |
| KEY2 BOOT | [STEP](key2_cap.step) | [STL](key2_cap.stl) |
| KEY3 RESET | [STEP](key3_cap.step) | [STL](key3_cap.stl) |

[FRONT](front.png) · [REAR / 盖隐藏布局](rear.png) · [SIDE / FRONT 右 REAR 左](side.png) · [ISO FRONT](iso_front.png) · [厚度剖面](thickness_section.png) · [连接剖面](connection_sections.png) · [右侧连接器](connector_layout.png) · [接口](interface_openings.png) · [检查报告](checks.json)

完整 12mm STEP 包括 723 个官方 solids 及所有已建模外壳、螺钉、螺母、泡棉/胶/阻尼和临时配件/线束。它不表示未知插头的插入鼻、配件端子已被精确还原。该大装配不进入 Git 历史；在 [T0 完整模型草稿附件](https://github.com/Gadil123/esp32-design/releases/tag/untagged-4c8e4087aeeff72f3e90) 下载，附件同时包含 `assembly_complete_12mm.step`、`assembly_complete_12.4mm.step`、两版报告及 12.4mm 单件/轻量文件。本地运行 `./scripts/generate-t0.sh` 也会生成它及 `t0-complete-assembly.zip`。

[工程说明、尺寸比较、全部未验证项](../../docs/11_cad_t0.md)。报告中 `geometry_status=PASS` 仅覆盖列明的刚性/候选几何；制造、真实连接、TF 动作、声孔和录音门槛另列，不能据此放行。
