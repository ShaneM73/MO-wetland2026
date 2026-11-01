#!/usr/bin/env bash
# Rebuild the site from the analysis outputs in ~/Wetland2026.
# Usage: build/build.sh [output dir]   (default: the repository root)
# The prep steps chain through intermediate JSON files in build/ (git-ignored):
#   prep -> data.json, prep2 -> data2, prep3 -> data3, prep4/4b/5 -> data4, geo_units -> geo_units_16m.tif, prep7 -> data7
# split.py then writes index.html + data/, and overview_build.py writes overview.html.
set -euo pipefail
PY=${PY:-python}   # e.g. PY=~/.conda/envs/wetland/bin/python
cd "$(dirname "$0")"
out=$(realpath "${1:-..}")
for s in prep prep2 prep3 prep4 prep4b prep5 geo_units prep7; do
  echo "== $s"; "$PY" "$s.py"
done
"$PY" split.py "$out" data7.json
"$PY" overview_build.py "$out"
