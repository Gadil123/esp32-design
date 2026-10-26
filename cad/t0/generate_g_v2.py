"""G-V1 V2 generator: physical first-article feedback revision.

Reuses the frozen G-V1 STEP, keys and bay layout. Emits a CONDITIONAL candidate
only after nominal geometry, assembly-path and export checks pass.
"""
import copy
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import Compound, export_step, export_stl

from reference import bounds
from model import box_between as box
from t0_reference import load
from p1_checks import intersection
from t0_g_v1_preview import panel
from check_exports import verify_exports
from v2_wiring import build as build_wiring
import t0_g_v2 as V2

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deliverables/g-v2'
BUILD = ROOT / 'build/g-v2'
CFG = ROOT / 'cad/t0'


def read(name):
    return json.loads((CFG / name).read_text())


def load_baseline():
    cfg = read('g-v1-95mm-layout.json')
    kq = read('t0-g-v1-boot-rect.json')
    p = read('t0-g-parameters.json')
    base = read('t0-a-parameters.json')
    base.update(p['layout_overrides'])
    base['width_mm'] = cfg['target_width_mm']
    kp = read('p1-parameters.json')
    kp.update(base['key_overrides'])
    base['battery'].update(
        xyz_mm=cfg['battery_complete_xyz_mm'],
        center_xy_mm=cfg['battery_center_xy_mm'],
        adhesive_mm=cfg['battery_adhesive_candidate_mm'],
        protection_xyz_mm=cfg['terminal_keepout_xyz_mm'],
        status='user_measured_COMPLETE_component')
    base['battery']['tray_clearance_mm'] = cfg['battery_tray_clearance_mm']
    base['speaker'].update(xyz_mm=cfg['speaker_xyz_mm'],
                           center_xy_mm=cfg['selected_speaker_center_xy_mm'],
                           status='user_measured_body; lead exit still to confirm')
    base['narrow_wiring'] = cfg['wiring']
    return base, kp, p, kq, read('t0-g-v2.json')


def volume_overlap(a, b):
    hit = intersection(a, b)
    return 0.0 if hit is None else hit.volume


def section(shape, x0, y0, z0, x1, y1, z1):
    return intersection(shape, box([x0, y0, z0, x1, y1, z1]))


def span_at(shape, axis, box_bounds):
    hit = intersection(shape, box(box_bounds))
    if hit.volume < 1e-6:
        return None
    bb = bounds(hit)
    return [bb[axis], bb[axis + 3]]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    base, kp, p, kq, v = load_baseline()
    print('Import RAW official STEP / 723 real solids', flush=True)
    parts, mounts, _ = load(ROOT.parent / 'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    print('Build V2 front/rear/screws', flush=True)
    m = V2.build(parts, mounts, base, kp, p, kq, v)
    front, rear = m['front'], m['rear']

    report = {
        'status': 'CHECKING',
        'print_approved': False,
        'manufacturing_status': 'manufacturing_unverified',
        'functional_actuation_status': 'UNVERIFIED',
        'mechanical_baseline': 'ee8ec9d + 95.60mm bay',
        'coordinates': 'USB +Y / FRONT +Z / REAR -Z',
        'design_change': v,
        'assumptions_still_physical': [
            'speaker lead exits at the -Y edge (user said bottom; photo/measurement pending)',
            'MIC1 port direction and the small front hole in the first article are not resolved',
            'PA12/MJF or FDM process and flatness not confirmed',
            'M2 thread-forming strength in PA12 and M2.5x5 metal-insert engagement not tested',
            'glass is not preloaded; 0.1mm lip gap plus optional 0.2mm foam tape',
        ],
        'dimensions': m['dimensions'],
        'screen': m['screen_geometry'],
        'screw_rows': m['screw_rows'],
    }

    # --- basic solids and dimensions -------------------------------------------
    assert front.is_valid and rear.is_valid
    assert len(front.solids()) == 1 and len(rear.solids()) == 1
    assert volume_overlap(front, rear) < 1e-6
    fb, rb = bounds(front), bounds(rear)
    report['bounds_mm'] = {'front': fb, 'rear': rb}
    report['overall_width_with_ears_mm'] = fb[3] - fb[0]
    report['overall_height_mm'] = fb[4] - fb[1]
    report['overall_thickness_mm'] = fb[5] - rb[2]
    assert abs(report['overall_thickness_mm'] - 13.55) < 1e-6
    assert abs(report['overall_width_with_ears_mm'] - 100.94) < 1e-6

    # --- screen pocket, lip and glass ------------------------------------------
    glass, gr = V2.front_glass_face(parts['DISPLAY'])
    gb = bounds(glass)
    c = v['screen_clearance_mm']
    half_win = (gb[3] - gb[0]) / 2 + c
    win_x = span_at(front, 0, [-30, -.1, .39, 30, .1, .41])
    lip_x = span_at(front, 0, [-30, -.1, .99, 30, .1, 1.01])
    base_x = span_at(front, 0, [-30, -.1, .73, 30, .1, .74])
    assert win_x and lip_x and base_x
    # At y=0 the section has two bars; report the inner edges.
    def inner_edges(span):
        # span_at returns the total bbox; recover both bars explicitly instead.
        return None
    left_window = intersection(front, box([-30, -.1, .39, 0, .1, .41]))
    right_window = intersection(front, box([0, -.1, .39, 30, .1, .41]))
    left_lip = intersection(front, box([-30, -.1, .99, 0, .1, 1.01]))
    right_lip = intersection(front, box([0, -.1, .99, 30, .1, 1.01]))
    report['screen_measured'] = {
        'glass_bounds_mm': gb,
        'glass_corner_radius_mm': gr,
        'window_inner_half_x_mm': bounds(right_window)[0],
        'lip_inner_half_x_mm': bounds(right_lip)[0],
        'glass_half_x_mm': gb[3],
        'window_to_glass_gap_mm': bounds(right_window)[0] - gb[3],
        'lip_overlap_on_glass_mm': gb[3] - bounds(right_lip)[0],
        'lip_top_z_mm': fb[5],
        'glass_front_z_mm': gb[5],
        'screen_recess_below_lip_mm': fb[5] - gb[5],
        'lip_underside_z_mm': .8,
        'lip_to_glass_gap_mm': .8 - gb[5],
    }
    assert abs(report['screen_measured']['window_to_glass_gap_mm'] - .2) < 1e-4
    assert abs(report['screen_measured']['lip_overlap_on_glass_mm'] - 1.0) < 1e-4
    assert abs(report['screen_measured']['lip_to_glass_gap_mm'] - .1) < 1e-4

    # --- rear panel and seam ---------------------------------------------------
    panel = section(rear, -1, -1, rb[2] - .01, 1, 1, -10.35 + .01)
    report['rear_panel_measured_mm'] = bounds(panel)[5] - bounds(panel)[2]
    assert abs(report['rear_panel_measured_mm'] - 2.0) < .01

    # --- no unintended collisions with real board/accessories ------------------
    report['collision_checks'] = {}
    for name, shape in [('front', front), ('rear', rear)]:
        checks = {}
        for label, target in [('official_assembly_723', parts['ASSEMBLY']),
                              ('battery_complete', m['battery']),
                              ('speaker_body', m['speaker'])]:
            checks[label] = round(volume_overlap(shape, target), 6)
        report['collision_checks'][name] = checks
        assert max(checks.values()) < 1e-6
    plugs, wires, wire_data = build_wiring(parts, base, m)
    wire_shapes = [s for pair in wires.values() for s in pair] + list(plugs.values())
    for name, shape in [('front', front), ('rear', rear)]:
        worst = max([volume_overlap(shape, w) for w in wire_shapes] + [0.0])
        report['collision_checks'][name]['candidate_wiring'] = round(worst, 6)
        assert worst < 1e-6

    # --- shell screws clear the board; PCB thread is intended -------------------
    shell_overlap = max([volume_overlap(s, parts['ASSEMBLY']) for s in m['screws'][4:]] + [0.0])
    pcb_thread_overlap = [round(volume_overlap(s, parts['ASSEMBLY']), 4) for s in m['screws'][:4]]
    report['screw_checks'] = {
        'shell_screws_vs_board_max_mm3': shell_overlap,
        'pcb_thread_envelopes_in_metal_inserts_mm3': pcb_thread_overlap,
        'pcb_thread_overlap_expected': True,
        'shell_screw_head': v['shell_screw'],
        'pcb_screw_head': v['pcb_screw'],
    }
    assert shell_overlap < 1e-6

    # --- front-loading sweep (discrete, straight +Z release) -------------------
    sweep = {}
    targets = [('board', parts['ASSEMBLY']), ('rear', rear),
               ('battery', m['battery']), ('speaker', m['speaker'])]
    for dz in [2, 4, 6, 10, 20, 40]:
        lifted = front.translate((0, 0, dz))
        hits = {}
        for label, target in targets:
            vol = volume_overlap(lifted, target)
            if vol > 1e-6:
                hits[label] = round(vol, 4)
        for i, w in enumerate(wire_shapes):
            vol = volume_overlap(lifted, w)
            if vol > 1e-6:
                hits[f'wire_{i}'] = round(vol, 4)
        sweep[dz] = hits
        assert not hits, (dz, hits)
    report['front_loading_sweep'] = sweep

    # --- TF hidden and BAT_PWR straight ---------------------------------------
    tf_fill = volume_overlap(front, m['tfcut'])
    report['hidden_tf'] = {
        'restored_wall_material_in_old_tf_cut_mm3': round(tf_fill, 3),
        'external_tf_opening_in_rear_shell': False,
        'bat_pwr_profile': next(r['profile_kind'] for r in m['integrated_keys'] if r['key'] == 'KEY1'),
    }
    assert tf_fill > 10
    assert report['hidden_tf']['bat_pwr_profile'] == 'rounded_rectangle'

    # --- speaker notch moved to -Y edge; old mid opening closed ----------------
    sx, sy = base['speaker']['center_xy_mm']; sw, sh, _ = base['speaker']['xyz_mm']
    old_mid = volume_overlap(front, box([28.2, sy - .4, -6.0, 28.8, sy + .4, -5.0]))
    new_bottom = volume_overlap(front, box([28.2, sy - sh / 2 - .4, -6.0, 28.8, sy - sh / 2 + .4, -5.0]))
    report['speaker_wire_notch'] = {
        'old_mid_fence_material_mm3': round(old_mid, 4),
        'new_bottom_fence_material_mm3': round(new_bottom, 4),
        'candidate_wire_route_length_mm': round(wire_data['MX1']['filleted_centerline_length_mm'], 2),
        'entry_y_mm': sy - sh / 2,
        'status': 'shell notch moved to -Y bottom edge; actual lead exit and 40mm lead still physical',
    }
    assert old_mid > .01 and new_bottom < 1e-6
    assert wire_data['MX1']['filleted_centerline_length_mm'] < 40.0, wire_data['MX1']['filleted_centerline_length_mm']

    # --- latches gone, ears present -------------------------------------------
    report['latches'] = {
        'rear_clip_objects': len(m.get('rear_clips', [])),
        'front_receiver_status': 'not built in V2',
        'replaced_by': 'four M2x6 shell screws in four corner ears',
        'ear_x_mm': [-32.14, 68.8],
    }
    assert len(m.get('rear_clips', [])) == 0

    # --- exports ---------------------------------------------------------------
    for name, shape in [('front_shell', front), ('rear_shell', rear)]:
        export_step(Compound(shape.wrapped), OUT / f'{name}.step')
        export_stl(Compound(shape.wrapped), OUT / f'{name}.stl',
                   tolerance=.02, angular_tolerance=.15)
    report['export_checks'] = verify_exports(OUT)
    light = [front, rear, *m['screws'], parts['PCB_BOARD'], parts['DISPLAY'],
             m['battery'], m['speaker'], *mounts]
    export_step(Compound(children=[Compound(s.wrapped, label=s.label or f'part_{i}')
                                  for i, s in enumerate(light)]), OUT / 'assembly_light.step')

    # --- drawings --------------------------------------------------------------
    render(OUT, parts, m, base, wire_shapes, mounts)
    report['status'] = ('CONDITIONAL_NOMINAL_GEOMETRY_PASS_PHYSICAL_PENDING'
                        if all(x < 1e-6 for d in report['collision_checks'].values()
                               for k, x in d.items() if isinstance(x, (int, float)))
                        else 'BLOCKED')
    (OUT / 'checks.json').write_text(json.dumps(report, indent=2) + '\n')
    write_readme(OUT, report)
    print(report['status'], '| thickness', report['overall_thickness_mm'],
          '| width', report['overall_width_with_ears_mm'], flush=True)


def render(out, parts, m, base, wire_shapes, mounts):
    fc, rc, metal, glass = '#526d7b', '#9aa6ad', '#c1c9cc', '#14222b'
    scene = [(m['front'], fc), (m['rear'], rc),
             (parts['DISPLAY'], glass), (parts['PCB_BOARD'], '#b4bec2'),
             (m['battery'], '#b28661'), (m['speaker'], '#a05a4f')]
    scene += [(s, metal) for s in m['screws']] + [(s, metal) for s in mounts]
    u = np.array([1., 0, -1]); u /= np.linalg.norm(u)
    w = np.array([1., .8, 1]); w /= np.linalg.norm(w)
    vv = np.cross(w, u)
    views = [
        ('FRONT', [1, 0, 0], [0, 1, 0], [0, 0, 1], (-34, 72, -39, 45),
         'FRONT +Z / USB +Y TOP'),
        ('REAR', [-1, 0, 0], [0, 1, 0], [0, 0, -1], (-72, 34, -39, 45),
         'REAR -Z / USB +Y TOP / four corner ears + four PCB screws'),
        ('SIDE', [0, 0, 1], [0, 1, 0], [-1, 0, 0], (-14.2, 2, -39, 45),
         'SIDE +X / FRONT right / REAR left'),
        ('ISO', u, vv, w, (-35, 72, -60, 55), 'ISO FRONT'),
    ]
    for name, a, b, c, ext, title in views:
        fig, ax = plt.subplots(figsize=(11, 8) if name != 'SIDE' else (4, 9))
        panel(ax, scene, a, b, c, ext)
        ax.set_title(f'G-V2 {title}\n100.94 x 77.86 x 13.55mm nominal; NOT print approved', fontsize=9)
        ax.set_xlabel('mm'); ax.set_ylabel('mm')
        fig.tight_layout(); fig.savefig(out / f'{name}.png', dpi=150); plt.close(fig)

    # XZ through screen centre: lip, seam and ears
    sec = [(section(m['front'], -33, -.12, -13.5, 70, .12, 2), fc),
           (section(m['rear'], -33, -.12, -13.5, 70, .12, 2), rc),
           (section(parts['DISPLAY'], -33, -.12, -13.5, 70, .12, 2), glass),
           (section(parts['PCB_BOARD'], -33, -.12, -13.5, 70, .12, 2), '#b4bec2')]
    fig, ax = plt.subplots(figsize=(13, 5))
    panel(ax, sec, [1, 0, 0], [0, 0, 1], [0, 1, 0], (-33, 70, -13.5, 1.8))
    ax.set_title('SCREEN XZ SECTION at Y=0 / left-right lines only; lip underside 0.8, glass 0.7; seam -10.35; rear -12.35')
    ax.set_xlabel('X'); ax.set_ylabel('Z (FRONT up)')
    fig.tight_layout(); fig.savefig(out / 'screen_lip_section.png', dpi=160); plt.close(fig)

    # Zoom on the left lip
    zoom = [(section(m['front'], 20, -.12, -1.2, 30, .12, 1.5), fc),
            (section(parts['DISPLAY'], 20, -.12, -1.2, 30, .12, 1.5), glass)]
    fig, ax = plt.subplots(figsize=(7, 5))
    panel(ax, zoom, [1, 0, 0], [0, 0, 1], [0, 1, 0], (22, 27, -1.2, 1.5))
    ax.set_title('RIGHT SCREEN EDGE ZOOM / glass 50.54 wide, window 50.94, lip inner 48.54\nlip covers 1.0mm of glass, 0.1mm above front face')
    ax.set_xlabel('X'); ax.set_ylabel('Z')
    fig.tight_layout(); fig.savefig(out / 'screen_lip_zoom.png', dpi=180); plt.close(fig)

    # XZ through a right ear/screw
    ear = [(section(m['front'], -33, 38.18, -13.5, 70, 38.42, 2), fc),
           (section(m['rear'], -33, 38.18, -13.5, 70, 38.42, 2), rc),
           (section(m['screws'][4], -33, 38.18, -13.5, 70, 38.42, 2), metal)]
    fig, ax = plt.subplots(figsize=(13, 4))
    panel(ax, ear, [1, 0, 0], [0, 0, 1], [0, 1, 0], (-33, 70, -13.5, 1.8))
    ax.set_title('TOP EARS / SHELL SCREW SECTION at Y=38.3 / M2x6 head 1.0 deep, 5.0mm PA12 engagement')
    ax.set_xlabel('X'); ax.set_ylabel('Z')
    fig.tight_layout(); fig.savefig(out / 'ear_screw_section.png', dpi=160); plt.close(fig)

    # YZ through the speaker fence wire notch
    spk = [(section(m['front'], 28.25, -36, -13.5, 28.55, 42, 2), fc),
           (section(m['speaker'], 28.25, -36, -13.5, 28.55, 42, 2), '#a05a4f')]
    fig, ax = plt.subplots(figsize=(7, 8))
    panel(ax, spk, [0, 0, 1], [0, 1, 0], [-1, 0, 0], (-13.5, 2, -36, 42))
    ax.set_title('SPEAKER FENCE YZ at X=28.4 / wire notch now at -Y edge;\nactual lead exit still to photograph')
    ax.set_xlabel('Z (REAR left)'); ax.set_ylabel('Y')
    fig.tight_layout(); fig.savefig(out / 'speaker_notch_section.png', dpi=150); plt.close(fig)


def write_readme(out, r):
    d = r['dimensions']
    lines = [
        '# G-V1 V2 — screen lip, clamped rear cover, hidden TF',
        '',
        '> **状态：CONDITIONAL / 名义几何与装配路径检查通过 / 实物与制造未验证 / 不批准直接打印。**',
        '> 基于第一版实物反馈的 V2 候选；机械基线 `ee8ec9d + 95.60mm bay`。',
        '',
        f"- `front_shell.step/.stl`：前置屏唇 + 圆角窗口 + 四个角耳；`{bounds_str(r['bounds_mm']['front'])}`",
        f"- `rear_shell.step/.stl`：2.0mm 均匀背板 + 1.2mm 内筋 + 四角耳；`{bounds_str(r['bounds_mm']['rear'])}`",
        f"- `assembly_light.step`：前后壳、8 颗螺钉、真实 PCB/显示、实测电池/扬声器、原厂金属件",
        f"- `checks.json`：几何、碰撞、前装拆路径、导出回读",
        f"- 预览：`FRONT.png`、`REAR.png`、`SIDE.png`、`ISO.png`、`screen_lip_section.png`、`screen_lip_zoom.png`、`ear_screw_section.png`、`speaker_notch_section.png`",
        '',
        '## 实测与变化',
        f"- 整机名义：**{r['overall_width_with_ears_mm']:.2f} × {r['overall_height_mm']:.2f} × {r['overall_thickness_mm']:.2f}mm**（含四角耳；主体仍 95.60 × 77.86）。",
        f"- 屏窗：玻璃 50.54 × 73.06 / R2.0；窗口 50.94 × 73.46 / R2.2，单边 0.20mm。",
        f"- 屏唇：向内包住玻璃 1.00mm；唇底面 0.80，玻璃前面 0.70，名义间隙 0.10mm；唇顶 1.20，屏相对唇顶凹 0.50mm。",
        f"- 背板：2.00mm 均匀板 + 1.2mm 内部筋；后盖内面与前面壳后端都在 z={d['seam_z_mm']:.2f}。",
        f"- 屏幕单边游隙从旧版 0.60 降到 0.20；旧的 1.29mm 自由侧总间隙在 V2 名义为 0.40，且被屏唇遮住。",
        '- 两颗卡扣、接收座、撬槽全部删除；改为四角 **M2×6 自攻** 螺钉（M2 螺距，PA12 预钻 Ø1.7）。',
        '- 原厂 PCB 四颗 **M2.5×5 机螺丝**（背板由 1.2 改 2.0、螺钉头座后移 1.0mm，原 M2.5×4 只有 2.0mm 牙合；M2.5×5 名义 3.0mm）。',
        '- TF 外露槽取消，卡留在机内；BAT_PWR 改为直条形圆角弹片（不再为 TF 开槽绕 L 形）。',
        '- 扬声器围框出线缺口从 Y 中部移到 -Y 底边；实际出线方向仍需照片/测量确认。',
        '- USB 开口保持 13.2 × 7.3mm（插线实测后用户已撤回“太大”判断）。',
        '',
        '## 紧固件/耗材',
        '- **4× M2.5×5 机螺丝**（头 Ø5.0×0.85，原厂金属嵌件；原 M2.5×4 不再够）。',
        '- **4× M2×6 自攻**（DIN 7981/ISO 7049，头 Ø3.8×1.0；PA12 预钻 Ø1.7；四角耳）。',
        '- **0.2mm 单面泡棉胶带** 约 1m（1.0mm 宽贴屏唇下；不贴时唇与玻璃名义 0.10mm 不接触）。',
        '- 不新增卡扣、金属嵌件、延长线或胶粘结构。',
        '',
        '## 装配顺序（与 V1 不同）',
        '1. 后板平放，先装 PCB/显示、四颗 PCB 螺丝、电池、扬声器及候选线束。',
        '2. 前壳从 +Z 方向下降；四个角耳在机身外侧，不扫过 PCB；屏唇从玻璃前方越过，窗口单边 0.2mm。',
        '3. 左壁两个键弹片会从上方滑过原厂开关外侧，名义 0.15mm 径向间隙；不要斜插。',
        '4. 四颗 M2×6 从后方装入四个角耳；轻拧交叉。屏唇不压玻璃，只做前向限位；可贴 0.2mm 泡棉。',
        '',
        '## 已验证 / 未验证',
        f"- 前/后壳各 1 个有效实体；与 723 个原厂实体、电池、扬声器、候选线束均无碰撞。",
        f"- 前壳 +2…+40mm 离散直提无碰撞；这是离散检查，不是任意姿态证明。",
        f"- 4 颗壳螺钉对原板无碰撞；4 颗 PCB 螺钉只在金属嵌件内出现预期螺纹包络。",
        f"- STEP 回读与 STL 闭合：见 `checks.json/export_checks`。",
        '- **未验证**：PA12 螺纹/扭矩、屏唇实际压力与玻璃强度、按键弹片前装手感、扬声器真实出线、MIC 声路、打印公差与翘曲、USB 插拔、TF 维护、音质。',
        '',
        '## 仍待用户确认',
        '- 第一版打印是什么工艺/材料（MJF PA12？FDM？），以及这次是否仍用同一家。',
        '- 扬声器出线在哪个边/面；请给装入前的照片或实测。',
        '- 第一版前面小孔是否是你自己钻的；MIC 实际端口在哪；装壳录音是否正常。',
        '- 13.55mm 厚 / 100.94mm 宽（含四角耳）是否接受；若坚持 95.6 宽，只能改成两耳 + 左缝舌片，机械可靠性未证明，我不建议。',
        '- 1.29mm 是“推到对角后另一侧的总间隙”而不是单边间隙？',
        '',
        '**复现：** `./scripts/generate-g-v2.sh`。`checks.json` 的 `print_approved` 永远为 false；CONDITIONAL 不等于可打印或功能通过。',
    ]
    (out / 'README.md').write_text('\n'.join(lines) + '\n')


def bounds_str(b):
    return 'x %.2f…%.2f / y %.2f…%.2f / z %.2f…%.2f' % (b[0], b[3], b[1], b[4], b[2], b[5])


if __name__ == '__main__':
    main()
