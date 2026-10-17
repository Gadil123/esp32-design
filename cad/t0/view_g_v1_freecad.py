"""Run inside desktop FreeCAD's Python console, from the extracted viewer ZIP.

No add-on or Assembly workbench. Display/explosion only, no new CAD geometry.
The original723 solids are one selectable Part::Feature to limit the model tree.
"""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part

ROOT=Path(__file__).resolve().parent


def open_version(version='boot_rect_task26'):
    doc=App.newDocument('PocketPi_'+version)
    files=[('FrontShell',ROOT/version/'FrontShell.step'),('RearShell',ROOT/'common/RearShell.step'),
           ('OfficialBoard_723',ROOT/'common/OfficialBoard_723.step'),('Hardware',ROOT/'common/Hardware.step'),
           ('Accessories_UNVERIFIED',ROOT/'common/Accessories_UNVERIFIED.step')]
    for name,path in files:
        obj=doc.addObject('Part::Feature',name);obj.Label=name;obj.Shape=Part.read(str(path))
        obj.addProperty('App::PropertyPlacement','AssembledPlacement','Viewer')
        obj.AssembledPlacement=obj.Placement
        obj.ViewObject.ShapeColor=(.2,.3,.35) if name=='FrontShell' else (.65,.68,.7)
    doc.recompute();Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
    return doc


def assembled(doc=None):
    doc=doc or App.ActiveDocument
    for obj in doc.Objects:obj.Placement=obj.AssembledPlacement
    doc.recompute();Gui.activeDocument().activeView().fitAll()


def exploded(doc=None):
    """Visual separation ONLY: not a collision-free service/assembly sequence."""
    doc=doc or App.ActiveDocument;assembled(doc)
    for name,delta in [('RearShell',(0,0,-25)),('OfficialBoard_723',(0,0,-12)),('Hardware',(0,0,-40)),('Accessories_UNVERIFIED',(45,0,0))]:
        obj=doc.getObject(name);p=obj.AssembledPlacement;p.Base=p.Base+App.Vector(*delta);obj.Placement=p
    doc.recompute();Gui.activeDocument().activeView().fitAll()


open_version()
