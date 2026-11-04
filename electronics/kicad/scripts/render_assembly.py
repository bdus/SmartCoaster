#!/usr/bin/env python3
"""Assembly drawings (top/bottom) for the routed 2-layer board.

Outputs `build/assembly/{top,bottom}.{pdf,png,svg}` at 1:1 scale (PDF is
printable for hand assembly).  Unlike the old 4-layer-era drawings these are
generated from `smartcoaster_2l.kicad_pcb`, so they contain exactly the 43
fitted parts (no LED, no test points).

Run (KiCad python bindings + matplotlib are needed, see build.sh env):
    LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu \
    PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages \
    /data/Documents/tools/sim-venv/bin/python render_assembly.py
"""

import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MCircle
from matplotlib.patches import Polygon as MPoly
from matplotlib.patches import Rectangle as MRect
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, '..', 'smartcoaster', 'smartcoaster_2l.kicad_pcb')
OUT = os.path.join(HERE, '..', 'build', 'assembly')
CTX = pcbnew.GetBoard()  # noqa: F841  (kept for API compatibility on some builds)


def mm(v):
    return pcbnew.ToMM(v)


def _arc_points(shape, n=24):
    """Sample a 3-point arc (start / mid / end) into a polyline."""
    p0, p1, p2 = shape.GetStart(), shape.GetArcMid(), shape.GetEnd()
    a = (mm(p0.x), mm(p0.y))
    b = (mm(p1.x), mm(p1.y))
    c = (mm(p2.x), mm(p2.y))
    # circle through 3 points
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return [a, c]
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    a0 = math.atan2(ay - uy, ax - ux)
    a1 = math.atan2(by - uy, bx - ux)
    a2 = math.atan2(cy - uy, cx - ux)
    # choose the sweep that passes through the mid angle
    def norm(t):
        return t % (2 * math.pi)
    sweep = norm(a2 - a0)
    mid_sw = norm(a1 - a0)
    if mid_sw > sweep:           # arc goes the other way
        sweep -= 2 * math.pi
    return [(ux + r * math.cos(a0 + sweep * i / n),
             uy + r * math.sin(a0 + sweep * i / n)) for i in range(n + 1)]


def draw_edges(ax, board):
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        shp = d.GetShape()
        if shp == pcbnew.SHAPE_T_SEGMENT:
            p, q = d.GetStart(), d.GetEnd()
            ax.plot([mm(p.x), mm(q.x)], [mm(p.y), mm(q.y)], color='#333333', lw=0.8)
        elif shp == pcbnew.SHAPE_T_ARC:
            pts = _arc_points(d)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color='#333333', lw=0.8)
        elif shp == pcbnew.SHAPE_T_CIRCLE:
            c = d.GetCenter()
            ax.add_patch(MCircle((mm(c.x), mm(c.y)), mm(d.GetRadius()),
                                 fill=False, ec='#333333', lw=0.8))
        elif shp == pcbnew.SHAPE_T_POLY:
            poly = d.GetPolyShape()
            for i in range(poly.OutlineCount()):
                chain = poly.Outline(i)
                xs = [mm(chain.CPoint(j).x) for j in range(chain.PointCount())]
                ys = [mm(chain.CPoint(j).y) for j in range(chain.PointCount())]
                ax.plot(xs, ys, color='#333333', lw=0.8)


def draw_pads(ax, board, side):
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            on_f = pad.IsOnLayer(pcbnew.F_Cu)
            on_b = pad.IsOnLayer(pcbnew.B_Cu)
            if side == 'top' and not on_f:
                continue
            if side == 'bottom' and not on_b:
                continue
            pos = pad.GetPosition()
            x, y = mm(pos.x), mm(pos.y)
            sx, sy = mm(pad.GetSize().x), mm(pad.GetSize().y)
            rot = pad.GetOrientationDegrees()
            color = '#b02a1e' if not (on_f and on_b) else '#8a4b00'
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                color = '#666666'
            corners = []
            for dx, dy in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2),
                           (sx / 2, sy / 2), (-sx / 2, sy / 2)):
                r = math.radians(rot)
                px = x + dx * math.cos(r) + dy * math.sin(r)
                py = y - dx * math.sin(r) + dy * math.cos(r)
                corners.append((px, py))
            ax.add_patch(MPoly(corners, closed=True, facecolor=color,
                               edgecolor='none', alpha=0.85, zorder=3))
            drill = pad.GetDrillSize()
            if drill.x > 0:
                ax.add_patch(MCircle((x, y), mm(drill.x) / 2,
                                     facecolor='white', edgecolor='none', zorder=4))


def draw_refs(ax, board, side):
    for fp in board.GetFootprints():
        if side == 'bottom' and not any(
                p.IsOnLayer(pcbnew.B_Cu) for p in fp.Pads()):
            continue
        ref = fp.Reference()
        pos = ref.GetPosition()
        ax.text(mm(pos.x), mm(pos.y), fp.GetReference(), fontsize=5.2,
                ha='center', va='center', color='#005f2a', zorder=5,
                fontweight='bold')


def render(side):
    board = pcbnew.LoadBoard(BOARD)
    bb = board.GetBoardEdgesBoundingBox()
    w, h = mm(bb.GetWidth()), mm(bb.GetHeight())
    fig_w, fig_h = (w + 12) / 25.4, (h + 22) / 25.4
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    draw_edges(ax, board)
    draw_pads(ax, board, side)
    if side == 'bottom':
        ax.invert_xaxis()
        draw_refs(ax, board, side)
    else:
        draw_refs(ax, board, side)
    ax.set_xlim(-w / 2 - 5, w / 2 + 5)
    # KiCad screen view: +Y is down, so the front C-notch (file y=+46.6)
    # appears at the bottom of the drawing, like it does in the PCB editor.
    ax.set_ylim(h / 2 + 14, -h / 2 - 5)
    ax.set_aspect('equal')
    ax.axis('off')
    n = len(board.GetFootprints())
    title = ('SmartCoaster 2-layer — TOP assembly' if side == 'top'
             else 'SmartCoaster 2-layer — BOTTOM assembly (mirrored, no parts)')
    ax.set_title(f'{title}\n{n} footprints (43 devices + 4 mounting holes) · '
                 '28 nets · no LED / no test points · 1:1 mm', fontsize=8)
    ax.text(-w / 2, -h / 2 - 4,
            'generated by render_assembly.py from smartcoaster_2l.kicad_pcb · '
            'pads red = copper · white = drill', fontsize=5, color='#555555')
    os.makedirs(OUT, exist_ok=True)
    for ext in ('pdf', 'png', 'svg'):
        fig.savefig(os.path.join(OUT, f'{side}.{ext}'), dpi=300,
                    bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {OUT}/{side}.pdf|png|svg')


if __name__ == '__main__':
    render('top')
    render('bottom')
