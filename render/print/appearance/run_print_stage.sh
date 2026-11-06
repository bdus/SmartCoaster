#!/usr/bin/env bash
# 3D-print delivery stage (task-6): REAL print orientation = plate+print top-face
# down (art face = first layer on the bed), button lying flat like a coin, one
# flat STL folder render/print/stl/.  Idempotent; last 4/4 step of run_all.sh.
#
#   bash render/print/appearance/run_print_stage.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."

BLENDER="${BLENDER:-/data/Documents/tools/blender/blender}"
PY="${PY:-python3}"

echo "== print delivery: bed layout + renders (print pose) =="
"$BLENDER" -b --python render/print/appearance/print_layout_appearance.py

echo "== print delivery: baked STLs -> render/print/stl/ + bed-layout 3MF + checksums =="
"$PY" render/print/appearance/make_stl_delivery.py

echo "== print delivery: sheets + manifests + README + combined board =="
"$PY" render/print/appearance/make_sheet_appearance.py

echo "== print delivery stage done =="
ls -la render/print/stl | sed -n '1,40p'
ls -la render/print/appearance/round render/print/appearance/square \
       render/print/appearance/PRINT_SHEET_APPEARANCE.png
