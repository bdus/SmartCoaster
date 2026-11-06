#!/usr/bin/env bash
# 3D-print delivery stage (task-9 structure): REAL print orientation = plate+print
# top-face-down (art face = first layer on the bed), button lying flat like a
# coin.  ONE delivery root render/print/stl/ classified by version:
#   render/print/stl/{round,square}/  STLs + PRINT_READY.3mf + PRINT_SHEET.png
#                                     + print_iso/top.png + layout/manifest/README
#                                     + CHECKSUMS.sha256
#   render/print/stl/                 README.md + delivery.json + PRINT_SHEET_BOTH.png
# Idempotent; last 4/4 step of appearance/render/run_all.sh.
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
find render/print/stl -maxdepth 2 -type f | sort
ls -la render/print/stl/round render/print/stl/square
