#!/usr/bin/env python3
"""Mesh quality report for gmsh MSH2 tet meshes (C3D4 / C3D10)."""
import sys, json, numpy as np

def parse(path):
    L = open(path).read().splitlines()
    i = L.index('$Nodes'); n = int(L[i+1])
    nodes = np.zeros((n+1, 3))
    for l in L[i+2:i+2+n]:
        p = l.split(); nodes[int(p[0])] = [float(x) for x in p[1:4]]
    j = L.index('$Elements'); ne = int(L[j+1])
    tets = []
    for l in L[j+2:j+2+ne]:
        p = l.split(); typ = int(p[1]); nt = int(p[2])
        if typ in (4, 11):
            c = [int(v) for v in p[3+nt:]]
            if typ == 11:
                c[8], c[9] = c[9], c[8]   # gmsh -> CalculiX
            tets.append(c)
    return nodes, np.array(tets)

def dN(l1, l2, l3, l4):
    return np.array([
        [4*l1-1, 0, 0], [0, 4*l2-1, 0], [0, 0, 4*l3-1],
        [-(4*l4-1), -(4*l4-1), -(4*l4-1)],
        [4*l2, 4*l1, 0], [0, 4*l3, 4*l2], [4*l3, 0, 4*l1],
        [4*(l4-l1), -4*l1, -4*l1], [-4*l2, 4*(l4-l2), -4*l2],
        [-4*l3, -4*l3, 4*(l4-l3)]])

def main(path):
    nodes, tets = parse(path)
    X = nodes[tets[:, :4]]
    a = X[:, 1]-X[:, 0]; b = X[:, 2]-X[:, 0]; c = X[:, 3]-X[:, 0]
    V = np.abs(np.einsum('ij,ij->i', a, np.cross(b, c))) / 6.0
    ed = np.stack([np.linalg.norm(X[:, i]-X[:, j], axis=1)
                   for i, j in [(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]], axis=1)
    q = 6*np.sqrt(2)*V/np.max(ed, axis=1)**3
    out = {'file': path, 'element_type': 'C3D10' if tets.shape[1] == 10 else 'C3D4',
           'nodes': int(nodes.shape[0]-1), 'tets': int(len(tets)),
           'corner_quality_min': float(q.min()),
           'corner_quality_p01': float(np.percentile(q, 1)),
           'corner_quality_median': float(np.median(q)),
           'corner_quality_p99': float(np.percentile(q, 99)),
           'volume_min_mm3': float(V.min()), 'volume_max_mm3': float(V.max())}
    if tets.shape[1] == 10:
        g = 0.5854101966249685; s = 0.1381966011250105
        pts = [(g,s,s),(s,g,s),(s,s,g),(s,s,s)]
        ratios = np.empty(len(tets)); worst = []
        for k in range(len(tets)):
            Xk = nodes[tets[k]]
            ds = []
            for p in pts:
                J = dN(p[0], p[1], p[2], 1-sum(p)).T @ Xk
                ds.append(abs(np.linalg.det(J)))
            ratios[k] = min(ds) / (6*V[k])
        out.update({'ho_jac_min_ratio': float(ratios.min()),
                    'ho_jac_p01_ratio': float(np.percentile(ratios, 1)),
                    'ho_jac_median_ratio': float(np.median(ratios)),
                    'ho_bad_elements_ratio_lt_0.1': int((ratios < 0.1).sum())})
    print(json.dumps(out, indent=2))
    json.dump(out, open(path.replace('.msh', '_quality.json'), 'w'), indent=2)

if __name__ == '__main__':
    main(sys.argv[1])
