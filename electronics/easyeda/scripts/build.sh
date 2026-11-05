#!/usr/bin/env bash
# SmartCoaster EasyEDA re-implementation — one-command reproducible build.
# Inputs : frozen KiCad 9 design (read-only)
# Outputs: design/design.json, smartcoaster_easyeda/*.eprj3 (offline eprj3), reports/*, render/*
# Tools  : /data/Documents/tools/easyeda-eprj3-skill (official, v2.2.1)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SKILL=/data/Documents/tools/easyeda-eprj3-skill
PROJ="$HERE/smartcoaster_easyeda"
mkdir -p "$HERE/reports" "$HERE/inputs" "$HERE/render"

export XDG_CONFIG_HOME="$ROOT/.tools/kicad-config"
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
mkdir -p "$XDG_CONFIG_HOME"

echo '== 1/9 extract canonical electrical+mechanical data from KiCad (read-only)'
python3 "$HERE/scripts/extract_kicad.py"

echo '== 2/9 generate eprj3 design.json'
python3 "$HERE/scripts/gen_design.py"

echo '== 3/9 build offline .eprj3 project (schematic + placement + 5 gates)'
node "$SKILL/scripts/build.js" --design "$HERE/design/design.json" --dir "$PROJ" \
  --force --report "$HERE/reports/build.json" 2>&1 | tee "$HERE/reports/build.log"

echo '== 4/9 patch mechanical board outline (C-ring) + NPTH mounting holes'
python3 "$HERE/scripts/patch_board.py"

echo '== 5/9 validate + placement DRC after the mechanical patch'
node "$SKILL/scripts/validate.js" --dir "$PROJ" 2>&1 | tee "$HERE/reports/validate.log"
node "$SKILL/scripts/drc.js" --dir "$PROJ" 2>&1 | tee "$HERE/reports/drc.log"

echo '== 6/9 netlist parity vs the frozen KiCad netlist'
node "$SKILL/scripts/netlist.js" --dir "$PROJ" --json > "$HERE/inputs/built_netlist.json"
python3 "$HERE/scripts/check_parity.py" 2>&1 | tee "$HERE/reports/parity.log"

echo '== 7/9 independent netlist audit package (hand to a fresh reviewer)'
node "$SKILL/scripts/netlist.js" --dir "$PROJ" --design "$HERE/design/design.json" \
  --audit "$PROJ/.tmp/netlist-audit.json" 2>&1 | tee "$HERE/reports/netlist_audit_package.log"
cp "$PROJ/.tmp/netlist-audit.json" "$HERE/reports/netlist-audit.json"
rm -rf "$PROJ/.tmp"

echo '== 8/9 human-readable project report + provenance note'
node "$SKILL/scripts/report.js" --dir "$PROJ" --design "$HERE/design/design.json" \
  --report "$HERE/reports/build.json" --out "$PROJ/project-report.md"
python3 "$HERE/scripts/annotate_report.py"

echo '== 9/9 offline PCB placement render'
python3 "$HERE/scripts/render_pcb.py"

echo "DONE → $PROJ"
