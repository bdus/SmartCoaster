#!/usr/bin/env bash
# SmartCoaster appearance delivery: assembly renders + Bambu-ready 3MF, both versions.
# One command, idempotent.  Blender 4.5.3 headless, Cycles CPU.
#
#   bash appearance/render/run_all.sh            # everything (~10-12 min)
#   SC_SAMPLES=16 bash appearance/render/run_all.sh   # fast preview (~1-2 min)
#
# Outputs:
#   appearance/render/{round,square}/{hero,top,macro_edge,print_top,section_exploded}.png
#   appearance/render/{round,square}/{scene.blend,scene_section.blend,scene_info.json,annotations.json}
#   appearance/build/render/{round,square}/{macro_edge,section_seated,section_exploded}.png (raw)
#   appearance/build/3mf/{round,square}.3mf + reference copies + validation.json
#   appearance/render/board.png
set -euo pipefail
cd "$(dirname "$0")/../.."

BLENDER="${BLENDER:-/data/Documents/tools/blender/blender}"
PY="${PY:-python3}"

echo "== 1/3 Blender assembly + renders (round, square) =="
"$BLENDER" -b --python appearance/render/build_scene.py

echo "== 2/3 Bambu 3MF assembly + validation =="
"$PY" appearance/render/make_3mf.py

echo "== 3/3 post-process: macro caption, section composition, comparison board =="
"$PY" appearance/render/postprocess.py

echo "== done =="
ls -la appearance/render/round appearance/render/square appearance/build/3mf | sed -n '1,80p'
