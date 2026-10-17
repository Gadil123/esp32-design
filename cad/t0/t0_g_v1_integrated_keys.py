"""One U-leaf candidate, G-V1 only. Real root radii; no separate caps.

Root-fixed press poses are clearance proxies using an end-force beam curve,
including end rotation. Neither stiffness nor fatigue is qualified by CAD.
"""
import math
from build123d import Axis, Plane, Polygon, Circle, extrude, offset, fillet, Compound, RectangleRounded, Align
from model import box_between as box
from reference import bounds
from p1_checks import intersection
from t0_g_model import build as old_g


def foundation(parts,mounts,base,kp,p,q):
    p={**p,'maximum_thickness_mm':q['maximum_thickness_mm'],'screen_recess_mm':0,
       'front_lip_overlap_mm':-base['panel_xy_clearance_mm'],
       'screw':{**p['screw'],'part':'User candidate M2.5x4 D5 H0.85',
                'source':'Task21 product-image envelope; UNVERIFIED',
                'head_height_mm':.85,'head_recess_mm':0}}
    m=old_g(parts,mounts,base,kp,p)
    ox=base['outer_x_min_mm'];ix=ox+base['wall_mm'];d=m['dimensions'];db=bounds(parts['DISPLAY']);c=base['panel_xy_clearance_mm']
    m['front']-=box([db[0]-c,db[1]-c,d['rear_bottom_z_mm']-1,db[3]+c,db[4]+c,d['front_z_mm']+1])
    # Undo ALL three historical cap cuts before making integrated leaves.
    for data in m['key_data'].values():
        y,z=data['center_yz_mm'];h=kp['key_flange_yz_mm'][0]/2+kp['key_guide_clearance_mm']+.01
        m['front']+=box([ox,y-h,d['rear_bottom_z_mm'],ix,y+h,d['front_z_mm']])
    from build123d import Cylinder,Align
    y,z=m['key_data']['KEY3']['center_yz_mm']
    m['front']-=Cylinder(q['reset_hole_diameter_mm']/2,base['wall_mm']+.2,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-.1,y,z))
    m['caps']={};m['integrated_keys']=[]
    return m,p


def build_keys(parts,m,base,q):
    ox=base['outer_x_min_mm'];ix=ox+base['wall_mm'];L=q['root_to_pad_mm'];t=q['leaf_thickness_mm'];g=q['slot_mm'];r=q['root_radius_mm']
    zl,zh=q['leaf_z_mm'];h=q['pad_half_y_mm'];bump_y,bump_z=q['bump_yz_mm'];tip=bounds(parts['DISPLAY'])[0]-q['glass_projection_clearance_mm']
    for key,direction in [('KEY1',-1),('KEY2',1)]:
        y,z=m['key_data'][key]['center_yz_mm'];root=y-direction*L
        rect=q.get('boot_rectangle') if key=='KEY2' else None
        lz,hz=(z-rect['height_mm']/2,z+rect['height_mm']/2) if rect else (zl,zh)
        # Local sketch axes (s,Z); three open sides surround an L-shaped
        # leaf/pad. Elevated beam avoids the TF opening and RESET bore.
        if rect:
            outline=RectangleRounded(L+h,rect['height_mm'],rect['outer_radius_mm'],align=(Align.MIN,Align.CENTER)).translate((0,z,0))
        else:
            outline=Polygon((0,zh),(L+h,zh),(L+h,z-q['pad_half_z_mm']),
                            (L-h,z-q['pad_half_z_mm']),(L-h,zl),(0,zl),align=None)
        ring=offset(outline,amount=g)-outline
        slot=extrude(Plane.YZ*ring,amount=base['wall_mm']+.2,dir=(1,0,0)).translate((ox-.1,0,0))
        slot=intersection(slot,box([ox-.2,.5,-20,ix+.2,L+h+g+1,2]))
        # Actual radius-.5 circular endpoints of the U slots (axis X).
        for zz in [hz+g/2,lz-g/2]:
            slot+=extrude(Plane.YZ*Circle(g/2),amount=base['wall_mm']+.2,dir=(1,0,0)).translate((ox-.1,.5,zz))
        solid_region=extrude(Plane.YZ*outline,amount=base['wall_mm']+5,dir=(1,0,0)).translate((ox,0,0))
        # A rounded milling-style recess supplies an actual XY root transition
        # at the thickness change, rather than merely reporting a radius number.
        cutter=Polygon((ox+t,0),(ix+5,0),(ix+5,L+h+1),(ox+t,L+h+1),align=None)
        v=[v for v in cutter.vertices() if abs(v.X-(ox+t))<1e-6 and abs(v.Y)<1e-6]
        cutter=fillet(v,radius=r)
        relief=intersection(extrude(cutter,amount=20).translate((0,0,-15)),solid_region)
        def tr(s):
            return (s.mirror(Plane.XZ) if direction<0 else s).translate((0,root,0))
        m['front']=m['front']-tr(slot)-tr(relief)
        by=y+direction*q['bump_y_precompensation_mm']
        bump=box([ox+t-.01,by-bump_y/2,z-bump_z/2,tip,by+bump_y/2,z+bump_z/2])
        m['front']+=bump
        # Separate only a free-end clearance region; it remains fused in FRONT.
        region=intersection(tr(box([ox-.1,q['fixed_root_length_mm'],-10,ix+5,L+h+.1,hz+.1])),tr(solid_region))
        # Only the actual connected U-leaf outline may deform. A rectangular
        # crop would accidentally move the fixed wall below the U-slot too.
        free=intersection(m['front'],region)
        row=dict(key=key,y=y,z=z,root_y=root,direction=direction,
                 free=free,bump=bump,slot=tr(slot),region=region,tip_x=tip,leaf_z_mm=[lz,hz],profile_kind='rounded_rectangle' if rect else 'L')
        m['integrated_keys'].append(row)
        # Independent non-glass inward stop above the contact bump. Measure its
        # X plane from the rotating pad at design travel, not from delta alone.
        pressed,_=press_pose(row,base,q,q['candidate_stop_mm'])
        if rect:
            # Keep the relocated stop away from the bump in Y. A top foot
            # joins fixed wall ABOVE the U-slot; no .05mm moving slit.
            ya,yb=[y+v for v in rect['stop_y_relative_mm']]
            sz0=hz-rect['stop_contact_top_inset_mm']-q['shell_stop_height_mm'];sz1=sz0+q['shell_stop_height_mm']
            face=intersection(pressed,box([ox-1,ya,sz0,ix+5,yb,sz1]))
            stop_x=bounds(face)[3];th=q['shell_stop_thickness_mm'];fz0,fz1=rect['stop_foot_z_mm']
            stop=box([stop_x,ya,sz0,stop_x+th,yb,fz1])+box([ix-.05,ya,fz0,stop_x+th,yb,fz1])
        else:
            sz0=lz+.2;sz1=sz0+q['shell_stop_height_mm']
            face=intersection(pressed,box([ox-1,y-2,sz0,ix+5,y+2,sz1]))
            stop_x=bounds(face)[3];th=q['shell_stop_thickness_mm'];aw=q['shell_stop_anchor_width_mm']
            ya,yb=sorted([y-direction*.8,y+direction*(h+g+aw)])
            anchor_a,anchor_b=sorted([y+direction*(h+g),y+direction*(h+g+aw)])
            stop=box([stop_x,ya,sz0,stop_x+th,yb,sz1])+box([ix-.05,anchor_a,sz0,stop_x+th,anchor_b,sz1])
        m['front']+=stop
        row.update(stop=stop,stop_x=stop_x,stop_z_mm=[sz0,sz1])
    return m


def press_pose(row,base,q,delta):
    """Euler-Bernoulli end-load displacement + rotated rigid pad/bump.

    Material, load, shear, large-deflection corrections and fatigue are pending.
    The first 1mm remains fixed, and the clearance proxy conserves leaf thickness.
    """
    ox=base['outer_x_min_mm'];t=q['leaf_thickness_mm'];L=q['root_to_pad_mm']-q['fixed_root_length_mm']
    start=row['root_y']+row['direction']*q['fixed_root_length_mm'];y=row['y'];zl,zh=row.get('leaf_z_mm',q['leaf_z_mm']);h=q['pad_half_y_mm']
    pad=intersection(row['free'],box([ox-1,y-h,-10,row['tip_x']+1,y+h,zh+.1]))
    angle=-row['direction']*math.degrees(math.atan(1.5*delta/L))
    pad=pad.rotate(Axis((ox+t/2,y,0),(0,0,1)),angle).translate((delta,0,0))
    points=[]
    for side in [-1,1]:
        a=[]
        for j in range(25):
            s=(L-h)*j/24;u=s/L;dx=delta*(3*u*u-u*u*u)/2
            slope=delta*(3*u-1.5*u*u)/L
            norm=math.sqrt(1+slope*slope)
            a.append((ox+t/2+dx+side*t/(2*norm),start+row['direction']*(s-side*t*slope/(2*norm))))
        if side>0:a.reverse()
        points+=a
    beam=extrude(Polygon(*points,align=None),amount=zh-zl,dir=(0,0,1)).translate((0,0,zl))
    return Compound([beam,pad]),angle
