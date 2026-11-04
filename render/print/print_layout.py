#!/usr/bin/env python3
"""3D-print reference layout: shell + top plate (flipped) + button on a 220 bed."""
import math
import os

import bpy
from mathutils import Matrix, Vector

ROOT = "/data/Documents/projects/SmartCoaster"
PARTS = os.path.join(ROOT, "mechanical", "square_v1", "build", "parts")
OUT = os.path.join(ROOT, "render", "print", "renders")
os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = -1.0
    return sc


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(PARTS, name + "_v01.stl"), global_scale=0.001)
    ob = [o for o in bpy.data.objects if o not in before][0]
    ob.name = name
    return ob


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def place(ob, xy, flip=False):
    """Centre part at xy (metres) on the bed; flip = top face down."""
    if flip:
        ob.matrix_world = Matrix.Rotation(math.pi, 4, "X") @ ob.matrix_world
    bpy.context.view_layer.update()
    lo, hi = bbox(ob)
    ob.matrix_world = Matrix.Translation(
        (xy[0] - (lo.x + hi.x) / 2, xy[1] - (lo.y + hi.y) / 2, -lo.z)
    ) @ ob.matrix_world
    bpy.context.view_layer.update()


def mat(name, base, metallic=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m


def main():
    sc = reset()
    shell = load("shell")
    plate = load("plate")
    button = load("button")
    # scene units are metres (STL imported with global_scale=0.001)
    place(shell, (-0.055, 0))
    place(plate, (0.055, 0), flip=True)
    place(button, (0, -0.060))
    for ob, col, met in ((shell, (0.05, 0.05, 0.055), 0.0),
                         (plate, (0.10, 0.03, 0.15), 0.0),
                         (button, (0.12, 0.03, 0.16), 0.0)):
        ob.data.materials.clear()
        ob.data.materials.append(mat("M_" + ob.name, col, met, 0.55))
    # build plate
    bpy.ops.mesh.primitive_plane_add(size=0.24, location=(0, 0, -0.0005))
    bed = bpy.context.object
    bed.data.materials.append(mat("M_bed", (0.10, 0.10, 0.11), 0.0, 0.8))
    # world / lights
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.04, 0.05, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
    def area(loc, rot, size, power):
        d = bpy.data.lights.new("a", "AREA"); d.energy = power; d.size = size
        o = bpy.data.objects.new("a", d); sc.collection.objects.link(o)
        o.location = loc; o.rotation_euler = rot
    area((0.22, -0.22, 0.32), (math.radians(55), 0, math.radians(45)), 0.4, 8)
    area((-0.3, -0.2, 0.2), (math.radians(70), 0, math.radians(-50)), 0.3, 3)
    # cameras
    def cam(name, loc, target, ortho=None, lens=60):
        c = bpy.data.cameras.new(name); c.lens = lens
        o = bpy.data.objects.new(name, c); sc.collection.objects.link(o)
        o.location = loc
        d = Vector(target) - o.location
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        if ortho:
            c.type = "ORTHO"; c.ortho_scale = ortho
        return o
    top = cam("top", (0, 0, 0.5), (0, 0, 0), ortho=0.23)
    iso = cam("iso", (0.19, -0.23, 0.20), (0, -0.01, 0.006), lens=48)
    for c, name, w_, h_ in ((top, "print_top.png", 1400, 1100), (iso, "print_iso.png", 1400, 900)):
        sc.camera = c
        sc.render.resolution_x = w_; sc.render.resolution_y = h_
        sc.render.filepath = os.path.join(OUT, name)
        bpy.ops.render.render(write_still=True)
        print("WROTE", sc.render.filepath)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "render", "print", "print_layout.blend"))


if __name__ == "__main__":
    main()
