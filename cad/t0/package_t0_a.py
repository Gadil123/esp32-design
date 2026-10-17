"""Package A only; original B deliverables remain intact."""
import json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
with zipfile.ZipFile(ROOT/'build/t0-a-review-complete.zip','w',zipfile.ZIP_DEFLATED) as z:
    for case in ['12','12_4']:
        src=ROOT/f'build/t0-a-{case}';dst=ROOT/f'deliverables/t0-a/{case}mm';dst.mkdir(parents=True,exist_ok=True)
        report=json.loads((src/'checks.json').read_text())
        assert report['geometry_status']=='PASS' and report['exports_complete']
        for f in src.iterdir():
            if f.name==report['complete_step_filename']:
                z.write(f,f'A-{case}mm/{f.name}')
            elif f.suffix in ['.step','.stl','.glb','.png','.json']:
                shutil.copy2(f,dst/f.name)
                if f.suffix!='.png':z.write(f,f'A-{case}mm/{f.name}')
    study=ROOT/'build/t0-key-study';dst=ROOT/'deliverables/t0-a/key-study'
    shutil.copytree(study,dst,dirs_exist_ok=True)
    for f in study.rglob('*'):
        if f.is_file():z.write(f,'key-study/'+str(f.relative_to(study)))
print('A packaged separately; B preserved. Full source assembly STEP stays outside Git history.')
