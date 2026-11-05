#!/usr/bin/env python3
"""Extract a canonical electrical/mechanical description from the frozen KiCad 9 design.

Read-only on electronics/kicad/**: this script never writes there.
Outputs:
  inputs/canonical.json   machine-readable: parts, pads (local, mil/y-up), nets, placement, outline, holes
Usage:
  XDG_CONFIG_HOME=... LD_LIBRARY_PATH=... PYTHONPATH=... python3 extract_kicad.py
"""
import json, math, os, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KICAD = ROOT / 'electronics' / 'kicad'
PCB = KICAD / 'smartcoaster' / 'smartcoaster_2l.kicad_pcb'
NET = KICAD / 'smartcoaster' / 'smartcoaster.net'
BOM = KICAD / 'BOM.csv'
OUT = Path(__file__).resolve().parents[1] / 'inputs' / 'canonical.json'

MM = 0.0254          # mm per mil
BOARD = 93.2         # mm outer square
HALF = BOARD / 2.0
CORNER_R = 6.0
OPENING = 38.0
HALF_OPEN = OPENING / 2.0
NOTCH_DEG = 80.0
HOLE_MM = 2.2
HOLES = ((40.0, 24.0), (-40.0, 24.0), (-40.0, -24.0), (40.0, -24.0))

def mm2mil(v): return v / MM
def mech_to_eda(x, y):  # mech y-up centred -> board mil y-up with origin at bottom-left
    return ((x + HALF) / MM, (y + HALF) / MM)

# ---- schematic block membership (semantic, from design.py BLOCKS + pinmap.md) ----
BLOCK_OF = {}
def _blocks():
    b = {
      'USB-C 5V input, CC resistors, ESD': ['J1','U7','R9','R10','C1'],
      'Li-ion charger + protection + LDO': ['U3','C3','C2','R8','J2','U4','U5','R11','C4','R12','U6','C5','C6','C7'],
      'ESP32-S3-MINI-1 MCU': ['U1','R1','C9','SW2','R2','SW3','C10'],
      'HX711 load-cell front-end': ['U2','R5','C11','C12','C14','C15','C16','R25','R26','J3'],
      'UI: OLED header + key': ['J4','J5','R3','R4'],
      'Battery voltage sense': ['R6','R7','C13'],
      'Mechanical mounting holes': ['H1','H2','H3','H4'],
    }
    for title, refs in b.items():
        for r in refs: BLOCK_OF[r] = title
    return b
BLOCKS = _blocks()

def parse_netlist():
    root = ET.parse(str(NET)).getroot()
    comps = {}
    for c in root.find('components'):
        comps[c.get('ref')] = {'value': c.findtext('value'), 'footprint': c.findtext('footprint')}
    pins = {}   # ref -> {padnum: {'net':, 'name':}}
    for n in root.find('nets'):
        name = n.get('name')
        for node in n.findall('node'):
            ref, num = node.get('ref'), node.get('pin')
            pins.setdefault(ref, {})[num] = {
                'net': name, 'name': node.get('pinfunction') or '', 'type': node.get('pintype') or ''}
    return comps, pins

def parse_bom():
    import csv
    out = {}
    with open(BOM, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            for ref in row['Refs'].split():
                out[ref] = {'mpn': row['MPN'], 'desc': row['Description'], 'note': row['Note']}
    return out

# ---- footprint geometry -----------------------------------------------------
def pad_shape(p, pcbnew):
    S = pcbnew.PAD
    sh = p.GetShape()
    import pcbnew as _p
    if sh in (_p.PAD_SHAPE_CIRCLE, _p.PAD_SHAPE_OVAL):
        return 'ELLIPSE'
    return 'RECT'

def pads_of(fp, pcbnew, theta):
    """Return EasyEDA-local pads (mil, y-up) for one placed KiCad footprint."""
    fp_mm = (fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6)
    out = []
    for p in fp.Pads():
        num = p.GetNumber() or 'MH'
        dx = p.GetPosition().x / 1e6 - fp_mm[0]
        dy = p.GetPosition().y / 1e6 - fp_mm[1]
        # KiCad y-down -> EasyEDA y-up, then undo the placement rotation
        dx_e, dy_e = dx, -dy
        t = math.radians(-theta)
        lx = dx_e * math.cos(t) - dy_e * math.sin(t)
        ly = dx_e * math.sin(t) + dy_e * math.cos(t)
        sz = p.GetSize(); dr = p.GetDrillSize()
        w, h = sz.x / 1e6, sz.y / 1e6
        rel = (p.GetOrientationDegrees() - theta) % 180.0
        if abs(rel - 90.0) < 1.0:
            w, h = h, w
        pad = {
            'num': num,
            'x': round(mm2mil(lx), 4), 'y': round(mm2mil(ly), 4),
            'w': round(mm2mil(w), 4), 'h': round(mm2mil(h), 4),
            'shape': pad_shape(p, pcbnew),
            'plated': p.GetAttribute() == 0,   # PTH (0) vs NPTH (3) vs SMD (1)
            'net': p.GetNetname(),
            'layer': p.GetLayerName(),
        }
        if dr.x > 0:
            pad['drill'] = round(mm2mil(dr.x / 1e6), 4)
        out.append(pad)
    return out

# ---- board outline (same geometry as mechanical/square_v1 make_pcb) ----------
def arc_points(cx, cy, ax, ay, bx, by, segs=12):
    """Points along the short (quarter-circle) arc a->b around (cx,cy)."""
    a0 = math.atan2(ay - cy, ax - cx)
    a1 = math.atan2(by - cy, bx - cx)
    r = math.hypot(ax - cx, ay - cy)
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi   # signed, in (-pi, pi]
    pts = []
    for i in range(1, segs + 1):
        a = a0 + d * i / segs
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def outline_mech():
    t = math.tan(math.radians(50.0))
    x_out = HALF / t; x_in = HALF_OPEN / t
    c = HALF - CORNER_R
    p = []
    p.append((x_out, -HALF))
    p.append((c, -HALF)); p += arc_points(c, -c, c, -HALF, HALF, -c)
    p.append((HALF, c)); p += arc_points(c, c, HALF, c, c, HALF)
    p.append((-c, HALF)); p += arc_points(-c, c, -c, HALF, -HALF, c)
    p.append((-HALF, -c)); p += arc_points(-c, -c, -HALF, -c, -c, -HALF)
    p.append((-x_out, -HALF))
    p.append((-x_in, -HALF_OPEN))
    p.append((-HALF_OPEN, -HALF_OPEN))
    p.append((-HALF_OPEN, HALF_OPEN))
    p.append((HALF_OPEN, HALF_OPEN))
    p.append((HALF_OPEN, -HALF_OPEN))
    p.append((x_in, -HALF_OPEN))
    p.append((x_out, -HALF))
    return p

def main():
    import pcbnew
    comps, netpins = parse_netlist()
    bom = parse_bom()
    board = pcbnew.LoadBoard(str(PCB))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    parts = []
    for ref in sorted(fps, key=lambda r: (r.rstrip('0123456789'), int(''.join(ch for ch in r if ch.isdigit()) or 0))):
        fp = fps[ref]
        theta = fp.GetOrientationDegrees()
        pos = fp.GetPosition()
        px, py = mech_to_eda(pos.x / 1e6, -pos.y / 1e6)
        pins = netpins.get(ref, {})
        pads = pads_of(fp, pcbnew, theta)
        # fold netlist pin info (name/net) onto pads by number
        pinmap = {}
        for num, info in pins.items():
            net = info['net']
            if net.startswith('unconnected-'):
                net = 'NC'
            else:
                net = net.lstrip('/')
            pinmap[num] = {'net': net, 'name': info['name'], 'type': info['type']}
        for pad in pads:
            info = pinmap.get(pad['num'])
            pad['pin_net'] = info['net'] if info else ('NC' if not pad['net'] else pad['net'])
            pad['pin_name'] = info['name'] if info else ''
        parts.append({
            'ref': ref, 'value': fp.GetValue(), 'block': BLOCK_OF.get(ref, 'Mechanical mounting holes'),
            'mpn': bom.get(ref, {}).get('mpn', ''), 'desc': bom.get(ref, {}).get('desc', ''),
            'footprint': str(fp.GetFPID().GetLibItemName()),
            'theta_kicad': theta,
            'place_mil': [round(px, 3), round(py, 3), theta],
            'pads': pads,
            'pinmap': pinmap,
        })
    outline_pts = [mech_to_eda(x, y) for (x, y) in outline_mech()]
    doc = {
        'meta': {
            'source_pcb': str(PCB.relative_to(ROOT)), 'source_netlist': str(NET.relative_to(ROOT)),
            'source_bom': str(BOM.relative_to(ROOT)), 'generated_by': 'electronics/easyeda/scripts/extract_kicad.py',
            'board_mm': BOARD, 'corner_r_mm': CORNER_R, 'opening_mm': OPENING, 'notch_deg': NOTCH_DEG,
            'coord_note': 'EasyEDA PCB mil, y-up, origin = bottom-left of the 93.2 mm square; x=(mech_x+46.6)/0.0254, y=(mech_y+46.6)/0.0254',
        },
        'parts': parts,
        'blocks': [{'title': t, 'parts': refs} for t, refs in BLOCKS.items()],
        'nets': {c: [] for c in sorted({p['pin_net'] for part in parts for p in part['pads'] if p.get('pin_net') not in (None, 'NC')})},
        'outline_mil': [[round(x, 3), round(y, 3)] for x, y in outline_pts],
        'mounting_holes': [{'ref': f'H{i+1}', 'at_mil': [round(mech_to_eda(x, y)[0], 3), round(mech_to_eda(x, y)[1], 3)],
                            'diameter_mil': round(mm2mil(HOLE_MM), 3)} for i, (x, y) in enumerate(HOLES)],
    }
    for part in doc['parts']:
        for p in part['pads']:
            if p.get('pin_net') not in (None, 'NC'):
                doc['nets'].setdefault(p['pin_net'], []).append(f"{part['ref']}.{p['num']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(f"wrote {OUT}  parts={len(doc['parts'])}  outline_pts={len(doc['outline_mil'])}  nets={len(doc['nets'])}")

if __name__ == '__main__':
    main()
