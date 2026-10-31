"""V4 seam-drop T-slot captive sliders: inserted from -Z seam, locked by rear shell.

0 side screws, 0 external retainer plate. The front shell's left wall owns both
the 1.50mm outer retaining wall and the 1.50mm inner stop wall; the rear shell's
integral keeper block seals the -Z slot opening when the rear cover closes.
"""
from model import box_between as box
from reference import bounds


def table(v):
    k = v['printed_keys']
    ox = v['outer_x_min_mm']
    seat_outer_x = ox + k['outer_wall_thickness_mm']
    seat_inner_x = seat_outer_x + k['flange_thickness_mm'] + k['stroke_mm']
    inner_x = k['wall_inner_x_mm']
    c = k['radial_clearance_mm']
    hy, hz = k['head_yz_mm']
    fy, fz = k['flange_yz_mm']
    sy, sz = k['stem_yz_mm']
    ty, tz = k['tip_yz_mm']
    zc = k['z_center']
    seam = v['seam_z_mm']
    return dict(
        outer_x=ox,
        seat_outer_x=seat_outer_x,
        seat_x=seat_inner_x,
        inner_x=inner_x,
        center_z=zc,
        seam_z=seam,
        clearance=c,
        head_y=hy, head_z=hz,
        flange_y=fy, flange_z=fz,
        stem_y=sy, stem_z=sz,
        tip_y=ty, tip_z=tz,
        aperture_y=hy + 2 * c, aperture_z_top=zc + hz / 2 + c,
        pocket_y=fy + 2 * c, pocket_z_top=zc + fz / 2 + c,
        guide_y=sy + 2 * c, guide_z_top=zc + sz / 2 + c,
        keeper_outer_z_top=zc - hz / 2 - c,
        keeper_flange_z_top=zc - fz / 2 - c,
        exterior_x=ox,
    )


def cutters(t, y):
    c_outer = box([t['outer_x'] - 0.05, y - t['aperture_y'] / 2, t['seam_z'] - 0.05,
                   t['seat_outer_x'] + 0.01, y + t['aperture_y'] / 2, t['aperture_z_top']])
    c_flange = box([t['seat_outer_x'] - 0.01, y - t['pocket_y'] / 2, t['seam_z'] - 0.05,
                    t['seat_x'] + 0.01, y + t['pocket_y'] / 2, t['pocket_z_top']])
    c_guide = box([t['seat_x'] - 0.01, y - t['guide_y'] / 2, t['seam_z'] - 0.05,
                   t['inner_x'] + 0.05, y + t['guide_y'] / 2, t['guide_z_top']])
    return c_outer, c_flange, c_guide


def rear_keeper(t, y):
    k_outer = box([t['outer_x'], y - t['head_y'] / 2, t['seam_z'] - 0.01,
                   t['seat_outer_x'] - 0.15, y + t['head_y'] / 2, t['keeper_outer_z_top']])
    k_flange = box([t['seat_outer_x'] - 0.16, y - t['head_y'] / 2, t['seam_z'] - 0.01,
                    t['seat_x'] - 0.20, y + t['head_y'] / 2, t['keeper_flange_z_top']])
    return k_outer + k_flange


def button(v, y, switch_x, delta=0.0):
    """Changing flange and tip together preserves the maximum inward tip plane."""
    k = v['printed_keys']
    t = table(v)
    zc = t['center_z']
    face_x = t['outer_x'] - k['head_projection_mm']
    flange_end = t['seat_outer_x'] + k['flange_thickness_mm'] + delta
    shoulder_x = k['stem_end_x_mm'] + delta
    tip_x = switch_x - k['rest_gap_mm'] + delta
    b_head = box([face_x, y - t['head_y'] / 2, zc - t['head_z'] / 2,
                  t['seat_outer_x'] + 0.01, y + t['head_y'] / 2, zc + t['head_z'] / 2])
    b_flange = box([t['seat_outer_x'], y - t['flange_y'] / 2, zc - t['flange_z'] / 2,
                    flange_end, y + t['flange_y'] / 2, zc + t['flange_z'] / 2])
    b_stem = box([flange_end - 0.01, y - t['stem_y'] / 2, zc - t['stem_z'] / 2,
                  shoulder_x, y + t['stem_y'] / 2, zc + t['stem_z'] / 2])
    b_tip = box([shoulder_x - 0.01, y - t['tip_y'] / 2, zc - t['tip_z'] / 2,
                 tip_x, y + t['tip_y'] / 2, zc + t['tip_z'] / 2])
    return b_head + b_flange + b_stem + b_tip


def build_buttons(v, parts):
    k = v['printed_keys']
    items = {}
    exports = {}
    for i, y in enumerate(k['y_mm'], 1):
        name = f'KEY{i}'
        sx = bounds(parts[name])[0]
        for label, delta in k['variants_mm'].items():
            shape = button(v, y, sx, delta)
            export_name = f'button_{"power" if i == 1 else "boot"}_{label}'
            shape.label = export_name.upper()
            exports[export_name] = shape
            if label == 'nominal':
                items[name] = shape
    return items, exports
