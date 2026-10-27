"""G-V1 V4-RECT generator: physical first-article feedback revision.

Reuses the frozen G-V1 STEP, keys and bay layout. Emits a CONDITIONAL candidate
only after nominal geometry, assembly-path and export checks pass.
"""
import hashlib
import shutil
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import Compound, export_step, export_stl, import_step

from reference import bounds
from model import box_between as box
from t0_reference import load
from p1_checks import intersection
from t0_g_v1_preview import panel
from check_exports import verify_exports
from v2_wiring import build as build_wiring
import t0_g_v4 as V4
import g_v4_checks as C
import g_v4_slider_checks as S
from g_v4_documentation import write_readme, write_measurement_sheet

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deliverables/g-v4'
BUILD = ROOT / 'build/g-v4'
CFG = ROOT / 'cad/t0'


def read(name):
    return json.loads((CFG / name).read_text())


def load_baseline():
    cfg = read('g-v1-95mm-layout.json')
    kq = read('t0-g-v1-boot-rect.json')
    p = read('t0-g-parameters.json')
    base = read('t0-a-parameters.json')
    base.update(p['layout_overrides'])
    base['width_mm'] = cfg['target_width_mm']
    kp = read('p1-parameters.json')
    kp.update(base['key_overrides'])
    base['battery'].update(
        xyz_mm=cfg['battery_complete_xyz_mm'],
        center_xy_mm=cfg['battery_center_xy_mm'],
        adhesive_mm=cfg['battery_adhesive_candidate_mm'],
        protection_xyz_mm=cfg['terminal_keepout_xyz_mm'],
        status='user_measured_COMPLETE_component')
    base['battery']['tray_clearance_mm'] = cfg['battery_tray_clearance_mm']
    base['speaker'].update(xyz_mm=cfg['speaker_xyz_mm'],
                           center_xy_mm=cfg['selected_speaker_center_xy_mm'],
                           status='user_measured_body; lead exit still to confirm')
    base['narrow_wiring'] = cfg['wiring']
    v = read('t0-g-v4.json')
    base['outer_x_min_mm'] = v['outer_x_min_mm']
    base['width_mm'] = v['width_mm']
    base['outer_y_mm'] = v['outer_y_mm']
    return base, kp, p, kq, v


def volume_overlap(a,b):
    return C.overlap(a,b)


def section(shape, x0, y0, z0, x1, y1, z1):
    return intersection(shape, box([x0, y0, z0, x1, y1, z1]))


def span_at(shape, axis, box_bounds):
    hit = intersection(shape, box(box_bounds))
    if hit.volume < 1e-6:
        return None
    bb = bounds(hit)
    return [bb[axis], bb[axis + 3]]


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    # Build and validate locally before replacing deliverables.
    base, kp, p, kq, v = load_baseline()
    report = dict(status='CHECKING', print_approved=False, functional_actuation_status='UNVERIFIED',
                  manufacturing_status='UNVERIFIED', coordinates='USB +Y / FRONT +Z / cap axis +X, side-wall plane YZ',
                  design_change=v, remaining_S2=[
                      'Printed slider friction/return/free play and actual switch actuation/max travel remain UNVERIFIED; optional spare lengths can be printed in the same batch',
                      'Supplier screw SKU, length/head tolerances, PA12 pilot/torque and service life unverified',
                      'Screen active-area/edge touch coverage, lip deflection, glass load, seam flatness and actual tolerance chain unverified',
                      'Actual battery screen/mainboard-side lead is UNMODELED; adhesive, battery tolerance/swelling and tray retention need measurement',
                      'MIC V1 drilled hole and acoustic inlet unmeasured; RESET operating stroke/force and real tools unverified',
                      'Empty-front loading is discrete; printed button axial motion/extraction are continuous; tilted insertion and actual lead remain unverified'])
    inputs=sorted([*CFG.glob('*.py'),*CFG.glob('*.json'),ROOT/'scripts/generate-g-v4.sh'])
    report['generator_inputs_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    (BUILD/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        print('Import RAW official STEP / 723 real solids', flush=True)
        parts, mounts, _ = load(ROOT.parent / 'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
        print('Build V4 shells, removable retainer and captive printed sliders',flush=True)
        m=V4.build(parts,mounts,base,kp,p,kq,v)
        f,r=m['front'],m['rear']
        # Native snapshots keep failed geometry inspectable in build, never publish it.
        for name in ['front','rear','key_bezel','battery_tray','battery','adhesive']:
            export_step(Compound(m[name].wrapped),BUILD/f'debug_{name}.step')
        for name in ['front','rear','key_bezel']:
            assert m[name].is_valid and len(m[name].solids())==1,(name,'invalid/disconnected')
        C.clear(f,r,'shells')
        report.update(dimensions=m['dimensions'],screen=m['screen_geometry'],screw_rows=m['screw_rows'],
                      bounds_mm={n:bounds(m[n]) for n in ['front','rear','key_bezel']})
        bb=report['bounds_mm'];report['overall_thickness_mm']=bb['front'][5]-bb['rear'][2]
        report['overall_bezel_width_mm']=bb['front'][3]-bb['key_bezel'][0]
        report['overall_width_mm']=max(bounds(s)[3] for s in [f,r,m['key_bezel'],*m['retainer_screws'],*m['buttons'].values()])-min(bounds(s)[0] for s in [f,r,m['key_bezel'],*m['retainer_screws'],*m['buttons'].values()])
        report['overall_height_mm']=bb['front'][4]-bb['front'][1]
        assert abs(report['overall_thickness_mm']-v['total_thickness_mm'])<1e-6
        report['screen_air']=C.screen_column(f,m['screen_geometry'])
        # Negative control reproduces F01: this MUST be rejected by the same gate.
        blocked=f+box([-20,-25,1.51,20,30,2.])
        try: C.screen_column(blocked,m['screen_geometry'])
        except AssertionError: report['screen_air']['regression_sealed_plate_rejected']=True
        else: raise AssertionError('screen gate failed its F01 negative control')
        corner_controls=[]
        for px,py in report['screen_air']['ray_xy_mm'][1:5]:
            witness=f+box([px-.02,py-.02,1.8,px+.02,py+.02,2.])
            try: C.screen_column(witness,m['screen_geometry'])
            except AssertionError: corner_controls.append(True)
            else: raise AssertionError('screen gate missed a corner obstruction')
        report['screen_air']['four_corner_negative_controls_rejected']=corner_controls
        sg=m['screen_geometry'];gb=sg['glass_bounds_mm'];lb=sg['lip_bottom_z_mm'];lt=sg['lip_top_z_mm']
        lip=intersection(f,box([23.9,-.1,lb-.1,24.5,.1,lt+.01]))
        actual_lb=bounds(lip)[2]
        assert abs(actual_lb-lb)<1e-6
        assert abs(lt-actual_lb-v['screen_lip_overhang_height_mm'])<1e-6
        window=intersection(f,box([25,-.1,.39,30,.1,.41]))
        report['screen_measured']=dict(lip_underside_z_mm=actual_lb,lip_to_glass_gap_mm=actual_lb-gb[5],
            lip_thickness_mm=lt-actual_lb,window_to_glass_gap_mm=bounds(window)[0]-gb[3],screen_recess_mm=lt-gb[5])
        assert abs(report['screen_measured']['window_to_glass_gap_mm']-v['screen_clearance_mm'])<1e-6
        # The reduced prototype scenario is explicit, not an asserted process capability.
        scenario=v['screen_fit_scenarios'];xy=scenario['selected_xy_per_axis_mm'];zz=scenario['selected_z_mm']
        screen_budget=[]
        for dx,dy in [(0,0),(xy,xy),(xy,-xy),(-xy,xy),(-xy,-xy)]:
            display=parts['DISPLAY'].translate((dx,dy,zz))
            screen_budget.append(dict(offset_xyz_mm=[dx,dy,zz],overlap_mm3=C.clear(f,display,'selected display fit scenario')))
        old_xy=scenario['previous_xy_per_axis_mm'];old_z=scenario['previous_z_mm']
        sensitivity=[]
        for dx,dy,dz in [(0,0,old_z),(old_xy,old_xy,0),(-old_xy,-old_xy,old_z)]:
            sensitivity.append(dict(offset_xyz_mm=[dx,dy,dz],overlap_mm3=C.overlap(f,parts['DISPLAY'].translate((dx,dy,dz)))))
        assert sensitivity[0]['overlap_mm3']>1e-6,'screen reduced-clearance sensitivity must detect old +0.6Z interference'
        report['screen_budget']=dict(cases=screen_budget,selected_scenario=scenario,previous_budget_sensitivity=sensitivity,
            residual_selected_Z_mm=v['screen_lip_bottom_gap_mm']-zz,
            previous_budget_covered=False,warp_and_tilt='UNVERIFIED, separate from dimensional error; no glass preload/foam; first-print XY observation does not prove Z accuracy')
        print('Check complete printed buttons, continuous sliding/extraction, capture and RESET',flush=True)
        report['v4_interfaces']=C.interfaces(m,parts,v,base)
        report['direct_key_readiness']=dict(status='PRINTED_SLIDER_GEOMETRIC_REACH_PASS_PHYSICAL_UNVERIFIED',
            keys=report['v4_interfaces']['keys'],supersedes='0127 direct cap span blocker; user authorized printed one-piece sliders')
        report['preprint_blockers_P1']=[]
        report['functional_verification_required']=['Actual switch actuation and maximum safe displacement are null; geometric stop displacement is a design candidate only',
            'PA12 slide friction and switch return force are null; free play is not forced back against outer stop',
            'Reduced screen fit scenario is unverified in Z/flatness; previous larger budget is explicitly NOT covered']
        print('Check battery adhesive, tolerance reserve and actual tray',flush=True)
        report['battery_stack']=C.battery(m,v,base)
        print('Check fasteners, bottoms, rear 4+4 holes and seam stops',flush=True)
        report['fasteners']=C.fasteners(m,v,mounts)
        report['USB_access']=C.usb_access(m)
        report['USB_negative_control']=C.usb_negative_control(m)
        mic=v['mic_port'];mp=V4.cyl(mic['diameter_mm']/2-.001,*mic['z_mm'],*mic['xy_mm'])
        report['MIC']=dict(**mic,full_thickness_path_overlap_mm3=C.clear(f,mp,'MIC full hole'),
                           measurement_required='Measure V1 printed/drilled hole diameter and XY from glass edges; locate PCB/MEMS inlet; candidate is not a measured V1 hole; acoustics UNVERIFIED')
        report['collision_checks']={}
        plugs,wires,wire_data=build_wiring(parts,base,m)
        wire_shapes=[*wires['MX1'],plugs['MX1']]
        targets=[('official_assembly_723',parts['ASSEMBLY']),('battery',m['battery']),('adhesive',m['adhesive']),('speaker',m['speaker'])]
        for name in ['front','rear','key_bezel']:
            report['collision_checks'][name]={label:C.clear(m[name],shape,name+'/'+label) for label,shape in targets}
            report['collision_checks'][name]['MX1_candidate_max_mm3']=max([C.clear(m[name],w,name+'/MX1') for w in wire_shapes]+[0])
        report['battery_wire']=dict(status='UNMODELED / UNVERIFIED',direction='screen/mainboard confirmed by user; obsolete MX0 loop excluded ONLY for battery')
        shell_overlap=max([volume_overlap(s,parts['ASSEMBLY']) for s in m['screws'][4:]]+[0])
        assert shell_overlap<1e-6
        report['screw_board_collision']=dict(shell_mm3=shell_overlap,pcb_thread_in_metal_expected_mm3=[volume_overlap(s,parts['ASSEMBLY']) for s in m['screws'][:4]])
        print('Check straight front loading, near-seam and MX1 poses',flush=True)
        sweep={}
        for dz in [.05,.1,.3,.5,.8,1,1.5,2,3,5,8,12,20,40]:
            lifted=f.translate((0,0,dz));hits={}
            for label,shape in [*targets,('rear',r),*[(f'MX1_{i}',w) for i,w in enumerate(wire_shapes)]]:
                n=volume_overlap(lifted,shape)
                if n>1e-6:hits[label]=n
            print(f'  front +Z={dz:g}: {len(hits)} collisions',flush=True)
            sweep[dz]=hits
            assert not hits,(dz,hits)
        report['front_loading']=dict(discrete_straight_pose_hits=sweep,cap_status='Printed buttons/retainer removed during front loading; continuous axial button installation/extraction checked separately',
            continuous_or_tilted_path='UNVERIFIED; 14 discrete straight poses, not continuous proof')
        report['speaker_candidate']=dict(route_length_mm=wire_data['MX1']['filleted_centerline_length_mm'],exit='+Y toward battery',real_lead='UNVERIFIED')
        assert report['speaker_candidate']['route_length_mm']<40
        # All exported parts round-trip independently, including coupon/retainer.
        exports={'front_shell':f,'rear_shell':r,'button_retainer':m['key_bezel'],**m['button_exports']}
        report['interface_negative_controls']=S.negative_controls(m,parts,v)
        for name,shape in exports.items():
            assert shape.is_valid and len(shape.solids())==1,name
            export_step(Compound(shape.wrapped),BUILD/f'{name}.step')
            export_stl(Compound(shape.wrapped),BUILD/f'{name}.stl',tolerance=.02,angular_tolerance=.15)
        report['export_checks']=verify_exports(BUILD,names=tuple(exports))
        exported_front=import_step(BUILD/'front_shell.step')
        report['screen_air_STEP_roundtrip']=C.screen_column(exported_front,sg)
        report['screen_air_STL_ray_hits']=C.stl_screen_rays(BUILD/'front_shell.stl',sg,report['screen_air']['ray_xy_mm'])
        reread={**m,'front':exported_front,'rear':import_step(BUILD/'rear_shell.step'),
                'key_bezel':import_step(BUILD/'button_retainer.step'),
                'button_exports':{name:import_step(BUILD/f'{name}.step') for name in m['button_exports']}}
        reread['buttons']={f'KEY{i}':reread['button_exports'][f'button_{label}_nominal'] for i,label in [(1,'power'),(2,'boot')]}
        report['printed_slider_STEP_roundtrip']=S.check(reread,parts,v)
        report['USB_access_STEP_roundtrip']=C.usb_access(reread)
        light=[f,r,m['key_bezel'],*m['buttons'].values(),*m['screws'],*m['retainer_screws'],parts['PCB_BOARD'],parts['DISPLAY'],m['battery'],m['adhesive'],m['speaker'],*mounts]
        export_step(Compound(children=[Compound(s.wrapped,label=s.label or f'part_{i}') for i,s in enumerate(light)]),BUILD/'assembly_light.step')
        print('Render V4 drawings and write measurement/BOM notes',flush=True)
        render(BUILD,parts,m,base,wire_shapes,mounts)
        report['status']='GEOMETRY_GATES_PASS_FUNCTIONAL_VERIFICATION_PENDING_NOT_PRINT_APPROVED'
        report['functional_actuation_status']='PRINTED_SLIDER_PHYSICAL_TRAVEL_RETURN_UNVERIFIED'
        (BUILD/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
        write_readme(BUILD,report)
        write_measurement_sheet(BUILD,v,report)
        OUT.mkdir(parents=True,exist_ok=True)
        names=[f'{n}.{ext}' for n in exports for ext in ['step','stl']]+['assembly_light.step','checks.json','README.md','printed_button_fit_sheet.md']
        names += ['FRONT.png','REAR.png','SIDE.png','ISO.png','FRONT_shell_only.png','printed_buttons_section.png','printed_button_variants.png','screen_lip_section.png','screen_lip_zoom.png','ear_screw_section.png','speaker_notch_section.png']
        previous=set()
        if (OUT/'MANIFEST.sha256').exists():
            previous={line.split(maxsplit=1)[1].strip() for line in (OUT/'MANIFEST.sha256').read_text().splitlines()}
        for obsolete in previous-set(names):
            candidate=OUT/obsolete
            assert candidate.parent==OUT,('unsafe stale output name',obsolete)
            if candidate.is_file():candidate.unlink()
        for name in names: shutil.copy2(BUILD/name,OUT/name)
        (BUILD/'MANIFEST.sha256').write_text(''.join(f'{hashlib.sha256((BUILD/n).read_bytes()).hexdigest()}  {n}\n' for n in sorted(names)))
        shutil.copy2(BUILD/'MANIFEST.sha256',OUT/'MANIFEST.sha256')
        print(report['status'],'| thickness',report['overall_thickness_mm'],'| width including bezel',report['overall_width_mm'],flush=True)
    except Exception as exc:
        report.update(status='BLOCKED_GEOMETRY_CHECK_FAILED',error=str(exc))
        (BUILD/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
        raise


def render(out, parts, m, base, wire_shapes, mounts):
    fc, rc, metal, glass = '#526d7b', '#9aa6ad', '#c1c9cc', '#14222b'
    scene = [(m['front'], fc), (m['rear'], rc),
             (parts['DISPLAY'], glass), (parts['PCB_BOARD'], '#b4bec2'),
             (m['battery'], '#b28661'), (m['speaker'], '#a05a4f')]
    scene += [(m['key_bezel'], '#718896')]+[(shape,'#c9974e') for shape in m['buttons'].values()]
    scene += [(s, metal) for s in [*m['screws'],*m['retainer_screws']]] + [(s, metal) for s in mounts]
    u = np.array([1., 0, -1]); u /= np.linalg.norm(u)
    w = np.array([1., .8, 1]); w /= np.linalg.norm(w)
    vv = np.cross(w, u)
    views = [
        ('FRONT', [1, 0, 0], [0, 1, 0], [0, 0, 1], (-37, 72, -39, 45),
         'FRONT +Z / USB +Y TOP'),
        ('REAR', [-1, 0, 0], [0, 1, 0], [0, 0, -1], (-72, 37, -39, 45),
         'REAR -Z / USB +Y TOP / four internal bosses + four PCB screws'),
        ('SIDE', [0, 0, 1], [0, 1, 0], [-1, 0, 0], (-14.5, 3.5, -39, 45),
         'SIDE +X / FRONT right / REAR left'),
        ('ISO', u, vv, w, (-35, 72, -60, 55), 'ISO FRONT'),
    ]
    for name, a, b, c, ext, title in views:
        fig, ax = plt.subplots(figsize=(11, 8) if name != 'SIDE' else (4, 9))
        panel(ax, scene, a, b, c, ext)
        ax.set_title(f"G-V4-RECT {title}\n{m['dimensions']['total_thickness_mm']:.2f}mm thick; NOT print approved", fontsize=9)
        ax.set_xlabel('mm'); ax.set_ylabel('mm')
        fig.tight_layout(); fig.savefig(out / f'{name}.png', dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10,8))
    panel(ax, [(m['front'],fc)], [1,0,0], [0,1,0], [0,0,1], (-36,69,-39,45))
    ax.set_title('V4 FRONT SHELL ONLY / screen aperture open through FULL lip height / NOT print approved')
    fig.tight_layout();fig.savefig(out/'FRONT_shell_only.png',dpi=160);plt.close(fig)

    k=m['v4_parameters']['printed_keys'];y=k['y_mm'][0]
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,pressed in zip(axes,[False,True]):
        delta=k['stroke_mm'] if pressed else 0
        scene2=[(section(m[n],-38,y-.1,-12.3,-23.5,y+.1,.8),color) for n,color in [('front',fc),('key_bezel','#718896')]]
        scene2 += [(m['buttons']['KEY1'].translate((delta,0,0)),'#c9974e'),(parts['KEY1'],metal)]
        panel(ax,scene2,[1,0,0],[0,0,1],[0,1,0],(-38,-23.5,-11.5,-1.5))
        ax.set_title('KEY1 '+('GEOMETRIC STOP / static switch witness' if pressed else 'REST / no nominal preload'),fontsize=9)
        ax.set_xlabel('X mm');ax.set_ylabel('Z mm')
    fig.suptitle('One-piece captured PA12 sliders / no flexure / actual force and switch travel UNVERIFIED',fontsize=10)
    fig.tight_layout();fig.savefig(out/'printed_buttons_section.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,(label,delta) in zip(axes,k['variants_mm'].items()):
        shape=m['button_exports'][f'button_power_{label}']
        panel(ax,[(shape,'#c9974e')],[1,0,0],[0,0,1],[0,1,0],(-38,-23.5,-11,-2))
        ax.set_title(f'{label}: flange + tip {delta:+.2f}mm / optional fit spare',fontsize=8)
        ax.set_xlabel('X mm');ax.set_ylabel('Z mm')
    fig.suptitle('Optional SAME-BATCH spare lengths; identical maximum inward tip plane / not measured switch ratings',fontsize=10)
    fig.tight_layout();fig.savefig(out/'printed_button_variants.png',dpi=160);plt.close(fig)

    # XZ through screen centre: lip and independent seam
    sec = [(section(m['front'], -33, -.12, -14.5, 70, .12, 3.3), fc),
           (section(m['rear'], -33, -.12, -14.5, 70, .12, 3.3), rc),
           (section(parts['DISPLAY'], -33, -.12, -14.5, 70, .12, 3.3), glass),
           (section(parts['PCB_BOARD'], -33, -.12, -14.5, 70, .12, 3.3), '#b4bec2')]
    fig, ax = plt.subplots(figsize=(13, 5))
    panel(ax, sec, [1, 0, 0], [0, 0, 1], [0, 1, 0], (-34, 70, -14.5, 3.3))
    ax.set_title(f"V4 SCREEN XZ at Y=0 / full lip height {m['screen_geometry']['lip_top_z_mm']:.2f}; underside {m['screen_geometry']['lip_bottom_z_mm']:.2f}; glass 0.70; seam -10.35")
    ax.set_xlabel('X'); ax.set_ylabel('Z (FRONT up)')
    fig.tight_layout(); fig.savefig(out / 'screen_lip_section.png', dpi=160); plt.close(fig)

    # Full-height zoom on the right lip
    zoom = [(section(m['front'], 20, -.12, -1.2, 30, .12, 3.3), fc),
            (section(parts['DISPLAY'], 20, -.12, -1.2, 30, .12, 3.3), glass)]
    fig, ax = plt.subplots(figsize=(7, 5))
    panel(ax, zoom, [1, 0, 0], [0, 0, 1], [0, 1, 0], (22, 29, -1.2, 3.3))
    v=m['v4_parameters']
    ax.set_title(f"V4 RIGHT SCREEN EDGE / full height; {v['screen_lip_overhang_height_mm']:.2f}mm lip; {v['screen_lip_base_mm']:.2f}mm base\n{v['screen_lip_bottom_gap_mm']:.2f}mm non-clamping gap; no foam; active edge coverage UNVERIFIED")
    ax.set_xlabel('X'); ax.set_ylabel('Z')
    fig.tight_layout(); fig.savefig(out / 'screen_lip_zoom.png', dpi=180); plt.close(fig)

    # XZ through left top boss/screw
    ear = [(section(m['front'], -33, 38.18, -14.5, 70, 38.42, 2), fc),
           (section(m['rear'], -33, 38.18, -14.5, 70, 38.42, 2), rc),
           (section(m['screws'][4], -33, 38.18, -14.5, 70, 38.42, 2), metal)]
    fig, ax = plt.subplots(figsize=(13, 4))
    panel(ax, ear, [1, 0, 0], [0, 0, 1], [0, 1, 0], (-34, 70, -14.5, 3.3))
    ax.set_title('V4 SHELL SCREW SECTION / 2x6 candidate low head, 1.0mm blind-bottom clearance; SKU UNVERIFIED')
    ax.set_xlabel('X'); ax.set_ylabel('Z')
    fig.tight_layout(); fig.savefig(out / 'ear_screw_section.png', dpi=160); plt.close(fig)

    # YZ through the speaker fence wire notch
    spk = [(section(m['front'], 28.25, -36, -14.5, 28.55, 42, 2), fc),
           (section(m['speaker'], 28.25, -36, -14.5, 28.55, 42, 2), '#a05a4f')]
    fig, ax = plt.subplots(figsize=(7, 8))
    panel(ax, spk, [0, 0, 1], [0, 1, 0], [-1, 0, 0], (-14.5, 2, -36, 42))
    ax.set_title('V4 SPEAKER FENCE YZ at X=28.4 / wire notch now at +Y edge (toward battery);\nV1 speaker/recording already works')
    ax.set_xlabel('Z (REAR left)'); ax.set_ylabel('Y')
    fig.tight_layout(); fig.savefig(out / 'speaker_notch_section.png', dpi=150); plt.close(fig)


if __name__ == '__main__':
    main()
