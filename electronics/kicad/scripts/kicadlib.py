"""Load KiCad 9 symbol libraries and extract pins / flattens `extends` inheritance."""

import os

import ksexpr

SYMBOL_ROOT = os.environ.get(
    'KICAD9_SYMBOL_DIR', '/data/Documents/tools/kicad/usr/share/kicad/symbols')

_cache = {}


def lib_path(libname):
    return os.path.join(SYMBOL_ROOT, libname + '.kicad_sym')


def load_lib(libname):
    if libname not in _cache:
        with open(lib_path(libname), encoding='utf-8') as f:
            root = ksexpr.parse(f.read())
        syms = {}
        for node in root:
            if isinstance(node, list) and node and node[0] == 'symbol':
                syms[node[1]] = node
        _cache[libname] = syms
    return _cache[libname]


def resolve(libname, name, _seen=None):
    """Return a flattened symbol node (extends resolved, properties from child)."""
    syms = load_lib(libname)
    if name not in syms:
        raise KeyError('%s:%s not found' % (libname, name))
    node = syms[name]
    parent_ref = ksexpr.first(node, 'extends')
    if parent_ref is None:
        return node
    pname = parent_ref[1]
    _seen = _seen or set()
    if pname in _seen:
        raise ValueError('extends cycle %s' % pname)
    _seen.add(pname)
    parent = resolve(libname, pname, _seen)
    merged = [ksexpr.Atom('symbol'), ksexpr.QStr(name)]
    own_props = {}
    own_children = []
    for c in node[2:]:
        if isinstance(c, list) and c and c[0] == 'property':
            own_props[c[1]] = c
        elif isinstance(c, list) and c and c[0] in ('symbol', 'pin_names', 'pin_numbers',
                                                    'exclude_from_sim', 'in_bom', 'on_board'):
            own_children.append(c)
    for c in parent[2:]:
        if isinstance(c, list) and c and c[0] == 'property':
            if c[1] in own_props:
                merged.append(own_props.pop(c[1]))
            else:
                merged.append(c)
        elif isinstance(c, list) and c and c[0] in ('symbol', 'pin_names', 'pin_numbers',
                                                    'exclude_from_sim', 'in_bom', 'on_board'):
            if c[0] == 'symbol' and isinstance(c[1], str) and c[1].startswith(pname + '_'):
                c = [c[0], ksexpr.QStr(name + c[1][len(pname):])] + list(c[2:])
            merged.append(c)
    merged.extend(own_props.values())
    merged.extend(own_children)
    return merged


def pins(libname, name):
    """List of dicts: number, name, type, x, y, angle, length, unit, style, hide."""
    sym = resolve(libname, name)
    out = []
    base = ksexpr.first(sym, 'pin')  # top-level pins (rare)
    if base:
        out.append(_pin(base, 0, 0))
    for c in sym:
        if isinstance(c, list) and c and c[0] == 'symbol':
            sub = c[1]
            parts = sub.rsplit('_', 2)
            unit = int(parts[1]) if len(parts) == 3 and parts[1].isdigit() else 0
            style = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 1
            for p in c:
                if isinstance(p, list) and p and p[0] == 'pin':
                    out.append(_pin(p, unit, style))
    return out


def _pin(p, unit, style):
    at = ksexpr.first(p, 'at')
    ln = ksexpr.first(p, 'length')
    name = ksexpr.first(p, 'name')
    num = ksexpr.first(p, 'number')
    hide = ksexpr.first(p, 'hide')
    d = {
        'number': num[1],
        'name': name[1],
        'type': p[1],
        'x': float(at[1]), 'y': float(at[2]),
        'angle': float(at[3]) if len(at) > 3 else 0.0,
        'length': float(ln[1]) if ln else 0.0,
        'unit': unit, 'style': style,
        'hide': bool(hide) and (len(hide) < 2 or hide[1] in ('yes', 'true')),
    }
    if len(p) > 2 and p[2] == 'line':
        d['shape'] = 'line'
    import math
    d['ovx'] = -math.cos(math.radians(d['angle']))
    d['ovy'] = -math.sin(math.radians(d['angle']))
    return d


def symbol_units(libname, name):
    sym = resolve(libname, name)
    us = set()
    for c in sym:
        if isinstance(c, list) and c and c[0] == 'symbol':
            parts = c[1].rsplit('_', 2)
            if len(parts) == 3 and parts[1].isdigit():
                us.add(int(parts[1]))
    return sorted(us) or [1]


def property_node(libname, name, key, default=''):
    sym = resolve(libname, name)
    for c in sym:
        if isinstance(c, list) and c and c[0] == 'property' and c[1] == key:
            return c[2]
    return default


if __name__ == '__main__':
    import sys
    for arg in sys.argv[1:]:
        lib, nm = arg.split(':')
        print('==', arg, 'units:', symbol_units(lib, nm))
        for p in sorted(pins(lib, nm), key=lambda d: (d['unit'], int(d['number'].split('-')[0])
                                                      if d['number'][0].isdigit() else 0)):
            print('  %-6s %-14s %-10s unit=%d at=(%6.2f,%6.2f) ang=%3d len=%.2f%s' % (
                p['number'], p['name'], p['type'], p['unit'], p['x'], p['y'], p['angle'],
                p['length'], ' HIDE' if p['hide'] else ''))
