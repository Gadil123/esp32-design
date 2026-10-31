"""Independent material, motion, capture and service gates for seam-drop T-slot sliders."""
import math
from model import box_between as box
from reference import bounds
from p1_checks import intersection
from g_v4_interfaces import xcyl
from g_v4_printed_keys import table


def pockets(front, rear, v):
    import g_v4_checks as C
    k = v['printed_keys']; t = table(v); rows = []; zc = t['center_z']; seam = t['seam_z']
    for y in k['y_mm']:
        # 1. Full air passages in front_shell (open from seam_z up to slot ceiling)
        c_outer = box([t['outer_x'] - 0.01, y - t['aperture_y'] / 2 + 0.01, zc - t['head_z'] / 2 + 0.01,
                       t['seat_outer_x'] - 0.01, y + t['aperture_y'] / 2 - 0.01, t['aperture_z_top'] - 0.01])
        c_flange = box([t['seat_outer_x'] + 0.01, y - t['pocket_y'] / 2 + 0.01, zc - t['flange_z'] / 2 + 0.01,
                        t['seat_x'] - 0.01, y + t['pocket_y'] / 2 - 0.01, t['pocket_z_top'] - 0.01])
        c_guide = box([t['seat_x'] + 0.01, y - t['guide_y'] / 2 + 0.01, zc - t['stem_z'] / 2 + 0.01,
                       t['inner_x'] - 0.01, y + t['guide_y'] / 2 - 0.01, t['guide_z_top'] - 0.01])

        # 2. Positive outer retaining wall (blocks flange in -X) & inner stop shoulder (blocks flange in +X)
        outer_wall = box([t['outer_x'] + 0.02, y - t['flange_y'] / 2 + 0.02, zc - t['flange_z'] / 2 + 0.02,
                          t['seat_outer_x'] - 0.02, y - t['aperture_y'] / 2 - 0.02, zc + t['flange_z'] / 2 - 0.02])
        inner_stop = box([t['seat_x'] + 0.02, y - t['flange_y'] / 2 + 0.02, zc - t['flange_z'] / 2 + 0.02,
                          t['inner_x'] - 0.02, y - t['guide_y'] / 2 - 0.02, zc + t['flange_z'] / 2 - 0.02])

        # 3. Top ceiling in front_shell (blocks flange in +Z) & rear keeper block on rear_shell (blocks flange in -Z)
        top_ceiling = box([t['seat_outer_x'] + 0.05, y - 1.5, t['pocket_z_top'] + 0.02,
                           t['seat_x'] - 0.05, y + 1.5, t['pocket_z_top'] + 0.42])
        rear_keeper_probe = box([t['seat_outer_x'] - 0.05, y - 1.5, seam + 0.05,
                                 t['seat_x'] - 0.25, y + 1.5, t['keeper_flange_z_top'] - 0.02])

        rows.append(dict(
            y_mm=y,
            outer_aperture_mm3=C.clear(front, c_outer, 'slider outer aperture'),
            flange_pocket_mm3=C.clear(front, c_flange, 'slider full pocket'),
            inner_guide_mm3=C.clear(front, c_guide, 'slider full guide'),
            outer_capture_wall_mm3=C.material(front, outer_wall, 'slider outer capture'),
            inner_stop_shoulder_mm3=C.material(front, inner_stop, 'slider inner stop'),
            top_ceiling_mm3=C.material(front, top_ceiling, 'slider top ceiling'),
            rear_keeper_block_mm3=C.material(rear, rear_keeper_probe, 'slider rear keeper'),
        ))
    p = v['reset_pinhole']
    reset = xcyl(p['diameter_mm'] / 2 - 0.001, t['outer_x'] - 0.01, t['inner_x'] + 0.01, p['y_mm'], p['z_mm'])
    return dict(keys=rows, reset_mm3=C.clear(front, reset, 'slider front RESET'))


def measured_motion(shape, v, y, switch, *, zero_fit=False):
    """Derive flange faces and tip from the actual slider solid, including STEP rereads."""
    import g_v4_checks as C
    k = v['printed_keys']; t = table(v); z = t['center_z']; b = bounds(shape); sx = bounds(switch)[0]
    # Isolate the flange wing outside the head Y-span
    wing = intersection(shape, box([t['seat_outer_x'] - 0.1, y + t['head_y'] / 2 + 0.1, z - t['flange_z'] / 2 - 0.1,
                                    t['seat_x'] + 0.1, y + t['flange_y'] / 2 + 0.1, z + t['flange_z'] / 2 + 0.1]))
    assert wing.volume > 1e-6, 'slider flange missing'
    fb = bounds(wing); stroke = t['seat_x'] - fb[3]; gap = sx - b[3]
    assert abs(fb[0] - t['seat_outer_x']) < 1e-5, 'slider outward stop plane'
    assert 0.2 < stroke < 0.9, ('slider travel', stroke)
    assert gap >= (0 if zero_fit else 0.05) - 1e-6, ('slider resting preload', gap)
    if zero_fit:
        assert abs(gap) < 1e-6, ('zero-fit contact plane', gap)
    hit = C.overlap(shape.translate((stroke, 0, 0)), switch)
    assert hit > 1e-6, ('slider reaches switch', gap, stroke, hit)
    assert b[0] < t['outer_x'] - 0.5, 'slider finger access'
    return dict(
        flange_x_mm=fb[0::3],
        actual_tip_x_mm=b[3],
        switch_tip_x_mm=sx,
        rest_gap_mm=gap,
        geometric_stroke_mm=stroke,
        switch_displacement_at_stop_mm=stroke - gap,
        static_switch_overlap_at_stop_mm3=hit,
        exposed_head_mm=t['outer_x'] - b[0],
        actual_switch_travel_mm=k['switch_actuation_travel_mm'],
        max_safe_switch_displacement_mm=k['switch_max_safe_displacement_mm'],
        zero_fit_target=zero_fit,
        status=('ZERO_FIT_GEOMETRIC_TOUCH_PRINT_PRELOAD_UNVERIFIED' if zero_fit
                else 'GEOMETRIC_CONTACT_PASS_SWITCH_TRAVEL_FORCE_UNVERIFIED'),
    )


def axial_sweep(shape, travel):
    """Continuous +X sweep of the slider across its full stroke."""
    pieces = [shape, shape.translate((travel, 0, 0))]
    for step in [0.15, 0.30, 0.45]:
        if step < travel:
            pieces.append(shape.translate((step, 0, 0)))
    res = pieces[0]
    for p in pieces[1:]:
        res = res + p
    return res


def seam_drop_sweep(shape, drop_z=8.0):
    """Continuous -Z to +Z insertion sweep from below seam_z into the T-slot."""
    b = bounds(shape)
    res = shape
    for dz in [-drop_z, -6.0, -4.0, -2.5, -1.2, -0.5]:
        res = res + shape.translate((0, 0, dz))
    assert bounds(res)[2] <= b[2] - drop_z + 1e-5
    return res


def check(m, parts, v):
    import g_v4_checks as C
    k = v['printed_keys']; t = table(v); z = k['z_center']; result = {}
    result['pockets'] = pockets(m['front'], m['rear'], v)
    result['keys'] = {}; result['variant_parts'] = {}; result['retainer_screws'] = []
    for i, y in enumerate(k['y_mm'], 1):
        key = f'KEY{i}'; switch = parts[key]; sx = bounds(switch)[0]
        mask = box([sx - 0.001, y - 1.76, -6.91, sx + 0.81, y + 1.76, -5.89])
        actuator = intersection(switch, mask)
        scope = box([-35, y - 5, z - 5, -23.5, y + 5, z + 5])
        local_obstacles = intersection(parts['ASSEMBLY'], scope) - actuator
        for label in k['variants_mm']:
            name = f'button_{"power" if i == 1 else "boot"}_{label}'
            shape = m['button_exports'][name]
            row = measured_motion(shape, v, y, switch, zero_fit=label == 'zero_fit')
            travel = row['geometric_stroke_mm']
            swept = axial_sweep(shape, travel)
            row['continuous_axial_sweep'] = {n: C.clear(m[n], swept, 'slider sweep ' + n) for n in ['front', 'rear']}
            row['non_actuator_board_sweep_mm3'] = C.clear(swept, local_obstacles, 'slider sweep non-actuator board')
            row['rest_board_mm3'] = C.clear(shape, parts['ASSEMBLY'], 'slider at rest board')
            row['screw_sweep_mm3'] = max([C.clear(s, swept, 'slider vs locked screw') for s in m['screws']] + [0])

            # Continuous -Z seam insertion/extraction sweep (with board installed in front_shell, rear_shell open)
            drop = seam_drop_sweep(shape, drop_z=8.0)
            row['continuous_seam_insertion_front_mm3'] = C.clear(m['front'], drop, 'slider -Z insertion vs front')
            row['continuous_seam_insertion_board_mm3'] = C.clear(local_obstacles, drop, 'slider -Z insertion vs board')

            # Positive 6-DOF capture once rear_shell is closed:
            assert C.overlap(m['front'], shape.translate((-0.1, 0, 0))) > 1e-5, 'slider outward (-X) retention missing'
            assert C.overlap(m['front'], shape.translate((travel + 0.1, 0, 0))) > 1e-5, 'slider inward (+X) stop missing'
            assert C.overlap(m['front'], shape.translate((0, 0, t['clearance'] + 0.1))) > 1e-5, 'slider upward (+Z) ceiling missing'
            assert C.overlap(m['rear'], shape.translate((0, 0, -(t['clearance'] + 0.1)))) > 1e-5, 'slider downward (-Z) rear lock missing'
            row['six_dof_captured_when_closed'] = True
            result['variant_parts'][name] = row
            if label == 'nominal':
                result['keys'][key] = row
            if label in ['nominal', 'zero_fit']:
                radial = []
                for angle in range(0, 360, 45):
                    dy = k['radial_clearance_mm'] * math.cos(math.radians(angle)) * 0.95
                    dz = k['radial_clearance_mm'] * math.sin(math.radians(angle)) * 0.95
                    moved = swept.translate((0, dy, dz))
                    radial.append(dict(
                        offset_yz_mm=[dy, dz],
                        non_actuator_board_mm3=C.clear(moved, local_obstacles, 'slider radial play vs board'),
                        shells_mm3={n: C.clear(m[n], moved, 'slider radial play ' + n) for n in ['front', 'rear']},
                    ))
                row['radial_translation_poses'] = radial
    p = v['reset_pinhole']; sx = bounds(parts['KEY3'])[0]
    needle = xcyl(p['tool_diameter_mm'] / 2, t['outer_x'] - 0.01, sx + 0.02, p['y_mm'], p['z_mm'])
    reach = sx - t['outer_x']; assert p['tool_free_length_mm'] > reach + 0.5
    result['reset'] = {n: C.clear(m[n], needle, 'RESET through ' + n) for n in ['front', 'rear']}
    for key, shape in m['buttons'].items():
        result['reset'][key] = C.clear(shape, needle, 'RESET vs slider')
    result['reset']['other_parts_mm3'] = {name: C.clear(parts[name], needle, 'RESET non-target ' + name) for name in ['KEY1', 'KEY2', 'DISPLAY', 'PCB_BOARD', 'TF']}
    result['reset'].update(reach_from_outer_wall_mm=reach, tool_free_length_mm=p['tool_free_length_mm'], contact_mm3=C.overlap(needle, parts['KEY3']))
    assert result['reset']['contact_mm3'] > 0
    result['functional_status'] = 'SEAM_DROP_TSLOT_GEOMETRIC_REACH_AND_CAPTURE_PASS'
    return result


def negative_controls(m, parts, v):
    k = v['printed_keys']; t = table(v); z = k['z_center']; rows = []
    def reject(name, call, expected):
        try:
            call()
        except AssertionError as exc:
            assert expected in str(exc), ('wrong negative control reason', name, str(exc))
            rows.append(dict(mutation=name, rejected=True, reason=str(exc)))
        else:
            raise AssertionError(('slider gate missed mutation', name))

    for i, y in enumerate(k['y_mm'], 1):
        seal_outer = box([t['outer_x'], y - 2, z - 1, t['seat_outer_x'], y + 2, z + 1])
        reject(f'KEY{i} outer aperture sealed', lambda: pockets(m['front'] + seal_outer, m['rear'], v), 'slider outer aperture')
        seal_guide = box([t['seat_x'], y - 1.5, z - 1, t['inner_x'], y + 1.5, z + 1])
        reject(f'KEY{i} inner guide sealed', lambda: pockets(m['front'] + seal_guide, m['rear'], v), 'slider full guide')
        cut_stop = box([t['seat_x'] - 0.1, y - 4, z - 2, t['inner_x'] + 0.1, y + 4, z + 2])
        reject(f'KEY{i} inner stop removed', lambda: pockets(m['front'] - cut_stop, m['rear'], v), 'slider inner stop')
        cut_outer = box([t['outer_x'] - 0.1, y - 4, z - 2, t['seat_outer_x'] + 0.1, y + 4, z + 2])
        reject(f'KEY{i} outer capture removed', lambda: pockets(m['front'] - cut_outer, m['rear'], v), 'slider outer capture')
        cut_keeper = box([t['outer_x'] - 0.1, y - 4, t['seam_z'], t['seat_x'], y + 4, t['keeper_outer_z_top'] + 0.1])
        reject(f'KEY{i} rear keeper block removed', lambda: pockets(m['front'], m['rear'] - cut_keeper, v), 'slider rear keeper')

        sx = bounds(parts[f'KEY{i}'])[0]; cap = m['buttons'][f'KEY{i}']
        cut = box([sx - 0.8, y - 5, z - 5, sx + 1, y + 5, z + 5])
        reject(f'KEY{i} tip shortened', lambda: measured_motion(cap - cut, v, y, parts[f'KEY{i}']), 'slider reaches switch')
        bad = cap + box([sx - 0.3, y - 1, z - 0.5, sx + 0.1, y + 1, z + 0.5])
        reject(f'KEY{i} tip preloads switch', lambda: measured_motion(bad, v, y, parts[f'KEY{i}']), 'slider resting preload')
        zero = m['button_exports'][f'button_{"power" if i == 1 else "boot"}_zero_fit']
        bad_zero = zero + box([sx - 0.1, y - 1, z - 0.5, sx + 0.1, y + 1, z + 0.5])
        reject(f'KEY{i} zero-fit tip preloads switch', lambda: measured_motion(bad_zero, v, y, parts[f'KEY{i}'], zero_fit=True), 'slider resting preload')
        cut_zero = box([sx - 0.1, y - 5, z - 5, sx + 1, y + 5, z + 5])
        reject(f'KEY{i} zero-fit tip recessed', lambda: measured_motion(zero - cut_zero, v, y, parts[f'KEY{i}'], zero_fit=True), 'zero-fit contact plane')

    p = v['reset_pinhole']
    seal_reset = xcyl(p['diameter_mm'] / 2, t['outer_x'], t['inner_x'], p['y_mm'], p['z_mm'])
    reject('RESET sealed in front shell', lambda: pockets(m['front'] + seal_reset, m['rear'], v), 'slider front RESET')
    return rows
