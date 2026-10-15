#!/usr/bin/env python3
"""One headless entry point. All fit checks use the full original board, not proxies."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
from importlib.metadata import version
from build123d import (Compound, Color, export_step, export_stl, export_gltf)
from reference import load_reference, to_pocket, bounds, hole_axes, compare_recorded
from model import make_shells, box_between
from preview import render
from check_exports import verify_exports

ROOT=Path(__file__).resolve().parents[1]


def overlap(a,b,tol):
    aa,bb=bounds(a),bounds(b)
    return all(min(aa[i+3],bb[i+3])-max(aa[i],bb[i]) > tol for i in range(3))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=ROOT.parent/'ESP32-C5-Touch-LCD-2.8')
    parser.add_argument('--parameters',type=Path,default=ROOT/'cad/parameters.json')
    parser.add_argument('--output',type=Path,default=ROOT/'build/p0')
    args=parser.parse_args()
    p=json.loads(args.parameters.read_text());out=args.output;out.mkdir(parents=True,exist_ok=True)
    step=args.reference/'dimensions/ESP32-C5-Touch-LCD-2.8.stp'
    print('Importing original STEP and accumulating assembly placements...',flush=True)
    original,mounts_original=load_reference(step)
    recorded=compare_recorded(original,ROOT/'data/step_component_bounds.csv',p['reference_bounds_tolerance_mm'])
    parts={k:to_pocket(s) for k,s in original.items()}
    mounts=[to_pocket(m) for m in mounts_original]
    holes=hole_axes(parts['PCB_BOARD'])
    assert abs(max(h[0] for h in holes)-min(h[0] for h in holes)-41)<.02
    assert abs(max(h[1] for h in holes)-min(h[1] for h in holes)-60)<.02
    # Inverse transform must recover the original bounds of EVERY selected component.
    inverse={k:max(abs(a-b) for a,b in zip(bounds(to_pocket(v)),bounds(original[k]))) for k,v in parts.items()}
    assert max(inverse.values())<p['geometry_tolerance_mm']
    assert parts['J2_USB_SIDE'].center().Y > 30
    assert all(parts[k].center().X<0 for k in ['KEY1','KEY2','KEY3'])
    assert parts['MIC1'].center().X>0
    # Distance preservation independently catches misplaced children and accidental shifts.
    distances=[]
    for a,b in [('KEY1','KEY3'),('KEY3','KEY2'),('J2_USB_SIDE','MIC1')]:
        before=(original[a].bounding_box().center()-original[b].bounding_box().center()).length
        after=(parts[a].bounding_box().center()-parts[b].bounding_box().center()).length
        assert abs(before-after)<p['geometry_tolerance_mm']
        distances.append({'pair':[a,b],'distance_mm':after,'difference_mm':abs(before-after)})
    print('Constructing shells from measured envelopes and PCB circular hole axes...',flush=True)
    front,rear,usb,keys,dimensions=make_shells(parts,mounts,holes,p)
    checks={}
    for name,s in [('front',front),('rear',rear)]:
        checks[name]={'valid':s.is_valid,'solid_count':len(s.solids()),'volume_mm3':s.volume}
        assert s.is_valid and len(s.solids())==1 and s.volume>0
    tol=p['geometry_tolerance_mm'];vtol=p['collision_volume_tolerance_mm3']
    collisions=[];candidate_count=0
    full_solids=parts['ASSEMBLY'].solids()
    print(f'Checking shells against all {len(full_solids)} original solids...',flush=True)
    for shell_name,shell in [('FRONT',front),('REAR',rear)]:
        for i,solid in enumerate(full_solids):
            if overlap(shell,solid,tol):
                candidate_count+=1
                common=shell.intersect(solid)
                volume=common.volume if common is not None else 0
                if volume>vtol:collisions.append({'shell':shell_name,'source_solid':i,'volume_mm3':volume})
    common=front.intersect(rear);shell_overlap=common.volume if common is not None else 0
    corridors={}
    for name,corridor in [('USB_TOP',usb)]+[(f'KEY_{i+1}',k) for i,k in enumerate(keys)]:
        for sn,shell in [('FRONT',front),('REAR',rear)]:
            c=shell.intersect(corridor);v=c.volume if c is not None else 0
            corridors[f'{name}_{sn}']=v
    source_valid=sum(s.is_valid for s in full_solids)
    solid_faces={hash(f) for solid in full_solids for f in solid.faces()}
    non_solid_faces=sum(hash(f) not in solid_faces for f in parts['ASSEMBLY'].faces())
    report={
        'status':'PASS' if source_valid==len(full_solids) and not collisions and shell_overlap<=vtol and all(v<=vtol for v in corridors.values()) else 'FAIL',
        'environment':{'python':platform.python_version(),'build123d':version('build123d'),
                       'ocp':version('cadquery-ocp-novtk')},
        'source':{'repository':'https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8',
                  'revision':subprocess.check_output(['git','-C',str(args.reference),'rev-parse','HEAD'],text=True).strip(),
                  'path':str(step.relative_to(args.reference)),'file_size_bytes':step.stat().st_size,
                  'solid_count':len(full_solids),'valid_solids':source_valid,
                  'non_solid_face_count':non_solid_faces},
        'original_bounds_comparison':recorded,'inverse_transform_bounds_error_mm':inverse,
        'rigid_distance_checks':distances,'pocket_bounds_mm':{k:bounds(v) for k,v in parts.items()},
        'pcb_hole_axes_x_y_radius_mm':holes,'pcb_outline':{'basis':'original BOARD solid; no rectangle substituted',
                  'face_count':len(parts['PCB_BOARD'].faces())},
        'dimensions':dimensions,'parameters':p,'shell_geometry':checks,
        'interference':{'broad_phase_candidates':candidate_count,'collisions':collisions,
                       'shell_overlap_mm3':shell_overlap,'corridor_overlap_mm3':corridors},
        'limitations':['Static CAD only; screw heads/threads, cable bend and insertion assembly are not verified.',
                      'Battery/speaker absent. Rear depth is a replaceable P0 parameter, not final thickness.',
                      'KEY functional mapping, actuator contact/travel and MIC acoustic port direction remain unverified.',
                      'Front/rear fastening and locating features remain preliminary; no print release.',
                      'Source may contain non-solid faces; interference checks cover source solids only.']}
    assert report['status']=='PASS',collisions
    print('Exporting shell STEP/STL and lightweight assembly...',flush=True)
    front.color=Color('#4e6580');rear.color=Color('#72869b')
    for name,shell in [('front_shell',front),('rear_shell',rear)]:
        export_step(shell,out/f'{name}.step')
        export_stl(shell,out/f'{name}.stl',tolerance=.05,angular_tolerance=.2)
    # Lightweight viewing assembly: exact PCB and nuts, envelopes for other selected parts.
    light=[front,rear,parts['PCB_BOARD'],*mounts]
    for name in ['DISPLAY','KEY1','KEY3','KEY2','MIC1','J2_USB_SIDE']:
        proxy=box_between(bounds(parts[name]));proxy.label=name+'_ENVELOPE_NOT_DETAIL'
        proxy.color=Color('#29363e' if name=='DISPLAY' else '#e9a64a')
        light.append(proxy)
    parts['PCB_BOARD'].color=Color('#1c8069')
    assembly=Compound(label='Pocket_Pi_P0_LIGHTWEIGHT',children=light)
    export_step(assembly,out/'assembly_light.step')
    export_gltf(assembly,out/'assembly_light.glb',binary=True,linear_deflection=.15,angular_deflection=.3)
    # Full original board retained only locally, excluded from our Git history.
    export_step(Compound(children=[front,rear,parts['ASSEMBLY']]),out/'assembly_full_local.step')
    report['export_checks']=verify_exports(out)
    render(out,parts,mounts,front,rear,p)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"PASS: {out}; original solid validity {source_valid}/{len(full_solids)}",flush=True)

if __name__=='__main__':main()
