#!/usr/bin/env python3
"""SmartCoaster appearance assembly render: real shell + recessed plate + Lumina-Layers print.

Builds, per version:
  SHELL_<VERSION> collection : real mechanical shell-assembly STLs, with the top
                               plate replaced by appearance/build/shell/<v>/plate_recessed.stl
  PRINT_ART_<ART> collection : one object per physical filament (Lumina-Layers STL or
                               placeholder), bottom on the pocket floor (shell.json),
                               XY centred, nominal 0.2 mm radial interference.
Shell and print stay separate objects/collections (Bambu Studio fuses at slice time).

Renders (Cycles CPU, AgX, denoise; same 3-point studio as render/square_b):
  appearance/render/<v>/hero.png            1000x1000  3/4 top
  appearance/render/<v>/top.png             1000x1000  orthographic top
  appearance/render/<v>/macro_edge.png      1600x1600  print rim in pocket, close-up
  appearance/render/<v>/section_exploded.png 1600x1200 composed 1/4 section + exploded inset
Raw section renders (inputs for the composition) go to
  appearance/build/render/<v>/section_{seated,exploded}.png
  appearance/render/<v>/scene.blend           assembled scene (shell/print separate)
  appearance/render/<v>/scene_section.blend   cut-away scene
  appearance/render/<v>/annotations.json      projected label anchors for postprocess
  appearance/render/<v>/scene_info.json       provenance/params/warnings/timings

Run:
  blender -b --python appearance/render/build_scene.py -- --version round
  blender -b --python appearance/render/build_scene.py            # both versions
Env: SC_SAMPLES, SC_RENDER_ONLY=hero,top,macro_edge,section
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene_common as SC  # noqa: E402

ROOT = SC.ROOT
VIEWS = ["hero", "top", "macro_edge", "print_top", "section"]


# --------------------------------------------------------------------------- #
# scene / collections
# --------------------------------------------------------------------------- #
def reset(rcfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    try:
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.adaptive_threshold = 0.02
        sc.cycles.max_bounces = 8
        sc.cycles.diffuse_bounces = 3
        sc.cycles.glossy_bounces = 3
        sc.cycles.transmission_bounces = 4
    except Exception:
        pass
    sc.render.resolution_x = 1000
    sc.render.resolution_y = 1000
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = rcfg.get("view_transform", "AgX")
    try:
        sc.view_settings.look = rcfg.get("look", "AgX - Medium High Contrast")
    except Exception:
        pass
    sc.view_settings.exposure = float(rcfg.get("exposure", -1.0))
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def relink(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def import_stl(path, col, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        raise RuntimeError("STL import produced no mesh: %s" % path)
    if len(new) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in new:
            o.select_set(True)
        bpy.context.view_layer.objects.active = new[0]
        bpy.ops.object.join()
        new = [bpy.context.view_layer.objects.active]
    obj = new[0]
    obj.name = name
    obj.data.name = name
    relink(obj, col)
    return obj


def mesh_bbox_world(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


# --------------------------------------------------------------------------- #
# materials
# --------------------------------------------------------------------------- #
def make_mat(name, rgb, rough=0.5, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = None
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            b = n
            break
    if b is None:
        b = m.node_tree.nodes.get("Principled BSDF")
    if b is None:
        raise RuntimeError("no Principled BSDF node in new material %r" % name)
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m


def cmf_material(cmf, part, name=None):
    ent = cmf["parts"].get(part, {})
    if ent.get("hex"):
        rgb = SC.srgb_hex_to_linear(ent["hex"])
    elif ent.get("base"):
        rgb = tuple(ent["base"])
    else:
        rgb = (0.35, 0.35, 0.35)
    return make_mat(name or ("M_" + part), rgb,
                    float(ent.get("rough", 0.5)), float(ent.get("metallic", 0.0)))


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def proxy_pocket(plate_obj, spec):
    """Render-only boolean proxy: cut the Ø86 pocket when the recessed plate is absent."""
    sh = spec["shell"]
    pocket_r = sh["pocket_dia_mm"] / 2000.0           # m
    floor = sh["floor_z_mm"] / 1000.0
    rim = (sh["rim_z_mm"] or sh["floor_z_mm"] + 2.0) / 1000.0
    top = rim + 0.002
    depth = top - floor
    bpy.ops.mesh.primitive_cylinder_add(vertices=256, radius=pocket_r, depth=depth,
                                        location=(0.0, 0.0, (top + floor) / 2.0))
    cutter = bpy.context.object
    cutter.name = "proxy_pocket_cutter"
    bpy.context.view_layer.objects.active = plate_obj
    mod = plate_obj.modifiers.new("pocket_proxy", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ok = True
    except Exception as exc:  # pragma: no cover - defensive
        print("PROXY_POCKET_FAILED", exc)
        plate_obj.modifiers.remove(mod)
        ok = False
    bpy.data.objects.remove(cutter, do_unlink=True)
    return ok


def add_placeholder_mesh(verts_mm, tris, name, col):
    me = bpy.data.meshes.new(name)
    verts = [(v[0] * 0.001, v[1] * 0.001, v[2] * 0.001) for v in verts_mm]
    me.from_pydata(verts, [], tris)
    me.update()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    return obj


# --------------------------------------------------------------------------- #
# render-only art face (Lumina predicted printed colour)
# --------------------------------------------------------------------------- #
def add_print_face(ver, art, spec, col):
    """Overlay the *predicted* printed colour on the print top (render only).

    Lumina-Layers reproduces colour by stacking translucent 0.08 mm filament
    layers, so the visible colour is NOT the flat colour of the topmost
    filament: e.g. a pink cheek is a White+Magenta mix.  Rendering the four
    per-filament solids with their raw colours would show the wrong picture.
    Lumina also returns the predicted per-pixel colour (`matched_rgb`, exported
    here as plate_preview.png); this thin textured disc samples that map 1:1 on
    the print top so the mockup shows what comes off the printer.

    It is a RENDER-ONLY object: it is not in the 3MF and not in the STL
    delivery.  The cut-away section keeps it so the visible face stays correct.
    """
    png = os.path.join(ROOT, "appearance", "build", "render", ver,
                       "print_face_%s.png" % art)
    os.makedirs(os.path.dirname(png), exist_ok=True)
    try:
        rgb_path = os.path.join(ROOT, "appearance", "build", "print", art,
                                "matched_rgb.npy")
        mask_path = os.path.join(ROOT, "appearance", "build", "print", art,
                                 "mask_solid.npy")
        rgb = np.load(rgb_path).astype(np.float32)
        mask = np.load(mask_path).astype(bool)
        # Lumina's own plate_preview.png has arbitrary RGB outside the alpha
        # circle; sampling it at the rim makes coloured speckles.  Rebuild the
        # face texture from the authoritative matched_rgb array and bleed the
        # inside colours outward so every texel is valid.
        known = mask.copy()
        out = rgb.copy()
        for _ in range(6):
            pad = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
            padk = np.pad(known, ((1, 1), (1, 1)), mode="edge")
            acc = np.zeros_like(out)
            cnt = np.zeros(mask.shape, dtype=np.float32)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    h, w = mask.shape
                    nb = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                    nk = padk[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                    acc += nb * nk[..., None]
                    cnt += nk
            grow = (~known) & (cnt > 0)
            out[grow] = acc[grow] / cnt[grow][:, None]
            known = known | grow
        # Blender has no PIL -> write the PNG through bpy (pixels are bottom-up
        # RGBA floats, sRGB-encoded for a byte image)
        hh, ww = mask.shape
        rgba = np.ones((hh, ww, 4), dtype=np.float32)
        rgba[:, :, :3] = np.clip(out, 0, 255).astype(np.float32) / 255.0
        img = bpy.data.images.new("PRINT_FACE_TEX_%s" % art.upper(),
                                  width=ww, height=hh, alpha=False)
        img.pixels.foreach_set(rgba[::-1].ravel())
        img.filepath_raw = png
        img.file_format = "PNG"
        img.save()
    except Exception as exc:      # pragma: no cover - fall back to the preview
        spec["warnings"].append("print face texture build failed (%s); using "
                                "plate_preview.png" % exc)
        png = os.path.join(ROOT, "appearance", "build", "print", art,
                           "plate_preview.png")
        if not os.path.exists(png):
            spec["warnings"].append("no plate_preview.png for %s: print face "
                                    "overlay skipped" % art)
            return None
    env = spec["print"].get("envelope") or {}
    top_z = env.get("top_z_mm")
    if top_z is None:
        spec["warnings"].append("print envelope missing: print face overlay skipped")
        return None
    # Geometry radius = the measured max radius: the print's top face is
    # coplanar with the plate rim AND overlaps it by the radial interference
    # ring, which z-fights in Cycles.  Covering that ring with the overlay (and
    # disabling its shadow) removes the jagged band at the seam.
    # radius = the print's NOMINAL radius: the art's own alpha circle is at
    # frame_r*0.998, so a larger overlay only samples the art's rim pixels and
    # smears them over the plate rim as coloured specks.
    r = float(spec["shell"]["print_dia_mm"]) / 2.0
    # UV frame = the art frame the texture was rendered in (art.json frame_mm)
    frame_r = 43.2
    try:
        aj = json.load(open(os.path.join(ROOT, "appearance", "build", "art", art,
                                         "art.json"), encoding="utf-8"))
        frame_r = float(aj.get("frame_mm") or 86.4) / 2.0
    except Exception:
        pass
    nseg, rings = 256, 24
    verts, uvs = [(0.0, 0.0, 0.0)], [(0.5, 0.5)]
    for ring in range(1, rings + 1):
        rr = r * ring / rings
        for k in range(nseg):
            a = 2.0 * math.pi * k / nseg
            x, y = rr * math.cos(a), rr * math.sin(a)
            verts.append((x / 1000.0, y / 1000.0, 0.0))
            uvs.append(((x + frame_r) / (2.0 * frame_r),
                        (y + frame_r) / (2.0 * frame_r)))
    faces = []
    for k in range(nseg):
        faces.append((0, 1 + k, 1 + (k + 1) % nseg))
    for ring in range(1, rings):
        b0 = 1 + (ring - 1) * nseg
        b1 = 1 + ring * nseg
        for k in range(nseg):
            k2 = (k + 1) % nseg
            faces.append((b0 + k, b0 + k2, b1 + k2, b1 + k))
    me = bpy.data.meshes.new("PRINT_FACE_%s" % art.upper())
    me.from_pydata(verts, [], faces)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = uvs[vi]
    for poly in me.polygons:
        # FLAT shading: smooth shading over a 256-triangle centre fan creates a
        # degenerate pole normal and renders a black dot/ring at the disc centre.
        poly.use_smooth = False
    obj = bpy.data.objects.new("PRINT_FACE_%s" % art.upper(), me)
    col.objects.link(obj)
    obj.location.z = top_z / 1000.0 + 30.0e-6     # 30 um above the real top face
    # (1 um was inside Cycles' ray precision: print staircase tips poked through)
    obj.visible_shadow = False                    # no hairline on the plate rim

    mat = bpy.data.materials.new("M_PRINT_FACE_%s" % art.upper())
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = None
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            bsdf = n
            break
    if bsdf is None:
        raise RuntimeError("no Principled BSDF node for the print face material")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png, check_existing=True)
    tex.image.colorspace_settings.name = "sRGB"
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"   # art frame is 86.4 mm, the disc reaches 86.6 mm
                               # at the pixel staircase -> clamp, never wrap
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Metallic"].default_value = 0.0
    obj.data.materials.append(mat)
    spec.setdefault("render_only_objects", []).append(obj.name)
    spec["notes"].append(
        "PRINT_FACE_%s is a RENDER-ONLY overlay sampling Lumina's predicted "
        "printed colour (matched_rgb / plate_preview.png); it is not part of the "
        "3MF or the STL delivery - the physical print is the 4 per-filament solids."
        % art.upper())
    print("PRINT_FACE overlay r=%.3f mm (frame r=%.2f), top z=%.3f mm, texture %s"
          % (r, frame_r, top_z, os.path.relpath(png, ROOT)))
    return obj


def build(spec, cfg, out_dir, raw_dir):
    sc = reset(cfg["render"])
    ver = spec["version"]
    art = spec["art"]

    col_shell = new_collection("SHELL_%s" % ver.upper())
    col_print = new_collection("PRINT_ART_%s" % art.upper())
    col_studio = new_collection("STUDIO")

    cmf = SC.load_cmf(cfg)

    # ---- shell assembly parts ------------------------------------------- #
    shell_objs, part_mats = [], {}
    for part in spec["parts"]:
        obj = import_stl(part["path"], col_shell, part["name"])
        m = cmf_material(cmf, part["name"], "M_" + part["name"])
        obj.data.materials.clear()
        obj.data.materials.append(m)
        part_mats[part["name"]] = m
        shell_objs.append(obj)
        print("PART", part["name"], os.path.basename(part["path"]))

    # ---- recessed plate (or boolean proxy of the original plate) --------- #
    plate_obj = None
    if spec["plate"]["path"]:
        plate_obj = import_stl(spec["plate"]["path"], col_shell, "plate")
        plate_obj.data.materials.clear()
        plate_obj.data.materials.append(cmf_material(cmf, "plate", "M_plate"))
        if spec["plate"]["proxy"]:
            ok = proxy_pocket(plate_obj, spec)
            spec.setdefault("notes", []).append(
                "plate pocket rendered via boolean proxy (recessed plate STL missing): %s" % ok)
    else:
        spec["warnings"].append("no plate STL at all for %s" % ver)

    # ---- print: one object per physical filament ------------------------ #
    pr = spec["print"]
    floor_m = spec["shell"]["floor_z_mm"] / 1000.0
    print_objs, print_mats = [], []
    palette = pr.get("palette") or []
    for i, pobj in enumerate(pr["objects"]):
        hexv = pobj.get("hex") or (palette[i] if i < len(palette) else "#CCCCCC")
        mat = make_mat("M_print_%02d_%s" % (i, hexv.lstrip("#")),
                       SC.srgb_hex_to_linear(hexv), rough=0.5, metallic=0.0)
        print_mats.append(mat)
        if pobj.get("path"):
            obj = import_stl(pobj["path"], col_print,
                             "ART_%s_%02d" % (art.upper(), i))
        else:
            v, t = SC.print_object_mesh(pobj)
            obj = add_placeholder_mesh(v, t, "ART_%s_%02d" % (art.upper(), i), col_print)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        print_objs.append(obj)

    # Align the print group as a WHOLE (all filament STLs share the same z=0
    # print-bottom datum) — never align per filament, that would shear the layers.
    if print_objs:
        lo, hi = mesh_bbox_world(print_objs)
        dz = floor_m - lo.z
        for obj in print_objs:
            obj.location.z += dz
        bpy.context.view_layer.update()
        for i, (obj, pobj) in enumerate(zip(print_objs, pr["objects"])):
            lo2, hi2 = mesh_bbox_world([obj])
            pobj["_world_bbox_mm"] = [[round(x * 1000, 3) for x in lo2],
                                      [round(x * 1000, 3) for x in hi2]]
            pobj["_zshift_mm"] = round(dz * 1000, 4)

    # actual max vertex radius (staircase corners can exceed the nominal Ø86.4/2)
    if print_objs:
        max_r = 0.0
        for obj in print_objs:
            n = len(obj.data.vertices)
            co = np.empty(n * 3, dtype=np.float32)
            obj.data.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            m = np.array(obj.matrix_world)
            w = co @ m[:3, :3].T + m[:3, 3]
            max_r = max(max_r, float(np.hypot(w[:, 0], w[:, 1]).max()) * 1000.0)
        interference = max_r - spec["shell"]["pocket_dia_mm"] / 2.0
        # numeric guard: a unit bug must fail the build, not reach an annotation
        if not (40.0 < max_r < 45.0):
            raise RuntimeError("print max radius %.3f mm is not in (40,45) mm" % max_r)
        if not (0.0 < interference < 1.0):
            raise RuntimeError("actual max radial interference %.3f mm is not in (0,1) mm"
                               % interference)
        spec["print"]["max_radius_mm"] = round(max_r, 3)
        spec["print"]["actual_max_interference_mm"] = round(interference, 3)
        print("PRINT_RADIUS max=%.3f mm pocket=%.3f mm interference=%.3f mm"
              % (max_r, spec["shell"]["pocket_dia_mm"] / 2.0, interference))

    # print envelope checks (report, never adjust geometry silently)
    if print_objs:
        lo, hi = mesh_bbox_world(print_objs)
        env = {"bbox_mm": [[round(x * 1000, 3) for x in lo],
                           [round(x * 1000, 3) for x in hi]],
               "dia_x_mm": round((hi.x - lo.x) * 1000, 3),
               "dia_y_mm": round((hi.y - lo.y) * 1000, 3),
               "height_mm": round((hi.z - lo.z) * 1000, 3),
               "bottom_z_mm": round(lo.z * 1000, 3),
               "top_z_mm": round(hi.z * 1000, 3)}
        spec["print"]["envelope"] = env
        # the print GROUP must be XY centred; individual filament objects cover
        # only their own art zones, so per-object centres are expected to differ.
        gcx = (lo.x + hi.x) / 2.0 * 1000.0
        gcy = (lo.y + hi.y) / 2.0 * 1000.0
        if abs(gcx) > 0.05 or abs(gcy) > 0.05:
            spec["warnings"].append("print group XY centre off by (%.3f, %.3f) mm"
                                    % (gcx, gcy))
        rim = spec["shell"]["rim_z_mm"]
        if rim is not None:
            env["top_gap_mm"] = round(rim - env["top_z_mm"], 3)
        pd = spec["shell"]["pocket_dia_mm"]
        if pd:
            env["radial_interference_mm"] = round(
                (env["dia_x_mm"] - pd) / 2.0, 3)

    # ---- render-only art face (predicted printed colour) ----------------- #
    if print_objs:
        add_print_face(ver, art, spec, col_print)

    # ---- studio / camera ------------------------------------------------- #
    studio(col_studio)
    lo, hi = mesh_bbox_world(shell_objs + ([plate_obj] if plate_obj else []))
    spec["shell_bbox_mm"] = [[round(x * 1000, 3) for x in lo],
                             [round(x * 1000, 3) for x in hi]]

    if ver == "square":
        add_screen_plane(lo, col_shell)

    cams = {}
    for view in VIEWS:
        c = cfg["versions"][ver]["cameras"].get(view)
        if view == "section":
            c = cfg["versions"][ver]["cameras"]["section_exploded"]
        if not c:
            continue
        if "ortho_scale" in c:
            cams[view] = make_camera(view, c["loc"], c["target"], ortho_scale=c["ortho_scale"])
        elif "offset" in c:
            loc = [c["target"][i] + c["offset"][i] for i in range(3)]
            cams[view] = make_camera(view, loc, c["target"], lens=c["lens"])
        else:
            cams[view] = make_camera(view, c["loc"], c["target"], lens=c["lens"])

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "scene.blend"))

    info = {
        "version": ver, "art": art, "blender": bpy.app.version_string,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "shell": spec["shell"], "plate": {k: v for k, v in spec["plate"].items()
                                          if k != "path"} | {"file": os.path.basename(spec["plate"]["path"] or "")},
        "print": {k: v for k, v in spec["print"].items()
                  if k not in ("objects",)},
        "print_objects": [{k: v for k, v in o.items() if not k.startswith("_")}
                          for o in spec["print"]["objects"]],
        "part_files": [{"name": p["name"], "file": os.path.basename(p["path"]),
                        "path": os.path.relpath(p["path"], ROOT)} for p in spec["parts"]],
        "collection_objects": {
            "SHELL_%s" % ver.upper(): [o.name for o in bpy.data.collections["SHELL_%s" % ver.upper()].objects],
            "PRINT_ART_%s" % art.upper(): [o.name for o in bpy.data.collections["PRINT_ART_%s" % art.upper()].objects],
        },
        "render_only_objects": spec.get("render_only_objects", []),
        "warnings": spec["warnings"], "mismatches": spec["mismatches"],
        "notes": spec["notes"], "timings_s": {}, "views": {},
    }
    return sc, cams, spec, info, col_shell, col_print, col_studio


# --------------------------------------------------------------------------- #
# studio (mirrors render/square_b: 3-point area lights, dark ground, AgX)
# --------------------------------------------------------------------------- #
def studio(col):
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "ground"
    # 0.9 roughness: the 3-point rig's rim light otherwise reflects as a hard
    # bright rectangle on the glossy ground (square_b convention kept otherwise)
    # NOTE make_mat(name, rgb, rough, metallic) — square_b's helper had the
    # metallic/roughness argument order swapped, so the ground is a matte
    # dielectric here (rough 0.85, metallic 0) instead of a polished metal mirror.
    g.data.materials.append(make_mat("M_ground", (0.055, 0.055, 0.060),
                                     rough=0.85, metallic=0.0))
    relink(g, col)

    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = None
    for n in w.node_tree.nodes:
        if n.type == "BACKGROUND":
            bg = n
            break
    if bg is None:
        bg = w.node_tree.nodes.new("ShaderNodeBackground")
        out = None
        for n in w.node_tree.nodes:
            if n.type == "OUTPUT_WORLD":
                out = n
                break
        if out is not None:
            w.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Color"].default_value = (0.035, 0.038, 0.045, 1)
    bg.inputs["Strength"].default_value = 0.6

    def area(name, loc, rot, size, power, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, "AREA")
        d.energy = power
        d.size = size
        d.color = color
        o = bpy.data.objects.new(name, d)
        col.objects.link(o)
        o.location = loc
        o.rotation_euler = rot
        o.visible_camera = False
        return o

    area("key", (0.22, -0.22, 0.30),
         (math.radians(55), 0, math.radians(45)), 0.35, 6.5)
    area("fill", (-0.28, -0.18, 0.18),
         (math.radians(70), 0, math.radians(-50)), 0.30, 2.2)
    area("rim", (0.02, 0.28, 0.22),
         (math.radians(110), 0, math.radians(180)), 0.28, 3.5,
         (0.75, 0.85, 1.0))


def add_screen_plane(lo, col):
    """UI screen content, square version only (render/square_b/ui_screen.png)."""
    ui = os.path.join(ROOT, "render", "square_b", "ui_screen.png")
    if not os.path.exists(ui):
        return None
    img = bpy.data.images.load(ui)
    m = bpy.data.materials.new("M_screen")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    em.inputs["Strength"].default_value = 2.5
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(
        size=1, location=(-8 * 0.001, lo.y - 0.0002, 8 * 0.001),
        rotation=(math.radians(90), 0, 0))
    plane = bpy.context.object
    plane.name = "screen_ui"
    plane.scale = (26 * 0.001, 7 * 0.001, 1)
    plane.data.materials.append(m)
    relink(plane, col)
    return plane


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def make_camera(name, loc, target, lens=62, ortho_scale=None):
    c = bpy.data.cameras.new(name)
    c.sensor_width = 36
    c.clip_start = 0.001
    c.clip_end = 10.0
    if ortho_scale is not None:
        c.type = "ORTHO"
        c.ortho_scale = ortho_scale
    else:
        c.lens = lens
    o = bpy.data.objects.new(name, c)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    return o


# --------------------------------------------------------------------------- #
# section helpers
# --------------------------------------------------------------------------- #
def bisect_quadrant(obj):
    """Remove the +X/+Y quadrant (keeps -X/-Y), fill the cut faces."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                            clear_outer=True, clear_inner=False, use_fill=True)
        bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(0, 1, 0),
                            clear_outer=True, clear_inner=False, use_fill=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        return True
    except Exception as exc:  # pragma: no cover
        print("BISECT_FAILED", obj.name, exc)
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        return False


def prepare_section(spec, shell, plate, print_objs):
    """Hide internals/ground, clip a quarter, return moved-object info."""
    keep = {o.name for o in list(shell) + ([plate] if plate else []) + list(print_objs)}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name not in keep and o.name not in ("ground",):
            o.hide_render = True
    for o in list(shell) + ([plate] if plate else []) + list(print_objs):
        o.hide_render = False
    if plate:
        bisect_quadrant(plate)
    for o in shell:
        bisect_quadrant(o)
    for o in print_objs:
        bisect_quadrant(o)
    g = bpy.data.objects.get("ground")
    if g:
        g.hide_render = True
    ui = bpy.data.objects.get("screen_ui")
    if ui:
        ui.hide_render = True


def project_points(sc, cam, spec, explode_mm):
    from bpy_extras.object_utils import world_to_camera_view
    sh = spec["shell"]
    floor = sh["floor_z_mm"] / 1000.0
    rim = (sh.get("rim_z_mm") or 0.0) / 1000.0
    thk = sh["print_thickness_mm"] / 1000.0
    ex = explode_mm / 1000.0
    pts = {}
    lp = spec.get("_label_points") or {}
    if not lp:
        cfg = SC.load_config()
        lp = cfg.get("section", {}).get("label_points_mm", {})
    zmap = {
        "print_top": floor + thk + ex,          # on the print art surface
        "print_bottom": floor + ex,
        "pocket_floor": floor + 0.15e-3,        # on the plate cut face near the floor
        "pocket_wall": floor + 0.6e-3,          # on the plate cut face in the pocket wall
        "plate_rim": rim,                       # on the plate top surface
    }
    for name, xy in lp.items():
        z = zmap.get(name, floor)
        p = Vector((xy[0] / 1000.0, xy[1] / 1000.0, z))
        uv = world_to_camera_view(sc, cam, p)
        pts[name] = [round(uv.x, 5), round(uv.y, 5), round(uv.z, 5)]
    return pts


def render_view(sc, cam, path, res, samples, label=None):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.cycles.samples = samples
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    print("RENDERED %s %.1fs (%dx%d, %d samples)"
          % (path, dt, res[0], res[1], samples))
    return dt


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run_version(version, cfg, args):
    spec = SC.resolve_assembly(version, cfg)
    spec["_label_points"] = cfg.get("section", {}).get("label_points_mm", {})
    out_dir = os.path.join(HERE, version)
    raw_dir = os.path.join(ROOT, "appearance", "build", "render", version)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    print("=" * 78)
    print("VERSION", version, "| art", spec["art"], "| shell", spec["shell"]["source"],
          "| print", spec["print"]["source"])
    for w in spec["warnings"]:
        print("WARN", w)
    for m in spec["mismatches"]:
        print("MISMATCH", m)

    sc, cams, spec, info, col_shell, col_print, col_studio = build(
        spec, cfg, out_dir, raw_dir)
    only = [v for v in args.render_only.split(",") if v] if args.render_only else VIEWS
    rcfg = cfg["render"]
    samples = rcfg["samples"]
    res = rcfg["resolution"]

    def sel(name):
        return int(args.samples) if args.samples else int(samples.get(name, 48))

    # regular views
    for view in ("hero", "top", "macro_edge"):
        if view not in only or view not in cams:
            continue
        dst = (os.path.join(raw_dir, view + ".png") if view == "macro_edge"
               else os.path.join(out_dir, view + ".png"))
        dt = render_view(sc, cams[view], dst, res[view], sel(view))
        info["views"][view] = {
            "file": view + ".png", "seconds": round(dt, 2),
            "resolution": res[view], "samples": sel(view),
            "raw": (os.path.relpath(dst, ROOT) if view == "macro_edge" else None)}
        info["timings_s"][view] = round(dt, 2)
        bpy.context.view_layer.update()

    if "print_top" in only and "print_top" in cams:
        # clean print-only top view: hide shell/plate/internals/ground, keep print
        hidden = []
        keep = set(o.name for o in col_print.objects)
        for o in bpy.data.objects:
            if o.type == "MESH" and o.name not in keep and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
        dt = render_view(sc, cams["print_top"],
                         os.path.join(out_dir, "print_top.png"),
                         res["print_top"], sel("print_top"))
        info["views"]["print_top"] = {"file": "print_top.png",
                                      "seconds": round(dt, 2),
                                      "resolution": res["print_top"],
                                      "samples": sel("print_top")}
        info["timings_s"]["print_top"] = round(dt, 2)
        for o in hidden:
            o.hide_render = False

    if "section" in only and "section" in cams:
        # seated 1/4 section (print on the pocket floor) -> composition base
        shell_keep = [bpy.data.objects.get("shell")]
        prepare_section(spec, [o for o in shell_keep if o],
                        bpy.data.objects.get("plate"),
                        [o for o in col_print.objects])
        bpy.context.view_layer.update()
        cam = cams["section"]
        sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
        info["annotations"] = {
            "view": "section_main", "resolution": [1600, 1200],
            "points": project_points(sc, cam, spec, 0.0),
            "explode_mm": 0.0,
        }
        dt = render_view(sc, cam, os.path.join(raw_dir, "section_seated.png"),
                         [1600, 1200], sel("section_exploded"))
        info["timings_s"]["section_seated"] = round(dt, 2)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "scene_section.blend"))

        # exploded inset: plate + print only (hide the shell), lift the print
        ex = float(cfg.get("section", {}).get("explode_print_mm", 6.0)) / 1000.0
        shell_obj = bpy.data.objects.get("shell")
        if shell_obj:
            shell_obj.hide_render = True
        for o in col_print.objects:
            o.location.z += ex
        bpy.context.view_layer.update()
        ann = project_points(sc, cam, spec, ex * 1000.0)
        info["annotations_exploded"] = {
            "view": "section_inset", "resolution": [1200, 1000],
            "points": ann, "explode_mm": ex * 1000.0,
        }
        dt = render_view(sc, cam, os.path.join(raw_dir, "section_exploded.png"),
                         [1200, 1000], max(24, sel("section_exploded") // 2))
        info["timings_s"]["section_exploded_raw"] = round(dt, 2)
        info["views"]["section"] = {"file": "section_exploded.png",
                                    "note": "composed by postprocess.py from raw renders",
                                    "samples": sel("section_exploded")}
        info["raw_section"] = {"seated": os.path.relpath(
            os.path.join(raw_dir, "section_seated.png"), ROOT),
            "exploded": os.path.relpath(
                os.path.join(raw_dir, "section_exploded.png"), ROOT)}

    info["total_seconds"] = round(sum(info["timings_s"].values()), 2)
    with open(os.path.join(out_dir, "scene_info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2, ensure_ascii=False)
    if "annotations" in info:
        with open(os.path.join(out_dir, "annotations.json"), "w", encoding="utf-8") as fh:
            json.dump(info["annotations"], fh, indent=2)
    print("DONE", version, "total render %.1fs" % info["total_seconds"])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="both", choices=["round", "square", "both"])
    ap.add_argument("--render-only", default=os.environ.get("SC_RENDER_ONLY", ""))
    ap.add_argument("--samples", default=os.environ.get("SC_SAMPLES", ""))
    args = ap.parse_args(argv)
    cfg = SC.load_config()
    versions = ["round", "square"] if args.version == "both" else [args.version]
    for v in versions:
        run_version(v, cfg, args)


if __name__ == "__main__":
    main()
