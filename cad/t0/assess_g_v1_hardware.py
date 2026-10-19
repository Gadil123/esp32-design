"""Hardware-arrival assessment against frozen real solids; does not modify shells.

Accessory bodies are measured rectangular envelopes, NOT detailed supplier CAD.
Air probes test only free-space connectivity to the MIC exterior, NOT its port.
"""
import json, math
from pathlib import Path
from build123d import Compound, Cylinder, Align, Axis, import_step, export_step
from t0_reference import load
from reference import bounds
from model import box_between as box
from p1_checks import common_volume, clashes, translated_box_sweep
from t0_g_v1_integrated_keys import foundation, build_keys
from t0_g_v1_closure import build as close_shell
from t0_g_v1_full_gate import evaluate, additional_fit_checks
from t0_wiring import build_wiring

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/g-v1-hardware-assessment'
def read(name): return json.loads((ROOT/'cad/t0'/name).read_text())
def segment(a,b,r):
    v=[y-x for x,y in zip(a,b)];L=math.sqrt(sum(x*x for x in v))
    s=Cylinder(r,L,align=(Align.CENTER,Align.CENTER,Align.MIN))
    if v[0]: s=s.rotate(Axis.Y,90 if v[0]>0 else -90)
    elif v[1]: s=s.rotate(Axis.X,-90 if v[1]>0 else 90)
    elif v[2]<0: s=s.rotate(Axis.X,180)
    return s.translate(a)

def main():
    OUT.mkdir(parents=True,exist_ok=True);h=read('g-v1-hardware-measurements.json')
    base=read('t0-a-parameters.json');p=read('t0-g-parameters.json');base.update(p['layout_overrides'])
    kp=read('p1-parameters.json');kp.update(base['key_overrides']);q=read('t0-g-v1-boot-rect.json');c=read('t0-g-v1-closure.json')
    print('Import ORIGINAL official STEP; preserve occurrence transforms; Rz180',flush=True)
    parts,mounts,tree=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    m,p=foundation(parts,mounts,base,kp,p,q);m=build_keys(parts,m,base,q);m=close_shell(m,parts,mounts,base,c)
    frozenfront=import_step(ROOT/'deliverables/t0-g-v1-boot-rect/front_shell.step')
    frozenrear=import_step(ROOT/'deliverables/t0-g-v1/rear_shell.step')
    delta={k:(m[k]-s).volume+(s-m[k]).volume for k,s in [('front',frozenfront),('rear',frozenrear)]}
    assert max(delta.values())<.001,delta
    tol=base['volume_tolerance_mm3'];oldbattery=bounds(m['battery']);oldspeaker=bounds(m['speaker'])
    bw,bh,bt=h['battery']['body_xyz_mm'];bx,by=h['battery']['center_xy_mm'];floor=m['closure_dimensions']['rear_floor_mm']
    bz=floor+h['battery']['adhesive_candidate_mm']
    m['battery']=box([bx-bw/2,by-bh/2,bz,bx+bw/2,by+bh/2,bz+bt])
    m['adhesive']=box([bx-bw/2,by-bh/2,floor,bx+bw/2,by+bh/2,bz])
    st=h['speaker']['body_xyz_mm'][2];sf=oldspeaker[5]
    m['speaker']=box([oldspeaker[0],oldspeaker[1],sf-st,oldspeaker[3],oldspeaker[4],sf])
    m['damping']=box([oldspeaker[0],oldspeaker[1],sf-st-base['speaker']['damping_mm'],oldspeaker[3],oldspeaker[4],sf-st])
    # Legacy protection/wires retained for sensitivity checks only; never promoted
    # to measured facts. Their placement is intentionally NOT silently repaired.
    print('Re-run inherited nominal full-assembly gates with measured body envelopes',flush=True)
    gate,held,accessories=evaluate(parts,mounts,m,base,q,c)
    fit=additional_fit_checks(parts,m,base,q,c,m['front'],accessories)
    report={'status':'ASSESSMENT_ONLY_HARDWARE_EVIDENCE_REQUIRED','print_approved':False,
        'mechanical_baseline':'ee8ec9d','coordinates':h['coordinates'],
        'frozen_shell_symmetric_difference_mm3':delta,'official_physical_solids':len(parts['ASSEMBLY'].solids()),
        'battery_body_bounds_mm':bounds(m['battery']),'old_battery_body_bounds_mm':oldbattery,
        'speaker_body_bounds_mm':bounds(m['speaker']),'old_speaker_body_bounds_mm':oldspeaker,
        'inherited_gate_with_measured_body_only':gate,'inherited_fit_checks':fit,
        'limits':'All official board and frozen shell collisions use real BRep. Battery/speaker are measured body-only envelopes. Legacy protection/plug/wires are UNVERIFIED, not actual complete installation envelopes.'}
    source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    plugs,wires,wiredata=build_wiring(parts,base,m)
    obs=[('FRONT',m['front']),('REAR',m['rear']),*source,*accessories]
    mc=h['mic_candidate'];x,y=mc['front_xy_mm'];r=mc['diameter_mm']/2
    bore=segment((x,y,-.51),(x,y,.8),r)
    mic=bounds(parts['MIC1']);px=(mic[0]+mic[3])/2
    # Bare centerline probes, not manufactured ducts. Stop outside package.
    pts=[(x,y,-.8),(x,y,-7.1),(px,y,-7.1),(px,y,-6.85)]
    air=[segment(a,b,mc['air_probe_radius_mm']) for a,b in zip(pts,pts[1:])]
    air_obstacles=[(n,s) for n,s in obs if n not in ['FRONT']]+[('FRONT',m['front']-bore)]
    micprobe=segment((px,y,-5.51),(px,y,-3.89),.3)
    report['microphone']={'package_bounds_mm':mic,'package_faces':len(parts['MIC1'].faces()),
        'package_geom_types':[str(f.geom_type) for f in parts['MIC1'].faces()],
        'candidate':mc,'candidate_bore_intersections':clashes(bore,[(n,s) for n,s in obs if n!='FRONT'],tol),
        'candidate_front_cut_volume_mm3':common_volume(bore,m['front']),
        'air_probe_points_mm':pts,'air_probe_hits':[clashes(s,air_obstacles,tol) for s in air],
        'pcb_center_probe_volume_mm3':common_volume(micprobe,parts['PCB_BOARD']),
        'pcb_center_full_cylinder_volume_mm3':math.pi*.3**2*1.6,
        'port_direction':'UNVERIFIED','pcb_acoustic_hole':'UNVERIFIED; center probe only is not an exhaustive hole search',
        'acoustic_performance':'UNVERIFIED; geometric access to package exterior is not connection to actual acoustic port',
        'finger_occlusion':'UNVERIFIED: right of glass near mid-height, right thumb/palm may cover it'}
    frontinner=m['dimensions']['front_z_mm']-base['bay_front_panel_mm'];reserve=h['battery']['swelling_candidate_mm']
    report['battery_z_chain']={'rear_outer_mm':m['closure_dimensions']['rear_bottom_mm'],'rear_panel_mm':c['rear_panel_mm'],
        'rear_floor_mm':floor,'adhesive_candidate_mm':h['battery']['adhesive_candidate_mm'],'body_mm':bt,
        'body_front_mm':bz+bt,'front_inner_mm':frontinner,'geometric_headroom_mm':frontinner-bz-bt,
        'swelling_candidate_mm':reserve,'remaining_after_candidate_swelling_mm':frontinner-bz-bt-reserve,
        'protection_and_wires_Z_mm':None,'complete_package_fit':'UNVERIFIED',
        'swelling_probe_hits':clashes(box([bx-bw/2,by-bh/2,bz+bt,bx+bw/2,by+bh/2,bz+bt+reserve]),[(n,s) for n,s in obs if n not in ['battery','adhesive']],tol)}
    report['wiring']={}
    for name,row in wiredata.items():
        pts0=row['wire_centerline_polyline_before_fillets_mm'][0]
        row['sharp_polyline_length_mm']=sum(math.dist(a,b) for a,b in zip(pts0,pts0[1:]))
        # Same FilletPolyline as actual swept envelope, not Manhattan estimate.
        from build123d import FilletPolyline
        row['filleted_centerline_length_mm']=FilletPolyline(*pts0,radius=base['wire_bend_radius_mm']).length
        row['approx_40mm_speaker_lead_sufficient_for_this_route']=row['filleted_centerline_length_mm']<=40 if name=='MX0' else None
        report['wiring'][name]=row
    report['width']={'old_outer_xyz_mm':[99.6,77.86,max(.7,bounds(m['front'])[5])-min(bounds(m['front'])[2],bounds(m['rear'])[2])],
        'body_only_X_saving_mm':34-bw,'body_only_Y_saving_mm':50-bh,
        'proposed_final_outer_xyz_mm':None,'approved_width_reduction_mm':0,
        'reason':'Existing 30mm speaker, latch receiver/release lane, unknown battery terminal envelope and inadequate legacy speaker route preclude committing a narrower production shell.'}
    report['speaker_support']={'rear_pad_to_new_damping_gap_mm':bounds(m['damping'])[2]-max(bounds(s)[5] for s in m['speaker_pads']),
        'new_foam_seal':'not designed; real rim, port and adhesive thickness required',
        'isolation':'Existing fence is interrupted at wire exit; no complete PCB/bay partition. No sealed enclosure or acoustic isolation proved.'}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    # Explicitly assessment, not revised printable shells/full validated device.
    scene=Compound(children=[Compound(s.wrapped,label=n) for n,s in [('OfficialBoard_REAL_723',Compound(parts['ASSEMBLY'].solids())),('FrozenFront_NO_MIC_HOLE',m['front']),('FrozenRear',m['rear']),('Battery_MEASURED_BODY_ONLY',m['battery']),('Speaker_MEASURED_BODY_ONLY',m['speaker'])]])
    build=ROOT/'build/g-v1-hardware-assessment';build.mkdir(parents=True,exist_ok=True)
    export_step(scene,build/'assessment_NOT_RELEASED.step')
    exported=import_step(build/'assessment_NOT_RELEASED.step')
    validation=dict(solids=len(exported.solids()),valid_solids=sum(s.is_valid for s in exported.solids()),
        bounds_mm=bounds(exported),status='ASSESSMENT_ONLY_NOT_RELEASED',
        includes='723 real board solids + frozen front + frozen rear + battery body + speaker body. NOT full harness, protection, fastener or manufacturing assembly.')
    assert validation['solids']==validation['valid_solids']==727
    (OUT/'assessment_export.json').write_text(json.dumps(validation,indent=2)+'\n')
    del exported
    from g_v1_hardware_drawings import render
    render(OUT,parts,m,h,report,bore,air)
    print('ASSESSMENT COMPLETE; actual MIC port/full accessory package unresolved; shells unchanged',flush=True)
if __name__=='__main__': main()
