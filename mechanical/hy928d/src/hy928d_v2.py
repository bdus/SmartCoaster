#!/usr/bin/env python3
"""
HY928D 5 kg strain-gauge cell - v2, rebuilt from the supplier drawing + photos.

Source of truth:
  ref/hy928d/hy928d_size.webp   (34x34, 28x28, 4x3.1, d5, U-slot outline)
  ref/hy928d/hy928d_photo*.webp (through-slot, arch, tongue, chamfers)
  ref/hy928d/hy928d_param.webp  (range/thickness/sensitivity table)

Hard dimensions are from the drawing (34, 28, 3.1, 5, H=1.0).
The U-slot / arch / tongue curves are NOT dimensioned on the drawing; the
values below are measured from the orthographic drawing (pixel ratios) and
the photos, and are marked PROVISIONAL. Review before FEA.

Outputs: build/hy928d_v2.step, build/hy928d_v2.stl, build/params.json
"""

from __future__ import annotations

import json
from pathlib import Path

from build123d import *

# ---------------------------------------------------------------- parameters
PLATE = 34.0
CORNER_R = 3.0
T = 1.0
HOLE_D = 3.1
PITCH = 28.0
CENTER_D = 5.0
HOLE_CHAMFER = 0.5
EDGE_CHAMFER = 0.3

# U-slot (through-cut). Provisional from drawing/photo ratios.
U_OUT = 14.3          # outer half width
U_IN = 11.8           # inner half width  (= U_OUT - slot 2.5)
U_TOP = 9.6           # top end of the two side slots
U_OUT_BOT = -13.9     # outer bottom edge
U_IN_BOT = -11.4      # inner bottom edge
U_OUT_SHOULDER = -8.0
U_IN_SHOULDER = -6.5
U_OUT_R = 6.0
U_IN_R = 4.0

# arch slot above the d5 hole (separates tongue top from frame)
ARCH_R_IN = 5.0
INNER_SLOT_X = 6.6
INNER_SLOT_L = 12.0
INNER_SLOT_W = 2.5
ARCH_R_OUT = 8.2
ARCH_A0 = 25.0
ARCH_A1 = 155.0

# cable relief notch at the bottom edge
NOTCH_R = 2.5

# strain-gauge marker centres (drawing "+")
GAUGES = [(9.8, 7.0), (-9.8, 7.0), (15.5, 0.0), (-15.5, 0.0)]

PARAMS = {
    "plate_mm": PLATE, "corner_r_mm": CORNER_R, "thickness_mm": T,
    "hole_d_mm": HOLE_D, "hole_pitch_mm": PITCH, "center_d_mm": CENTER_D,
    "u_out_half_mm": U_OUT, "u_slot_width_mm": round(U_OUT - U_IN, 2),
    "u_top_mm": U_TOP, "u_out_bottom_mm": U_OUT_BOT,
    "u_outer_r_mm": U_OUT_R, "u_inner_r_mm": U_IN_R,
    "arch_r_in_mm": ARCH_R_IN, "arch_r_out_mm": ARCH_R_OUT,
    "arch_a0_deg": ARCH_A0, "arch_a1_deg": ARCH_A1,
    "notch_r_mm": NOTCH_R,
    "status": "U-slot/arch curves PROVISIONAL - confirm with supplier or section",
}


def u_face(half: float, top: float, side: float, bottom: float, radius: float):
    """U-shaped face: two vertical sides, flat bottom, rounded bottom corners."""
    with BuildSketch() as sk:
        with BuildLine():
            Polyline((-half, top), (-half, side))
            RadiusArc((-half, side), (-half + radius, bottom), -radius)
            Line((-half + radius, bottom), (half - radius, bottom))
            RadiusArc((half - radius, bottom), (half, side), -radius)
            Polyline((half, side), (half, top), (-half, top))
        make_face()
    return sk.sketch


def crescent(r_in: float, r_out: float, a0: float, a1: float):
    """Annular sector face, angles in degrees (open at the bottom)."""
    import math
    p0 = (r_out * math.cos(math.radians(a0)), r_out * math.sin(math.radians(a0)))
    p1 = (r_out * math.cos(math.radians(a1)), r_out * math.sin(math.radians(a1)))
    p2 = (r_in * math.cos(math.radians(a1)), r_in * math.sin(math.radians(a1)))
    p3 = (r_in * math.cos(math.radians(a0)), r_in * math.sin(math.radians(a0)))
    with BuildSketch() as sk:
        with BuildLine():
            CenterArc((0, 0), r_out, a0, a1 - a0)
            Line(p1, p2)
            CenterArc((0, 0), r_in, a1, a0 - a1)
            Line(p3, p0)
        make_face()
    return sk.sketch


def build():
    plate = extrude(RectangleRounded(PLATE, PLATE, CORNER_R), T)
    # edge break on the blank perimeter (avoids selecting cut edges later)
    plate = chamfer(plate.edges(), EDGE_CHAMFER)

    # U-shaped through slot (horseshoe, closed top ends)
    outer = u_face(U_OUT, U_TOP, U_OUT_SHOULDER, U_OUT_BOT, U_OUT_R)
    inner = u_face(U_IN, U_TOP, U_IN_SHOULDER, U_IN_BOT, U_IN_R)
    plate -= extrude(outer - inner, T)

    # crescent arch above the centre hole
    plate -= Pos(0, 0, -0.05) * extrude(
        crescent(ARCH_R_IN, ARCH_R_OUT, ARCH_A0, ARCH_A1), T + 0.1)

    # two vertical slots flanking the centre hole (inner beams)
    for sx in (-1, 1):
        plate -= Pos(sx * INNER_SLOT_X, 0.0, -0.05) * Rot(0, 0, 90) * \
            extrude(SlotOverall(INNER_SLOT_L, INNER_SLOT_W), T + 0.1)

    # centre hole
    plate -= Pos(0, 0, -0.05) * Cylinder(
        CENTER_D / 2, T + 0.1, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # 4 corner holes with a top countersink
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * PITCH / 2, sy * PITCH / 2
            plate -= Pos(x, y, -0.05) * Cylinder(
                HOLE_D / 2, T + 0.1,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
            plate -= Pos(x, y, T - HOLE_CHAMFER) * Cone(
                HOLE_D / 2, HOLE_D / 2 + HOLE_CHAMFER, HOLE_CHAMFER,
                align=(Align.CENTER, Align.CENTER, Align.MIN))

    # small notch at the tongue bottom (U inner bottom), as in the photo
    plate -= Pos(0, U_IN_BOT, -0.05) * Cylinder(
        NOTCH_R, T + 0.1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # cable exit notch at the TOP edge (photos show wires at the top)
    plate -= Pos(0, PLATE / 2, -0.05) * Cylinder(
        NOTCH_R, T + 0.1, align=(Align.CENTER, Align.CENTER, Align.MIN))

    return plate


def gauges():
    pads = []
    for x, y in GAUGES:
        pads.append(Pos(x, y, T) * Box(3.0, 3.0, 0.12,
                                       align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return Compound(children=pads)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "build"
    out.mkdir(parents=True, exist_ok=True)
    part = build()
    export_step(part, str(out / "hy928d_v2.step"))
    export_stl(part, str(out / "hy928d_v2.stl"), tolerance=0.01,
               angular_tolerance=0.05)
    export_stl(gauges(), str(out / "hy928d_v2_gauges.stl"), tolerance=0.02)
    (out / "params.json").write_text(json.dumps(PARAMS, indent=2), encoding="utf-8")
    bb = part.bounding_box()
    print(f"volume {part.volume:.2f} mm3  bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}")
    print(f"solids {len(part.solids())}  valid {part.is_valid}")
    print(f"STEP -> {out / 'hy928d_v2.step'}")
