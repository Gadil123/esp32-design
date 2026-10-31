"""Finite extra checks for changed bay; inherited gates remain intact."""
import math
from build123d import Compound,Solid,Plane,Vector
from model import box_between as box
from reference import bounds
from p1_checks import clashes,translated_box_sweep,common_volume,intersection
def segment(a,b,r):
    return Solid.make_cylinder(r,math.dist(a,b),Plane(origin=a,z_dir=Vector(b)-Vector(a)))
from t0_model import cyl


def extra_checks(parts,m,mounts,base,kq,c,cfg,accessories):
    tol=base['volume_tolerance_mm3'];source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    boardobs=[('FRONT',m['front']),('REAR',m['rear']),*source]
    speakerpath=clashes(translated_box_sweep(m['speaker'],(0,0,-20)),[('FRONT',m['front']),*source],tol)
    batterypath=clashes(translated_box_sweep(m['battery'],(0,0,20)),[('OPEN_LID',m['rear'])],tol)
    # Conservative whole-battery XY size+position budget, growth/tolerance only
    # toward FRONT. No crushing or fictitious extra protector stack.
    b=bounds(m['battery']);g=cfg['battery_xy_dimension_and_position_budget_mm'];gz=cfg['battery_swelling_candidate_mm']+cfg['battery_z_tolerance_candidate_mm']
    reserve=box([b[0]-g,b[1]-g,b[2],b[3]+g,b[4]+g,b[5]+gz])
    reserveobs=[*boardobs,*[(n,s) for n,s in accessories if n not in ['battery','adhesive']]]
    reservehits=clashes(reserve,reserveobs,tol)
    from t0_g_v1_full_gate import rotational_box
    angle=math.asin(c['first_corner_pull_mm']/(c['upper_bearing_pivot_y_mm']-c['clip_sites'][0]['y_mm']))
    expanded_lift=rotational_box(reserve,c['upper_bearing_pivot_y_mm'],m['closure_dimensions']['rear_floor_mm'],angle)
    expanded_motion=clashes(translated_box_sweep(expanded_lift,(0,0,-20)),[('FRONT',m['front']),*source,*[(n,s) for n,s in accessories if n not in ['battery','adhesive','protection']]],tol)
    x,y=cfg['mic_candidate_xy_mm'];mb=bounds(parts['MIC1']);mx=(mb[0]+mb[3])/2
    pts=[(x,y,-.8),(x,y,-7.1),(mx,y,-7.1),(mx,y,-6.85)]
    air=[segment(a,b,.25) for a,b in zip(pts,pts[1:])]
    airhits=[clashes(s,[*boardobs,*accessories],tol) for s in air]
    bore=segment((x,y,-.51),(x,y,.8),cfg['mic_candidate_diameter_mm']/2)
    borehits=clashes(bore,[('REAR',m['rear']),*source,*accessories],tol)
    sb=bounds(m['speaker']);sc=base['speaker']['tray_clearance_mm'];tw=base['speaker']['tray_wall_mm']
    fence=intersection(m['front'],box([sb[0]-sc-tw-.1,sb[1]-sc-tw-.1,sb[2]-.31,sb[3]+sc+tw+.1,sb[4]+sc+tw+.1,-.5001]))
    receiver_gap=m['rear_clips'][0]['receiver'].distance_to(fence)
    print_budget=kq['printed_feature_offset_budget_mm']
    gap_budget_ok=receiver_gap-2*print_budget>=.2-1e-7
    seat=[]
    for row in m['screw_rows']:
        x0,y0=row['axis_xy_mm'];zone=cyl(3.5,row['head_seat_mm'],row['head_seat_mm']+row['seat_mm'],x0,y0)
        seat.append(dict(seat_mm=row['seat_mm'],material_volume_mm3=common_volume(zone,m['rear'])))
    return dict(**{'pass':not(speakerpath or batterypath or reservehits or expanded_motion or borehits or any(airhits)) and gap_budget_ok},
        receiver_to_speaker_fence_gap_mm=receiver_gap,receiver_fence_gap_after_two_print_budgets_mm=receiver_gap-2*print_budget,each_printed_surface_offset_budget_mm=print_budget,minimum_candidate_gap_after_budget_mm=.2,
        speaker_REAR_installation_and_reverse_removal=speakerpath,battery_installation_into_open_lid_and_removal=batterypath,
        battery_full_measured_bounds_mm=b,expanded_cell_bounds_mm=bounds(reserve),battery_expanded_clearance_hits=reservehits,battery_expanded_continuous_lift_and_removal_hits=expanded_motion,
        battery_XY_dimension_and_position_budget_each_side_mm=g,battery_swelling_candidate_mm=cfg['battery_swelling_candidate_mm'],battery_Z_tolerance_candidate_mm=cfg['battery_z_tolerance_candidate_mm'],
        battery_remaining_front_headroom_after_all_candidates_mm=m['dimensions']['front_z_mm']-base['bay_front_panel_mm']-bounds(reserve)[5],
        microphone_air_probe_points_mm=pts,microphone_air_probe_hits=airhits,microphone_hole_candidate_cut_hits=borehits,
        microphone_actual_port='UNVERIFIED; preserve free-space route to package exterior, do not claim acoustic performance or drill hole',screw_real_rear_material=seat,
        lead_service_motion='UNVERIFIED real harness deformation; rigid-lid/source paths checked, actual lead slack/unplug access remains physical gate')


def structure_comparison(old,m,b0,base,c0,c):
    rows=[]
    for label,bb,cc,mm in [('frozen99.60',b0,c0,old),('candidate95.60',base,c,m)]:
        xwidth=cc['clip_x_mm'][1]-cc['clip_x_mm'][0];z=cc['rear_panel_mm'];ex=bb['outer_x_min_mm']+bb['width_mm']
        eps=.001
        rows.append(dict(version=label,wall_mm=bb['wall_mm'],front_bay_skin_mm=bb['bay_front_panel_mm'],rear_panel_mm=z,
            clip_beam_length_mm=cc['clip_length_mm'],clip_fixed_root_length_mm=cc['clip_root_fixed_mm'],clip_beam_width_mm=xwidth,
            clip_slot_mm=cc['clip_slot_mm'],clip_root_slot_radius_mm=cc['root_radius_mm'],clip_section_area_mm2=xwidth*z,
            clip_section_I_for_in_plane_bending_mm4=z*xwidth**3/12,clip_hook_total_X_width_mm=cc['hook_x_mm'][1]-cc['hook_x_mm'][0],
            clip_hook_inward_projection_mm=cc['clip_x_mm'][0]-cc['hook_x_mm'][0],
            clip_effective_horizontal_retaining_overlap_mm=cc['receiver_x_mm'][1]-cc['hook_x_mm'][0],
            clip_nominal_retaining_area_mm2=(cc['receiver_x_mm'][1]-cc['hook_x_mm'][0])*cc['hook_y_mm'],
            clip_axial_play_mm=cc['rearward_play_mm'],registration_gap_mm=cc['registration_radial_clearance_mm'],registration_width_mm=cc['registration_width_mm'],registration_height_mm=cc['registration_height_mm'],
            minimum_outer_wall_at_release_mm=ex-cc['front_wall_release_x_max_mm'],
            screw_rows=mm['screw_rows'],speaker_fence_wall_mm=bb['speaker']['tray_wall_mm'],speaker_fence_radial_clearance_mm=bb['speaker']['tray_clearance_mm'],
            speaker_pad_count=len(mm['speaker_pads']),speaker_pad_bounds_mm=[bounds(s) for s in mm['speaker_pads']],
            speaker_pad_contact_area_each_mm2=9,speaker_front_foam_candidate_mm=bb['speaker']['foam_mm'],speaker_rear_damping_candidate_mm=bb['speaker']['damping_mm'],
            foam_to_front_seating_area_mm2=common_volume(mm['foam'].translate((0,0,eps)),mm['front'])/eps,
            front_window_to_grille_ligament_mm=bb['speaker']['center_xy_mm'][0]-bb['speaker']['grille_xy_mm'][0]/2-mm['window_bounds_mm'][3],
            outer_right_to_grille_ligament_mm=ex-bb['speaker']['center_xy_mm'][0]-bb['speaker']['grille_xy_mm'][0]/2,
            receiver_inner_edge_to_grille_mm=cc['receiver_x_mm'][0]-bb['speaker']['center_xy_mm'][0]-bb['speaker']['grille_xy_mm'][0]/2,
            receiver_outer_edge_to_sidewall_gap_mm=ex-bb['wall_mm']-cc['receiver_x_mm'][1],
            receiver_root_area_mm2=(cc['receiver_x_mm'][1]-cc['receiver_x_mm'][0])*2*cc['receiver_half_y_mm'],
            front_plate_bridge_to_sidewall_section_mm2=bb['bay_front_panel_mm']*2*cc['receiver_half_y_mm'],
            battery_tray_wall_mm=bb['battery']['tray_wall_mm'],battery_tray_radial_clearance_mm=bb['battery']['tray_clearance_mm'],battery_tray_height_mm=bb['battery']['tray_height_mm']))
    rx0=c0['receiver_x_mm'][0];y=c0['clip_sites'][0]['y_mm'];hy=c0['receiver_half_y_mm']
    zone=box([rx0-.03,y-hy-.2,-10.36,b0['outer_x_min_mm']+b0['width_mm']+.07,y+hy+.2,.8])
    a=intersection(old['front'],zone);b=intersection(m['front'].translate((b0['width_mm']-base['width_mm'],0,0)),zone)
    bridge_delta=(a-b).volume+(b-a).volume
    assert bridge_delta<.001, 'Receiver-root / plate-to-wall primary load path changed'
    return dict(rows=rows,lower_receiver_root_and_outer_wall_load_bridge_delta_mm3=bridge_delta,load_path='4 screw heads -> unchanged PA12 bearing seats -> original metal M2.5 mounts; independent shell shoulders/register. Neither battery nor glass is a clamp stop.',
        limits='Matching local BRep sections and dimensions are not proof of unchanged global stiffness, fatigue, PA12 creep or service force. Narrower span and shifted grille/load positions require physical/supplier confirmation; no FEA or strength certification.')
