# G-V1 95.60mm候选 / CONDITIONAL

机械基线ee8ec9d；原板/显示/一体键/四螺丝固定位置保留。USB+Y、FRONT+Z、REAR−Z。

[设计与定量对照31](../../docs/31_g_v1_95mm_layout_optimization.md) · [完整检查](checks.json) · [局部搜索](local_search.json) · [第一次整壳失败](iteration_a_failure.json) · [下绕线束中间结果](iteration_b_result.json)。

- `front_shell.step/.stl`、`rear_shell.step/.stl`：通过完整名义几何/装拆检查后导出，各单有效实体，STL闭合；**不批准打印**。
- `assembly_light_PROXIES.step`：低资源快速查看；显示屏/接口等含明确代理，不能用于碰撞或尺寸证明。
- `old_new_same_scale_FRONT.png`：冻结99.60与新95.60真实外观同尺度。
- `old_new_bay_same_scale_FRONT_cutaway.png`：扩展仓和完整原板实剖布局。
- `receiver_speaker_interference_resolved.png`：17.1252mm³冲突及最终0.83mm间隙。
- `latch_and_native_screw_sections.png`：真实下扣、原厂金属件、螺钉/承座剖面。
- `bay_Z_stack_and_support_section.png`：电池完整尺寸链与扬声器承托。
- `MIC_and_conditional_wiring.png`：MIC候选空气间隙与真实圆角路线投影；下口MX1扬声器已由用户确认。
- `REAR_and_FRONT_ISO.png`：后视与正面等轴测，所有方向有标注。

完整精确STEP在忽略目录 `build/g-v1-95mm/assembly_complete.step`，重新生成命令 `./scripts/generate-g-v1-95mm.sh`。739实体包括723真实原板＋2壳＋4螺钉包络＋10配件/线束/空间预留；后者含候选材料和自由空间，**不能称为739个已验证实物零件**。保留所有原板物理实体，不将完整官方STEP复制进Git历史。

## 授权下载完整装配

本轮独立追加私有Draft附件，不发布、不覆盖旧附件。使用有仓库权限的`gh`：

```bash
gh release download t0-cad-review-20261016-9ec1022 \
  --repo Gadil123/esp32-design \
  --pattern g-v1-95mm-layout-review-20261020.zip \
  --dir ./g-v1-95mm-review
```

ZIP含 `assembly_complete.step`、同坐标分组`viewer/`、原ee8ec9d壳体对照、新壳STEP/STL和检查/剖面。下载验证另见 `download_verification.json`（在PR中，不作为ZIP几何认证）。

FreeCAD可直接打开完整STEP；或解压后在桌面Python控制台执行：

```python
exec(open('/absolute/unpacked/viewer/view_g_v1_95mm_freecad.py').read())
open_assembly('/absolute/unpacked/viewer')
exploded()  # 视觉分解，非真实拆卸路径
assembled()
```

按五组显隐检查；`Battery.step`和`Speaker.step`是单独查看用，不要与包含它们的完整配件组重复计数。实际拆卸路径及其限制以报告31和JSON为准。FreeCAD GUI未在服务器执行；STEP经OCP真实回读，脚本检查Python语法，未声称FreeCAD GUI验收。

旧冻结前/后壳、E和PR #5保留。原按键不利公差失败、实际按力/行程、PA12薄特征、螺丝扭矩、真实线束服务与收音门槛均未关闭。
