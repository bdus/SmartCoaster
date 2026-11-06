#!/usr/bin/env python3
"""Bake + deliver the 3D-printable STLs (task-6) and the BED-LAYOUT 3MF.

Physics: print TOP-FACE-DOWN.  The plate is rotated 180 deg about X so its
original top face (rim) lies on the bed and the recess opens downward; the print
is rotated 180 deg about X too (art face down) and nested in the recess with the
designed 0.05 mm top gap now just above the bed; the shell stays bottom-down; the
square button is laid down (axis horizontal, along X).

Delivered (flat folder, ONE directory):
  render/print/stl/<version>_shell.stl
  render/print/stl/<version>_plate_recessed.stl
  render/print/stl/<version>_button.stl                        (square only)
  render/print/stl/<version>_print_filament_<n>_<HEX>.stl      (6 / 7)
  render/print/stl/CHECKSUMS.sha256
  render/print/stl/README.md
  render/print/stl/delivery.json
and the sliceable bed-layout 3MF per version:
  render/print/appearance/<v>/PRINT_READY.3mf   (shell + flipped plate + nested
                                                 print components + lying button)

Every delivered STL is verified against its source: triangle count equal, volume
equal, bbox == rigidly transformed source bbox, min z == 0; the rigid transform
(R, t) and the source sha256 are stored in delivery.json.  The 3MF is read back
and validated (objects/components/colours/Z ranges/bed bbox).

Run:  python3 render/print/appearance/make_stl_delivery.py
"""
import json
import os
import shutil
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "appearance", "render"))
import scene_common as SC      # noqa: E402
import transform_common as TC  # noqa: E402

STL_DIR = os.path.join(ROOT, "render", "print", "stl")
VERSIONS = ("round", "square")
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MODEL_REL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
IDENTITY = (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0)
WELD = {"print": False}   # weld vertices only, never drop triangles


def load_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def bbox_mm(tris):
    lo, hi = TC.tri_bbox(tris)
    return {"min": [round(float(x), 3) for x in lo],
            "max": [round(float(x), 3) for x in hi],
            "size": [round(float(hi[i] - lo[i]), 3) for i in range(3)]}


def check_rigid(tris, M, src, name):
    """Verify a baked triangle set against its source + rigid transform."""
    out = TC.apply_matrix(M, tris)
    lo, hi = TC.tri_bbox(out)
    exp_lo, exp_hi = TC.rot_bbox(M[:3, :3], *TC.tri_bbox(tris))
    exp_lo = exp_lo + M[3, :3]
    exp_hi = exp_hi + M[3, :3]
    errs = []
    if len(out) != len(tris):
        errs.append("triangle count %d != %d" % (len(out), len(tris)))
    vol_in = TC.volume_mm3(tris)
    vol_out = TC.volume_mm3(out)
    if abs(vol_out - vol_in) > max(1e-6 * vol_in, 0.01):
        errs.append("volume %.6f != %.6f" % (vol_out, vol_in))
    if np.max(np.abs(lo - exp_lo)) > 1e-3 or np.max(np.abs(hi - exp_hi)) > 1e-3:
        errs.append("bbox %r..%r != rotated source %r..%r"
                    % (lo, hi, exp_lo, exp_hi))
    if abs(float(lo[2])) > 1e-6:
        errs.append("min z %.6f != 0" % lo[2])
    if errs:
        raise RuntimeError("bake check failed for %s: %s" % (name, "; ".join(errs)))
    return {"triangles": int(len(out)), "source_triangles": int(len(tris)),
            "volume_mm3": round(vol_out, 3),
            "source_volume_mm3": round(vol_in, 3),
            "min_z_mm": 0.0,
            "bbox_mm": bbox_mm(out),
            "expected_bbox_mm": {"min": [round(float(x), 3) for x in exp_lo],
                                 "max": [round(float(x), 3) for x in exp_hi]}}


# --------------------------------------------------------------------------- #
# 3MF bed-layout writer
# --------------------------------------------------------------------------- #
def _f(v):
    s = "%.4f" % float(v)
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def weld(tris):
    """Vertices welded, EVERY triangle kept (interface caps are intentional)."""
    flat = np.asarray(tris, dtype=np.float64).reshape(-1, 3)
    key = np.round(flat, 6)
    uniq, inverse = np.unique(key, axis=0, return_inverse=True)
    verts = np.zeros_like(uniq)
    verts[inverse] = flat
    faces = inverse.reshape(-1, 3).astype(np.int64)
    return verts, faces


def write_3mf_bedlayout(path, version, baked, layout, cmf_hex, art_hexes, meta):
    """baked: {'shell':tris,'plate':tris,'button':tris|None,'print':[(name,hex,tris)]}"""
    objects = []
    materials = []
    mat_index = {}

    def mat_for(name, hexv):
        key = (name, hexv)
        if key not in mat_index:
            mat_index[key] = len(materials)
            materials.append({"name": name, "hex": hexv})
        return mat_index[key]

    nid = 2
    def mesh_obj(name, tris, hexv):
        nonlocal nid
        verts, faces = weld(tris)
        ob = {"id": nid, "name": name, "verts": verts, "tris": faces,
              "mat": mat_for(name, hexv)}
        objects.append(ob)
        nid += 1
        return ob

    placements = layout["units"]
    shell = mesh_obj("SHELL", baked["shell"], cmf_hex["shell"])
    shell["item_transform"] = (1, 0, 0, 0, 1, 0, 0, 0, 1,
                               placements["shell"]["placement_xy_mm"][0],
                               placements["shell"]["placement_xy_mm"][1], 0)
    plate = mesh_obj("PLATE_RECESSED_FLIPPED", baked["plate"], cmf_hex["plate"])
    plate["item_transform"] = (1, 0, 0, 0, 1, 0, 0, 0, 1,
                               placements["plate_unit"]["placement_xy_mm"][0],
                               placements["plate_unit"]["placement_xy_mm"][1], 0)
    button = None
    if baked.get("button") is not None:
        bpl = layout["button"]["placement_xy_mm"]
        button = mesh_obj("BUTTON_LYING", baked["button"], cmf_hex["button"])
        button["item_transform"] = (1, 0, 0, 0, 1, 0, 0, 0, 1, bpl[0], bpl[1], 0)
    comps = []
    for name, hexv, tris in baked["print"]:
        ob = mesh_obj(name, tris, hexv)
        ob["build_item"] = False
        comps.append(ob["id"])
    assembly = {"id": nid, "name": "PRINT_ART_%s" % layout["art"],
                "components": comps,
                "item_transform": (1, 0, 0, 0, 1, 0, 0, 0, 1,
                                   placements["plate_unit"]["placement_xy_mm"][0],
                                   placements["plate_unit"]["placement_xy_mm"][1],
                                   layout["print_pose"]["print_art_face_z_mm"])}
    nid += 1
    objects.append(assembly)

    parts = ['<?xml version="1.0" encoding="UTF-8"?>\n',
             '<model unit="millimeter" xml:lang="en-US" xmlns="%s">\n' % CORE_NS]
    for k, v in meta.items():
        parts.append('  <metadata name="%s">%s</metadata>\n' % (_esc(k), _esc(v)))
    parts.append("  <resources>\n    <basematerials id=\"1\">\n")
    for m in materials:
        parts.append('      <base name="%s" displaycolor="%sFF"/>\n'
                     % (_esc(m["name"]), m["hex"]))
    parts.append("    </basematerials>\n")
    for ob in objects:
        if ob.get("components"):
            parts.append('    <object id="%d" type="model" name="%s">\n'
                         % (ob["id"], _esc(ob["name"])))
            parts.append("      <components>\n")
            for cid in ob["components"]:
                parts.append('        <component objectid="%d"/>\n' % cid)
            parts.append("      </components>\n    </object>\n")
            continue
        parts.append('    <object id="%d" type="model" name="%s" pid="1" '
                     'pindex="%d">\n' % (ob["id"], _esc(ob["name"]), ob["mat"]))
        parts.append("      <mesh>\n        <vertices>\n")
        for v in ob["verts"]:
            parts.append('          <vertex x="%s" y="%s" z="%s"/>\n'
                         % (_f(v[0]), _f(v[1]), _f(v[2])))
        parts.append("        </vertices>\n        <triangles>\n")
        for t in ob["tris"]:
            parts.append('          <triangle v1="%d" v2="%d" v3="%d"/>\n'
                         % (int(t[0]), int(t[1]), int(t[2])))
        parts.append("        </triangles>\n      </mesh>\n    </object>\n")
    parts.append("  </resources>\n  <build>\n")
    for ob in objects:
        if ob.get("components") or ob.get("build_item") is False:
            if ob.get("components"):
                tr = ob["item_transform"]
                parts.append('    <item objectid="%d" transform="%s"/>\n'
                             % (ob["id"], " ".join(_f(x) for x in tr)))
            continue
        tr = ob["item_transform"]
        parts.append('    <item objectid="%d" transform="%s"/>\n'
                     % (ob["id"], " ".join(_f(x) for x in tr)))
    parts.append("  </build>\n</model>\n")
    xml = "".join(parts)
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<Types xmlns="%s">\n  <Default Extension="rels" '
          'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
          '  <Default Extension="model" '
          'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
          '</Types>\n' % CT_NS)
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="%s">\n  <Relationship Id="rel0" '
            'Target="/3D/3dmodel.model" Type="%s"/>\n</Relationships>\n'
            % (REL_NS, MODEL_REL))
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", xml)
        z.writestr("Metadata/SmartCoaster.txt",
                   meta.get("Description", "") + "\n")
    os.replace(tmp, path)


def mat4(tr):
    m = [float(x) for x in tr]
    return np.array([[m[0], m[1], m[2], 0.0],
                     [m[3], m[4], m[5], 0.0],
                     [m[6], m[7], m[8], 0.0],
                     [m[9], m[10], m[11], 1.0]])


def validate_3mf(path, version, layout, filament_expected):
    res = {"file": os.path.relpath(path, ROOT), "ok": True, "errors": [],
           "warnings": []}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        root = ET.fromstring(z.read("3D/3dmodel.model"))
        ET.fromstring(z.read("[Content_Types].xml"))
        ET.fromstring(z.read("_rels/.rels"))
    res["members"] = names
    res["unit"] = root.get("unit")
    if res["unit"] != "millimeter":
        res["errors"].append("unit %r != millimeter" % res["unit"])
    mats = []
    for group in root.iter("{%s}basematerials" % CORE_NS):
        for b in group.findall("{%s}base" % CORE_NS):
            mats.append({"name": b.get("name"), "color": b.get("displaycolor")})
    res["materials"] = mats
    objs = {}
    for obj in root.iter("{%s}object" % CORE_NS):
        oid = int(obj.get("id"))
        mesh = obj.find("{%s}mesh" % CORE_NS)
        comps_el = obj.find("{%s}components" % CORE_NS)
        ent = {"id": oid, "name": obj.get("name"), "verts": [], "tris": [],
               "components": [], "pid": obj.get("pid"),
               "pindex": obj.get("pindex")}
        if mesh is not None:
            v_el = mesh.find("{%s}vertices" % CORE_NS)
            t_el = mesh.find("{%s}triangles" % CORE_NS)
            ent["verts"] = [(float(ve.get("x")), float(ve.get("y")),
                             float(ve.get("z"))) for ve in
                            v_el.findall("{%s}vertex" % CORE_NS)]
            ent["tris"] = [(int(te.get("v1")), int(te.get("v2")),
                            int(te.get("v3"))) for te in
                           t_el.findall("{%s}triangle" % CORE_NS)]
        elif comps_el is not None:
            for c in comps_el.findall("{%s}component" % CORE_NS):
                tr = c.get("transform")
                ent["components"].append((int(c.get("objectid")),
                                          [float(x) for x in tr.split()]
                                          if tr else list(IDENTITY)))
        else:
            res["errors"].append("object %r has no mesh/components" % obj.get("name"))
        objs[oid] = ent
    items = []
    for it in root.iter("{%s}item" % CORE_NS):
        tr = it.get("transform")
        items.append((int(it.get("objectid")),
                      [float(x) for x in tr.split()] if tr else list(IDENTITY)))
    res["object_count"] = len(objs)
    res["build_items"] = len(items)
    mesh_objs = [o for o in objs.values() if o["tris"]]
    res["total_triangles"] = sum(len(o["tris"]) for o in mesh_objs)
    if res["total_triangles"] <= 0:
        res["errors"].append("zero triangles")

    lo = [1e18] * 3
    hi = [-1e18] * 3
    world = {}
    print_names = set()
    for oid, tr in items:
        top = objs.get(oid)
        if top is None:
            res["errors"].append("build item -> missing object %d" % oid)
            continue
        m_item = mat4(tr)
        if top["components"]:
            for cid, ctr in top["components"]:
                comp = objs.get(cid)
                if comp is None:
                    res["errors"].append("component missing object %d" % cid)
                    continue
                v = np.asarray(comp["verts"], dtype=float)
                w = v @ (mat4(ctr) @ m_item)[:3, :3].T + (mat4(ctr) @ m_item)[3, :3]
                for k in range(3):
                    lo[k] = min(lo[k], float(w[:, k].min()))
                    hi[k] = max(hi[k], float(w[:, k].max()))
                world[comp["name"]] = [float(w[:, 2].min()), float(w[:, 2].max())]
                print_names.add(comp["name"])
                # per-filament material check
                if comp["pid"] == "1" and comp["pindex"] is not None:
                    mat = mats[int(comp["pindex"])]
                    want = filament_expected.get(comp["name"])
                    if want and not mat["color"].upper().startswith(want + "FF"):
                        res["errors"].append("filament %r colour %r != %r"
                                             % (comp["name"], mat["color"], want))
                else:
                    res["errors"].append("filament %r has no pid/pindex"
                                         % comp["name"])
        else:
            v = np.asarray(top["verts"], dtype=float)
            w = v @ m_item[:3, :3].T + m_item[3, :3]
            for k in range(3):
                lo[k] = min(lo[k], float(w[:, k].min()))
                hi[k] = max(hi[k], float(w[:, k].max()))
            world[top["name"]] = [float(w[:, 2].min()), float(w[:, 2].max())]

    res["bbox_mm"] = {"min": [round(v, 3) for v in lo],
                      "max": [round(v, 3) for v in hi],
                      "size": [round(hi[i] - lo[i], 3) for i in range(3)]}
    if max(abs(lo[0]), abs(lo[1]), abs(hi[0]), abs(hi[1])) > 110.0001:
        res["errors"].append("bed overhang: bbox %r" % res["bbox_mm"])
    if res["bbox_mm"]["size"][0] > 220.0001 or res["bbox_mm"]["size"][1] > 220.0001:
        res["errors"].append("bed bbox > 220 mm")

    # print components: nested in the recess, art face just above the bed
    art = layout["print_pose"]["print_art_face_z_mm"]
    depth = layout["print_pose"]["pocket_floor_z_mm"]
    print_keys = sorted(print_names)
    zmin_print = min([world[k][0] for k in print_keys], default=None)
    zmax_print = max([world[k][1] for k in print_keys], default=None)
    res["print_world_z"] = {"min": zmin_print, "max": zmax_print,
                            "art_face_expected": art,
                            "pocket_floor_expected": depth}
    if zmin_print is None:
        res["errors"].append("no print components found")
    else:
        if abs(zmin_print - art) > 1e-3:
            res["errors"].append("print art face z %.4f != %.4f" % (zmin_print, art))
        if zmax_print > depth + 1e-3:
            res["errors"].append("print back z %.4f above pocket floor %.4f"
                                 % (zmax_print, depth))
    res["z_ranges_mm"] = {k: [round(v[0], 4), round(v[1], 4)]
                          for k, v in world.items()}
    exp_parts = {"round": {"SHELL", "PLATE_RECESSED_FLIPPED"}, "square": {
        "SHELL", "PLATE_RECESSED_FLIPPED", "BUTTON_LYING"}}
    for n in exp_parts[version]:
        if n not in world:
            res["errors"].append("missing build part %r" % n)
    res["filament_count"] = len(print_keys)
    if len(print_keys) != len(filament_expected):
        res["errors"].append("filament count %d != %d"
                             % (len(print_keys), len(filament_expected)))
    res["ok"] = not res["errors"]
    return res


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    cfg = SC.load_config()
    os.makedirs(STL_DIR, exist_ok=True)
    t0 = time.time()
    expected_files = set(["CHECKSUMS.sha256", "README.md", "delivery.json"])
    delivery = {"schema": "smartcoaster.print-delivery/v2",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "folder": os.path.relpath(STL_DIR, ROOT),
                "note": "STLs are BAKED in the real print orientation "
                        "(plate+print top-face-down, art face on the first layer, "
                        "button lying axis-horizontal). Rigid transforms: triangle "
                        "count + volume preserved; see transform in each entry.",
                "versions": {}}
    all_entries = []
    three_mf = {}
    for version in VERSIONS:
        spec = SC.resolve_assembly(version, cfg)
        layout = load_json(os.path.join(HERE, version, "layout.json"))
        T = layout["bake_transforms"]
        parts = {p["name"]: p["path"] for p in spec["parts"]}
        cmf = SC.load_cmf(cfg)
        cmf_hex = {"shell": "#" + cmf["parts"]["shell"]["hex"].lstrip("#").upper(),
                   "plate": "#" + cmf["parts"]["plate"]["hex"].lstrip("#").upper(),
                   "button": "#" + cmf["parts"]["button"]["hex"].lstrip("#").upper()}
        entries = []

        def baked_entry(src, part, dest_name, M_json, hexv):
            M = np.eye(4)
            M[:3, :3] = np.array(M_json["R"], dtype=float)
            M[3, :3] = np.array(M_json["t"], dtype=float)
            tris = TC.read_stl(src)
            check = check_rigid(tris, M, src, dest_name)
            out = TC.apply_matrix(M, tris)
            dst = os.path.join(STL_DIR, dest_name)
            TC.write_stl(dst, out, header=("SmartCoaster %s %s print-pose"
                                           % (version, part)).encode())
            entry = {
                "file": dest_name,
                "path": os.path.relpath(dst, ROOT),
                "version": version, "part": part, "material_hex": hexv,
                "source": os.path.relpath(src, ROOT),
                "source_sha256": TC.sha256_file(src),
                "bytes": os.path.getsize(dst),
                "sha256": TC.sha256_file(dst),
                "transform": M_json,
                **check,
            }
            entries.append(entry)
            expected_files.add(dest_name)
            print("BAKED %-10s %-58s %10d B  min_z=%.6f  tris=%d  vol=%.1f mm3"
                  % (version, dest_name, entry["bytes"], entry["min_z_mm"],
                     entry["triangles"], entry["volume_mm3"]))
            return entry, out

        shell_e, shell_t = baked_entry(parts["shell"], "shell",
                                       "%s_shell.stl" % version,
                                       T["shell"], cmf_hex["shell"])
        plate_e, plate_t = baked_entry(spec["plate"]["path"], "plate_recessed",
                                       "%s_plate_recessed.stl" % version,
                                       T["plate"], cmf_hex["plate"])
        button_e = button_t = None
        if version == "square":
            button_e, button_t = baked_entry(parts["button"], "button",
                                             "%s_button.stl" % version,
                                             T["button"], cmf_hex["button"])
        print_list = []
        for i, pobj in enumerate(spec["print"]["objects"]):
            hexv = "#" + str(pobj.get("hex") or spec["print"]["palette"][i]).lstrip("#").upper()
            name = "%s_print_filament_%d_%s.stl" % (version, i + 1,
                                                    hexv.lstrip("#"))
            e, tris = baked_entry(pobj["path"], "print_filament", name,
                                  T["print_group"], hexv)
            e["filament_index"] = i + 1
            print_list.append((e, tris))
        # note: same transform for every filament keeps the art aligned
        delivery["versions"][version] = {
            "art": layout["art"],
            "print_pose": layout["print_pose"],
            "bed_bbox_mm": layout["bed_bbox_mm"],
            "placements": {k: v["placement_xy_mm"] for k, v in layout["units"].items()},
            "button": layout.get("button"),
            "entries": entries,
            "checks": layout["checks"],
            "sources": layout["sources"],
        }
        all_entries.extend(entries)

        # ---- sliceable bed-layout 3MF ------------------------------------ #
        three_mf_path = os.path.join(HERE, version, "PRINT_READY.3mf")
        meta = {
            "Title": "SmartCoaster %s bed layout (print pose, art face down)"
                     % version,
            "Designer": "SmartCoaster print-delivery stage (task-6)",
            "Description": "SLICEABLE BED LAYOUT on a 220x220 mm bed: shell "
                           "bottom-down, plate flipped 180deg (recess down, "
                           "original top face on the bed), Kromacut print nested "
                           "with its art face down (first layer), button lying. "
                           "Finished part is flipped over after printing. "
                           "Assembled final-pose digital mockup: "
                           "appearance/build/3mf/%s.3mf" % version,
            "Application": "Bambu Studio / 3MF core spec",
        }
        write_3mf_bedlayout(three_mf_path, version,
                            {"shell": shell_t, "plate": plate_t,
                             "button": button_t,
                             "print": [(e["file"], e["material_hex"], t)
                                       for e, t in print_list]},
                            layout, cmf_hex, None, meta)
        fil_expected = {e["file"]: e["material_hex"] for e, _ in print_list}
        val = validate_3mf(three_mf_path, version, layout, fil_expected)
        val["bytes"] = os.path.getsize(three_mf_path)
        val["path"] = os.path.relpath(three_mf_path, ROOT)
        three_mf[version] = val
        print("3MF %-7s %s | objects=%d components=%d build_items=%d tris=%d "
              "bbox=%s" % (version, "OK" if val["ok"] else "FAIL",
                           val["object_count"], val["filament_count"],
                           val["build_items"], val["total_triangles"],
                           val["bbox_mm"]["size"]))
        for e in val["errors"]:
            print("    ERROR", e)

    # ---- cleanup stale files / old per-version stl dirs ------------------ #
    for f in os.listdir(STL_DIR):
        p = os.path.join(STL_DIR, f)
        if os.path.isfile(p) and f not in expected_files:
            os.remove(p)
            print("REMOVED stale", f)
    for v in VERSIONS:
        for d in (os.path.join(HERE, v, "stl"),
                  os.path.join(HERE, v, "CHECKSUMS.sha256")):
            if os.path.isdir(d):
                shutil.rmtree(d)
                print("REMOVED old per-version dir", os.path.relpath(d, ROOT))
            elif os.path.isfile(d):
                os.remove(d)
                print("REMOVED old per-version file", os.path.relpath(d, ROOT))

    # ---- CHECKSUMS + README + delivery.json ----------------------------- #
    lines = ["%s  %s" % (e["sha256"], e["file"]) for e in all_entries]
    cks = os.path.join(STL_DIR, "CHECKSUMS.sha256")
    with open(cks, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    delivery["checksums"] = os.path.relpath(cks, ROOT)
    delivery["file_count"] = len(all_entries)
    delivery["total_bytes"] = sum(e["bytes"] for e in all_entries)
    delivery["all_min_z_zero"] = all(abs(e["min_z_mm"]) < 1e-6 for e in all_entries)
    delivery["all_rigid_checks"] = all(
        e["triangles"] == e["source_triangles"]
        and abs(e["volume_mm3"] - e["source_volume_mm3"])
        <= max(1e-6 * abs(e["source_volume_mm3"]), 0.01)
        for e in all_entries)
    delivery["three_mf"] = three_mf

    md = ["# render/print/stl — 3D 打印交付 STL（两种外观版本）", "",
          "> **打印姿态：顶板+印花整体翻转（凹槽朝下）**。第一层 = 印花正面 / 顶板外表面贴床；"
          "印花正面在床面上方 0.05 mm（设计顶隙）。打印完成后整体翻面即为成品外观。", "",
          "所有文件为 `cp` 副本/烘焙件（非软链）；每件均通过 triangle-count / volume / "
          "bbox=刚性旋转源 / min z=0 校验，变换矩阵与源 sha256 见 `delivery.json`。", "",
          "## 文件", "", "| 文件 | 版本 | 零件 | 材料 | 三角数 | 体积 mm³ | min z | 字节 |",
          "|---|---|---|---|---|---|---|---|"]
    for e in all_entries:
        md.append("| `%s` | %s | %s | %s | %d | %.1f | %.6f | %d |"
                  % (e["file"], e["version"], e["part"], e["material_hex"],
                     e["triangles"], e["volume_mm3"], e["min_z_mm"], e["bytes"]))
    md += ["", "## 变换（打印姿态，mm，行向量 v' = v @ R.T + t）", ""]
    for v in VERSIONS:
        bt = load_json(os.path.join(HERE, v, "layout.json"))["bake_transforms"]
        md.append("- **%s**：plate = 180° about X；print = 180° about X（同一变换用于 6/7 个"
                  "印花件，保持相对位置）；shell 不变；%s"
                  % (v, "button = 90° about Z（轴水平沿 X，侧躺）" if v == "square"
                     else "无按键"))
        md.append("  - plate R=%s t=%s" % (bt["plate"]["R"], bt["plate"]["t"]))
        md.append("  - print R=%s t=%s" % (bt["print_group"]["R"],
                                           bt["print_group"]["t"]))
    md += ["", "## Bambu Studio 导入顺序", "",
           "1. 导入本目录全部 `*_print_filament_*.stl`（6 / 7 个印花色），或直接使用 "
           "`render/print/appearance/<v>/PRINT_READY.3mf`（已排好床面）；",
           "2. 每个印花对象指定一个 AMS 槽位（6 色需 ≥6 槽位 / 7 色需 ≥7 槽位；4 槽需换料或第二台 AMS）；",
           "3. `*_plate_recessed.stl` 为翻转后姿态（凹槽朝下、原顶面贴床），与印花同盘嵌套打印"
           "（第一版 0.05 mm 在床面上方）；",
           "4. `*_shell.stl` 底面朝下单独打印；方形加 `square_button.stl`（侧躺，轴水平，5 mm brim）；",
           "5. 打印完成后整体翻面 → 成品外观。", "",
           "## 两个 3MF 的用途", "",
           "- `render/print/appearance/<v>/PRINT_READY.3mf`：可切片**床面排版**（本交付）。",
           "- `appearance/build/3mf/<v>.3mf`：装配完成姿态的数字样机（mockup，不用于直接切片）。", "",
           "## 备注", "",
           "- 本姿态无需支撑（第一层贴床）；PROVISIONAL：尚未实物打印验证。",
           "- 印花各色件为带“同面异向界面”的闭合实体，全部三角形保留（不删面）。"]
    with open(os.path.join(STL_DIR, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    with open(os.path.join(STL_DIR, "delivery.json"), "w", encoding="utf-8") as fh:
        json.dump(delivery, fh, indent=2, ensure_ascii=False)
    print("WROTE", os.path.relpath(cks, ROOT), "(%d files)" % len(lines))
    print("WROTE", os.path.join(os.path.relpath(STL_DIR, ROOT), "README.md"))
    print("WROTE", os.path.join(os.path.relpath(STL_DIR, ROOT), "delivery.json"))
    ok = all(v["ok"] for v in three_mf.values())
    print("STL DELIVERY %d files / %.2f MB | min_z_zero=%s rigid_checks=%s | "
          "3MF_ALL_OK=%s | %.1fs"
          % (len(all_entries), delivery["total_bytes"] / 1e6,
             delivery["all_min_z_zero"], delivery["all_rigid_checks"], ok,
             time.time() - t0))
    if not (delivery["all_min_z_zero"] and delivery["all_rigid_checks"] and ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
