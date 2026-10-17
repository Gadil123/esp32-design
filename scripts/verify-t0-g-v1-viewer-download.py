#!/usr/bin/env python3
"""Verify an ACTUALLY downloaded Task26 viewer ZIP; no SHA/checksum step.

Full STEP and independent same-coordinate components must describe the same
739 valid physical solids. This checks export placement, not native switch
function or FreeCAD GUI performance.
"""
import argparse,gc,json,zipfile
from pathlib import Path
from build123d import import_step


def rows(shape):
    out=[]
    for s in shape.solids():
        assert s.is_valid
        b=s.bounding_box();out.append(dict(bounds=[b.min.X,b.min.Y,b.min.Z,b.max.X,b.max.Y,b.max.Z],volume=s.volume,faces=len(s.faces())))
    return sorted(out,key=lambda r:tuple(round(v,4) for v in r['bounds'])+(round(r['volume'],4),r['faces']))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('downloaded_zip',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    dest=a.downloaded_zip.parent/'verified_viewer';dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(a.downloaded_zip) as z:entries=z.namelist();z.extractall(dest)
    print('Read downloaded full STEP',flush=True)
    full=import_step(dest/'boot_rect_task26/assembly_complete_12_4mm.step');expected=rows(full);assert len(expected)==739
    b=full.bounding_box();full_bounds=[b.min.X,b.min.Y,b.min.Z,b.max.X,b.max.Y,b.max.Z]
    del full;gc.collect()
    observed=[];counts={}
    for p in [dest/'boot_rect_task26/FrontShell.step',*sorted((dest/'common').glob('*.step'))]:
        print('Read downloaded component',p.name,flush=True)
        shape=import_step(p);rr=rows(shape);counts[p.stem]=len(rr);observed.extend(rr)
        del shape;gc.collect()
    observed=sorted(observed,key=lambda r:tuple(round(v,4) for v in r['bounds'])+(round(r['volume'],4),r['faces']))
    assert len(observed)==739 and counts['OfficialBoard_723']==723
    bd=max(abs(x-y) for e,o in zip(expected,observed) for x,y in zip(e['bounds'],o['bounds']))
    vd=max(abs(e['volume']-o['volume'])/max(e['volume'],1e-9) for e,o in zip(expected,observed))
    face_match=all(e['faces']==o['faces'] for e,o in zip(expected,observed))
    assert bd<1e-5 and vd<1e-6 and face_match
    report=dict(status='DOWNLOADED_ZIP_AND_EXACT_PARTSET_VERIFIED',asset=a.downloaded_zip.name,downloaded_bytes=a.downloaded_zip.stat().st_size,
        zip_entries=entries,complete_valid_solids=739,component_valid_solids=counts,maximum_per_solid_bounds_difference_mm=bd,
        maximum_per_solid_relative_volume_difference=vd,per_solid_face_counts_match=face_match,
        complete_bounds_mm=full_bounds,maximum_thickness_mm=full_bounds[5]-full_bounds[2],
        verification_scope='Actual downloaded archive, STEP validity and same-coordinate export consistency; no FreeCAD GUI run or physical-fit approval.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)


if __name__=='__main__':main()
