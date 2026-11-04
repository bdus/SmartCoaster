#!/usr/bin/env bash
# One-command host verification for the firmware core (no hardware, no ESP-IDF).
#
#   1. CMake host build + CTest
#        - host_core_test : the 11 firmware/model scenarios ported to C
#        - host_mock_test : HX711 mock (noise/drift/saturation/quantisation)
#   2. differential      : C core vs Python model on identical traces
#   3. Python model      : reference baseline (11 passed)
#
# Usage:
#   tests/firmware/run_host_tests.sh
#   BUILD_DIR=/tmp/scoaster tests/firmware/run_host_tests.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PYTHON:-/data/Documents/tools/sim-venv/bin/python}"
PYTEST="${PYTEST:-/data/Documents/tools/sim-venv/bin/pytest}"
BUILD_DIR="${BUILD_DIR:-/tmp/smartcoaster-host-build}"
CMAKE="${CMAKE:-cmake}"

cd "${ROOT}"

echo "== [1/3] CMake host build + CTest (${BUILD_DIR}) =="
"${CMAKE}" -S tests/firmware -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=RelWithDebInfo >/dev/null
"${CMAKE}" --build "${BUILD_DIR}" -j >/dev/null
ctest --test-dir "${BUILD_DIR}" --output-on-failure

echo
echo "== [2/3] C vs Python differential =="
PYTHONPATH= "${PYTHON}" tests/firmware/differential.py

echo
echo "== [3/3] Python reference model =="
PYTHONPATH= "${PYTEST}" firmware/model -q
