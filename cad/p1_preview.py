"""CAD sections with explicit FRONT/REAR orientation and an exploded assembly."""
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import to_rgb
from model import box_between
from preview import rasterize
from reference import bounds
from p1_checks import intersection


def panel(ax,items,u,v,w,extent):
    triangles=[];colors=[]
    for shape,color in items:
        if shape is None or len(shape.faces())==0:continue
        verts,tris=shape.tessellate(.06,.2)
        if not tris:continue
        tri=np.asarray([tuple(x) for x in verts])[np.asarray(tris)]
        normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(normals,axis=1);length[length==0]=1
        shade=.55+.45*np.abs(normals@np.asarray(w)/length)
        triangles.extend(tri);colors.extend(np.asarray(to_rgb(color))[None,:]*shade[:,None])
    tri=np.asarray(triangles);u,v,w=map(np.asarray,[u,v,w])
    xy=np.stack([tri@u,tri@v],axis=2)
    height=700;width=max(300,int(700*(extent[1]-extent[0])/(extent[3]-extent[2])))
    img=rasterize(xy,tri@w,np.asarray(colors),extent,(width,height))
    ax.imshow(img,extent=extent,origin='lower',interpolation='nearest')
    ax.set_xlim(extent[:2]);ax.set_ylim(extent[2:]);ax.set_aspect('equal');ax.grid(alpha=.18)


def render_details(out,parts,mounts,m,plug):
    front,rear=m['front'],m['rear']
    blue,gray,yellow,silver='#4e6580','#72869b','#e9a64a','#b3bac2'
    fig,axes=plt.subplots(1,3,figsize=(15,6))
    # Through a mounting screw, looking from +Y. +Z (FRONT) is vertical up.
    stack=m['mount_data'][2];x,y=stack['axis_mm']
    clip=box_between([x-4,y-.12,-17.5,28.5,y+.12,-3.0])
    items=[(intersection(front,clip),blue),(intersection(rear,clip),gray),(intersection(m['screws'][2],clip),silver)]
    nut=min(mounts,key=lambda n:abs(n.center().X-x)+abs(n.center().Y-y))
    items.append((intersection(nut,clip),'#b7a270'))
    panel(axes[0],items,[1,0,0],[0,0,1],[0,1,0],(x-4,28.5,-17.5,-3.0))
    axes[0].set_title('MOUNT SECTION\nFRONT +Z up / REAR down')
    axes[0].set_xlabel('X mm');axes[0].set_ylabel('Z mm')
    axes[0].text(x-3.7,-16.9,'M2.5 x 8 / original nut\nfront arm + rear support',fontsize=8)
    # BAT_PWR section exposes the captive flange and independent guide clearances.
    key='KEY1';kd=m['key_data'][key];yc,zc=kd['center_yz_mm']
    xmin=bounds(m['caps'][key])[0]-.3
    clip=box_between([xmin,yc-.08,zc-3,-23,yc+.08,zc+3])
    items=[(intersection(front,clip),blue),(intersection(rear,clip),gray),
           (intersection(m['caps'][key],clip),yellow),(intersection(parts[key],clip),'#a76d31')]
    panel(axes[1],items,[1,0,0],[0,0,1],[0,1,0],(xmin,-23,zc-3,zc+3))
    axes[1].set_title('BAT_PWR GUIDE SECTION\nFRONT +Z up / REAR down')
    axes[1].set_xlabel('X mm');axes[1].set_ylabel('Z mm')
    axes[1].text(xmin+.15,zc-2.8,'0.15 mm rest gap\n0.40 mm CAP budget\nactual switch travel UNKNOWN',fontsize=8)
    # USB section at the real rim center, view from FRONT.
    ub=m['usb_mouth_face_bounds_mm'];cz=(ub[2]+ub[5])/2
    clip=box_between([-9,35.5,cz-.08,9,45.5,cz+.08])
    items=[(intersection(front,clip),blue),(intersection(rear,clip),gray),
           (intersection(parts['J2_USB_SIDE'],clip),silver),(intersection(plug,clip),'#5ca3b1')]
    panel(axes[2],items,[1,0,0],[0,1,0],[0,0,1],(-9,9,35.5,45.5))
    axes[2].set_title('USB-C BODY PRISM SECTION\nVIEW: FRONT (+Z) / TOP +Y')
    axes[2].set_xlabel('X mm');axes[2].set_ylabel('Y mm')
    axes[2].text(-8.6,44.6,'Sourced body width 12.2 mm\nConservative shoulder at rim',fontsize=8)
    fig.suptitle('Pocket Pi P1 | CAD sections | review only, no print release',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.93));fig.savefig(out/'structure_sections.png',dpi=170);plt.close(fig)

    # Exploded view keeps source axes; translations are ONLY for this illustration.
    items=[(front.translate((0,0,12)),blue),(rear.translate((0,0,-12)),gray)]
    items += [(parts[k],'#29363e' if k=='DISPLAY' else '#1c8069') for k in ['DISPLAY','PCB_BOARD']]
    items += [(n,silver) for n in mounts]+[(c,yellow) for c in m['caps'].values()]
    items += [(s.translate((0,0,-22)),silver) for s in m['screws']]
    w=np.array([1,.9,1.]);w/=np.linalg.norm(w);u=np.array([1,0,-1.]);u/=np.linalg.norm(u);v=np.cross(w,u)
    fig,ax=plt.subplots(figsize=(8,9))
    panel(ax,items,u,v,w,(-50,60,-66,65))
    ax.set_title('P1 EXPLODED | VIEW: ISO FRONT\nFront +12Z / rear -12Z / screws -22Z (illustration only)')
    ax.set_xlabel('projected mm');ax.set_ylabel('projected +Y / +Z mm')
    fig.tight_layout();fig.savefig(out/'assembly_exploded.png',dpi=160);plt.close(fig)


def render_manufacturing(out,parts,m,p,report,coupons):
    key='KEY1';cap=m['caps'][key];kd=m['key_data'][key];yc,zc=kd['center_yz_mm']
    cb=bounds(cap);blue,gray,yellow='#4e6580','#72869b','#e9a64a'
    fig,axes=plt.subplots(1,3,figsize=(16,6))
    clip=box_between([cb[0]-.2,yc-.05,zc-2.4,-24,yc+.05,zc+2.4])
    items=[(intersection(m['front'],clip),blue),(intersection(m['rear'],clip),gray),
           (intersection(cap,clip),yellow),(intersection(parts[key],clip),'#a76d31')]
    panel(axes[0],items,[1,0,0],[0,0,1],[0,1,0],(cb[0]-.2,-24,zc-2.4,zc+2.4))
    axes[0].set_title('KEY1 AXIAL SECTION\nFRONT +Z up / REAR down')
    axes[0].set_xlabel('X mm (press toward +X)');axes[0].set_ylabel('Z mm')
    f0,f1=kd['flange_x_mm']
    axes[0].annotate(f"{p['key_flange_thickness_mm']:.2f} flange",xy=((f0+f1)/2,zc+1.2),xytext=(cb[0]+.1,zc+2),
                     arrowprops={'arrowstyle':'->'},fontsize=8)
    axes[0].annotate(f"{p['key_tip_projection_mm']-p['key_tip_transition_mm']:.2f} flat + {p['key_tip_transition_mm']:.2f} taper",xy=(kd['tip_root_x_mm'],zc-.2),xytext=(cb[0]+.1,zc-2),
                     arrowprops={'arrowstyle':'->'},fontsize=8)
    x=(f0+f1)/2;clip=box_between([x-.04,yc-3,zc-3,x+.04,yc+3,zc+3])
    items=[(intersection(m['front'],clip),blue),(intersection(m['rear'],clip),gray),(intersection(cap,clip),yellow)]
    panel(axes[1],items,[0,1,0],[0,0,1],[-1,0,0],(yc-3,yc+3,zc-3,zc+3))
    axes[1].set_title('FLANGE CROSS SECTION / SIDE -X\nFRONT +Z up / REAR down')
    axes[1].set_xlabel('Y mm');axes[1].set_ylabel('Z mm')
    axes[1].text(yc-2.9,zc-2.8,f"Flange Y/Z {p['key_flange_yz_mm'][0]:.1f} x {p['key_flange_yz_mm'][1]:.1f}\nTransverse gap {p['key_guide_clearance_mm']:.2f} per side",fontsize=8)
    # Assembly pose retained for comparison; these three files are printed separately.
    u=np.array([1,0,-1.]);u/=np.linalg.norm(u);w=np.array([1,.8,1.]);w/=np.linalg.norm(w);v=np.cross(w,u)
    all_bounds=[bounds(s) for s in coupons.values()]
    center=np.array([(min(b[i] for b in all_bounds)+max(b[i+3] for b in all_bounds))/2 for i in range(3)])
    cu,cv=center@u,center@v
    items=[(coupons['coupon_front_guide'],blue),(coupons['coupon_rear_guide'],gray),(coupons['coupon_key1_cap'],yellow)]
    panel(axes[2],items,u,v,w,(cu-6,cu+6,cv-5,cv+5))
    axes[2].set_title('TINY COUPON / ISO FRONT\nAssembly pose; three separate parts')
    axes[2].set_xlabel('projected mm');axes[2].set_ylabel('projected +Y / +Z mm')
    mm=report['metrics'][key];budget=report['tolerance_budget']
    caption=(f"Body Y/Z {p['key_stem_yz_mm'][0]:.1f} x {p['key_stem_yz_mm'][1]:.1f}; length {mm['body_length_mm']:.2f}; "
             f"contact {p['key_tip_yz_mm'][0]:.1f} x {p['key_tip_yz_mm'][1]:.1f}; projection {p['key_tip_projection_mm']:.2f} mm. "
             f"Head end nominal {budget['head_end_nominal_mm']:.2f}; conditional residual {budget['head_end_effective_mm']:.2f} mm.\n"
             'SLA candidate / manufacturing_unverified / actual switch travel UNKNOWN / NO PRINT APPROVAL')
    fig.suptitle('P1 KEY MANUFACTURABILITY | FRONT/REAR remain source +Z/-Z',fontsize=14)
    fig.text(.5,.025,caption,ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.12,1,.93));fig.savefig(out/'key_manufacturing.png',dpi=170);plt.close(fig)
