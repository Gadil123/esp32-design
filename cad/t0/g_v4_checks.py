"""V4 functional geometry gates, independent of nominal collision summaries.

A successful gate concerns the named proxy/budget only. Missing silicone/lead
measurements remain explicit blockers in checks.json.
"""
import struct
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from build123d import Plane, RectangleRounded, extrude, import_step, GeomType
from model import box_between as box
from p1_checks import intersection, common_volume
from reference import bounds
from t0_model import cyl
from g_v4_interfaces import key_table, key_cutters, xcyl

TOL=1e-6


def overlap(a,b):
    return common_volume(a,b)


def clear(a,b,label):
    n=overlap(a,b)
    assert n<TOL,(label,n,bounds(intersection(a,b)) if n>=TOL else None)
    return round(n,8)


def material(a,b,label):
    n=overlap(a,b)
    assert abs(n-b.volume)<max(TOL,b.volume*1e-6),(label,n,b.volume)
    return round(n,8)


def speaker_notch_probes(base,dimensions):
    """Witnesses across the actual fence wall, independent of its cutter."""
    s=base['speaker'];sx,sy=s['center_xy_mm'];sw,sh,st=s['xyz_mm']
    c=s['tray_clearance_mm'];w=s['tray_wall_mm']
    x0=sx-sw/2-c-w+.02;x1=sx-sw/2-c-.02
    sf=dimensions['front_face_z_mm']-base['bay_front_panel_mm']-s['foam_mm']
    # Check the entire 2.6mm central passage behind the front panel, with
    # a 0.01mm inset to avoid coincident Boolean boundaries.
    opening=box([x0,sy-1.29,sf-st-.28,x1,sy+1.29,-.61])
    edge=sy+sh/2
    # V2/V4's former edge slot must have its fence wall restored, too.
    closed=box([x0,edge-.8,base['speaker_wire_z_mm']-.2,
                x1,edge-.2,base['speaker_wire_z_mm']+.2])
    return opening,closed


def speaker_notch(front,base,dimensions):
    opening,closed=speaker_notch_probes(base,dimensions)
    return dict(reference='V1 central speaker fence gap',
        y_center_mm=base['speaker']['center_xy_mm'][1],nominal_width_y_mm=2.6,
        central_passage_probe_bounds_mm=bounds(opening),
        central_passage_overlap_mm3=clear(front,opening,'speaker central wire notch'),
        former_edge_wall_material_mm3=material(front,closed,'speaker former edge wall'),
        replacement_body_and_real_lead='Thickness 6.8mm user-reported; inherited XY and replacement lead length UNVERIFIED')


def speaker_notch_negative_controls(front,base,dimensions):
    opening,closed=speaker_notch_probes(base,dimensions);rows=[]
    for label,bad,expected in [
        ('Fill central speaker wire passage',front+opening,'speaker central wire notch'),
        ('Reopen former edge wire slot',front-closed,'speaker former edge wall')]:
        try:speaker_notch(bad,base,dimensions)
        except AssertionError as exc:
            assert expected in str(exc),str(exc)
            rows.append(dict(mutation=label,rejected=True,reason=str(exc)))
        else:raise AssertionError(('speaker notch gate missed mutation',label))
    return rows


def speaker_supports(m,base):
    """Read rear pad tops and the speaker from the actual solids."""
    s=base['speaker'];sx,sy=s['center_xy_mm'];sw,sh,_=s['xyz_mm']
    sb=bounds(m['speaker']);db=bounds(m['damping']);rows=[]
    assert abs(sb[5]-sb[2]-s['xyz_mm'][2])<TOL,'speaker body thickness'
    for x in [sx-sw/2+2,sx+sw/2-2]:
        for y in [sy-sh/2+2,sy+sh/2-2]:
            section=intersection(m['rear'],box([x-.5,y-.5,-14,x+.5,y+.5,db[2]+.5]))
            assert section.volume>0,'speaker rear support missing'
            top=bounds(section)[5];gap=sb[2]-top
            assert abs(gap-s['damping_mm'])<TOL,('speaker damping allowance',gap,s['damping_mm'])
            rows.append(dict(xy_mm=[x,y],actual_top_z_mm=top,body_to_support_mm=gap))
    return dict(actual_body_bounds_mm=sb,actual_thickness_mm=sb[5]-sb[2],
        damping_bounds_mm=db,rear_supports=rows,
        damping_vs_rear_mm3=clear(m['damping'],m['rear'],'speaker damping vs rear'),
        physical_compression_and_closed_fit='UNVERIFIED')


def speaker_support_negative_control(m,base):
    s=base['speaker'];sx,sy=s['center_xy_mm'];sw,sh,_=s['xyz_mm']
    x=sx-sw/2+2;y=sy-sh/2+2;z=bounds(m['damping'])[2]
    bad={**m,'rear':m['rear']+box([x-.6,y-.6,z-.01,x+.6,y+.6,z+.1])}
    try:speaker_supports(bad,base)
    except AssertionError as exc:
        assert 'speaker damping allowance' in str(exc),str(exc)
        return dict(mutation='Raise one rear speaker pad by 0.1mm',rejected=True,reason=str(exc))
    raise AssertionError('speaker support gate missed a raised pad')


def retainer_windows(plate,v,ys):
    """Check every complete nominal opening, not only flange-capture witnesses.

    These are air volumes in PA12, not invented silicone dimensions. A closed
    window must fail even while the actual top/body measurements remain unknown.
    """
    k=v['silicone_keys'];rk=k['retainer'];ox=v['outer_x_min_mm'];z=k['z_center']
    rows=[]
    for y in ys:
        window=box([ox-rk['thickness_x_mm']-.01,y-rk['aperture_y_mm']/2,z-rk['aperture_z_mm']/2,
                    ox+.01,y+rk['aperture_y_mm']/2,z+rk['aperture_z_mm']/2])
        # Check the entire reported base projection outside the aperture. This
        # proves nominal retaining material, not a measured flange or pull force.
        by=k['reported_part_mm']['base_y']/2-.01
        bz=k['reported_part_mm']['base_z']/2-.01
        capture=box([ox-rk['thickness_x_mm']+.02,y-by,z-bz,ox-.02,y+by,z+bz])-window
        rows.append(dict(y_mm=y,full_window_overlap_mm3=clear(plate,window,'retainer full window'),
                         full_capture_projection_material_mm3=material(plate,capture,'retainer full capture projection')))
    return rows


def coupon_interface(block,plate,v,clearance):
    """Functional checks on the actual coupon pair, including STEP rereads."""
    k=v['silicone_keys'];rk=k['retainer'];t=key_table(v,clearance)
    ox=t['outer_x'];seat=t['seat_x'];ix=t['inner_x'];z=t['center_z']
    # Independent probes from interface dimensions; do not reuse the solids
    # returned by the coupon constructor or accept its export validity as fit.
    counter=box([ox-.01,-t['pocket_y']/2,z-t['pocket_z']/2,
                 seat,t['pocket_y']/2,z+t['pocket_z']/2])
    tunnel=box([seat,-t['tunnel_y']/2,z-t['tunnel_z']/2,
                ix+.01,t['tunnel_y']/2,z+t['tunnel_z']/2])
    by=k['reported_part_mm']['base_y']/2-.01;bz=k['reported_part_mm']['base_z']/2-.01
    shoulder=box([seat+.02,-by,z-bz,seat+.06,by,z+bz])-tunnel
    bridge=box([ox+.05,-t['pocket_y']/2+.05,k['local_seam_z_mm']+.01,
                seat-.05,t['pocket_y']/2-.05,z-t['pocket_z']/2-.01])
    bridge_thickness=z-t['pocket_z']/2-k['local_seam_z_mm']
    assert bridge_thickness>=k['bridge_required_mm'],('coupon bridge thickness',bridge_thickness)
    result=dict(clearance_per_side_mm=clearance,
        full_counter_overlap_mm3=clear(block,counter,'coupon full counter'),
        full_tunnel_overlap_mm3=clear(block,tunnel,'coupon full tunnel'),
        full_shoulder_material_mm3=material(block,shoulder,'coupon full shoulder'),
        bridge_mm=bridge_thickness,bridge_material_mm3=material(block,bridge,'coupon bridge'),
        retainer=retainer_windows(plate,v,[0]),pair_overlap_mm3=clear(block,plate,'coupon block/bezel'),fasteners=[])
    for y in [-7.4,7.4]:
        pilot=xcyl(rk['pilot_mm']/2-.001,ox+.01,ox+rk['pilot_depth_mm']-.001,y,z)
        passage=xcyl(rk['screw_diameter_mm']/2+.149,ox-rk['thickness_x_mm']-.01,ox+.001,y,z)
        bottom=xcyl(rk['pilot_mm']/2-.01,ox+rk['pilot_depth_mm']+.01,ox+rk['pilot_depth_mm']+.31,y,z)
        result['fasteners'].append(dict(y_mm=y,pilot_overlap_mm3=clear(block,pilot,'coupon pilot'),
            passage_overlap_mm3=clear(plate,passage,'coupon bezel passage'),
            pilot_bottom_material_mm3=material(block,bottom,'coupon pilot bottom')))
    return result


def retainer_reset_window(plate,v):
    k=v['silicone_keys'];p=v['reset_pinhole'];ox=v['outer_x_min_mm']
    opening=xcyl(p['diameter_mm']/2-.001,ox-k['retainer']['thickness_x_mm']-.01,ox+.01,p['y_mm'],p['z_mm'])
    return clear(plate,opening,'retainer RESET full hole')


def interface_negative_controls(plate,fixtures,v):
    """Real Boolean mutations; require rejection by the named functional gate."""
    k=v['silicone_keys'];rk=k['retainer'];ox=v['outer_x_min_mm'];z=k['z_center'];rows=[]
    def rejected(label,gate,expected):
        try: gate()
        except AssertionError as exc:
            assert expected in str(exc),('negative control failed for another reason',label,str(exc))
            rows.append(dict(mutation=label,rejected=True,reason=str(exc)))
        else: raise AssertionError(('functional gate missed negative control',label))
    for y in k['y_mm']:
        seal=box([ox-rk['thickness_x_mm'],y-rk['aperture_y_mm']/2,z-rk['aperture_z_mm']/2,
                  ox,y+rk['aperture_y_mm']/2,z+rk['aperture_z_mm']/2])
        bad=plate+seal
        rejected(f'production retainer window sealed at Y={y}',lambda:retainer_windows(bad,v,k['y_mm']),'retainer full window')
    p=v['reset_pinhole']
    bad=plate+xcyl(p['diameter_mm']/2,ox-rk['thickness_x_mm'],ox,p['y_mm'],p['z_mm'])
    rejected('production retainer RESET hole sealed',lambda:retainer_reset_window(bad,v),'retainer RESET full hole')
    for name,(block,bezel,clearance) in fixtures.items():
        t=key_table(v,clearance)
        seal=box([t['seat_x']+.001,-t['tunnel_y']/2,z-t['tunnel_z']/2,
                  t['inner_x'],t['tunnel_y']/2,z+t['tunnel_z']/2])
        bad=block+seal
        rejected(name+' tunnel sealed',lambda:coupon_interface(bad,bezel,v,clearance),'coupon full tunnel')
        # An empty cavity is insufficient if the seat that stops inward travel
        # has been removed. Exercise the material half of the gate as well.
        cut=box([t['seat_x']-.01,-t['pocket_y']/2,z-t['pocket_z']/2,
                 t['inner_x']+.01,t['pocket_y']/2,z+t['pocket_z']/2])
        bad=block-cut
        rejected(name+' shoulder removed',lambda:coupon_interface(bad,bezel,v,clearance),'coupon full shoulder')
    return rows


def direct_key_readiness(parts,v):
    """Necessary axial span for a directly operated, externally exposed cap.

    Total cap length is a supplier nominal, not a measurement of the post.
    This lower bound needs neither a guessed flange thickness nor a guessed
    post projection. Recessing the finger face or adding a pusher would change
    the architecture and requires an explicit new model and accessibility test.
    """
    k=v['silicone_keys'];rk=k['retainer']
    face=v['outer_x_min_mm']-rk['thickness_x_mm']
    total=k['reported_part_mm']['total_axis_x_including_post']
    rows=[]
    for name in ['KEY1','KEY2']:
        switch_x=bounds(parts[name])[0]
        span=switch_x-face
        rows.append(dict(key=name,external_retainer_plane_x_mm=face,switch_contact_x_mm=switch_x,
            required_face_to_contact_span_mm=span,supplier_nominal_total_x_mm=total,
            missing_span_at_flush_face_mm=max(0,span-total),
            status='BLOCKED_DIRECT_EXTERNAL_CAP_AXIAL_SPAN' if total<span else 'UNVERIFIED'))
    blocked=any(row['status'].startswith('BLOCKED') for row in rows)
    return dict(status='BLOCKED_P1_DIRECT_CAP_LAYOUT' if blocked else 'UNVERIFIED',keys=rows,
        assumption='Direct silicone actuation; finger face at or outside the retainer exterior. No pusher or deep finger well is modeled.',
        limits='Necessary static span only, not a silicone deformation model. A multi-mm stroke or deeply recessed face is not validated by an empty tunnel.',
        resolution='Define measured flange/seat-to-tip and safe travel, then relocate the mounting/access geometry and recheck it. Do not extend the reported post or add an unapproved pusher by assumption.')


def usb_access(m):
    """Independent cable-body probe from the official socket mouth, not usbcut."""
    probe=m['usbprobe']
    return dict(probe_bounds_mm=bounds(probe),
        hits_mm3={name:clear(m[name],probe,'USB independent cable body '+name)
                  for name in ['front','rear','key_bezel']},
        scope='12.2 x 6.3 nominal body from the official mouth; no credit for a narrow metal nose. Real cable/side-load and print fit remain UNVERIFIED.')


def usb_negative_control(m):
    b=bounds(m['usbprobe']);seam=m['v4_parameters']['seam_z_mm']
    blocker=box([b[0]-.6,b[1]+.4,seam-.1,b[3]+.6,b[1]+.8,seam+1.6])
    broken={**m,'rear':m['rear']+blocker}
    try: usb_access(broken)
    except AssertionError as exc:
        assert 'USB independent cable body rear' in str(exc),str(exc)
        return dict(rejected=True,reason=str(exc))
    raise AssertionError('USB gate missed restored register obstruction')


def screen_column(front,sg):
    w,h,r=sg['lip_inner_whr_mm'];gb=sg['glass_bounds_mm']
    x=(gb[0]+gb[3])/2;y=(gb[1]+gb[4])/2;z=gb[5]-.01
    column=extrude(Plane.XY.offset(z)*RectangleRounded(w-.002,h-.002,r-.001),amount=sg['lip_top_z_mm']-z+.1).translate((x,y,0))
    value=clear(front,column,'full rounded screen air column, INCLUDING corners')
    points=[(x,y)]+[(x+sx*(w/2-r),y+sy*(h/2-r)) for sx in [-1,1] for sy in [-1,1]]
    points += [(x+sx*(w/2-.05),y) for sx in [-1,1]]+[(x,y+sy*(h/2-.05)) for sy in [-1,1]]
    probes=[clear(front,cyl(.015,z,sg['lip_top_z_mm']+.1,px,py),'screen ray') for px,py in points]
    return dict(full_inner_column_overlap_mm3=value,center_four_corners_four_edges_overlap_mm3=probes,ray_xy_mm=points,active_display_and_edge_touch_visibility='UNVERIFIED actual active-area outline absent; check verifies geometric lip inner aperture only')


def stl_screen_rays(path,sg,points):
    data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0]
    t=np.array([struct.unpack_from('<12fH',data,84+50*i)[3:12] for i in range(n)]).reshape(-1,3,3)
    results=[]
    for x,y in points:
        a=t[:,0,:];b=t[:,1,:];c=t[:,2,:]
        den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1])
        valid=abs(den)>1e-10;safe=np.where(valid,den,1.)
        u=((b[:,1]-c[:,1])*(x-c[:,0])+(c[:,0]-b[:,0])*(y-c[:,1]))/safe
        vv=((c[:,1]-a[:,1])*(x-c[:,0])+(a[:,0]-c[:,0])*(y-c[:,1]))/safe
        zz=u*a[:,2]+vv*b[:,2]+(1-u-vv)*c[:,2]
        hit=valid&(u>=-1e-8)&(vv>=-1e-8)&(u+vv<=1+1e-8)&(zz>=sg['glass_front_z_mm']-.01)&(zz<=sg['lip_top_z_mm']+.1)
        results.append(int(hit.sum()))
    assert not any(results),('STL screen obstruction',results)
    return results


def interfaces(m,parts,v,base):
    if 'printed_keys' in v:
        from g_v4_slider_checks import check
        return check(m,parts,v)
    f=m['front'];r=m['rear'];bezel=m['key_bezel'];k=v['silicone_keys'];t=key_table(v);rk=k['retainer'];ox=t['outer_x'];zc=t['center_z']
    windows=retainer_windows(bezel,v,k['y_mm'])
    reset_window=retainer_reset_window(bezel,v)
    keys=[]
    for i,y in enumerate(k['y_mm'],1):
        counter,tunnel=key_cutters(t,y)
        switch=parts[f'KEY{i}'];sb=bounds(switch);switch_x=sb[0]
        trigger=xcyl(.4,t['seat_x']+.01,switch_x+.015,y,zc)
        target=overlap(trigger,switch)
        assert target>0,('trigger axis misses switch',i)
        gap_z=zc-t['pocket_z']/2-k['local_seam_z_mm']
        assert gap_z>=k['bridge_required_mm']
        bridge=box([ox+.05,y-t['pocket_y']/2+.05,k['local_seam_z_mm']+.01,t['seat_x']-.05,y+t['pocket_y']/2-.05,zc-t['pocket_z']/2-.01])
        # Seat shoulder and outer bezel overlap the REPORTED base projection.
        # This does not invent a real flange axial thickness or body diameter.
        support=box([t['seat_x']+.02,y-4.5,zc+3.0,t['seat_x']+.04,y+4.5,zc+3.5])
        capture=box([ox-rk['thickness_x_mm']+.02,y-4.5,zc+3.0,ox-.02,y+4.5,zc+3.5])
        keys.append(dict(key=f'KEY{i}',pocket_clear_mm3=clear(f,counter,'full counterbore'),tunnel_clear_mm3=clear(f,tunnel,'full tunnel'),
            diagnostic_axis_clear_mm3=clear(f,trigger,'trigger tool axis'),axis_switch_contact_mm3=target,
            seat_to_switch_x_mm=switch_x-t['seat_x'],seat_to_post_tip_x_mm=None,rest_gap_mm=None,effective_stroke_mm=None,trigger_status='UNVERIFIED: measured seat-to-post and switch travel required; diagnostic axis is NOT a cap/post model',
            pocket_to_local_seam_bridge_mm=gap_z,bridge_material_mm3=material(f,bridge,'key seam bridge'),
            seat_shoulder_material_mm3=material(f,support,'inner seat shoulder'),outer_bezel_capture_material_mm3=material(bezel,capture,'positive outer capture'),
            reported_base_overlap_y_mm=(k['reported_part_mm']['base_y']-rk['aperture_y_mm'])/2,
            reported_base_overlap_z_mm=(k['reported_part_mm']['base_z']-rk['aperture_z_mm'])/2,
            cap_fit='UNVERIFIED: actual top must clear bezel aperture and actual flange must be captured'))
    retainer_screws=[]
    for y,zs in rk['fastener_yz_mm']:
        # Head outside plate; under-head shaft traverses plate then enters PA12.
        hs=ox-rk['thickness_x_mm'];tip=hs+rk['screw_length_mm']
        head=xcyl(rk['head_max_diameter_mm']/2,hs-rk['head_max_height_mm'],hs,y,zs)
        passage=xcyl(.94,hs-.01,ox+.001,y,zs)
        tool=xcyl(1.4,hs-15,hs-.01,y,zs)
        assert ox+rk['pilot_depth_mm']-tip>=.8
        retainer_screws.append(dict(yz_mm=[y,zs],bezel_shaft_clear_mm3=clear(bezel,passage,'retainer shaft'),
            head_vs_shell_mm3=clear(f,head,'retainer head'),tool_vs_shell_mm3=clear(f,tool,'retainer tool'),
            tool_vs_rear_mm3=clear(r,tool,'retainer tool rear'),tool_vs_bezel_mm3=clear(bezel,tool,'retainer tool bezel'),
            pilot_clear_mm3=clear(f,xcyl(rk['pilot_mm']/2-.01,ox+.01,ox+rk['pilot_depth_mm']-.01,y,zs),'retainer pilot'),
            bottom_clearance_mm=ox+rk['pilot_depth_mm']-tip,sku_and_torque='UNVERIFIED'))
    for rs in m['retainer_screws']:
        clear(rs,parts['ASSEMBLY'],'retainer screw vs board')
        for screw in m['screws']: clear(rs,screw,'orthogonal retainer vs shell/PCB screw')
    clear(f,bezel,'bezel/front');clear(r,bezel,'bezel/rear');clear(bezel,parts['ASSEMBLY'],'bezel/board')
    rp=v['reset_pinhole'];sx=bounds(parts['KEY3'])[0]
    entry=ox-rk['thickness_x_mm']
    needle=xcyl(rp['tool_diameter_mm']/2,entry-.01,sx+.02,rp['y_mm'],rp['z_mm'])
    reach=sx-entry;assert rp['tool_free_length_mm']>reach+.5
    hit=overlap(needle,parts['KEY3']);assert hit>0
    other_hits={name:clear(shape,needle,'RESET needle vs '+name) for name,shape in parts.items() if name not in ['ASSEMBLY','KEY3'] and name in ['KEY1','KEY2','DISPLAY','PCB_BOARD','TF']}
    reset=dict(full_tool_path_mm3=clear(f,needle,'RESET full reach'),switch_contact_mm3=hit,reach_from_outer_wall_mm=reach,
        reach_from_retainer_exterior_mm=reach,
        reach_from_front_wall_mm=sx-ox,entry_retainer_exterior_x_mm=entry,
        full_retainer_hole_mm3=reset_window,full_tool_vs_retainer_mm3=clear(bezel,needle,'RESET needle vs installed retainer'),
        tool_diameter_mm=rp['tool_diameter_mm'],required_free_length_mm=rp['tool_free_length_mm'],other_parts=other_hits,status='Nominal reach from installed retainer exterior only; real TS24CA travel/force, tip and safe overtravel UNVERIFIED; do not insert beyond contact')
    return dict(parameter_table=t,keys=keys,retainer_windows=windows,retainer_screws=retainer_screws,service='Install/remove caps along X with bezel removed AFTER front seam closure; remove caps before front lift. Actual cap insertion path UNVERIFIED pending top/body/post.',reset=reset)


def battery(m,v,base):
    bs=v['battery_stack'];b=bounds(m['battery']);seam=v['seam_z_mm']
    assert abs(b[2]-seam-bs['adhesive_mm'])<1e-6
    a=bounds(m['adhesive']);assert abs(a[5]-a[2]-bs['adhesive_mm'])<1e-6
    xy=bs['xy_component_and_position_budget_mm']+bs['shell_surface_budget_mm']
    reserve=box([b[0]-xy,b[1]-xy,b[2]-bs['adhesive_thickness_tolerance_mm'],b[3]+xy,b[4]+xy,b[5]+bs['adhesive_thickness_tolerance_mm']+bs['z_dimension_tolerance_mm']+bs['swelling_allowance_mm']])
    result=dict(actual_battery_bounds_mm=b,adhesive_bounds_mm=a,xy_budget_mm=xy,expanded_reserve_bounds_mm=bounds(reserve),lead='UNMODELED, user confirms screen/mainboard direction; no old MX0 loop',hits={})
    for name in ['front','rear']:
        result['hits'][name+'_battery']=clear(m[name],m['battery'],name+' battery')
        result['hits'][name+'_adhesive']=clear(m[name],m['adhesive'],name+' adhesive')
        result['hits'][name+'_expanded']=clear(m[name],reserve,name+' expanded battery/adhesive tolerance/swelling')
    result['tray_vs_expanded_mm3']=clear(m['battery_tray'],reserve,'tray actual rails vs expanded battery')
    x,y=v['shell_screw']['axes_xy_mm'][2];rad=v['shell_screw']['boss_diameter_mm']/2
    boss=cyl(rad,seam,.7,x,y)
    result['right_top_boss_vs_reserve_mm3']=clear(boss,reserve,'RT boss vs expanded battery')
    result['right_top_boss_vs_actual_tray_mm3']=clear(boss,m['battery_tray'],'RT boss vs actual tray rails')
    result['right_top_distance_to_reserve_mm']=boss.distance_to(reserve)
    result['actual_tray_to_front_mm3']=clear(m['front'],m['battery_tray'],'front vs actual tray')
    # Check intact rail sections, rather than claiming a shaved corner is strong.
    bw,bh,_=base['battery']['xyz_mm'];bx,by=base['battery']['center_xy_mm'];c=bs['tray_clearance_mm'];tw=bs['tray_wall_mm']
    rail=box([bx-2,by+bh/2+c+.01,seam+.1,bx+2,by+bh/2+c+tw-.01,seam+.9])
    result['retained_top_rail_material_mm3']=material(m['battery_tray'],rail,'full retained tray wall')
    result['tray_wall_nominal_mm']=tw
    result['corner_opening']='RT rails end at X=59/Y=34 before boss; retention/adhesive strength remains physical'
    return result


def fasteners(m,v,mounts):
    f,r=m['front'],m['rear'];sc=v['shell_screw'];pc=v['pcb_screw'];B=v['rear_outer_z_mm'];seam=v['seam_z_mm']
    hs=B+sc['head_pocket_depth_mm'];tip=hs+sc['shaft_length_mm'];end=sc['pilot_end_z_mm'];rad=sc['boss_diameter_mm']/2
    rows=[]
    for i,(x,y) in enumerate(sc['axes_xy_mm']):
        probe=cyl(sc['pilot_diameter_mm']/2-.01,seam+.01,end-.001,x,y)
        bottom=cyl(.7,end+.01,end+.31,x,y)
        head=cyl(sc['head_diameter_mm']/2,B+.001,hs-.001,x,y)
        tool=cyl(sc['tool_diameter_mm']/2,B-15,hs-.01,x,y)
        hole=cyl(sc['head_pocket_diameter_mm']/2-.001,B-.01,hs-.001,x,y)
        shaft=cyl(1.14,hs+.001,seam-.001,x,y)
        web=cyl(rad-.01,end+.01,.69,x,y)
        bearing=cyl(sc['head_pocket_diameter_mm']/2-.01,hs+.02,seam-.02,x,y)-cyl(sc['thread_diameter_mm']/2+.16,hs+.01,seam-.01,x,y)
        wall_proxy=cyl(rad-.01,seam+.2,seam+.4,x,y)-cyl(sc['thread_diameter_mm']/2+.001,seam+.19,seam+.41,x,y)
        cylinders=[face for face in r.faces() if face.geom_type==GeomType.CYLINDER
                   and abs(BRepAdaptor_Surface(face.wrapped).Cylinder().Radius()-sc['head_pocket_diameter_mm']/2)<1e-6
                   and abs(face.axis_of_rotation.position.X-x)<1e-5 and abs(face.axis_of_rotation.position.Y-y)<1e-5]
        assert cylinders,('missing actual diameter 4.2 cylinder',x,y)
        assert end-(hs+sc['shaft_length_max_mm'])-.3-.3 >= .2-1e-8
        wall=rad-sc['thread_diameter_mm']/2
        assert wall>1.5
        assert end-tip>=.8
        assert end-(hs+sc['shaft_length_max_mm'])-.3>=.4-1e-8
        assert seam-hs>=1.5
        rows.append(dict(axis_xy_mm=[x,y],under_head_bearing_material_mm3=material(r,bearing,'actual head bearing ring'),post_wall_material_mm3=material(f,wall_proxy,'actual boss wall ring'),pilot_clear_mm3=clear(f,probe,'M2 pilot'),bottom_material_mm3=material(f,bottom,'M2 blind bottom'),
            head_clear_mm3=clear(r,head,'shell head'),rear_head_pocket_clear_mm3=clear(r,hole,'full rear 4.2 pocket'),rear_shaft_clear_mm3=clear(r,shaft,'rear shaft'),
            tool_front_mm3=clear(f,tool,'shell tool front'),tool_rear_mm3=clear(r,tool,'shell tool rear'),
            tip_z_mm=tip,pilot_end_z_mm=end,bottom_clearance_mm=end-tip,bottom_clearance_length_max_and_pilot_minus_0_3_mm=end-(hs+sc['shaft_length_max_mm'])-.3,
            bottom_clearance_length_max_pilot_minus_0_3_and_seat_plus_0_3_mm=end-(hs+sc['shaft_length_max_mm'])-.3-.3,remaining_solid_bottom_web_mm=.7-end,under_head_bearing_thickness_mm=seam-hs,nominal_thread_envelope_engagement_mm=tip-seam,wall_after_thread_envelope_mm=wall))
    pcb=[]
    for row in m['screw_rows']:
        x,y=row['axis_xy_mm'];seat=row['head_seat_z_mm']
        head=cyl(pc['head_diameter_mm']/2,seat-pc['head_height_mm']+.001,seat-.001,x,y)
        bore=cyl(pc['head_pocket_diameter_mm']/2-.001,B-.01,seat-.001,x,y)
        tool=cyl(2.4,B-15,seat-.01,x,y)
        cylinders=[face for face in r.faces() if face.geom_type==GeomType.CYLINDER
                   and abs(BRepAdaptor_Surface(face.wrapped).Cylinder().Radius()-pc['head_pocket_diameter_mm']/2)<1e-6
                   and abs(face.axis_of_rotation.position.X-x)<1e-5 and abs(face.axis_of_rotation.position.Y-y)<1e-5]
        assert cylinders,('missing actual diameter 5.8 cylinder',x,y)
        bearing=cyl(pc['head_diameter_mm']/2-.01,seat+.02,seat+.52,x,y)-cyl(pc['shaft_bore_diameter_mm']/2+.01,seat+.01,seat+.53,x,y)
        pcb.append(dict(under_head_bearing_material_mm3=material(r,bearing,'PCB real head seat'),axis_xy_mm=[x,y],head_clear_mm3=clear(r,head,'PCB head'),full_5_8_pocket_clear_mm3=clear(r,bore,'PCB 5.8 pocket'),tool_rear_mm3=clear(r,tool,'PCB tool'),metal_thread_overlap_expected=True))
    backfaces=[face for face in r.faces() if face.geom_type==GeomType.PLANE and abs(bounds(face)[2]-B)<1e-5 and abs(bounds(face)[5]-B)<1e-5]
    face=max(backfaces,key=lambda x:x.area)
    assert len(face.wires())==9,('rear face must have outer + 4 shell + 4 PCB wires',len(face.wires()))
    # Real independent seam stop at both sides, away from display/glass.
    stops=[]
    for x,y in [(65.3,0),(-32.6,20)]:
        above=box([x-.15,y-.4,seam+.01,x+.15,y+.4,seam+.11])
        below=above.translate((0,0,-.12))
        stops.append(dict(front_material_mm3=material(f,above,'front seam hard stop'),rear_material_mm3=material(r,below,'rear seam hard stop')))
    return dict(shell=rows,pcb=pcb,rear_bottom_face_wire_count=len(face.wires()),rear_openings='4 x diameter 4.2 + 4 x diameter 5.8',seam_hard_stops=stops,
                sku_pilot_torque='UNVERIFIED supplier low-head plastic screws; head/length envelopes enforced, not DIN7981/ISO7049')
