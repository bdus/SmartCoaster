#!/usr/bin/env bash
# KiCad <-> EasyEDA cross-tool validation at the data-contract level.
# Needs: KiCad 9 runtime, sim-venv (pcbnew), inputs/client_netlist.json exported
# from the live EasyEDA client (node <eprj3-skill>/scripts/eda.js netlist ...).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export XDG_CONFIG_HOME="$ROOT/.tools/kicad-config"
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
mkdir -p "$XDG_CONFIG_HOME"
exec /data/Documents/tools/sim-venv/bin/python "$HERE/scripts/check_cross_tool.py"
