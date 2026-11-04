#!/usr/bin/env python3
"""Compose render/print/PRINT_SHEET.png (3D-print reference sheet, square B).

Run:
  blender -b --python render/print/print_layout.py   # -> renders/print_iso.png + print_top.png
  python3 render/print/make_sheet.py                 # -> PRINT_SHEET.png

No LED / no emissive part (removed 2026-11-04): printed shell front face has
only the 26x7 screen window and the button hole.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = "/data/Documents/projects/SmartCoaster"
REN = f"{ROOT}/render/print/renders"
OUT = f"{ROOT}/render/print/PRINT_SHEET.png"

BG = (21, 23, 27)
FG = (232, 236, 242)
MUT = (150, 158, 172)
ACC = (140, 120, 230)

BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def F(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else REG, size, index=2)
    except OSError:
        return ImageFont.load_default()


def main():
    W, H = 1800, 1200
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 44), "方形 B — 3D 打印参考", font=F(46, True), fill=FG)
    d.text((60, 108), "外壳 / 顶板 / 按键为打印件；电子、传感器、玻璃、硅胶垫为采购件",
           font=F(23), fill=MUT)

    iso = Image.open(f"{REN}/print_iso.png").convert("RGB")
    iw, ih = 1080, int(1080 * iso.size[1] / iso.size[0])
    iso = iso.resize((iw, ih), Image.LANCZOS)
    img.paste(iso, (60, 170))

    top = Image.open(f"{REN}/print_top.png").convert("RGB")
    tw, th = 360, int(360 * top.size[1] / top.size[0])
    top = top.resize((tw, th), Image.LANCZOS)
    img.paste(top, (60, 170 + ih + 16))
    d.text((60 + tw + 18, 170 + ih + 22), "顶视图：外壳 / 顶板（翻转）/ 按键",
           font=F(20), fill=MUT)

    x = 1190
    y = 170

    def head(t, yy):
        d.text((x, yy), t, font=F(28, True), fill=ACC)
        return yy + 44

    def row(k, v, yy):
        d.text((x, yy), k, font=F(22, True), fill=FG)
        d.text((x + 330, yy), v, font=F(22), fill=MUT)
        return yy + 36

    y = head("打印件", y)
    y = row("Shell 底壳 ×1", "100 × 100 × 18 mm", y)
    y = row("Top plate 顶板 ×1", "100 × 100 × 14.5 mm", y)
    y = row("Button 按键 ×1", "Ø8.2 × 5 mm", y)
    y += 14
    y = head("不打印（采购 / 另做）", y)
    for line in ("OLED 玻璃（PMMA）、硅胶垫、PCB、HY928D、电池、",
                 "螺钉、0.91\" 屏模组、按键帽（可选打印）"):
        d.text((x, y), line, font=F(21), fill=MUT)
        y += 32
    y += 12
    y = head("打印参数（起步）", y)
    for line in ("PLA / PETG · 0.2 mm 层高 · 3 墙 · 15% 填充",
                 "外壳 / 顶板平放，无需支撑；按键加 5 mm brim",
                 "0.2 mm 间隙（按键孔 / 屏窗）",
                 "首件先打外壳 + 顶板验证屏/键/传感器配合，再打按键"):
        d.text((x, y), line, font=F(21), fill=MUT)
        y += 32
    y += 12
    y = head("装配要点", y)
    for line in ("前脸只有 26×7 屏窗与按键；无灯、无灯带。",
                 "顶板-底座 0.5 mm 是秤的浮动缝：不要填、不要加灯。",
                 "四角传感器凸台共面度是关键（FEA：+y 两颗承担 99.4%）。",
                 "屏幕/按键固定在底壳前壁，不随浮动顶板运动。"):
        d.text((x, y), line, font=F(21), fill=MUT)
        y += 32

    d.text((480, H - 74),
           "STL: mechanical/square_v1/build/parts/{shell,plate,button}_v01.stl（由参数化 CAD 生成；不要从 Blender 反向导出打印件）",
           font=F(19), fill=(110, 118, 132))
    d.text((480, H - 44),
           "颜色：顶板深紫、底壳石墨灰、按键紫色（视觉参考；实际以耗材为准）· 2026-11-04 无灯版",
           font=F(19), fill=(110, 118, 132))
    img.save(OUT)
    print("WROTE", OUT, img.size)


if __name__ == "__main__":
    main()
