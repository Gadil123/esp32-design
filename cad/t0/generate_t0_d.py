#!/usr/bin/env python3
"""Finite D study: original STEP -> one edge pair + four nests -> stop gate."""
import json, shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import Compound, GeomType, export_step, import_step, extrude
from reference import bounds, compare_recorded, to_pocket
from t0_reference import load
from t0_d_study import build
from t0_model import build as build_a_reference
from t0_wiring import build_wiring
from p1_checks import clashes, common_volume, intersection, translated_box_sweep
from p1_preview import panel
from model import box_between as box

ROOT=Path(__file__).resolve().parents[2]


def run(parts,mounts,p,base,out):
    m=build(parts,mounts,p,base); tol=p['collision_volume_tolerance_mm3']; dim=m['dimensions']
    source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    new=[('FRONT_open_frame',m['frame']),*[(f'REAR_nest_{i}',s) for i,s in enumerate(m['seats'])],('edge_FRONT',m['front']),('edge_REAR',m['rear'])]
    static={k:clashes(s,source,tol) for k,s in new}
    # Exact continuous containment proof, no sampled-pose PASS substituted for a path.
    ab=bounds(parts['ASSEMBLY']); ap=dim['display_aperture_xy_mm']
    margins=[ab[0]-ap[0],ab[1]-ap[1],ap[2]-ab[3],ap[3]-ab[4]]
    frame_path={'all_official_solids_inside_open_xy_passage':min(margins)>0,
                'minimum_xy_clearance_mm':min(margins),'xy_margins_mm':margins,
                'scope':'Continuous straight Z translation through this open frame only; keys/leads not certified by this containment test.'}
    escape=p['board_escape_witness_z_mm']
    # The complete module can move toward FRONT while REAR remains CLOSED.
    # Exact -Z sweep for these prismatic fixtures: union downward planar faces
    # extruded through the interval, preserving apertures and annular cavities.
    fixtures=[(k,s) for k,s in new]
    escape_hits={}
    for k,s in fixtures:
        swept=s
        for face in s.faces():
            if face.geom_type==GeomType.PLANE and face.normal_at().Z<-.0001:
                swept=swept+extrude(face,amount=escape,dir=(0,0,-1))
        escape_hits[k]=clashes(swept,source,tol)
    cover_path=[]
    for dz in [-8,-2,-1,0]:
        cover_path.append({'rear_offset_z_mm':dz,'nest_collisions':[clashes(s.translate((0,0,dz)),source,tol) for s in m['seats']]})
    # Original A accessories/caps are reference obstacles ONLY. No A PCB clips or
    # A 12mm shell flexures are included in D's CAD or credited as restraints.
    kp=json.loads((ROOT/'cad/t0/p1-parameters.json').read_text()); kp.update(base['key_overrides'])
    aref=build_a_reference(parts,mounts,base,kp)
    plugs,wires,_=build_wiring(parts,base,aref)
    accessories=[(k,aref[k]) for k in ['battery','speaker','protection','foam','damping','adhesive']]
    accessories += list(plugs.items())+[(f'{k}_wire',s) for k,ss in wires.items() for s in ss]
    accessories += list(aref['caps'].items())+[('USB_independent_plug',aref['usbprobe']),('TF_candidate_corridor',aref['tfcut'])]
    changed=[(k,s) for k,s in new if k!='FRONT_open_frame']
    additions={k:clashes(s,accessories,tol) for k,s in changed}
    # Do not use the reference aperture frame as a finished interface-cut shell.
    d=p['release_deflection_mm']; pull=p['release_pull_mm']; tongue=m['tongue']; fixed=m['fixed_rear']; front=m['front']
    retained=common_volume(tongue.translate((0,0,-.3)),front)
    retracted=tongue.translate((-d,0,0))
    released=clashes(translated_box_sweep(retracted,(0,0,-pull)),[('FRONT_receiver',front)],tol)
    approach=clashes(translated_box_sweep(retracted,(0,0,-4)),[('FRONT_receiver',front)],tol)
    relaxed=common_volume(tongue.translate((0,0,-pull)),front)
    pick=clashes(m['pick'],[('FRONT_receiver',front),('REAR_fixed',fixed)],tol)
    edge_pair=common_volume(front,m['rear'])
    L=dim['compliant_length_to_tip_load_mm']
    report={'stage':'D','status':'BLOCKED_MISSING_FRONTWARD_PCB_RESTRAINT','primary_blocker':'Rear shallow nests provide -Z support and bounded XY while seated, but no +Z reaction. No glass/battery/component clamp is permitted. Whole board moves +Z with cover closed.',
        'full_D_enclosure_completed':False,'print_approved':False,'parameters':p,'dimensions':dim,
        'original_STEP_solid_count':len(source),'local_fixtures_vs_all_official_solids':static,'mounts':m['rows'],
        'PCB_insertion_open_frame':frame_path,'shallow_nest_cover_closing_samples':cover_path,
        'closed_cover_frontward_escape':{'module_displacement_z_mm':escape,'continuous_fixture_sweeps_vs_original_solids':escape_hits,
            'witness_clear':not any(escape_hits.values()),'screen_front_would_be_above_flush_mm':escape,'DOF_gate':'FAIL',
            'note':'Fixture swept -Z is relative equivalent of entire board swept +Z. Positive BRep witness disproves reliable Z location; no need for an escape-to-infinity path.'},
        'DOF':{'X_Y':'Finite radial free play only while four metal exteriors remain inside shallow nests. Left pair nominal .1mm; upper left Y elongated .3mm; right pair .3mm relief. Manufacturing not proven.',
               'rotation_about_Z':'Two separated left datum nests bound yaw while seated; no validated preload or interference fit.',
               'minus_Z_and_tilt':'Four rear annular bearing faces support rearward load; one-sided support only.',
               'plus_Z':'UNRESTRAINED; cannot replace the absent stop with glass, keys, connectors or battery.'},
        'local_additions_vs_unchanged_unverified_accessories':additions,
        'edge_pair':{'nominal_front_rear_overlap_mm3':edge_pair,'hold_after_rear_pull_0_3_mm3':retained,
            'retracted_approach_sweep_collisions':approach,'external_pick_fixed_geometry_collisions':pick,'retracted_withdrawal_sweep_collisions':released,
            'relaxed_after_release_pull_overlap_mm3':relaxed,'local_clearance_gate': 'PASS' if edge_pair<tol and retained>tol and not approach and not released and not pick and relaxed<tol else 'FAIL',
            'beam_proxy_linear_strain':1.5*p['tongue_thickness_mm']*d/L**2,
            'mechanics_status':'UNVERIFIED: root-fixed actual wall bending is NOT a rigid translation; tongue translation only bounds free-end clearance. No fatigue/force or full-cover sequential-release proof.',
            'features_mm':{'rear_panel':p['rear_panel_mm'],'tongue_thickness':p['tongue_thickness_mm'],'tooth_projection':p['tooth_projection_mm'],
                'tip_flat_height':p['tooth_tip_top_z_mm']-p['tooth_bottom_z_mm'],'window_lower_ligament':p['window_bottom_z_mm']-p['receiver_bottom_z_mm'],'lap_gap':p['lap_clearance_mm']},
            'process_risks':'1.2mm panel, .7mm tooth projection/.1mm tip flat, 1.5mm local retaining ligament and .3mm running clearance require MJF PA12 supplier review; sharp root/stress concentration and ~5% linear strain estimate not qualified.'},
        'assembly_sequence':[
            {'step':'1 place existing independent caps from REAR','status':'UNVERIFIED; existing A/C native-switch fixed-frame risk retained; no key redesign'},
            {'step':'2 complete official PCB/display through open FRONT frame from REAR','status':'Open-frame continuous passage clear; cap/native-switch crossing and wire installation not qualified'},
            {'step':'3 close four shallow REAR nests around native metal exteriors','status':'Sampled source-geometry approach clear; zero nominal rear-face gap; no thread pins'},
            {'step':'4 engage ONE short tooth/window','status':'Local free-end clearance only; actual PA12 bending unverified'},
            {'step':'5 keep cover closed and apply FRONT +Z board displacement','status':'FAIL: no reaction; stop before whole-enclosure redesign'},
            {'step':'6 pry through window, hold inward .5mm and local gap 2.8mm, withdraw board toward REAR','status':'Single local edge clearance studied; complete assembly/disassembly NOT validated'}],
        'unchanged_gates':['native key travel/frame identity/return; no actual switch travel assumed','MIC1 port/recording; no acoustic redesign','TF actual seating/ejection','MX identities/polarity/mating plugs and lead routing','temporary battery/speaker dimensions and .23mm protection-side gap','PA12 bending, cleaning, tolerances, supplier acceptance'],
        'stop':'One primary missing +Z restraint. No C2 screw fallback, no restored four PCB flexclips, no further mechanism search or whole D shell.'}
    export_step(Compound([front,m['rear']]),out/'D_one_short_tooth_pair_LOCAL.step')
    export_step(Compound([parts['DISPLAY'],parts['PCB_BOARD'],*mounts,m['frame'],*m['seats']]),out/'D_four_nests_open_frame_BLOCKED.step')
    report['exports']={}
    for name in ['D_one_short_tooth_pair_LOCAL','D_four_nests_open_frame_BLOCKED']:
        shape=import_step(out/f'{name}.step');bb=bounds(shape)
        report['exports'][name]={'solids':len(shape.solids()),'all_valid':all(s.is_valid for s in shape.solids()),'bounds_mm':bb,'max_z_mm':bb[5]-bb[2]}
        assert shape.is_valid and all(s.is_valid for s in shape.solids()) and bb[5]-bb[2]<=12.40001
    assert not any(static.values()) and not any(additions.values())
    assert frame_path['all_official_solids_inside_open_xy_passage'] and not any(escape_hits.values())
    render(out,parts,mounts,m,p)
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def render(out,parts,mounts,m,p):
    colors={'front':'#526a80','rear':'#dba64d','board':'#258870','display':'#8aa6a2','metal':'#ac9665'}
    y=p['edge_center_y_mm'];clip=box([65,y-.04,-12,71,y+.04,1])
    fig,axs=plt.subplots(1,3,figsize=(14,7))
    for ax,dz,dx,title in [(axs[0],0,0,'Closed | short tooth + overlap edge'),(axs[1],-.3,0,'Rigid hold witness: rear pull 0.3mm'),(axs[2],-p['release_pull_mm'],-p['release_deflection_mm'],'Free-end release proxy: -X .5 / -Z 2.8mm')]:
        items=[(m['front'],colors['front']),(m['fixed_rear'].translate((0,0,dz)),colors['rear']),(m['tongue'].translate((dx,0,dz)),colors['rear'])]
        if dx: items.append((m['pick'],'#ae6275'))
        panel(ax,[(intersection(s,clip),c) for s,c in items],[1,0,0],[0,0,1],[0,1,0],(65.5,71,-12,1))
        ax.set_title(title,fontsize=9);ax.set_xlabel('X mm / OUTSIDE right');ax.set_ylabel('Z mm / FRONT up, REAR down')
    axs[0].annotate('0.4mm overlap\nwindow lower ligament 1.5mm',(69,-6.15),(65.65,-2),arrowprops={'arrowstyle':'->'},fontsize=8)
    fig.suptitle('D ONE LOCAL PAIR / right edge, USB +Y out of section\nCAD sections; translated tongue is clearance proxy, NOT validated PA12 bending or whole-cover release')
    fig.tight_layout();fig.savefig(out/'D_short_tooth_sections.png',dpi=170);plt.close(fig)
    y=m['rows'][0]['axis_xy_mm'][1];clip=box([-31,y-.04,-12,30,y+.04,2])
    fig,axs=plt.subplots(3,1,figsize=(14,10))
    for ax,dz,cover,title in [(axs[0],-2,False,'REAR insertion: 2mm before final / REAR cover absent'),(axs[1],0,True,'Nominal flush pose / four shallow nests / no FRONT axial stop'),(axs[2],p['board_escape_witness_z_mm'],True,'FAIL witness: module +0.4mm toward FRONT while REAR stays closed')]:
        scene=[(parts['DISPLAY'].translate((0,0,dz)),colors['display']),(parts['PCB_BOARD'].translate((0,0,dz)),colors['board'])]
        scene += [(s.translate((0,0,dz)),colors['metal']) for s in mounts]+[(m['frame'],colors['front'])]
        if cover:scene += [(s,colors['rear']) for s in m['seats']]
        panel(ax,[(intersection(s,clip),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(-31,30,-12,2))
        ax.axhline(m['dimensions']['front_top_z_mm'],ls='--',color='#a94b56',lw=.7)
        ax.set_title(title);ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up')
    fig.suptitle('D FOUR NATIVE METAL MOUNTS / sections through lower pair; same upper-pair mechanism\nUSB +Y out of section | FRONT +Z / REAR -Z | local max 12.4mm at nominal pose; NO full D enclosure')
    fig.tight_layout();fig.savefig(out/'D_mount_path_sections.png',dpi=170);plt.close(fig)


def main():
    p=json.loads((ROOT/'cad/t0/t0-d-parameters.json').read_text())
    base=json.loads((ROOT/'cad/t0/t0-a-parameters.json').read_text());base['target_thickness_mm']=p['maximum_thickness_mm']
    out=ROOT/'build/t0-d';out.mkdir(parents=True,exist_ok=True)
    print('D: import original vendor STEP, preserving occurrences and proper Rz180',flush=True)
    parts,mounts,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    recorded=compare_recorded({k:to_pocket(s) for k,s in parts.items()},ROOT/'data/step_component_bounds.csv',.05)
    print('D: one edge pair, four shallow nests, original-solid stage gate',flush=True)
    report=run(parts,mounts,p,base,out);report['original_coordinate_round_trip_vs_recorded']=recorded
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    dest=ROOT/'deliverables/t0-d';dest.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.suffix in ['.step','.png','.json']:shutil.copy2(f,dest/f.name)
    print(report['status']+'; stop, no full D shell, no print approval',flush=True)


if __name__=='__main__':main()
