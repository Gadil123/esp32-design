#!/usr/bin/env python3
"""Task 21 first gate. Stop at a real interference; never finish failed shell.

Old G/E files remain reproducible. This uses ALL raw official occurrences for
board clearance, and exact moved cap BReps for the failure witness. A swept AABB
alone is not accepted as proof of interference.
"""
import json
import shutil
import zipfile
from pathlib import Path
from build123d import Compound, Cylinder, Align, Axis, export_step, export_stl, import_step
from reference import bounds, to_pocket, compare_recorded
from t0_reference import load
from t0_g_model import build
from t0_e_gate import source_clashes
from p1_checks import clashes, common_volume, intersection, translated_box_sweep, cap_components
from model import box_between as box
from check_exports import verify_exports

ROOT = Path(__file__).resolve().parents[2]


def verify_witness(out):
    """One full-source negative witness round-trip; not an accepted assembly."""
    s=import_step(out/'key1_blocked_with_full_official.step')
    solids=list(s.solids());valid=sum(t.is_valid for t in solids)
    assert len(solids)==valid==725  # 723 official + one FRONT + moved cap
    return dict(solids=len(solids),valid_solids=valid,bounds_mm=bounds(s),
                scope='KEY1 collision pose; 723 official solids + FRONT + cap at Z offset -3mm; not a completed assembly')


def main():
    out = ROOT/'build/t0-g-v1-gate'
    out.mkdir(parents=True, exist_ok=True)
    q = json.loads((ROOT/'cad/t0/t0-g-v1-gate-parameters.json').read_text())
    p = json.loads((ROOT/'cad/t0/t0-g-parameters.json').read_text())
    for k in ['maximum_thickness_mm', 'screen_recess_mm', 'front_lip_overlap_mm']:
        p[k] = q[k]
    p['screw'] = {**p['screw'], 'part': 'User candidate M2.5x4 machine screw',
                  'source': 'Task 21 user product image; UNVERIFIED',
                  'head_height_mm': q['screw_head_height_mm'], 'head_recess_mm': q['screw_head_recess_mm']}
    base = json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text())
    base.update(p['layout_overrides'])
    kp = json.loads((ROOT/'cad/t0/p1-parameters.json').read_text())
    kp.update(base['key_overrides'])
    print('G-V1 first gate: import raw official STEP / all occurrence transforms / Rz180', flush=True)
    parts, mounts, _ = load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    source = [(f'official_{i}', s) for i, s in enumerate(parts['ASSEMBLY'].solids())]
    assert len(source) == 723
    m = build(parts, mounts, base, kp, p)  # NO old G hidden latches / finish().
    db = bounds(parts['DISPLAY']); d = m['dimensions']
    # Through window: absolutely no over-glass lip at any Z, .6mm lateral gap.
    clear = base['panel_xy_clearance_mm']
    m['front'] -= box([db[0]-clear, db[1]-clear, d['rear_bottom_z_mm']-1,
                       db[3]+clear, db[4]+clear, d['front_z_mm']+1])
    # Restore old RESET cap cavity in the deep wall, then drill only a pin hole.
    ox = base['outer_x_min_mm']; ix = ox+base['wall_mm']
    ry, rz = m['key_data']['KEY3']['center_yz_mm']
    half = kp['key_flange_yz_mm'][0]/2+kp['key_guide_clearance_mm']+.01
    m['front'] += box([ox, ry-half, d['rear_bottom_z_mm'], ix, ry+half, d['front_z_mm']])
    pinhole = Cylinder(q['reset_hole_diameter_mm']/2, base['wall_mm']+.2,
                      align=(Align.CENTER, Align.CENTER, Align.MIN)).rotate(Axis.Y,90).translate((ox-.1,ry,rz))
    m['front'] -= pinhole
    m['caps'].pop('KEY3')
    tol = base['volume_tolerance_mm3']
    print('G-V1 gate (a): complete board without caps, then two real caps from REAR', flush=True)
    board_path = translated_box_sweep(parts['ASSEMBLY'], (0,0,-q['rear_insertion_distance_mm']))
    board_hits = clashes(board_path, [('deep_FRONT', m['front'])], tol)
    front_hits = source_clashes(m['front'], parts, source, tol)
    rows = []
    dz = q['collision_witness_cap_z_offset_mm']
    for key, cap in m['caps'].items():
        moved = cap.translate((0,0,dz))
        hit = intersection(moved, m['front'])
        sweep_hits = []
        for piece in cap_components(cap, m['key_data'][key], kp):
            sweep_hits += clashes(translated_box_sweep(piece,(0,0,-q['rear_insertion_distance_mm'])),
                                  [('deep_FRONT',m['front']),*source],tol)
        # Exact instantaneous witness distinguishes real solid overlap from a
        # false-positive conservative swept box. The reverse path is identical.
        rows.append(dict(key=key, function=m['key_data'][key]['function'],
                         installed_source_hits=clashes(cap,source,tol),
                         installed_front_overlap_mm3=common_volume(cap,m['front']),
                         continuous_rear_insertion_hits=sweep_hits,
                         actual_cap_offset_z_mm=dz, actual_cap_front_overlap_mm3=hit.volume,
                         actual_overlap_bounds_mm=bounds(hit),
                         reverse_removal_uses_same_blocked_path=True))
        export_step(Compound([moved,m['front'],parts['ASSEMBLY']]), out/f'{key.lower()}_blocked_with_full_official.step')
        slab=box([ox-3,m['key_data'][key]['center_yz_mm'][0]-.04,-16,-20,m['key_data'][key]['center_yz_mm'][0]+.04,2])
        export_step(Compound([intersection(s,slab) for s in [m['front'],parts['ASSEMBLY'],moved]]),out/f'{key.lower()}_blocked_section.step')
    blocked = bool(board_hits or front_hits or any(r['actual_cap_front_overlap_mm3']>tol for r in rows))
    assert blocked, 'This diagnostic expects the documented first-gate blocker; reassess before progressing.'
    # Scope STOP: these are unfinished gate fixtures, NOT an accepted whole shell.
    manufactured=[('deep_front_GATE_ONLY',m['front']),('rear_seats_GATE_ONLY',m['rear']),
                  *[(k.lower()+'_cap',s) for k,s in m['caps'].items()]]
    for name,s in manufactured:
        assert s.is_valid and len(s.solids())==1
        export_step(s,out/f'{name}.step');export_stl(s,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    exported=verify_exports(out,[n for n,_ in manufactured])
    bb=bounds(Compound([parts['ASSEMBLY'],m['front'],m['rear'],*m['caps'].values(),*m['screws']]))
    suggestion=[]
    for key, cap in m['caps'].items():
        # One proposed concession only: REAR-open slots bounding the real cap
        # sweep through the wall, with .2mm candidate running clearance.
        # Clip the REAL cap to the wall's XY column first: the wider external
        # head does not cross that wall, so its AABB must not inflate slot width.
        b=bounds(intersection(cap,box([ox,-40,-100,ix,45,10])))
        suggestion.append(dict(key=key, minimum_wall_sweep_y_mm=[b[1],b[4]],
                               proposed_slot_y_mm=[b[1]-q['proposed_guide_running_clearance_mm'],b[4]+q['proposed_guide_running_clearance_mm']],
                               slot_from_rear_z_mm=d['rear_bottom_z_mm'], slot_frontmost_z_mm=b[5]+q['proposed_guide_running_clearance_mm'],
                               nominal_added_width_mm=0.0))
    report=dict(status='BLOCKED_G_V1_FIRST_ASSEMBLY_GATE', print_approved=False, full_G_V1_completed=False,
                parameters=q, official_solids=len(source), coordinate_system='USB +Y; FRONT +Z; REAR -Z; native keys LEFT -X',
                source_bounds_comparison=compare_recorded({k:to_pocket(s) for k,s in parts.items()},ROOT/'data/step_component_bounds.csv',.05),
                board_without_caps_continuous_insertion=board_hits, installed_front_source_hits=front_hits,
                two_caps_after_board=rows, part_export_checks=exported,
                incomplete_fixture_bounds_mm=bb, incomplete_fixture_maximum_thickness_mm=bb[5]-bb[2],
                thickness_status='12.4mm only for unfinished gate fixture; not full assembly PASS; no new latches or tolerance float included',
                preliminary_screw_rows=m['screw_rows'],
                first_failure='Rear-inserted daily cap flange/stem physically intersects the continuous deep FRONT sidewall before reaching its closed guide pocket. Reverse removal blocked too.',
                one_minimum_concession=dict(description='Open the two daily-key guides to REAR; rear lid then provides axial cap retention. Not implemented or validated; user decision required by task 21 STOP.', candidate_slots=suggestion,
                                            pending='Retention while lid absent; finger/tweezer access; positive fit clearance; cap-to-native moving actuator under PCB XY play; shell ligament strength'),
                not_run_after_STOP=['PCB safe independent forward support and four-hole alignment before tightening',
                                    'worst-case operating cap contact / actual switch travel',
                                    'two shallow latches and single-card sequential release',
                                    'USB/TF/pin operation; provisional accessories / live harness service slack',
                                    'full G-V1 shell and maximum retained thickness'],
                MIC_status='MIC_AUDIO_PATH_BLOCKED_UNTIL_HARDWARE',
                material_status='PA12 unqualified; no print approval; reviewer/Gemini failure probabilities and strain limits are not adopted as facts')
    report['witness_STEP_roundtrip']=verify_witness(out)
    from t0_g_v1_gate_drawings import render
    render(out,parts,m,base,q,rows)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    dest=ROOT/'deliverables/t0-g-v1-gate';dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.stl','.png','.json'] and '_with_full_official' not in f.name:
            shutil.copy2(f,dest/f.name)
    with zipfile.ZipFile(out/'t0-g-v1-blocked-gate.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.iterdir()):
            if f.suffix in ['.step','.stl','.png','.json']:
                z.write(f,f.name)
    print('BLOCKED: actual cap/deep-wall collision. STOP; no complete shell, new latches or alternative architecture.',flush=True)


if __name__=='__main__':
    main()
