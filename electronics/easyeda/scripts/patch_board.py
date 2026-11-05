#!/usr/bin/env python3
"""Post-process the eprj3-generated PCB:
  1. replace the auto-sized rectangle board outline with the frozen mechanical
     C-ring outline (93.2x93.2, R6, 38x38 opening, 80 deg front notch);
  2. restore the real KiCad pad shapes (ROUNDRECT radius / OVAL / CIRCLE) into
     the embedded footprint documents, instead of the skill's plain RECT;
  3. mark the four M2 mounting-hole pads as NPTH (plated:false).
Idempotent; run after every build.js rebuild."""
import glob, json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CANON = HERE / 'inputs' / 'canonical.json'
DESIGN = HERE / 'design' / 'design.json'
PROJ = HERE / 'smartcoaster_easyeda'

def main():
    doc = json.loads(CANON.read_text())
    pts = [[round(x, 3), round(y, 3)] for x, y in doc['outline_mil']]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    path = [pts[0][0], pts[0][1]]
    for x, y in pts[1:]:
        path += ['L', x, y]

    # pad geometry by (display footprint name, pad number); the skill trims names to 40 chars
    pad_spec = {}
    for part in doc['parts']:
        title = part['footprint'][:40]
        for pad in part['pads']:
            pad_spec.setdefault((title, str(pad['num'])), pad)

    pcbs = sorted(PROJ.glob('pcb/*.epcb2'))
    assert len(pcbs) == 1, pcbs
    f = pcbs[0]
    lines = f.read_text().split('\n')
    outline = holes = shapes = 0
    doc_type = title = None
    for i, line in enumerate(lines):
        if '||' in line:
            head, body = line.split('||', 1)
            try:
                h = json.loads(head); b = json.loads(body.strip().rstrip('|'))
            except Exception:
                continue
            if h.get('type') == 'DOCHEAD':
                doc_type = b.get('docType'); title = None
                continue
            if h.get('type') == 'META':
                if doc_type == 'FOOTPRINT' and b.get('title'):
                    title = b['title']
                continue
            if h.get('type') == 'POLY' and b.get('polyType') == 'BOARD_OUTLINE':
                b['path'] = path
                b['width'] = 10
                lines[i] = head + '||' + json.dumps(b, separators=(',', ':')) + '|'
                outline += 1
                continue
            if h.get('type') != 'PAD':
                continue
            # NPTH mounting holes (num MH, big drill) — copper == hole, unplated
            if b.get('num') == 'MH' and b.get('hole') and b.get('hole', {}).get('width', 0) >= 80:
                b['plated'] = False
                b['layerId'] = 12
                b['netName'] = ''
                b['defaultPad'] = {'padType': 'ELLIPSE',
                                   'width': b['hole']['width'], 'height': b['hole']['height']}
                lines[i] = head + '||' + json.dumps(b, separators=(',', ':')) + '|'
                holes += 1
                continue
            spec = pad_spec.get((title, str(b.get('num'))))
            if not spec:
                continue
            pad_type = {'CIRCLE': 'ELLIPSE', 'OVAL': 'ELLIPSE'}.get(spec['shape'], 'RECT')
            dp = {'padType': pad_type, 'width': round(spec['w'], 3), 'height': round(spec['h'], 3)}
            if pad_type == 'RECT':
                dp['radius'] = round(spec.get('r_mil', 0), 3) if spec['shape'] == 'ROUNDRECT' else 0
            b['defaultPad'] = dp
            lines[i] = head + '||' + json.dumps(b, separators=(',', ':')) + '|'
            shapes += 1
    assert outline == 1, f'outline records patched: {outline}'
    assert holes >= 1, f"NPTH pads patched: {holes}"  # H1-H4 share one embedded footprint doc
    assert shapes + holes >= 160, f'pad shapes patched: {shapes}, holes: {holes}'
    f.write_text('\n'.join(lines))
    print(f'patched {f.name}: outline {len(pts)} pts, {shapes} pad shapes, {holes} NPTH holes')

if __name__ == '__main__':
    main()
