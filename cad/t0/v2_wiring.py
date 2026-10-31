"""V2 candidate speaker route: enters the fence at the speaker's -Y edge.

The old builder's final Y was the speaker center. V2 only changes that datum and
the loop Y; wire section, bend radius and the connector plug envelope stay as
inherited candidates. The actual lead exit still needs a photo/measurement.
"""
from copy import deepcopy
from g_v1_95mm_wiring import build as _old


def build(parts, p, m):
    q = deepcopy(p)
    q['narrow_wiring'] = deepcopy(p['narrow_wiring'])
    sx, sy = p['speaker']['center_xy_mm']
    sh = p['speaker']['xyz_mm'][1]
    entry = sy + sh / 2
    q['narrow_wiring']['speaker_loop_y_mm'] = entry - 4.0
    q['speaker'] = deepcopy(p['speaker'])
    q['speaker']['center_xy_mm'] = [sx, entry]
    return _old(parts, q, m)
