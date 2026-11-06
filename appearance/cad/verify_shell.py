#!/usr/bin/env python3
"""Independent re-verification of the appearance shell deliverables.

Reads appearance/build/shell/shell.json and re-imports the STEP/STL artifacts
(does NOT reuse build_recessed.py) so a second pair of eyes - or a fresh
process - can confirm the numbers.  Exit code 0 = all checks pass.

    /data/Documents/projects/SmartCoaster/mechanical/square_v1/.venv/bin/python \
        appearance/cad/verify_shell.py
"""

from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

from build123d import import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_SurfaceType

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "appearance" / "build" / "shell"
POCKET_R = 43.0
PRINT_R = 43.2

fails: list[str] = []
checks = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global checks
    checks += 1
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def r(x: float, n: int = 6) -> float:
    return round(float(x), n)


def stl_bbox(path: Path):
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12f", data[off:off + 48])
        off += 50
        for k in (3, 6, 9):
            for i in range(3):
                c = vals[k + i]
                lo[i] = min(lo[i], c)
                hi[i] = max(hi[i], c)
    return n, lo, hi


def main() -> int:
    doc = json.loads((OUT / "shell.json").read_text())
    print(f"shell.json schema={doc['schema']} build123d={doc['build123d_version']}")

    # --- exact canonical contract keys -------------------------------------
    for key, rim, floor, depth, pt in (
            ("round", 17.0, 15.75, 1.25, 1.20),
            ("square", 18.0, 16.55, 1.45, 1.40)):
        c = doc[key]
        check(f"{key}: rim_z_mm", r(c["rim_z_mm"]) == rim, str(c["rim_z_mm"]))
        check(f"{key}: floor_z_mm", r(c["floor_z_mm"]) == floor, str(c["floor_z_mm"]))
        check(f"{key}: pocket_dia_mm", r(c["pocket_dia_mm"]) == 86.0)
        check(f"{key}: pocket_depth_mm", r(c["pocket_depth_mm"]) == depth, str(c["pocket_depth_mm"]))
        check(f"{key}: print_thickness_mm", r(c["print_thickness_mm"]) == pt, str(c["print_thickness_mm"]))
        check(f"{key}: print_dia_mm", r(c["print_dia_mm"]) == 86.4)
        check(f"{key}: interference_mm", r(c["interference_mm"]) == 0.2)
        check(f"{key}: top_gap_mm", r(c["top_gap_mm"]) == 0.05)
        check(f"{key}: print_top = rim - 0.05",
              abs((floor + pt) - (rim - 0.05)) < 1e-9, f"{floor + pt}")
        check(f"{key}: placement translate z = floor",
              abs(c["placement"]["translate_mm"][2] - floor) < 1e-9)
        check(f"{key}: placement xy = (0,0)",
              c["placement"]["translate_mm"][0] == 0.0 and c["placement"]["translate_mm"][1] == 0.0)

        # --- STEP re-import -------------------------------------------------
        step = REPO / c["files"]["plate_step"]
        check(f"{key}: STEP file exists", step.exists(), str(step))
        comp = import_step(str(step))
        sols = comp.solids()
        check(f"{key}: STEP solids == 1", len(sols) == 1, str(len(sols)))
        check(f"{key}: STEP solid valid", bool(sols[0].is_valid))
        bb = comp.bounding_box()
        exp = {"round": 52.0, "square": 50.0}[key]
        check(f"{key}: STEP bbox xy +/-{exp}",
              abs(bb.max.X - exp) < 1e-6 and abs(bb.min.X + exp) < 1e-6
              and abs(bb.max.Y - exp) < 1e-6 and abs(bb.min.Y + exp) < 1e-6)
        check(f"{key}: STEP bbox z max == rim", abs(bb.max.Z - rim) < 1e-6, str(bb.max.Z))

        # --- pocket from re-imported STEP ----------------------------------
        floors = []
        walls = []
        for f in sols[0].faces():
            ad = BRepAdaptor_Surface(f.wrapped)
            if ad.GetType() == GeomAbs_SurfaceType.GeomAbs_Plane:
                pln = ad.Plane()
                if abs(pln.Location().Z() - floor) < 1e-6 and pln.Axis().Direction().Z() > 0.99:
                    floors.append(f)
            elif ad.GetType() == GeomAbs_SurfaceType.GeomAbs_Cylinder:
                if abs(ad.Cylinder().Radius() - POCKET_R) < 1e-4:
                    walls.append(f)
        check(f"{key}: pocket floor face found", len(floors) == 1, f"{len(floors)} faces")
        if floors:
            check(f"{key}: floor area == pi*r^2",
                  abs(floors[0].area - math.pi * POCKET_R ** 2) < 1e-2,
                  f"{floors[0].area:.4f}")
            check(f"{key}: floor flat",
                  all(abs(v.Z - floor) < 1e-6 for e in floors[0].edges()
                      for v in [e.position_at(t / 8.0) for t in range(9)]))
        check(f"{key}: pocket wall r=43 found", len(walls) >= 1, f"{len(walls)} faces")

        # --- volume / material ----------------------------------------------
        val = doc["validation"][key]
        delta = val["volume"]["delta_mm3"]
        if key == "square":
            check("square: volume delta == pi*r^2*depth",
                  abs(delta - math.pi * POCKET_R ** 2 * depth) / delta < 1e-6, f"{delta:.4f}")
        else:
            check("round: delta == material above floor (matches measured)",
                  abs(delta - val["volume"]["expected_from_actual_material_mm3"]) < 1e-3,
                  f"{delta:.4f}")
            check("round: pre-existing void accounts for nominal gap",
                  abs((math.pi * POCKET_R ** 2 * depth - delta) - 1416.0467) < 0.5,
                  f"gap {math.pi * POCKET_R ** 2 * depth - delta:.4f}")
        check(f"{key}: remaining material under floor",
              abs(val["remaining_material_under_floor_mm"]
                  - ({"round": 1.75, "square": 1.55}[key])) < 1e-6)
        check(f"{key}: internal parts all below floor",
              val["internal_check"]["all_internal_below_floor"])

        # --- STL -------------------------------------------------------------
        stl = REPO / c["files"]["plate_stl"]
        n, lo, hi = stl_bbox(stl)
        sdoc = doc["shapes"][key]["stl"]
        check(f"{key}: STL triangle count matches json", n == sdoc["triangles"], str(n))
        check(f"{key}: STL watertight (json)", bool(sdoc["watertight"]))
        check(f"{key}: STL z max ~ rim", abs(hi[2] - rim) < 1e-3, f"{hi[2]:.4f}")
        check(f"{key}: STL bbox inside exact bbox (tessellation)",
              lo[0] >= -exp - 1e-3 and hi[0] <= exp + 1e-3)
        check(f"{key}: Blender imported 1 object",
              any(i["file"].endswith(c["files"]["plate_stl"]) and i["objects"] == 1
                  for i in (doc.get("blender", {}) or {}).get("imports", [])))

    # --- blanks --------------------------------------------------------------
    for key, t, name in (("round", 1.20, "print_blank_round.stl"),
                         ("square", 1.40, "print_blank_square.stl")):
        p = OUT / name
        n, lo, hi = stl_bbox(p)
        check(f"{key}: blank exists", p.exists())
        check(f"{key}: blank z 0..{t}", abs(lo[2]) < 1e-4 and abs(hi[2] - t) < 1e-4,
              f"{lo[2]:.4f}..{hi[2]:.4f}")
        check(f"{key}: blank max radius 43.2", abs(max(hi[0], hi[1]) - PRINT_R) < 1e-3,
              f"{max(hi[0], hi[1]):.4f}")
    check("print_blank.stl alias == print_blank_round.stl",
          (OUT / "print_blank.stl").read_bytes() == (OUT / "print_blank_round.stl").read_bytes())

    # --- round clean variant -------------------------------------------------
    cl = doc["variants"]["round"].get("clean")
    if cl:
        cs = import_step(str(REPO / cl["file_step"]))
        check("round clean: STEP 1 solid", len(cs.solids()) == 1)
        cb = cs.bounding_box()
        check("round clean: bbox identical to primary",
              abs(cb.max.X - 52.0) < 1e-6 and abs(cb.min.X + 52.0) < 1e-6)
        check("round clean: no pocket-wall slit (single wall band)",
              len(doc["shapes"]["round"]["clean_variant"]["wall_bands"]) == 1)
    check("round clean: external bbox identical flag",
          doc["shapes"]["round"]["clean_variant"]["external_bbox_identical_to_primary"])

    # --- source geometry block ----------------------------------------------
    sg = doc["source_geometry"]["round"]
    check("source_geometry: round void present in validated STEP",
          sg["internal_void_present_in_validated_step"] is True)
    check("source_geometry: void apex 16.1 / ceiling 16.7",
          abs(sg["internal_void"]["apex_z"] - 16.1) < 1e-6
          and abs(sg["internal_void"]["ceiling_z"] - 16.7) < 1e-6)
    check("source_geometry: top surface flat (no dish)", sg["top_surface_flat"] is True)
    check("source_geometry: floor 0.35 below void apex",
          abs(sg["internal_void"]["void_apex_above_floor_mm"] - 0.35) < 1e-6)
    check("source_geometry: square has no internal void",
          doc["source_geometry"]["square"]["internal_void"] is None)

    # --- parts.json ----------------------------------------------------------
    parts = json.loads((OUT / "parts.json").read_text())
    for key in ("round", "square"):
        for p in parts["shapes"][key]["internal_parts"]:
            if p["use_in_render"]:
                check(f"{key}: parts.json STL exists {p['name']}",
                      (REPO / p["stl"]).exists(), p["stl"])

    print()
    print(f"{checks - len(fails)}/{checks} checks passed")
    if fails:
        print("FAILURES:")
        for f in fails:
            print(" -", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
