# G-V1 到货空间评估（不是改壳发行件）

机械基线 `ee8ec9d`；统一坐标 USB+Y / FRONT+Z / REAR−Z。当前阶段一完成，缺少MIC1声口/完整配件接线证据，未盲开孔或发布窄壳，不批准打印。

- [评估与下一步实测清单](../../docs/30_g_v1_hardware_arrival_space_and_mic_assessment.md)
- [精确检查报告](checks.json)：原始官方723实体、冻结真实壳体；配件仅主体包络。
- [缩宽局部敏感性](width_local_checks.json)：实际接收座内移2/4mm，非完整窄壳装配认证。
- [MIC与电池Z剖面](MIC_and_battery_XZ_sections.png)
- [PCB、电池与扬声器剖面](PCB_battery_speaker_sections.png)
- [新旧主体同尺度FRONT切开布局](old_new_body_same_scale_FRONT.png)

运行 `./scripts/assess-g-v1-hardware.sh` 重建所有报告和图，同时在忽略目录 `build/g-v1-hardware-assessment/assessment_NOT_RELEASED.step` 输出完整723原板实体＋冻结前后壳＋新主体包络的查看装配。它不是最终完整配件总成，不含已证实的保护板/接线，也不应交给打印厂。

原冻结前壳/后盖STEP/STL仍使用报告29指向文件；本次不重复提交未变化的打印网格。旧版完整装配取得办法见报告28。

## 精确查看模型的授权下载

本轮独立追加到原有私有 Draft 附件区，旧附件保留，Draft 不发布。普通 Draft 标签页不能作为有效下载链接；使用已登录此私有仓库的 `gh`：

```bash
gh release download t0-cad-review-20261016-9ec1022 \
  --repo Gadil123/esp32-design \
  --pattern g-v1-hardware-arrival-assessment-20261019.zip \
  --dir ./g-v1-arrival-assessment
```

ZIP 包含 `assessment_NOT_RELEASED.step`、剖面和检查报告。STEP 回读 **727/727有效实体**（723原板＋冻结前/后壳＋两个主体包络），详见 `assessment_export.json`。这不是旧版739实体完整安装候选，未加入未经实测的保护板/线束或将其当作“已安装成功”；四螺丝及原条件配件的检查另见 `checks.json`。FreeCAD可直接打开该STEP并展开五组查看；不要把主体包络当成最终配件模型。
