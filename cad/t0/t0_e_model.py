"""E only: A's existing three clips + D nests and short shell teeth. A-D retained."""
from build123d import Axis
from p1_checks import intersection
from t0_model import build as build_a
from t0_d_study import build as build_d
from model import box_between as box
from reference import bounds


def parameters(base,p):
    base={**base,**p,'snap_edge_signs':[],'side_snaps':[],'registration_centers_y_mm':[]}
    return base


def finish(parts,mounts,m,base,p,dp):
    front,rear=m['front'],m['rear'];original_front=front
    ox=base['outer_x_min_mm'];ex=ox+base['width_mm'];oy,ey=base['outer_y_mm']
    local={};pairs=[];d=None
    for site in p['short_tooth_sites']:
        half=site['half_length_mm']
        if half not in local:
            q={**dp,'edge_center_y_mm':0,'edge_local_half_length_mm':half,'lap_end_setback_mm':p['lap_end_setback_mm'],
               'peripheral_stop_gap_mm':p['peripheral_stop_gap_mm'],'nest_axial_clearance_mm':p['nest_axial_clearance_mm']}
            local[half]=build_d(parts,mounts,q,base)
        d=local[half];edge=site['edge'];at=site['coordinate_mm']
        angle,shift={'right':(0,(0,at,0)),'left':(180,(ox+ex,at,0)),
                     'top':(90,(at,ey-ex,0)),'bottom':(-90,(at,oy+ex,0))}[edge]
        def turn(s):return s.rotate(Axis.Z,angle).translate(shift)
        f,r,free,rf,pick=[turn(d[k]) for k in ['front','rear','tongue','fixed_rear','pick']]
        bb=bounds(r);floor=m['dimensions']['rear_inside_z_mm'];top=m['dimensions']['glass_and_front_z_mm']
        cut=box([bb[0],bb[1],floor,bb[3],bb[4],top+.1])
        # The D local receiver is only a wall. Keep A's original front skin
        # above it, preserving the screen aperture and bay/grille openings.
        # Otherwise replacing the wall patch would open a new slot in FRONT.
        skin=intersection(original_front,box([bb[0],bb[1],top-base['bay_front_panel_mm'],bb[3],bb[4],top+.1]))
        front=(front-cut)+f+skin;rear=(rear-cut)+r
        inward={'right':(-1,0,0),'left':(1,0,0),'top':(0,-1,0),'bottom':(0,1,0)}[edge]
        pairs.append({'site':site,'front':f,'rear':r,'tongue':free,'fixed_rear':rf,'pick':pick,'inward':inward})
    for seat in d['seats']:rear=rear+seat
    m.update(front=front,rear=rear,nests=d['seats'],nest_rows=d['rows'],short_pairs=pairs)
    return m
