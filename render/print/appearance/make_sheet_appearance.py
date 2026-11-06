#!/usr/bin/env python3
"""Print-delivery reference sheets + manifest/README/board (task-6).

Reads the bed layout/validation (print_layout_appearance.py) and the baked STL
delivery + bed-layout 3MF validation (make_stl_delivery.py, render/print/stl/),
then produces per version:

  render/print/appearance/<v>/PRINT_SHEET.png  1800x1200 reference sheet
  render/print/appearance/<v>/manifest.json    machine-readable manifest
  render/print/appearance/<v>/README.md        human-readable README
and the combined board render/print/appearance/PRINT_SHEET_APPEARANCE.png.

The sheet states the corrected physics: plate+print are printed TOP-FACE-DOWN
(recess down, art face = first layer on the bed, back visible in the sliced
orientation), no supports needed; the button lies flat like a coin; after printing
the part is flipped over.  A post-flip appearance render is included for context.

Run:  python3 render/print/appearance/make_sheet_appearance.py
"""
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "appearance", "render"))
import scene_common as SC  # noqa: E402

BG = (21, 23, 27)
FG = (232, 236, 242)
MUT = (150, 158, 172)
ACC = (140, 120, 230)
WARN = (255, 170, 120)
GREEN = (130, 220, 170)
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SHEET_W, SHEET_H = 1800, 1200
STL_DIR = os.path.join(ROOT, "render", "print", "stl")


def F(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def wrap(draw, text, font, maxw):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= maxw:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def load_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_art(version):
    spec = SC.resolve_assembly(version)
    art = spec["art"]
    m = load_json(os.path.join(ROOT, "appearance", "build", "print", art,
                               "manifest.json"))
    opaque = int(m["art"]["stats"]["opaquePixels"])
    face = {int(p["classIndex"]): int(p["activePixels"])
            for p in m["layout"]["parts"] if p["kind"] == "face"}
    fils = []
    for st in sorted(m["stls"], key=lambda s: int(s["filamentIndex"])):
        n = int(st["filamentIndex"])
        fils.append({"number": n,
                     "hex": "#" + str(st["hex"]).lstrip("#").upper(),
                     "triangles": int(st["triangles"]),
                     "share_pct": round(100.0 * face.get(n, 0) / opaque, 1)})
    return spec, m, fils


def slicer_settings(nfil, version):
    return {
        "layer_height_mm": 0.2,
        "nozzle_mm": 0.4,
        "line_width_mm": 0.45,
        "walls": 2,
        "top_bottom_layers": "4 / 3",
        "infill_pct": 15,
        "supports": "NONE for route A (plate original top face + print art face are "
                    "the first layer on the bed); button lying flat",
        "brim": "5 mm brim for the button" if version == "square" else "none",
        "ams_slots": "one filament per AMS slot: %d colors -> needs >=%d slots; a "
                     "4-slot AMS requires spool swaps or a second AMS / AMS lite"
                     % (nfil, nfil),
        "first_layer": "0.2 mm; plate outer face on the bed, print art face 0.05 mm "
                       "above the bed by design (same first layer)",
        "note": "PROVISIONAL starting point; not physically tested.",
    }


def routes(version):
    return {
        "A_recommended": {
            "label": "A) 推荐 · 顶板+印花整体翻转（凹槽朝下）同盘打印",
            "description": "第一层 = 印花正面 / 顶板外表面贴床；打印中看到的是印花背面"
                           "（正确）；无需支撑；打完整体翻面即成品。用 PRINT_READY.3mf。",
        },
        "B_alternative": {
            "label": "B) 备选 · 分开打印 + 压配/胶接",
            "description": "顶板与印花分开打印（顶板仍凹槽朝下贴床；印花正面朝下单独平打），"
                           "取出后压配/点胶（不是打印时粘合）。用 stl/ 分件。",
        },
    }


def parts_table(version, spec, delivery_v):
    entries = {e["part"]: e for e in delivery_v["entries"]}
    fil_entries = [e for e in delivery_v["entries"]
                   if e["part"] == "print_filament"]
    rows = [{"label": "外壳（底壳）", "part": "shell", "qty": 1,
             "material": "PLA/PETG · #2A2E35", "file": entries["shell"]["file"],
             "orientation": "底面朝下（不变）", "method": "打印"},
            {"label": "开槽顶板", "part": "plate", "qty": 1,
             "material": "PLA/PETG · #6B40A0",
             "file": entries["plate_recessed"]["file"],
             "orientation": "翻转：凹槽朝下、原顶面贴床", "method": "打印"},
            {"label": "Kromacut 印花（%s）" % spec["art"], "part": "print",
             "qty": 1, "material": "%d 色 · 见耗材表" % len(fil_entries),
             "file": "%d × %s_print_filament_*.stl" % (len(fil_entries), version),
             "orientation": "翻转：印花正面朝下（第一层贴床）", "method": "打印"}]
    if version == "square":
        rows.append({"label": "按键", "part": "button", "qty": 1,
                     "material": "PLA/PETG · #6B40A0",
                     "file": entries["button"]["file"],
                     "orientation": "平躺（圆盘贴床，厚度 5.2 mm 竖直，正面朝下）",
                     "method": "打印"})
    return rows


# --------------------------------------------------------------------------- #
# sheet
# --------------------------------------------------------------------------- #
def render_stats(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float64)
    return {"file": os.path.relpath(path, ROOT), "size": list(im.size),
            "mean": round(float(a.mean()), 2),
            "std": round(float(a.std()), 2),
            "unique_colors": int(len(np.unique(a.reshape(-1, 3), axis=0)))}


def make_version_sheet(version):
    ver_dir = os.path.join(HERE, version)
    layout = load_json(os.path.join(ver_dir, "layout.json"))
    delivery = load_json(os.path.join(STL_DIR, "delivery.json"))
    dv = delivery["versions"][version]
    spec, art_manifest, fils = read_art(version)
    pose = layout["print_pose"]
    stats = {"iso": render_stats(os.path.join(ver_dir, "print_iso.png")),
             "top": render_stats(os.path.join(ver_dir, "print_top.png"))}
    for st in stats.values():
        if st["mean"] < 15.0 or st["unique_colors"] < 500:
            raise RuntimeError("%s render looks black/empty: %s" % (version, st))
    for e in dv["entries"]:
        p = os.path.join(ROOT, e["path"])
        if not os.path.exists(p):
            raise RuntimeError("delivered STL missing: " + e["path"])
        if e["sha256"] != sha256(p):
            raise RuntimeError("delivered STL sha mismatch: " + e["path"])
        if abs(e["min_z_mm"]) > 1e-6:
            raise RuntimeError("delivered STL min z != 0: " + e["file"])
    print("STL_VERIFY", version, len(dv["entries"]), "files OK (sha256/min z)")

    W, H = SHEET_W, SHEET_H
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    title = ("圆形 LUMEN · 印花 + 外壳 3D 打印交付"
             if version == "round" else
             "方形 square_v1 · 印花 + 外壳 3D 打印交付")
    d.text((40, 30), title, font=F(42, True), fill=FG)
    d.text((42, 86),
           "打印姿态：顶板+印花整体翻转（凹槽朝下）· 第一层=印花正面/顶板外表面贴床 · "
           "%d 色 Kromacut · 220×220 · PROVISIONAL" % len(fils),
           font=F(21), fill=MUT)
    d.line((40, 128, W - 40, 128), fill=(60, 64, 74), width=2)

    # ---- left: bed iso + top + post-flip appearance --------------------- #
    iso = Image.open(os.path.join(ver_dir, "print_iso.png")).convert("RGB")
    iw = 1000
    ih = int(iw * iso.height / iso.width)
    img.paste(iso.resize((iw, ih), Image.LANCZOS), (40, 150))
    d.rectangle((40, 150, 40 + iw, 150 + ih), outline=(60, 64, 74), width=2)

    top = Image.open(os.path.join(ver_dir, "print_top.png")).convert("RGB")
    tw = 340
    th = int(tw * top.height / top.width)
    ty = 150 + ih + 22
    img.paste(top.resize((tw, th), Image.LANCZOS), (40, ty))
    d.rectangle((40, ty, 40 + tw, ty + th), outline=(60, 64, 74), width=2)
    d.text((40, ty + th + 4), "床面排版顶视（看到印花背面＝正确）",
           font=F(14), fill=MUT)

    # post-flip appearance (read-only appearance render, for context)
    x2 = 40 + tw + 18
    hero = os.path.join(ROOT, "appearance", "render", version, "hero.png")
    if os.path.exists(hero):
        hb = Image.open(hero).convert("RGB")
        hs = 250
        img.paste(hb.resize((hs, hs), Image.LANCZOS), (x2, ty))
        d.rectangle((x2, ty, x2 + hs, ty + hs), outline=(60, 64, 74), width=2)
        d.text((x2, ty + hs + 4), "打印后整体翻面 = 成品外观（参考）",
               font=F(14), fill=GREEN)

    # pose numbers + flat STL index (compact: 10 STLs must fit)
    x = x2 + (250 if os.path.exists(hero) else tw) + 22
    yy = ty - 2
    d.text((x, yy), "打印姿态 / 关键尺寸", font=F(18, True), fill=ACC)
    yy += 24
    if dv.get("button"):
        bl = dv["button"]["bbox_mm"]["size"]
        button_line = ("按键：平躺 %.1f×%.1f×%.1f mm（z=厚度 5.2，正面朝下）"
                       % (bl[0], bl[1], bl[2]))
    else:
        button_line = "按键：无（LUMEN 无按键件）"
    pose_lines = [
        "顶板原顶面贴床 z=%.3f · 槽底 z=%.2f mm"
        % (pose["plate_outer_face_z_mm"], pose["pocket_floor_z_mm"]),
        "印花正面 z=%.2f（床上方 0.05 设计顶隙）· 背面 z=%.2f（坐槽底）"
        % (pose["print_art_face_z_mm"], pose["print_back_z_mm"]),
        button_line,
    ]
    for ln in pose_lines:
        d.text((x, yy), ln, font=F(13), fill=MUT)
        yy += 18
    yy += 4
    d.text((x, yy), "STL 文件清单（render/print/stl/）", font=F(16, True),
           fill=ACC)
    yy += 21
    short = {"shell": "外壳", "plate_recessed": "顶板", "button": "按键"}
    for e in dv["entries"]:
        purpose = short.get(e["part"])
        if purpose is None:
            purpose = "印花#%d" % e.get("filament_index", 0)
        swatch_c = tuple(int(e["material_hex"].lstrip("#")[i:i + 2], 16)
                         for i in (0, 2, 4))
        d.rounded_rectangle((x, yy + 3, x + 11, yy + 14), radius=3,
                            fill=swatch_c, outline=(90, 94, 104))
        d.text((x + 16, yy), e["file"], font=F(11), fill=MUT)
        d.text((x + 340, yy), purpose, font=F(11), fill=(120, 128, 142))
        yy += 15
    d.text((x, yy + 3), "CHECKSUMS.sha256 · 全部 min z=0 · 变换矩阵见 delivery.json",
           font=F(11), fill=(120, 128, 142))

    # ---- right column --------------------------------------------------- #
    rx, rw = 1090, W - 1090 - 40
    y = 150

    def head(txt):
        nonlocal y
        d.text((rx, y), txt, font=F(22, True), fill=ACC)
        y += 30

    def para(txt, size=15, color=MUT):
        nonlocal y
        for ln in wrap(d, txt, F(size), rw):
            d.text((rx, y), ln, font=F(size), fill=color)
            y += size + 7

    head("打印姿态（重要）")
    para("· 顶板+印花整体翻转：凹槽朝下，顶板外表面与印花正面贴床（第一层）。")
    para("· 切片/打印时看到的是印花背面，不是图案 —— 这是正确的。")
    para("· 打完整体翻面，翻面后才是成品外观；本姿态无需支撑。", color=GREEN)
    y += 4

    head("打印件清单（STL 已交付到 render/print/stl/）")
    rows = parts_table(version, spec, dv)
    d.text((rx, y), "零件", font=F(13, True), fill=FG)
    d.text((rx + 140, y), "×", font=F(13, True), fill=FG)
    d.text((rx + 166, y), "材料", font=F(13, True), fill=FG)
    d.text((rx + 330, y), "STL 文件", font=F(13, True), fill=FG)
    y += 19
    for r in rows:
        d.text((rx, y), r["label"], font=F(13), fill=FG)
        d.text((rx + 140, y), str(r["qty"]), font=F(13), fill=MUT)
        d.text((rx + 166, y), r["material"], font=F(12), fill=MUT)
        d.text((rx + 330, y), r["file"].replace(version + "_", ""),
               font=F(11), fill=(130, 138, 152))
        y += 20
    y += 4

    head("耗材表（Kromacut filament）")
    for f in fils:
        c = tuple(int(f["hex"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        d.rounded_rectangle((rx, y + 2, rx + 16, y + 18), radius=3, fill=c,
                            outline=(90, 94, 104))
        d.text((rx + 24, y),
               "#%d  %s  ·  %4.1f%% 画面 · %d 三角"
               % (f["number"], f["hex"], f["share_pct"], f["triangles"]),
               font=F(15), fill=MUT)
        y += 24
    y += 4

    rt = routes(version)
    head("两种打印路线")
    for key in ("A_recommended", "B_alternative"):
        d.text((rx, y), rt[key]["label"], font=F(15, True),
               fill=GREEN if key.startswith("A") else FG)
        y += 20
        for ln in wrap(d, rt[key]["description"], F(14), rw):
            d.text((rx, y), ln, font=F(14), fill=MUT)
            y += 19
        y += 2
    y += 4

    ss = slicer_settings(len(fils), version)
    head("打印参数建议")
    para("0.2 mm 层高 · 0.4 mm 喷嘴 · 0.45 mm 线宽 · 2 墙 · 15%% 填充 · "
         "无需支撑%s" % (" · 按键 5 mm brim" if version == "square" else ""),
         size=14)
    para("AMS %d 色（需 ≥%d 槽位；4 槽需换料/第二台 AMS）" % (len(fils), len(fils)),
         size=14)
    y += 4

    head("文件")
    for ln in ["render/print/appearance/%s/PRINT_READY.3mf（床面排版，可切片）"
               % version,
               "render/print/stl/（全部 STL + CHECKSUMS + README）",
               "appearance/build/3mf/%s.3mf（装配完成姿态 mockup）" % version]:
        d.text((rx, y), "· " + ln, font=F(12), fill=MUT)
        y += 18

    d.text((40, H - 20),
           "渲染：Blender 4.5.3 Cycles CPU（iso %.1fs + top %.1fs） · STL %d 个 / %.1f MB "
           "· 生成：make_sheet_appearance.py"
           % (layout["renders"]["iso_seconds"], layout["renders"]["top_seconds"],
              len(dv["entries"]), delivery["total_bytes"] / 1e6),
           font=F(14), fill=(110, 118, 132))
    img.save(os.path.join(ver_dir, "PRINT_SHEET.png"))
    print("WROTE", os.path.relpath(os.path.join(ver_dir, "PRINT_SHEET.png"), ROOT),
          img.size)
    if img.size != (SHEET_W, SHEET_H):
        raise RuntimeError("sheet size wrong")
    return layout, dv, fils, stats


# --------------------------------------------------------------------------- #
# manifest / README
# --------------------------------------------------------------------------- #
def write_manifest(version):
    ver_dir = os.path.join(HERE, version)
    layout = load_json(os.path.join(ver_dir, "layout.json"))
    delivery = load_json(os.path.join(STL_DIR, "delivery.json"))
    dv = delivery["versions"][version]
    spec, art_manifest, fils = read_art(version)
    pose = layout["print_pose"]
    three = delivery["three_mf"][version]
    cks = os.path.join(STL_DIR, "CHECKSUMS.sha256")
    stats = {"iso": render_stats(os.path.join(ver_dir, "print_iso.png")),
             "top": render_stats(os.path.join(ver_dir, "print_top.png"))}
    parts = parts_table(version, spec, dv)
    manifest = {
        "schema": "smartcoaster.print-delivery/v2",
        "version": version, "art": layout["art"],
        "generated_by": "render/print/appearance/make_sheet_appearance.py",
        "generated_at": layout["generated_at"],
        "print_pose": pose,
        "print_routes": routes(version),
        "route_recommended": "A_recommended",
        "bed_size_mm": layout["bed_size_mm"],
        "bed_bbox_mm": layout["bed_bbox_mm"],
        "placements": {k: v["placement_xy_mm"] for k, v in layout["units"].items()},
        "gaps_mm": layout["gaps_mm"], "min_gap_mm": layout["min_gap_mm"],
        "button": layout.get("button"),
        "parts": parts,
        "purchased_parts": [
            "OLED 模组 0.91\" 128×32（含玻璃）", "硅胶垫（防滑）", "PCB（2 层）",
            "HY928D 称重传感器", "ESP32-S3 模组", "HX711 ADC 模组",
            "USB-C 连接器/线缆", "500 mAh 锂电池", "M2 螺钉/铜柱",
        ],
        "filaments": {"layer_height_mm": 0.2,
                      "palette_hex": [f["hex"] for f in fils],
                      "filament_objects": fils},
        "slicer_settings": slicer_settings(len(fils), version),
        "bambu_import_order": [
            "1. 导入 render/print/stl/%s_print_filament_*.stl（%d 个印花色，"
            "按翻转姿态已烘焙）" % (version, len(fils)),
            "2. 每个印花对象指定一个 AMS 槽位（%d 色需 ≥%d 槽位；4 槽需换料/第二台 AMS）"
            % (len(fils), len(fils)),
            "3. 导入 %s_plate_recessed.stl（凹槽朝下、原顶面贴床），与印花同盘嵌套"
            "（印花正面在床面上方 0.05 mm）" % version,
            "4. 导入 %s_shell.stl（底面朝下单独打印）%s"
            % (version, "，%s_button.stl（平躺，正面朝下 + 5 mm brim）" % version
               if version == "square" else ""),
            "5. 或直接用 render/print/appearance/%s/PRINT_READY.3mf（床面排版）"
            % version,
            "6. 打印完成后整体翻面 → 成品外观（本姿态看到的是印花背面，正确）",
        ],
        "sources": dv["sources"],
        "files": {
            "print_ready_3mf": three,
            "stl_dir": os.path.relpath(STL_DIR, ROOT),
            "stl_files": dv["entries"],
            "checksums_sha256": os.path.relpath(cks, ROOT),
            "delivery_json": os.path.relpath(os.path.join(STL_DIR, "delivery.json"),
                                             ROOT),
            "assembled_mockup_3mf": "appearance/build/3mf/%s.3mf" % version,
            "sheet": os.path.relpath(os.path.join(ver_dir, "PRINT_SHEET.png"), ROOT),
            "layout_json": os.path.relpath(os.path.join(ver_dir, "layout.json"), ROOT),
            "renders": [stats["iso"]["file"], stats["top"]["file"]],
        },
        "validation": {
            "checks": layout["checks"],
            "bed_fits_220": layout["checks"]["bed_fits_220"],
            "print_art_face_z_mm": pose["print_art_face_z_mm"],
            "pocket_floor_z_mm": pose["pocket_floor_z_mm"],
            "plate_outer_face_z_mm": pose["plate_outer_face_z_mm"],
            "no_supports_route_A": True,
            "stl_delivery": {
                "count": len(dv["entries"]),
                "total_bytes": sum(e["bytes"] for e in dv["entries"]),
                "all_min_z_zero": all(abs(e["min_z_mm"]) < 1e-6
                                      for e in dv["entries"]),
                "all_rigid_checks": all(
                    e["triangles"] == e["source_triangles"]
                    and abs(e["volume_mm3"] - e["source_volume_mm3"])
                    <= max(1e-6 * abs(e["source_volume_mm3"]), 0.01)
                    for e in dv["entries"]),
                "checksums_file": os.path.relpath(cks, ROOT),
            },
            "three_mf": {"ok": three["ok"], "path": three["path"],
                         "object_count": three["object_count"],
                         "build_items": three["build_items"],
                         "total_triangles": three["total_triangles"],
                         "bbox_mm": three["bbox_mm"],
                         "errors": three["errors"]},
            "renders": stats,
            "sheet_size": [SHEET_W, SHEET_H],
            "note": "bed layout / pose assertions from measured geometry; baked STLs "
                    "rigid-transform checked (triangle count + volume + bbox); 3MF "
                    "read-back validated; physical print untested = PROVISIONAL",
        },
    }
    with open(os.path.join(ver_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print("WROTE", os.path.relpath(os.path.join(ver_dir, "manifest.json"), ROOT))

    md = ["# 3D 打印交付 — %s / %s" % (
        "圆形 LUMEN" if version == "round" else "方形 square_v1", layout["art"]), "",
          "> **打印姿态：顶板+印花整体翻转（凹槽朝下）**。第一层 = 印花正面 / 顶板外表面贴床；"
          "切片时看到印花背面（正确），打印完成后整体翻面即为成品。"
          "STL 已烘焙到此姿态并放在 `render/print/stl/`（非软链，sha256 校验）。", "",
          "## 打印姿态关键尺寸", "",
          "| 项 | 值 |", "|---|---|",
          "| 顶板外表面（原顶面）贴床 | z = %.3f mm |" % pose["plate_outer_face_z_mm"],
          "| 顶板槽底（凹槽朝下后的顶面） | z = %.2f mm |" % pose["pocket_floor_z_mm"],
          "| 印花正面（第一层） | z = %.2f mm（床上方 0.05 设计顶隙）"
          % pose["print_art_face_z_mm"],
          "| 印花背面（坐在槽底） | z = %.2f mm |" % pose["print_back_z_mm"],
          "| 印花厚度 | %.2f mm |" % pose["print_thickness_mm"],
          "| 支撑 | 不需要（第一层贴床） |", ""]
    if version == "square":
        bl = layout["button"]["bbox_mm"]["size"]
        md += ["## 按键（平躺）", "",
               "- bbox ≈ %.1f × %.1f × %.1f mm（z = 厚度 5.2 mm，圆盘平行床面）"
               % (bl[0], bl[1], bl[2]),
               "- 可见正面（原 -Y 帽面）**朝下贴床**；翻面后可见面为光滑顶面"
               "（PROVISIONAL）。", ""]
    md += ["## 打印件 / STL", "",
           "| 零件 | STL（render/print/stl/） | 材料 | 打印方式 | 方向 |",
           "|---|---|---|---|---|"]
    for r in parts:
        md.append("| %s | `%s` | %s | %s | %s |" % (
            r["label"], r["file"], r["material"], r["method"], r["orientation"]))
    md += ["", "## STL 文件清单（18 个文件，扁平目录）", "",
           "| 文件 | 三角数 | 体积 mm³ | min z | 字节 | sha256(16) |",
           "|---|---|---|---|---|---|"]
    for e in dv["entries"]:
        md.append("| `%s` | %d | %.1f | %.6f | %d | `%s` |" % (
            e["file"], e["triangles"], e["volume_mm3"], e["min_z_mm"],
            e["bytes"], e["sha256"][:16]))
    md += ["", "## 两种打印路线", ""]
    rt = routes(version)
    md.append("- **A（推荐）**：" + rt["A_recommended"]["description"])
    md.append("- **B（备选）**：" + rt["B_alternative"]["description"])
    md += ["", "## 排版与验证", "",
           "- 床面 220×220；本版占用 %.1f×%.1f mm，最小间距 %.2f mm，无越界/重叠。"
           % (layout["bed_bbox_mm"]["size"][0], layout["bed_bbox_mm"]["size"][1],
              layout["min_gap_mm"])]
    for name, u in layout["units"].items():
        md.append("- %s：放置 (%.2f, %.2f) mm，bbox %s mm。" % (
            name, u["placement_xy_mm"][0], u["placement_xy_mm"][1],
            u["bbox_mm"]["size"]))
    md.append("- 每个交付 STL：三角数/体积与源一致、bbox = 刚性旋转源、min z = 0。")
    md.append("- 3MF 回读校验：%s（objects %d / build items %d / tris %d / bbox %s）。"
              % ("OK" if three["ok"] else "FAIL", three["object_count"],
                 three["build_items"], three["total_triangles"],
                 three["bbox_mm"]["size"]))
    md.append("- 渲染非黑；sheet 1800×1200。")
    md += ["", "## Bambu 导入顺序", ""]
    for ln in manifest["bambu_import_order"]:
        md.append("- " + ln)
    md += ["", "## 两个 3MF", "",
           "- `render/print/appearance/%s/PRINT_READY.3mf`：可切片床面排版。" % version,
           "- `appearance/build/3mf/%s.3mf`：装配完成姿态 mockup（不直接切片）。" % version,
           "", "## 未验证", "",
           "- 未在真实切片器切片/打印；0.05 mm 首层、按键朝向为 PROVISIONAL。", ""]
    with open(os.path.join(ver_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("WROTE", os.path.relpath(os.path.join(ver_dir, "README.md"), ROOT))
    return manifest


# --------------------------------------------------------------------------- #
# combined board
# --------------------------------------------------------------------------- #
def make_combined_board(manifests):
    W, H = 2400, 1250
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((50, 30), "SmartCoaster — 3D 打印交付（两种外观版本）",
           font=F(44, True), fill=FG)
    d.text((52, 90),
           "打印姿态：顶板+印花整体翻转（凹槽朝下）· 第一层=印花正面/顶板外表面贴床 · "
           "无需支撑 · 打印后整体翻面 · 220×220 · PROVISIONAL", font=F(21), fill=MUT)
    d.line((50, 132, W - 50, 132), fill=(60, 64, 74), width=2)

    tiles = []
    for ver in ("round", "square"):
        m = manifests[ver]
        iso = Image.open(os.path.join(HERE, ver, "print_iso.png")).convert("RGB")
        iw = 1100
        ih = int(iw * iso.height / iso.width)
        tiles.append((ver, m, iso.resize((iw, ih), Image.LANCZOS)))

    for i, (ver, m, iso) in enumerate(tiles):
        x0 = 50 + i * 1200
        y0 = 160
        img.paste(iso, (x0, y0))
        d.rectangle((x0, y0, x0 + iso.width, y0 + iso.height),
                    outline=(60, 64, 74), width=2)
        title = ("圆形 LUMEN · dog 印花（6 色）" if ver == "round"
                 else "方形 square_v1 · elf 印花（7 色）")
        d.text((x0, y0 + iso.height + 14), title, font=F(28, True), fill=FG)
        p = m["print_pose"]
        bed = m["bed_bbox_mm"]["size"]
        info = ("床面 %.1f×%.1f mm · 最小间距 %.2f mm · 顶板原顶面 z=%.2f · "
                "印花正面 z=%.2f · 槽底 z=%.2f"
                % (bed[0], bed[1], m["min_gap_mm"], p["plate_outer_face_z_mm"],
                   p["print_art_face_z_mm"], p["pocket_floor_z_mm"]))
        d.text((x0, y0 + iso.height + 52), info, font=F(18), fill=MUT)
        if m.get("button"):
            bl = m["button"]["bbox_mm"]["size"]
            d.text((x0, y0 + iso.height + 78),
                   "按键平躺 bbox %.1f×%.1f×%.1f mm（z=厚度，正面朝下）"
                   % (bl[0], bl[1], bl[2]), font=F(17), fill=GREEN)

    ytab = 160 + tiles[0][2].height + 108
    d.line((50, ytab, W - 50, ytab), fill=(60, 64, 74), width=2)
    d.text((50, ytab + 14), "打印件：外壳 ×1 / 开槽顶板 ×1 / Kromacut 印花 ×1 / "
                            "方形按键 ×1（圆形无按键）  ·  采购件：OLED 玻璃、硅胶垫、"
                            "PCB、HY928D、ESP32-S3、HX711、USB-C、电池、M2 螺钉",
           font=F(20), fill=FG)
    d.text((50, ytab + 52),
           "A（推荐）：顶板+印花整体翻转（凹槽朝下）同盘打印，第一层=印花正面/顶板外表面贴床，"
           "无需支撑，打完整体翻面。 B（备选）：分开打印后压配/胶接（非打印时粘合）。",
           font=F(18), fill=GREEN)
    d.text((50, ytab + 88),
           "STL：render/print/stl/（18 个，扁平目录，CHECKSUMS.sha256） · "
           "床面排版 3MF：render/print/appearance/{round,square}/PRINT_READY.3mf · "
           "装配 mockup：appearance/build/3mf/",
           font=F(16), fill=(110, 118, 132))
    out = os.path.join(HERE, "PRINT_SHEET_APPEARANCE.png")
    img.save(out)
    print("WROTE", os.path.relpath(out, ROOT), img.size)
    return out


def main():
    manifests = {}
    for v in ("round", "square"):
        print("=" * 78)
        layout, dv, fils, stats = make_version_sheet(v)
        manifests[v] = write_manifest(v)
    make_combined_board(manifests)

    delivery = load_json(os.path.join(STL_DIR, "delivery.json"))
    print("=" * 78)
    ok = True
    for v, m in manifests.items():
        three = delivery["three_mf"][v]
        dv = delivery["versions"][v]
        dims = [os.path.getsize(os.path.join(HERE, v, "PRINT_SHEET.png")) /
                1e6]
        sig = (m["validation"]["stl_delivery"]["all_min_z_zero"]
               and m["validation"]["stl_delivery"]["all_rigid_checks"]
               and three["ok"] and all(m["validation"]["checks"].values()))
        ok = ok and sig
        print("%-7s sheet=%.2f MB  STL=%d/%.2f MB  min_z0=%s rigid=%s  "
              "print_pose z(art)=%.3f floor=%.2f  bed=%.1fx%.1f  gap=%.2f  "
              "3MF=%s  %s"
              % (v, dims[0], len(dv["entries"]),
                 sum(e["bytes"] for e in dv["entries"]) / 1e6,
                 m["validation"]["stl_delivery"]["all_min_z_zero"],
                 m["validation"]["stl_delivery"]["all_rigid_checks"],
                 m["print_pose"]["print_art_face_z_mm"],
                 m["print_pose"]["pocket_floor_z_mm"],
                 m["bed_bbox_mm"]["size"][0], m["bed_bbox_mm"]["size"][1],
                 m["min_gap_mm"], "OK" if three["ok"] else "FAIL",
                 "OK" if sig else "FAIL"))
        if m.get("button"):
            print("         button bbox", m["button"]["bbox_mm"]["size"],
                  "face_down:", m["button"]["face_down"])
    print("PRINT DELIVERY (task-6) ALL OK:", ok)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
