#!/usr/bin/env python3
"""Post-process the eprj3-generated PCB:
  1. replace the auto-sized rectangle board outline with the frozen mechanical
     C-ring outline (93.2x93.2, R6, 38x38 opening, 80 deg front notch) from
     inputs/canonical.json;
  2. mark the four M2 mounting-hole pads as NPTH (plated:false).
Idempotent; run after every build.js rebuild."""
import glob, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CANON = HERE / 'inputs' / 'canonical.json'
PROJ = HERE / 'smartcoaster_easyeda'

def main():
    doc = json.loads(CANON.read_text())
    pts = [[round(x, 3), round(y, 3)] for x, y in doc['outline_mil']]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    path = [pts[0][0], pts[0][1]]
    for x, y in pts[1:]:
        path += ['L', x, y]
    pcbs = sorted(PROJ.glob('pcb/*.epcb2'))
    assert len(pcbs) == 1, pcbs
    f = pcbs[0]
    lines = f.read_text().split('\n')
    outline = holes = 0
    for i, line in enumerate(lines):
        if '||' not in line:
            continue
        head, body = line.split('||', 1)
        try:
            h = json.loads(head); b = json.loads(body.rstrip('|'))
        except Exception:
            continue
        if h.get('type') == 'POLY' and b.get('polyType') == 'BOARD_OUTLINE':
            b['path'] = path
            b['width'] = 10
            lines[i] = head + '||' + json.dumps(b, separators=(',', ':')) + '|'
            outline += 1
        elif h.get('type') == 'PAD' and b.get('num') == 'MH' and b.get('hole'):
            # mounting holes only: NPTH, copper == hole, no net
            if b.get('hole', {}).get('width', 0) >= 80:
                b['plated'] = False
                b['layerId'] = 12
                b['netName'] = ''
                b['defaultPad'] = {'padType': 'ELLIPSE',
                                   'width': b['hole']['width'], 'height': b['hole']['height']}
                lines[i] = head + '||' + json.dumps(b, separators=(',', ':')) + '|'
                holes += 1
    assert outline == 1, f'outline records patched: {outline}'
    assert holes >= 1, f"NPTH pads patched: {holes}"  # H1-H4 share one embedded footprint doc
    f.write_text('\n'.join(lines))
    print(f'patched {f.name}: outline polygon {len(pts)} pts, {holes} NPTH mounting holes')

if __name__ == '__main__':
    main()
