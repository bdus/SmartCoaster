#!/usr/bin/env python3
"""LUMEN round product render: per-part STL -> materials -> cameras.

blender -b --python render/lumen/build_scene.py
"""
import json
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = json.load(open(os.path.join(HERE, "config.json")))
OUT = os.path.join(HERE, "renders")
os.makedirs(OUT, exist_ok=True)

PARTS_ORDER = ["shell", "pcb", "sensor", "esp32", "hx711", "usbc", "battery",
               "glass", "oled", "guide", "ledflex", "pad", "plate"]


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
    sc.view_settings.exposure = -1.0
    return sc


def import_parts():
    objs = {}
    for name in PARTS_ORDER:
        if name == "sensor":
            path = os.path.join(ROOT, "mechanical", "hy928d", "build", "hy928d_v2.stl")
            zoff = 0.005
        else:
            path = os.path.join(ROOT, "mechanical", "lumen", "build", "parts",
                                name + "_v01.stl")
            zoff = 0.0
        if not os.path.exists(path):
            print("MISSING", path)
            continue
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for o in new:
            o.name = name
            o.location.z += zoff
        objs[name] = new
    return objs


def material(name, base, metallic=0.0, rough=0.5, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def apply_materials(objs, lo, hi, s):
    for name, lst in objs.items():
        if name == "guide":
            m = material("M_guide", (0.04, 0.16, 0.20), 0.0, 0.3,
                         emission=(0.15, 0.75, 1.0), strength=4.0)
        elif name == "ledflex":
            m = material("M_ledflex", (0.9, 0.95, 1.0), 0.0, 0.4,
                         emission=(0.85, 0.95, 1.0), strength=2.0)
        else:
            c = CFG["colors"][name]
            m = material("M_" + name, c["base"], c.get("metallic", 0), c.get("rough", 0.5))
        for o in lst:
            o.data.materials.clear()
            o.data.materials.append(m)
    # front OLED window
    k = (hi.x - lo.x) / 110.0
    img = bpy.data.images.load(os.path.join(HERE, "ui_lumen.png"))
    sm = bpy.data.materials.new("M_screen")
    sm.use_nodes = True
    nt = sm.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    em.inputs["Strength"].default_value = 2.5
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, lo.y - 0.0002, 8 * k),
                                     rotation=(math.radians(90), 0, 0))
    plane = bpy.context.object
    plane.name = "screen_ui"
    plane.scale = (11.6 * k, 6.8 * k, 1)
    plane.data.materials.append(sm)


def studio():
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "ground"
    g.data.materials.append(material("M_ground", (0.055, 0.055, 0.060), 0.0, 0.70))
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.035, 0.038, 0.045, 1)
    bg.inputs["Strength"].default_value = 0.6

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
    area("key", (0.24, -0.24, 0.33), (math.radians(55), 0, math.radians(45)), 0.38, 7.5)
    area("fill", (-0.30, -0.20, 0.20), (math.radians(70), 0, math.radians(-50)), 0.32, 2.6)
    area("rim", (0.02, 0.30, 0.24), (math.radians(110), 0, math.radians(180)), 0.30, 4.0,
         (0.75, 0.85, 1.0))


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


def render(sc, cam, path, w=1000, h=1000):
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("WROTE", path)


def main():
    sc = reset()
    objs = import_parts()
    mins, maxs = [], []
    for lst in objs.values():
        for o in lst:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mins.append(w); maxs.append(w)
    lo = Vector((min(v.x for v in mins), min(v.y for v in mins), min(v.z for v in mins)))
    hi = Vector((max(v.x for v in maxs), max(v.y for v in maxs), max(v.z for v in maxs)))
    print("bbox", lo[:], hi[:])
    apply_materials(objs, lo, hi, 1.0)
    studio()
    hero = camera("hero", (0.215, -0.255, 0.150), (0, 0, 0.008), 60)
    front = camera("front", (0, -0.340, 0.012), (0, 0, 0.008), 70)
    pcb = camera("pcb", (0.10, -0.13, 0.12), (0, 0, 0.006), 65)
    expl = camera("exploded", (0.22, -0.28, 0.13), (0, 0, 0.004), 55)
    render(sc, hero, os.path.join(OUT, "hero.png"))
    render(sc, front, os.path.join(OUT, "front.png"), 1200, 600)
    plate = bpy.data.objects.get("plate")
    if plate:
        plate.hide_render = True
    render(sc, pcb, os.path.join(OUT, "pcb_detail.png"), 1000, 800)
    if plate:
        plate.hide_render = False
    # exploded
    ground = bpy.data.objects.get("ground")
    if ground:
        ground.hide_render = True
    for name, off in CFG["exploded"].items():
        offv = Vector(off)
        for o in objs.get(name, []):
            o.matrix_world.translation = o.matrix_world.translation + offv
        if name == "shell":
            sui = bpy.data.objects.get("screen_ui")
            if sui:
                sui.location = sui.location + offv
    render(sc, expl, os.path.join(OUT, "exploded.png"), 1200, 1000)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "lumen.blend"))
    print("DONE")


if __name__ == "__main__":
    main()
