#!/usr/bin/env python3
"""Square V1-B product render: GLB parts -> materials -> lights -> cameras.

Run:
  blender -b --python render/square_b/build_scene.py
Outputs (render/square_b/renders/): hero.png, front.png, exploded.png
The .blend is saved for re-rendering / tweaking.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = json.load(open(os.path.join(HERE, "config.json")))
PARTS = os.path.join(ROOT, CFG["parts_dir"])
OUT = os.path.join(HERE, "renders")
os.makedirs(OUT, exist_ok=True)

PARTS_ORDER = ["shell", "pcb", "sensor", "esp32", "hx711", "usbc",
               "battery", "oled", "button", "glass", "pad", "light_guide", "plate"]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1000
    sc.render.resolution_y = 1000
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = -1.0
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def import_parts():
    """Per-part STL (mm) at their world positions; STL is visualisation-only.

    STEP remains the manufacturing source. (Per-part GLB from build123d did not
    preserve the assembly placement, so the renderer uses the STL set.)
    """
    objs = {}
    for name in PARTS_ORDER:
        if name == "sensor":
            path = os.path.join(ROOT, "mechanical", "hy928d", "build", "hy928d_v2.stl")
        else:
            path = os.path.join(ROOT, "mechanical", "square_v1", "build", "parts",
                                name + "_v01.stl")
        if not os.path.exists(path):
            print("MISSING", path)
            continue
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for o in new:
            o.name = name
            if name == "sensor":
                o.location.z += 0.005
        objs[name] = new
    return objs


def normalize(objs, target=0.10):
    """STL import is already in metres at the right positions; only measure."""
    mins, maxs = [], []
    for lst in objs.values():
        for o in lst:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mins.append(w); maxs.append(w)
    lo = Vector((min(v.x for v in mins), min(v.y for v in mins), min(v.z for v in mins)))
    hi = Vector((max(v.x for v in maxs), max(v.y for v in maxs), max(v.z for v in maxs)))
    return None, lo, hi, 1.0


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
        if name == "light_guide":
            m = material("M_light_guide", (0.12, 0.45, 0.65), 0.0, 0.15,
                         emission=(0.15, 0.75, 1.0), strength=1.6)
        else:
            c = CFG["colors"][name]
            m = material("M_" + name, c["base"], c.get("metallic", 0), c.get("rough", 0.5))
        for o in lst:
            o.data.materials.clear()
            o.data.materials.append(m)
            o.select_set(True)
    # screen emission plane
    ui = os.path.join(HERE, "ui_screen.png")
    img = bpy.data.images.load(ui)
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
    k = (hi.x - lo.x) / 100.0          # metres per mm
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-8 * k, lo.y - 0.0002, 8 * k),
                                     rotation=(math.radians(90), 0, 0))
    plane = bpy.context.object
    plane.name = "screen_ui"
    plane.scale = (26 * k, 7 * k, 1)
    plane.data.materials.append(sm)

def studio():
    # ground
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "ground"
    gm = material("M_ground", (0.055, 0.055, 0.060), 0.0, 0.70)
    g.data.materials.append(gm)
    # world
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.035, 0.038, 0.045, 1)
    bg.inputs["Strength"].default_value = 0.6
    # lights
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
    area("key", (0.22, -0.22, 0.30), (math.radians(55), 0, math.radians(45)), 0.35, 6.5)
    area("fill", (-0.28, -0.18, 0.18), (math.radians(70), 0, math.radians(-50)), 0.30, 2.2)
    area("rim", (0.02, 0.28, 0.22), (math.radians(110), 0, math.radians(180)), 0.28, 3.5,
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
    root, lo, hi, s = normalize(objs)
    print("scale", s, "bbox", lo[:], hi[:])
    apply_materials(objs, lo, hi, s)
    studio()
    hero = camera("hero", (0.17, -0.21, 0.14), (0, 0, 0.007), 62)
    front = camera("front", (0, -0.30, 0.012), (0, 0, 0.008), 75)
    expl = camera("exploded", (0.20, -0.28, 0.12), (0, 0, 0.004), 60)
    os.makedirs(OUT, exist_ok=True)
    render(sc, hero, os.path.join(OUT, "hero.png"))
    render(sc, front, os.path.join(OUT, "front.png"), 1200, 600)
    # PCB detail: hide the top plate and look into the base
    plate = bpy.data.objects.get("plate")
    if plate:
        plate.hide_render = True
    pcb = camera("pcb", (0.085, -0.10, 0.105), (0, 0, 0.006), 70)
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
            for nm in ("screen_ui", "halo"):
                ob = bpy.data.objects.get(nm)
                if ob:
                    ob.location = ob.location + offv
    render(sc, expl, os.path.join(OUT, "exploded.png"), 1200, 1000)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "square_b.blend"))
    print("DONE")


if __name__ == "__main__":
    main()
