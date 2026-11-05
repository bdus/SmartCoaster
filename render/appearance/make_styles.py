#!/usr/bin/env python3
"""Style-board renderer for the FROZEN geometry.

One style = one entry in `styles.json`: per-part colour (sRGB hex), metallic and
roughness overrides. The script patches the *existing* square_b Blender scene
config, renders the requested views, restores everything, then composes a
labelled contact sheet.

Geometry is not touched: before rendering, every STL is hashed against
`frozen_geometry_square.sha256`. If a hash differs the script aborts, so an
"appearance only" round cannot silently ship a geometry change.

Run:
  # all styles in styles.json, hero + front
  python3 render/appearance/make_styles.py

  # fast single style, hero only
  python3 render/appearance/make_styles.py --only lumen_violet --views hero

  # parity check into a separate folder, no board
  python3 render/appearance/make_styles.py --only lumen_violet \
      --out render/appearance/proof --no-sheet

Outputs:
  render/appearance/styles/<id>/{hero,front}.png
  render/appearance/01_style_board.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

ROOT = "/data/Documents/projects/SmartCoaster"
APPEAR = f"{ROOT}/render/appearance"
SCENE = f"{ROOT}/render/square_b/build_scene.py"
BASE_CFG = f"{APPEAR}/config_base.json"
LIVE_CFG = f"{ROOT}/render/square_b/config.json"
SCENE_OUT = f"{ROOT}/render/square_b/renders"
FROZEN = f"{APPEAR}/frozen_geometry_square.sha256"
BLENDER = "/data/Documents/tools/blender/blender"

BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

BG = (17, 19, 24)
CARD = (26, 29, 36)
FG = (234, 238, 244)
MUT = (150, 158, 172)
DIM = (110, 118, 132)
ACC = (124, 108, 232)


def F(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def lin(h: str):
    """sRGB hex -> linear RGB (Blender base_color expects linear)."""
    c = [int(h.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def hexrgb(h: str):
    return tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


# --------------------------------------------------------------------------
# geometry freeze check
# --------------------------------------------------------------------------
def verify_geometry(manifest: str = FROZEN) -> None:
    bad = []
    n = 0
    for line in open(manifest):
        line = line.strip()
        if not line:
            continue
        want, rel = line.split(None, 1)
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            bad.append((rel, "missing"))
            continue
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        n += 1
        if h != want:
            bad.append((rel, "hash mismatch"))
    if bad:
        print("GEOMETRY CHANGED — refusing to render appearance:", file=sys.stderr)
        for rel, why in bad:
            print(f"  {why}: {rel}", file=sys.stderr)
        raise SystemExit(2)
    print(f"geometry frozen OK ({n} STL hashes match)")


# --------------------------------------------------------------------------
# style application / rendering
# --------------------------------------------------------------------------
def apply_style(cfg: dict, style: dict) -> None:
    for part, spec in style.get("parts", {}).items():
        if part not in cfg["colors"]:
            raise KeyError(f"{style['id']}: unknown part '{part}'")
        dst = cfg["colors"][part]
        if "hex" in spec:
            dst["base"] = lin(spec["hex"])
        if "rgb" in spec:
            dst["base"] = list(spec["rgb"])
        for k in ("metallic", "rough"):
            if k in spec:
                dst[k] = spec[k]


def render_view(style_id: str, view: str, samples: int, out_dir: str) -> str:
    env = dict(os.environ, SC_RENDER_ONLY=view, SC_SAMPLES=str(samples))
    r = subprocess.run([BLENDER, "-b", "--python", SCENE],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(r.stdout[-1500:])
        print(r.stderr[-2500:], file=sys.stderr)
        raise RuntimeError(f"{style_id}: blender failed on {view}")
    src = os.path.join(SCENE_OUT, f"{view}.png")
    if not os.path.exists(src):
        raise RuntimeError(f"{style_id}: {view} not produced")
    dst = os.path.join(out_dir, style_id, f"{view}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    return dst


def render_styles(styles: list[dict], views: list[str], samples: int, out_dir: str):
    if not os.path.exists(BASE_CFG):
        raise SystemExit(f"missing base config: {BASE_CFG}")
    shutil.copy(BASE_CFG, LIVE_CFG)
    base = json.load(open(BASE_CFG))
    os.makedirs(out_dir, exist_ok=True)
    backups = {}
    for view in ("hero", "front"):
        src = os.path.join(SCENE_OUT, f"{view}.png")
        if os.path.exists(src):
            bak = os.path.join(out_dir, f"_{view}_square_b.png")
            shutil.copy(src, bak)
            backups[view] = (src, bak)
    built = []
    try:
        for st in styles:
            cfg = json.loads(json.dumps(base))
            apply_style(cfg, st)
            json.dump(cfg, open(LIVE_CFG, "w"), indent=2)
            t0 = time.time()
            for view in views:
                render_view(st["id"], view, samples, out_dir)
            print(f"OK {st['id']}: {'+'.join(views)} ({time.time() - t0:.1f}s)")
            built.append(st)
    finally:
        if os.path.exists(BASE_CFG):
            shutil.copy(BASE_CFG, LIVE_CFG)
        for view, (src, bak) in backups.items():
            if os.path.exists(bak):
                shutil.copy(bak, src)
                os.remove(bak)
    return built


# --------------------------------------------------------------------------
# contact sheet
# --------------------------------------------------------------------------
def compose_sheet(styles: list[dict], out_dir: str, path: str, title: str):
    tiles = []
    for st in styles:
        p = os.path.join(out_dir, st["id"], "hero.png")
        if not os.path.exists(p):
            p = os.path.join(out_dir, st["id"], "front.png")
        if os.path.exists(p):
            tiles.append((st, p))
    if not tiles:
        print("no tiles, skip sheet")
        return

    cols = min(4, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    tile = 380
    gap = 34
    pad = 44
    label_h = 96
    W = pad * 2 + cols * tile + (cols - 1) * gap
    H = 158 + rows * (tile + label_h) + 34
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    d.text((pad, 30), title, font=F(40, True), fill=FG)
    d.text((pad, 84),
           "geometry frozen (STL hashes verified) · only colour / finish changes · "
           "existing lighting + cameras",
           font=F(19), fill=MUT)
    tag = "APPEARANCE ONLY"
    tw = d.textlength(tag, font=F(21, True))
    d.text((W - pad - tw, 40), tag, font=F(21, True), fill=ACC)

    for i, (st, p) in enumerate(tiles):
        col, row = i % cols, i // cols
        x = pad + col * (tile + gap)
        y = 148 + row * (tile + label_h)
        im = Image.open(p).convert("RGB")
        im.thumbnail((tile, tile), Image.LANCZOS)
        canvas = Image.new("RGB", (tile, tile), CARD)
        canvas.paste(im, ((tile - im.width) // 2, (tile - im.height) // 2))
        sheet.paste(canvas, (x, y))
        d.rectangle([x - 1, y - 1, x + tile, y + tile], outline=(48, 52, 62), width=1)

        d.text((x, y + tile + 12), st.get("label", st["id"]), font=F(24, True), fill=FG)
        note = st.get("note", "")
        if note:
            d.text((x, y + tile + 45), note[:38], font=F(16), fill=MUT)
        # swatches from the style spec only (no invented hex)
        sx = x
        for part in ("plate", "shell", "button"):
            hexv = st.get("parts", {}).get(part, {}).get("hex")
            if not hexv:
                continue
            d.rectangle([sx, y + tile + 68, sx + 22, y + tile + 90],
                        fill=hexrgb(hexv), outline=(70, 74, 86))
            d.text((sx + 29, y + tile + 71), part, font=F(15), fill=DIM)
            sx += 29 + int(d.textlength(part, font=F(15))) + 16

    d.text((pad, H - 26),
           "render/appearance/make_styles.py  ·  Blender 4.5.3 Cycles CPU  ·  "
           "styles.json is the single source for each round",
           font=F(15), fill=(96, 104, 118))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path)
    print("WROTE", path, sheet.size)


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--styles", default=f"{APPEAR}/styles.json")
    ap.add_argument("--only", default="", help="comma separated style ids")
    ap.add_argument("--views", default="", help="hero,front (default: from styles.json)")
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--out", default=f"{APPEAR}/styles")
    ap.add_argument("--sheet", default=f"{APPEAR}/01_style_board.png")
    ap.add_argument("--title", default="SmartCoaster · 外观风格板")
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--no-geometry-check", action="store_true")
    args = ap.parse_args()

    spec = json.load(open(args.styles))
    styles = spec["styles"]
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        styles = [s for s in styles if s["id"] in want]
        missing = want - {s["id"] for s in styles}
        if missing:
            raise SystemExit(f"unknown style id(s): {sorted(missing)}")
    if not styles:
        raise SystemExit("no styles selected")

    views = ([v.strip() for v in args.views.split(",") if v.strip()]
             or spec.get("views", ["hero"]))
    samples = args.samples or spec.get("samples", 48)

    if not args.no_geometry_check:
        verify_geometry()
    os.makedirs(args.out, exist_ok=True)
    built = render_styles(styles, views, samples, args.out)
    if not args.no_sheet:
        compose_sheet(built, args.out, args.sheet, args.title)
    print("DONE", len(built), "style(s)", views, f"{samples} samples")


if __name__ == "__main__":
    main()
