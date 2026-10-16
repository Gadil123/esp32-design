#!/usr/bin/env python3
"""Small CAD study: preserved B vs guided A and optional 1.2mm head. Not qualification."""
import json
from pathlib import Path
from build123d import export_step,export_stl
from t0_reference import load
from t0_model import build
from t0_key_contact import evaluate
from t0_checks import cap_axial_sweep
from p1_manufacturing import tolerance_budget,budget_pass
from p1_checks import cap_components,translated_box_sweep,clashes
from t0_revision_drawings import render_revision
ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'build/t0-key-study';out.mkdir(parents=True,exist_ok=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    base=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text());report={'print_approved':False,'cases':{}}
    for name,filename,override in [('B_1_9mm','t0-parameters.json',{}),('A_1_9mm','t0-a-parameters.json',{}),('A_1_2mm_candidate','t0-a-parameters.json',{'key_head_depth_mm':.6,'key_head_motion_gap_mm':.6})]:
        p=json.loads((ROOT/'cad/t0'/filename).read_text());p['target_thickness_mm']=12.4
        kp={**base,**p.get('key_overrides',{}),**override};m=build(parts,mounts,p,kp)
        case={'contact':evaluate(parts,m,p,kp),'parameters':kp,'assembly_from_REAR':{},'centered_shell_motion':{},
              'head_end_gap_mm':kp['key_head_motion_gap_mm']-kp['key_cap_design_motion_mm'],
              'status':'UNVERIFIED','actual_switch_travel_mm':None}
        for key,cap in m['caps'].items():
            pieces=cap_components(cap,m['key_data'][key],kp)
            shift=.5 if key=='KEY3' and p.get('variant')=='A' else 0
            case['assembly_from_REAR'][key]=[hit for s in pieces for hit in clashes(translated_box_sweep(s.translate((shift,0,0)),[0,0,-15]),[('fixed_front_guide',m['front'])],p['volume_tolerance_mm3'])]
            case['centered_shell_motion'][key]=[hit for s in pieces for hit in clashes(cap_axial_sweep(s,m['key_data'][key],kp),[('front',m['front']),('rear',m['rear'])],p['volume_tolerance_mm3'])]
            if name=='A_1_2mm_candidate':
                export_step(cap,out/f'{key.lower()}_low_candidate.step');export_stl(cap,out/f'{key.lower()}_low_candidate.stl',tolerance=.015,angular_tolerance=.12)
        if p.get('variant')=='A':
            case['RESET_final_slide_before_PCB']=[hit for part in cap_components(m['caps']['KEY3'],m['key_data']['KEY3'],kp) for hit in clashes(cap_axial_sweep(part,m['key_data']['KEY3'],{**kp,'key_cap_design_motion_mm':.5}),[('fixed_front_guide',m['front'])],p['volume_tolerance_mm3'])]
        case['RESET_assembly_note']='Before PCB installation: hold RESET +0.5mm X, insert from REAR; slide -X into needle entry. Final return path uses same centered motion screen, not a switch-travel assumption.' if p.get('variant')=='A' else 'Original B rear insertion; exterior rectangle risk retained.'
        profile=json.loads((ROOT/'cad/t0/p1-manufacturing.json').read_text())
        case['conditional_tolerance_budget']=tolerance_budget(kp,profile)
        case['conditional_process_screen_pass']=budget_pass(case['conditional_tolerance_budget'],profile) and kp['key_guide_clearance_mm']>=profile['published_sla_reference']['moving_gap_nominal_min_mm']
        report['cases'][name]=case
        if name in ['B_1_9mm','A_1_2mm_candidate']:
            folder=out/name;folder.mkdir(exist_ok=True);render_revision(folder,parts,m,p)
    (out/'key_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Key study complete: CAD motion/installation screens recorded; all functional/process gates remain unverified.',flush=True)

if __name__=='__main__':main()
