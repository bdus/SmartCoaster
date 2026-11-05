#!/usr/bin/env bash
# Live EasyEDA Pro checks (requires an installed, *logged-in / activated* desktop client).
# Currently BLOCKED on this host: the client stops at the Regist window and pro.lceda.cn is
# CloudWAF-418 blocked for this IP, so open/sch-drc/pcb sessions never get a command space.
# See /data/Documents/tools/EASYEDA_INSTALL_NOTES.md §4.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SKILL=/data/Documents/tools/easyeda-eprj3-skill
PROJ="$HERE/smartcoaster_easyeda"
BIN=/data/Documents/tools/easyeda-pro/lceda-pro/lceda-pro
TOOLS=/data/Documents/tools

export HOME=/home/pi
export LCEDA_PRO_CLI="$BIN"
export DISPLAY=:99
if ! xdpyinfo >/dev/null 2>&1; then
  "$ROOT/.tools/xvfb/usr/bin/Xvfb" :99 -screen 0 1600x1200x24 -nolisten tcp >/tmp/xvfb-eda.log 2>&1 &
  sleep 2
fi
if ! "$BIN" doctor 2>/dev/null | grep -q '"connected":true'; then
  "$BIN" --owner >/tmp/lceda-owner.log 2>&1 &
  sleep 8
fi
echo '== client doctor'
node "$SKILL/scripts/eda.js" doctor || { echo '❌ client bridge not ready — see install notes §4 (login/activation)'; exit 2; }
echo '== schematic DRC (client native)'
node "$SKILL/scripts/eda.js" sch-drc --dir "$PROJ" 2>&1 | tee "$HERE/reports/client_sch_drc.log" || exit 3
echo '== netlist export (client native)'
node "$SKILL/scripts/eda.js" netlist --dir "$PROJ" --out "$HERE/inputs/client_netlist.json" 2>&1 | tee "$HERE/reports/client_netlist.log" || exit 4
echo '== screenshots'
mkdir -p "$HERE/render/client"
node "$SKILL/scripts/eda.js" screenshot --dir "$PROJ" --out "$HERE/render/client" 2>&1 | tee "$HERE/reports/client_screenshot.log" || exit 5
echo '== PCB auto-route (2-layer) + save'
node "$SKILL/scripts/eda.js" pcb --dir "$PROJ" --route 2>&1 | tee "$HERE/reports/client_route.log" || exit 6
echo '== PCB DRC after routing'
node "$SKILL/scripts/eda.js" screenshot --dir "$PROJ" --out "$HERE/render/client" --doc pcb 2>&1 | tee -a "$HERE/reports/client_screenshot.log"
echo 'DONE — copy the real numbers from reports/client_*.log into REPORT.md §6'
