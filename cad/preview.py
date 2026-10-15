"""Headless orthographic images of CAD tessellations; never used to measure geometry."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reference import bounds

COLORS = {'FRONT':'#4e6580', 'REAR':'#72869b', 'PCB_BOARD':'#1c8069',
          'DISPLAY':'#29363e','J2_USB_SIDE':'#c9ccd1','KEY1':'#e9a64a',
          'KEY3':'#e9a64a','KEY2':'#e9a64a','MIC1':'#bd6986','MOUNT':'#adb4bc'}


def render(out, parts, mounts, front, rear, p, stage='P0', extras=None):
    items = [('FRONT',front),('REAR',rear)] + [(k,parts[k]) for k in COLORS if k in parts]
    items += [('MOUNT',m) for m in mounts]
    palette=dict(COLORS)
    for i,(shape,color) in enumerate(extras or []):
        tag=f'EXTRA_{i}';palette[tag]=color;items.append((tag,shape))
    meshes = []
    for name,shape in items:
        v,t = shape.tessellate(p['preview_mesh_deflection_mm'],0.3)
        meshes.append((name,np.asarray([tuple(x) for x in v])[np.asarray(t)]))
    # u is screen-right, v is screen-up, w points from object toward viewer.
    views = {
        'FRONT':([1,0,0],[0,1,0],[0,0,1]),
        'REAR':([-1,0,0],[0,1,0],[0,0,-1]),
        'SIDE':([0,0,1],[0,1,0],[-1,0,0]),
        'ISO_FRONT':([1,0,-1],[-0.45,1,-0.45],[1,0.9,1])}
    for title,(u,v,w) in views.items():
        w=np.array(w,dtype=float);w/=np.linalg.norm(w)
        u=np.array(u,dtype=float);u/=np.linalg.norm(u)
        v=np.cross(w,u);v/=np.linalg.norm(v)
        fig,axes=plt.subplots(1,2,figsize=(11,7),facecolor='#f0f2f5')
        for ax,hide in zip(axes,[False,True]):
            triangles=[]; colors=[]
            for name,tri in meshes:
                if hide and (name in ['FRONT','REAR'] or name.startswith('EXTRA_')):continue
                triangles.extend(tri)
                colors.extend([palette[name]]*len(tri))
            tri=np.asarray(triangles)
            xy=np.stack([tri@u,tri@v],axis=2)
            normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
            norms=np.linalg.norm(normals,axis=1);norms[norms==0]=1
            light=.55+.45*np.abs(normals@w/norms)
            from matplotlib.colors import to_rgb
            rgb=np.array([to_rgb(c) for c in colors])*light[:,None]
            # Per-pixel depth, rather than centroid sorting: large panel triangles
            # must occlude the components behind them in oblique views as well.
            pixels = rasterize(xy,tri@w,rgb)
            ax.imshow(pixels,extent=(-47,47,-48,54),origin='lower',interpolation='nearest')
            ax.set_xlim(-47,47);ax.set_ylim(-48,54);ax.set_aspect('equal')
            ax.set_facecolor('#f0f2f5');ax.set_xlabel('projected mm');ax.set_ylabel('UP / +Y (mm)')
            ax.set_title('Reference geometry / shells hidden' if hide else f'{stage} assembled shells')
            # Projected center labels explicitly verify front/rear handedness.
            if hide:
                for key in ['J2_USB_SIDE','KEY1','KEY3','KEY2','MIC1']:
                    b=bounds(parts[key]);c=(np.array(b[:3])+np.array(b[3:]))/2
                    px,py=c@u,c@v
                    direction=-1 if px<0 else 1
                    ax.annotate(key.replace('_USB_SIDE',' / USB-C'),(px,py),
                                (direction*28,py),ha='right' if direction<0 else 'left',
                                fontsize=7,arrowprops={'arrowstyle':'-','lw':.6})
            ax.grid(alpha=.14)
        view_label='SIDE / FRONT right / REAR left' if title=='SIDE' else title
        fig.suptitle(f'Pocket Pi {stage} | VIEW: {view_label} | USB-C = +Y / TOP',fontsize=15)
        fig.text(.5,.02,f'Derived from original STEP. {stage} review only; battery/speaker, actual switch travel and acoustic port unverified.',
                 ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/f'{title.lower()}.png',dpi=160);plt.close(fig)


def rasterize(xy, depth, colors, extent=(-47,47,-48,54), size=(660,716)):
    width,height=size
    xmin,xmax,ymin,ymax=extent
    pixel_xy=(xy-np.array([xmin,ymin]))*np.array([(width-1)/(xmax-xmin),(height-1)/(ymax-ymin)])
    image=np.empty((height,width,3));image[:]=np.array([240,242,245])/255
    zbuffer=np.full((height,width),-np.inf)
    for pts,z,color in zip(pixel_xy,depth,colors):
        lo=np.maximum(np.floor(pts.min(axis=0)).astype(int),[0,0])
        hi=np.minimum(np.ceil(pts.max(axis=0)).astype(int),[width-1,height-1])
        if np.any(hi<lo):continue
        (x0,y0),(x1,y1),(x2,y2)=pts
        den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(den)<1e-10:continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        a=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
        b=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
        c=1-a-b
        zz=a*z[0]+b*z[1]+c*z[2]
        tile=zbuffer[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        keep=(a>=-1e-8)&(b>=-1e-8)&(c>=-1e-8)&(zz>tile)
        tile[keep]=zz[keep]
        image[lo[1]:hi[1]+1,lo[0]:hi[0]+1][keep]=color
    return image
