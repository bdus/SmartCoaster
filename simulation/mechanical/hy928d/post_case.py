#!/usr/bin/env python3
"""Post-process one HY928D CalculiX case: metrics, JSON, top-view contours, VTP.

Usage:
  python post_case.py --msh mesh_h020_c3d10.msh --case case_h020_c3d10_5kg \
      --label "C3D10 h=0.20 mm" --out results_h020_c3d10.json --figs figs
"""
from __future__ import annotations
import argparse, json, math, os
import numpy as np

HOLE_CENTRES = np.array([[14., 14.], [-14., 14.], [14., -14.], [-14., -14.]])
CLAMP_R = 2.2
LOAD_R = 4.0
T = 1.0


def parse_msh(path):
    lines = open(path).read().splitlines()
    i = lines.index('$Nodes')
    n = int(lines[i + 1])
    ids = np.empty(n, dtype=np.int64)
    xyz = np.empty((n, 3), dtype=np.float64)
    for k, l in enumerate(lines[i + 2:i + 2 + n]):
        p = l.split()
        ids[k] = int(p[0]); xyz[k] = (float(p[1]), float(p[2]), float(p[3]))
    j = lines.index('$Elements')
    ne = int(lines[j + 1])
    tets, tris = [], []
    for l in lines[j + 2:j + 2 + ne]:
        p = l.split()
        typ, nt = int(p[1]), int(p[2])
        conn = [int(v) for v in p[3 + nt:]]
        if typ == 4:
            tets.append(conn[:4])
        elif typ == 11:
            tets.append(conn[:10])
        elif typ == 2:
            tris.append(conn[:3])
        elif typ == 9:
            tris.append(conn[:6])
    return ids, xyz, np.array(tets), np.array(tris), ('C3D10' if tets and len(tets[0]) == 10 else 'C3D4')


def parse_frd(path):
    lines = open(path).read().splitlines()
    disp, stress = {}, {}
    k = 0
    while k < len(lines):
        l = lines[k]
        if l.startswith(' -4  DISP') or l.startswith(' -4  STRESS'):
            is_disp = 'DISP' in l
            # FRD header declares 4 for DISP (D1,D2,D3,ALL) but only 3 values
            # are stored per node; ALL is the magnitude.
            nvals = 3 if is_disp else int(l.split()[2])
            data = {}
            k += 1
            while k < len(lines) and not lines[k].startswith(' -3'):
                s = lines[k]
                if s.startswith(' -1'):
                    nid = int(s[3:13])
                    vals = [float(s[13 + 12 * c:25 + 12 * c]) for c in range(nvals)]
                    if is_disp:
                        vals.append(math.sqrt(sum(v * v for v in vals)))
                    data[nid] = vals
                k += 1
            if is_disp:
                disp = data
            else:
                stress = data
        k += 1
    return disp, stress


def parse_dat(path):
    lines = open(path).read().splitlines()
    out = {}
    for key, label in [('U', 'displacements (vx,vy,vz)'), ('RF', 'forces (fx,fy,fz)')]:
        idx = [i for i, l in enumerate(lines) if label in l]
        if not idx:
            continue
        d = {}
        for l in lines[idx[-1] + 2:]:
            if not l.strip():
                break
            p = l.split()
            d[int(p[0])] = [float(x) for x in p[1:4]]
        out[key] = d
    return out


def vmises(s):
    sxx, syy, szz, sxy, syz, szx = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))


def region_stats(xyz, val, mask):
    if not np.any(mask):
        return None
    idx = np.where(mask)[0]
    k = idx[np.argmax(val[idx])]
    return {'max': float(val[k]), 'xyz': [float(v) for v in xyz[k]],
            'n_nodes': int(mask.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--msh', required=True)
    ap.add_argument('--case', required=True)
    ap.add_argument('--label', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--figs', default='figs')
    ap.add_argument('--load', type=float, default=49.05)
    ap.add_argument('--no-fig', action='store_true')
    ap.add_argument('--vtp', default='')
    a = ap.parse_args()
    os.makedirs(a.figs, exist_ok=True)

    ids, xyz, tets, tris, etype = parse_msh(a.msh)
    disp, stress = parse_frd(a.case + '.frd')
    dat = parse_dat(a.case + '.dat')
    meta = json.load(open(a.case + '.sets.json'))
    idx = {int(n): k for k, n in enumerate(ids)}
    nd = len(ids)
    id2row = np.full(int(ids.max()) + 1, -1, dtype=np.int64)
    id2row[ids] = np.arange(nd)

    # nodal arrays
    U = np.full((nd, 3), np.nan)
    Umag = np.full(nd, np.nan)
    for nid, v in disp.items():
        k = idx[nid]; U[k] = v[:3]; Umag[k] = v[3]
    VM = np.full(nd, np.nan)
    for nid, v in stress.items():
        if len(v) >= 6:
            VM[idx[nid]] = vmises(v[:6])
    good = np.isfinite(VM) & np.isfinite(Umag)
    print(f'parsed: {nd} nodes, disp {len(disp)}, stress {len(stress)}, good {good.sum()}')

    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    r = np.hypot(x, y)
    top = z > T - 1e-4
    bot = z < 1e-4
    hole_d = np.min(np.hypot(x[:, None] - HOLE_CENTRES[None, :, 0],
                             y[:, None] - HOLE_CENTRES[None, :, 1]), axis=1)
    clamped = hole_d <= CLAMP_R
    free = hole_d > CLAMP_R + 0.35

    # centre displacement: top nodes on the hole rim (r<=2.6)
    rim = top & (r <= 2.6)
    uz_rim = U[rim, 2]
    centre_node_k = np.argmin(np.where(top, np.hypot(x, y), 1e9))
    # nearest top node to (0,0,1)
    print(f'rim nodes {rim.sum()}')

    res = {
        'case': a.case, 'label': a.label,
        'mesh': {'file': a.msh, 'element_type': etype, 'nodes': int(nd),
                 'elements': int(len(tets)), 'boundary_triangles': int(len(tris)),
                 'hmax_mm': float(meta.get('hmax', 0) or 0)},
        'load': {'force_N': a.load, 'area_mm2': meta['load_area_mm2'],
                 'pressure_MPa': a.load / meta['load_area_mm2'],
                 'nodes': meta['load_nodes'], 'rule': meta['load_rule']},
        'clamp': {'rule': meta['clamp_rule'], 'nodes': meta['clamp_nodes'], 'radius_mm': CLAMP_R},
        'materials': {'name': '65Mn', 'E_MPa': 210000.0, 'nu': 0.3, 'rho_t_mm3': 7.85e-9,
                      'model': 'linear elastic, small strain'},
        'results': {},
        'regions': {},
        'reactions': {},
        'scaling': {},
    }

    r5 = res['results']
    r5['center_uz_mean_mm'] = float(uz_rim.mean())
    r5['center_uz_min_mm'] = float(uz_rim.min())
    r5['center_uz_max_mm'] = float(uz_rim.max())
    r5['center_node_xyz'] = [float(v) for v in xyz[centre_node_k]]
    r5['center_node_uz_mm'] = float(U[centre_node_k, 2])
    r5['max_abs_u_mm'] = float(np.nanmax(Umag))
    kmax = int(np.nanargmax(Umag))
    r5['max_abs_u_xyz'] = [float(v) for v in xyz[kmax]]
    r5['max_abs_uz_mm'] = float(np.nanmax(np.abs(U[:, 2])))

    kvm = int(np.nanargmax(np.where(good, VM, -1)))
    r5['max_vm_mpa'] = float(VM[kvm])
    r5['max_vm_xyz'] = [float(v) for v in xyz[kvm]]
    r5['max_vm_clamped'] = bool(clamped[kvm])
    # max outside clamp influence
    mask_free = good & free
    kf = int(np.nanargmax(np.where(mask_free, VM, -1)))
    r5['max_vm_free_mpa'] = float(VM[kf])
    r5['max_vm_free_xyz'] = [float(v) for v in xyz[kf]]
    r5['max_vm_top_mpa'] = float(np.nanmax(np.where(good & top, VM, -1)))
    r5['max_vm_bottom_mpa'] = float(np.nanmax(np.where(good & bot, VM, -1)))
    r5['uz_range_mm'] = [float(np.nanmin(U[:, 2])), float(np.nanmax(U[:, 2]))]
    # clamp-region stress (artefact of ENCASTRE edge)
    r5['max_vm_in_clamp_mpa'] = float(np.nanmax(np.where(good & clamped, VM, -1))) if np.any(clamped) else None
    # U-slot end corners are sharp in the reconstructed geometry: stress is singular.
    # report a max that ignores a 1 mm neighbourhood of those corners.
    slot_corners = np.array([[11.8, 9.6], [-11.8, 9.6], [14.3, 9.6], [-14.3, 9.6]])
    dsc = np.min(np.hypot(x[:, None] - slot_corners[None, :, 0],
                          y[:, None] - slot_corners[None, :, 1]), axis=1)
    no_corner = dsc > 1.0
    kk = int(np.nanargmax(np.where(good & free & no_corner, VM, -1)))
    r5['max_vm_free_no_slotcorner_mpa'] = float(VM[kk])
    r5['max_vm_free_no_slotcorner_xyz'] = [float(v) for v in xyz[kk]]
    r5['vm_p99_9_free_mpa'] = float(np.nanpercentile(VM[good & free], 99.9))
    r5['vm_p99_free_mpa'] = float(np.nanpercentile(VM[good & free], 99.0))

    # reactions
    rf = np.array(list(dat['RF'].values())) if 'RF' in dat else np.zeros((0, 3))
    res['reactions'] = {
        'sum_N': [float(v) for v in rf.sum(axis=0)] if len(rf) else None,
        'sum_fz_over_load': float(rf[:, 2].sum() / a.load) if len(rf) else None,
        'n_fixed_nodes_with_rf': int(len(rf)),
        'per_corner_fz_N': [],
    }
    rf_ids = np.array(list(dat['RF'].keys()), dtype=np.int64) if 'RF' in dat else np.array([], dtype=np.int64)
    if len(rf_ids):
        rx = xyz[[idx[int(n)] for n in rf_ids]]
        for cx, cy in HOLE_CENTRES:
            m = np.hypot(rx[:, 0] - cx, rx[:, 1] - cy) <= CLAMP_R + 1e-6
            res['reactions']['per_corner_fz_N'].append(float(rf[m, 2].sum()))

    # regions (max von Mises)
    regions = {
        'tongue_root_y8-12.5': (np.abs(x) <= 12.0) & (y >= 8.0) & (y <= 12.5),
        'tongue_root_mid_|x|<=10.5': (np.abs(x) <= 10.5) & (y >= 8.5) & (y <= 12.5),
        'tongue_section_y9.5-10.5': (y >= 9.5) & (y <= 10.5) & (np.abs(x) <= 11.8),
        'beam_ligament_|x|2.5-5.5': (np.abs(x) >= 2.5) & (np.abs(x) <= 5.5) & (np.abs(y) <= 2.0),
        'slot_end_pm6.6_pm6': np.min(np.hypot(x[:, None] - np.array([6.6, -6.6, 6.6, -6.6])[None, :],
                                             y[:, None] - np.array([6.0, 6.0, -6.0, -6.0])[None, :]), axis=1) <= 1.6,
        'arch_end_pm7.4_y3.5': np.min(np.hypot(x[:, None] - np.array([7.43, -7.43])[None, :],
                                              y[:, None] - np.array([3.47, 3.47])[None, :]), axis=1) <= 1.6,
        'loaded_boss_r4': r <= 4.0,
        'free_surface_top': top & free,
        'free_surface_bottom': bot & free,
    }
    for name, m in regions.items():
        res['regions'][name] = region_stats(xyz, np.where(good, VM, np.nan), m & good)

    # 1 kg if present (sibling file)
    one = a.case.replace('_5kg', '_1kg')
    if os.path.exists(one + '.dat'):
        d1 = parse_dat(one + '.dat')
        f1 = np.array(list(d1['U'].values()))
        # compare via FRD mean rim
        disp1, _ = parse_frd(one + '.frd')
        u1 = np.array([disp1[int(n)][2] for n in ids[rim] if int(n) in disp1])
        res['scaling'] = {
            'case_1kg': one, 'force_ratio': 1.0 / 5.0,
            'center_uz_5kg_mm': float(uz_rim.mean()),
            'center_uz_1kg_mm': float(u1.mean()) if len(u1) else None,
            'ratio_1kg_over_5kg': float(u1.mean() / uz_rim.mean()) if len(u1) else None,
            'expected_ratio': 0.2,
        }

    # ---------------- figures: top view ----------------
    if not a.no_fig:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.tri as mtri
        from matplotlib.patches import Circle, Rectangle

        tri = id2row[tris[:, :3]]
        keep = np.all(z[tri] > T - 1e-4, axis=1)
        tri_top = tri[keep]
        # compact remap for plotting speed
        vals_uz = -U[:, 2]  # downward positive
        vals_vm = VM

        def make_ax(ax, val, title, cmap, vmin, vmax, label, norm=None):
            tp = ax.tripcolor(x, y, tri_top, val, shading='gouraud', cmap=cmap,
                              vmin=vmin, vmax=vmax, rasterized=True)
            ax.set_aspect('equal'); ax.set_xlim(-17.5, 17.5); ax.set_ylim(-17.5, 17.5)
            ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)')
            ax.set_title(title, fontsize=10)
            for cx, cy in HOLE_CENTRES:
                ax.add_patch(Circle((cx, cy), CLAMP_R, fill=False, ls='--', lw=0.8, ec='k', alpha=0.7))
                ax.add_patch(Circle((cx, cy), 1.55, fill=False, lw=0.6, ec='k', alpha=0.7))
            ax.add_patch(Circle((0, 0), 2.5, fill=False, lw=0.7, ec='k'))
            ax.add_patch(Rectangle((-17, -17), 34, 34, fill=False, lw=0.8, ec='0.3'))
            cb = plt.colorbar(tp, ax=ax, shrink=0.82, pad=0.02)
            cb.set_label(label, fontsize=9)
            return tp

        fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.4))
        vmax_u = float(np.nanpercentile(vals_uz[top], 99.9))
        make_ax(axes[0], np.where(top, vals_uz, np.nan), f'(a) downward displacement -Uz, {a.label}',
                'viridis', 0, vmax_u, 'mm')
        vm_top = np.where(top & free, vals_vm, np.nan)
        vmax_vm = float(np.nanpercentile(VM[top & free], 99.7)) if np.any(top & free) else float(np.nanmax(VM))
        make_ax(axes[1], vm_top, f'(b) von Mises (top surface), {a.label}', 'inferno', 0, vmax_vm, 'MPa')
        for ax in axes:
            ax.plot(0, 0, 'k+', ms=8, mew=1.2)
        fig.suptitle(f'HY928D v2, 65Mn, 5 kg (49.05 N) - {a.label}', fontsize=12)
        fig.tight_layout()
        fig.savefig(os.path.join(a.figs, f'fig_{a.case}_top.png'), dpi=220)
        plt.close(fig)
        print('wrote top figure')

    # ---------------- VTP for 3D rendering (surface triangles) ----------------
    if a.vtp:
        tri = id2row[tris[:, :3]]
        used = np.unique(tri.ravel())
        remap = -np.ones(nd, dtype=np.int64)
        remap[used] = np.arange(len(used))
        with open(a.vtp, 'w') as f:
            f.write('<?xml version="1.0"?>\n<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">\n<PolyData>\n')
            f.write(f'<Piece NumberOfPoints="{len(used)}" NumberOfPolys="{len(tri)}">\n')
            f.write('<PointData Vectors="U" Scalars="vonMises">\n')
            f.write('<DataArray type="Float32" Name="U" NumberOfComponents="3" format="ascii">\n')
            for k in used:
                f.write(f'{U[k,0]:.6g} {U[k,1]:.6g} {U[k,2]:.6g}\n')
            f.write('</DataArray>\n<DataArray type="Float32" Name="vonMises" format="ascii">\n')
            for k in used:
                f.write(f'{VM[k]:.6g}\n')
            f.write('</DataArray>\n<DataArray type="Float32" Name="Uz" format="ascii">\n')
            for k in used:
                f.write(f'{U[k,2]:.6g}\n')
            f.write('</DataArray>\n</PointData>\n')
            f.write('<Points>\n<DataArray type="Float32" NumberOfComponents="3" format="ascii">\n')
            for k in used:
                f.write(f'{xyz[k,0]:.6g} {xyz[k,1]:.6g} {xyz[k,2]:.6g}\n')
            f.write('</DataArray>\n</Points>\n<Polys>\n')
            f.write('<DataArray type="Int64" Name="connectivity" format="ascii">\n')
            for t in tri:
                f.write(f'{remap[t[0]]} {remap[t[1]]} {remap[t[2]]}\n')
            f.write('</DataArray>\n<DataArray type="Int64" Name="offsets" format="ascii">\n')
            for i in range(1, len(tri) + 1):
                f.write(f'{3*i}\n')
            f.write('</DataArray>\n</Polys>\n</Piece>\n</PolyData>\n</VTKFile>\n')
        print('wrote', a.vtp)

    json.dump(res, open(a.out, 'w'), indent=2)
    print(json.dumps({k: res[k] for k in ['results', 'reactions']}, indent=2))


if __name__ == '__main__':
    main()
