# Pocket Pi V1 — P0 查看文件

**P0 静态基线，等待 Review；不批准打印。** 电池/扬声器型号、最终厚度、键帽行程、声孔方向及壳体锁紧结构未定。

优先下载 [轻量 STEP 装配](assembly_light.step)（约 2.2MB）或 [GLB 装配](assembly_light.glb)（约 0.59MB）。PCB/原厂螺母保留原始几何；标为 `ENVELOPE_NOT_DETAIL` 的屏幕、USB、KEY、MIC 为静态包络，不能作为局部接触面依据。8GB Mac 可在支持 STEP/glTF 的查看器中打开；尚未实测 Mac 兼容性。

- 壳体：[FRONT STEP](front_shell.step)、[REAR STEP](rear_shell.step)、[FRONT STL](front_shell.stl)、[REAR STL](rear_shell.stl)，STEP/STL 单位 mm。
- 预览：[FRONT](front.png)、[REAR](rear.png)、[SIDE（FRONT 右 / REAR 左）](side.png)、[ISO FRONT](iso_front.png)。每图左侧合壳、右侧隐藏壳体显示原始选中组件。
- [几何、方向、孔轴和干涉检查报告](checks.json)。检查使用完整原始板卡 solids，不使用简化包络代替原板。
- [复现命令、坐标定义、主要尺寸及全部风险](../../docs/08_cad_p0.md)。完整原板装配不在 Git 内，运行生成命令即可在本地取得。
