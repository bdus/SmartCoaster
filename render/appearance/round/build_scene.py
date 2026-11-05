#!/usr/bin/env python3
"""Round form study (appearance only) — LUMEN lineage, current function.

Proportions locked from the design brief:
  Ø110 × 17 mm, floating plate Ø104 × 3, 0.6 mm seam,
  flat top + 0.6 mm dish, front flat recess with 26×7 capsule window (left)
  and Ø8.2 button (right), no LED / no light guide.

This is a FORM STUDY for appearance decisions, not the final CAD. It is built
from primitives so proportions, CMF and the front panel can be iterated fast;
the production geometry will be rebuilt in build123d and re-verified before
freezing.

Run:
  /data/Documents/tools/blender/blender -b --python render/appearance/round/build_scene.py
Output:
  render/appearance/round/renders/{hero,front,top,detail}.png
"""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT_MODE = os.environ.get("SC_FRONT", "panel")   # panel | two
OUT = os.path.join(HERE, "renders" if FRONT_MODE == "panel" else f"renders_{FRONT_MODE}")
os.makedirs(OUT, exist_ok=True)

MM = 0.001
# ---- locked dimensions (mm) ----
D_OUT = 110.0
R_OUT = D_OUT / 2
SHELL_H = 13.4
FLOAT_GAP = 0.6
PLATE_R = 52.0
PLATE_T = 3.0
PLATE_Z = SHELL_H + FLOAT_GAP          # 14.0
PLATE_TOP = PLATE_Z + PLATE_T          # 17.0
PANEL_W, PANEL_H = 54.0, 9.6
PANEL_DEPTH = 4.5                      # recess at the widest point
PANEL_Z = 7.2
WIN_W, WIN_H, WIN_R = 26.0, 7.0, 3.5
WIN_X, WIN_DEPTH = -8.0, 2.0
BTN_D, BTN_X, BTN_PROUD = 8.2, 17.0, 0.4
DISH_D, DISH_DEPTH = 96.0, 0.6

# ---- CMF (solid warm-white line) ----
C_BODY = "#F1ECE1"
C_PLATE = "#F1ECE1"
C_BTN = "#F1ECE1"
GLASS = "#C8C8C8"
BG = (0.030, 0.032, 0.037)


def lin(h: str):
    c = [int(h.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = -0.9
    sc.unit_settings.system = "METRIC"
    return sc


def material(name, hexv, rough=0.5, metallic=0.0, emission=None, strength=0.0,
             transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*lin(hexv), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmission
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*lin(emission), 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def apply_mod(o, m):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)


def bevel(o, width_mm, segments=4, angle=30):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = width_mm * MM
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    apply_mod(o, m)


def bevel_loop(o, local_z_mm, width_mm, segments=4):
    """Bevel only the edge loop at a given local Z (mm)."""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    z = local_z_mm * MM
    edges = [e for e in bm.edges
             if all(abs(v.co.z - z) < 1e-7 for v in e.verts)]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=width_mm * MM,
                        segments=segments, affect="EDGES")
    bm.to_mesh(me)
    bm.free()


def smooth(o, angle=30):
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    tri = o.modifiers.new("tri", "TRIANGULATE")
    tri.keep_custom_normals = False
    apply_mod(o, tri)
    m = o.modifiers.new("split", "EDGE_SPLIT")
    m.split_angle = math.radians(angle)
    apply_mod(o, m)


def add_cyl(name, r_mm, h_mm, z_mm, verts=128, x=0.0, y=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r_mm * MM,
                                        depth=h_mm * MM,
                                        location=(x * MM, y * MM, z_mm * MM))
    o = bpy.context.object
    o.name = name
    return o


def rounded_box(name, w, d, h, r, loc):
    """Cube with rounded edges. w along X, d along Y, h along Z."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    o.scale = (w * MM, d * MM, h * MM)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(o, r, segments=6)
    o.location = (loc[0] * MM, loc[1] * MM, loc[2] * MM)
    return o


def capsule_profile(w, h, seg=32):
    """2D capsule outline in the XZ plane (x, z)."""
    r = h / 2.0
    cx = w / 2.0 - r
    pts = []
    for i in range(seg + 1):                      # right end, bottom -> top
        a = math.radians(-90 + 180 * i / seg)
        pts.append((cx + r * math.cos(a), r * math.sin(a)))
    for i in range(seg + 1):                      # left end, top -> bottom
        a = math.radians(90 + 180 * i / seg)
        pts.append((-cx + r * math.cos(a), r * math.sin(a)))
    return pts


def capsule_prism(name, w, h, thick, loc, mat=None):
    """Capsule outline in XZ, solidified along Y by `thick`."""
    pts = capsule_profile(w, h)
    verts = [(x * MM, 0.0, z * MM) for (x, z) in pts]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    sol = o.modifiers.new("sol", "SOLIDIFY")
    sol.thickness = thick * MM
    sol.offset = 0.0
    apply_mod(o, sol)
    o.location = (loc[0] * MM, loc[1] * MM, loc[2] * MM)
    if mat:
        o.data.materials.append(mat)
    return o


def cut(target, cutter):
    m = target.modifiers.new("cut", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = cutter
    m.solver = "EXACT"
    apply_mod(target, m)
    bpy.data.objects.remove(cutter, do_unlink=True)


def build():
    m_body = material("M_body", C_BODY, rough=0.62)
    m_plate = material("M_plate", C_PLATE, rough=0.60)
    m_btn = material("M_btn", C_BTN, rough=0.46)
    m_glass = material("M_glass", GLASS, rough=0.03, transmission=0.95)
    ui = bpy.data.images.load(os.path.join(os.path.dirname(HERE),
                                           "..", "..", "render", "square_b",
                                           "ui_screen.png"))

    # ---- shell ----
    body = add_cyl("shell", R_OUT, SHELL_H, SHELL_H / 2)
    bevel(body, 0.8, segments=4)
    # front control recess: one wide panel, or a screen flat + button pad
    screen_plane = -R_OUT + (PANEL_DEPTH if FRONT_MODE == "panel" else 3.2)
    if FRONT_MODE == "panel":
        cut(body, rounded_box("cut_panel", PANEL_W, 20.0, PANEL_H, 1.6,
                              (0, screen_plane - 10.0, PANEL_Z)))
    else:
        cut(body, rounded_box("cut_screen", 36.0, 20.0, 9.6, 1.5,
                              (WIN_X, screen_plane - 10.0, PANEL_Z)))
    # capsule window opening (cuts through the recess into the body)
    cut(body, capsule_prism("cut_win", WIN_W, WIN_H, 12.0,
                            (WIN_X, screen_plane - 1.0, PANEL_Z)))
    smooth(body)
    body.data.materials.append(m_body)

    # ---- plate ----
    plate = add_cyl("plate", PLATE_R, PLATE_T, PLATE_Z + PLATE_T / 2)
    bevel_loop(plate, PLATE_T / 2, 1.2, segments=5)
    bevel_loop(plate, -PLATE_T / 2, 0.3, segments=3)
    # shallow conical dish: cutter starts above the plate (no coplanar faces)
    cone = bpy.ops.mesh.primitive_cone_add(vertices=128, radius1=0.0,
                                           radius2=(DISH_D / 2) * 2 * MM,
                                           depth=DISH_DEPTH * 2 * MM,
                                           location=(0, 0, PLATE_TOP * MM))
    cutter = bpy.context.object
    cut(plate, cutter)
    smooth(plate)
    plate.data.materials.append(m_plate)

    # ---- screen glass + UI ----
    glass = capsule_prism("glass", WIN_W, WIN_H, 1.2,
                          (WIN_X, screen_plane + 0.6, PANEL_Z), m_glass)
    smooth(glass, 40)

    sm = bpy.data.materials.new("M_ui")
    sm.use_nodes = True
    nt = sm.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = ui
    em.inputs["Strength"].default_value = 3.0
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(WIN_X * MM,
                                                       (screen_plane + 1.3) * MM,
                                                       PANEL_Z * MM),
                                     rotation=(math.radians(90), 0, 0))
    ui_plane = bpy.context.object
    ui_plane.name = "screen_ui"
    ui_plane.scale = (WIN_W * MM, WIN_H * MM, 1)
    ui_plane.data.materials.append(sm)

    # ---- button (on a shallow pad in the two-flat variant) ----
    btn_y = (screen_plane - BTN_PROUD + 0.9) if FRONT_MODE == "panel" else -52.3
    if FRONT_MODE != "panel":
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=5.5 * MM,
                                            depth=1.0 * MM,
                                            location=(BTN_X * MM, -52.2 * MM,
                                                      PANEL_Z * MM),
                                            rotation=(math.radians(90), 0, 0))
        pad = bpy.context.object
        pad.name = "button_pad"
        bevel(pad, 0.3, segments=3)
        smooth(pad)
        pad.data.materials.append(m_body)

    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=BTN_D / 2 * MM,
                                        depth=1.8 * MM,
                                        location=(BTN_X * MM, btn_y * MM,
                                                  PANEL_Z * MM),
                                        rotation=(math.radians(90), 0, 0))
    btn = bpy.context.object
    btn.name = "button"
    bevel(btn, 0.35, segments=4)
    smooth(btn)
    btn.data.materials.append(m_btn)

    # ---- studio ----
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -0.0002))
    g = bpy.context.object
    g.name = "ground"
    g.data.materials.append(material("M_ground", "#171512", rough=0.66))

    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bgn = w.node_tree.nodes["Background"]
    bgn.inputs["Color"].default_value = (*BG, 1)
    bgn.inputs["Strength"].default_value = 0.55

    def area(name, loc, rot, size, power, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, "AREA")
        d.energy = power
        d.size = size
        d.color = color
        o = bpy.data.objects.new(name, d)
        bpy.context.scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot
        return o

    area("key", (0.22, -0.22, 0.32), (math.radians(55), 0, math.radians(45)), 0.36, 7.8)
    area("fill", (-0.30, -0.20, 0.20), (math.radians(70), 0, math.radians(-50)), 0.34, 2.8)
    area("rim", (0.02, 0.30, 0.24), (math.radians(110), 0, math.radians(180)), 0.32, 4.2,
         (0.78, 0.86, 1.0))
    area("top", (0.0, 0.02, 0.48), (0, 0, 0), 0.42, 3.0)

    def look_at(cam, target):
        d = Vector(target) - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    def camera(name, loc, target, lens):
        c = bpy.data.cameras.new(name)
        c.lens = lens
        c.sensor_width = 36
        o = bpy.data.objects.new(name, c)
        bpy.context.scene.collection.objects.link(o)
        o.location = loc
        look_at(o, target)
        return o

    sc = bpy.context.scene
    cams = {
        "hero": camera("hero", (0.19, -0.235, 0.145), (0, 0, 0.008), 62),
        "front": camera("front", (0, -0.34, 0.011), (0, 0, 0.008), 78),
        "top": camera("top", (0, 0.0001, 0.40), (0, 0, 0.008), 90),
        "detail": camera("detail", (0.050, -0.19, 0.045), (0, -0.040, 0.0072), 100),
    }
    sizes = {"hero": (1200, 1200), "front": (1400, 700),
             "top": (1200, 1200), "detail": (1200, 900)}
    for name, cam in cams.items():
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = sizes[name]
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("WROTE", sc.render.filepath)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, f"round_study_{FRONT_MODE}.blend"))


if __name__ == "__main__":
    reset()
    build()
    print("DONE")
