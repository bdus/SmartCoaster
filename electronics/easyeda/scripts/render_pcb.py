#!/usr/bin/env python3
"""Render the placement-only EasyEDA PCB (from inputs/canonical.json) to PNG.
Shows: mechanical C-ring outline, mounting holes, pads by net class,
component refs, and a ratsnest approximation of every net (no copper exists)."""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parents[1]
CANON = HERE / 'inputs' / 'canonical.json'
OUT = HERE / 'render' / 'pcb_placement.png'
MM = 0.0254  # mm per mil
SIZE = 2200  # px
MARGIN = 90

def main():
    d = json.loads(CANON.read_text())
    board_mil = 93.2 / MM
    scale = (SIZE - 2 * MARGIN) / board_mil
    def xy(x, y, y_up=True):
        return (MARGIN + x * scale, SIZE - MARGIN - y * scale) if y_up else (MARGIN + x * scale, MARGIN + y * scale)
    img = Image.new('RGB', (SIZE, SIZE), 'white')
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        font_b = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except Exception:
        font = font_b = ImageFont.load_default()
    # board outline
    outline = [xy(x, y) for x, y in d['outline_mil']]
    dr.polygon(outline, fill=(247, 249, 240), outline=(30, 60, 30))
    # mounting holes (NPTH)
    for h in d['mounting_holes']:
        cx, cy = xy(*h['at_mil'])
        r = h['diameter_mil'] * scale / 2
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill='white', outline=(20, 20, 20), width=3)
    # pads + ratsnest
    pad_info = []   # (x,y,net,ref)
    colors = {'GND': (90, 90, 90), '3V3': (200, 40, 40), 'VBUS': (220, 90, 20),
              'VBAT': (180, 30, 120), 'NC': (170, 170, 170)}
    pads = []
    for part in d['parts']:
        px, py, ang = part['place_mil']
        t = math.radians(ang)
        for pad in part['pads']:
            lx, ly = pad['x'], pad['y']
            ax = px + lx * math.cos(t) - ly * math.sin(t)
            ay = py + lx * math.sin(t) + ly * math.cos(t)
            net = pad.get('pin_net') or 'NC'
            pads.append((ax, ay, net, part['ref'], pad))
            if net != 'NC':
                pad_info.append((ax, ay, net, part['ref']))
    # ratsnest: connect all pads of a net as a simple MST (Prim) of their centres
    nets = {}
    for x, y, net, ref in pad_info:
        nets.setdefault(net, []).append((x, y))
    for net, pts in nets.items():
        if len(pts) < 2:
            continue
        pts = list(pts)
        used = {0}
        while len(used) < len(pts):
            best = None
            for i in used:
                for j in range(len(pts)):
                    if j in used:
                        continue
                    dx = pts[i][0] - pts[j][0]; dy = pts[i][1] - pts[j][1]
                    dd = dx * dx + dy * dy
                    if best is None or dd < best[0]:
                        best = (dd, i, j)
            _, i, j = best
            used.add(j)
            dr.line([xy(*pts[i]), xy(*pts[j])], fill=(205, 120, 120), width=1)
    # pads
    def rot_rect(cx, cy, w, h, ang):
        t = math.radians(-ang)   # screen y is down, part angle is y-up CCW
        pts = []
        for dx, dy in ((-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)):
            pts.append((cx + dx*math.cos(t) - dy*math.sin(t), cy + dx*math.sin(t) + dy*math.cos(t)))
        return pts
    for ax, ay, net, ref, pad in pads:
        w = max(2.0, pad['w'] * scale); h = max(2.0, pad['h'] * scale)
        cx, cy = xy(ax, ay)
        c = colors.get(net, (40, 80, 180))
        if pad.get('drill'):
            r = max(w, h) / 2
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 190, 60), outline=(120, 90, 0))
            rr = pad['drill'] * scale / 2
            dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill='white', outline=(120, 90, 0))
        elif pad.get('shape') == 'ELLIPSE':
            r = max(w, h) / 2
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
        else:
            ang = next(p2['place_mil'][2] for p2 in d['parts'] if p2['ref'] == ref)
            dr.polygon(rot_rect(cx, cy, w, h, ang), fill=c)
    # component labels (offset to avoid covering the footprint)
    for part in d['parts']:
        px, py, ang = part['place_mil']
        if part['ref'].startswith('H'):
            continue
        cx, cy = xy(px, py)
        text = part['ref']
        dr.text((cx + 6, cy - 22), text, fill=(10, 10, 10), font=font)
    # frame / title / scale bar
    dr.rectangle([8, 8, SIZE - 9, SIZE - 9], outline=(60, 60, 60), width=2)
    dr.text((MARGIN, 18), 'SmartCoaster V1 — EasyEDA re-implementation (placement only, no copper yet)',
            fill=(0, 0, 0), font=font_b)
    dr.text((MARGIN, 44), 'board 93.2×93.2 mm, R6, 38×38 opening, 80° front notch; 4×M2 NPTH @(±40,±24) mm',
            fill=(60, 60, 60), font=font)
    dr.text((MARGIN, SIZE - 56), 'red = 3V3/VBUS/VBAT rail, grey = GND, blue = signal, yellow = through-hole pad',
            fill=(60, 60, 60), font=font)
    # scale bar 10 mm
    sb = 10 / MM * scale
    x0 = SIZE - MARGIN - sb; y0 = SIZE - 34
    dr.line([x0, y0, x0 + sb, y0], fill='black', width=4)
    dr.text((x0, y0 - 22), '10 mm', fill='black', font=font)
    img.save(OUT)
    print(f'wrote {OUT} ({SIZE}x{SIZE})')

if __name__ == '__main__':
    main()
