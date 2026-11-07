#!/usr/bin/env bash
# Lumina-Layers appearance line - ONE command, idempotent.
#
#   bash appearance/compile.sh --dry-run     # validate config/tools/contract only (no writes)
#   bash appearance/compile.sh               # art -> lumina -> shell -> render -> 3mf ->
#                                            # postprocess -> print delivery -> acceptance
#                                            #   (~10-12 min, 36-core CPU)
#   bash appearance/compile.sh --only A2     # one stage (see appearance/tools/compile_lumina.py)
#   bash appearance/compile.sh --from A4     # resume from a stage
#
# Report: appearance/build/COMPILE_LUMINA_REPORT.{json,md}   Log: appearance/build/compile_lumina.log
# The previous Kromacut orchestrator (appearance/tools/compile.py) is OBSOLETE.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 appearance/tools/compile_lumina.py "$@"
