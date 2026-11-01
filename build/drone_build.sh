#!/usr/bin/env bash
# Build drone.html and data/drone/ (Barton Fen drone LiDAR + orthophoto tiles) from ~/Wetland2026/data/LiDAR/BartonFen_20250415_DSM_Ortho.
# Usage: build/drone_build.sh [output dir] [work dir]   (defaults: repository root, build/drone_work, git-ignored; ~3 GB, ~6 min)
set -euo pipefail
PY=${PY:-python}
here=$(cd "$(dirname "$0")" && pwd)
out=$(realpath "${1:-$here/..}"); work=${2:-$here/drone_work}
mkdir -p "$work"; cd "$work"
bin=$(dirname "$(command -v "$PY" || echo "$PY")")
export PROJ_DATA=${PROJ_DATA:-$bin/../share/proj}
S=~/Wetland2026/data/LiDAR/BartonFen_20250415_DSM_Ortho
t2t() { "$PY" "$bin/gdal2tiles.py" --xyz -w none -q --tiledriver WEBP --processes 48 "$@"; }
"$bin/gdal_translate" -q -of VRT -colorinterp red,green,blue,alpha -a_nodata none $S/Ortho_Preliminary_Lidar_20250415_WGS1984_UTMZone15.tif ortho.vrt
"$bin/gdal_translate" -q -of VRT -projwin 670181 4168410 670600 4168005 ortho.vrt ortho_site.vrt     # matches Z22 in overlays.py
"$PY" "$here/relief.py"; "$PY" "$here/bare.py"
d=$out/data/drone; rm -rf "$d"; mkdir -p "$d"
t2t -z 14-21 -r average --webp-quality 78 ortho.vrt "$d/ortho"
t2t -z 22 -r average --webp-quality 78 ortho_site.vrt "$d/ortho"
t2t -z 14-21 -r average --webp-quality 80 relief.tif "$d/relief"
t2t -z 14-20 -r near --webp-lossless height_rgba.tif "$d/height"
t2t -z 14-19 -r average --webp-quality 82 bare_rgba.tif "$d/bare"
"$PY" "$here/overlays.py" "$d"
cp "$here/drone_template.html" "$out/drone.html"
du -sh "$d"
