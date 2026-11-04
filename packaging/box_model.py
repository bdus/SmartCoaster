#!/usr/bin/env python3
"""SmartCoaster packaging (P3): 120x120x36 two-piece box + pulp insert + sleeve.

Box: base 120x120x20, lid 122x122x16 (1 mm overhang), 2 mm walls, R3 corners.
Insert: 116x116x6 molded pulp, 101x101x3 coaster recess + finger notch.
Card: 90x60x0.4 on top of the coaster. Sleeve: 124x124x38, 0.6 mm paper.
"""
import os

from build123d import (Align, Axis, Box, Pos, export_step, export_stl,
                       fillet)

W = D = 120.0
BASE_H = 20.0
LID_H = 16.0
WALL = 2.0
FLOOR = 2.0
OVER = 1.0
COASTER = 100.0
COASTER_H = 18.0
INSERT_H = 6.0
RECESS = 3.0


def box_base():
    o = Box(W, D, BASE_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    o = fillet(o.edges().filter_by(Axis.Z), 3.0)
    i = Pos(0, 0, FLOOR) * Box(W - 2 * WALL, D - 2 * WALL, BASE_H - FLOOR + 1,
                               align=(Align.CENTER, Align.CENTER, Align.MIN))
    return o - i


def box_lid():
    lw, ld = W + 2 * OVER, D + 2 * OVER
    o = Box(lw, ld, LID_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    o = fillet(o.edges().filter_by(Axis.Z), 3.0)
    i = Pos(0, 0, -1) * Box(lw - 2 * WALL, ld - 2 * WALL, LID_H - FLOOR + 1,
                            align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Pos(0, 0, BASE_H) * (o - i)


def box_insert():
    b = Box(W - 4, D - 4, INSERT_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    r = Box(COASTER + 1, COASTER + 1, RECESS, align=(Align.CENTER, Align.CENTER, Align.MIN))
    b -= Pos(0, 0, INSERT_H - RECESS) * r
    notch = Box(34, 12, INSERT_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    b -= Pos(0, -(D - 4) / 2, 0) * notch
    return Pos(0, 0, FLOOR) * b


def box_card():
    return Pos(0, 0, FLOOR + INSERT_H - RECESS + COASTER_H + 0.2) * Box(
        90, 60, 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN))


def box_sleeve():
    sw, sd = W + 2 * OVER + 2, D + 2 * OVER + 2
    sh = BASE_H + LID_H + 2
    o = Box(sw, sd, sh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    i = Box(sw - 1.2, sd - 1.2, sh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Pos(0, 0, -1) * (o - i)


PARTS = {"box_base": box_base, "box_lid": box_lid, "box_insert": box_insert,
         "box_card": box_card, "box_sleeve": box_sleeve}

if __name__ == "__main__":
    os.makedirs("build", exist_ok=True)
    for name, fn in PARTS.items():
        p = fn()
        export_step(p, f"build/{name}.step")
        export_stl(p, f"build/{name}.stl")
        bb = p.bounding_box()
        print(f"{name:12s} vol {p.volume:9.1f} mm3  bbox {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}")
