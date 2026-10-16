#!/usr/bin/env python3
"""Rebuild T0 from the original STEP. Nominal geometry is not print approval."""
import argparse,json,subprocess,platform,zipfile
from pathlib import Path
from importlib.metadata import version
from build123d import Compound,Color,export_step,export_stl,export_gltf,import_step
from reference import bounds,to_pocket,compare_recorded,hole_axes
from t0_reference import load
from t0_model import build
from t0_wiring import build_wiring
from t0_checks import validate
from p1_manufacturing import validate_manufacturing
from check_exports import verify_exports
from model import box_between
from t0_preview import render_all
ROOT=Path(__file__).resolve().parents[2]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--reference',type=Path,default=ROOT.parent/'ESP32-C5-Touch-LCD-2.8');ap.add_argument('--output',type=Path,default=ROOT/'build/t0');ap.add_argument('--parameters',type=Path,default=ROOT/'cad/t0/t0-parameters.json');ap.add_argument('--thickness',type=float);a=ap.parse_args()
    out=a.output;out.mkdir(parents=True,exist_ok=True);(out/'checks.json').unlink(missing_ok=True)
    p=json.loads(a.parameters.read_text());
    if a.thickness is not None:p['target_thickness_mm']=a.thickness
    kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text())
    print('T0: import complete original STEP and occurrence placements',flush=True)
    path=a.reference/'dimensions/ESP32-C5-Touch-LCD-2.8.stp';parts,mounts,tree=load(path)
    original={k:to_pocket(s) for k,s in parts.items()};recorded=compare_recorded(original,ROOT/'data/step_component_bounds.csv',.05)
    assert parts['J2_USB_SIDE'].center().Y>30 and parts['KEY1'].center().X<0
    print('T0: construct flush shell, separate PCB retainers and side-bay connection',flush=True)
    m=build(parts,mounts,p,kp);plugs,wires,wire_data=build_wiring(parts,p,m)
    checks,acoustic,tfprobe=validate(parts,m,p,kp,plugs,wires)
    kchecks,keyreport=validate_manufacturing(m,kp,json.loads((ROOT/'cad/t0/p1-manufacturing.json').read_text()));checks.update(kchecks)
    source_solids=parts['ASSEMBLY'].solids();source_valid=sum(s.is_valid for s in source_solids)
    checks['valid_complete_official_solids']={'pass':source_valid==len(source_solids),'valid':source_valid,'count':len(source_solids)}
    b=bounds(parts['ASSEMBLY']);boarddepth=b[5]-b[2];panel=p['rear_panel_mm'];minimum=boarddepth+panel+p['minimum_rigid_gap_mm']
    alt_floor=b[5]-p['exploration_thickness_mm']+panel;altgap=b[2]-alt_floor
    comparison={f"{p['target_thickness_mm']:g}mm":{'nominal_max_thickness_mm':checks['maximum_complete_assembly_thickness']['actual_maximum_mm'],
        'rigid_geometry_pass':all(v['pass'] for v in checks.values()),'complete_real_mating_and_acoustics_proven':False},
        '11_5mm':{'status':'FAIL' if altgap<p['minimum_rigid_gap_mm'] else 'NEEDS_FURTHER_CHECKS',
        'rear_floor_z_mm':alt_floor,'official_lowest_z_mm':b[2],'minimum_gap_mm':p['minimum_rigid_gap_mm'],'actual_gap_mm':altgap,
        'reason':'necessary whole-board/rear-floor clearance fails before detailed assembly; no solids omitted'},
        'nominal_board_plus_panel_lower_bound_mm':minimum,
        'conditional_outsource_budget':{'board_error_mm':.2,'rear_inside_face_error_mm':.2,'assembly_float_mm':.1,
        'required_depth_mm':minimum+.5,'candidate_remaining_clearance_mm':b[2]-m['dimensions']['rear_inside_z_mm']-.5,
        'supplier_and_board_tolerances_confirmed':False},
        'width':{'initial_mm':p['initial_width_mm'],'candidate_mm':p['width_mm'],
        'minimum_for_current_boss_axes_mm':max(x+p['m2_boss_radius_mm'] for x,y in p['m2_axes_xy_mm'])-p['outer_x_min_mm'],
        'height_not_increased_mm':p['outer_y_mm'][1]-p['outer_y_mm'][0]}}
    usb_web=bounds(m['usbcut'])[2]-m['dimensions']['rear_bottom_z_mm']
    manufacturing={'status':'manufacturing_unverified','USB_lower_edge_web_mm':usb_web,
        'PCB_front_stop_mm':min(c['front_stop_thickness_mm'] for c in m['clip_data']),
        'PCB_front_stop_LCD_gap_mm':min(c['front_stop_to_LCD_mm'] for c in m['clip_data']),
        'minimum_depth_for_USB_0_8mm_web_mm':b[5]-bounds(m['usbcut'])[2]+.8,
        'full_process_qualification':False,
        'SLA_0_8mm_wall_screen_pass':usb_web>=.8-1e-5,
        'SLS_MJF_1mm_wall_screen_pass':usb_web>=1-1e-5 and p['pcb_front_stop_thickness_mm']>=1,
        'FDM_1_2mm_wall_screen_pass':usb_web>=1.2-1e-5 and p['pcb_front_stop_thickness_mm']>=1.2,
        'notes':'Selected local wall screens only, not all-part manufacturing approval. Keys have a separate short-pad exception. Snap release/material, 0.1mm PCB/LCD fit and tolerances remain unverified.'}
    report={'stage':'T0','manufacturing_risks':manufacturing,'geometry_status':'PASS' if all(v['pass'] for v in checks.values()) else 'FAIL',
        'overall_status':'REVIEW_ONLY_FUNCTIONAL_GATES_OPEN','print_approved':False,'manufacturing_status':'manufacturing_unverified',
        'functional_actuation_status':'UNVERIFIED','microphone_status':'BLOCKED_PORT_DIRECTION_AND_RECORDING_TEST',
        'connection_status':'UNVERIFIED_MATCHING_PLUGS_LEAD_EXIT_AND_BOARD_IDENTITIES',
        'source':{'repository':'https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8','revision':subprocess.check_output(['git','-C',str(a.reference),'rev-parse','HEAD'],text=True).strip(),'step':str(path.relative_to(a.reference)),
            'solid_count':len(source_solids),'non_solid_surfaces_not_volume_checked':len(parts['ASSEMBLY'].faces())-sum(len(s.faces()) for s in source_solids)},
        'environment':{'python':platform.python_version(),'build123d':version('build123d'),'ocp':version('cadquery-ocp-novtk')},
        'evidence':json.loads((ROOT/'cad/t0/t0-evidence.json').read_text()),'parameters':p,'key_parameters':kp,'dimensions':m['dimensions'],'thickness_and_layout_comparison':comparison,
        'original_bounds_comparison':recorded,'selected_occurrences':tree,'pocket_bounds_mm':{k:bounds(s) for k,s in parts.items()},
        'PCB_hole_axes_mm':hole_axes(parts['PCB_BOARD']),'PCB_clips':m['clip_data'],'shell_snaps':m['snap_data'],'M2_stack':m['screw_data'],
        'wiring':wire_data,'microphone_evidence':acoustic,'key_feature_screen':keyreport,'checks':checks,
        'evidence_gates':{'actual_battery_speaker_and_protection_dimensions':False,'matched_MX1_25_plug_and_polarity':False,
          'SPK_BAT_occurrence_identity_confirmed':False,'connector_pin_to_accessory_terminal_continuity_and_lead_route':False,
          'TF_inside_seating_and_eject_travel':False,'MIC_port_direction_and_board_acoustic_hole':False,
          'bare_board_vs_enclosed_recording_and_speaker_crosstalk':False,'printing_material_tolerance_and_snap_release':False,
          'actual_switch_travel_return_and_off_axis_operation':False},
        'limits':['Conditional plug and cable envelopes only; no matched physical plug model or actual accessory leads available.',
                  'MIC1 is a closed package proxy; no speculative acoustic hole is cut. Closed enclosure recording is not qualified.',
                  'Rear closure uses five released-snap rigid poses; flexure, hand access and connected cable motion are unverified.',
                  'PCB front stops are locally 0.8mm with 0.1mm nominal front gap; source LCD clearance is nominal only.',
                  'Linear beam strain is an estimate, not strength/fatigue approval. No complete manufacturing qualification.',
                  'Original radio module STEP child is named ESP32-S3-WROOM-1_ASM despite C5 board; do not infer a changed SoC or exact antenna pattern from placeholder.',
                  'No production print, no merge, no change to Pocket OS software architecture.']}
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    failures=[k for k,v in checks.items() if not v['pass']]
    assert not failures,failures
    print('T0: export separate parts, complete original-geometry assembly and light assembly',flush=True)
    manufactured={'front_shell':m['front'],'rear_shell':m['rear'],**{f'{k.lower()}_cap':v for k,v in m['caps'].items()}}
    for name,s in manufactured.items():export_step(s,out/f'{name}.step');export_stl(s,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    report['export_checks']=verify_exports(out,manufactured)
    def child(s,label,color):
        s.label=label;s.color=Color(color);return s
    styled=[child(m['front'],'FRONT_T0_FLUSH','#526a80'),child(m['rear'],'REAR_T0_1_2mm','#8293a4')]
    styled += [child(s,k+'_CAP_TRAVEL_UNVERIFIED','#e9a64a') for k,s in m['caps'].items()]
    styled += [child(m[k],k.upper()+'_UNVERIFIED','#b36b4d' if k in ['battery','protection'] else '#59636b') for k in ['battery','speaker','foam','damping','adhesive','protection']]
    styled += [child(s,f'M2_SCREW_{i}','#aeb6be') for i,s in enumerate(m['screws'])]+[child(s,f'M2_NUT_{i}','#b9a56d') for i,s in enumerate(m['nuts'])]
    styled += [child(s,k+'_PLUG_UNVERIFIED','#eee2bf') for k,s in plugs.items()]+[child(s,f'{k}_WIRE_{i}_UNVERIFIED','#c24942') for k,pair in wires.items() for i,s in enumerate(pair)]
    full=Compound(label=f"T0_{p['target_thickness_mm']:g}mm_COMPLETE_REVIEW_NOT_PRINT_APPROVED",children=[parts['ASSEMBLY'],*styled])
    full_name=f"assembly_complete_{p['target_thickness_mm']:g}mm.step"
    export_step(full,out/full_name)
    report['complete_step_filename']=full_name
    report['complete_step_bounds_mm']=bounds(full)
    reread=import_step(out/full_name);rb=bounds(reread)
    expected=len(source_solids)+sum(len(s.solids()) for s in styled)
    roundtrip={'solid_count':len(reread.solids()),'expected_solid_count':expected,
               'valid_solids':sum(s.is_valid for s in reread.solids()),'bounds_mm':rb,
               'maximum_thickness_mm':rb[5]-rb[2]}
    assert roundtrip['solid_count']==expected==roundtrip['valid_solids']
    assert abs(roundtrip['maximum_thickness_mm']-p['target_thickness_mm'])<1e-5
    report['complete_step_roundtrip']=roundtrip
    report['dimensions']['complete_external_xyz_mm']=[rb[i+3]-rb[i] for i in range(3)]
    del reread
    light_refs=[parts['PCB_BOARD'],*mounts,parts['TF'],parts['MX0'],parts['MX1']]
    for k in ['DISPLAY','J2_USB_SIDE','KEY1','KEY2','KEY3','MIC1']:
        proxy=box_between(bounds(parts[k]));proxy.label=k+'_ENVELOPE_NOT_DETAIL';proxy.color=Color('#263a43' if k=='DISPLAY' else '#c99e6b');light_refs.append(proxy)
    light=Compound(label='T0_LIGHT_PRECISE_PCB_AND_CONNECTORS_OTHER_REF_ENVELOPES',children=[*light_refs,*styled])
    export_step(light,out/'assembly_light.step');export_gltf(light,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    render_all(out,parts,m,p,plugs,wires,tfprobe,report)
    report['exports_complete']=True
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(out/'t0-complete-assembly.zip','w',zipfile.ZIP_DEFLATED) as z:
        z.write(out/full_name,full_name);z.write(out/'checks.json','checks.json')
    print(f"T0 nominal geometry PASS: {len(checks)} checks; actual mating/acoustics/printing UNVERIFIED",flush=True)

if __name__=='__main__':main()
