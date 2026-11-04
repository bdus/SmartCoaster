#!/usr/bin/env python3
"""Re-export the netlist with kicad-cli and compare it pin-by-pin with design.py.

This is the real check that the generated schematic is electrically what the
design says (stub/label geometry can silently merge or drop nets).
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import design

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.join(HERE, '..', 'smartcoaster', 'smartcoaster.kicad_sch')
OUT = os.path.join(HERE, '..', 'build', 'smartcoaster.net.xml')


def export(path=SCH, out=OUT):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml',
           '-o', out, path]
    env = dict(os.environ)
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0 or not os.path.exists(out):
        print(r.stdout)
        print(r.stderr)
        raise SystemExit('netlist export failed (%d)' % r.returncode)
    return out


def read_netlist(path=OUT):
    tree = ET.parse(path)
    root = tree.getroot()
    comps = {}
    for c in root.iter('comp'):
        comps[c.get('ref')] = {
            'value': (c.findtext('value') or ''),
            'footprint': (c.findtext('footprint') or ''),
        }
    nets = {}
    for n in root.iter('net'):
        name = n.get('name')
        pins = set()
        for node in n.findall('node'):
            pins.add((node.get('ref'), node.get('pin')))
        nets[name] = pins
    return comps, nets


def main():
    export()
    comps, nets = read_netlist()
    ok = True

    want_refs = {p['ref'] for p in design.PARTS}
    got_refs = set(comps)
    missing = want_refs - got_refs
    extra = got_refs - want_refs
    if missing or extra:
        ok = False
        print('REF MISMATCH missing=%s extra=%s' % (sorted(missing), sorted(extra)))

    # map (ref,pin) -> actual net name
    pin2net = {}
    for name, pins in nets.items():
        for k in pins:
            pin2net[k] = name

    problems = []
    for net, conns in design.NETS.items():
        want = set(conns)
        actual_names = {pin2net.get(c) for c in want}
        if len(actual_names) != 1:
            problems.append('net %-12s split across %s' % (net, sorted(actual_names)))
            continue
        an = actual_names.pop()
        got = nets.get(an, set())
        if got != want:
            problems.append('net %-12s (%s) extra=%s missing=%s'
                            % (net, an, sorted(got - want), sorted(want - got)))

    # any net in the schematic that we did not intend?
    intended_actual = set()
    for conns in design.NETS.values():
        for c in conns:
            if c in pin2net:
                intended_actual.add(pin2net[c])
    stray = {n: p for n, p in nets.items()
             if n not in intended_actual and p and not n.startswith('unconnected-')}
    for n, p in sorted(stray.items()):
        problems.append('unintended net %-12s %s' % (n, sorted(p)))

    # unconnected pins must be exactly NC_PINS
    all_pins = set()
    for p in design.PARTS:
        for pin in p.get('pin_numbers', []):
            all_pins.add((p['ref'], pin))
    real_pins = {k for k, n in pin2net.items() if not n.startswith('unconnected-')}
    floating = {c for c in all_pins if c not in real_pins}
    if floating - set(design.NC_PINS):
        problems.append('floating pins not marked NC: %s'
                        % sorted(floating - set(design.NC_PINS)))

    for pr in problems:
        ok = False
        print('FAIL ' + pr)

    print('components=%d nets=%d intended_nets=%d'
          % (len(comps), len(nets), len(design.NETS)))
    print('RESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
