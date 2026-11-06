#!/usr/bin/env bash
# SmartCoaster appearance/print pipeline — ONE command.
#
#   bash appearance/compile.sh                 # full pipeline + Lead acceptance
#   bash appearance/compile.sh --dry-run       # validate only, write nothing
#   bash appearance/compile.sh --list          # show stages/commands
#   bash appearance/compile.sh --only shell    # one stage
#   bash appearance/compile.sh --from render   # render -> print -> acceptance
#
# Inputs:  appearance/config/appearance_project.yaml  (single source of truth)
# Contract: appearance/INPUTS.md
# Agent prompt: appearance/AGENT_PROMPT.md
#
# This wrapper only forwards to appearance/tools/compile.py; it re-implements
# nothing. All timing/status/validation evidence lands in
# appearance/build/COMPILE_REPORT.{json,md} and appearance/build/compile.log.
set -euo pipefail

SELF=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$SELF/.." && pwd)
cd "$REPO"

exec python3 appearance/tools/compile.py "$@"
