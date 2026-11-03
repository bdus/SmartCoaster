"""
Smart Coaster - wrap-around (C-ring) PCB layout study V0.1

A C-shaped PCB (inner cavity MINUS the central sensor keepout) that wraps
around the HY928D, fitting the full inner floor inside the base.

Design points:
  - outer profile follows the inner wall (R47.6 = 95.2/2); keep 1mm margin
  - central SQUARE opening 38x38 matches the 34x34 SQUARE sensor (2mm/side gap);
    NOT a circle - PCB is coplanar with the sensor on the same boss layer
  - C-gap opens toward the FRONT (y=-50) where the button/OLED live,
    leaving room for control wiring + USB-C on the front wall
  - ESP32-S3 does NOT fit in a thin ring band (max square ~13.2mm),
    so the board keeps the corner quadrants as a C-shaped plate
  - component footprints (provisional):
      ESP32-S3 module ~18 x 25 mm (rear-right corner)
      HX711 amplifier ~12 x 15 mm (right ring band)
      USB-C receptacle 8.94 x 7.5 mm (front-right ring)
      battery ~25 x 30 x 5 mm (rear-left floor; 40x40 does not fit)
  - board thickness 1.6 mm, coplanar with HY928D at z = 5.0 (on the same bosses)

This is a BOARD LAYOUT study (placement/keepout), not a routed PCB.
The board is shown as a solid C-shaped plate; component boxes are reference.

Run: .venv/bin/python cad/pcb_ring_v01.py
Outputs: build/pcb_ring/pcb_ring_v01.step + stl
"""

import os
from build123d import *

# ---------- board geometry ----------
# The board is the inner cavity MINUS the central sensor keepout: a C-shaped
# plate (ring + full corner quadrants) rather than a thin annulus. This is
# needed because ESP32-S3 (18x25) does NOT fit in a thin R27..R46.6 annulus
# (max square side ~13.2mm).
#   outer profile = inner wall rounded-square, 1mm margin
#   inner hole    = SQUARE 38x38 (matches the 34x34 SQUARE HY928D, 2mm/side gap;
#                   NOT a circle - sensor is square, PCB is coplanar with it)
#   front C-gap   = 70 deg opening toward front for controls/wiring
SQ_IN = 38.0            # central square opening: clears 34x34 sensor + 2mm/side
R_OUT = 47.6 - 1.0      # outer profile follows inner wall, 1mm margin
PCB_T = 1.6
PCB_Z = 5.0             # coplanar with HY928D (sensor bottom at z=5.0, on bosses)

# C-gap: opening angle toward front (y = -R_OUT side).
GAP_HALF = 35.0

# outer profile corner radius (match base inner rounded square)
OUTER_R = 6.0

# ---------- build C-shaped board ----------
def c_ring():
    # Outer profile: rounded-square matching the inner cavity (1mm margin).
    # 93.2 x 93.2 rounded square (inner wall 95.2 minus 2*1.0 margin)
    outer_profile = RectangleRounded(
        (R_OUT * 2), (R_OUT * 2), OUTER_R)
    # Inner opening: SQUARE 38x38 matching the 34x34 SQUARE sensor (2mm/side gap)
    inner_hole = Rectangle(SQ_IN, SQ_IN)
    board_face = outer_profile - inner_hole
    # Front C-gap: remove a 70-deg wedge at the front (-Y, angle 270)
    import math as m
    a = m.radians(GAP_HALF)
    L = R_OUT + 10
    p1 = (L * m.cos(3*m.pi/2 - a), L * m.sin(3*m.pi/2 - a))  # 270-a
    p2 = (L * m.cos(3*m.pi/2 + a), L * m.sin(3*m.pi/2 + a))  # 270+a
    wedge = Polygon((0, 0), p1, p2)
    board_face = board_face - wedge
    return extrude(board_face, amount=PCB_T)

# ---------- component reference boxes (provisional placement) ----------
# Layout on the C-shaped board (full cavity minus R27 sensor hole):
#   ESP32-S3  -> rear-right quadrant tab (big module needs the open corner)
#   HX711     -> right side of the ring band
#   USB-C     -> front-right, near the C-gap edge, facing front-right wall
#   battery   -> 25x30 pack on the rear-left floor (40x40 / 30x20 do not fit)
def component_refs():
    comps = []
    # ESP32-S3 module (18x25): rear-right corner, center (32, 31)
    #   (35,34) poked the outer profile corner; (32,31) keeps all corners in-board
    comps.append(Pos(32, 31, PCB_Z) * Box(18, 25, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    # HX711 (12x15): right side ring, center (36, 0)
    comps.append(Pos(36, 0, PCB_Z) * Box(12, 15, 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    # USB-C receptacle: front-right on ring, r40 @ 320 deg
    #   (305 deg corner landed inside the front C-gap wedge; 320 clears it)
    import math as _m
    _a = _m.radians(320.0)
    _r = 40.0
    _ux = _r * _m.cos(_a)
    _uy = _r * _m.sin(_a)
    comps.append(Pos(_ux, _uy, PCB_Z) * Box(8.94, 7.5, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    # battery: 25x30x5 pack on top of the PCB, rear-left band.
    #   PCB is now coplanar with the sensor (z=5.0), so the floor underneath is
    #   occupied by the board; battery rides on the board top (z=6.6).
    #   (30x20/40x40 did not fit the band quadrant)
    comps.append(Pos(-32, 24, PCB_Z + PCB_T) * Box(25, 30, 5.0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return comps

pcb = c_ring()
comps = component_refs()

outdir = os.path.join(os.path.dirname(__file__), "..", "build", "pcb_ring")
os.makedirs(outdir, exist_ok=True)

assembly = Compound(children=[pcb] + comps)
export_step(assembly, os.path.join(outdir, "pcb_ring_v01.step"))
export_stl(pcb, os.path.join(outdir, "pcb_ring_board_v01.stl"))
for i, c in enumerate(comps):
    export_stl(c, os.path.join(outdir, f"pcb_ring_comp{i}_v01.stl"))
print("Exported wrap-around C-ring PCB layout study V0.1")
print(f"Board: C-shaped plate, central SQUARE {SQ_IN:.1f}x{SQ_IN:.1f} (clears 34x34 sensor +2mm/side), outer -1.0, t {PCB_T}")
print(f"PCB coplanar with HY928D at z={PCB_Z:.1f}; C-gap half-angle {GAP_HALF} deg (open toward front)")
print("Component refs: ESP32-S3 (rear-right), HX711 (right), USB-C (front-right), battery 25x30 (rear-left floor)")
