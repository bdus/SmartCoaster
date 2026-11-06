# appearance/render — RENDER_LOG

> Real-shell + embedded Kromacut multi-material print, round (LUMEN + dog) and square
> (square_v1 + elf), plus Bambu-Studio-ready assembled 3MF.
> Machine: 36-core CPU / 62 GB. Blender **4.5.3 LTS** (`/data/Documents/tools/blender/blender`),
> headless `blender -b --python …`. Cycles CPU, AgX, denoise (OpenImageDenoise), 3-point
> studio reused from `render/square_b`.
>
> Date: 2026-11-06. All numbers below are from the final run.

## One-command reproduction

```bash
cd /data/Documents/projects/SmartCoaster

# everything (~3.5 min renders + ~1.3 min 3MF + ~15 s compositing)
bash appearance/render/run_all.sh

# or step by step (what run_all.sh does)
/data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py   # both versions
python3 appearance/render/make_3mf.py                                               # 3MF + validator
python3 appearance/render/postprocess.py                                            # macro caption, section composition, board

# fast preview / single view
SC_SAMPLES=16 SC_RENDER_ONLY=hero /data/Documents/tools/blender/blender -b \
    --python appearance/render/build_scene.py -- --version round
```

Inputs (read-only, owned by other agents): `appearance/build/shell/shell.json` + `parts.json` +
`{round,square}/plate_recessed.stl`; `appearance/build/print/{dog,elf}/filament_*.stl` +
`manifest.json`; `render/appearance/styles.json`; `render/square_b/ui_screen.png`.
Outputs: `appearance/render/**`, `appearance/build/render/**` (raw), `appearance/build/3mf/**`.

## Assembly / scene

* **Shell and print stay separate objects in separate collections** — no join, no boolean:
  * `SHELL_ROUND`: `battery, esp32, glass, hx711, oled, pad, pcb, sensor, shell, usbc, plate`
  * `PRINT_ART_DOG`: `ART_DOG_00…05` (one object per physical filament)
  * `SHELL_SQUARE`: same 10 + `button` + `plate` + `screen_ui`
  * `PRINT_ART_ELF`: `ART_ELF_00…06`
  * `STUDIO`: ground, 3 area lights, 4 cameras.
* Plate = **faithful `plate_recessed.stl`** from `shell.json` (not the `_clean` variant); assembly
  part list comes from `appearance/build/shell/parts.json` (LUMEN: 10 non-legacy parts; no
  `button_v01.stl` exists for LUMEN; `guide_v01`/`ledflex_v01` excluded as legacy per docs/13).
* Print placed as a **group**: bottom z = pocket floor (round **15.75**, square **16.55**),
  XY centred at 0,0, **no rotation** (image TOP = +Y, so the art reads upright for a user
  facing the front −Y). All filament STLs share the same z=0 datum, so one group translation
  is applied (a per-filament shift would shear the layers).
* Print envelope measured from geometry: Ø86.4 × 1.20 mm (round) / × 1.40 mm (square),
  group bbox `[-43.2,-43.2,floor] … [43.2,43.2,floor+t]`; print top **0.05 mm below the rim**.
  Max vertex radius **43.288 mm** vs pocket radius **43.000 mm** → **0.288 mm max radial
  interference** (0.200 nominal + 0.088 mm pixel-staircase corners). Reported/annotated, not "fixed".
* CMF: **lumen_violet for both versions** (shell `#2A2E35`, plate/button `#6B40A0` from
  `render/appearance/styles.json`); other parts neutral from `config_base.json`; glass neutral
  dark; screen content = `render/square_b/ui_screen.png` emission plane for the **square** only.
  Print colours come 1:1 from the Kromacut manifest (sRGB hex → linear per spec).
* `scene.blend` is the assembled uncut scene (per version). `scene_section.blend` is a **render-only
  copy** clipped to a 1/4 section for `section_exploded.png` — the assembled .blend is never cut.

## Renders (Cycles CPU, AgX, denoise)

| view | resolution | samples | round | square | notes |
|---|---|---|---|---|---|
| `hero.png` | 1000×1000 | 48 | 10.87 s | 11.43 s | 3/4 top, print flush in the recess |
| `top.png` | 1000×1000 | 48 | 12.38 s | 13.22 s | orthographic top |
| `macro_edge.png` | 1600×1600 | 64 | 40.71 s | 39.37 s | print rim seated in pocket; 170 mm lens, 46° elevation, 15 mm frame; caption drawn by postprocess |
| `print_top.png` | 1000×1000 | 48 | 8.80 s | 8.68 s | clean print-only ortho top (shell/plate/ground hidden) |
| `section_exploded.png` | 2400×1200 composed | 48 + 24 | 9.51 + 3.92 s | 10.50 + 4.05 s | raw = 1/4 clipped seated section (1600×1200) + exploded plate+print panel (1200×1000, 24 samples), composited |
| **total render calls** | — | — | **86.2 s** | **87.2 s** | wall clock for both versions (incl. 280 MB .blend + 40–52 MB section .blend saves): **3 min 19 s** |

Compositing (`postprocess.py`, PIL): macro caption, 5-label 1/4-section + exploded panel + text-only
fit summary, and `board.png` (2276×2406: heroes top row, macro crops bottom row, labels).

Final delivered files (appearance/render/):

```
round/{hero,top,macro_edge,print_top,section_exploded}.png   + scene.blend, scene_section.blend,
square/{hero,top,macro_edge,print_top,section_exploded}.png       scene_info.json, annotations.json
board.png
round/hero.png            1000×1000  0.87 MB
round/top.png             1000×1000  0.94 MB
round/macro_edge.png      1600×1600  1.46 MB
round/print_top.png       1000×1000  0.92 MB
round/section_exploded.png 2400×1200 1.63 MB
square/hero.png           1000×1000  0.90 MB
square/top.png            1000×1000  0.95 MB
square/macro_edge.png     1600×1600  1.48 MB
square/print_top.png      1000×1000  0.97 MB
square/section_exploded.png 2400×1200 1.58 MB
board.png                 2276×2406  3.16 MB
```

Raw render inputs kept for re-compositing: `appearance/build/render/{round,square}/
{macro_edge,section_seated,section_exploded}.png`.

## Bambu 3MF (appearance/build/3mf)

Built with `python3 appearance/render/make_3mf.py` (3MF core-spec zip: `[Content_Types].xml`,
`_rels/.rels`, `3D/3dmodel.model` with `basematerials`, one object per shell part, and the print
grouped as **one assembly object `PRINT_ART_<dog|elf>` with one `<component>` per physical
filament**; shell parts are their own build items).

```
round.3mf   15.9 MB  objects 18 = 11 shell-assembly + 1 print assembly + 6 filament components
                     build items 12 | triangles 1,982,994 = 41,262 shell/plate + 1,941,732 print
                     bbox 110.0 × 110.0 × 17.0 mm
                     PRINT_ART_dog transform z=15.75; print components 1,236,024 / 324,776 /
                     145,340 / 113,796 / 62,748 / 59,048 tris (= STL); colours #FBF4E8 #CBE0F5
                     #9FB2DA #F9CD72 #F09FAF #6C574C; world z 15.75…16.95
square.3mf  20.8 MB  objects 20 = 12 shell-assembly + 1 print assembly + 7 filament components
                     build items 13 | triangles 2,545,626 = 45,086 shell/plate + 2,500,540 print
                     bbox 100.0 × 100.0 × 18.0 mm
                     PRINT_ART_elf transform z=16.55; print components 1,574,104 / 311,920 /
                     232,036 / 146,216 / 99,704 / 72,264 / 64,296 tris (= STL); colours
                     #EDE1F0 #D9CFE6 #C3AEDC #F7D2C0 #E8A9B8 #C9A45B #5B4A72; z 16.55…17.95
dog_kromacut.3mf / elf_kromacut.3mf  reference copies of the print-only Kromacut exports
validation.json                      read-back validation of both assembled files
```

> **No triangle de-duplication.** Coincident opposite-winding interface caps between
> abutting Kromacut layout parts of the same filament (e.g. backing-class-1 top cap +Z vs
> face-class-1 bottom cap −Z at z = layer boundary) are *intentional* and keep each
> per-filament solid closed. The 3MF writer welds vertices only; every print component's
> triangle count equals the source STL count exactly, and validation asserts it.

Validator (`make_3mf.py`, all checks pass, `errors: []`, `ok: true`, 62.6 s total): zip members +
XML parse; `unit=millimeter`; `[Content_Types].xml` model default; `_rels/.rels` target; exactly one
print assembly whose component count equals the filament count (6 / 7); **every filament object's
`pid`/`pindex` points at a distinct `basematerial` whose displaycolour equals the manifest hex**
(case-insensitive); **every print component's triangle count equals its STL triangle count**
(no coincident-interface de-duplication) and the print total equals the manifest total
(1,941,732 dog / 2,500,540 elf); **every filament's world-Z range lies inside
`[floor, floor+t]`**; whole-build
bbox ≈ 110×110×17 / 100×100×18; interference = max_radius − pocket_radius = 0.288 mm;
print top vs rim = −0.05 mm. Full details in `appearance/build/3mf/validation.json` and README.

Not emitted: Bambu-proprietary `Metadata/model_settings.config` — assign each print component to an
AMS slot in Bambu Studio (colours match the Kromacut palette, so "use current filament colours"
usually maps 1:1). The Kromacut reference 3MFs already carry Bambu metadata.

## Mismatches / issues found and how they were resolved

1. **Round part list vs task text**: the spec listed a `button` for round, but LUMEN has **no
   `button_v01.stl`** and `parts.json` lists 10 non-legacy parts (battery, esp32, glass, hx711,
   oled, pad, pcb, sensor, shell, usbc). Used `parts.json` as authoritative → 11 shell objects
   (= 10 + recessed plate) in the round `.blend`/3MF. Not silently added.
2. **Square floor / pocket depth**: task-3's early text said floor 16.75 / depth 1.25 (dog thickness);
   the final `shell.json` + Lead confirm **floor 16.55 / depth 1.45** for the 1.40 mm elf print.
   `shell.json` matches the manifest thickness → no mismatch in the delivered files.
3. **Interference**: nominal 0.200 mm radial, but the measured max vertex radius is 43.288 mm →
   **0.288 mm max** (pixel-staircase corners). Annotated in macro + section, not "corrected".
4. **Kromacut "duplicate" triangles are intentional interface caps**: the coincident
   opposite-winding triangles between abutting layout parts of the same filament (multiplicity
   exactly 2) keep each filament solid closed. The delivered 3MF **keeps every STL triangle**
   (dog 1,941,732 / elf 2,500,540 print triangles; per-component counts asserted equal to the
   manifest). Only Blender's own STL importer removes them for the render mesh (display only —
   the rendered PNGs are unaffected and the 3MF is not).
5. **`render/square_b` material helper signature** is `(name, base, metallic, rough)` while this
   pipeline uses `(name, base, rough, metallic)`; the inherited ground call accidentally produced a
   near-mirror ground (hard bright reflection). Ground is now matte dielectric (rough 0.85,
   metallic 0), matching the square_b look without the artefact.

## PROVISIONAL / not verified here

* **No slicer/print test**: Bambu Studio is not installed in this environment; the 3MF is validated
  structurally (core-spec XML, counts, bboxes, colours, fit transforms), not sliced or printed.
* Fusion of print ↔ recessed plate is **nominal** (0.200 mm interference, 0.288 mm max); real FDM
  tolerance/fit and the strength of the fused interface are untested.
* Recessed plate stiffness/stress is shell-cad's PROVISIONAL note (recess is an appearance
  adaptation, no FEA re-run) — not re-validated here.
* 3MF contains the full shell assembly for context; the purchased/mechanical internals
  (pcb, sensor, esp32, hx711, usbc, battery, oled, glass, pad) are **reference geometry**, not
  printed parts. Actual print candidates are shell, plate, button (square only) and the print.
* `macro_edge.png` is an illustrative render, not metrology. Small 0.05 mm steps are below
  pixel resolution at hero scale; the numbers come from `shell.json` + measured geometry.
* LUMEN round shell is legacy concept geometry (no button, old 0.49" screen cut-out) used as the
  round shape/CMF carrier per the task; it is not the frozen square_v1 functional core.
* Section/exploded view is a **render-only** clipped copy (`scene_section.blend`); the delivered
  assembled `scene.blend` and the 3MF are uncut.
