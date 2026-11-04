#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Headless STEP sanity check for the SmartCoaster square V1 assembly.

Run with:
    freecadcmd /data/Documents/projects/SmartCoaster/mechanical/square_v1/tools/freecad_verify.py

Opens the STEP file read-only (it is never written to) and reports:
  * top-level Shape type
  * number of solids
  * global bounding box -- both the analytical OCCT BoundBox and a
    tessellation-based (true geometric) bbox
  * total volume
  * per-solid volume and bounding box (both flavours)

Why two bounding boxes?
    OCCT computes Shape.BoundBox() from the exact surfaces.  For faces lying
    on a torus it can return a box noticeably larger than the trimmed face
    (the underlying surface patch is bounded instead of the face).  In this
    assembly that inflates X/Y in the round LUMEN assembly.  Tessellating the shape
    and measuring the actual vertices gives the real extent, which is what the
    expectations below use.

NOTE for maintainers: freecadcmd executes a script with __name__ set to the
file's module name (e.g. "verify_step"), not "__main__", so there is no
`if __name__ == "__main__"` guard here.  sys.exit() is avoided too, because an
abrupt exit can drop buffered stdout.
"""

import os
import sys

STEP_FILE = "/data/Documents/projects/SmartCoaster/mechanical/square_v1/build/assembly/assembly_v01.step"

# Expected values from the CAD pipeline (used only for a pass/fail hint).
# 12 parts, no light guide (user decision 2026-11-04).
EXPECT_SOLIDS = 12
EXPECT_BBOX = (100.0, 100.0, 18.0)
EXPECT_VOLUME = 78338.15

TESS_TOL = 0.02  # mm, chord tolerance for the tessellation-based measurement


def load_shape(path):
    """Load a STEP file into a Part.Shape without any GUI."""
    import FreeCAD  # noqa: F401  (initialises the FreeCAD runtime)
    import Part

    if not os.path.isfile(path):
        raise SystemExit("ERROR: STEP file not found: %s" % path)

    shape = Part.Shape()
    shape.read(path)
    if shape.isNull():
        # Fallback: some builds only populate shapes through the Import module.
        import Import

        doc = FreeCAD.newDocument("stepcheck")
        Import.insert(path, doc.Name)
        doc.recompute()
        shapes = [o.Shape for o in doc.Objects
                  if hasattr(o, "Shape") and not o.Shape.isNull()]
        if not shapes:
            raise SystemExit("ERROR: no shapes imported from %s" % path)
        shape = Part.makeCompound(shapes)
    return shape


def mesh_bbox(shp, tol=TESS_TOL):
    """Bounding box of the tessellated shape: (dx, dy, dz, min, max, nverts)."""
    verts, _facets = shp.tessellate(tol)
    if not verts:
        return None
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
            (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)), len(verts))


def main():
    print("=" * 72)
    print("FreeCAD STEP verification (headless)")
    print("=" * 72)

    import FreeCAD
    v = FreeCAD.Version()
    print("FreeCAD version : %s.%s  (rev %s)" % (v[0], v[1], v[2]))
    print("Python          : %s" % sys.version.split()[0])
    print("STEP file       : %s" % STEP_FILE)
    if os.path.isfile(STEP_FILE):
        print("File size       : %d bytes" % os.path.getsize(STEP_FILE))
    print("")

    shape = load_shape(STEP_FILE)
    solids = shape.Solids

    # IMPORTANT: read every analytical BoundBox *before* tessellating anything.
    # Once a shape carries a triangulation, FreeCAD's BoundBox switches to the
    # (tighter) triangulation-based box, which would hide the torus artefact we
    # are documenting here.
    bb = shape.BoundBox
    exact_solid_boxes = [s.BoundBox for s in solids]

    mb = mesh_bbox(shape)
    solid_mesh_boxes = [mesh_bbox(s) for s in solids]

    print("-" * 72)
    print("Shape type      : %s" % shape.ShapeType)
    print("Solids          : %d" % len(solids))
    print("Faces / edges   : %d / %d" % (len(shape.Faces), len(shape.Edges)))
    print("BoundBox (exact, OCCT analytical):")
    print("    XLength=%.3f  YLength=%.3f  ZLength=%.3f" % (bb.XLength, bb.YLength, bb.ZLength))
    print("    min=(%.3f, %.3f, %.3f)  max=(%.3f, %.3f, %.3f)"
          % (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax))
    print("BoundingBox (tessellated, tol=%.2f mm -- true geometry):" % TESS_TOL)
    print("    XLength=%.3f  YLength=%.3f  ZLength=%.3f" % mb[:3])
    print("    min=(%.3f, %.3f, %.3f)  max=(%.3f, %.3f, %.3f)" % (mb[3] + mb[4]))
    print("Volume (whole)  : %.3f mm^3" % shape.Volume)
    print("Volume (sum of solids): %.3f mm^3" % sum(s.Volume for s in solids))
    if abs(shape.Volume - sum(s.Volume for s in solids)) > 1e-3:
        print("  note: whole-shape volume differs from the sum of the solids")
    print("")

    print("-" * 72)
    print("Per-solid detail (bbox: tessellated | OCCT analytical)")
    print("%-3s %13s  %20s  %20s" % ("#", "Volume(mm^3)", "dX x dY x dZ (tess)", "dX x dY x dZ (exact)"))
    for i, solid in enumerate(solids):
        sb = exact_solid_boxes[i]
        smb = solid_mesh_boxes[i]
        print("%-3d %13.3f  %6.2f x %6.2f x %5.2f  %6.2f x %6.2f x %5.2f"
              % (i + 1, solid.Volume, smb[0], smb[1], smb[2],
                 sb.XLength, sb.YLength, sb.ZLength))
    print("-" * 72)
    print("Per-solid Z placement (tessellated):")
    for i, smb in enumerate(solid_mesh_boxes, 1):
        print("  #%-2d  Z %6.2f .. %6.2f" % (i, smb[3][2], smb[4][2]))
    print("")

    # Sanity comparison against the expected assembly figures.
    ok_solids = len(solids) == EXPECT_SOLIDS
    ok_bbox = all(abs(a - b) <= 0.5 for a, b in zip(mb[:3], EXPECT_BBOX))
    vol = shape.Volume
    ok_vol = abs(vol - EXPECT_VOLUME) <= EXPECT_VOLUME * 0.02
    print("Expectation check:")
    print("  solids == %-3d            : %s (got %d)"
          % (EXPECT_SOLIDS, "PASS" if ok_solids else "MISMATCH", len(solids)))
    print("  bbox ~= %.0f x %.0f x %.0f    : %s (got %.2f x %.2f x %.2f)"
          % (EXPECT_BBOX[0], EXPECT_BBOX[1], EXPECT_BBOX[2],
             "PASS" if ok_bbox else "MISMATCH", mb[0], mb[1], mb[2]))
    print("  volume ~= %.0f mm^3   : %s (got %.1f, delta %.1f = %.3f%%)"
          % (EXPECT_VOLUME, "PASS" if ok_vol else "MISMATCH", vol,
             vol - EXPECT_VOLUME, 100.0 * (vol - EXPECT_VOLUME) / EXPECT_VOLUME))
    print("")
    all_ok = ok_solids and ok_bbox and ok_vol
    print("RESULT: %s" % ("OK - STEP loaded, 12 solids, 100 x 100 x 18 mm, 78338 mm^3"
                         if all_ok else "LOADED, but some figures differ (see above)"))
    return 0 if all_ok else 1


main()
try:
    sys.stdout.flush()
except Exception:
    pass
