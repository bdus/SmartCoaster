"""
Smart Coaster – square shell concept V0.1
Parametric starter model using build123d.

This is an EXTERNAL SHELL / packaging envelope study, not a production-ready
load-cell mechanism. HY928D dimensions are included as reference parameters.
Unknown force-transfer details are deliberately not modeled.

Run:
    python smart_coaster_shell_v01.py

Requires:
    pip install build123d

Outputs:
    smart_coaster_shell_v01.step
    smart_coaster_top_v01.stl
    smart_coaster_base_v01.stl
"""

from build123d import *

# -----------------------------
# Design parameters (millimetres)
# -----------------------------
BODY_X = 100.0             # provisional square footprint
BODY_Y = 100.0
CORNER_R = 8.0

BASE_HEIGHT = 15.0         # provisional; shell base only
BASE_FLOOR = 2.0
BASE_WALL = 2.4

TOP_THICKNESS = 3.0
TOP_EDGE_R = 1.0           # small edge softening, not the plan-view corner radius

# Front controls: front is Y = -BODY_Y/2.
# Small OLED window at front-right; circular button to its left, same height.
OLED_WINDOW_W = 18.0
OLED_WINDOW_H = 7.0
OLED_CENTER_X = 27.0
BUTTON_D = 8.2
BUTTON_CENTER_X = 5.0
CONTROL_CENTER_Z = 8.0
FRONT_CUT_DEPTH = BASE_WALL + 1.0

# HY928D 5 kg drawing-derived reference dimensions.
SENSOR_X = 34.0
SENSOR_Y = 34.0
SENSOR_THICKNESS = 1.0
SENSOR_HOLE_D = 3.1
SENSOR_HOLE_PITCH = 28.0
SENSOR_CENTRAL_MARK_D = 5.0  # drawing callout Ø5; mechanical meaning needs confirmation

# Packaging keepout around the sensor. This is a clearance envelope only,
# NOT a modeled mounting or load-transfer solution.
SENSOR_KEEP_OUT = 42.0

# -----------------------------
# Base shell
# -----------------------------
base_outer = extrude(
    RectangleRounded(BODY_X, BODY_Y, CORNER_R),
    amount=BASE_HEIGHT,
)

base_inner_profile = RectangleRounded(
    BODY_X - 2 * BASE_WALL,
    BODY_Y - 2 * BASE_WALL,
    max(0.5, CORNER_R - BASE_WALL),
)
base_inner = Pos(0, 0, BASE_FLOOR) * extrude(
    base_inner_profile,
    amount=BASE_HEIGHT - BASE_FLOOR + 0.2,
)
base = base_outer - base_inner

# OLED aperture on the front vertical wall (right-hand side of the front edge).
oled_cut = Pos(
    OLED_CENTER_X,
    -BODY_Y / 2,
    CONTROL_CENTER_Z,
) * Box(
    OLED_WINDOW_W,
    FRONT_CUT_DEPTH,
    OLED_WINDOW_H,
    align=(Align.CENTER, Align.MIN, Align.CENTER),
)
# The cut box extends inward from the front face.
# Box Y alignment MIN starts at y=-BODY_Y/2 and extends toward +Y.
base = base - oled_cut

# Circular button aperture. Cylinder is rotated so its axis is along Y.
button_cut = (
    Pos(BUTTON_CENTER_X, -BODY_Y / 2, CONTROL_CENTER_Z)
    * Rot(-90, 0, 0)
    * Cylinder(
        BUTTON_D / 2,
        FRONT_CUT_DEPTH,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
)
base = base - button_cut

# -----------------------------
# Floating top tray / top plate
# -----------------------------
top = Pos(0, 0, BASE_HEIGHT) * extrude(
    RectangleRounded(BODY_X, BODY_Y, CORNER_R),
    amount=TOP_THICKNESS,
)

# Gentle top perimeter edge treatment. Kept conservative for printability.
try:
    top_top_edges = top.edges().filter_by(Axis.Z, reverse=True)
    # Avoid aggressive edge selection in the starter model; the plan-view
    # rounded rectangle already defines the main visual language.
except Exception:
    pass

# -----------------------------
# Reference geometry (not included in production shell exports)
# -----------------------------
# HY928D plate footprint and four Ø3.1 mounting holes at ±14 mm.
sensor_ref = Pos(0, 0, BASE_FLOOR) * Box(
    SENSOR_X,
    SENSOR_Y,
    SENSOR_THICKNESS,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
)
for sx in (-SENSOR_HOLE_PITCH / 2, SENSOR_HOLE_PITCH / 2):
    for sy in (-SENSOR_HOLE_PITCH / 2, SENSOR_HOLE_PITCH / 2):
        hole = Pos(sx, sy, BASE_FLOOR - 0.1) * Cylinder(
            SENSOR_HOLE_D / 2,
            SENSOR_THICKNESS + 0.2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        sensor_ref = sensor_ref - hole

# Sensor reference is intentionally not fused to the base or top:
# actual support/strain/load path must follow the physical sensor construction.
assembly = Compound(children=[base, top])

# -----------------------------
# Export
# -----------------------------
export_step(assembly, "smart_coaster_shell_v01.step")
export_stl(top, "smart_coaster_top_v01.stl")
export_stl(base, "smart_coaster_base_v01.stl")

print("Exported shell concept V0.1")
print(f"Footprint: {BODY_X:.1f} x {BODY_Y:.1f} mm")
print(f"Overall nominal height: {BASE_HEIGHT + TOP_THICKNESS:.1f} mm")
print(f"HY928D reference: {SENSOR_X} x {SENSOR_Y} x {SENSOR_THICKNESS} mm")
