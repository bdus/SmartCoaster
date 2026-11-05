#!/usr/bin/env python3
"""Shape decision aid: square vs round vs two low-change variants.

Top views are drawn to scale (1 mm = 2.8 px) with a Ø85 mug outline, so the
cup-to-body relationship is directly comparable. This is a discussion diagram,
not CAD; the frozen square geometry is untouched.

Run:  python3 render/appearance/shape/make_shape_options.py
Out:  render/appearance/shape/00_shape_options.png
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFont

OUT = "/data/Documents/projects/SmartCoaster/render/appearance/shape/00_shape_options.png"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

S = 2.8                     # px per mm
PANEL_W, PANEL_H = 410, 500
GAP = 24
MARGIN = 36
HEADER = 132
FOOTER = 42
W = MARGIN * 2 + PANEL_W * 4 + GAP * 3
H = HEADER + PANEL_H + FOOTER

BG = (16, 18, 23)
CARD = (25, 28, 35)
BODY = (44, 49, 59)
PLATE = (62, 69, 82)
EDGE = (96, 104, 120)
CUP = (147, 158, 178)
WIN = (86, 214, 255)
BTN = (185, 166, 255)
FG = (235, 239, 245)
MUT = (152, 160, 174)
DIM = (112, 120, 134)
ACC = (126, 110, 234)


def F(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def dashed_circle(d, cx, cy, r, fill, width=2, dash=7, gap=5):
    circ = 2 * math.pi * r
    step = dash + gap
    n = max(8, int(circ / step))
    for i in range(n):
        a0 = 360.0 * i / n
        a1 = a0 + 360.0 * dash / step / n
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=fill, width=width)


def cross(d, cx, cy, color=MUT, r=4):
    d.line([cx - r, cy, cx + r, cy], fill=color, width=1)
    d.line([cx, cy - r, cx, cy + r], fill=color, width=1)


def front_marks(d, cx, y, scale=S):
    """Front-face callout: 26 mm window bar + Ø8.2 button, projected on the edge."""
    wx = cx + (-8) * scale
    bx = cx + 17 * scale
    w = 26 * scale
    d.line([wx - w / 2, y - 3, wx + w / 2, y - 3], fill=WIN, width=5)
    br = 8.2 / 2 * scale
    d.ellipse([bx - br, y - 3 - br, bx + br, y - 3 + br], fill=BTN, outline=(30, 26, 46))


def cup(d, cx, cy, scale=S):
    r = 85 / 2 * scale
    dashed_circle(d, cx, cy, r, CUP, width=2)
    d.text((cx - 22, cy - r - 20), "Ø85 杯", font=F(15), fill=CUP)


def square_top(d, cx, cy, radius_px, scale=S, plate_r=None):
    half = 50 * scale
    d.rounded_rectangle([cx - half, cy - half, cx + half, cy + half],
                        radius=radius_px, fill=BODY, outline=EDGE, width=2)
    if plate_r:
        pr = plate_r * scale
        d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=PLATE, outline=EDGE, width=2)
    else:
        inset = 3 * scale
        d.rounded_rectangle([cx - half + inset, cy - half + inset,
                             cx + half - inset, cy + half - inset],
                            radius=max(0, radius_px - inset), outline=(80, 88, 104), width=1)
    cross(d, cx, cy)
    front_marks(d, cx, cy + half)


def round_top(d, cx, cy, r, scale=S):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BODY, outline=EDGE, width=2)
    pr = 52 * scale
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=PLATE, outline=(80, 88, 104), width=1)
    cross(d, cx, cy)
    front_marks(d, cx, cy + r)


PANELS = [
    dict(title="A · 方形（现状）", sub="100×100 R8 · 零改动",
         bullets=["机械 / PCB / 包装全部冻结",
                  "Ø85 杯居中：边余量 7.5 mm",
                  "对角 70.7 mm：偏载力臂最大"]),
    dict(title="B · 圆形（LUMEN）", sub="Ø110×17 · 需机械+PCB 改版",
         bullets=["全向余量 12.5 mm，最像杯垫",
                  "最远边缘 55 mm（比方角短 22%）",
                  "需重排圆形 PCB 与包装"]),
    dict(title="C · 方底座 + 圆浮板", sub="Ø96 圆盘 · 受控改版",
         bullets=["杯子落在圆盘上，方体朝前",
                  "前面板 / 内部 / PCB 保留",
                  "只改顶板 + 壳口 + 裙边"]),
    dict(title="D · 大圆角（squircle）", sub="100×100 R24 · 低成本软化",
         bullets=["轮廓去尖角，仍是 100×100",
                  "前面板仍够排 26×7 屏 + 键",
                  "内部基本不动，只改角半径"]),
]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 28), "SmartCoaster · 形状决策：杯是圆的，杯垫该圆还是方？",
           font=F(38, True), fill=FG)
    d.text((MARGIN, 82),
           "顶视示意，按 1:1 比例绘制（1 mm ≈ 2.8 px）· 杯 Ø85 为常见马克杯 · 仅用于形状讨论，实际几何以 CAD 为准",
           font=F(18), fill=MUT)
    tag = "SHAPE DECISION"
    tw = d.textlength(tag, font=F(20, True))
    d.text((W - MARGIN - tw, 40), tag, font=F(20, True), fill=ACC)

    for i, p in enumerate(PANELS):
        x = MARGIN + i * (PANEL_W + GAP)
        y = HEADER
        d.rounded_rectangle([x, y, x + PANEL_W, y + PANEL_H], radius=14, fill=CARD)
        cx, cy = x + PANEL_W // 2, y + 168
        if i == 0:
            square_top(d, cx, cy, radius_px=8 * S)
        elif i == 1:
            round_top(d, cx, cy, 55 * S)
        elif i == 2:
            square_top(d, cx, cy, radius_px=8 * S, plate_r=48)
        else:
            square_top(d, cx, cy, radius_px=24 * S)
        cup(d, cx, cy)
        d.text((x + 22, y + 336), p["title"], font=F(24, True), fill=FG)
        d.text((x + 22, y + 368), p["sub"], font=F(15), fill=MUT)
        for j, b in enumerate(p["bullets"]):
            d.text((x + 22, y + 400 + j * 24), "· " + b, font=F(15), fill=DIM)

    d.text((MARGIN, H - 30),
           "render/appearance/shape/make_shape_options.py　·　比例约 1:1　·　"
           "方形的 26×7 屏与 Ø8.2 键位置按现行 B 版投影；圆形/混合款的前窗需随造型重排，功能不变",
           font=F(15), fill=(96, 104, 118))
    sheet.save(OUT)
    print("WROTE", OUT, sheet.size)


if __name__ == "__main__":
    main()
