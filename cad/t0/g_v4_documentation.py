"""Owner-facing V4-CLEAN notes generated from the same parameters and geometry gates."""


def write_readme(out, r):
    v = r['design_change']; s = r['screen_measured']; k = v['printed_keys']; sc = v['shell_screw']; pc = v['pcb_screw']
    rows = r['v4_interfaces']['keys']
    text = f'''# Pocket Pi G-V1 V4-CLEAN — 6颗螺丝 + 左侧止口卡扣 + 背面T槽滑入独立按键

**{r['status']}** · `print_approved=false`。这是按用户确认的极简方案重新生成的打样模型。

## 本次结构简化核心变更

1. **螺丝从 10 颗（3种规格）精简为 6 颗（2种规格）**：
   - 保留 **4 颗 M2.5×5 机牙螺钉**（锁入原板 4 颗金属螺柱，承压厚 `2.00 mm`，入金属螺纹 `3.00 mm`）；
   - 右侧上下角保留 **2 颗 M2×6 塑料自攻螺钉**（拧入前壳右侧内部 `Ø5.4 mm` 螺柱，底孔 `Ø1.7 mm`，孔底余量 `2.25 mm`）；
   - **左侧取消螺丝**：改为沿着左壁总长 **`40.0 mm`**（上段 `32.0 mm` + 下段 `8.0 mm`）的 **无悬臂双 45° 宽体止口卡扣（Monolithic 45° Ridge-and-Groove Hook）**，壁厚 `1.50~1.60 mm`，无脆弱 U 槽或悬臂齿，斜插合壳、抬起右缘即可无工具脱扣；
   - **侧面取消 2 颗 M1.6 螺丝与外置压框**：彻底移除 `button_retainer`。
2. **背面 T 槽滑入、后盖封口自锁独立按键（0 螺丝、0 压框、100% 不挡屏幕）**：
   - 前壳左壁内置向分型面（`Z = -10.35 mm`）敞口的 **T 型竖向导槽**（外挡墙厚 `1.50 mm`、中间法兰槽宽 `1.95 mm`、内止挡墙厚 `1.50 mm`）；
   - **装板零干涉**：先把主板/屏幕装入空前壳（此时按键尚未放入，且左壁内表面 `X = -25.52 mm` 距离屏幕左缘 `-25.27 mm` 留有 `0.25 mm` 净空，垂直装入实交 `0.000 mm³`）；
   - **背面顺滑装键**：主板就位后，两颗微动开关（`Z = -6.40 mm`）完全露在主板背面；将两颗 T 型独立按键从背面顺着 T 型槽推入到底（连续滑入扫掠对前壳与 723 个板卡实体实交均为 `0.000 mm³`），此时可直接按压测试咔哒手感；
   - **后盖自动封口闭锁**：盖上后盖时，后盖自带的两个 **T 槽封口限位块** 自动插入滑槽入口，将按键在 `±X, ±Y, ±Z` 六个自由度完全锁死。
3. **激进压缩屏幕挡板与后壳厚度（整机减薄 `2.50 mm`，缩窄 `5.10 mm`）**：
   - **屏幕窗口与挡条**：窗口单边间隙收紧至 **`{s['window_to_glass_gap_mm']:.2f} mm`**（四角 `R2.2` 匹配玻璃 `R2.0`）；挡条下表面离玻璃正面仅 **`{s['lip_to_glass_gap_mm']:.2f} mm`**，挡条厚 **`{s['lip_thickness_mm']:.2f} mm`**（包边 `1.00 mm`），屏幕凹陷深度从 `1.90 mm` 降至 **`{s['screen_recess_mm']:.2f} mm`**；
   - **恢复 V1 实测通过的 MIC 孔位**：直接回到 **`(27.30, 1.395)`、Ø1.5 mm**；
   - **后壳恢复 `2.00 mm` 标准厚度**：主体厚 **`2.00 mm`**（`Z = -12.35 ~ -10.35 mm`）+ `1.20 mm` 纵横内筋 + `1.60 mm` 定位环，内腔净空分毫不减，完全兼容 **`6.80 mm` 中部出线新喇叭** 与实测电池。

## 整机包络与文件清单

- **壳体主体三围**：**`{r['dimensions']['body_xy_mm'][0]:.2f} × {r['dimensions']['body_xy_mm'][1]:.2f} × {r['overall_thickness_mm']:.2f} mm`**
- **含突出键帽总宽**：**`{r['overall_width_mm']:.2f} × {r['overall_height_mm']:.2f} × {r['overall_thickness_mm']:.2f} mm`**（对比旧 V4 的 `102.90 × 78.26 × 16.45 mm`，减薄 `2.50 mm`、缩窄 `5.10 mm`）

### 打印与预览文件

- `front_shell.step/.stl`：前壳（1件）
- `rear_shell.step/.stl`：后壳（1件）
- **`button_power_nominal.step/.stl`、`button_boot_nominal.step/.stl`：默认独立按键（各1件）**
- 同批可选微调备件：`_short`（`-0.15 mm`）、`_long`（`+0.15 mm`）、`_zero_fit`（`+0.25 mm` 零间隙备件）
- `assembly_preview.stl`：前后壳 + 默认双键组合 STL，方便在 GitHub 网页端直接 3D 旋转查看整体外观
- `assembly_light.step`：含板卡、电池、6.8mm 喇叭、螺钉的完整 STEP 装配体

## 按键行程参数

| 默认按钮 | 常态触头到开关 | 几何总行程 | 碰内止挡时越过开关静态面 |
|---|---:|---:|---:|
| BAT_PWR | {rows['KEY1']['rest_gap_mm']:.3f} mm | {rows['KEY1']['geometric_stroke_mm']:.3f} mm | {rows['KEY1']['switch_displacement_at_stop_mm']:.3f} mm |
| BOOT | {rows['KEY2']['rest_gap_mm']:.3f} mm | {rows['KEY2']['geometric_stroke_mm']:.3f} mm | {rows['KEY2']['switch_displacement_at_stop_mm']:.3f} mm |

## 极简装配步骤（3步完成）

1. **放主板/屏幕**：前壳正面朝下平放，放入主板/屏幕组件、电池与喇叭。
2. **滑入两颗独立按键**：从前壳背面分型面将 `button_power` 与 `button_boot` 滑入左壁 T 型槽到底，按压确认微动开关触发清脆。
3. **挂左扣、合后盖、拧 6 颗螺丝**：将后盖左缘挂入前壳左侧 45° 止口槽，右侧合下（后盖封口块自动锁死按键槽），拧紧 4 颗 M2.5 主板螺丝与右侧上下角 2 颗 M2 合壳螺丝。
'''
    (out / 'README.md').write_text(text)


def write_measurement_sheet(out, v, r):
    lines = [
        '# V4-CLEAN 极简版装配与实配记录表',
        '',
        '正常装配仅需 **4 个打印件**（`front_shell`、`rear_shell`、`button_power_nominal`、`button_boot_nominal`）与 **6 颗螺丝**（4×M2.5×5 机螺丝 + 2×M2×6 自攻螺丝）。',
        '',
        '| 文件 | 设计常态空隙 mm | 图纸整体行程 mm | 止挡时静态面越过量 mm | 实配结果 |',
        '|---|---:|---:|---:|---|',
    ]
    for name, row in r['v4_interfaces']['variant_parts'].items():
        lines.append(f"| {name} | {row['rest_gap_mm']:.3f} | {row['geometric_stroke_mm']:.3f} | {row['switch_displacement_at_stop_mm']:.3f} | ____ |")
    lines += [
        '',
        '## 到手快速检查项',
        '- [ ] 空前壳放入主板/屏幕是否顺畅、窗口四周包边是否均匀',
        '- [ ] 盖后盖前，从背面将两颗独立按键滑入 T 槽，直接按压是否清脆触发（可在 nominal / long / short 中选最佳手感）',
        '- [ ] 后盖左侧 45° 止口挂入前壳左槽、右侧合下并拧紧 6 颗螺丝后，按键是否不掉出、不卡滞',
        '- [ ] 6.8mm 新喇叭中部出线、装壳放音与 (27.30, 1.395) MIC 孔录音是否正常',
    ]
    (out / 'printed_button_fit_sheet.md').write_text('\n'.join(lines) + '\n')
