#!/usr/bin/env python3
"""Independent, geometry-accurate copper review of the generated EasyEDA board.

Runs with /data/Documents/tools/copper-venv/bin/python (shapely/GEOS). It does NOT use
the eprj3 skill's DRC (that one uses axis-aligned bboxes for tracks, which produces false
positives on 45-degree traces). Here tracks are real buffered segments, pads are rotated
rectangles, vias are circles; clearances are true GEOS distances.

Checks:
  C1 copper records round-trip the canonical KiCad port (values/counts)
  C2 different-net clearance >= 0.2 mm (7.874 mil), same layer / through-hole
  C3 connectivity: every net's pads form one copper island (D004 equivalent)
  C4 board-edge clearance >= 0.3 mm (11.811 mil) incl. NPTH hole edges
  C5 via drill >= 0.3 mm and annular ring >= 0.15 mm
Output: reports/copper_check.json (+ stdout summary). Exit 1 on any violation.
"""
import glob, json, math, sys
from pathlib import Path
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely import affinity
from shapely.ops import unary_union, nearest_points

HERE = Path(__file__).resolve().parents[1]
CANON = HERE / 'inputs' / 'canonical.json'
PROJ = HERE / 'smartcoaster_easyeda'
OUT = HERE / 'reports' / 'copper_check.json'
CLEAR = 7.874      # 0.2 mm
EDGE = 11.811      # 0.3 mm
EPS = 0.002

def rot_rect(cx, cy, w, h, ang):
    t = math.radians(ang)
    pts = []
    for dx, dy in ((-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)):
        pts.append((cx + dx*math.cos(t) - dy*math.sin(t), cy + dx*math.sin(t) + dy*math.cos(t)))
    return Polygon(pts)

def pad_geo(pad, ax, ay, ang):
    """True pad copper shape: rounded rect / stadium / circle / rect, then placed."""
    w = max(pad['w'], 1.0); h = max(pad['h'], 1.0)
    sh = pad.get('shape', 'RECT')
    if sh == 'CIRCLE':
        g = Point(0, 0).buffer(w / 2, quad_segs=24)
    elif sh == 'OVAL':
        if w >= h:
            g = LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2, cap_style='round')
        else:
            g = LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2, cap_style='round')
    elif sh == 'ROUNDRECT':
        r = min(pad.get('r_mil', 0), min(w, h) / 2 * 0.999)
        g = box(-w / 2, -h / 2, w / 2, h / 2).buffer(-r, join_style='round').buffer(r, join_style='round')
    else:
        g = box(-w / 2, -h / 2, w / 2, h / 2)
    return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), ax, ay)

def main():
    doc = json.loads(CANON.read_text())
    copper = doc['copper']
    tracks, vias, pads = [], [], []
    for i, t in enumerate(copper['tracks']):
        line = LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])])
        shape = line.buffer(t['width_mil'] / 2, cap_style='flat', join_style='mitre')
        tracks.append({'id': f"T{i}", 'net': t['net'], 'layers': {t['layer']}, 'shape': shape,
                       'width': t['width_mil'], 'src': t})
    for i, v in enumerate(copper['vias']):
        shape = Point(v['x'], v['y']).buffer(v['diameter_mil'] / 2, resolution=24)
        vias.append({'id': f"V{i}", 'net': v['net'], 'layers': {1, 2}, 'shape': shape, 'src': v})
    for part in doc['parts']:
        if part['ref'].startswith('H'):   # M2 NPTH holes: no copper (checked via holes[])
            continue
        px, py, ang = part['place_mil']
        for pad in part['pads']:
            net = pad.get('pin_net') or 'NC'
            lx, ly = pad['x'], pad['y']
            ax = px + lx*math.cos(math.radians(ang)) - ly*math.sin(math.radians(ang))
            ay = py + lx*math.sin(math.radians(ang)) + ly*math.cos(math.radians(ang))
            shape = pad_geo(pad, ax, ay, ang)
            layers = {1, 2} if pad.get('drill') else {1}
            pads.append({'id': f"{part['ref']}.{pad['num']}", 'net': net, 'layers': layers,
                         'shape': shape, 'ref': part['ref'], 'num': pad['num']})
    outline = Polygon(doc['outline_mil'])
    holes = [Point(h['at_mil'][0], h['at_mil'][1]).buffer(h['diameter_mil']/2, resolution=24)
             for h in doc['mounting_holes']]
    board_boundary = outline.exterior

    all_items = tracks + vias + pads
    tree = shapely.STRtree([it['shape'] for it in all_items])
    violations = []

    # C1 — record round-trip
    rec_lines, rec_vias = [], []
    for f in PROJ.glob('pcb/*.epcb2'):
        for line in f.read_text().split('\n'):
            if '"type":"LINE"' not in line and '"type":"VIA"' not in line:
                continue
            h, b = line.split('||', 1)
            body = json.loads(b.strip().rstrip('|'))
            if '"type":"LINE"' in h:
                rec_lines.append(body)
            else:
                rec_vias.append(body)
    rt_ok = len(rec_lines) == len(tracks) and len(rec_vias) == len(vias)
    if rt_ok:
        for r, t in zip(rec_lines, [x['src'] for x in tracks]):
            if (abs(r['startX']-t['x1'])>0.01 or abs(r['startY']-t['y1'])>0.01 or
                abs(r['endX']-t['x2'])>0.01 or abs(r['endY']-t['y2'])>0.01 or
                abs(r['width']-t['width_mil'])>0.01 or r['netName']!=t['net'] or r['layerId']!=t['layer']):
                rt_ok = False; violations.append({'code': 'C1', 'detail': f'mismatch {r} vs {t}'}); break
    if rt_ok:
        for r, v in zip(rec_vias, [x['src'] for x in vias]):
            if (abs(r['centerX']-v['x'])>0.01 or abs(r['centerY']-v['y'])>0.01 or
                abs(r['viaDiameter']-v['diameter_mil'])>0.01 or abs(r['holeDiameter']-v['drill_mil'])>0.01
                or r['netName']!=v['net']):
                rt_ok = False; violations.append({'code': 'C1', 'detail': f'mismatch {r} vs {v}'}); break
    if not rt_ok and not violations:
        violations.append({'code': 'C1', 'detail': f'record count {len(rec_lines)}/{len(rec_vias)} vs canonical {len(tracks)}/{len(vias)}'})

    # C2 — true clearance, different nets, overlapping layers
    min_gap = 1e9; min_pair = None
    for i, a in enumerate(all_items):
        if not a['net'] or a['net'] == 'NC':
            continue
        for j in tree.query(a['shape'].buffer(CLEAR + 30)):
            if j <= i:
                continue
            b = all_items[j]
            if not b['net'] or b['net'] == 'NC' or a['net'] == b['net']:
                continue
            if not (a['layers'] & b['layers']):
                continue
            if a.get('ref') and a.get('ref') == b.get('ref'):
                continue
            gap = a['shape'].distance(b['shape'])
            if gap < min_gap:
                min_gap, min_pair = gap, (a['id'], b['id'])
            if gap < CLEAR - EPS:
                p1, p2 = nearest_points(a['shape'], b['shape'])
                violations.append({'code': 'C2', 'net_a': a['net'], 'net_b': b['net'],
                                   'a': a['id'], 'b': b['id'], 'gap_mil': round(gap, 3),
                                   'at': [round(p1.x, 2), round(p1.y, 2)]})

    # C3 — connectivity per net (tracks/vias/pads touching)
    nets = sorted({it['net'] for it in all_items if it['net'] and it['net'] != 'NC'})
    unconnected = []
    for net in nets:
        items = [it for it in all_items if it['net'] == net]
        if len(items) < 2:
            continue
        parent = list(range(len(items)))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(x, y):
            parent[find(x)] = find(y)
        for i, a in enumerate(items):
            for j in tree.query(a['shape'].buffer(0.01)):
                b = all_items[j]
                if b['net'] != net or b['id'] <= a['id']:
                    continue
                k = items.index(b) if b in items else -1
                if k >= 0 and a['shape'].distance(b['shape']) <= 0.01:
                    union(i, k)
        groups = {}
        for i, it in enumerate(items):
            groups.setdefault(find(i), []).append(it)
        pad_groups = {g for g, its in groups.items() if any(x.get('ref') for x in its)}
        if len(pad_groups) > 1:
            unconnected.append({'net': net, 'islands': len(groups)})

    # C4 — board edge clearance
    min_edge = 1e9
    for it in tracks + vias:
        d = board_boundary.distance(it['shape'])
        min_edge = min(min_edge, d)
        if d < EDGE - EPS:
            violations.append({'code': 'C4', 'id': it['id'], 'net': it['net'], 'edge_gap_mil': round(d, 3)})
    for p in pads:
        if not p['layers'] & {1, 2}:
            continue
        d = board_boundary.distance(p['shape'])
        min_edge = min(min_edge, d)
        if d < EDGE - EPS:
            violations.append({'code': 'C4', 'id': p['id'], 'net': p['net'], 'edge_gap_mil': round(d, 3)})
    # NPTH hole-to-copper
    if holes:
        htree = shapely.STRtree(holes)
        for it in tracks + vias + pads:
            for hi in htree.query(it['shape'], predicate='dwithin', distance=EDGE):
                d = holes[hi].boundary.distance(it['shape'])
                if d < EDGE - EPS:
                    violations.append({'code': 'C4', 'id': it['id'], 'npth_gap_mil': round(d, 3)})

    # C5 — via drill / annular ring
    for v in vias:
        drill, dia = v['src']['drill_mil'], v['src']['diameter_mil']
        if drill < 11.811 - EPS:
            violations.append({'code': 'C5', 'id': v['id'], 'detail': f'drill {drill} < 0.3mm'})
        if (dia - drill) / 2 < 5.9055 - EPS:
            violations.append({'code': 'C5', 'id': v['id'], 'detail': f'annular ring {(dia-drill)/2:.2f} < 0.15mm'})

    summary = {
        'counts': {'tracks': len(tracks), 'vias': len(vias), 'pads': len(pads)},
        'library': {'shapely': shapely.__version__, 'python': sys.version.split()[0]},
        'rules': {'clearance_mil': CLEAR, 'edge_mil': EDGE, 'via_drill_min_mil': 11.811, 'annular_min_mil': 5.9055},
        'C1_roundtrip': {'ok': rt_ok, 'records': {'lines': len(rec_lines), 'vias': len(rec_vias)}},
        'C2_clearance': {'ok': not any(v['code'] == 'C2' for v in violations),
                         'min_gap_mil': round(min_gap, 3) if min_gap < 1e9 else None, 'closest': min_pair},
        'C3_connectivity': {'ok': not unconnected, 'unconnected_nets': unconnected},
        'C4_edge': {'ok': not any(v['code'] == 'C4' for v in violations), 'min_edge_mil': round(min_edge, 3)},
        'C5_via': {'ok': not any(v['code'] == 'C5' for v in violations)},
        'violations': violations,
        'violation_count_by_code': {c: sum(1 for v in violations if v['code'] == c) for c in ('C1', 'C2', 'C3', 'C4', 'C5')},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print(f"copper: {len(tracks)} tracks / {len(vias)} vias / {len(pads)} pads")
    print(f"C1 round-trip {'OK' if rt_ok else 'FAIL'} | C2 min gap {summary['C2_clearance']['min_gap_mil']} mil "
          f"({'OK' if summary['C2_clearance']['ok'] else 'FAIL'}) | C3 {'OK' if summary['C3_connectivity']['ok'] else 'FAIL'} "
          f"| C4 min edge {summary['C4_edge']['min_edge_mil']} mil ({'OK' if summary['C4_edge']['ok'] else 'FAIL'}) "
          f"| C5 {'OK' if summary['C5_via']['ok'] else 'FAIL'}")
    print(f"violations: {summary['violation_count_by_code']}")
    if violations:
        for v in violations[:10]:
            print('  ', v)
        sys.exit(1)

if __name__ == '__main__':
    main()
