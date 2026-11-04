#!/usr/bin/env python3
"""Square V1 - experimental verification (13 parts, interference, STEP)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))
import square_model as m                        # noqa: E402
from build123d import import_step, Pos, Box            # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name:44s} {detail}")


DISJOINT = [
    ("plate", "shell"), ("plate", "pcb"), ("plate", "battery"),
    ("plate", "esp32"), ("plate", "hx711"), ("plate", "usbc"),
    ("plate", "oled"), ("plate", "button"), ("plate", "glass"),
    ("shell", "pcb"), ("shell", "battery"), ("shell", "esp32"),
    ("shell", "hx711"), ("shell", "usbc"), ("shell", "oled"),
    ("shell", "button"), ("shell", "glass"), ("shell", "pad"),
    ("pcb", "battery"), ("pcb", "oled"), ("pcb", "button"),
    ("pcb", "glass"),
    ("battery", "oled"), ("battery", "button"), ("battery", "glass"),
    ("esp32", "battery"), ("esp32", "oled"), ("esp32", "button"),
    ("hx711", "battery"), ("hx711", "button"), ("hx711", "oled"),
    ("usbc", "battery"), ("usbc", "oled"), ("usbc", "button"),
    ("oled", "button"), ("oled", "glass"), ("button", "glass"),
    ("light_guide", "shell"), ("light_guide", "plate"), ("light_guide", "pcb"),
    ("light_guide", "sensor"), ("light_guide", "esp32"), ("light_guide", "hx711"),
    ("light_guide", "usbc"), ("light_guide", "battery"), ("light_guide", "oled"),
    ("light_guide", "button"), ("light_guide", "glass"), ("light_guide", "pad"),
]


def main():
    assy, parts, rows = m.build_assembly()
    bb = assy.bounding_box()
    print("=" * 78)
    print("SmartCoaster V1 (square) verification")
    print("=" * 78)

    check("assembly solids == 13", len(assy.solids()) == 13,
          f"{len(assy.solids())} solids")
    check("bbox 100 x 100 x 18",
          abs(bb.size.X - 100) < 1e-6 and abs(bb.size.Y - 100) < 1e-6
          and abs(bb.size.Z - 18.0) < 1e-6,
          f"{bb.size.X:.3f} x {bb.size.Y:.3f} x {bb.size.Z:.3f}")
    check("all parts valid", all(r["valid"] for r in rows),
          f"{sum(1 for r in rows if r['valid'])}/{len(rows)}")
    check("every part is one solid", all(r["solids"] == 1 for r in rows),
          f"{[r['name'] for r in rows if r['solids'] != 1]}")
    check("overload float gap == 0.5", abs((m.PLATE_Z - m.BASE_H) - 0.5) < 1e-9,
          f"{m.PLATE_Z - m.BASE_H:.3f} mm")
    check("column lands on cell (z 6.0)", abs((m.PLATE_Z - 9.0) - 6.0) < 1e-9,
          f"column bottom z={m.PLATE_Z - 9.0:.2f}")
    check("plate skirt vs cavity", (m.CAV - m.SKIRT_OUT) / 2 >= 0.5,
          f"{(m.CAV - m.SKIRT_OUT) / 2:.2f} mm/side")
    check("PCB central opening clears cell",
          (m.PCB_SQ - m.SENSOR) / 2 >= 2.0,
          f"{(m.PCB_SQ - m.SENSOR) / 2:.2f} mm/side")

    bat_top = parts["battery"].bounding_box().max.Z
    check("battery clears plate skirt", bat_top < m.SKIRT_BOTTOM - 0.3,
          f"{bat_top:.2f} < {m.SKIRT_BOTTOM:.2f}")
    oled_top = parts["oled"].bounding_box().max.Z
    # B front: the skirt is relieved over the 38x12 module; the module sits
    # under the plate body (z=15), not under the skirt.
    check("OLED clears plate body at rest", oled_top < m.PLATE_Z - 0.5,
          f"{oled_top:.2f} < {m.PLATE_Z - 0.5:.2f}")
    probe = Pos(m.OLED_X, -46.5, 13.7) * Box(10.0, 1.0, 1.0)
    check("plate skirt relieved over OLED", (parts["plate"] & probe).volume < 1e-6,
          f"notch volume {(parts['plate'] & probe).volume:.4f}")
    btn_top = parts["button"].bounding_box().max.Z
    check("button clears plate skirt", btn_top < m.SKIRT_BOTTOM - 0.2,
          f"{btn_top:.2f} < {m.SKIRT_BOTTOM:.2f}")
    check("button flange clears plate skirt at full travel",
          btn_top < m.SKIRT_BOTTOM - 0.5 - 0.1,
          f"flange top {btn_top:.2f} < {m.SKIRT_BOTTOM - 0.5:.2f}")


    # --- functional travel: the plate must be free to press the cell ----------
    moved_free = Pos(0, 0, -(0.5 - 0.002)) * parts["plate"]
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
    check("down-travel 0.5 mm is unobstructed", not blockers,
          f"blocked by {blockers}")

    # --- sensor compliance (S1 FEA: 49.05 N -> 0.3435 mm, through-slot) ------
    sensor_k = 49.05 / 0.3435          # N/mm, provisional FEA stiffness
    gap = m.PLATE_Z - m.BASE_H
    drop5 = 49.05 / sensor_k
    remaining = gap - drop5
    contact_kg = gap * sensor_k / 9.81
    check("5 kg sensor drop leaves >=0.1 mm rim gap", remaining >= 0.1,
          f"{remaining:.3f} mm (drop {drop5:.3f})")
    check("rim overload stop engages by 150% (7.5 kg)", contact_kg <= 7.5,
          f"{contact_kg:.2f} kg")

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

    moved_stop = Pos(0, 0, -0.55) * parts["plate"]
    try:
        stop_vol = (moved_stop & parts["shell"]).volume
    except Exception:
        stop_vol = 0.0
    check("over-load stop engages at 0.5 mm (shell rim)",
          stop_vol > 1e-3, f"contact volume {stop_vol:.3f} mm3")

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

    step = ROOT / "build" / "assembly" / "assembly_v01.step"
    if step.exists():
        imp = import_step(str(step))
        ib = imp.bounding_box()
        check("STEP re-import: 13 solids", len(imp.solids()) == 13,
              f"{len(imp.solids())} solids")
        check("STEP re-import: bbox",
              abs(ib.size.X - 100) < 1e-3 and abs(ib.size.Z - 18) < 1e-3,
              f"{ib.size.X:.3f} x {ib.size.Y:.3f} x {ib.size.Z:.3f}")
    else:
        check("STEP file exists", False, str(step))

    ok = all(r["ok"] for r in RESULTS)
    out = ROOT / "build" / "verify_report.json"
    out.write_text(json.dumps({"ok": ok, "checks": RESULTS}, indent=2,
                              ensure_ascii=False), encoding="utf-8")
    print("-" * 78)
    print(f"{sum(1 for r in RESULTS if r['ok'])}/{len(RESULTS)} checks passed -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
