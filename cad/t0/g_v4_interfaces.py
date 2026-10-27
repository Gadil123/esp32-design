"""Single source of V4 0127 interface geometry. Unknown part dimensions stay None."""
from build123d import Align, Axis, Cylinder
from model import box_between as box


def xcyl(radius, x0, x1, y, z):
    return Cylinder(radius, x1-x0, align=(Align.CENTER, Align.CENTER, Align.MIN)).rotate(Axis.Y,90).translate((x0,y,z))


def key_table(v, clearance=None):
    k=v['silicone_keys']; p=k['pocket']; r=k['reported_part_mm']
    c=p['clearance_per_side_mm'] if clearance is None else clearance
    ox=v['outer_x_min_mm']
    return dict(outer_x=ox, seat_x=ox+p['depth_x_mm'], inner_x=k['wall_inner_x_mm'],
                pocket_y=r['base_y']+2*c, pocket_z=r['base_z']+2*c,
                tunnel_y=p['tunnel_y_mm'], tunnel_z=p['tunnel_z_mm'],
                center_z=k['z_center'], clearance=c)


def key_cutters(t,y):
    z=t['center_z']; ox=t['outer_x']; seat=t['seat_x']; ix=t['inner_x']
    return (box([ox-.01,y-t['pocket_y']/2,z-t['pocket_z']/2,seat,y+t['pocket_y']/2,z+t['pocket_z']/2]),
            box([seat-.001,y-t['tunnel_y']/2,z-t['tunnel_z']/2,ix+.01,y+t['tunnel_y']/2,z+t['tunnel_z']/2]))


def bezel(v,t,ys,ymin,ymax,fastener_ys):
    k=v['silicone_keys']; r=k['retainer']; ox=t['outer_x']; z=t['center_z']; th=r['thickness_x_mm']
    plate=box([ox-th,ymin,k['local_seam_z_mm'],ox,ymax,.7])
    for y in ys:
        plate-=box([ox-th-.01,y-r['aperture_y_mm']/2,z-r['aperture_z_mm']/2,ox+.01,y+r['aperture_y_mm']/2,z+r['aperture_z_mm']/2])
    for position in fastener_ys:
        y,zs=position if isinstance(position,(list,tuple)) else (position,z)
        plate-=xcyl(r['screw_diameter_mm']/2+.15,ox-th-.01,ox+.01,y,zs)
    return plate


def production_bezel(v):
    k=v['silicone_keys'];t=key_table(v)
    plate=bezel(v,t,k['y_mm'],*k['retainer']['outer_y_bounds_mm'],k['retainer']['fastener_yz_mm'])
    # RESET must remain serviceable with the production retainer installed.
    # Single-key coupons do not contain a RESET interface.
    p=v['reset_pinhole'];ox=t['outer_x'];th=k['retainer']['thickness_x_mm']
    return plate-xcyl(p['diameter_mm']/2,ox-th-.01,ox+.01,p['y_mm'],p['z_mm'])


def coupons(v):
    """A/B/C independent single-pocket coupons in production axes, no cap guesses."""
    k=v['silicone_keys'];r=k['retainer']; result={}
    for name,c in zip('ABC',k['coupon_clearances_per_side_mm']):
        t=key_table(v,c);ox=t['outer_x'];z=t['center_z']
        block=box([ox,-10,k['local_seam_z_mm'],t['inner_x'],10,.7])
        for cutter in key_cutters(t,0): block-=cutter
        for y in [-7.4,7.4]: block-=xcyl(r['pilot_mm']/2,ox-.01,ox+r['pilot_depth_mm'],y,z)
        plate=bezel(v,t,[0],-10,10,[-7.4,7.4])
        result[f'0127_coupon_{name}']=(block,t)
        result[f'0127_coupon_{name}_bezel']=(plate,t)
    return result
