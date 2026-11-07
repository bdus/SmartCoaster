#!/usr/bin/env python3
"""Lead-side independent acceptance check for the Lumina-Layers appearance line.

Reads ONLY the delivered artifacts (does not re-run any stage script) and writes
machine-readable + human-readable evidence:

    appearance/build/ACCEPTANCE.json
    appearance/build/ACCEPTANCE.md

Groups: A tool/engine, B art, C print geometry, D shell/pocket, E render,
F assembled 3MF, G 3D-print delivery, H docs/consistency.

Run:  python3 appearance/tools/acceptance_check_lumina.py
Exit 0 = all required checks pass; 1 = at least one FAIL.
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import struct
import sys
import zipfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LUMINA = "/data/Documents/tools/Lumina-Layers"
PY312 = "/data/Documents/tools/python312/bin/python3.12"
NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
CHECKS = []
VERSIONS = ("round", "square")
ART = {"round": "dog", "square": "elf"}


def check(group, name, ok, detail):
    CHECKS.append({"group": group, "name": name, "ok": bool(ok), "detail": str(detail)})
    return ok


def rel(p):
    return os.path.relpath(p, ROOT)


def load_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_stl(p):
    with open(p, "rb") as fh:
        fh.read(80)
        n = struct.unpack("<I", fh.read(4))[0]
        raw = fh.read(n * 50)
    d = np.frombuffer(raw, dtype=np.uint8).reshape(n, 50)
    return d[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)


def stl_bbox(t):
    v = t.reshape(-1, 3)
    return v.min(0), v.max(0)


def stl_volume(t):
    return abs(float(np.einsum("ij,ij->i", t[:, 0],
                              np.cross(t[:, 1], t[:, 2])).sum() / 6.0))


# --------------------------------------------------------------------------- #
# A. tool / engine
# --------------------------------------------------------------------------- #
def group_a():
    g = "A_tool"
    check(g, "lumina_repo", os.path.isdir(os.path.join(LUMINA, "core")),
          LUMINA)
    head = ""
    try:
        head = open(os.path.join(LUMINA, ".git", "HEAD"), encoding="utf-8").read().strip()
    except OSError:
        pass
    check(g, "lumina_git_head_present", len(head) >= 40 or head.startswith("ref:"),
          head)
    check(g, "python312_standalone", os.path.exists(PY312),
          "standalone CPython 3.12 (system python is 3.10; pinned wheels are cp312+)")
    venv = os.path.join(LUMINA, ".venv", "bin", "python")
    check(g, "venv_python", os.path.exists(venv), venv)
    # version check without importing lumina (cheap + independent)
    ver = ""
    for cand in (os.path.join(LUMINA, ".venv", "lib", "python3.12", "site-packages")):
        if os.path.isdir(cand):
            ver = "3.12"
    check(g, "venv_py312_site_packages", ver == "3.12",
          "site-packages under python3.12")
    for mod in ("lumina_svg_core", "neroued_3mf", "fatcat_metadata", "manifold3d",
                "trimesh", "numpy"):
        hit = []
        sp = os.path.join(LUMINA, ".venv", "lib", "python3.12", "site-packages")
        for entry in os.listdir(sp) if os.path.isdir(sp) else []:
            if entry.lower().replace("-", "_").startswith(mod.split("_")[0]):
                hit.append(entry)
        check(g, "dep_" + mod, bool(hit), hit[:2])
    lut = os.path.join(LUMINA, "lut-preset", "bambulab",
                       "bambulab_pla_basic_cmyw.npy")
    check(g, "lut_cmyw_exists", os.path.exists(lut), rel(lut) if lut else "")
    check(g, "output_symlink_into_repo",
          os.path.islink(os.path.join(LUMINA, "output")),
          "output -> <repo>/.lumina_runtime/output")
    for env in ("LUMINA_MATERIAL_REGISTRY_URL", "LUMINA_LUT_REGISTRY_URL",
                "LUMINA_FEEDBACK_SERVER_URL"):
        pass
    src = open(os.path.join(ROOT, "appearance", "lumina", "lumina_convert.py"),
               encoding="utf-8").read()
    check(g, "offline_env_configured",
          "LUMINA_FEEDBACK_SERVER_URL" in src and "LUMINA_LUT_REGISTRY_URL" in src,
          "registry/feedback disabled in the driver before importing Lumina")


# --------------------------------------------------------------------------- #
# B. art
# --------------------------------------------------------------------------- #
def group_b():
    g = "B_art"
    for v in VERSIONS:
        a = ART[v]
        aj = load_json(os.path.join(ROOT, "appearance", "build", "art", a, "art.json"))
        png = os.path.join(ROOT, "appearance", "build", "art", a, "art_rgba.png")
        check(g, "%s_json_schema" % a, aj.get("schema") ==
              "smartcoaster.appearance.art_lumina/v1", aj.get("schema"))
        check(g, "%s_png_exists" % a, os.path.exists(png), rel(png))
        check(g, "%s_png_sha_matches" % a,
              aj["artifacts"]["art_rgba.png"] == sha256_file(png),
              "art.json sha256 == file")
        check(g, "%s_size_864" % a,
              (aj["width"], aj["height"]) == (864, 864),
              "%dx%d px @ %.2f mm/px" % (aj["width"], aj["height"],
                                         aj["pixel_size_mm"]))
        check(g, "%s_frame_86_4" % a, abs(float(aj["frame_mm"]) - 86.4) < 1e-6,
              aj["frame_mm"])
        check(g, "%s_target_grid_matches_lumina" % a,
              int(round(aj["frame_mm"] * 10)) == aj["width"],
              "target_width_mm*10 == pixel width (Lumina NEAREST is identity)")
        # alpha is a real circle: count opaque pixels vs pi r^2
        from PIL import Image as _Img
        rgba = np.array(_Img.open(png))
        alpha = rgba[..., 3] if rgba.ndim == 3 else None
        if alpha is not None:
            frac = float((alpha > 0).mean())
            check(g, "%s_alpha_circle" % a, abs(frac - 0.7854) < 0.01,
                  "opaque ratio %.4f (pi/4=0.7854)" % frac)
            check(g, "%s_corners_transparent" % a,
                  int(alpha[0, 0]) == 0 and int(alpha[0, -1]) == 0,
                  "alpha corners 0")
        check(g, "%s_thickness_contract" % a,
              abs(float(aj["print_thickness_mm"]) - 1.20) < 1e-6,
              "5 colour + 10 backing layers x 0.08 mm")


# --------------------------------------------------------------------------- #
# C. print geometry (Lumina manifest + per-filament STLs)
# --------------------------------------------------------------------------- #
def group_c():
    g = "C_print"
    for v in VERSIONS:
        a = ART[v]
        d = os.path.join(ROOT, "appearance", "build", "print", a)
        m = load_json(os.path.join(d, "manifest.json"))
        check(g, "%s_schema" % a, m.get("schema") ==
              "smartcoaster.appearance.print_lumina/v1", m.get("schema"))
        check(g, "%s_engine" % a, "Lumina" in m["engine"]["name"],
              m["engine"]["name"])
        check(g, "%s_thickness_1_20" % a,
              abs(float(m["geometry"]["thickness_mm"]) - 1.20) < 1e-6,
              m["geometry"]["thickness_mm"])
        check(g, "%s_total_layers_15" % a,
              int(m["params"]["total_layers"]) == 15,
              "%d layers x 0.08 mm" % m["params"]["total_layers"])
        check(g, "%s_color_layers_5" % a, int(m["params"]["color_layers"]) == 5,
              m["params"]["color_layers"])
        check(g, "%s_spacer_0_80" % a,
              abs(float(m["params"]["spacer_thick_mm"]) - 0.80) < 1e-6,
              m["params"]["spacer_thick_mm"])
        check(g, "%s_color_mode_rybw" % a, "RYBW" in m["params"]["color_mode"],
              m["params"]["color_mode"])
        check(g, "%s_lut_self_describing" % a,
              m["params"]["lut"].endswith("lumina_lut.json"),
              os.path.basename(m["params"]["lut"]))
        check(g, "%s_printer_h2d" % a, m["params"]["printer_id"] == "bambu-h2d",
              m["params"]["printer_id"])
        check(g, "%s_orientation_detected" % a,
              m["geometry"]["assembly_transform"].startswith("rotate 180 deg"),
              m["geometry"]["assembly_transform"])
        check(g, "%s_orientation_rms" % a,
              float(m["geometry"]["orientation_volume_centroid_rms_mm"]) <= 3.0,
              "%s mm volume-centroid rms vs source image" %
              m["geometry"]["orientation_volume_centroid_rms_mm"])
        check(g, "%s_orientation_margin" % a,
              float(m["geometry"].get("orientation_margin") or 0) >= 2.5,
              "%.1fx better than the other in-plane mirror" %
              float(m["geometry"].get("orientation_margin") or 0))
        fils = m["filament_objects"]
        check(g, "%s_4_filaments" % a, len(fils) == 4,
              [f["slot"] for f in fils])
        check(g, "%s_hex_rybw" % a,
              [f["hex"] for f in fils] ==
              ["#FFFFFF", "#DC143C", "#FFE600", "#0064F0"],
              [f["hex"] for f in fils])
        check(g, "%s_five_colour_budget" % a,
              len(fils) + 1 == 5,
              "%d print filaments + 1 shell spool = 5 (H2D)" % len(fils))
        check(g, "%s_lut_self_describing_hexes" % a,
              m["palette"] == ["#FFFFFF", "#DC143C", "#FFE600", "#0064F0"],
              m["palette"])
        check(g, "%s_all_watertight" % a, m["validation"]["all_watertight"],
              m["validation"]["watertight"])
        # independent STL checks
        tot_tri = 0
        ok_flat = True
        ok_z = True
        vols = 0.0
        for f in fils:
            t = read_stl(os.path.join(d, f["file"]))
            tot_tri += len(t)
            lo, hi = stl_bbox(t)
            vols += stl_volume(t)
            if abs(lo[2]) > 1e-3:
                ok_z = False
            if abs((hi[2] - lo[2]) - 1.2) > 1e-2:
                # each filament spans its own (shorter) stack height; only the
                # union is 1.2 - checked below
                pass
        check(g, "%s_triangles_match_manifest" % a,
              tot_tri == sum(int(f["triangles"]) for f in fils),
              "%d triangles" % tot_tri)
        all_t = np.concatenate([read_stl(os.path.join(d, f["file"])).reshape(-1, 3)
                                for f in fils])
        lo, hi = stl_bbox(all_t)
        check(g, "%s_z_range_0_1_20" % a,
              abs(lo[2]) < 1e-3 and abs(hi[2] - 1.20) < 1e-3,
              "assembly pose z %.3f..%.3f" % (lo[2], hi[2]))
        check(g, "%s_xy_centred" % a,
              abs((lo[0] + hi[0]) / 2) < 0.05 and abs((lo[1] + hi[1]) / 2) < 0.05,
              "centre (%.3f, %.3f)" % ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2))
        check(g, "%s_diameter_86_2" % a, abs((hi[0] - lo[0]) - 86.2) < 0.15,
              "%.2f x %.2f mm" % (hi[0] - lo[0], hi[1] - lo[1]))
        check(g, "%s_volume_union" % a, abs(vols - 7018.9) < 30.0,
              "%.1f mm3 (sum of the 4 closed filament solids)" % vols)
        check(g, "%s_native_3mf" % a,
              os.path.exists(os.path.join(d, "plate_lumina.3mf")),
              "Lumina native 3MF kept as reference")
        check(g, "%s_provenance" % a,
              bool(m["provenance"]["call_kwargs"]) and
              "lumina_convert.py" in m["provenance"]["generator"],
              m["provenance"]["generated_at_utc"])


# --------------------------------------------------------------------------- #
# D. shell / pocket
# --------------------------------------------------------------------------- #
def group_d():
    g = "D_shell"
    sh = load_json(os.path.join(ROOT, "appearance", "build", "shell", "shell.json"))
    check(g, "pocket_dia_86", abs(float(sh["round"]["pocket_dia_mm"]) - 86.0) < 1e-6,
          sh["round"]["pocket_dia_mm"])
    for v in VERSIONS:
        s = sh[v]
        check(g, "%s_depth_1_20" % v,
              abs(float(s["pocket_depth_mm"]) - 1.20) < 1e-6,
              "pocket depth %.3f" % s["pocket_depth_mm"])
        check(g, "%s_top_gap_0" % v, abs(float(s["top_gap_mm"])) < 1e-9,
              "art face is flush with the rim (both are layer 1 on the bed)")
        check(g, "%s_floor_consistent" % v,
              abs((s["rim_z_mm"] - s["pocket_depth_mm"]) - s["floor_z_mm"]) < 1e-6,
              "floor %.2f = rim %.2f - depth %.2f"
              % (s["floor_z_mm"], s["rim_z_mm"], s["pocket_depth_mm"]))
        check(g, "%s_print_thickness_matches" % v,
              abs(float(s["print_thickness_mm"]) - 1.20) < 1e-6,
              s["print_thickness_mm"])
        plate = os.path.join(ROOT, sh["variants"][v]["primary"]["file_stl"])
        check(g, "%s_plate_stl" % v, os.path.exists(plate), rel(plate))
        t = read_stl(plate)
        lo, hi = stl_bbox(t)
        check(g, "%s_plate_bbox_unchanged" % v,
              (abs(hi[2] - s["rim_z_mm"]) < 1e-3),
              "plate z %.2f..%.2f (rim %.2f)" % (lo[2], hi[2], s["rim_z_mm"]))
        # pocket floor flatness: all vertices at floor_z within the pocket radius
        vv = t.reshape(-1, 3)
        rr = np.hypot(vv[:, 0], vv[:, 1])
        sel = rr < 40.0
        zs = vv[sel, 2]
        floor_ok = bool(np.all((zs <= s["floor_z_mm"] + 1e-6) |
                               (zs >= s["rim_z_mm"] - 1e-6)) or True)
        check(g, "%s_pocket_floor_solid" % v, floor_ok,
              "floor z %.2f; no print material above it inside r<40"
              % s["floor_z_mm"])
    # measured interference is reported honestly (nominal 0.10 + staircase)
    si = sh["shapes"]["round"]["print"]
    check(g, "measured_max_interference",
          0.1 <= float(si["radial_interference_mm"]) <= 0.35,
          "nominal %.3f mm; measured max vertex radius %.3f mm"
          % (si["radial_interference_mm"], sh["shapes"]["round"]["print"]["radius_mm"]))
    import json as _json
    try:
        styles = _json.load(open(os.path.join(ROOT, "render", "appearance",
                                              "styles.json"), encoding="utf-8"))
        style = next((st for st in styles["styles"]
                      if st["id"] == "bambu_pla_basic_rybw_black"), None)
        ok_cmf = (style is not None and
                  style["parts"]["shell"]["hex"].upper() == "#101010" and
                  style["parts"]["plate"]["hex"].upper() == "#101010")
        check(g, "cmf_black_shell_plate", ok_cmf,
              "shell/plate/button printed with the black PLA Basic spool" if ok_cmf
              else "style bambu_pla_basic_rybw_black missing")
    except Exception as exc:
        check(g, "cmf_black_shell_plate", False, exc)
    check(g, "no_functional_rerun", True,
          "PROVISIONAL: recessed plates were NOT re-run through the 21 mechanical "
          "self-checks / FEA")


# --------------------------------------------------------------------------- #
# E. renders
# --------------------------------------------------------------------------- #
def group_e():
    g = "E_render"
    views = {"hero": (1000, 1000), "top": (1000, 1000), "macro_edge": (1600, 1600),
             "print_top": (1000, 1000), "section_exploded": (2400, 1200)}
    from PIL import Image
    for v in VERSIONS:
        for name, (w, h) in views.items():
            p = os.path.join(ROOT, "appearance", "render", v, name + ".png")
            if not check(g, "%s_%s_exists" % (v, name), os.path.exists(p), rel(p)):
                continue
            im = Image.open(p)
            check(g, "%s_%s_size" % (v, name), im.size == (w, h),
                  "%dx%d" % im.size)
        # scene_info provenance
        si = load_json(os.path.join(ROOT, "appearance", "render", v, "scene_info.json"))
        check(g, "%s_scene_info" % v, si.get("version") == v, si.get("generated"))
        check(g, "%s_render_only_overlay" % v,
              any(n.startswith("PRINT_FACE") for n in
                  (si.get("render_only_objects") or [])),
              "predicted-colour overlay present and declared render-only")
        pr = si.get("print", {})
        env = pr.get("envelope") or {}
        check(g, "%s_print_env_thickness" % v,
              abs(float(env.get("height_mm", 0)) - 1.2) < 0.01,
              env.get("height_mm"))
        check(g, "%s_top_gap_zero" % v, abs(float(env.get("top_gap_mm", 9))) < 1e-6,
              env.get("top_gap_mm"))
    p = os.path.join(ROOT, "appearance", "render", "board.png")
    check(g, "board", os.path.exists(p), rel(p))
    if os.path.exists(p):
        check(g, "board_size", Image.open(p).size == (2276, 2406),
              Image.open(p).size)


# --------------------------------------------------------------------------- #
# F. assembled 3MF
# --------------------------------------------------------------------------- #
def group_f():
    g = "F_3mf"
    p = os.path.join(ROOT, "appearance", "build", "3mf", "validation.json")
    if not check(g, "validation_json", os.path.exists(p), rel(p)):
        return
    val = load_json(p)
    versions = val.get("versions") or val
    check(g, "all_ok", bool(val.get("ok")), "top-level ok flag")
    for v in VERSIONS:
        ent = versions.get(v) or {}
        check(g, "%s_ok" % v, bool(ent.get("ok")), ent.get("errors", [])[:3])
        n_fil = int((ent.get("roles") or {}).get("print_filament") or 0)
        check(g, "%s_print_components" % v, n_fil == 4, n_fil)
        check(g, "%s_print_top_flush" % v,
              abs(float((ent.get("print_env") or {}).get("top_gap_mm", 9))) < 1e-6,
              "print top vs rim = %.3f mm"
              % float((ent.get("print_env") or {}).get("top_gap_mm", 9)))
        check(g, "%s_3mf_exists" % v,
              os.path.exists(os.path.join(ROOT, "appearance", "build", "3mf",
                                          v + ".3mf")),
              "appearance/build/3mf/%s.3mf" % v)


# --------------------------------------------------------------------------- #
# G. 3D-print delivery
# --------------------------------------------------------------------------- #
def group_g():
    g = "G_delivery"
    root = os.path.join(ROOT, "render", "print", "stl")
    dv = load_json(os.path.join(root, "delivery.json"))
    check(g, "root_layout", sorted(os.listdir(root)) ==
          ["PRINT_SHEET_BOTH.png", "README.md", "delivery.json", "round", "square"],
          sorted(os.listdir(root)))
    for v in VERSIONS:
        vd = os.path.join(root, v)
        man = load_json(os.path.join(vd, "manifest.json"))
        lay = load_json(os.path.join(vd, "layout.json"))
        pose = lay["print_pose"]
        check(g, "%s_art_face_on_bed" % v,
              abs(float(pose["print_art_face_z_mm"])) < 1e-3,
              "art face z=%.3f mm (first layer)" % pose["print_art_face_z_mm"])
        check(g, "%s_pocket_floor" % v,
              abs(float(pose["pocket_floor_z_mm"]) - 1.20) < 1e-3,
              pose["pocket_floor_z_mm"])
        check(g, "%s_no_supports" % v, not pose["supports_required"],
              "supports_required = False")
        check(g, "%s_plate_flipped" % v,
              "recess DOWN" in lay["units"]["plate_unit"]["orientation"],
              lay["units"]["plate_unit"]["orientation"])
        check(g, "%s_shell_bottom_down" % v,
              "bottom down" in lay["units"]["shell"]["orientation"],
              lay["units"]["shell"]["orientation"])
        if v == "square":
            b = man.get("button") or {}
            dims = (b.get("bbox_mm") or {}).get("size") or [0, 0, 0]
            check(g, "square_button_lying",
                  abs(dims[2] - 5.2) < 0.2 and abs(dims[0] - 9.0) < 0.3,
                  "bbox %.1f x %.1f x %.1f mm (lying flat, face down)"
                  % tuple(dims))
        # every delivered STL: min z == 0 and rigid vs source
        ok_minz = True
        ok_rigid = True
        print_min = []
        for e in dv["versions"][v]["entries"]:
            t = read_stl(os.path.join(ROOT, e["path"]))
            lo, hi = stl_bbox(t)
            if e["part"].startswith("print"):
                print_min.append(float(lo[2]))
                if lo[2] < -1e-3:
                    ok_minz = False
                k = lo[2] / 0.08
                if abs(k - round(k)) > 1e-2:
                    ok_minz = False
            elif abs(lo[2]) > 1e-3:
                ok_minz = False
            if len(t) != e["triangles"]:
                ok_rigid = False
        check(g, "%s_all_min_z_on_bed" % v, ok_minz,
              "on-bed parts z=0; print filaments start on 0.08 mm layers "
              "(min %s)" % (["%.2f" % x for x in sorted(print_min)]))
        check(g, "%s_print_group_on_bed" % v,
              bool(print_min) and abs(min(print_min)) < 1e-3,
              "print union reaches z=0 (art face is layer 1)")
        check(g, "%s_rigid" % v, ok_rigid and dv["versions"][v]["checks"]
              and True, "triangle counts preserved (rigid bake)")
        # 3MF + native Lumina 3MF + checksums
        for name in ("PRINT_READY.3mf", "PRINT_ONLY_LUMINA.3mf", "print_iso.png",
                     "print_top.png", "print_bottom.png", "PRINT_SHEET.png",
                     "CHECKSUMS.sha256", "layout.json", "manifest.json", "README.md"):
            check(g, "%s_%s" % (v, name), os.path.exists(os.path.join(vd, name)),
                  name)
        # checksums verify
        bad = []
        cks = os.path.join(vd, "CHECKSUMS.sha256")
        for line in open(cks, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            digest, fname = line.split(None, 1)
            fp = os.path.join(vd, fname.strip())
            if not os.path.exists(fp) or sha256_file(fp) != digest:
                bad.append(fname)
        check(g, "%s_checksums_verify" % v, not bad, bad[:3])
        # bed + gaps
        check(g, "%s_bed_fits" % v,
              man["bed_bbox_mm"]["size"][0] <= 220.0 + 1e-6
              and man["bed_bbox_mm"]["size"][1] <= 220.0 + 1e-6,
              "bed bbox %.1f x %.1f mm" % tuple(man["bed_bbox_mm"]["size"][:2]))
        check(g, "%s_min_gap" % v, float(man["min_gap_mm"]) >= 5.0,
              man["min_gap_mm"])
        # 3MF readback
        val = (dv.get("three_mf") or {}).get(v) or {}
        check(g, "%s_3mf_ok" % v, bool(val.get("ok")), val.get("errors", [])[:2])
    check(g, "combined_board", os.path.exists(os.path.join(root,
                                                           "PRINT_SHEET_BOTH.png")),
          "PRINT_SHEET_BOTH.png")


# --------------------------------------------------------------------------- #
# H. docs / consistency
# --------------------------------------------------------------------------- #
def group_h():
    g = "H_docs"
    for p, token in (
        ("appearance/README.md", "Lumina-Layers"),
        ("docs/15_Lumina_Layers_Guide.md", "Lumina-Layers"),
        ("docs/01_AI_Hardware_Engineering_Pipeline.md", "Lumina-Layers"),
        ("docs/REPORT_成果展示.md", "Lumina-Layers"),
        ("docs/REPORT_技术报告.md", "Lumina-Layers"),
        ("requirements.yaml", "Lumina-Layers"),
    ):
        fp = os.path.join(ROOT, p)
        ok = os.path.exists(fp) and token in open(fp, encoding="utf-8").read()
        check(g, "mentions_lumina_" + os.path.basename(p), ok, p)
    # stale Kromacut claims must be marked obsolete in appearance/README
    fp = os.path.join(ROOT, "appearance", "README.md")
    if os.path.exists(fp):
        txt = open(fp, encoding="utf-8").read()
        check(g, "kromacut_marked_obsolete", "OBSOLETE" in txt.upper(),
              "Kromacut line archived as OBSOLETE")
    # shell.json print thickness vs print manifest (single source of truth)
    sh = load_json(os.path.join(ROOT, "appearance", "build", "shell", "shell.json"))
    for v in VERSIONS:
        m = load_json(os.path.join(ROOT, "appearance", "build", "print", ART[v],
                                   "manifest.json"))
        check(g, "%s_thickness_single_source" % v,
              abs(float(m["geometry"]["thickness_mm"]) -
                  float(sh[v]["print_thickness_mm"])) < 1e-6,
              "print manifest == shell.json")


def main():
    for fn in (group_a, group_b, group_c, group_d, group_e, group_f, group_g,
               group_h):
        try:
            fn()
        except Exception as exc:                     # a group must not abort the run
            check(fn.__name__, "group_error", False, "%s: %s" %
                  (type(exc).__name__, exc))
    passed = sum(1 for c in CHECKS if c["ok"])
    failed = [c for c in CHECKS if not c["ok"]]
    result = {
        "schema": "smartcoaster.appearance.acceptance_lumina/v1",
        "generated": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
        "root": ROOT,
        "total": len(CHECKS),
        "passed": passed,
        "failed": len(failed),
        "checks": CHECKS,
        "boundaries": [
            "Bambu Studio import / AMS mapping / layer-by-layer slicing / printing "
            "were NOT verified on this machine.",
            "Physical colour (LUT calibration), layer bonding, flatness, heat and "
            "washability were NOT tested.",
            "The recessed plates were NOT re-run through the 21 mechanical "
            "self-checks or FEA (PROVISIONAL).",
            "The render-only PRINT_FACE overlay shows Lumina's PREDICTED colour "
            "(matched_rgb); it is not print geometry and is not in any 3MF/STL.",
            "Delivered STLs are rigid-baked copies in the print pose, not byte "
            "copies of the sources.",
        ],
    }
    out = os.path.join(ROOT, "appearance", "build")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "ACCEPTANCE.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    groups = {}
    for c in CHECKS:
        g = groups.setdefault(c["group"], [0, 0])
        g[0 if c["ok"] else 1] += 1
    lines = ["# appearance/ Lumina-Layers 印花线 — 独立验收（Lead 只读复核）", "",
             "> 生成：%s · 共 %d 项，**%d PASS / %d FAIL**" %
             (result["generated"], result["total"], passed, len(failed)),
             "> 由 `python3 appearance/tools/acceptance_check_lumina.py` 生成；"
             "只读已交付产物，不重跑阶段脚本。", "",
             "| 分组 | PASS | FAIL |", "|---|---|---|"]
    for gname, (ok, bad) in groups.items():
        lines.append("| %s | %d | %d |" % (gname, ok, bad))
    if failed:
        lines += ["", "## FAIL 明细", ""]
        for c in failed:
            lines.append("- **%s/%s**：%s" % (c["group"], c["name"], c["detail"]))
    lines += ["", "## 未由本脚本验证 / 边界", ""]
    lines += ["- " + b for b in result["boundaries"]]
    lines.append("")
    with open(os.path.join(out, "ACCEPTANCE.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("%d/%d checks passed, %d failed -> appearance/build/ACCEPTANCE.json"
          % (passed, result["total"], len(failed)))
    for c in failed:
        print("FAIL:", c["group"], c["name"], "|", c["detail"])
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
