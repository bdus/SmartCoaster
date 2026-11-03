"""
Smart Coaster – interior packaging study V0.1

Visualises the interior packaging envelope WITHOUT fusing components:
  - central HY928D keepout zone (42 x 42 mm)
  - wrap-around PCB ring (annulus R21 -> R47.6) shown as a thin ring at floor level
  - front control apertures (OLED + button) on the base wall

The ring / keepout are REFERENCE ONLY (transparent concept), not mounted parts.
This is packaging space determination, not the load-cell mechanism.

Run:  .venv/bin/python cad/smart_coaster_packaging_v01.py
Outputs: build/packaging/packaging_v01.step + preview STLs
"""

import os
from build123d import *

# ---------------- shared params (mirror shell v01) ----------------
BODY_X = 100.0
BODY_Y = 100.0
CORNER_R = 8.0
BASE_HEIGHT = 15.0
BASE_FLOOR = 2.0
BASE_WALL = 2.4
TOP_THICKNESS = 3.0

OLED_WINDOW_W = 18.0
OLED_WINDOW_H = 7.0
OLED_CENTER_X = 27.0
BUTTON_D = 8.2
BUTTON_CENTER_X = 5.0
CONTROL_CENTER_Z = 8.0
FRONT_CUT_DEPTH = BASE_WALL + 1.0

# HY928D packaging keepout (provisional, from shell v01)
SENSOR_KEEP_OUT = 42.0
SENSOR_H = 1.0

# Wrap-around PCB ring (annulus) reference
PCB_RING_R_IN = SENSOR_KEEP_OUT / 2  # 21.0
PCB_RING_R_OUT = (BODY_X - 2 * BASE_WALL) / 2  # 47.6
PCB_RING_THICK = 1.6

# ---------------- base shell (same as v01) ----------------
def base_shell():
    outer = extrude(RectangleRounded(BODY_X, BODY_Y, CORNER_R), amount=BASE_HEIGHT)
    inner = Pos(0, 0, BASE_FLOOR) * extrude(
        RectangleRounded(BODY_X - 2 * BASE_WALL, BODY_Y - 2 * BASE_WALL, max(0.5, CORNER_R - BASE_WALL)),
        amount=BASE_HEIGHT - BASE_FLOOR + 0.2,
    )
    b = outer - inner
    oled = Pos(OLED_CENTER_X, -BODY_Y / 2, CONTROL_CENTER_Z) * Box(
        OLED_WINDOW_W, FRONT_CUT_DEPTH, OLED_WINDOW_H,
        align=(Align.CENTER, Align.MIN, Align.CENTER),
    )
    b = b - oled
    btn = (Pos(BUTTON_CENTER_X, -BODY_Y / 2, CONTROL_CENTER_Z)
           * Rot(-90, 0, 0)
           * Cylinder(BUTTON_D / 2, FRONT_CUT_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    b = b - btn
    return b

# ---------------- top tray ----------------
def top_tray():
    return Pos(0, 0, BASE_HEIGHT) * extrude(
        RectangleRounded(BODY_X, BODY_Y, CORNER_R), amount=TOP_THICKNESS)

# ---------------- reference zones (NOT fused) ----------------
# Central keepout block (concept only)
keepout = Pos(0, 0, BASE_FLOOR) * Box(
    SENSOR_KEEP_OUT, SENSOR_KEEP_OUT, 0.6,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
)

# Wrap-around PCB ring: annulus (torus-flattened) at floor level.
# Build as two boxes + circle subtraction for a square-with-rounded ring look:
# simpler: a ring plate = outer rounded square minus inner rounded square.
ring_outer = RectangleRounded(
    PCB_RING_R_OUT * 2, PCB_RING_R_OUT * 2, max(0.5, CORNER_R - 0.0))
ring_inner = RectangleRounded(
    PCB_RING_R_IN * 2, PCB_RING_R_IN * 2, max(0.5, 6.0))
pcb_ring = Pos(0, 0, BASE_FLOOR) * extrude(ring_outer - ring_inner, amount=PCB_RING_THICK)

# Reference sensor plate (drawing-derived, not load path)
sensor_ref = Pos(0, 0, BASE_FLOOR) * Box(
    34.0, 34.0, SENSOR_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
for sx in (-14.0, 14.0):
    for sy in (-14.0, 14.0):
        hole = Pos(sx, sy, BASE_FLOOR - 0.1) * Cylinder(
            3.1 / 2, SENSOR_H + 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        sensor_ref = sensor_ref - hole

base = base_shell()
top = top_tray()

# Reference zones (keepout + ring + sensor) as separate solids for visual study
zones = Compound(children=[keepout, pcb_ring, sensor_ref])

# Export
outdir = os.path.join(os.path.dirname(__file__), "..", "build", "packaging")
os.makedirs(outdir, exist_ok=True)
step_path = os.path.join(outdir, "packaging_v01.step")
stl_top = os.path.join(outdir, "packaging_top_v01.stl")
stl_base = os.path.join(outdir, "packaging_base_v01.stl")
zones_step = os.path.join(outdir, "packaging_zones_v01.step")

assembly = Compound(children=[base, top])
export_step(assembly, step_path)
export_step(zones, zones_step)
export_stl(top, stl_top)
export_stl(base, stl_base)
print("Exported packaging study V0.1")
print(f"STEP: {step_path}")
print(f"Zones STEP (keepout+ring+sensor ref): {zones_step}")
print(f"Interior: {BODY_X - 2 * BASE_WALL:.1f} x {BODY_Y - 2 * BASE_WALL:.1f} mm, height {BASE_HEIGHT - BASE_FLOOR:.1f} mm")
print(f"PCB ring: R{PCB_RING_R_IN:.1f} -> R{PCB_RING_R_OUT:.1f} mm (radial ~{PCB_RING_R_OUT - PCB_RING_R_IN:.1f} mm)")
