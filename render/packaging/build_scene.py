#!/usr/bin/env python3
"""Packaging renders (P3): closed box, open box with coaster, insert detail.

Coaster has no LED / emissive part (removed 2026-11-04): only the 26x7 screen
window + button on the front face.

Run:
  blender -b --python render/packaging/build_scene.py
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = "/data/Documents/projects/SmartCoaster"
OUT = f"{ROOT}/render/packaging/renders"
BOX = f"{ROOT}/packaging/build"
COASTER = f"{ROOT}/mechanical/square_v1/build/parts"
SCALE = 0.001


def lin(h):
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(os.environ.get("SC_SAMPLES", "96"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1000
    sc.render.resolution_y = 1000
    sc.render.film_transparent = False
    sc.view_settings.look = "AgX - Medium High Contrast"
    return sc


def imp(path):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.object
    o.scale = (SCALE, SCALE, SCALE)
    return o


def material(name, base, rough, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = rough
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def apply(parts):
    mats = {
        "box_base": material("paper_cream", lin("EDE6D6"), 0.55),
        "box_lid": material("paper_cream2", lin("EDE6D6"), 0.55),
        "box_insert": material("pulp", lin("D8CCB4"), 0.9),
        "box_sleeve": material("sleeve_violet", lin("6B40A0"), 0.5),
        "box_card": material("card_white", lin("F4F2EC"), 0.45),
        "plate": material("plate_violet", lin("6B40A0"), 0.42),
        "shell": material("shell_charcoal", lin("2A2E35"), 0.55),
        "button": material("button_violet", lin("6B40A0"), 0.25),
        "glass": material("glass_smoked", lin("20242A"), 0.15),
        "pad": material("pad_silicone", lin("3A3F48"), 0.85),
        "pcb": material("pcb", lin("1B3A2A"), 0.6),
        "sensor": material("cell", lin("9AA0A8"), 0.4),
        "esp32": material("esp32", lin("2A2E35"), 0.7),
        "hx711": material("hx711", lin("1A1D22"), 0.6),
        "usbc": material("usbc", lin("8A8F98"), 0.3),
        "battery": material("battery", lin("3A3F48"), 0.7),
        "oled": material("oled", lin("101216"), 0.3),
    }
    for name, o in parts.items():
        o.data.materials.clear()
        o.data.materials.append(mats[name])
    return mats


def studio():
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.04, 0.05, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    for name, loc, rot, size, power, col in [
        ("key", (0.30, -0.30, 0.45), (math.radians(50), 0, math.radians(45)), 0.5, 8.0, (1, 1, 1)),
        ("fill", (-0.35, -0.20, 0.25), (math.radians(65), 0, math.radians(-50)), 0.4, 2.5, (1, 1, 1)),
        ("rim", (0.0, 0.40, 0.30), (math.radians(110), 0, math.radians(180)), 0.4, 4.0, (0.8, 0.85, 1.0)),
    ]:
        d = bpy.data.lights.new(name, "AREA")
        d.energy = power
        d.size = size
        d.color = col
        o = bpy.data.objects.new(name, d)
        bpy.context.scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0))
    g = bpy.context.object
    g.data.materials.append(material("ground", (0.09, 0.09, 0.10), 0.6))


def camera(loc, target, lens):
    c = bpy.data.cameras.new("cam")
    c.lens = lens
    c.sensor_width = 36
    o = bpy.data.objects.new("cam", c)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(sc, cam, path, w=1000, h=1000):
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("WROTE", path)


def main():
    sc = reset()
    parts = {}
    for n in ("box_base", "box_lid", "box_insert", "box_card", "box_sleeve"):
        parts[n] = imp(f"{BOX}/{n}.stl")
    for n in ("shell", "plate", "pcb", "sensor", "esp32", "hx711", "usbc",
              "battery", "oled", "button", "glass", "pad"):
        o = imp(f"{COASTER}/{n}_v01.stl")
        o.location.z += 0.005
        parts[n] = o
    apply(parts)
    studio()
    os.makedirs(OUT, exist_ok=True)
    closed = camera((0.20, -0.26, 0.20), (0, 0, 0.018), 62)
    render(sc, closed, f"{OUT}/closed.png")
    # open: hide sleeve + card? keep card; lift lid
    parts["box_sleeve"].hide_render = True
    lid = parts["box_lid"]
    lid.location = (0.13, 0.10, 0.055)
    open_cam = camera((0.24, -0.28, 0.26), (0.01, 0.01, 0.022), 55)
    render(sc, open_cam, f"{OUT}/open.png")
    # insert detail: overhead
    lid.hide_render = True
    top = camera((0.0, -0.005, 0.40), (0, 0, 0.02), 70)
    render(sc, top, f"{OUT}/insert.png")
    print("DONE packaging")


if __name__ == "__main__":
    main()
