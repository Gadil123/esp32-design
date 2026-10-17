#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/generate-t0.sh --parameters cad/t0/t0-a-parameters.json --output build/t0-a-12
./scripts/generate-t0.sh --parameters cad/t0/t0-a-parameters.json --thickness 12.4 --output build/t0-a-12_4
./scripts/generate-t0-key-study.sh
.venv/bin/python cad/t0/package_t0_a.py
