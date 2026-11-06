#!/usr/bin/env bash
# SmartCoaster appearance pipeline — Kromacut Flat Paint conversion (headless).
#
# Converts both art plates produced by appearance/tools/make_art.py:
#   appearance/build/art/dog/  (6 filaments, 1.20 mm)  -> appearance/build/print/dog/
#   appearance/build/art/elf/  (7 filaments, 1.40 mm)  -> appearance/build/print/elf/
#
# One command, idempotent. Outputs per art:
#   <name>_kromacut.3mf      multi-material 3MF (Kromacut export, one object per filament)
#   filament_<n>_<HEX>.stl   one binary STL per filament (XY centred on 0,0, bottom z=0)
#   manifest.json            palette, bbox, triangle counts, sha256, timings, self-checks
#
# Usage:
#   appearance/kromacut/run_convert.sh
#   SMOOTH=medium appearance/kromacut/run_convert.sh     # smooth meshing variant
#   DETERMINISM=1 appearance/kromacut/run_convert.sh     # rerun each art and compare geometry
#
# Env overrides: ART_DIR, OUT_DIR, SMOOTH, NODE, KROMACUT_FLATPAINT.
set -euo pipefail

SELF=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SELF/../.." && pwd)

CLI=${KROMACUT_FLATPAINT:-/data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs}
ART_DIR=${ART_DIR:-$ROOT/appearance/build/art}
OUT_DIR=${OUT_DIR:-$ROOT/appearance/build/print}
SMOOTH=${SMOOTH:-none}
NODE=${NODE:-$(command -v node || true)}
DETERMINISM=${DETERMINISM:-0}

if [[ -z "$NODE" ]]; then
    echo "run_convert: node not found on PATH" >&2
    exit 1
fi
if [[ ! -f "$CLI" ]]; then
    echo "run_convert: Kromacut bridge CLI not found: $CLI" >&2
    echo "run_convert: expected from the Kromacut install step (appearance/tools/install_kromacut.sh)" >&2
    exit 1
fi

convert_one() {
    local name=$1
    local art="$ART_DIR/$name"
    local out="$OUT_DIR/$name"
    if [[ ! -f "$art/art.json" ]]; then
        echo "run_convert: missing $art/art.json — run: python3 appearance/tools/make_art.py" >&2
        exit 1
    fi
    echo "==> [$name] $art -> $out (smooth=$SMOOTH)"
    "$NODE" "$CLI" --art "$art" --out "$out" --smooth "$SMOOTH" --name "$name" \
        --require-full-palette
}

compare_runs() {
    local a=$1 b=$2 label=$3
    "$NODE" - "$a" "$b" "$label" <<'NODE_JS'
const fs = require('node:fs');
const [aDir, bDir, label] = process.argv.slice(2);
const read = (dir) => JSON.parse(fs.readFileSync(`${dir}/manifest.json`, 'utf8'));
const a = read(aDir);
const b = read(bDir);
const problems = [];
const same = (name, x, y) => {
    if (JSON.stringify(x) !== JSON.stringify(y)) problems.push(name);
};
same('layout.totalHeightMm', a.layout.totalHeightMm, b.layout.totalHeightMm);
same('layout.partCount', a.layout.partCount, b.layout.partCount);
same(
    'export.objects',
    a.export.objects.map((o) => [o.name, o.triangles, o.vertices, o.bboxNativeMm]),
    b.export.objects.map((o) => [o.name, o.triangles, o.vertices, o.bboxNativeMm])
);
same(
    'stls',
    a.stls.map((s) => [s.file, s.triangles, s.bboxMm, s.sha256]),
    b.stls.map((s) => [s.file, s.triangles, s.bboxMm, s.sha256])
);
if (a.export.threeMfSha256 === b.export.threeMfSha256) {
    problems.push('3mf.sha256 byte-identical (unexpected: 3MF embeds UUIDs)');
}
console.log(
    `${label}: ${problems.length === 0 ? 'PASS' : 'FAIL'} ` +
        `(objects=${b.export.objectCount}, triangles=${b.export.totalTriangles}, ` +
        `STL sha256 identical=${JSON.stringify(a.stls.map((s) => s.sha256)) === JSON.stringify(b.stls.map((s) => s.sha256))}, ` +
        `3mf sha differs=${a.export.threeMfSha256 !== b.export.threeMfSha256}` +
        `${problems.length ? '; mismatches: ' + problems.join(', ') : ''})`
);
process.exit(problems.length === 0 ? 0 : 1);
NODE_JS
}

mkdir -p "$OUT_DIR"
for name in dog elf; do
    convert_one "$name"
done

if [[ "$DETERMINISM" == "1" ]]; then
    echo "==> determinism check (rerun each art into a temp dir, compare geometry + STL bytes)"
    for name in dog elf; do
        tmp=$(mktemp -d "${TMPDIR:-/tmp}/kroma-determinism-${name}-XXXXXX")
        trap 'rm -rf "$tmp"' EXIT
        "$NODE" "$CLI" --art "$ART_DIR/$name" --out "$tmp" --smooth "$SMOOTH" \
            --name "$name" --require-full-palette --quiet
        compare_runs "$OUT_DIR/$name" "$tmp" "$name"
        rm -rf "$tmp"
        trap - EXIT
    done
fi

echo "==> done: $OUT_DIR/{dog,elf}"
