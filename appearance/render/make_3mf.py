#!/usr/bin/env python3
"""Assemble Bambu-Studio-importable 3MF packages for the two SmartCoaster versions.

Writes a plain 3MF core-spec package (zip):
  [Content_Types].xml
  _rels/.rels
  3D/3dmodel.model          <resources> with <basematerials>, one <object> per
                            shell part / per print filament, plus ONE print
                            assembly object (<components> -> per-filament objects)
                            <build> with mm transforms

Contents per version:
  * the real shell-assembly STLs (mechanical/{lumen,square_v1}/build/parts)
  * the recessed top plate appearance/build/shell/<v>/plate_recessed.stl
  * the Kromacut print as ONE PRINT ASSEMBLY object ("PRINT_ART_<dog|elf>") whose
    components are one mesh object per physical filament (from
    appearance/build/print/{dog,elf}/manifest.json).  The assembly is placed at the
    pocket floor from shell.json, XY centred, no rotation; the component objects
    never appear as separate build items.  Shell and print are separate objects;
    Bambu Studio fuses them at slice time.
  * the Kromacut print-only 3MFs are copied alongside as reference copies.

Bambu metadata: NOT emitted (Metadata/model_settings.config is Bambu-proprietary and
risky to hand-write); the user assigns each print component to an AMS slot in Bambu
Studio.  The Kromacut print-only 3MF reference copies already carry Bambu metadata.

Then the file is read back and verified: unzip, XML parse, object/component/triangle
counts, per-filament pid/pindex colours against the manifest, per-filament world-Z
range inside [floor, floor+t], whole-build bbox, material mapping.
Result: appearance/build/3mf/{round,square}.3mf + validation.json.

Run:
  python3 appearance/render/make_3mf.py                 # both
  python3 appearance/render/make_3mf.py --version round
"""
import argparse
import json
import os
import shutil
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene_common as SC  # noqa: E402

ROOT = SC.ROOT
OUT_DIR = os.path.join(ROOT, "appearance", "build", "3mf")
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MODEL_REL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'
IDENTITY = (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def linear_to_srgb_hex(rgb):
    out = []
    for c in rgb[:3]:
        c = min(1.0, max(0.0, float(c)))
        s = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        out.append(int(round(s * 255)))
    return "#%02X%02X%02X" % tuple(out)


def part_hex(cmf, name):
    ent = cmf["parts"].get(name, {})
    if ent.get("hex"):
        return "#" + str(ent["hex"]).lstrip("#").upper()
    if ent.get("base"):
        return linear_to_srgb_hex(ent["base"])
    return "#808080"


def _f(v):
    s = "%.4f" % float(v)
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def _xml_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def transform_str(tr):
    return " ".join(_f(x) for x in tr)


def mat4_from_3mf(tr):
    """3MF transform (4x3 row-major) -> 4x4 row-vector matrix."""
    m = _np.array(tr, dtype=float).tolist()
    return _np.array([
        [m[0], m[1], m[2], 0.0],
        [m[3], m[4], m[5], 0.0],
        [m[6], m[7], m[8], 0.0],
        [m[9], m[10], m[11], 1.0],
    ])


def apply_mat(verts, mat):
    v = _np.asarray(verts, dtype=float)
    return v @ mat[:3, :3].T + mat[3, :3]


# --------------------------------------------------------------------------- #
# writer
# --------------------------------------------------------------------------- #
def write_3mf(path, objects, materials, meta):
    """objects: list of dicts.  Either mesh objects:
         {'id','name','verts','tris','mat'(index),'transform'}
       or assembly objects:
         {'id','name','components':[(objectid, transform), ...],'transform'}
       Build items reference top-level (shell + assembly) objects only."""
    parts = [XML_DECL,
             '<model unit="millimeter" xml:lang="en-US" xmlns="%s">\n' % CORE_NS]
    for k, v in meta.items():
        parts.append('  <metadata name="%s">%s</metadata>\n'
                     % (_xml_escape(k), _xml_escape(v)))
    parts.append("  <resources>\n")
    parts.append('    <basematerials id="1">\n')
    for m in materials:
        parts.append('      <base name="%s" displaycolor="%sFF"/>\n'
                     % (_xml_escape(m["name"]), m["hex"]))
    parts.append("    </basematerials>\n")
    for ob in objects:
        if ob.get("components"):
            parts.append('    <object id="%d" type="model" name="%s">\n'
                         % (ob["id"], _xml_escape(ob["name"])))
            parts.append("      <components>\n")
            for cid, ctr in ob["components"]:
                if ctr and tuple(ctr) != IDENTITY:
                    parts.append('        <component objectid="%d" transform="%s"/>\n'
                                 % (cid, transform_str(ctr)))
                else:
                    parts.append('        <component objectid="%d"/>\n' % cid)
            parts.append("      </components>\n    </object>\n")
            continue
        parts.append('    <object id="%d" type="model" name="%s" pid="1" pindex="%d">\n'
                     % (ob["id"], _xml_escape(ob["name"]), ob["mat"]))
        parts.append('      <mesh>\n        <vertices>\n')
        for v in ob["verts"]:
            parts.append('          <vertex x="%s" y="%s" z="%s"/>\n'
                         % (_f(v[0]), _f(v[1]), _f(v[2])))
        parts.append("        </vertices>\n        <triangles>\n")
        for t in ob["tris"]:
            parts.append('          <triangle v1="%d" v2="%d" v3="%d"/>\n'
                         % (t[0], t[1], t[2]))
        parts.append("        </triangles>\n      </mesh>\n    </object>\n")
    parts.append("  </resources>\n  <build>\n")
    for ob in objects:
        if not ob.get("build_item", True):
            continue
        tr = ob.get("transform")
        if tr:
            parts.append('    <item objectid="%d" transform="%s"/>\n'
                         % (ob["id"], transform_str(tr)))
        else:
            parts.append('    <item objectid="%d"/>\n' % ob["id"])
    parts.append("  </build>\n</model>\n")
    model_xml = "".join(parts)

    content_types = (
        XML_DECL +
        '<Types xmlns="%s">\n' % CT_NS +
        '  <Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="model" '
        'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        "</Types>\n")
    rels = (
        XML_DECL +
        '<Relationships xmlns="%s">\n' % REL_NS +
        '  <Relationship Id="rel0" Target="/3D/3dmodel.model" Type="%s"/>\n'
        % MODEL_REL +
        "</Relationships>\n")

    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model_xml)
        z.writestr("Metadata/SmartCoaster.txt", meta.get("Description", "") + "\n")
    os.replace(tmp, path)
    meshes = [o for o in objects if not o.get("components")]
    return {"bytes": os.path.getsize(path), "objects": len(objects),
            "mesh_objects": len(meshes),
            "assemblies": len(objects) - len(meshes),
            "triangles": sum(len(o["tris"]) for o in meshes),
            "vertices": sum(len(o["verts"]) for o in meshes),
            "materials": len(materials)}


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #
def collect(version, cfg, cmf):
    spec = SC.resolve_assembly(version, cfg)
    objects, materials = [], []
    mat_index = {}
    warnings = list(spec["warnings"])

    def mat_for(name, hexv):
        key = (name, hexv)
        if key not in mat_index:
            mat_index[key] = len(materials)
            materials.append({"name": name, "hex": hexv})
        return mat_index[key]

    next_id = 2

    # ---- shell assembly parts (one object per part) ---------------------- #
    shell_names, plate_name = [], None
    for part in spec["parts"]:
        tris = SC.read_stl_triangles_mm(part["path"])
        verts, faces = SC._tri_soup_to_mesh(tris, dedupe=False)
        hexv = part_hex(cmf, part["name"])
        objects.append({"id": next_id, "name": part["name"],
                        "verts": verts.tolist(), "tris": faces.tolist(),
                        "mat": mat_for(part["name"], hexv),
                        "transform": IDENTITY, "role": "shell_assembly",
                        "source": os.path.relpath(part["path"], ROOT)})
        shell_names.append(part["name"])
        next_id += 1

    plate = spec["plate"]
    if plate.get("path"):
        tris = SC.read_stl_triangles_mm(plate["path"])
        verts, faces = SC._tri_soup_to_mesh(tris, dedupe=False)
        hexv = part_hex(cmf, "plate")
        objects.append({"id": next_id, "name": "plate_recessed",
                        "verts": verts.tolist(), "tris": faces.tolist(),
                        "mat": mat_for("plate", hexv),
                        "transform": IDENTITY, "role": "shell_assembly",
                        "source": os.path.relpath(plate["path"], ROOT),
                        "proxy": plate.get("proxy", False)})
        plate_name = "plate_recessed"
        next_id += 1
    else:
        warnings.append("no plate object for %s" % version)

    # ---- print: one mesh object per physical filament, grouped in one ---- #
    # ---- print assembly object (components) placed on the pocket floor --- #
    floor = spec["shell"]["floor_z_mm"]
    pr = spec["print"]
    meshes = []
    zmin_group = None
    for i, pobj in enumerate(pr["objects"]):
        verts, faces = SC.print_object_mesh(pobj, dedupe=False)
        if len(verts) == 0 or len(faces) == 0:
            warnings.append("print object %d is empty; skipped" % i)
            continue
        if not hasattr(verts, "min"):
            verts = _np.asarray(verts, dtype=float)
            faces = _np.asarray(faces, dtype=_np.int64)
        zmin_group = (float(verts[:, 2].min()) if zmin_group is None
                      else min(zmin_group, float(verts[:, 2].min())))
        meshes.append((i, pobj, verts, faces))
    dz = (floor - zmin_group) if zmin_group is not None else floor
    max_r = 0.0
    for (i, pobj, verts, faces) in meshes:
        if hasattr(verts, "min"):
            max_r = max(max_r, float(_np.hypot(verts[:, 0], verts[:, 1]).max()))
    spec["print"]["max_radius_mm"] = round(max_r, 3)
    spec["print"]["actual_max_interference_mm"] = round(
        max_r - spec["shell"]["pocket_dia_mm"] / 2.0, 3)
    if not (40.0 < max_r < 45.0):
        raise RuntimeError("print max radius %.3f mm is not in (40,45) mm" % max_r)

    filament_ids, filament_info = [], []
    for (i, pobj, verts, faces) in meshes:
        hexv = pobj.get("hex") or (pr["palette"][i]
                                   if i < len(pr["palette"]) else "#CCCCCC")
        hexv = "#" + str(hexv).lstrip("#").upper()
        name = pobj.get("name") or ("print_%s_%02d" % (spec["art"], i))
        objects.append({"id": next_id, "name": name,
                        "verts": verts.tolist(), "tris": faces.tolist(),
                        "mat": mat_for(name, hexv),
                        "transform": None, "build_item": False,
                        "role": "print_filament",
                        "source": (os.path.relpath(pobj["path"], ROOT)
                                   if pobj.get("path") else "placeholder:%s"
                                   % pr["source"]),
                        "hex": hexv})
        bb = SC.mesh_stats(verts, faces)["bbox_mm"]
        filament_ids.append(next_id)
        filament_info.append({"id": next_id, "name": name, "hex": hexv,
                              "tris": len(faces),
                              "source_tris": len(faces),
                              "declared_tris": pobj.get("tris_declared"),
                              "bbox_mm": [[round(x, 4) for x in bb[0]],
                                          [round(x, 4) for x in bb[1]]]})
        next_id += 1

    assembly_id = None
    if filament_ids:
        assembly_id = next_id
        next_id += 1
        objects.append({
            "id": assembly_id, "name": "PRINT_ART_%s" % spec["art"],
            "components": [(cid, IDENTITY) for cid in filament_ids],
            "transform": (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, dz),
            "build_item": True, "role": "print_assembly"})
    else:
        warnings.append("no print filaments for %s" % version)

    # expected per-filament world-z range after the assembly transform
    for fi in filament_info:
        fi["world_z_mm"] = [round(fi["bbox_mm"][0][2] + dz, 3),
                            round(fi["bbox_mm"][1][2] + dz, 3)]
    env = None
    if filament_info:
        los = [min(f["bbox_mm"][0][k] for f in filament_info) for k in range(3)]
        his = [max(f["bbox_mm"][1][k] for f in filament_info) for k in range(3)]
        env = {"bbox_mm": [los, his], "objects": len(filament_info),
               "print_total_triangles": sum(f["tris"] for f in filament_info),
               "print_declared_triangles": sum(
                   f["declared_tris"] for f in filament_info
                   if f.get("declared_tris") is not None) or None,
               "thickness_mm": spec["shell"]["print_thickness_mm"],
               "bottom_z_mm": round(los[2] + dz, 3),
               "top_z_mm": round(his[2] + dz, 3),
               "assembly_object": "PRINT_ART_%s" % spec["art"]}
        rim = spec["shell"].get("rim_z_mm")
        if rim:
            env["top_gap_mm"] = round(rim - env["top_z_mm"], 3)
    return (spec, objects, materials, warnings, filament_info, env,
            assembly_id, shell_names + ([plate_name] if plate_name else []))


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def _parse_model(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        ct = ET.fromstring(z.read("[Content_Types].xml"))
        rels = ET.fromstring(z.read("_rels/.rels"))
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    return names, ct, rels, root


def validate_3mf(path, version, spec, expected, print_env, filament_expected):
    """expected: {'shell_assembly': n, 'print_assembly': n, 'print_filament': n}
    filament_expected: [{name, hex, tris, declared_tris}] (one per physical filament)"""
    filament_expected = list(filament_expected)
    expected_hex = {f["name"]: f["hex"] for f in filament_expected}
    res = {"file": os.path.relpath(path, ROOT), "version": version,
           "ok": True, "errors": [], "warnings": []}
    try:
        names, ct, rels, root = _parse_model(path)
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        res["ok"] = False
        res["errors"].append("package/XML error: %s" % exc)
        return res
    res["members"] = names
    for req in ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"):
        if req not in names:
            res["errors"].append("missing package member %r" % req)
    types = {e.get("Extension"): e.get("ContentType")
             for e in ct.findall("{%s}Default" % CT_NS)}
    if "model" not in types:
        res["errors"].append("[Content_Types].xml has no model default")
    targets = [e.get("Target") for e in rels.findall("{%s}Relationship" % REL_NS)]
    if "/3D/3dmodel.model" not in targets:
        res["errors"].append("_rels/.rels does not point at 3D/3dmodel.model")
    res["unit"] = root.get("unit")
    if res["unit"] != "millimeter":
        res["errors"].append("unit is %r, expected millimeter" % res["unit"])
    for md in root.findall("{%s}metadata" % CORE_NS):
        if md.get("name") == "Title":
            res["title"] = (md.text or "").strip()

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
        ent = {"id": oid, "name": obj.get("name"),
               "verts": [], "tris": [], "components": [],
               "pid": obj.get("pid"), "pindex": obj.get("pindex")}
        if mesh is not None:
            v_el = mesh.find("{%s}vertices" % CORE_NS)
            t_el = mesh.find("{%s}triangles" % CORE_NS)
            if v_el is not None:
                ent["verts"] = [(float(ve.get("x")), float(ve.get("y")),
                                 float(ve.get("z")))
                                for ve in v_el.findall("{%s}vertex" % CORE_NS)]
            if t_el is not None:
                ent["tris"] = [(int(te.get("v1")), int(te.get("v2")),
                                int(te.get("v3")))
                               for te in t_el.findall("{%s}triangle" % CORE_NS)]
            if not ent["tris"]:
                res["errors"].append("mesh object %r has 0 triangles"
                                     % obj.get("name"))
            for t in ent["tris"]:
                if max(t) >= len(ent["verts"]) or min(t) < 0:
                    res["errors"].append("object %r has out-of-range triangle index"
                                         % obj.get("name"))
                    break
        elif comps_el is not None:
            for c in comps_el.findall("{%s}component" % CORE_NS):
                tr = c.get("transform")
                cm = ([float(x) for x in tr.split()] if tr else list(IDENTITY))
                ent["components"].append((int(c.get("objectid")), cm))
        else:
            res["errors"].append("object %r has neither mesh nor components"
                                 % obj.get("name"))
        objs[oid] = ent

    items = []
    for it in root.iter("{%s}item" % CORE_NS):
        tr = it.get("transform")
        m = ([float(x) for x in tr.split()] if tr else list(IDENTITY))
        items.append({"objectid": int(it.get("objectid")), "transform": m})
    res["object_count"] = len(objs)
    res["build_items"] = len(items)

    # ---- traverse build items (assemblies expand to components) ---------- #
    mesh_objects = [o for o in objs.values() if o["tris"]]
    res["total_triangles"] = sum(len(o["tris"]) for o in mesh_objects)
    res["total_vertices"] = sum(len(o["verts"]) for o in mesh_objects)
    if res["total_triangles"] <= 0:
        res["errors"].append("zero total triangles")
    lo = [_np.inf] * 3
    hi = [-_np.inf] * 3
    world_z = {}
    filament_objs = {}
    for it in items:
        top = objs.get(it["objectid"])
        if top is None:
            res["errors"].append("build item references missing object %d"
                                 % it["objectid"])
            continue
        m_item = mat4_from_3mf(it["transform"])
        if top["components"]:
            for cid, ctr in top["components"]:
                comp = objs.get(cid)
                if comp is None:
                    res["errors"].append("component references missing object %d" % cid)
                    continue
                world = apply_mat(comp["verts"], mat4_from_3mf(ctr) @ m_item)
                for k in range(3):
                    lo[k] = min(lo[k], float(world[:, k].min()))
                    hi[k] = max(hi[k], float(world[:, k].max()))
                filament_objs[comp["name"]] = comp
                world_z[comp["name"]] = [round(float(world[:, 2].min()), 3),
                                         round(float(world[:, 2].max()), 3)]
        else:
            world = apply_mat(top["verts"], m_item)
            for k in range(3):
                lo[k] = min(lo[k], float(world[:, k].min()))
                hi[k] = max(hi[k], float(world[:, k].max()))

    if res["total_triangles"] > 0 and _np.isfinite(lo).all():
        res["bbox_mm"] = {"min": [round(v, 3) for v in lo],
                          "max": [round(v, 3) for v in hi],
                          "size": [round(hi[i] - lo[i], 3) for i in range(3)]}
        exp = {"round": (110.0, 110.0, 17.0), "square": (100.0, 100.0, 18.0)}[version]
        size = res["bbox_mm"]["size"]
        tol = 2.0
        if abs(size[0] - exp[0]) > tol or abs(size[1] - exp[1]) > tol:
            res["errors"].append("XY bbox %r not ~%r" % (size[:2], exp[:2]))
        if abs(size[2] - exp[2]) > tol:
            res["errors"].append("Z bbox %.2f not ~%.2f" % (size[2], exp[2]))
        if abs(lo[2]) > 1.0:
            res["warnings"].append("build z-min %.2f not on the bed plane" % lo[2])

    # ---- role / assembly checks ----------------------------------------- #
    assemblies = [o for o in objs.values() if o["components"]]
    build_mesh = [objs[it["objectid"]] for it in items
                  if objs.get(it["objectid"]) and objs[it["objectid"]]["tris"]]
    roles = {"shell_assembly": len(build_mesh),
             "print_assembly": len(assemblies),
             "print_filament": len(filament_objs)}
    res["roles"] = roles
    if roles != expected:
        res["errors"].append("role counts %r != expected %r" % (roles, expected))
    if len(assemblies) != 1:
        res["errors"].append("expected exactly 1 print assembly object, found %d"
                             % len(assemblies))
    else:
        res["print_assembly"] = {
            "name": assemblies[0]["name"],
            "components": len(assemblies[0]["components"]),
            "build_item_transform": next(
                (it["transform"] for it in items
                 if it["objectid"] == assemblies[0]["id"]), None)}
    if len(filament_objs) != expected["print_filament"]:
        res["errors"].append("assembly references %d filament objects, expected %d"
                             % (len(filament_objs), expected["print_filament"]))

    # ---- per-filament material + world-Z self checks --------------------- #
    res["filaments"] = []
    seen_pindex = {}
    for finfo in sorted(filament_expected, key=lambda f: f["name"]):
        name, hexv = finfo["name"], finfo["hex"]
        ob = filament_objs.get(name)
        if ob is None:
            res["errors"].append("print filament object %r missing from assembly"
                                 % name)
            continue
        mat = None
        if ob["pid"] == "1" and ob["pindex"] is not None:
            mi = int(ob["pindex"])
            if 0 <= mi < len(mats):
                mat = mats[mi]
        entry = {"name": name, "expected_hex": hexv, "pindex": ob["pindex"],
                 "color": mat["color"] if mat else None,
                 "world_z_mm": world_z.get(name),
                 "triangles": len(ob["tris"]),
                 "source_tris": finfo["tris"],
                 "declared_tris": finfo.get("declared_tris")}
        res["filaments"].append(entry)
        if mat is None:
            res["errors"].append("print filament %r has no basematerial pid/pindex"
                                 % name)
            continue
        want = "#" + str(hexv).lstrip("#").upper()
        # exact triangle preservation: no coincident-interface de-duplication
        if len(ob["tris"]) != finfo["tris"]:
            res["errors"].append(
                "print component %r has %d triangles, STL has %d (interface caps "
                "must not be deduped)" % (name, len(ob["tris"]), finfo["tris"]))
        if finfo.get("declared_tris") is not None and \
                int(finfo["declared_tris"]) != finfo["tris"]:
            res["errors"].append(
                "print component %r STL has %d triangles but manifest declares %d"
                % (name, finfo["tris"], finfo["declared_tris"]))
        if not (mat["color"] or "").upper().startswith(want + "FF"):
            res["errors"].append(
                "print filament %r colour %r != manifest %r"
                % (name, mat["color"], want))
        if mi in seen_pindex:
            res["errors"].append(
                "print filaments %r and %r share basematerial index %d"
                % (name, seen_pindex[mi], mi))
        seen_pindex[mi] = name
        floor = spec["shell"]["floor_z_mm"]
        thk = spec["shell"]["print_thickness_mm"]
        zr = world_z.get(name)
        if zr is None:
            res["errors"].append("print filament %r has no world bbox" % name)
        else:
            if not (floor - 0.01 <= zr[0] and zr[1] <= floor + thk + 0.5):
                res["errors"].append(
                    "print filament %r world z %r outside [%.3f, %.3f]"
                    % (name, zr, floor, floor + thk))

    # ---- pocket / interference numbers ---------------------------------- #
    res["print_total_triangles"] = sum(f["tris"] for f in filament_expected)
    res["print_declared_triangles"] = sum(
        int(f["declared_tris"]) for f in filament_expected
        if f.get("declared_tris") is not None) or None
    if res["print_declared_triangles"] is not None and \
            res["print_declared_triangles"] != res["print_total_triangles"]:
        res["errors"].append(
            "print component total %d != manifest total %d"
            % (res["print_total_triangles"], res["print_declared_triangles"]))
    sh = spec["shell"]
    res["pocket_dia_mm"] = sh["pocket_dia_mm"]
    res["print_dia_mm"] = sh["print_dia_mm"]
    res["print_max_radius_mm"] = spec["print"].get("max_radius_mm")
    res["actual_max_interference_mm"] = spec["print"].get(
        "actual_max_interference_mm")
    if res["print_max_radius_mm"] is not None:
        exp_int = res["print_max_radius_mm"] - sh["pocket_dia_mm"] / 2.0
        res["interference_check_mm"] = round(exp_int, 3)
        if exp_int <= 0:
            res["warnings"].append("print max radius does not interfere with pocket")
    if print_env and print_env.get("top_z_mm") is not None:
        rim = sh.get("rim_z_mm")
        if rim:
            res["print_top_vs_rim_mm"] = round(print_env["top_z_mm"] - rim, 3)
    res["ok"] = not res["errors"]
    return res


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run_version(version, cfg):
    cmf = SC.load_cmf(cfg)
    (spec, objects, materials, warnings, filament_info, env,
     assembly_id, shell_names) = collect(version, cfg, cmf)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, version + ".3mf")
    sh = spec["shell"]
    meta = {
        "Title": "SmartCoaster %s \u00b7 %s + %s print"
                 % (version, spec["label"], spec["art"]),
        "Designer": "SmartCoaster appearance pipeline (Blender scene: "
                    "appearance/render/%s/scene.blend)" % version,
        "Description": (
            "Assembled appearance 3MF. Shell assembly STLs + recessed top plate + "
            "Kromacut multi-material print grouped as ONE print assembly object "
            "whose components are one mesh per physical filament. Print bottom on "
            "pocket floor z=%.2f mm, XY centred, no rotation, nominal \u00d886.4 print "
            "in \u00d886.0 pocket (0.20 mm nominal radial interference, %.3f mm max "
            "including pixel-staircase corners), print top %.2f mm below rim "
            "z=%.2f mm. Shell and print are SEPARATE objects; Bambu Studio fuses "
            "them at slice time; assign each print component to an AMS slot."
            % (sh["floor_z_mm"],
               spec["print"].get("actual_max_interference_mm", 0.2),
               sh.get("top_gap_mm", 0.05), sh.get("rim_z_mm") or 0.0)),
        "Application": "Bambu Studio / 3MF core spec 1.2",
        "Copyright": "SmartCoaster project",
    }
    stats = write_3mf(out, objects, materials, meta)

    # reference copies of the print-only Kromacut 3MFs (next to the assembled ones)
    ref = None
    src3 = spec["print"].get("reference_3mf")
    if src3 and os.path.exists(src3):
        ref = os.path.join(OUT_DIR, "%s_kromacut.3mf" % spec["art"])
        shutil.copy2(src3, ref)
    else:
        warnings.append("Kromacut print-only 3MF not found for %s "
                        "(reference copy skipped)" % spec["art"])

    expected = {"shell_assembly": len(shell_names),
                "print_assembly": 1 if filament_info else 0,
                "print_filament": len(filament_info)}
    filament_expected = filament_info
    val = validate_3mf(out, version, spec, expected, env, filament_expected)
    val["write_stats"] = stats
    val["print_env"] = env
    val["filament_objects"] = filament_info
    val["print_assembly_id"] = assembly_id
    val["warnings"] = list(val.get("warnings", [])) + warnings
    val["mismatches"] = spec["mismatches"]
    val["reference_3mf"] = os.path.relpath(ref, ROOT) if ref else None
    val["print_source"] = spec["print"]["source"]
    val["shell_source"] = spec["shell"]["source"]
    val["shell_params"] = spec["shell"]
    val["print_palette"] = spec["print"]["palette"]
    val["bambu_metadata"] = ("not emitted (proprietary model_settings.config); "
                             "assign print components to AMS slots in Bambu Studio")
    return val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="both", choices=["round", "square", "both"])
    args = ap.parse_args()
    cfg = SC.load_config()
    versions = ["round", "square"] if args.version == "both" else [args.version]
    allv = {}
    t0 = time.time()
    for v in versions:
        t = time.time()
        val = run_version(v, cfg)
        val["seconds"] = round(time.time() - t, 2)
        allv[v] = val
        print("=" * 78)
        print("3MF", v, "ok" if val["ok"] else "FAILED",
              "| objects", val.get("object_count"),
              "| build_items", val.get("build_items"),
              "| triangles", val.get("total_triangles"),
              "| bbox", val.get("bbox_mm", {}).get("size"),
              "| %.2fs" % val["seconds"])
        for e in val["errors"]:
            print("  ERROR", e)
        for w in val["warnings"]:
            print("  warn", w)
        for m in val["mismatches"]:
            print("  MISMATCH", m)
    report = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "blender": "4.5.3 LTS", "seconds": round(time.time() - t0, 2),
              "versions": allv,
              "ok": all(v["ok"] for v in allv.values())}
    with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print("3MF all ok:", report["ok"], "| total %.1fs" % report["seconds"])


if __name__ == "__main__":
    main()
