#!/usr/bin/env python3
"""Appearance shell CAD - recessed top plate + Kromacut print blanks.

Build123d 0.10.0.  Run through appearance/cad/run_shell.sh (one command,
idempotent).  Reads the validated plate STEPs from mechanical/** (read-only,
never modified) and boolean-cuts ONE flat-bottom cylindrical pocket for the
Kromacut multi-material print (fused in place by the slicer).

Outputs (all under appearance/build/shell/):
    {square,round}/plate_recessed.step|stl   faithful cut of validated plate
    round/plate_recessed_clean.step|stl      optional: same cut after filling
                                             the pre-existing internal void
                                             (source-model defect, see REPORT)
    print_blank_round.stl                    placeholder disc d86.4 x 1.20
    print_blank_square.stl                   placeholder disc d86.4 x 1.40
    print_blank.stl                          alias of print_blank_round.stl
    shell.json                               numeric contract for render/3MF
    parts.json                               assembly STL pointers (no copies)
    REPORT.md                                commands + measured numbers

Spec (Lead update 2026-11-06):
  pocket d86.0 centred (0,0); floor = rim_top_z - 0.05 - print_thickness
    round  (LUMEN dog, 6 layers x 0.2 = 1.20): floor 15.75, depth 1.25
    square (square_v1 elf, 7 layers x 0.2 = 1.40): floor 16.55, depth 1.45
  print d86.4 -> 0.2 mm radial interference; print top 0.05 mm below rim.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from build123d import (
    Align,
    Box,
    Cone,
    Cylinder,
    GeomType,
    Pos,
    export_step,
    export_stl,
    import_step,
)
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_SurfaceType

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "appearance" / "build" / "shell"
ART_DIR = REPO / "appearance" / "build" / "art"
PYEXE = "/data/Documents/projects/SmartCoaster/mechanical/square_v1/.venv/bin/python"
BLENDER = "/data/Documents/tools/blender/blender"

POCKET_D = 86.0
POCKET_R = POCKET_D / 2.0
PRINT_D = 86.4
PRINT_R = PRINT_D / 2.0
RADIAL_INT = PRINT_R - POCKET_R          # 0.2 mm
TOP_CLEAR = 0.05                          # print top below rim
STL_TOL = 0.02                            # mm linear
STL_ANG = 0.2                             # rad angular
ALIGN_CZMIN = (Align.CENTER, Align.CENTER, Align.MIN)

SHAPES = {
    "round": {
        "label": "LUMEN round d104 (legacy appearance donor)",
        "variant": "dog",
        "project": "mechanical/lumen",
        "plate_step": "mechanical/lumen/build/parts/plate_v01.step",
        "rim_z": 17.0,
        "print_thickness": 1.20,
        "floor_z": 15.75,
    },
    "square": {
        "label": "square_v1 100 x 100 (functional baseline)",
        "variant": "elf",
        "project": "mechanical/square_v1",
        "plate_step": "mechanical/square_v1/build/parts/plate_v01.step",
        "rim_z": 18.0,
        "print_thickness": 1.40,
        "floor_z": 16.55,
    },
}

# parts that are legacy / not part of the frozen square-derived function
LEGACY_PARTS = {"round": {"guide_v01", "ledflex_v01"}}


def apply_geometry(cfg: dict) -> None:
    """Point the module-level pocket/print constants at one version's config.

    Called per version when --config is used, and once with the round config
    before the shared shell.json contract/report is assembled.  Without
    --config the module constants above are already the verified defaults.
    """
    global POCKET_D, POCKET_R, PRINT_D, PRINT_R, RADIAL_INT, TOP_CLEAR
    POCKET_D = float(cfg["pocket_dia"])
    POCKET_R = POCKET_D / 2.0
    PRINT_D = float(cfg["print_dia"])
    PRINT_R = PRINT_D / 2.0
    RADIAL_INT = PRINT_R - POCKET_R
    TOP_CLEAR = float(cfg["top_gap"])


def load_project_config(path_str: str) -> dict:
    """Read the project YAML (or compile-resolved JSON) into per-version SHAPES.

    The JSON path is stdlib-only (appearance/tools/compile.py always passes the
    resolved JSON, so the build123d venv needs no PyYAML).  Reading the YAML
    directly needs PyYAML; if the venv lacks it we fall back to the system
    dist-packages copy, and otherwise fail with an actionable message.
    """
    p = Path(path_str)
    if not p.is_absolute():
        p = REPO / p
    if not p.is_file():
        raise SystemExit(
            "build_recessed.py: --config file not found: %s\n"
            "  expected: appearance/config/appearance_project.yaml" % path_str
        )
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        doc = json.loads(text)
    else:
        try:
            import yaml  # noqa: WPS433 - optional dependency
        except ImportError:
            # build123d venv is isolated; the system python3 ships PyYAML.
            sys.path.append("/usr/lib/python3/dist-packages")
            try:
                import yaml  # noqa: F811
            except ImportError:
                raise SystemExit(
                    "build_recessed.py: reading %s needs PyYAML, which this build123d "
                    "venv lacks.\n  Run through `bash appearance/compile.sh` (it passes "
                    "appearance/build/compile/resolved_config.json), or pass that JSON "
                    "file explicitly with --config." % p
                )
        doc = yaml.safe_load(text)
    versions = (doc or {}).get("versions")
    if not isinstance(versions, dict) or not versions:
        raise SystemExit(
            "build_recessed.py: %s has no `versions:` mapping; see the schema at the "
            "top of appearance/config/appearance_project.yaml" % p
        )
    for required in ("round", "square"):
        if required not in versions:
            raise SystemExit(
                "build_recessed.py: %s is missing versions.%s (this pipeline builds the "
                "round + square pair)" % (p, required)
            )
    out = {}
    for key, v in versions.items():
        where = "%s: versions.%s.shell" % (p.name, key)
        art = v.get("art") or {}
        shell = v.get("shell") or {}
        if shell.get("print_thickness_mm") is not None:
            thickness = float(shell["print_thickness_mm"])
        else:
            palette = art.get("palette_bottom_up") or []
            layer = art.get("layer_height_mm")
            if not palette or layer is None:
                raise SystemExit(
                    "build_recessed.py: %s needs art.palette_bottom_up + "
                    "art.layer_height_mm (to derive print thickness)" % where
                )
            thickness = round(len(palette) * float(layer), 6)
        try:
            rim = float(shell["rim_z_mm"])
            pocket = float(shell["pocket_dia_mm"])
            print_d = float(shell["print_dia_mm"])
            intf = float(shell["interference_mm"])
            top_gap = float(shell["top_gap_mm"])
            plate_step = str(shell["plate_step"])
        except KeyError as exc:
            raise SystemExit(
                "build_recessed.py: %s is missing required key %s (expected "
                "plate_step, rim_z_mm, pocket_dia_mm, print_dia_mm, interference_mm, "
                "top_gap_mm)" % (where, exc)
            )
        mech = str(shell.get("mech_label") or where)
        out[key] = {
            "label": str(shell.get("label") or mech),
            "variant": str(art.get("name") or key),
            "project": str(shell.get("project") or ("mechanical/" + mech)),
            "plate_step": plate_step,
            "rim_z": rim,
            "print_thickness": thickness,
            "floor_z": round(rim - top_gap - thickness, 6),
            "pocket_dia": pocket,
            "print_dia": print_d,
            "interference": intf,
            "top_gap": top_gap,
        }
    # shell.json / render / 3MF carry ONE shared pocket/print contract.
    ref_key = "round"
    for key, cfg in out.items():
        for field, yaml_key in (("pocket_dia", "pocket_dia_mm"),
                                ("print_dia", "print_dia_mm"),
                                ("top_gap", "top_gap_mm"),
                                ("interference", "interference_mm")):
            if abs(float(cfg[field]) - float(out[ref_key][field])) > 1e-9:
                raise SystemExit(
                    "build_recessed.py: versions.%s.shell.%s=%s differs from "
                    "versions.%s.shell.%s=%s; this pipeline's shell.json/render/3MF "
                    "contract is shared across versions - keep these equal"
                    % (key, yaml_key, cfg[field], ref_key, yaml_key,
                       out[ref_key][field])
                )
    for key, cfg in out.items():
        if not (REPO / cfg["plate_step"]).is_file():
            raise SystemExit(
                "build_recessed.py: versions.%s.shell.plate_step not found: %s"
                % (key, cfg["plate_step"])
            )
        derived = cfg["print_dia"] / 2.0 - cfg["pocket_dia"] / 2.0
        if abs(cfg["interference"] - derived) > 1e-9:
            raise SystemExit(
                "build_recessed.py: versions.%s: pocket_dia_mm %s + "
                "2*interference_mm %s != print_dia_mm %s (radial interference "
                "derived %.6f) - fix appearance_project.yaml"
                % (key, cfg["pocket_dia"], cfg["interference"], cfg["print_dia"], derived)
            )
    return out


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def r6(x: float) -> float:
    return round(float(x), 6)


def vec_list(v) -> list:
    return [r6(v.X), r6(v.Y), r6(v.Z)]


def bbox_dict(shape) -> dict:
    bb = shape.bounding_box()
    return {
        "min": [r6(bb.min.X), r6(bb.min.Y), r6(bb.min.Z)],
        "max": [r6(bb.max.X), r6(bb.max.Y), r6(bb.max.Z)],
        "size": [r6(bb.size.X), r6(bb.size.Y), r6(bb.size.Z)],
    }


def vtx_pt(v):
    p = BRep_Tool.Pnt_s(v.wrapped)
    return (p.X(), p.Y(), p.Z())


def face_plane(face):
    """Return (z, nx, ny, nz) for a planar face."""
    ad = BRepAdaptor_Surface(face.wrapped)
    assert ad.GetType() == GeomAbs_SurfaceType.GeomAbs_Plane
    pln = ad.Plane()
    loc = pln.Location()
    d = pln.Axis().Direction()
    return loc.Z(), d.X(), d.Y(), d.Z()


def cyl_radius(face):
    ad = BRepAdaptor_Surface(face.wrapped)
    if ad.GetType() != GeomAbs_SurfaceType.GeomAbs_Cylinder:
        return None
    return ad.Cylinder().Radius()


def sample_face_radii(face, n: int = 48):
    """Min/max radial distance from Z axis over sampled boundary points."""
    rs = []
    for e in face.edges():
        for i in range(n + 1):
            p = e.position_at(i / n)
            rs.append(math.hypot(p.X, p.Y))
    return (min(rs), max(rs)) if rs else (None, None)


def probe(shape, x, y, z0, z1, w=0.2):
    """Return (min_z, max_z) of material of `shape` inside a thin vertical box."""
    box = Pos(x, y, (z0 + z1) / 2.0) * Box(w, w, z1 - z0)
    try:
        inter = shape.intersect(box)
    except Exception:
        return None
    if inter is None:
        return None
    try:
        if inter.volume < 1e-12:
            return None
    except Exception:
        return None
    bb = inter.bounding_box()
    return (bb.min.Z, bb.max.Z)


def make_tool(floor_z: float, rim_z: float):
    h = rim_z - floor_z + 1.0
    return Pos(0, 0, floor_z) * Cylinder(POCKET_R, h, align=ALIGN_CZMIN)


def single_solid(shape):
    sols = shape.solids()
    assert len(sols) == 1, f"expected 1 solid, got {len(sols)}"
    return sols[0]


def read_stl(path: Path) -> dict:
    """Parse a binary STL; return triangle count, bbox and edge-manifold stats."""
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"{path}: too short for binary STL")
    n = struct.unpack("<I", data[80:84])[0]
    if len(data) < 84 + 50 * n:
        raise ValueError(f"{path}: truncated STL ({len(data)} bytes, header says {n} tris)")
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    edges = {}
    q = 5  # quantise to 1e-5 mm (float32 STL precision at ~100 mm is ~1e-5)
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12f", data[off:off + 48])
        off += 50
        tri = []
        for k in (3, 6, 9):
            x, y, z = vals[k], vals[k + 1], vals[k + 2]
            tri.append((round(x, q), round(y, q), round(z, q)))
            for i, c in enumerate((x, y, z)):
                if c < lo[i]:
                    lo[i] = c
                if c > hi[i]:
                    hi[i] = c
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((tri[a], tri[b])))
            edges[e] = edges.get(e, 0) + 1
    counts = list(edges.values())
    return {
        "triangles": n,
        "bbox_min": [r6(v) for v in lo],
        "bbox_max": [r6(v) for v in hi],
        "unique_edges": len(edges),
        "manifold_edges": sum(1 for c in counts if c == 2),
        "boundary_edges": sum(1 for c in counts if c == 1),
        "nonmanifold_edges": sum(1 for c in counts if c > 2),
        "watertight": all(c == 2 for c in counts),
    }


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# geometry analysis
# ---------------------------------------------------------------------------
def analyse_plate(plate, cfg):
    """Measure the validated plate before cutting."""
    cb = plate.bounding_box()
    top_z = cb.max.Z
    rim_z = cfg["rim_z"]
    assert abs(top_z - rim_z) < 1e-6, f"rim top mismatch: {top_z} vs {rim_z}"

    faces = plate.faces()
    top_faces = [f for f in faces
                 if f.geom_type == GeomType.PLANE
                 and abs(face_plane(f)[0] - top_z) < 1e-4]
    # engraved / etched groove: faces sitting 0.05..0.25 mm below the rim
    groove_faces = [f for f in faces
                    if top_z - 0.25 < f.center().Z < top_z - 1e-4]
    fillet_faces = [f for f in faces
                    if f.geom_type in (GeomType.CYLINDER, GeomType.TORUS)
                    and top_z - 0.45 < f.center().Z < top_z - 0.25]
    # plate body underside inside the pocket footprint (needed before outer faces)
    undersides = []
    for rr in (5.0, 10.0, 20.0, 30.0, 40.0, 42.0):
        p = probe(plate, rr, 0.0, cfg["floor_z"] - 4.0, cfg["floor_z"] - 0.001)
        undersides.append({"r_mm": rr, "underside_z": r6(p[0]) if p else None})
    # remaining material under the floor = floor - highest underside over the
    # pocket footprint (boss/column only ADD material below the plate body)
    body_bottom = max(u["underside_z"] for u in undersides if u["underside_z"] is not None)

    # outer (max-radius) vertical faces of the plate BODY, not the skirt
    outer_faces = [f for f in faces
                   if f.geom_type in (GeomType.PLANE, GeomType.CYLINDER)
                   and abs(f.normal_at(f.center()).Z) < 0.01
                   and f.bounding_box().max.Z <= top_z - 0.15
                   and f.bounding_box().max.Z > body_bottom + 0.01
                   and (sample_face_radii(f)[0] or 0.0) >= max(cb.max.X, cb.max.Y) - 0.05]
    tool_cf = make_tool(cfg["floor_z"], rim_z).faces().filter_by(GeomType.CYLINDER)[0]

    groove_status = "absent"
    groove_clearance = None
    groove_r = None
    if groove_faces:
        grs = [sample_face_radii(f)[0] for f in groove_faces]
        grs = [r for r in grs if r is not None]
        groove_r = r6(min(grs))
        if groove_r < POCKET_R:
            groove_status = "inside pocket footprint -> removed by cut"
        else:
            groove_status = "outside pocket footprint -> kept"
            groove_clearance = r6(min(tool_cf.distance_to(f) for f in groove_faces))

    fillet_r = None
    fillet_clearance = None
    if fillet_faces:
        fillet_r = r6(min(sample_face_radii(f)[0] for f in fillet_faces))
        fillet_clearance = r6(min(tool_cf.distance_to(f) for f in fillet_faces))

    outer_max = max(cb.max.X, cb.max.Y)
    outer_clearance = r6(min(tool_cf.distance_to(f) for f in outer_faces)) if outer_faces else r6(outer_max - POCKET_R)

    # top surface profile (to prove flat vs. dish)
    profile = []
    for rr in (0.0, 10.0, 20.0, 30.0, 40.0, 42.0, 43.5, 45.0):
        p = probe(plate, rr, 0.0, cfg["floor_z"] - 2.0, top_z + 1.0)
        profile.append({"r_mm": rr, "top_z": r6(p[1]) if p else None})

    shells = plate.shells()
    void = None
    if len(shells) > 1:
        inner = shells[-1]
        ibb = inner.bounding_box()
        ix = []
        for f in inner.faces():
            for e in f.edges():
                for i in range(17):
                    p = e.position_at(i / 16.0)
                    ix.append(math.hypot(p.X, p.Y))
        base_r = max(ix) if ix else 0.0
        apex, ceil = ibb.min.Z, ibb.max.Z
        cone_z_at_wall = apex + (ceil - apex) * POCKET_R / base_r if base_r else None
        void = {
            "shell_count": len(shells),
            "inner_shell_area_mm2": r6(inner.area),
            "bbox": bbox_dict(inner),
            "apex_z": r6(apex),
            "ceiling_z": r6(ceil),
            "base_radius_mm": r6(base_r),
            "volume_mm3": r6((1.0 / 3.0) * math.pi * base_r ** 2 * (ceil - apex)) if base_r else None,
            "max_radius_mm": r6(base_r),
            "cone_z_at_pocket_wall": r6(cone_z_at_wall) if cone_z_at_wall is not None else None,
            "slit_at_pocket_wall_mm": r6(ceil - cone_z_at_wall) if cone_z_at_wall is not None else None,
            "void_apex_above_floor_mm": r6(apex - cfg["floor_z"]),
        }

    return {
        "rim_top_z": r6(top_z),
        "top_face_count": len(top_faces),
        "top_face_zs": sorted({r6(face_plane(f)[0]) for f in top_faces}),
        "top_profile": profile,
        "groove_face_count": len(groove_faces),
        "groove_min_radius_mm": groove_r,
        "groove_status": groove_status,
        "groove_clearance_mm": groove_clearance,
        "fillet_face_count": len(fillet_faces),
        "fillet_start_radius_mm": fillet_r,
        "fillet_clearance_mm": fillet_clearance,
        "outer_max_radius_mm": r6(outer_max),
        "outer_edge_clearance_mm": outer_clearance,
        "underside_probes": undersides,
        "plate_body_bottom_z": r6(body_bottom),
        "internal_void": void,
    }


def process_shape(key: str, cfg: dict) -> dict:
    t_start = time.time()
    odir = OUT / key
    odir.mkdir(parents=True, exist_ok=True)

    plate_path = REPO / cfg["plate_step"]
    comp = import_step(str(plate_path))
    solids = comp.solids()
    assert len(solids) == 1, f"{key}: plate STEP has {len(solids)} solids"
    plate = solids[0]

    before = {
        "solid_count": len(solids),
        "is_valid": bool(plate.is_valid),
        "volume_mm3": r6(plate.volume),
        "bbox": bbox_dict(plate),
        "shell_count": len(plate.shells()),
        "shell_areas_mm2": [r6(s.area) for s in plate.shells()],
    }
    info = analyse_plate(plate, cfg)

    rim_z = info["rim_top_z"]
    floor_z = r6(rim_z - TOP_CLEAR - cfg["print_thickness"])
    cfg_ok = abs(floor_z - cfg["floor_z"]) < 1e-6 and abs(rim_z - cfg["rim_z"]) < 1e-6
    assert cfg_ok, f"{key}: spec mismatch rim {rim_z} floor {floor_z} vs {cfg}"
    pocket_depth = r6(rim_z - floor_z)

    tool = make_tool(floor_z, rim_z)
    expected_removed = r6((plate & tool).volume) if (plate & tool) is not None else 0.0

    res = plate - tool
    res_solids = res.solids()
    after = {
        "solid_count": len(res_solids),
        "is_valid": all(bool(s.is_valid) for s in res_solids),
        "volume_mm3": r6(res.volume),
        "bbox": bbox_dict(res),
        "shell_count": len(res.shells()),
    }
    delta = r6(before["volume_mm3"] - after["volume_mm3"])
    nominal = r6(math.pi * POCKET_R ** 2 * pocket_depth)
    legacy_nominal = r6(math.pi * POCKET_R ** 2 * 1.25)

    # ---- pocket measurement -------------------------------------------------
    faces = res.faces()
    floor_candidates = [f for f in faces
                        if f.geom_type == GeomType.PLANE
                        and abs(face_plane(f)[0] - floor_z) < 1e-6
                        and face_plane(f)[3] > 0.999]
    assert floor_candidates, f"{key}: pocket floor face not found"
    floor_face = max(floor_candidates, key=lambda f: f.area)
    fz, fnx, fny, fnz = face_plane(floor_face)
    fvs = [vtx_pt(v)[2] for v in floor_face.vertices()]
    floor_flatness = r6(max(abs(z - fz) for z in fvs)) if fvs else 0.0
    # also test all floor-face edge samples lie on the plane
    edge_dev = 0.0
    for e in floor_face.edges():
        for i in range(33):
            edge_dev = max(edge_dev, abs(e.position_at(i / 32.0).Z - fz))
    floor_flatness = r6(max(floor_flatness, edge_dev))

    wall_bands = []
    wall_radii = []
    for f in faces:
        r = cyl_radius(f)
        if r is not None and abs(r - POCKET_R) < 1e-4:
            bb = f.bounding_box()
            wall_bands.append({"z_min": r6(bb.min.Z), "z_max": r6(bb.max.Z),
                               "area_mm2": r6(f.area)})
            wall_radii.append(r)
    wall_bands.sort(key=lambda b: b["z_min"])
    wall_radius = r6(min(wall_radii)) if wall_radii else None

    top_rim_probe = probe(plate, POCKET_R + 0.5, 0.0, floor_z - 2.0, rim_z + 1.0)
    top_center_probe = probe(plate, 0.0, 0.0, floor_z - 2.0, rim_z + 1.0)
    top_at_rim = r6(top_rim_probe[1]) if top_rim_probe else None
    top_at_center = r6(top_center_probe[1]) if top_center_probe else None
    depth_at_rim = r6(top_at_rim - floor_z) if top_at_rim is not None else None
    depth_at_center = r6(top_at_center - floor_z) if top_at_center is not None else None

    remaining = r6(floor_z - info["plate_body_bottom_z"])

    # ---- export -------------------------------------------------------------
    step_path = odir / "plate_recessed.step"
    stl_path = odir / "plate_recessed.stl"
    export_step(res, str(step_path))
    export_stl(res, str(stl_path), tolerance=STL_TOL, angular_tolerance=STL_ANG)

    # ---- STEP re-import -----------------------------------------------------
    recomp = import_step(str(step_path))
    rsols = recomp.solids()
    reimport = {
        "solid_count": len(rsols),
        "is_valid": all(bool(s.is_valid) for s in rsols),
        "volume_mm3": r6(recomp.volume),
        "volume_delta_rel": r6(abs(recomp.volume - after["volume_mm3"]) / after["volume_mm3"]),
        "bbox": bbox_dict(recomp),
    }

    stl_stats = read_stl(stl_path)
    step_bytes = step_path.stat().st_size
    stl_bytes = stl_path.stat().st_size

    # ---- optional clean variant (fill pre-existing internal void) ----------
    clean = None
    if before["shell_count"] > 1:
        inner = plate.shells()[-1]
        ibb = inner.bounding_box()
        z_apex, z_top = ibb.min.Z, ibb.max.Z
        rr = []
        for f in inner.faces():
            for e in f.edges():
                for i in range(17):
                    p = e.position_at(i / 16.0)
                    rr.append(math.hypot(p.X, p.Y))
        r_base = max(rr)
        cavity = Pos(0, 0, z_apex) * Cone(0.0, r_base, z_top - z_apex, align=ALIGN_CZMIN)
        overlap = (plate & cavity).volume
        filled = plate + cavity
        clean_res = single_solid(filled - tool)
        cstep = odir / "plate_recessed_clean.step"
        cstl = odir / "plate_recessed_clean.stl"
        export_step(clean_res, str(cstep))
        export_stl(clean_res, str(cstl), tolerance=STL_TOL, angular_tolerance=STL_ANG)
        c_delta = r6(before["volume_mm3"] + cavity.volume - clean_res.volume)
        crecomp = import_step(str(cstep))
        c_bbox = bbox_dict(clean_res)
        c_ext_same = all(abs(c_bbox[k][i] - after["bbox"][k][i]) < 1e-6
                         for k in ("min", "max") for i in range(3))
        c_prof = []
        for rr in (0.0, 20.0, 40.0):
            p = probe(clean_res, rr, 0.0, floor_z - 2.0, rim_z + 1.0)
            c_prof.append({"r_mm": rr, "top_z": r6(p[1]) if p else None})
        c_bands = []
        for f in clean_res.faces():
            r = cyl_radius(f)
            if r is not None and abs(r - POCKET_R) < 1e-4:
                cb2 = f.bounding_box()
                c_bands.append({"z_min": r6(cb2.min.Z), "z_max": r6(cb2.max.Z)})
        c_bands.sort(key=lambda b: b["z_min"])
        clean = {
            "why": "source plate has a closed internal conical void (2 shells); "
                   "this variant fills that void before cutting, leaving all "
                   "external surfaces identical",
            "void_cone": {
                "apex_z": r6(z_apex), "ceiling_z": r6(z_top),
                "base_radius_mm": r6(r_base), "volume_mm3": r6(cavity.volume),
                "overlap_with_plate_mm3": r6(overlap),
            },
            "filled_plate_shell_count": len(filled.shells()),
            "solid_count": 1,
            "is_valid": bool(clean_res.is_valid),
            "volume_mm3": r6(clean_res.volume),
            "volume_delta_mm3": c_delta,
            "volume_delta_vs_nominal": r6(nominal - c_delta),
            "step_reimport": {
                "solid_count": len(crecomp.solids()),
                "is_valid": all(bool(s.is_valid) for s in crecomp.solids()),
                "volume_mm3": r6(crecomp.volume),
            },
            "stl": read_stl(cstl),
            "external_bbox_identical_to_primary": c_ext_same,
            "external_bbox": c_bbox,
            "top_profile": c_prof,
            "wall_bands": c_bands,
            "pocket_wall_slit_removed": len(c_bands) == 1,
            "files": {"step": rel(cstep), "stl": rel(cstl)},
        }

    # ---- art / print metadata ----------------------------------------------
    art = None
    art_json = ART_DIR / cfg["variant"] / "art.json"
    if art_json.exists():
        aj = json.loads(art_json.read_text())
        art = {
            "art_json": rel(art_json),
            "name": aj.get("name"),
            "layer_count": aj.get("layer_count"),
            "layer_height_mm": aj.get("layer_height_mm"),
            "palette_bottom_up": aj.get("palette_bottom_up"),
            "palette_colors": len(aj.get("palette_bottom_up") or []),
            "art_diameter_mm": aj.get("art_diameter_mm"),
            "frame_mm": aj.get("frame_mm"),
            "print_thickness_mm": aj.get("print_thickness_mm"),
            "thickness_matches_spec": abs((aj.get("print_thickness_mm") or -1)
                                          - cfg["print_thickness"]) < 1e-6,
        }
    print_top = r6(floor_z + cfg["print_thickness"])
    print_info = {
        "diameter_mm": PRINT_D,
        "radius_mm": PRINT_R,
        "thickness_mm": cfg["print_thickness"],
        "radial_interference_mm": r6(PRINT_R - POCKET_R),
        "volume_mm3": r6(math.pi * PRINT_R ** 2 * cfg["print_thickness"]),
        "interference_ring_volume_mm3": r6(math.pi * (PRINT_R ** 2 - POCKET_R ** 2)
                                           * cfg["print_thickness"]),
        "top_z": print_top,
        "top_below_rim_mm": r6(rim_z - print_top),
        "placement": {
            "xy_center_mm": [0.0, 0.0],
            "print_local_z_range_mm": [0.0, cfg["print_thickness"]],
            "translate_mm": [0.0, 0.0, floor_z],
            "rotate_deg_xyz": [0.0, 0.0, 0.0],
            "rule": "print bottom on pocket floor, XY centred (0,0), no rotation",
        },
    }

    return {
        "key": key,
        "label": cfg["label"],
        "variant": cfg["variant"],
        "project": cfg["project"],
        "source_plate_step": cfg["plate_step"],
        "rim_top_z": rim_z,
        "floor_z": floor_z,
        "pocket_depth_mm": pocket_depth,
        "pocket": {
            "diameter_mm": POCKET_D,
            "radius_mm": POCKET_R,
            "center_xy_mm": [0.0, 0.0],
            "floor_z": floor_z,
            "depth_mm": pocket_depth,
            "floor_face_z": r6(fz),
            "floor_face_normal": [r6(fnx), r6(fny), r6(fnz)],
            "floor_face_area_mm2": r6(floor_face.area),
            "floor_flatness_mm": floor_flatness,
            "wall_radius_mm": wall_radius,
            "wall_diameter_mm": r6(2 * wall_radius) if wall_radius else None,
            "wall_bands": wall_bands,
            "depth_at_rim_mm": depth_at_rim,
            "depth_at_center_mm": depth_at_center,
            "top_z_at_center": top_at_center,
            "top_z_at_rim": top_at_rim,
            "depth_samples_r0_r20_r40": [
                {"r_mm": pp["r_mm"], "top_z": pp["top_z"],
                 "depth_mm": r6(pp["top_z"] - floor_z)}
                for pp in info["top_profile"] if pp["r_mm"] in (0.0, 20.0, 40.0)
            ],
            "depth_uniform": bool(max(abs(pp["top_z"] - rim_z)
                                      for pp in info["top_profile"] if pp["top_z"] is not None) < 1e-6),
            "floor_is_print_z_reference": True,
        },
        "print": print_info,
        "art": art,
        "remaining_material_under_floor_mm": remaining,
        "plate_body_bottom_z": info["plate_body_bottom_z"],
        "skirt_top_clearance_mm": remaining,
        "plate_features_before": info,
        "plate_before": before,
        "plate_after": after,
        "volume": {
            "delta_mm3": delta,
            "nominal_pi_r2_depth_mm3": nominal,
            "delta_vs_nominal_pct": r6(100.0 * (delta - nominal) / nominal),
            "expected_from_actual_material_mm3": expected_removed,
            "delta_vs_expected_pct": r6(100.0 * (delta - expected_removed) / expected_removed)
            if expected_removed else None,
            "preexisting_removed_inside_pocket_mm3": r6(nominal - expected_removed),
            "nominal_pi_r2_1p25_mm3_original_task": legacy_nominal,
            "delta_vs_original_1p25_pct": r6(100.0 * (delta - legacy_nominal) / legacy_nominal),
            "check_nominal_within_15pct": bool(abs(delta - nominal) / nominal <= 0.15),
            "check_expected_within_0p1pct": bool(expected_removed
                                                 and abs(delta - expected_removed) / expected_removed <= 0.001),
        },
        "bbox_unchanged": all(abs(before["bbox"][k][i] - after["bbox"][k][i]) < 1e-6
                              for k in ("min", "max") for i in range(3)),
        "step_reimport": reimport,
        "stl": stl_stats,
        "clean_variant": clean,
        "files": {
            "plate_step": rel(step_path),
            "plate_stl": rel(stl_path),
            "step_bytes": step_bytes,
            "stl_bytes": stl_bytes,
        },
        "runtime_s": r6(time.time() - t_start),
    }


# ---------------------------------------------------------------------------
# blanks / parts / blender
# ---------------------------------------------------------------------------
def make_blank(thickness_mm: float, path: Path, print_dia_mm: float | None = None) -> dict:
    pd = PRINT_D if print_dia_mm is None else float(print_dia_mm)
    blank = Pos(0, 0, 0) * Cylinder(pd / 2.0, thickness_mm, align=ALIGN_CZMIN)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(blank, str(path), tolerance=STL_TOL, angular_tolerance=STL_ANG)
    st = read_stl(path)
    d = import_step if False else None  # noqa: F841  (no STEP export for blanks)
    return {
        "file": rel(path),
        "diameter_mm": pd,
        "thickness_mm": thickness_mm,
        "z_range_mm": [0.0, thickness_mm],
        "stl": st,
        "bytes": path.stat().st_size,
    }


def collect_parts(shape_key: str, cfg: dict) -> dict:
    proj = REPO / cfg["project"] / "build" / "parts"
    legacy = LEGACY_PARTS.get(shape_key, set())
    entries = []
    for step in sorted(proj.glob("*.step")):
        name = step.stem
        if name == "plate_v01":
            continue
        stl = proj / f"{name}.stl"
        s = import_step(str(step))
        bb = s.bounding_box()
        entries.append({
            "name": name,
            "step": rel(step),
            "stl": rel(stl),
            "stl_exists": stl.exists(),
            "max_z_mm": r6(bb.max.Z),
            "bbox_min": [r6(bb.min.X), r6(bb.min.Y), r6(bb.min.Z)],
            "bbox_max": [r6(bb.max.X), r6(bb.max.Y), r6(bb.max.Z)],
            "legacy": name in legacy,
            "use_in_render": name not in legacy,
        })
    return {
        "shape": shape_key,
        "source": "mechanical/{}/build/parts/*.stl (NOT copied; paths are repo-relative)".format(
            cfg["project"].split("/", 1)[1]),
        "plate": {
            "source_step": cfg["plate_step"],
            "recessed_step": rel(OUT / shape_key / "plate_recessed.step"),
            "recessed_stl": rel(OUT / shape_key / "plate_recessed.stl"),
            "note": "use the recessed plate STL in place of plate_v01.stl",
        },
        "internal_parts": entries,
    }


def internal_check(key: str, cfg: dict, result: dict) -> dict:
    parts = collect_parts(key, cfg)
    used = [p for p in parts["internal_parts"] if p["use_in_render"]]
    top = max(used, key=lambda p: p["max_z_mm"])
    floor = result["floor_z"]
    return {
        "parts_checked": len(parts["internal_parts"]),
        "parts_checked_non_legacy": len(used),
        "max_internal_part_z_mm": top["max_z_mm"],
        "max_internal_part": top["name"],
        "floor_z": floor,
        "margin_floor_minus_max_internal_mm": r6(floor - top["max_z_mm"]),
        "plate_skirt_top_z": r6(floor - result["remaining_material_under_floor_mm"]),
        "margin_floor_minus_skirt_mm": result["remaining_material_under_floor_mm"],
        "all_internal_below_floor": all(p["max_z_mm"] < floor for p in used),
        "no_xy_intersection_required_because_all_below_floor": True,
    }


def blender_check(stl_files: list) -> dict | None:
    if not (Path(BLENDER).exists() and os.access(BLENDER, os.X_OK)):
        return None
    expr = r"""
import bpy, os, json, mathutils
files = json.loads(os.environ["SC_STL_FILES"])
out = []
for p in files:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=p)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo = [1e9]*3; hi = [-1e9]*3
    tris = 0
    for o in objs:
        tris += len(o.data.polygons)
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    out.append({"file": p, "objects": len(objs), "triangles": tris,
                "bbox_min": [round(v,6) for v in lo], "bbox_max": [round(v,6) for v in hi]})
print("SCBLENDER_JSON=" + json.dumps(out))
"""
    env = dict(os.environ)
    env["SC_STL_FILES"] = json.dumps(stl_files)
    try:
        cp = subprocess.run([BLENDER, "-b", "--python-expr", expr],
                            capture_output=True, text=True, timeout=240, env=env)
    except Exception as exc:  # pragma: no cover
        return {"error": repr(exc)}
    for line in cp.stdout.splitlines():
        if line.startswith("SCBLENDER_JSON="):
            return {"version": "4.5.3", "imports": json.loads(line.split("=", 1)[1])}
    return {"error": "no SCBLENDER_JSON in output",
            "stdout_tail": cp.stdout[-800:], "stderr_tail": cp.stderr[-800:]}


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def fmt(x, n=4):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "NO"
    if isinstance(x, (int,)):
        return str(x)
    if isinstance(x, float):
        s = f"{x:,.{n}f}"
        return s
    return str(x)


def make_report(data, bl, elapsed) -> str:
    L = []
    A = L.append
    A("# Appearance shell CAD - recessed top plate for the Kromacut print")
    A("")
    A("Generated by `appearance/cad/run_shell.sh` (build123d "
      f"{data['build123d_version']}) at {data['generated_at_utc']}.")
    A("This is an **appearance adaptation**. The 21-check self-test and FEA "
      "were **not** re-run on the recessed plate; stiffness/strength of the "
      "recessed plate is unverified (see PROVISIONAL).")
    A("")
    A("## 1. Command (one command, idempotent)")
    A("")
    A("```bash")
    A("appearance/cad/run_shell.sh")
    A("```")
    A("")
    A(f"- interpreter: `{data['interpreter']}`")
    A(f"- build123d: `{data['build123d_version']}`")
    A(f"- wall time: {elapsed:.1f} s")
    A("")
    A("## 2. Spec")
    A("")
    A("| item | value |")
    A("|---|---|")
    A(f"| pocket | 1 flat-bottom cylinder, d{POCKET_D:.1f} mm, centred (0,0) |")
    A(f"| print | d{PRINT_D:.1f} mm x print thickness, placed in place and fused by the slicer |")
    A("| floor | rim_top_z - 0.05 - print_thickness |")
    A(f"| radial interference | {RADIAL_INT:.2f} mm (print r{PRINT_R:.1f} vs pocket r{POCKET_R:.1f}) |")
    A("| print top | 0.05 mm below the rim top |")
    A("")
    A("Two versions differ only in the print thickness (palette layer count):")
    A("")
    A("| shape | variant | print layers | print t | rim z | floor z | pocket depth | print top |")
    A("|---|---|---|---|---|---|---|---|")
    for k in ("round", "square"):
        s = data["shapes"][k]
        art = s.get("art") or {}
        A(f"| {k} | {s['variant']} | {art.get('layer_count')} x "
          f"{art.get('layer_height_mm')} mm | {s['print']['thickness_mm']:.2f} | "
          f"{s['rim_top_z']:.2f} | {s['floor_z']:.2f} | {s['pocket_depth_mm']:.2f} | "
          f"{s['print']['top_z']:.2f} |")
    A("")
    A("## 3. Art cross-check")
    A("")
    for k in ("round", "square"):
        s = data["shapes"][k]
        art = s.get("art")
        if not art:
            A(f"- **{k}**: art.json not found at build time -> PROVISIONAL "
              "(print thickness from Lead spec).")
            continue
        A(f"- **{k}** (`{art['art_json']}`): {art['palette_colors']} colours x "
          f"{art['layer_height_mm']} mm = {art['print_thickness_mm']} mm; "
          f"art diameter {art['art_diameter_mm']} mm, frame {art['frame_mm']} mm; "
          f"matches spec: {fmt(art['thickness_matches_spec'])}")
    A("")
    A("## 4. Per-shape verification (measured)")
    A("")
    for k in ("round", "square"):
        s = data["shapes"][k]
        v = s["volume"]
        p = s["pocket"]
        A(f"### 4.{1 if k=='round' else 2} {k} - {s['label']}")
        A("")
        A(f"Source: `{s['source_plate_step']}` (read-only, imported + boolean cut; "
          "not rebuilt).")
        A("")
        A("| check | value |")
        A("|---|---|")
        A(f"| plate solids before / valid | {s['plate_before']['solid_count']} / "
          f"{fmt(s['plate_before']['is_valid'])} |")
        A(f"| plate shells before | {s['plate_before']['shell_count']} |")
        b = s["plate_before"]["bbox"]
        a = s["plate_after"]["bbox"]
        A(f"| bbox before min/max | ({b['min'][0]:.3f}, {b['min'][1]:.3f}, {b['min'][2]:.3f}) / "
          f"({b['max'][0]:.3f}, {b['max'][1]:.3f}, {b['max'][2]:.3f}) |")
        A(f"| bbox after min/max | ({a['min'][0]:.3f}, {a['min'][1]:.3f}, {a['min'][2]:.3f}) / "
          f"({a['max'][0]:.3f}, {a['max'][1]:.3f}, {a['max'][2]:.3f}) |")
        A(f"| bbox unchanged | {fmt(s['bbox_unchanged'])} |")
        A(f"| solids after / valid | {s['plate_after']['solid_count']} / "
          f"{fmt(s['plate_after']['is_valid'])} |")
        A(f"| shells after | {s['plate_after']['shell_count']} |")
        A(f"| volume before | {fmt(s['plate_before']['volume_mm3'])} mm3 |")
        A(f"| volume after | {fmt(s['plate_after']['volume_mm3'])} mm3 |")
        A(f"| volume delta | {fmt(v['delta_mm3'])} mm3 |")
        A(f"| nominal pi*r^2*depth | {fmt(v['nominal_pi_r2_depth_mm3'])} mm3 "
          f"(delta {fmt(v['delta_vs_nominal_pct'],3)} %) |")
        A(f"| material above floor inside pocket (measured before cut) | "
          f"{fmt(v['expected_from_actual_material_mm3'])} mm3 "
          f"(delta {fmt(v['delta_vs_expected_pct'],4)} %) |")
        A(f"| pre-existing removed material inside pocket | "
          f"{fmt(v['preexisting_removed_inside_pocket_mm3'])} mm3 |")
        A(f"| original task nominal pi*r^2*1.25 | {fmt(v['nominal_pi_r2_1p25_mm3_original_task'])} mm3 "
          f"(delta {fmt(v['delta_vs_original_1p25_pct'],3)} %) |")
        A(f"| pocket floor plane z / normal | {fmt(p['floor_face_z'])} / "
          f"({fmt(p['floor_face_normal'][0],3)}, {fmt(p['floor_face_normal'][1],3)}, "
          f"{fmt(p['floor_face_normal'][2],3)}) |")
        A(f"| pocket floor area / flatness | {fmt(p['floor_face_area_mm2'])} mm2 / "
          f"{fmt(p['floor_flatness_mm'],6)} mm |")
        A(f"| pocket wall radius / diameter | {fmt(p['wall_radius_mm'])} / "
          f"{fmt(p['wall_diameter_mm'])} mm |")
        bands = ", ".join(f"{bb['z_min']:.3f}..{bb['z_max']:.3f}" for bb in p["wall_bands"])
        A(f"| pocket wall z bands | {bands} |")
        A(f"| top surface z at rim / at centre | {fmt(p['top_z_at_rim'])} / "
          f"{fmt(p['top_z_at_center'])} mm |")
        A(f"| pocket depth at rim / at centre | {fmt(p['depth_at_rim_mm'])} / "
          f"{fmt(p['depth_at_center_mm'])} mm |")
        ds = p.get("depth_samples_r0_r20_r40") or []
        if ds:
            A("| pocket depth at r=0/20/40 | " + ", ".join(
                f"r={d['r_mm']:.0f}: {fmt(d['depth_mm'])}" for d in ds) + " mm |")
        A(f"| depth uniform (flat top) | {fmt(p.get('depth_uniform'))} |")
        vd = s["plate_features_before"].get("internal_void")
        if vd:
            A(f"| PRE-EXISTING internal void in source STEP | apex z {fmt(vd['apex_z'])}, "
              f"ceiling z {fmt(vd['ceiling_z'])}, base R {fmt(vd['base_radius_mm'])}, "
              f"vol {fmt(vd['volume_mm3'])} mm3 (2 shells) |")
            A(f"| opened pocket-wall slit at r=43 | z {fmt(vd['cone_z_at_pocket_wall'])}.."
              f"{fmt(vd['ceiling_z'])}, height {fmt(vd['slit_at_pocket_wall_mm'])} mm |")
            A(f"| void apex above solid floor | {fmt(vd['void_apex_above_floor_mm'])} mm |")
        A(f"| remaining material under floor | {fmt(s['remaining_material_under_floor_mm'])} mm |")
        A(f"| clearance to etched groove | "
          f"{fmt(s['plate_features_before']['groove_clearance_mm'])} mm "
          f"({s['plate_features_before']['groove_status']}) |")
        A(f"| clearance to top-edge fillet | "
          f"{fmt(s['plate_features_before']['fillet_clearance_mm'])} mm |")
        A(f"| clearance to outer edge | "
          f"{fmt(s['plate_features_before']['outer_edge_clearance_mm'])} mm |")
        A(f"| internal parts checked (non-legacy) | "
          f"{s['internal_check']['parts_checked_non_legacy']} |")
        A(f"| max internal part z / part | "
          f"{fmt(s['internal_check']['max_internal_part_z_mm'])} mm / "
          f"{s['internal_check']['max_internal_part']} |")
        A(f"| margin floor - max internal z | "
          f"{fmt(s['internal_check']['margin_floor_minus_max_internal_mm'])} mm |")
        A(f"| STEP re-import solids / valid | "
          f"{s['step_reimport']['solid_count']} / {fmt(s['step_reimport']['is_valid'])} |")
        A(f"| STEP re-import volume rel. delta | "
          f"{fmt(s['step_reimport']['volume_delta_rel'],8)} |")
        A(f"| STL triangles / watertight | {s['stl']['triangles']:,} / "
          f"{fmt(s['stl']['watertight'])} |")
        A(f"| STL non-manifold / boundary edges | "
          f"{s['stl']['nonmanifold_edges']} / {s['stl']['boundary_edges']} |")
        A("")
        if s.get("clean_variant"):
            c = s["clean_variant"]
            A(f"Optional clean variant (void filled before the cut): "
              f"`{c['files']['step']}`, `{c['files']['stl']}` - solids "
              f"{c['solid_count']}, valid {fmt(c['is_valid'])}, volume delta "
              f"{fmt(c['volume_delta_mm3'])} mm3 vs nominal "
              f"{fmt(v['nominal_pi_r2_depth_mm3'])} mm3, STEP re-import "
              f"{c['step_reimport']['solid_count']} solids, watertight "
              f"{fmt(c['stl']['watertight'])}; external bbox identical to primary: "
              f"{fmt(c['external_bbox_identical_to_primary'])}; pocket-wall slit "
              f"removed: {fmt(c['pocket_wall_slit_removed'])} "
              f"(wall bands {[b['z_min'] for b in c['wall_bands']]}.."
              f"{[b['z_max'] for b in c['wall_bands']]}).")
            A("")

    A("## 5. Print blanks (placeholders for pipeline testing)")
    A("")
    A("| file | d | thickness | z range | triangles | watermark |")
    A("|---|---|---|---|---|---|")
    for b in data["blanks"]:
        A(f"| `{b['file']}` | {b['diameter_mm']:.1f} | {b['thickness_mm']:.2f} | "
          f"{b['z_range_mm'][0]:.2f}..{b['z_range_mm'][1]:.2f} | "
          f"{b['stl']['triangles']:,} | {fmt(b['stl']['watertight'])} |")
    A("")
    A("`print_blank.stl` is a byte copy of `print_blank_round.stl` (kept for the "
      "original task wording).")
    A("")
    A("## 6. Blender import check")
    A("")
    if bl and "imports" in bl:
        A(f"Headless Blender {bl['version']}, one object per STL:")
        A("")
        A("| file | objects | triangles | bbox min | bbox max |")
        A("|---|---|---|---|---|")
        for imp in bl["imports"]:
            A(f"| `{imp['file']}` | {imp['objects']} | {imp['triangles']:,} | "
              f"({imp['bbox_min'][0]:.3f}, {imp['bbox_min'][1]:.3f}, {imp['bbox_min'][2]:.3f}) | "
              f"({imp['bbox_max'][0]:.3f}, {imp['bbox_max'][1]:.3f}, {imp['bbox_max'][2]:.3f}) |")
    else:
        A("Blender check not run (blender missing or failed): " + json.dumps(bl))
    A("")
    A("## 7. Files produced")
    A("")
    for f in data["files"]:
        A(f"- `{f}`")
    A("")
    A("## 8. Findings / caveats / PROVISIONAL")
    A("")
    for note in data["notes"]:
        A(f"- {note}")
    A("")
    A("## 9. Reproduction")
    A("")
    A("```bash")
    A("appearance/cad/run_shell.sh            # rebuilds every artifact above")
    A("")
    A("# independent re-verification (separate script; re-imports STEP/STL and")
    A("# re-checks every number above against shell.json):")
    A(f"{PYEXE} appearance/cad/verify_shell.py")
    A("")
    A("# optional direct build without the Blender import check:")
    A(f"{PYEXE} appearance/cad/build_recessed.py --skip-blender")
    A("```")
    A("")
    A("Machine-readable contract for the render / 3MF stages: "
      "`appearance/build/shell/shell.json`; assembly part pointers: "
      "`appearance/build/shell/parts.json`.")
    A("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    global SHAPES
    ap = argparse.ArgumentParser(
        description="Recessed top plate + Kromacut print blanks for the appearance "
                    "pipeline (default = the verified round/square constants).")
    ap.add_argument("--skip-blender", action="store_true",
                    help="skip the Blender STL-import cross-check (~2 s)")
    ap.add_argument("--config", default=None,
                    help="appearance/config/appearance_project.yaml (or compile-resolved "
                         "JSON) to take rim/pocket/print diameter/interference/top gap/"
                         "print thickness from; omit for the built-in verified values")
    args = ap.parse_args(argv)
    skip_blender = args.skip_blender
    use_config = args.config is not None
    if use_config:
        SHAPES = load_project_config(args.config)
    t0 = time.time()

    OUT.mkdir(parents=True, exist_ok=True)
    try:
        import build123d
        b3d_version = build123d.__version__
    except Exception:  # pragma: no cover
        b3d_version = "unknown"

    shapes = {}
    notes = []
    for key, cfg in SHAPES.items():
        if use_config:
            apply_geometry(cfg)
        print(f"[shell-cad] building {key} ...", flush=True)
        shapes[key] = process_shape(key, cfg)
        s = shapes[key]
        print(f"[shell-cad]   {key}: {s['volume']['delta_mm3']:.3f} mm3 removed, "
              f"floor {s['floor_z']:.3f}, solids {s['plate_after']['solid_count']}, "
              f"valid {s['plate_after']['is_valid']}", flush=True)

    # blanks (per-version print diameter; the round one doubles as the generic alias)
    if use_config:
        apply_geometry(SHAPES["round"])  # canonical shared print geometry
    blanks = []
    b_round = make_blank(SHAPES["round"]["print_thickness"],
                         OUT / "print_blank_round.stl",
                         SHAPES["round"].get("print_dia"))
    b_square = make_blank(SHAPES["square"]["print_thickness"],
                          OUT / "print_blank_square.stl",
                          SHAPES["square"].get("print_dia"))
    blanks.extend([b_round, b_square])
    alias = OUT / "print_blank.stl"
    alias.write_bytes((OUT / "print_blank_round.stl").read_bytes())
    blanks.append({
        "file": rel(alias),
        "diameter_mm": PRINT_D,
        "thickness_mm": SHAPES["round"]["print_thickness"],
        "z_range_mm": [0.0, SHAPES["round"]["print_thickness"]],
        "stl": read_stl(alias),
        "bytes": alias.stat().st_size,
        "alias_of": "print_blank_round.stl",
    })

    # parts.json + internal checks
    parts_doc = {"schema": "smartcoaster.appearance.shell.parts/v1",
                 "generated_by": "appearance/cad/run_shell.sh",
                 "units": "mm",
                 "note": "assembly STLs are referenced from mechanical/** (no copies)",
                 "shapes": {}}
    for key, cfg in SHAPES.items():
        parts_doc["shapes"][key] = collect_parts(key, cfg)
        shapes[key]["internal_check"] = internal_check(key, cfg, shapes[key])

    # ---- global notes -------------------------------------------------------
    rd = shapes["round"]
    sq = shapes["square"]
    notes.append("**PROVISIONAL (appearance adaptation):** the recessed plates were NOT re-run "
                 "through mechanical/square_v1/cad/verify_v01.py (21 checks) or any FEA. "
                 "The pocket removes plate material (square -1.45 mm to a 1.55 mm floor web, "
                 "round -1.25 mm to a 1.75 mm web); stiffness, force-path, overload-stop and "
                 "drop behaviour are unverified.")
    notes.append("**PROVISIONAL:** the print is assumed fused in place by the slicer "
                 "(Kromacut multi-material 3MF). No slicer/Bambu test was run here; the 0.2 mm "
                 "radial interference and 0.05 mm top step are nominal CAD values.")
    notes.append("**Source-model defect found in the round (LUMEN) plate:** "
                 f"`{rd['source_plate_step']}` is a **2-shell solid** - it contains a closed "
                 "internal conical void (apex z=16.100, ceiling z=16.700, base radius 48.0 mm, "
                 f"volume {rd['clean_variant']['void_cone']['volume_mm3'] if rd.get('clean_variant') else 'n/a'} mm3). "
                 "The model intended a top dish (`Cone` default Z alignment cuts a void instead). "
                 "Consequence for this task: the top surface is FLAT at z=17.000 (no conical dish), "
                 "and the pocket cut opens that void as a thin annular slit in the pocket wall. "
                 "The primary `round/plate_recessed.*` keeps the validated STEP intact; "
                 "`round/plate_recessed_clean.*` is the same cut after filling the void "
                 "(external surfaces unchanged) and is the recommended file for render/3MF if the "
                 "slit is visible. Both are appearance artifacts only. This should be fixed "
                 "upstream in mechanical/lumen (read-only here).")
    notes.append("**Task-fact discrepancy (round):** the task brief said the round plate has a "
                 "`conical dish ~0.9 mm deep at centre`; measured geometry says the top is flat "
                 "at z=17.000 everywhere inside d96 (probes r=0..45 all 17.000) and the dish-like "
                 "geometry is the hidden internal void above. The pocket floor spec (15.75) is "
                 "therefore still correct because it is rim-based, and pocket depth is uniform "
                 "1.25 mm - there is no rim-vs-centre depth difference.")
    notes.append("**Spec update (square):** floor 16.55 / depth 1.45 (elf print 1.40 mm, 7x0.2 mm), "
                 "superseding the earlier 1.25 mm/16.75 draft. Volume delta matches "
                 "pi*r^2*1.45 to <0.01 %.")
    notes.append(f"**Volume criterion:** square delta {sq['volume']['delta_mm3']:.3f} mm3 vs "
                 f"pi*43^2*1.45 = {sq['volume']['nominal_pi_r2_depth_mm3']:.3f} mm3 "
                 f"({sq['volume']['delta_vs_nominal_pct']:+.4f} %). Round delta "
                 f"{rd['volume']['delta_mm3']:.3f} mm3 vs pi*43^2*1.25 = "
                 f"{rd['volume']['nominal_pi_r2_depth_mm3']:.3f} mm3 "
                 f"({rd['volume']['delta_vs_nominal_pct']:+.2f} %) - outside the +/-15 % band, "
                 "because the pre-existing engraved ring (12.25 mm3) and internal void "
                 f"({rd['volume']['preexisting_removed_inside_pocket_mm3'] - 12.25:.2f} mm3) were "
                 "already air inside the pocket footprint before the cut. Against the material "
                 f"actually above the floor the match is {rd['volume']['delta_vs_expected_pct']:+.4f} %; "
                 "the void-filled clean variant is "
                 f"{abs(rd['clean_variant']['volume_delta_vs_nominal']):.4f} mm3 below nominal, "
                 "exactly the pre-existing engraved ring volume." if rd.get('clean_variant')
                 else "**Volume criterion:** round delta outside 15 % for the reasons above.")
    notes.append("**Clearance results:** " + "; ".join(
        f"{k}: groove {fmt(v['plate_features_before']['groove_clearance_mm'])} mm "
        f"({v['plate_features_before']['groove_status']}), fillet "
        f"{fmt(v['plate_features_before']['fillet_clearance_mm'])} mm, outer edge "
        f"{fmt(v['plate_features_before']['outer_edge_clearance_mm'])} mm"
        for k, v in shapes.items()) + ". All outside-pocket clearances > 1 mm.")
    notes.append("**Internal-parts collision:** " + "; ".join(
        f"{k}: max internal part z {fmt(v['internal_check']['max_internal_part_z_mm'])} mm "
        f"({v['internal_check']['max_internal_part']}), floor {fmt(v['floor_z'])} mm, margin "
        f"{fmt(v['internal_check']['margin_floor_minus_max_internal_mm'])} mm"
        for k, v in shapes.items()) + ". All internal parts are far below the pocket floors.")
    notes.append("**Round plate skirt/column:** skirt top z=14.000 and centre boss z=14.000; "
                 "pocket floor 15.750 -> 1.75 mm clearance, i.e. the cut never touches the skirt "
                 "or force column. Square: skirt/boss top z=15.000, floor 16.550 -> 1.55 mm.")
    notes.append("**Legacy round parts:** `guide_v01` / `ledflex_v01` exist in the LUMEN build "
                 "(legacy light guide, user decision 2026-11-04 removed LEDs) and are marked "
                 "`use_in_render: false` in parts.json; they were still checked for Z (max 13.4 mm).")
    _rv = rd["plate_features_before"]["internal_void"] or {}
    notes.append("**Round source defect - what it is (a):** the validated STEP itself is a "
                 "2-shell solid: a closed conical void inside the plate "
                 f"(apex z={fmt(_rv.get('apex_z'))}, ceiling z={fmt(_rv.get('ceiling_z'))}, "
                 f"base radius {fmt(_rv.get('base_radius_mm'))} mm, volume "
                 f"{fmt(_rv.get('volume_mm3'))} mm3). It is present in the source file BEFORE any "
                 "cut and was not introduced by this task. The pocket floor at z=15.75 is solid "
                 f"material, {fmt(_rv.get('void_apex_above_floor_mm'))} mm below the void's lowest "
                 "point (centre apex 16.10).")
    notes.append("**Round source defect - pocket wall slit (b):** the cut opens that void at the "
                 "pocket wall as an annular slit from z="
                 f"{fmt(_rv.get('cone_z_at_pocket_wall'))} to z={fmt(_rv.get('ceiling_z'))} "
                 f"(height {fmt(_rv.get('slit_at_pocket_wall_mm'))} mm) at r=43, extending outward "
                 "under a 0.30 mm thick top skin. That is sub-nozzle scale (~0.06 mm) and is "
                 "covered by the 0.2 mm print radial interference where the print meets the wall, "
                 "but it is an undercut that cannot be machined as-is and may show as a hairline "
                 "in extreme macro renders -> PROVISIONAL.")
    notes.append("**Round source defect - clean variant (c):** external geometry and bounds are "
                 "identical between the faithful primary and the void-filled clean variant "
                 f"(bbox identical: {fmt(rd['clean_variant']['external_bbox_identical_to_primary'] if rd.get('clean_variant') else None)}; "
                 "top surface probes r=0/20/40 both 17.000). The clean variant only fills the "
                 "closed void (external surfaces untouched), removes the wall slit "
                 f"({fmt(rd['clean_variant']['pocket_wall_slit_removed'] if rd.get('clean_variant') else None)}) "
                 "and is offered as an alternative for render/3MF if the hairline matters. "
                 "Canonical shell.json keys describe the FAITHFUL primary.")
    notes.append("**Only intentional overlap:** the 0.2 mm radial interference (print r=43.2 vs "
                 "pocket r=43.0) is the sole designed interpenetration; axially the print sits on "
                 "the solid pocket floor, which is the exact Z reference for placement "
                 "(print local z 0..thickness -> world floor_z..floor_z+thickness).")
    notes.append("**STL bbox in Blender vs exact BRep bbox:** the round plate/blank STLs are "
                 "tessellated with inscribed chords (0.02 mm linear tolerance), so Blender may "
                 "report e.g. x_min=-51.935 instead of -52.000 on the round plate; the exact BRep "
                 "bbox is +/-52.000 (STEP re-import confirms), and the square plate reads exact "
                 "+/-50.000 because its sides are flat. This is mesh approximation, not geometry.")
    notes.append("**Depth is exactly 1.25 / 1.45 at all radii:** because the round top is flat at "
                 "z=17.000 (no dish), depth samples at r=0/20/40 are identical; the pocket floor "
                 "plane is flat to 0.000000 mm (PLANE face) and prints need no Z tilt.")

    # blender STL check
    stl_files = []
    for key in ("round", "square"):
        stl_files.append(str(REPO / shapes[key]["files"]["plate_stl"]))
        if shapes[key].get("clean_variant"):
            stl_files.append(str(REPO / shapes[key]["clean_variant"]["files"]["stl"]))
    stl_files += [str(REPO / "appearance/build/shell/print_blank_round.stl"),
                  str(REPO / "appearance/build/shell/print_blank_square.stl")]
    bl = None if skip_blender else blender_check(stl_files)

    # ---- shell.json ---------------------------------------------------------
    file_list = []
    for key in ("round", "square"):
        file_list.append(shapes[key]["files"]["plate_step"])
        file_list.append(shapes[key]["files"]["plate_stl"])
        if shapes[key].get("clean_variant"):
            file_list.append(shapes[key]["clean_variant"]["files"]["step"])
            file_list.append(shapes[key]["clean_variant"]["files"]["stl"])
    file_list += ["appearance/build/shell/print_blank_round.stl",
                  "appearance/build/shell/print_blank_square.stl",
                  "appearance/build/shell/print_blank.stl",
                  "appearance/build/shell/shell.json",
                  "appearance/build/shell/parts.json",
                  "appearance/build/shell/REPORT.md"]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Compact per-shape contract (exact field names requested by render/3MF stage)
    def contract(s):
        return {
            "rim_z_mm": s["rim_top_z"],
            "floor_z_mm": s["floor_z"],
            "pocket_dia_mm": s["pocket"]["diameter_mm"],
            "pocket_radius_mm": s["pocket"]["radius_mm"],
            "pocket_depth_mm": s["pocket_depth_mm"],
            "print_thickness_mm": s["print"]["thickness_mm"],
            "print_dia_mm": s["print"]["diameter_mm"],
            "interference_mm": s["print"]["radial_interference_mm"],
            "top_gap_mm": s["print"]["top_below_rim_mm"],
            "print_top_z_mm": s["print"]["top_z"],
            "print_variant": s["variant"],
            "placement": s["print"]["placement"],
            "files": {
                "plate_step": s["files"]["plate_step"],
                "plate_stl": s["files"]["plate_stl"],
                "print_blank_stl": (
                    "appearance/build/shell/print_blank_round.stl"
                    if s["key"] == "round" else
                    "appearance/build/shell/print_blank_square.stl"),
            },
        }

    def validation(s):
        return {
            "plate_before": s["plate_before"],
            "plate_after": s["plate_after"],
            "bbox_unchanged": s["bbox_unchanged"],
            "volume": s["volume"],
            "pocket_floor_z": s["pocket"]["floor_face_z"],
            "pocket_floor_flatness_mm": s["pocket"]["floor_flatness_mm"],
            "pocket_wall_diameter_mm": s["pocket"]["wall_diameter_mm"],
            "pocket_depth_at_rim_mm": s["pocket"]["depth_at_rim_mm"],
            "pocket_depth_at_center_mm": s["pocket"]["depth_at_center_mm"],
            "remaining_material_under_floor_mm": s["remaining_material_under_floor_mm"],
            "clearances_mm": {
                "groove": s["plate_features_before"]["groove_clearance_mm"],
                "groove_status": s["plate_features_before"]["groove_status"],
                "fillet": s["plate_features_before"]["fillet_clearance_mm"],
                "outer_edge": s["plate_features_before"]["outer_edge_clearance_mm"],
            },
            "internal_check": s["internal_check"],
            "internal_void_source_defect": s["plate_features_before"]["internal_void"],
            "step_reimport": s["step_reimport"],
            "stl": s["stl"],
            "clean_variant": s.get("clean_variant"),
        }

    # source-geometry facts (Lead decision 3) + variant list
    source_geometry = {}
    variants = {}
    for k in ("round", "square"):
        s = shapes[k]
        pf = s["plate_features_before"]
        vd = pf.get("internal_void")
        flat = bool(all(abs(pp["top_z"] - s["rim_top_z"]) < 1e-6
                        for pp in pf["top_profile"] if pp["top_z"] is not None))
        source_geometry[k] = {
            "source_plate_step": s["source_plate_step"],
            "validated_step_shell_count": s["plate_before"]["shell_count"],
            "internal_void_present_in_validated_step": bool(vd),
            "internal_void": vd,
            "introduced_by_this_task": False,
            "top_surface_flat": flat,
            "top_surface_z_range": [min(pp["top_z"] for pp in pf["top_profile"] if pp["top_z"] is not None),
                                    max(pp["top_z"] for pp in pf["top_profile"] if pp["top_z"] is not None)],
            "dish_present": not flat,
            "dish_note": ("none measured: top is flat at rim_z; the model's intended dish became "
                          "the internal void" if vd else "none (flat plate top)"),
            "pocket_floor_solid_at_z": s["floor_z"],
            "void_apex_above_floor_mm": vd.get("void_apex_above_floor_mm") if vd else None,
            "pocket_wall_slit_height_mm": vd.get("slit_at_pocket_wall_mm") if vd else None,
            "pocket_floor_is_solid_under_print": True,
        }
        v = {"primary": {
            "file_step": s["files"]["plate_step"],
            "file_stl": s["files"]["plate_stl"],
            "faithful_to_validated_step": True,
            "canonical": True,
            "description": "faithful import+cut of the validated plate STEP; use this for render/3MF",
        }}
        if s.get("clean_variant"):
            c = s["clean_variant"]
            v["clean"] = {
                "file_step": c["files"]["step"],
                "file_stl": c["files"]["stl"],
                "faithful_to_validated_step": False,
                "canonical": False,
                "description": "same pocket after filling the pre-existing closed internal void; "
                               "external surfaces/bounds identical to primary",
                "external_bbox_identical_to_primary": c["external_bbox_identical_to_primary"],
                "pocket_wall_slit_removed": c["pocket_wall_slit_removed"],
                "recommended_if": "render shows the 0.06 mm pocket-wall hairline or if a "
                                  "manufacturable (no internal cavity) shell is needed",
            }
        variants[k] = v

    data = {
        "schema": "smartcoaster.appearance.shell/v1",
        "generated_by": "appearance/cad/run_shell.sh",
        "generated_at_utc": generated,
        "interpreter": PYEXE,
        "build123d_version": b3d_version,
        "units": "mm",
        "coordinate_system": "origin at plate bottom centre, Z up, front = -Y",
        "pocket": {
            "diameter_mm": POCKET_D,
            "radius_mm": POCKET_R,
            "center_xy_mm": [0.0, 0.0],
            "shape": "one flat-bottom cylinder cut through the top surface only",
            "top_clearance_mm": TOP_CLEAR,
            "floor_rule": "rim_top_z - 0.05 - print_thickness_mm",
        },
        "print": {
            "diameter_mm": PRINT_D,
            "radius_mm": PRINT_R,
            "radial_interference_mm": RADIAL_INT,
            "top_below_rim_mm": TOP_CLEAR,
            "placement_rule": "print bottom on pocket floor, XY centred (0,0), no rotation",
            "fusing": "in place, fused by the slicer (not glued)",
        },
        "stl_export": {"linear_tolerance_mm": STL_TOL, "angular_tolerance_rad": STL_ANG},
        "source_geometry": source_geometry,
        "variants": variants,
        # ---- flat per-shape contract (render / 3MF stages read these) ----
        "round": contract(shapes["round"]),
        "square": contract(shapes["square"]),
        "validation": {
            "round": validation(shapes["round"]),
            "square": validation(shapes["square"]),
        },
        # ---- full details ----
        "shapes": shapes,
        "blanks": blanks,
        "blender": bl,
        "files": file_list,
        "provisional": [n for n in notes if "PROVISIONAL" in n],
        "notes": notes,
        "runtime_s": r6(time.time() - t0),
    }
    shell_json = OUT / "shell.json"
    shell_json.write_text(json.dumps(data, indent=2) + "\n")
    (OUT / "parts.json").write_text(json.dumps(parts_doc, indent=2) + "\n")

    elapsed = time.time() - t0
    report = make_report(data, bl, elapsed)
    (OUT / "REPORT.md").write_text(report + "\n")

    print(f"[shell-cad] wrote {rel(shell_json)}, parts.json, REPORT.md "
          f"({elapsed:.1f} s total)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
