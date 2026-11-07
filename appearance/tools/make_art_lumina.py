#!/usr/bin/env python3
"""Split the art sheet into per-version print images for the Lumina-Layers stage.

This replaces the Kromacut-era quantiser.  Lumina-Layers does its own colour
matching (optical layer mixing), so this stage only has to deliver a clean,
correctly sized, transparent-background PNG per art:

    appearance/src/surface.png            1774 x 887, two flattened ellipses on a white sheet
        |  crop the measured ellipse bbox, resample to a square (ellipse -> true circle)
        |  bleed circle colours outward a few px (kills the white LANCZOS fringe)
        |  alpha = 0 outside the inscribed circle
        v
    appearance/build/art/<art>/art_rgba.png     864 x 864 RGBA (0.10 mm/px, 86.4 mm frame)
    appearance/build/art/<art>/art.json         provenance + geometry contract
    appearance/build/art/art_board.png          both arts side by side (review aid)

Why 864 px: Lumina-Layers HIGH_FIDELITY rasterises on a fixed 0.10 mm/px grid
(`target_w = int(target_width_mm * 10)`, image_processing.py:548-574).  Feeding
exactly 864 px for `target_width_mm = 86.4` makes its NEAREST resample an
identity, so no second-generation aliasing is introduced.

Run:  python3 appearance/tools/make_art_lumina.py
      python3 appearance/tools/make_art_lumina.py --check    # verify only, no write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "appearance", "src", "surface.png")
OUT_ROOT = os.path.join(ROOT, "appearance", "build", "art")

# Geometry contract (mirrors appearance/build/shell/shell.json).
PIXEL_MM = 0.10          # Lumina HIGH_FIDELITY fixed raster grid
N = 864                  # 864 * 0.10 = 86.4 mm frame
FRAME_MM = N * PIXEL_MM  # 86.4
ART_DIAMETER_MM = 86.40  # visible disc diameter = frame (alpha circle touches bbox)
TOTAL_LAYERS = 15        # 5 colour layers + 10 backing layers
LUMINA_LAYER_MM = 0.08   # fixed by PrinterConfig.LAYER_HEIGHT
PRINT_THICKNESS_MM = TOTAL_LAYERS * LUMINA_LAYER_MM   # 1.20

# Per-art prep tuning (PIL ImageEnhance): the elf sheet is low-contrast pastel and
# the 4-filament CMYW LUT otherwise returns a visibly washed-out print.  Lifting
# contrast/saturation in the SOURCE is the same trick the old Kromacut line used
# (PROVISIONAL: re-check against the physical print once one is made).
# 1.0 = ship the source colours unchanged (the reports/acceptance quote the numbers
# of this baseline).  Raise them only together with a physical colour check.
TUNING = {
    "dog": {"contrast": 1.00, "color": 1.00},
    "elf": {"contrast": 1.00, "color": 1.00},
}

# Source sheet geometry (measured; see appearance/README.md section 4).
ARTS = {
    "dog": (449.0, 439.5, 415.5, 406.0),
    "elf": (1325.0, 439.0, 415.5, 406.5),
}


def rel(path: str) -> str:
    try:
        return os.path.relpath(os.path.abspath(path), ROOT)
    except ValueError:  # pragma: no cover
        return os.path.abspath(path)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bleed_outward(rgb: np.ndarray, inside: np.ndarray, iterations: int = 6) -> np.ndarray:
    """Grow colours from `inside` into the transparent margin (kills white fringe)."""
    out = rgb.astype(np.float32).copy()
    known = inside.copy()
    h, w = inside.shape
    for _ in range(iterations):
        pad = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
        padk = np.pad(known, ((1, 1), (1, 1)), mode="edge")
        acc = np.zeros_like(out)
        cnt = np.zeros((h, w), dtype=np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                nk = padk[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                acc += nb * nk[..., None]
                cnt += nk
        grow = (~known) & (cnt > 0)
        out[grow] = acc[grow] / cnt[grow][:, None]
        known = known | grow
    return np.clip(out, 0, 255).astype(np.uint8)


def process(name: str) -> dict:
    cx, cy, rx, ry = ARTS[name]
    box = (cx - rx, cy - ry, cx + rx, cy + ry)
    sheet = Image.open(SRC).convert("RGB")
    crop = sheet.resize((N, N), Image.LANCZOS, box=box)

    from PIL import ImageEnhance
    tune = TUNING.get(name) or {"contrast": 1.0, "color": 1.0}
    crop = ImageEnhance.Contrast(crop).enhance(float(tune["contrast"]))
    crop = ImageEnhance.Color(crop).enhance(float(tune["color"]))
    rgb = np.asarray(crop, dtype=np.float32)
    yy, xx = np.mgrid[0:N, 0:N]
    c = (N - 1) / 2.0
    r_px = N / 2.0
    rr = np.hypot(xx - c, yy - c)
    inside = rr <= (r_px - 0.5)

    rgb = bleed_outward(rgb, inside)
    alpha = np.where(inside, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])

    out_dir = os.path.join(OUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, "art_rgba.png")
    Image.fromarray(rgba, "RGBA").save(png, optimize=True)
    Image.fromarray(rgba, "RGBA").resize((192, 192), Image.LANCZOS).save(
        os.path.join(out_dir, "art_thumb.png"))
    crop.save(os.path.join(out_dir, "art_source_crop.png"))

    # scale: the alpha disc must span the full frame (diameter = N px)
    disc_px = 2.0 * r_px - 1.0
    meta = {
        "schema": "smartcoaster.appearance.art_lumina/v1",
        "generator": "appearance/tools/make_art_lumina.py",
        "name": name,
        "engine": "Lumina-Layers (Lumina Studio 2.0)",
        "width": N,
        "height": N,
        "pixel_size_mm": PIXEL_MM,
        "frame_mm": round(FRAME_MM, 3),
        "art_diameter_mm": round(ART_DIAMETER_MM, 3),
        "disc_diameter_px": round(disc_px, 2),
        "alpha": "binary (0 outside the inscribed circle)",
        "color_model": "unquantised sRGB; Lumina does LUT/recipe matching downstream",
        "prep_tuning": tune,
        # generic contract used by appearance/cad/build_recessed.py + reports
        "layer_height_mm": LUMINA_LAYER_MM,
        "layer_count": 5,
        "print_thickness_mm": round(PRINT_THICKNESS_MM, 3),
        "orientation": "face-up (assembly pose); print pose is art-face-down",
        "palette_bottom_up": ["#FFFFFF", "#0086D6", "#EC008C", "#F4EE2A"],
        "lumine_geometry": {
            "target_width_mm": round(FRAME_MM, 3),
            "target_pixel_grid": N,
            "color_layers": 5,
            "backing_layers": 10,
            "layer_height_mm": LUMINA_LAYER_MM,
            "total_layers": TOTAL_LAYERS,
            "print_thickness_mm": round(PRINT_THICKNESS_MM, 3),
            "structure": "single-sided, colour face at z=0 (printed first), flat back",
        },
        "source": {
            "file": rel(SRC),
            "sha256": sha256_file(SRC),
            "bbox_xyxy": [round(v, 2) for v in box],
            "source_ellipse_rx_ry": [rx, ry],
            "note": "source ellipses are re-squared to true circles (rx != ry on the sheet)",
        },
        "artifacts": {
            "art_rgba.png": sha256_file(png),
            "art_source_crop.png": sha256_file(os.path.join(out_dir, "art_source_crop.png")),
        },
        "pixel_stats": {
            "opaque_pixels": int(inside.sum()),
            "transparent_pixels": int((~inside).sum()),
            "opaque_ratio": round(float(inside.mean()), 6),
        },
    }
    with open(os.path.join(out_dir, "art.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return meta


def make_board(metas: list) -> str:
    pad = 16
    w = N * len(metas) + pad * (len(metas) + 1)
    h = N + 2 * pad
    board = Image.new("RGB", (w, h), (28, 30, 34))
    for i, m in enumerate(metas):
        img = Image.open(os.path.join(OUT_ROOT, m["name"], "art_rgba.png")).convert("RGBA")
        bg = Image.new("RGB", img.size, (28, 30, 34))
        bg.paste(img, (0, 0), img)
        board.paste(bg, (pad + i * (N + pad), pad))
    out = os.path.join(OUT_ROOT, "art_board.png")
    board.save(out, optimize=True)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify only, do not write")
    ap.add_argument("--arts", default="dog,elf")
    args = ap.parse_args(argv)

    names = [n.strip() for n in args.arts.split(",") if n.strip()]
    metas = []
    ok = True
    for name in names:
        if name not in ARTS:
            raise SystemExit("unknown art %r (known: %s)" % (name, ", ".join(ARTS)))
        if args.check:
            p = os.path.join(OUT_ROOT, name, "art.json")
            if not os.path.exists(p):
                print("MISSING %s" % rel(p))
                ok = False
                continue
            m = json.load(open(p, encoding="utf-8"))
            print("OK %-4s %dx%d %s frame %.2f mm disc %.2f mm sha %s" % (
                name, m["width"], m["height"], m["color_model"].split(";")[0],
                m["frame_mm"], m["art_diameter_mm"], m["artifacts"]["art_rgba.png"][:12]))
            metas.append(m)
            continue
        m = process(name)
        print("art %-4s -> %s (%dx%d, %.2f mm, %.2f mm thick)" % (
            name, rel(os.path.join(OUT_ROOT, name, "art_rgba.png")),
            m["width"], m["height"], m["frame_mm"],
            m["lumine_geometry"]["print_thickness_mm"]))
        metas.append(m)

    if not args.check and metas:
        print("board ->", rel(make_board(metas)))
    if args.check and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
