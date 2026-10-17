"""Independent envelopes, measured maximum thickness and explicit evidence gates."""
import numpy as np
from build123d import GeomType,Compound,Cylinder,Axis,Align
from reference import bounds
from model import box_between as box
from p1_checks import clashes,common_volume,intersection,translated_box_sweep,cap_components


def cap_axial_sweep(piece,data,kp):
    b=bounds(piece);motion=kp['key_cap_design_motion_mm']
    if data['function']=='RESET' and b[3]<=data.get('body_start_x_mm',b[0])+1e-5:
        return Cylinder((b[4]-b[1])/2,b[3]-b[0]+motion,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((b[0],(b[1]+b[4])/2,(b[2]+b[5])/2))
    return translated_box_sweep(piece,[motion,0,0])


def board_insertion_fixture(parts,m,p):
    fixed=m['front']
    for clip in m['pcb_clips']:fixed=fixed-clip
    moving=translated_box_sweep(parts['ASSEMBLY'],[0,0,-20])
    obstacles=[('front_without_compliant_clips',fixed),*[(f'held_released_clip{i}',s) for i,s in enumerate(m['pcb_releases'])]]
    hits=clashes(moving,obstacles,p['volume_tolerance_mm3'])
    return {'pass':not hits,'collisions':hits,'board_continuous_conservative_AABB':True,
            'insertion_direction':'from REAR -Z toward +Z','translation_mm':[0,0,20],
            'scope':'clips held in rigid released fixture poses; actual elastic roots, finger access and material behavior unverified'}


def validate(parts,m,p,kp,plugs,wires):
    checks={};tol=p['volume_tolerance_mm3'];board=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    def rec(n,ok,**d):checks[n]={'pass':bool(ok),**d}
    rigid=[('front',m['front']),('rear',m['rear']),*m['caps'].items(),*[(f'screw{i}',s) for i,s in enumerate(m['screws'])],*[(f'nut{i}',s) for i,s in enumerate(m['nuts'])]]
    soft=[(k,m[k]) for k in ['battery','speaker','foam','damping','adhesive','protection']]
    cable=[*plugs.items(),*[(f'{k}_wire{i}',s) for k,pair in wires.items() for i,s in enumerate(pair)]]
    all_new=rigid+soft+cable
    print('T0: checking all rigid, provisional accessory and cable solids against full original board',flush=True)
    for name,s in all_new:
        rec(f'valid_{name}',s.is_valid and len(s.solids())==1 and s.volume>0,solid_count=len(s.solids()))
        hits=clashes(s,board,tol);rec(f'board_{name}',not hits,collisions=hits)
    print('T0: pairwise interference',flush=True)
    for i,(name,s) in enumerate(all_new):
        for other,t in all_new[i+1:]:
            v=common_volume(s,t);rec(f'pair_{name}_{other}',v<=tol,volume_mm3=v)
    # Full actual external solid bounds, including all original parts, screw heads,
    # clips, caps, foam/adhesive, candidate plugs and every swept conductor.
    installed=[('official_complete',parts['ASSEMBLY']),*all_new]
    bb={n:bounds(s) for n,s in installed};zlo=min(v[2] for v in bb.values());zhi=max(v[5] for v in bb.values());depth=zhi-zlo
    rec('maximum_complete_assembly_thickness',depth<=p['target_thickness_mm']+1e-5,
        actual_maximum_mm=depth,min_z_mm=zlo,max_z_mm=zhi,individual_bounds_mm=bb,excluded_installed_solids=[])
    rec('glass_flush_no_lip',abs(bounds(m['front'])[5]-bounds(parts['DISPLAY'])[5])<1e-5,
        front_z_mm=bounds(m['front'])[5],glass_z_mm=bounds(parts['DISPLAY'])[5])
    gap=parts['ASSEMBLY'].distance_to(m['rear'])
    floor=m['dimensions']['rear_inside_z_mm'];floor_gap=bounds(parts['ASSEMBLY'])[2]-floor
    rec('PCB_to_rear_panel_clearance',floor_gap>=p['minimum_rigid_gap_mm'],floor_gap_mm=floor_gap,
        minimum_all_rear_distance_mm=gap,scope='nominal rigid geometry, board/manufacturing tolerances unknown')
    probe=m['usbprobe'];hits=clashes(probe,[*rigid,*board],tol)
    rec('USB_independent_continuous_body_probe',not hits,collisions=hits,minimum_shell_gap_mm=min(probe.distance_to(m[k]) for k in ['front','rear']))
    # Full SD form factor supplied by SD Association. This verifies the OUTSIDE
    # approach to the mouth, not the contacts/seat/spring inside the simplified socket.
    tb=bounds(parts['TF']);yc=(tb[1]+tb[4])/2;z=(tb[2]+tb[5])/2;w=p['tf_card_xyz_mm'][1];h=p['tf_card_xyz_mm'][2]
    tf=box([p['outer_x_min_mm']-20,yc-w/2,z-h/2,tb[0],yc+w/2,z+h/2])
    hits=clashes(tf,[*rigid,*board],tol)
    rec('TF_external_approach_corridor',not hits,collisions=hits,probe_bounds_mm=bounds(tf),
        insertion_direction=[1,0,0],socket_seating_verified=False,ejection_mechanism_verified=False,
        ejection_budget_mm=p['tf_ejection_budget_mm'])
    print('T0: actuator, edge clip and peripheral snap checks',flush=True)
    for key,cap in m['caps'].items():
        hits=[]
        for piece in cap_components(cap,m['key_data'][key],kp):
            hits+=clashes(cap_axial_sweep(piece,m['key_data'][key],kp),rigid[:2],tol)
        rec(f'{key}_centered_cap_motion',not hits,collisions=hits,actual_switch_travel_mm=None,
            candidate_budget_mm=kp['key_cap_design_motion_mm'],functional_actuation_verified=False)
        if p.get('variant')=='A':
            corner_hits=[]
            c=kp['key_guide_clearance_mm']
            for dy in [-c,c]:
                for dz in [-c,c]:
                    for piece in cap_components(cap,m['key_data'][key],kp):
                        hh=clashes(cap_axial_sweep(piece.translate((0,dy,dz)),m['key_data'][key],kp),rigid[:2],tol)
                        if hh:corner_hits.append({'offset_yz_mm':[dy,dz],'collisions':hh})
            rec(f'{key}_translated_corner_motion',not corner_hits,collisions=corner_hits,
                scope='four transverse float corners, continuous conservative axial sweep; tilt/contact force/return remain functional gates')
        rec(f'{key}_nominal_no_preload',cap.distance_to(parts[key])>=kp['key_contact_gap_mm']-.001,
            measured_gap_mm=cap.distance_to(parts[key]),assembled_tolerance_verified=False)
    if p.get('variant')=='A':
        yc,zc=m['key_data']['KEY3']['center_yz_mm'];ox=p['outer_x_min_mm']
        needle=Cylinder(kp['reset_tool_radius_mm'],5+kp['reset_recess_mm'],align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-5,yc,zc))
        hh=clashes(needle,[*rigid,*board],tol)
        rec('RESET_independent_needle_entry',not hh,collisions=hh,probe_diameter_mm=2*kp['reset_tool_radius_mm'],
            nominal_hole_diameter_mm=2*kp['reset_hole_radius_mm'],front_face_stock_mm=p['reset_face_stock_mm'],
            recessed_nose_diameter_mm=2*p['reset_nose_radius_mm'],actual_actuation_verified=False)
    for i,clip in enumerate(m['pcb_clips']):
        rec(f'PCB_clip_{i}_support_contact',m['supports'][i].distance_to(parts['PCB_BOARD'])<.001,
            distance_mm=m['supports'][i].distance_to(parts['PCB_BOARD']),**m['clip_data'][i])
        rec(f'PCB_clip_{i}_released_clears_board',not clashes(m['pcb_releases'][i],board,tol))
    for i,(snap,recv,sd) in enumerate(zip(m['snaps'],m['receivers'],m['snap_data'])):
        caught=common_volume(snap.translate((0,0,-.5)),recv)
        released=snap.translate(sd['release_vector_mm']);clear=common_volume(released.translate((0,0,-.5)),recv)
        rec(f'snap_{i}_capture_and_release',caught>tol and clear<=tol,
            blocked_pull_volume_mm3=caught,released_pull_volume_mm3=clear,**sd,
            scope='rigid released poses + linear strain estimate; force/fatigue/print qualification unverified')
    checks['PCB_insert_from_REAR_with_clips_held_released']=board_insertion_fixture(parts,m,p)
    # Snap flexure is not pretended to be rigid interference-free closure.
    movable=Compound([m['rear'],m['battery'],m['adhesive'],m['protection']])
    for s in m['snaps']:movable=movable-s
    movable=Compound([movable,*[s.translate(sd['release_vector_mm']) for s,sd in zip(m['snaps'],m['snap_data'])]])
    pose_hits=[]
    for dz in np.linspace(-20,0,5):
        hh=clashes(movable.translate((0,0,float(dz))),[('front',m['front']),*m['caps'].items(),*board],tol)
        if hh:pose_hits.append({'z_offset_mm':float(dz),'collisions':hh})
    rec('rear_closure_with_snaps_released_sampled',not pose_hits,collisions=pose_hits,
        sample_count=5,continuous_or_wired_assembly_proof=False)
    # MIC is a closed six-face proxy. Look for actual modeled substrate holes near it.
    mb=bounds(parts['MIC1']);edges=[]
    for e in parts['PCB_BOARD'].edges():
        if e.geom_type==GeomType.CIRCLE:
            c=e.arc_center
            if mb[0]-.5<c.X<mb[3]+.5 and mb[1]-.5<c.Y<mb[4]+.5:edges.append({'center_mm':list(c),'radius_mm':e.radius})
    reserve=box([mb[0]-.5,mb[1]-.5,floor,mb[3]+.5,mb[4]+.5,mb[2]])
    hits=clashes(reserve,[*all_new,*board],tol)
    rec('MIC_internal_rear_reservation_only',not hits,collisions=hits,reserve_bounds_mm=bounds(reserve),port_direction_verified=False,housing_acoustic_hole_cut=False)
    acoustic={'microphone':'MIC1 (only V1 microphone)','codec':'ES8311 (not microphone)',
        'package_face_count':len(parts['MIC1'].faces()),'package_bounds_mm':mb,'modeled_PCB_circle_edges_near_MIC':edges,
        'port_direction':'UNVERIFIED','hole_drilled':False,'recording_comparison':'NOT_PERFORMED',
        'short_rear_path_candidate_mm':mb[2]-floor,'front_path':'not proven; PCB/glass can obstruct, do not drill',
        'speaker_crosstalk':'UNVERIFIED; separate foam perimeter and no rigid speaker-to-PCB mount'}
    # Destructive probes exercise the SAME geometry and size detectors.
    negatives={}
    b=bounds(probe);block=box([b[0]+1,b[1]+.5,b[2]+1,b[3]-1,b[1]+1,b[5]-1])
    negatives['blocked_USB']=bool(clashes(probe,[('blocked',m['rear']+block)],tol))
    negatives['battery_into_PCB']=bool(clashes(m['battery'].translate((-50,0,0)),board,tol))
    negatives['hidden_external_foot']=max(bounds(m['rear'].translate((0,0,-1)))[5],zhi)-min(bounds(m['rear'].translate((0,0,-1)))[2],zlo)>p['target_thickness_mm']+.5
    negatives['broken_snap_catch']=common_volume(m['snaps'][0].translate((0,0,-.5)),m['receivers'][0].translate((10,0,0)))<=tol
    if p.get('variant')=='A':
        ex97=p['outer_x_min_mm']+p['initial_width_mm']
        wall97=box([ex97-p['wall_mm'],p['outer_y_mm'][0],floor,ex97,p['outer_y_mm'][1],m['dimensions']['glass_and_front_z_mm']])
        v97=common_volume(m['protection'],wall97)
        negatives['97mm_protection_hits_right_wall']=v97>tol
        rec('fixed_layout_width_and_right_bay_clearance',m['protection'].distance_to(m['rear'])>=p['minimum_rigid_gap_mm'],
            protection_to_rear_mm=m['protection'].distance_to(m['rear']),
            right_wall_net_x_clearance_mm=p['outer_x_min_mm']+p['width_mm']-p['wall_mm']-bounds(m['protection'])[3],
            fixed_layout_minimum_width_mm=bounds(m['protection'])[3]+p['wall_mm']+p['minimum_rigid_gap_mm']-p['outer_x_min_mm'],
            rejected_97mm_protection_wall_overlap_mm3=v97,
            scope='minimum for retained provisional accessory layout only; not a global packing optimum')
    rec('negative_fixtures',all(negatives.values()),fixtures={k:{'detected':v} for k,v in negatives.items()})
    return checks,acoustic,tf
