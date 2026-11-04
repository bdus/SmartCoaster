#!/usr/bin/env python3
"""Build a CalculiX .inp for the HY928D plate from a gmsh MSH2 mesh.

Assumptions (case A): four corner screw areas clamped, vertical load on the
top face annulus r <= 4.0 mm around the centre hole.

Writes <case>.inp and <case>.sets.json.  Units mm-N-MPa.
"""
from __future__ import annotations
import argparse, json, math
from collections import Counter

HOLE_CENTRES = [(14.0, 14.0), (-14.0, 14.0), (14.0, -14.0), (-14.0, -14.0)]
CLAMP_R = 2.2
TOP_Z = 1.0
LOAD_R = 4.0
TOL_Z = 1e-4


def read_msh(path):
    lines = open(path).read().splitlines()
    nodes = {}
    i = lines.index('$Nodes')
    n = int(lines[i + 1])
    for l in lines[i + 2:i + 2 + n]:
        p = l.split()
        nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
    j = lines.index('$Elements')
    ne = int(lines[j + 1])
    tets, tris = [], []
    types = Counter()
    for l in lines[j + 2:j + 2 + ne]:
        p = l.split()
        eid, typ = int(p[0]), int(p[1])
        ntags = int(p[2])
        conn = [int(v) for v in p[3 + ntags:]]
        types[typ] += 1
        if typ == 4:
            tets.append((eid, conn[:4]))
        elif typ == 11:
            tets.append((eid, conn[:10]))
        elif typ == 2:
            tris.append(conn[:3])
        elif typ == 9:
            tris.append(conn[:6])
    return nodes, tets, tris, types


def tri_area(coords):
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = coords
    ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
    vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
    cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def shape_tri6(r, s):
    l1, l2, l3 = 1.0 - r - s, r, s
    return [l1 * (2 * l1 - 1), l2 * (2 * l2 - 1), l3 * (2 * l3 - 1),
            4 * l1 * l2, 4 * l2 * l3, 4 * l3 * l1]


def load_distribution(nodes, tris, total_force, R=LOAD_R):
    """Consistent nodal forces on the top face inside radius R.

    Uses 3-point quadrature on quadratic boundary triangles (and the exact
    centroid rule for linear ones), so the sum of nodal forces equals
    total_force even if triangle centroids are used for selection.
    """
    sel = []
    for conn in tris:
        if len(conn) not in (3, 6):
            continue
        xyz = [nodes[n] for n in conn]
        if min(p[2] for p in xyz) < TOP_Z - TOL_Z:
            continue
        cx = sum(p[0] for p in xyz[:3]) / 3.0
        cy = sum(p[1] for p in xyz[:3]) / 3.0
        if math.hypot(cx, cy) > R:
            continue
        sel.append((conn, tri_area(xyz[:3])))
    A = sum(a for _, a in sel)
    p = total_force / A
    contrib = {}
    if not sel:
        raise RuntimeError('no load triangles found')
    quad = [(1/6, 1/6, 2/3), (2/3, 1/6, 1/6), (1/6, 2/3, 1/6)]
    for conn, area in sel:
        xyz = [nodes[n] for n in conn]
        if len(conn) == 3:
            for n in conn:
                contrib[n] = contrib.get(n, 0.0) + p * area / 3.0
        else:
            for r, s, w in quad:
                N = shape_tri6(r, s)
                for n, ni in zip(conn, N):
                    contrib[n] = contrib.get(n, 0.0) + p * area * w * ni
    s = sum(contrib.values())
    if abs(s - total_force) > 1e-6 * total_force:
        raise RuntimeError(f'load sum {s} != {total_force}')
    # tiny negative loads at quadratic corners are legitimate; keep them
    return contrib, A, len(sel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--msh', required=True)
    ap.add_argument('--case', required=True)
    ap.add_argument('--force', type=float, default=49.05)
    ap.add_argument('--material', default='65MN')
    a = ap.parse_args()

    nodes, tets, tris, types = read_msh(a.msh)
    ndim = 10 if any(len(c) == 10 for _, c in tets) else 4
    etype = 'C3D10' if ndim == 10 else 'C3D4'
    maxid = max(nodes)
    print(f'nodes={len(nodes)} tets={len(tets)} ({etype}) bnd_tris={len(tris)} types={dict(types)}')

    # clamp sets: everything within CLAMP_R of a corner hole centre, full thickness
    fix = []
    for nid, (x, y, z) in nodes.items():
        for cx, cy in HOLE_CENTRES:
            if (x - cx) ** 2 + (y - cy) ** 2 <= CLAMP_R ** 2:
                fix.append(nid)
                break
    fix.sort()
    if not fix:
        raise RuntimeError('empty clamp set')

    loads, A, ntri = load_distribution(nodes, tris, a.force)
    # order by node id for reproducibility
    loads = dict(sorted(loads.items()))

    with open(a.case + '.inp', 'w') as f:
        w = f.write
        w('*HEADING\n')
        w(f'HY928D v2 65Mn plate, {etype}, case A: 4 corner clamps + central top load {a.force:.2f} N\n')
        w('*NODE, NSET=NALL\n')
        for nid in sorted(nodes):
            x, y, z = nodes[nid]
            w(f'{nid}, {x:.9g}, {y:.9g}, {z:.9g}\n')
        w(f'*ELEMENT, TYPE={etype}, ELSET=EALL\n')
        for eid, conn in tets:
            if etype == 'C3D10':
                # gmsh tet10: 5=(1,2) 6=(2,3) 7=(3,1) 8=(1,4) 9=(3,4) 10=(2,4)
                # CalculiX/Abaqus C3D10: 9=(2,4) 10=(3,4) -> swap last two
                conn = list(conn)
                conn[8], conn[9] = conn[9], conn[8]
            w(f'{eid}, ' + ', '.join(str(n) for n in conn) + '\n')
        w('*NSET, NSET=FIX\n')
        for k in range(0, len(fix), 8):
            w(', '.join(str(n) for n in fix[k:k + 8]) + '\n')
        w('*NSET, NSET=LOAD\n')
        ln = list(loads)
        for k in range(0, len(ln), 8):
            w(', '.join(str(n) for n in ln[k:k + 8]) + '\n')
        w(f'*MATERIAL, NAME={a.material}\n')
        w('*ELASTIC\n210000., 0.3\n')
        w('*DENSITY\n7.85e-9\n')
        w(f'*SOLID SECTION, ELSET=EALL, MATERIAL={a.material}\n')
        w('*STEP, NAME=LOAD, INC=100\n')
        w('*STATIC\n')
        w('*BOUNDARY\nFIX, 1, 3, 0.\n')
        w('*CLOAD\n')
        for nid, fz in loads.items():
            w(f'{nid}, 3, {-fz:.9g}\n')
        w('*NODE PRINT, NSET=LOAD, FREQUENCY=1\nU\n')
        w('*NODE PRINT, NSET=FIX, FREQUENCY=1\nRF\n')
        w('*NODE FILE\nU\n')
        w('*EL FILE\nS\n')
        w('*END STEP\n')

    meta = {
        'mesh': a.msh, 'element_type': etype, 'nodes': len(nodes),
        'elements': len(tets), 'boundary_tris': len(tris),
        'clamp_nodes': len(fix), 'load_nodes': len(loads), 'load_tris': ntri,
        'load_area_mm2': A, 'force_N': a.force,
        'clamp_rule': 'all nodes within 2.2 mm of each corner-hole centre (14,14), full thickness',
        'load_rule': 'consistent nodal forces on top face z=1, r<=4.0 mm, sum exactly F',
        'sum_load_Fz': -sum(loads.values()),
        'max_node_id': maxid,
    }
    open(a.case + '.sets.json', 'w').write(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
