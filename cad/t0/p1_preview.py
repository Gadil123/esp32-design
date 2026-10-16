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
