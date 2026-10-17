"""Conditional two-conductor envelopes; no claimed matching plug or lead location."""
from build123d import FilletPolyline,Plane,Circle,sweep
from reference import bounds
from model import box_between as box


def build_wiring(parts,p,m):
    plugs={};wires={};data={}
    for index in range(2):
        name=f'MX{index}';b=bounds(parts[name]);yc=(b[1]+b[4])/2;zc=p['wire_source_z_mm']
        x=b[0];proj=p['plug_projection_x_mm'];wy,wz=p['plug_yz_mm'];start=x-proj
        plug=box([start,yc-wy/2,zc-wz/2,x,yc+wy/2,zc+wz/2]);plugs[name]=plug
        loop=p['wire_loop_y_mm'][index];xx=start-p['wire_retreat_mm']
        pair=[];paths=[]
        for offset in [0.0]:
            # One circumscribed 1.5mm bundle encloses two 0.7mm wires in any cross-section rotation; never count overlapping conductor solids as separate parts.
            yy=yc;ll=loop;zz=zc+offset;bay=p['wire_bay_x_mm'];destx,desty=p['wire_staging_xy_mm'][index];frontz=p['wire_front_z_mm']+offset
            if index==0:
                spbay=p['speaker_wire_bay_x_mm'];spz=p['speaker_wire_z_mm']+offset
                pts=[(start,yy,zz),(xx,yy,zz),(xx,ll,zz),(spbay,ll,zz),(spbay,ll,spz),(spbay,desty,spz),(destx,desty,spz)]
            else:
                pts=[(start,yy,zz),(xx,yy,zz),(xx,ll,zz),(bay,ll,zz),(bay,ll,frontz),(destx,ll,frontz),(destx,desty,frontz)]
            path=FilletPolyline(*pts,radius=p['wire_bend_radius_mm'])
            profile=Plane(origin=pts[0],z_dir=(-1,0,0))*Circle(p['wire_bundle_radius_mm'])
            pair.append(sweep(profile,path=path));paths.append(pts)
        wires[name]=pair
        data[name]={'socket_bounds_mm':b,'opening_direction_inferred_from_cavity':[-1,0,0],
                    'plug_body_status':'unverified','wire_spec_and_bend_radius_status':'unverified',
                    'function_identity':'upper/lower connector occurrence; SPK/BAT association requires board/official silkscreen confirmation',
                    'destination_candidate':'speaker lead staging' if index==0 else 'battery lead staging above cell',
                    'wire_centerline_polyline_before_fillets_mm':paths,'bend_radius_mm':p['wire_bend_radius_mm'],
                    'terminal_connection_verified':False,'wire_model':'circumscribed bundle, not individual conductor simulation','bundle_diameter_mm':2*p['wire_bundle_radius_mm']}
    return plugs,wires,data
