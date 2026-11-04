#!/usr/bin/env python3
"""Per-part binary glTF (GLB) for the Blender render pipeline.

STEP/STL remain the manufacturing sources; GLB is visualisation only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))
import square_model as m                      # noqa: E402
from build123d import export_gltf             # noqa: E402


def main():
    out = ROOT / "build" / "glb"
    out.mkdir(parents=True, exist_ok=True)
    _, parts, _ = m.build_assembly()
    for name, part in parts.items():
        ok = export_gltf(part, str(out / f"{name}.glb"), binary=True,
                         linear_deflection=0.05, angular_deflection=0.3)
        print(f"{name:8s} {ok}  {(out / f'{name}.glb').stat().st_size/1024:.1f} KiB")


if __name__ == "__main__":
    main()
