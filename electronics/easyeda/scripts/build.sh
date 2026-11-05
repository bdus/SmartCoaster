#!/usr/bin/env bash
# SmartCoaster EasyEDA re-implementation — one-command reproducible build.
# Inputs : frozen KiCad 9 design (read-only)
# Outputs: design/design.json, smartcoaster_easyeda/*.eprj3 (schematic + PCB + copper), reports/*, render/*
# Tools  : /data/Documents/tools/easyeda-eprj3-skill (official, v2.2.1)
#          /data/Documents/tools/sim-venv (shapely 2.1.2 for the independent copper check)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SKILL=/data/Documents/tools/easyeda-eprj3-skill
PY=/data/Documents/tools/sim-venv/bin/python
PROJ="$HERE/smartcoaster_easyeda"
mkdir -p "$HERE/reports" "$HERE/inputs" "$HERE/render"

export EPRJ3_DETERMINISTIC=1   # byte-stable ids/timestamps for diffs
export XDG_CONFIG_HOME="$ROOT/.tools/kicad-config"
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
mkdir -p "$XDG_CONFIG_HOME"

echo '== 1/11 extract canonical electrical+mechanical data (incl. verified copper) from KiCad (read-only)'
$PY "$HERE/scripts/extract_kicad.py"

echo '== 2/11 generate eprj3 design.json'
$PY "$HERE/scripts/gen_design.py"

echo '== 3/11 build offline .eprj3 project (schematic + placement + 5 gates)'
node "$SKILL/scripts/build.js" --design "$HERE/design/design.json" --dir "$PROJ" \
  --force --report "$HERE/reports/build.json" 2>&1 | tee "$HERE/reports/build.log"

echo '== 4/11 patch mechanical board outline (C-ring), real pad shapes, NPTH mounting holes'
$PY "$HERE/scripts/patch_board.py"

echo '== 5/11 validate + PLACEMENT DRC (no copper yet; the skill DRC is used for placement only)'
node "$SKILL/scripts/validate.js" --dir "$PROJ" 2>&1 | tee "$HERE/reports/validate.log"
node "$SKILL/scripts/drc.js" --dir "$PROJ" 2>&1 | tee "$HERE/reports/drc_placement.log"

echo '== 6/11 port the verified KiCad 2-layer copper into the EasyEDA PCB (576 tracks / 62 vias)'
$PY "$HERE/scripts/port_copper.py"
node "$SKILL/scripts/validate.js" --dir "$PROJ" 2>&1 | tee "$HERE/reports/validate_routed.log"

echo '== 7/11 independent geometry-accurate copper review (shapely/GEOS; the skill DRC uses AABB and is not used for 45° traces)'
$PY "$HERE/scripts/check_copper.py" 2>&1 | tee "$HERE/reports/copper_check.log"

echo '== 8/11 netlist parity vs the frozen KiCad netlist'
node "$SKILL/scripts/netlist.js" --dir "$PROJ" --json > "$HERE/inputs/built_netlist.json"
$PY "$HERE/scripts/check_parity.py" 2>&1 | tee "$HERE/reports/parity.log"

echo '== 9/11 independent netlist audit package (hand to a fresh reviewer)'
node "$SKILL/scripts/netlist.js" --dir "$PROJ" --design "$HERE/design/design.json" \
  --audit "$PROJ/.tmp/netlist-audit.json" 2>&1 | tee "$HERE/reports/netlist_audit_package.log"
cp "$PROJ/.tmp/netlist-audit.json" "$HERE/reports/netlist-audit.json"
rm -rf "$PROJ/.tmp"

echo '== 10/11 human-readable project report + provenance note'
node "$SKILL/scripts/report.js" --dir "$PROJ" --design "$HERE/design/design.json" \
  --report "$HERE/reports/build.json" --out "$PROJ/project-report.md"
$PY "$HERE/scripts/annotate_report.py"

echo '== 11/11 routed PCB render'
$PY "$HERE/scripts/render_pcb.py"

echo "DONE → $PROJ"
