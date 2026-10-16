# G-V1 — BLOCKED first gate / review only

两颗日常帽从REAR后装，各与深FRONT侧壁相交 **11.004mm³**；反向拆出同样失败。依任务书21 **STOP**，未完成新卡扣或整壳；不批准打印。

[报告/唯一最小让步](../../docs/22_t0_g_v1_first_gate_stop.md) · [检查](checks.json) · [参数](../../cad/t0/t0-g-v1-gate-parameters.json)

```bash
./scripts/generate-t0-g-v1-gate.sh
```

| 文件 | 含义 |
|---|---|
| `deep_front_GATE_ONLY.step / .stl` | 齐平深前壳首闸门，未完成连接结构 |
| `rear_seats_GATE_ONLY.step / .stl` | 初步后盖/四承座，无新卡扣，非完成后盖 |
| `key1_cap.step / .stl`、`key2_cap.step / .stl` | 独立帽，实际行程待实物 |
| `key1_blocked_section.step`、`key2_blocked_section.step` | 完整原板对应的真实薄剖面和−3mm帽姿态 |
| `key1_rear_insertion_section.png`、`key2_rear_insertion_section.png` | 后装及反向拆出失败证据 |
| `flush_gate_section.png`、`preliminary_screw_section.png` | 齐平和初步1.35mm承座尺寸链，非固定通过 |
| `E_vs_G_V1_gate_same_scale.png` | 同尺度原生CAD对照，G-V1标注未完成 |

四件独立STEP各1有效实体、STL闭合，仅验证导出。含四螺丝的未完成闸门跨度12.400mm，**不是完整装配/公差验收**。E、旧G和Pocket OS不变。

完整原板碰撞姿态STEP不进Git；原私有草稿附件下载：

```bash
gh release download t0-cad-review-20261016-9ec1022 \
  --repo Gadil123/esp32-design --pattern t0-g-v1-blocked-gate.zip
```

包内保留全部723原厂实体，不是可打印装配。方向 **USB +Y TOP / FRONT +Z / REAR −Z**。
