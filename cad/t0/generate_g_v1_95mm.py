"""G-V1 width optimization; original board and frozen key/screw geometry.

A local search precedes full-shell rebuilding. Do not export print meshes if
any NEW nominal geometry or motion gate fails. Conditional physical risks stay.
"""
import json,copy,gc,shutil,zipfile
from pathlib import Path
from build123d import Compound,import_step,export_step,export_stl
from t0_reference import load
from reference import bounds
from model import box_between as box
from p1_checks import common_volume,intersection,clashes
from t0_g_v1_integrated_keys import foundation,build_keys
from t0_g_v1_closure import build as close_shell
from t0_g_v1_full_gate import evaluate,additional_fit_checks
from g_v1_95mm_wiring import build as wiring
from study_g_v1_95mm import study
from check_exports import verify_exports
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/g-v1-95mm'
def read(name):return json.loads((ROOT/'cad/t0'/name).read_text())
def make(parts,mounts,base,p,kq,c):
    kp=read('p1-parameters.json');kp.update(base['key_overrides'])
    m,_=foundation(parts,mounts,base,kp,p,kq);m=build_keys(parts,m,base,kq)
    return close_shell(m,parts,mounts,base,c)
def delta(a,b):return (a-b).volume+(b-a).volume

def main():
    OUT.mkdir(parents=True,exist_ok=True);build=ROOT/'build/g-v1-95mm';build.mkdir(parents=True,exist_ok=True)
    cfg=read('g-v1-95mm-layout.json');kq=read('t0-g-v1-boot-rect.json');c0=read('t0-g-v1-closure.json')
    p=read('t0-g-parameters.json');b0=read('t0-a-parameters.json');b0.update(p['layout_overrides'])
    print('Import RAW official STEP / all723 real solids / cumulative placements / Rz180',flush=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    search=study(parts,OUT,cfg);assert next(row for row in search['rows'] if row['speaker_shift_x_mm']==search['selected_shift_x_mm'])['receiver_fence_overlap_mm3']<.001
    print('Local search clear. Rebuild frozen baseline and verify helper invariance.',flush=True)
    old=make(parts,mounts,b0,p,kq,c0)
    freeze={n:delta(old[n],import_step(ROOT/f'deliverables/{path}')) for n,path in [('front','t0-g-v1-boot-rect/front_shell.step'),('rear','t0-g-v1/rear_shell.step')]}
    assert max(freeze.values())<.001
    base=copy.deepcopy(b0);base['width_mm']=cfg['target_width_mm']
    base['battery'].update(xyz_mm=cfg['battery_complete_xyz_mm'],center_xy_mm=cfg['battery_center_xy_mm'],adhesive_mm=cfg['battery_adhesive_candidate_mm'],protection_xyz_mm=cfg['terminal_keepout_xyz_mm'],status='user_measured_COMPLETE_component')
    base['battery']['tray_clearance_mm']=cfg['battery_tray_clearance_mm']
    base['speaker'].update(xyz_mm=cfg['speaker_xyz_mm'],center_xy_mm=cfg['selected_speaker_center_xy_mm'],status='user_measured_body; lead fit verified by user at intended position')
    base['narrow_wiring']=cfg['wiring'];c=copy.deepcopy(c0);d=cfg['width_reduction_mm']
    for field in ['clip_x_mm','receiver_x_mm','hook_x_mm']:c[field]=[x-d for x in c[field]]
    c['clip_sites'][0]['beam_x0_mm']-=d;c['front_wall_release_x_max_mm']-=d
    print(f'Build full95.60 shell: speakerX{cfg["selected_speaker_center_xy_mm"][0]-46:+.2f}, battery-2, right latch+wall-4; no thinner features',flush=True)
    m=make(parts,mounts,base,p,kq,c)
    assert m['front'].is_valid and m['rear'].is_valid
    # Geometry comparisons cover complete lower latch and root neighborhood,
    # not just dimensional constants. Upper latch / LEFT wall stay in place.
    comparisons={'baseline_regeneration_delta_mm3':freeze}
    left=box([-31,-36,-12,25.9,42,1])
    comparisons['all_front_material_X_below_25_9_delta_mm3']=delta(intersection(m['front'],left),intersection(old['front'],left))
    comparisons['lower_free_latch_translated_back_delta_mm3']=delta(m['rear_clips'][0]['free'].translate((d,0,0)),old['rear_clips'][0]['free'])
    comparisons['upper_free_latch_delta_mm3']=delta(m['rear_clips'][1]['free'],old['rear_clips'][1]['free'])
    root=old['rear_clips'][0]['root_y'];a,b=c0['clip_x_mm'];rb=old['closure_dimensions']['rear_bottom_mm'];floor=old['closure_dimensions']['rear_floor_mm']
    rootzone=box([a-1.1,root-.7,rb-.01,b+1.1,root+.7,floor+.01])
    comparisons['lower_root_neighborhood_delta_mm3']=delta(intersection(m['rear'].translate((d,0,0)),rootzone),intersection(old['rear'],rootzone))
    comparisons['screw_seat_deltas_mm3']=[delta(a,b) for a,b in zip(m['seats'],old['seats'])]
    comparisons['screw_deltas_mm3']=[delta(a,b) for a,b in zip(m['screws'],old['screws'])]
    for n in ['all_front_material_X_below_25_9_delta_mm3','lower_free_latch_translated_back_delta_mm3','upper_free_latch_delta_mm3','lower_root_neighborhood_delta_mm3']:
        assert comparisons[n]<.001,(n,comparisons[n])
    report=dict(status='CHECKING',print_approved=False,mechanical_baseline='ee8ec9d',coordinates='USB+Y / FRONT+Z / REAR-Z / native keys LEFT-X',
        user_confirmations=cfg,local_search=search,geometry_comparison=comparisons,
        terminal_keepout='Legacy protection key now represents FREE connector/lead keepout beside COMPLETE measured battery, not extra protector thickness. All old collision/motion tests still apply to that reserved space.')
    (OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    gate,held,accessories=evaluate(parts,mounts,m,base,kq,c,wiring_builder=wiring)
    report['full_assembly_gate']=gate
    report['inherited_fit_checks']=additional_fit_checks(parts,m,base,kq,c,m['front'],accessories)
    from g_v1_95mm_checks import extra_checks,structure_comparison
    extra=extra_checks(parts,m,mounts,base,kq,c,cfg,accessories)
    report['additional_geometry']=extra;report['structure_comparison']=structure_comparison(old,m,b0,base,c0,c)
    nominal_ok=not gate['status'].startswith('BLOCKED') and extra['pass']
    report['status']='CONDITIONAL_NOMINAL_GEOMETRY_PASS_PHYSICAL_PENDING' if nominal_ok else 'BLOCKED_NEW_GEOMETRY_OR_PATH'
    (OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    # Always provide actual failure/comparison drawings; only export shells on nominal pass.
    from g_v1_95mm_drawings import render
    render(OUT,parts,old,m,b0,base,c0,c,cfg,report)
    if not nominal_ok:
        for filename in ['front_shell.step','front_shell.stl','rear_shell.step','rear_shell.stl','assembly_light_PROXIES.step']:
            (OUT/filename).unlink(missing_ok=True)
        print('STOP: new nominal geometry/motion gate failed; no STEP/STL released',flush=True);return
    for name in ['front','rear']:
        detached=Compound(m[name].wrapped)
        export_step(detached,OUT/f'{name}_shell.step');export_stl(detached,OUT/f'{name}_shell.stl',tolerance=.015,angular_tolerance=.12)
    report['shell_export_checks']=verify_exports(OUT)
    groups=[('OfficialBoard_REAL_723',Compound(parts['ASSEMBLY'].solids())),('FrontShell_BOOT_RECT_BAT_L',m['front']),('RearShell_TWO_CLIPS',m['rear']),('Four_M2_5_CANDIDATE_SCREWS',Compound(m['screws'])),('MEASURED_ACCESSORY_ENVELOPES_AND_CONDITIONAL_WIRES_KEEP_OUT',Compound([s for _,s in accessories]))]
    scene=Compound(label='G_V1_95_60_CONDITIONAL_REVIEW',children=[Compound(s.wrapped,label=n) for n,s in groups])
    print('Export full exact board assembly and read back all solids',flush=True)
    export_step(scene,build/'assembly_complete.step')
    reread=import_step(build/'assembly_complete.step');ss=reread.solids();bb=bounds(reread)
    report['assembly_export']=dict(solids=len(ss),valid_solids=sum(s.is_valid for s in ss),bounds_mm=bb,maximum_thickness_mm=bb[5]-bb[2])
    assert len(ss)==report['assembly_export']['valid_solids']==739
    assert abs(bb[3]-bb[0]-95.6)<1e-5 and abs(bb[4]-bb[1]-77.86)<1e-5 and bb[5]-bb[2]<=12.400001
    del reread,ss;gc.collect()
    lightparts=[m['front'],m['rear'],*m['screws'],parts['PCB_BOARD'],*mounts]
    for n in ['DISPLAY','J2_USB_SIDE','TF','KEY1','KEY2','KEY3','MIC1','MX0','MX1']:
        proxy=box(bounds(parts[n]));proxy.label=n+'_PROXY_NOT_FOR_CLEARANCE';lightparts.append(proxy)
    lightparts += [s for _,s in accessories]
    export_step(Compound(children=[Compound(s.wrapped,label=s.label or f'part_{i}') for i,s in enumerate(lightparts)]),OUT/'assembly_light_PROXIES.step')
    (OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    # Self-contained precise FreeCAD Part::Feature groups, not GUI automation.
    viewer=build/'viewer';viewer.mkdir(exist_ok=True)
    for n,s in groups:export_step(Compound(s.wrapped,label=n),viewer/f'{n}.step')
    export_step(Compound(m['battery'].wrapped,label='Measured_COMPLETE_Battery'),viewer/'Battery.step')
    export_step(Compound(m['speaker'].wrapped,label='Measured_Speaker_Body'),viewer/'Speaker.step')
    shutil.copy2(ROOT/'cad/t0/view_g_v1_95mm_freecad.py',viewer/'view_g_v1_95mm_freecad.py')
    (OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status']+'; NOT PRINT APPROVED',flush=True)
if __name__=='__main__':main()
