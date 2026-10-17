#!/usr/bin/env python3
"""Task23 finite gate: all original solids, one U-leaf design and one error witness.

Only a substantive failed gate stops shell work. Unknown switch travel/material
properties are recorded separately, not converted into invented failures.
"""
import json,math,shutil,zipfile
from pathlib import Path
from build123d import Compound, GeomType, export_step, export_stl, import_step
from t0_reference import load
from reference import bounds,to_pocket,compare_recorded
from p1_model import contact_face
from p1_checks import clashes,common_volume,intersection,translated_box_sweep
from t0_e_gate import source_clashes
from t0_g_v1_integrated_keys import foundation,build_keys,press_pose
from check_exports import verify_exports
from model import box_between as box

ROOT=Path(__file__).resolve().parents[2]


def shortened(row,q):
    """Actual terminal undersize, not illegal .45mm translation of the PCB.

    Leave the leaf/root/stop untouched. Shorten the protrusion X reach by .3mm,
    then place the original board +.15mm within screw-bore radial play.
    """
    b=bounds(row['bump']);cut=box([row['tip_x']-q['printed_feature_offset_budget_mm'],b[1]-.01,b[2]-.01,
                                  row['tip_x']+.1,b[4]+.01,b[5]+.01])
    return {**row,'free':row['free']-cut,'bump':row['bump']-cut},cut


def main():
    out=ROOT/'build/t0-g-v1-integrated';out.mkdir(parents=True,exist_ok=True)
    q=json.loads((ROOT/'cad/t0/t0-g-v1-integrated-keys.json').read_text())
    p=json.loads((ROOT/'cad/t0/t0-g-parameters.json').read_text());base=json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text());base.update(p['layout_overrides'])
    kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text());kp.update(base['key_overrides'])
    print('Task23: raw official STEP -> accumulated occurrence locations -> Rz180',flush=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())];assert len(source)==723
    m,p=foundation(parts,mounts,base,kp,p,q);m=build_keys(parts,m,base,q)
    assert m['front'].is_valid and len(m['front'].solids())==1
    tol=base['volume_tolerance_mm3'];distance=p['assembly_translation_mm'];rows=[]
    print('Check full PCB/display insertion/removal with both integral bumps AND stops',flush=True)
    path=translated_box_sweep(parts['ASSEMBLY'],(0,0,-distance))
    insertion=clashes(path,[('complete_integral_FRONT',m['front'])],tol)
    installed=source_clashes(m['front'],parts,source,tol)
    for row in m['integrated_keys']:
        key=row['key'];face=contact_face(parts[key]);fb=bounds(face);kb=bounds(parts[key])
        # Outside the outward face footprint is ONLY a frame proxy: no asserted
        # internal moving/fixed identity. Reach failure uses the WHOLE source key.
        frame=parts[key]-box([kb[0]-1,fb[1],fb[2],kb[3]+1,fb[4],fb[5]])
        fixed=m['front']-row['free'];press_rows=[]
        nonkey=[(n,s) for n,s in source if max(abs(a-b) for a,b in zip(bounds(s),kb))>1e-5]
        assert len(nonkey)==722
        for delta in [0,q['candidate_press_mm'],q['candidate_stop_mm'],q['candidate_stop_mm']+.02]:
            pose,angle=press_pose(row,base,q,delta)
            press_rows.append(dict(pad_reference_displacement_mm=delta,end_rotation_degrees=angle,
                whole_native_switch_distance_mm=pose.distance_to(parts[key]),
                whole_native_switch_overlap_mm3=common_volume(pose,parts[key]),
                outside_face_footprint_PROXY_overlap_mm3=common_volume(pose,frame),
                independent_shell_stop_overlap_mm3=common_volume(pose,row['stop']),
                other_front_overlap_mm3=common_volume(pose,fixed-row['stop']),
                other_source_hits=clashes(pose,nonkey,tol)))
        rest,_=press_pose(row,base,q,0)
        rest_identity_error=abs(rest.volume-row['free'].volume)+abs(row['free'].volume-common_volume(rest,row['free']))
        assert rest_identity_error<tol, 'The rest deformation proxy must match the true free leaf'
        er,cut=shortened(row,q);error_pose,angle=press_pose(er,base,q,q['candidate_stop_mm'])
        native=parts[key].translate((q['pcb_xy_radial_play_mm'],0,0));target=face.translate((q['pcb_xy_radial_play_mm'],0,0))
        gap=error_pose.distance_to(native)
        y_witnesses=[]
        for dy in [-q['pcb_xy_radial_play_mm'],q['pcb_xy_radial_play_mm']]:
            shifted=native.translate((0,dy,0))
            y_witnesses.append(dict(PCB_Y_mm=dy,gap_mm=error_pose.distance_to(shifted),native_overlap_mm3=common_volume(error_pose,shifted)))
        result=dict(key=key,function=m['key_data'][key]['function'],native_outward_face_bounds_mm=fb,
            root_y_mm=row['root_y'],direction=row['direction'],rest_bump_x_mm=bounds(row['bump'])[3],
            rest_first_contact_axial_gap_mm=fb[0]-row['tip_x'],
            continuous_module_AABB_to_rest_bump_gap_mm=row['bump'].distance_to(path),
            continuous_module_AABB_to_stop_gap_mm=row['stop'].distance_to(path),
            rest_proxy_identity_volume_error_mm3=rest_identity_error,nominal_press_poses=press_rows,
            tolerance_witness=dict(PCB_X_mm=q['pcb_xy_radial_play_mm'],bump_terminal_X_undersize_mm=q['printed_feature_offset_budget_mm'],
                at_shell_stop_displacement_mm=q['candidate_stop_mm'],whole_native_switch_gap_mm=gap,
                additional_conservative_square_Y_endpoints=y_witnesses,
                outward_face_gap_mm=error_pose.distance_to(target),native_switch_overlap_mm3=common_volume(error_pose,native),
                shell_stop_overlap_mm3=common_volume(error_pose,row['stop']),
                source_identity_note='Whole unmodified official KEY BRep; positive gap means no contact with ANY modeled part, no moving-head assumption required.',
                status='BLOCKED_CANNOT_CONTACT_SWITCH_AT_STOP' if gap>.001 or any(w['gap_mm']>.001 for w in y_witnesses) else 'CONTACT_ONLY_FUNCTION_UNVERIFIED'))
        rows.append(result)
        print(key,json.dumps(result['tolerance_witness']),flush=True)
        slab=box([-31,row['y']-1.5,-13,-20,row['y']+1.5,1])
        export_step(Compound([intersection(s,slab) for s in [m['front'],parts['ASSEMBLY']]]),out/f'{key.lower()}_rest_section.step')
    press_blocked=any(p['other_source_hits'] or p['other_front_overlap_mm3']>tol or
                      p['outside_face_footprint_PROXY_overlap_mm3']>tol
                      for r in rows for p in r['nominal_press_poses'])
    assert all(r['nominal_press_poses'][-1]['independent_shell_stop_overlap_mm3']>tol for r in rows)
    failed=bool(insertion or installed or press_blocked or any(r['tolerance_witness']['status'].startswith('BLOCKED') for r in rows))
    # The only subsequent work on failure is review evidence, not new shell CAD.
    status='BLOCKED_INTEGRATED_KEY_GEOMETRY' if failed else 'LOCAL_NOMINAL_GATE_PASS_PHYSICAL_PENDING'
    bb=bounds(Compound([parts['ASSEMBLY'],m['front']]))
    report=dict(status=status,full_G_V1_completed=False,print_approved=False,parameters=q,
        source=dict(official_solids=723,coordinate_system='USB +Y TOP / FRONT +Z / REAR -Z / keys LEFT -X',
            recorded_bounds=compare_recorded({k:to_pocket(s) for k,s in parts.items()},ROOT/'data/step_component_bounds.csv',.05)),
        whole_front_installed_source_hits=installed,complete_module_continuous_insertion_and_reverse_removal=insertion,
        assembly_scope='Resting integral leaves, both bumps, fixed stops, all723 solids; continuous conservative Z AABB. No simultaneous external leaf holding required.',
        buttons=rows,local_fixture_bounds_mm=bb,local_fixture_Z_span_mm=bb[5]-bb[2],
        thickness_scope='Local unfinished FRONT+board only; not a full enclosure/retained-thickness pass',
        strength_risk=dict(effective_length_mm=q['root_to_pad_mm']-q['fixed_root_length_mm'],
            end_force_small_deflection_root_strain_at_0_4=1.5*q['leaf_thickness_mm']*q['candidate_press_mm']/(q['root_to_pad_mm']-q['fixed_root_length_mm'])**2,
            end_force_small_deflection_root_strain_at_stop=1.5*q['leaf_thickness_mm']*q['candidate_stop_mm']/(q['root_to_pad_mm']-q['fixed_root_length_mm'])**2,
            actual_allowable_strain=None,force_N=None,life_cycles=None,
            limits='End-force Euler-Bernoulli clearance proxy with end rotation; no zero-slope free end assumption. Fillet concentration, pad eccentricity, torsion, nonlinear/material and print orientation effects pending.'),
        physical_switch_function='UNVERIFIED_UNTIL_HARDWARE',actual_switch_travel_mm=None,
        MIC_status='MIC_AUDIO_PATH_BLOCKED_UNTIL_HARDWARE',
        manufacturing=dict(source='https://jlc3dp.com/help/article/3d-printing-design-guideline',
            status='PENDING_VENDOR_ACCEPTANCE_NOT_DFM_PASS',
            facts='MJF guide: 10x10 local wall1.2; moving clearance .6; model tolerance +/- .3 below100mm; protrusions/snaps recommended >1.5. These do NOT approve this flexure.',
            exception='Contact tip .8x.8 below nylon wall/small-column recommendations; not accepted merely because embossed-detail resolution is .8. Root return, powder removal and bead blasting need supplier review.'),
        stopped_work=(['New two-latch rear and single-card opening','Four-screw PCB final restraint/seat and full tolerance stack','Accessory/harness closure and complete retained thickness','Completed G-V1 enclosure export'] if failed else []),
        one_minimum_concession=('Use the already authorized REAR-open guide plus original separate caps (task22); independent cap translation avoids this long-leaf end-rotation/reach coupling. Needs its own gate; not automatically built or claimed passed.' if failed else None))
    # Review parts: full original reference remains outside Git.
    export_step(m['front'],out/'front_integrated_GATE_ONLY.step');export_stl(m['front'],out/'front_integrated_GATE_ONLY.stl',tolerance=.015,angular_tolerance=.12)
    report['front_export_checks']=verify_exports(out,['front_integrated_GATE_ONLY'])
    front=import_step(out/'front_integrated_GATE_ONLY.step')
    ox=base['outer_x_min_mm'];ix=ox+base['wall_mm'];zl,zh=q['leaf_z_mm']
    def span(region,axis):
        b=bounds(intersection(front,box(region)));return b[axis+3]-b[axis]
    ub=bounds(m['tfcut']);yy=(max(ub[1],m['integrated_keys'][0]['y']+2)+min(ub[4],m['integrated_keys'][0]['root_y']-1))/2
    report['exported_named_local_features']=dict(
        leaf_X_thickness_mm=[span([ox-.01,row['root_y']+row['direction']*4-.02,(zl+zh)/2-.02,ix+.01,row['root_y']+row['direction']*4+.02,(zl+zh)/2+.02],0) for row in m['integrated_keys']],
        TF_to_U_slot_ligament_mm=span([ox+.2,yy-.02,ub[5]-.1,ox+.4,yy+.02,zl-q['slot_mm']+.1],2),
        FRONT_rim_above_U_slot_mm=span([ox+.2,yy-.02,zh+q['slot_mm']-.1,ox+.4,yy+.02,.8],2),
        U_slot_pair_distance_mm=m['integrated_keys'][0]['slot'].distance_to(m['integrated_keys'][1]['slot']),
        stop_axial_section_height_mm=q['shell_stop_height_mm'],
        note='Named sections, not global minimum wall certificate; rounded boundaries are not zero-thickness defects.')
    radii=[]
    for f in front.faces():
        if f.geom_type==GeomType.CYLINDER and abs(f.radius-q['root_radius_mm'])<1e-6:
            axis=f.axis_of_rotation
            if abs(axis.direction.Z)>.99 and abs(axis.position.X-(base['outer_x_min_mm']+q['leaf_thickness_mm']+q['root_radius_mm']))<1e-5:
                radii.append(dict(radius_mm=f.radius,axis_origin_mm=list(axis.position)))
    report['exported_root_transition_cylinders']=radii;assert len(radii)==2
    nominal=Compound([parts['ASSEMBLY'],front]);export_step(nominal,out/'local_nominal_with_full_official.step')
    rr=import_step(out/'local_nominal_with_full_official.step');ss=list(rr.solids());valid=sum(s.is_valid for s in ss)
    assert len(ss)==valid==724
    report['nominal_reference_STEP_roundtrip']=dict(solids=len(ss),valid_solids=valid,bounds_mm=bounds(rr),scope='Local FRONT+723 official, no complete rear/accessory assembly')
    first=m['integrated_keys'][0];er,cut=shortened(first,q);pose,_=press_pose(er,base,q,q['candidate_stop_mm'])
    export_step(Compound([parts['ASSEMBLY'].translate((q['pcb_xy_radial_play_mm'],0,0)),front-first['free'],pose]),out/'worst_reach_key1_with_full_official.step')
    from t0_g_v1_integrated_drawings import render
    render(out,parts,m,base,q,report)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    dest=ROOT/'deliverables/t0-g-v1-integrated';dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.stl','.json','.png'] and '_with_full_official' not in f.name and '_dev' not in f.name:
            shutil.copy2(f,dest/f.name)
    with zipfile.ZipFile(out/'t0-g-v1-integrated-local-review.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.iterdir()):
            if f.suffix in ['.step','.stl','.json','.png'] and '_dev' not in f.name:z.write(f,f.name)
    print(status+'; NOT PRINT APPROVED',flush=True)
    return parts,mounts,m,base,kp,p,q,report


if __name__=='__main__':main()
