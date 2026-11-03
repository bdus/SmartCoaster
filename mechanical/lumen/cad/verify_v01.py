#!/usr/bin/env python3
"""
LUMEN v1.0 - experimental verification.

    .venv/bin/python cad/verify_v01.py

Checks
  1. assembly metrics (solids, bbox, validity)
  2. design-intent clearances from the parameter table
  3. pairwise interference for parts that must stay apart
  4. STEP round-trip (re-import the exported file)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))

import lumen_model as m                       # noqa: E402
from build123d import import_step, Compound, Pos    # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name:42s} {detail}")


# pairs that must not share solid material (contacts handled separately)
DISJOINT = [
    ("plate", "shell"), ("plate", "guide"), ("plate", "ledflex"),
    ("plate", "pcb"), ("plate", "battery"), ("plate", "esp32"),
    ("plate", "hx711"), ("plate", "usbc"), ("plate", "oled"),
    ("plate", "glass"),
    ("shell", "guide"), ("shell", "ledflex"), ("shell", "pcb"),
    ("shell", "battery"), ("shell", "esp32"), ("shell", "hx711"),
    ("shell", "usbc"), ("shell", "oled"), ("shell", "glass"),
    ("shell", "pad"),
    ("guide", "pcb"), ("guide", "battery"), ("guide", "esp32"),
    ("guide", "hx711"), ("guide", "usbc"), ("guide", "oled"),
    ("ledflex", "pcb"), ("ledflex", "battery"), ("ledflex", "oled"),
    ("pcb", "battery"), ("pcb", "oled"), ("pcb", "glass"),
    ("battery", "oled"), ("battery", "glass"),
    ("oled", "glass"),
    ("esp32", "battery"), ("hx711", "battery"), ("usbc", "battery"),
]


def max_radius(shape):
    return max((v.X ** 2 + v.Y ** 2) ** 0.5 for v in shape.vertices())


def main():
    assy, parts, rows = m.build_assembly()
    bb = assy.bounding_box()

    print("=" * 78)
    print("LUMEN v1.0 verification")
    print("=" * 78)

    # 1. assembly level -----------------------------------------------------
    check("assembly solids == 13", len(assy.solids()) == 13,
          f"{len(assy.solids())} solids")
    check("assembly bbox 110 x 110 x 17",
          abs(bb.size.X - 110) < 1e-6 and abs(bb.size.Y - 110) < 1e-6
          and abs(bb.size.Z - 17.0) < 1e-6,
          f"{bb.size.X:.3f} x {bb.size.Y:.3f} x {bb.size.Z:.3f}")
    check("all parts valid", all(r["valid"] for r in rows),
          f"{sum(1 for r in rows if r['valid'])}/{len(rows)}")
    check("every part is one solid", all(r["solids"] == 1 for r in rows),
          f"{[r['name'] for r in rows if r['solids'] != 1]}")
    check("estimated mass < 200 g",
          sum(r["mass_g"] for r in rows) < 200,
          f"{sum(r['mass_g'] for r in rows):.1f} g")

    # 2. design-intent clearances ------------------------------------------
    gap = m.PLATE_Z - m.SHELL_H
    check("overload float gap == 0.6", abs(gap - 0.6) < 1e-9, f"{gap:.3f} mm")
    check("column lands on cell (z 6.0)",
          abs(m.PLATE_Z - 8.0 - 6.0) < 1e-9,
          f"column bottom z={m.PLATE_Z - 8.0:.2f}")
    check("plate skirt vs light guide bore",
          abs((m.GUIDE_R_IN - m.SKIRT_R_OUT) - 0.3) < 1e-9,
          f"{m.GUIDE_R_IN - m.SKIRT_R_OUT:.2f} mm radial")
    check("halo slot radial width",
          abs((m.R_IN - m.R_PLATE) - 0.6) < 1e-9,
          f"{m.R_IN - m.R_PLATE:.2f} mm")
    check("PCB central opening clears cell by 2 mm/side",
          abs((m.PCB_SQ - m.SENSOR_X) / 2 - 2.0) < 1e-9,
          f"{(m.PCB_SQ - m.SENSOR_X) / 2:.2f} mm")

    bat_r = max_radius(parts["battery"])
    check("battery outside plate-skirt sweep",
          bat_r < m.SKIRT_R_IN - 0.3,
          f"r={bat_r:.2f} < {m.SKIRT_R_IN:.2f}")
    check("battery top clears plate underside",
          parts["battery"].bounding_box().max.Z < m.PLATE_Z - 1.0,
          f"top z={parts['battery'].bounding_box().max.Z:.2f}")

    oled_bb = parts["oled"].bounding_box()
    check("OLED clears floor and plate",
          oled_bb.min.Z > m.FLOOR + 0.2 and oled_bb.max.Z < m.PLATE_Z - 0.2,
          f"z {oled_bb.min.Z:.2f}..{oled_bb.max.Z:.2f}")
    oled_top_r = max(
        ((v.X ** 2 + v.Y ** 2) ** 0.5 for v in parts["oled"].vertices()
         if v.Z > m.GUIDE_Z), default=0.0)
    check("OLED top stays inside light-guide bore",
          oled_top_r < m.GUIDE_R_IN - 0.2,
          f"r={oled_top_r:.2f} < {m.GUIDE_R_IN:.2f}")

    sens_bb = parts["sensor"].bounding_box()
    check("cell sits on 4 corner bosses (z=5.0)",
          abs(sens_bb.min.Z - m.SENSOR_Z) < 1e-9,
          f"sensor z {sens_bb.min.Z:.2f}..{sens_bb.max.Z:.2f}")


    # --- functional travel: the plate must be free to press the cell ----------
    moved_free = Pos(0, 0, -(0.6 - 0.002)) * parts["plate"]
    blockers = []
    for name, part in parts.items():
        if name in ("plate", "sensor"):
            continue
        b1, b2 = moved_free.bounding_box(), part.bounding_box()
        if (b1.min.X > b2.max.X or b2.min.X > b1.max.X or
                b1.min.Y > b2.max.Y or b2.min.Y > b1.max.Y or
                b1.min.Z > b2.max.Z or b2.min.Z > b1.max.Z):
            continue
        try:
            vol = (moved_free & part).volume
        except Exception:
            vol = 0.0
        if vol > 1e-6:
            blockers.append((name, round(vol, 4)))
    check("down-travel 0.6 mm is unobstructed", not blockers,
          f"blocked by {blockers}")

    moved_touch = Pos(0, 0, -0.05) * parts["plate"]
    early = []
    for name, part in parts.items():
        if name in ("plate", "sensor"):
            continue
        try:
            vol = (moved_touch & part).volume
        except Exception:
            vol = 0.0
        if vol > 1e-6:
            early.append((name, round(vol, 4)))
    check("no part within 0.05 mm below plate at rest", not early,
          f"{early}")

    moved_stop = Pos(0, 0, -(0.6 + 0.05)) * parts["plate"]
    try:
        stop_vol = (moved_stop & parts["guide"]).volume
    except Exception:
        stop_vol = 0.0
    check("over-load stop engages at 0.6 mm (guide top / shell)",
          stop_vol > 1e-3, f"contact volume {stop_vol:.3f} mm3")

    # 3. pairwise interference ---------------------------------------------
    bad = []
    for a, b in DISJOINT:
        pa, pb = parts[a], parts[b]
        ba, bb2 = pa.bounding_box(), pb.bounding_box()
        if (ba.min.X > bb2.max.X or bb2.min.X > ba.max.X or
                ba.min.Y > bb2.max.Y or bb2.min.Y > ba.max.Y or
                ba.min.Z > bb2.max.Z or bb2.min.Z > ba.max.Z):
            vol = 0.0
        else:
            try:
                inter = pa & pb
                vol = inter.volume if inter is not None else 0.0
            except Exception:
                vol = 0.0
        if vol > 1e-6:
            bad.append((a, b, round(vol, 4)))
    check("pairwise interference == 0", not bad, f"{len(DISJOINT)} pairs {bad}")

    # 4. STEP round-trip ----------------------------------------------------
    step_path = ROOT / "build" / "assembly" / "assembly_v01.step"
    if step_path.exists():
        imported = import_step(str(step_path))
        ib = imported.bounding_box()
        check("STEP re-import: 13 solids", len(imported.solids()) == 13,
              f"{len(imported.solids())} solids")
        check("STEP re-import: bbox",
              abs(ib.size.X - 110) < 1e-3 and abs(ib.size.Z - 17) < 1e-3,
              f"{ib.size.X:.3f} x {ib.size.Y:.3f} x {ib.size.Z:.3f}")
    else:
        check("STEP file exists", False, str(step_path))

    ok = all(r["ok"] for r in RESULTS)
    out = ROOT / "build" / "verify_report.json"
    out.write_text(json.dumps({"ok": ok, "checks": RESULTS}, indent=2,
                              ensure_ascii=False), encoding="utf-8")
    print("-" * 78)
    print(f"{sum(1 for r in RESULTS if r['ok'])}/{len(RESULTS)} checks passed "
          f"-> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
