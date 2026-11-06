# Kromacut headless Flat Paint bridge (appearance/kromacut)

Turns a **Kromacut v4.2.0 Flat Paint art asset** (`art.json` + `layer_counts.bin`)
into print files **without opening the desktop application**:

- a **multi-material 3MF** produced by Kromacut's own 3MF exporter (one object per
  physical filament, Bambu Studio / OrcaSlicer / Creality Print metadata included),
- **one binary STL per filament** (`filament_<n>_<HEX>.stl`) for Blender/assembly
  work, XY-recentred to `(0, 0)` with the print bottom at `z = 0`,
- `manifest.json` with palette, bbox, per-object/per-filament triangle counts,
  sha256 of every output, timings, and the result of self-verification checks.

The conversion is one command per art and idempotent. The Kromacut desktop app
is **not** GUI-automated: Kromacut's own TypeScript core modules *are* the
integration surface, loaded headlessly exactly the way Kromacut's tests load
them (`tests/helpers/viteModule.ts`: Vite dev server in middleware/SSR mode).

```
project root (SmartCoaster)
├── appearance/kromacut/                 ← this project wrapper
│   ├── run_convert.sh                   ← one command for both plates
│   └── README.md                        ← this file
├── appearance/build/art/{dog,elf}/      ← input art (owned by art step)
├── appearance/build/print/{dog,elf}/    ← output 3MF + STL + manifest.json
└── /data/Documents/tools/Kromacut/      ← installed tool (not modified)
    ├── app/ bin/                        ← desktop AppImage (not used by this bridge)
    ├── src/Kromacut-4.2.0/              ← v4.2.0 source tag (loaded read-only)
    ├── node_modules/                    ← three 0.180.0, jszip 3.10.1, vite 7.1.2
    └── tools/kromacut-flatpaint.mjs     ← generic CLI (deliverable)
```

## 1. Install / version facts

| Component | Version | Location |
|---|---|---|
| Kromacut (desktop AppImage, extracted) | 4.2.0 | `/data/Documents/tools/Kromacut/app`, launcher `bin/kromacut` (also `~/.local/bin/kromacut`) |
| Kromacut source tag used by the bridge | v4.2.0 (sha256 of tarball `74ae596f…df126a`) | `/data/Documents/tools/Kromacut/src/Kromacut-4.2.0` |
| Node.js | v24.15.0 | `/usr/bin/node` |
| three | 0.180.0 | `/data/Documents/tools/Kromacut/node_modules/three` |
| jszip | 3.10.1 | `/data/Documents/tools/Kromacut/node_modules/jszip` |
| vite | 7.1.2 | `/data/Documents/tools/Kromacut/node_modules/vite` |

Installation was performed by `appearance/tools/install_kromacut.sh` (downloads the
official AppImage + the v4.2.0 source tag, extracts the AppImage without FUSE, and
`npm install`s the three bridge dependencies under the tool root). The install log
is `/data/Documents/tools/Kromacut/logs/install.log`.

The desktop GUI is **not required** for this bridge, but it *does* run on this
machine when a display is available: under `Xvfb :99` with `DISPLAY=:99
app/AppRun` the app stayed alive for 10+ s and produced a real window (screenshot
`/data/Documents/tools/Kromacut/logs/gui_offscreen.png`; recorded in
`/data/Documents/tools/KROMACUT_INSTALL_NOTES.md`). Normal desktop launch is the
`kromacut` launcher; only launching `app/usr/bin/kromacut` directly panics on
`gtk::rt::init` because it misses AppRun's bundled library environment. This
bridge uses only the source modules, never the GUI. Quick environment check:

```bash
node --version                                        # v24.15.0
node -e "console.log(require('/data/Documents/tools/Kromacut/node_modules/three/package.json').version)"
test -f /data/Documents/tools/Kromacut/src/Kromacut-4.2.0/src/lib/flatPaint.ts && echo source-ok
ls /data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs
```

## 2. Usage

### Project (this pipeline)

```bash
# from the project root: convert both plates (dog = 6 filaments/1.20 mm,
# elf = 7 filaments/1.40 mm) into appearance/build/print/{dog,elf}/
appearance/kromacut/run_convert.sh

# optional smooth-meshing variant (slower; recorded in the manifest)
SMOOTH=medium appearance/kromacut/run_convert.sh

# optional determinism check: convert each art twice and compare geometry,
# per-filament bboxes and STL sha256 (3MF sha256 legitimately differs: Kromacut
# 3MF embeds random p:UUIDs and zip timestamps)
DETERMINISM=1 appearance/kromacut/run_convert.sh
```

`run_convert.sh` env overrides: `ART_DIR`, `OUT_DIR`, `SMOOTH`, `NODE`,
`KROMACUT_FLATPAINT`.

### Generic CLI (any Flat Paint art)

```bash
node /data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs \
    --art <art-dir-or-art.json> --out <out-dir> \
    [--smooth none|minimal|medium|aggressive] [--name <slug>] \
    [--orientation face-up|face-down] [--source <kromacut-src-dir>] \
    [--require-full-palette] [--quiet]
```

`--help` prints the full reference. Exit codes: `0` exported + all self-checks
passed, `1` error or failed check, `2` bad usage.

### Input format

`--art DIR` reads `DIR/art.json` and `DIR/layer_counts.bin` (or pass the
`art.json` path directly; the binary must sit next to it).

`art.json` fields used (both spellings accepted for the aliases):

| Field | Required | Meaning |
|---|---|---|
| `width`, `height` | yes | pixel grid size; must match the bin length |
| `pixel_size_mm` | yes | pixel pitch in mm (SmartCoaster: 0.15) |
| `layer_height_mm` | yes | one physical image layer (SmartCoaster: 0.2) |
| `palette` / `palette_bottom_up` | yes | hex colours, **bottom-up**, one per image layer; index 0 = foundation layer |
| `first_layer_thickness_mm` / `first_layer_mm` | no | default = `layer_height_mm` (SmartCoaster: 0.2) |
| `orientation` | no | `face-up` (default in the CLI) or `face-down` |
| `layer_count` | no | if present must equal `palette.length` |
| `name` | no | default output slug (else `--name`, else art dir name) |
| `art_diameter_mm` | no | informational only, copied to the manifest |

`layer_counts.bin`: **uint16 little-endian**, row-major, `y = 0` is the image
**top** row, value = palette index + 1, `0` = transparent, length =
`width * height`. This is Kromacut's Flat Paint layer-count grid.

### Outputs

For `--out appearance/build/print/dog --name dog --smooth none`:

```
appearance/build/print/dog/
├── dog_kromacut.3mf             multi-material 3MF, native Kromacut coordinates
│                                (x/y = 0…art width/depth, z = 0…thickness)
├── filament_1_FBF4E8.stl        one closed-shell binary STL per filament,
├── filament_2_CBE0F5.stl        XY bbox centred on (0,0), print bottom at z=0,
├── …                            header "Kromacut Binary STL"
├── filament_6_6C574C.stl
└── manifest.json
```

`n` is the 1-based filament index in the **same order as the 3MF base materials /
slicer extruders** (1 → `extruder 1`, …), so slicer material assignment and the
STL file names line up. `manifest.json` records: tool/source versions and module
sha256, art schema + input sha256, layout parts, per-filament STL triangle counts
and bboxes + sha256, 3MF per-object triangle/vertex counts and native bbox,
placement offset, timings, and every self-verification check.

## 3. How the bridge uses Kromacut (exact functions)

Modules are loaded with Vite SSR (`createServer({root: <source dir>,
appType:'custom', configFile:false, logLevel:'error', cacheDir: <tmp>,
optimizeDeps:{noDiscovery:true}, server:{middlewareMode:true, hmr:false,
watch:null}})`, then `server.ssrLoadModule('/src/lib/…')`). This is needed because
the Kromacut sources are TypeScript with extensionless imports; it is exactly how
`tests/helpers/viteModule.ts` loads them. `three` and `jszip` resolve through
Node from the tool root and are shared with the SSR module graph.

Pipeline for one art:

1. `orientFlatPaintLayerCounts(counts, width, height, orientation)` — scene Y is
   flipped (and X for face-down); face-up keeps the art's X.
2. `buildFlatPaintLayout({layerCounts, width, height, layerCount: palette.length,
   layerHeight, carrierThickness: layerHeight, orientation, firstLayerThickness,
   layerVirtualHexes: palette, layerFilamentHexes: palette})` — returns the solid
   slabs (`face`, `zone`, `backing`; no carrier in face-up) and `totalHeight`.
   Face-up semantics: each column keeps its normal bottom-up stack, the visible
   top layer is `palette[k-1]` for a `k`-layer column, and shorter columns are
   backfilled with the foundation `palette[0]` below, so the top surface is flat.
3. `createFlatPaintMesher(orientedCounts, width, height, pixelSize, strength,
   {yieldIntervalMs: Infinity, onYield})` — one shared XY tessellation, then one
   closed mesh per layout part. The mesher emits normalized `z ∈ [0,1]`; the
   bridge remaps `z = baseZ + z * (topZ - baseZ)` per part.
4. Each part's `THREE.BufferGeometry` is tagged exactly like Kromacut's own test
   fixture (`buildFixturePartMeshes` in `tests/flatPaint.test.ts`):
   `geometry.userData.kromacutExportGeometry = {positions, indices, activePixels,
   width, height, pixelSize, topZ, compactHeightfield: false}` and the mesh
   `userData.kromacutExportGroup / kromacutFilamentHex / kromacutMaterialKey /
   kromacutPartName`. Because all parts of one physical filament share the same
   `kromacutExportGroup`, the exporter merges them into **one object per
   filament**.
5. `exportObjectTo3MFBlob(root, {layerHeight, firstLayerHeight,
   smoothMeshingStrength, layerFilamentColors: palette})` — Kromacut 3MF
   (model + Bambu/Orca `model_settings.config` + `project_settings.config` +
   `kromacut.config`), DEFLATE compression.
6. Per filament: the meshes of that export group are moved into a temporary
   `THREE.Group` translated by `(-bboxCenterX, -bboxCenterY, -minZ)` and written
   with `exportObjectToStlBlob(group)` → binary STL with empty shells not merged
   across filaments.

`appearance/build/print/*/manifest.json` records the sha256 of the loaded
Kromacut source modules so the exact engine revision is auditable.

## 4. Verification performed by the CLI

Every run re-reads its own outputs and fails (exit 1) if a check does not hold:

- `art` bin size/values vs `width*height` and palette length; declared
  `layer_count` vs palette length; non-empty opaque area; full palette usage
  (`--require-full-palette`).
- 3MF unzips; required entries present; `3D/3dmodel.model` and
  `Metadata/model_settings.config` are well-formed XML (own tag-balance parser);
  `project_settings.config` parses as JSON.
- exactly **one 3MF mesh object per filament group** (+ the assembly object),
  every object has triangles and no zero-area triangles, object names/material
  indices/extruders/base materials all map 1:1 to the palette groups.
- 3MF triangle and vertex totals equal the source meshes (nothing dropped);
  per-object counts equal the per-filament source counts.
- 3MF bbox equals the opaque pixel footprint × pixel size; z = 0…`totalHeight`;
  `totalHeight` = `firstLayerThickness + (usedLayers-1)*layerHeight`.
- one STL per export group, Kromacut STL header, triangle count = source mesh
  triangle count, per-file bbox = source mesh bbox translated to XY-centred/z=0,
  union bbox = centred footprint × thickness, zero-area triangle count reported.
- **mesh integrity of every filament object (no size cutoff)**: exact float32
  vertex welding + edge-incidence histogram. Every edge must have even incidence
  (0 boundary edges) — 2 = ordinary manifold edge, 4 = edge between two abutting
  parts, 6 = edge where three parts meet. It also counts **coincident interface
  caps** (same 3 vertices, opposite winding) between vertically abutting parts of
  the *same* filament: these are intentional (closed per-material solids, slicer
  resolves internal interfaces), NOT duplicate/degenerate geometry, and are
  reported in `manifest.coincidentInterfaceFaces` / `manifest.meshIntegrity`.
- path transparency: the exported 3MF embeds `Kromacut:SmoothMeshingStrength`
  and slicer layer heights equal the requested values.

## 5. Determinism

- **STL files are byte-identical across runs** (no timestamps in the header);
  `DETERMINISM=1 ./run_convert.sh` checks the sha256 of every STL plus all
  geometry counts and bboxes.
- **3MF files are not byte-identical across runs** by design of Kromacut's
  exporter: every object/build node gets a random `p:UUID` and JSZip stamps the
  archive with the current time. Geometry, object count, names, materials,
  triangle/vertex counts and bbox are identical (the determinism check compares
  those numbers, not the 3MF bytes).
- `manifest.json` contains timings and a `generatedAt` timestamp, so it is not
  byte-identical either; everything geometric in it is.

## 6. Limitations / what is NOT verified

- **No slicer and no physical print test.** Files were not imported into Bambu
  Studio/OrcaSlicer and no print was run; printability (AMS/tool-change waste
  towers, adhesion, colour mixing, layer bonding) is untested. The 3MF is
  Kromacut's own Bambu/Orca-compatible output but importing it is unverified.
- **No colour management**: palette hex values are passed through as sRGB hex;
  no ICC conversion, no measured filament spectra. Rendered/printed colours will
  differ from the artwork.
- **Face-up only in this pipeline**: `orientation` is honoured by the CLI and
  the face-down carrier code path exists in Kromacut, but only face-up is
  exercised here (no transparent carrier object).
- **Per-filament objects are unions of closed solids, not one manifold.** Adjacent
  parts of the same filament abut, producing coincident *opposite-winding* cap
  pairs (dog foundation: 261 777; elf foundation: 325 697; measured, in the
  manifest). Do NOT dedupe/weld them away: each part stays a closed solid and
  slicers ignore internal interfaces; removing one of each pair makes the object
  non-watertight. Max edge incidence is 6 (three-part junction), so a simple
  "every edge exactly 2" watertight test is the wrong criterion for these files.
- **Smooth meshing**: `minimal|medium|aggressive` are supported, but smoothed
  caps can emit a handful of sub-micron zero-area triangles in binary STL
  (float32 precision; slicers skip them). The exported SmartCoaster choice is
  `none`, which has zero. See `appearance/build/print/REPORT.md` for a timed
  `medium` comparison.
- **Model size**: 576×576 Flat Paint meshes are triangle-heavy by construction
  (Kromacut's greedy rectangle caps; see REPORT). Each plate produces a few
  million triangles / a few hundred MB of STL. That is Kromacut's geometry, not
  decimation — do not decimate if the 3MF/STL must match the slicer preview.
  A multi-material print additionally needs an AMS/toolchanger (6 or 7
  filaments); a 4-slot AMS needs a swap or a second AMS.
- **The art itself is out of scope**: quantisation, palette choice and the
  `layer_counts.bin` generation live in `appearance/tools/make_art.py`
  (`appearance/build/art/REPORT.md`). The bridge converts; it does not recolour
  or repair art.
- **Kromacut version pinned**: the bridge targets the v4.2.0 source tag. A
  Kromacut upgrade must re-verify `flatPaint.ts` / `flatPaintMeshing.ts` /
  `export3mf.ts` / `exportStl.ts` APIs (the manifest records their sha256).
- The printed geometry is the Flat Paint slab only — **not** the coaster shell,
  the recess fit, or the assembled part (those are `appearance/cad` and
  `appearance/render`).
