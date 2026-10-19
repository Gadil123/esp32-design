# G-V1 95.60mm · T1 首次试打印最终交付

本目录由 `python scripts/finalize-g-v1-t1-print.py` 自动生成，源头为 [PR #6](https://github.com/Gadil123/esp32-design/pull/6) 经 [PR #7](https://github.com/Gadil123/esp32-design/pull/7) 独立审查的 95.60mm 候选。

**用户确认：选择在 CAD 内直接新增正面 Ø1.5mm MIC 孔；可以生成 T1 试打印交付文件。尚未向厂家下单，也不能视为厂家确认工艺。**

## 交付清单

- `front_shell_MIC_1p5mm.step` / `front_shell_MIC_1p5mm.stl`：真实 OpenCascade 布尔减法切出前壳 Ø1.5mm 通孔，坐标 **FRONT X27.30/Y1.395**，贯穿候选前面板 Z−0.50…+0.70。
- `rear_shell_UNCHANGED.step` / `rear_shell_UNCHANGED.stl`：与 PR #6 的 95.60mm 后盖**一致，不做任何修改**。
- `print_checks.json`：切孔体积、STEP有效性、STL水密与体积、整件包络检查记录。
- `G-V1_95p60_T1_MIC1p5_PRINT_FILES.zip`：包含上面4个模型和检查记录，用于交付/存档。

**不得将旧目录 `deliverables/g-v1-95mm/front_shell.stl` 作为最终前壳提交**：该文件尚无MIC孔。也不得把带有代理形状的 `assembly_light_PROXIES.step` 交给打印厂作为整件壳体模型。

## 检查证据边界

- 几何上贯穿 Ø1.5mm 孔；孔到 MIC1 封装外侧的自然空气路径沿用 PR #6 的有条件几何验证。**真实 MIC1 芯片声口方向和装壳收音效果仍需 T1 实物验证**。
- 生成脚本只切除预计约 **2.1206mm³** 前面板材料，验证其他范围没有非预期变动；后盖原样保留。
- PR #6 原有 723 实体/739 实体完整装配和装拆路径检查仍是本次机械基础；本步骤只改变一处非承力的正面圆孔，不声称重新跑完全部装配验证。
- 独立 Reviewer 的结论是 **CONDITIONAL GO (T1)**，**并非量产批准**。

## 提交厂家前仍须确认

1. MJF PA12 对 0.81mm×约12mm 连续薄壁、1.0mm U槽、0.30mm卡扣止退、0.15mm轴向游隙、1.0mm螺钉承座及清粉/精度的适配性；不要对卡扣配合面进行滚桶或侵蚀性喷砂，不得随意缩放模型。
2. 使用实物机螺丝试入四处金属件，确认确为 M2.5 螺纹及适合的螺纹长度。
3. 到货后优先验证装板与卡扣/一体式按键，随后验证装壳收音和扬声器回声。无须在本轮重复开发声道。

**用户当前批准生成文件，不等同已授权代理代下单。**
