#!/usr/bin/env python3
"""Print-zone / layout diagram for the round top-plate print (flat silk print only)."""
import math

from PIL import Image, ImageDraw, ImageFont

OUT = "/data/Documents/projects/SmartCoaster/render/appearance/round/01_print_zones.png"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

W, H = 1560, 840
BG = (17, 19, 24)
CARD = (26, 29, 36)
PLATE = (232, 226, 213)
BAND = (244, 238, 224)
CUP = (150, 158, 172)
FG = (234, 238, 244)
MUT = (150, 158, 172)
DIM = (112, 120, 134)
ACC = (124, 108, 232)
GOLD = (196, 168, 110)
SAGE = (143, 176, 150)


def F(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def dashed_circle(d, cx, cy, r, fill, width=2, dash=10, gap=6):
    n = max(12, int(2 * math.pi * r / (dash + gap)))
    for i in range(n):
        a0 = 360.0 * i / n
        a1 = a0 + 360.0 * dash / (dash + gap) / n
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=fill, width=width)


def star(d, cx, cy, r, color, width=2):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        a = math.radians(-90 + 36 * i)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.line(pts + [pts[0]], fill=color, width=width)


def paw(d, cx, cy, r, color, width=2):
    d.ellipse([cx - r * 0.55, cy - r * 0.15, cx + r * 0.55, cy + r * 0.9],
              outline=color, width=width)
    for i, ang in enumerate((-150, -110, -70, -30)):
        a = math.radians(ang)
        px = cx + r * 0.82 * math.cos(a)
        py = cy + r * 0.82 * math.sin(a)
        d.ellipse([px - r * 0.26, py - r * 0.26, px + r * 0.26, py + r * 0.26],
                  outline=color, width=width)


def flower(d, cx, cy, r, color, width=2):
    for i in range(5):
        a = math.radians(72 * i - 90)
        px = cx + r * 0.55 * math.cos(a)
        py = cy + r * 0.55 * math.sin(a)
        d.ellipse([px - r * 0.42, py - r * 0.42, px + r * 0.42, py + r * 0.42],
                  outline=color, width=width)
    d.ellipse([cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16],
              fill=color)


S = 4.0  # px per mm


def top_view(d, x, y, layout):
    cx, cy = x + 240, y + 220
    rp = 52 * S
    rc = 42.5 * S
    d.ellipse([cx - rp, cy - rp, cx + rp, cy + rp], fill=PLATE, outline=(70, 66, 58), width=2)
    # printable annulus
    d.ellipse([cx - rp + 4, cy - rp + 4, cx + rp - 4, cy + rp - 4],
              outline=(210, 200, 182), width=1)
    d.ellipse([cx - (rp + rc) / 2, cy - (rp + rc) / 2,
               cx + (rp + rc) / 2, cy + (rp + rc) / 2],
              outline=(214, 205, 188), width=1)
    dashed_circle(d, cx, cy, rc, CUP, width=2)
    # centre cross
    d.line([cx - 5, cy, cx + 5, cy], fill=(170, 164, 150), width=1)
    d.line([cx, cy - 5, cx, cy + 5], fill=(170, 164, 150), width=1)

    if layout == "front":
        # one main motif on the front arc (6 o'clock) + two small stars
        star(d, cx, cy + 47 * S, 4 * S, GOLD, width=3)
        paw(d, cx - 17 * S, cy + 45.5 * S, 3.2 * S, ACC, width=2)
        flower(d, cx + 17 * S, cy + 45.5 * S, 3.0 * S, SAGE, width=2)
    else:
        for i in range(12):
            a = math.radians(360 * i / 12)
            px = cx + 47 * S * math.cos(a)
            py = cy + 47 * S * math.sin(a)
            kind = i % 3
            if kind == 0:
                star(d, px, py, 4.6 * S, GOLD, width=2)
            elif kind == 1:
                paw(d, px, py, 3.6 * S, ACC, width=2)
            else:
                flower(d, px, py, 3.4 * S, SAGE, width=2)




def main():
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((44, 28), "圆形 · 顶板平面印花（无浮雕）", font=F(40, True), fill=FG)
    d.text((44, 82),
           "Ø110×17 · 顶板 Ø104 · Ø85 杯会盖住中心；可印区 = 杯外 9.5 mm 环带 · 印花只做一层，不新增壳模",
           font=F(19), fill=MUT)
    tag = "PRINT LAYOUT"
    tw = d.textlength(tag, font=F(20, True))
    d.text((W - 44 - tw, 40), tag, font=F(20, True), fill=ACC)

    # panel A
    x, y = 44, 140
    d.rounded_rectangle([x, y, x + 480, y + 620], radius=14, fill=CARD)
    d.text((x + 24, y + 20), "A · 前弧主图", font=F(25, True), fill=FG)
    d.text((x + 24, y + 54), "杯外前弧放一个主图案，两侧小星点", font=F(15), fill=MUT)
    top_view(d, x, y + 84, "front")
    d.text((x + 24, y + 538), "Ø104 顶板 · Ø85 杯（虚线）· 可印环 9.5 mm", font=F(14), fill=MUT)
    d.text((x + 24, y + 562), "· 最像“杯子旁边的小角色”，正面可见", font=F(15), fill=DIM)
    d.text((x + 24, y + 586), "· 主图 6–8 mm（环宽限制），适合小图标", font=F(15), fill=DIM)

    # panel B
    x = 556
    d.rounded_rectangle([x, y, x + 480, y + 620], radius=14, fill=CARD)
    d.text((x + 24, y + 20), "B · 整圈小图案", font=F(25, True), fill=FG)
    d.text((x + 24, y + 54), "环带一周重复小图案（星 / 爪印 / 小花）", font=F(15), fill=MUT)
    top_view(d, x, y + 84, "ring")
    d.text((x + 24, y + 538), "Ø104 顶板 · Ø85 杯（虚线）· 可印环 9.5 mm", font=F(14), fill=MUT)
    d.text((x + 24, y + 562), "· 任意角度都看到一点图案，摆件感更强", font=F(15), fill=DIM)
    d.text((x + 24, y + 586), "· 单图 4–6 mm；杯大时仍可见", font=F(15), fill=DIM)

    # notes
    x = 1068
    d.rounded_rectangle([x, y, x + 448, y + 620], radius=14, fill=CARD)
    d.text((x + 24, y + 20), "约束 / 做法", font=F(25, True), fill=FG)
    notes = [
        ("印花面", "顶板顶面；杯底投影内不可见，图案必须落在环带"),
        ("工艺", "丝印/移印一层；无浮雕、无额外厚度"),
        ("共用", "纯色款与两条 IP 款共用同一套壳体/顶板"),
        ("耐候", "杯底摩擦区建议留空或加耐磨清漆"),
        ("图像", "最终用授权素材；本轮只定位置/比例/画风"),
    ]
    for i, (k, v) in enumerate(notes):
        yy = y + 80 + i * 100
        d.text((x + 24, yy), k, font=F(17, True), fill=ACC)
        d.text((x + 24, yy + 26), v, font=F(15), fill=DIM)

    d.text((44, H - 58),
           "顶板环带仅 9.5 mm 宽 → 主图 ≤ 8 mm；大面积 IP 建议侧壁平印（约 8 × 345 mm 环绕）",
           font=F(16), fill=MUT)
    d.text((44, H - 28),
           "render/appearance/round/make_print_zones.py · 示意图形为占位（星/爪印/小花），非最终 IP 图 · "
           "实际比例 1 mm = 4 px",
           font=F(15), fill=(96, 104, 118))
    sheet.save(OUT)
    print("WROTE", OUT, sheet.size)


if __name__ == "__main__":
    main()
