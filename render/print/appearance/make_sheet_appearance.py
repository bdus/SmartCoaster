#!/usr/bin/env python3
"""Print-delivery reference sheets + STL delivery + manifest/README, both versions.

Reads the bed layout + validation written by print_layout_appearance.py and the
read-only manifests from the appearance pipeline, then produces, per version:

  render/print/appearance/<v>/stl/shell.stl                     real copied STL
  render/print/appearance/<v>/stl/plate_recessed.stl            real copied STL
  render/print/appearance/<v>/stl/button.stl                    (square only)
  render/print/appearance/<v>/stl/print/multimaterial/filament_<n>_<HEX>.stl
  render/print/appearance/<v>/PRINT_READY.3mf                   copy of assembled 3MF
  render/print/appearance/<v>/CHECKSUMS.sha256                  sha256 of delivered files
  render/print/appearance/<v>/PRINT_SHEET.png                   1800x1200 reference sheet
  render/print/appearance/<v>/manifest.json                     machine-readable manifest
  render/print/appearance/<v>/README.md                         human-readable delivery README

and the combined board:
  render/print/appearance/PRINT_SHEET_APPEARANCE.png

Optional single-colour preview STL is intentionally NOT delivered (documented why).
All copied STLs are verified byte-for-byte against their sources (sha256) and the
renders are checked non-black; print bottom == pocket floor is re-checked from the
layout JSON and printed.

Run:  python3 render/print/appearance/make_sheet_appearance.py
"""
import hashlib
import json
import os
import shutil
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
PREVIEW_SKIP_REASON = (
    "skipped: the 6/7 per-filament STLs are closed solids with intentional "
    "coincident interface faces (parallel caps); a single-colour concatenation would "
    "carry internal/overlapping faces and a boolean union of 1.9-2.5 M triangles per "
    "version is not a reliable printable preview. Use PRINT_READY.3mf (multi-material) "
    "or the per-filament STLs instead.")


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


def swatch(draw, x, y, hexv, r=10):
    rgb = tuple(int(hexv.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    draw.rounded_rectangle((x, y, x + 2 * r, y + 2 * r), radius=4,
                           fill=rgb, outline=(90, 94, 104))


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
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


def read_art_data(version):
    spec = SC.resolve_assembly(version)
    art = spec["art"]
    m = load_json(os.path.join(ROOT, "appearance", "build", "print", art,
                               "manifest.json"))
    palette = m["art"]["palette"]
    layer_count = int(m["art"]["layerCount"])
    thickness = float(m["art"]["thicknessMm"])
    opaque = int(m["art"]["stats"]["opaquePixels"])
    face_px = {int(p["classIndex"]): int(p["activePixels"])
               for p in m["layout"]["parts"] if p["kind"] == "face"}
    filaments = []
    for st in sorted(m["stls"], key=lambda s: int(s["filamentIndex"])):
        idx = int(st["filamentIndex"])
        hexv = "#" + str(st["hex"]).lstrip("#").upper()
        filaments.append({
            "number": idx,
            "hex": hexv,
            "triangles": int(st["triangles"]),
            "art_pixels": face_px.get(idx),
            "art_share_pct": round(100.0 * face_px.get(idx, 0) / opaque, 1),
            "part_name": st.get("partName"),
            "source": st.get("file"),
        })
    return spec, m, {
        "palette": palette, "layer_count": layer_count, "thickness_mm": thickness,
        "filaments": filaments,
    }


def render_stats(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float64)
    return {"file": os.path.relpath(path, ROOT), "size": list(im.size),
            "mean": round(float(a.mean()), 2),
            "std": round(float(a.std()), 2),
            "unique_colors": int(len(np.unique(a.reshape(-1, 3), axis=0)))}


def slicer_settings():
    return {
        "printer_profile": "generic FDM, 220 x 220 mm bed (Bambu Studio example)",
        "layer_height_mm": 0.2,
        "nozzle_mm": 0.4,
        "line_width_mm": 0.45,
        "walls": 2,
        "top_bottom_layers": "4 / 3",
        "infill_pct": 15,
        "infill_pattern": "grid (shell) / gyroid (plate)",
        "supports": "tree supports under the plate body (route A, recess-up nested print)",
        "brim": "5 mm for the button; none for shell; plate uses supports",
        "filament_slots": "one filament per AMS slot: dog needs 6 slots, elf needs 7; "
                          "a 4-slot AMS requires spool swaps or a second AMS / AMS lite",
        "first_layer": "0.2 mm, 200 mm/s max, part cooling off first layer",
        "notes": "PROVISIONAL starting point; not physically tested. Screen window / "
                 "button hole may need local support or bridging checks.",
    }


def routes(version):
    return {
        "A_recommended_multi_material_in_place": {
            "label": "A) 推荐 · 多材料原位粘合",
            "description": "顶板凹槽朝上 + 印花嵌在槽内，同盘打印（顶板裙边/传力柱需支撑，"
                           "PROVISIONAL）；外壳单独打印。使用 PRINT_READY.3mf。",
            "file": "PRINT_READY.3mf",
            "supports": "tree supports under plate body",
        },
        "B_support_free_alternative": {
            "label": "B) 备选 · 无支撑",
            "description": "顶板倒扣打印（表面好）+ 印花单独平打，之后压入/胶接"
                           "（不是打印时粘合）。使用 stl/ 里的文件。",
            "file": "stl/ (per-part STLs)",
            "supports": "none",
        },
    }


def parts_table(version, art_d):
    spec = SC.resolve_assembly(version)
    rows = [{
        "part": "shell", "label": "外壳（底壳）", "stl": "stl/shell.stl",
        "file": os.path.relpath([p["path"] for p in spec["parts"]
                                 if p["name"] == "shell"][0], ROOT),
        "qty": 1, "material": "PLA/PETG · #2A2E35", "printed": True,
        "orientation": "底面朝下平放（按设计）", "supports": "无支撑",
    }, {
        "part": "plate_recessed", "label": "开槽顶板", "stl": "stl/plate_recessed.stl",
        "file": os.path.relpath(spec["plate"]["path"], ROOT),
        "qty": 1, "material": "PLA/PETG · #6B40A0", "printed": True,
        "orientation": "凹槽朝上，与印花嵌套（原位粘合）",
        "supports": "PROVISIONAL：需树状支撑（裙边/传力柱悬空）",
    }, {
        "part": "print_assembly", "label": "Kromacut 印花（%s）" % spec["art"],
        "stl": "stl/print/multimaterial/filament_*.stl",
        "file": os.path.relpath(spec["print"]["dir"], ROOT) + "/filament_*.stl",
        "qty": 1, "material": "%d 色 · 见耗材表" % len(art_d["filaments"]),
        "printed": True,
        "orientation": "面朝上（face-up），嵌套进顶板凹槽",
        "supports": "无；与顶板同一嵌套打印任务",
    }]
    if version == "square":
        rows.append({
            "part": "button", "label": "按键", "stl": "stl/button.stl",
            "file": os.path.relpath([p["path"] for p in spec["parts"]
                                     if p["name"] == "button"][0], ROOT),
            "qty": 1, "material": "PLA/PETG · #6B40A0", "printed": True,
            "orientation": "底面朝下平放", "supports": "无需；5 mm brim",
        })
    purchased = [
        "OLED 模组 0.91\" 128×32（含玻璃）", "硅胶垫（防滑）", "PCB（2 层，已设计）",
        "HY928D 称重传感器", "ESP32-S3 模组", "HX711 ADC 模组",
        "USB-C 连接器/线缆", "500 mAh 锂电池", "M2 螺钉/铜柱",
    ]
    return rows, purchased


# --------------------------------------------------------------------------- #
# STL / 3MF delivery
# --------------------------------------------------------------------------- #
def deliver_stls(version, layout, art_d):
    """Copy the real printable STLs + assembled 3MF, write CHECKSUMS.sha256."""
    ver_dir = os.path.join(HERE, version)
    spec = SC.resolve_assembly(version)
    cmf = SC.load_cmf(SC.load_config())
    stl_dir = os.path.join(ver_dir, "stl")
    mat_dir = os.path.join(stl_dir, "print", "multimaterial")
    os.makedirs(mat_dir, exist_ok=True)
    entries = []

    def add(src, dest_rel, purpose, hexv):
        src = src if os.path.isabs(src) else os.path.join(ROOT, src)
        if not os.path.exists(src):
            raise RuntimeError("delivery source missing: " + src)
        dst = os.path.join(ver_dir, dest_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        s_sha = sha256(src)
        if os.path.exists(dst) and sha256(dst) == s_sha:
            pass                      # idempotent: identical copy already delivered
        else:
            shutil.copy2(src, dst)
        d_sha = sha256(dst)
        if s_sha != d_sha:
            raise RuntimeError("sha256 mismatch after copy: " + dest_rel)
        entry = {
            "path": os.path.relpath(dst, ROOT),
            "rel": dest_rel,
            "source": os.path.relpath(src, ROOT),
            "bytes": os.path.getsize(dst),
            "sha256": d_sha,
            "purpose": purpose,
            "material_hex": hexv,
            "printed": True,
            "sha256_match": True,
        }
        entries.append(entry)
        print("STL_COPY %-10s %-58s %10d B  sha256=%s  match=True"
              % (version, dest_rel, entry["bytes"], d_sha[:16]))
        return entry

    # assembled multi-material 3MF (recommended route A)
    src3 = os.path.join(ROOT, "appearance", "build", "3mf", version + ".3mf")
    dst3 = os.path.join(ver_dir, "PRINT_READY.3mf")
    if not os.path.exists(src3):
        raise RuntimeError("assembled 3MF missing: " + src3)
    if not (os.path.exists(dst3) and sha256(dst3) == sha256(src3)):
        shutil.copy2(src3, dst3)
    threemf = {
        "path": os.path.relpath(dst3, ROOT), "rel": "PRINT_READY.3mf",
        "source": os.path.relpath(src3, ROOT), "bytes": os.path.getsize(dst3),
        "sha256": sha256(dst3), "purpose": "route A: assembled multi-material 3MF "
        "(shell + recessed plate + print, one print assembly)",
        "sha256_source": sha256(src3),
    }
    if threemf["sha256"] != threemf["sha256_source"]:
        raise RuntimeError("PRINT_READY.3mf copy mismatch")
    print("3MF_COPY %-10s %-58s %10d B  sha256=%s" % (
        version, "PRINT_READY.3mf", threemf["bytes"], threemf["sha256"][:16]))

    shell_src = [p["path"] for p in spec["parts"] if p["name"] == "shell"][0]
    add(shell_src, "stl/shell.stl", "外壳（底壳），底面朝下打印",
        "#" + cmf["parts"]["shell"]["hex"].lstrip("#").upper())
    add(spec["plate"]["path"], "stl/plate_recessed.stl",
        "开槽顶板，凹槽朝上嵌套印花（路线 A）或倒扣（路线 B）",
        "#" + cmf["parts"]["plate"]["hex"].lstrip("#").upper())
    if version == "square":
        btn_src = [p["path"] for p in spec["parts"] if p["name"] == "button"][0]
        add(btn_src, "stl/button.stl", "按键，底面朝下 + 5 mm brim",
            "#" + cmf["parts"]["button"]["hex"].lstrip("#").upper())
    for f in art_d["filaments"]:
        pobj = spec["print"]["objects"][f["number"] - 1]
        dest = "stl/print/multimaterial/filament_%d_%s.stl" % (
            f["number"], f["hex"].lstrip("#"))
        add(pobj["path"], dest, "印花第 %d 色（filament %d），与其他色一起导入、"
                                "每对象一色" % (f["number"], f["number"]), f["hex"])

    # CHECKSUMS.sha256 (paths relative to the version dir)
    lines = ["%s  %s" % (e["sha256"], e["rel"]) for e in entries]
    lines.append("%s  %s" % (threemf["sha256"], threemf["rel"]))
    cks_path = os.path.join(ver_dir, "CHECKSUMS.sha256")
    with open(cks_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("WROTE", os.path.relpath(cks_path, ROOT), "(%d files)" % len(lines))

    return {
        "entries": entries,
        "threemf": threemf,
        "checksums": os.path.relpath(cks_path, ROOT),
        "stl_dir": os.path.relpath(stl_dir, ROOT),
        "count": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "all_sha256_match": all(e["sha256_match"] for e in entries)
        and threemf["sha256"] == threemf["sha256_source"],
        "preview": {"delivered": False, "file": None,
                    "reason": PREVIEW_SKIP_REASON},
    }


# --------------------------------------------------------------------------- #
# per-version sheet
# --------------------------------------------------------------------------- #
def make_version_sheet(version):
    ver_dir = os.path.join(HERE, version)
    layout = load_json(os.path.join(ver_dir, "layout.json"))
    spec, art_manifest, art_d = read_art_data(version)
    art = spec["art"]
    sh = spec["shell"]

    iso_path = os.path.join(ver_dir, "print_iso.png")
    top_path = os.path.join(ver_dir, "print_top.png")
    stats = {"iso": render_stats(iso_path), "top": render_stats(top_path)}
    for key, st in stats.items():
        if st["mean"] < 15.0 or st["unique_colors"] < 500:
            raise RuntimeError("%s %s render looks black/empty: %s"
                               % (version, key, st))
    print("RENDER_STATS", version, stats)
    delivery = deliver_stls(version, layout, art_d)

    W, H = SHEET_W, SHEET_H
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    title = ("圆形 LUMEN · 印花 + 外壳 3D 打印交付"
             if version == "round" else
             "方形 square_v1 · 印花 + 外壳 3D 打印交付")
    d.text((40, 30), title, font=F(42, True), fill=FG)
    d.text((42, 86),
           "STL 交付 + 凹槽朝上嵌套打印（原位粘合） · %d 色 Kromacut · 220×220 打印床 · "
           "PROVISIONAL（未实物验证）" % len(art_d["filaments"]),
           font=F(21), fill=MUT)
    d.line((40, 128, W - 40, 128), fill=(60, 64, 74), width=2)

    # ---- left: iso + top renders --------------------------------------- #
    iso = Image.open(iso_path).convert("RGB")
    iw = 1000
    ih = int(iw * iso.height / iso.width)
    img.paste(iso.resize((iw, ih), Image.LANCZOS), (40, 150))
    d.rectangle((40, 150, 40 + iw, 150 + ih), outline=(60, 64, 74), width=2)

    top = Image.open(top_path).convert("RGB")
    tw = 380
    th = int(tw * top.height / top.width)
    ty = 150 + ih + 24
    img.paste(top.resize((tw, th), Image.LANCZOS), (40, ty))
    d.rectangle((40, ty, 40 + tw, ty + th), outline=(60, 64, 74), width=2)

    # bed / fit annotation + STL index beside the top view
    x = 40 + tw + 26
    yy = ty + 2
    bed = layout["bed_bbox_mm"]
    d.text((x, yy), "排版 / 床面 (220×220)", font=F(20, True), fill=ACC)
    yy += 30
    for ln in [
        "床面占用 %.1f × %.1f mm（≤220） · 最小间距 %.2f mm（≥5）"
        % (bed["size"][0], bed["size"][1], layout["min_gap_mm"]),
        "无越界 / 无重叠（bbox 断言）",
        "印花底面 z = %.2f mm ＝ 槽底 z = %.2f mm（相对顶板 %.2f）"
        % (layout["units"]["plate_unit"]["print_bottom_bed_z_mm"],
           layout["units"]["plate_unit"]["pocket_floor_bed_z_mm"],
           sh["floor_z_mm"]),
    ]:
        d.text((x, yy), ln, font=F(15), fill=MUT)
        yy += 22

    yy += 6
    d.text((x, yy), "STL 文件清单（stl/；印花在 print/multimaterial/）",
           font=F(18, True), fill=ACC)
    yy += 28
    short_purpose = {"shell": "外壳", "plate_recessed": "顶板",
                     "button": "按键"}
    items = []
    for e in delivery["entries"]:
        name = e["rel"].split("/")[-1]
        purpose = short_purpose.get(os.path.splitext(name)[0], "")
        if not purpose:
            purpose = ("印花#%s" % name.split("_")[1]
                       if name.startswith("filament_") else "印花")
        items.append((name, e["material_hex"], purpose))
    colw = (1090 - 8 - x) // 2
    per_col = (len(items) + 1) // 2
    for i, (name, hexv, purpose) in enumerate(items):
        cx = x + (i // per_col) * colw
        cy = yy + (i % per_col) * 20
        swatch(d, cx, cy + 2, hexv, 7)
        d.text((cx + 18, cy), name, font=F(12), fill=MUT)
        d.text((cx + colw - 42, cy), purpose, font=F(12), fill=(120, 128, 142))
    yy += per_col * 20 + 6
    d.text((x, yy), "CHECKSUMS.sha256 校验；PRINT_READY.3mf 为推荐路线 A；"
                    "单色预览 STL 未交付（原因见 README）。",
           font=F(13), fill=(120, 128, 142))

    # ---- right column --------------------------------------------------- #
    rx, rw = 1090, W - 1090 - 40
    y = 150

    def head(txt):
        nonlocal y
        d.text((rx, y), txt, font=F(23, True), fill=ACC)
        y += 32

    def para(txt, size=16, color=MUT):
        nonlocal y
        for ln in wrap(d, txt, F(size), rw):
            d.text((rx, y), ln, font=F(size), fill=color)
            y += size + 8

    rows, purchased = parts_table(version, art_d)
    head("打印件清单（STL 已交付到 stl/）")
    d.text((rx, y), "零件", font=F(14, True), fill=FG)
    d.text((rx + 168, y), "×", font=F(14, True), fill=FG)
    d.text((rx + 196, y), "材料/颜色", font=F(14, True), fill=FG)
    d.text((rx + 382, y), "方式", font=F(14, True), fill=FG)
    d.text((rx + 428, y), "STL", font=F(14, True), fill=FG)
    y += 21
    for r in rows:
        d.text((rx, y), r["label"], font=F(14), fill=FG)
        d.text((rx + 168, y), str(r["qty"]), font=F(14), fill=MUT)
        d.text((rx + 196, y), r["material"], font=F(13), fill=MUT)
        d.text((rx + 382, y), "打印", font=F(13), fill=GREEN)
        d.text((rx + 428, y), r["stl"], font=F(11), fill=(130, 138, 152))
        y += 23
    y += 4
    head("不打印（采购 / 另做）")
    para("、".join(purchased), size=15)
    y += 6

    head("耗材表（Kromacut filament）")
    for f in art_d["filaments"]:
        swatch(d, rx, y + 2, f["hex"], 9)
        d.text((rx + 28, y - 1),
               "#%d  %s  ·  %4.1f%% 画面 · %d 三角" % (
                   f["number"], f["hex"], f["art_share_pct"], f["triangles"]),
               font=F(15), fill=MUT)
        y += 25
    y += 6

    rt = routes(version)
    head("两种打印路线（必须是路线 A 的嵌套同盘打印）")
    for key in ("A_recommended_multi_material_in_place", "B_support_free_alternative"):
        r = rt[key]
        d.text((rx, y), r["label"], font=F(16, True),
               fill=GREEN if key.startswith("A") else FG)
        y += 22
        for ln in wrap(d, r["description"], F(15), rw):
            d.text((rx, y), ln, font=F(15), fill=MUT)
            y += 21
        y += 2
    y += 4

    head("打印方向 / 支撑（PROVISIONAL）")
    para("· 外壳：底面朝下平放，无支撑；屏窗/按键孔需检查桥接。", size=15)
    para("· 顶板+印花：凹槽朝上、印花底面坐在槽底（z=%.2f mm）；该姿态顶板裙边/"
         "传力柱悬空 → 树状支撑（未实物验证）。" % sh["floor_z_mm"], size=15,
         color=WARN)
    y += 4

    head("打印参数建议")
    nfil = len(art_d["filaments"])
    button_clause = " · 按键 5 mm brim" if version == "square" else ""
    para("0.2 mm 层高 · 0.4 mm 喷嘴 · 0.45 mm 线宽 · 2 墙 · 15%% 填充 · "
         "AMS %d 色（需 ≥%d 槽位；4 槽需换料/第二台 AMS）%s"
         % (nfil, nfil, button_clause), size=15)
    y += 4

    head("文件")
    for ln in [
        "render/print/appearance/%s/PRINT_READY.3mf" % version,
        "render/print/appearance/%s/stl/" % version,
        "render/print/appearance/%s/CHECKSUMS.sha256" % version,
    ]:
        d.text((rx, y), "· " + ln, font=F(13), fill=MUT)
        y += 20

    d.text((40, H - 20),
           "渲染：Blender 4.5.3 Cycles CPU（iso %.1fs + top %.1fs） · "
           "STL %d 个 / %.1f MB · 生成：make_sheet_appearance.py"
           % (layout["renders"]["iso_seconds"], layout["renders"]["top_seconds"],
              delivery["count"], delivery["total_bytes"] / 1e6),
           font=F(14), fill=(110, 118, 132))
    img.save(os.path.join(ver_dir, "PRINT_SHEET.png"))
    print("WROTE", os.path.relpath(os.path.join(ver_dir, "PRINT_SHEET.png"), ROOT),
          img.size)
    if img.size != (SHEET_W, SHEET_H):
        raise RuntimeError("sheet size wrong")
    return layout, art_d, stats, delivery


# --------------------------------------------------------------------------- #
# manifest / README
# --------------------------------------------------------------------------- #
def write_manifest(version, layout, art_d, stats, delivery):
    ver_dir = os.path.join(HERE, version)
    rows, purchased = parts_table(version, art_d)
    manifest = {
        "schema": "smartcoaster.print-delivery/v1",
        "version": version,
        "art": layout["art"],
        "generated_by": "render/print/appearance/make_sheet_appearance.py",
        "generated_at": layout["generated_at"],
        "bed_size_mm": layout["bed_size_mm"],
        "bed_bbox_mm": layout["bed_bbox_mm"],
        "placements": {k: v["placement_xy_mm"] for k, v in layout["units"].items()},
        "gaps_mm": layout["gaps_mm"],
        "min_gap_mm": layout["min_gap_mm"],
        "plate_print_unit": layout["units"]["plate_unit"],
        "orientation": {
            "shell": "bed down (as designed)",
            "plate": "recess UP, print nested in the recess (route A in-place bonding)",
            "print": "face up, nested; print bottom on the pocket floor",
            "button": "bed down" if version == "square" else None,
        },
        "print_routes": routes(version),
        "route_recommended": "A_recommended_multi_material_in_place",
        "support_guidance": {
            "status": "PROVISIONAL - not physically tested",
            "plate": layout["support_note"],
            "support_free_alternative": layout["support_free_alternative"],
        },
        "parts": rows,
        "purchased_parts": purchased,
        "filaments": {
            "layer_height_mm": 0.2,
            "palette_hex": art_d["palette"],
            "filament_objects": art_d["filaments"],
        },
        "slicer_settings": slicer_settings(),
        "bambu_import_order": [
            "1. 导入 stl/print/multimaterial/filament_*.stl（全部 %d 个印花色）"
            % len(art_d["filaments"]),
            "2. 印花各对象按原位（XY 0,0 / 底面 z=0）装配，每个对象指定一个 AMS 槽位",
            "3. 导入 stl/plate_recessed.stl，凹槽朝上，置于印花下方同一嵌套位置",
            "4. 导入 stl/shell.stl（外壳单独打印）"
            + ("，stl/button.stl（按键，5 mm brim）" if version == "square" else ""),
            "5. 或直接使用 PRINT_READY.3mf（路线 A，已按装配位摆好）",
        ],
        "sources": layout["sources"],
        "files": {
            "print_ready_3mf": delivery["threemf"],
            "stl_dir": delivery["stl_dir"],
            "stl_files": delivery["entries"],
            "checksums_sha256": delivery["checksums"],
            "print_combined_preview": delivery["preview"],
            "sheet": os.path.relpath(os.path.join(ver_dir, "PRINT_SHEET.png"), ROOT),
            "layout_json": os.path.relpath(os.path.join(ver_dir, "layout.json"), ROOT),
            "renders": [stats["iso"]["file"], stats["top"]["file"]],
        },
        "validation": {
            "checks": layout["checks"],
            "print_bottom_equals_pocket_floor": layout["checks"][
                "print_bottom_on_pocket_floor"],
            "pocket_floor_vertices_found": layout["units"]["plate_unit"][
                "pocket_floor_vertices_found"],
            "print_bottom_bed_z_mm": layout["units"]["plate_unit"][
                "print_bottom_bed_z_mm"],
            "pocket_floor_bed_z_mm": layout["units"]["plate_unit"][
                "pocket_floor_bed_z_mm"],
            "renders": stats,
            "sheet_size": [SHEET_W, SHEET_H],
            "stl_delivery": {
                "count": delivery["count"],
                "total_bytes": delivery["total_bytes"],
                "all_sha256_match": delivery["all_sha256_match"],
                "checksums_file": delivery["checksums"],
            },
            "note": "bed layout + print-bottom assertions from measured bboxes; every "
                    "delivered STL sha256-verified against source; renders checked "
                    "non-black; sheet/copy sizes checked",
        },
    }
    with open(os.path.join(ver_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print("WROTE", os.path.relpath(os.path.join(ver_dir, "manifest.json"), ROOT))

    md = []
    md.append("# 3D 打印交付 — %s / %s\n" % (
        "圆形 LUMEN" if version == "round" else "方形 square_v1", layout["art"]))
    md.append("> PROVISIONAL：打印方向/支撑建议未实物验证；尺寸来自外观管线 STL + "
              "`shell.json` + Kromacut manifest。**真实可打印 STL 已复制到 `stl/`，"
              "sha256 见 `CHECKSUMS.sha256`。**\n")
    md.append("## 打印路线（二选一）\n")
    rt = routes(version)
    md.append("### A) 推荐 · 多材料原位粘合（PRINT_READY.3mf）\n")
    md.append(rt["A_recommended_multi_material_in_place"]["description"] + "\n")
    md.append("### B) 备选 · 无支撑（stl/ 分件）\n")
    md.append(rt["B_support_free_alternative"]["description"] + "\n")
    md.append("## 打印件 / STL 文件\n")
    md.append("| 零件 | STL（相对本目录） | 源文件 | 数量 | 材料/颜色 | 方向 | 支撑 |")
    md.append("|---|---|---|---|---|---|---|")
    for r in rows:
        md.append("| %s | `%s` | `%s` | %d | %s | %s | %s |" % (
            r["label"], r["stl"], r["file"], r["qty"], r["material"],
            r["orientation"], r["supports"]))
    md.append("\n### STL 文件清单（交付副本）\n")
    md.append("| 文件 | 大小 | sha256（前 16 位） | 用途 | 材料 |")
    md.append("|---|---|---|---|---|")
    for e in delivery["entries"]:
        md.append("| `%s` | %d B | `%s` | %s | %s |" % (
            e["rel"], e["bytes"], e["sha256"][:16], e["purpose"], e["material_hex"]))
    md.append("| `PRINT_READY.3mf` | %d B | `%s` | 路线 A 装配体 | 多色 |" % (
        delivery["threemf"]["bytes"], delivery["threemf"]["sha256"][:16]))
    md.append("\n- 单色预览 STL：**未交付**。" + PREVIEW_SKIP_REASON + "\n")
    md.append("## Bambu 导入顺序\n")
    for ln in manifest["bambu_import_order"]:
        md.append("- " + ln)
    md.append("\n## 采购件\n")
    md.append("、".join(purchased) + "\n")
    md.append("## 耗材表\n")
    md.append("| # | 色号 | 画面占比 | 三角数 |\n|---|---|---|---|")
    for f in art_d["filaments"]:
        md.append("| %d | %s | %.1f%% | %d |" % (
            f["number"], f["hex"], f["art_share_pct"], f["triangles"]))
    md.append("\n## 打印方向 / 支撑（PROVISIONAL）\n")
    md.append("- 路线 A：顶板凹槽朝上、印花嵌套（原位粘合），印花底面 = 槽底 "
              "z = %.2f mm。" % SC.resolve_assembly(version)["shell"]["floor_z_mm"])
    md.append("- 该姿态下顶板裙边/传力柱悬空 → 需树状支撑；未实物验证。")
    md.append("- 路线 B：顶板倒扣 + 印花单独平打，后压配/点胶（非原位粘合），无支撑。\n")
    md.append("## 排版与验证\n")
    md.append("- 床面：220×220 mm；本版占用 %.1f×%.1f mm，最小间距 %.2f mm。"
              % (layout["bed_bbox_mm"]["size"][0],
                 layout["bed_bbox_mm"]["size"][1], layout["min_gap_mm"]))
    for name, u in layout["units"].items():
        md.append("- %s：放置 (%.2f, %.2f) mm，bbox %s mm。" % (
            name, u["placement_xy_mm"][0], u["placement_xy_mm"][1],
            u["bbox_mm"]["size"]))
    md.append("- 断言全部通过：床面适配、无越界、间距 ≥5 mm、无重叠、印花底面 = "
              "槽底（%.3f mm）、印花厚度 %.2f mm。"
              % (layout["units"]["plate_unit"]["print_bottom_bed_z_mm"],
                 layout["units"]["plate_unit"]["print_thickness_mm"]))
    md.append("- 渲染非黑：iso mean %.2f / top mean %.2f；sheet 1800×1200。"
              % (stats["iso"]["mean"], stats["top"]["mean"]))
    md.append("- 交付 STL：%d 个 / %.1f MB，全部 sha256 与源文件一致。\n"
              % (delivery["count"], delivery["total_bytes"] / 1e6))
    md.append("## 打印参数建议\n")
    for k, v in slicer_settings().items():
        md.append("- **%s**: %s" % (k, v))
    md.append("\n## 文件\n")
    md.append("- `PRINT_SHEET.png`（1800×1200）")
    md.append("- `manifest.json` / `layout.json` / `CHECKSUMS.sha256`")
    md.append("- 源文件：`%s`、`%s`、`%s/`"
              % (layout["sources"]["shell_stl"], layout["sources"]["plate_stl"],
                 layout["sources"]["print_stl_dir"]))
    md.append("\n## 未验证\n")
    md.append("- 未在真实切片器中切片/打印；支撑与 z 间隙未实测。")
    md.append("- 3MF 中电子/玻璃/硅胶垫为参考几何，非打印件。")
    with open(os.path.join(ver_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("WROTE", os.path.relpath(os.path.join(ver_dir, "README.md"), ROOT))
    return manifest


# --------------------------------------------------------------------------- #
# combined board
# --------------------------------------------------------------------------- #
def make_combined_board(manifests):
    W, H = 2400, 1200
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((50, 34), "SmartCoaster — 3D 打印交付（两种外观版本）",
           font=F(44, True), fill=FG)
    d.text((52, 94),
           "真实可打印 STL + 装配体 3MF · 外壳 + 开槽顶板（含 Kromacut 印花） · "
           "凹槽朝上嵌套打印（路线 A） · 220×220 · PROVISIONAL",
           font=F(21), fill=MUT)
    d.line((50, 136, W - 50, 136), fill=(60, 64, 74), width=2)

    tiles = []
    for ver in ("round", "square"):
        m = manifests[ver]
        iso = Image.open(os.path.join(HERE, ver, "print_iso.png")).convert("RGB")
        iw = 1100
        ih = int(iw * iso.height / iso.width)
        tiles.append((ver, m, iso.resize((iw, ih), Image.LANCZOS)))

    for i, (ver, m, iso) in enumerate(tiles):
        x0 = 50 + i * 1200
        y0 = 168
        img.paste(iso, (x0, y0))
        d.rectangle((x0, y0, x0 + iso.width, y0 + iso.height),
                    outline=(60, 64, 74), width=2)
        title = ("圆形 LUMEN · dog 印花（6 色）" if ver == "round"
                 else "方形 square_v1 · elf 印花（7 色）")
        d.text((x0, y0 + iso.height + 16), title, font=F(28, True), fill=FG)
        pu = m["plate_print_unit"]
        bed = m["bed_bbox_mm"]["size"]
        info = ("床面占用 %.1f×%.1f mm · 最小间距 %.2f mm · 印花底面 z=%.2f mm "
                "＝槽底 z=%.2f mm" % (bed[0], bed[1], m["min_gap_mm"],
                                       pu["print_bottom_bed_z_mm"],
                                       pu["pocket_floor_bed_z_mm"]))
        d.text((x0, y0 + iso.height + 56), info, font=F(18), fill=MUT)
        v = m["validation"]["stl_delivery"]
        d.text((x0, y0 + iso.height + 84),
               "STL 交付：%d 个 / %.1f MB（sha256 全部一致）· stl/ + CHECKSUMS.sha256"
               % (v["count"], v["total_bytes"] / 1e6), font=F(17), fill=GREEN)

    ytab = 168 + tiles[0][2].height + 118
    d.line((50, ytab, W - 50, ytab), fill=(60, 64, 74), width=2)
    d.text((50, ytab + 16), "打印件：外壳 ×1 / 开槽顶板 ×1 / Kromacut 印花 ×1 / "
                            "方形按键 ×1（圆形无按键）  ·  采购件：OLED 玻璃、硅胶垫、"
                            "PCB、HY928D、ESP32-S3、HX711、USB-C、电池、M2 螺钉",
           font=F(20), fill=FG)
    d.text((50, ytab + 54),
           "路线 A（推荐 · 多材料原位粘合）：顶板凹槽朝上 + 印花嵌槽内同盘打印，"
           "裙边/传力柱需树状支撑（PROVISIONAL）；用 PRINT_READY.3mf。  "
           "路线 B（备选 · 无支撑）：顶板倒扣 + 印花单独平打，后压配/胶接；用 stl/ 分件。",
           font=F(18), fill=WARN)
    d.text((50, ytab + 90),
           "文件：render/print/appearance/{round,square}/{stl/, PRINT_READY.3mf, "
           "PRINT_SHEET.png, manifest.json, README.md, CHECKSUMS.sha256}  ·  "
           "Blender 4.5.3 Cycles CPU", font=F(15), fill=(110, 118, 132))
    out = os.path.join(HERE, "PRINT_SHEET_APPEARANCE.png")
    img.save(out)
    print("WROTE", os.path.relpath(out, ROOT), img.size)
    return out


def main():
    manifests = {}
    deliveries = {}
    for v in ("round", "square"):
        print("=" * 78)
        layout, art_d, stats, delivery = make_version_sheet(v)
        deliveries[v] = delivery
        manifests[v] = write_manifest(v, layout, art_d, stats, delivery)
    make_combined_board(manifests)

    print("=" * 78)
    ok = True
    for v, m in manifests.items():
        chk = m["validation"]["checks"]
        bad = [k for k, val in chk.items() if not val]
        deliv = deliveries[v]
        all_sha = deliv["all_sha256_match"]
        ok = ok and not bad and all_sha
        print("%-7s PRINT_SHEET=%s  PRINT_READY.3mf=%.2f MB  STL=%d / %.2f MB  "
              "sha256_match=%s  bed=%.1fx%.1f mm  min_gap=%.2f mm  "
              "print_bottom=%.3f mm  checks=%s"
              % (v, m["files"]["sheet"],
                 m["files"]["print_ready_3mf"]["bytes"] / 1e6,
                 deliv["count"], deliv["total_bytes"] / 1e6, all_sha,
                 m["bed_bbox_mm"]["size"][0], m["bed_bbox_mm"]["size"][1],
                 m["min_gap_mm"], m["validation"]["print_bottom_bed_z_mm"],
                 "OK" if not bad else "FAIL " + str(bad)))
        for e in deliv["entries"]:
            print("        STL %-58s %10d B  sha256=%s  match=%s"
                  % (e["rel"], e["bytes"], e["sha256"][:16], e["sha256_match"]))
        print("        3MF %-58s %10d B  sha256=%s" % (
            "PRINT_READY.3mf", m["files"]["print_ready_3mf"]["bytes"],
            m["files"]["print_ready_3mf"]["sha256"][:16]))
        for f in m["validation"]["renders"].values():
            print("        render %-47s mean=%5.1f std=%5.1f colors=%d"
                  % (f["file"], f["mean"], f["std"], f["unique_colors"]))
    print("PRINT DELIVERY ALL OK:", ok)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
