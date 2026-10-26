"""G-V1 V2: screen-capturing bezel, clamped 2.0mm rear cover, no snap latches.

Built from the frozen G-V1 foundation and key helper. The V2-specific changes are
local and explicit: rounded tight window, overhanging front lip, hidden TF card,
straight BAT_PWR leaf, four shell screws into front posts, and a uniform 2.0mm
ribbed rear plate. Nominal geometry only; see t0-g-v2.json for open risks.
"""
import json
from pathlib import Path
from build123d import (
    Align, Axis, Cylinder, GeomType, Plane, RectangleRounded, extrude,
)

from model import box_between as box
from reference import bounds
from p1_checks import intersection
from t0_model import cyl, rr
from t0_g_v1_integrated_keys import foundation
from t0_g_v2_keys import build_keys


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


def pad_post(front, x, y, z0, z1, half_y, x0, x1):
    """A rectangular rear pad attached to the left inner wall."""
    return front + box([x0, y - half_y, z0, x1, y + half_y, z1])


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
    front = m['front'] + box([ox - .1, ty - 6.2, tz - .8, ix, ty + 6.2, tz + .8])

    # 2. V4-RECT: no integrated PA12 leaves. Add the left key slab and the
    # two 0127 silicone pockets; RESET remains a Ø2.2 pinhole.
    if v.get('v4'):
        ls = v['left_slab']
        front = front + box([ls['x_mm'][0], ls['y_mm'][0], ls['z_mm'][0],
                             ls['x_mm'][1], ls['y_mm'][1], ls['z_mm'][1]])
        sk = v['silicone_keys']; zc = sk['z_center']
        for yc in sk['y_mm']:
            # counterbore: 9.4 Y x 7.4 Z x 1.3 X deep
            front = front - box([ox - .1, yc - sk['counterbore_y_mm'] / 2,
                                 zc - sk['counterbore_z_mm'] / 2,
                                 ox + sk['depth_mm'], yc + sk['counterbore_y_mm'] / 2,
                                 zc + sk['counterbore_z_mm'] / 2])
            # through: 9.2 Y x 6.0 Z, from the counterbore bottom to the inner wall
            front = front - box([ox + sk['depth_mm'], yc - sk['through_y_mm'] / 2,
                                 zc - sk['through_z_mm'] / 2,
                                 -25.87, yc + sk['through_y_mm'] / 2,
                                 zc + sk['through_z_mm'] / 2])
        rp = v['reset_pinhole']
        front = front - Cylinder(rp['diameter_mm'] / 2, rp['x_mm'][1] - rp['x_mm'][0],
                                 align=(Align.CENTER, Align.CENTER, Align.MIN)).rotate(
                                     Axis.Y, 90).translate((rp['x_mm'][0], rp['y_mm'], rp['z_mm']))
    else:
        m['front'] = front
        m = build_keys(parts, m, base, q)
        front = m['front']

    # 2b. Speaker lead now exits at the -Y edge; move the fence notch from mid-Y.
    sp = base['speaker']; sx, sy = sp['center_xy_mm']; sw, sh, st = sp['xyz_mm']
    sf = m['dimensions']['glass_z_mm'] - base['bay_front_panel_mm'] - sp['foam_mm']
    wall_half = sp['tray_wall_mm'] / 2
    # Fill the old mid notch through BOTH the fence wall and the front face.
    front = front + box([sx - sw / 2 - 2, sy - 1.3, -.6,
                         sx - sw / 2 + .1, sy + 1.3,
                         m['dimensions']['front_z_mm']])
    front = front + box([sx - sw / 2 - 1, sy - 1.3, sf - st - 1,
                         sx - sw / 2, sy + 1.3, -.6])
    # New +Y notch is a slot in the fence wall only; the front face stays closed.
    front = front - box([sx - sw / 2 - 2, sy + sh / 2 - 1.3, sf - st - 1,
                         sx - sw / 2 + .1, sy + sh / 2 + 1.3, -.6])

    # 3. Tight rounded window, screen-capturing lip and inner guide rib.
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

    # 3b. Preserve the V1 printed front hole that records correctly; the V1 CAD
    # had only a probe. Location is the V1 candidate; confirm against the photo.
    mp = v.get('mic_port')
    if mp:
        front = front - cyl(mp['diameter_mm'] / 2, mp['z_mm'][0], mp['z_mm'][1],
                            mp['xy_mm'][0], mp['xy_mm'][1])

    # 4. Cut the front tub at the seam, keep the USB mouth bridge, add screw posts.
    # Remove the old G shoulder pads; the clamped seam replaces them.
    for stop in m.get('stops', []):
        front = front - stop
    original = front
    front = original - box([ox - 1, oy - 1, bottom - 1, ex + 1, ey + 1, seam])
    ub = bounds(m['usbcut'])
    bridge = intersection(original, box([ub[0] - 1.2, ey - wall - .3, bottom,
                                       ub[3] + 1.2, ey + .2, -3.5]))
    front = front + bridge
    screw_axes = v['shell_screw']['axes_xy_mm']
    if not v.get('v4'):
        ears = v['shell_screw']['ears']; inset = ears['inset_mm']; over = ears['overhang_mm']
        eh = ears['half_width_mm']; er = ears['corner_radius_mm']
        def ear_span(x):
            return (ox - over, ox + inset) if x < 0 else (ex - inset, ex + over)
        for x, y in screw_axes:
            ea, eb = ear_span(x)
            front = front + rr(eb - ea, 2 * eh, er, seam, .7, (ea + eb) / 2, y)
    boss = v['shell_screw'].get('boss_diameter_mm')
    if boss:
        for x, y in screw_axes:
            front = front + cyl(boss / 2, seam, .7, x, y)
    lf = v.get('left_flange')
    if lf:
        for y in lf['y_mm']:
            front = front + box([ix, y - lf['half_y_mm'], seam,
                                 ix + lf['width_mm'], y + lf['half_y_mm'], seam + lf['height_mm']])
    for x, y in screw_axes:
        front = front - cyl(v['shell_screw']['pilot_diameter_mm'] / 2,
                            seam - .05, B + 1.0 + v['shell_screw']['shaft_length_mm'], x, y)

    # 5. Uniform ribbed rear plate on the exact seam face.
    rear = rr(ex - ox, ey - oy, base['corner_radius_mm'], B, seam, (ox + ex) / 2, (oy + ey) / 2)
    gc = .15; rt = 1.0
    reg = (rr(jx - ix - 2 * gc, jy - iy - 2 * gc, 1, seam - .01, seam + rt, (ix + jx) / 2, (iy + jy) / 2)
           - rr(jx - ix - 2 * gc - 2 * rt, jy - iy - 2 * gc - 2 * rt, .5, seam - .1,
                seam + rt + .1, (ix + jx) / 2, (iy + jy) / 2))
    rear = rear + reg
    b = base['battery']; bw, bh, _ = b['xyz_mm']; bx, by = b['center_xy_mm']
    c = b['tray_clearance_mm']; tw = b['tray_wall_mm']
    tray = (rr(bw + 2 * c + 2 * tw, bh + 2 * c + 2 * tw, 1.5, seam - .01, seam + 1.0, bx, by)
            - rr(bw + 2 * c, bh + 2 * c, .6, seam - .1, seam + 1.1, bx, by))
    tray = tray - box([bx + bw / 2, 4, seam - .1, bx + bw / 2 + 4, 14, seam + 2])
    tray = intersection(tray, box([ix + gc, iy + gc, seam - .1, jx - gc, jy - gc, seam + 2]))
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
        rear = rear + box([ix + .7, y - rw / 2, seam, 22, y + rw / 2, seam + rh])
    # Four PCB screws through the original metal inserts.
    pc = v['pcb_screw']; head_depth = pc['head_height_mm']
    screw_rows = []
    for i, mount in enumerate(sorted(mounts, key=lambda st: (st.center().X, st.center().Y))):
        f = next(f for f in mount.faces() if f.geom_type == GeomType.CYLINDER
                 and abs(f.axis_of_rotation.direction.Z) > .99)
        x, y, _ = f.axis_of_rotation.position; mb = bounds(mount)[2]
        rear = rear + cyl(3.5, seam - .01, mb, x, y)
        rear = rear - cyl(pc['shaft_bore_diameter_mm'] / 2, B - .1, mb + .1, x, y)
        rear = rear - cyl(pc['head_pocket_diameter_mm'] / 2, B - .1, B + head_depth, x, y)
        screw_rows.append(dict(axis_xy_mm=[x, y], metalback_z_mm=mb,
                               head_seat_z_mm=B + head_depth,
                               tip_z_mm=B + head_depth + pc['shaft_length_mm'],
                               kind='PCB_M2_5x5_machine'))
    # Four shell screws with head pockets in the rear plate; all corner ears.
    sc = v['shell_screw']
    for x, y in screw_axes:
        if not v.get('v4'):
            ea, eb = ear_span(x)
            rear = rear + rr(eb - ea, 2 * eh, er, B, seam, (ea + eb) / 2, y)
        rear = rear - cyl(sc['thread_diameter_mm'] / 2 + .15, B - .1, seam + .1, x, y)
        rear = rear - cyl(sc['head_pocket_diameter_mm'] / 2, B - .1, B + sc['head_height_mm'], x, y)
        if sc.get('boss_diameter_mm'):
            if not v.get('v4'):
                rear = rear + cyl(sc['boss_diameter_mm'] / 2, B, seam, x, y)
            rear = rear - cyl(sc['boss_diameter_mm'] / 2 + .2, seam - .05, seam + 1.2, x, y)
    if lf:
        for y in lf['y_mm']:
            rear = rear - box([ix - .2, y - lf['half_y_mm'] - .2, seam - .1,
                               ix + lf['width_mm'] + .2, y + lf['half_y_mm'] + .2,
                               seam + lf['height_mm'] + .2])
    # USB mouth: panel notch gives the plug its lower clearance and keeps the bridge.
    rear = rear - box([ub[0] - 1.2, ey - wall - .3, B - .5, ub[3] + 1.2, ey + .2, -8.15])
    if v.get('v4'):
        ls = v['left_slab']
        rear = rear - box([ix - .2, ls['y_mm'][0], seam - .1,
                           -25.5, ls['y_mm'][1], seam + 1.2])
    # No TF cut: the card is entirely inside.

    # 6. Screw envelopes. Threads are envelopes, not cut metal.
    screws = []
    for row in screw_rows:
        x, y = row['axis_xy_mm']; hs = row['head_seat_z_mm']
        screws.append(cyl(pc['head_diameter_mm'] / 2, hs - head_depth, hs, x, y)
                      + cyl(pc['thread_diameter_mm'] / 2, hs, row['tip_z_mm'], x, y))
    for x, y in screw_axes:
        length = sc['shaft_length_mm']
        hs = B + sc['head_height_mm']
        screws.append(cyl(sc['head_diameter_mm'] / 2, hs - sc['head_height_mm'], hs, x, y)
                      + cyl(sc['thread_diameter_mm'] / 2, hs, hs + length, x, y))

    front.label = 'FRONT_V2_SCREEN_LIP_AND_POSTS'
    rear.label = 'REAR_V2_2MM_RIBBED_CLAMP'
    m.update(front=front, rear=rear, screws=screws, screw_rows=screw_rows,
             v2_parameters=v, mic_port=v.get('mic_port'), screen_geometry=dict(glass_bounds_mm=gb, glass_radius_mm=gr,
             window_whr_mm=[ww, wh, wr], lip_inner_whr_mm=[lip_inner_w, lip_inner_h, lip_inner_r],
             lip_base_whr_mm=[base_w, base_h, base_r], glass_front_z_mm=gb[5],
             lip_top_z_mm=v['screen_lip_top_z_mm']),
             dimensions=dict(front_top_z_mm=v['screen_lip_top_z_mm'],
                             front_face_z_mm=m['dimensions']['front_z_mm'],
                             seam_z_mm=seam, rear_outer_z_mm=B,
                             total_thickness_mm=v['screen_lip_top_z_mm'] - B,
                             body_xy_mm=[ex - ox, ey - oy]))
    return m
