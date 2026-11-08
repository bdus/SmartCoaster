#!/usr/bin/env python3
"""Import a Lumina-Layers **vector-mode 3MF export** as the print of one version.

The raster line (appearance/lumina/lumina_convert.py) drives Lumina head-less and
derives the print from a PNG.  This importer is the other supported input: a 3MF
that the user exported from the Lumina GUI in *vector* mode (Production-extension
Bambu project, one part per physical filament).  It produces the exact same data
contract so the rest of the pipeline (shell / render / 3MF / print delivery /
acceptance) does not change:

    <three-mf> (Lumina vector export)
        |  read 3D/Objects/*.model, map part names -> RYBW slots
        |  drop the optional transparent "Coating" part (5th spool; H2D budget)
        |  scale XY to the design diameter (non-uniform: the vector art is a
        |  traced ellipse, the shell pocket is a cylinder -> "re-square" it the
        |  same way the raster line re-squares surface.png)
        |  Lumina print pose (colour face z=0, X-mirrored) -> assembly pose
        |  (art face up at z=t, back at z=0)
        v
    appearance/build/print/<art>/filament_<n>_<HEX>.stl + manifest.json
        + matched_rgb.npy / mask_solid.npy  (render-only predicted/design colours)
        + plate_preview.png, provenance.json, source_lumina_vector.3mf

Run (needs the Lumina venv: trimesh + resvg):
  /data/Documents/tools/Lumina-Layers/.venv/bin/python \
      appearance/lumina/import_vector_3mf.py --art elf \
      --three-mf appearance/src/art/tmprarihgxw_Lumina_Vector_4C_20261108_131917.3mf
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
PRINT_ROOT = ROOT / "appearance" / "build" / "print"
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"

# project slots (same order/hexes as appearance/config/lumina_project.yaml)
SLOTS = [
    ("White", "#FFFFFF", ("白玉", "白", "WHITE", "JADE")),
    ("Red", "#DC143C", ("红", "RED")),
    ("Yellow", "#FFE600", ("黄", "YELLOW")),
    ("Blue", "#0064F0", ("蓝", "BLUE")),
]
COATING_KEYS = ("COATING", "涂层", "透明", "CLEAR", "VARNISH")


def rel(p) -> str:
    try:
        return os.path.relpath(str(p), str(ROOT))
    except ValueError:
        return str(p)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(name: str):
    up = (name or "").upper()
    for key in COATING_KEYS:
        if key in up:
            return "Coating"
    for slot, _hex, keys in SLOTS:
        for k in keys:
            if k in up:
                return slot
    return None


def read_3mf_parts2(path: Path):
    """Return [(name, vertices (n,3), faces (m,3))] for every mesh object."""
    z = zipfile.ZipFile(path)
    models = [n for n in z.namelist() if n.startswith("3D/") and n.endswith(".model")]
    parts = []
    for m in models:
        root = ET.fromstring(z.read(m))
        for obj in root.iter(CORE + "object"):
            mesh = obj.find(CORE + "mesh")
            if mesh is None:
                continue
            verts = np.array([[float(v.get("x")), float(v.get("y")), float(v.get("z"))]
                              for v in mesh.findall(f"{CORE}vertices/{CORE}vertex")],
                             dtype=np.float64)
            faces = np.array([[int(t.get("v1")), int(t.get("v2")), int(t.get("v3"))]
                              for t in mesh.findall(f"{CORE}triangles/{CORE}triangle")],
                             dtype=np.int64)
            if len(faces):
                parts.append((obj.get("name") or "", verts, faces))
    return parts


def make_face_texture(svg: Path, size: int, out_png: Path, out_npy: Path,
                      out_mask: Path, warnings: list):
    """Rasterise the *vector source* SVG and write the render-only face maps.

    This is the artwork as designed (vectorizer output), NOT a physical colour
    prediction: the vector branch gives no optical-mix prediction, so the render
    overlay simply shows the design.  Recorded as such in the manifest.
    """
    import resvg_py
    from PIL import Image

    big = size * 2
    png = resvg_py.svg_to_bytes(svg_path=str(svg), width=big, height=big)
    img = Image.open(io.BytesIO(bytes(png))).convert("RGBA")
    a = np.array(img)
    alpha = a[..., 3]
    op = alpha > 16
    if not op.any():
        warnings.append("face texture: SVG rendered empty")
        return None
    ys, xs = np.where(op)
    crop = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray(crop, "RGBA").resize((size, size), Image.LANCZOS)
    arr = np.array(im)
    rgb = arr[..., :3].copy()
    mask = arr[..., 3] > 16
    # fill the transparent margin with the nearest inside colour (bleed) so the
    # render overlay never samples undefined texels
    known = mask.copy()
    out = rgb.astype(np.float32)
    for _ in range(8):
        pad = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
        padk = np.pad(known, ((1, 1), (1, 1)), mode="edge")
        h, w = mask.shape
        acc = np.zeros_like(out)
        cnt = np.zeros((h, w), dtype=np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                acc += pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] * \
                    padk[1 + dy:1 + dy + h, 1 + dx:1 + dx + w][..., None]
                cnt += padk[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        grow = (~known) & (cnt > 0)
        out[grow] = acc[grow] / cnt[grow][:, None]
        known = known | grow
    out = np.clip(out, 0, 255).astype(np.uint8)
    np.save(out_npy, out)
    np.save(out_mask, mask)
    im.save(out_png)
    return crop.shape


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--art", default="elf")
    ap.add_argument("--three-mf", required=True)
    ap.add_argument("--out-root", default=str(PRINT_ROOT))
    ap.add_argument("--target-diameter-mm", type=float, default=86.2)
    ap.add_argument("--keep-coating", action="store_true",
                    help="keep the transparent 'Coating' part (needs a 5th spool)")
    ap.add_argument("--face-texture", default="appearance/src/vectorized.svg")
    ap.add_argument("--face-size", type=int, default=864)
    args = ap.parse_args(argv)

    src = Path(args.three_mf)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        raise SystemExit("3MF not found: %s" % src)
    out_dir = Path(args.out_root) / args.art
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings = []

    parts = read_3mf_parts2(src)
    if not parts:
        raise SystemExit("no mesh objects in %s" % src)

    by_slot: dict[str, list] = {}
    coatings = []
    for name, verts, faces in parts:
        slot = classify(name)
        if slot is None:
            raise SystemExit("cannot classify 3MF part %r to a RYBW slot" % name)
        if slot == "Coating":
            coatings.append((name, verts, faces))
            continue
        by_slot.setdefault(slot, []).append((name, verts, faces))
    if not args.keep_coating:
        for name, verts, faces in coatings:
            m = trimesh.Trimesh(verts, faces, process=False)
            print("[vector-3mf] dropping part %-12s (%8.1f mm3, 0.08 mm transparent layer)"
                  % (name, m.volume))
    else:
        by_slot.setdefault("Coating", []).extend(coatings)
    if sorted(by_slot) != ["Blue", "Red", "White", "Yellow"] and not args.keep_coating:
        raise SystemExit("expected exactly White/Red/Yellow/Blue, got %s" % sorted(by_slot))

    # union bbox (drop coating already applied to by_slot)
    all_v = np.concatenate([v for lst in by_slot.values() for _n, v, _f in lst], axis=0)
    lo, hi = all_v.min(0), all_v.max(0)
    t = float(hi[2] - lo[2])
    print("[vector-3mf] source bbox x %.3f..%.3f (%.3f) y %.3f..%.3f (%.3f) z %.3f..%.3f (%.4f)"
          % (lo[0], hi[0], hi[0] - lo[0], lo[1], hi[1], hi[1] - lo[1], lo[2], hi[2], t))

    # "re-square" the traced ellipse to the circular design diameter
    D = float(args.target_diameter_mm)
    sx = D / float(hi[0] - lo[0])
    sy = D / float(hi[1] - lo[1])
    cx = (lo[0] + hi[0]) / 2.0
    cy = (lo[1] + hi[1]) / 2.0
    print("[vector-3mf] scale_xy = %.5f x %.5f  (%.2f x %.2f mm -> Ø%.2f)" %
          (sx, sy, hi[0] - lo[0], hi[1] - lo[1], D))

    def to_assembly(v):
        x = (v[:, 0] - cx) * sx
        y = (v[:, 1] - cy) * sy
        z = v[:, 2] - lo[2]
        # print pose (art face z=0, X-mirrored) -> assembly pose (art face up):
        # rotate 180 deg about Y: x -> -x, z -> t - z
        return np.stack([-x, y, t - z], axis=1)

    entries = []
    all_pts = []
    for idx, (slot, hexv, _keys) in enumerate(SLOTS, start=1):
        lst = by_slot.get(slot)
        if not lst:
            raise SystemExit("slot %s missing from the 3MF" % slot)
        meshes = []
        for name, verts, faces in lst:
            m = trimesh.Trimesh(vertices=to_assembly(verts), faces=faces, process=False)
            meshes.append(m)
        mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        fname = "filament_%d_%s.stl" % (idx, hexv.lstrip("#"))
        mesh.export(str(out_dir / fname))
        all_pts.append(np.asarray(mesh.vertices))
        entries.append({
            "number": idx,
            "slot": slot,
            "hex": hexv,
            "file": fname,
            "triangles": int(len(mesh.faces)),
            "volume_mm3": round(float(abs(mesh.volume)), 3),
            "sha256": sha256_file(out_dir / fname),
            "parts": len(lst),
            "watertight": bool(mesh.is_watertight),
            "min_z_mm": round(float(np.asarray(mesh.vertices)[:, 2].min()), 4),
        })
        print("[vector-3mf] %-6s -> %-34s tris %6d  vol %9.2f mm3  watertight=%s"
              % (slot, fname, len(mesh.faces), abs(mesh.volume), mesh.is_watertight))

    verts = np.concatenate(all_pts, axis=0)
    lo2, hi2 = verts.min(0), verts.max(0)
    thickness = float(hi2[2] - lo2[2])
    dia = float(max(hi2[0] - lo2[0], hi2[1] - lo2[1]))
    print("[vector-3mf] assembled bbox %s .. %s  t=%.4f  dia=%.3f"
          % (np.round(lo2, 3).tolist(), np.round(hi2, 3).tolist(), thickness, dia))

    # ---- render-only face maps (design colours of the vector art) ---------- #
    tex_svg = ROOT / args.face_texture if not Path(args.face_texture).is_absolute() \
        else Path(args.face_texture)
    mat_npy = out_dir / "matched_rgb.npy"
    mask_npy = out_dir / "mask_solid.npy"
    prev_png = out_dir / "plate_preview.png"
    tex_shape = None
    if tex_svg.exists():
        try:
            tex_shape = make_face_texture(tex_svg, args.face_size, prev_png, mat_npy, mask_npy,
                                          warnings)
        except Exception as exc:                      # pragma: no cover
            warnings.append("face texture build failed: %s" % exc)
    else:
        warnings.append("face texture SVG not found: %s" % tex_svg)

    # ---- native 3MF kept for provenance ------------------------------------ #
    nat = out_dir / "source_lumina_vector.3mf"
    shutil.copy2(src, nat)

    src_doc = {}
    try:
        inner = zipfile.ZipFile(io.BytesIO(
            zipfile.ZipFile(src).read("Metadata/Lumina/project.lum")))
        conv = json.loads(inner.read("documents/converter.main.json"))
        src_doc = conv.get("payload", {})
    except Exception:
        pass
    recipe = (src_doc.get("recipe") or {}).get("base") or {}
    geom = (src_doc.get("recipe") or {}).get("geometry") or {}
    coating = (src_doc.get("recipe") or {}).get("coating") or {}

    manifest = {
        "schema": "smartcoaster.appearance.print_lumina/v1",
        "engine": {
            "name": "Lumina-Layers (Lumina Studio 2.0) — vector 3MF import",
            "root": "/data/Documents/tools/Lumina-Layers",
            "license": "AGPL-3.0-only (output imported, tool not modified)",
            "entry": "GUI export (vector mode) imported by appearance/lumina/import_vector_3mf.py",
            "python": sys.version.split()[0],
        },
        "art": {
            "name": args.art,
            "source_svg": rel(tex_svg) if tex_svg.exists() else None,
            "source_svg_sha256": sha256_file(tex_svg) if tex_svg.exists() else None,
            "target_width_mm": D,
            "note": "vector art traced from appearance/src/ai_elf_noedge.svg",
        },
        "params": {
            "structure_mode": "Single-sided",
            "modeling_mode": "vector (Lumina export)",
            "color_mode": "4-Color (RYBW)",
            "lut": "lut-preset/Custom/lumina_lut.json",
            "color_layers": int(recipe.get("color_layers") or 5),
            "layer_height_mm": 0.08,
            "spacer_thick_mm": float(geom.get("spacer_thick") or 1.2),
            "total_layers": None,
            "base_color_gap_mm": 0.005,
            "quantize_colors": recipe.get("quantize_colors"),
            "printer_id": ((src_doc.get("recipe") or {}).get("device") or {}).get(
                "printer_id", "bambu-h2d"),
            "device_profile_id": ((src_doc.get("recipe") or {}).get("device") or {}).get(
                "device_profile_id", "BambuStudio:bbl:bambu-lab-h2d:0.4"),
            "nozzle_size_mm": 0.4,
            "backing_color": "Jade White (slot White)",
            "backing_infill_density_percent": 100,
            "coating": "removed (0.08 mm transparent layer; would need a 5th spool)"
                       if not args.keep_coating else "kept",
            "coating_height_mm": float(coating.get("coating_height_mm") or 0.08),
        },
        "geometry": {
            "orientation": "assembly pose: art face up (+Z), flat back at z=0",
            "assembly_transform": "print pose -> assembly: scale XY to Ø%.2f, centre XY, "
                                  "rotate 180 deg about Y (x -> -x, z -> t - z)" % D,
            "assembly_sign": [-1.0, 1.0, -1.0],
            "orientation_volume_centroid_rms_mm": None,
            "orientation_margin": None,
            "orientation_method": "imported 3MF: Lumina applies the same X mirror to the "
                                  "vector export as to the raster path; verified visually "
                                  "against the source art",
            "thickness_mm": round(thickness, 6),
            "print_thickness_mm": round(thickness, 6),
            "total_thickness_mm": round(thickness, 6),
            "diameter_mm": round(dia, 4),
            "bbox_mm": {"min": [round(float(v), 4) for v in lo2],
                        "max": [round(float(v), 4) for v in hi2],
                        "size": [round(float(hi2[i] - lo2[i]), 4) for i in range(3)]},
            "image_top_axis": "+Y",
        },
        "palette": [hexv for _s, hexv, _k in SLOTS],
        "palette_bottom_up": [hexv for _s, hexv, _k in SLOTS],
        "slot_names": [s for s, _h, _k in SLOTS],
        "slot_volume_mm3": {e["slot"]: e["volume_mm3"] for e in entries},
        "slot_pixel_counts": {e["slot"]: max(1, int(round(e["volume_mm3"])))
                              for e in entries},   # volume proxy for the sheet shares
        "filament_objects": entries,
        "filaments": entries,
        "parts": entries,
        "artifacts": {
            "threemf": {"file": nat.name, "bytes": nat.stat().st_size,
                        "sha256": sha256_file(nat)},
            "face_texture": {"file": prev_png.name if prev_png.exists() else None,
                             "source": "vectorized.svg (design colours, render-only)"},
        },
        "lumina_transform_metadata": {},
        "runtime_s": None,
        "progress": [],
        "provenance": {
            "source_3mf": {"path": rel(src), "sha256": sha256_file(src),
                           "bytes": src.stat().st_size},
            "scale_xy": [round(sx, 6), round(sy, 6)],
            "source_bbox_mm": {"min": [round(float(v), 4) for v in lo],
                               "max": [round(float(v), 4) for v in hi]},
            "dropped_parts": [n for n, _v, _f in coatings] if not args.keep_coating else [],
            "lumina_recipe": {k: recipe.get(k) for k in
                              ("modeling_mode", "color_mode", "target_width_mm",
                               "target_height_mm", "quantize_colors")},
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "appearance/lumina/import_vector_3mf.py",
        },
        "validation": {
            "thickness_ok": abs(thickness - t) < 1e-3,
            "diameter_ok": abs(dia - D) < 0.2,
            "slots_ok": True,
            "watertight": {e["file"]: e["watertight"] for e in entries},
            "all_watertight": all(e["watertight"] for e in entries),
            "volume_mm3": round(sum(e["volume_mm3"] for e in entries), 3),
        },
        "warnings": warnings,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "provenance.json").write_text(
        json.dumps(manifest["provenance"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print("[vector-3mf] %-4s -> %s" % (args.art, rel(out_dir)))
    print("[vector-3mf]   thickness %.3f mm  diameter %.2f mm  slots %d  tris %d  "
          "watertight %s  volume %.1f mm3"
          % (thickness, dia, len(entries), sum(e["triangles"] for e in entries),
             manifest["validation"]["all_watertight"],
             manifest["validation"]["volume_mm3"]))
    for w in warnings:
        print("[vector-3mf] WARNING", w)
    if not manifest["validation"]["all_watertight"]:
        raise SystemExit("some filament meshes are not watertight")
    return 0


if __name__ == "__main__":
    sys.exit(main())
