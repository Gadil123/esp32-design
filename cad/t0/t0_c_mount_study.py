"""Stage gate: actual factory metal standoffs, rear seats and FRONT PCB stops."""
from build123d import GeomType
from t0_model import cyl
from model import box_between as box
from reference import bounds
from p1_checks import common_volume,clashes

def capsule(r,e,z0,z1,x,y):
    if not e:return cyl(r,z0,z1,x,y)
    return cyl(r,z0,z1,x,y-e)+cyl(r,z0,z1,x,y+e)+box([x-r,y-e,z0,x+r,y+e,z1])


def study(parts,mounts,p):
    floor=bounds(parts['DISPLAY'])[5]-p['maximum_thickness_mm']+p['rear_panel_mm'];pb=bounds(parts['PCB_BOARD']);rows=[];seats=[];stops=[]
    board=[(str(i),s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    for i,mount in enumerate(sorted(mounts,key=lambda s:(s.center().X,s.center().Y))):
        axes=[];planes=[]
        for f in mount.faces():
            b=bounds(f)
            if f.geom_type==GeomType.CYLINDER:
                a=f.axis_of_rotation;axes.append({'center':list(a.position),'direction':list(a.direction),'radius_mm':f.radius,'bounds_mm':b})
            elif f.geom_type==GeomType.PLANE:planes.append({'normal':list(f.normal_at()),'area_mm2':f.area,'bounds_mm':b})
        zc=[a for a in axes if abs(a['direction'][2])>.99];x,y,_=zc[0]['center'];mb=bounds(mount)
        outer=max(a['radius_mm'] for a in zc);r=outer+p['rear_nest_radial_clearance_mm'][i];elong=p['rear_nest_y_elongation_mm'][i]
        bottom_face=min((f for f in mount.faces() if f.geom_type==GeomType.PLANE and f.normal_at().Z<-.99),key=lambda f:bounds(f)[2]);seat_z=bounds(bottom_face)[2]
        # No pin enters the threaded bore: a broad rear seat plus a low outer nest.
        seat=(capsule(r+p['rear_nest_wall_mm'],elong,floor-.01,seat_z+p['rear_nest_capture_height_mm'],x,y)-capsule(r,elong,seat_z,seat_z+p['rear_nest_capture_height_mm']+.1,x,y))-cyl(p['thread_bore_keepout_radius_mm'],floor-.1,seat_z+p['rear_nest_capture_height_mm']+.1,x,y)
        # Four simple rigid front stops touch ONLY PCB under axial float.
        stop_z=pb[5]+p['front_stop_PCB_gap_mm'];stop_top=stop_z+p['front_stop_thickness_mm']
        stop=cyl(p['front_stop_outer_radius_mm'],stop_z,stop_top,x,y)-cyl(p['front_stop_inner_radius_mm'],stop_z-.1,stop_top+.1,x,y)
        side=1 if x>0 else -1
        arm=box([min(x,side*p['front_stop_arm_end_x_abs_mm']),y-p['front_stop_arm_width_mm']/2,stop_z,max(x,side*p['front_stop_arm_end_x_abs_mm']),y+p['front_stop_arm_width_mm']/2,stop_top])
        stop=stop+arm
        rows.append({'index':i,'axis_xy_mm':[x,y],'mount_bounds_mm':mb,'cylinders':axes,'planes':planes,
            'rear_floor_to_mount_mm':mb[2]-floor,'nest_radii_mm':[r,r+p['rear_nest_wall_mm']],'slot_y_elongation_mm':elong,'seat_z_mm':seat_z,
            'clear_through_metal_bore_R1_volume_mm3':common_volume(cyl(1,mb[2]-1,mb[5]+.1,x,y),mount),
            'front_tool_display_collision_mm3':common_volume(cyl(1,mb[5],2,x,y),parts['DISPLAY']),
            'rear_seat_board_collisions':clashes(seat,board,.001),'rear_seat_mount_distance_mm':seat.distance_to(mount),
            'front_stop_board_collisions':clashes(stop,board,.001),'front_stop_PCB_distance_mm':stop.distance_to(parts['PCB_BOARD']),
            'front_stop_display_distance_mm':stop.distance_to(parts['DISPLAY'])})
        seats.append(seat);stops.append(stop)
    return rows,seats,stops
