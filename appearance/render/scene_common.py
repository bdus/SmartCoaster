#!/usr/bin/env python3
"""Shared dependency resolver for the SmartCoaster appearance scene + 3MF writer.

Single source of truth (used by build_scene.py in Blender and make_3mf.py with
system Python) for:

  * where the real shell-assembly STLs live (mechanical/{lumen,square_v1}/build/parts)
    and that the top plate is replaced by appearance/build/shell/{version}/plate_recessed.stl
  * recessed-plate parameters from appearance/build/shell/shell.json
    (pocket diameter, floor z, rim z, print thickness / interference / top gap)
  * the Kromacut per-filament print STLs + palette from
    appearance/build/print/{dog,elf}/manifest.json
  * placeholder fallbacks (print_blank.stl split into per-filament radial bands,
    or synthetic annulus rings when even print_blank.stl is missing)
  * sRGB hex -> linear conversion and the lumen_violet CMF baselines

Pure stdlib (runs both in Blender 4.5 Python 3.11 and system Python 3.x).
Read-only w.r.t. the inputs; never writes geometry files.
"""
import glob
import json
import math
import os
import struct

try:
    import numpy as _np
except Exception:  # pragma: no cover - numpy is bundled with Blender
    _np = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

VERSIONS = {
    "round": {
        "mech": "lumen",
        "art": "dog",
        "label": "LUMEN round",
        "tag": "ROUND \u00b7 LUMEN \u00d8110",
    },
    "square": {
        "mech": "square_v1",
        "art": "elf",
        "label": "square_v1",
        "tag": "SQUARE \u00b7 square_v1 100\u00d7100",
    },
}

# default assembly lists; task-3 spec + docs/13 (round: no guide/ledflex).
# plate is always replaced by the recessed plate, so it is not listed here.
SQUARE_PARTS = ["shell", "pcb", "sensor", "esp32", "hx711", "usbc",
                "battery", "oled", "button", "glass", "pad"]
# LUMEN has no button part; guide/ledflex are legacy light parts (excluded).
ROUND_PARTS = ["shell", "pcb", "sensor", "esp32", "hx711", "usbc",
               "battery", "oled", "glass", "pad"]
EXCLUDE_PARTS = {"guide", "ledflex"}          # docs/13: legacy LED/light-guide


# --------------------------------------------------------------------------- #
# config / paths
# --------------------------------------------------------------------------- #
def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def load_config():
    return _load_json(os.path.join(HERE, "config.json")) or {}


def shell_json_path(version):
    """shell-cad may ship one shared shell.json or per-version files."""
    cands = [
        os.path.join(ROOT, "appearance", "build", "shell", "shell.json"),
        os.path.join(ROOT, "appearance", "build", "shell", version, "shell.json"),
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def _select_version(raw, version):
    """Pick the version subtree if shell.json contains both shapes."""
    if not isinstance(raw, dict):
        return raw
    mech = VERSIONS[version]["mech"]
    for key in (version, mech, VERSIONS[version]["label"]):
        if key in raw and isinstance(raw[key], dict):
            return raw[key]
    for nest in ("versions", "shapes", "plates", "parts"):
        sub = raw.get(nest)
        if isinstance(sub, dict):
            for key in (version, mech):
                if key in sub and isinstance(sub[key], dict):
                    return sub[key]
    return raw


def deep_find(obj, keys, default=None):
    """Recursively find the first numeric value under one of the candidate keys."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                v = obj[k]
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return float(v)
        for v in obj.values():
            r = deep_find(v, keys)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_find(v, keys)
            if r is not None:
                return r
    return default


def srgb_hex_to_linear(hex_str):
    """sRGB hex -> linear RGB.  c<=0.04045 ? c/12.92 : ((c+0.055)/1.055)^2.4"""
    h = str(hex_str).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) < 6:
        raise ValueError("bad hex colour: %r" % (hex_str,))
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def srgb_hex_to_rgba8(hex_str):
    h = str(hex_str).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


# --------------------------------------------------------------------------- #
# shell / CMF
# --------------------------------------------------------------------------- #
def load_cmf(config=None):
    """lumen_violet from render/appearance/styles.json + neutral config_base.json."""
    cfg = config or load_config()
    cmf = cfg.get("cmf", {})
    styles = _load_json(os.path.join(ROOT, cmf.get("styles_json",
                                                  "render/appearance/styles.json")))
    base = _load_json(os.path.join(ROOT, cmf.get("config_base",
                                                 "render/appearance/config_base.json")))
    want = cmf.get("style", "lumen_violet")
    style = None
    if styles:
        for st in styles.get("styles", []):
            if st.get("id") == want:
                style = st
                break
    out = {"style_id": want, "source": "styles.json" if style else "fallback",
           "parts": {}, "base": base or {}, "mismatches": []}
    neutral = (base or {}).get("colors", {})
    out["parts"] = {k: dict(v) for k, v in neutral.items()}
    if style:
        for part, spec in style.get("parts", {}).items():
            hx = spec.get("hex") if isinstance(spec, dict) else spec
            if hx:
                ent = out["parts"].get(part, {})
                ent["hex"] = hx
                out["parts"][part] = ent
    # hard fallbacks (README / docs/10)
    out["parts"].setdefault("shell", {})["hex"] = out["parts"]["shell"].get("hex", "#2A2E35")
    out["parts"].setdefault("plate", {})["hex"] = out["parts"]["plate"].get("hex", "#6B40A0")
    out["parts"].setdefault("button", {})["hex"] = out["parts"]["button"].get("hex", "#6B40A0")
    return out


# --------------------------------------------------------------------------- #
# print manifest
# --------------------------------------------------------------------------- #
_FILE_KEYS = ("file", "filename", "name", "path", "stl", "stl_file")
_HEX_KEYS = ("hex", "color", "colour", "filament_hex", "filament", "palette_hex")


def _extract_palette(data):
    if not isinstance(data, dict):
        return []
    for key in ("palette", "colors", "colours", "filament_colors",
                "palette_hex", "layer_colors"):
        v = data.get(key)
        if isinstance(v, list) and v and isinstance(v[0], str):
            return [str(x) for x in v]
        if isinstance(v, dict):
            vals = [v[k] for k in sorted(v)]
            if vals and isinstance(vals[0], str):
                return [str(x) for x in vals]
    return []


def _extract_files(data, pdir):
    """Return [(filename, hex_or_None, extra_dict)] from a manifest (flexible)."""
    out = []
    files = None
    if isinstance(data, dict):
        for key in ("files", "objects", "stls", "parts", "filaments"):
            if isinstance(data.get(key), (list, dict)):
                files = data[key]
                break
    elif isinstance(data, list):
        files = data
    if files is None:
        return out
    if isinstance(files, dict):
        for fn, val in files.items():
            hx = val if isinstance(val, str) else None
            extra = {}
            if isinstance(val, dict):
                for k in _HEX_KEYS:
                    if isinstance(val.get(k), str):
                        hx = val[k]
                        break
                extra = val
            out.append((str(fn), hx, extra))
        return out
    for ent in files:
        if isinstance(ent, str):
            out.append((ent, None, {}))
            continue
        if not isinstance(ent, dict):
            continue
        fn = None
        for k in _FILE_KEYS:
            if isinstance(ent.get(k), str):
                fn = ent[k]
                break
        if fn is None:
            continue
        hx = None
        for k in _HEX_KEYS:
            if isinstance(ent.get(k), str):
                hx = ent[k]
                break
        out.append((fn, hx, ent))
    return out


def _print_thickness(data, default):
    t = None
    if isinstance(data, dict):
        t = deep_find(data, ("total_thickness_mm", "thickness_mm", "height_mm",
                             "total_height_mm", "print_thickness_mm",
                             "slab_thickness_mm", "thicknessMm", "totalHeightMm",
                             "heightMm", "printThicknessMm", "slabThicknessMm"))
        if t is None:
            layers = deep_find(data, ("layer_count", "layers", "num_layers",
                                      "layerCount"))
            lh = deep_find(data, ("layer_height_mm", "layer_height",
                                  "layerHeightMm", "layerHeight"))
            if layers and lh:
                t = layers * lh
    return t if t else default


def load_print(version, cfg=None, fallback_thickness=None):
    """Resolve the per-filament print STLs (Kromacut) or a placeholder.

    Returns dict:
      source: 'manifest' | 'stl_glob' | 'placeholder_print_blank' | 'placeholder_synthetic'
      objects: [{'name','path'|'tris'|'ring','hex','file'}]  (one per physical filament)
      palette, thickness_mm, manifest_path, reference_3mf, bbox_mm, warnings
    """
    cfg = cfg or load_config()
    art = VERSIONS[version]["art"]
    pdir = os.path.join(ROOT, "appearance", "build", "print", art)
    fallback_pal = cfg.get("print", {}).get("fallback_palette", {}).get(art) or []
    res = {"art": art, "dir": pdir, "source": None, "objects": [], "palette": [],
           "thickness_mm": fallback_thickness, "manifest_path": None,
           "reference_3mf": None, "bbox_mm": None, "warnings": [], "palette_source": None}

    manifest = os.path.join(pdir, "manifest.json")
    data = _load_json(manifest) if os.path.exists(manifest) else None
    if data is not None:
        res["manifest_path"] = manifest
        palette = _extract_palette(data)
        if palette:
            res["palette"] = palette
            res["palette_source"] = "manifest"
        res["thickness_mm"] = _print_thickness(data, res["thickness_mm"])
        entries = _extract_files(data, pdir)
        missing = []
        for i, (fn, hx, extra) in enumerate(entries):
            p = fn if os.path.isabs(fn) else os.path.join(pdir, fn)
            if not os.path.exists(p) and os.path.exists(os.path.join(pdir, os.path.basename(fn))):
                p = os.path.join(pdir, os.path.basename(fn))
            if not os.path.exists(p):
                missing.append(fn)
                continue
            if hx is None and i < len(res["palette"]):
                hx = res["palette"][i]
            res["objects"].append({"name": os.path.splitext(os.path.basename(p))[0],
                                   "path": p, "hex": hx, "file": os.path.basename(p),
                                   "tris_declared": extra.get("triangles")})
        if missing:
            res["warnings"].append("manifest lists %d missing STL(s): %s"
                                   % (len(missing), ", ".join(missing[:6])))
        if res["objects"]:
            res["source"] = "manifest"
            if not res["palette"]:
                res["palette"] = [o["hex"] for o in res["objects"] if o.get("hex")]
                res["palette_source"] = "manifest:stl_hex"

    if not res["objects"]:
        stls = sorted(glob.glob(os.path.join(pdir, "*.stl")))
        if stls:
            pal = res["palette"] or fallback_pal
            if not res["palette"]:
                res["palette"] = pal
                res["palette_source"] = "fallback"
            for i, p in enumerate(stls):
                hx = pal[i % len(pal)] if pal else None
                res["objects"].append({"name": os.path.splitext(os.path.basename(p))[0],
                                       "path": p, "hex": hx,
                                       "file": os.path.basename(p)})
            res["source"] = "stl_glob"
            res["warnings"].append("manifest.json missing/incomplete; "
                                   "globbed %d STL(s) and assigned palette by order" % len(stls))

    m3mfs = sorted(glob.glob(os.path.join(pdir, "*.3mf")))
    if m3mfs:
        res["reference_3mf"] = m3mfs[0]

    if not res["objects"]:
        # ---- placeholder -------------------------------------------------- #
        pal = res["palette"] or [str(h) for h in fallback_pal]
        if not pal:
            raise RuntimeError("no print files and no fallback palette for %s" % version)
        res["palette"] = pal
        res["palette_source"] = "fallback"
        thickness = res["thickness_mm"] or 1.2
        dia = cfg.get("print", {}).get("print_dia_mm", 86.4)
        blank = os.path.join(ROOT, "appearance", "build", "shell", "print_blank.stl")
        if os.path.exists(blank):
            tris = read_stl_triangles_mm(blank)
            res["bbox_mm"] = triangles_bbox_mm(tris)
            if res["bbox_mm"]:
                thickness = res["bbox_mm"][1][2] - res["bbox_mm"][0][2]
            res["thickness_mm"] = thickness
            for i, hx in enumerate(pal):
                band = split_triangles_by_radius(tris, len(pal))[i]
                res["objects"].append({"name": "PRINT_%s_%02d" % (art.upper(), i),
                                       "tris": band, "hex": hx, "file": None})
            res["source"] = "placeholder_print_blank"
            res["warnings"].append("print_blank.stl split into %d radial colour bands "
                                   "(placeholder; re-run when Kromacut print lands)" % len(pal))
        else:
            n = len(pal)
            r_out = dia / 2.0
            for i, hx in enumerate(pal):
                ring = (r_out * i / n, r_out * (i + 1) / n, 0.0, thickness, 160)
                res["objects"].append({"name": "PRINT_%s_%02d" % (art.upper(), i),
                                       "ring": ring, "hex": hx, "file": None})
            res["source"] = "placeholder_synthetic"
            res["bbox_mm"] = ((-dia / 2, -dia / 2, 0.0), (dia / 2, dia / 2, thickness))
            res["warnings"].append("no Kromacut print and no print_blank.stl; "
                                   "synthetic %d-ring placeholder disc \u00d886.4 x %.2f mm"
                                   % (n, thickness))
    return res


# --------------------------------------------------------------------------- #
# assembly parts
# --------------------------------------------------------------------------- #
def _resolve_part_stl(version, name):
    mech = VERSIONS[version]["mech"]
    p = os.path.join(ROOT, "mechanical", mech, "build", "parts", name + "_v01.stl")
    if os.path.exists(p):
        return p
    alt = os.path.join(ROOT, "mechanical", mech, "build", "parts", name + ".stl")
    if os.path.exists(alt):
        return alt
    return None


def _parts_from_parts_json(version):
    p = os.path.join(ROOT, "appearance", "build", "shell", "parts.json")
    data = _load_json(p)
    if not data:
        return None
    sub = _select_version(data, version)
    if sub is data and not any(k in data for k in (version, VERSIONS[version]["mech"])):
        # maybe {"square": [...], "round": [...]}
        sub = data.get(version) or data.get(VERSIONS[version]["mech"])
    if sub is None:
        return None
    out = []
    items = None
    if isinstance(sub, dict):
        for key in ("parts", "internal_parts", "assembly_parts", "items"):
            if isinstance(sub.get(key), (list, dict)):
                items = sub[key]
                break
    elif isinstance(sub, list):
        items = sub
    if isinstance(items, dict):
        items = [dict(name=k, **(v if isinstance(v, dict) else {"path": v}))
                 for k, v in items.items()]
    if not isinstance(items, list):
        return None
    for ent in items:
        if isinstance(ent, str):
            out.append({"name": ent, "path": None})
        elif isinstance(ent, dict):
            name = ent.get("name") or ent.get("part")
            if not name:
                continue
            # shell-cad's parts.json uses mechanical part names + render flags
            if ent.get("use_in_render") is False or ent.get("legacy") is True:
                continue
            if ent.get("stl_exists") is False:
                continue
            if name.endswith("_v01"):
                name = name[:-4]
            path = None
            for k in ("path", "stl", "file"):
                if isinstance(ent.get(k), str):
                    path = ent[k]
                    break
            out.append({"name": name, "path": path})
    return out or None


def resolve_assembly(version, cfg=None):
    """Resolve parts + plate + shell params + print for one version."""
    cfg = cfg or load_config()
    if version not in VERSIONS:
        raise SystemExit("unknown version %r (use round|square)" % version)
    mech = VERSIONS[version]["mech"]
    warps = {"warnings": [], "mismatches": [], "notes": []}

    # ---- shell parameters ------------------------------------------------ #
    fb = cfg.get("shell_fallback", {}).get(version, {})
    sj_path = shell_json_path(version)
    raw = _load_json(sj_path) if sj_path else None
    raw_v = _select_version(raw, version) if raw is not None else None

    pocket_dia = deep_find(raw_v, ("pocket_diameter_mm", "pocket_dia_mm",
                                   "recess_diameter_mm", "pocket_d_mm",
                                   "recess_dia_mm"))
    rim_z = deep_find(raw_v, ("rim_z_mm", "rim_z", "top_rim_z_mm",
                              "plate_top_z_mm", "top_z_mm"))
    floor_z = deep_find(raw_v, ("floor_z_mm", "floor_z", "pocket_floor_z_mm",
                                "print_bottom_z_mm", "recess_floor_z_mm"))
    pocket_depth = deep_find(raw_v, ("pocket_depth_mm", "recess_depth_mm", "depth_mm"))
    intf = deep_find(raw_v, ("interference_radial_mm", "radial_interference_mm",
                             "interference_mm", "nominal_interference_mm"))
    top_gap = deep_find(raw_v, ("top_gap_mm", "below_rim_mm", "print_top_gap_mm",
                                "top_step_mm", "clearance_top_mm"))
    print_dia = deep_find(raw_v, ("print_diameter_mm", "print_dia_mm",
                                  "art_diameter_mm"))
    print_thk_shell = deep_find(raw_v, ("print_thickness_mm", "slab_thickness_mm",
                                        "art_thickness_mm"))

    shell_source = "shell.json" if raw_v is not None else "fallback"
    if raw_v is None:
        warps["warnings"].append("appearance/build/shell/shell.json not found; "
                                 "using provisional fallback shell params")

    rim_z = rim_z or fb.get("rim_z_mm")
    pocket_dia = pocket_dia or fb.get("pocket_dia_mm") or cfg.get("print", {}).get("pocket_dia_mm", 86.0)
    print_dia = print_dia or cfg.get("print", {}).get("print_dia_mm", 86.4)
    intf = intf if intf is not None else cfg.get("print", {}).get("interference_mm", 0.2)
    top_gap = top_gap if top_gap is not None else cfg.get("print", {}).get("top_gap_mm", 0.05)
    fallback_thk = fb.get("thickness_mm") or print_thk_shell or 1.2

    # ---- print (manifest drives the real thickness) ---------------------- #
    pr = load_print(version, cfg, fallback_thickness=fallback_thk)
    warps["warnings"].extend(pr["warnings"])
    thickness = pr["thickness_mm"] or fallback_thk

    if floor_z is None:
        floor_z = (rim_z or fb.get("rim_z_mm", 0.0)) - thickness - top_gap
        warps["notes"].append("floor z derived as rim - print thickness - top gap = %.3f" % floor_z)
    elif rim_z is not None:
        derived = rim_z - thickness - top_gap
        if abs(derived - floor_z) > 0.02:
            warps["mismatches"].append(
                "shell.json floor_z=%.3f but rim(%.2f) - print_thickness(%.2f) - "
                "top_gap(%.2f) = %.3f  (print top would be %.3f vs rim %.3f, "
                "delta %+.3f mm)" % (floor_z, rim_z, thickness, top_gap, derived,
                                     floor_z + thickness, rim_z,
                                     (floor_z + thickness) - rim_z))
    if print_thk_shell is not None and abs(print_thk_shell - thickness) > 0.02:
        warps["mismatches"].append(
            "shell.json print_thickness=%.2f mm vs manifest/actual print thickness=%.2f mm"
            % (print_thk_shell, thickness))
    if pocket_dia is not None and print_dia is not None:
        real_intf = (print_dia - pocket_dia) / 2.0
        if abs(real_intf - intf) > 0.015:
            warps["mismatches"].append(
                "interference mismatch: (print \u00d8%.2f - pocket \u00d8%.2f)/2 = %.3f mm "
                "vs nominal %.2f mm" % (print_dia, pocket_dia, real_intf, intf))

    # ---- plate ----------------------------------------------------------- #
    plate_path = os.path.join(ROOT, "appearance", "build", "shell", version,
                              "plate_recessed.stl")
    plate_fallback = os.path.join(ROOT, "mechanical", mech, "build", "parts", "plate_v01.stl")
    plate = {"path": plate_path, "proxy": False, "source": "recessed",
             "fallback_path": plate_fallback}
    if not os.path.exists(plate_path):
        plate.update(path=plate_fallback if os.path.exists(plate_fallback) else None,
                     proxy=True, source="fallback_plate_v01_boolean")
        warps["warnings"].append(
            "recessed plate missing for %s; using %s with a render-time boolean "
            "pocket proxy (render/3MF provisional)" % (version, os.path.basename(plate_fallback)))
    elif not os.path.exists(plate_path):
        warps["warnings"].append("plate STL missing for %s" % version)

    # ---- shell assembly parts -------------------------------------------- #
    pj = _parts_from_parts_json(version)
    if pj:
        entries = pj
        warps["notes"].append("assembly part list from appearance/build/shell/parts.json")
        explicit = True
    else:
        names = SQUARE_PARTS if version == "square" else ROUND_PARTS
        entries = [{"name": n, "path": None} for n in names]
        explicit = False
    parts = []
    for ent in entries:
        name = ent["name"]
        if name in EXCLUDE_PARTS:
            warps["notes"].append("excluded legacy light part %r (docs/13)" % name)
            continue
        p = ent.get("path")
        if p:
            if not os.path.isabs(p):
                p = os.path.join(ROOT, p)
        else:
            p = _resolve_part_stl(version, name)
        if not p or not os.path.exists(p):
            warps["warnings"].append("assembly part %r STL not found (skipped)" % name)
            continue
        parts.append({"name": name, "path": p})
    missing_default = [n for n in (SQUARE_PARTS if version == "square" else ROUND_PARTS)
                       if not any(x["name"] == n for x in parts)]
    if missing_default:
        warps["notes"].append("parts named in the task spec but absent on disk for %s: %s"
                              % (version, ", ".join(missing_default)))
    extra = [x["name"] for x in parts
             if x["name"] not in (SQUARE_PARTS if version == "square" else ROUND_PARTS)]
    if extra:
        warps["notes"].append("extra assembly parts included for %s: %s"
                             % (version, ", ".join(extra)))

    spec = {
        "version": version,
        "mech": mech,
        "art": VERSIONS[version]["art"],
        "label": VERSIONS[version]["label"],
        "tag": VERSIONS[version]["tag"],
        "config": cfg,
        "shell": {"source": shell_source, "shell_json": sj_path,
                  "pocket_dia_mm": pocket_dia, "print_dia_mm": print_dia,
                  "rim_z_mm": rim_z, "floor_z_mm": floor_z,
                  "pocket_depth_mm": pocket_depth, "interference_mm": intf,
                  "top_gap_mm": top_gap, "print_thickness_mm": thickness},
        "plate": plate,
        "parts": parts,
        "print": pr,
        "warnings": warps["warnings"],
        "mismatches": warps["mismatches"],
        "notes": warps["notes"],
    }
    return spec


# --------------------------------------------------------------------------- #
# STL / mesh helpers (mm)
# --------------------------------------------------------------------------- #
def read_stl_triangles_mm(path):
    """Read a binary or ASCII STL -> (n,3,3) float array (or list of tuples) in mm."""
    with open(path, "rb") as fh:
        head = fh.read(84)
        if len(head) < 84:
            raise ValueError("STL too short: %s" % path)
        n = struct.unpack("<I", head[80:84])[0]
        is_binary = (os.path.getsize(path) == 84 + n * 50)
        if not is_binary:
            fh.seek(0)
            return _read_ascii_stl(fh)
        raw = fh.read(n * 50)
    if _np is not None:
        arr = _np.frombuffer(raw, dtype=_np.uint8).reshape(n, 50)
        tris = arr[:, 12:48].copy().view("<f4").reshape(n, 3, 3)
        return tris.astype(_np.float64)
    tris = []
    for i in range(n):
        off = i * 50 + 12
        vals = struct.unpack("<9f", raw[off:off + 36])
        tris.append(((vals[0], vals[1], vals[2]),
                     (vals[3], vals[4], vals[5]),
                     (vals[6], vals[7], vals[8])))
    return tris


def _read_ascii_stl(fh):
    tris, cur = [], []
    for line in fh.read().decode("utf-8", "replace").splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            cur.append(tuple(float(x) for x in line.split()[1:4]))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    return tris


def triangles_bbox_mm(tris):
    if tris is None or len(tris) == 0:
        return None
    if _np is not None and isinstance(tris, _np.ndarray):
        v = tris.reshape(-1, 3)
        return (tuple(float(x) for x in v.min(0)),
                tuple(float(x) for x in v.max(0)))
    lo = [min(t[k][i] for t in tris for k in range(3)) for i in range(3)]
    hi = [max(t[k][i] for t in tris for k in range(3)) for i in range(3)]
    return (tuple(lo), tuple(hi))


def split_triangles_by_radius(tris, nbands):
    """Split triangle soup into n equal radial bands by centroid radius (mm)."""
    if tris is None or len(tris) == 0 or nbands <= 0:
        return []
    if _np is not None and isinstance(tris, _np.ndarray):
        c = tris.mean(axis=1)
        r = _np.hypot(c[:, 0], c[:, 1])
        rmax = float(r.max()) if len(r) else 0.0
        if rmax <= 0:
            return [tris] + [_np.empty((0, 3, 3)) for _ in range(nbands - 1)]
        idx = _np.minimum(nbands - 1, (r / rmax * nbands).astype(int))
        return [tris[idx == i] for i in range(nbands)]
    rmax = max(math.hypot(t[0][0], t[0][1]) for t in tris)
    if rmax <= 0:
        return [list(tris)] + [[] for _ in range(nbands - 1)]
    groups = [[] for _ in range(nbands)]
    for t in tris:
        cx = sum(v[0] for v in t) / 3.0
        cy = sum(v[1] for v in t) / 3.0
        r = math.hypot(cx, cy)
        idx = min(nbands - 1, int(r / rmax * nbands))
        groups[idx].append(t)
    return groups


def make_annulus(r_in, r_out, z0, z1, segments=160):
    """Return (verts, tris) for a closed annular slab in mm (r_in may be 0)."""
    verts, tris = [], []
    n = max(8, int(segments))
    inner = r_in > 1e-9

    def add(v):
        verts.append(v)
        return len(verts) - 1

    # vertex rings: bottom/top x (inner/outer)
    for z in (z0, z1):
        if inner:
            for i in range(n):
                a = 2.0 * math.pi * i / n
                verts.append((r_in * math.cos(a), r_in * math.sin(a), z))
        else:
            verts.append((0.0, 0.0, z))          # centre vertex
    if inner:
        for z in (z0, z1):
            for i in range(n):
                a = 2.0 * math.pi * i / n
                verts.append((r_out * math.cos(a), r_out * math.sin(a), z))
    else:
        for i in range(n):
            a = 2.0 * math.pi * i / n
            verts.append((r_out * math.cos(a), r_out * math.sin(a), z0))
        for i in range(n):
            a = 2.0 * math.pi * i / n
            verts.append((r_out * math.cos(a), r_out * math.sin(a), z1))
    # index helpers
    if inner:
        ib = lambda i: i
        it = lambda i: n + i
        ob = lambda i: 2 * n + i
        ot = lambda i: 3 * n + i
    else:
        cb = 0
        ct = 1
        ob = lambda i: 2 + i
        ot = lambda i: 2 + n + i

    for i in range(n):
        j = (i + 1) % n
        # top (+z)
        if inner:
            tris.append((it(i), ot(i), ot(j)))
            tris.append((it(i), ot(j), it(j)))
        else:
            tris.append((ct, ot(i), ot(j)))
        # bottom (-z)
        if inner:
            tris.append((ib(i), ib(j), ob(j)))
            tris.append((ib(i), ob(j), ob(i)))
        else:
            tris.append((cb, ob(j), ob(i)))
        # outer wall
        tris.append((ob(i), ob(j), ot(j)))
        tris.append((ob(i), ot(j), ot(i)))
        # inner wall (inward normal)
        if inner:
            tris.append((ib(i), it(i), it(j)))
            tris.append((ib(i), it(j), ib(j)))
    return verts, tris


def print_object_mesh(obj, dedupe=True):
    """Return (verts, tris) in mm for a resolved print object (real/band/ring)."""
    if obj.get("path"):
        return _tri_soup_to_mesh(read_stl_triangles_mm(obj["path"]), dedupe=dedupe)
    if obj.get("tris") is not None:
        return _tri_soup_to_mesh(obj["tris"], dedupe=dedupe)
    if obj.get("ring") is not None:
        r_in, r_out, z0, z1, seg = obj["ring"]
        return make_annulus(r_in, r_out, z0, z1, seg)
    raise ValueError("print object has no mesh source: %r" % (obj,))


def _tri_soup_to_mesh(tris, dedupe=True):
    """Triangles -> (vertices, triangle index triples) with welded vertices.

    dedupe=True also drops degenerate and exact-duplicate triangles; this is a
    *display/placeholder* default only. The 3MF writer must call with
    dedupe=False: coincident opposite-winding interface caps between abutting
    Kromacut layout parts are what keep each per-filament solid closed, so the
    exported component must keep the STL triangle set exactly.
    """
    if tris is None or len(tris) == 0:
        return [], []
    if _np is not None and isinstance(tris, _np.ndarray):
        flat = tris.reshape(-1, 3)
        key = _np.round(flat, 6)
        uniq, inverse = _np.unique(key, axis=0, return_inverse=True)
        # keep the unrounded coordinate of a representative vertex
        verts = _np.zeros_like(uniq)
        verts[inverse] = flat
        faces = inverse.reshape(-1, 3).astype(_np.int64)
        if not dedupe:
            return verts, faces
        # drop degenerate triangles (two welded vertices collapse)
        ok = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & \
             (faces[:, 0] != faces[:, 2])
        faces = faces[ok]
        # drop exact duplicate triangles (display only)
        if len(faces):
            fkey = _np.sort(faces, axis=1)
            _, first = _np.unique(fkey, axis=0, return_index=True)
            faces = faces[_np.sort(first)]
        return verts, faces
    verts, idx, tris_out = [], {}, []
    for t in tris:
        face = []
        for v in t:
            key = (round(float(v[0]), 6), round(float(v[1]), 6), round(float(v[2]), 6))
            i = idx.get(key)
            if i is None:
                i = len(verts)
                idx[key] = i
                verts.append(v)
            face.append(i)
        tris_out.append(tuple(face))
    return verts, tris_out


def mesh_stats(verts, tris):
    if _np is not None and isinstance(verts, _np.ndarray):
        lo = [float(x) for x in verts.min(0)]
        hi = [float(x) for x in verts.max(0)]
    else:
        lo = [min(v[i] for v in verts) for i in range(3)]
        hi = [max(v[i] for v in verts) for i in range(3)]
    return {"verts": len(verts), "tris": len(tris), "bbox_mm": (tuple(lo), tuple(hi))}
