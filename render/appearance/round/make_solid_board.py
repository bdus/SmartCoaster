#!/usr/bin/env python3
"""Compose the chosen round solid-colour form study (B · two micro-flats)."""
import os

from PIL import Image, ImageDraw, ImageFont

R = "/data/Documents/projects/SmartCoaster/render/appearance/round"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

W, H = 1700, 1340
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


def tile(path, w, h):
    im = Image.open(path).convert("RGB")
    im.thumbnail((w, h), Image.LANCZOS)
    c = Image.new("RGB", (w, h), CARD)
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def main():
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((44, 28), "圆形 · 暖白纯色（形态研究 · 定稿候选）", font=F(40, True), fill=FG)
    d.text((44, 82),
           "Ø110 × 17 mm · PC/ABS + 30% PCR 细磨砂 · 0.6 mm 浮缝 · 顶板 0.6 mm 浅碟 · 无灯",
           font=F(19), fill=MUT)
    tag = "FORM STUDY · NOT CAD"
    tw = d.textlength(tag, font=F(20, True))
    d.text((W - 44 - tw, 40), tag, font=F(20, True), fill=ACC)

    # left column
    x, y = 44, 150
    sheet.paste(tile(f"{R}/renders_two/hero.png", 560, 560), (x, y))
    d.text((x, y + 574), "主视角 · 45°", font=F(22, True), fill=FG)
    d.text((x, y + 604), "圆、浮缝、双微凹控件区在自然光下的关系", font=F(16), fill=MUT)

    sheet.paste(tile(f"{R}/renders_two/detail.png", 560, 420), (x, y + 654))
    d.text((x, y + 654 + 434), "细节 · 屏凹 + Ø11 按键圆台", font=F(22, True), fill=FG)
    d.text((x, y + 654 + 464), "26×7 胶囊窗、同色哑光键、3.2 mm 浅凹", font=F(16), fill=MUT)

    # right column
    rx = 660
    sheet.paste(tile(f"{R}/renders_two/front.png", 940, 470), (rx, y))
    d.text((rx, y + 484), "正视图 · 屏左 / 键右（水平）", font=F(22, True), fill=FG)
    d.text((rx, y + 514), "26×7 胶囊窗 x=−8 · Ø8.2 键 x=17 · z=7.2", font=F(16), fill=MUT)

    sheet.paste(tile(f"{R}/renders_two/top.png", 520, 520), (rx + 60, y + 570))
    d.text((rx, y + 1104), "顶视图 · Ø104 浮板 / 0.6 mm 浮缝 / 0.6 mm 浅碟",
           font=F(22, True), fill=FG)
    # notes block
    nx = rx + 640
    notes = [
        ("外观口径", "暖白、细磨砂、无 logo、无灯"),
        ("控件", "屏凹 3.2 mm；按键圆台 Ø11 外凸 0.4 mm"),
        ("顶板", "Ø104×3；平顶 + 0.6 mm 浅碟；可整片取下"),
        ("后续", "IP 款在纯色几何上换表面工艺；"),
        ("", "立体浮雕版需独立壳体/模具"),
    ]
    ny = y + 600
    d.text((nx, ny), "要点", font=F(24, True), fill=FG)
    for i, (k, v) in enumerate(notes):
        yy = ny + 40 + i * 64
        if k:
            d.text((nx, yy), k, font=F(18, True), fill=ACC)
            d.text((nx, yy + 24), v, font=F(16), fill=DIM)
        else:
            d.text((nx, yy + 24), v, font=F(16), fill=DIM)

    d.text((44, H - 34),
           "render/appearance/round/ · 形态研究（primitive build，非最终 CAD）· "
           "相机/灯光一致；正式几何将按此比例在 build123d 重建并自检",
           font=F(15), fill=(96, 104, 118))
    out = f"{R}/00_solid_warm_white.png"
    sheet.save(out)
    print("WROTE", out, sheet.size)


if __name__ == "__main__":
    main()
