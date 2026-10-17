"""Closed-pose height bound from actual CAD bearing patches, not just Z play.

A tilted rear reference plane has height w=aX+bY+c relative to nominal. Flat
FRONT shoulders bound w above; the two diagonal hook patches bound it below.
This is a nominal rigid-contact model, NOT a PA12/warpage tolerance approval.
"""
import math
import numpy as np
from scipy.optimize import linprog
from build123d import GeomType,offset
from p1_checks import intersection
from reference import bounds


def evaluate(parts,m,q):
    eps=.0001;forward=[];back=[];patches=[]
    for stop in m['stops']:
        contact=intersection(stop,m['rear'].translate((0,0,eps)))
        faces=[f for f in contact.faces() if f.geom_type==GeomType.PLANE and f.normal_at().Z>.99]
        assert faces
        f=max(faces,key=lambda f:f.area)
        core=offset(f,amount=-.2)
        pts=[(v.X,v.Y) for v in core.vertices()];assert len(pts)>=3
        forward+=pts;patches.append(dict(contact_bounds_mm=bounds(contact),eroded_support_points_xy_mm=pts))
    for row in m['rear_clips']:
        contact=intersection(row['free'].translate((0,0,-q['rearward_play_mm']-eps)),m['front'])
        assert contact.volume>0
        b=bounds(contact);back.append(dict(center_xy_mm=[(b[0]+b[3])/2,(b[1]+b[4])/2],
            uncertainty_half_xy_mm=[(b[3]-b[0])/2+.25,(b[4]-b[1])/2+.25],contact_bounds_mm=b))
    ob=bounds(m['rear']);db=bounds(parts['DISPLAY']);bodypts=[(x,y) for x in [ob[0]-.3,ob[3]+.3] for y in [ob[1]-.3,ob[4]+.3]]
    glasspts=[(x,y) for x in [db[0]-.4,db[3]+.4] for y in [db[1]-.4,db[4]+.4]]
    worst_back=0.;worst_front=0.;slopes=[];witnesses=[]
    for sx in [-1,1]:
      for sy in [-1,1]:
        A=[[x,y,1] for x,y in forward];B=[0.]*len(A)
        for p in back:
            x,y=p['center_xy_mm'];dx,dy=p['uncertainty_half_xy_mm']
            A.append([-(x+sx*dx),-(y+sy*dy),-1]);B.append(q['rearward_play_mm']+.001)
        lim=[(0,None) if sx>0 else (None,0),(0,None) if sy>0 else (None,0),(None,None)]
        for points,sign in [(bodypts,1),(glasspts,-1)]:
          for x,y in points:
            fit=linprog(np.array([x,y,1])*sign,A_ub=A,b_ub=B,bounds=lim,method='highs')
            assert fit.success,fit.message
            value=float(np.dot([x,y,1],fit.x));slopes.append(list(fit.x[:2]))
            if sign>0:worst_back=max(worst_back,-value)
            else:worst_front=max(worst_front,value)
            witnesses.append(dict(target='rear' if sign>0 else 'glass',xy_mm=[x,y],plane_abc=list(fit.x),delta_z_mm=value))
    slope2=max(a*a+b*b for a,b in slopes)
    # Parallel-plane vertical separation changes quadratically on tilt. The
    # explicit .005 bound exceeds this CAD model's computed correction.
    factor=math.sqrt(1+slope2)-1
    floor=m['closure_dimensions']['rear_floor_mm'];height=max(abs(db[5]-floor),abs(ob[2]-floor))
    correction=height*factor;assert correction<.005
    guard=.005
    moving_min=ob[2]-worst_back-guard;front_max=max(bounds(m['front'])[5],db[5]+worst_front+guard)
    zmin=min(bounds(m['front'])[2],moving_min)
    return dict(status='NOMINAL_RIGID_CONTACT_BOUND',forward_patches=patches,diagonal_hook_patches=back,
        maximum_rear_plane_drop_mm=worst_back,maximum_glass_plane_rise_mm=worst_front,
        quadratic_plane_correction_bound_mm=correction,guard_mm=guard,
        conservative_z_min_mm=zmin,conservative_z_max_mm=front_max,maximum_thickness_mm=front_max-zmin,
        LP_objective_evaluations=len(witnesses),nominal_closed_pose_witnesses=[min((w for w in witnesses if w['target']=='rear'),key=lambda w:w['delta_z_mm']),max((w for w in witnesses if w['target']=='glass'),key=lambda w:w['delta_z_mm'])],
        limits='Actual CAD contact patches eroded .2; hook contact location expanded .25; rear footprint expanded .3 and glass .4. Four slope-sign LPs bound rigid plane rocking. Contact overlap, friction, elasticity and printer warp still require physical verification. This does not certify arbitrary loaded deformation.')
