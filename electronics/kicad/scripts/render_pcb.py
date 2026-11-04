#!/usr/bin/env python3
"""Quick matplotlib render of the PCB draft (outline, pads, refs) for visual QA."""

import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import ksexpr

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'smartcoaster', 'smartcoaster.kicad_pcb')


def rotp(px, py, deg):
    """R(-deg) as used by KiCad footprints (pad angle is stored absolute)."""
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (c * px + s * py, -s * px + c * py)


def main():
    root = ksexpr.parse(open(PCB, encoding='utf-8').read())
    fig, ax = plt.subplots(figsize=(12, 12), dpi=140)

    for g in list(ksexpr.find_all(root, 'gr_line')) + list(ksexpr.find_all(root, 'gr_arc')):
        lay = ksexpr.first(g, 'layer')
        if not lay or lay[1] != 'Edge.Cuts':
            continue
        pts = []
        for tag in ('start', 'mid', 'end'):
            p = ksexpr.first(g, tag)
            if p:
                pts.append((float(p[1]), -float(p[2])))
        for i in range(len(pts) - 1):
            ax.plot([pts[i][0], pts[i + 1][0]], [pts[i][1], pts[i + 1][1]],
                    'k-', lw=1.0)

    for fp in ksexpr.find_all(root, 'footprint'):
        ref = ''
        for c in ksexpr.find_all(fp, 'property'):
            if c[1] == 'Reference':
                ref = str(c[2])
                pat = ksexpr.first(c, 'at')
        at = ksexpr.first(fp, 'at')
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        ax.text(x, -y, ref, fontsize=4.5, ha='center', va='center',
                color='#0a7a2a', zorder=5)
        for pad in ksexpr.find_all(fp, 'pad'):
            num = pad[1]
            pat = ksexpr.first(pad, 'at')
            sz = ksexpr.first(pad, 'size')
            if not sz:
                continue
            px, py = float(pat[1]), float(pat[2])
            w, h = float(sz[1]), float(sz[2])
            pa = float(pat[3]) if len(pat) > 3 else 0.0
            # pad position is footprint-local (rotated by the footprint),
            # pad orientation is already absolute in the file
            bx_, by_ = rotp(px, py, rot)
            bx_ += x
            by_ += y
            corners = []
            for cx, cy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
                sx, sy = rotp(cx, cy, pa)
                corners.append((bx_ + sx, -(by_ + sy)))
            net = ksexpr.first(pad, 'net')
            col = '#d05050' if net else '#bbbbbb'
            ax.add_patch(MPoly(corners, closed=True, facecolor=col,
                               edgecolor='#801010', lw=0.15, alpha=0.9))
    ax.set_aspect('equal')
    ax.set_xlim(-52, 52)
    ax.set_ylim(-52, 52)
    ax.set_title('SmartCoaster 2-layer — placement / pads (copper: see build/pcb_2l.png)')
    ax.grid(True, lw=0.15, alpha=0.3)
    out = os.path.join(HERE, '..', 'build', 'pcb_layout.png')
    fig.savefig(out, bbox_inches='tight')
    print('wrote', out)


if __name__ == '__main__':
    main()
