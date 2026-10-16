#!/usr/bin/env python3
"""G assembly gates first, then review exports. No changes to E or other stages."""
import json,shutil,zipfile
from pathlib import Path
from build123d import Compound,Color,export_step,export_stl,export_gltf,import_step
from t0_reference import load
from reference import bounds,to_pocket,compare_recorded
from t0_g_model import build,finish
from t0_g_gate import evaluate
from check_exports import verify_exports
from model import box_between as box

ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'build/t0-g';out.mkdir(parents=True,exist_ok=True)
    p=json.loads((ROOT/'cad/t0/t0-g-parameters.json').read_text());assert p['maximum_thickness_mm']<=12.9
    base=json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text());base.update(p['layout_overrides'])
    kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text());kp.update(base['key_overrides'])
    print('G: import ORIGINAL STEP, preserve all occurrences, proper Rz180',flush=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    assert len(parts['ASSEMBLY'].solids())==723
    report=dict(stage='G',print_approved=False,material_functional_acceptance='PENDING',full_G_completed=False,parameters=p,
                volume_tolerance_mm3=base['volume_tolerance_mm3'],
                assembly_tolerance_status='BLOCKED_PCB_XY_LOCATION: permitted screw play can consume cap/glass clearance; manual alignment method and physical operation unverified',
                nominal_path_is_robust_to_permitted_screw_play=False,
                source_bounds_comparison=compare_recorded({k:to_pocket(s) for k,s in parts.items()},ROOT/'data/step_component_bounds.csv',.05))
    m=build(parts,mounts,base,kp,p)
    print('G: gate complete board, four rear M2.5 load paths, cap staging and right bay',flush=True)
    gate,_,_,_=evaluate(parts,mounts,m,base,kp,p)
    report['foundation_gate']=gate
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if gate['status']!='NOMINAL_GEOMETRY_GATE_PASS':raise RuntimeError('G foundation STOP; see checks.json; do not finish shell')
    print('G: foundation nominal PASS; four blind-groove tongues and independent shoulders',flush=True)
    m=finish(m,base,p)
    gate,held,accessories,parked=evaluate(parts,mounts,m,base,kp,p,True);report['complete_assembly_gate']=gate
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if gate['status']!='NOMINAL_GEOMETRY_GATE_PASS':raise RuntimeError('G hidden latch/assembly STOP; see checks.json')
    print('G: gates nominal PASS; export one full shell and verify exported geometry',flush=True)
    manufactured=[('front_shell',m['front']),('rear_shell',m['rear']),*[(k.lower()+'_cap',s) for k,s in m['caps'].items()]]
    for name,s in manufactured:
        assert s.is_valid and len(s.solids())==1
        export_step(s,out/f'{name}.step');export_stl(s,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    report['part_export_checks']=verify_exports(out,[k for k,_ in manufactured])
    export_step(Compound(m['screws']),out/'four_NBK_SSH_M2_5_4_envelopes.step')
    screw_export=import_step(out/'four_NBK_SSH_M2_5_4_envelopes.step')
    assert len(screw_export.solids())==4 and all(s.is_valid for s in screw_export.solids())
    report['screw_export']=dict(solids=4,valid=True,model='Purchased-part outer envelopes; not detailed male threads/socket machining')
    styled=[]
    for name,s in [*manufactured,*[(f'screw_{i}',s) for i,s in enumerate(m['screws'])],*accessories]:
        s.label='G_'+name;s.color=Color(.16,.18,.20) if name in ['front_shell','rear_shell'] or '_cap' in name else Color(.4,.43,.46);styled.append(s)
    complete=Compound(label='T0_G_FULL_OFFICIAL_REFERENCE_REVIEW_ONLY',children=[parts['ASSEMBLY'],*styled])
    expected=len(complete.solids());export_step(complete,out/'assembly_complete_12_9mm.step')
    reread=import_step(out/'assembly_complete_12_9mm.step');bb=bounds(reread)
    report['complete_STEP_roundtrip']=dict(expected_solids=expected,solids=len(reread.solids()),valid_solids=sum(s.is_valid for s in reread.solids()),bounds_mm=bb,maximum_thickness_mm=bb[5]-bb[2])
    assert expected==len(reread.solids())==report['complete_STEP_roundtrip']['valid_solids'] and bb[5]-bb[2]<=12.900001
    # Outward cap staging is transient but must also be counted in X/Z checks.
    report['complete_STEP_roundtrip']['parked_cap_max_width_mm']=gate['complete_bounds']['maximum_width_including_parked_caps_mm']
    refs=[parts['PCB_BOARD'],*mounts,parts['TF'],parts['MX0'],parts['MX1']]
    for k in ['DISPLAY','J2_USB_SIDE','KEY1','KEY2','KEY3','MIC1']:
        proxy=box(bounds(parts[k]));proxy.label=k+'_REFERENCE_ENVELOPE';refs.append(proxy)
    light=Compound(label='T0_G_LIGHT_NOT_FOR_CLEARANCE',children=[*refs,*styled])
    export_step(light,out/'assembly_light.step');export_gltf(light,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    report['full_G_completed']=True
    report['status']='G full nominal assembly CAD complete; geometry reviewed; material/functional acceptance pending'
    from t0_g_drawings import render
    render(out,parts,mounts,m,held,accessories,parked,base,kp,p,report)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(out/'t0-g-review-complete.zip','w',zipfile.ZIP_DEFLATED) as z:
        z.write(out/'assembly_complete_12_9mm.step','assembly_complete_12_9mm.step');z.write(out/'checks.json','checks.json')
    dest=ROOT/'deliverables/t0-g';dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.stl','.glb','.png','.json'] and f.name not in ['assembly_complete_12_9mm.step','dev-checks.json']:shutil.copy2(f,dest/f.name)
    print(report['status']+'; NOT PRINT APPROVED',flush=True)


if __name__=='__main__':main()
