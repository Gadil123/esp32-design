"""Box helper reused from P0; coordinates in mm."""
from build123d import Box


def box_between(b):
    x0,y0,z0,x1,y1,z1 = b
    return Box(x1-x0, y1-y0, z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))


