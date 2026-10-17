#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/generate-t0.sh
./scripts/generate-t0.sh --thickness 12.4 --output build/t0-12_4
./scripts/package-t0.sh
.venv/bin/python - <<'PY'
import json,zipfile
from pathlib import Path
with zipfile.ZipFile('build/t0-review-complete-assemblies.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ['build/t0','build/t0-12_4']:
  out=Path(folder);r=json.loads((out/'checks.json').read_text())
  z.write(out/r['complete_step_filename'],r['complete_step_filename'])
  z.write(out/'checks.json',f"checks_{r['parameters']['target_thickness_mm']:g}mm.json")
  if r['parameters']['target_thickness_mm']>12:
   for f in out.iterdir():
    if f.suffix in ['.step','.stl','.glb'] and f.name!=r['complete_step_filename']:
     z.write(f,'12.4mm/'+f.name)
print('Complete STEP review attachment: build/t0-review-complete-assemblies.zip')
PY
