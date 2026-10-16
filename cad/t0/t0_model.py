"""T0: flush glass, independent PCB clips; B screws or A peripheral snaps."""
import math
from build123d import (Align,Axis,Box,Cylinder,Sphere,Plane,RectangleRounded,Rectangle,
                      RegularPolygon,Polyline,FilletPolyline,Circle,extrude,loft,sweep,Compound)
from model import box_between as box
from reference import bounds,hole_axes
from p1_model import contact_face,usb_mouth_face,FUNCTIONS


def cyl(r,z0,z1,x,y):
    return Cylinder(r,z1-z0,align=(Align.CENTER,Align.CENTER,Align.MIN)).translate((x,y,z0))


def rr(w,h,r,z0,z1,x,y):
    return extrude(RectangleRounded(w,h,r),amount=z1-z0).translate((x,y,z0))


def build(parts,mounts,p,kp):
    db=bounds(parts['DISPLAY']);top=db[5];bottom=top-p['target_thickness_mm'];floor=bottom+p['rear_panel_mm']
    ox=p['outer_x_min_mm'];ex=ox+p['width_mm'];oy,ey=p['outer_y_mm'];wall=p['wall_mm'];split=p['split_z_mm'];sg=p['seam_gap_mm']
    ix=db[0]-p['panel_xy_clearance_mm'];jx=db[3]+p['panel_xy_clearance_mm'];iy=oy+wall;jy=ey-wall
    def outer(z0,z1):return rr(ex-ox,ey-oy,p['corner_radius_mm'],z0,z1,(ox+ex)/2,(oy+ey)/2)
    front=outer(split+sg/2,top)-box([ix,iy,split-1,jx,jy,top+1])
    # Hollow bay behind a front grille plate, separate from the full glass opening.
    front=front-box([jx+wall,iy,split-1,ex-wall,jy,top-p['bay_front_panel_mm']])
    rear=outer(bottom,split-sg/2)-box([ix,iy,floor,ex-wall,jy,top+1])
    supports=[];pcb_clips=[];pcb_releases=[];clip_data=[]
    pb=bounds(parts['PCB_BOARD']);support_z=pb[2];stop_z=pb[5]+p['pcb_clip_front_gap_mm']
    for i,(x,y,r) in enumerate(hole_axes(parts['PCB_BOARD'])):
        if i not in p.get('pcb_clip_indices',[0,1,2,3]):continue
        side=1 if x>0 else -1;end=y;root=y+(p['pcb_clip_beam_length_mm'] if y<0 else -p['pcb_clip_beam_length_mm'])
        ya,yb=sorted([root,end]);xc=side*p['pcb_clip_beam_x_abs_mm'];t=p['pcb_clip_beam_thickness_mm'];zh=p['pcb_clip_beam_height_mm']
        beam_z=p['pcb_clip_beam_bottom_z_mm']
        beam=box([xc-t/2,ya,beam_z,xc+t/2,yb,beam_z+zh])
        # Free space for sideways deflection, independent of rear cover position.
        slot=box([min(xc-t/2-side*1.4,xc-t/2)-.1,ya-.3,-5.3,
                  max(xc+t/2+side*1.4,xc+t/2)+.1,yb+.3,-3.3])
        if 'pcb_clip_outward_relief_mm' in p:
            # E only: cover the EXISTING clip's entire outward envelope, including
            # its rear bearing/front stop, with correct sign on the left side.
            relief=side*p['pcb_clip_outward_relief_mm'];half=p['pcb_clip_bearing_y_mm']/2
            slot=box([min(xc-t/2,xc-t/2+relief)-.1,min(ya,end-half)-.2,p['pcb_clip_slot_bottom_z_mm'],
                      max(xc+t/2,xc+t/2+relief)+.1,max(yb,end+half)+.2,p['pcb_clip_slot_top_z_mm']])
        # Both signs get a deliberately generous side slot; the inside is vacant.
        front=front-slot
        anchor=box([min(xc-1,side*28),root-.7,-5.5,max(xc+1,side*28),root+.7,-2.5])
        xl,xh=sorted([side*p['pcb_clip_edge_x_mm'],xc+side*t/2]);half=p['pcb_clip_bearing_y_mm']/2
        hook=box([xl,end-half,support_z-p['pcb_rear_bearing_thickness_mm'],xh,end+half,support_z])
        upright=box([xc-t/2,end-half,-6.5,xc+t/2,end+half,-3.7])
        stop=box([xl,end-half,stop_z,xh,end+half,stop_z+p['pcb_front_stop_thickness_mm']])
        clip=beam+upright+hook+stop
        front=front+anchor+clip
        rear=rear-box([xl-.2,end-half-.2,-6.8,xh+.2,end+half+.2,-6.1])
        pcb_clips.append(clip);supports.append(hook);pcb_releases.append(clip.translate((side*p['pcb_clip_release_mm'],0,0)))
        clip_data.append({'mount_axis_mm':[x,y],'clip_edge_x_mm':side*p['pcb_clip_edge_x_mm'],
                          'PCB_REAR_support_z_mm':support_z,'FRONT_stop_z_mm':stop_z,'beam_length_mm':yb-ya,
                          'release_direction':[side,0,0],'beam_strain_estimate':1.5*t*p['pcb_clip_release_mm']/(yb-ya)**2,
                          'front_stop_thickness_mm':bounds(stop)[5]-bounds(stop)[2],'front_stop_to_LCD_mm':stop.distance_to(parts['DISPLAY']),
                          'front_stop_to_PCB_mm':stop.distance_to(parts['PCB_BOARD']),'strain_is_linear_estimate_not_material_approval':True})
    # P1 actuator datums and load-path dimensions retained; new enclosure thickness is independent.
    caps={};key_data={};features={}
    for key,fn in FUNCTIONS.items():
        fb=bounds(contact_face(parts[key]));yc=(fb[1]+fb[4])/2;zc=(fb[2]+fb[5])/2
        tip=fb[0]-kp['key_contact_gap_mm'];sy,sz=kp['key_stem_yz_mm'];ty,tz=kp['key_tip_yz_mm']
        f0=ox+kp['key_flange_rest_offset_mm'];f1=f0+kp['key_flange_thickness_mm'];fw,fh=kp['key_flange_yz_mm']
        stem0=ox+(kp['reset_recess_mm'] if fn=='RESET' else -kp['key_head_motion_gap_mm'])
        be=tip-kp['key_tip_projection_mm'];tr=be+kp['key_tip_transition_mm']
        body0=ox+p['reset_face_stock_mm'] if fn=='RESET' and p.get('variant')=='A' else stem0
        body=box([body0,yc-sy/2,zc-sz/2,be,yc+sy/2,zc+sz/2]);contact=box([tr,yc-ty/2,zc-tz/2,tip,yc+ty/2,zc+tz/2])
        transition=loft([(Plane.YZ*Rectangle(sy,sz)).translate((be,yc,zc)),(Plane.YZ*Rectangle(ty,tz)).translate((tr,yc,zc))])
        if body0>stem0:
            body=body+Cylinder(p['reset_nose_radius_mm'],body0-stem0+.1,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((stem0,yc,zc))
        flange=box([f0,yc-fw/2,zc-fh/2,f1,yc+fw/2,zc+fh/2]);cap=body+contact+transition+flange
        if fn!='RESET':
            hw,hh=kp['key_head_yz_mm'];head=extrude(Plane.YZ*RectangleRounded(hw,hh,kp['key_head_corner_mm']),amount=kp['key_head_depth_mm']).translate((stem0-kp['key_head_depth_mm'],yc,zc));cap=cap+head
        gc=kp['key_guide_clearance_mm'];ac=kp['key_axial_clearance_mm'];motion=kp['key_cap_design_motion_mm']
        pocket=box([f0-ac,yc-fw/2-gc,zc-fh/2-gc,f1+motion+ac,yc+fw/2+gc,zc+fh/2+gc])
        guide0=(ox+p['reset_face_stock_mm'] if p.get('variant')=='A' else stem0-gc) if fn=='RESET' else ox-1
        pocket=pocket+box([guide0,yc-sy/2-gc,zc-sz/2-gc,tip+gc,yc+sy/2+gc,zc+sz/2+gc])
        if fn=='RESET':pocket=pocket+Cylinder(kp['reset_hole_radius_mm'],2,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-1,yc,zc))
        front=front-pocket;rear=rear-pocket;caps[key]=cap
        features[key]={'body':body,'contact':contact,'transition':transition,'flange':flange}
        key_data[key]={'function':fn,'static_actuator_face_bounds_mm':fb,'center_yz_mm':[yc,zc],'flange_x_mm':[f0,f1],
                       'body_start_x_mm':body0,'body_end_x_mm':be,'tip_root_x_mm':tr,'tip_x_mm':tip}
    # Two bay screws close the shells; PCB clips stay attached when rear is removed.
    screws=[];nuts=[];bosses=[];screw_data=[]
    seat=bottom+p['m2_head_recess_mm']+p['m2_head_height_mm'];tip=seat+p['m2_length_mm']
    for x,y in p['m2_axes_xy_mm']:
        boss=cyl(p['m2_boss_radius_mm'],p['m2_front_contact_z_mm'],top-p['bay_front_panel_mm']+.1,x,y)
        bore=cyl(1.15,bottom-1,tip+.1,x,y)
        nutz=tip-p['m2_nut_height_mm'];nut=extrude(RegularPolygon(p['m2_nut_af_mm']/math.sqrt(3),6),amount=p['m2_nut_height_mm']).translate((x,y,nutz))-cyl(1.0,nutz-.1,tip+.1,x,y)
        trap=extrude(RegularPolygon((p['m2_nut_af_mm']+.35)/math.sqrt(3),6),amount=p['m2_nut_height_mm']+.2).translate((x,y,nutz-.1))
        # Radial loading slot permits installing the stock nut from the open rear bay.
        load=box([x-4,y-2.35,nutz-.1,x,y+2.35,tip+.1])
        boss=boss-bore-trap-load;front=(front+boss)-bore-trap-load
        rear=rear-cyl(p['m2_boss_radius_mm']+.2,p['m2_front_contact_z_mm'],top,x,y)
        rear=rear+cyl(p['m2_boss_radius_mm'],floor,p['m2_front_contact_z_mm'],x,y)
        rear=rear-bore-cyl(p['m2_head_radius_mm']+.3,bottom-.1,seat,x,y)
        screw=cyl(1.0,seat,tip,x,y)+cyl(p['m2_head_radius_mm'],seat-p['m2_head_height_mm'],seat,x,y)
        screws.append(screw);nuts.append(nut);bosses.append(boss);screw_data.append({'axis_mm':[x,y],'head_bottom_z_mm':seat-p['m2_head_height_mm'],'tip_z_mm':tip,'head_seat_z_mm':seat,'nut_z_mm':[nutz,tip]})
    # Four peripheral horizontal beams; free tips engage open-sided receiver windows.
    snaps=[];receivers=[];snap_data=[]
    for sign in p.get('snap_edge_signs',[-1,1]):
        inner=iy if sign<0 else jy
        for end in p['snap_free_x_mm']:
            root=end-p['snap_beam_length_mm'];yc=inner-sign*.8
            beam=box([root,yc-.5,-8.3,end+.6,yc+.5,-7.3])
            upper=box([end-.6,min(inner-sign*.4,inner+sign*.6),-6.9,end+.6,max(inner-sign*.4,inner+sign*.6),-5.9])
            lower=box([end-.6,yc-.5,-8.3,end+.6,yc+.5,-5.9])
            snap=beam+lower+upper
            rootblock=box([root-.5,min(inner,yc-.5),-9.0,root+1.0,max(inner,yc+.5),-7.3])
            recv=box([end-1.6,min(inner,inner+sign*wall),-8.6,end+1.6,max(inner,inner+sign*wall),-5.4])
            window=box([end-1.0,min(inner-sign*.1,inner+sign*(wall+.1)),-7.1,end+1,max(inner-sign*.1,inner+sign*(wall+.1)),-5.6])
            recv=recv-window
            channel=box([end-1.8,min(inner-sign*2.4,inner+sign*wall),-8.8,end+1.8,max(inner-sign*2.4,inner+sign*wall),-5.6])
            front=front-channel+recv
            clearance=box([end-1.8,min(inner-sign*.2,inner+sign*(wall+.2)),-8.8,end+1.8,max(inner-sign*.2,inner+sign*(wall+.2)),split+1])
            rear=rear-clearance+rootblock+snap
            snaps.append(snap);receivers.append(recv);snap_data.append({'free_x_mm':end,'edge_sign':sign,'release_vector_mm':[0,-sign*p['snap_release_mm'],0],'strain_estimate':1.5*p['snap_beam_thickness_mm']*p['snap_release_mm']/p['snap_beam_length_mm']**2})
    # Additional long-edge snaps use the same beam/window geometry rotated 90deg.
    for spec in p.get('side_snaps',[]):
        right=spec['side']=='right';sign=-1 if right else 1
        inner=-(ex-wall if right else ox+wall);end=spec['end_y_mm'];root=end-p['snap_beam_length_mm'];yc=inner-sign*.8
        def turn(s):return s.rotate(Axis.Z,90)
        beam=box([root,yc-.5,-8.3,end+.6,yc+.5,-7.3])
        upper=box([end-.6,min(inner-sign*.4,inner+sign*.6),-6.9,end+.6,max(inner-sign*.4,inner+sign*.6),-5.9])
        lower=box([end-.6,yc-.5,-8.3,end+.6,yc+.5,-5.9]);snap=turn(beam+lower+upper)
        rootblock=turn(box([root-.5,min(inner,yc-.5),-9,root+1,max(inner,yc+.5),-7.3]))
        recv=box([end-1.6,min(inner,inner+sign*wall),-8.6,end+1.6,max(inner,inner+sign*wall),-5.4])
        window=box([end-1,min(inner-sign*.1,inner+sign*(wall+.1)),-7.1,end+1,max(inner-sign*.1,inner+sign*(wall+.1)),-5.6]);recv=turn(recv-window)
        channel=turn(box([end-1.8,min(inner-sign*2.4,inner+sign*wall),-8.8,end+1.8,max(inner-sign*2.4,inner+sign*wall),-5.6]))
        clearance=turn(box([end-1.8,min(inner-sign*.2,inner+sign*(wall+.2)),-8.8,end+1.8,max(inner-sign*.2,inner+sign*(wall+.2)),split+1]))
        front=front-channel+recv;rear=rear-clearance+rootblock+snap
        snaps.append(snap);receivers.append(recv);snap_data.append({'side':spec['side'],'end_y_mm':end,'release_vector_mm':[sign*p['snap_release_mm'],0,0],'strain_estimate':1.5*p['snap_beam_thickness_mm']*p['snap_release_mm']/p['snap_beam_length_mm']**2})
    # Discrete, non-locking registration pads: no extra clamp path through the cell.
    registrations=[]
    if p.get('variant')=='A':
        for y in p['registration_centers_y_mm']:
            pad=box([ex-wall-.6,y-1,-7.5,ex-wall+.2,y+1,-5.8])
            rear=rear-box([ex-wall-.8,y-1.2,-7.7,ex-wall+.4,y+1.2,split+.2])
            front=front+pad;registrations.append(pad)
    b=p['battery'];bw,bh,bt=b['xyz_mm'];bx,by=b['center_xy_mm'];bz=floor+b['adhesive_mm']
    battery=box([bx-bw/2,by-bh/2,bz,bx+bw/2,by+bh/2,bz+bt]);adhesive=box([bx-bw/2,by-bh/2,floor,bx+bw/2,by+bh/2,bz])
    c=b['tray_clearance_mm'];tw=b['tray_wall_mm'];h=b['tray_height_mm']
    tray=rr(bw+2*c+2*tw,bh+2*c+2*tw,1.5,floor-.05,floor+h,bx,by)-rr(bw+2*c,bh+2*c,.6,floor-.1,floor+h+.1,bx,by)
    # Open the right fence for the unverified protection tab/lead envelope.
    protection=box([bx+bw/2+.7,5,bz,bx+bw/2+.7+b['protection_xyz_mm'][0],5+b['protection_xyz_mm'][1],bz+b['protection_xyz_mm'][2]])
    tray=tray-box([bx+bw/2,4,floor-.1,bx+bw/2+4,14,floor+h+1]);rear=rear+tray
    s=p['speaker'];sw,sh,st=s['xyz_mm'];sx,sy=s['center_xy_mm'];sf=top-p['bay_front_panel_mm']-s['foam_mm']
    speaker=box([sx-sw/2,sy-sh/2,sf-st,sx+sw/2,sy+sh/2,sf])
    damping=box([sx-sw/2,sy-sh/2,sf-st-s['damping_mm'],sx+sw/2,sy+sh/2,sf-st])
    foam=rr(sw,sh,1,sf,sf+s['foam_mm'],sx,sy)-rr(sw-4,sh-4,.5,sf-.1,sf+s['foam_mm']+.1,sx,sy)
    for j in range(s['slot_count']):
        yy=sy+(j-(s['slot_count']-1)/2)*s['slot_pitch_mm'];front=front-rr(s['grille_xy_mm'][0],s['slot_mm'],s['slot_mm']/2-.01,top-2,top+1,sx,yy)
    # Speaker perimeter fence attaches to FRONT plate; no rear compression stack.
    sc=s['tray_clearance_mm'];stw=s['tray_wall_mm']
    fence=rr(sw+2*sc+2*stw,sh+2*sc+2*stw,1.5,sf-st-.3,top-.2,sx,sy)-rr(sw+2*sc,sh+2*sc,.5,sf-st-.4,top+.1,sx,sy)
    fence=fence-box([sx-sw/2-2,sy-1.3,sf-st-1,sx-sw/2+.1,sy+1.3,top+1])
    front=front+fence
    # Rear-accessible wiring relief in the side partition, away from MIC1.
    ca,cb=p['wire_partition_channel_x_mm'];da,dbb=p['wire_partition_channel_y_mm']
    front=front-box([ca,da,-8.0,cb,dbb,-2.8])
    # USB cut and independent cable envelope use different configured profiles.
    ub=bounds(usb_mouth_face(parts['J2_USB_SIDE']));ux=(ub[0]+ub[3])/2;uz=(ub[2]+ub[5])/2;uw,uh=p['usb_opening_xz_mm']
    usbcut=box([ux-uw/2,ub[4]-.3,uz-uh/2,ux+uw/2,ey+1,uz+uh/2]);front=front-usbcut;rear=rear-usbcut
    pw,ph=p['usb_plug_body_xz_mm'];usbprobe=box([ux-pw/2,ub[4],uz-ph/2,ux+pw/2,ey+30,uz+ph/2])
    # TF candidate corridor; independent inserted card path is measured separately.
    tb=bounds(parts['TF']);ty=(tb[1]+tb[4])/2;tz=(tb[2]+tb[5])/2
    tfcut=box([ox-1,ty-6.2,tz-.8,tb[0]+.2,ty+6.2,tz+.8]);front=front-tfcut;rear=rear-tfcut
    # Small edge radii stay within the flush/thickness envelope.
    def soften(shape,z):
        edges=[]
        for e in shape.edges():
            eb=bounds(e)
            if abs(eb[2]-z)<1e-5 and abs(eb[5]-z)<1e-5 and any(abs(eb[i]-v)<1e-5 for i,v in [(0,ox),(3,ex),(1,oy),(4,ey)]):edges.append(e)
        return shape.fillet(p['edge_radius_mm'],edges)
    front=soften(front,top);rear=soften(rear,bottom)
    front.label='FRONT_T0_FLUSH';rear.label='REAR_T0_1_2mm'
    return dict(front=front,rear=rear,caps=caps,key_data=key_data,cap_features=features,pcb_clips=pcb_clips,pcb_releases=pcb_releases,
                supports=supports,clip_data=clip_data,screws=screws,nuts=nuts,bosses=bosses,screw_data=screw_data,snaps=snaps,receivers=receivers,snap_data=snap_data,
                battery=battery,adhesive=adhesive,protection=protection,speaker=speaker,damping=damping,foam=foam,usbprobe=usbprobe,usbcut=usbcut,tfcut=tfcut,
                registrations=registrations,dimensions={'outer_x_mm':[ox,ex],'outer_y_mm':[oy,ey],'glass_and_front_z_mm':top,'rear_bottom_z_mm':bottom,'rear_inside_z_mm':floor,'target_thickness_mm':p['target_thickness_mm']})
