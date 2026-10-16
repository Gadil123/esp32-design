"""Separate PA12 coupons and explicitly limited switch-frame evidence."""
import math
from build123d import Axis,Align,Cylinder,Plane,Rectangle,RectangleRounded,extrude,loft
from reference import bounds
from model import box_between as box
from t0_model import rr
from p1_model import contact_face
from p1_checks import intersection,common_volume,clashes,translated_box_sweep


def key_fixture(parts,kp,p,gap,key='KEY1'):
    fb=bounds(contact_face(parts[key]));yc=(fb[1]+fb[4])/2;zc=(fb[2]+fb[5])/2;ox=p['outer_x_min_mm']
    reset=key=='KEY3';stem0=ox+(p['reset_body_recess_mm'] if reset else -kp['key_head_motion_gap_mm'])
    tip=fb[0]-kp['key_contact_gap_mm'];be=tip-kp['key_tip_projection_mm'];tr=be+kp['key_tip_transition_mm']
    sy,sz=kp['key_stem_yz_mm'];ty,tz=kp['key_tip_yz_mm'];fw,fh=kp['key_flange_yz_mm']
    f0=ox+p['key_flange_rest_offset_mm'];f1=f0+kp['key_flange_thickness_mm'];ac=p['key_axial_clearance_mm'];motion=kp['key_cap_design_motion_mm']
    cap=box([stem0,yc-sy/2,zc-sz/2,be,yc+sy/2,zc+sz/2])+box([tr,yc-ty/2,zc-tz/2,tip,yc+ty/2,zc+tz/2])
    cap=cap+loft([(Plane.YZ*Rectangle(sy,sz)).translate((be,yc,zc)),(Plane.YZ*Rectangle(ty,tz)).translate((tr,yc,zc))])+box([f0,yc-fw/2,zc-fh/2,f1,yc+fw/2,zc+fh/2])
    if not reset:
        hw,hh=kp['key_head_yz_mm'];cap=cap+extrude(Plane.YZ*RectangleRounded(hw,hh,kp['key_head_corner_mm']),amount=kp['key_head_depth_mm']).translate((stem0-kp['key_head_depth_mm'],yc,zc))
    pocket=box([f0-ac,yc-fw/2-gap,zc-fh/2-gap,f1+motion+ac,yc+fw/2+gap,zc+fh/2+gap])
    guide0=ox+p['reset_face_stock_mm'] if reset else ox-1
    pocket=pocket+box([guide0,yc-sy/2-gap,zc-sz/2-gap,tip+gap,yc+sy/2+gap,zc+sz/2+gap])
    if reset:pocket=pocket+Cylinder(p['reset_initial_candidate_diameter_mm']/2,1+p['reset_face_stock_mm']+.01,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-1,yc,zc))
    hy,hz=p['coupon_half_yz_mm'];split=p['split_z_mm'];seam=p['seam_gap_mm'];depth=p['left_wall_depth_mm']
    front=box([ox,yc-hy,split+seam/2,ox+depth,yc+hy,zc+hz])-pocket
    rear=box([ox,yc-hy,zc-hz,ox+depth,yc+hy,split-seam/2])-pocket
    return front,rear,cap,{'face_bounds_mm':fb,'center_yz_mm':[yc,zc],'body_end_x_mm':be,'flange_x_mm':[f0,f1],'tip_root_x_mm':tr,'body_start_x_mm':stem0,'function':'RESET' if reset else 'EXPOSED'}


def switch_frame_study(parts,kp,p,gap,key):
    front,rear,cap,d=key_fixture(parts,kp,p,gap,key);fb=d['face_bounds_mm'];kb=bounds(parts[key]);yc,zc=d['center_yz_mm']
    # Only the source geometry OUTSIDE the outward actuator footprint is classed
    # as a frame proxy. The source is fused; it cannot prove moving-part identity.
    projected_actuator=box([kb[0]-1,fb[1],fb[2],kb[3]+1,fb[4],fb[5]])
    frame=parts[key]-projected_actuator
    rows=[];outer=p['outer_x_min_mm']+(.2 if key!='KEY3' else p['reset_body_recess_mm']+.1)
    theta=math.degrees(math.atan(2*gap/(d['body_end_x_mm']-outer)))
    for mode in ['translation','tilt_stress']:
        for sy in [-1,1]:
            for sz in [-1,1]:
                pose=cap
                if mode=='tilt_stress':pose=pose.rotate(Axis((outer,yc,zc),(0,1,0)),-sz*theta).rotate(Axis((outer,yc,zc),(0,0,1)),sy*theta)
                pose=pose.translate((0,sy*gap,sz*gap))
                for dx in [0,kp['key_contact_gap_mm'],kp['key_cap_design_motion_mm']]:
                    shifted=pose.translate((dx,0,0));v=common_volume(shifted,frame)
                    area=intersection(contact_face(parts[key]),shifted.translate((.001,0,0))).area
                    rows.append({'source_actuator_face_overlap_at_sample_mm2':area,'mode':mode,'offset_sign_yz':[sy,sz],'advance_mm':dx,'frame_proxy_volume_mm3':v,'frame_proxy_distance_mm':shifted.distance_to(frame)})
    return {'status':'FRAME_PROXY_COLLISION_RISK' if any(r['frame_proxy_volume_mm3']>.001 for r in rows) else 'NO_COLLISION_IN_SAMPLED_PROXY_POSES_FUNCTION_UNVERIFIED',
            'guide_gap_per_side_mm':gap,'source_single_fused_solid':len(parts[key].solids())==1,'actuator_face_bounds_mm':fb,
            'source_frame_proxy_bounds_mm':bounds(frame),'stress_tilt_degrees':theta,'poses':rows,
            'limits':'Static fused STEP; projected actuator prism is an explicit proxy exclusion, not a verified movable part. Sampled poses do not prove continuous tilted operation or legal guide-constrained tilt. No travel/return/force qualification.',
            'actuator_face_probe_nudge_mm':.001,'actual_switch_travel_mm':None,'physical_function_passed':False}


def reset_hole_coupon(diameter,p):
    # Front face is round; open rear relief represents the .8mm face stock.
    part=box([0,-5,-4,3.6,5,4])-box([p['reset_face_stock_mm'],-2,-2,3.7,2,2])
    bore=Cylinder(diameter/2,4,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((-.1,0,0))
    return part-bore
