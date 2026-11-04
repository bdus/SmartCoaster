#!/usr/bin/env python3
"""Render the 4 CMF colorways with the existing square_b scene, then compose
CMF_variants.png. No LED / no emissive part (removed 2026-11-04), so the front face
is only the 26x7 screen window + button.

Run:
  python3 render/cmf/make_variants.py
Outputs:
  render/cmf/{lumen_violet,moss,sand,graphite}.png  (hero view per colorway)
  render/cmf/CMF_variants.png                       (2x2 contact sheet)
"""
import json
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = "/data/Documents/projects/SmartCoaster"
BASE = f"{ROOT}/render/square_b"
CFG = f"{BASE}/config.json"
OUT = f"{ROOT}/render/cmf"
BACK = f"{OUT}/config_base.json"
BLENDER = "/data/Documents/tools/blender/blender"

BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# env for the shared scene: hero only (fast), 48 samples is enough for 1 MP
CHILD_ENV = dict(os.environ, SC_RENDER_ONLY="hero", SC_SAMPLES="48")


def lin(h):
    """sRGB hex -> linear (Blender base_color expects linear)."""
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


VARIANTS = {
    "lumen_violet": {"plate": lin("6B40A0"), "shell": lin("2A2E35"),
                     "button": lin("6B40A0")},
    "moss":         {"plate": lin("4F6B4A"), "shell": lin("2B302B"),
                     "button": lin("4F6B4A")},
    "sand":         {"plate": lin("C9B79A"), "shell": lin("3A3530"),
                     "button": lin("C9B79A")},
    "graphite":     {"plate": lin("3A3D42"), "shell": lin("1E2024"),
                     "button": lin("942826")},
}

LABELS = {
    "lumen_violet": ("Lumen Violet", "#6B40A0", "#2A2E35"),
    "moss":         ("Moss",         "#4F6B4A", "#2B302B"),
    "sand":         ("Sand",         "#C9B79A", "#3A3530"),
    "graphite":     ("Graphite",     "#3A3D42", "#1E2024"),
}


def F(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def compose_sheet():
    bg = (18, 20, 24)
    fg = (232, 236, 242)
    mut = (150, 158, 172)
    acc = (140, 120, 230)
    pad, tile, gap = 40, 440, 24
    w = pad * 2 + tile * 2 + gap
    h = pad + 90 + (tile + 74) * 2
    sheet = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 30), "SmartCoaster - CMF colorways", font=F(40, True), fill=fg)
    d.text((pad, 82), "no LED - quiet surfaces; 26 x 7 OLED window + button",
           font=F(22), fill=mut)
    d.text((w - pad - 260, 40), "QUIET TECH", font=F(26, True), fill=acc)
    for i, name in enumerate(("lumen_violet", "moss", "sand", "graphite")):
        col, row = i % 2, i // 2
        x = pad + col * (tile + gap)
        y = 130 + row * (tile + 74)
        im = Image.open(f"{OUT}/{name}.png").convert("RGB").resize((tile, tile),
                                                                  Image.LANCZOS)
        sheet.paste(im, (x, y))
        label, plate, shell = LABELS[name]
        d.text((x, y + tile + 12), label, font=F(28, True), fill=fg)
        sw = [(plate, "plate"), (shell, "shell")]
        for j, (hexv, _nm) in enumerate(sw):
            rgb = tuple(int(hexv.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
            d.rectangle([x + 240 + j * 44, y + tile + 16,
                         x + 272 + j * 44, y + tile + 48], fill=rgb)
    d.text((pad, h - 26), "render/cmf/make_variants.py  -  Blender 4.5.3 Cycles CPU",
           font=F(18), fill=(110, 118, 132))
    sheet.save(f"{OUT}/CMF_variants.png")
    print("WROTE", f"{OUT}/CMF_variants.png", sheet.size)


def main():
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(CFG, BACK)
    # the shared scene writes hero.png; keep the default (main) hero render intact
    hero = f"{BASE}/renders/hero.png"
    hero_bak = f"{OUT}/_hero_square_b.png"
    if os.path.exists(hero):
        shutil.copy(hero, hero_bak)
    failed = []
    for name, cols in VARIANTS.items():
        cfg = json.load(open(BACK))
        for k, v in cols.items():
            cfg["colors"][k]["base"] = v
        json.dump(cfg, open(CFG, "w"), indent=2)
        r = subprocess.run([BLENDER, "-b", "--python", f"{BASE}/build_scene.py"],
                           capture_output=True, text=True, env=CHILD_ENV)
        if r.returncode != 0:
            print("FAIL", name, r.stderr[-400:])
            failed.append(name)
            continue
        shutil.copy(f"{BASE}/renders/hero.png", f"{OUT}/{name}.png")
        print("OK", name)
    shutil.copy(BACK, CFG)
    if os.path.exists(hero_bak):
        shutil.copy(hero_bak, hero)
        os.remove(hero_bak)
    compose_sheet()
    print("DONE variants" + (" (failed: %s)" % failed if failed else ""))


if __name__ == "__main__":
    main()
