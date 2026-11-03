"""
HY928D 5kg load cell - real 3D geometry v0.2 (rebuilt from drawing).

Engineering drawing (cad_HY928D.jpeg / HY928D.txt) shows a flat load cell plate:
  - square plate 34 x 34 mm, thickness H = 1.0 mm (5kg spec)
  - 4 x mounting through-holes d=3.1 at +-14 (pitch 28 x 28)
  - CENTRAL MACHINED CAVITY (the strain region). Section view shows a
    U-shaped recess (slot with arc/round base) cut into the plate.
  - central hole d=5 in the cavity base (load pin / alignment)
  - 2-R9 fillets at the two cavity inner ends; 4-R3 fillets on outer bottom
  - '+' marks at cavity inner+outer walls = strain-gauge patch positions
    (full-bridge on parallel beams)

This is the load cell BODY. The central recess leaves two parallel beams that
flex under centre load (classic flat parallel-beam cell). Recess/beam dims are
interpreted from the 34 = 2.5+2.5+10+2.5+2.5 chain and are PROVISIONAL.

Run: .venv/bin/python cad/hy928d_real_v01.py
Outputs: build/hy928d/hy928d_real_v01.step + stl
"""

import os
from build123d import *

# ---------- drawing-derived parameters ----------
SENSOR_X = 34.0
SENSOR_Y = 34.0
SENSOR_H = 1.0          # 5kg spec
HOLE_D = 3.1
HOLE_PITCH = 28.0       # center-to-center (+-14)
CENTER_D = 5.0          # central hole in cavity base

# Central cavity (strain region). Dimension chain along top edge:
#   2.5 | 2.5 | 10 | 2.5 | 2.5  = 34
# Interpretation (PROVISIONAL):
#   outer margin to cavity edge .... 2.5
#   beam width (material left) ...... 2.5
#   central slot width .............. 10
#   (mirrored on other side)
# So cavity outer width = 34 - 2*2.5 = 29, slot width 10, beam 2.5 each side.
CAV_LEN = 34.0 - 2 * 2.5          # cavity overall length along the beam axis = 29
CAV_SLOT_W = 10.0                 # central slot width (between beams)
BEAM_W = 2.5                      # each parallel beam width
CAV_DEPTH = 0.7                   # recess depth from top face (PROVISIONAL, 0.3 bottom web)

# cavity inner-end fillets 2-R9 (cavity wall/base transition radius)
R_INNER = 9.0

# ---------- build ----------
# Outer plate 34x34. Drawing: 4-R3 on outer bottom corners (NOT R9).
# The 2-R9 are the INNER cavity fillets (cavity wall/base transition).
# Plan corner radius uses R3 to match the 4-R3 outer corner callout.
plate = extrude(RectangleRounded(SENSOR_X, SENSOR_Y, 3.0), amount=SENSOR_H)

# Central cavity: recess from the TOP face, U-shaped (rounded ends).
# Cavity profile = overall rect (29 long) minus the two beams (2.5 wide) that
# remain at the sides, i.e. the removed material is a central slot 10 wide
# with rounded ends, leaving beams at +/- side.
# Build cavity as a rounded slot (pill) of width CAV_SLOT_W, length CAV_LEN.
slot = SlotOverall(CAV_LEN, CAV_SLOT_W)  # capsule slot (rounded ends = U base arc)
cavity = Pos(0, 0, SENSOR_H - CAV_DEPTH) * extrude(slot, amount=CAV_DEPTH + 0.2)
plate = plate - cavity

# central d5 through hole in cavity base
center_hole = Pos(0, 0, -0.1) * Cylinder(
    CENTER_D / 2, SENSOR_H + 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
plate = plate - center_hole

# 4 x mounting through-holes
for sx in (-HOLE_PITCH / 2, HOLE_PITCH / 2):
    for sy in (-HOLE_PITCH / 2, HOLE_PITCH / 2):
        hole = Pos(sx, sy, -0.1) * Cylinder(
            HOLE_D / 2, SENSOR_H + 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        plate = plate - hole

# ---------- export ----------
outdir = os.path.join(os.path.dirname(__file__), "..", "build", "hy928d")
os.makedirs(outdir, exist_ok=True)
step_path = os.path.join(outdir, "hy928d_real_v01.step")
stl_path = os.path.join(outdir, "hy928d_real_v01.stl")

export_step(plate, step_path)
export_stl(plate, stl_path)

print("Exported HY928D real geometry V0.2 (central U-cavity parallel-beam)")
print(f"Plate: {SENSOR_X} x {SENSOR_Y} x {SENSOR_H} mm")
print(f"Holes: 4 x d{HOLE_D} @ pitch {HOLE_PITCH}; centre d{CENTER_D}")
print(f"Cavity: L{CAV_LEN} slotW{CAV_SLOT_W} beamW{BEAM_W} depth{CAV_DEPTH} (PROVISIONAL)")
print(f"STEP: {step_path}")
print("NOTE: cavity dims/beam width PROVISIONAL pending supplier section.")
