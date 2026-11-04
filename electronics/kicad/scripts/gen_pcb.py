#!/usr/bin/env python3
"""Generate smartcoaster.kicad_pcb: C-ring outline + placement (2 layers, no routing yet).

Outline reproduces mechanical/square_v1/cad/square_model.py::make_pcb():
  93.2 x 93.2, R6 corners, 38 x 38 centre opening, 80 deg front C-notch,
  4 x M2 mounting holes on a 80 x 48 pattern.
Mechanical coordinates are Y-up with the front at -Y; KiCad is Y-down, so
kicad_y = -mech_y.
"""

import math
import os
import sys

import design
import ksexpr
from ksexpr import Atom, QStr

FP_ROOT = os.environ.get(
    'KICAD9_FOOTPRINT_DIR', '/data/Documents/tools/kicad/usr/share/kicad/footprints')

PCB = 93.2
PCB_HALF = PCB / 2.0
CORNER_R = 6.0
HOLE = 38.0
HOLE_HALF = HOLE / 2.0
GAP_DEG = 80.0
HOLES = ((40.0, 24.0), (-40.0, 24.0), (-40.0, -24.0), (40.0, -24.0))

# ref -> (x_kicad, y_kicad, rot)
PLACEMENT = {
    'U1':  (29.0, -35.8, 0),      # ESP32-S3-MINI-1, rear right, antenna to edge
    'U2':  (39.0, 0.0, 90),       # HX711, right flank
    'J3':  (39.5, 12.0, 90),      # load-cell connector, next to HX711
    'J1':  (0.0, -41.0, 0),       # USB-C, rear edge
    'U3':  (13.0, -36.0, 0),      # TP4056 next to USB-C
    'U6':  (-13.0, -35.0, 0),     # LDO
    'U4':  (-24.0, -33.0, 0),     # DW01A
    'U5':  (-30.0, -38.0, 0),     # 8205A
    'J2':  (-34.0, -25.0, 90),    # battery JST-PH, rear left
    'J4':  (-28.5, 20.0, 90),     # OLED header, front left
    'J5':  (24.0, 21.0, 90),      # key connector, front right corner
    'D1':  (-32.0, -7.0, 0),      # halo RGB 1, left arm
    'D2':  (31.0, 27.0, 0),       # halo RGB 2, right arm
    'Q1':  (-39.0, 2.0, 0),
    'Q2':  (-39.0, 8.5, 0),
    'Q3':  (-39.0, 15.0, 0),
    'SW2': (10.0, -24.0, 0),      # RESET
    'SW3': (10.0, -29.0, 0),      # BOOT
    'TP1': (30.0, 5.0, 0),
    'TP2': (28.0, 11.0, 0),
    'TP3': (43.0, 18.0, 0),
    'TP4': (44.0, 21.0, 0),
    'TP5': (25.0, 4.0, 0),
    'TP6': (25.0, -2.0, 0),
    'U7': (-9.5, -43.5, 0),       # USB ESD, right behind the receptacle
    'R9': (-15.0, -43.0, 0),
    'R10': (-15.0, -40.5, 0),
}

# passives: packed around their functional block
PASSIVE = {
    # charger / protection
    'C1': (7.0, -33.0, 0), 'C3': (17.0, -31.5, 0), 'C2': (17.0, -28.5, 90),
    'R8': (4.0, -30.0, 0),
    'R11': (-18.0, -41.0, 0), 'C4': (-21.5, -41.0, 0), 'R12': (-25.0, -42.5, 0),
    # LDO caps + MCU support
    'C5': (-8.5, -38.0, 0), 'C6': (-5.0, -35.5, 0), 'C7': (-8.0, -31.0, 0),
    'C10': (33.0, -21.0, 0),
    'R1': (25.0, -22.0, 0), 'C9': (28.0, -22.0, 0),
    'R2': (17.0, -22.0, 0),
    # HX711 analogue front end (tight around U2)
    'C11': (37.0, 7.0, 0), 'C12': (40.0, 7.0, 0),
    'C14': (39.0, -5.0, 0), 'C15': (42.0, -5.0, 0), 'R5': (33.0, 8.0, 0),
    'R25': (28.0, 14.0, 0), 'R26': (30.5, 17.0, 0), 'C16': (24.5, 12.0, 0),
    # UI
    'R3': (24.0, -8.0, 0), 'R4': (24.0, -5.0, 0),
    'R13': (-36.0, -2.0, 0), 'R14': (-36.0, 4.5, 0), 'R15': (-36.0, 11.0, 0),
    'R16': (-42.0, -2.0, 0), 'R17': (-42.0, 4.5, 0), 'R18': (-42.0, 11.0, 0),
    'R19': (-27.5, 3.5, 0), 'R20': (-27.5, 6.5, 0), 'R21': (-27.5, 9.5, 0),
    'R22': (34.5, 15.0, 0), 'R23': (34.5, 18.0, 0), 'R24': (34.5, 21.0, 0),
    # battery sense
    'R6': (-42.0, -14.0, 0), 'R7': (-42.0, -11.0, 0), 'C13': (-42.0, -8.0, 0),
}


def mech_to_kicad(x, y):
    return (x, -y)


def arc_mid(cx, cy, ax, ay, bx, by):
    dx, dy = ax - cx, ay - cy
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    nx, ny = mx - cx, my - cy
    n = math.hypot(nx, ny) or 1.0
    return (cx + nx / n * math.hypot(dx, dy), cy + ny / n * math.hypot(dx, dy))


def outline_mech():
    """Closed C-ring boundary in mechanical coords (y up), as ('line',p) / ('arc',...) items."""
    t = math.tan(math.radians(50.0))          # 50 deg from -Y
    x_out = PCB_HALF / t                      # where the notch ray meets the front edge
    x_in = HOLE_HALF / t                      # where it meets the centre opening
    c = PCB_HALF - CORNER_R
    items = []
    items.append(('line', (x_out, -PCB_HALF), (c, -PCB_HALF)))
    items.append(('arc', (c, -c), (c, -PCB_HALF), (PCB_HALF, -c)))
    items.append(('line', (PCB_HALF, -c), (PCB_HALF, c)))
    items.append(('arc', (c, c), (PCB_HALF, c), (c, PCB_HALF)))
    items.append(('line', (c, PCB_HALF), (-c, PCB_HALF)))
    items.append(('arc', (-c, c), (-c, PCB_HALF), (-PCB_HALF, c)))
    items.append(('line', (-PCB_HALF, c), (-PCB_HALF, -c)))
    items.append(('arc', (-c, -c), (-PCB_HALF, -c), (-c, -PCB_HALF)))
    items.append(('line', (-c, -PCB_HALF), (-x_out, -PCB_HALF)))
    items.append(('line', (-x_out, -PCB_HALF), (-x_in, -HOLE_HALF)))
    items.append(('line', (-x_in, -HOLE_HALF), (-HOLE_HALF, -HOLE_HALF)))
    items.append(('line', (-HOLE_HALF, -HOLE_HALF), (-HOLE_HALF, HOLE_HALF)))
    items.append(('line', (-HOLE_HALF, HOLE_HALF), (HOLE_HALF, HOLE_HALF)))
    items.append(('line', (HOLE_HALF, HOLE_HALF), (HOLE_HALF, -HOLE_HALF)))
    items.append(('line', (HOLE_HALF, -HOLE_HALF), (x_in, -HOLE_HALF)))
    items.append(('line', (x_in, -HOLE_HALF), (x_out, -PCB_HALF)))
    return items


def load_footprint(lib_id):
    lib, name = lib_id.split(':')
    path = os.path.join(FP_ROOT, lib + '.pretty', name + '.kicad_mod')
    with open(path, encoding='utf-8') as f:
        node = ksexpr.parse(f.read())
    keep = []
    for c in node[2:]:
        if not isinstance(c, list):
            continue
        if c[0] in ('version', 'generator', 'generator_version', 'layer', 'at',
                    'tedit', 'tstamp', 'path'):
            continue
        if c[0] == 'property' and c[1] in ('Reference', 'Value', 'Footprint',
                                           'Datasheet', 'Description'):
            continue
        keep.append(c)
    return lib_id, keep


def N(*items):
    """Build an s-expression node; first item is the tag."""
    out = [Atom(items[0])]
    out.extend(items[1:])
    return out


def prop(name, value, x, y, layer, hide=False, size=0.8):
    eff = N('effects', N('font', N('size', size, size), N('thickness', 0.12)))
    if hide:
        eff.append(N('hide', Atom('yes')))
    return N('property', name, value, N('at', x, y, 0), N('layer', layer),
             N('uuid', uid()), eff)


_UUID = [0]


def uid():
    import uuid as _u
    return str(_u.uuid4())


def board_footprint(part, at, rot, netmap, sym_uuid):
    lib_id, children = load_footprint(part['fp'])
    out = N('footprint', lib_id, N('layer', 'F.Cu'), N('uuid', uid()),
            N('at', at[0], at[1], rot))
    # footprint field positions are relative to the footprint origin
    out.append(prop('Reference', part['ref'], 0, -2.2, 'F.SilkS'))
    out.append(prop('Value', part['value'], 0, 3.0, 'F.Fab', hide=True))
    out.append(prop('Footprint', part['fp'], 0, 0, 'F.Fab', hide=True))
    out.append(prop('Datasheet', '~', 0, 0, 'F.Fab', hide=True))
    out.append(prop('Description', part.get('note', ''), 0, 0, 'F.Fab', hide=True))
    out.append(N('path', '/' + sym_uuid))
    pad_net = {}
    if part.get('nets'):
        pad_net = part['nets']
    for c in children:
        if isinstance(c, list) and c and c[0] == 'zone':
            for pts in ksexpr.find_all(c, 'pts'):
                for xy in list(pts):
                    if isinstance(xy, list) and xy and xy[0] == 'xy':
                        lx, ly = float(xy[1]), float(xy[2])
                        dx, dy = (lx, ly) if rot == 0 else (
                            (ly, -lx) if rot == 90 else
                            ((-lx, -ly) if rot == 180 else (-ly, lx)))
                        xy[1] = Atom('%g' % (at[0] + dx))
                        xy[2] = Atom('%g' % (at[1] + dy))
        if isinstance(c, list) and c and c[0] == 'pad':
            # KiCad stores pad orientation in board coordinates: add footprint rot
            pat = ksexpr.first(c, 'at')
            if pat is not None:
                base = float(pat[3]) if len(pat) > 3 else 0.0
                ang = (base + rot) % 360
                if len(pat) > 3:
                    pat[3] = Atom('%g' % ang)
                else:
                    pat.append(Atom('%g' % ang))
            num = c[1]
            if num in pad_net:
                n = pad_net[num]
                net_node = N('net', netmap[n][0], n)
                if ksexpr.first(c, 'net'):
                    c = [x for x in c if not (isinstance(x, list) and x[0] == 'net')]
                idx = None
                for i, x in enumerate(c):
                    if isinstance(x, list) and x[0] == 'layers':
                        idx = i
                c = c[:idx + 1] + [net_node] + c[idx + 1:]
        out.append(c)
    return out


def main():
    parts = [dict(p) for p in design.PARTS]
    byref = {p['ref']: p for p in parts}

    # net numbering + per-footprint pad->net map
    netmap = {}
    for i, n in enumerate(design.NETS, start=1):
        netmap[n] = (i, n)
    for p in parts:
        p['nets'] = {}
    for n, conns in design.NETS.items():
        for ref, pin in conns:
            byref[ref]['nets'].setdefault(pin, n)

    # schematic symbol uuids for board<->schematic parity
    import uuid as _uuid
    for p in parts:
        p['uuid'] = str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'smartcoaster:' + p['ref']))

    items = outline_mech()
    body = []
    for it in items:
        if it[0] == 'line':
            (x1, y1), (x2, y2) = it[1], it[2]
            X1, Y1 = mech_to_kicad(x1, y1)
            X2, Y2 = mech_to_kicad(x2, y2)
            body.append(
                '(gr_line\n\t\t(start %.3f %.3f)\n\t\t(end %.3f %.3f)\n'
                '\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type default)\n\t\t)\n'
                '\t\t(layer "Edge.Cuts")\n\t\t(uuid "%s")\n\t)'
                % (X1, Y1, X2, Y2, uid()))
        else:
            (cx, cy), (ax, ay), (bx, by) = it[1], it[2], it[3]
            mx, my = arc_mid(cx, cy, ax, ay, bx, by)
            A = mech_to_kicad(ax, ay)
            B = mech_to_kicad(bx, by)
            M = mech_to_kicad(mx, my)
            body.append(
                '(gr_arc\n\t\t(start %.3f %.3f)\n\t\t(mid %.3f %.3f)\n'
                '\t\t(end %.3f %.3f)\n\t\t(stroke\n\t\t\t(width 0.05)\n'
                '\t\t\t(type default)\n\t\t)\n\t\t(layer "Edge.Cuts")\n'
                '\t\t(uuid "%s")\n\t)' % (A[0], A[1], M[0], M[1], B[0], B[1], uid()))

    # mounting holes
    mh = dict(ref='H1', lib='Mechanical', value='M2', kind='ic',
              fp='MountingHole:MountingHole_2.2mm_M2', note='M2 PCB screw')
    for i, (mx, my) in enumerate(HOLES):
        p = dict(mh)
        p['ref'] = 'H%d' % (i + 1)
        p['uuid'] = uid()
        X, Y = mech_to_kicad(mx, my)
        fp = board_footprint(p, (X, Y), 0, netmap, p['uuid'])
        body.append(ksexpr.dump(fp))

    # components
    placed = 0
    for p in parts:
        pos = PLACEMENT.get(p['ref']) or PASSIVE.get(p['ref'])
        if pos is None:
            print('!! no placement for', p['ref'])
            continue
        x, y, rot = pos
        body.append(ksexpr.dump(board_footprint(p, (x, y), rot, netmap, p['uuid'])))
        placed += 1

    # board text
    body.append(
        '(gr_text "SmartCoaster V1-B main board  rev %s"\n\t\t(at -30 -44)\n'
        '\t\t(layer "F.SilkS")\n\t\t(uuid "%s")\n\t\t(effects\n\t\t\t(font\n'
        '\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n'
        '\t\t\t(justify left bottom)\n\t\t)\n\t)' % (design.REV, uid()))

    nets = '\n'.join('\t(net %d "%s")' % (v[0], k) for k, v in netmap.items())
    head = (
        '(kicad_pcb\n\t(version 20241229)\n\t(generator "pcbnew")\n'
        '\t(generator_version "9.0")\n\t(general\n\t\t(thickness 1.6)\n'
        '\t\t(legacy_teardrops no)\n\t)\n\t(paper "A3")\n'
        '\t(title_block\n\t\t(title "%s")\n\t\t(date "%s")\n\t\t(rev "%s")\n'
        '\t\t(comment 1 "C-ring outline from square_v1 make_pcb(); 2 layers")\n'
        '\t)\n\t(layers\n'
        '\t\t(0 "F.Cu" signal)\n\t\t(31 "B.Cu" signal)\n'
        '\t\t(32 "B.Adhes" user "B.Adhesive")\n'
        '\t\t(33 "F.Adhes" user "F.Adhesive")\n'
        '\t\t(34 "B.Paste" user)\n\t\t(35 "F.Paste" user)\n'
        '\t\t(36 "B.SilkS" user "B.Silkscreen")\n'
        '\t\t(37 "F.SilkS" user "F.Silkscreen")\n'
        '\t\t(38 "B.Mask" user)\n\t\t(39 "F.Mask" user)\n'
        '\t\t(40 "Dwgs.User" user "User.Drawings")\n'
        '\t\t(41 "Cmts.User" user "User.Comments")\n'
        '\t\t(42 "Eco1.User" user "User.Eco1")\n'
        '\t\t(43 "Eco2.User" user "User.Eco2")\n'
        '\t\t(44 "Edge.Cuts" user)\n\t\t(45 "Margin" user)\n'
        '\t\t(46 "B.CrtYd" user "B.Courtyard")\n'
        '\t\t(47 "F.CrtYd" user "F.Courtyard")\n'
        '\t\t(48 "B.Fab" user)\n\t\t(49 "F.Fab" user)\n\t)\n'
        '\t(setup\n\t\t(pad_to_mask_clearance 0)\n'
        '\t\t(allow_soldermask_bridges_in_footprints no)\n'
        '\t\t(tenting front back)\n\t)\n'
        '\t(net 0 "")\n%s\n' % (design.TITLE, design.DATE, design.REV, nets))
    tail = '\t(embedded_fonts no)\n)\n'
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                       'smartcoaster', 'smartcoaster.kicad_pcb')
    out = os.path.abspath(out)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(head + '\n'.join('\t' + b for b in body) + '\n' + tail)
    print('wrote', out, os.path.getsize(out), 'bytes; footprints', placed + 4)


if __name__ == '__main__':
    main()
