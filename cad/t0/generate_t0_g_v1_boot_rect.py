#!/usr/bin/env python3
"""Task26: one BOOT profile, local gate first; preserve task23 exports."""
import json,shutil,zipfile
from pathlib import Path
from build123d import Compound,Color,GeomType,export_step,export_stl,export_gltf,import_step
from t0_reference import load
from reference import bounds
from model import box_between as box
from p1_model import contact_face
from p1_checks import common_volume,clashes,translated_box_sweep,intersection
from t0_e_gate import source_clashes
from t0_g_v1_integrated_keys import foundation,build_keys,press_pose
from generate_t0_g_v1_integrated import shortened
from t0_g_v1_closure import build as close_shell
from t0_g_v1_full_gate import evaluate,additional_fit_checks
from check_exports import verify_exports

ROOT=Path(__file__).resolve().parents[2]
NAME='t0-g-v1-boot-rect'


def local_check(parts,m,base,q):
    tol=base['volume_tolerance_mm3'];source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    assert len(source)==723
    path=translated_box_sweep(parts['ASSEMBLY'],(0,0,-20))
    installed=source_clashes(m['front'],parts,source,tol)
    insertion=clashes(path,[('FRONT_with_real_bumps_and_stops',m['front'])],tol)
    row=m['integrated_keys'][1];native=parts['KEY2'];kb=bounds(native);fb=bounds(contact_face(native))
    others=[(n,s) for n,s in source if max(abs(a-b) for a,b in zip(bounds(s),kb))>1e-5];assert len(others)==722
    frame=native-box([kb[0]-1,fb[1],fb[2],kb[3]+1,fb[4],fb[5]])
    fixed=m['front']-row['free']-row['stop'];poses=[]
    for d in [0,q['candidate_press_mm'],q['candidate_stop_mm'],q['candidate_stop_mm']+.03]:
        pose,angle=press_pose(row,base,q,d)
        poses.append(dict(pad_reference_mm=d,rotation_deg=angle,native_distance_mm=pose.distance_to(native),
            native_overlap_mm3=common_volume(pose,native),outside_face_PROXY_overlap_mm3=common_volume(pose,frame),
            fixed_front_overlap_mm3=common_volume(pose,fixed),stop_overlap_mm3=common_volume(pose,row['stop']),
            other_722_source_hits=clashes(pose,others,tol)))
    rest,_=press_pose(row,base,q,0)
    rest_error=abs(rest.volume-row['free'].volume)+abs(common_volume(rest,row['free'])-row['free'].volume)
    old=import_step(ROOT/'deliverables/t0-g-v1-integrated/front_integrated_GATE_ONLY.step')
    # A single finite allowed BOOT region; any change elsewhere is a regression.
    zone=box([-29.6,-33,-10,-25.5,-15.8,-.2])
    added=m['front']-old;removed=old-m['front']
    outside=(added-zone).volume+(removed-zone).volume
    er,_=shortened(row,q);pressed,_=press_pose(er,base,q,q['candidate_stop_mm'])
    reach=pressed.distance_to(native.translate((q['pcb_xy_radial_play_mm'],0,0)))
    bad=bool(installed or insertion or rest_error>tol or outside>tol or reach>.001)
    bad=bad or any(p['fixed_front_overlap_mm3']>tol or p['outside_face_PROXY_overlap_mm3']>tol or p['other_722_source_hits'] for p in poses)
    bad=bad or poses[0]['native_overlap_mm3']>tol or poses[-1]['stop_overlap_mm3']<=tol
    L=q['root_to_pad_mm']-q['fixed_root_length_mm'];height=row['leaf_z_mm'][1]-row['leaf_z_mm'][0]
    return dict(status='BLOCKED_LOCAL_BOOT' if bad else 'LOCAL_BOOT_NOMINAL_PASS_PHYSICAL_PENDING',print_approved=False,
        official_solids=723,coordinates='USB +Y / FRONT +Z / REAR -Z / native keys LEFT -X',
        installed_source_hits=installed,continuous_board_insertion_and_reverse_removal=insertion,
        rest_proxy_identity_error_mm3=rest_error,poses=poses,local_allowed_change_bounds_mm=bounds(zone),
        changes_outside_BOOT_mm3=outside,added_volume_mm3=added.volume,removed_volume_mm3=removed.volume,
        rest_bump_to_continuous_board_gap_mm=row['bump'].distance_to(path),stop_to_continuous_board_gap_mm=row['stop'].distance_to(path),
        bore_0_15_and_tip_minus_0_30_reach_gap_mm=reach,free_leaf_bounds_mm=bounds(row['free']),
        dimensions=dict(outline_root_to_end_mm=q['root_to_pad_mm']+q['pad_half_y_mm'],free_leaf_length_mm=bounds(row['free'])[4]-bounds(row['free'])[1],
            effective_length_mm=L,leaf_X_mm=q['leaf_thickness_mm'],leaf_Z_height_mm=height,slot_mm=q['slot_mm'],outer_YZ_radius_mm=q['boot_rectangle']['outer_radius_mm'],root_XY_radius_mm=q['root_radius_mm']),
        strength_comparison=dict(old_beam_Z_height_mm=2,new_beam_Z_height_mm=height,nominal_bending_stiffness_ratio_same_material=height/2,
            root_strain_at_stop_proxy=1.5*q['leaf_thickness_mm']*q['candidate_stop_mm']/L**2,
            old_root_strain_at_stop_proxy=1.5*q['leaf_thickness_mm']*q['candidate_stop_mm']/L**2,
            force_N=None,allowable_strain=None,life_cycles=None,
            limits='Same11mm effective length and1.2mm thickness; +50% nominal beam stiffness, NOT same force or verified comfort. Old L pad Z eccentricity reduced. Root concentration, torsion, nonlinear PA12 and printing orientation unverified.'),
        actual_native_travel_mm=None,function='UNVERIFIED_UNTIL_HARDWARE',
        limits=['1.4mm is pad-reference displacement, not native travel. Contact with whole KEY BRep is not triggering proof.',
                'Outside-face fixed-frame test is a proxy; actual moving head/overpressure remain unverified.',
                'Known register .20 + bore .15 + tip -.30 failure retained; no automatic .12mm tip extension.'])


def main():
    out=ROOT/'build'/NAME;out.mkdir(parents=True,exist_ok=True)
    q=json.loads((ROOT/'cad/t0/t0-g-v1-boot-rect.json').read_text())
    base=json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text());p=json.loads((ROOT/'cad/t0/t0-g-parameters.json').read_text());base.update(p['layout_overrides'])
    kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text());kp.update(base['key_overrides'])
    print('Task26: import RAW official STEP / all723 solids / cumulative locations / Rz180',flush=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    m,p=foundation(parts,mounts,base,kp,p,q);m=build_keys(parts,m,base,q)
    assert m['front'].is_valid and len(m['front'].solids())==1
    local=local_check(parts,m,base,q)
    (out/'local_checks.json').write_text(json.dumps(local,indent=2)+'\n')
    export_step(m['front'],out/'front_local_GATE_ONLY.step')
    from t0_g_v1_boot_rect_drawings import local_views
    local_views(out,parts,m,base,q,local)
    print(local['status'],flush=True)
    if local['status'].startswith('BLOCKED'):
        local['minimum_concession']='Keep the e805d38 L-shaped BOOT; no shorter lever or separate cap is designed.'
        (out/'local_checks.json').write_text(json.dumps(local,indent=2)+'\n');publish(out);return
    c=json.loads((ROOT/'cad/t0/t0-g-v1-closure.json').read_text());m=close_shell(m,parts,mounts,base,c)
    gate,held,accessories=evaluate(parts,mounts,m,base,q,c)
    report=dict(task='26 BOOT rounded rectangle only',local=local,full_assembly_gate=gate,print_approved=False,
                actual_native_switch_travel_mm=None,material_and_function='UNVERIFIED_UNTIL_HARDWARE',MIC='MIC_AUDIO_PATH_BLOCKED_UNTIL_HARDWARE')
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if gate['status'].startswith('BLOCKED'):
        print('STOP full nominal assembly gate',flush=True);publish(out);return
    oldfront=import_step(ROOT/'deliverables/t0-g-v1/front_shell.step');oldrear=import_step(ROOT/'deliverables/t0-g-v1/rear_shell.step')
    zone=box(local['local_allowed_change_bounds_mm']);delta=(m['front']-oldfront-zone).volume+(oldfront-m['front']-zone).volume
    rear_delta=(m['rear']-oldrear).volume+(oldrear-m['rear']).volume
    assert delta<base['volume_tolerance_mm3'] and rear_delta<base['volume_tolerance_mm3']
    report['freeze_checks']=dict(front_change_outside_BOOT_mm3=delta,rear_symmetric_difference_mm3=rear_delta,
        BAT_PWR_TF_RESET_E_oldG_PocketOS='unchanged; old delivery directories not overwritten')
    export_step(m['front'],out/'front_shell.step');export_stl(m['front'],out/'front_shell.stl',tolerance=.015,angular_tolerance=.12)
    report['part_export_checks']=verify_exports(out,['front_shell'])
    report.update(additional_fit_checks(parts,m,base,q,c,import_step(out/'front_shell.step'),accessories))
    # Keep the complete board as one named exact group. No proxy in this file.
    board=Compound(parts['ASSEMBLY'].solids());board.label='OfficialBoard_ALL_723_REAL_SOLIDS'
    front=Compound(m['front'].wrapped);front.label='FrontShell_BOOT_RECT_BAT_PWR_L'
    rear=Compound(m['rear'].wrapped);rear.label='RearShell_UNCHANGED'
    hardware=Compound(m['screws']);hardware.label='Four_M2_5_CANDIDATE_SCREWS'
    extras=Compound([s for _,s in accessories]);extras.label='UNVERIFIED_ACCESSORIES_PLUGS_WIRES'
    complete=Compound(label='G_V1_TASK26_EXACT_NAMED_ASSEMBLY',children=[board,front,rear,hardware,extras])
    print('Export named complete assembly / source board / same-coordinate viewer parts',flush=True)
    export_step(complete,out/'assembly_complete_12_4mm.step')
    rr=import_step(out/'assembly_complete_12_4mm.step');ss=rr.solids();bb=bounds(rr);valid=sum(s.is_valid for s in ss)
    assert len(ss)==valid==739 and bb[5]-bb[2]<=12.400001
    report['complete_STEP_roundtrip']=dict(solids=len(ss),valid_solids=valid,bounds_mm=bb,maximum_thickness_mm=bb[5]-bb[2],
        top_level_names=[ch.label for ch in rr.children],official_physical_solids_preserved=723,non_solid_reference_faces_omitted=True,maximum_with_retained_rear_play_mm=gate['maximum_with_retained_rear_play_mm'])
    refs=[parts['PCB_BOARD'],*mounts]
    for name in ['DISPLAY','J2_USB_SIDE','KEY1','KEY2','KEY3','TF','MIC1','MX0','MX1']:
        s=box(bounds(parts[name]));s.label=name+'_PROXY_NOT_FOR_CLEARANCE';refs.append(s)
    light=Compound(label='TASK26_LIGHT_PROXIES_NOT_FOR_CLEARANCE',children=[*refs,front,rear,hardware,extras])
    export_step(light,out/'assembly_light.step');export_gltf(light,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    viewer=out/'viewer';(viewer/'common').mkdir(parents=True,exist_ok=True)
    for version in ['baseline_e805d38','boot_rect_task26']:(viewer/version).mkdir(exist_ok=True)
    for name,s in [('OfficialBoard_723',board),('RearShell',rear),('Hardware',hardware),('Accessories_UNVERIFIED',extras)]:
        # A shared scene child is not an export root. Detach the wrapper,
        # preserving its already-absolute BRep coordinates.
        standalone=Compound(s.wrapped);standalone.label=name
        export_step(standalone,viewer/'common'/f'{name}.step')
    shutil.copy2(ROOT/'deliverables/t0-g-v1/front_shell.step',viewer/'baseline_e805d38/FrontShell.step')
    shutil.copy2(out/'front_shell.step',viewer/'boot_rect_task26/FrontShell.step')
    shutil.copy2(out/'assembly_complete_12_4mm.step',viewer/'boot_rect_task26/assembly_complete_12_4mm.step')
    print('Read back independent viewer parts and preserve their coordinates',flush=True)
    vr={}
    for f in sorted((viewer/'common').glob('*.step')):
        s=import_step(f);bs=bounds(s);count=len(s.solids());ok=sum(x.is_valid for x in s.solids());assert count==ok
        vr[f.stem]=dict(solids=count,valid_solids=ok,bounds_mm=bs)
    assert vr['OfficialBoard_723']['solids']==723
    report['viewer_parts_roundtrip']=vr
    report['viewer_limit']='Exact same-coordinate Part::Feature groups, not a FreeCAD constraint-based Assembly WB project; visual explosion is not an assembly path proof.'
    report['status']='NOMINAL_BOOT_RECT_CAD_COMPLETE / '+report['combined_register_bore_print_reach']['status']
    from t0_g_v1_boot_rect_drawings import full_views
    full_views(out,parts,m,mounts,base,q,report)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copy2(ROOT/'cad/t0/view_g_v1_freecad.py',viewer/'view_g_v1_freecad.py')
    shutil.copy2(ROOT/'docs/28_g_v1_private_download_freecad.md',viewer/'README.md')
    shutil.copy2(out/'checks.json',viewer/'checks.json')
    with zipfile.ZipFile(out/'t0-g-v1-boot-rect-task26-viewer.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(viewer.rglob('*')):
            if f.is_file():z.write(f,str(f.relative_to(viewer)))
    publish(out);print(report['status']+'; NOT PRINT APPROVED',flush=True)


def publish(out):
    dest=ROOT/'deliverables'/NAME;dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.stl','.glb','.png','.json'] and f.name not in ['assembly_complete_12_4mm.step']:
            shutil.copy2(f,dest/f.name)


if __name__=='__main__':main()
