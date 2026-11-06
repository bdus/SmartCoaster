#!/usr/bin/env bash
# Appearance shell CAD - one command, idempotent rebuild of every artifact.
#
#   appearance/cad/run_shell.sh [--skip-blender]
#
# Writes appearance/build/shell/{square,round}/plate_recessed.{step,stl},
# optional round clean variant, print blanks, shell.json, parts.json, REPORT.md.
# mechanical/** is read-only: the validated plate STEPs are imported and cut,
# never rebuilt.  System python3 has no build123d; the square_v1 venv is used.
set -euo pipefail

REPO="/data/Documents/projects/SmartCoaster"
PY="/data/Documents/projects/SmartCoaster/mechanical/square_v1/.venv/bin/python"

cd "$REPO"

if [[ ! -x "$PY" ]]; then
  echo "run_shell.sh: build123d interpreter not found/executable: $PY" >&2
  exit 1
fi

mkdir -p appearance/build/shell

echo "[run_shell] repo:   $REPO"
echo "[run_shell] python: $PY"
"$PY" -c 'import sys, build123d; print("[run_shell] ver:   python", sys.version.split()[0], "| build123d", build123d.__version__)'

"$PY" appearance/cad/build_recessed.py "$@"
