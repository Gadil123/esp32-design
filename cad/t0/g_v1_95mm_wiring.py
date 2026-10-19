"""Conditional bundle clearances, separate from user's successful 40mm fit test.

Lower speaker socket confirmed by user; upper battery/plug details remain checks.
No route length from the obsolete79.46mm proxy is used as a failure criterion.
"""
from build123d import FilletPolyline,Plane,Circle,sweep
from reference import bounds
from model import box_between as box


def build(parts,p,m):
    q=p['narrow_wiring'];plugs={};wires={};data={}
    for i in range(2):
        name=f'MX{i}';b=bounds(parts[name]);y=(b[1]+b[4])/2;z=p['wire_source_z_mm'];start=b[0]-p['plug_projection_x_mm'];xx=start-p['wire_retreat_mm'];wy,wz=p['plug_yz_mm']
        plugs[name]=box([start,y-wy/2,z-wz/2,b[0],y+wy/2,z+wz/2])
        if i==0:
            loop=p['wire_loop_y_mm'][0];bay=q['battery_left_lane_x_mm'];top=q['battery_top_lane_y_mm'];right=q['battery_right_lane_x_mm']
            pts=[(start,y,z),(xx,y,z),(xx,loop,z),(bay,loop,z),(bay,top,z),(right,top,z),(right,q['battery_terminal_y_mm'],z)]
        else:
            loop=q['speaker_loop_y_mm'];bay=q['speaker_left_lane_x_mm'];sz=p['speaker_wire_z_mm'];sy=p['speaker']['center_xy_mm'][1]
            pts=[(start,y,z),(xx,y,z),(xx,loop,z),(bay,loop,z),(bay,loop,sz),(bay,sy,sz),(q['speaker_staging_x_mm'],sy,sz)]
        path=FilletPolyline(*pts,radius=p['wire_bend_radius_mm'])
        wires[name]=[sweep(Plane(origin=pts[0],z_dir=(-1,0,0))*Circle(p['wire_bundle_radius_mm']),path=path)]
        data[name]=dict(socket_bounds_mm=b,opening_direction_inferred_from_cavity=[-1,0,0],
            function_identity=('Upper MX0 routed to battery; final silkscreen/polarity/plug qualification pending' if i==0 else 'Lower MX1 = SPEAKER, explicitly confirmed by user2026-10-20; plug and terminal geometry pending'),
            wire_centerline_polyline_before_fillets_mm=[pts],filleted_centerline_length_mm=path.length,
            bundle_diameter_mm=2*p['wire_bundle_radius_mm'],bend_radius_mm=p['wire_bend_radius_mm'],
            source='Geometric candidate route, not supplier harness CAD. User verified40mm speaker lead at intended placement; does not establish this new endpoint or service slack.',
            terminal_connection_verified=False,plug_body_status='UNVERIFIED',wire_spec_and_bend_radius_status='UNVERIFIED')
    return plugs,wires,data
