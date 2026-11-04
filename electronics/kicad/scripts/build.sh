#!/usr/bin/env bash
# Regenerate everything under electronics/kicad and re-run all checks:
# schematic -> ERC -> unrouted PCB -> Freerouting + SES import -> DRC 0/0 ->
# BOM / manufacturing outputs / DFM / previews.
set -euo pipefail
source /data/Documents/tools/kicad/bin/env.sh
export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
export MPLCONFIGDIR=/data/Documents/projects/SmartCoaster/.tools/mplconfig
mkdir -p "$MPLCONFIGDIR"
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

echo "== route 2-layer =="
bash ./route_2l.sh

echo "== outputs =="
$PY gen_bom.py | tail -1
kicad-cli sch export pdf -o ../build/sch.pdf ../smartcoaster/smartcoaster.kicad_sch >/dev/null 2>&1 || true
pdftoppm -png -r 110 ../build/sch.pdf ../build/sch 2>/dev/null || true
$PY render_pcb.py | tail -1

echo "== manufacturing outputs =="
rm -rf ../build/gerbers
mkdir -p ../build/gerbers
kicad-cli pcb export gerbers \
    --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --output ../build/gerbers/ ../smartcoaster/smartcoaster_2l.kicad_pcb >/dev/null 2>&1
kicad-cli pcb export drill --format excellon --drill-origin absolute --generate-map \
    --map-format gerberx2 --output ../build/gerbers/ \
    ../smartcoaster/smartcoaster_2l.kicad_pcb >/dev/null 2>&1
kicad-cli pcb export pos --format csv --units mm --side both \
    --output ../build/gerbers/smartcoaster_2l.pos \
    ../smartcoaster/smartcoaster_2l.kicad_pcb >/dev/null 2>&1
( cd ../build/gerbers && rm -f ../smartcoaster_2l_gerbers.zip && zip -q -r ../smartcoaster_2l_gerbers.zip . )
kicad-cli pcb export pdf --mode-single \
    --layers F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,Edge.Cuts \
    --output ../build/pcb_2l.pdf ../smartcoaster/smartcoaster_2l.kicad_pcb >/dev/null 2>&1
$PY render_routed.py | tail -1
/usr/bin/python3 dfm_check.py | head -1
echo done
