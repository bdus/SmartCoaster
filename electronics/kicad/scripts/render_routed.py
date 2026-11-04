#!/usr/bin/env python3
"""Render the *routed* 2-layer board to build/pcb_2l.png for visual QA.

Unlike render_pcb.py (placement only, reads smartcoaster.kicad_pcb) this one
draws the copper: B.Cu segments blue, F.Cu segments red, vias, pads and the
Edge.Cuts outline.  Pure s-expression + matplotlib, so it runs without pcbnew.
"""

import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MCircle
from matplotlib.patches import Polygon as MPoly

import ksexpr

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'smartcoaster', 'smartcoaster_2l.kicad_pcb')
OUT = os.path.join(HERE, '..', 'build', 'pcb_2l.png')

F_CU = '#c0392b'
B_CU = '#2c5fb3'
PTH = '#b8860b'


def rotp(px, py, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (c * px + s * py, -s * px + c * py)


def num(node, tag, idx=1, default=0.0):
    v = ksexpr.first(node, tag)
    if not v or len(v) <= idx:
        return default
    return float(v[idx])


def main():
    root = ksexpr.parse(open(PCB, encoding='utf-8').read())
    fig, ax = plt.subplots(figsize=(11, 11), dpi=160)
    ax.set_facecolor('#111111')

    # --- Edge.Cuts outline -------------------------------------------------
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
                    color='#cccccc', lw=1.1, zorder=2)

    # --- copper segments (B.Cu first, then F.Cu) ---------------------------
    segs = ksexpr.find_all(root, 'segment')
    for layer, col, z in (('B.Cu', B_CU, 3), ('F.Cu', F_CU, 5)):
        for s in segs:
            l = ksexpr.first(s, 'layer')
            if not l or l[1] != layer:
                continue
            x1, y1 = num(s, 'start'), -num(s, 'start', 2)
            x2, y2 = num(s, 'end'), -num(s, 'end', 2)
            w = num(s, 'width', default=0.25)
            ax.plot([x1, x2], [y1, y2], color=col, lw=max(0.4, w * 7),
                    solid_capstyle='round', alpha=0.85, zorder=z)

    # --- vias --------------------------------------------------------------
    for v in ksexpr.find_all(root, 'via'):
        at = ksexpr.first(v, 'at')
        if not at:
            continue
        x, y = float(at[1]), -float(at[2])
        size = num(v, 'size', default=0.6)
        ax.add_patch(MCircle((x, y), size / 2, facecolor='#d4b106',
                             edgecolor='#5a4a00', lw=0.3, zorder=7))

    # --- pads + refs -------------------------------------------------------
    for fp in ksexpr.find_all(root, 'footprint'):
        ref = ''
        for c in ksexpr.find_all(fp, 'property'):
            if c[1] == 'Reference':
                ref = str(c[2])
        at = ksexpr.first(fp, 'at')
        if not at:
            continue
        fx, fy = float(at[1]), float(at[2])
        frot = float(at[3]) if len(at) > 3 else 0.0
        for pad in ksexpr.find_all(fp, 'pad'):
            pat = ksexpr.first(pad, 'at')
            sz = ksexpr.first(pad, 'size')
            if not pat or not sz:
                continue
            px, py = float(pat[1]), float(pat[2])
            w, h = float(sz[1]), float(sz[2])
            pa = float(pat[3]) if len(pat) > 3 else 0.0
            bx, by = rotp(px, py, frot)
            bx += fx
            by += fy
            layers = ksexpr.first(pad, 'layers')
            lays = [str(x) for x in layers[1:]] if layers else []
            col = PTH if '*.Cu' in lays else (B_CU if 'B.Cu' in lays else F_CU)
            corners = []
            for cx, cy in ((-w / 2, -h / 2), (w / 2, -h / 2),
                           (w / 2, h / 2), (-w / 2, h / 2)):
                sx, sy = rotp(cx, cy, pa)
                corners.append((bx + sx, -(by + sy)))
            ax.add_patch(MPoly(corners, closed=True, facecolor=col,
                               edgecolor='none', alpha=0.95, zorder=6))
        ax.text(fx, -fy, ref, fontsize=4.2, ha='center', va='center',
                color='#9fe6a0', zorder=9)

    ax.set_aspect('equal')
    ax.set_xlim(-50, 50)
    ax.set_ylim(-50, 50)
    ax.set_title('SmartCoaster 2-layer routed board — F.Cu (red) / B.Cu (blue) / vias (yellow)',
                 color='#eeeeee', fontsize=11)
    ax.tick_params(colors='#888888', labelsize=8)
    for sp in ax.spines.values():
        sp.set_color('#555555')
    ax.grid(True, lw=0.15, alpha=0.25, color='#666666')
    fig.tight_layout()
    fig.savefig(OUT, facecolor='#111111')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
