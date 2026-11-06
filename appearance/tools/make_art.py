#!/usr/bin/env python3
"""Split an art sheet into printable multi-layer art plates.

Without --config this is the original, verified behaviour: it splits
appearance/src/surface.png into the two hard-coded arts (dog, elf), each a
576 x 576 RGBA plate (circle inscribed, transparent outside) plus a per-pixel
palette-index grid that the Kromacut headless Flat Paint bridge consumes:

    layer_counts.bin  uint16 LE, row-major (y = image top row first),
                      value = palette index + 1, 0 = transparent

With --config <appearance/config/appearance_project.yaml | resolved JSON> the
art name, source image, crop (ellipse or bbox), palette, tuning, pixel size,
layer height and output root all come from the config.  Geometry is derived:

    n_px            = print_dia_mm / pixel_size_mm      (must be an integer)
    print_thickness = len(palette_bottom_up) * layer_height_mm
    art_diameter    = (n_px - 0.2) * pixel_size_mm
    frame           = n_px * pixel_size_mm

`--config` accepts either the project YAML (needs PyYAML, present in system
python3) or the resolved JSON written by appearance/tools/compile.py (stdlib
only).  The compile pipeline always passes the resolved JSON.

Palette order is BOTTOM-UP for Kromacut's face-up Flat Paint layout: entry 0 is
the foundation filament, entry i is the visible top filament of a column with
layer count i+1.  The number of palette entries equals the physical layer count:
dog = 6 layers (1.2 mm slab), elf = 7 layers (1.4 mm slab); the matching plate
pocket depths are in appearance/build/shell/shell.json.

Outputs (defaults; out_dir can be overridden per version):
    appearance/build/art/<name>/
        art_rgba.png          quantized plate, transparent outside the circle
        art_quant_preview.png 2x nearest preview on a neutral background
        art_source_crop.png   the raw crop before quantization (reference)
        layer_counts.bin
        art.json              bridge input + provenance
        palette.png           palette swatches
    appearance/build/art/art_board.png

Run:  python3 appearance/tools/make_art.py                      # current verified arts
      python3 appearance/tools/make_art.py --config appearance/config/appearance_project.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "appearance", "src", "surface.png")
OUT_ROOT = os.path.join(ROOT, "appearance", "build", "art")

# ---------------------------------------------------------------------------
# Defaults = the current, verified pipeline.  Used only when --config is absent.
# ---------------------------------------------------------------------------
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

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ---------------------------------------------------------------------------
# config loading / normalisation
# ---------------------------------------------------------------------------
def rel(path: str) -> str:
    try:
        return os.path.relpath(os.path.abspath(path), ROOT)
    except ValueError:  # pragma: no cover - different drive on Windows
        return os.path.abspath(path)


def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def load_config_doc(path: str) -> dict:
    """Load the project YAML (PyYAML) or a compile-resolved JSON file."""
    path = abspath(path)
    if not os.path.isfile(path):
        raise SystemExit(
            "make_art.py: --config file not found: %s\n"
            "  expected: appearance/config/appearance_project.yaml" % rel(path)
        )
    with open(path, "r", encoding="utf-8") as fh:
        if path.lower().endswith(".json"):
            return json.load(fh)
        text = fh.read()
    try:
        import yaml  # noqa: WPS433 - optional dependency
    except ImportError:  # pragma: no cover - system python3 has PyYAML
        raise SystemExit(
            "make_art.py: reading %s needs PyYAML, which this interpreter lacks.\n"
            "  Either run via `bash appearance/compile.sh` (passes a resolved JSON),\n"
            "  or `python3 appearance/tools/compile.py` to produce "
            "appearance/build/compile/resolved_config.json and pass that with --config.\n"
            % rel(path)
        )
    return yaml.safe_load(text)


def _versions(doc: dict, config_label: str) -> dict:
    versions = (doc or {}).get("versions")
    if not isinstance(versions, dict) or not versions:
        raise SystemExit(
            "make_art.py: %s has no `versions:` mapping; see the schema documented at "
            "the top of appearance/config/appearance_project.yaml" % config_label
        )
    return versions


def _crop_box(raw: dict, where: str) -> tuple:
    mode = str(raw.get("mode") or "ellipse").lower()
    if mode == "ellipse":
        try:
            cx, cy = float(raw["cx"]), float(raw["cy"])
            rx, ry = float(raw["rx"]), float(raw["ry"])
        except (KeyError, TypeError, ValueError):
            raise SystemExit(
                "make_art.py: %s.crop.mode=ellipse needs numeric cx, cy, rx, ry "
                "(example: {mode: ellipse, cx: 449.0, cy: 439.5, rx: 415.5, ry: 406.0})"
                % where
            )
        if rx <= 0 or ry <= 0:
            raise SystemExit("make_art.py: %s.crop.rx/ry must be > 0" % where)
        box = (cx - rx, cy - ry, cx + rx, cy + ry)
        ellipse = [rx, ry]
    elif mode == "bbox":
        try:
            box = tuple(float(raw[k]) for k in ("x0", "y0", "x1", "y1"))
        except (KeyError, TypeError, ValueError):
            raise SystemExit(
                "make_art.py: %s.crop.mode=bbox needs numeric x0, y0, x1, y1 "
                "(source-image pixel coordinates; x1/y1 exclusive-ish, PIL box order)"
                % where
            )
        ellipse = None
        if not (box[0] < box[2] and box[1] < box[3]):
            raise SystemExit("make_art.py: %s.crop bbox needs x0<x1 and y0<y1: %r"
                             % (where, list(box)))
    else:
        raise SystemExit("make_art.py: %s.crop.mode=%r unsupported (use ellipse|bbox)"
                         % (where, mode))
    return box, mode, ellipse


def _palette(raw, where: str) -> list:
    if not isinstance(raw, list) or not raw:
        raise SystemExit(
            "make_art.py: %s.palette_bottom_up must be a non-empty list of #RRGGBB "
            "colours (bottom-up, one per physical layer)" % where
        )
    out = []
    for i, h in enumerate(raw):
        h = str(h).strip()
        if not HEX_RE.match(h):
            raise SystemExit(
                "make_art.py: %s.palette_bottom_up[%d]=%r is not #RRGGBB" % (where, i, h)
            )
        out.append(h)  # keep the author's case in art.json
    return out


def config_specs(doc: dict, config_path: str) -> list:
    """Normalise project YAML / resolved JSON -> list of art specs."""
    label = rel(config_path)
    specs = []
    for vkey, v in _versions(doc, label).items():
        where = "%s: versions.%s.art" % (label, vkey)
        if not isinstance(v, dict):
            raise SystemExit("make_art.py: %s.versions.%s must be a mapping" % (label, vkey))
        art = dict(v.get("art") or {})
        shell = v.get("shell") or {}
        name = str(art.get("name") or vkey)
        image = str(art.get("image") or rel(SRC))
        box, mode, ellipse = _crop_box(art.get("crop") or {}, where)
        palette = _palette(art.get("palette_bottom_up"), where)
        tune = art.get("tuning") or {}
        try:
            contrast = float(tune.get("contrast", 1.0))
            saturation = float(tune.get("saturation", 1.0))
        except (TypeError, ValueError):
            raise SystemExit(
                "make_art.py: %s.tuning.contrast/saturation must be numbers (1.0 = no-op)"
                % where
            )
        try:
            pixel = float(art.get("pixel_size_mm", PX))
            layer = float(art.get("layer_height_mm", LAYER_MM))
        except (TypeError, ValueError):
            raise SystemExit(
                "make_art.py: %s.pixel_size_mm / layer_height_mm must be numbers" % where
            )
        if pixel <= 0 or layer <= 0:
            raise SystemExit("make_art.py: %s.pixel_size_mm/layer_height_mm must be > 0" % where)

        print_dia = art.get("print_dia_mm")
        if print_dia is None:
            print_dia = shell.get("print_dia_mm")
        n = art.get("n_px")
        if n is None:
            if print_dia is None:
                raise SystemExit(
                    "make_art.py: %s has neither n_px nor print_dia_mm (project YAML puts "
                    "print_dia_mm under versions.%s.shell)" % (where, vkey)
                )
            raw_n = float(print_dia) / pixel
            n = int(round(raw_n))
            if n <= 0 or abs(raw_n - n) > 1e-6:
                raise SystemExit(
                    "make_art.py: %s print_dia_mm=%s / pixel_size_mm=%s = %s is not an "
                    "integer pixel count; adjust one of them (e.g. 86.4/0.15 = 576)"
                    % (where, print_dia, pixel, raw_n)
                )
        n = int(n)
        if n <= 0:
            raise SystemExit("make_art.py: %s.n_px must be > 0" % where)
        out_root = str(art.get("out_dir") or rel(OUT_ROOT))
        specs.append({
            "version": vkey,
            "name": name,
            "image": image,
            "crop": {"mode": mode, "box": box, "ellipse": ellipse},
            "palette_bottom_up": palette,
            "contrast": contrast,
            "saturation": saturation,
            "pixel_size_mm": pixel,
            "layer_height_mm": layer,
            "n_px": n,
            "out_root": out_root,
        })
    return specs


def default_specs() -> list:
    """The no-config path: exactly the original, verified two-art behaviour."""
    specs = []
    for name, (cx, cy, rx, ry) in ARTS.items():
        specs.append({
            "version": name,
            "name": name,
            "image": rel(SRC),
            "crop": {"mode": "ellipse",
                     "box": (cx - rx, cy - ry, cx + rx, cy + ry),
                     "ellipse": [rx, ry]},
            "palette_bottom_up": list(PALETTES[name]),
            "contrast": float(TUNING[name]["contrast"]),
            "saturation": float(TUNING[name]["saturation"]),
            "pixel_size_mm": PX,
            "layer_height_mm": LAYER_MM,
            "n_px": N,
            "out_root": rel(OUT_ROOT),
        })
    return specs


# ---------------------------------------------------------------------------
# image / colour helpers (unchanged)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# per-art processing
# ---------------------------------------------------------------------------
def process(spec: dict) -> tuple:
    name = spec["name"]
    n = spec["n_px"]
    px = spec["pixel_size_mm"]
    layer_mm = spec["layer_height_mm"]
    palette_hex = list(spec["palette_bottom_up"])
    palette = np.array([hex_to_rgb01(h) for h in palette_hex])
    image_path = abspath(spec["image"])
    out_root = abspath(spec["out_root"])
    out_dir = os.path.join(out_root, name)

    if not os.path.isfile(image_path):
        raise SystemExit(
            "make_art.py: source image not found for art %r: %s\n"
            "  put the sheet there or fix versions.<v>.art.image in "
            "appearance/config/appearance_project.yaml" % (name, rel(image_path))
        )
    sheet = Image.open(image_path).convert("RGB")
    x0, y0, x1, y1 = spec["crop"]["box"]
    if not (0.0 <= x0 < x1 <= sheet.width and 0.0 <= y0 < y1 <= sheet.height):
        raise SystemExit(
            "make_art.py: crop for art %r is outside the %dx%d source image: "
            "box=(%.1f, %.1f, %.1f, %.1f)\n  fix versions.<v>.art.crop in "
            "appearance/config/appearance_project.yaml"
            % (name, sheet.width, sheet.height, x0, y0, x1, y1)
        )
    box = (x0, y0, x1, y1)
    # Ellipse bbox -> n x n square: restores a true circle and resamples.
    crop = sheet.resize((n, n), Image.LANCZOS, box=box)

    rgb = np.asarray(crop).astype(np.float32) / 255.0
    yy, xx = np.mgrid[0:n, 0:n]
    # cell-centre distance; radius n/2 - 0.1 px -> art diameter (n-0.2)*px
    dist = np.hypot(xx + 0.5 - n / 2.0, yy + 0.5 - n / 2.0)
    mask = dist <= (n / 2.0 - 0.1)
    # bleed colors outside the circle before quantizing, then mask hard
    rgb_bleed = bleed_outward(rgb, mask, iterations=6)
    contrast = float(spec["contrast"])
    saturation = float(spec["saturation"])
    labels = quantize(rgb_bleed, mask, palette, contrast=contrast, saturation=saturation)

    hard = mask
    counts = np.where(hard, labels + 1, 0).astype(np.uint16)

    os.makedirs(out_dir, exist_ok=True)

    quant = palette[np.clip(labels, 0, len(palette) - 1)]
    rgba = np.zeros((n, n, 4), dtype=np.uint8)
    rgba[..., :3] = np.round(quant * 255.0).astype(np.uint8)
    rgba[..., 3] = np.where(hard, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(out_dir, "art_rgba.png"))

    # previews
    checker = np.zeros((n, n, 3), dtype=np.uint8)
    checker[:] = 60
    checker[((yy // 16 + xx // 16) % 2) == 0] = 90
    pre = rgba[..., :3].astype(np.float32) * (rgba[..., 3:4].astype(np.float32) / 255.0)
    bg = pre + checker.astype(np.float32) * (1.0 - rgba[..., 3:4].astype(np.float32) / 255.0)
    prev = Image.fromarray(np.round(bg).astype(np.uint8), "RGB").resize(
        (n * 2, n * 2), Image.NEAREST
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
    source = {
        "file": rel(image_path),
        "bbox_xyxy": [round(box[0], 2), round(box[1], 2), round(box[2], 2), round(box[3], 2)],
    }
    if spec["crop"]["mode"] == "ellipse":
        source["source_ellipse_rx_ry"] = list(spec["crop"]["ellipse"])
    else:
        source["crop_mode"] = "bbox"
    source["sha256"] = hashlib.sha256(open(image_path, "rb").read()).hexdigest()
    art = {
        "name": name,
        "width": n,
        "height": n,
        "pixel_size_mm": px,
        "layer_height_mm": layer_mm,
        "first_layer_mm": layer_mm,
        "orientation": "face-up",
        "layer_count": len(palette_hex),
        "print_thickness_mm": round(len(palette_hex) * layer_mm, 4),
        "art_diameter_mm": round((n - 0.2) * px, 4),
        "frame_mm": round(n * px, 4),
        "palette_bottom_up": palette_hex,
        "palette_pixel_counts": stats,
        "source": source,
        "layers": {
            "0 (transparent)": int((counts == 0).sum()),
            **{f"{i + 1} = {h}": int((counts == i + 1).sum()) for i, h in enumerate(palette_hex)},
        },
        "generator": "appearance/tools/make_art.py",
    }
    with open(os.path.join(out_dir, "art.json"), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, ensure_ascii=False)
    print(f"[{name}] {out_dir}: {stats}")
    return art, out_dir


def make_board(arts: list) -> str:
    """Comparison board: source crop | quantized plate, one row per art."""
    widths = [a["width"] for a, _ in arts]
    heights = [a["height"] for a, _ in arts]
    board_w = 2 * max(widths)
    board_h = sum(heights)
    board = Image.new("RGB", (board_w, board_h), (255, 255, 255))
    y = 0
    for art, d in arts:
        w, h = art["width"], art["height"]
        a = Image.open(os.path.join(d, "art_source_crop.png")).resize((w, h))
        b = Image.open(os.path.join(d, "art_rgba.png"))
        bg = Image.new("RGB", (w, h), (70, 70, 74))
        bg.paste(b, (0, 0), b)
        board.paste(a, (0, y))
        board.paste(bg, (max(widths), y))
        y += h
    out_root = os.path.dirname(arts[0][1]) if arts else OUT_ROOT
    board_path = os.path.join(out_root, "art_board.png")
    board.save(board_path)
    return board_path


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description="Split an art sheet into printable multi-layer art plates "
                    "(default = the verified dog/elf pipeline).")
    ap.add_argument("--config", default=None,
                    help="appearance/config/appearance_project.yaml or a compile-resolved "
                         "JSON; omit for the built-in verified dog/elf defaults")
    args = ap.parse_args(argv)

    if args.config:
        doc = load_config_doc(args.config)
        specs = config_specs(doc, args.config)
    else:
        specs = default_specs()

    for spec in specs:
        os.makedirs(abspath(spec["out_root"]), exist_ok=True)
    arts = [process(spec) for spec in specs]
    board = make_board(arts)
    print(f"[board] {board}")


if __name__ == "__main__":
    main()
