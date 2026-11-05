#!/usr/bin/env python3
"""Render the generated EasyEDA PCB (from inputs/canonical.json) to PNG.
Shows: mechanical C-ring outline, NPTH holes, top/bottom copper (ported 1:1 from
the verified KiCad 2-layer routing), vias, pads and component refs."""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parents[1]
CANON = HERE / 'inputs' / 'canonical.json'
OUT = HERE / 'render' / 'pcb_routed.png'
MM = 0.0254  # mm per mil
SIZE = 2200  # px
MARGIN = 90
TOP = (198, 40, 40)
BOT = (40, 80, 198)

def main():
    d = json.loads(CANON.read_text())
    board_mil = 93.2 / MM
    scale = (SIZE - 2 * MARGIN) / board_mil
    def xy(x, y):
        return (MARGIN + x * scale, SIZE - MARGIN - y * scale)
    img = Image.new('RGB', (SIZE, SIZE), 'white')
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
        font_b = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 19)
    except Exception:
        font = font_b = ImageFont.load_default()
    # board outline + NPTH holes
    dr.polygon([xy(x, y) for x, y in d['outline_mil']], fill=(247, 249, 240), outline=(30, 60, 30))
    for h in d['mounting_holes']:
        cx, cy = xy(*h['at_mil'])
        r = h['diameter_mil'] * scale / 2
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill='white', outline=(20, 20, 20), width=3)
    # copper: bottom layer first, then top (so top reads on top)
    copper = d.get('copper', {})
    for layer, color in ((2, BOT), (1, TOP)):
        for t in copper.get('tracks', []):
            if t['layer'] != layer:
                continue
            dr.line([xy(t['x1'], t['y1']), xy(t['x2'], t['y2'])],
                    fill=color, width=max(1, round(t['width_mil'] * scale)))
    # vias
    for v in copper.get('vias', []):
        cx, cy = xy(v['x'], v['y'])
        r = max(2.0, v['diameter_mil'] * scale / 2)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(225, 190, 60), outline=(120, 90, 0))
        rr = max(1.0, v['drill_mil'] * scale / 2)
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill='white', outline=(120, 90, 0))
    # pads
    colors = {'GND': (90, 90, 90), '3V3': (200, 40, 40), 'VBUS': (220, 90, 20),
              'VBAT': (180, 30, 120), 'NC': (180, 180, 180)}
    def rot_rect(cx, cy, w, h, ang):
        t = math.radians(-ang)   # screen y is down, part angle is y-up CCW
        pts = []
        for dx, dy in ((-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)):
            pts.append((cx + dx*math.cos(t) - dy*math.sin(t), cy + dx*math.sin(t) + dy*math.cos(t)))
        return pts
    for part in d['parts']:
        px, py, ang = part['place_mil']
        t = math.radians(ang)
        for pad in part['pads']:
            lx, ly = pad['x'], pad['y']
            ax = px + lx*math.cos(t) - ly*math.sin(t)
            ay = py + lx*math.sin(t) + ly*math.cos(t)
            net = pad.get('pin_net') or 'NC'
            w = max(2.0, pad['w'] * scale); h = max(2.0, pad['h'] * scale)
            cx, cy = xy(ax, ay)
            c = colors.get(net, (40, 80, 180))
            if pad.get('drill'):
                r = max(w, h) / 2
                dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(225, 190, 60), outline=(120, 90, 0))
                rr = pad['drill'] * scale / 2
                dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill='white', outline=(120, 90, 0))
            elif pad.get('shape') == 'ELLIPSE':
                r = max(w, h) / 2
                dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
            else:
                dr.polygon(rot_rect(cx, cy, w, h, ang), fill=c)
    # designators
    for part in d['parts']:
        if part['ref'].startswith('H'):
            continue
        cx, cy = xy(part['place_mil'][0], part['place_mil'][1])
        dr.text((cx + 5, cy - 20), part['ref'], fill=(10, 10, 10), font=font)
    # frame / title / legend / scale
    dr.rectangle([8, 8, SIZE - 9, SIZE - 9], outline=(60, 60, 60), width=2)
    dr.text((MARGIN, 16), 'SmartCoaster V1 — EasyEDA re-implementation, routed (2 layers)',
            fill=(0, 0, 0), font=font_b)
    dr.text((MARGIN, 42), f"board 93.2×93.2 mm, R6, 38×38 opening, 80° front notch; "
                          f"{len(copper.get('tracks', []))} tracks / {len(copper.get('vias', []))} vias ported 1:1 "
                          f"from the verified KiCad routing", fill=(60, 60, 60), font=font)
    dr.text((MARGIN, SIZE - 54), 'red = top copper (F.Cu)   blue = bottom copper (B.Cu)   '
                                 'yellow ring = via / through-hole pad', fill=(60, 60, 60), font=font)
    sb = 10 / MM * scale
    x0 = SIZE - MARGIN - sb; y0 = SIZE - 34
    dr.line([x0, y0, x0 + sb, y0], fill='black', width=4)
    dr.text((x0, y0 - 22), '10 mm', fill='black', font=font)
    img.save(OUT)
    print(f'wrote {OUT} ({SIZE}x{SIZE})')

if __name__ == '__main__':
    main()
