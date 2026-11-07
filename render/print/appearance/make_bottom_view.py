#!/usr/bin/env python3
"""Bottom view of the delivered print pose: proof that the art face IS layer 1.

The delivery prints the plate + print TOP-FACE-DOWN.  Seen from above you only
see the plate's underside and the print's cream/backing back - which is correct
and is exactly what the slicer preview shows.  This script renders the same
baked STLs from BELOW the build plate so the reviewer can see the artwork
sitting on the bed (the first layer), i.e. that the print is not upside down.

Output: render/print/stl/<version>/print_bottom.png  (1400x1000)
Run:    blender -b --python render/print/appearance/make_bottom_view.py
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "render", "print", "stl")
sys.path.insert(0, os.path.join(ROOT, "appearance", "render"))
sys.path.insert(0, os.path.join(ROOT, "render", "print", "appearance"))
import scene_common as SC  # noqa: E402

VERSIONS = ("round", "square")


def mat(name, rgb, rough=0.5, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return m


def import_stl(path, name, col):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        raise RuntimeError("no mesh imported from " + path)
    if len(new) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in new:
            o.select_set(True)
        bpy.context.view_layer.objects.active = new[0]
        bpy.ops.object.join()
        new = [bpy.context.view_layer.objects.active]
    o = new[0]
    o.name = name
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def relink(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def main():
    sc = bpy.context.scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 32
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = -1.2

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.55, 0.57, 0.62, 1.0)
    bg.inputs["Strength"].default_value = 1.6

    for v in VERSIONS:
        vdir = os.path.join(OUT, v)
        layout = json.load(open(os.path.join(vdir, "layout.json"), encoding="utf-8"))
        dv = json.load(open(os.path.join(ROOT, "render", "print", "stl",
                                         "delivery.json"), encoding="utf-8"))
        cmf = SC.load_cmf(SC.load_config())
        hexes = {p: "#" + cmf["parts"][p]["hex"].lstrip("#") for p in
                 ("shell", "plate", "button")}
        entries = dv["versions"][v]["entries"]
        units = layout["units"]
        place = units["plate_unit"]["placement_xy_mm"]
        place_of = {"shell": units["shell"]["placement_xy_mm"],
                    "plate": place,
                    "button": (units.get("button") or {}).get("placement_xy_mm", [0, 0])}
        # fresh scene
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        col = bpy.data.collections.new("DELIVERED_%s" % v.upper())
        sc.collection.children.link(col)
        for e in entries:
            p = os.path.join(ROOT, e["path"])
            name = os.path.splitext(e["file"])[0]
            ob = import_stl(p, name, col)
            hx = e.get("material_hex") or "#888888"
            rgb = SC.srgb_hex_to_linear(hx)
            ob.data.materials.clear()
            ob.data.materials.append(mat("M_" + name, rgb, 0.55))
            if e["part"].startswith("print"):
                off = place
            elif e["part"] in ("plate", "plate_recessed"):
                off = place
            elif e["part"] == "button":
                off = place_of["button"]
            elif e["part"] == "shell":
                off = place_of["shell"]
            else:
                off = [0, 0]
            ob.location.x += off[0] / 1000.0
            ob.location.y += off[1] / 1000.0
            print("BOTTOM %-7s import %-36s %s" % (v, e["file"], hx))

        # ortho camera looking UP at the bed from below (z = -120 mm)
        cam_data = bpy.data.cameras.new("bottom")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 0.125
        cam = bpy.data.objects.new("cam_bottom", cam_data)
        col.objects.link(cam)
        cam.location = (place[0] / 1000.0, place[1] / 1000.0, -0.12)
        # frame the plate+print unit (the shell is visible only as context)
        cam.rotation_euler = (math.radians(180.0), 0.0, 0.0)
        sc.camera = cam


        sc.render.resolution_x = 1400
        sc.render.resolution_y = 1000
        sc.render.filepath = os.path.join(vdir, "print_bottom.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", os.path.relpath(sc.render.filepath, ROOT))
        # strip the runtime objects for the next version
        for o in list(bpy.data.objects):
            if o.name.startswith(("cam_bottom", "key")):
                bpy.data.objects.remove(o, do_unlink=True)


if __name__ == "__main__":
    main()
