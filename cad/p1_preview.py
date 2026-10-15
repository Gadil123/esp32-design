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
    clip=box_between([-30,yc-.08,-8.5,-23,yc+.08,-4.7])
    items=[(intersection(front,clip),blue),(intersection(rear,clip),gray),
           (intersection(m['caps'][key],clip),yellow),(intersection(parts[key],clip),'#a76d31')]
    panel(axes[1],items,[1,0,0],[0,0,1],[0,1,0],(-30,-23,-8.5,-4.7))
    axes[1].set_title('BAT_PWR GUIDE SECTION\nFRONT +Z up / REAR down')
    axes[1].set_xlabel('X mm');axes[1].set_ylabel('Z mm')
    axes[1].text(-29.8,-8.25,'0.15 mm rest gap\n0.40 mm CAP budget\nactual switch travel UNKNOWN',fontsize=8)
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
