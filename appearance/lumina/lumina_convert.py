#!/usr/bin/env python3
"""Headless Lumina-Layers conversion: print image -> multi-material flat print.

Replaces the Kromacut Flat Paint bridge (appearance/kromacut/).  Runs the real
Lumina Studio 2.0 pipeline in-process (no FastAPI session, no Electron, no GUI
automation -- docs/01 section 14.4), then re-exports the result in the data
contract the rest of the SmartCoaster pipeline already consumes:

    appearance/build/art/<art>/art_rgba.png        (make_art_lumina.py)
        |
        |  Lumina core.converter.build_image_model_context()
        |    S01..S12: LUT match -> voxel build -> per-filament meshing -> 3MF
        v
    appearance/build/print/<art>/
        filament_<n>_<HEX>.stl     one closed solid per physical filament, ASSEMBLY pose
        manifest.json              same schema as before + full Lumina provenance
        plate_lumina.3mf           Lumina's native 3MF (Bambu project metadata, AMS materials)
        plate_preview.png          Lumina's 2-D colour preview (reference)
        material_matrix.npy        (H,W,5) int32 slot id per voxel column (-1 = air)
        matched_rgb.npy            (H,W,3) predicted printed colour
        lumina_call.json           every argument actually passed + versions

Geometry contract (see appearance/lumina/README.md):
  * Lumina single-sided = colour face at z=0, backing above, X-mirrored on
    export (core/pipeline/s09_export_3mf.py).  The print is therefore delivered
    ART FACE DOWN (= first layer on the bed) -- exactly the print orientation
    we want.
  * This driver converts it back to the ASSEMBLY pose used by the rest of the
    pipeline: art face UP at z = thickness, flat back at z = 0, XY centred,
    image TOP = +Y.  The chosen mirror is detected and asserted against the
    source image, never assumed silently.
  * thickness = (color_layers + round(spacer_thick / 0.08)) * 0.08 mm.

Run (must use the Lumina venv: lumina-svg-core/neroued-3mf are cp312 wheels):
  /data/Documents/tools/Lumina-Layers/.venv/bin/python \
      appearance/lumina/lumina_convert.py --art dog
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LUMINA = Path(os.environ.get("LUMINA_ROOT", "/data/Documents/tools/Lumina-Layers"))
ART_ROOT = ROOT / "appearance" / "build" / "art"
PRINT_ROOT = ROOT / "appearance" / "build" / "print"

# --------------------------------------------------------------------------- #
# version / parameter contract (one place; compile + acceptance read this)
# --------------------------------------------------------------------------- #
PARAMS = {
    "dog": {
        "label": "round LUMEN x dog",
        "target_width_mm": 86.4,
        "spacer_thick_mm": 0.80,
        "color_layers": 5,
        "lut": "lut-preset/Custom/lumina_lut.json",
        "color_mode": "4-Color (RYBW)",
        "quantize_colors": 48,
        "smooth_sigma": 10,
        "blur_kernel": 0,
        "notes": "user spools: Bambu PLA Basic red/yellow/blue/white (RYBW) + black shell; "
                 "self-describing Keyed-JSON LUT (palette hexes included)",
    },
    "elf": {
        "label": "square square_v1 x elf",
        "target_width_mm": 86.4,
        "spacer_thick_mm": 0.80,
        "color_layers": 5,
        "lut": "lut-preset/Custom/lumina_lut.json",
        "color_mode": "4-Color (RYBW)",
        "quantize_colors": 48,
        "smooth_sigma": 10,
        "blur_kernel": 0,
        "notes": "low-contrast lavender illustration; the same 4 RYBW spools (no cyan/magenta)",
    },
}

LAYER_MM = 0.08            # Lumina PrinterConfig.LAYER_HEIGHT (fixed in geometry)
PIXEL_MM = 0.10            # Lumina HIGH_FIDELITY raster grid
PRINTER_ID = "bambu-h2d"
DEVICE_PROFILE_ID = "BambuStudio:bbl:bambu-lab-h2d:0.4"
NOZZLE = "0.4"

# Colour previews for the 4 slots (Lumina config.ColorSystem.CMYW.preview, sRGB).
# The .npy LUT carries no filament hex, so the 3MF/slot names come from Lumina
# metadata and these are the reported/rendered filament colours.
SLOT_HEX = {
    # Lumina config.ColorSystem preview colours == the hexes inside the
    # self-describing lut-preset/Custom/lumina_lut.json (RYBW, the shipped set)
    "White": "#FFFFFF",
    "Red": "#DC143C",
    "Yellow": "#FFE600",
    "Blue": "#0064F0",
    # kept for reference / other LUTs
    "Cyan": "#0086D6",
    "Magenta": "#EC008C",
}

# numba @njit(cache=True) needs a writable locator next to the module; the Lumina
# checkout is read-only for this project, so point numba's cache at the workspace.
_NUMBA_CACHE = ROOT / ".lumina_runtime" / "numba_cache"
_NUMBA_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NUMBA_CACHE_DIR", str(_NUMBA_CACHE))

OFFLINE_ENV = {
    "LUMINA_MATERIAL_REGISTRY_URL": "",
    "LUMINA_LUT_REGISTRY_URL": "",
    "LUMINA_FEEDBACK_SERVER_URL": "off",
    "LUMINA_MATERIAL_SYNC_STARTUP_REFRESH": "false",
    "LUMINA_MATERIAL_SYNC_REFRESH_INTERVAL_S": "0",
    "LUMINA_BACKEND": "memory",
    "LUMINA_TELEMETRY": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
}


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


# --------------------------------------------------------------------------- #
# import Lumina
# --------------------------------------------------------------------------- #
def import_lumina():
    if not (LUMINA / "core" / "converter.py").exists():
        raise SystemExit("Lumina-Layers not found at %s (install it first)" % LUMINA)
    for k, v in OFFLINE_ENV.items():
        os.environ.setdefault(k, v)
    sys.path.insert(0, str(LUMINA))
    import config as lc  # noqa: F401  (creates output/ dirs; must be writable/symlinked)
    from config import ModelingMode
    from core.converter import build_image_model_context
    return lc, ModelingMode, build_image_model_context


# --------------------------------------------------------------------------- #
# assembly-pose conversion
# --------------------------------------------------------------------------- #
# Lumina exports the colour face at z=0 and mirrors X (core/pipeline/s09:404-417).
# Assembly pose (what the shell/render/3MF side expects) is the same part with
# the art face UP: rotate 180 deg about Y  ->  (x,y,z) -> (-x, y, t-z).
# Detection: we project the view-face vertices back onto the image grid for both
# candidate in-plane mirrors and keep the one that matches the source alpha mask.
CANDIDATES = {
    "flip_x": (np.array([-1.0, 1.0, -1.0]), "rotate 180 deg about Y (invert X and Z)"),
    "flip_y": (np.array([1.0, -1.0, -1.0]), "rotate 180 deg about X (invert Y and Z)"),
}


def to_assembly(tris: np.ndarray, sign: np.ndarray, thickness: float) -> np.ndarray:
    """print pose -> assembly pose (art face up)."""
    out = tris * sign  # rows are vertices
    out[:, :, 2] += thickness
    return out


def tris_centroid_xy(tris: np.ndarray) -> np.ndarray:
    v = tris.reshape(-1, 3)
    return v[:, :2].mean(axis=0)


def mesh_slot_centroid(meshes):
    """Area-weighted XY centroid of a filament solid (surface centroid ~ volume
    centroid in XY: the top/bottom faces are identical, the side walls cancel).

    Using ALL triangles (not just the art face) is deliberate: with a 4-filament
    palette the *viewing surface* of a pale artwork can be 100% White (white top
    layer over coloured under-layers), so an art-face-only signal is degenerate.
    """
    tot = 0.0
    acc = np.zeros(2)
    for m in meshes:
        tris = np.asarray(m.triangles, dtype=np.float64)
        if not len(tris):
            continue
        e1 = tris[:, 1] - tris[:, 0]
        e2 = tris[:, 2] - tris[:, 0]
        area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
        cent = tris.mean(axis=1)
        tot += float(area.sum())
        acc += (cent[:, :2] * area[:, None]).sum(axis=0)
    if tot <= 0:
        return None, 0.0
    return acc / tot, tot


def image_slot_centroids(material_matrix, width_mm, height_mm,
                         backing_layers=10, backing_slot=0):
    """Thickness-weighted XY centroid of each slot, including the backing.

    weight(s, x, y) = number of colour layers of slot s above this pixel, plus
    `backing_layers` for the backing slot.  That weight is proportional to the
    solid volume of slot s at that pixel, i.e. the same statistic we measure on
    the exported per-filament meshes.
    """
    h, w = material_matrix.shape[:2]
    view = material_matrix[..., 0]
    ys, xs = np.mgrid[0:h, 0:w]
    X = (xs + 0.5) * width_mm / w - width_mm / 2.0
    Y = -(ys + 0.5) * height_mm / h + height_mm / 2.0
    solid = view >= 0
    out = {}
    for s in sorted(set(int(v) for v in np.unique(material_matrix))):
        if s < 0:
            continue
        wts = (material_matrix == s).sum(axis=2).astype(np.float64)
        if s == backing_slot:
            wts = wts + solid.astype(np.float64) * float(backing_layers)
        tot = float(wts.sum())
        if tot < 1.0:
            continue
        out[s] = (float((X * wts).sum() / tot), float((Y * wts).sum() / tot), tot)
    return out


def detect_orientation(slot_meshes, slot_names, material_matrix, width_mm,
                       height_mm, backing_layers=10):
    """Pick the in-plane mirror that puts the art in ASSEMBLY pose.

    Lumina exports the part face-down (colour face at z=0).  Going back to the
    assembly pose is a 180 deg rotation about an in-plane axis; which axis is
    decided here by matching per-slot volume-weighted centroids against the
    source image (image TOP = +Y).  Slots are weighted by their volume share, and
    the white/backing slot is down-weighted because it covers the whole disc and
    carries almost no orientation information.
    """
    img = image_slot_centroids(material_matrix, width_mm, height_mm,
                               backing_layers=backing_layers)
    mesh = {}
    for idx, sname in enumerate(slot_names):
        c, area = mesh_slot_centroid(slot_meshes.get(sname, []))
        if c is not None and area > 1.0:
            mesh[idx] = (c[0], c[1], area)
    common = sorted(set(img) & set(mesh))
    if len(common) < 1:
        raise SystemExit("orientation detection needs a common colour slot "
                         "(image %s, mesh %s)" % (sorted(img), sorted(mesh)))
    tot_img = sum(img[s][2] for s in common)
    weights = {}
    for s in common:
        share = img[s][2] / tot_img
        weights[s] = 0.05 if share > 0.80 else max(share, 0.02)
    scores = {}
    for key, (sign, _desc) in CANDIDATES.items():
        err = 0.0
        wsum = 0.0
        for s in common:
            ix, iy, _n = img[s]
            mx, my, _a = mesh[s]
            dx = sign[0] * mx - ix
            dy = sign[1] * my - iy
            err += weights[s] * (dx * dx + dy * dy)
            wsum += weights[s]
        scores[key] = (err / wsum) ** 0.5
        print("[lumina] orientation %-6s volume-centroid rms %.3f mm" % (key, scores[key]))
    best = min(scores, key=scores.get)
    for s in common:
        ix, iy, n = img[s]
        mx, my = mesh[s][:2]
        sg = CANDIDATES[best][0]
        print("[lumina]   slot %-8s img(%7.2f,%7.2f) mesh(%7.2f,%7.2f) -> pred(%7.2f,%7.2f) "
              "err %.2f mm  vol-share %.1f%%"
              % (slot_names[s] if s < len(slot_names) else s, ix, iy, mx, my,
                 sg[0] * mx, sg[1] * my,
                 np.hypot(sg[0] * mx - ix, sg[1] * my - iy), 100.0 * weights[s]))
    second = min((v for k, v in scores.items() if k != best), default=None)
    margin = (second / scores[best]) if (second and scores[best] > 1e-9) else float("inf")
    print("[lumina] orientation margin: best %.3f mm vs runner-up %.3f mm = %.1fx"
          % (scores[best], second if second is not None else -1, margin))
    # Two independent gates: (a) the winning pose must be a sane fit in absolute
    # terms, (b) it must be clearly better than the other mirror.  The absolute
    # value is only a sanity bound (the white/backing volume centroid is a coarse
    # statistic), the discrimination is what actually identifies the pose.
    if scores[best] > 3.0 or margin < 2.5:
        raise SystemExit("could not establish assembly orientation (best %s rms %.2f mm, "
                         "margin %.1fx; need <=3.0 mm and >=2.5x)"
                         % (best, scores[best], margin))
    return best, scores[best], margin


# --------------------------------------------------------------------------- #
# main conversion
# --------------------------------------------------------------------------- #
def convert(art: str, out_dir: Path, args) -> dict:
    p = dict(PARAMS[art])
    if args.spacer is not None:
        p["spacer_thick_mm"] = args.spacer
    if args.lut:
        p["lut"] = args.lut
    if args.color_mode:
        p["color_mode"] = args.color_mode
    if args.quantize is not None:
        p["quantize_colors"] = args.quantize

    png = ART_ROOT / art / "art_rgba.png"
    if not png.exists():
        raise SystemExit("missing %s -- run appearance/tools/make_art_lumina.py first" % rel(png))
    lut = LUMINA / p["lut"]
    if not lut.exists():
        raise SystemExit("missing LUT %s" % lut)

    # pixel grid Lumina will rasterise to (must equal our input, else it resamples)
    target_w = int(round(p["target_width_mm"] * 10))
    with_image = None
    from PIL import Image
    with Image.open(png) as im:
        with_image = im.size
    if with_image[0] != target_w or with_image[1] != target_w:
        raise SystemExit("art PNG is %dx%d but target_width_mm=%.2f needs %dx%d; "
                         "re-run make_art_lumina.py so Lumina does not resample"
                         % (with_image[0], with_image[1], p["target_width_mm"],
                            target_w, target_w))

    lc, ModelingMode, build_ctx = import_lumina()
    transform_meta: dict = {}
    logs: list = []

    def progress(value, desc=""):
        try:
            logs.append({"t": round(time.time(), 3), "value": round(float(value), 4),
                         "desc": str(desc)})
        except Exception:
            pass

    kwargs = dict(
        image_path=str(png),
        lut_path=str(lut),
        target_width_mm=float(p["target_width_mm"]),
        spacer_thick=float(p["spacer_thick_mm"]),
        structure_mode="Single-sided",
        color_mode=p["color_mode"],
        add_loop=False, loop_width=4.0, loop_length=8.0, loop_hole=2.5, loop_pos=None,
        modeling_mode=ModelingMode.HIGH_FIDELITY,
        color_layers=int(p["color_layers"]),
        layer_height_mm=None,
        quantize_colors=int(p["quantize_colors"]),
        blur_kernel=int(p["blur_kernel"]),
        smooth_sigma=float(p["smooth_sigma"]),
        enable_cleanup=True,
        enable_relief=False,
        enable_cloisonne=False,
        enable_outline=False,
        enable_coating=False,
        enable_fridge_magnet=False,
        separate_backing=False,
        backing_output="same_project",
        backing_color_id=0,
        backing_infill_density_percent=100,
        enable_base_layer_height_modifier=False,
        enable_wipe_tower_auto_placement=False,
        center_on_bed=True,
        printer_id=PRINTER_ID,
        slicer="BambuStudio",
        nozzle_size=NOZZLE,
        device_profile_id=DEVICE_PROFILE_ID,
        material_source="lut",
        progress=progress,
        export_transform_metadata=transform_meta,
    )

    t0 = time.time()
    ctx = build_ctx(**kwargs)
    runtime = time.time() - t0
    if ctx.get("error"):
        raise SystemExit("Lumina conversion failed: %s" % ctx["error"])

    total_layers = int(ctx["total_layers"])
    thickness = round(total_layers * LAYER_MM, 6)
    if abs(thickness - args.expect_thickness) > 1e-6:
        raise SystemExit("thickness %.3f mm != expected %.3f mm (total_layers=%d)"
                         % (thickness, args.expect_thickness, total_layers))

    scene = ctx["scene"]
    slot_names = list(ctx.get("slot_names") or [])
    material_matrix = np.asarray(ctx["material_matrix"])
    h, w = material_matrix.shape[:2]
    width_mm = w * PIXEL_MM
    height_mm = h * PIXEL_MM

    # group scene geometries by colour slot (Lumina may split a slot into __part_N)
    # keep the real Trimesh topology (do NOT re-weld triangles: STL is exported
    # straight from these meshes, and watertightness is checked on them).
    slot_meshes: dict[str, list] = {}
    for name, geom in scene.geometry.items():
        base = str(name).split("__part_")[0]
        slot_meshes.setdefault(base, []).append(geom)

    print("[lumina] slots: %s" % slot_names)
    print("[lumina] scene nodes: %d -> %d slots, total_layers=%d, t=%.2f mm, %.1fs"
          % (len(scene.geometry), len(slot_meshes), total_layers, thickness, runtime))
    raw_v = np.concatenate([np.asarray(m.vertices, dtype=np.float64)
                            for ml in slot_meshes.values() for m in ml])
    print("[lumina] raw scene bbox min=%s max=%s" % (
        np.round(raw_v.min(0), 4).tolist(), np.round(raw_v.max(0), 4).tolist()))
    # S09 leaves the part in absolute bed coordinates (e.g. +128 mm centre on a
    # 256 mm bed).  Re-centre XY on the part bbox; Z already starts at 0.
    centre_xy = (raw_v.min(0)[:2] + raw_v.max(0)[:2]) / 2.0
    print("[lumina] re-centring XY by -%s mm" % np.round(centre_xy, 4).tolist())
    for ml in slot_meshes.values():
        for m in ml:
            v = np.asarray(m.vertices, dtype=np.float64)
            v[:, :2] -= centre_xy
            m.vertices = v
    print("[lumina] material_matrix shape=%s dtype=%s range=[%d,%d] view-layer air=%d"
          % (material_matrix.shape, material_matrix.dtype,
             int(material_matrix.min()), int(material_matrix.max()),
             int((material_matrix[..., 0] < 0).sum())))
    if args.debug:
        dbg = Path(args.out_root) / art / "debug"
        dbg.mkdir(parents=True, exist_ok=True)
        for i, (sname, mlist) in enumerate(slot_meshes.items(), start=1):
            import trimesh as _tm
            mesh = _tm.util.concatenate(mlist) if len(mlist) > 1 else mlist[0]
            mesh.export(str(dbg / ("raw_%d_%s.stl" % (i, sname.replace(" ", "_")))))
        np.save(dbg / "material_matrix.npy", material_matrix)
        (dbg / "raw_bbox.json").write_text(json.dumps(
            {"min": np.round(raw_v.min(0), 4).tolist(),
             "max": np.round(raw_v.max(0), 4).tolist(),
             "slots": slot_names}, indent=2))
        print("[lumina] debug dump ->", rel(dbg))

    def transformed(meshes):
        """print pose -> assembly pose for a list of trimesh meshes."""
        out = []
        for m in meshes:
            g = m.copy()
            v = np.asarray(g.vertices, dtype=np.float64) * sign + np.array([0.0, 0.0, thickness])
            g.vertices = v
            out.append(g)
        return out

    # detect the in-plane mirror that lands the art in ASSEMBLY pose
    best, best_err, best_margin = detect_orientation(slot_meshes, slot_names,
                                                     material_matrix,
                                                     width_mm, height_mm)
    sign, desc = CANDIDATES[best]
    print("[lumina] assembly pose: %s (%s), rms %.3f mm, margin %.1fx"
          % (best, desc, best_err, best_margin))

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("filament_*.stl"):
        old.unlink()

    import trimesh

    # slot order = slot_names order; fall back to node order
    ordered = []
    for i, sname in enumerate(slot_names):
        if sname in slot_meshes:
            ordered.append((sname, slot_meshes[sname]))
    for sname in slot_meshes:
        if not any(sname == o[0] for o in ordered):
            ordered.append((sname, slot_meshes[sname]))

    entries = []
    all_tris = []
    total_vol = 0.0
    for i, (sname, mlist) in enumerate(ordered, start=1):
        hexv = SLOT_HEX.get(sname, "#808080")
        meshes = transformed(mlist)
        mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        vol = abs(float(mesh.volume))
        ntri = int(len(mesh.faces))
        fname = "filament_%d_%s.stl" % (i, hexv.lstrip("#"))
        mesh.export(str(out_dir / fname))
        all_tris.append(np.asarray(mesh.triangles, dtype=np.float64))
        total_vol += vol
        entries.append({
            "number": i,
            "slot": sname,
            "hex": hexv,
            "file": fname,
            "triangles": ntri,
            "volume_mm3": round(vol, 3),
            "sha256": sha256_file(out_dir / fname),
            "parts": len(mlist),
            "watertight": bool(getattr(mesh, "is_watertight", False)),
        })

    # shared bbox / thickness from the union
    verts = np.concatenate([t.reshape(-1, 3) for t in all_tris])
    lo = [round(float(v), 4) for v in verts.min(0)]
    hi = [round(float(v), 4) for v in verts.max(0)]
    dia = round(max(hi[0] - lo[0], hi[1] - lo[1]), 4)
    t_meas = round(hi[2] - lo[2], 4)
    if abs(t_meas - thickness) > 0.01:
        raise SystemExit("exported print thickness %.3f != %.3f" % (t_meas, thickness))

    # copy Lumina's own artifacts (names carry timestamps -> stable local names)
    artifacts = {}
    tmf = ctx.get("result_tuple")[0] if ctx.get("result_tuple") else None
    glb = ctx.get("result_tuple")[1] if ctx.get("result_tuple") else None
    prev = ctx.get("result_tuple")[2] if ctx.get("result_tuple") else ctx.get("preview_img")
    if tmf and Path(tmf).exists():
        dst = out_dir / "plate_lumina.3mf"
        dst.write_bytes(Path(tmf).read_bytes())
        artifacts["threemf"] = {"file": dst.name, "bytes": dst.stat().st_size,
                                "sha256": sha256_file(dst)}
    if prev is not None:
        dstp = out_dir / "plate_preview.png"
        prev.save(dstp)
        artifacts["preview"] = {"file": dstp.name, "sha256": sha256_file(dstp)}
    if glb and Path(glb).exists():
        dstg = out_dir / "plate_preview.glb"
        dstg.write_bytes(Path(glb).read_bytes())
        artifacts["glb"] = {"file": dstg.name, "bytes": dstg.stat().st_size}
    for key, name in (("material_matrix", "material_matrix.npy"),
                      ("matched_rgb", "matched_rgb.npy"),
                      ("mask_solid", "mask_solid.npy")):
        if ctx.get(key) is not None:
            np.save(out_dir / name, np.asarray(ctx[key]))
            artifacts[key] = {"file": name,
                              "sha256": sha256_file(out_dir / name)}

    # per-slot usage: (a) voxels over ALL colour layers (what the print actually
    # consumes; a pale artwork can have a 100% White viewing surface while Yellow
    # and Blue live in the under-layers), (b) the viewing-layer count.
    usage = {}
    view_usage = {}
    view = material_matrix[..., 0]
    for i, sname in enumerate(slot_names):
        usage[sname] = int((material_matrix == i).sum())
        view_usage[sname] = int((view == i).sum())

    manifest = {
        "schema": "smartcoaster.appearance.print_lumina/v1",
        "engine": {
            "name": "Lumina-Layers (Lumina Studio 2.0)",
            "root": str(LUMINA),
            "git_head": args.git_head or "",
            "license": "AGPL-3.0-only (called as a library, not modified)",
            "entry": "core.converter.build_image_model_context",
            "python": sys.version.split()[0],
        },
        "art": {
            "name": art,
            "png": rel(png),
            "png_sha256": sha256_file(png),
            "width": w,
            "height": h,
            "pixel_size_mm": PIXEL_MM,
            "target_width_mm": p["target_width_mm"],
        },
        "params": {
            "structure_mode": "Single-sided",
            "modeling_mode": "HIGH_FIDELITY",
            "color_mode": p["color_mode"],
            "lut": p["lut"],
            "lut_sha256": sha256_file(lut),
            "color_layers": int(p["color_layers"]),
            "spacer_thick_mm": float(p["spacer_thick_mm"]),
            "layer_height_mm": LAYER_MM,
            "total_layers": total_layers,
            "quantize_colors": int(p["quantize_colors"]),
            "blur_kernel": int(p["blur_kernel"]),
            "smooth_sigma": float(p["smooth_sigma"]),
            "printer_id": PRINTER_ID,
            "device_profile_id": DEVICE_PROFILE_ID,
            "nozzle_size_mm": float(NOZZLE),
            "backing_color": "White (slot 0)",
            "backing_infill_density_percent": 100,
        },
        "geometry": {
            "orientation": "assembly pose: art face up (+Z), flat back at z=0",
            "assembly_transform": desc,
            "assembly_sign": [float(x) for x in sign],
            "thickness_mm": thickness,
            "print_thickness_mm": thickness,
            "total_thickness_mm": thickness,
            "diameter_mm": dia,
            "bbox_mm": {"min": lo, "max": hi, "size": [round(hi[i] - lo[i], 4) for i in range(3)]},
            "orientation_volume_centroid_rms_mm": round(best_err, 4),
            "orientation_margin": round(best_margin, 2),
            "orientation_method": "volume-weighted per-slot XY centroid, both in-plane "
                                  "mirrors scored, winner must be <=3.0 mm and >=2.5x "
                                  "better than the runner-up",
            "image_top_axis": "+Y",
        },
        "palette": [SLOT_HEX.get(s, "#808080") for s, _ in ordered],
        "palette_bottom_up": [SLOT_HEX.get(s, "#808080") for s, _ in ordered],
        "slot_names": slot_names,
        "slot_pixel_counts": usage,          # voxel count over all colour layers
        "slot_view_layer_counts": view_usage,  # viewing-surface pixel count
        "filament_objects": entries,
        "filaments": entries,
        "parts": entries,
        "artifacts": artifacts,
        "lumina_transform_metadata": transform_meta,
        "runtime_s": round(runtime, 2),
        "progress": logs,
        "provenance": {
            "call_kwargs": {k: (str(v) if not isinstance(v, (int, float, bool, str, type(None)))
                                else v) for k, v in kwargs.items() if k != "progress"},
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "appearance/lumina/lumina_convert.py",
        },
        "validation": {
            "thickness_ok": abs(t_meas - thickness) <= 0.01,
            "diameter_ok": abs(dia - p["target_width_mm"]) <= 0.2,
            "slots_ok": [s for s, _ in ordered] == slot_names[:len(ordered)],
            "watertight": None,   # filled below
            "volume_mm3": round(total_vol, 3),
        },
    }

    # watertight check per filament (already computed on the exported topology)
    wt = {e["file"]: bool(e["watertight"]) for e in entries}
    manifest["validation"]["watertight"] = wt
    manifest["validation"]["all_watertight"] = all(wt.values())

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "lumina_call.json").write_text(
        json.dumps(manifest["provenance"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print("[lumina] %-4s -> %s" % (art, rel(out_dir)))
    print("[lumina]   thickness %.3f mm  diameter %.2f mm  slots %d  triangles %s"
          % (thickness, dia, len(entries), sum(e["triangles"] for e in entries)))
    print("[lumina]   watertight %s  volume %.1f mm3  runtime %.1fs"
          % (manifest["validation"]["all_watertight"], total_vol, runtime))
    if not manifest["validation"]["all_watertight"]:
        raise SystemExit("some filament meshes are not watertight")
    return manifest


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--art", default="dog,elf")
    ap.add_argument("--out-root", default=str(PRINT_ROOT))
    ap.add_argument("--spacer", type=float, default=None,
                    help="backing thickness mm (total = (5 + round(spacer/0.08))*0.08)")
    ap.add_argument("--expect-thickness", type=float, default=1.20)
    ap.add_argument("--lut", default=None)
    ap.add_argument("--color-mode", default=None)
    ap.add_argument("--quantize", type=int, default=None)
    ap.add_argument("--git-head", default=None)
    ap.add_argument("--manifest-only", action="store_true", help="skip conversion, validate only")
    ap.add_argument("--debug", action="store_true", help="dump raw print-pose meshes for diagnostics")
    args = ap.parse_args(argv)

    arts = [a.strip() for a in args.art.split(",") if a.strip()]
    ok = True
    for art in arts:
        if art not in PARAMS:
            raise SystemExit("unknown art %r (known: %s)" % (art, ", ".join(PARAMS)))
        out_dir = Path(args.out_root) / art
        if args.manifest_only:
            mf = out_dir / "manifest.json"
            if not mf.exists():
                print("MISSING", rel(mf)); ok = False; continue
            m = json.loads(mf.read_text())
            print("OK %-4s t=%.3f dia=%.2f slots=%d watertight=%s"
                  % (art, m["geometry"]["thickness_mm"], m["geometry"]["diameter_mm"],
                     len(m["filament_objects"]), m["validation"]["all_watertight"]))
            continue
        convert(art, out_dir, args)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
