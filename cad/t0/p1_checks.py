"""Independent interference/path probes and destructive fixture tests for P1."""
import numpy as np
from model import box_between
from reference import bounds
from p1_model import cylinder, usb_mouth_face
from build123d import GeomType,Compound
from functools import lru_cache


@lru_cache(maxsize=8192)
def spatial_bounds(shape):
    return bounds(shape)


def intersection(a,b):
    return Compound(a.intersect(b) or [])


def common_volume(a,b):
    aa,bb=spatial_bounds(a),spatial_bounds(b)
    if any(min(aa[i+3],bb[i+3])-max(aa[i],bb[i])<=1e-7 for i in range(3)):return 0.0
    c=intersection(a,b)
    return c.volume


def clashes(moving,obstacles,tolerance):
    return [{'obstacle':name,'volume_mm3':v} for name,shape in obstacles
            if (v:=common_volume(moving,shape))>tolerance]


def translated_box_sweep(shape,vector):
    """Conservative continuous linear sweep of the shape's AABB, independent of cuts."""
    b=bounds(shape)
    return box_between([b[i]+min(0,vector[i]) for i in range(3)] +
                       [b[i+3]+max(0,vector[i]) for i in range(3)])


def usb_probe(parts,p):
    # A separately sourced cable body profile, placed at the receiver mouth, even
    # without credit for a narrow metal nose. No opening-cutter dimensions reused.
    b=bounds(usb_mouth_face(parts['J2_USB_SIDE']));x=(b[0]+b[3])/2;z=(b[2]+b[5])/2
    w,h=p['usb_plug_body_xz_mm'];y=b[4]+p['usb_mating_y_adjustment_mm']
    return box_between([x-w/2,y,z-h/2,x+w/2,y+p['usb_validation_prism_length_mm'],z+h/2])


def cap_components(cap,data,p):
    # Split at the flange planes to get tighter conservative installation/path boxes.
    b=bounds(cap);f0,f1=data['flange_x_mm']
    cuts=sorted([b[0],f0,f1,data['body_end_x_mm'],data['tip_root_x_mm'],b[3]])
    pieces=[]
    for a,z in zip(cuts,cuts[1:]):
        if z-a<1e-6:continue
        c=intersection(cap,box_between([a,b[1]-1,b[2]-1,z,b[4]+1,b[5]+1]))
        if c is not None and c.volume>1e-8:pieces.extend(c.solids())
    # Head+stem share the outer segment; further separate them at the head/stem joint.
    if data['function']!='RESET':
        joint=b[0]+p['key_head_depth_mm']
        result=[]
        for piece in pieces:
            pb=bounds(piece)
            if pb[0]<joint-1e-5 and pb[3]>joint+1e-5:
                for lo,hi in [(pb[0],joint),(joint,pb[3])]:
                    c=intersection(piece,box_between([lo,pb[1]-1,pb[2]-1,hi,pb[4]+1,pb[5]+1]))
                    if c is not None:result.extend(c.solids())
            else:result.append(piece)
        pieces=result
    return pieces
