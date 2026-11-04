#!/usr/bin/env python3
"""Generate electronics/kicad/smartcoaster/smartcoaster.kicad_sch from design.py.

Strategy: every component pin gets a short stub plus a net label (KiCad's
connectivity engine joins pins by label name).  Power pins are drawn the same
way; PWR_FLAG symbols mark the connector-fed nets so ERC sees a driver.
This keeps a 55-part netlist machine-verifiable: verify.py re-exports the
netlist and compares it pin-by-pin with design.py.
"""

import os
import uuid

import design
import kicadlib
import ksexpr

LIB = '/data/Documents/tools/kicad/usr/share/kicad/symbols'
STUB = 5.08


ROOT_UUID = '7c1f9a50-2b64-5b8e-9f0a-1d2c3b4a5e60'


def uid():
    return str(uuid.uuid4())


def stable_uid(ref):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'smartcoaster:' + ref))


def esc(v):
    return str(v).replace('\\', '\\\\').replace('"', '\\"')


def xf(px, py, rot):
    r = int(rot) % 360
    if r == 0:
        return (px, -py)
    if r == 90:
        return (-py, -px)
    if r == 180:
        return (-px, py)
    if r == 270:
        return (py, px)
    raise ValueError(rot)


def pid(part):
    return '%s:%s' % (part['lib'].split(':')[0], part['lib'].split(':')[1])


class Sch(object):
    def __init__(self):
        self.root = ROOT_UUID
        self.libs = {}
        self.body = []

    def lib_node(self, lib_id):
        if lib_id in self.libs:
            return self.libs[lib_id]
        if lib_id in design.CUSTOM_SYMBOLS:
            node = ksexpr.parse(design.CUSTOM_SYMBOLS[lib_id].strip())
        else:
            lib, name = lib_id.split(':')
            node = kicadlib.resolve(lib, name)
        node = list(node)
        node[1] = ksexpr.QStr(lib_id)
        self.libs[lib_id] = node
        return node

    # -- primitives ------------------------------------------------------
    def wire(self, x1, y1, x2, y2):
        self.body.append(
            '(wire\n\t\t(pts\n\t\t\t(xy %.2f %.2f) (xy %.2f %.2f)\n\t\t)\n'
            '\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)' % (x1, y1, x2, y2, uid()))

    def label(self, text, x, y, ang):
        just = 'right bottom' if ang in (180, 270) else 'left bottom'
        self.body.append(
            '(label "%s"\n\t\t(at %.2f %.2f %d)\n\t\t(effects\n\t\t\t(font\n'
            '\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)' % (text, x, y, ang, just, uid()))

    def no_connect(self, x, y):
        self.body.append('(no_connect\n\t\t(at %.2f %.2f)\n\t\t(uuid "%s")\n\t)'
                         % (x, y, uid()))

    def text(self, s, x, y, size=2.0, bold=True):
        b = '\n\t\t\t\t(bold yes)' if bold else ''
        self.body.append(
            '(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %.2f %.2f 0)\n'
            '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %.2f %.2f)%s\n\t\t\t)\n'
            '\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)'
            % (s, x, y, size, size, b, uid()))

    def rect(self, x1, y1, x2, y2):
        self.body.append(
            '(rectangle\n\t\t(start %.2f %.2f)\n\t\t(end %.2f %.2f)\n'
            '\t\t(stroke\n\t\t\t(width 0.127)\n\t\t\t(type dash)\n\t\t)\n'
            '\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "%s")\n\t)'
            % (x1, y1, x2, y2, uid()))


def emit_symbol(sch, part, pins_meta):
    lib_id = part['lib']
    sch.lib_node(lib_id)
    x, y = part['at']
    rot = part['rot']
    b = []
    b.append('(symbol\n\t\t(lib_id "%s")\n\t\t(at %.2f %.2f %d)\n\t\t(unit 1)\n'
             '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n'
             '\t\t(dnp no)\n\t\t(uuid "%s")'
             % (lib_id, x, y, rot, part['uuid']))
    cx, cy, top, right = part['bbox']
    if part['kind'] == 'passive':
        rx, ry = cx, top - 2.54
        vx, vy = cx, top - 5.08
        just = ''
    else:
        rx, ry = right + 2.54, top - 2.54
        vx, vy = right + 2.54, top - 5.08
        just = '\n\t\t\t\t(justify left)'
    props = [
        ('Reference', part['ref']),
        ('Value', part['value']),
        ('Footprint', part['fp']),
        ('Datasheet', '~'),
        ('Description', part.get('note', '')),
    ]
    for i, (k, v) in enumerate(props):
        px, py = (rx, ry) if k == 'Reference' else (vx, vy)
        hide = '' if i < 2 else '\n\t\t\t\t(hide yes)'
        j = just if i < 2 else just
        b.append('(property "%s" "%s"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n'
                 '\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)%s%s\n'
                 '\t\t\t)\n\t\t)' % (k, esc(v), px, py, hide, j))
    for pn in part['pin_numbers']:
        b.append('(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)' % (pn, uid()))
    b.append('(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n'
             '\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n'
             '\t\t\t)\n\t\t)' % (design.PROJECT, sch.root, part['ref']))
    b.append(')')
    sch.body.append('\n\t\t'.join(b))


def main():
    sch = Sch()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                       'smartcoaster', 'smartcoaster.kicad_sch')
    out = os.path.abspath(out)

    parts = []
    for p in design.PARTS:
        p = dict(p)
        p['uuid'] = stable_uid(p['ref'])
        # snap to the 1.27 mm connection grid so ERC does not warn off-grid
        p['at'] = (round(p['at'][0] / 1.27) * 1.27,
                   round(p['at'][1] / 1.27) * 1.27)
        parts.append(p)
    byref = {p['ref']: p for p in parts}

    # --- pin geometry ---------------------------------------------------
    for p in parts:
        metas = kicadlib.pins(p['lib'].split(':')[0], p['lib'].split(':')[1]) \
            if p['lib'] not in design.CUSTOM_SYMBOLS else custom_pins(p['lib'])
        p['pins'] = {}
        p['pin_numbers'] = sorted({m['number'] for m in metas},
                                  key=lambda s: (not s[0].isdigit(), s))
        xs, ys = [], []
        for m in metas:
            dx, dy = xf(m['x'], m['y'], p['rot'])
            ox, oy = xf(m['ovx'], m['ovy'], p['rot'])
            X, Y = p['at'][0] + dx, p['at'][1] + dy
            p['pins'][m['number']] = dict(
                x=X, y=Y, out=(ox, oy), hidden=m['hide'], type=m['type'],
                name=m['name'])
            xs.append(X)
            ys.append(Y)
        p['bbox'] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                     min(ys), max(xs))

    # --- sanity: every pin is in exactly one net -------------------------
    pin_net = {}
    for net, conns in design.NETS.items():
        for ref, pin in conns:
            if ref not in byref:
                raise SystemExit('unknown ref %s in net %s' % (ref, net))
            key = (ref, pin)
            if pin not in byref[ref]['pins']:
                raise SystemExit('%s has no pin %s' % (ref, pin))
            if key in pin_net:
                raise SystemExit('%s.%s in nets %s and %s'
                                 % (ref, pin, pin_net[key], net))
            pin_net[key] = net
    for p in parts:
        for pn in p['pins']:
            if (p['ref'], pn) not in pin_net and (p['ref'], pn) not in design.NC_PINS:
                print('  [NC] %s.%s (%s)' % (p['ref'], pn, p['pins'][pn]['name']))

    # --- place pins -------------------------------------------------------
    for p in parts:
        emit_symbol(sch, p, None)

    seen = {}
    for p in parts:
        for pn, m in p['pins'].items():
            if m['hidden'] or m['type'] == 'no_connect':
                continue
            net = pin_net.get((p['ref'], pn))
            key = (round(m['x'], 2), round(m['y'], 2))
            if key in seen:
                if seen[key] != net:
                    raise SystemExit('stacked pins %s at %s on %s and %s'
                                     % (p['ref'] + '.' + pn, key, seen[key], net))
                continue
            seen[key] = net
            ox, oy = m['out']
            if net is None:
                sch.no_connect(m['x'], m['y'])
                continue
            ex, ey = m['x'] + STUB * ox, m['y'] + STUB * oy
            sch.wire(m['x'], m['y'], ex, ey)
            if ox > 0.5:
                ang = 0
            elif ox < -0.5:
                ang = 180
            elif oy > 0.5:
                ang = 270
            else:
                ang = 90
            sch.label(net, ex, ey, ang)

    # --- PWR_FLAGs --------------------------------------------------------
    flag_pin = kicadlib.pins('power', 'PWR_FLAG')[0]
    for i, net in enumerate(design.PWR_FLAGS):
        X, Y = 254.0 + 30.48 * i, 222.25
        sch.lib_node('power:PWR_FLAG')
        b = ('(symbol\n\t\t(lib_id "power:PWR_FLAG")\n\t\t(at %.2f %.2f 0)\n'
             '\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n'
             '\t\t(on_board no)\n\t\t(dnp no)\n\t\t(uuid "%s")\n'
             '\t\t(property "Reference" "#FLG%02d"\n\t\t\t(at %.2f %.2f 0)\n'
             '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
             '\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
             '\t\t(property "Value" "PWR_FLAG"\n\t\t\t(at %.2f %.2f 0)\n'
             '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
             '\t\t\t\t)\n\t\t\t)\n\t\t)\n'
             '\t\t(property "Footprint" ""\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n'
             '\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
             '\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
             '\t\t(property "Datasheet" ""\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n'
             '\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
             '\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
             '\t\t(property "Description" "Power flag"\n\t\t\t(at %.2f %.2f 0)\n'
             '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
             '\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
             '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n'
             '\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n'
             '\t\t\t\t\t(reference "#FLG%02d")\n\t\t\t\t\t(unit 1)\n'
             '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)'
             % (X, Y, uid(), i + 1, X, Y + 2.54, X, Y - 2.54, X, Y, X, Y,
                X, Y, uid(), design.PROJECT, sch.root, i + 1))
        sch.body.append(b)
        sch.wire(X, Y, X, Y + 5.08)
        sch.label(net, X, Y + 5.08, 270)

    # --- block frames + titles -------------------------------------------
    for title, x1, y1, x2, y2 in design.BLOCKS:
        sch.rect(x1, y1, x2, y2)
        sch.text(title, x1 + 2, y1 + 6, size=2.5)

    # --- write ------------------------------------------------------------
    lib_txt = '\n'.join('\t\t' + ksexpr.dump(v).replace('\n', '\n\t')
                        for v in sch.libs.values())
    head = (
        '(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n'
        '\t(generator_version "9.0")\n\t(uuid "%s")\n\t(paper "%s")\n'
        '\t(title_block\n\t\t(title "%s")\n\t\t(date "%s")\n\t\t(rev "%s")\n'
        '\t\t(comment 1 "Generated by gen_sch.py - see REPORT.md")\n\t)\n'
        '\t(lib_symbols\n%s\n\t)\n' % (sch.root, design.PAPER, design.TITLE,
                                       design.DATE, design.REV, lib_txt))
    tail = ('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n'
            '\t(embedded_fonts no)\n)\n')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(head + '\n'.join('\t' + b for b in sch.body) + '\n' + tail)

    # project symbol library + lib table so the custom parts resolve
    d = os.path.dirname(out)
    lib_src = ['(kicad_symbol_lib\n\t(version 20241209)\n'
               '\t(generator "kicad_symbol_editor")\n\t(generator_version "9.0")\n']
    for lib_id, text in design.CUSTOM_SYMBOLS.items():
        node = ksexpr.parse(text.strip())
        node[1] = ksexpr.QStr(lib_id.split(':')[1])
        lib_src.append('\t' + ksexpr.dump(node) + '\n')
    lib_src.append(')\n')
    with open(os.path.join(d, 'smartcoaster.kicad_sym'), 'w', encoding='utf-8') as f:
        f.write(''.join(lib_src))
    import json
    tpl = ('/data/Documents/tools/kicad/usr/share/kicad/demos/interf_u/'
           'interf_u.kicad_pro')
    pro = json.load(open(tpl, encoding='utf-8'))
    pro['meta']['filename'] = 'smartcoaster.kicad_pro'
    pro['sheets'] = [[sch.root, 'Root']]
    pro['boards'] = []
    pro['libraries'] = {'pinned_footprint_libs': [], 'pinned_symbol_libs': []}
    pro['board']['design_settings']['rules'].update({
        'min_clearance': 0.2, 'min_track_width': 0.2,
        'min_via_diameter': 0.5, 'min_microvia_diameter': 0.2,
        'min_through_hole_diameter': 0.3,
        'min_hole_to_hole': 0.25, 'min_copper_edge_clearance': 0.3,
    })
    for cls in pro['net_settings']['classes']:
        cls['clearance'] = 0.2
        cls['track_width'] = 0.25
        cls['via_diameter'] = 0.6
        cls['via_drill'] = 0.3
    sev = pro['board']['design_settings'].setdefault('rule_severities', {})
    # Silkscreen is cosmetic for this board (JLC clips silk over copper, refdes
    # are placed from the pos file).  The 4-layer variant used the same policy,
    # so keep both variants comparable.
    sev['silk_over_copper'] = 'ignore'
    sev['silk_overlap'] = 'ignore'
    # Board footprints are generated from libs/ + footprints/SmartCoaster.pretty
    # by gen_pcb.py; a library mismatch is not actionable here.
    sev['lib_footprint_mismatch'] = 'warning'
    pro['board']['design_settings']['track_widths'] = [0, 0.2, 0.25, 0.4, 0.6, 1.0]
    pro['board']['design_settings']['via_dimensions'] = [
        {'diameter': 0.6, 'drill': 0.3}, {'diameter': 0.8, 'drill': 0.4}]
    with open(os.path.join(d, 'smartcoaster.kicad_pro'), 'w', encoding='utf-8') as f:
        json.dump(pro, f, indent=2)
    with open(os.path.join(d, 'sym-lib-table'), 'w', encoding='utf-8') as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                '  (lib (name "smartcoaster")(type "KiCad")'
                '(uri "${KIPRJMOD}/smartcoaster.kicad_sym")(options "")(descr "SmartCoaster project symbols"))\n)\n')
    # footprint lib table so U1 (SmartCoaster:ESP32-S3-MINI-1) resolves and DRC
    # does not report "footprint library not configured".
    with open(os.path.join(d, 'fp-lib-table'), 'w', encoding='utf-8') as f:
        f.write('(fp_lib_table\n  (version 7)\n'
                '  (lib (name "SmartCoaster")(type "KiCad")'
                '(uri "${KIPRJMOD}/../footprints/SmartCoaster.pretty")(options "")(descr "SmartCoaster project footprints"))\n)\n')
    print('wrote', out, os.path.getsize(out), 'bytes')
    print('parts', len(parts), 'nets', len(design.NETS),
          'labels', sum(1 for b in sch.body if b.startswith('(label')))


def custom_pins(lib_id):
    """Pins of a custom symbol, including the outward direction."""
    node = ksexpr.parse(design.CUSTOM_SYMBOLS[lib_id].strip())
    out = []
    for c in node:
        if isinstance(c, list) and c and c[0] == 'symbol':
            for p in c:
                if isinstance(p, list) and p and p[0] == 'pin':
                    at = ksexpr.first(p, 'at')
                    x, y, a = float(at[1]), float(at[2]), float(at[3])
                    import math
                    out.append(dict(
                        number=ksexpr.first(p, 'number')[1],
                        name=ksexpr.first(p, 'name')[1],
                        type=p[1],
                        x=x, y=y, angle=a, length=0, unit=1, hide=False,
                        ovx=-math.cos(math.radians(a)),
                        ovy=-math.sin(math.radians(a))))
    return out


if __name__ == '__main__':
    main()
