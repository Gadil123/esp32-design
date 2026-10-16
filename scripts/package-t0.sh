#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import json,shutil
from pathlib import Path
src=Path('build/t0');dst=Path('deliverables/t0');r=json.loads((src/'checks.json').read_text())
assert r['geometry_status']=='PASS' and r.get('exports_complete')
dst.mkdir(parents=True,exist_ok=True)
names=['front_shell','rear_shell','key1_cap','key2_cap','key3_cap']
files=[f'{n}.{ext}' for n in names for ext in ['step','stl']]
files+=['assembly_light.step','assembly_light.glb','front.png','rear.png','side.png','iso_front.png','thickness_section.png','connection_sections.png','connector_layout.png','interface_openings.png','checks.json']
for f in files:shutil.copy2(src/f,dst/f)
extra=Path('build/t0-12_4/checks.json')
if extra.exists():
 rr=json.loads(extra.read_text())
 assert rr['geometry_status']=='PASS' and rr.get('exports_complete')
 shutil.copy2(extra,dst/'checks_12_4mm.json')
 shutil.copy2(extra.parent/'assembly_light.glb',dst/'assembly_light_12_4mm.glb')
print('Packaged T0 lightweight review files; complete original-geometry STEP stays outside Git history')
PY
