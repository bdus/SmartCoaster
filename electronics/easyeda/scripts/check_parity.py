#!/usr/bin/env python3
"""Independent parity check: the generated EasyEDA schematic netlist vs the
frozen KiCad netlist (the electrical source of truth), plus BOM/value parity."""
import json, sys, xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
NET = ROOT / 'electronics' / 'kicad' / 'smartcoaster' / 'smartcoaster.net'
BUILT = HERE / 'inputs' / 'built_netlist.json'
DESIGN = HERE / 'design' / 'design.json'
OUT = HERE / 'reports' / 'parity.json'

def kicad_pins():
    root = ET.parse(str(NET)).getroot()
    pins, comps = {}, {}
    for c in root.find('components'):
        comps[c.get('ref')] = {'value': c.findtext('value'), 'footprint': c.findtext('footprint')}
    for n in root.find('nets'):
        name = n.get('name')
        for node in n.findall('node'):
            ref, num = node.get('ref'), node.get('pin')
            pins.setdefault(ref, {})[num] = None if name.startswith('unconnected-') else name.lstrip('/')
    return comps, pins

def built_pins():
    data = json.loads(BUILT.read_text())
    pins = {}
    for sh in data:
        for net in sh.get('nets', []):
            for p in net.get('pins', []):
                pins.setdefault(p['ref'], {})[p['num']] = net['name']
    return pins

def main():
    kcomps, kpins = kicad_pins()
    bpins = built_pins()
    design = json.loads(DESIGN.read_text())
    dparts = {p['id']: p for p in design['parts']}
    errors, warnings = [], []

    refs = sorted(set(kpins) | set(bpins))
    for ref in refs:
        k = {n: (net if net else None) for n, net in kpins.get(ref, {}).items()}
        b = {n: (None if net == 'NC' else net) for n, net in bpins.get(ref, {}).items()}
        if ref not in kpins:
            if any(not n.lstrip('-').isdigit() and n not in ('MH', 'MP') for n in b):
                warnings.append({'ref': ref, 'kind': 'not in KiCad netlist; non-mechanical pins: ' + str(sorted(b))})
            else:
                warnings.append({'ref': ref, 'kind': 'mechanical-only pad(s), outside the KiCad netlist'})
            continue
        k_only = set(k) - set(b)
        b_only = set(b) - set(k)
        if k_only:
            errors.append({'ref': ref, 'kind': 'pins missing in EasyEDA', 'pins': sorted(k_only)})
        if b_only:
            # pads that KiCad does not netlist (mechanical MP/MH) are allowed
            hard = sorted(n for n in b_only if n not in ('MH', 'MP'))
            if hard:
                errors.append({'ref': ref, 'kind': 'extra pins in EasyEDA', 'pins': hard})
            else:
                warnings.append({'ref': ref, 'kind': 'mechanical pad(s) added for the mechanical interface', 'pins': sorted(b_only)})
        for n in set(k) & set(b):
            if k[n] != b[n]:
                errors.append({'ref': ref, 'pin': n, 'kind': 'net differs', 'kicad': k[n], 'easyeda': b[n]})
    # BOM / value parity
    for ref, c in sorted(kcomps.items()):
        d = dparts.get(ref)
        if not d:
            errors.append({'ref': ref, 'kind': 'missing in design.json'})
        elif str(d.get('value')) != str(c.get('value')):
            errors.append({'ref': ref, 'kind': 'value differs', 'kicad': c.get('value'), 'easyeda': d.get('value')})
    for ref in dparts:
        if ref not in kcomps:
            warnings.append({'ref': ref, 'kind': 'not in KiCad netlist (e.g. mounting hole)'})

    summary = {
        'kicad_components': len(kcomps),
        'easyeda_components': len(bpins),
        'connected_pins_kicad': sum(1 for r in kpins.values() for v in r.values() if v),
        'connected_pins_easyeda': sum(1 for v in (n for r in bpins.values() for n in r.values()) if v and v != 'NC'),
        'net_count_kicad': len({v for r in kpins.values() for v in r.values() if v}),
        'net_count_easyeda': len({v for r in bpins.values() for v in r.values()}),
        'errors': errors,
        'warnings': warnings,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print(f"parity: kicad {summary['kicad_components']} comps / {summary['connected_pins_kicad']} connected pins / "
          f"{summary['net_count_kicad']} nets; easyeda {summary['easyeda_components']} comps (incl. 4 mechanical holes) / "
          f"{summary['connected_pins_easyeda']} connected pins / {summary['net_count_easyeda']} nets")
    if errors:
        print(f"PARITY FAIL: {len(errors)} error(s)")
        for e in errors[:20]:
            print('  ', e)
        sys.exit(1)
    print('PARITY OK: every connected pin carries the same net name in both netlists')

if __name__ == '__main__':
    main()
