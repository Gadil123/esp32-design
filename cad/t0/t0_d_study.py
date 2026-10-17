"""One local D candidate. A missing axial reaction is a stop gate, not a PASS."""
from build123d import Compound, GeomType, Plane, Polygon, extrude
from model import box_between as box
from t0_model import cyl
from t0_c_mount_study import capsule
from reference import bounds


def build(parts, mounts, p, base):
    top = bounds(parts['DISPLAY'])[5]
    bottom = top-p['maximum_thickness_mm']; floor = bottom+p['rear_panel_mm']
    ox=base['outer_x_min_mm']; ex=ox+p['body_xy_mm'][0]
    oy,ey=base['outer_y_mm']; split=base['split_z_mm']; gap=base['seam_gap_mm']
    # A continuous open display passage, with NO front stops/PCB elastic clips.
    db=bounds(parts['DISPLAY']); c=base['panel_xy_clearance_mm']
    aperture=[db[0]-c, oy+base['wall_mm'], db[3]+c, ey-base['wall_mm']]
    outline=box([ox,oy,split+gap/2,aperture[2]+base['wall_mm'],ey,top])
    frame=outline-box([aperture[0],aperture[1],split-1,aperture[2],aperture[3],top+1])
    # Only the board band: no implied finished right-bay enclosure.
    seats=[]; rows=[]
    for i,m in enumerate(sorted(mounts,key=lambda s:(s.center().X,s.center().Y))):
        fs=[f for f in m.faces() if f.geom_type==GeomType.CYLINDER and abs(f.axis_of_rotation.direction.Z)>.99]
        x,y,_=fs[0].axis_of_rotation.position
        outer=max(f.radius for f in fs);metal_z=bounds(m)[2];z=metal_z-p.get('nest_axial_clearance_mm',0)
        r=outer+p['nest_radial_clearance_mm'][i]; e=p['nest_y_elongation_mm'][i]
        h=p['nest_capture_height_mm']+p.get('nest_axial_clearance_mm',0); w=p['nest_wall_mm']
        seat=capsule(r+w,e,floor-.01,z+h,x,y)-capsule(r,e,z,z+h+.1,x,y)
        seat=seat-cyl(p['thread_bore_keepout_radius_mm'],bottom-.1,z+h+.1,x,y)
        patch=box([x-5,y-5,bottom,x+5,y+5,floor])
        seats.append(seat+patch)
        rows.append({'index':i,'axis_xy_mm':[x,y],'metal_back_z_mm':metal_z,'seat_z_mm':z,'axial_clearance_mm':metal_z-z,'nest_radial_clearance_mm':p['nest_radial_clearance_mm'][i],
                     'nest_y_elongation_mm':e,'inner_outer_radius_mm':[r,r+w],'seat_to_floor_mm':z-floor,
                     'wall_capture_mm':p['nest_capture_height_mm'],'cavity_depth_mm':h})
    # ONE right-edge pair. Short vertical relieved wall, not a 12mm horizontal beam.
    y=p['edge_center_y_mm']; half=p['edge_local_half_length_mm']
    wallx=ex-p['receiver_wall_mm']; tx=wallx-p['lap_clearance_mm']; t=p['tongue_thickness_mm']
    tw=p['tongue_width_mm']; wy=p['window_width_mm']
    front=box([wallx,y-half,p['receiver_bottom_z_mm'],ex,y+half,top])
    front=front-box([wallx-.1,y-wy/2,p['window_bottom_z_mm'],ex+.1,y+wy/2,p['window_top_z_mm']])
    rear=box([tx-t-.5,y-half,bottom,ex,y+half,floor])
    rear=rear+box([wallx,y-half,floor-.01,ex,y+half,p['receiver_bottom_z_mm']-p.get('peripheral_stop_gap_mm',gap)])
    # Continuous overlap outside the relief around this ONE tooth.
    edge=tw/2+p['tongue_side_relief_mm']
    setback=p.get('lap_end_setback_mm',0)
    for a,b in [(y-half+setback,y-edge),(y+edge,y+half-setback)]:
        if b-a>1e-6:rear=rear+box([tx-t,a,floor-.01,tx,b,p['lap_top_z_mm']])
    tongue=box([tx-t,y-tw/2,floor-.01,tx,y+tw/2,p['tongue_top_z_mm']])
    pr=p['tooth_projection_mm']
    profile=Plane.XZ*Polygon((tx-.1,p['tooth_bottom_z_mm']),(tx+pr,p['tooth_bottom_z_mm']),
        (tx+pr,p['tooth_tip_top_z_mm']),(tx,p['tongue_top_z_mm']),(tx-.1,p['tongue_top_z_mm']),align=None)
    tooth=extrude(profile,amount=tw).translate((0,y+tw/2,0))
    tongue=tongue+tooth
    edge_rear=rear+tongue
    d=p['release_deflection_mm']; pickz=p['pick_center_z_mm']; ph=p['pick_thickness_z_mm']; pw=p['pick_width_y_mm']
    pick=box([tx-d,y-pw/2,pickz-ph/2,ex+3,y+pw/2,pickz+ph/2])
    return dict(frame=frame,seats=seats,rows=rows,front=front,rear=edge_rear,fixed_rear=rear,tongue=tongue,pick=pick,
        dimensions={'body_target_xy_mm':p['body_xy_mm'],'front_top_z_mm':top,'rear_bottom_z_mm':bottom,'rear_inside_z_mm':floor,
                    'local_max_thickness_mm':top-bottom,'edge_wall_inner_x_mm':wallx,'tongue_outer_x_mm':tx,
                    'hook_overlap_mm':pr-p['lap_clearance_mm'],'compliant_length_to_tip_load_mm':p['tooth_tip_top_z_mm']-floor,
                    'display_aperture_xy_mm':aperture})
