#!/usr/bin/env python3
"""One E assembly gate, then one complete shell; no mechanism search or print approval."""
import json,shutil,zipfile
from pathlib import Path
from build123d import Compound,Color,export_step,export_stl,export_gltf,import_step,Axis,extrude
from reference import bounds,to_pocket,compare_recorded
from t0_reference import load
from t0_model import build as build_a
from t0_d_study import build as build_d
from t0_e_model import parameters,finish
from t0_e_gate import evaluate,axial_sweep,source_clashes
from t0_wiring import build_wiring
from t0_checks import cap_axial_sweep
from p1_checks import clashes,common_volume,intersection,translated_box_sweep,cap_components
from check_exports import verify_exports
from model import box_between as box

ROOT=Path(__file__).resolve().parents[2]


def run(parts,mounts,p,base,kp,dp,out,recorded=None):
    base=parameters(base,p);dp={**dp,'maximum_thickness_mm':p['target_thickness_mm'],'nest_axial_clearance_mm':p['nest_axial_clearance_mm']}
    m=build_a(parts,mounts,base,kp);d=build_d(parts,mounts,dp,base)
    print('E: stage 1 complete-board continuous insertion / three actual PCB stop faces',flush=True)
    gate,released=evaluate(parts,mounts,m,d['seats'],base,p,kp)
    report={'stage':'E','PCB_assembly_gate':gate,'print_approved':False,'manufacturing_status':'UNVERIFIED','full_E_completed':False,
            'parameters':p,'inherited_A_key_parameters':kp,'source_solids':len(parts['ASSEMBLY'].solids())}
    if recorded is not None:report['original_bounds_roundtrip']=recorded
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if gate['status']!='NOMINAL_ASSEMBLY_GATE_PASS':
        export_step(Compound([parts['DISPLAY'],parts['PCB_BOARD'],*mounts,m['front'],*d['seats']]),out/'E_GATE_BLOCKED.step')
        raise RuntimeError('E insertion/contact gate failed; no full enclosure generated; see checks.json')
    print('E gate nominal PASS: build ONE full enclosure with D-style short teeth',flush=True)
    m=finish(parts,mounts,m,base,p,dp);plugs,wires,wiredata=build_wiring(parts,base,m)
    source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    rigid=[('front',m['front']),('rear',m['rear']),*m['caps'].items()]
    accessories=[(k,m[k]) for k in ['battery','speaker','protection','adhesive','foam','damping']]
    accessories+=list(plugs.items())+[(f'{k}_wire_{i}',s) for k,ss in wires.items() for i,s in enumerate(ss)]
    installed=rigid+accessories;tol=base['volume_tolerance_mm3']
    checks={}
    print('E: full source / installed-part and pairwise interference checks',flush=True)
    for k,s in installed:
        checks[k]={'valid_single_solid':s.is_valid and len(s.solids())==1,'source_collisions':source_clashes(s,parts,source,tol)}
    pair_hits=[]
    for i,(k,s) in enumerate(installed):
        for name,t in installed[i+1:]:
            v=common_volume(s,t)
            if v>tol:pair_hits.append({'a':k,'b':name,'volume_mm3':v})
    print('E: recheck PCB path in FINAL shell and local external release channels',flush=True)
    final_gate,final_released=evaluate(parts,mounts,m,d['seats'],base,p,kp)
    # No assumed simultaneous snap displacement proves an opening sequence.
    # Check each external pick and local retained/released states in the actual shell.
    fixed_front=m['front'];fixed_rear=m['rear']
    for pair in m['short_pairs']:fixed_rear=fixed_rear-pair['tongue']
    teeth=[]
    for i,pair in enumerate(m['short_pairs']):
        rel=tuple(a*dp['release_deflection_mm'] for a in pair['inward']);free=pair['tongue']
        after=free.translate(rel)
        approach=clashes(translated_box_sweep(after,(0,0,-20)),[('FRONT',fixed_front),*source,*accessories],tol)
        withdrawal=clashes(translated_box_sweep(after,(0,0,-dp['release_pull_mm'])),[('FRONT',fixed_front)],tol)
        tooth_obstacles=[('FRONT',fixed_front),('REAR_without_compliant_teeth',fixed_rear),*source,*accessories]
        pick_hits=clashes(pair['pick'],tooth_obstacles,tol)
        teeth.append({'index':i,'site':pair['site'],'hold_pull_0_3_mm3':common_volume(free.translate((0,0,-.3)),fixed_front),
            'external_pick_collisions':pick_hits,'released_approach_sweep_collisions':approach,'released_withdrawal_sweep_collisions':withdrawal,
            'relaxed_after_local_2_8mm_gap_volume_mm3':common_volume(free.translate((0,0,-dp['release_pull_mm'])),fixed_front),
            'actual_elasticity':'UNVERIFIED; local 0.5mm free-end translation is a clearance proxy, not physical bending',
            'approximate_strain':1.5*dp['tongue_thickness_mm']*dp['release_deflection_mm']/(dp['tooth_tip_top_z_mm']-m['dimensions']['rear_inside_z_mm'])**2})
    outer_stops=[common_volume(q['front'],q['fixed_rear'].translate((0,0,.05))) for q in m['short_pairs']]
    cups_before_compression=[source_clashes(s.translate((0,0,.05)),parts,source,tol) for s in m['nests']]
    # The NONCOMPLIANT rear structure must traverse a continuous, independent path.
    # Sweep each original/front obstacle toward the rear, preserving hollow shell
    # geometry; sample actual rear solids as a secondary check, NOT a proof alone.
    closure=[]
    for dz in [-20,-8,-3,-1,0]:
        hits=clashes(fixed_rear.translate((0,0,dz)),[('FRONT',m['front']),*source,*m['caps'].items(),*[(k,s) for k,s in accessories if not k.startswith(('battery','protection','adhesive'))]],tol)
        closure.append({'REAR_offset_z_mm':dz,'noncompliant_rear_collisions':hits})
    closure_obstacles=[('FRONT',m['front']),*source,*m['caps'].items(),*[(k,s) for k,s in accessories if k not in ['battery','protection','adhesive']]]
    continuous_rear=[]
    # The leading faces of this rear part have constant nonpositive Z normals
    # (planar floor/steps and lower outer fillets). Their extrusion plus the
    # original part is its downward translation envelope, retaining every recess.
    for i,f in enumerate(fixed_rear.faces()):
        if f.normal_at().Z<-.0001:
            prism=extrude(f,amount=20,dir=(0,0,-1))
            hits=clashes(prism,closure_obstacles,tol)
            if hits:continuous_rear.append({'leading_face':i,'collisions':hits})
    moving_accessories=[]
    for k in ['battery','protection','adhesive']:
        moving_accessories.append({'part':k,'continuous_sweep_collisions':clashes(translated_box_sweep(m[k],(0,0,-20)),closure_obstacles,tol)})
    # Interface probes and cap motion remain the old A geometry; no new travel claim.
    usb=clashes(m['usbprobe'],[('FRONT',m['front']),('REAR',m['rear']),*source],tol)
    tb=bounds(parts['TF']);yc=(tb[1]+tb[4])/2;zc=(tb[2]+tb[5])/2
    tf=box([base['outer_x_min_mm']-20,yc-5.5,zc-.5,tb[0],yc+5.5,zc+.5])
    tfhits=clashes(tf,[('FRONT',m['front']),('REAR',m['rear']),*source],tol)
    caps={}
    for key,cap in m['caps'].items():
        caps[key]=[hit for piece in cap_components(cap,m['key_data'][key],kp) for hit in clashes(cap_axial_sweep(piece,m['key_data'][key],kp),rigid[:2],tol)]
    bb={k:bounds(s) for k,s in [('official_complete',parts['ASSEMBLY']),*installed]}
    lo=min(b[2] for b in bb.values());hi=max(b[5] for b in bb.values())
    report.update(full_E_completed=True,final_full_shell_PCB_gate=final_gate,nominal_installed=checks,pair_interferences=pair_hits,
        short_shell_teeth=teeth,peripheral_closure_load_path={'edge_stop_overlap_at_0_05mm_overclosure_mm3':outer_stops,
            'nests_at_0_05mm_overclosure_source_collisions':cups_before_compression,'nominal_nest_axial_relief_mm':p['nest_axial_clearance_mm'],
            'note':'Outer walls stop at nominal closure; cups still have .05mm axial relief in this .05mm diagnostic. PCB is not the shell closure hard stop. Actual tolerance stack unverified.'},
        rear_nest_geometry=m['nest_rows'],noncompliant_REAR_closure_samples=closure,
        continuous_REAR_leading_face_sweep_collisions=continuous_rear,REAR_attached_accessory_continuous_sweeps=moving_accessories,
        USB_independent_plug_collisions=usb,TF_external_approach_collisions=tfhits,
        existing_caps_centered_candidate_motion=caps,complete_installed_bounds_mm=bb,
        maximum_thickness={'minimum_z_mm':lo,'maximum_z_mm':hi,'actual_mm':hi-lo,'included':'all official solids, both full shells, caps, provisional accessories, layers, plugs and wire bundles; no external feet/fasteners omitted'},
        wiring=wiredata,remaining_gates=['MJF PA12 elasticity, snap release force and full-cover sequential flexure/creep','holding three root-fixed PCB clips open in actual assembly; installation tools not qualified','zero nominal PCB axial float, 0.2mm stop/LCD gap and shallow-nest fits/tolerances; no manufactured clamp/preload qualification','switch actual travel/frame/contact/return; no electronics added','MIC1 port/recording, actual MX plugs/polarity/lead exit, TF seat/eject','battery/speaker/protection provisional dimensions and 0.23mm side gap'],
        opening_sequence={'order':[q['site'] for q in m['short_pairs']],
            'action':'From the bottom window insert a .35mm plastic pick, hold tooth inward .5mm, support local gap >=2.8mm by hand; work right lower -> right upper -> top -> left. Keep earlier gaps open; support both halves and remove rear without pulling leads. Reverse for closure.',
            'status':'LOCAL_TOOL_AND_CLEARANCE_CHECKS_ONLY_FULL_FLEXIBLE_COVER_SEQUENCE_UNVERIFIED','not_a_simultaneous_release_claim':True},
        version_preservation='A/B/C/D deliverables unchanged; software untouched')
    failures=[]
    if any(not v['valid_single_solid'] or v['source_collisions'] for v in checks.values()):failures.append('installed source validity/clash')
    if pair_hits:failures.append('installed pair clash')
    if final_gate['status']!='NOMINAL_ASSEMBLY_GATE_PASS':failures.append('final shell PCB assembly gate')
    if any(q['external_pick_collisions'] or q['released_approach_sweep_collisions'] or q['released_withdrawal_sweep_collisions'] or q['hold_pull_0_3_mm3']<=tol or q['relaxed_after_local_2_8mm_gap_volume_mm3']>tol for q in teeth):failures.append('short tooth local clearance')
    if any(q['noncompliant_rear_collisions'] for q in closure):failures.append('rear closure samples')
    if continuous_rear or any(q['continuous_sweep_collisions'] for q in moving_accessories):failures.append('continuous rear approach')
    if any(v<=tol for v in outer_stops) or any(cups_before_compression):failures.append('independent peripheral closure load path')
    if usb or tfhits or any(caps.values()):failures.append('native interfaces')
    if hi-lo>12.40001:failures.append('12.4mm maximum thickness')
    report['geometry_status']='PASS' if not failures else 'FAIL';report['geometry_failures']=failures
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if failures:raise RuntimeError(f'Full E nominal checks: {failures}; no qualified exports')
    print('E: export full original-geometry assembly and independent shell solids',flush=True)
    manufactured={'front_shell':m['front'],'rear_shell':m['rear'],**{k.lower()+'_cap':s for k,s in m['caps'].items()}}
    for name,s in manufactured.items():
        export_step(s,out/f'{name}.step');export_stl(s,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    report['export_checks']=verify_exports(out,manufactured)
    styled=[]
    for k,s in installed:
        s.label=k+('_UNVERIFIED' if k not in ['front','rear'] else '_T0_E');s.color=Color('#526a80' if k=='front' else '#dba64d' if k=='rear' else '#788a82');styled.append(s)
    full=Compound(label='T0_E_COMPLETE_12_4mm_REVIEW_NOT_PRINT_APPROVED',children=[parts['ASSEMBLY'],*styled])
    export_step(full,out/'assembly_complete_12_4mm.step')
    reread=import_step(out/'assembly_complete_12_4mm.step');b=bounds(reread);count=len(reread.solids())
    expected=len(source)+sum(len(s.solids()) for s in styled)
    report['complete_STEP_roundtrip']={'solids':count,'expected':expected,'valid_solids':sum(s.is_valid for s in reread.solids()),'bounds_mm':b,'thickness_mm':b[5]-b[2]}
    assert count==expected==report['complete_STEP_roundtrip']['valid_solids'] and b[5]-b[2]<=12.40001
    refs=[parts['PCB_BOARD'],*mounts,parts['TF'],parts['MX0'],parts['MX1']]
    for k in ['DISPLAY','J2_USB_SIDE','KEY1','KEY2','KEY3','MIC1']:
        proxy=box(bounds(parts[k]));proxy.label=k+'_REFERENCE_ENVELOPE';refs.append(proxy)
    light=Compound(label='T0_E_LIGHT_REFERENCE_ENVELOPES_NOT_FOR_CLEARANCE',children=[*refs,*styled])
    export_step(light,out/'assembly_light.step');export_gltf(light,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    from t0_e_drawings import render
    render(out,parts,mounts,m,released,base,p,report)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(out/'t0-e-review-complete.zip','w',zipfile.ZIP_DEFLATED) as z:
        z.write(out/'assembly_complete_12_4mm.step','assembly_complete_12_4mm.step');z.write(out/'checks.json','checks.json')
    return report


def main():
    out=ROOT/'build/t0-e';out.mkdir(parents=True,exist_ok=True)
    p=json.loads((ROOT/'cad/t0/t0-e-parameters.json').read_text());base=json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text());kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text());kp.update(base['key_overrides'])
    dp=json.loads((ROOT/'cad/t0/t0-d-parameters.json').read_text())
    print('E: import ORIGINAL vendor STEP and proper occurrence transforms',flush=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    recorded=compare_recorded({k:to_pocket(s) for k,s in parts.items()},ROOT/'data/step_component_bounds.csv',.05)
    report=run(parts,mounts,p,base,kp,dp,out,recorded)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    dest=ROOT/'deliverables/t0-e';dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.stl','.glb','.png','.json'] and f.name!='assembly_complete_12_4mm.step':shutil.copy2(f,dest/f.name)
    print('E nominal geometry and exports complete; functional/material gates remain open, no print approval',flush=True)


if __name__=='__main__':main()
