#!/usr/bin/env python3
"""Actual downloaded95.60 review package: placements, validity, raw STEP source.

Uses the frozen task26 verifier's per-solid bounds/volume/face-count method.
No SHA/checksum validation, FreeCAD GUI, or physical-function approval.
"""
import argparse,gc,json,zipfile,sys,subprocess
from pathlib import Path
from build123d import import_step
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad/t0'))
from t0_reference import load

def rows(shape):
    result=[]
    for index,s in enumerate(shape.solids()):
        assert s.is_valid
        b=s.bounding_box();result.append(dict(index=index,bounds=[*b.min,*b.max],volume=s.volume,faces=len(s.faces())))
    return sorted(result,key=lambda r:tuple(round(v,4) for v in r['bounds'])+(round(r['volume'],4),r['faces']))
def compare(a,b,raw_shapes=None,exported_shapes=None):
    a=sorted(a,key=lambda r:tuple(round(v,4) for v in r['bounds'])+(round(r['volume'],4),r['faces']))
    b=sorted(b,key=lambda r:tuple(round(v,4) for v in r['bounds'])+(round(r['volume'],4),r['faces']))
    assert len(a)==len(b)
    bd=max(abs(x-y) for e,o in zip(a,b) for x,y in zip(e['bounds'],o['bounds']))
    vd=max(abs(e['volume']-o['volume'])/max(e['volume'],1e-9) for e,o in zip(a,b));faces=all(e['faces']==o['faces'] for e,o in zip(a,b))
    assert bd<1e-5 and faces
    native_checks=[]
    if raw_shapes is None:
        assert vd<1e-6
    else:
        from OCP.ShapeAnalysis import ShapeAnalysis_ShapeTolerance
        for raw,exported in zip(a,b):
            rel=abs(raw['volume']-exported['volume'])/max(raw['volume'],1e-9)
            if rel<=1e-6:continue
            x,y=raw_shapes[raw['index']],exported_shapes[exported['index']]
            # No input geometry or tolerance is manually changed.
            # Native BRep booleans determine material equivalence when the
            # non-invariant scalar mass integral differs after STEP transfer.
            forward=x-y;backward=y-x
            fv,bv=forward.volume,backward.volume
            assert not forward.solids() and not backward.solids() and abs(fv)<1e-9 and abs(bv)<1e-9
            native_checks.append(dict(raw_solid_index=raw['index'],exported_solid_index=exported['index'],
                raw_default_volume_mm3=raw['volume'],exported_default_volume_mm3=exported['volume'],default_relative_volume_difference=rel,
                forward_difference_mm3=fv,reverse_difference_mm3=bv,
                native_max_topological_tolerance_mm=ShapeAnalysis_ShapeTolerance().Tolerance(x.wrapped,1),
                exported_max_topological_tolerance_mm=ShapeAnalysis_ShapeTolerance().Tolerance(y.wrapped,1)))
    return dict(solids=len(a),maximum_per_solid_bounds_difference_mm=bd,maximum_per_solid_relative_volume_difference=vd,per_solid_face_counts_match=faces,
        native_BRep_difference_checks_for_default_volume_discrepancies=native_checks,
        interpretation='Strict scalar comparison for same-export groups. Raw-source mass discrepancies explicitly retained and checked by BOTH native-tolerance BRep cuts, without manually relaxing tolerance; native-tolerance equivalence, not a mathematical-zero or manufacturing precision guarantee.')
def phase(name,dest,output):
    if name=='full':
        shape=import_step(dest/'assembly_complete.step');rr=rows(shape)
        b=shape.bounding_box();result=dict(rows=rr,bounds=[*b.min,*b.max])
    elif name=='groups':
        observed=[];counts={}
        for key in ['OfficialBoard_REAL_723','FrontShell_BOOT_RECT_BAT_L','RearShell_TWO_CLIPS','Four_M2_5_CANDIDATE_SCREWS','MEASURED_ACCESSORY_ENVELOPES_AND_CONDITIONAL_WIRES_KEEP_OUT']:
            print('Read downloaded group',key,flush=True)
            shape=import_step(dest/'viewer'/(key+'.step'));rr=rows(shape);counts[key]=len(rr);observed.extend(rr)
            del shape;gc.collect()
        result=dict(rows=observed,counts=counts)
    elif name=='raw':
        print('Read downloaded board and original official source',flush=True)
        board=import_step(dest/'viewer/OfficialBoard_REAL_723.step')
        parts,_,_=load(ROOT.parent/'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
        result=compare(rows(parts['ASSEMBLY']),rows(board),parts['ASSEMBLY'].solids(),board.solids())
    output.write_text(json.dumps(result,indent=2)+'\n')
def main():
    if len(sys.argv)>1 and sys.argv[1]=='--phase':
        phase(sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]));return
    ap=argparse.ArgumentParser();ap.add_argument('downloaded_zip',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    dest=a.downloaded_zip.parent/'verified_95mm';dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(a.downloaded_zip) as z:entries=z.namelist();z.extractall(dest)
    results={}
    # Separate processes release OpenCascade STEP caches between large imports.
    for name in ['full','groups','raw']:
        path=dest/(name+'_verification.json')
        print('Verify phase',name,flush=True)
        subprocess.run([sys.executable,__file__,'--phase',name,str(dest),str(path)],check=True)
        results[name]=json.loads(path.read_text())
    expected=results['full']['rows'];bb=results['full']['bounds'];counts=results['groups']['counts']
    assert len(expected)==739 and counts['OfficialBoard_REAL_723']==723
    consistency=compare(expected,results['groups']['rows']);source=results['raw']
    assert abs(bb[3]-bb[0]-95.6)<1e-5 and abs(bb[4]-bb[1]-77.86)<1e-5 and bb[5]-bb[2]<=12.4
    result=dict(status='DOWNLOADED_95_60_ASSEMBLY_AND_RAW_SOURCE_VERIFIED',asset=a.downloaded_zip.name,downloaded_bytes=a.downloaded_zip.stat().st_size,
        complete_valid_solids=739,component_valid_solids=counts,same_coordinate_group_consistency=consistency,downloaded_board_vs_original_official_STEP=source,
        full_bounds_mm=bb,maximum_thickness_mm=bb[5]-bb[2],zip_entries=entries,
        scope='Actual authorized ZIP download and STEP semantic checks; not FreeCAD GUI, strength, material, real harness or acoustic approval.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)
if __name__=='__main__':main()
