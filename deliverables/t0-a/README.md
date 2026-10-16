# T0 A 纯卡扣候选 / Review only

[工程说明](../../docs/13_t0_snap_revision.md) · [原 B 104mm 对照](../t0) · [完整精确 STEP 草稿附件](https://github.com/Gadil123/esp32-design/releases/tag/untagged-4c8e4087aeeff72f3e90)

A 壳体 99.6×77.86mm，含主候选键帽宽 101.5mm。约 97mm 未通过当前临时保护板空间检查。两种厚度都是名义 CAD 研究，不是实机或制造放行。

- [12.4mm 工程对照](12_4mm)：先用 `assembly_light.glb` 查看；零件 STEP/STL、轻量 STEP、`checks.json` 及各视图均在该目录。
- [12.0mm 挑战候选](12mm)：USB 下薄边约 0.480mm；不能因为厚度几何成立就打印。
- [键帽局部比较](key-study)：B/A 1.9mm、A 1.2mm 候选的接触/装入/运动与条件配合预算；低凸起零件为单独候选，不替换主装配。原 B 的准确图另存在子目录，原 B 交付文件未覆写。

`orthographic.png` 是同 mm 比例的 FRONT/LEFT/REAR；`key_sections.png` 是外露帽与隐藏 RESET 的真实局部剖面；`long_edge_sections.png` 区分合壳卡扣与独立 PCB 夹位。其余四向预览、厚度、接口及连接器图也全部来自 CAD，局部图不按整机比例。

完整 STEP 含所有原厂实体，各约 157MB，**不存入 Git**。草稿附件新增 `t0-a-review-complete.zip`，包含 A 两厚度的完整装配、零件/轻装配和报告；原 B 的 `t0-review-complete-assemblies.zip` 保留。需仓库权限；草稿附件不是正式生产 Release。

几何 PASS 与功能/制造门槛分开。键帽严格全接触门槛 FAIL，0.2mm 导向条件打印预算 FAIL，偏心触发/回弹未实测；卡扣弹性/手工释放/长缝翘曲未验证。MIC1 未开正式声孔，TF 实际取卡、USB 实物座入、MX 插头/接线及临时电池/扬声器仍待确认。所有文件 `print_approved=false`，等待 Reviewer，不合并、不打印。
