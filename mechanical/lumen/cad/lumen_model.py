#!/usr/bin/env python3
"""
LUMEN - Smart Hydration Coaster / concept v1.0 (build123d 0.10.x)

A 110 mm round, 17 mm slim coaster that weighs every cup you set down and
tracks daily water intake.  The top plate floats on a 5 kg load cell and a
recessed light guide turns the 0.6 mm shadow gap into a 360 deg progress halo.

Architecture is inherited from the M1.2 parameter manual
(docs/恢复：智能杯垫工程（自包含参数手册）.md):
  * HY928D 34x34x1.0 strain-gauge cell, 4 corner mounts, centre force
  * unique load path: cup -> top plate -> force column -> cell centre ->
    strain beams -> corner bosses -> shell -> table (no bypass)
  * C-shaped main PCB coplanar with the cell, central 38x38 opening
  * FLOAT_GAP overload stop, ESP32-S3 + HX711 + USB-C + LiPo
Changes for v1.0: round 110 mm body, floating piston-skirt plate, 360 deg
light guide halo, 0.49" OLED behind a smoked curved lens, no mechanical
button (tap the plate to wake), removable plate for cleaning.

This module is the single source of truth for the geometry (no file I/O).
Render / export through:
    cad/export_v01.py          -> build/parts/*.step|stl + build/assembly/assembly_v01.step
    cad/lumen_assembly_v01.py  -> agentcad run entry (show_assembly)
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from build123d import *

# =============================================================================
# 1. Design table (mm, origin = bottom centre, Z up, front = -Y)
# =============================================================================

# ---- outer shell -----------------------------------------------------------
D_OUT = 110.0
R_OUT = D_OUT / 2.0          # 55.0
SHELL_H = 13.4               # top rim height
WALL = 2.4
R_IN = R_OUT - WALL          # 52.6 inner cavity radius
FLOOR = 2.0
RIM_FILLET = 1.6
BASE_FILLET = 3.0

# ---- bottom silicone pad ---------------------------------------------------
PAD_R_OUT = 50.0
PAD_R_IN = 39.0
PAD_T = 1.4

# ---- floating top plate ----------------------------------------------------
R_PLATE = 52.0
PLATE_T = 3.0
FLOAT_GAP = 0.6              # overload stop AND light slot
PLATE_Z = SHELL_H + FLOAT_GAP        # 14.0
PLATE_TOP = PLATE_Z + PLATE_T        # 17.0
SKIRT_R_OUT = 48.7
SKIRT_R_IN = 47.5
SKIRT_H = 3.0
SKIRT_GAP_DEG = 60.0         # C-skirt opening at the front (screen clearance)

# ---- light guide + LED flex ------------------------------------------------
GUIDE_R_OUT = 52.5
GUIDE_R_IN = 49.0
GUIDE_T = 1.2
GUIDE_Z = SHELL_H - GUIDE_T           # 12.2
LED_R = 51.0
LED_COUNT = 12

# ---- force path ------------------------------------------------------------
COL_R = 3.0                  # d6 force column
COL_BOTTOM = 6.0             # = sensor top face
BOSS_R = 8.0                 # d16 pad under the plate

# ---- HY928D load cell (drawing-derived, PROVISIONAL per M1.2) --------------
SENSOR_X = 34.0
SENSOR_Y = 34.0
SENSOR_H = 1.0
SENSOR_Z = 5.0
HOLE_D = 3.1
HOLE_PITCH = 28.0
CENTER_D = 5.0
CAV_LEN = 29.0
CAV_SLOT_W = 10.0
CAV_DEPTH = 0.7

# ---- main PCB --------------------------------------------------------------
PCB_R = 51.0
PCB_T = 1.6
PCB_Z = 5.0
PCB_SQ = 38.0                # central opening, clears 34x34 cell + 2 mm/side
PCB_GAP_DEG = 60.0           # C-gap at the front for OLED / display flex
PCB_HOLE_R = 45.0
PCB_HOLE_ANGLES = (15.0, 75.0, 195.0, 345.0)

# ---- electronics (representative envelopes) --------------------------------
ESP_X, ESP_Y, ESP_Z = 18.0, 25.0, 2.5       # ESP32-S3 module
ESP_R, ESP_ANG = 38.0, 45.0
HX_X, HX_Y, HX_Z = 12.0, 15.0, 1.6           # HX711
HX_R, HX_ANG = 40.0, 0.0
USBC_W, USBC_D, USBC_H = 8.94, 7.5, 3.26
USBC_Y = 48.7
BAT_X, BAT_Y, BAT_Z = 25.0, 30.0, 5.0        # 500 mAh LiPo
BAT_R, BAT_ANG = 32.0, 135.0
OLED_W, OLED_H, OLED_T = 14.6, 11.0, 1.2     # 0.49" 64x32 OLED
OLED_Y, OLED_Z, OLED_TILT = -48.6, 7.9, 20.0
GLASS_W, GLASS_H, GLASS_R = 11.6, 6.8, 3.0
WIN_W, WIN_H, WIN_R = 12.0, 7.2, 3.2

# ---- materials / densities (g/cm3) ----------------------------------------
MATERIALS = {
    "shell":   ("PC/ABS + soft-touch", 1.15),
    "plate":   ("6063-T5 anodised Al", 2.70),
    "guide":   ("PMMA light guide", 1.18),
    "ledflex": ("PET flex + LED", 1.30),
    "pcb":     ("FR-4 4-layer", 1.85),
    "sensor":  ("stainless steel", 7.90),
    "esp32":   ("module", 1.60),
    "hx711":   ("module", 1.60),
    "usbc":    ("connector", 7.00),
    "battery": ("LiPo pouch", 1.90),
    "oled":    ("OLED module", 1.80),
    "glass":   ("smoked PMMA 2H", 1.18),
    "pad":     ("silicone 50A", 1.15),
}

COLORS = {
    "shell":   "#EFEDE6",
    "plate":   "#C8CBCE",
    "guide":   "#EAF4FF",
    "ledflex": "#1E5B3B",
    "pcb":     "#0E5A34",
    "sensor":  "#B8BEC5",
    "esp32":   "#20242A",
    "hx711":   "#1E3F6E",
    "usbc":    "#A7ADB4",
    "battery": "#C9C6BC",
    "oled":    "#15171A",
    "glass":   "#2A2E35",
    "pad":     "#4A4C50",
}


# =============================================================================
# 2. Small geometry helpers
# =============================================================================

CENTER = (Align.CENTER, Align.CENTER, Align.CENTER)
MINZ = (Align.CENTER, Align.CENTER, Align.MIN)


def cyl(radius: float, height: float, z: float = 0.0):
    """Cylinder sitting on z = `z`."""
    return Pos(0, 0, z) * Cylinder(radius, height, align=MINZ)


def ring(r_out: float, r_in: float, height: float, z: float = 0.0):
    return cyl(r_out, height, z) - cyl(r_in, height, z)


def sector(r: float, a0: float, a1: float):
    """2-D pie slice from a0 to a1 degrees, apex at the origin."""
    p0 = (0.0, 0.0)
    p1 = (r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0)))
    p2 = (r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1)))
    return make_face(Polyline(p0, p1, p2, close=True))


def rounded_box_y(w: float, d: float, h: float, r: float):
    """Box rounded on the 4 edges parallel to Y (an XZ rounded rectangle)."""
    b = Box(w, d, h)
    return fillet(b.edges().filter_by(Axis.Y), r)


def circle_edges_at_z(shape, z: float, tol: float = 1e-4):
    return [
        e for e in shape.edges().filter_by(GeomType.CIRCLE)
        if abs(e.center().Z - z) < tol
    ]


# =============================================================================
# 3. Parts
# =============================================================================

def make_shell():
    """One-piece PC/ABS shell: floor, bosses, PCB standoffs, port cut-outs."""
    body = cyl(R_OUT, SHELL_H)

    # soft outer edges
    body = fillet(body.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[0],
                  BASE_FILLET)
    body = fillet(body.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1],
                  RIM_FILLET)

    # main cavity + bottom gasket recess
    body -= cyl(R_IN, SHELL_H - FLOOR + 1.0, FLOOR)
    body -= cyl(PAD_R_OUT + 0.2, PAD_T, 0.0)

    # 4 cell corner bosses (d7, M2.5 self-tap)
    for sx in (-1, 1):
        for sy in (-1, 1):
            body += Pos(sx * HOLE_PITCH / 2, sy * HOLE_PITCH / 2, FLOOR) * \
                Cylinder(3.5, 3.0, align=MINZ)
    # central over-load stop for the cell: 0.8 mm below the cell, so the
    # plate rim stop (0.6 mm) always engages first and cannot pre-load the cell
    body += cyl(6.0, 2.2, FLOOR)

    # 4 PCB standoffs (d7, M2 self-tap)
    for a in PCB_HOLE_ANGLES:
        x = PCB_HOLE_R * math.cos(math.radians(a))
        y = PCB_HOLE_R * math.sin(math.radians(a))
        body += Pos(x, y, FLOOR) * Cylinder(3.5, 3.0, align=MINZ)

    # pilots
    for sx in (-1, 1):
        for sy in (-1, 1):
            body -= Pos(sx * HOLE_PITCH / 2, sy * HOLE_PITCH / 2, 2.5) * \
                Cylinder(1.05, 2.6, align=MINZ)
    for a in PCB_HOLE_ANGLES:
        x = PCB_HOLE_R * math.cos(math.radians(a))
        y = PCB_HOLE_R * math.sin(math.radians(a))
        body -= Pos(x, y, 2.5) * Cylinder(0.9, 2.6, align=MINZ)

    # USB-C port: rounded opening in the rear wall
    body -= Pos(0, 53.0, 8.3) * rounded_box_y(9.4, 8.0, 3.6, 1.0)

    # OLED window: rounded opening in the front wall
    body -= Pos(0, -50.0, 8.0) * rounded_box_y(WIN_W, 20.0, WIN_H, WIN_R)

    return body


def make_plate():
    """Floating anodised plate + C-skirt + force column (local z=0 at underside)."""
    plate = cyl(R_PLATE, PLATE_T)

    # outer top round-over
    plate = fillet(plate.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1],
                   1.2)
    # shallow conical dish (0.6 mm deep over d96)
    plate -= Pos(0, 0, 2.4) * Cone(0.0, 48.0, 0.6)
    # finely engraved cup-alignment ring at d78
    plate -= Pos(0, 0, 2.80) * ring(39.125, 38.875, 0.30, 0.0)
    # light-catching chamfer on the bottom outer edge
    plate = chamfer(plate.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[0],
                    0.3)

    # C-shaped piston skirt (opens toward the display) - centres the plate
    skirt = ring(SKIRT_R_OUT, SKIRT_R_IN, SKIRT_H, -SKIRT_H)
    skirt -= Pos(0, 0, -SKIRT_H) * extrude(
        sector(60.0, 270 - SKIRT_GAP_DEG / 2, 270 + SKIRT_GAP_DEG / 2),
        SKIRT_H)

    # centre boss + force column down to the cell
    boss = cyl(BOSS_R, 1.0, -1.0)
    column = cyl(COL_R, 7.0, -8.0)                     # z -8 .. -1
    column = chamfer(
        column.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[0], 0.4)

    plate = plate + skirt + boss + column
    return Pos(0, 0, PLATE_Z) * plate


def make_guide():
    """PMMA light guide ring, flush with the shell rim, 12 LED pockets."""
    guide = ring(GUIDE_R_OUT, GUIDE_R_IN, GUIDE_T, GUIDE_Z)
    for i in range(LED_COUNT):
        a = i * 360.0 / LED_COUNT
        guide -= Rot(0, 0, a) * Pos(LED_R, 0, GUIDE_Z) * \
            Box(2.8, 2.8, 0.6, align=MINZ)
    tops = circle_edges_at_z(guide, SHELL_H)
    guide = chamfer(tops, 0.4)
    return guide


def make_led_flex():
    """12-LED flex ring, bonded under the light guide."""
    flex = ring(52.3, 49.5, 0.4, 11.8)
    for i in range(LED_COUNT):
        a = i * 360.0 / LED_COUNT
        flex += Rot(0, 0, a) * Pos(LED_R, 0, 12.2) * \
            Box(2.0, 1.6, 0.6, align=MINZ)
    return flex


def make_pcb():
    """C-shaped 4-layer main PCB, coplanar with the cell."""
    face = Circle(PCB_R) - Rectangle(PCB_SQ, PCB_SQ)
    face -= sector(60.0, 270 - PCB_GAP_DEG / 2, 270 + PCB_GAP_DEG / 2)
    pcb = extrude(face, PCB_T)
    for a in PCB_HOLE_ANGLES:
        x = PCB_HOLE_R * math.cos(math.radians(a))
        y = PCB_HOLE_R * math.sin(math.radians(a))
        pcb -= Pos(x, y, -0.1) * Cylinder(1.2, PCB_T + 0.2, align=MINZ)
    return Pos(0, 0, PCB_Z) * pcb


def make_load_cell():
    """HY928D 5 kg cell: 34x34x1.0, 4-R3, U-cavity, d5 centre (M1.2 geometry)."""
    plate = extrude(RectangleRounded(SENSOR_X, SENSOR_Y, 3.0), amount=SENSOR_H)
    slot = SlotOverall(CAV_LEN, CAV_SLOT_W)
    cavity = Pos(0, 0, SENSOR_H - CAV_DEPTH) * \
        extrude(slot, amount=CAV_DEPTH + 0.2)
    plate -= cavity
    plate -= Pos(0, 0, -0.1) * Cylinder(CENTER_D / 2, SENSOR_H + 0.2,
                                        align=MINZ)
    for sx in (-1, 1):
        for sy in (-1, 1):
            plate -= Pos(sx * HOLE_PITCH / 2, sy * HOLE_PITCH / 2, -0.1) * \
                Cylinder(HOLE_D / 2, SENSOR_H + 0.2, align=MINZ)
    return Pos(0, 0, SENSOR_Z) * plate


def make_esp32():
    b = Box(ESP_X, ESP_Y, ESP_Z, align=MINZ)
    b = fillet(b.edges().filter_by(Axis.Z), 0.6)
    return Pos(0, 0, 6.6) * Rot(0, 0, ESP_ANG) * Pos(ESP_R, 0, 0) * b


def make_hx711():
    return Pos(0, 0, 6.6) * Rot(0, 0, HX_ANG) * Pos(HX_R, 0, 0) * \
        Box(HX_X, HX_Y, HX_Z, align=MINZ)


def make_usbc():
    b = Box(USBC_W, USBC_D, USBC_H, align=MINZ)
    b = fillet(b.edges().filter_by(Axis.Y), 0.6)
    return Pos(0, USBC_Y, 6.6) * b


def make_battery():
    b = Box(BAT_X, BAT_Y, BAT_Z, align=MINZ)
    b = fillet(b.edges().filter_by(Axis.Z), 1.5)
    return Pos(0, 0, 6.6) * Rot(0, 0, BAT_ANG) * Pos(BAT_R, 0, 0) * b


def make_oled():
    return Pos(0, OLED_Y, OLED_Z) * Rot(-OLED_TILT, 0, 0) * \
        Box(OLED_W, OLED_T, OLED_H)


def make_glass():
    shell = Pos(0, 0, 8.0) * (Cylinder(R_OUT, 20.0) - Cylinder(R_OUT - 2.3, 20.0))
    blank = Pos(0, -50.0, 8.0) * rounded_box_y(GLASS_W, 20.0, GLASS_H, GLASS_R)
    return shell & blank


def make_pad():
    pad = ring(PAD_R_OUT, PAD_R_IN, PAD_T, 0.0)
    pad = chamfer(circle_edges_at_z(pad, 0.0), 0.4)
    return pad


# =============================================================================
# 4. Assembly
# =============================================================================

PARTS = {
    "shell":   make_shell,
    "plate":   make_plate,
    "guide":   make_guide,
    "ledflex": make_led_flex,
    "pcb":     make_pcb,
    "sensor":  make_load_cell,
    "esp32":   make_esp32,
    "hx711":   make_hx711,
    "usbc":    make_usbc,
    "battery": make_battery,
    "oled":    make_oled,
    "glass":   make_glass,
    "pad":     make_pad,
}


def project_root() -> Path:
    here = Path(__file__).resolve().parent
    for start in (here, Path.cwd()):
        for q in (start, *start.parents):
            if (q / "agentcad.json").exists():
                return q
    return here.parent


def build_assembly():
    parts, rows = {}, []
    for name, fn in PARTS.items():
        p = fn()
        p.color = Color(COLORS[name])
        parts[name] = p
        bb = p.bounding_box()
        vol = p.volume
        dens = MATERIALS[name][1]
        rows.append({
            "name": name,
            "material": MATERIALS[name][0],
            "solids": len(p.solids()),
            "volume_mm3": round(vol, 2),
            "mass_g": round(vol / 1000.0 * dens, 2),
            "bbox": [round(bb.size.X, 3), round(bb.size.Y, 3), round(bb.size.Z, 3)],
            "valid": p.is_valid() if callable(getattr(p, "is_valid", None)) else True,
        })
    assy = Compound(children=list(parts.values()))
    return assy, parts, rows
