#!/usr/bin/env python3
"""Geometric sanity check of the PCB draft: footprints must sit on the C-ring,
inside the board edge, and must not overlap each other's courtyards."""

import math
import os
import sys

from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union, polygonize
import ksexpr

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'smartcoaster', 'smartcoaster.kicad_pcb')

HALF = 46.6
R = 6.0
HOLEH = 19.0


def board_polygon():
    """C-ring in KiCad coords (y down)."""
    # build in mech coords (y up) then flip
    t = math.tan(math.radians(50.0))
    x_out = HALF / t
    x_in = HOLEH / t
    pts = []
    # front edge right part, then corners, anti-clockwise in mech space
    pts.append((x_out, -HALF))
    pts.append((HALF - R, -HALF))
    for i in range(9):
        a = math.radians(-90 + i * 90 / 8.0)
        pts.append((HALF - R + R * math.cos(a), -(HALF - R) + R * math.sin(a)))
    for i in range(9):
        a = math.radians(0 + i * 90 / 8.0)
        pts.append((HALF - R + R * math.cos(a), HALF - R + R * math.sin(a)))
    for i in range(9):
        a = math.radians(90 + i * 90 / 8.0)
        pts.append((-(HALF - R) + R * math.cos(a), HALF - R + R * math.sin(a)))
    for i in range(9):
        a = math.radians(180 + i * 90 / 8.0)
        pts.append((-(HALF - R) + R * math.cos(a), -(HALF - R) + R * math.sin(a)))
    pts.append((-x_out, -HALF))
    pts.append((-x_in, -HOLEH))
    pts.append((-HOLEH, -HOLEH))
    pts.append((-HOLEH, HOLEH))
    pts.append((HOLEH, HOLEH))
    pts.append((HOLEH, -HOLEH))
    pts.append((x_in, -HOLEH))
    poly = Polygon([(x, -y) for x, y in pts])
    assert poly.is_valid, 'board polygon invalid'
    return poly


def rot_pt(x, y, deg):
    a = math.radians(deg)
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))


def courtyard_poly(node):
    """Courtyard polygon from F.CrtYd primitives (polygonized); None if absent."""
    segs, rects = [], []
    for tag in ('fp_line', 'fp_arc'):
        for c in ksexpr.find_all(node, tag):
            layer = ksexpr.first(c, 'layer')
            if not layer or layer[1] != 'F.CrtYd':
                continue
            a = ksexpr.first(c, 'start')
            b = ksexpr.first(c, 'end')
            if a and b:
                segs.append(LineString([(float(a[1]), float(a[2])),
                                        (float(b[1]), float(b[2]))]))
    for c in ksexpr.find_all(node, 'fp_circle'):
        layer = ksexpr.first(c, 'layer')
        if not layer or layer[1] != 'F.CrtYd':
            continue
        ctr = ksexpr.first(c, 'center')
        end = ksexpr.first(c, 'end')
        cx, cy = float(ctr[1]), float(ctr[2])
        r = math.hypot(float(end[1]) - cx, float(end[2]) - cy)
        rects.append(Point(cx, cy).buffer(r))
    for c in ksexpr.find_all(node, 'fp_rect'):
        layer = ksexpr.first(c, 'layer')
        if not layer or layer[1] != 'F.CrtYd':
            continue
        a = ksexpr.first(c, 'start')
        b = ksexpr.first(c, 'end')
        rects.append(box(min(float(a[1]), float(b[1])), min(float(a[2]), float(b[2])),
                         max(float(a[1]), float(b[1])), max(float(a[2]), float(b[2]))))
    polys = list(polygonize(segs)) + rects
    if not polys:
        return None
    return unary_union(polys)


def pad_poly(node):
    boxes = []
    for c in ksexpr.find_all(node, 'pad'):
        at = ksexpr.first(c, 'at')
        size = ksexpr.first(c, 'size')
        px, py = float(at[1]), float(at[2])
        w, h = float(size[1]), float(size[2])
        boxes.append(box(px - w / 2, py - h / 2, px + w / 2, py + h / 2))
    return unary_union(boxes) if boxes else None


def main():
    board = board_polygon()
    root = ksexpr.parse(open(PCB, encoding='utf-8').read())
    items = []
    for fp in ksexpr.find_all(root, 'footprint'):
        ref = None
        for c in ksexpr.find_all(fp, 'property'):
            if c[1] == 'Reference':
                ref = c[2]
        at = ksexpr.first(fp, 'at')
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        crt = courtyard_poly(fp)
        pads = pad_poly(fp)
        if crt is None and pads is None:
            print('  no geometry', ref)
            continue
        geom = crt if crt is not None else pads
        from shapely import affinity
        geom = affinity.rotate(geom, -rot, origin=(0, 0))
        geom = affinity.translate(geom, x, y)
        if pads is not None:
            p2 = affinity.rotate(pads, -rot, origin=(0, 0))
            p2 = affinity.translate(p2, x, y)
        else:
            p2 = geom
        items.append((ref, geom, crt is not None, x, y, p2))

    bad = 0
    for ref, poly, has_crt, x, y, pads in items:
        if not board.buffer(-0.05).contains(pads):
            print('PADS OUTSIDE BOARD: %-4s at (%.1f, %.1f) outside %.1f mm2'
                  % (ref, x, y, pads.difference(board).area))
            bad += 1
        if not has_crt:
            print('  no courtyard:', ref)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            inter = a[1].intersection(b[1])
            if inter.area > 0.01:
                print('OVERLAP: %s <-> %s  %.2f mm2' % (a[0], b[0], inter.area))
                bad += 1
    print('checked %d footprints, %d problems' % (len(items), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
