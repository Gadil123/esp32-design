"""V4 captive sliders: printed head/flange/stem, inserted from outside.

These dimensions define a prototype, not measured switch travel/return force.
The flange, rather than the switch or friction, carries the two hard stops.
"""
from build123d import Align, Axis, Cylinder
from model import box_between as box
from g_v4_interfaces import xcyl
from reference import bounds


def table(v):
    k=v['printed_keys'];r=k['retainer'];ox=v['outer_x_min_mm']
    return dict(outer_x=ox,seat_x=ox+k['flange_thickness_mm']+k['stroke_mm'],
                inner_x=k['wall_inner_x_mm'],center_z=k['z_center'],
                pocket_d=k['flange_diameter_mm']+2*k['radial_clearance_mm'],
                guide_d=k['stem_diameter_mm']+2*k['radial_clearance_mm'],
                aperture_d=k['head_diameter_mm']+2*k['radial_clearance_mm'],
                exterior_x=ox-r['thickness_x_mm'])


def cutters(t,y):
    return (xcyl(t['pocket_d']/2,t['outer_x']-.02,t['seat_x'],y,t['center_z']),
            xcyl(t['guide_d']/2,t['seat_x']-.001,t['inner_x']+.02,y,t['center_z']))


def retainer(v):
    k=v['printed_keys'];r=k['retainer'];t=table(v);ox=t['outer_x'];th=r['thickness_x_mm']
    plate=box([ox-th,*[r['outer_y_bounds_mm'][0],k['local_seam_z_mm']],ox,r['outer_y_bounds_mm'][1],.7])
    for y in k['y_mm']:
        plate-=xcyl(t['aperture_d']/2,ox-th-.02,ox+.02,y,k['z_center'])
    for y,z in r['fastener_yz_mm']:
        plate-=xcyl(r['screw_diameter_mm']/2+.15,ox-th-.02,ox+.02,y,z)
    p=v['reset_pinhole']
    return plate-xcyl(p['diameter_mm']/2,ox-th-.02,ox+.02,p['y_mm'],p['z_mm'])


def button(v,y,switch_x,delta=0):
    """Changing flange and tip together preserves the maximum inward tip plane."""
    k=v['printed_keys'];t=table(v);ox=t['outer_x'];z=k['z_center']
    flange_end=ox+k['flange_thickness_mm']+delta
    face=t['exterior_x']-k['head_projection_mm']
    tip=switch_x-k['rest_gap_mm']+delta
    shoulder=k['stem_end_x_mm']+delta
    s=xcyl(k['head_diameter_mm']/2,face,ox+.001,y,z)
    s+=xcyl(k['flange_diameter_mm']/2,ox,flange_end,y,z)
    s+=xcyl(k['stem_diameter_mm']/2,flange_end-.001,shoulder,y,z)
    s+=xcyl(k['tip_diameter_mm']/2,shoulder-.001,tip,y,z)
    return s


def build_buttons(v,parts):
    k=v['printed_keys'];items={};exports={}
    for i,y in enumerate(k['y_mm'],1):
        name=f'KEY{i}';sx=bounds(parts[name])[0]
        for label,delta in k['variants_mm'].items():
            shape=button(v,y,sx,delta)
            export_name=f'button_{"power" if i==1 else "boot"}_{label}'
            shape.label=export_name.upper();exports[export_name]=shape
            if label=='nominal':items[name]=shape
    return items,exports
