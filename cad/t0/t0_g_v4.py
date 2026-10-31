"""G-V1 V4-CLEAN: 6-screw left-hook enclosure, rear-locked T-slot buttons, 0.8mm screen lip, 2.0mm ribbed rear."""
import json
from pathlib import Path
from build123d import (
    Align, Axis, Cylinder, GeomType, Plane, Polygon, RectangleRounded, extrude,
)

from model import box_between as box
from reference import bounds
from p1_checks import intersection
from t0_model import cyl, rr
from t0_g_v1_integrated_keys import foundation
from t0_g_v2_keys import build_keys
from g_v4_printed_keys import table as key_table, cutters as key_cutters, rear_keeper, build_buttons


def read(root, name):
    return json.loads((Path(root) / 'cad/t0' / name).read_text())


def front_glass_face(display):
    """Largest +Z planar face at the front-most display plane."""
    zmax = bounds(display)[5]
    faces = [f for f in display.faces()
             if f.geom_type == GeomType.PLANE and f.normal_at().Z > .99
             and abs(bounds(f)[5] - zmax) < 1e-3]
    assert faces
    face = max(faces, key=lambda f: f.area)
    radii = [e.radius for e in face.edges() if e.geom_type == GeomType.CIRCLE]
    assert radii, 'Display front face has no modelled corner radius'
    return face, min(radii)


def left_hook_groove(lh, y0, y1):
    gx = lh['groove_peak_x_mm']
    z0, z1, z2, z3 = lh['groove_z_mm']
    ix = lh['wall_x_mm'][0] - 0.14  # -28.66
    pts = [(ix + 0.05, z0), (gx, z1), (gx, z2), (ix + 0.05, z3)]
    return extrude(Plane.XZ * Polygon(*pts, align=None), amount=(y1 - y0) + 0.4, dir=(0, 1, 0)).translate((0, y0 - 0.2, 0))


def left_hook_rib(lh, seam, y0, y1):
    wx0, wx1 = lh['wall_x_mm']
    rx = lh['rib_peak_x_mm']
    z0, z1, z2, z3 = lh['rib_z_mm']
    wall = box([wx0, y0, seam - 0.01, wx1, y1, lh['wall_top_z_mm']])
    pts = [(wx0 + 0.02, z0), (rx, z1), (rx, z2), (wx0 + 0.02, z3)]
    rib = extrude(Plane.XZ * Polygon(*pts, align=None), amount=y1 - y0, dir=(0, 1, 0)).translate((0, y0, 0))
    return wall + rib


def build(parts, mounts, base, kp, p, q, v):
    m, _ = foundation(parts, mounts, base, kp, p, q)
    ox = base['outer_x_min_mm']; ex = ox + base['width_mm']
    oy, ey = base['outer_y_mm']; wall = base['wall_mm']
    ix, jx = ox + wall, ex - wall
    iy, jy = oy + wall, ey - wall
    bottom = m['dimensions']['rear_bottom_z_mm']
    seam = v['seam_z_mm']; B = v['rear_outer_z_mm']

    # 1. Hide the TF card: restore the left wall material removed by the old slot.
    tb = bounds(parts['TF']); ty = (tb[1] + tb[4]) / 2; tz = (tb[2] + tb[5]) / 2
    front = m['front'] + box([ox, ty - 6.2, tz - .8, ix, ty + 6.2, tz + .8])

    # 2. V4-CLEAN: Left button housing slab + two -Z drop-in T-slots + RESET pinhole.
    if v.get('v4'):
        ls = v['left_slab']
        front = front + box([ls['x_mm'][0], ls['y_mm'][0], ls['z_mm'][0],
                             ls['x_mm'][1], ls['y_mm'][1], ls['z_mm'][1]])
        sk = v['printed_keys']; kt = key_table(v)
        for yc in sk['y_mm']:
            for cutter in key_cutters(kt, yc):
                front = front - cutter
        rp = v['reset_pinhole']
        front = front - Cylinder(rp['diameter_mm'] / 2, rp['x_mm'][1] - rp['x_mm'][0],
                                 align=(Align.CENTER, Align.CENTER, Align.MIN)).rotate(
                                     Axis.Y, 90).translate((rp['x_mm'][0], rp['y_mm'], rp['z_mm']))
    else:
        m['front'] = front
        m = build_keys(parts, m, base, q)
        front = m['front']

    # 3. Tight rounded window (0.20mm/side), 0.80mm screen lip (0.10mm gap) and inner guide rib.
    glass, gr = front_glass_face(parts['DISPLAY'])
    gb = bounds(glass); gx = (gb[0] + gb[3]) / 2; gy = (gb[1] + gb[4]) / 2
    gw = gb[3] - gb[0]; gh = gb[4] - gb[1]
    c = v['screen_clearance_mm']
    ww, wh, wr = gw + 2 * c, gh + 2 * c, gr + c
    plate = box([gx - ww / 2 - 1.0, gy - wh / 2 - 1.0, -.6,
                 gx + ww / 2 + 1.0, gy + wh / 2 + 1.0, .7])
    front = front + plate
    window = extrude(Plane.XY.offset(-1.0) * RectangleRounded(ww, wh, wr),
                     amount=2.5).translate((gx, gy, 0))
    front = front - window
    lip_inner_w = gw - 2 * v['screen_lip_overlap_mm']
    lip_inner_h = gh - 2 * v['screen_lip_overlap_mm']
    lip_inner_r = max(gr - v['screen_lip_overlap_mm'], .5)
    lip_inner = RectangleRounded(lip_inner_w, lip_inner_h, lip_inner_r)
    zg = gb[5]
    lip_bottom = zg + v['screen_lip_bottom_gap_mm']
    lip_top = zg + v['screen_lip_base_height_mm']
    over = (extrude(Plane.XY.offset(lip_bottom) * RectangleRounded(ww, wh, wr),
                    amount=lip_top - lip_bottom).translate((gx, gy, 0))
            - extrude(Plane.XY.offset(lip_bottom) * lip_inner,
                      amount=lip_top - lip_bottom + .1).translate((gx, gy, 0)))
    base_w = ww + 2 * v['screen_lip_base_mm']
    base_h = wh + 2 * v['screen_lip_base_mm']
    base_r = wr + v['screen_lip_base_mm']
    lip_full = extrude(Plane.XY.offset(zg - .05) * RectangleRounded(ww, wh, wr),
                       amount=lip_top - zg + .2).translate((gx, gy, 0))
    lip_base = (extrude(Plane.XY.offset(zg) * RectangleRounded(base_w, base_h, base_r),
                        amount=lip_top - zg).translate((gx, gy, 0))
                - lip_full)
    front = front + over + lip_base
    rib = v['screen_guide_rib_mm']; z0, z1 = v['screen_guide_rib_z_mm']
    rib_outer = RectangleRounded(ww + 2 * rib, wh + 2 * rib, wr + rib)
    guide = (extrude(Plane.XY.offset(z0) * rib_outer, amount=z1 - z0).translate((gx, gy, 0))
             - extrude(Plane.XY.offset(z0) * RectangleRounded(ww, wh, wr),
                       amount=z1 - z0 + .1).translate((gx, gy, 0)))
    front = front + guide

    # 3b. Restored V1 T1 MIC hole at (27.3, 1.395).
    mp = v.get('mic_port')
    if mp:
        front = front - cyl(mp['diameter_mm'] / 2, mp['z_mm'][0], mp['z_mm'][1],
                            mp['xy_mm'][0], mp['xy_mm'][1])

    # 4. Cut the front tub at the seam, keep the USB mouth bridge, add 2 right screw posts & left hook grooves.
    for stop in m.get('stops', []):
        front = front - stop
    original = front
    front = original - box([ox - 1, oy - 1, bottom - 1, ex + 1, ey + 1, seam])
    ub = bounds(m['usbcut'])
    bridge = intersection(original, box([ub[0] - 1.2, ey - wall - .3, bottom,
                                       ub[3] + 1.2, ey + .2, -3.5]))
    front = front + bridge

    # Cut T-slots cleanly to the seam
    sk = v['printed_keys']; kt = key_table(v)
    for yc in sk['y_mm']:
        for cutter in key_cutters(kt, yc):
            front = front - cutter

    # Cut left-wall 45-degree locking grooves (monolithic snap/hinge interlock)
    lh = v.get('left_hook')
    if lh:
        for y0, y1 in lh['y_spans_mm']:
            front = front - left_hook_groove(lh, y0, y1)

    # Two right-corner screw bosses only
    screw_axes = v['shell_screw']['axes_xy_mm']
    boss = v['shell_screw'].get('boss_diameter_mm')
    if boss:
        for x, y in screw_axes:
            front = front + cyl(boss / 2, seam, .7, x, y)
    for x, y in screw_axes:
        front = front - cyl(v['shell_screw']['pilot_diameter_mm'] / 2,
                            seam - .05, v['shell_screw']['pilot_end_z_mm'], x, y)

    # 5. Uniform 2.0mm ribbed rear plate on the exact seam face.
    rear = rr(ex - ox, ey - oy, base['corner_radius_mm'], B, seam, (ox + ex) / 2, (oy + ey) / 2)
    gc = .15; rt = 1.6
    reg = (rr(jx - ix - 2 * gc, jy - iy - 2 * gc, 1, seam - .01, seam + rt, (ix + jx) / 2, (iy + jy) / 2)
           - rr(jx - ix - 2 * gc - 2 * rt, jy - iy - 2 * gc - 2 * rt, .5, seam - .1,
                seam + rt + .1, (ix + jx) / 2, (iy + jy) / 2))
    # Clear register ring along the left button slab
    ls = v['left_slab']
    reg = reg - box([ox - 1, ls['y_mm'][0] - 0.25, seam - 0.1, ls['x_mm'][1] + 0.25, ls['y_mm'][1] + 0.25, seam + rt + 0.2])
    rear = rear + reg

    # Add left-side 45-degree locking hook walls/ribs on rear shell
    if lh:
        for y0, y1 in lh['y_spans_mm']:
            rear = rear + left_hook_rib(lh, seam, y0, y1)

    # Add rear T-slot keeper blocks that lock the buttons in Z when rear cover closes
    for yc in sk['y_mm']:
        rear = rear + rear_keeper(kt, yc)

    b = base['battery']; bw, bh, bt = b['xyz_mm']; bx, by = b['center_xy_mm']
    bs = v['battery_stack']; bz = seam + bs['adhesive_mm']
    m['battery'] = box([bx - bw / 2, by - bh / 2, bz, bx + bw / 2, by + bh / 2, bz + bt])
    m['battery'].label = 'BATTERY_COMPLETE_V4'
    m['adhesive'] = box([bx - bw / 2, by - bh / 2, seam, bx + bw / 2, by + bh / 2, bz])
    m['adhesive'].label = 'BATTERY_ADHESIVE_0_2'
    c_tray = bs['tray_clearance_mm']; tw = bs['tray_wall_mm']
    tray = (rr(bw + 2 * c_tray + 2 * tw, bh + 2 * c_tray + 2 * tw, 1.5, seam - .01, seam + 1.0, bx, by)
            - rr(bw + 2 * c_tray, bh + 2 * c_tray, .6, seam - .1, seam + 1.1, bx, by))
    tray = tray - box([bx + bw / 2, 4, seam - .1, bx + bw / 2 + 4, 14, seam + 2])
    tray = intersection(tray, box([ix + gc, iy + gc, seam - .1, jx - gc, jy - gc, seam + 2]))
    tray = tray - box([59.0, 34.0, seam - .1, ex + 1, ey + 1, seam + 2])
    m['battery_tray'] = tray
    rear = rear + tray
    s = base['speaker']; sx, sy = s['center_xy_mm']; sw, sh, _ = s['xyz_mm']
    dampback = bounds(m['damping'])[2]
    for x in [sx - sw / 2 + 2, sx + sw / 2 - 2]:
        for y in [sy - sh / 2 + 2, sy + sh / 2 - 2]:
            rear = rear + box([x - 1.5, y - 1.5, seam - .01, x + 1.5, y + 1.5, dampback])
    # Internal ribs in the free left bay, well behind the PCB rear face.
    rh = v['rear_ribs']['height_mm']; rw = v['rear_ribs']['width_mm']
    for x in v['rear_ribs']['x_mm']:
        rear = rear + box([x - rw / 2, iy + .7, seam, x + rw / 2, jy - .7, seam + rh])
    for y in v['rear_ribs']['y_mm']:
        rear = rear + box([max(ix + .7, ls['x_mm'][1] + .5), y - rw / 2, seam, 22, y + rw / 2, seam + rh])
    # Four PCB screws through the original metal inserts.
    pc = v['pcb_screw']; head_depth = pc['head_pocket_depth_mm']
    screw_rows = []
    for i, mount in enumerate(sorted(mounts, key=lambda st: (st.center().X, st.center().Y))):
        f_cyl = next(f for f in mount.faces() if f.geom_type == GeomType.CYLINDER
                     and abs(f.axis_of_rotation.direction.Z) > .99)
        x, y, _ = f_cyl.axis_of_rotation.position; mb = bounds(mount)[2]
        rear = rear + cyl(3.5, seam - .01, mb, x, y)
        rear = rear - cyl(pc['shaft_bore_diameter_mm'] / 2, B - .1, mb + .1, x, y)
        rear = rear - cyl(pc['head_pocket_diameter_mm'] / 2, B - .1, B + head_depth, x, y)
        screw_rows.append(dict(axis_xy_mm=[x, y], metalback_z_mm=mb,
                               head_seat_z_mm=B + head_depth,
                               tip_z_mm=B + head_depth + pc['shaft_length_mm'],
                               kind='PCB_M2_5x5_machine'))
    # Two right-side shell screws with head pockets in the rear plate.
    sc = v['shell_screw']
    for x, y in screw_axes:
        rear = rear - cyl(sc['thread_diameter_mm'] / 2 + .15, B - .1, seam + .1, x, y)
        rear = rear - cyl(sc['head_pocket_diameter_mm'] / 2, B - .1, B + sc['head_pocket_depth_mm'], x, y)
        if sc.get('boss_diameter_mm'):
            rear = rear - cyl(sc['boss_diameter_mm'] / 2 + .3, seam, seam + rt + .1, x, y)

    # USB mouth: panel notch gives the plug its lower clearance and keeps the bridge.
    rear = rear - box([ub[0] - 1.2, ey - wall - .3, B - .5, ub[3] + 1.2, ey + .2, -8.15])
    rear = rear - m['usbcut']

    # 6. Screw envelopes (4 PCB M2.5 screws + 2 right-side M2 shell screws = 6 screws total).
    screws = []
    for row in screw_rows:
        x, y = row['axis_xy_mm']; hs = row['head_seat_z_mm']
        screws.append(cyl(pc['head_diameter_mm'] / 2, hs - pc['head_height_mm'], hs, x, y)
                      + cyl(pc['thread_diameter_mm'] / 2, hs, row['tip_z_mm'], x, y))
    for x, y in screw_axes:
        length = sc['shaft_length_mm']
        hs = B + sc['head_pocket_depth_mm']
        screws.append(cyl(sc['head_diameter_mm'] / 2, hs - sc['head_height_mm'], hs, x, y)
                      + cyl(sc['thread_diameter_mm'] / 2, hs, hs + length, x, y))

    assert abs(lip_top - v['screen_lip_top_z_mm']) < 1e-6
    assert abs(lip_top - lip_bottom - v['screen_lip_overhang_height_mm']) < 1e-6
    assert abs(seam - B - v['rear_panel_mm']) < 1e-6
    front.label = 'FRONT_V4_CLEAN_HOOK_AND_TSLOT'
    rear.label = 'REAR_V4_CLEAN_2MM_RIBBED'
    buttons, button_exports = build_buttons(v, parts)
    m.update(
        buttons=buttons,
        button_exports=button_exports,
        front=front,
        rear=rear,
        key_bezel=None,
        retainer_screws=[],
        screws=screws,
        screw_rows=screw_rows,
        v4_parameters=v,
        mic_port=v.get('mic_port'),
        screen_geometry=dict(
            glass_bounds_mm=gb, glass_radius_mm=gr,
            window_whr_mm=[ww, wh, wr], lip_inner_whr_mm=[lip_inner_w, lip_inner_h, lip_inner_r],
            lip_base_whr_mm=[base_w, base_h, base_r], glass_front_z_mm=gb[5],
            lip_top_z_mm=lip_top, lip_bottom_z_mm=lip_bottom
        ),
        dimensions=dict(
            front_top_z_mm=lip_top,
            front_face_z_mm=m['dimensions']['front_z_mm'],
            seam_z_mm=seam,
            rear_outer_z_mm=B,
            total_thickness_mm=lip_top - B,
            body_xy_mm=[ex - ox, ey - oy]
        )
    )
    return m
