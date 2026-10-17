#!/usr/bin/env python3
"""One command: task23 local gate -> complete G-V1 -> independent exports."""
import json,shutil,zipfile
from pathlib import Path
from build123d import Compound,Color,export_step,export_stl,export_gltf,import_step
from generate_t0_g_v1_integrated import main as local_gate
from t0_g_v1_closure import build
from t0_g_v1_full_gate import evaluate,additional_fit_checks
from check_exports import verify_exports
from reference import bounds
from model import box_between as box

ROOT=Path(__file__).resolve().parents[2]


def main():
    parts,mounts,m,base,kp,p,kq,local=local_gate()
    if local['status']!='LOCAL_NOMINAL_GATE_PASS_PHYSICAL_PENDING':
        print('STOP: local gate failed; see deliverables/t0-g-v1-integrated/checks.json',flush=True);return
    q=json.loads((ROOT/'cad/t0/t0-g-v1-closure.json').read_text())
    out=ROOT/'build/t0-g-v1-full';out.mkdir(exist_ok=True)
    m=build(m,parts,mounts,base,q)
    gate,held,accessories=evaluate(parts,mounts,m,base,kq,q)
    report=dict(stage='G-V1 integrated PA12 sidekeys',print_approved=False,full_G_V1_completed=False,
                local_gate=local,closure_parameters=q,full_assembly_gate=gate,
                physical_function='UNVERIFIED_UNTIL_HARDWARE',MIC='MIC_AUDIO_PATH_BLOCKED_UNTIL_HARDWARE')
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if gate['status']!='NOMINAL_FULL_ASSEMBLY_GATE_PASS_PHYSICAL_PENDING':
        print('STOP: full assembly gate failed; see build/t0-g-v1-full/checks.json',flush=True);return
    print('G-V1: nominal gates PASS; export complete original-board assembly',flush=True)
    manufactured=[('front_shell',m['front']),('rear_shell',m['rear'])]
    for name,s in manufactured:
        assert s.is_valid and len(s.solids())==1
        export_step(s,out/f'{name}.step');export_stl(s,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    report['part_export_checks']=verify_exports(out,[name for name,_ in manufactured])
    report.update(additional_fit_checks(parts,m,base,kq,q,import_step(out/'front_shell.step'),accessories))
    styled=[]
    for name,s in [*manufactured,*[(f'M2_5_{i}',s) for i,s in enumerate(m['screws'])],*accessories]:
        s.label='G_V1_'+name;s.color=Color(.2,.25,.28) if name=='front_shell' else Color(.43,.47,.5);styled.append(s)
    complete=Compound(label='G_V1_FULL_OFFICIAL_REFERENCE_REVIEW_ONLY',children=[parts['ASSEMBLY'],*styled])
    expected=len(complete.solids());export_step(complete,out/'assembly_complete_12_4mm.step')
    imported=import_step(out/'assembly_complete_12_4mm.step');ss=list(imported.solids());bb=bounds(imported)
    valid=sum(s.is_valid for s in ss)
    assert len(ss)==valid==expected and bb[5]-bb[2]<=12.400001
    report['complete_STEP_roundtrip']=dict(solids=len(ss),valid_solids=valid,bounds_mm=bb,maximum_thickness_mm=bb[5]-bb[2],
        maximum_with_retained_rear_play_mm=gate['maximum_with_retained_rear_play_mm'])
    refs=[parts['PCB_BOARD'],*mounts]
    for key in ['DISPLAY','J2_USB_SIDE','KEY1','KEY2','KEY3','TF','MIC1','MX0','MX1']:
        proxy=box(bounds(parts[key]));proxy.label=key+'_ENVELOPE_NOT_FOR_CLEARANCE';refs.append(proxy)
    light=Compound(label='G_V1_LIGHT_REFERENCE_NOT_FOR_CLEARANCE',children=[*refs,*styled])
    export_step(light,out/'assembly_light.step');export_gltf(light,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    from t0_g_v1_integrated_drawings import render as render_keys
    render_keys(out,parts,m,base,kq,local)
    from t0_g_v1_full_drawings import render
    render(out,parts,mounts,m,base,kq,q,report,held,accessories)
    finalize(out,report)


def finalize(out,report):
    """Publish the checked geometry with explicit conditional-fit status."""
    report['full_G_V1_completed']=True
    blocked=report.get('combined_register_bore_print_reach',{}).get('status')=='BLOCKED_CONDITIONAL_PRINT_FIT'
    report['status']='NOMINAL_CAD_COMPLETE / '+('BLOCKED_CONDITIONAL_PRINT_FIT' if blocked else 'MATERIAL_AND_PHYSICAL_FIT_PENDING')
    report['completion_scope']='Nominal CAD and modeled assembly paths only; not manufactured switch function or print approval.'
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    dest=ROOT/'deliverables/t0-g-v1';dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.stl','.glb','.png','.json'] and f.name not in ['assembly_complete_12_4mm.step','dev-checks.json'] and '_dev' not in f.name:
            shutil.copy2(f,dest/f.name)
    with zipfile.ZipFile(out/'t0-g-v1-review-complete.zip','w',zipfile.ZIP_DEFLATED) as z:
        z.write(out/'assembly_complete_12_4mm.step','assembly_complete_12_4mm.step');z.write(out/'checks.json','checks.json')
    print(report['status']+'; NOT PRINT APPROVED',flush=True)


if __name__=='__main__':main()
