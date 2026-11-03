#!/usr/bin/env python3
"""Square V1 - agentcad run entry point."""
import importlib.util
import sys
from pathlib import Path


def _load_model():
    here = Path(__file__).resolve()
    for root in (here.parent, *here.parents, Path.cwd()):
        candidate = root / "cad" / "square_model.py"
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("square_model", candidate)
            module = importlib.util.module_from_spec(spec)
            sys.modules["square_model"] = module
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("cad/square_model.py not found above this script")


_model = _load_model()
_assy, _parts, _rows = _model.build_assembly()

for _name, _part in _parts.items():
    show_object(_part, id=_name, name=_name,
                options={"color": _model.COLORS[_name], "expect_solids": 1})
