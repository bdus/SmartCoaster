"""Lead-side quick check: render a flat top view of a Kromacut print (STLs).

Not part of the delivery pipeline — a fast visual/geometry sanity check that the
Flat Paint export has the expected top colours, orientation and size.

  blender -b --python appearance/tools/check_print_top.py -- dog
"""
import glob
import json
import os
import sys

import bpy

ROOT = "/data/Documents/projects/SmartCoaster"
art = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "dog"
d = f"{ROOT}/appearance/build/print/{art}"
man = json.load(open(f"{d}/manifest.json"))
out = f"{d}/preview_top.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.render.resolution_x = 900
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "OBJECT"
world = bpy.data.worlds.new("W")
sc.world = world
world.color = (0.05, 0.05, 0.05)

for entry in man["stls"]:
    path = os.path.join(d, entry["file"])
    bpy.ops.wm.stl_import(filepath=path)
    ob = bpy.context.selected_objects[-1]
    hexs = entry["hex"]
    ob.color = tuple(int(hexs[i : i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)
    ob.name = f"{entry['filamentIndex']:02d}_{hexs}"

# orthographic top camera
cam_data = bpy.data.cameras.new("top")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 92.0
cam = bpy.data.objects.new("top", cam_data)
sc.collection.objects.link(cam)
cam.location = (0, 0, 120)
cam.rotation_euler = (0, 0, 0)
sc.camera = cam
sc.render.film_transparent = False
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out)
