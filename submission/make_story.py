#!/usr/bin/env python3
"""Red Dot submission sheet: A3 landscape, hero + story + specs + CMF."""
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = "/data/Documents/projects/SmartCoaster"
W, H = 4961, 3508
BG = (18, 20, 24)
FG = (232, 236, 242)
MUT = (150, 158, 172)
ACC = (140, 120, 230)

BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def F(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REG, size, index=2)


def para(d, x, y, w, text, size=27, color=FG, leading=39):
    f = F(size)
    lines = []
    for chunk in text.split("\n"):
        lines += textwrap.wrap(chunk, width=int(w / (size * 0.52))) or [""]
    d.multiline_text((x, y), "\n".join(lines), font=f, fill=color, spacing=leading - size)
    return y + len(lines) * leading


def section(d, x, y, title, body, w=2150):
    d.text((x, y), title, font=F(31, True), fill=ACC)
    return para(d, x, y + 46, w, body)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((150, 100), "SmartCoaster", font=F(150, True), fill=FG)
    d.text((150, 300), "A coaster that knows when you drink.", font=F(48), fill=MUT)
    d.text((W - 150 - 520, 130), "RED DOT 2026", font=F(36, True), fill=ACC)
    d.text((W - 150 - 520, 190), "Product Design", font=F(28), fill=MUT)

    hero = Image.open(f"{ROOT}/submission/01_hero.png").convert("RGB")
    hero = hero.resize((2350, 2350), Image.LANCZOS)
    img.paste(hero, (150, 430))

    x = 2650
    y = 120
    y = section(d, x, y, "THE PROBLEM",
                "Staying hydrated is a habit, not a reminder. Phone notifications "
                "live on another screen and are easy to ignore; cups do not know "
                "how much you drank.")
    y = section(d, x, y + 40, "THE INSIGHT",
                "Drinking water is a 'put the cup down' action. The coaster is the "
                "only object that is always there.")
    y = section(d, x, y + 40, "THE DESIGN",
                "Weight is the input. Place the cup, lift, drink, put it back - the "
                "difference is the sip. Refills are ignored. The front face carries "
                "only a 26 x 7 OLED window and one button: no light ring, no light "
                "seam. The single functional seam is the 0.5 mm floating gap between "
                "top plate and shell.")
    y = section(d, x, y + 40, "THE EXPERIENCE",
                "When it is time to drink, the window shows a quiet reminder - no "
                "glow, no sound. It shows today's progress only when needed, then "
                "sleeps after 8 s. Seven days on a 500 mAh battery; BLE sync only "
                "on demand.")
    y = section(d, x, y + 40, "SUSTAINABILITY",
                "30% PCR shell, FSC moulded-pulp packaging, no glue, replaceable "
                "battery, four screws to repair.")
    d.text((x, y + 40), "SPECIFICATIONS", font=F(31, True), fill=ACC)
    specs = [
        ("Size / weight", "100 x 100 x 18 mm / 155 g"),
        ("Range", "5 kg (HY928D + HX711, 24-bit)"),
        ("Goal", "2200 ml/day (app adjustable)"),
        ("Display", '0.91" 128x32 OLED, 26 x 7 window'),
        ("Feedback", "on-screen only (no LEDs)"),
        ("Wireless", "BLE 5 (NimBLE, 0xFF00)"),
        ("Battery", "500 mAh, 7-day class"),
        ("Charging", "USB-C"),
    ]
    yy = y + 100
    for k, v in specs:
        d.text((x, yy), k, font=F(26, True), fill=MUT)
        d.text((x + 620, yy), v, font=F(26), fill=FG)
        yy += 48
    d.text((x, yy + 20), "CMF", font=F(31, True), fill=ACC)
    sw = [("6B40A0", "Lumen Violet"), ("2A2E35", "Charcoal"),
          ("4F6B4A", "Moss"), ("C9B79A", "Sand"), ("3A3D42", "Graphite")]
    for i, (hexv, name) in enumerate(sw):
        col = tuple(int(hexv[j:j + 2], 16) for j in (0, 2, 4))
        cx = x + 20 + i * 210
        d.ellipse([cx, yy + 80, cx + 90, yy + 170], fill=col)
        d.text((cx, yy + 180), name, font=F(22), fill=MUT)

    thumbs = [("02_front.png", "FRONT"), ("03_exploded.png", "STRUCTURE"),
              ("04_package.png", "PACKAGING")]
    for i, (fn, label) in enumerate(thumbs):
        t = Image.open(f"{ROOT}/submission/{fn}").convert("RGB").resize((500, 500), Image.LANCZOS)
        tx = 150 + i * 540
        img.paste(t, (tx, 2920))
        d.text((tx, 3440), label, font=F(24, True), fill=MUT)
    d.text((150, 3470), "SmartCoaster  ·  P1 prototype / P2 DFM-passed PCB / P3 CMF & packaging  ·  2026",
           font=F(22), fill=(110, 118, 132))
    img.save(f"{ROOT}/submission/SmartCoaster_Story.pdf", "PDF", resolution=300)
    img.save(f"{ROOT}/submission/SmartCoaster_Story.png")
    print("story saved", img.size)


if __name__ == "__main__":
    main()
