#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import shutil
source = Path('build/p0')
report = json.loads((source/'checks.json').read_text())
assert report['status'] == 'PASS', 'Regenerate and resolve geometry failures before packaging'
target = Path('deliverables/p0')
target.mkdir(parents=True, exist_ok=True)
for name in ['front_shell.step', 'rear_shell.step', 'front_shell.stl', 'rear_shell.stl',
             'assembly_light.step', 'assembly_light.glb', 'front.png', 'rear.png',
             'side.png', 'iso_front.png', 'checks.json']:
    shutil.copy2(source/name, target/name)
print(f'Packaged P0 review files: {target}')
PY
