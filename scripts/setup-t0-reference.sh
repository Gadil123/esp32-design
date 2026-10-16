#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
reference_dir="$(dirname "$PWD")/ESP32-C5-Touch-LCD-2.8"
reference_revision="$(python3 -c 'import json; print(json.load(open("cad/t0/official-reference.json"))["revision"])')"
if [[ -e "$reference_dir" ]]; then
  echo "Reference directory already exists: $reference_dir (left untouched)"
  exit 0
fi
git clone --depth 1 --filter=blob:none --sparse https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8.git "$reference_dir"
git -C "$reference_dir" sparse-checkout set dimensions schematic docs
git -C "$reference_dir" fetch --depth 1 origin "$reference_revision"
git -C "$reference_dir" checkout --detach FETCH_HEAD
