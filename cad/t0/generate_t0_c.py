#!/usr/bin/env python3
"""C stage-gate evidence + local alternatives/coupons; never bypass a failed gate."""
import json,shutil
from pathlib import Path
from build123d import Compound,Align,Axis,Cylinder,import_step,export_step,export_stl
from reference import bounds,to_pocket,compare_recorded
from t0_reference import load
from t0_model import build,cyl,rr
from t0_wiring import build_wiring
from t0_c_mount_study import study
from t0_c_samples import key_fixture,switch_frame_study,reset_hole_coupon
from t0_c_drawings import render
from p1_checks import common_volume,intersection,clashes,translated_box_sweep
from model import box_between as box
from check_exports import verify_exports
ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'build/t0-c';out.mkdir(parents=True,exist_ok=True);coupons=out/'coupons';coupons.mkdir(exist_ok=True)
    p=json.loads((ROOT/'cad/t0/t0-c-parameters.json').read_text());assert p['maximum_thickness_mm']<=12.4
    pa=json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text());pa['target_thickness_mm']=p['maximum_thickness_mm']
    kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text());kp.update(pa['key_overrides'])
    print('C stage 1: original STEP, mount planes and actual insertion collisions',flush=True)
    parts,mounts,tree=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    recorded=compare_recorded({k:to_pocket(s) for k,s in parts.items()},ROOT/'data/step_component_bounds.csv',.05)
    rows,seats,stops=study(parts,mounts,p);bottom=bounds(parts['DISPLAY'])[5]-p['maximum_thickness_mm'];floor=bottom+p['rear_panel_mm']
    patches=[box([row['axis_xy_mm'][0]-5,row['axis_xy_mm'][1]-5,bottom,row['axis_xy_mm'][0]+5,row['axis_xy_mm'][1]+5,floor]) for row in rows]
    paths=[]
    for dz in [-12,-6,-4,-2,-1,0,1,2,4,6,12]:
        moving=parts['DISPLAY'] if dz<=0 else parts['ASSEMBLY']
        obstacles=[(f'original_{i}',s.translate((0,0,dz))) for i,s in enumerate(moving.solids())]
        paths.append({'direction':'from REAR' if dz<=0 else 'from FRONT','offset_z_mm':dz,
                      'collisions':[{'stop_index':i,**hit} for i,s in enumerate(stops) for hit in clashes(s,obstacles,.001)]})
    blocked=any(r['collisions'] for r in paths if r['offset_z_mm']!=0)
    report={'stage':'C','status':'BLOCKED_FIXED_STOP_INSERTION' if blocked else 'REQUIRES_FURTHER_DESIGN_REVIEW','full_C_enclosure_completed':False,'print_approved':False,
            'parameters':p,'original_reference_bounds_comparison':recorded,'mounts':rows,'insertion_path_counterexamples':paths,
            'scope':'Rigid four-front-stop plus rear-nest scheme: final static fit does not imply assembly. Sampled real BRep collisions disprove tested straight insertion. No claim of global impossibility of tilted/alternative four-position schemes.'}
    passive=Compound([parts['PCB_BOARD'],parts['DISPLAY'],*mounts,*seats,*stops,*patches]);export_step(passive,out/'C1_four_mount_static_BLOCKED.step')
    # Only proceed with local alternatives, per the task's failed stage gate.
    print('C gate BLOCKED: no whole enclosure rewrite; build local two-screw comparison',flush=True)
    backup=[];screws=[];screw_rows=[];sp=p['backup_screw']
    for i,(row,seat,patch) in enumerate(zip(rows,seats,patches)):
        x,y=row['axis_xy_mm'];part=seat+patch
        if i in p['backup_screw_mount_indices']:
            head_bottom=bottom+sp['head_recess_mm'];head_seat=head_bottom+sp['head_height_mm'];tip=head_seat+sp['length_mm']
            part=part-cyl(sp['shaft_bore_diameter_mm']/2,bottom-.1,row['seat_z_mm']+.9,x,y)-cyl(sp['head_pocket_diameter_mm']/2,bottom-.1,head_seat,x,y)
            screw=cyl(sp['head_diameter_mm']/2,head_bottom,head_seat,x,y)+cyl(sp['thread_mm']/2,head_seat,tip,x,y);screws.append(screw)
            tool=cyl(.8,bottom-4,head_bottom,x,y)
            screw_rows.append({'mount_index':i,'head_bottom_z_mm':head_bottom,'head_seat_z_mm':head_seat,'tip_z_mm':tip,'seat_thickness_mm':row['seat_z_mm']-head_seat,
                               'nominal_thread_engagement_mm':tip-row['seat_z_mm'],'tool_circumscribed_probe_diameter_mm':1.6,'local_tool_access_collisions':clashes(tool,[('seat',part),('board',parts['ASSEMBLY'])],.001),
                               'printed_seat_to_metal_contact_distance_mm':part.distance_to(sorted(mounts,key=lambda s:(s.center().X,s.center().Y))[i]),
                               'thread_mating':'shaft major-diameter envelope overlaps intended nut thread; not a detailed meshed male thread',
                               'material_status':'MANUFACTURING_RISK: local ~0.8mm bearing seat, supplier/torque unverified'})
        backup.append(part)
    rear_board_path=[]
    for dz in [20,6,2,1,0]:
        moving=[(f'official_{i}',s.translate((0,0,dz))) for i,s in enumerate(parts['ASSEMBLY'].solids())]
        rear_board_path.append({'offset_z_mm':dz,'collisions':[{'support_index':i,**hit} for i,s in enumerate(backup) for hit in clashes(s,moving,.001)]})
    backup_scene=Compound([parts['PCB_BOARD'],parts['DISPLAY'],*mounts,*backup,*screws]);export_step(backup_scene,out/'C2_two_native_M2_5_REAR_local_ONLY.step')
    reread=import_step(out/'C2_two_native_M2_5_REAR_local_ONLY.step');bb=bounds(reread)
    assert reread.is_valid and all(s.is_valid for s in reread.solids()) and bb[5]-bb[2]<=p['maximum_thickness_mm']+1e-5
    report['two_M2_5_comparison']={'status':'LOCAL_GEOMETRY_CANDIDATE_MANUFACTURING_AND_FULL_ASSEMBLY_UNVERIFIED','screws':screw_rows,
        'mount_board_to_rear_before_front_frame':rear_board_path,'local_context_bounds_mm':bb,'local_context_max_z_mm':bb[5]-bb[2],
        'load_path':'heads -> rear printed seats -> factory metal nuts; PCB follows REAR at opening. No FRONT/glass clamp.',
        'not_preferred_front_fixation':'No separate FRONT-attached retainer designed; direct fixed FRONT stops fail the tested assembly path. Rear-fix candidate shown explicitly for comparison, not silently adopted.',
        'open_cover_risks':'PCB/display move with REAR; support both halves, disengage native keys, prevent glass scraping frame, unplug actual leads without traction. Actual lead lengths/MX identities unknown.'}
    print('C local USB, four-latch release fixture and separate PA12 samples',flush=True)
    ma=build(parts,mounts,pa,kp);plugs,wires,_=build_wiring(parts,pa,ma)
    report['rear_locators_to_existing_provisional_accessories']=[clashes(s,[*plugs.items(),*[(f'{k}_wire',w) for k,ws in wires.items() for w in ws],*[(k,ma[k]) for k in ['battery','speaker','protection']]],.001) for s in seats]
    clip=box([-11,36,bottom,11,43,.8]);uf=intersection(ma['front'],clip);ur=intersection(ma['rear'],clip)
    ribs=[rr(*p['usb_rib_xy_mm'],p['usb_rib_corner_radius_mm'],floor-.05,p['usb_rib_top_z_mm'],x,y) for x,y in p['usb_rib_centers_xy_mm']]
    for rib in ribs:ur=ur+rib
    report['USB_local']={'opening_xz_mm':pa['usb_opening_xz_mm'],'opening_changed':False,'lower_web_mm':bounds(ma['usbcut'])[2]-bottom,
        'independent_plug_probe_collisions':clashes(ma['usbprobe'],[('front',uf),('reinforced_rear',ur)],.001),
        'rib_board_collisions':[clashes(s,[(f'official_{i}',t) for i,t in enumerate(parts['ASSEMBLY'].solids())],.001) for s in ribs],
        'status':'MANUFACTURING_RISK: two side ribs do not thicken the 0.88mm bottom web; no assumed strength qualification'}
    export_step(Compound([uf,ur,parts['J2_USB_SIDE']]),out/'USB_two_side_ribs_local.step')
    names=[];manifest={}
    def sample(name,shape,purpose):
        b=bounds(shape);normalized=shape.translate(tuple(1-v for v in b[:3]));names.append(name)
        export_step(normalized,coupons/f'{name}.step');export_stl(normalized,coupons/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
        manifest[name]={'purpose':purpose,'units':'mm','original_to_export_translation_mm':[1-v for v in b[:3]],'source_bounds_mm':b,'print_approved':False}
    fixtures={};key_results={}
    for gap in p['key_guide_clearances_per_side_mm']:
        f,r,cap,d=key_fixture(parts,kp,p,gap);tag=str(gap).replace('.','_')
        sample(f'key_guide_{tag}_FRONT',f,f'{gap}mm per-side guide, common cap')
        sample(f'key_guide_{tag}_REAR',r,f'{gap}mm per-side guide, common cap')
        if gap==.3:sample('key_cap_COMMON',cap,'Same 4.6x2.2 head/1.9 protrusion; reuse one cap across all 3 guide pairs');fixtures['KEY1']=(f,r,cap,d)
        export_step(Compound([f,r,cap,parts['KEY1']]),out/f'key_fixture_{tag}_context_NOT_PRINT.step')
        key_results[str(gap)]=switch_frame_study(parts,kp,p,gap,'KEY1')
    for key in ['KEY2','KEY3']:key_results[key+'_0.3']=switch_frame_study(parts,kp,p,.3,key)
    f,r,cap,d=key_fixture(parts,kp,p,.3,'KEY3');fixtures['KEY3']=(f,r,cap,d)
    export_step(Compound([f,r,cap,parts['KEY3']]),out/'RESET_2_2_fixture_context_NOT_PRINT.step')
    sample('RESET_recessed_pusher_candidate',cap,'1.0mm recessed flat pusher; no fragile .7mm nose; candidate only')
    for diameter in p['reset_hole_diameters_mm']:sample('RESET_hole_'+str(diameter).replace('.','_'),reset_hole_coupon(diameter,p),f'D{diameter} round FRONT opening / .8mm face web with open rear relief; hole shrink and cleaning trial')
    row=rows[0];x,y=row['axis_xy_mm'];sample('native_mount_female_nest',seats[0]+patches[0],'Actual factory nut outer fit; no pin in M2.5 thread; .1mm radial datum clearance')
    # One actual A latch, isolated; add ONE entry adjacent to its receiver window.
    snap=ma['snaps'][1];recv=ma['receivers'][1];sc=box([12.8,-36,bottom,28,-30.8,-4.8])
    lf=intersection(ma['front'],sc);lr=intersection(ma['rear'],sc);oy=pa['outer_y_mm'][0];ea,eb=p['release_entry_x_mm']
    notch=box([ea,oy-.1,p['release_entry_bottom_z_mm'],eb,oy+p['release_entry_depth_mm'],pa['split_z_mm']])
    lf=lf-notch;lr=lr-notch
    sample('shell_snap_FRONT_receiver',lf,'One receiver + explicit pry entry, isolated from enclosure')
    export_step(Compound([lf,lr]),out/'snap_pair_context_NOT_PRINT.step')
    sample('shell_snap_REAR_beam',lr,'One mating rear beam; 1mm flexure is a PA12 trial, not certified')
    fixed_rear=lr-snap
    entry=box([21.75,oy-3,-7.0,22.25,oy+.7,-6.5]);slide=box([21.75,oy+.2,-7.0,26.25,oy+.7,-6.5])
    push=box([25.75,oy-3,-6.65,26.25,bounds(snap)[1]+.8,-6.15])
    release_checks={n:clashes(s,[('front',lf),('rear_without_compliant_beam',fixed_rear)],.001) for n,s in [('entry',entry),('slide_to_window',slide),('push_hook_inward',push)]}
    gap=p['local_anti_recapture_gap_mm'];rel=ma['snap_data'][1]['release_vector_mm']
    release_checks['capture_after_half_mm_pull_mm3']=common_volume(snap.translate((0,0,-.5)),recv)
    release_checks['released_pull_mm3']=common_volume(snap.translate(rel).translate((0,0,-.5)),recv)
    release_checks['relaxed_hook_after_local_3mm_gap_mm3']=common_volume(snap.translate((0,0,-gap)),recv)
    locations=[(26,oy+pa['wall_mm']),(pa['outer_x_min_mm']+pa['width_mm']-pa['wall_mm'],-17),(26,pa['outer_y_mm'][1]-pa['wall_mm']),(pa['outer_x_min_mm']+pa['wall_mm'],28)]
    report['four_latch_plan']={'status':'LOCAL_FIXTURES_ONLY_FULL_C_SEQUENCE_UNVERIFIED','locations_FRONT_xy_mm':locations,'opening_sequence':['bottom entry / bottom hook','right hook','top hook','left hook'],
        'single_pick_use':'Enter the one 5.2x0.8mm local notch, slide to receiver window, push inward. Hand holds opened cover edge; then move pick to next hook.',
        'local_tests':release_checks,'anti_recapture_local_gap_mm':gap,
        'limit':'A 3mm LOCAL gap clears an already released hook; no proof the complete cover can flex to preserve all previous gaps sequentially. No simultaneous all-snaps-released claim. Physical latch/warp/tool-access coupon required.'}
    report['key_frame_proxy_study']=key_results
    report['conditional_PA12_guide_budget']={str(g):{'per_side_gap_mm':g,'after_per_part_size_error_0_3_and_cleanup_0_05_mm':g-.3-.05,'supplier_confirmed':False,'status':'UNVERIFIED'} for g in p['key_guide_clearances_per_side_mm']}
    report['coupon_manifest']=manifest
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    report['coupon_export_checks']=verify_exports(coupons,names)
    report['PA12_process']={'requested':'black PA12 MJF','supplier_order_acceptance':False,'coupon_tested':False,
        'sources':{'general':'https://www.jlc-3dp.cn/technicalColumnsDetails/27832.html','MJF_PA12_listing':'https://www.jlc-3dp.cn/model','linked_PA12_article_is_SLS':'https://www.jlc-3dp.cn/technicalColumnsDetails/59512.html','backup_head_dimensions':'https://www.nbk1560.com/images/en-US/product/lowsmallheadscrew/SSH/SSH_1.pdf'},
        'general_references_not_order_guarantees':{'protrusion_snap_recommended_mm':'>1.5','nylon_under100mm_mm':'+/-0.3'},
        'known_features_requiring_supplier_and_coupon_review':{'rear_plate_mm':1.2,'USB_bottom_web_mm':report['USB_local']['lower_web_mm'],'front_stop_mm':.75,'front_stop_LCD_gap_mm':.1,'snap_beam_mm':1,'key_contact_thickness_mm':kp['key_tip_yz_mm'][1],'grille_slot_mm':.9,'grille_rib_mm':1.1,'protection_side_clearance_mm':.23}}
    report['unchanged_real_device_gates']=['MIC1 port direction/PCB acoustic hole/recording; no formal acoustic opening','TF seating/eject/fingernail','MX0/MX1 BAT/SPK identity, polarity, actual mating plugs, lead length and exit','battery/speaker/protection actual dimensions','switch travel/return/force; frame proxy is not a moving-component model']
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    render(out,parts,mounts,rows,seats,stops,patches,backup,screws,(uf,ur,ribs,ma['usbprobe']),fixtures,{'snaps':[ma['snaps'][i] for i in p['four_latch_A_indices']],'locations':locations,'coupon':(lf,lr)})
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    dst=ROOT/'deliverables/t0-c';dst.mkdir(exist_ok=True)
    for file in out.iterdir():
        if file.suffix in ['.step','.png','.json']:shutil.copy2(file,dst/file.name)
    shutil.copytree(coupons,dst/'coupons',dirs_exist_ok=True)
    print('C gate BLOCKED, evidence/local alternatives and individual coupons exported. A/B unchanged. No full C or print approval.',flush=True)

if __name__=='__main__':main()
