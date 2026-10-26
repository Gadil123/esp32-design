#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export XDG_CACHE_HOME="$PWD/build/cache"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$PWD/build/matplotlib"
exec .venv/bin/python cad/t0/generate_g_v4.py
