"""G-V1 only: inset rear, independent four seats and two shallow latch beams.

Release through existing U-slot clearances with ONE .8mm plastic pick, lower
then upper. PCB screws come out FIRST; the display never follows lid peeling.
"""
import math
from build123d import Axis,Plane,Polygon,Circle,extrude,offset,fillet,Compound
from model import box_between as box
from reference import bounds
from t0_model import rr,cyl
from p1_checks import intersection


def build(m,parts,mounts,base,q):
    ox=base['outer_x_min_mm'];ex=ox+base['width_mm'];oy,ey=base['outer_y_mm'];w=base['wall_mm'];ix,jx=ox+w,ex-w;iy,jy=oy+w,ey-w
    bottom=m['dimensions']['rear_bottom_z_mm'];rb=bottom+q['rear_inset_mm'];floor=rb+q['rear_panel_mm'];outertop=rb+q['outer_rabbet_mm'];frontend=outertop+.2
    original=m['front'];ub=bounds(m['usbcut'])
    frameback=ub[2]-q['USB_lower_web_mm']
    usbframe=intersection(original,box([ub[0]-1,ey-w-.1,frameback,ub[3]+1,ey+.1,frontend+.01]))
    front=original-box([ox-1,oy-1,bottom-1,ex+1,ey+1,frontend]);front+=usbframe
    # Remove old G shoulders before placing one top-right bearing beyond both
    # latch heads. That bearing is the temporary rigid lid-opening pivot.
    for s in m['stops']:front-=s
    stops=[]
    for x,y,hy in [(ix+.4,-33.5,1),(ix+.4,39.8,1),(jx-.4,-33.5,1),(jx-.4,39.6,1)]:
        pad=box([x-.5,y-hy,floor,x+.5,y+hy,floor+.8]);front+=pad;stops.append(pad)
    cx,cy=(ox+ex)/2,(oy+ey)/2
    rear=rr(ex-ox,ey-oy,base['corner_radius_mm'],rb,outertop,cx,cy)
    gc=q['registration_radial_clearance_mm']
    core=rr(jx-ix-2*gc,jy-iy-2*gc,1,outertop-.01,floor,(ix+jx)/2,(iy+jy)/2);rear+=core
    # A 1mm non-locking register replaces the old G .6mm spigot.
    t=q['registration_width_mm'];h=q['registration_height_mm']
    reg=rr(jx-ix-2*gc,jy-iy-2*gc,1,floor-.01,floor+h,(ix+jx)/2,(iy+jy)/2)-rr(jx-ix-2*gc-2*t,jy-iy-2*gc-2*t,.5,floor-.1,floor+h+.1,(ix+jx)/2,(iy+jy)/2)
    for s in stops:
        b=bounds(s)
        # Interrupt the WHOLE register width, rather than leave a .15mm web.
        xa,xb=(ix-.1,ix+gc+t+.1) if b[0]<(ix+jx)/2 else (jx-gc-t-.1,jx+.1)
        reg-=box([xa,b[1]-.2,floor-.1,xb,b[4]+.2,floor+h+.1])
    b=base['battery'];bw,bh,_=b['xyz_mm'];bx,by=b['center_xy_mm'];c=b['tray_clearance_mm'];tw=b['tray_wall_mm']
    reg-=box([bx-bw/2-c,by+bh/2-c-t,floor-.1,bx+bw/2+c,jy+.2,floor+h+.1])
    pb=bounds(m['protection']);reg-=box([pb[0]-.2,pb[1]-.2,floor-.1,jx+.1,pb[4]+.2,floor+h+.1]);rear+=reg
    tray=rr(bw+2*c+2*tw,bh+2*c+2*tw,1.5,floor-.01,floor+b['tray_height_mm'],bx,by)-rr(bw+2*c,bh+2*c,.6,floor-.1,floor+b['tray_height_mm']+.1,bx,by)
    tray-=box([bx+bw/2,4,floor-.1,bx+bw/2+4,14,floor+2])
    tray=intersection(tray,box([ix+gc,iy+gc,floor-.1,jx-gc,jy-gc,floor+2]));rear+=tray
    dz=floor-m['dimensions']['rear_inside_z_mm']
    for k in ['battery','adhesive','protection']:m[k]=m[k].translate((0,0,dz))
    # Speaker support ends at the provisional damping, no glass/battery clamp.
    pads=[];s=base['speaker'];sx,sy=s['center_xy_mm'];sw,sh,_=s['xyz_mm'];dampback=bounds(m['damping'])[2]
    for x in [sx-sw/2+2,sx+sw/2-2]:
      for y in [sy-sh/2+2,sy+sh/2-2]:
        pad=box([x-1.5,y-1.5,floor-.01,x+1.5,y+1.5,dampback]);rear+=pad;pads.append(pad)
    screws=[];seats=[];screwrows=[]
    from build123d import GeomType
    for i,mount in enumerate(sorted(mounts,key=lambda s:(s.center().X,s.center().Y))):
        f=next(f for f in mount.faces() if f.geom_type==GeomType.CYLINDER and abs(f.axis_of_rotation.direction.Z)>.99)
        x,y,_=f.axis_of_rotation.position;mb=bounds(mount)[2];hs=rb+q['head_height_mm'];tip=hs+q['shaft_length_mm']
        seat=cyl(3.5,floor-.01,mb,x,y);rear+=seat
        rear-=cyl(q['shaft_bore_diameter_mm']/2,rb-.1,mb+.1,x,y);rear-=cyl(q['head_pocket_diameter_mm']/2,rb-.1,hs,x,y)
        screw=cyl(q['head_diameter_mm']/2,rb,hs,x,y)+cyl(1.25,hs,tip,x,y)
        screws.append(screw);seats.append(seat);screwrows.append(dict(index=i,axis_xy_mm=[x,y],head_bottom_mm=rb,head_seat_mm=hs,tip_mm=tip,seat_mm=mb-hs,nominal_engagement_mm=tip-mb))
    # The FRONT-owned USB lower frame keeps its candidate .85mm web even while
    # the inset lid may float rearward .15mm. Do not silently narrow the plug cut.
    notch=box([ub[0]-1.2,ey-w-.3,rb-1,ub[3]+1.2,ey+.2,floor+2]);rear-=notch
    rear=rear-m['usbcut']-m['tfcut']
    clips=[];a,bxclip=q['clip_x_mm'];L=q['clip_length_mm'];g=q['clip_slot_mm'];r=q['root_radius_mm']
    for site in q['clip_sites']:
        y=site['y_mm'];direction=site['direction'];root=y-direction*L;dx=site['beam_x0_mm']-a
        def tr(s):return (s.mirror(Plane.XZ) if direction<0 else s).translate((dx,root,0))
        outline=Polygon((a,0),(bxclip,0),(bxclip,L+1),(a,L+1),align=None)
        slot=offset(outline,amount=g)-outline
        slot=intersection(extrude(slot,amount=5).translate((0,0,rb-.1)),box([a-g-.1,.5,rb-.2,bxclip+g+.1,L+g+1.1,floor+3]))
        for xx in [a-g/2,bxclip+g/2]:slot+=extrude(Circle(g/2),amount=5).translate((xx,.5,rb-.1))
        slot=tr(slot)
        # Free beam is 1.1x1.2, built into the rear panel; no long vertical tongue.
        leaf=tr(box([a,0,rb,bxclip,L+1,floor]));rear+=leaf;rear-=slot
        # Slot must also clear the register; no hidden bridge may lock the beam.
        end_region=tr(box([a-g-.1,.5,floor,bxclip+g+.1,L+1.1,floor+2]))
        rear-=intersection(reg,end_region)
        hz0,hz1=q['hook_z_mm']
        stem=box([a+.3+dx,y-1,floor-.01,bxclip+dx,y+1,hz1])
        hook=extrude(Plane.XZ*Polygon((q['hook_x_mm'][0],hz0),(q['hook_x_mm'][1],hz0),
                      (q['hook_x_mm'][1],hz1),(q['hook_x_mm'][0]+.5,hz1),(q['hook_x_mm'][0],hz1-.2),align=None),amount=1,both=True).translate((dx,y,0))
        rear=rear+stem+hook
        rx0,rx1=[v+dx for v in q['receiver_x_mm']];hy=q['receiver_half_y_mm']
        boss=box([rx0,y-hy,floor,rx1,y+hy,m['dimensions']['front_z_mm']-base['bay_front_panel_mm']+.01])
        groove=box([rx0+.8,y-hy+.2,hz0-q['rearward_play_mm'],rx1+.1,y+hy-.2,hz1+.2]);front=(front+boss)-groove
        rear-=box([rx0-.2,y-hy-.2,floor,rx1+.2,y+hy+.2,floor+h+.1])
        # Outward leaf release stays in a shallow blind inner-wall relief.
        ya,yb=sorted([root,y])
        if dx==0:
            relief=box([jx-.1,ya-1.2,frontend-.1,q['front_wall_release_x_max_mm'],yb+1.2,hz1+.3]);front-=relief
        else:
            tool_y=root+direction*q['clip_tool_point_from_root_mm']
            # Left pick is still outside the original PCB. Relieve only its
            # near-case corner; keep a >1mm outer wall, no second side hole.
            front-=box([a+dx-1.1,tool_y-2,frontend-.1,ix+.1,tool_y+2,floor+.3])
        region=tr(box([a-.01,q['clip_root_fixed_mm'],rb-.01,bxclip+.01,L+1.01,hz1+.1]))
        free=intersection(rear,region)+hook
        # Pick: .8mm thick, triangular card corner, body remains behind case.
        tool_y=root+direction*q['clip_tool_point_from_root_mm'];ty,tz=q['tool_triangle_yz_mm'];zt=q['tool_top_z_mm']
        pick=extrude(Plane.YZ*Polygon((tool_y,zt),(tool_y-ty/2,zt-tz),(tool_y+ty/2,zt-tz),align=None),amount=q['tool_thickness_mm'],dir=(1,0,0)).translate((a+dx-q['tool_thickness_mm'],0,0))
        clips.append(dict(y=y,root_y=root,direction=direction,clip_x_mm=[a+dx,bxclip+dx],free=free,stem=stem,hook=hook,slot=slot,receiver=boss,groove=groove,pick=pick))
    # One lower-right starting grip. Cut only the OUTER part of a full wall,
    # away from latch reliefs, keeping 1mm inner stock and the rear rim intact.
    gy0,gy1=q['initial_grip_notch_y_mm']
    grip=box([ex-q['initial_grip_notch_x_depth_mm'],gy0,frontend-.01,ex+.1,gy1,outertop+q['initial_grip_gap_mm']])
    front-=grip
    m.update(front=front,rear=rear,screws=screws,seats=seats,screw_rows=screwrows,stops=stops,rear_clips=clips,speaker_pads=pads,initial_grip_notch=grip,
             closure_dimensions=dict(rear_bottom_mm=rb,rear_floor_mm=floor,outer_rabbet_top_mm=outertop,front_wall_end_mm=frontend,retained_rearward_play_mm=q['rearward_play_mm']))
    return m


def released(row,m,q):
    """Root-fixed point-load clearance proxy; hook/pad follows free-end rotation."""
    a,b=row['clip_x_mm'];mid=(a+b)/2;L=q['clip_length_mm'];s0=q['clip_root_fixed_mm'];Le=L-s0;at=q['clip_tool_point_from_root_mm']-s0;delta=q['clip_release_mm'];C=delta/(at*at*(3*Le-at))
    def w(s):return C*s*s*(3*at-s) if s<at else C*at*at*(3*s-at)
    points=[]
    for edge in [-1,1]:
        pts=[]
        for j in range(25):
            s=(Le-1)*j/24;pts.append((mid+w(s)+edge*(b-a)/2,row['root_y']+row['direction']*(s0+s)))
        if edge>0:pts.reverse()
        points+=pts
    rb=m['closure_dimensions']['rear_bottom_mm'];floor=m['closure_dimensions']['rear_floor_mm']
    beam=extrude(Polygon(*points,align=None),amount=floor-rb,dir=(0,0,1)).translate((0,0,rb))
    y=row['y'];pad=intersection(row['free'],box([a-.1,y-1,rb-.1,b+.1,y+1,q['hook_z_mm'][1]+.1]))+row['hook']
    theta=-row['direction']*math.degrees(math.atan(3*C*at*at))
    pad=pad.rotate(Axis((mid,y,0),(0,0,1)),theta).translate((delta,0,0))
    return Compound([beam,pad]),w(at),theta
