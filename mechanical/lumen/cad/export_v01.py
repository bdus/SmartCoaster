#!/usr/bin/env python3
"""
LUMEN v1.0 - build and export every part + the full assembly.

    .venv/bin/python cad/export_v01.py

Writes:
    build/parts/<part>_v01.step|stl
    build/assembly/assembly_v01.step|stl
    build/assembly/meta.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))

import lumen_model as m                       # noqa: E402
from build123d import export_step, export_stl  # noqa: E402


def main():
    (ROOT / "build" / "parts").mkdir(parents=True, exist_ok=True)
    (ROOT / "build" / "assembly").mkdir(parents=True, exist_ok=True)

    assy, parts, rows = m.build_assembly()

    for name, part in parts.items():
        export_step(part, str(ROOT / "build" / "parts" / f"{name}_v01.step"))
        export_stl(part, str(ROOT / "build" / "parts" / f"{name}_v01.stl"))

    export_step(assy, str(ROOT / "build" / "assembly" / "assembly_v01.step"))
    export_stl(assy, str(ROOT / "build" / "assembly" / "assembly_v01.stl"))

    bb = assy.bounding_box()
    total_vol = sum(r["volume_mm3"] for r in rows)
    total_mass = sum(r["mass_g"] for r in rows)
    meta = {
        "product": "LUMEN smart hydration coaster",
        "version": "v1.0",
        "units": "mm",
        "total_height_mm": round(bb.size.Z, 3),
        "diameter_mm": round(bb.size.X, 3),
        "solids": len(assy.solids()),
        "parts": len(rows),
        "volume_mm3": round(total_vol, 2),
        "mass_estimate_g": round(total_mass, 2),
        "rows": rows,
    }
    (ROOT / "build" / "assembly" / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 78)
    print("LUMEN v1.0  -  smart hydration coaster")
    print("=" * 78)
    print(f"{'part':9s} {'solids':>6s} {'vol mm3':>10s} {'mass g':>7s}  bbox")
    for r in rows:
        print(f"{r['name']:9s} {r['solids']:6d} {r['volume_mm3']:10.1f} "
              f"{r['mass_g']:7.1f}  {r['bbox']}")
    print("-" * 78)
    print(f"parts {len(rows)}  solids {len(assy.solids())}  "
          f"bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
    print(f"volume {total_vol:.1f} mm3   estimated mass {total_mass:.1f} g")
    print(f"float gap {m.FLOAT_GAP} mm   plate underside z={m.PLATE_Z:.1f}   "
          f"rim z={m.SHELL_H:.1f}")
    print(f"STEP -> {ROOT / 'build' / 'assembly' / 'assembly_v01.step'}")


if __name__ == "__main__":
    main()
