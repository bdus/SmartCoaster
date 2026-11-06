#!/usr/bin/env python3
"""3D-print delivery stage (task-6) — bed layout in the REAL print orientation.

Physics (user correction):
  * the Kromacut print's artwork face must be the FIRST layer on the build plate,
    so the plate+print unit is printed TOP-FACE-DOWN: the plate's original top
    face (rim) lies on the bed, the pocket/recess opens DOWNWARD onto the bed and
    the print (art face down) is nested inside it.  After printing, the finished
    part is flipped over.  In the sliced orientation you see the BACK of the
    print, not the art - that is correct.
  * the button is laid LYING (axis horizontal = along X) on the bed.
  * the shell is unchanged (bottom down).

The delivered STLs are BAKED in this orientation (rigid transform: triangle count
and volume preserved).  This script builds the bed scene, measures, asserts and
renders iso/top views; it writes render/print/appearance/<v>/layout.json with the
transforms, placements, pose numbers and checks used by the STL/3MF/sheet stage.

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
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "appearance", "render"))
import scene_common as SC      # noqa: E402
import transform_common as TC  # noqa: E402

OUT = HERE
BED_MM = 220.0
MIN_GAP_MM = 5.0
PRINT_NEST_Z_MM = 0.05        # designed top gap, now just above the bed
VERSIONS = ("round", "square")


# --------------------------------------------------------------------------- #
# blender helpers
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


def apply_mm_matrix(obj, M):
    """Apply a mm-space row-vector transform to an STL-imported object."""
    R = Matrix([[float(M[i][j]) for j in range(3)] for i in range(3)]).to_4x4()
    t = Vector((M[3, 0] / 1000.0, M[3, 1] / 1000.0, M[3, 2] / 1000.0))
    obj.matrix_world = Matrix.Translation(t) @ R @ obj.matrix_world
    bpy.context.view_layer.update()


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


def recenter_unit(objs):
    lo, hi = bbox(objs)
    translate(objs, (-(lo[0] + hi[0]) / 2.0, -(lo[1] + hi[1]) / 2.0, -lo[2]))
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
    bpy.ops.mesh.primitive_plane_add(size=BED_MM / 1000.0, location=(0, 0, -0.0004))
    bed = bpy.context.object
    bed.name = "bed_220"
    bed.data.materials.append(mat_rgb("M_bed", (0.055, 0.060, 0.070), 0.9))
    for c in list(bed.users_collection):
        c.objects.unlink(bed)
    col.objects.link(bed)
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
# source data + transforms (computed with numpy in mm, verified in blender)
# --------------------------------------------------------------------------- #
def source_data(version, spec):
    """Read source STLs and compute the baked (print-pose) transforms."""
    sh = spec["shell"]
    mech = {"round": "lumen", "square": "square_v1"}[version]
    parts = {p["name"]: p["path"] for p in spec["parts"]}
    out = {"version": version, "art": spec["art"], "sources": {},
           "transforms": {}, "expected": {}}

    def info(path):
        tris = TC.read_stl(path)
        lo, hi = TC.tri_bbox(tris)
        return {"path": path, "tris": tris, "lo": lo, "hi": hi,
                "count": len(tris), "volume": TC.volume_mm3(tris)}

    shell = info(parts["shell"])
    out["sources"]["shell"] = os.path.relpath(shell["path"], ROOT)
    out["transforms"]["shell"] = TC.bake_matrix(TC.ID, shell["lo"], shell["hi"])
    out["expected"]["shell"] = {"triangles": shell["count"],
                                "volume_mm3": shell["volume"],
                                "source_bbox": [shell["lo"], shell["hi"]]}

    plate = info(spec["plate"]["path"])
    out["sources"]["plate"] = os.path.relpath(plate["path"], ROOT)
    out["transforms"]["plate"] = TC.bake_matrix(TC.RX180, plate["lo"], plate["hi"])
    out["expected"]["plate"] = {"triangles": plate["count"],
                                "volume_mm3": plate["volume"],
                                "source_bbox": [plate["lo"], plate["hi"]]}

    plist = []
    for pobj in spec["print"]["objects"]:
        plist.append((pobj, info(pobj["path"])))
    g_lo = np.min([p["lo"] for _, p in plist], axis=0)
    g_hi = np.max([p["hi"] for _, p in plist], axis=0)
    M_print = TC.bake_matrix(TC.RX180, g_lo, g_hi)
    out["transforms"]["print_group"] = M_print
    out["expected"]["print"] = []
    for pobj, p in plist:
        hexv = "#" + str(pobj.get("hex") or "CCCCCC").lstrip("#").upper()
        lo2, hi2 = TC.rot_bbox(TC.RX180, p["lo"], p["hi"])
        out["expected"]["print"].append({
            "name": pobj["name"], "hex": hexv,
            "source": os.path.relpath(p["path"], ROOT),
            "triangles": p["count"], "volume_mm3": p["volume"],
            "source_bbox": [p["lo"], p["hi"]],
        })
    out["group_bbox"] = [g_lo, g_hi]

    if version == "square":
        button = info(parts["button"])
        out["sources"]["button"] = os.path.relpath(button["path"], ROOT)
        out["transforms"]["button"] = TC.bake_matrix(TC.RX90, button["lo"],
                                                     button["hi"])
        out["expected"]["button"] = {"triangles": button["count"],
                                     "volume_mm3": button["volume"],
                                     "source_bbox": [button["lo"], button["hi"]]}
    return out


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
    src = source_data(version, spec)
    print("SOURCE", version, "art", art, "floor", floor_mm, "thk", thk_mm)

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

    # ---- shell (unchanged print orientation: bottom down) --------------- #
    shell = import_stl(part_path("shell"), "shell", col_job)
    apply_mm_matrix(shell, src["transforms"]["shell"])
    shell.data.materials.clear()
    shell.data.materials.append(mat_hex("M_shell", cmf_hex["shell"], 0.6))
    shell_bb = bbox([shell])

    # ---- plate: 180 deg about X -> original top face on the bed ---------- #
    plate = import_stl(spec["plate"]["path"], "plate", col_job)
    apply_mm_matrix(plate, src["transforms"]["plate"])
    plate.data.materials.clear()
    plate.data.materials.append(mat_hex("M_plate", cmf_hex["plate"], 0.55))
    plate_bb = bbox([plate])
    pv = world_verts(plate)                            # after transform
    # transformed pocket-floor vertices: native floor plane maps to z = depth
    native = TC.apply_matrix(src["transforms"]["plate"],
                             TC.read_stl(spec["plate"]["path"]))
    pv_all = native.reshape(-1, 3)                     # mm
    rr = np.hypot(pv_all[:, 0], pv_all[:, 1])          # mm
    depth = sh["rim_z_mm"] - floor_mm
    pocket_r_mm = sh["pocket_dia_mm"] / 2.0 + 0.5      # mm
    floor_sel = (np.abs(pv_all[:, 2] - depth) < 0.01) & (rr < pocket_r_mm)
    pocket_floor_z = float(np.median(pv_all[floor_sel, 2])) if floor_sel.any() else None
    pocket_floor_vertices = int(floor_sel.sum())

    # ---- print: 180 deg about X (art face down) + nest +0.05 mm ---------- #
    print_objs = []
    M_print = src["transforms"]["print_group"]
    for i, pobj in enumerate(spec["print"]["objects"]):
        hexv = "#" + str(pobj.get("hex") or spec["print"]["palette"][i]).lstrip("#").upper()
        ob = import_stl(pobj["path"], "PRINT_%s_%02d" % (art.upper(), i), col_job)
        apply_mm_matrix(ob, M_print)
        ob.data.materials.clear()
        ob.data.materials.append(mat_hex("M_print_%02d_%s"
                                         % (i, hexv.lstrip("#")), hexv, 0.5))
        print_objs.append(ob)
    # nesting offset relative to the plate (designed 0.05 mm top gap)
    translate(print_objs, (0.0, 0.0, PRINT_NEST_Z_MM / 1000.0))
    plate_unit = [plate] + print_objs
    p_lo, p_hi = bbox(print_objs)
    art_face_z = float(p_lo[2] * 1000.0)
    print_back_z = float(p_hi[2] * 1000.0)

    # ---- button (square): lay it down, axis horizontal (X) --------------- #
    button = None
    if version == "square":
        button = import_stl(part_path("button"), "button", col_job)
        apply_mm_matrix(button, src["transforms"]["button"])
        button.data.materials.clear()
        button.data.materials.append(mat_hex("M_button", cmf_hex["button"], 0.5))
    button_dims = None
    if button is not None:
        bb = bbox([button])
        button_dims = (bb[1] - bb[0]) * 1000.0
        # lying FLAT like a coin: disc parallel to the bed, thickness (5.2 mm)
        # vertical -> z extent is the smallest dimension; x/y ~= 9 mm circle.
        if not (abs(button_dims[2] - 5.2) < 0.2
                and button_dims[2] < 0.8 * min(button_dims[0], button_dims[1])
                and abs(button_dims[0] - 9.0) < 0.3
                and abs(button_dims[1] - 9.0) < 0.3):
            raise RuntimeError("button is not lying flat (coin): dims %r"
                               % button_dims)
        print("BUTTON %s lying flat dims x=%.2f y=%.2f z=%.2f (z=thickness, "
              "visible front face DOWN)" % (version, *button_dims))

    # ---- pose assertions ------------------------------------------------- #
    plate_outer_z = float(plate_bb[0][2] * 1000.0)
    checks_pose = {
        "plate_outer_face_on_bed": abs(plate_outer_z) < 1e-3,
        "pocket_floor_depth_ok": pocket_floor_z is not None
        and abs(pocket_floor_z - depth) < 0.01,
        "print_art_face_at_0p05": abs(art_face_z - PRINT_NEST_Z_MM) < 1e-3,
        "print_back_on_pocket_floor": abs(print_back_z - depth) < 0.01,
        "print_thickness_ok": abs((print_back_z - art_face_z) - thk_mm) < 0.02,
        "pocket_floor_vertices_found": pocket_floor_vertices > 50,
        "button_lying_flat": button_dims is None or (
            abs(button_dims[2] - 5.2) < 0.2
            and button_dims[2] < 0.8 * min(button_dims[0], button_dims[1])),
    }
    checks_pose = {k: bool(v) for k, v in checks_pose.items()}
    for k, v in checks_pose.items():
        if not v:
            raise RuntimeError("%s: pose check failed: %s" % (version, k))
    print("POSE %s plate_outer_face_z=%.6f pocket_floor_z=%.4f print_art_face_z=%.4f "
          "print_back_z=%.4f depth=%.3f floor_verts=%d"
          % (version, plate_outer_z, pocket_floor_z, art_face_z, print_back_z,
             depth, pocket_floor_vertices))

    # ---- bed layout from measured bboxes --------------------------------- #
    def dim(bb):
        return (bb[1] - bb[0]) * 1000.0

    units = [("shell", [shell], shell_bb),
             ("plate_unit", plate_unit, bbox(plate_unit))]
    widths = [dim(bb)[0] for _, _, bb in units]
    gap = MIN_GAP_MM if version == "round" else 8.0
    total = sum(widths) + gap * (len(units) - 1)
    x = -total / 2.0
    placements = {}
    for (name, objs, bb), w in zip(units, widths):
        cx = x + w / 2.0
        translate(objs, (cx / 1000.0, 0.0, 0.0))
        placements[name] = [round(cx, 3), 0.0]
        x += w + gap
    if button is not None:
        row_lo = min(bbox([shell])[0][1], bbox(plate_unit)[0][1])
        b_w = dim(bbox([button]))[1]
        cy = row_lo * 1000.0 - MIN_GAP_MM - b_w / 2.0
        translate([button], (0.0, cy / 1000.0, 0.0))
        placements["button"] = [0.0, round(cy, 3)]
    bpy.context.view_layer.update()

    # ---- validation: bed bbox, gaps, no overlap -------------------------- #
    unit_boxes = {name: bbox(objs) for name, objs, _ in units}
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
            gaps.append({"between": [a, b], "gap_mm": round(rect_gap(*boxes), 4)})
            if ox > 1e-9 and oy > 1e-9:
                overlaps.append({"between": [a, b],
                                 "overlap_mm": [round(ox * 1000.0, 4),
                                                round(oy * 1000.0, 4)]})
    half = BED_MM / 2.0
    overhang = {"x_min": bed_lo_mm[0] < -half, "x_max": bed_hi_mm[0] > half,
                "y_min": bed_lo_mm[1] < -half, "y_max": bed_hi_mm[1] > half}
    min_gap = min(g["gap_mm"] for g in gaps) if gaps else 0.0
    checks = dict(checks_pose)
    checks.update({
        "bed_fits_220": bed_hi_mm[0] - bed_lo_mm[0] <= BED_MM + 1e-6
        and bed_hi_mm[1] - bed_lo_mm[1] <= BED_MM + 1e-6,
        "no_bed_overhang": not any(overhang.values()),
        "gaps_ge_5mm": min_gap >= MIN_GAP_MM - 0.01,
        "no_bbox_overlap": not overlaps,
        "parts_on_bed_z": all(abs(float(bbox(objs)[0][2])) < 1e-5
                              for _, objs, _ in units)
        and (button is None or abs(float(bbox([button])[0][2])) < 1e-5),
    })
    checks = {k: bool(v) for k, v in checks.items()}
    for k, v in checks.items():
        if not v:
            raise RuntimeError("layout check failed for %s: %s" % (version, k))
    print("LAYOUT %s bed_bbox=%s..%s min_gap=%.2fmm"
          % (version, bed_lo_mm, bed_hi_mm, min_gap))

    # ---- cameras / renders ---------------------------------------------- #
    top = make_camera("top", (0, 0, 0.50), (0, 0, 0),
                      ortho=BED_MM / 1000.0 * 1.06)
    iso = make_camera("iso", (0.20, -0.26, 0.26), (0, -0.01, 0.012), lens=45)
    ver_dir = os.path.join(OUT, version)
    os.makedirs(ver_dir, exist_ok=True)
    t_iso = render_view(sc, iso, os.path.join(ver_dir, "print_iso.png"),
                        (1600, 1100), 48)
    t_top = render_view(sc, top, os.path.join(ver_dir, "print_top.png"),
                        (1600, 1200), 32)

    # ---- layout json ----------------------------------------------------- #
    def bbox_mm(objs):
        lo, hi = bbox(objs)
        return {"min": [round(float(v) * 1000.0, 3) for v in lo],
                "max": [round(float(v) * 1000.0, 3) for v in hi],
                "size": [round(float(hi[i] - lo[i]) * 1000.0, 3) for i in range(3)]}

    def transform_json(M):
        return {k: ([[round(float(x), 9) for x in row] for row in v]
                    if k == "R" else [round(float(x), 6) for x in v])
                for k, v in TC.mat_lists(M).items()}

    print_expected = []
    for i, pobj in enumerate(spec["print"]["objects"]):
        hexv = "#" + str(pobj.get("hex") or spec["print"]["palette"][i]).lstrip("#").upper()
        print_expected.append({"name": pobj["name"], "hex": hexv,
                               "index": i + 1})
    layout = {
        "version": version, "art": art,
        "generated_by": "render/print/appearance/print_layout_appearance.py",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "blender": bpy.app.version_string,
        "bed_size_mm": [BED_MM, BED_MM],
        "bed_bbox_mm": {"min": bed_lo_mm, "max": bed_hi_mm,
                        "size": [round(bed_hi_mm[i] - bed_lo_mm[i], 4)
                                 for i in range(3)]},
        "print_pose": {
            "description": "plate+print printed TOP-FACE-DOWN: plate original top "
                           "face on the bed, recess opens downward, print art face "
                           "down inside the recess; finished part flipped afterwards",
            "plate_outer_face_z_mm": round(plate_outer_z, 6),
            "pocket_floor_z_mm": round(pocket_floor_z, 4),
            "print_art_face_z_mm": round(art_face_z, 4),
            "print_back_z_mm": round(print_back_z, 4),
            "print_thickness_mm": thk_mm,
            "pocket_floor_vertices_found": pocket_floor_vertices,
            "supports_required": False,
            "note": "no supports: the plate's original top face and the print art "
                    "face are the first layer on the bed (art face 0.05 mm above "
                    "the bed by design).",
        },
        "units": {
            "shell": {"objects": ["shell"], "bbox_mm": bbox_mm([shell]),
                      "placement_xy_mm": placements["shell"],
                      "orientation": "bottom down (as designed)"},
            "plate_unit": {
                "objects": ["plate"] + [o.name for o in print_objs],
                "bbox_mm": bbox_mm(plate_unit),
                "placement_xy_mm": placements["plate_unit"],
                "orientation": "plate flipped 180deg about X: recess DOWN, "
                               "original top face on the bed",
            },
        },
        "button": None,
        "gaps_mm": gaps, "min_gap_mm": round(min_gap, 4),
        "overlaps": overlaps, "overhang": overhang, "checks": checks,
        "bake_transforms": {
            "shell": transform_json(src["transforms"]["shell"]),
            "plate": transform_json(src["transforms"]["plate"]),
            "print_group": transform_json(src["transforms"]["print_group"]),
            "button": transform_json(src["transforms"]["button"])
            if version == "square" else None,
            "convention": "row-vector v' = v @ R.T + t, mm; rigid (rotation only)",
        },
        "sources": {
            "shell_stl": src["sources"]["shell"],
            "plate_stl": src["sources"]["plate"],
            "print_stl_dir": os.path.relpath(spec["print"]["dir"], ROOT),
            "shell_json": os.path.relpath(spec["shell"]["shell_json"], ROOT)
            if spec["shell"].get("shell_json") else None,
            "print_manifest": os.path.relpath(spec["print"]["manifest_path"], ROOT)
            if spec["print"].get("manifest_path") else None,
            "assembled_mockup_3mf": "appearance/build/3mf/%s.3mf" % version,
        },
        "renders": {"iso": "print_iso.png", "top": "print_top.png",
                    "iso_seconds": round(t_iso, 2),
                    "top_seconds": round(t_top, 2),
                    "iso_size": [1600, 1100], "top_size": [1600, 1200]},
        "total_seconds": round(t_iso + t_top, 2),
    }
    if button is not None:
        layout["button"] = {
            "objects": ["button"], "bbox_mm": bbox_mm([button]),
            "placement_xy_mm": placements["button"],
            "orientation": "lying FLAT like a coin: disc parallel to the bed, "
                           "thickness axis vertical (Z); z extent = 5.2 mm",
            "thickness_axis": "Z (vertical)",
            "face_down": "visible front/cap face (native -Y) DOWN on the bed; after "
                         "flipping the printed button the visible cap is the smooth "
                         "top (PROVISIONAL choice)",
            "expected_dims_mm": [9.0, 9.0, 5.2],
            "triangle_count": src["expected"]["button"]["triangles"],
        }
    with open(os.path.join(ver_dir, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=2, ensure_ascii=False)
    print("WROTE", os.path.join(ver_dir, "layout.json"))
    return layout


def main():
    cfg = SC.load_config()
    t0 = time.time()
    for v in VERSIONS:
        print("=" * 78)
        print("PRINT LAYOUT (task-6, art face down)", v)
        build_version(v, cfg)
    print("PRINT STAGE LAYOUT DONE %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
