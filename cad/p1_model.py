"""P1: four shared factory-nut fasteners, split guides, captive key pistons."""
from build123d import Align, Axis, Cylinder, GeomType, Plane, Rectangle, RectangleRounded, extrude, loft
from model import box_between
from reference import bounds

FUNCTIONS = {'KEY1':'BAT_PWR', 'KEY2':'BOOT', 'KEY3':'RESET'}


def cylinder(radius, z0, z1, x, y):
    return Cylinder(radius,z1-z0,align=(Align.CENTER,Align.CENTER,Align.MIN)).translate((x,y,z0))


def contact_face(key):
    """Select the outward, planar actuator face; do not use switch whole-body center."""
    x=bounds(key)[0]
    candidates=[f for f in key.faces() if f.geom_type==GeomType.PLANE
                and f.normal_at().X < -.99 and abs(bounds(f)[0]-x)<.001]
    assert len(candidates)==1, f'Ambiguous actuator face: {len(candidates)}'
    return candidates[0]


def usb_mouth_face(connector):
    """The +Y rim face, not whole J2 bounds (which include raised rear pins)."""
    ymax=bounds(connector)[4]
    candidates=[f for f in connector.faces() if f.geom_type==GeomType.PLANE
                and f.normal_at().Y>.99 and abs(bounds(f)[4]-ymax)<.01]
    assert len(candidates)==1, f'Ambiguous USB mouth: {len(candidates)}'
    return candidates[0]


def make_p1(parts,mounts,holes,p):
    db,ab=bounds(parts['DISPLAY']),bounds(parts['ASSEMBLY'])
    x0,y0,_,x1,y1,zglass=db
    c=p['panel_xy_clearance_mm'];wall=p['wall_mm'];split=p['split_z_mm'];gap=p['seam_gap_mm']
    ix0,iy0,ix1,iy1=x0-c,y0-c,x1+c,y1+c
    ox0,oy0,ox1,oy1=ix0-wall-p['key_side_wall_extra_mm'],iy0-wall,ix1+wall,iy1+wall
    top=zglass+p['front_above_glass_mm'];floor=ab[2]-p['rear_extra_depth_mm'];bottom=floor-wall
    def outer(lo,hi):
        return extrude(RectangleRounded(ox1-ox0,oy1-oy0,p['outer_corner_radius_mm']),amount=hi-lo).translate(((ox0+ox1)/2,(oy0+oy1)/2,lo))
    front=outer(split+gap/2,top)-box_between([ix0,iy0,split-1,ix1,iy1,top+1])
    rear=outer(bottom,split-gap/2)-box_between([ix0,iy0,floor,ix1,iy1,top+1])
    screws=[];pads=[];rails=[];supports=[];mount_data=[]
    sorted_mounts=sorted(mounts,key=lambda m:(round(m.center().X,3),round(m.center().Y,3)))
    for (x,y,r),nut in zip(holes,sorted_mounts):
        nb=bounds(nut);assert abs((nb[0]+nb[3])/2-x)<.05 and abs((nb[1]+nb[4])/2-y)<.05
        padtop=nb[2];padbottom=padtop-p['bracket_thickness_mm']
        pad=cylinder(p['bracket_radius_mm'],padbottom,padtop,x,y)
        # Arm connects a pad under the factory nut to a rail in the perimeter wall.
        right=x>0; railx=(ix1+ox1)/2 if right else (ix0+ox0)/2
        arm=box_between([min(x,railx),y-p['bracket_arm_width_mm']/2,padbottom,
                         max(x,railx),y+p['bracket_arm_width_mm']/2,padtop])
        rw=p['rail_width_mm'];aw=p['bracket_arm_width_mm']
        rail=box_between([railx-rw/2,y-aw/2,padbottom,railx+rw/2,y+aw/2,split+gap/2+1])
        front=front+pad+arm+rail
        # Recess starts at the split and is open to +Z for rear-cover insertion.
        rc=p['rail_clearance_mm']
        pocket=box_between([min(x-p['bracket_radius_mm'],railx-rw/2)-rc,y-max(aw/2,p['bracket_radius_mm'])-rc,
                            padbottom-rc,max(x+p['bracket_radius_mm'],railx+rw/2)+rc,
                            y+max(aw/2,p['bracket_radius_mm'])+rc,split+2])
        rear=rear-pocket
        support=cylinder(p['support_outer_radius_mm'],floor,padbottom,x,y)
        rear=rear+support
        footbottom=floor-p['foot_height_mm']
        rear=rear+cylinder(p['foot_radius_mm'],footbottom,bottom+.1,x,y)
        headseat=footbottom+p['head_recess_depth_mm']
        drill=cylinder(p['mount_screw_clearance_radius_mm'],footbottom-1,top+1,x,y)
        front=front-drill;rear=rear-drill
        rear=rear-cylinder(p['head_recess_radius_mm'],footbottom-1,headseat,x,y)
        screw=(cylinder(p['screw_shaft_radius_mm'],headseat,headseat+p['screw_underhead_length_mm'],x,y)
               +cylinder(p['screw_head_radius_mm'],headseat-p['screw_head_height_mm'],headseat,x,y))
        screw.label=f'M2_5x8_screw_{len(screws)+1}_THREAD_ENVELOPE'
        screws.append(screw);pads.append(pad-drill);rails.append(rail);supports.append(support-drill)
        mount_data.append({'axis_mm':[x,y], 'nut_rear_z_mm':padtop,'pad_bottom_z_mm':padbottom,
                           'head_seat_z_mm':headseat,'foot_bottom_z_mm':footbottom,
                           'tip_z_mm':headseat+p['screw_underhead_length_mm'],
                           'nominal_thread_overlap_mm':min(nb[5],headseat+p['screw_underhead_length_mm'])-padtop,
                           'floor_web_mm':floor-headseat})

    # Short registration tongues on the non-key side, with open grooves in rear cover.
    for yc in p['registration_centers_y_mm']:
        half_length=p['registration_length_mm']/2
        tx=(ix1+ox1)/2;tw=p['seam_tongue_width_mm'];td=p['seam_tongue_depth_mm'];fc=p['seam_fit_clearance_mm']
        tongue=box_between([tx-tw/2,yc-half_length,split-td,tx+tw/2,yc+half_length,split+gap/2+.1])
        groove=box_between([tx-tw/2-fc,yc-half_length-fc,split-td-fc,tx+tw/2+fc,yc+half_length+fc,split+1])
        front=front+tongue;rear=rear-groove

    # Cut dimensions come from enclosure configuration, not from validation probe geometry.
    ub=bounds(usb_mouth_face(parts['J2_USB_SIDE']));ucx=(ub[0]+ub[3])/2;ucz=(ub[2]+ub[5])/2
    uw,uh=p['usb_opening_xz_mm']
    usb_cut=box_between([ucx-uw/2,ub[4]-p['usb_opening_backset_mm'],ucz-uh/2,
                         ucx+uw/2,oy1+1,ucz+uh/2])
    front=front-usb_cut;rear=rear-usb_cut

    caps={};key_data={};key_pockets={};cap_features={}
    for key,function in FUNCTIONS.items():
        face=contact_face(parts[key]);fb=bounds(face)
        # Planar face normal is almost -X (the source board has a tiny in-plane rotation).
        face_x=fb[0];yc=(fb[1]+fb[4])/2;zc=(fb[2]+fb[5])/2
        tip=face_x-p['key_contact_gap_mm'];sy,sz=p['key_stem_yz_mm'];clear=p['key_guide_clearance_mm']
        fw,fh=p['key_flange_yz_mm'];ft=p['key_flange_thickness_mm'];stroke=p['key_cap_design_motion_mm']
        flange0=ox0+p['key_flange_rest_offset_mm'];flange1=flange0+ft
        if function=='RESET':
            stem0=ox0+p['reset_recess_mm']
        else:
            stem0=ox0-p['key_head_motion_gap_mm']
        ty,tz=p['key_tip_yz_mm'];body_end=tip-p['key_tip_projection_mm']
        tip_root=body_end+p['key_tip_transition_mm']
        body=box_between([stem0,yc-sy/2,zc-sz/2,body_end,yc+sy/2,zc+sz/2])
        transition=loft([(Plane.YZ*Rectangle(sy,sz)).translate((body_end,yc,zc)),
                         (Plane.YZ*Rectangle(ty,tz)).translate((tip_root,yc,zc))])
        contact=box_between([tip_root,yc-ty/2,zc-tz/2,tip,yc+ty/2,zc+tz/2])
        flange=box_between([flange0,yc-fw/2,zc-fh/2,flange1,yc+fw/2,zc+fh/2])
        cap=body+transition+contact+flange
        cap_features[key]={'body':body,'flange':flange,'contact':contact,'transition':transition}
        if function!='RESET':
            hw,hh=p['key_head_yz_mm']
            head=extrude(Plane.YZ*RectangleRounded(hw,hh,p['key_head_corner_mm']),amount=p['key_head_depth_mm'])
            head=head.translate((stem0-p['key_head_depth_mm'],yc,zc))
            cap=cap+head
        # Split guides capture the flange. A thick body carries the load; only the
        # last short contact pad fits the original actuator. No switch travel inferred.
        axial=p['key_axial_clearance_mm']
        pocket=box_between([flange0-axial,yc-fw/2-clear,zc-fh/2-clear,
                            flange1+stroke+axial,yc+fw/2+clear,zc+fh/2+clear])
        if function=='RESET':
            guide=box_between([stem0-clear,yc-sy/2-clear,zc-sz/2-clear,tip+clear,yc+sy/2+clear,zc+sz/2+clear])
            tool=Cylinder(p['reset_hole_radius_mm'],stem0-ox0+clear+1,
                          align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox0-1,yc,zc))
            pocket=pocket+guide+tool
        else:
            guide=box_between([ox0-1,yc-sy/2-clear,zc-sz/2-clear,tip+clear,yc+sy/2+clear,zc+sz/2+clear])
            pocket=pocket+guide
        front=front-pocket;rear=rear-pocket
        cap.label=f'{key}_{function}_CAP_P1';caps[key]=cap;key_pockets[key]=pocket
        key_data[key]={'function':function,'static_actuator_face_bounds_mm':fb,'face_area_mm2':face.area,
                       'face_normal':list(face.normal_at()),'center_yz_mm':[yc,zc],
                       'tip_x_mm':tip,'body_end_x_mm':body_end,'tip_root_x_mm':tip_root,'rest_gap_mm':p['key_contact_gap_mm'],
                       'cap_motion_budget_mm':stroke,'switch_actual_travel_mm':None,
                       'flange_x_mm':[flange0,flange1],'guide_clearance_per_side_mm':clear,
                       'reset_recess_mm':p['reset_recess_mm'] if function=='RESET' else None,
                       'outer_cage_stock_mm':flange0-axial-ox0,
                       'inner_cage_stock_mm':ix0-(flange1+stroke+axial)}
    front.label='FRONT_P1_shared_screw_brackets';rear.label='REAR_P1_split_guides_and_supports'
    return {'front':front,'rear':rear,'caps':caps,'screws':screws,'pads':pads,'rails':rails,
            'supports':supports,'key_data':key_data,'mount_data':mount_data,'usb_cut':usb_cut,
            'cap_features':cap_features,'key_pockets':key_pockets,'usb_mouth_face_bounds_mm':ub,'dimensions':{'xy_mm':[ox1-ox0,oy1-oy0],
            'main_body_bottom_z_mm':bottom,'front_top_z_mm':top,'floor_top_z_mm':floor,
            'provisional_depth_including_feet_mm':top-min(m['foot_bottom_z_mm'] for m in mount_data),
            'final_device_thickness_mm':None,'outer_x_mm':[ox0,ox1],'outer_y_mm':[oy0,oy1]}}
