"""Finite G-V1 assembly checks, including continuous conservative lid opening.

Exact CAD partitions cover ALL fixed rear material; analytic rotational AABBs
then bound every angle in the first-corner lift. No mesh or sampled-pose pass
is substituted for that conservative clearance proof.
"""
import math
from build123d import Axis,Compound
from model import box_between as box
from reference import bounds
from p1_checks import clashes,common_volume,intersection,translated_box_sweep
from t0_e_gate import source_clashes
from t0_g_v1_closure import released
from t0_wiring import build_wiring


def rotational_box(shape,pivot_y,pivot_z,angle):
    b=bounds(shape);ys=[];zs=[]
    for y in [b[1],b[4]]:
      for z in [b[2],b[5]]:
        dy,dz=y-pivot_y,z-pivot_z
        aa=[0,angle]
        for root in [math.atan2(-dz,dy),math.atan2(dy,dz)]:
          aa += [root+k*math.pi for k in [-2,-1,0,1,2] if 0<root+k*math.pi<angle]
        for a in aa:
            ys.append(pivot_y+dy*math.cos(a)-dz*math.sin(a))
            zs.append(pivot_z+dy*math.sin(a)+dz*math.cos(a))
    return box([b[0],min(ys),min(zs),b[3],max(ys),max(zs)])


def rear_cells(fixed,m,base,q):
    """Exact low ring / inner base / high ribs, split only at actual notches."""
    d=m['closure_dimensions'];rb,floor=d['rear_bottom_mm'],d['rear_floor_mm'];ot=d['outer_rabbet_top_mm'];b=bounds(fixed)
    ub=bounds(m['usbcut']);ey=base['outer_y_mm'][1];wall=base['wall_mm'];pieces=[]
    xs=[b[0],ub[0]-1.2,ub[3]+1.2,b[3]];ys=[b[1],ey-wall-.3,b[4]]
    for x0,x1 in zip(xs,xs[1:]):
      for y0,y1 in zip(ys,ys[1:]):
        pieces+=list(intersection(fixed,box([x0,y0,rb-.01,x1,y1,ot])).solids())
    # Local latch root pads extend past the inner plate's straight side. Split
    # at that datum so their AABB does not invent a raised strip along the wall.
    core_right=base['outer_x_min_mm']+base['width_mm']-base['wall_mm']-q['registration_radial_clearance_mm']
    for xa,xb in [(b[0],core_right),(core_right,b[3])]:
        pieces+=list(intersection(fixed,box([xa,b[1],ot,xb,b[4],floor])).solids())
    dy=q['receiver_half_y_mm']+.2
    high_ys=[b[1],b[4]]+[s['y_mm']+a for s in q['clip_sites'] for a in [-dy,dy]]
    for stop in m['stops']:
        bb=bounds(stop);high_ys += [bb[1]-.2,bb[4]+.2]
    high_ys=sorted(set(max(b[1],min(b[4],y)) for y in high_ys))
    for y0,y1 in zip(high_ys,high_ys[1:]):
        pieces+=list(intersection(fixed,box([b[0],y0,floor,b[3],y1,b[5]+.01])).solids())
    pieces=[s for s in pieces if s.volume>1e-8]
    error=abs(sum(s.volume for s in pieces)-fixed.volume)/fixed.volume
    assert error<1e-6
    return pieces,error


def evaluate(parts,mounts,m,base,kq,q,wiring_builder=build_wiring):
    tol=base['volume_tolerance_mm3'];source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    plugs,wires,wiredata=wiring_builder(parts,base,m)
    accessories=[(k,m[k]) for k in ['battery','adhesive','protection','speaker','foam','damping']]+list(plugs.items())+[(f'{k}_wire_{i}',s) for k,ss in wires.items() for i,s in enumerate(ss)]
    installed=[('FRONT',m['front']),('REAR',m['rear']),*accessories]
    print('G-V1: nominal source and installed-pair checks',flush=True)
    src={k:source_clashes(s,parts,source,tol) for k,s in installed}
    pairs=[]
    for i,(name,s) in enumerate(installed):
      for other,t in installed[i+1:]:
        v=common_volume(s,t)
        if v>tol:pairs.append(dict(a=name,b=other,volume_mm3=v))
    insertion=clashes(translated_box_sweep(parts['ASSEMBLY'],(0,0,-20)),[('FRONT',m['front'])],tol)
    fixed=m['rear']
    for row in m['rear_clips']:fixed-=row['free']
    cells,coverage=rear_cells(fixed,m,base,q)
    print(f'G-V1: continuous lid paths, {len(cells)} exact fixed-rear partitions',flush=True)
    obstacles=[('FRONT',m['front']),*source,*[(k,m[k]) for k in ['speaker','foam','damping']]]
    straight=[dict(cell=i,**hit) for i,s in enumerate(cells) for hit in clashes(translated_box_sweep(s,(0,0,-20)),obstacles,tol)]
    axis=Axis((0,q['upper_bearing_pivot_y_mm'],m['closure_dimensions']['rear_floor_mm']),(1,0,0))
    angle=math.asin(q['first_corner_pull_mm']/(q['upper_bearing_pivot_y_mm']-q['clip_sites'][0]['y_mm']))
    deg=math.degrees(angle);py=q['upper_bearing_pivot_y_mm'];pz=m['closure_dimensions']['rear_floor_mm']
    tilt=[dict(cell=i,**hit) for i,s in enumerate(cells) for hit in clashes(rotational_box(s,py,pz,angle),obstacles,tol)]
    final_path=[dict(cell=i,**hit) for i,s in enumerate(cells) for hit in clashes(translated_box_sweep(rotational_box(s,py,pz,angle),(0,0,-20)),obstacles,tol)]
    # Battery and its fixation follow lid; speaker stays on its provisional
    # front foam adhesive. This is not a verified real lead service-loop model.
    moving_accessory=[dict(part=k,hits=clashes(rotational_box(m[k],py,pz,angle),obstacles,tol)) for k in ['battery','adhesive','protection']]
    print('G-V1: two clips and one sequential plastic pick',flush=True)
    cliprows=[];held=[];toolrows=[]
    for i,row in enumerate(m['rear_clips']):
        rel,point,theta=released(row,m,q);held.append(rel)
        a=row['clip_x_mm'][0];tool_y=row['root_y']+row['direction']*q['clip_tool_point_from_root_mm']
        pick=row['pick'];pressed=pick.rotate(Axis((a,tool_y,0),(0,0,1)),theta).translate((point,0,0))
        # Source/front checks use the true whole tool at endpoints; the bounded
        # near-case corner covers its entire ordered pressing rotation.
        pb=bounds(pick);crop=box([pb[0]-1,pb[1]-1,-11.8,pb[3]+1,pb[4]+1,pb[5]+.1]);near=intersection(pick,crop);near2=intersection(pressed,crop)
        b0,b1=bounds(near),bounds(near2);eps=.01
        envelope=box([min(b0[j],b1[j])-eps for j in range(3)]+[max(b0[j],b1[j])+eps for j in range(3,6)])
        static_obs=[('FRONT',m['front']),('fixed_REAR',fixed),*source,*[(k,m[k]) for k in ['battery','speaker','protection']]]
        endpoint=clashes(pressed,static_obs,tol);presspath=clashes(envelope,static_obs,tol)
        entry=clashes(translated_box_sweep(near,(0,0,-25)),static_obs,tol)
        # Existing U-slot is the access path, not a .15mm special shim lane.
        toolrows.append(dict(index=i,plastic_pick_thickness_mm=q['tool_thickness_mm'],point_displacement_mm=point,
            insertion=entry,near_corner_press_envelope=presspath,pressed_endpoint=endpoint,
            pick_to_held_beam_overlap_mm3=common_volume(pressed,rel),
            second_access_with_lid_tilt=clashes(rotational_box(envelope,py,pz,angle),[('FRONT',m['front']),*source],tol) if i else [],
            material_tool_force='UNVERIFIED: actual plastic pick stiffness/edge and PA12 force; no printed tool or simultaneous holding set'))
        # Both held paths bound straight closure; automatic lead-in force is
        # unverified. Each can return in its own receiving pocket at closure.
        heldpath=clashes(translated_box_sweep(rel,(0,0,-20)),obstacles,tol)
        heldfixed=clashes(rel,[('FRONT',m['front']),('fixed_REAR',fixed),*source],tol)
        if i==0:
            opening=clashes(rotational_box(rel,py,pz,angle),obstacles,tol)
            end_relax=clashes(row['free'].rotate(axis,deg),obstacles,tol)
            # Bound intermediate relaxation at the opened pose with a union
            # AABB: hook is now behind receiver, not trapped under its lip.
            rr,hh=row['free'].rotate(axis,deg),rel.rotate(axis,deg);r0,r1=bounds(rr),bounds(hh)
            returnbox=box([min(r0[j],r1[j]) for j in range(3)]+[max(r0[j],r1[j]) for j in range(3,6)])
            end_return=clashes(returnbox,obstacles,tol)
        else:
            # Inactive upper tooth remains within its groove until the same
            # single tool is moved to the second U-slot.
            rb=m['closure_dimensions']['rear_bottom_mm'];floor=m['closure_dimensions']['rear_floor_mm'];hz=q['hook_z_mm'][0]
            inactive=[]
            rf=bounds(row['free'])
            for z0,z1 in [(rb-.01,floor),(floor,hz),(hz,q['hook_z_mm'][1]+.01)]:
                s=intersection(row['free'],box([rf[0]-.1,rf[1]-.1,z0,rf[3]+.1,rf[4]+.1,z1]))
                for t in s.solids():inactive+=clashes(rotational_box(t,py,pz,angle),obstacles,tol)
            opening=inactive;end_relax=[];end_return=[]
        cliprows.append(dict(index=i,y_mm=row['y'],held_straight_closure=heldpath,held_at_closed=heldfixed,
            first_lift_or_second_retained_envelope=opening,lower_relaxed_at_first_lift=end_relax,
            lower_continuous_relax_at_first_lift=end_return,
            receiver_hold_probe_mm3=common_volume(row['free'].translate((0,0,-q['rearward_play_mm']-.01)),m['front']),
            root_fixed_point_load_strain_estimate=3*(q['clip_x_mm'][1]-q['clip_x_mm'][0])*q['clip_release_mm']/((q['clip_tool_point_from_root_mm']-q['clip_root_fixed_mm'])*(3*(q['clip_length_mm']-q['clip_root_fixed_mm'])-(q['clip_tool_point_from_root_mm']-q['clip_root_fixed_mm'])))))
    # Screw mating metal alone is excluded from screw-envelope collision tests.
    mb=[bounds(s) for s in mounts];nonmetal=[(n,s) for n,s in source if not any(max(abs(a-b) for a,b in zip(bounds(s),bb))<1e-5 for bb in mb)];assert len(nonmetal)==719
    screwrows=[]
    from t0_model import cyl
    for row,s in zip(m['screw_rows'],m['screws']):
        x,y=row['axis_xy_mm'];tool=cyl(q['driver_diameter_mm']/2,row['head_bottom_mm']-25,row['head_bottom_mm']+.1,x,y)
        screwrows.append(row|dict(nonmating_source=clashes(s,nonmetal,tol),rear_clearance=clashes(s,[('REAR',m['rear'])],tol),
            driver_access=clashes(tool,[('FRONT',m['front']),('REAR',m['rear']),*source],tol),
            head_bearing_area_mm2=math.pi*((q['head_diameter_mm']/2)**2-(q['shaft_bore_diameter_mm']/2)**2)))
    usb=clashes(m['usbprobe'],[('FRONT',m['front']),('REAR',m['rear']),*source],tol)
    tb=bounds(parts['TF']);ty=(tb[1]+tb[4])/2;tz=(tb[2]+tb[5])/2
    tf=clashes(box([base['outer_x_min_mm']-20,ty-5.5,tz-.5,tb[0],ty+5.5,tz+.5]),[('FRONT',m['front']),('REAR',m['rear']),*source],tol)
    from build123d import Cylinder,Align
    from p1_model import contact_face
    fb=bounds(contact_face(parts['KEY3']));py,pzc=m['key_data']['KEY3']['center_yz_mm'];ox=base['outer_x_min_mm']
    pin=Cylinder(.4,fb[3]+.01-(ox-10),align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-10,py,pzc))
    key3b=bounds(parts['KEY3']);notreset=[(n,s) for n,s in source if max(abs(a-b) for a,b in zip(bounds(s),key3b))>1e-5];assert len(notreset)==722
    reset=clashes(pin,[('FRONT',m['front']),('REAR',m['rear']),*notreset],tol)
    negative_pick=m['rear_clips'][0]['pick']+m['rear_clips'][0]['pick'].translate((-.3,0,0))
    negative_volume=common_volume(negative_pick,fixed)
    assert negative_volume>tol,'Gate must reject a 1.1mm pick in a 1mm U-slot'
    bb=bounds(Compound([parts['ASSEMBLY'],m['front'],m['rear'],*m['screws'],*[s for _,s in accessories]]))
    from t0_g_v1_retained_bounds import evaluate as retained_bounds
    retained=retained_bounds(parts,m,q);maxretained=retained['maximum_thickness_mm']
    bad=bool(any(src.values()) or pairs or insertion or straight or tilt or final_path or any(r['hits'] for r in moving_accessory) or usb or tf or reset or maxretained>12.400001)
    bad=bad or any(r[k] for r in cliprows for k in ['held_straight_closure','held_at_closed','first_lift_or_second_retained_envelope','lower_relaxed_at_first_lift','lower_continuous_relax_at_first_lift'])
    bad=bad or any(r[k] for r in toolrows for k in ['insertion','near_corner_press_envelope','pressed_endpoint','second_access_with_lid_tilt'])
    bad=bad or any(r[k] for r in screwrows for k in ['nonmating_source','rear_clearance','driver_access'])
    bad=bad or any(r['receiver_hold_probe_mm3']<=tol for r in cliprows)
    report=dict(status='BLOCKED_FULL_ASSEMBLY_GATE' if bad else 'NOMINAL_FULL_ASSEMBLY_GATE_PASS_PHYSICAL_PENDING',
        source_collisions=src,installed_pair_collisions=pairs,complete_board_insertion=insertion,
        fixed_rear_exact_partition=dict(cells=len(cells),relative_volume_error=coverage),
        fixed_rear_continuous_straight_closure=straight,fixed_rear_continuous_first_lift=tilt,
        fixed_rear_continuous_final_withdrawal=final_path,first_lift_degrees=deg,
        moving_battery_group_during_first_lift=moving_accessory,clips=cliprows,single_pick=toolrows,four_screws=screwrows,
        USB_independent_body=usb,TF_independent_card=tf,RESET_pin_to_native_key_only=reset,
        negative_too_thick_pick=dict(thickness_mm=1.1,U_slot_mm=1.0,actual_fixed_rear_overlap_mm3=negative_volume,rejected=True),conditional_wiring=wiredata,
        closed_complete_bounds_mm=bb,closed_maximum_thickness_mm=bb[5]-bb[2],maximum_with_retained_rear_play_mm=maxretained,
        retained_rigid_pose_bound=retained,
        assembly_order=['FRONT down on clean soft support; do not flip unscrewed module; support native metal mounting parts when handling',
            'Complete board straight from REAR; integral keys stay at rest, no caps to install',
            'Route conditional leads; close rear with two shallow lead-in hooks, then four M2.5x4 machine screws from REAR',
            'Opening: FRONT down, remove ALL four PCB screws first; PCB stays in FRONT on soft support',
            'One .8mm plastic pick in lower existing U-slot, deflect beam outward; lift lower lid corner2.2mm, then release/remove same pick',
            'Move same pick to upper existing U-slot; release second, withdraw lid; real service-lead slack/unplug access pending'],
        limits=['No verified PA12 force, fatigue, creep, print tolerance approval or actual switch travel.',
                'A single pick is moved between two existing latch U-slots; no four simultaneous shims or 8.3mm held module withdrawal.',
                'PCB does not follow lid after all screws removed. Workbench/soft-support handling required; no open-shell flip restraint.',
                'Conditional plugs/lead endpoints, battery and speaker remain unverified; static routing is not real connector/lead qualification.',
                'MIC_AUDIO_PATH_BLOCKED_UNTIL_HARDWARE. No speculative sound hole.'])
    return report,held,accessories


def additional_fit_checks(parts,m,base,kq,q,front,accessories):
    """Nominal screw interference and conditional full XY/print reach."""
    screws=[dict(index=i,hits=clashes(s,[('FRONT',front),*accessories,*[(f'other_screw_{j}',t) for j,t in enumerate(m['screws']) if i!=j]],base['volume_tolerance_mm3'])) for i,s in enumerate(m['screws'])]
    assert not any(r['hits'] for r in screws)
    # The bore play is not the only XY freedom: include the rear register's
    # nominal radial clearance too. Keep this conditional PRINT-fit witness
    # separate from the verified nominal insertion geometry and native travel.
    from generate_t0_g_v1_integrated import shortened
    from t0_g_v1_integrated_keys import press_pose
    combined=q['registration_radial_clearance_mm']+kq['pcb_xy_radial_play_mm']
    reach=[]
    for row in m['integrated_keys']:
        error,_=shortened(row,kq);pose,_=press_pose(error,base,kq,kq['candidate_stop_mm'])
        native=parts[row['key']].translate((combined,0,0))
        reach.append(dict(key=row['key'],PCB_X_mm=combined,printed_tip_undersize_mm=kq['printed_feature_offset_budget_mm'],gap_at_shell_stop_mm=pose.distance_to(native),native_overlap_mm3=common_volume(pose,native)))
    combined_report=dict(status='BLOCKED_CONDITIONAL_PRINT_FIT' if any(r['gap_at_shell_stop_mm']>.001 for r in reach) else 'CONTACT_ONLY_FUNCTION_UNVERIFIED',witnesses=reach,
        limits='Rear register .2 plus screw-bore radial .15 are cumulative freedoms. Printed-tip .3 undersize is a conditional guide-tolerance budget, not measured hardware. Nominal insertion gates do not certify this combined manufactured fit.')


    return dict(screw_to_other_nonmating_parts=screws,combined_register_bore_print_reach=combined_report)
