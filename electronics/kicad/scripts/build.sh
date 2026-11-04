#!/usr/bin/env bash
# Regenerate everything under electronics/kicad and re-run all checks.
set -euo pipefail
source /data/Documents/tools/kicad/bin/env.sh
PY=/data/Documents/tools/sim-venv/bin/python
cd "$(dirname "$0")"

echo "== schematic =="
$PY gen_sch.py | tail -2
$PY verify.py | tail -2
kicad-cli sch erc --format report --severity-all --units mm \
    -o ../build/ERC.rpt ../smartcoaster/smartcoaster.kicad_sch 2>/dev/null | tail -2

echo "== pcb =="
$PY gen_pcb.py | tail -1
$PY check_pcb.py | tail -2
kicad-cli pcb drc --format report --severity-all --units mm \
    -o ../build/DRC.rpt ../smartcoaster/smartcoaster.kicad_pcb 2>/dev/null | tail -2

echo "== outputs =="
$PY gen_bom.py | tail -1
kicad-cli sch export pdf -o ../build/sch.pdf ../smartcoaster/smartcoaster.kicad_sch >/dev/null 2>&1 || true
pdftoppm -png -r 110 ../build/sch.pdf ../build/sch 2>/dev/null || true
$PY render_pcb.py | tail -1
echo done
