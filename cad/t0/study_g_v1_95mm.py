"""Small real-BRep layout search, before rebuilding shells."""
import json
from pathlib import Path
from build123d import import_step
from model import box_between as box
from p1_checks import intersection,common_volume
from t0_e_gate import source_clashes
ROOT=Path(__file__).resolve().parents[2]

def study(parts,out,config):
    f=import_step(ROOT/'deliverables/t0-g-v1-boot-rect/front_shell.step')
    source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    receiver=intersection(f,box([65.7,-30,-9.5,67.45,-26,-1])).translate((-config['width_reduction_mm'],0,0))
    fence=intersection(f,box([29.4,-34,-8.2,62.6,-10.8,-.5001]))
    rows=[]
    for dx in config['speaker_search_shift_x_mm']:
        sf=fence.translate((dx,0,0));body=box([31+dx,-32.4,-7.5,61+dx,-12.4,-1])
        rows.append(dict(speaker_shift_x_mm=dx,receiver_fence_overlap_mm3=common_volume(receiver,sf),
            receiver_to_fence_distance_mm=receiver.distance_to(sf),fence_source_hits=source_clashes(sf,parts,source,.001),
            body_source_hits=source_clashes(body,parts,source,.001),fence_to_display_mm=sf.distance_to(parts['DISPLAY'])))
    r=dict(stage='LOCAL_REAL_BREP_SEARCH_ONLY',reference='Frozen shell STEP and original official occurrence BReps, USB+Y FRONT+Z; final acceptance requires full rebuilt assembly.',rows=rows,selected_shift_x_mm=config['selected_speaker_center_xy_mm'][0]-46)
    (out/'local_search.json').write_text(json.dumps(r,indent=2)+'\n');return r
