#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import shutil
source=Path('build/p1');target=Path('deliverables/p1')
report=json.loads((source/'checks.json').read_text())
assert report['status']=='PASS' and report.get('exports_complete'), 'P1 generation/exports must complete successfully'
target.mkdir(parents=True,exist_ok=True)
names=['front_shell','rear_shell','key1_cap','key2_cap','key3_cap','coupon_front_guide','coupon_rear_guide','coupon_key1_cap']
files=[f'{name}.{ext}' for name in names for ext in ['step','stl']]
files+=['assembly_light.step','assembly_light.glb','front.png','rear.png','side.png','iso_front.png',
        'structure_sections.png','assembly_exploded.png','key_manufacturing.png','checks.json']
for name in files:shutil.copy2(source/name,target/name)
print(f'Packaged P1 review files: {target}')
PY
