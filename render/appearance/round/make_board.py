#!/usr/bin/env python3
"""Compose the round form-study comparison: single control band vs two micro-flats."""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = "/data/Documents/projects/SmartCoaster/render/appearance/round"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

W, H = 1580, 1330
BG = (17, 19, 24)
CARD = (26, 29, 36)
FG = (234, 238, 244)
MUT = (150, 158, 172)
DIM = (112, 120, 134)
ACC = (124, 108, 232)


def F(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def tile(path, w, h, bg=CARD):
    im = Image.open(path).convert("RGB")
    im.thumbnail((w, h), Image.LANCZOS)
    c = Image.new("RGB", (w, h), bg)
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


COLS = [
    dict(title="A · 单条控制带", sub="一个 54 × 9.6 mm 凹槽，屏+键共用平面",
         hero=f"{ROOT}/renders/hero.png", front=f"{ROOT}/renders/front.png",
         notes=["更像“控制面板 / 一条带”，整体感强",
                "凹槽深 4.5 mm，阴影重，容易被读成“嘴”",
                "密封、开模、装配最简单"]),
    dict(title="B · 双微凹（推荐）", sub="屏 36 × 9.6 浅凹 + 按键 Ø11 圆台",
         hero=f"{ROOT}/renders_two/hero.png", front=f"{ROOT}/renders_two/front.png",
         notes=["更接近“微凹平面”，两个控件各自独立",
                "屏凹深 3.2 mm，按键圆台外凸 0.4 mm",
                "更像摆件，圆感保留得更好"]),
]

COL_W = 740
X0 = (W - COL_W * 2 - 40) // 2


def main():
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((44, 28), "圆形形态研究 · 前脸两种做法", font=F(40, True), fill=FG)
    d.text((44, 82),
           "Ø110 × 17 mm · 暖白 PC/ABS 细磨砂 · 0.6 mm 浮缝 · 顶板 0.6 mm 浅碟 · 无灯",
           font=F(19), fill=MUT)
    tag = "FORM STUDY"
    tw = d.textlength(tag, font=F(20, True))
    d.text((W - 44 - tw, 40), tag, font=F(20, True), fill=ACC)

    for i, c in enumerate(COLS):
        x = X0 + i * (COL_W + 40)
        y = 132
        hw, hh = 450, 450
        fw, fh = 660, 330
        d.text((x, y), c["title"], font=F(27, True), fill=FG)
        d.text((x, y + 34), c["sub"], font=F(16), fill=MUT)
        hero = tile(c["hero"], hw, hh)
        sheet.paste(hero, (x + (COL_W - hw) // 2, y + 62))
        front = tile(c["front"], fw, fh)
        sheet.paste(front, (x + (COL_W - fw) // 2, y + 62 + hh + 24))
        for j, n in enumerate(c["notes"]):
            d.text((x, y + 62 + hh + 24 + fh + 26 + j * 26), "· " + n,
                   font=F(16), fill=DIM if j else FG)

    d.text((44, H - 34),
           "render/appearance/round/ · 形态研究（primitive build，非最终 CAD）· "
           "相机/灯光一致，只改变前脸做法",
           font=F(15), fill=(96, 104, 118))
    out = f"{ROOT}/00_front_treatment_compare.png"
    sheet.save(out)
    print("WROTE", out, sheet.size)


if __name__ == "__main__":
    main()
