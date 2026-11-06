#!/usr/bin/env python3
"""3D-print delivery layout for BOTH SmartCoaster appearance versions.

For each version build a 220 x 220 mm bed scene with the parts that actually go on
the printer, using the READ-ONLY inputs produced by the appearance pipeline:

  round / dog :  LUMEN shell_v01                          (separate, bed down)
                 plate_recessed (round) recess-UP  +  dog print nested in the
                 recess (print bottom on the pocket floor, z = 15.75 mm relative
                 to the plate)                            (one nested unit)
                 no button (LUMEN has no button part)

  square / elf:  square_v1 shell_v01                      (separate, bed down)
                 plate_recessed (square) recess-UP + elf print nested
                 (floor z = 16.55 mm relative to the plate)
                 button_v01                              (separate, bed down)

The plate is laid with the recess UP so the Kromacut print can be nested in it
("in-place bonding" job).  In that orientation the plate underside skirt and force
column hang below the plate body, so the plate needs supports in the slicer
(PROVISIONAL - not physically tested).

Positions are computed from measured bboxes (never hardcoded), asserted to fit the
220 bed with >= 5 mm gaps between separate parts, no overhang and no overlap.  The
print-bottom-on-pocket-floor relation is asserted against shell.json + plate STL
floor vertices.  Renders clean matte iso + orthographic top views:
  render/print/appearance/<v>/print_iso.png
  render/print/appearance/<v>/print_top.png
and writes the measured layout/validation to render/print/appearance/<v>/layout.json.

Run:  blender -b --python render/print/appearance/print_layout_appearance.py
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "appearance", "render"))
import scene_common as SC  # noqa: E402

OUT = HERE
BED_MM = 220.0
MIN_GAP_MM = 5.0
FLOOR_TOL_MM = 0.02
VERSIONS = ("round", "square")


# --------------------------------------------------------------------------- #
# scene helpers
# --------------------------------------------------------------------------- #
def reset(samples=48):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.adaptive_threshold = 0.02
    except Exception:
        pass
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = -1.0
    sc.unit_settings.system = "METRIC"
    return sc


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


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
    o.data.name = name
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def world_verts(o):
    n = len(o.data.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    o.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(o.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def bbox(objs):
    v = np.vstack([world_verts(o) for o in objs])
    return v.min(axis=0), v.max(axis=0)


def translate(objs, d):
    m = Matrix.Translation(Vector(d))
    for o in objs:
        o.matrix_world = m @ o.matrix_world
    bpy.context.view_layer.update()


def recenter_unit(objs, z_to_bed=True):
    lo, hi = bbox(objs)
    dz = -lo[2] if z_to_bed else 0.0
    translate(objs, (-(lo[0] + hi[0]) / 2.0, -(lo[1] + hi[1]) / 2.0, dz))
    return bbox(objs)


def principled(m):
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    raise RuntimeError("no Principled BSDF")


def mat_rgb(name, rgb, rough=0.55, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = principled(m)
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return m


def mat_hex(name, hexv, rough=0.55):
    return mat_rgb(name, SC.srgb_hex_to_linear(hexv), rough=rough, metallic=0.0)


def look_at(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def make_camera(name, loc, target, lens=45, ortho=None):
    c = bpy.data.cameras.new(name)
    c.sensor_width = 36
    c.clip_start = 0.001
    c.clip_end = 20.0
    if ortho is not None:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    else:
        c.lens = lens
    o = bpy.data.objects.new(name, c)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    return o


def studio(sc, col):
    # 220 x 220 bed
    bpy.ops.mesh.primitive_plane_add(size=BED_MM / 1000.0, location=(0, 0, -0.0004))
    bed = bpy.context.object
    bed.name = "bed_220"
    bed.data.materials.append(mat_rgb("M_bed", (0.055, 0.060, 0.070), 0.9))
    for c in list(bed.users_collection):
        c.objects.unlink(bed)
    col.objects.link(bed)
    # thin bed border frame (visual bed extents)
    half = BED_MM / 2000.0
    bw = 0.0015
    for i, (cx, cy, sx, sy) in enumerate([
            (0, half, BED_MM / 1000.0 + 2 * bw, bw),
            (0, -half, BED_MM / 1000.0 + 2 * bw, bw),
            (half, 0, bw, BED_MM / 1000.0 + 2 * bw),
            (-half, 0, bw, BED_MM / 1000.0 + 2 * bw)]):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, -0.0001))
        fr = bpy.context.object
        fr.name = "bed_frame_%d" % i
        fr.scale = (sx, sy, 0.0008)
        fr.data.materials.append(mat_rgb("M_bedframe", (0.16, 0.17, 0.19), 0.7))
        for c in list(fr.users_collection):
            c.objects.unlink(fr)
        col.objects.link(fr)

    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.040, 0.042, 0.050, 1)
    bg.inputs["Strength"].default_value = 0.7

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

    area("key", (0.22, -0.22, 0.32), (math.radians(55), 0, math.radians(45)),
         0.40, 8.0)
    area("fill", (-0.30, -0.20, 0.22), (math.radians(70), 0, math.radians(-50)),
         0.30, 3.0)
    area("rim", (0.0, 0.30, 0.24), (math.radians(115), 0, math.radians(180)),
         0.30, 4.0, (0.75, 0.85, 1.0))


def render_view(sc, cam, path, res, samples):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.cycles.samples = samples
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    print("RENDERED %s %.1fs (%dx%d, %d spp)" % (path, dt, res[0], res[1], samples))
    return dt


# --------------------------------------------------------------------------- #
# build one version
# --------------------------------------------------------------------------- #
def build_version(version, cfg):
    spec = SC.resolve_assembly(version, cfg)
    cmf = SC.load_cmf(cfg)
    sh = spec["shell"]
    art = spec["art"]
    floor_mm = sh["floor_z_mm"]
    thk_mm = sh["print_thickness_mm"]
    cmf_hex = {"shell": cmf["parts"]["shell"]["hex"],
               "plate": cmf["parts"]["plate"]["hex"],
               "button": cmf["parts"]["button"]["hex"]}
    t0 = time.time()
    sc = reset(48)
    col_job = new_collection("PRINTJOB_%s" % version.upper())
    col_bed = new_collection("BED")
    col_studio = new_collection("STUDIO")
    studio(sc, col_bed)

    def part_path(name):
        for p in spec["parts"]:
            if p["name"] == name:
                return p["path"]
        raise RuntimeError("part %r missing for %s" % (name, version))

    # ---- shell ----------------------------------------------------------- #
    shell = import_stl(part_path("shell"), "shell", col_job)
    shell.data.materials.clear()
    shell.data.materials.append(mat_hex("M_shell", cmf_hex["shell"], rough=0.6))
    shell_bb = recenter_unit([shell])

    # ---- plate unit: recessed plate (recess UP, native orientation) + print #
    plate = import_stl(spec["plate"]["path"], "plate", col_job)
    plate.data.materials.clear()
    plate.data.materials.append(mat_hex("M_plate", cmf_hex["plate"], rough=0.55))
    plate_lo, plate_hi = bbox([plate])
    plate_min_z = float(plate_lo[2])
    # pocket floor flatness / presence measured on the native plate STL
    pv = world_verts(plate)
    r = np.hypot(pv[:, 0], pv[:, 1])
    floor_ok = (np.abs(pv[:, 2] - floor_mm / 1000.0) < 0.02e-3) & (
        r < (sh["pocket_dia_mm"] / 2000.0) + 0.0005)
    floor_vertex_count = int(floor_ok.sum())
    floor_vertex_r_mm = float(r[floor_ok].max() * 1000.0) if floor_ok.any() else -1.0

    print_objs = []
    for i, pobj in enumerate(spec["print"]["objects"]):
        hexv = pobj.get("hex") or spec["print"]["palette"][i]
        ob = import_stl(pobj["path"], "ART_%s_%02d" % (art.upper(), i), col_job)
        ob.data.materials.clear()
        ob.data.materials.append(mat_hex("M_print_%02d_%s"
                                         % (i, str(hexv).lstrip("#")), hexv, rough=0.5))
        print_objs.append(ob)
    p_lo, p_hi = bbox(print_objs)
    print_min_z = float(p_lo[2])
    # shift print group so its bottom sits on the pocket floor (assembly coords)
    translate(print_objs, (0.0, 0.0, floor_mm / 1000.0 - print_min_z))
    # then shift plate+print together so the plate underside sits on the bed
    translate([plate] + print_objs, (0.0, 0.0, -plate_min_z))
    plate_unit = [plate] + print_objs
    plate_bb = recenter_unit(plate_unit)
    p_bottom_bed_mm = float(bbox(print_objs)[0][2] * 1000.0)
    p_top_bed_mm = float(bbox(print_objs)[1][2] * 1000.0)
    floor_bed_mm = floor_mm - plate_min_z * 1000.0
    floor_assert = abs(p_bottom_bed_mm - floor_bed_mm) < 1e-6
    print("PRINT_BOTTOM %s bed_z=%.6f  pocket_floor_bed_z=%.6f  native_floor=%.2f "
          "plate_min_z=%.2f  floor_verts=%d (r<=%.2f)"
          % (version, p_bottom_bed_mm, floor_bed_mm, floor_mm,
             plate_min_z * 1000.0, floor_vertex_count, floor_vertex_r_mm))
    if not floor_assert:
        raise RuntimeError("print bottom != pocket floor for %s" % version)
    if floor_vertex_count < 50:
        raise RuntimeError("plate pocket floor not found in %s STL" % version)

    # ---- button (square only) ------------------------------------------- #
    button = None
    button_bb = None
    if version == "square":
        button = import_stl(part_path("button"), "button", col_job)
        button.data.materials.clear()
        button.data.materials.append(mat_hex("M_button", cmf_hex["button"], rough=0.5))
        button_bb = recenter_unit([button])

    # ---- bed layout from measured bboxes (mm) ---------------------------- #
    def dim(bb):
        return (bb[1] - bb[0]) * 1000.0

    if version == "round":
        gap = MIN_GAP_MM                 # 110 + 5 + 103.935 = 218.935 <= 220
        units = [("shell", [shell], shell_bb), ("plate_unit", plate_unit, plate_bb)]
        widths = [dim(bb)[0] for _, _, bb in units]
        total = sum(widths) + gap * (len(units) - 1)
        x = -total / 2.0
        placements = {}
        for (name, objs, bb), w in zip(units, widths):
            cx = x + w / 2.0
            translate(objs, (cx / 1000.0, 0.0, 0.0))
            placements[name] = [round(cx, 3), 0.0]
            x += w + gap
    else:
        gap = 8.0                        # 100 + 8 + 100 = 208 <= 220, margins 6
        units = [("shell", [shell], shell_bb), ("plate_unit", plate_unit, plate_bb)]
        widths = [dim(bb)[0] for _, _, bb in units]
        total = sum(widths) + gap * (len(units) - 1)
        x = -total / 2.0
        placements = {}
        for (name, objs, bb), w in zip(units, widths):
            cx = x + w / 2.0
            translate(objs, (cx / 1000.0, 0.0, 0.0))
            placements[name] = [round(cx, 3), 0.0]
            x += w + gap
        # button below the row, computed from bboxes: 5 mm clear of the row bottom
        row_lo = min(bbox([shell])[0][1], bbox(plate_unit)[0][1])
        b_w = dim(button_bb)[1]
        cy = row_lo * 1000.0 - MIN_GAP_MM - b_w / 2.0
        translate([button], (0.0, cy / 1000.0, 0.0))
        placements["button"] = [0.0, round(cy, 3)]

    bpy.context.view_layer.update()

    # ---- validation: bed bbox, gaps, no overlap -------------------------- #
    unit_boxes = {}
    for name, objs, _ in units:
        unit_boxes[name] = bbox(objs)
    if button is not None:
        unit_boxes["button"] = bbox([button])
    all_objs = [shell] + plate_unit + ([button] if button else [])
    bed_lo, bed_hi = bbox(all_objs)
    bed_lo_mm = [round(float(v) * 1000.0, 4) for v in bed_lo]
    bed_hi_mm = [round(float(v) * 1000.0, 4) for v in bed_hi]

    def rect_gap(a, b):
        dx = max(a[0][0] - b[1][0], b[0][0] - a[1][0], 0.0) * 1000.0
        dy = max(a[0][1] - b[1][1], b[0][1] - a[1][1], 0.0) * 1000.0
        return math.hypot(dx, dy)

    names = list(unit_boxes)
    gaps, overlaps = [], []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            boxes = (unit_boxes[a], unit_boxes[b])
            ox = min(boxes[0][1][0], boxes[1][1][0]) - max(boxes[0][0][0], boxes[1][0][0])
            oy = min(boxes[0][1][1], boxes[1][1][1]) - max(boxes[0][0][1], boxes[1][0][1])
            g = rect_gap(*boxes)
            gaps.append({"between": [a, b], "gap_mm": round(g, 4)})
            if ox > 1e-9 and oy > 1e-9:
                overlaps.append({"between": [a, b],
                                 "overlap_mm": [round(ox * 1000.0, 4), round(oy * 1000.0, 4)]})

    half = BED_MM / 2.0
    overhang = {
        "x_min": bed_lo_mm[0] < -half, "x_max": bed_hi_mm[0] > half,
        "y_min": bed_lo_mm[1] < -half, "y_max": bed_hi_mm[1] > half,
    }
    min_gap = min(g["gap_mm"] for g in gaps) if gaps else 0.0
    checks = {
        "bed_fits_220": bed_hi_mm[0] - bed_lo_mm[0] <= BED_MM + 1e-6
        and bed_hi_mm[1] - bed_lo_mm[1] <= BED_MM + 1e-6,
        "no_bed_overhang": not any(overhang.values()),
        "gaps_ge_5mm": min_gap >= MIN_GAP_MM - 0.01,
        "no_bbox_overlap": not overlaps,
        "print_bottom_on_pocket_floor": floor_assert,
        "print_thickness_ok": abs((p_top_bed_mm - p_bottom_bed_mm) - thk_mm) < 0.02,
        "parts_on_bed_z": all(abs(float(bbox(objs)[0][2])) < 1e-6 for _, objs, _ in units)
        and (button is None or abs(float(bbox([button])[0][2])) < 1e-6),
    }
    for k, v in checks.items():
        if not v:
            raise RuntimeError("layout check failed for %s: %s" % (version, k))
    print("LAYOUT %s bed_bbox=%s..%s min_gap=%.2fmm gaps=%s"
          % (version, bed_lo_mm, bed_hi_mm, min_gap, gaps))

    # ---- cameras / renders ---------------------------------------------- #
    top = make_camera("top", (0, 0, 0.50), (0, 0, 0), ortho=BED_MM / 1000.0 * 1.06)
    iso = make_camera("iso", (0.20, -0.26, 0.24), (0, -0.01, 0.008), lens=45)
    ver_dir = os.path.join(OUT, version)
    os.makedirs(ver_dir, exist_ok=True)
    t_iso = render_view(sc, iso, os.path.join(ver_dir, "print_iso.png"),
                        (1600, 1100), 48)
    t_top = render_view(sc, top, os.path.join(ver_dir, "print_top.png"),
                        (1600, 1200), 32)

    # ---- measured layout json ------------------------------------------- #
    def bbox_mm(objs):
        lo, hi = bbox(objs)
        return {"min": [round(float(v) * 1000.0, 3) for v in lo],
                "max": [round(float(v) * 1000.0, 3) for v in hi],
                "size": [round(float(hi[i] - lo[i]) * 1000.0, 3) for i in range(3)]}

    layout = {
        "version": version, "art": art,
        "generated_by": "render/print/appearance/print_layout_appearance.py",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "blender": bpy.app.version_string,
        "bed_size_mm": [BED_MM, BED_MM],
        "bed_bbox_mm": {"min": bed_lo_mm, "max": bed_hi_mm,
                        "size": [round(bed_hi_mm[i] - bed_lo_mm[i], 4) for i in range(3)]},
        "units": {
            "shell": {"objects": ["shell"], "bbox_mm": bbox_mm([shell]),
                      "placement_xy_mm": placements["shell"],
                      "orientation": "bed down (as designed)"},
            "plate_unit": {
                "objects": ["plate"] + [o.name for o in print_objs],
                "bbox_mm": bbox_mm(plate_unit),
                "placement_xy_mm": placements["plate_unit"],
                "orientation": "plate recess UP, print nested in recess (in-place bonding)",
                "plate_min_z_native_mm": round(plate_min_z * 1000.0, 3),
                "pocket_floor_native_z_mm": floor_mm,
                "pocket_floor_bed_z_mm": round(floor_bed_mm, 4),
                "print_bottom_bed_z_mm": round(p_bottom_bed_mm, 4),
                "print_top_bed_z_mm": round(p_top_bed_mm, 4),
                "print_thickness_mm": thk_mm,
                "pocket_floor_vertices_found": floor_vertex_count,
                "pocket_floor_vertex_max_radius_mm": round(floor_vertex_r_mm, 3),
                "print_objects": [{"name": o.name, "hex": spec["print"]["objects"][i].get("hex")}
                                  for i, o in enumerate(print_objs)],
            },
        },
        "gaps_mm": gaps,
        "min_gap_mm": round(min_gap, 4),
        "overlaps": overlaps,
        "overhang": overhang,
        "checks": checks,
        "support_note": (
            "PROVISIONAL (not physically tested): the plate is printed recess-UP so the "
            "Kromacut print can be nested in it; the plate underside skirt and force "
            "column then hang below the plate body, so the slicer needs supports under "
            "the plate body (tree supports recommended)."),
        "support_free_alternative": (
            "Plate flipped (recess down, flat face on bed) + print printed separately, "
            "then press-fit/glue after printing - NOT in-place bonding, and the plate "
            "then needs no supports."),
        "renders": {"iso": "print_iso.png", "top": "print_top.png",
                    "iso_seconds": round(t_iso, 2), "top_seconds": round(t_top, 2),
                    "iso_size": [1600, 1100], "top_size": [1600, 1200]},
        "sources": {
            "shell_stl": os.path.relpath(part_path("shell"), ROOT),
            "plate_stl": os.path.relpath(spec["plate"]["path"], ROOT),
            "print_stl_dir": os.path.relpath(spec["print"]["dir"], ROOT),
            "shell_json": os.path.relpath(spec["shell"]["shell_json"], ROOT)
            if spec["shell"].get("shell_json") else None,
            "print_manifest": os.path.relpath(spec["print"]["manifest_path"], ROOT)
            if spec["print"].get("manifest_path") else None,
            "assembled_3mf": "appearance/build/3mf/%s.3mf" % version,
        },
        "total_seconds": round(t_iso + t_top, 2),
    }
    with open(os.path.join(ver_dir, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=2, ensure_ascii=False)
    print("WROTE %s" % os.path.join(ver_dir, "layout.json"))
    return layout


def main():
    cfg = SC.load_config()
    t0 = time.time()
    for v in VERSIONS:
        print("=" * 78)
        print("PRINT LAYOUT", v)
        build_version(v, cfg)
    print("PRINT STAGE LAYOUT DONE %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
