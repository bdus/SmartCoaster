#!/usr/bin/env python3
"""Compose the "existing appearance versions" inventory sheet.

Purpose
-------
One-page visual index of every product appearance asset that already exists in
the repo (square + round, all colours), so the multi-round appearance iteration
starts from a shared, explicit baseline. This script only reads existing PNGs;
it does not re-render and does not touch the product geometry.

Run:
  python3 render/appearance/make_inventory.py
Output:
  render/appearance/00_inventory_existing.png
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = "/data/Documents/projects/SmartCoaster"
OUT = f"{ROOT}/render/appearance/00_inventory_existing.png"

BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# Canvas geometry
W, H = 1800, 1385
MARGIN = 40
TILE = 400
GAP = 40
ROW1_Y = 218
ROW2_Y = 800

BG = (17, 19, 24)
CARD = (26, 29, 36)
FG = (234, 238, 244)
MUT = (150, 158, 172)
DIM = (110, 118, 132)
ACC = (124, 108, 232)
CYAN = (92, 214, 255)


def F(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def hexrgb(h: str):
    return tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


TILES = [
    # ---- row 1: square B, 4 colourways --------------------------------
    dict(
        img="render/cmf/lumen_violet.png",
        label="Lumen Violet 紫罗兰",
        sub="B 版默认 · 顶板 #6B40A0 · 壳体 #2A2E35",
        sw=[("#6B40A0", "顶板"), ("#2A2E35", "壳体")],
    ),
    dict(
        img="render/cmf/moss.png",
        label="Moss 苔绿",
        sub="顶板 #4F6B4A · 壳体 #2B302B · 按键同顶板",
        sw=[("#4F6B4A", "顶板"), ("#2B302B", "壳体")],
    ),
    dict(
        img="render/cmf/sand.png",
        label="Sand 沙色",
        sub="顶板 #C9B79A · 壳体 #3A3530 · 按键同顶板",
        sw=[("#C9B79A", "顶板"), ("#3A3530", "壳体")],
    ),
    dict(
        img="render/cmf/graphite.png",
        label="Graphite 石墨",
        sub="顶板 #3A3D42 · 壳体 #1E2024 · 红按键",
        sw=[("#3A3D42", "顶板"), ("#1E2024", "壳体"), ("#942826", "按键")],
    ),
    # ---- row 2: square baseline/front, then round ---------------------
    dict(
        img="mechanical/square_v1/build/render/hero.png",
        label="P1 白 / 浅灰基线",
        sub="M1.2 基线渲染 · VTK 中性白/浅灰 · 非 B 版",
        sw=[],
    ),
    dict(
        img="render/square_b/renders/front.png",
        label="B 版前脸（现行）",
        sub="26×7 窗 x=−8 · Ø8.2 按键 x=17",
        sw=[],
    ),
    dict(
        img="mechanical/lumen/build/render/hero.png",
        label="LUMEN 白 / 银",
        sub="暖白壳 + 银铝顶板 + 青色光晕（VTK）",
        sw=[],
        tag="圆形",
    ),
    dict(
        img="render/lumen/renders/hero.png",
        label="LUMEN 石墨黑",
        sub="深灰壳 + 金属顶板 + 青色光缝（含光导）",
        sw=[],
        tag="圆形",
    ),
]


def fit(im: Image.Image, box: int) -> Image.Image:
    """Contain-fit into a square tile, centred."""
    im = im.convert("RGB")
    im.thumbnail((box, box), Image.LANCZOS)
    canvas = Image.new("RGB", (box, box), CARD)
    canvas.paste(im, ((box - im.width) // 2, (box - im.height) // 2))
    return canvas


def main():
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    # header
    d.text((MARGIN, 34), "SmartCoaster · 已有外观版本盘点", font=F(46, True), fill=FG)
    d.text((MARGIN, 96),
           "方形 100×100×18 / R8 · 圆形 Ø110×17　｜　盘点日期 2026-11-04　｜　几何已冻结，后续只改外观",
           font=F(23), fill=MUT)
    tag = "GEOMETRY FROZEN · NO LED"
    tw = d.textlength(tag, font=F(24, True))
    d.text((W - MARGIN - tw, 44), tag, font=F(24, True), fill=ACC)

    # section labels
    d.text((MARGIN, 168), "方形 · B 版 4 个配色（2026-11-04 按“无灯”重渲，当前主资产）",
           font=F(26, True), fill=FG)
    d.text((MARGIN, 752), "方形 · 原始基线 / 当前前脸", font=F(26, True), fill=FG)
    d.text((MARGIN + 2 * TILE + GAP + 40, 752),
           "圆形 · LUMEN 现有 2 种外观", font=F(26, True), fill=FG)

    # divider between square and round halves on row 2
    div_x = MARGIN + 2 * TILE + GAP + 10
    d.line([(div_x, ROW2_Y - 12), (div_x, ROW2_Y + TILE + 74)], fill=(52, 56, 68), width=2)

    for i, t in enumerate(TILES):
        col = i % 4
        row = i // 4
        x = MARGIN + col * (TILE + GAP)
        y = ROW1_Y if row == 0 else ROW2_Y
        path = os.path.join(ROOT, t["img"])
        if not os.path.exists(path):
            print("MISSING", path)
        else:
            tile = fit(Image.open(path), TILE)
            sheet.paste(tile, (x, y))
        d.rectangle([x - 1, y - 1, x + TILE, y + TILE], outline=(48, 52, 62), width=1)
        d.text((x, y + TILE + 14), t["label"], font=F(27, True), fill=FG)
        d.text((x, y + TILE + 50), t["sub"], font=F(17), fill=MUT)
        # swatches
        sx = x
        for hexv, name in t["sw"]:
            d.rectangle([sx, y + TILE + 78, sx + 26, y + TILE + 104], fill=hexrgb(hexv),
                        outline=(70, 74, 86))
            d.text((sx + 34, y + TILE + 82), name, font=F(17), fill=DIM)
            sx += 34 + int(d.textlength(name, font=F(17))) + 22

    # footer
    d.text((MARGIN, H - 42),
           "render/appearance/make_inventory.py　·　完整资产路径见 render/appearance/README.md　·　现有配色只作用于"
           " shell / plate / button，其余件沿用中性色",
           font=F(17), fill=(96, 104, 118))
    sheet.save(OUT)
    print("WROTE", OUT, sheet.size)


if __name__ == "__main__":
    main()
