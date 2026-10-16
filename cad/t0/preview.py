"""Headless z-buffer rasterizer reused from P0."""
import numpy as np


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
