#!/usr/bin/env bash
# 3D-print delivery stage for the two appearance versions (round/LUMEN+dog,
# square/square_v1+elf).  Idempotent: re-renders the bed layouts, then rebuilds
# the reference sheets, manifests, README and combined board.
#
#   bash render/print/appearance/run_print_stage.sh
#   SC_SAMPLES=16 BLENDER=... bash ... (samples are fixed in the layout script)
#
# Outputs under render/print/appearance/:
#   {round,square}/print_iso.png, print_top.png   bed layout renders (1600x1100 / 1600x1200)
#   {round,square}/layout.json                    measured layout + validation
#   {round,square}/PRINT_SHEET.png                1800x1200 reference sheet
#   {round,square}/PRINT_READY.3mf                assembled print-ready 3MF copy
#   {round,square}/manifest.json + README.md      delivery manifest / README
#   PRINT_SHEET_APPEARANCE.png                    combined board
set -euo pipefail
cd "$(dirname "$0")/../../.."

BLENDER="${BLENDER:-/data/Documents/tools/blender/blender}"
PY="${PY:-python3}"

echo "== print delivery stage: bed layout + renders =="
"$BLENDER" -b --python render/print/appearance/print_layout_appearance.py

echo "== print delivery stage: sheets + manifests + PRINT_READY + combined board =="
"$PY" render/print/appearance/make_sheet_appearance.py

echo "== print delivery stage done =="
ls -la render/print/appearance/round render/print/appearance/square \
       render/print/appearance/PRINT_SHEET_APPEARANCE.png
