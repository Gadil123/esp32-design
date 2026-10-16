"""Independent interference/path probes and destructive fixture tests for P1."""
import numpy as np
from model import box_between
from reference import bounds
from p1_model import cylinder, usb_mouth_face
from build123d import GeomType,Compound
from functools import lru_cache


@lru_cache(maxsize=8192)
def spatial_bounds(shape):
    return bounds(shape)


def intersection(a,b):
    return Compound(a.intersect(b) or [])


def common_volume(a,b):
    aa,bb=spatial_bounds(a),spatial_bounds(b)
    if any(min(aa[i+3],bb[i+3])-max(aa[i],bb[i])<=1e-7 for i in range(3)):return 0.0
    c=intersection(a,b)
    return c.volume


def clashes(moving,obstacles,tolerance):
    return [{'obstacle':name,'volume_mm3':v} for name,shape in obstacles
            if (v:=common_volume(moving,shape))>tolerance]


def translated_box_sweep(shape,vector):
    """Conservative continuous linear sweep of the shape's AABB, independent of cuts."""
    b=bounds(shape)
    return box_between([b[i]+min(0,vector[i]) for i in range(3)] +
                       [b[i+3]+max(0,vector[i]) for i in range(3)])


def usb_probe(parts,p):
    # A separately sourced cable body profile, placed at the receiver mouth, even
    # without credit for a narrow metal nose. No opening-cutter dimensions reused.
    b=bounds(usb_mouth_face(parts['J2_USB_SIDE']));x=(b[0]+b[3])/2;z=(b[2]+b[5])/2
    w,h=p['usb_plug_body_xz_mm'];y=b[4]+p['usb_mating_y_adjustment_mm']
    return box_between([x-w/2,y,z-h/2,x+w/2,y+p['usb_validation_prism_length_mm'],z+h/2])


def cap_components(cap,data,p):
    # Split at the flange planes to get tighter conservative installation/path boxes.
    b=bounds(cap);f0,f1=data['flange_x_mm']
    cuts=sorted([b[0],f0,f1,data['body_end_x_mm'],data['tip_root_x_mm'],b[3]])
    pieces=[]
    for a,z in zip(cuts,cuts[1:]):
        if z-a<1e-6:continue
        c=intersection(cap,box_between([a,b[1]-1,b[2]-1,z,b[4]+1,b[5]+1]))
        if c is not None and c.volume>1e-8:pieces.extend(c.solids())
    # Head+stem share the outer segment; further separate them at the head/stem joint.
    if data['function']!='RESET':
        joint=b[0]+p['key_head_depth_mm']
        result=[]
        for piece in pieces:
            pb=bounds(piece)
            if pb[0]<joint-1e-5 and pb[3]>joint+1e-5:
                for lo,hi in [(pb[0],joint),(joint,pb[3])]:
                    c=intersection(piece,box_between([lo,pb[1]-1,pb[2]-1,hi,pb[4]+1,pb[5]+1]))
                    if c is not None:result.extend(c.solids())
            else:result.append(piece)
        pieces=result
    return pieces


def axis_error(support,hole,radius):
    axes={(round(e.arc_center.X,5),round(e.arc_center.Y,5)) for e in support.edges()
          if e.geom_type==GeomType.CIRCLE and abs(e.radius-radius)<.001}
    assert len(axes)==1, f'Ambiguous support bore {axes}'
    xy=next(iter(axes))
    return float(np.hypot(xy[0]-hole[0],xy[1]-hole[1]))


def validate(parts,mounts,holes,m,p):
    tol=p['collision_volume_tolerance_mm3'];front,rear=m['front'],m['rear']
    checks={}
    def record(name,passed,**details):
        checks[name]={'pass':bool(passed),**details}
    all_solids=parts['ASSEMBLY'].solids()
    board=[(f'official_solid_{i}',s) for i,s in enumerate(all_solids)]
    print('P1: matching factory nut interfaces',flush=True)
    nut_bounds=[bounds(n) for n in mounts]
    solid_bounds=[bounds(s) for s in all_solids]
    nut_indices={i for i,sb in enumerate(solid_bounds) if any(max(abs(a-b) for a,b in zip(sb,nb))<.001 for nb in nut_bounds)}
    record('identified_factory_thread_interfaces',len(nut_indices)==4,indices=sorted(nut_indices))
    unthreaded_board=[item for i,item in enumerate(board) if i not in nut_indices]
    print('P1: static solids and fastener interfaces',flush=True)
    for name,s in [('front',front),('rear',rear),*m['caps'].items(),*[(f'screw_{i}',s) for i,s in enumerate(m['screws'])]]:
        record(f'valid_{name}',s.is_valid and len(s.solids())==1 and s.volume>0,solid_count=len(s.solids()),volume_mm3=s.volume)
        obstacles=unthreaded_board if name.startswith('screw') else board
        hits=clashes(s,obstacles,tol)
        record(f'board_interference_{name}',not hits,collisions=hits,
               excluded_interfaces='four factory threaded nuts only' if name.startswith('screw') else None)
    built=[('front',front),('rear',rear),*m['caps'].items(),*[(f'screw_{i}',s) for i,s in enumerate(m['screws'])]]
    for i,(name,a) in enumerate(built):
        for other,b in built[i+1:]:
            v=common_volume(a,b);record(f'pair_{name}_{other}',v<=tol,volume_mm3=v)
    for i,(h,stack) in enumerate(zip(holes,m['mount_data'])):
        x,y,_=h
        alignment=axis_error(m['supports'][i],h,p['mount_screw_clearance_radius_mm'])
        record(f'mount_axis_{i}',alignment<.02,error_mm=alignment)
        record(f'fastener_stack_{i}',stack['nominal_thread_overlap_mm']>=2.5-p['geometry_tolerance_mm'] and stack['floor_web_mm']>=1.0-p['geometry_tolerance_mm'],
               **stack,minimum_thread_overlap_mm=2.5,minimum_floor_web_mm=1.0)
        # Direct distance checks of independently imported nut and manufactured support interfaces.
        nut=min(mounts,key=lambda s:abs(s.center().X-x)+abs(s.center().Y-y))
        distances=[m['pads'][i].distance_to(nut),m['pads'][i].distance_to(m['supports'][i])]
        record(f'stack_contact_{i}',max(distances)<.001,interface_distances_mm=distances)
        tool=cylinder(p['head_recess_radius_mm']-.15,stack['foot_bottom_z_mm']-20,
                      stack['head_seat_z_mm']-p['screw_head_height_mm'],x,y)
        record(f'rear_hex_tool_access_{i}',not clashes(tool,[('rear',rear)],tol))

    print('P1: independently sourced USB body probe',flush=True)
    plug=usb_probe(parts,p)
    hits=clashes(plug,[('front',front),('rear',rear),*board],tol)
    distances=[plug.distance_to(s) for s in [front,rear]]
    record('usb_body_insertion_prism',not hits and min(distances)>=p['usb_min_lateral_clearance_mm'],
           collisions=hits,minimum_shell_distances_mm=distances,probe_bounds_mm=bounds(plug),
           basis='StarTech USB2CC1MNC body X/Z; conservative prism begins at receiver mouth; shoulder/nose not credited')
    # This check is deliberately named a boolean operation check, not insertion proof.
    cuts=[common_volume(m['usb_cut'],s) for s in [front,rear]]
    record('usb_boolean_cut_only',max(cuts)<=tol,volumes_mm3=cuts)

    print('P1: continuous conservative board insertion and cap paths',flush=True)
    board_sweep=translated_box_sweep(parts['ASSEMBLY'],[0,0,p['assembly_translation_mm']])
    hits=clashes(board_sweep,[('front',front)],tol)
    record('board_insert_from_FRONT_continuous_AABB',not hits,collisions=hits,
           translation_mm=[0,0,-p['assembly_translation_mm']],sweep_bounds_mm=bounds(board_sweep))
    for key,cap in m['caps'].items():
        data=m['key_data'][key];pieces=cap_components(cap,data,p)
        # Verify material remains at the closed ends of the capture cavity, away
        # from the stem opening. These witness solids must be fully in the shell.
        yc,zc=data['center_yz_mm'];ox=m['dimensions']['outer_x_mm'][0]
        f0,f1=data['flange_x_mm'];gc=p['key_axial_clearance_mm']
        wall_sections=[(ox,f0-gc),(f1+p['key_cap_design_motion_mm']+gc,ox+p['wall_mm']+p['key_side_wall_extra_mm'])]
        witnesses=[]
        for lo,hi in wall_sections:
            wy=p['key_stem_yz_mm'][0]/2+p['key_guide_clearance_mm']+.1
            witness=box_between([lo,yc+wy,zc+.6,hi,yc+wy+.15,zc+.8])
            material=common_volume(witness,front)+common_volume(witness,rear)
            witnesses.append({'stock_mm':hi-lo,'witness_volume_mm3':witness.volume,'occupied_volume_mm3':material})
        record(f'{key}_capture_wall_stock',all(w['stock_mm']>=p['minimum_key_cage_stock_mm']-p['geometry_tolerance_mm'] and abs(w['witness_volume_mm3']-w['occupied_volume_mm3'])<1e-6 for w in witnesses),sections=witnesses)

        install_hits=[];motion_hits=[]
        for piece in pieces:
            install_hits+=clashes(translated_box_sweep(piece,[0,0,-p['assembly_translation_mm']]),[('front',front),*board],tol)
            motion_hits+=clashes(translated_box_sweep(piece,[p['key_cap_design_motion_mm'],0,0]),[('front',front),('rear',rear)],tol)
        record(f'{key}_install_from_REAR_continuous_AABBs',not install_hits,collisions=install_hits)
        end=cap.translate((p['key_cap_design_motion_mm'],0,0))
        clearances=[cap.distance_to(s) for s in [front,rear]]+[end.distance_to(s) for s in [front,rear]]
        record(f'{key}_guide_motion_continuous_AABBs',not motion_hits and min(clearances)>=p['minimum_key_running_clearance_mm'],collisions=motion_hits,
               shell_clearance_rest_then_end_mm=clearances,minimum_required_mm=p['minimum_key_running_clearance_mm'],
               design_cap_motion_mm=p['key_cap_design_motion_mm'],actual_switch_travel_mm=None)
        # Detect modeled capture boundaries; these are NOT verified safe switch stops.
        outward=clashes(cap.translate((-1.2,0,0)),[('front',front),('rear',rear)],tol)
        inward=clashes(cap.translate((1.2,0,0)),[('front',front),('rear',rear)],tol)
        record(f'{key}_outward_retention_stop',bool(outward),blocking_intersections=outward)
        record(f'{key}_inward_capture_boundary',bool(inward),blocking_intersections=inward)
        # Actual switch is static; first contact is a measured gap, not a travel claim.
        rest_distance=cap.distance_to(parts[key])
        record(f'{key}_no_preload',rest_distance>=p['key_contact_gap_mm']-.001,rest_distance_mm=rest_distance)
        # Beyond contact, allow only the bounded static actuator footprint. This is
        # virtual clearance accounting, not a simulated/verified switch deflection.
        fb=data['static_actuator_face_bounds_mm']
        allowance=box_between([fb[0]-.001,fb[1]-.001,fb[2]-.001,
                              fb[3]+p['key_cap_design_motion_mm'],fb[4]+.001,fb[5]+.001])
        virtual_hits=[]
        for dx in np.linspace(0,p['key_cap_design_motion_mm'],5):
            moved=cap.translate((float(dx),0,0))
            for name,s in board:
                if common_volume(moved,s)>tol:
                    common=intersection(moved,s)
                    outside=common-allowance
                    if outside.volume>tol:virtual_hits.append({'translation_mm':float(dx),'obstacle':name,'unallowed_volume_mm3':outside.volume})
        record(f'{key}_virtual_path_except_static_actuator',not virtual_hits,collisions=virtual_hits,
               switch_actuation_verified=False)
    # Tool must reach a recessed RESET piston through a separate circular opening.
    reset=m['key_data']['KEY3'];yc,zc=reset['center_yz_mm'];ox=m['dimensions']['outer_x_mm'][0]
    from build123d import Cylinder,Align,Axis
    reset_tool=Cylinder(p['reset_tool_radius_mm'],p['reset_recess_mm']+.8,
                        align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-.8,yc,zc))
    hits=clashes(reset_tool,[('front',front),('rear',rear)],tol)
    record('RESET_recessed_tool_access',not hits and reset['reset_recess_mm']>0,collisions=hits,
           minimum_shell_distance_mm=min(reset_tool.distance_to(s) for s in [front,rear]))

    print('P1: sampled rear closure and screw insertion',flush=True)
    closure=[]
    for dz in np.linspace(-p['assembly_translation_mm'],0,p['assembly_samples']):
        hits=clashes(rear.translate((0,0,float(dz))),[('front',front),*m['caps'].items(),*board],tol)
        if hits:closure.append({'offset_z_mm':float(dz),'collisions':hits})
    record('rear_closure_sampled',not closure,collisions=closure,sample_count=p['assembly_samples'],
           continuous_proof=False,scope='rigid linear poses only; handling, torque and deformation unverified')
    for i,screw in enumerate(m['screws']):
        hits=[]
        for dz in np.linspace(-p['assembly_translation_mm'],0,5):
            hits+=clashes(screw.translate((0,0,float(dz))),[('front',front),('rear',rear),*unthreaded_board],tol)
        record(f'screw_{i}_insertion_sampled',not hits,collisions=hits,sample_count=5)

    # Mutation fixtures call the SAME independent detectors; each mutation must fail.
    print('P1: negative fixtures',flush=True)
    negatives={}
    b=bounds(plug);block=box_between([b[0]+1,b[1]+.5,b[2]+1,b[3]-1,b[1]+1.5,b[5]-1])
    negatives['usb_blocked']={'detected':bool(clashes(plug,[('blocked_rear',rear+block)],tol))}
    x,y,r=holes[0];bad_axis_error=axis_error(m['supports'][0].translate((.6,0,0)),holes[0],p['mount_screw_clearance_radius_mm'])
    negatives['mount_axis_offset_0_6mm']={'detected':bool(bad_axis_error>=.02),'error_mm':bad_axis_error}
    obstruction=box_between(bounds(parts['PCB_BOARD']))
    negatives['shell_into_board']={'detected':bool(clashes(front+obstruction,[('PCB_BOARD',parts['PCB_BOARD'])],tol))}
    bad_cap=m['caps']['KEY1'].translate((0,1.2,0))
    negatives['key_guide_misaligned']={'detected':bool(clashes(bad_cap,[('front',front),('rear',rear)],tol))}
    obstruction=box_between([-1,-1,5,1,1,7])
    negatives['board_insertion_blocked']={'detected':bool(clashes(board_sweep,[('front_with_bar',front+obstruction)],tol))}
    for result in negatives.values():
        result['mutated_geometry_check_result']='FAIL' if result['detected'] else 'PASS_UNEXPECTED'
    record('negative_fixtures',all(v['detected'] for v in negatives.values()),fixtures=negatives)
    spatial_bounds.cache_clear()
    return checks,plug
