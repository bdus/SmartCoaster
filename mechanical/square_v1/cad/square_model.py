#!/usr/bin/env python3
"""
SmartCoaster V1 — square 100 x 100 x 18 mm smart coaster (build123d 0.10.x)

This is the *square* generation, kept separate from the round LUMEN project.
It follows the V1 mechanical brief and the M1.2 parameter manual:

  * 100 x 100 mm footprint, R8 corners, 18 mm total (base 14.5 + plate 3 + 0.5 gap)
  * HY928D 5 kg cell, four corner mounts, centre force, 0.5 mm overload stop
  * floating 100 x 100 x 3 top plate with a centring skirt + d6 force column
  * C-shaped main PCB 93.2 x 93.2 (central 38 x 38 opening, 90 deg front gap)
  * OLED window 18 x 7 at the front-right, round d8.2 button on the same line
  * USB-C on the rear edge, LiPo on the PCB, four PCB standoffs

Geometry lives only here; export/verify/agentcad entries are separate files.
All mm, origin at bottom centre, Z up, front = -Y.
"""

from __future__ import annotations

import math
from build123d import *

# =============================================================================
# 1. Parameter table
# =============================================================================
L = 100.0
W = 100.0
CORNER_R = 8.0

BASE_H = 14.5            # shell rim height
PLATE_T = 3.0
GAP = 0.5                # overload stop AND perimeter shadow line
PLATE_Z = BASE_H + GAP   # 15.0
TOTAL_H = PLATE_Z + PLATE_T  # 18.0

WALL = 2.4
FLOOR = 2.0
CAV = L - 2 * WALL       # 95.2
CAV_R = 6.0

# floating plate
SKIRT_OUT = 93.6
SKIRT_IN = 92.4
SKIRT_BOTTOM = 12.4
COL_R = 3.0
COL_BOTTOM = 6.0

# load cell
SENSOR = 34.0
SENSOR_H = 1.0
SENSOR_Z = 5.0
HOLE_D = 3.1
HOLE_PITCH = 28.0
CENTER_D = 5.0
CAV_LEN = 29.0
CAV_SLOT_W = 10.0
CAV_DEPTH = 0.7

# PCB
PCB = 93.2
PCB_R = 6.0
PCB_T = 1.6
PCB_Z = 5.0
PCB_SQ = 38.0
PCB_GAP_DEG = 80.0
PCB_HOLE_POS = ((40.0, 24.0), (-40.0, 24.0), (-40.0, -24.0), (40.0, -24.0))

# front controls (same horizontal line)
OLED_X, OLED_Z = 27.0, 7.2
WIN_W, WIN_H = 18.0, 7.0
BTN_X = 5.0
BTN_D = 8.2

# electronics
ESP_X, ESP_Y, ESP_Z = 18.0, 25.0, 2.5
ESP_POS = (30.0, 28.0)
HX_X, HX_Y, HX_Z = 12.0, 15.0, 1.6
HX_POS = (40.0, 0.0)
USBC_W, USBC_D, USBC_H = 8.94, 7.5, 3.26
BAT_X, BAT_Y, BAT_Z = 25.0, 30.0, 5.0
BAT_POS = (-32.0, 24.0)
OLED_MOD_W, OLED_MOD_H, OLED_MOD_T = 22.0, 8.0, 1.2

MATERIALS = {
    "shell":   ("PC/ABS + soft-touch", 1.15),
    "plate":   ("6063-T5 anodised Al", 2.70),
    "pcb":     ("FR-4 4-layer", 1.85),
    "sensor":  ("stainless steel", 7.90),
    "esp32":   ("module", 1.60),
    "hx711":   ("module", 1.60),
    "usbc":    ("connector", 7.00),
    "battery": ("LiPo pouch", 1.90),
    "oled":    ("OLED module", 1.80),
    "button":  ("PC + silicone", 1.20),
    "glass":   ("smoked PMMA 2H", 1.18),
    "pad":     ("silicone 50A", 1.15),
}

COLORS = {
    "shell":   "#EFEDE6",
    "plate":   "#C8CBCE",
    "pcb":     "#0E5A34",
    "sensor":  "#B8BEC5",
    "esp32":   "#20242A",
    "hx711":   "#1E3F6E",
    "usbc":    "#A7ADB4",
    "battery": "#C9C6BC",
    "oled":    "#15171A",
    "button":  "#E6E3DC",
    "glass":   "#2A2E35",
    "pad":     "#4A4C50",
}

CENTER = (Align.CENTER, Align.CENTER, Align.CENTER)
MINZ = (Align.CENTER, Align.CENTER, Align.MIN)


# =============================================================================
# 2. helpers
# =============================================================================
def sq_face(size: float, r: float) -> Sketch:
    return RectangleRounded(size, size, r)


def sq_ring(out_size: float, in_size: float, out_r: float, in_r: float,
            height: float, z: float = 0.0) -> Part:
    return Pos(0, 0, z) * (
        extrude(sq_face(out_size, out_r), height)
        - extrude(sq_face(in_size, in_r), height)
    )


def cyl(radius: float, height: float, z: float = 0.0):
    return Pos(0, 0, z) * Cylinder(radius, height, align=MINZ)


def rounded_box_y(w: float, d: float, h: float, r: float):
    b = Box(w, d, h)
    return fillet(b.edges().filter_by(Axis.Y), r)


def edges_at_z(shape, z: float, tol: float = 1e-6):
    return [e for e in shape.edges() if abs(e.center().Z - z) < tol]


def sector(r: float, a0: float, a1: float):
    p0 = (0.0, 0.0)
    p1 = (r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0)))
    p2 = (r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1)))
    return make_face(Polyline(p0, p1, p2, close=True))


def cyl_y(radius: float, length: float, x: float, y_front: float, z: float):
    """Cylinder along -Y, from y_front to y_front - length."""
    return Pos(x, y_front, z) * Rot(90, 0, 0) * Cylinder(
        radius, length, align=MINZ)


# =============================================================================
# 3. parts
# =============================================================================
def make_shell():
    body = extrude(sq_face(L, CORNER_R), BASE_H)
    body = fillet(edges_at_z(body, 0.0), 2.0)
    body = fillet(edges_at_z(body, BASE_H), 1.0)
    body -= Pos(0, 0, FLOOR) * extrude(sq_face(CAV, CAV_R),
                                       BASE_H - FLOOR + 1.0)

    # silicone gasket recess (1.2 deep ring)
    body -= Pos(0, 0, 0.0) * (extrude(sq_face(94.0, 7.0), 1.2)
                              - extrude(sq_face(80.0, 4.0), 1.2))

    # four cell bosses
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * HOLE_PITCH / 2, sy * HOLE_PITCH / 2
            body += Pos(x, y, FLOOR) * Cylinder(3.5, 3.0, align=MINZ)
            body -= Pos(x, y, 2.5) * Cylinder(1.05, 2.6, align=MINZ)
    body += cyl(6.0, 2.2, FLOOR)          # 0.8 mm below cell: rim stop engages first

    # four PCB standoffs
    for x, y in PCB_HOLE_POS:
        body += Pos(x, y, FLOOR) * Cylinder(3.25, 3.0, align=MINZ)
        body -= Pos(x, y, 2.5) * Cylinder(0.9, 2.6, align=MINZ)

    # front controls
    body -= Pos(OLED_X, -L / 2, OLED_Z) * rounded_box_y(WIN_W, 8.0, WIN_H, 2.0)
    body -= Pos(BTN_X, -L / 2, OLED_Z) * Rot(90, 0, 0) * \
        Cylinder(BTN_D / 2, 8.0)

    # rear USB-C
    body -= Pos(0, L / 2, 8.4) * rounded_box_y(9.2, 8.0, 3.3, 1.0)

    return body


def make_plate():
    plate = extrude(sq_face(L, CORNER_R), PLATE_T)
    plate = fillet(edges_at_z(plate, PLATE_T), 1.2)

    # fine etched frame groove, 8 mm in from the edge
    groove = extrude(sq_face(92.0, 6.0), 0.4) - \
        extrude(sq_face(91.2, 5.6), 0.4)
    plate -= Pos(0, 0, 2.8) * groove

    skirt = sq_ring(SKIRT_OUT, SKIRT_IN, 6.0, 6.0,
                    PLATE_Z - SKIRT_BOTTOM, SKIRT_BOTTOM - PLATE_Z)
    boss = cyl(8.0, 1.0, -1.0)
    column = cyl(COL_R, 8.0, -9.0)       # local -9 .. -1  ->  z 6 .. 14
    column = chamfer(
        column.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[0], 0.4)

    plate = plate + skirt + boss + column
    return Pos(0, 0, PLATE_Z) * plate


def make_load_cell():
    cell = extrude(RectangleRounded(SENSOR, SENSOR, 3.0), amount=SENSOR_H)
    slot = SlotOverall(CAV_LEN, CAV_SLOT_W)
    cell -= Pos(0, 0, SENSOR_H - CAV_DEPTH) * \
        extrude(slot, amount=CAV_DEPTH + 0.2)
    cell -= Pos(0, 0, -0.1) * Cylinder(CENTER_D / 2, SENSOR_H + 0.2,
                                       align=MINZ)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cell -= Pos(sx * HOLE_PITCH / 2, sy * HOLE_PITCH / 2, -0.1) * \
                Cylinder(HOLE_D / 2, SENSOR_H + 0.2, align=MINZ)
    return Pos(0, 0, SENSOR_Z) * cell


def make_pcb():
    board = sq_face(PCB, PCB_R) - Rectangle(PCB_SQ, PCB_SQ)
    board -= sector(80.0, 270 - PCB_GAP_DEG / 2, 270 + PCB_GAP_DEG / 2)
    pcb = extrude(board, PCB_T)
    for x, y in PCB_HOLE_POS:
        pcb -= Pos(x, y, -0.1) * Cylinder(1.2, PCB_T + 0.2, align=MINZ)
    return Pos(0, 0, PCB_Z) * pcb


def make_esp32():
    b = Box(ESP_X, ESP_Y, ESP_Z, align=MINZ)
    b = fillet(b.edges().filter_by(Axis.Z), 0.6)
    return Pos(ESP_POS[0], ESP_POS[1], 6.6) * b


def make_hx711():
    return Pos(HX_POS[0], HX_POS[1], 6.6) * Box(HX_X, HX_Y, HX_Z, align=MINZ)


def make_usbc():
    b = Box(USBC_W, USBC_D, USBC_H, align=MINZ)
    b = fillet(b.edges().filter_by(Axis.Y), 0.6)
    return Pos(0, L / 2 - 2.5 - USBC_D / 2, 6.6) * b


def make_battery():
    b = Box(BAT_X, BAT_Y, BAT_Z, align=MINZ)
    b = fillet(b.edges().filter_by(Axis.Z), 1.5)
    return Pos(BAT_POS[0], BAT_POS[1], 6.6) * b


def make_oled():
    return Pos(OLED_X, -L / 2 + 3.1, OLED_Z) * \
        Box(OLED_MOD_W, OLED_MOD_T, OLED_MOD_H)


def make_button():
    cap = cyl_y(BTN_D / 2 - 0.1, 2.5, BTN_X, -L / 2 + 2.5, OLED_Z)     # -50.0..-47.5
    flange = cyl_y(4.5, 0.8, BTN_X, -L / 2 + 3.2, OLED_Z)              # d9.0, clears skirt at full travel
    stem = cyl_y(2.0, 2.1, BTN_X, -L / 2 + 5.2, OLED_Z)                # -46.9..-44.8
    return cap + flange + stem


def make_glass():
    g = Box(WIN_W - 0.6, 2.2, WIN_H - 0.6)
    g = fillet(g.edges().filter_by(Axis.Y), 1.6)
    return Pos(OLED_X, -L / 2 + 1.1, OLED_Z) * g


def make_pad():
    pad = sq_ring(93.8, 80.0, 6.9, 4.0, 1.2, 0.0)
    pad = chamfer(edges_at_z(pad, 0.0), 0.3)
    return pad


PARTS = {
    "shell":   make_shell,
    "plate":   make_plate,
    "pcb":     make_pcb,
    "sensor":  make_load_cell,
    "esp32":   make_esp32,
    "hx711":   make_hx711,
    "usbc":    make_usbc,
    "battery": make_battery,
    "oled":    make_oled,
    "button":  make_button,
    "glass":   make_glass,
    "pad":     make_pad,
}


def build_assembly():
    parts, rows = {}, []
    for name, fn in PARTS.items():
        p = fn()
        p.color = Color(COLORS[name])
        parts[name] = p
        bb = p.bounding_box()
        dens = MATERIALS[name][1]
        rows.append({
            "name": name,
            "material": MATERIALS[name][0],
            "solids": len(p.solids()),
            "volume_mm3": round(p.volume, 2),
            "mass_g": round(p.volume / 1000.0 * dens, 2),
            "bbox": [round(bb.size.X, 3), round(bb.size.Y, 3),
                     round(bb.size.Z, 3)],
            "valid": p.is_valid() if callable(getattr(p, "is_valid", None)) else True,
        })
    assy = Compound(children=list(parts.values()))
    return assy, parts, rows
