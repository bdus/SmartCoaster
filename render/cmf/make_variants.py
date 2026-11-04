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

VARIANTS = {
    "lumen_violet": {"plate": [0.42, 0.25, 0.63], "shell": [0.16, 0.18, 0.21],
                     "button": [0.42, 0.25, 0.63]},
    "moss":         {"plate": [0.31, 0.42, 0.29], "shell": [0.17, 0.19, 0.17],
                     "button": [0.31, 0.42, 0.29]},
    "sand":         {"plate": [0.79, 0.72, 0.60], "shell": [0.23, 0.21, 0.19],
                     "button": [0.79, 0.72, 0.60]},
    "graphite":     {"plate": [0.23, 0.24, 0.26], "shell": [0.11, 0.12, 0.14],
                     "button": [0.58, 0.16, 0.15]},
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
