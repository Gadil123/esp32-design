"""Run in desktop FreeCAD Python console; no FreeCAD dependency for generation.

exec(open('/absolute/view_g_v1_95mm_freecad.py').read())
open_assembly('/absolute/unpacked/viewer')
exploded() / assembled() -- visual inspection, not a kinematic solver.
"""
from pathlib import Path
_NAMES=['OfficialBoard_REAL_723','FrontShell_BOOT_RECT_BAT_L','RearShell_TWO_CLIPS',
        'Four_M2_5_CANDIDATE_SCREWS','MEASURED_ACCESSORY_ENVELOPES_AND_CONDITIONAL_WIRES_KEEP_OUT']
_DOC=None

def open_assembly(directory):
    import FreeCAD as App,Part,FreeCADGui as Gui
    global _DOC
    _DOC=App.newDocument('G_V1_95_60_CONDITIONAL')
    for i,name in enumerate(_NAMES):
        obj=_DOC.addObject('Part::Feature',f'Part{i}')
        obj.Label=name;obj.Shape=Part.read(str(Path(directory)/(name+'.step')))
        obj.addProperty('App::PropertyPlacement','AssembledPlacement','Review');obj.AssembledPlacement=obj.Placement
        obj.ViewObject.ShapeColor=[(.7,.73,.76),(.24,.38,.47),(.35,.5,.58),(.65,.65,.67),(.81,.65,.32)][i]
    _DOC.recompute();Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
    return _DOC

def assembled():
    if _DOC is None:raise RuntimeError('Call open_assembly(directory) first')
    for obj in _DOC.Objects:obj.Placement=obj.AssembledPlacement
    _DOC.recompute()

def exploded(distance_mm=18):
    import FreeCAD as App,FreeCADGui as Gui
    assembled()
    for obj,scale in zip(_DOC.Objects,[.5,0,-1,-2,-.5]):
        p=App.Placement(obj.AssembledPlacement);p.Base=p.Base+App.Vector(0,0,distance_mm*scale);obj.Placement=p
    _DOC.recompute();Gui.activeDocument().activeView().fitAll()
