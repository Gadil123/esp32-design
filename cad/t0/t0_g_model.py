"""G only. One deep shell, native four machine screws and four hidden tongues.

E geometry and its files are frozen. A helpers supply existing cap/accessory datums.
"""
from build123d import Axis, Polygon, Plane, extrude, Compound
from t0_model import build as build_a, rr, cyl
from reference import bounds
from model import box_between as box


def build(parts,mounts,base,kp,p):
    a={**base,'target_thickness_mm':p['maximum_thickness_mm']-p['screen_recess_mm'],'rear_panel_mm':p['rear_panel_mm'],'pcb_clip_indices':[],
       'snap_edge_signs':[],'side_snaps':[],'registration_centers_y_mm':[]}
    m=build_a(parts,mounts,a,kp)
    db=bounds(parts['DISPLAY']);top=db[5]+p['screen_recess_mm'];bottom=top-p['maximum_thickness_mm'];floor=bottom+p['rear_panel_mm']
    ox=base['outer_x_min_mm'];ex=ox+base['width_mm'];oy,ey=base['outer_y_mm'];wall=base['wall_mm'];gc=p['lid_radial_clearance_mm']
    ix,jx=ox+wall,ex-wall;iy,jy=oy+wall,ey-wall
    def outer(z0,z1):return rr(ex-ox,ey-oy,base['corner_radius_mm'],z0,z1,(ox+ex)/2,(oy+ey)/2)
    front=outer(bottom,top)-box([ix,iy,bottom-1,jx,jy,top-base['bay_front_panel_mm']])
    # The lip is ABOVE glass, never a clamping plane. Its overlap is unverified.
    lipbase=top-p['front_lip_thickness_mm'];clear=base['panel_xy_clearance_mm']
    front=front-box([db[0]-clear,iy,bottom-1,db[3]+clear,jy,lipbase])
    overlap=p['front_lip_overlap_mm']
    window=[db[0]+overlap,db[1]+overlap,lipbase-.01,db[3]-overlap,db[4]-overlap,top+.1]
    front=front-box(window)
    # Native USB / TF openings come from source faces, independent plug probes retained.
    front=front-m['usbcut']-m['tfcut']
    for key,d in m['key_data'].items():
        yc,zc=d['center_yz_mm'];f0,f1=d['flange_x_mm'];fw,fh=kp['key_flange_yz_mm'];sy,sz=kp['key_stem_yz_mm']
        ac=kp['key_axial_clearance_mm'];g=kp['key_guide_clearance_mm']
        pocket=box([f0-ac,yc-fw/2-g,zc-fh/2-g,f1+kp['key_cap_design_motion_mm']+ac,yc+fw/2+g,zc+fh/2+g])
        # G only: the RESET body also needs the .3mm outward staging allowance;
        # preserve its original cap, leaving .5mm face stock (explicit PA12 risk).
        start=d['body_start_x_mm']-p['key_assembly_outward_mm'] if d['function']=='RESET' else ox-1
        pocket=pocket+box([start,yc-sy/2-g,zc-sz/2-g,d['tip_x_mm']+g,yc+sy/2+g,zc+sz/2+g])
        if d['function']=='RESET':
            from build123d import Cylinder,Align
            pocket=pocket+Cylinder(kp['reset_hole_radius_mm'],2,align=(Align.CENTER,Align.CENTER,Align.MIN)).rotate(Axis.Y,90).translate((ox-1,yc,zc))
        front=front-pocket
    # Flush inset rear panel; its outer shoulder is the independent axial stop.
    rear=rr(jx-ix-2*gc,jy-iy-2*gc,1.0,bottom,floor,(ix+jx)/2,(iy+jy)/2)
    sp=p['spigot_width_mm'];h=p['spigot_height_mm']
    spigot=rr(jx-ix-2*gc,jy-iy-2*gc,1.0,floor-.01,floor+h,(ix+jx)/2,(iy+jy)/2)-rr(jx-ix-2*gc-2*sp,jy-iy-2*gc-2*sp,.5,floor-.1,floor+h+.1,(ix+jx)/2,(iy+jy)/2)
    rear=rear+spigot
    # Four broad blind shoulders are OUTSIDE the original board, not glass stops.
    stops=[]
    for x,signx in [(ix,1),(jx,-1)]:
      for y in [iy+p['closure_stop_corner_inset_mm'],jy-p['closure_stop_corner_inset_mm']]:
        xa,xb=sorted([x-signx*.1,x+signx*.9]);ya,yb=y-p['closure_stop_length_mm']/2,y+p['closure_stop_length_mm']/2
        pad=box([xa,ya,floor,xb,yb,floor+.8]);front=front+pad;stops.append(pad)
        rear=rear-box([xa-.1,ya-.1,floor,xb+.1,yb+.1,floor+h+.1])
    screws=[];seats=[];rows=[];spc=p['screw']
    for i,mount in enumerate(sorted(mounts,key=lambda s:(s.center().X,s.center().Y))):
        from build123d import GeomType
        f=next(f for f in mount.faces() if f.geom_type==GeomType.CYLINDER and abs(f.axis_of_rotation.direction.Z)>.99)
        x,y,_=f.axis_of_rotation.position;metalback=bounds(mount)[2]
        hb=bottom+spc['head_recess_mm'];hs=hb+spc['head_height_mm'];tip=hs+spc['length_mm']
        seat=cyl(p['mount_seat_outer_radius_mm'],floor-.01,metalback,x,y)-cyl(spc['shaft_bore_diameter_mm']/2,bottom-.1,metalback+.1,x,y)
        rear=rear+seat
        rear=rear-cyl(spc['shaft_bore_diameter_mm']/2,bottom-.1,metalback+.1,x,y)-cyl(spc['head_pocket_diameter_mm']/2,bottom-.1,hs,x,y)
        # Full major-diameter thread envelope, not a detailed meshed male thread.
        screw=cyl(spc['head_diameter_mm']/2,hb,hs,x,y)+cyl(spc['thread_diameter_mm']/2,hs,tip,x,y)
        screws.append(screw);seats.append(seat)
        rows.append(dict(index=i,axis_xy_mm=[x,y],metalback_z_mm=metalback,head_bottom_z_mm=hb,head_seat_z_mm=hs,tip_z_mm=tip,
                         PA12_bearing_thickness_mm=metalback-hs,nominal_thread_engagement_mm=tip-metalback))
    # Reuse the provisional dimensions, not any assumption of final accessory size.
    dz=top-db[5]
    for k in ['speaker','foam','damping']:m[k]=m[k].translate((0,0,dz))
    b=base['battery'];bw,bh,_=b['xyz_mm'];bx,by=b['center_xy_mm'];c=b['tray_clearance_mm'];tw=b['tray_wall_mm']
    tray=rr(bw+2*c+2*tw,bh+2*c+2*tw,1.5,floor-.01,floor+b['tray_height_mm'],bx,by)-rr(bw+2*c,bh+2*c,.6,floor-.1,floor+b['tray_height_mm']+.1,bx,by)
    tray=tray-box([bx+bw/2,4,floor-.1,bx+bw/2+4,14,floor+2])
    from p1_checks import intersection
    tray=intersection(tray,box([ix+gc,iy+gc,floor-.1,jx-gc,jy-gc,floor+2]))
    # The old rear tray occupied the rear half of the former split sidewall.
    # A deep FRONT owns that wall now. Interrupt the shallow spigot at the
    # battery's upper edge rather than silently cutting the provisional cell.
    rear=rear-box([bx-bw/2-c,by+bh/2-c,floor,bx+bw/2+c,jy+.1,floor+h+.1])
    pb=bounds(m['protection'])
    rear=rear-box([pb[0]-.2,pb[1]-.2,floor,jx+.1,pb[4]+.2,floor+h+.1])
    rear=rear+tray
    s=base['speaker'];sw,sh,st=s['xyz_mm'];sx,sy=s['center_xy_mm'];sf=top-base['bay_front_panel_mm']-s['foam_mm'];sc=s['tray_clearance_mm'];stw=s['tray_wall_mm']
    fence=rr(sw+2*sc+2*stw,sh+2*sc+2*stw,1.5,sf-st-.3,top-.2,sx,sy)-rr(sw+2*sc,sh+2*sc,.5,sf-st-.4,top+.1,sx,sy)
    fence=fence-box([sx-sw/2-2,sy-1.3,sf-st-1,sx-sw/2+.1,sy+1.3,top+1]);front=front+fence
    # Speaker/damping travel with the rear module; four broad pads support the
    # provisional damping envelope without squeezing the battery or glass.
    speaker_pads=[]
    for x in [sx-sw/2+2,sx+sw/2-2]:
      for y in [sy-sh/2+2,sy+sh/2-2]:
        pad=box([x-1.5,y-1.5,floor-.01,x+1.5,y+1.5,sf-st-s['damping_mm']]);rear=rear+pad;speaker_pads.append(pad)
    for j in range(s['slot_count']):
        yy=sy+(j-(s['slot_count']-1)/2)*s['slot_pitch_mm'];front=front-rr(s['grille_xy_mm'][0],s['slot_mm'],s['slot_mm']/2-.01,top-2,top+.1,sx,yy)
    # No closed partition across unverified MX wire routes or MIC.
    rear=rear-m['usbcut']-m['tfcut']
    m.update(front=front,rear=rear,screws=screws,seats=seats,screw_rows=rows,stops=stops,
             speaker_pads=speaker_pads,dimensions=dict(front_z_mm=top,glass_z_mm=db[5],rear_bottom_z_mm=bottom,rear_inside_z_mm=floor,lipbase_z_mm=lipbase),window_bounds_mm=window)
    return m


def latch_pair(m,base,p,site):
    """One vertical root-fixed rear tongue, blind inner groove and rear tool lane.

    Local right edge, then rigidly map to each selected edge. The beam itself
    is never translated rigidly as evidence of elasticity.
    """
    q=p['latch'];ex=base['outer_x_min_mm']+base['width_mm'];ix=ex-base['wall_mm'];floor=m['dimensions']['rear_inside_z_mm']
    t=q['beam_thickness_mm'];w=q['beam_width_mm'];root=q['beam_root_z_mm'];tip=q['beam_tip_z_mm'];g=q['channel_clearance_mm']
    inner=ix+q['beam_inner_offset_from_wall_mm'];outer=inner+t
    beam=box([inner,-w/2,floor-.01,outer,w/2,tip])
    hook=extrude(Plane.XZ*Polygon((outer,tip-q['hook_height_mm']),(outer+q['hook_projection_mm'],tip-q['hook_height_mm']),(outer,tip),align=None),amount=w/2,both=True)
    tongue=beam+hook
    bottom=m['dimensions']['rear_bottom_z_mm']
    rootpad=box([inner-.3,-w/2,bottom,outer,w/2,root])
    channel=box([inner-.01,-w/2-g,bottom-.1,outer+g,w/2+g,tip+.3])
    groove=box([outer-.01,-w/2-g,tip-q['hook_height_mm']-q['groove_axial_clearance_mm'],outer+q['groove_depth_mm'],w/2+g,tip+q['groove_axial_clearance_mm']])
    # .15mm candidate shim enters BESIDE the beam root, then its small tip reaches
    # the hook. It can move inward without translating through the rigid root.
    # Material/availability and handling of this thin external tool are unverified.
    toe=extrude(Plane.XZ*Polygon((outer+q['hook_projection_mm']*.2/q['hook_height_mm'],tip-.2),
        (outer+.175,tip-.2),(outer+.175,tip+.1),(outer,tip+.1),(outer,tip),align=None),amount=.675/2,both=True).translate((0,w/2-.1625,0))
    pick=box([outer+.025,w/2+.025,bottom-1.1,outer+.175,w/2+.175,tip+.1])+toe
    pick=pick+box([outer-2,w/2-2,bottom-3,outer+2,w/2+2,bottom-1])
    ox=base['outer_x_min_mm'];oy,ey=base['outer_y_mm'];at=site['coordinate_mm']
    angle,shift={'right':(0,(0,at,0)),'left':(180,(ox+ex,at,0)),
                 'top':(90,(at,ey-ex,0)),'bottom':(-90,(at,oy+ex,0))}[site['edge']]
    def tr(s):return s.rotate(Axis.Z,angle).translate(shift)
    freebeam=box([inner,-w/2,root,outer,w/2,tip])
    return {k:tr(s) for k,s in dict(tongue=tongue,freebeam=freebeam,hook=hook,rootpad=rootpad,channel=channel,groove=groove,pick=pick).items()}|dict(site=site,angle=angle,inner=inner,outer=outer)


def finish(m,base,p):
    front,rear=m['front'],m['rear'];pairs=[]
    for site in p['latch']['sites']:
        pair=latch_pair(m,base,p,site);pairs.append(pair)
        front=front-pair['channel']-pair['groove'];rear=rear+pair['rootpad']+pair['tongue']
    # One deliberate rear-edge starting notch; other shim entries use the opened
    # rear seam. No through-side receiver windows. Real tool handling pending.
    first=pairs[0];ox=base['outer_x_min_mm'];y=first['site']['coordinate_mm']
    entry=box([ox+.8,y-3.4,m['dimensions']['rear_bottom_z_mm']-.1,ox+2.2,y-2.4,m['dimensions']['rear_bottom_z_mm']+.5])
    front=front-entry;rear=rear-entry
    m.update(front=front,rear=rear,latch_pairs=pairs,pry_entry=entry)
    return m
