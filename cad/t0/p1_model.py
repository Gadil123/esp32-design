"""P1: four shared factory-nut fasteners, split guides, captive key pistons."""
from build123d import Align, Axis, Cylinder, GeomType, Plane, Rectangle, RectangleRounded, extrude, loft
from model import box_between
from reference import bounds

FUNCTIONS = {'KEY1':'BAT_PWR', 'KEY2':'BOOT', 'KEY3':'RESET'}


def cylinder(radius, z0, z1, x, y):
    return Cylinder(radius,z1-z0,align=(Align.CENTER,Align.CENTER,Align.MIN)).translate((x,y,z0))


def contact_face(key):
    """Select the outward, planar actuator face; do not use switch whole-body center."""
    x=bounds(key)[0]
    candidates=[f for f in key.faces() if f.geom_type==GeomType.PLANE
                and f.normal_at().X < -.99 and abs(bounds(f)[0]-x)<.001]
    assert len(candidates)==1, f'Ambiguous actuator face: {len(candidates)}'
    return candidates[0]


def usb_mouth_face(connector):
    """The +Y rim face, not whole J2 bounds (which include raised rear pins)."""
    ymax=bounds(connector)[4]
    candidates=[f for f in connector.faces() if f.geom_type==GeomType.PLANE
                and f.normal_at().Y>.99 and abs(bounds(f)[4]-ymax)<.01]
    assert len(candidates)==1, f'Ambiguous USB mouth: {len(candidates)}'
    return candidates[0]
