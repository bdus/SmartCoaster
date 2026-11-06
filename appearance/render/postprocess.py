#!/usr/bin/env python3
"""Post-process the SmartCoaster appearance renders.

1. appearance/render/<v>/macro_edge.png
   Cycles raw render from appearance/build/render/<v>/macro_edge.png + a fit
   caption (pocket Ø86.0 / print Ø86.4, nominal 0.200 -> max 0.288 mm radial
   interference, 0.05 mm below rim).  All numbers are formatted from
   scene_info.json values with 3 decimals and numerically asserted.
2. appearance/render/<v>/section_exploded.png
   two-panel composition (2400x1200):
     left  = 1/4 clipped section, print seated on the pocket floor, 5 call-outs
     right = exploded panel (print lifted +6 mm clear of the plate pocket) and a
             schematic FIT DETAIL inset fully inside the canvas
3. appearance/render/board.png
   labelled side-by-side board of round (LUMEN + dog) and square (square_v1 + elf):
   hero renders top row, macro_edge crops bottom row.

Run: python3 appearance/render/postprocess.py [--skip-section] [--skip-board]
"""
import argparse
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene_common as SC  # noqa: E402

ROOT = SC.ROOT
RENDER = os.path.join(ROOT, "appearance", "render")
RAW = os.path.join(ROOT, "appearance", "build", "render")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

PALETTE = {
    "print_top": (255, 214, 120),
    "print_bottom": (255, 214, 120),
    "pocket_floor": (140, 220, 255),
    "plate_rim": (255, 255, 255),
    "pocket_wall": (255, 140, 150),
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def font(size, bold=False):
    p = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    try:
        return ImageFont.truetype(p, size)
    except OSError:
        return ImageFont.load_default()


def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def load_info(version):
    p = os.path.join(RENDER, version, "scene_info.json")
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def real_numbers(version):
    """Merge shell.json/manifest values with the measured render-geometry values."""
    spec = SC.resolve_assembly(version)
    info = load_info(version)
    sh = dict(spec["shell"])
    pr = dict(spec["print"])
    if info:
        sh.update(info.get("shell", {}) or {})
        pr.update({k: v for k, v in (info.get("print") or {}).items()
                   if k != "objects"})
    env = pr.get("envelope") or {}
    floor = float(sh["floor_z_mm"])
    thk = float(sh.get("print_thickness_mm") or 1.2)
    rim = float(sh.get("rim_z_mm") or floor + thk + 0.05)
    pocket_r = (sh.get("pocket_dia_mm") or 86.0) / 2.0
    nominal = float(sh.get("interference_mm") or 0.2)
    top = float(env.get("top_z_mm")) if env else floor + thk
    max_r = float(pr["max_radius_mm"]) if pr.get("max_radius_mm") else pocket_r
    max_int = (float(pr["actual_max_interference_mm"])
               if pr.get("actual_max_interference_mm") is not None
               else max_r - pocket_r)
    rn = {
        "spec": spec, "sh": sh, "pr": pr, "env": env,
        "floor": floor, "rim": rim, "thk": thk, "top": top,
        "gap": rim - top, "pocket_dia": pocket_r * 2.0,
        "pocket_r": pocket_r, "print_dia": float(sh.get("print_dia_mm") or 86.4),
        "nominal": nominal, "max_int": max_int, "max_r": max_r,
        "nfil": len(spec["print"]["objects"]),
        "art": spec["art"], "label": spec["label"],
    }
    verify_numbers(rn)
    return rn


def verify_numbers(rn):
    """Fail the build if any geometry number is implausible or mis-formatted."""
    errs = []
    if not (40.0 < rn["max_r"] < 45.0):
        errs.append("max print radius %.4f mm not in (40,45)" % rn["max_r"])
    if not (42.0 < rn["pocket_r"] < 44.5):
        errs.append("pocket radius %.4f mm not in (42,44.5)" % rn["pocket_r"])
    if not (0.0 < rn["max_int"] < 1.0):
        errs.append("max radial interference %.4f mm not in (0,1)" % rn["max_int"])
    if not (0.0 < rn["nominal"] < 1.0):
        errs.append("nominal radial interference %.4f mm not in (0,1)" % rn["nominal"])
    if abs(rn["max_int"] - (rn["max_r"] - rn["pocket_r"])) > 0.002:
        errs.append("max interference %.4f != max_radius - pocket_radius"
                    % rn["max_int"])
    if abs((rn["floor"] + rn["thk"]) - rn["top"]) > 0.01:
        errs.append("print top %.4f != floor + thickness" % rn["top"])
    if abs((rn["rim"] - rn["top"]) - rn["gap"]) > 0.02:
        errs.append("rim - top %.4f != documented gap %.4f"
                    % (rn["rim"] - rn["top"], rn["gap"]))
    if not (0.5 < rn["thk"] < 3.0):
        errs.append("print thickness %.4f mm not in (0.5,3)" % rn["thk"])
    # every number that reaches a label must format as a plain 3-decimal value
    for key in ("max_r", "pocket_r", "max_int", "nominal", "floor", "rim",
                "top", "gap", "thk"):
        s = "%.3f" % rn[key]
        if not re.fullmatch(r"-?\d+\.\d{3}", s):
            errs.append("bad label format for %s: %r" % (key, s))
    if abs(float("%.3f" % rn["max_r"]) - 43.288) > 0.002:
        errs.append("formatted max radius %.3f is not the measured 43.288 mm"
                    % rn["max_r"])
    if errs:
        raise SystemExit("NUMBER ASSERTION FAILED (%s): %s"
                         % (rn["spec"]["version"], "; ".join(errs)))
    rn["staircase"] = rn["max_int"] - rn["nominal"]


# --------------------------------------------------------------------------- #
# macro caption
# --------------------------------------------------------------------------- #
def scene_info_exists(version):
    return os.path.exists(os.path.join(RENDER, version, "scene_info.json"))


def annotate_macro(version):
    raw = os.path.join(RAW, version, "macro_edge.png")
    out = os.path.join(RENDER, version, "macro_edge.png")
    if not (os.path.exists(raw) and scene_info_exists(version)):
        print("SKIP macro %s: raw render / scene_info missing" % version)
        return False
    rn = real_numbers(version)
    img = Image.open(raw).convert("RGBA")
    bar_h = 118
    ov = Image.new("RGBA", (img.width, bar_h), (8, 9, 12, 216))
    d = ImageDraw.Draw(ov)
    d.text((26, 14), "MACRO \u2014 PRINT RIM SEATED IN THE RECESSED POCKET",
           font=font(28, True), fill=(255, 255, 255, 255))
    d.text((26, 54),
           "POCKET \u00d8%.1f (r %.3f mm) \u00b7 PRINT \u00d8%.1f (max vertex "
           "radius %.3f mm) \u00b7 %.3f mm max radial interference"
           % (rn["pocket_dia"], rn["pocket_r"], rn["print_dia"], rn["max_r"],
              rn["max_int"]),
           font=font(20), fill=(206, 210, 220, 255))
    d.text((26, 82),
           "%.3f mm nominal + %.3f mm pixel-staircase \u00b7 print top z %.2f mm "
           "= %.2f mm below rim z %.2f mm"
           % (rn["nominal"], rn["staircase"], rn["top"], rn["gap"], rn["rim"]),
           font=font(20), fill=(160, 166, 180, 255))
    img.alpha_composite(ov, (0, img.height - bar_h))
    img.convert("RGB").save(out)
    print("WROTE", os.path.relpath(out, ROOT))
    return True


# --------------------------------------------------------------------------- #
# section composition
# --------------------------------------------------------------------------- #
def section_lines(rn):
    return [
        ("PRINT  \u00d8%.1f \u00d7 %.2f mm \u00b7 %s \u00b7 %d filaments"
         % (rn["print_dia"], rn["thk"], rn["art"], rn["nfil"]), "print_top"),
        ("POCKET \u00d8%.1f \u00b7 floor z %.2f mm \u00b7 rim z %.2f mm"
         % (rn["pocket_dia"], rn["floor"], rn["rim"]), "pocket_floor"),
        ("PRINT TOP z %.2f = rim %.2f \u2212 %.2f mm"
         % (rn["top"], rn["rim"], rn["gap"]), "plate_rim"),
        ("PRINT BOTTOM z %.2f \u00b7 seated on the pocket floor" % rn["floor"],
         "print_bottom"),
        ("RADIAL %.3f mm max (%.3f nominal + %.3f staircase) \u00b7 fused in slicer"
         % (rn["max_int"], rn["nominal"], rn["staircase"]), "pocket_wall"),
    ]


def annotate_main(main, ann, rn):
    img = main.convert("RGBA")
    dr = ImageDraw.Draw(img)
    w, h = img.size
    pts = {k: (v[0] * w, (1.0 - v[1]) * h) for k, v in ann["points"].items()}

    panel = (22, 22, 1010, 318)
    rounded(dr, panel, 16, (9, 10, 13, 228))
    dr.rectangle(panel, outline=(70, 74, 84, 255), width=2)
    dr.text((40, 34), "EMBEDDED KROMACUT PRINT \u2014 1/4 SECTION",
            font=font(26, True), fill=(255, 255, 255, 255))
    dr.text((40, 66), "%s shell \u00b7 %s \u00b7 print bottom on pocket floor"
            % (rn["label"], rn["art"]), font=font(18), fill=(170, 176, 190, 255))

    y = 100
    anchors = []
    for line, key in section_lines(rn):
        color = PALETTE.get(key, (230, 230, 230))
        dr.ellipse((40, y + 7, 52, y + 19), fill=color + (255,))
        dr.text((64, y), line, font=font(19), fill=(232, 235, 242, 255))
        anchors.append((key, (panel[2] - 6, y + 10), color))
        y += 38

    for key, anchor, color in anchors:
        if key not in pts:
            continue
        px, py = pts[key]
        dr.line([anchor, (px, py)], fill=color + (200,), width=2)
        r = 7
        dr.ellipse((px - r, py - r, px + r, py + r), outline=color + (255,), width=3)
        dr.ellipse((px - 2, py - 2, px + 2, py + 2), fill=color + (255,))
    return img


def crop_to_content(img, pad=18, thresh=18):
    """Crop a render to the non-background pixels (for the exploded panel)."""
    a = np.asarray(img.convert("RGB"), dtype=np.uint8)
    mask = a.max(axis=2) > thresh
    if not mask.any():
        return img
    ys, xs = np.where(mask)
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(img.width, int(xs.max()) + pad)
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(img.height, int(ys.max()) + pad)
    return img.crop((x0, y0, x1, y1))


def fit_detail(draw, box, rn):
    """Schematic cross-section of the print/plate fit; fully inside `box`."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    rounded(draw, (x0, y0, x1, y1), 12, (17, 18, 23, 255))
    draw.text((x0 + 18, y0 + 10), "FIT DETAIL \u2014 schematic, exaggerated",
              font=font(19, True), fill=(255, 255, 255, 255))
    thk, max_int, nominal, gap = rn["thk"], rn["max_int"], rn["nominal"], rn["gap"]
    sx = 100.0                      # px per mm radially
    sy = 130.0                      # px per mm vertically
    bx = x0 + w * 0.5 + 60.0        # pocket wall position
    by = y1 - 55.0                  # plate bottom line
    plate = (bx, by - thk * sy, bx + 1.2 * sx, by)
    draw.rectangle(plate, fill=(107, 64, 160, 255), outline=(180, 140, 230, 255))
    draw.text((bx + 0.22 * sx, by - 26), "PLATE", font=font(15),
              fill=(235, 226, 246, 255))
    pr = (bx - 2.4 * sx, by - thk * sy, bx + max_int * sx, by - gap * sy)
    draw.rectangle(pr, fill=(247, 239, 227, 255), outline=(255, 255, 255, 255))
    draw.text((bx - 2.25 * sx, by - 26), "PRINT", font=font(15),
              fill=(60, 55, 50, 255))
    # rim line
    draw.line([(bx - 2.5 * sx, by - thk * sy - 2),
               (bx + 1.3 * sx, by - thk * sy - 2)],
              fill=(255, 214, 120, 255), width=2)
    # interference arrows (nominal then pixel-staircase), inside the panel
    ay = by - thk * sy * 0.55
    draw.line([(bx, ay), (bx + nominal * sx, ay)],
              fill=(255, 120, 130, 255), width=4)
    draw.line([(bx + nominal * sx, ay), (bx + max_int * sx, ay)],
              fill=(255, 196, 120, 255), width=3)
    draw.text((bx + max_int * sx + 8, ay - 24),
              "%.3f max" % max_int, font=font(14, True),
              fill=(255, 196, 120, 255))
    draw.text((bx + 4, ay + 7), "%.3f nominal" % nominal, font=font(13),
              fill=(255, 140, 150, 255))
    # 0.05 mm step
    vx = bx - 2.35 * sx
    draw.line([(vx, by - thk * sy), (vx, by - thk * sy - gap * sy)],
              fill=(255, 214, 120, 255), width=3)
    draw.text((vx + 8, by - thk * sy - gap * sy - 18),
              "%.2f mm step" % gap, font=font(14, True),
              fill=(255, 214, 120, 255))
    draw.text((x0 + 18, y1 - 24),
              "pocket \u00d8%.1f \u00b7 print \u00d8%.1f \u00b7 floor z %.2f"
              % (rn["pocket_dia"], rn["print_dia"], rn["floor"]),
              font=font(14), fill=(160, 166, 180, 255))


def compose_section(version):
    main_p = os.path.join(RAW, version, "section_seated.png")
    expl_p = os.path.join(RAW, version, "section_exploded.png")
    ann_p = os.path.join(RENDER, version, "annotations.json")
    out = os.path.join(RENDER, version, "section_exploded.png")
    if not (os.path.exists(main_p) and os.path.exists(ann_p)
            and scene_info_exists(version)):
        print("SKIP section %s: raw renders / scene_info missing" % version)
        return False
    rn = real_numbers(version)
    main = annotate_main(Image.open(main_p).convert("RGB"),
                         json.load(open(ann_p)), rn).convert("RGB")

    colw = 800
    canvas = Image.new("RGB", (1600 + colw, 1200), (11, 12, 15))
    canvas.paste(main, (0, 0))
    dr = ImageDraw.Draw(canvas, "RGBA")
    dr.rectangle((1600, 0, 2400, 1200), fill=(15, 16, 20, 255))
    dr.line([(1600, 0), (1600, 1200)], fill=(60, 64, 74, 255), width=2)
    dr.text((1624, 26), "EXPLODED \u2014 PRINT OUT OF THE POCKET",
            font=font(28, True), fill=(255, 255, 255, 255))
    dr.text((1624, 64), "%s  \u00b7  %s  \u00b7  print lifted +6.0 mm"
            % (rn["label"], rn["art"]), font=font(18),
            fill=(178, 184, 198, 255))

    if os.path.exists(expl_p):
        ins = crop_to_content(Image.open(expl_p).convert("RGB"))
        tile = 760
        s = tile / max(ins.width, ins.height)
        ins = ins.resize((max(1, int(ins.width * s)), max(1, int(ins.height * s))),
                         Image.LANCZOS)
        frame = Image.new("RGB", (tile, tile), (10, 11, 14))
        frame.paste(ins, ((tile - ins.width) // 2, (tile - ins.height) // 2))
        canvas.paste(frame, (1620, 100))
        dr.rectangle((1620, 100, 2380, 860), outline=(70, 74, 84, 255), width=2)
        dr.text((1620, 872),
                "plate + print only \u00b7 print lifted +6.0 mm \u00b7 assembled "
                "print z %.2f\u2013%.2f mm" % (rn["floor"], rn["top"]),
                font=font(16), fill=(200, 205, 215, 255))

    # numeric fit summary (text only: no inset can be clipped)
    lines = [
        "FIT SUMMARY (nominal, from shell.json + Kromacut manifest)",
        "print \u00d8%.1f  \u00b7  pocket \u00d8%.1f  \u00b7  floor z %.2f mm"
        % (rn["print_dia"], rn["pocket_dia"], rn["floor"]),
        "print top z %.2f mm  \u00b7  rim z %.2f mm  \u00b7  %.2f mm below rim"
        % (rn["top"], rn["rim"], rn["gap"]),
        "radial interference %.3f mm nominal  \u00b7  %.3f mm max"
        % (rn["nominal"], rn["max_int"]),
        "(%.3f mm pixel-staircase corners)  \u00b7  shell + print are separate objects"
        % rn["staircase"],
    ]
    yy = 940
    for i, line in enumerate(lines):
        dr.text((1624, yy), line, font=font(18 if i == 0 else 17),
                fill=(255, 255, 255, 255) if i == 0 else (188, 194, 208, 255))
        yy += 34
    dr.text((1624, 1158),
            "fused only at slice time in Bambu Studio  \u00b7  composited by postprocess.py",
            font=font(14), fill=(130, 136, 150, 255))
    canvas.save(out)
    print("WROTE", os.path.relpath(out, ROOT))
    return True


# --------------------------------------------------------------------------- #
# comparison board
# --------------------------------------------------------------------------- #
def crop_square(img, size):
    w, h = img.size
    s = min(w, h, size)
    x = (w - s) // 2
    y = (h - s) // 2
    return img.crop((x, y, x + s, y + s)).resize((size, size), Image.LANCZOS)


def draw_label_bar(img, text, sub, color=(255, 255, 255), h=96):
    ov = Image.new("RGBA", (img.width, h), (8, 9, 12, 205))
    d = ImageDraw.Draw(ov)
    d.text((22, 14), text, font=font(30, True), fill=color + (255,))
    d.text((22, 56), sub, font=font(20), fill=(196, 200, 210, 255))
    img.alpha_composite(ov, (0, img.height - h))


def make_board():
    tiles = []
    for ver in ("round", "square"):
        if not scene_info_exists(ver):
            print("SKIP board: scene_info missing for", ver)
            return False
        rn = real_numbers(ver)
        labels = {
            "hero": ("%s \u00b7 %s art" % (rn["spec"]["tag"], rn["art"]),
                     "%d-filament Kromacut print \u00b7 pocket \u00d8%.1f \u00b7 "
                     "%.2f mm below rim"
                     % (rn["nfil"], rn["pocket_dia"], rn["gap"])),
            "macro_edge": ("%s \u00b7 MICRO EDGE" % ver.upper(),
                           "print rim in pocket \u00b7 %.3f mm max radial "
                           "interference (%.3f nominal)"
                           % (rn["max_int"], rn["nominal"])),
        }
        for view in ("hero", "macro_edge"):
            p = os.path.join(RENDER, ver, view + ".png")
            if not os.path.exists(p):
                print("SKIP board: missing", os.path.relpath(p, ROOT))
                return False
            tiles.append((ver, view, Image.open(p).convert("RGB"), labels[view]))

    margin, gap, tile = 40, 36, 1080
    width = margin * 2 + tile * 2 + gap
    height = margin + 96 + tile * 2 + gap + 74
    canvas = Image.new("RGB", (width, height), (12, 13, 16))
    dr = ImageDraw.Draw(canvas)
    dr.text((margin, 26),
            "SmartCoaster \u2014 real shell + embedded Kromacut multi-material print",
            font=font(40, True), fill=(255, 255, 255))
    dr.text((margin, 78),
            "Blender 4.5.3 \u00b7 Cycles CPU \u00b7 shell and print are separate objects; "
            "fused only at slice time in Bambu Studio",
            font=font(20), fill=(168, 174, 188))

    y0 = margin + 96
    for i, (ver, view, img, (text, sub)) in enumerate(tiles):
        row, col = divmod(i, 2)
        tile_img = crop_square(img, tile).convert("RGBA")
        draw_label_bar(tile_img, text, sub)
        x = margin + col * (tile + gap)
        y = y0 + row * (tile + gap)
        canvas.paste(tile_img.convert("RGB"), (x, y))
        dr.rectangle((x, y, x + tile, y + tile), outline=(58, 62, 72), width=2)
    dr.text((margin, height - 52),
            "shell #2A2E35 / plate #6B40A0 (lumen_violet) \u00b7 print palette from "
            "Kromacut manifest \u00b7 renders: appearance/render/{round,square}/",
            font=font(17), fill=(140, 146, 160))
    out = os.path.join(RENDER, "board.png")
    canvas.save(out)
    print("WROTE", os.path.relpath(out, ROOT), canvas.size)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-section", action="store_true")
    ap.add_argument("--skip-board", action="store_true")
    args = ap.parse_args()
    if not args.skip_section:
        for v in ("round", "square"):
            annotate_macro(v)
            compose_section(v)
    if not args.skip_board:
        make_board()


if __name__ == "__main__":
    main()
