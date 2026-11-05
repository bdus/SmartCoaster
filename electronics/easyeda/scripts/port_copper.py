#!/usr/bin/env python3
"""Port the verified KiCad 2-layer routing into the generated EasyEDA PCB1.epcb2.

The EasyEDA board has exactly the same placement, pad geometry and netlist as the
frozen KiCad board (verified by check_parity.py + placement), so the already
validated 576 tracks / 62 vias can be transferred 1:1 as EasyEDA LINE/VIA records.
This makes the .eprj3 a *routed* board that the offline DRC can review in full
(D001-D012, incl. D004 connectivity), without needing the login-gated client.

Honest boundary: this is copper ported from KiCad, not EasyEDA-native routing.
"""
import glob, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CANON = HERE / 'inputs' / 'canonical.json'
PROJ = HERE / 'smartcoaster_easyeda'

def rid(seed):
    return hashlib.md5(seed.encode()).hexdigest()[:16]

def line_record(ticket, t, seed):
    return ('{"type":"LINE","ticket":%d,"id":"%s"}||{"partitionId":"","groupId":0,'
            '"netName":"%s","layerId":%d,"startX":%s,"startY":%s,"endX":%s,"endY":%s,'
            '"width":%s,"locked":false,"zIndex":-1}|') % (
        ticket, rid(seed), t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], t['width_mil'])

def via_record(ticket, v, seed):
    return ('{"type":"VIA","ticket":%d,"id":"%s"}||{"partitionId":"","groupId":0,'
            '"netName":"%s","ruleName":"viaSize","centerX":%s,"centerY":%s,'
            '"holeDiameter":%s,"viaDiameter":%s,"viaType":"NORMAL",'
            '"topSolderExpansion":null,"bottomSolderExpansion":null,"unusedInnerLayers":[],'
            '"locked":false,"zIndex":-1}|') % (
        ticket, rid(seed), v['net'], v['x'], v['y'], v['drill_mil'], v['diameter_mil'])

def main():
    doc = json.loads(CANON.read_text())
    copper = doc['copper']
    files = sorted(PROJ.glob('pcb/*.epcb2'))
    assert len(files) == 1, files
    f = files[0]
    lines = f.read_text().split('\n')

    desired, ids = [], set()
    for i, t in enumerate(copper['tracks']):
        if not t['net']:
            continue
        seed = f"track|{i}|{t['net']}|{t['x1']}|{t['y1']}|{t['x2']}|{t['y2']}|{t['layer']}|{t['width_mil']}"
        ids.add(rid(seed))
        desired.append(('track', t, seed))
    for i, v in enumerate(copper['vias']):
        if not v['net']:
            continue
        seed = f"via|{i}|{v['net']}|{v['x']}|{v['y']}|{v['diameter_mil']}|{v['drill_mil']}"
        ids.add(rid(seed))
        desired.append(('via', v, seed))

    # idempotent: drop records this script wrote on a previous run
    kept = []
    for line in lines:
        if '||' in line:
            try:
                head = json.loads(line.split('||', 1)[0])
            except Exception:
                head = None
            if head and head.get('id') in ids:
                continue
        kept.append(line)
    # ticket base = max ticket in the *main* doc (after the last DOCHEAD)
    last_head = max(i for i, l in enumerate(kept) if '"type":"DOCHEAD"' in l) if any('"type":"DOCHEAD"' in l for l in kept) else 0
    max_ticket = 0
    for line in kept[last_head:]:
        if '||' not in line:
            continue
        try:
            h = json.loads(line.split('||', 1)[0])
        except Exception:
            continue
        if isinstance(h.get('ticket'), int):
            max_ticket = max(max_ticket, h['ticket'])
    ticket = max_ticket
    out = []
    for kind, item, seed in desired:
        ticket += 1
        out.append(line_record(ticket, item, seed) if kind == 'track' else via_record(ticket, item, seed))
    while kept and kept[-1] == '':
        kept.pop()
    f.write_text('\n'.join(kept + out) + '\n')
    print(f'ported copper into {f.name}: {len(copper["tracks"])} tracks + {len(copper["vias"])} vias '
          f'(tickets {max_ticket + 1}..{ticket})')

if __name__ == '__main__':
    main()
