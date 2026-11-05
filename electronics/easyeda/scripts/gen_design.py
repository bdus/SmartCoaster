#!/usr/bin/env python3
"""Turn inputs/canonical.json (extracted from the frozen KiCad design) into the
eprj3 skill's declarative design.json.  Single source: canonical.json only."""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / 'inputs' / 'canonical.json'
DST = HERE / 'design' / 'design.json'
POWERS = {'GND': 'down', '3V3': 'up', 'VBUS': 'up', 'VBAT': 'up'}
DESIGNATOR = {'U': 'U', 'R': 'R', 'C': 'C', 'J': 'J', 'SW': 'SW', 'H': 'H'}

def clean_pin_name(name):
    if not name:
        return ''
    name = re.sub(r'~\{([^}]*)\}', r'\1', name)
    name = re.sub(r'[^A-Za-z0-9_+\-/.]', '', name)
    return name[:24] or 'P'

def main():
    doc = json.loads(SRC.read_text())
    parts, place = [], {}
    used_nets = set()
    for p in doc['parts']:
        ref = p['ref']
        prefix = re.match(r'[A-Za-z]+', ref).group(0)
        # dedupe pads by number (USB-C shell has 4 pads on one number)
        seen, pads, pins, pins_seen = set(), [], [], set()
        for pad in p['pads']:
            num = str(pad['num'])
            net = pad.get('pin_net') or 'NC'
            if num in seen:
                # keep the pad geometry in the footprint, but one symbol pin
                continue
            seen.add(num)
            if net != 'NC':
                used_nets.add(net)
            pname = clean_pin_name(pad.get('pin_name') or '')
            base = pname or f'P{num}'
            pname, k = base, 2
            while pname in pins_seen:
                pname = f"{base}_{k}"; k += 1
            pins_seen.add(pname)
            pins.append(f"{num}:{pname}")
        # all pads including duplicates for the footprint geometry
        fp_pads = []
        for pad in p['pads']:
            num = pad['num']
            entry = [num if not num.isdigit() else int(num), round(pad['x'], 3), round(pad['y'], 3),
                     round(pad['w'], 3), round(pad['h'], 3)]
            if pad.get('drill'):
                entry.append(round(pad['drill'], 3))
            fp_pads.append(entry)
        pinmap = {}
        for pad in p['pads']:
            num = str(pad['num'])
            net = pad.get('pin_net') or 'NC'
            pinmap.setdefault(num, net)
        parts.append({
            'id': ref,
            'symbol': {'name': f"{ref}_{p['footprint'][:28]}", 'designator': DESIGNATOR.get(prefix, 'U'), 'pins': pins},
            'footprint': {'name': f"{p['footprint'][:40]}", 'designator': DESIGNATOR.get(prefix, 'U'),
                          'pads': fp_pads, 'outline': None},
            'pins': pinmap,
            'value': p['value'],
            'name': p.get('mpn') or p['value'],
        })
        place[ref] = [p['place_mil'][0], p['place_mil'][1], p['place_mil'][2]]
    # drop None outline fields (schema tolerates omission better)
    for part in parts:
        if part['footprint'].get('outline') is None:
            del part['footprint']['outline']
    blocks = [{'title': b['title'], 'parts': b['parts']} for b in doc['blocks']]
    design = {
        'name': 'smartcoaster_easyeda',
        'sheet': {'schematic': 'SmartCoaster', 'name': 'SmartCoaster V1 schematic (EasyEDA re-implementation)'},
        'powers': POWERS,
        'blocks': blocks,
        'parts': parts,
        'pcb': {
            'place': place,
            'layout': 'skill',
            'rules': {'clearance': 8, 'trackWidth': 8, 'edgeClearance': 12,
                      'minDrill': 12, 'minRing': 4, 'minAngle': 45},
        },
        'meta': {
            'function': 'Smart coaster main board: USB-C charging, Li-ion protection, 3V3 rail, ESP32-S3 MCU, HX711 load-cell front-end, OLED header, key header, battery sense.',
            'input': 'USB-C 5 V (VBUS) / LiPo 3.7 V (VBAT)',
            'rails': ['VBUS 5V', 'VBAT 3.0-4.2V', '3V3 3.3V'],
            'interfaces': ['USB 2.0', 'I2C OLED', 'HX711 2-wire', 'UART/BOOT', 'BLE antenna'],
            'mcu': 'ESP32-S3-MINI-1 (N8R2)',
            'layers': 2,
            'modules': [b['title'] for b in blocks],
            'source': 'electronics/kicad design.py / netlist @ 2026-11-04 (frozen)',
        },
    }
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(design, indent=2, ensure_ascii=False) + '\n')
    print(f"wrote {DST}  parts={len(parts)}  blocks={len(blocks)}  nets={len(used_nets)}")

if __name__ == '__main__':
    main()
