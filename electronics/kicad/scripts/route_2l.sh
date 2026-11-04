#!/usr/bin/env bash
# Route the 2-layer SmartCoaster board: generated board -> DSN -> Freerouting ->
# SES -> import back into KiCad -> widen/clean -> DRC report.
#
# Usage:  ./route_2l.sh            # export, route, import, clean, DRC
#         ./route_2l.sh --keep     # keep an existing .ses (import/clean/DRC only)
#
# Prereq: `gen_pcb.py` has produced an *unrouted* smartcoaster.kicad_pcb
# (build.sh does this).  Freerouting 2.5.0 needs a Java 25 runtime, which ships
# with the app image, but it still opens an AWT frame, so we run a throwaway
# Xvfb display.  NOTE: the DSH sandbox gives every bash call its own /tmp tmpfs,
# therefore Xvfb and Freerouting must run inside the *same* invocation.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
KDIR="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$KDIR/../.." && pwd)"
BUILD="$KDIR/build"
PY=/usr/bin/python3

export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
export XDG_CONFIG_HOME="$ROOT/.tools/kicad-config"
export MPLCONFIGDIR="$ROOT/.tools/mplconfig"
mkdir -p "$XDG_CONFIG_HOME" "$MPLCONFIGDIR" "$BUILD"

FR="$ROOT/.tools/freerouting/freerouting-2.5.0-linux-x64/bin/freerouting"
XVFB="$ROOT/.tools/xvfb/usr/bin/Xvfb"
FR_XDG_CONFIG="$ROOT/.tools/fr-home/config"
FR_XDG_STATE="$ROOT/.tools/fr-home/state"
FR_XDG_CACHE="$ROOT/.tools/fr-home/cache"

cd "$KDIR"

if [[ "${1:-}" != "--keep" ]]; then
  echo "== export DSN =="
  $PY scripts/route_2l.py export

  echo "== route (Freerouting 2.5.0) =="
  mkdir -p /tmp/.X11-unix
  "$XVFB" :99 -screen 0 1280x1024x24 -nolisten tcp >/dev/null 2>&1 &
  XVFB_PID=$!
  trap 'kill $XVFB_PID 2>/dev/null || true' EXIT
  sleep 3
  mkdir -p "$FR_XDG_CONFIG" "$FR_XDG_STATE/logs" "$FR_XDG_CACHE"
  DISPLAY=:99 XDG_CONFIG_HOME="$FR_XDG_CONFIG" \
      XDG_STATE_HOME="$FR_XDG_STATE" XDG_CACHE_HOME="$FR_XDG_CACHE" \
      "$FR" -de "$BUILD/smartcoaster_2l.dsn" -do "$BUILD/smartcoaster_2l.ses" \
            -mt 1 -mp 100 2>&1 \
      | tee "$BUILD/freerouting_2l.log" \
      | grep -E "Auto-routing stage completed|Optimization was completed|Saved .*session|Saving .*ses" || true
  kill $XVFB_PID 2>/dev/null || true
  trap - EXIT
fi

echo "== import SES =="
$PY scripts/route_2l.py import

echo "== clean + DRC =="
$PY scripts/route_2l.py clean
grep -E "^\*\* Found" "$BUILD/DRC_2l.rpt" || true
