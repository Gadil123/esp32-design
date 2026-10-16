#!/usr/bin/env python3
"""Generate the P1 review package from the untouched original Waveshare STEP."""
import argparse
import json
import platform
import subprocess
from pathlib import Path
from importlib.metadata import version
from build123d import Compound,Color,export_step,export_stl,export_gltf
from reference import load_reference,to_pocket,bounds,hole_axes,compare_recorded
from model import box_between
from p1_model import make_p1
from p1_checks import validate
from check_exports import verify_exports
from preview import render
from p1_preview import render_details, render_manufacturing
from p1_manufacturing import validate_manufacturing, make_coupon

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=ROOT.parent/'ESP32-C5-Touch-LCD-2.8')
    parser.add_argument('--parameters',type=Path,default=ROOT/'cad/p1-parameters.json')
    parser.add_argument('--output',type=Path,default=ROOT/'build/p1')
    args=parser.parse_args();p=json.loads(args.parameters.read_text());out=args.output
    out.mkdir(parents=True,exist_ok=True)
    (out/'checks.json').unlink(missing_ok=True)
    print('P1: importing original STEP',flush=True)
    path=args.reference/'dimensions/ESP32-C5-Touch-LCD-2.8.stp'
    original,original_mounts=load_reference(path)
    recorded=compare_recorded(original,ROOT/'data/step_component_bounds.csv',p['reference_bounds_tolerance_mm'])
    parts={k:to_pocket(v) for k,v in original.items()};mounts=[to_pocket(n) for n in original_mounts]
    holes=hole_axes(parts['PCB_BOARD'])
    transform_errors={k:max(abs(a-b) for a,b in zip(bounds(to_pocket(s)),bounds(original[k]))) for k,s in parts.items()}
    assert max(transform_errors.values())<p['geometry_tolerance_mm']
    assert parts['J2_USB_SIDE'].center().Y>30 and parts['MIC1'].center().X>0
    assert all(parts[k].center().X<0 for k in ['KEY1','KEY2','KEY3'])
    assert abs(max(h[0] for h in holes)-min(h[0] for h in holes)-41)<.02
    assert abs(max(h[1] for h in holes)-min(h[1] for h in holes)-60)<.02
    print('P1: constructing brackets, fastener stack and split guides',flush=True)
    m=make_p1(parts,mounts,holes,p)
    checks,plug=validate(parts,mounts,holes,m,p)
    profile=json.loads((ROOT/'cad/p1-manufacturing.json').read_text())
    manufacturing_checks,manufacturing=validate_manufacturing(m,p,profile)
    checks.update(manufacturing_checks)
    coupons=make_coupon(m,profile)
    for name,shape in coupons.items():
        checks[f'valid_{name}']={'pass':shape.is_valid and len(shape.solids())==1 and shape.volume>0,
                                'solid_count':len(shape.solids()),'bounds_mm':bounds(shape)}
    solids=parts['ASSEMBLY'].solids()
    valid=sum(s.is_valid for s in solids)
    solid_faces={hash(f) for s in solids for f in s.faces()}
    non_solid_faces=sum(hash(f) not in solid_faces for f in parts['ASSEMBLY'].faces())
    report={'stage':'P1','status':'PASS' if all(v['pass'] for v in checks.values()) and valid==len(solids) else 'FAIL',
            'release_status':'REVIEW_ONLY_NOT_PRINTABLE','functional_actuation_status':'UNVERIFIED',
            'manufacturing_status':'manufacturing_unverified','manufacturing':manufacturing,
            'source':{'repository':'https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8',
                      'revision':subprocess.check_output(['git','-C',str(args.reference),'rev-parse','HEAD'],text=True).strip(),
                      'step':str(path.relative_to(args.reference)),'solid_count':len(solids),'valid_solids':valid,
                      'non_solid_face_count_not_volume_checked':non_solid_faces},
            'environment':{'python':platform.python_version(),'build123d':version('build123d'),'ocp':version('cadquery-ocp-novtk')},
            'parameters':p,'evidence':json.loads((ROOT/'cad/p1-evidence.json').read_text()),
            'original_bounds_comparison':recorded,'inverse_transform_bounds_error_mm':transform_errors,
            'pocket_bounds_mm':{k:bounds(s) for k,s in parts.items()},'pcb_hole_axes_x_y_radius_mm':holes,
            'dimensions':m['dimensions'],'mount_stack':m['mount_data'],'keys':m['key_data'],
            'usb_mouth_face_bounds_mm':m['usb_mouth_face_bounds_mm'],'checks':checks,
            'unverified':['Candidate SLA/material/supplier unconfirmed. Short contact pad strength, guide wear, warp, support removal and coupon fit untested.',
                          'Guide float exceeds full-contact edge margins. Off-axis actuation/case contact and assembled datum preload are UNVERIFIED; axial centered paths only.',
                          'Actual switch travel, return force and actuation remain unknown; cap motion budget does not prove functional operation.',
                          'USB datum/metal nose and cable-specific shoulder geometry require physical seating test; only sourced body clearance verified.',
                          'Assembly poses are rigid; rear closure and screws sampled, not a full continuous proof.',
                          'Screw clamp torque, threaded engagement strength, arm/guide print tolerances, load deformation and screen/PCB stress require physical verification.',
                          'Battery/speaker absent; final thickness is null. MIC acoustic port still unverified.',
                          'Non-solid reference surfaces are not included in volume interference checks.']}
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    failures=[k for k,v in checks.items() if not v['pass']]
    assert report['status']=='PASS',failures
    print('P1: exporting manufactured parts and review assembly',flush=True)
    manufactured={'front_shell':m['front'],'rear_shell':m['rear'],
                  **{f'{k.lower()}_cap':v for k,v in m['caps'].items()}}
    for name,s in manufactured.items():
        s.color=Color('#e9a64a' if name.endswith('cap') else '#4e6580' if name=='front_shell' else '#72869b')
        export_step(s,out/f'{name}.step');export_stl(s,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    for name,shape in coupons.items():
        export_step(shape,out/f'{name}.step');export_stl(shape,out/f'{name}.stl',tolerance=.015,angular_tolerance=.12)
    report['export_checks']=verify_exports(out,[*manufactured,*coupons])
    light=list(manufactured.values())+[parts['PCB_BOARD'],*mounts,*m['screws']]
    parts['PCB_BOARD'].color=Color('#1c8069')
    for key in ['DISPLAY','KEY1','KEY2','KEY3','MIC1','J2_USB_SIDE']:
        proxy=box_between(bounds(parts[key]));proxy.label=key+'_ENVELOPE_NOT_DETAIL'
        proxy.color=Color('#29363e' if key=='DISPLAY' else '#a76d31');light.append(proxy)
    assembly=Compound(label='Pocket_Pi_V1_P1_LIGHTWEIGHT',children=light)
    export_step(assembly,out/'assembly_light.step')
    export_gltf(assembly,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    extras=[(v,'#e9a64a') for v in m['caps'].values()]+[(s,'#b3bac2') for s in m['screws']]
    render(out,parts,mounts,m['front'],m['rear'],p,stage='P1',extras=extras)
    render_details(out,parts,mounts,m,plug)
    render_manufacturing(out,parts,m,p,manufacturing,coupons)
    report['exports_complete']=True
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'P1 PASS: {len(checks)} checks; functional actuation UNVERIFIED; {out}',flush=True)

if __name__=='__main__':main()
