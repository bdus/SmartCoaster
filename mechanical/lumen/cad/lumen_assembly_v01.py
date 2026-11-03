#!/usr/bin/env python3
"""
LUMEN v1.0 - agentcad run entry point.

agentcad executes scripts under a non-__main__ module name and writes the
canonical STEP/GLB itself, so this file only exposes the named parts:

    agentcad run cad/lumen_assembly_v01.py --label lumen_v1

All geometry lives in cad/lumen_model.py; direct export (per-part STEP/STL,
assembly STEP/STL) is cad/export_v01.py.
"""

import importlib.util
import sys
from pathlib import Path


def _load_model():
    here = Path(__file__).resolve()
    for root in (here.parent, *here.parents, Path.cwd()):
        candidate = root / "cad" / "lumen_model.py"
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("lumen_model", candidate)
            module = importlib.util.module_from_spec(spec)
            sys.modules["lumen_model"] = module
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("cad/lumen_model.py not found above this script")


_model = _load_model()
_assy, _parts, _rows = _model.build_assembly()

for _name, _part in _parts.items():
    show_object(
        _part,
        id=_name,
        name=_name,
        options={"color": _model.COLORS[_name], "expect_solids": 1},
    )
