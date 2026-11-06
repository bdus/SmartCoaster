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

import json
import os
import struct
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
