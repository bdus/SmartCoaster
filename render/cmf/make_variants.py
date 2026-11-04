#!/usr/bin/env python3
"""Render the 4 CMF colorways with the existing square_b scene."""
import json
import os
import shutil
import subprocess

ROOT = "/data/Documents/projects/SmartCoaster"
BASE = f"{ROOT}/render/square_b"
CFG = f"{BASE}/config.json"
OUT = f"{ROOT}/render/cmf"
BACK = f"{OUT}/config_base.json"
BLENDER = "/data/Documents/tools/blender/blender"

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

os.makedirs(OUT, exist_ok=True)
shutil.copy(CFG, BACK)
for name, cols in VARIANTS.items():
    cfg = json.load(open(BACK))
    for k, v in cols.items():
        cfg["colors"][k]["base"] = v
    json.dump(cfg, open(CFG, "w"), indent=2)
    r = subprocess.run([BLENDER, "-b", "--python", f"{BASE}/build_scene.py"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL", name, r.stderr[-400:])
        continue
    shutil.copy(f"{BASE}/renders/hero.png", f"{OUT}/{name}.png")
    print("OK", name)
shutil.copy(BACK, CFG)
print("DONE variants")
