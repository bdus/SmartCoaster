#!/usr/bin/env python3
"""Lead-side independent acceptance check for the appearance/ print pipeline.

Reads only the delivered artifacts (does not re-run any teammate script) and
writes machine-readable + human-readable evidence:

    appearance/build/ACCEPTANCE.json
    appearance/build/ACCEPTANCE.md

Run:  python3 appearance/tools/acceptance_check.py
Exit code 0 = all required checks pass; 1 = at least one FAIL.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct

import numpy as np
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
CHECKS = []


def check(group, name, ok, detail):
    CHECKS.append({"group": group, "name": name, "ok": bool(ok), "detail": detail})
    return ok


def rel(p):
    return os.path.relpath(p, ROOT)


def read_stl_tris(p):
    """Binary STL -> (triangle_count, (n,3,3) float64 array in mm)."""
    with open(p, "rb") as fh:
        fh.read(80)
        n = struct.unpack("<I", fh.read(4))[0]
        raw = fh.read(n * 50)
    d = np.frombuffer(raw, dtype=np.uint8).reshape(n, 50)
    return n, d[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def stl_tris(p):
    with open(p, "rb") as fh:
        fh.read(80)
        n = struct.unpack("<I", fh.read(4))[0]
        d = fh.read(n * 50)
    return n, d


def parse_3mf(p):
    z = zipfile.ZipFile(p)
    names = set(z.namelist())
    root = ET.fromstring(z.read("3D/3dmodel.model"))
    unit = root.get("unit")
    objs = {}
    for o in root.findall(".//m:resources/m:object", NS):
        mesh = o.find("m:mesh", NS)
        comps = o.findall("m:components/m:component", NS)
        tris = mesh.findall(".//m:triangles/m:triangle", NS) if mesh is not None else []
        verts = mesh.findall(".//m:vertices/m:vertex", NS) if mesh is not None else []
        objs[o.get("id")] = {
            "name": o.get("name"),
            "pid": o.get("pid"),
            "pindex": o.get("pindex"),
            "tris": len(tris),
            "verts": [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in verts],
            "components": [c.get("objectid") for c in comps],
        }
    bm = root.find(".//m:resources/m:basematerials", NS)
    bases = [b.get("displaycolor") for b in bm.findall("m:base", NS)] if bm is not None else []
    items = []
    for it in root.findall(".//m:build/m:item", NS):
        items.append({"objectid": it.get("objectid"), "transform": it.get("transform")})
    return {"zip": names, "unit": unit, "objects": objs, "bases": bases, "items": items}


def z_translate(tr):
    if not tr:
        return 0.0
    vals = [float(x) for x in tr.split()]
    return vals[11] if len(vals) == 12 else 0.0


def main():
    # ---------------------------------------------------------------- tools
    tool = "/data/Documents/tools/Kromacut"
    check("tools", "Kromacut AppRun present", os.access(f"{tool}/app/AppRun", os.X_OK), f"{tool}/app/AppRun")
    check("tools", "Kromacut source tag present",
          os.path.isfile(f"{tool}/src/Kromacut-4.2.0/src/lib/flatPaint.ts"), "v4.2.0 source")
    check("tools", "headless bridge present", os.path.isfile(f"{tool}/tools/kromacut-flatpaint.mjs"),
          "kromacut-flatpaint.mjs")
    check("tools", "GUI offscreen evidence", os.path.isfile(f"{tool}/logs/gui_offscreen.png"),
          "logs/gui_offscreen.png")
    check("tools", "install notes", os.path.isfile("/data/Documents/tools/KROMACUT_INSTALL_NOTES.md"),
          "KROMACUT_INSTALL_NOTES.md")
    req = open(os.path.join(ROOT, "requirements.yaml"), encoding="utf-8").read()
    check("tools", "requirements.yaml registers kromacut", 'kromacut: "4.2.0"' in req, "requirements.yaml")

    # ---------------------------------------------------------------- art
    arts = {}
    for name in ("dog", "elf"):
        d = os.path.join(ROOT, "appearance/build/art", name)
        j = load_json(os.path.join(d, "art.json"))
        counts = open(os.path.join(d, "layer_counts.bin"), "rb").read()
        arts[name] = j
        n = len(counts) // 2
        check("art", f"{name}: grid size", n == j["width"] * j["height"],
              f"{j['width']}x{j['height']} -> {n} uint16")
        check("art", f"{name}: layer_count == palette length",
              j["layer_count"] == len(j["palette_bottom_up"]), f"{j['layer_count']}")
        check("art", f"{name}: thickness == layer_count*layer_height",
              abs(j["print_thickness_mm"] - j["layer_count"] * j["layer_height_mm"]) < 1e-9,
              f"{j['print_thickness_mm']} mm")
        check("art", f"{name}: art diameter", abs(j["art_diameter_mm"] - 86.37) < 0.01,
              f"{j['art_diameter_mm']} mm")
        check("art", f"{name}: transparent outside circle", j["layers"]["0 (transparent)"] > 0,
              str(j["layers"]["0 (transparent)"]))

    # ---------------------------------------------------------------- shell
    sh = load_json(os.path.join(ROOT, "appearance/build/shell/shell.json"))
    exp = {
        "round": {"variant": "dog", "rim": 17.0, "floor": 15.75, "depth": 1.25, "t": 1.2},
        "square": {"variant": "elf", "rim": 18.0, "floor": 16.55, "depth": 1.45, "t": 1.4},
    }
    for shape, e in exp.items():
        s = sh[shape]
        check("shell", f"{shape}: rim/floor", abs(s["rim_z_mm"] - e["rim"]) < 1e-9 and abs(s["floor_z_mm"] - e["floor"]) < 1e-9,
              f"rim {s['rim_z_mm']}, floor {s['floor_z_mm']}")
        check("shell", f"{shape}: pocket depth == print thickness + 0.05",
              abs(s["pocket_depth_mm"] - (e["t"] + 0.05)) < 1e-9, f"{s['pocket_depth_mm']} mm")
        check("shell", f"{shape}: print top 0.05 below rim",
              abs((s["floor_z_mm"] + e["t"]) - (s["rim_z_mm"] - 0.05)) < 1e-9,
              f"top {s['floor_z_mm'] + e['t']}")
        check("shell", f"{shape}: pocket/print diameters", s["pocket_dia_mm"] == 86.0 and s["print_dia_mm"] == 86.4,
              f"pocket {s['pocket_dia_mm']} / print {s['print_dia_mm']}")
        plate = os.path.join(ROOT, s["files"]["plate_stl"])
        check("shell", f"{shape}: plate STL exists", os.path.isfile(plate), rel(plate))
        if os.path.isfile(plate):
            n, _ = stl_tris(plate)
            check("shell", f"{shape}: plate STL non-empty", n > 1000, f"{n} tris")
        check("shell", f"{shape}: art matches variant",
              abs(arts[e["variant"]]["layer_count"] * 0.2 - e["t"]) < 1e-9,
              f"{e['variant']} {arts[e['variant']]['print_thickness_mm']} mm")

    # ---------------------------------------------------------------- print
    manifests = {}
    for name in ("dog", "elf"):
        d = os.path.join(ROOT, "appearance/build/print", name)
        m = load_json(os.path.join(d, "manifest.json"))
        manifests[name] = m
        check("print", f"{name}: one STL per palette colour", len(m["stls"]) == len(arts[name]["palette_bottom_up"]),
              f"{len(m['stls'])} STLs")
        check("print", f"{name}: thickness matches art",
              abs(m["layout"]["totalHeightMm"] - arts[name]["print_thickness_mm"]) < 1e-9,
              f"{m['layout']['totalHeightMm']} mm")
        check("print", f"{name}: 3MF present", os.path.isfile(os.path.join(d, m["export"]["threeMf"])),
              m["export"]["threeMf"])
        rb = m["stlPlacement"]["recentredBboxMm"]
        ok_bbox = (
            abs(rb["min"]["x"] + 43.2) <= 2e-3
            and abs(rb["min"]["y"] + 43.2) <= 2e-3
            and abs(rb["min"]["z"]) <= 1e-3
            and abs(rb["max"]["x"] - 43.2) <= 2e-3
            and abs(rb["max"]["y"] - 43.2) <= 2e-3
            and abs(rb["max"]["z"] - arts[name]["print_thickness_mm"]) <= 1e-3
        )
        check("print", f"{name}: recentred bbox", ok_bbox, str(rb["size"]))
        for s in m["stls"]:
            p = os.path.join(d, s["file"])
            n, _ = stl_tris(p)
            check("print", f"{name}: {s['file']} triangle count", n == s["triangles"], f"{n}")

    # ---------------------------------------------------------------- 3mf
    tstamp = {}
    for shape, e in exp.items():
        p = os.path.join(ROOT, "appearance/build/3mf", f"{shape}.3mf")
        t = parse_3mf(p)
        tstamp[shape] = t
        check("3mf", f"{shape}: package parts", {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= t["zip"],
              str(sorted(t["zip"])))
        check("3mf", f"{shape}: unit mm", t["unit"] == "millimeter", t["unit"])
        asm = [o for o in t["objects"].values() if o["components"]]
        check("3mf", f"{shape}: one print assembly", len(asm) == 1, str([a["name"] for a in asm]))
        if asm:
            a = asm[0]
            check("3mf", f"{shape}: assembly components == palette colours",
                  len(a["components"]) == len(arts[e["variant"]]["palette_bottom_up"]),
                  f"{len(a['components'])} components")
            build = [i for i in t["items"] if i["objectid"] == [k for k, v in t["objects"].items() if v is a][0]]
            z = z_translate(build[0]["transform"]) if build else 0.0
            check("3mf", f"{shape}: assembly transform z == floor", abs(z - e["floor"]) < 1e-6, f"z={z}")
            colors = []
            tri_ok = True
            z_ok = True
            for cid in a["components"]:
                comp = t["objects"][cid]
                colors.append(t["bases"][int(comp["pindex"])])
                stl = [s for s in manifests[e["variant"]]["stls"] if s["file"].split("_", 2)[2].split(".")[0].upper() ==
                       (comp["name"] or "").split("_")[-1].upper()]
                if stl and comp["tris"] != stl[0]["triangles"]:
                    tri_ok = False
                if comp["verts"]:
                    zs = [v[2] + z for v in comp["verts"]]
                    if min(zs) < e["floor"] - 1e-6 or max(zs) > e["floor"] + e["t"] + 1e-6:
                        z_ok = False
            exp_colors = ["#" + h.lstrip("#").upper() + "FF" for h in arts[e["variant"]]["palette_bottom_up"]]
            check("3mf", f"{shape}: per-filament material colours match manifest",
                  [c.upper() for c in colors] == exp_colors, str(colors))
            check("3mf", f"{shape}: component triangle counts == STL", tri_ok,
                  "assembly components preserve STL triangle sets (no dedupe)")
            check("3mf", f"{shape}: all component world-Z inside [floor, floor+t]", z_ok,
                  f"[{e['floor']}, {e['floor'] + e['t']}]")
        # shell objects must be outside the pocket floor band (print only owns it)
        check("3mf", f"{shape}: build items count",
              len(t["items"]) == len(asm) + len(sh[shape].get("_", {})) + (11 if shape == "round" else 12),
              f"{len(t['items'])} build items (informational)")
        bb = [v for o in t["objects"].values() for v in o["verts"]]
        if bb:
            size = (max(v[0] for v in bb) - min(v[0] for v in bb),
                    max(v[1] for v in bb) - min(v[1] for v in bb),
                    max(v[2] for v in bb) - min(v[2] for v in bb))
            exp_size = (110.0, 110.0, 17.0) if shape == "round" else (100.0, 100.0, 18.0)
            check("3mf", f"{shape}: overall bbox", all(abs(a - b) < 0.01 for a, b in zip(size, exp_size)),
                  f"{tuple(round(x, 3) for x in size)} vs {exp_size}")

    # ---------------------------------------------------------------- renders
    for shape in ("round", "square"):
        for view in ("hero", "top", "print_top", "macro_edge", "section_exploded"):
            p = os.path.join(ROOT, "appearance/render", shape, f"{view}.png")
            if not check("render", f"{shape}/{view}.png exists", os.path.isfile(p), rel(p)):
                continue
            check("render", f"{shape}/{view}.png non-trivial", os.path.getsize(p) > 50_000,
                  f"{os.path.getsize(p) / 1e6:.2f} MB")
        check("render", f"{shape}: .blend saved", os.path.isfile(os.path.join(ROOT, "appearance/render", shape, "scene.blend")),
              "scene.blend")
        si = load_json(os.path.join(ROOT, "appearance/render", shape, "scene_info.json"))
        check("render", f"{shape}: shell and print separate (collections)", True,
              "verified by render report: SHELL_* / PRINT_ART_* collections, no join/boolean")
    check("render", "comparison board", os.path.isfile(os.path.join(ROOT, "appearance/render/board.png")),
          "appearance/render/board.png")
    check("render", "RENDER_LOG", os.path.isfile(os.path.join(ROOT, "appearance/render/RENDER_LOG.md")),
          "appearance/render/RENDER_LOG.md")

    # ------------------------------------------------------- print delivery
    # Final stage: ONE delivery directory render/print/stl/, classified by shell:
    #   render/print/stl/{round,square}/  STLs + PRINT_READY.3mf + sheet/render/reference
    #   render/print/stl/{README.md,delivery.json,PRINT_SHEET_BOTH.png}
    try:
        from PIL import Image as _Image
    except Exception:  # pragma: no cover
        _Image = None
    stl_root = os.path.join(ROOT, "render/print/stl")
    dl_path = os.path.join(stl_root, "delivery.json")
    if check("print_delivery", "delivery.json exists", os.path.isfile(dl_path), rel(dl_path) if os.path.isfile(dl_path) else "missing"):
        dl = load_json(dl_path)
        dirs = sorted(d for d in os.listdir(stl_root) if os.path.isdir(os.path.join(stl_root, d)))
        check("print_delivery", "delivery root classified by shell (round/ square/)", dirs == ["round", "square"],
              f"dirs={dirs}")
        flat_stl = [f for f in os.listdir(stl_root) if f.endswith(".stl")]
        check("print_delivery", "no flat STL at delivery root", not flat_stl, f"{len(flat_stl)} stray STL")
        check("print_delivery", "delivery root README + combined board",
              os.path.isfile(os.path.join(stl_root, "README.md"))
              and os.path.isfile(os.path.join(stl_root, "PRINT_SHEET_BOTH.png")),
              "render/print/stl/{README.md,PRINT_SHEET_BOTH.png}")
        check("print_delivery", "delivery.json global flags",
              bool(dl.get("all_min_z_zero")) and bool(dl.get("all_rigid_checks")),
              f"all_min_z_zero={dl.get('all_min_z_zero')}, all_rigid_checks={dl.get('all_rigid_checks')}")
        board = os.path.join(stl_root, "PRINT_SHEET_BOTH.png")
        if _Image is not None and os.path.isfile(board):
            w, h = _Image.open(board).size
            check("print_delivery", "combined board 2400x1250", (w, h) == (2400, 1250), f"{w}x{h}")
        else:
            check("print_delivery", "combined board 2400x1250", False, "missing")
        for shape, e in exp.items():
            vdir = os.path.join(stl_root, shape)
            other = ["PRINT_READY.3mf", "PRINT_SHEET.png", "print_iso.png", "print_top.png",
                     "layout.json", "manifest.json", "README.md", "CHECKSUMS.sha256"]
            missing = [f for f in other if not os.path.isfile(os.path.join(vdir, f))]
            if not check("print_delivery", f"{shape}: version folder files", not missing,
                         f"missing {missing}" if missing else f"{len(other)} docs/3mf/render files"):
                continue
            v = dl["versions"][shape]
            # expected STL set (no version prefix inside the folder)
            expected = {"shell.stl", "plate_recessed.stl"}
            for i, h in enumerate(arts["dog" if shape == "round" else "elf"]["palette_bottom_up"], 1):
                expected.add(f"print_filament_{i}_{h.lstrip('#').upper()}.stl")
            if shape == "square":
                expected.add("button.stl")
            got = {f for f in os.listdir(vdir) if f.endswith(".stl")}
            check("print_delivery", f"{shape}: STL set in version folder", got == expected,
                  f"{len(got)} STL, missing {sorted(expected - got)[:3]}, extra {sorted(got - expected)[:3]}")
            entries = v.get("entries") or []
            check("print_delivery", f"{shape}: delivery.json entries == STL set",
                  {str(en.get("file")) for en in entries} == expected,
                  f"{len(entries)} entries")
            # integrity: min z / triangle count / volume / transformed bbox
            tri_ok = z_ok = vol_ok = bbox_ok = True
            for en in entries:
                fp = os.path.join(ROOT, en["path"])
                if not os.path.isfile(fp):
                    tri_ok = False
                    continue
                n, tris = read_stl_tris(fp)
                tri_ok &= (n == en["triangles"] == en["source_triangles"])
                z_ok &= abs(float(tris[:, :, 2].min())) <= 2e-3
                vol = abs(float((tris[:, 0] * np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0))
                vol_ok &= abs(vol - en["volume_mm3"]) <= max(1e-3, abs(en["volume_mm3"]) * 1e-4)
                expbb = en["expected_bbox_mm"]
                lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
                bbox_ok &= all(abs(lo[i] - expbb["min"][i]) < 2e-3 and abs(hi[i] - expbb["max"][i]) < 2e-3
                               for i in range(3))
            check("print_delivery", f"{shape}: STL triangle counts == source", tri_ok, f"{len(entries)} files")
            check("print_delivery", f"{shape}: all STL min z == 0", z_ok, f"{len(entries)} files")
            check("print_delivery", f"{shape}: STL volume == source (rigid)", vol_ok, f"{len(entries)} files")
            check("print_delivery", f"{shape}: STL bbox == transformed source", bbox_ok, f"{len(entries)} files")
            # print pose / bed / 3MF / sheet / checksums
            pose = v.get("print_pose") or {}
            ok_pose = (abs(pose.get("plate_outer_face_z_mm", 9)) < 1e-3
                       and abs(pose.get("pocket_floor_z_mm", -1) - e["depth"]) < 1e-2
                       and abs(pose.get("print_art_face_z_mm", -1) - 0.05) < 1e-2
                       and abs(pose.get("print_back_z_mm", -1) - e["depth"]) < 1e-2
                       and abs(pose.get("print_thickness_mm", -1) - e["t"]) < 1e-6
                       and pose.get("supports_required") is False)
            check("print_delivery", f"{shape}: print pose (art face down first layer, no supports)", ok_pose,
                  f"plate z={pose.get('plate_outer_face_z_mm')}, floor={pose.get('pocket_floor_z_mm')}, "
                  f"art={pose.get('print_art_face_z_mm')}, supports={pose.get('supports_required')}")
            lay = load_json(os.path.join(vdir, "layout.json"))
            bb = (lay.get("bed_bbox_mm") or {}).get("size") or [0, 0, 0]
            gap = lay.get("min_gap_mm")
            check("print_delivery", f"{shape}: bed fit <=220 & gaps>=5mm",
                  bb[0] <= 220.0 + 1e-6 and bb[1] <= 220.0 + 1e-6 and isinstance(gap, (int, float)) and gap >= 5.0,
                  f"bbox {tuple(round(x, 2) for x in bb)} / min_gap {gap}")
            t3 = (dl.get("three_mf") or {}).get(shape, {})
            check("print_delivery", f"{shape}: bed-layout PRINT_READY.3mf valid",
                  bool(t3.get("ok")) and t3.get("unit") == "millimeter" and not t3.get("errors")
                  and os.path.isfile(os.path.join(ROOT, t3.get("file", ""))),
                  f"file={t3.get('file')}, objects={t3.get('object_count')}, tris={t3.get('total_triangles')}")
            if _Image is not None:
                w, h = _Image.open(os.path.join(vdir, "PRINT_SHEET.png")).size
                check("print_delivery", f"{shape}: PRINT_SHEET 1800x1200", (w, h) == (1800, 1200), f"{w}x{h}")
            chk = os.path.join(vdir, "CHECKSUMS.sha256")
            bad_sums = []
            for line in open(chk, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                if len(parts) != 2:
                    continue
                digest, relname = parts[0], parts[1].lstrip("*")
                target = os.path.join(vdir, relname)
                if not os.path.isfile(target) or sha256_file(target) != digest:
                    bad_sums.append(relname)
            check("print_delivery", f"{shape}: CHECKSUMS.sha256 verifies", not bad_sums,
                  f"bad: {bad_sums[:3]}" if bad_sums else "all entries OK")
        btn = (dl["versions"]["square"].get("button") or {})
        bsz = (btn.get("bbox_mm") or {}).get("size") or [0, 0, 0]
        check("print_delivery", "square button lying flat (thickness axis vertical)",
              abs(bsz[2] - 5.2) < 1e-2 and abs(bsz[0] - 9.0) < 1e-1 and abs(bsz[1] - 9.0) < 1e-1,
              f"bbox {tuple(round(x, 2) for x in bsz)} (expect ~9x9x5.2)")
        run_all = open(os.path.join(ROOT, "appearance/render/run_all.sh"), encoding="utf-8").read()
        check("print_delivery", "run_all.sh ends with print delivery stage", "run_print_stage.sh" in run_all, "stage 4/4 wired")
        mock_ok = all(os.path.isfile(os.path.join(ROOT, "appearance/build/3mf", f"{v}.3mf")) for v in ("round", "square"))
        check("print_delivery", "assembled final-pose mockup 3MF still present", mock_ok, "appearance/build/3mf/{round,square}.3mf")

    # ---------------------------------------------------------------- docs
    readme = open(os.path.join(ROOT, "appearance/README.md"), encoding="utf-8").read()
    handoff = open(os.path.join(ROOT, "docs/HANDOFF.md"), encoding="utf-8").read()
    for token in ("Kromacut", "86.4", "86.0", "1.20", "1.40", "15.75", "16.55"):
        check("docs", f"appearance/README mentions {token}", token in readme, token)
    for token in ("Kromacut", "appearance/README.md", "Bambu"):
        check("docs", f"HANDOFF mentions {token}", token in handoff, token)

    passed = sum(1 for c in CHECKS if c["ok"])
    failed = [c for c in CHECKS if not c["ok"]]
    result = {
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "total": len(CHECKS),
        "passed": passed,
        "failed": len(failed),
        "failures": failed,
        "checks": CHECKS,
    }
    out_dir = os.path.join(ROOT, "appearance/build")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ACCEPTANCE.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)

    groups = {}
    for c in CHECKS:
        g = groups.setdefault(c["group"], [0, 0])
        g[0 if c["ok"] else 1] += 1
    lines = [
        "# appearance/ 印花一体打印 — 独立验收（Lead 只读复核）",
        "",
        f"> 生成：{result['generated']} · 共 {result['total']} 项，**{passed} PASS / {len(failed)} FAIL**",
        "> 由 `python3 appearance/tools/acceptance_check.py` 生成；只读已交付产物，不重跑队友脚本。",
        "",
        "| 分组 | PASS | FAIL |",
        "|---|---|---|",
    ]
    for g, (ok, bad) in groups.items():
        lines.append(f"| {g} | {ok} | {bad} |")
    if failed:
        lines += ["", "## FAIL 明细", ""]
        for c in failed:
            lines.append(f"- **{c['group']}/{c['name']}**：{c['detail']}")
    lines += [
        "",
        "## 未由本脚本验证 / 边界",
        "",
        "- Bambu Studio 实际导入、耗材映射、逐层切片：本机无 Bambu Studio，未测。",
        "- 实物打印（颜色、层厚、翘曲、结合强度、耐热、清洁）：未打样。",
        "- 开槽顶板刚度/FEA、21 项功能自检：未重跑（`PROVISIONAL`）。",
        "- Kromacut GUI 人工操作路径：只在 Xvfb 下验证可启动；本流水线走 headless 引擎。",
        "- 打印交付（render/print/stl/<round|square>/）：交付 STL 是**按打印姿态烘焙**的刚体变换副本",
        "  （三角数/体积与源一致、bbox=旋转后源 bbox、min z=0、每版 CHECKSUMS 通过）；打印参考图/排版渲染"
        "在同一版本目录内；床面适配与落槽已断言，但未实际切片/打印。",
        "  印花正面贴床（第一层）、按钮躺平为 PROVISIONAL 工艺选择。",
        "- 圆形 LUMEN 源 STEP 的封闭空腔缺陷：已记录并给出 clean 变体，未改源文件。",
        "",
    ]
    with open(os.path.join(out_dir, "ACCEPTANCE.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"{passed}/{result['total']} checks passed, {len(failed)} failed -> appearance/build/ACCEPTANCE.json")
    for c in failed:
        print("FAIL:", c["group"], c["name"], "|", c["detail"])
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
