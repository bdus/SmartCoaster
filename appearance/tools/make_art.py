#!/usr/bin/env python3
"""Split appearance/src/surface.png into two printable art plates.

The source sheet holds two round illustrations side by side on a white
background. Each becomes a 576 x 576 RGBA plate (circle inscribed, transparent
outside) plus a per-pixel palette-index grid that the Kromacut headless Flat
Paint bridge consumes:

    layer_counts.bin  uint16 LE, row-major (y = image top row first),
                      value = palette index + 1, 0 = transparent

Palette order is BOTTOM-UP for Kromacut's face-up Flat Paint layout: entry 0 is
the foundation filament, entry i is the visible top filament of a column with
layer count i+1. The number of palette entries equals the physical layer count:
dog = 6 layers (1.2 mm slab), elf = 7 layers (1.4 mm slab); the matching plate
pocket depths are in appearance/build/shell/shell.json.

Outputs (appearance/build/art/<name>/):
    art_rgba.png          quantized plate, transparent outside the circle
    art_quant_preview.png 2x nearest preview on a neutral background
    art_source_crop.png   the raw crop before quantization (reference)
    layer_counts.bin
    art.json              bridge input + provenance
    palette.png           palette swatches

Run:  python3 appearance/tools/make_art.py
"""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "appearance", "src", "surface.png")
OUT_ROOT = os.path.join(ROOT, "appearance", "build", "art")

# Geometry of the printed plate (mm). 576 x 0.15 = 86.4 mm.
PX = 0.15
N = 576
DIAMETER_MM = N * PX
LAYER_MM = 0.2

# Source sheet geometry (measured, see docs in appearance/README.md).
ARTS = {
    # name: (cx, cy, rx, ry)  -- the source art is a slightly flattened ellipse;
    # resampling its bbox to a square restores a true circle.
    "dog": (449.0, 439.5, 415.5, 406.0),
    "elf": (1325.0, 439.0, 415.5, 406.5),
}

# Bottom-up palettes (Kromacut face-up Flat Paint: layerFilamentHexes order).
# Number of entries = physical layer count = print thickness / 0.2 mm.
PALETTES = {
    "dog": [
        "#FBF4E8",  # 0 cream     foundation / fur / clouds / white flowers
        "#CBE0F5",  # 1 sky       background
        "#9FB2DA",  # 2 periwinkle blue flowers / eye shadow / accents
        "#F9CD72",  # 3 yellow    chick, flowers
        "#F09FAF",  # 4 pink      blush
        "#6C574C",  # 5 brown     outline / linework
    ],
    "elf": [
        "#EDE1F0",  # 0 pale lavender foundation / background / hair base
        "#D9CFE6",  # 1 hair shadow   hair shading / eyebrows
        "#C3AEDC",  # 2 purple        background flowers / accents
        "#F7D2C0",  # 3 skin          face / hands
        "#E8A9B8",  # 4 blush         cheeks
        "#C9A45B",  # 5 gold          collar / trim
        "#5B4A72",  # 6 deep purple   outline / linework
    ],
}

# Per-art quantization tuning: the elf art is much lower contrast, so it needs a
# little lift to survive a 7-colour flat print. Values are applied in CIELAB
# before nearest-colour assignment (L* around 50, a*b* gain).
TUNING = {
    "dog": {"contrast": 1.08, "saturation": 1.15},
    "elf": {"contrast": 1.05, "saturation": 1.10},
}


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB [0,1] -> CIELAB (D65). Vectorized, shape (...,3)."""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    lab = np.empty_like(f)
    lab[..., 0] = 116.0 * f[..., 1] - 16.0
    lab[..., 1] = 500.0 * (f[..., 0] - f[..., 1])
    lab[..., 2] = 200.0 * (f[..., 1] - f[..., 2])
    return lab


def hex_to_rgb01(hex_str: str) -> np.ndarray:
    h = hex_str.lstrip("#")
    return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255.0


def bleed_outward(rgb: np.ndarray, inside: np.ndarray, iterations: int = 6) -> np.ndarray:
    """Fill outside-mask pixels with nearby inside colors (kills white halos)."""
    out = rgb.astype(np.float32).copy()
    known = inside.copy()
    for _ in range(iterations):
        if known.all():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(known.shape, dtype=np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                shifted = np.roll(np.roll(out, dy, axis=0), dx, axis=1)
                kshift = np.roll(np.roll(known, dy, axis=0), dx, axis=1)
                acc += shifted * kshift[..., None]
                cnt += kshift
        fill = (~known) & (cnt > 0)
        out[fill] = acc[fill] / cnt[fill, None]
        known = known | fill
    return out


def quantize(
    rgb: np.ndarray,
    mask: np.ndarray,
    palette: np.ndarray,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> np.ndarray:
    """Nearest palette color in CIELAB for masked pixels; majority despeckle."""
    lab = srgb_to_lab(rgb)
    if contrast != 1.0:
        lab[..., 0] = 50.0 + (lab[..., 0] - 50.0) * contrast
    if saturation != 1.0:
        lab[..., 1] *= saturation
        lab[..., 2] *= saturation
    pal_lab = srgb_to_lab(palette)
    d = ((lab[:, :, None, :] - pal_lab[None, None, :, :]) ** 2).sum(-1)
    labels = d.argmin(-1).astype(np.int16)
    labels = np.where(mask, labels, -1)
    K = len(palette)

    # 3x3 majority pass: only rewrite pixels where >=4/9 neighbours agree.
    for _ in range(3):
        counts = np.zeros((K,) + labels.shape, dtype=np.int16)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                shifted = np.roll(np.roll(labels, dy, axis=0), dx, axis=1)
                for k in range(K):
                    counts[k] += shifted == k
        best = counts.argmax(0)
        best_n = counts.max(0)
        change = mask & (labels != best) & (best_n >= 4)
        labels = np.where(change, best, labels)

    # Final pass: no pixel may be isolated (every surviving colour pixel needs a
    # same-label neighbour), otherwise it becomes an unprintable 0.15 mm dot.
    for _ in range(2):
        same = np.zeros(labels.shape, dtype=np.int16)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                same += np.roll(np.roll(labels, dy, axis=0), dx, axis=1) == labels
        counts = np.zeros((K,) + labels.shape, dtype=np.int16)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                shifted = np.roll(np.roll(labels, dy, axis=0), dx, axis=1)
                for k in range(K):
                    counts[k] += shifted == k
        best = counts.argmax(0)
        labels = np.where(mask & (same == 0), best, labels)
    return labels


def process(name: str) -> dict:
    cx, cy, rx, ry = ARTS[name]
    palette_hex = PALETTES[name]
    palette = np.array([hex_to_rgb01(h) for h in palette_hex])

    sheet = Image.open(SRC).convert("RGB")
    # Ellipse bbox -> 576x576 square: restores a true circle and resamples.
    box = (cx - rx, cy - ry, cx + rx, cy + ry)
    crop = sheet.resize((N, N), Image.LANCZOS, box=box)

    rgb = np.asarray(crop).astype(np.float32) / 255.0
    yy, xx = np.mgrid[0:N, 0:N]
    # cell-centre distance; radius 287.9 = 86.37 mm plate (target 86.4)
    dist = np.hypot(xx + 0.5 - N / 2.0, yy + 0.5 - N / 2.0)
    mask = dist <= (N / 2.0 - 0.1)  # 287.9
    # bleed colors outside the circle before quantizing, then mask hard
    rgb_bleed = bleed_outward(rgb, mask, iterations=6)
    tune = TUNING[name]
    labels = quantize(
        rgb_bleed, mask, palette, contrast=tune["contrast"], saturation=tune["saturation"]
    )

    hard = mask
    counts = np.where(hard, labels + 1, 0).astype(np.uint16)

    out_dir = os.path.join(OUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)

    quant = palette[np.clip(labels, 0, len(palette) - 1)]
    rgba = np.zeros((N, N, 4), dtype=np.uint8)
    rgba[..., :3] = np.round(quant * 255.0).astype(np.uint8)
    rgba[..., 3] = np.where(hard, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(out_dir, "art_rgba.png"))

    # previews
    checker = np.zeros((N, N, 3), dtype=np.uint8)
    checker[:] = 60
    checker[((yy // 16 + xx // 16) % 2) == 0] = 90
    pre = rgba[..., :3].astype(np.float32) * (rgba[..., 3:4].astype(np.float32) / 255.0)
    bg = pre + checker.astype(np.float32) * (1.0 - rgba[..., 3:4].astype(np.float32) / 255.0)
    prev = Image.fromarray(np.round(bg).astype(np.uint8), "RGB").resize(
        (N * 2, N * 2), Image.NEAREST
    )
    prev.save(os.path.join(out_dir, "art_quant_preview.png"))
    crop.save(os.path.join(out_dir, "art_source_crop.png"))

    # palette swatch strip
    sw = Image.new("RGB", (96 * len(palette_hex), 96), (128, 128, 128))
    for i, h in enumerate(palette_hex):
        tile = Image.new("RGB", (96, 96), tuple(int(h[j : j + 2], 16) for j in (1, 3, 5)))
        sw.paste(tile, (i * 96, 0))
    sw.save(os.path.join(out_dir, "palette.png"))

    counts.astype("<u2").tofile(os.path.join(out_dir, "layer_counts.bin"))

    stats = {}
    for i, h in enumerate(palette_hex):
        stats[h] = int((counts == i + 1).sum())
    art = {
        "name": name,
        "width": N,
        "height": N,
        "pixel_size_mm": PX,
        "layer_height_mm": LAYER_MM,
        "first_layer_mm": LAYER_MM,
        "orientation": "face-up",
        "layer_count": len(palette_hex),
        "print_thickness_mm": round(len(palette_hex) * LAYER_MM, 4),
        "art_diameter_mm": round((N - 0.2) * PX, 4),
        "frame_mm": round(DIAMETER_MM, 4),
        "palette_bottom_up": palette_hex,
        "palette_pixel_counts": stats,
        "source": {
            "file": "appearance/src/surface.png",
            "bbox_xyxy": [round(box[0], 2), round(box[1], 2), round(box[2], 2), round(box[3], 2)],
            "source_ellipse_rx_ry": [rx, ry],
            "sha256": hashlib.sha256(open(SRC, "rb").read()).hexdigest(),
        },
        "layers": {
            "0 (transparent)": int((counts == 0).sum()),
            **{f"{i + 1} = {h}": int((counts == i + 1).sum()) for i, h in enumerate(palette_hex)},
        },
        "generator": "appearance/tools/make_art.py",
    }
    with open(os.path.join(out_dir, "art.json"), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, ensure_ascii=False)
    print(f"[{name}] {out_dir}: {stats}")
    return art


def main() -> None:
    os.makedirs(OUT_ROOT, exist_ok=True)
    arts = [process(name) for name in ARTS]
    # comparison board: source crop | quantized plate, per art
    tiles = []
    for art in arts:
        d = os.path.join(OUT_ROOT, art["name"])
        a = Image.open(os.path.join(d, "art_source_crop.png")).resize((N, N))
        b = Image.open(os.path.join(d, "art_rgba.png"))
        bg = Image.new("RGB", (N, N), (70, 70, 74))
        bg.paste(b, (0, 0), b)
        tiles.append((a, bg.resize((N, N))))
    board = Image.new("RGB", (N * 2, N * 2), (255, 255, 255))
    for i, (a, b) in enumerate(tiles):
        board.paste(a, (0, i * N))
        board.paste(b, (N, i * N))
    board.save(os.path.join(OUT_ROOT, "art_board.png"))
    print(f"[board] {os.path.join(OUT_ROOT, 'art_board.png')}")


if __name__ == "__main__":
    main()
