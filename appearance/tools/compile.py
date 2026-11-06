#!/usr/bin/env python3
"""ONE command that compiles the whole SmartCoaster appearance/print pipeline.

The single source of truth for every input is
appearance/config/appearance_project.yaml.  This script:

  1. loads + validates the config (schema, required inputs, derived geometry,
     user-editable expectations);
  2. validates the environment (Node >= 22, Blender 4.5.3, build123d venv,
     Kromacut headless bridge) and the stage scripts;
  3. cross-checks the config against constants that are still hard-coded in the
     stage scripts (render/config.json fallbacks, scene_common.py VERSIONS,
     run_convert.sh art loop, print-layout constants, Lead-owned
     acceptance_check.py baselines) and refuses to build a mismatched model;
  4. runs the existing stage scripts in order (it never re-implements geometry);
  5. validates the artifacts each stage is expected to produce;
  6. writes per-stage status/time + validation evidence to
     appearance/build/COMPILE_REPORT.json / .md and streams all logs to
     appearance/build/compile.log; exits non-zero with an actionable message
     ("edit file X constant Y") on any failure.

Usage (repo root):
    bash appearance/compile.sh                      # full pipeline + acceptance
    bash appearance/compile.sh --dry-run            # validate only, write nothing
    bash appearance/compile.sh --list               # show stages/commands
    bash appearance/compile.sh --only shell         # one stage
    bash appearance/compile.sh --from render        # render -> print -> acceptance
    bash appearance/compile.sh --skip acceptance    # everything but acceptance
    bash appearance/compile.sh --no-acceptance      # same, explicit flag
    bash appearance/compile.sh --verbose            # list every validation check

Exit codes: 0 = PASS, 1 = a stage/artifact failed, 2 = config/validation failed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from array import array
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # keep --dry-run free of __pycache__ writes

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "appearance" / "config" / "appearance_project.yaml"

SCHEMA_PROJECT = "smartcoaster.appearance-project/v1"
SCHEMA_RESOLVED = "smartcoaster.appearance.resolved/v1"

# Pipeline stage order.  Stage commands are NOT re-implemented here: render is
# split into run_all.sh's 1/4-3/4 commands and print is its 4/4, so each stage
# gets its own status/time; validate_stage_constants() checks run_all.sh still
# contains exactly those sub-commands and fails if that split drifts.
STAGES = ["art", "convert", "shell", "render", "print", "acceptance"]
STAGE_DESC = {
    "art": "sheet image -> layer grid (build/art)",
    "convert": "layer grid -> Kromacut 3MF/STLs/manifest (build/print)",
    "shell": "validated STEP -> recessed plate + shell.json/parts.json",
    "render": "Blender scene + assembly 3MF + postprocess (run_all.sh 1/4-3/4)",
    "print": "print-pose STL delivery + bed layout (run_all.sh 4/4)",
    "acceptance": "Lead-side independent acceptance (130/130)",
}
REQUIRES = {
    "art": [],
    "convert": ["art"],
    "shell": [],
    "render": ["art", "convert", "shell"],
    "print": ["shell", "render"],
    "acceptance": ["art", "convert", "shell", "render", "print"],
}


# ---------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------
def rel(path) -> str:
    try:
        return os.path.relpath(os.path.abspath(str(path)), str(ROOT))
    except (ValueError, OSError):
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError:  # pragma: no cover - system python3 ships PyYAML
        raise SystemExit(
            "compile.py: PyYAML is required to read %s.\n"
            "  Ubuntu: sudo apt-get install -y python3-yaml" % rel(path)
        )
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def norm_hex(value) -> str:
    return str(value).strip().upper()


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ---------------------------------------------------------------------------
# validation report
# ---------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, group: str, name: str, ok: bool, detail: str = "",
            fix: str = "", severity: str = "error") -> bool:
        ok = bool(ok)
        self.checks.append({
            "group": group, "name": name, "ok": ok,
            "detail": str(detail), "fix": str(fix),
            "severity": severity if not ok else "error",
        })
        return ok

    def fail(self, group: str, name: str, detail: str, fix: str,
             severity: str = "error") -> bool:
        return self.add(group, name, False, detail, fix, severity)

    def ok(self, group: str, name: str, detail: str = "") -> bool:
        return self.add(group, name, True, detail)

    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"] and c["severity"] == "error"]

    def warnings(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"] and c["severity"] == "warn"]

    def summary(self) -> dict:
        passed = sum(1 for c in self.checks if c["ok"])
        return {
            "total": len(self.checks),
            "passed": passed,
            "failed": len(self.failures()),
            "warnings": len(self.warnings()),
        }

    def failures_by_group(self) -> dict:
        out: dict = {}
        for c in self.failures():
            out.setdefault(c["group"], []).append(c)
        return out


def _num(rep: Report, group: str, name: str, value, source: str,
         required: bool = True) -> float | None:
    if value is None:
        if required:
            rep.fail(group, name, f"missing required numeric value ({source})",
                     f"add {source} to appearance/config/appearance_project.yaml")
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        rep.fail(group, name, f"not a number: {value!r} ({source})",
                 f"set {source} to a number")
        return None


def _eq(rep: Report, group: str, name: str, actual, expected: float,
        tol: float, fix: str, detail: str | None = None) -> bool:
    ok = actual is not None
    if ok:
        try:
            ok = abs(float(actual) - float(expected)) <= tol
        except (TypeError, ValueError):
            ok = False
    return rep.add(group, name, ok,
                   detail if detail is not None else f"{actual!r} vs expected {expected!r}",
                   "" if ok else fix)


def _truthy(rep: Report, group: str, name: str, value, fix: str,
            detail: str | None = None) -> bool:
    ok = bool(value)
    return rep.add(group, name, ok, detail if detail is not None else str(value),
                   "" if ok else fix)


# ---------------------------------------------------------------------------
# config resolution
# ---------------------------------------------------------------------------
def resolve_project(doc, config_rel: str) -> tuple[dict | None, Report]:
    rep = Report()
    tag = "config"
    if not isinstance(doc, dict):
        rep.fail(tag, "top-level mapping", "config is not a YAML mapping",
                 "fix the YAML syntax of appearance/config/appearance_project.yaml")
        return None, rep

    schema = doc.get("schema")
    rep.add(tag, "schema", schema == SCHEMA_PROJECT,
            f"schema={schema!r}", f"set `schema: {SCHEMA_PROJECT}`")
    project = doc.get("project") if isinstance(doc.get("project"), dict) else {}
    paths_raw = doc.get("paths") if isinstance(doc.get("paths"), dict) else {}
    tools_raw = doc.get("tools") if isinstance(doc.get("tools"), dict) else {}
    stages_raw = doc.get("stages") if isinstance(doc.get("stages"), dict) else {}
    versions_raw = doc.get("versions")

    # ---- paths ---------------------------------------------------------- #
    defaults = {
        "art_out": "appearance/build/art",
        "print_out": "appearance/build/print",
        "shell_out": "appearance/build/shell",
        "build_out": "appearance/build",
        "compile_out": "appearance/build/compile",
        "render_cfg": "appearance/render/config.json",
        "log": "appearance/build/compile.log",
        "report_json": "appearance/build/COMPILE_REPORT.json",
        "report_md": "appearance/build/COMPILE_REPORT.md",
    }
    paths = {}
    for key, default in defaults.items():
        value = paths_raw.get(key, default)
        if not isinstance(value, str) or not value:
            rep.fail(tag, f"paths.{key}", f"not a non-empty string: {value!r}",
                     f"set paths.{key} to a repo-relative path")
            value = default
        paths[key] = value
    for key in ("art_out", "print_out", "shell_out"):
        p = ROOT / paths[key]
        if not p.parent.exists() and not p.exists():
            # not fatal: the pipeline creates build dirs; only check obvious typos
            pass

    # ---- tools ---------------------------------------------------------- #
    def resolve_tool(value, name):
        if value is None or value == "auto":
            return "auto"
        if not isinstance(value, str) or not value:
            rep.fail(tag, f"tools.{name}", f"not a non-empty string: {value!r}",
                     f"set tools.{name} to a command or repo-relative/absolute path")
            return "auto"
        if os.path.isabs(value):
            return value
        if "/" in value:
            # NOTE: no Path.resolve() here - the build123d venv python is a
            # symlink to the system interpreter and resolving it escapes the venv.
            return os.path.abspath(os.path.join(str(ROOT), value))
        return value  # bare command name -> resolved through PATH

    tools = {}
    for key in ("python", "bash", "node", "blender", "build123d_python", "kromacut_cli"):
        tools[key] = resolve_tool(tools_raw.get(key), key)
    if tools["node"] in ("auto", None):
        found = shutil.which("node")
        if not found:
            rep.fail("tools", "node", "not found on PATH (tools.node: auto)",
                     "install Node >= 22 or set tools.node to its absolute path")
        tools["node"] = found or ""
    if tools["python"] in ("auto", None):
        found = shutil.which("python3")
        tools["python"] = found or "python3"
    if tools["bash"] in ("auto", None):
        tools["bash"] = shutil.which("bash") or "bash"

    # ---- stages --------------------------------------------------------- #
    for stage in STAGES:
        entry = stages_raw.get(stage)
        if not isinstance(entry, dict):
            rep.fail(tag, f"stages.{stage}", "missing stage definition",
                     f"add stages.{stage}.commands to appearance_project.yaml")
            continue
        cmds = entry.get("commands")
        if not isinstance(cmds, list) or not cmds:
            rep.fail(tag, f"stages.{stage}.commands", "missing/empty command list",
                     f"set stages.{stage}.commands to a non-empty list of lists")
            continue
        for i, cmd in enumerate(cmds):
            if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) for x in cmd):
                rep.fail(tag, f"stages.{stage}.commands[{i}]",
                         f"not a list of strings: {cmd!r}",
                         "fix the command list syntax")
    if rep.failures():
        return None, rep

    # ---- versions ------------------------------------------------------- #
    if not isinstance(versions_raw, dict) or not versions_raw:
        rep.fail(tag, "versions", "missing/empty `versions:` mapping",
                 "define versions.round and versions.square")
        return None, rep
    version_keys = set(versions_raw.keys())
    rep.add(tag, "versions == round+square", version_keys == {"round", "square"},
            f"found {sorted(version_keys)}",
            "this pipeline is keyed on round/square in appearance/render/scene_common.py "
            "and the print-delivery stage; version names are NOT config-only")

    versions: dict = {}
    for vkey, raw in versions_raw.items():
        where = f"versions.{vkey}"
        if not isinstance(raw, dict):
            rep.fail(tag, where, "version entry is not a mapping",
                     f"make {where} a mapping with art/shell/print/expect")
            continue
        art_raw = raw.get("art") if isinstance(raw.get("art"), dict) else {}
        shell_raw = raw.get("shell") if isinstance(raw.get("shell"), dict) else {}
        print_raw = raw.get("print") if isinstance(raw.get("print"), dict) else {}
        expect_raw = raw.get("expect") if isinstance(raw.get("expect"), dict) else {}

        # art
        name = art_raw.get("name")
        if not isinstance(name, str) or not name:
            rep.fail(tag, f"{where}.art.name", f"missing/invalid: {name!r}",
                     f"set {where}.art.name (e.g. dog)")
            name = vkey
        image = art_raw.get("image")
        if not isinstance(image, str) or not image:
            rep.fail(tag, f"{where}.art.image", f"missing/invalid: {image!r}",
                     f"set {where}.art.image to the sheet image path")
            image = ""
        crop_raw = art_raw.get("crop") if isinstance(art_raw.get("crop"), dict) else {}
        mode = str(crop_raw.get("mode") or "ellipse").lower()
        crop = {"mode": mode}
        if mode == "ellipse":
            fields = ("cx", "cy", "rx", "ry")
        elif mode == "bbox":
            fields = ("x0", "y0", "x1", "y1")
        else:
            rep.fail(tag, f"{where}.art.crop.mode", f"unsupported: {mode!r}",
                     f"set crop.mode to ellipse or bbox")
            fields = ()
        for field in fields:
            val = _num(rep, tag, f"{where}.art.crop.{field}", crop_raw.get(field),
                       f"{where}.art.crop.{field}")
            if val is not None:
                crop[field] = val
        palette_raw = art_raw.get("palette_bottom_up")
        palette = []
        if not isinstance(palette_raw, list) or not palette_raw:
            rep.fail(tag, f"{where}.art.palette_bottom_up", "missing/empty list",
                     f"set {where}.art.palette_bottom_up to one #RRGGBB per physical layer")
        else:
            for i, hx in enumerate(palette_raw):
                if not HEX_RE.match(str(hx).strip()):
                    rep.fail(tag, f"{where}.art.palette_bottom_up[{i}]",
                             f"not #RRGGBB: {hx!r}",
                             f"fix {where}.art.palette_bottom_up[{i}]")
                palette.append(str(hx).strip())
        tune = art_raw.get("tuning") if isinstance(art_raw.get("tuning"), dict) else {}
        contrast = _num(rep, tag, f"{where}.art.tuning.contrast",
                        tune.get("contrast", 1.0), f"{where}.art.tuning.contrast",
                        required=False)
        saturation = _num(rep, tag, f"{where}.art.tuning.saturation",
                          tune.get("saturation", 1.0), f"{where}.art.tuning.saturation",
                          required=False)
        pixel = _num(rep, tag, f"{where}.art.pixel_size_mm",
                     art_raw.get("pixel_size_mm"), f"{where}.art.pixel_size_mm")
        layer = _num(rep, tag, f"{where}.art.layer_height_mm",
                     art_raw.get("layer_height_mm"), f"{where}.art.layer_height_mm")
        if pixel is not None and pixel <= 0:
            rep.fail(tag, f"{where}.art.pixel_size_mm", f"must be > 0: {pixel}",
                     f"fix {where}.art.pixel_size_mm")
            pixel = None
        if layer is not None and layer <= 0:
            rep.fail(tag, f"{where}.art.layer_height_mm", f"must be > 0: {layer}",
                     f"fix {where}.art.layer_height_mm")
            layer = None

        # shell
        plate_step = shell_raw.get("plate_step")
        if not isinstance(plate_step, str) or not plate_step:
            rep.fail(tag, f"{where}.shell.plate_step", f"missing/invalid: {plate_step!r}",
                     f"set {where}.shell.plate_step to the validated plate STEP")
            plate_step = ""
        mech = shell_raw.get("mech_label")
        if not isinstance(mech, str) or not mech:
            rep.fail(tag, f"{where}.shell.mech_label", f"missing/invalid: {mech!r}",
                     f"set {where}.shell.mech_label (lumen | square_v1)")
            mech = vkey
        label = shell_raw.get("label") or mech
        style = shell_raw.get("style") or ""
        if not isinstance(style, str) or not style:
            rep.fail(tag, f"{where}.shell.style", f"missing/invalid: {style!r}",
                     f"set {where}.shell.style (currently lumen_violet)")
            style = ""
        rim = _num(rep, tag, f"{where}.shell.rim_z_mm",
                   shell_raw.get("rim_z_mm"), f"{where}.shell.rim_z_mm")
        pocket = _num(rep, tag, f"{where}.shell.pocket_dia_mm",
                      shell_raw.get("pocket_dia_mm"), f"{where}.shell.pocket_dia_mm")
        print_dia = _num(rep, tag, f"{where}.shell.print_dia_mm",
                         shell_raw.get("print_dia_mm"), f"{where}.shell.print_dia_mm")
        interference = _num(rep, tag, f"{where}.shell.interference_mm",
                            shell_raw.get("interference_mm"),
                            f"{where}.shell.interference_mm")
        top_gap = _num(rep, tag, f"{where}.shell.top_gap_mm",
                       shell_raw.get("top_gap_mm"), f"{where}.shell.top_gap_mm")

        # print
        bed = _num(rep, tag, f"{where}.print.bed_mm",
                   print_raw.get("bed_mm"), f"{where}.print.bed_mm")
        button = str(print_raw.get("button") or "").lower()
        if button not in ("none", "part"):
            rep.fail(tag, f"{where}.print.button", f"must be none|part: {button!r}",
                     f"set {where}.print.button to none or part")
        if bed is not None and bed <= 0:
            rep.fail(tag, f"{where}.print.bed_mm", f"must be > 0: {bed}",
                     f"fix {where}.print.bed_mm")
            bed = None

        # expect (optional)
        expect = {}
        for key in ("n_px", "art_diameter_mm", "print_layers", "print_thickness_mm",
                    "pocket_depth_mm", "floor_z_mm", "acceptance_checks"):
            if key in expect_raw:
                val = _num(rep, tag, f"{where}.expect.{key}", expect_raw[key],
                           f"{where}.expect.{key}", required=False)
                if val is not None:
                    expect[key] = val

        # ---- derivation (only if the inputs are usable) ------------------ #
        if not palette or pixel is None or layer is None or print_dia is None or \
                plate_step == "" or pocket is None or interference is None or \
                rim is None or top_gap is None:
            continue
        thickness = round(len(palette) * layer, 6)
        raw_n = print_dia / pixel
        n_px = int(round(raw_n))
        rep.add(tag, f"{where}: n_px integer", abs(raw_n - n_px) <= 1e-6,
                f"print_dia_mm/pixel_size_mm = {print_dia}/{pixel} = {raw_n}",
                f"adjust {where}.shell.print_dia_mm or {where}.art.pixel_size_mm so it "
                "is an integer number of pixels (86.4/0.15 = 576)")
        art_diameter = round((n_px - 0.2) * pixel, 4)
        frame = round(n_px * pixel, 4)
        pocket_depth = round(top_gap + thickness, 6)
        floor = round(rim - top_gap - thickness, 6)
        print_top = round(floor + thickness, 6)
        interference_derived = round((print_dia - pocket) / 2.0, 9)

        rep.add(tag, f"{where}: pocket = print - 2*interference",
                abs(interference - interference_derived) <= 1e-9,
                f"pocket={pocket}, print={print_dia}, interference={interference} "
                f"-> derived radial interference={interference_derived}",
                f"fix {where}.shell.pocket_dia_mm / print_dia_mm / interference_mm: "
                "pocket_dia must equal print_dia - 2*interference_mm")
        rep.add(tag, f"{where}: thickness = layers*layer_height",
                abs(thickness - len(palette) * layer) <= 1e-12,
                f"{len(palette)} x {layer} = {thickness} mm",
                f"fix {where}.art.palette_bottom_up / layer_height_mm")

        # expect (regression baseline) checks
        if expect:
            if "n_px" in expect:
                _eq(rep, tag, f"{where}: expect.n_px", n_px, expect["n_px"], 0,
                    f"update {where}.expect.n_px or revert the pixel/diameter change")
            if "art_diameter_mm" in expect:
                _eq(rep, tag, f"{where}: expect.art_diameter_mm", art_diameter,
                    expect["art_diameter_mm"], 0.005,
                    f"update {where}.expect.art_diameter_mm or revert the pixel/diameter change")
            if "print_layers" in expect:
                _eq(rep, tag, f"{where}: expect.print_layers",
                    len(palette), expect["print_layers"], 0,
                    f"palette has {len(palette)} colours but expect.print_layers="
                    f"{expect['print_layers']:g}; either fix {where}.art.palette_bottom_up "
                    "or update expect.print_layers AND all downstream constants "
                    "(see appearance/INPUTS.md)")
            if "print_thickness_mm" in expect:
                _eq(rep, tag, f"{where}: expect.print_thickness_mm", thickness,
                    expect["print_thickness_mm"], 1e-6,
                    f"derived print thickness {thickness} != expect.print_thickness_mm="
                    f"{expect['print_thickness_mm']:g}; fix {where}.art.palette_bottom_up / "
                    "layer_height_mm or update expect.print_thickness_mm")
            if "pocket_depth_mm" in expect:
                _eq(rep, tag, f"{where}: expect.pocket_depth_mm", pocket_depth,
                    expect["pocket_depth_mm"], 1e-6,
                    f"update {where}.expect.pocket_depth_mm or revert top_gap/palette")
            if "floor_z_mm" in expect:
                _eq(rep, tag, f"{where}: expect.floor_z_mm", floor,
                    expect["floor_z_mm"], 1e-6,
                    f"config {where}.shell.rim_z_mm={rim:g} gives floor_z_mm={floor:g} "
                    f"(rim - top_gap - thickness) but expect.floor_z_mm="
                    f"{expect['floor_z_mm']:g}; fix {where}.shell.rim_z_mm or update "
                    f"{where}.expect.floor_z_mm AND the hard-coded stage constants "
                    "(see appearance/INPUTS.md)")

        versions[vkey] = {
            "art": {
                "name": name, "image": image,
                "crop": crop, "palette_bottom_up": palette,
                "tuning": {"contrast": contrast if contrast is not None else 1.0,
                           "saturation": saturation if saturation is not None else 1.0},
                "pixel_size_mm": pixel, "layer_height_mm": layer,
                "n_px": n_px, "print_dia_mm": print_dia,
                "art_diameter_mm": art_diameter, "frame_mm": frame,
                "print_thickness_mm": thickness,
                "out_dir": str(art_raw.get("out_dir") or paths["art_out"]),
            },
            "shell": {
                "plate_step": plate_step, "mech_label": mech, "label": str(label),
                "style": style, "rim_z_mm": rim, "pocket_dia_mm": pocket,
                "print_dia_mm": print_dia, "interference_mm": interference,
                "top_gap_mm": top_gap, "print_thickness_mm": thickness,
                "pocket_depth_mm": pocket_depth, "floor_z_mm": floor,
                "print_top_z_mm": print_top,
                "project": "mechanical/" + mech,
            },
            "print": {"bed_mm": bed, "button": button},
            "expect": expect,
        }

    if set(versions.keys()) != set(versions_raw.keys()):
        return None, rep  # structurally incomplete -> cannot continue

    # ---- cross-version invariants -------------------------------------- #
    version_items = list(versions.items())
    if version_items:
        ref_key, ref = version_items[0]
        for field, name in (("pocket_dia_mm", "pocket diameter"),
                            ("print_dia_mm", "print diameter"),
                            ("interference_mm", "radial interference"),
                            ("top_gap_mm", "top gap")):
            for vkey, v in version_items[1:]:
                _eq(rep, "config", f"shared {name} across versions",
                    v["shell"][field], ref["shell"][field], 1e-9,
                    f"versions.{vkey}.shell.{field} differs from versions.{ref_key}."
                    f"shell.{field}; this pipeline's shell.json/render/3MF print "
                    "geometry is shared across versions - keep them equal")
    for vkey, v in versions.items():
        if v["print"]["button"] == "part" and vkey != "square":
            rep.add("config", f"{vkey}.print.button=part", True,
                    "non-square button part -> print stage is square-only; verified below")
        if v["print"]["bed_mm"] is not None and abs(v["print"]["bed_mm"] - 220.0) > 1e-9:
            rep.fail("config", f"versions.{vkey}.print.bed_mm",
                     f"{v['print']['bed_mm']} != 220 (bed layout script hardcodes 220)",
                     "render/print/appearance/print_layout_appearance.py BED_MM is fixed at "
                     "220; changing the bed is NOT config-only - edit that script (outside "
                     "compile's write scope) and re-verify")
    resolved = {
        "schema": SCHEMA_RESOLVED,
        "source_config": config_rel,
        "source_config_sha256": sha256_file(ROOT / config_rel),
        "project": project,
        "paths": paths,
        "tools": tools,
        "stages": stages_raw,
        "versions": versions,
    }
    return resolved, rep


# ---------------------------------------------------------------------------
# environment / inputs / stage constants
# ---------------------------------------------------------------------------
def check_tools(resolved: dict, rep: Report) -> None:
    tools = resolved["tools"]
    tag = "tools"

    def which_check(key: str, label: str) -> str | None:
        value = tools.get(key, "")
        if not value:
            rep.fail(tag, label, "not configured", f"set tools.{key} in appearance_project.yaml")
            return None
        path = value if (os.path.isabs(value) or os.sep in value) else shutil.which(value)
        if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
            rep.fail(tag, label, f"not executable: {value}",
                     f"install it or point tools.{key} at the executable")
            return None
        rep.ok(tag, label, path)
        return path

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    python_path = which_check("python", "system python3")
    which_check("bash", "bash")
    node = which_check("node", "node (Kromacut bridge)")
    blender = which_check("blender", "Blender")
    b3d_py = which_check("build123d_python", "build123d venv python")
    which_check("kromacut_cli", "Kromacut headless CLI")

    if python_path:
        cp = subprocess.run([python_path, "-c", "import yaml, numpy, PIL; print(yaml.__version__)"],
                            capture_output=True, text=True, timeout=120, env=env)
        rep.add(tag, "python3 has yaml/numpy/Pillow", cp.returncode == 0,
                (cp.stdout or cp.stderr).strip()[:200],
                "install python3-yaml python3-numpy python3-pil")

    if node:
        cp = subprocess.run([node, "--version"], capture_output=True, text=True,
                            timeout=60, env=env)
        version = (cp.stdout or "").strip()
        try:
            major = int(version.lstrip("v").split(".")[0])
        except ValueError:
            major = 0
        rep.add(tag, "Node >= 22", cp.returncode == 0 and major >= 22, version,
                "install Node >= 22 (Kromacut headless bridge uses Vite SSR); "
                "point tools.node at it")
    if blender:
        cp = subprocess.run([blender, "--version"], capture_output=True, text=True,
                            timeout=120, env=env)
        out = (cp.stdout or "") + (cp.stderr or "")
        rep.add(tag, "Blender 4.5.3", cp.returncode == 0 and "4.5.3" in out,
                out.splitlines()[0] if out else "no output",
                "install Blender 4.5.3 LTS or point tools.blender at it")
    if b3d_py:
        cp = subprocess.run(
            [b3d_py, "-c", "import sys, build123d; print(sys.version.split()[0], build123d.__version__)"],
            capture_output=True, text=True, timeout=180, env=env)
        out = (cp.stdout or cp.stderr).strip()
        rep.add(tag, "build123d 0.10.0 in venv", cp.returncode == 0 and "0.10.0" in out, out,
                "project venv mechanical/square_v1/.venv must have build123d 0.10.0 "
                "(see requirements.yaml); tools.build123d_python points at it")
    req = ROOT / "requirements.yaml"
    if req.is_file():
        text = req.read_text(encoding="utf-8")
        rep.add(tag, "requirements.yaml registers kromacut 4.2.0",
                'kromacut: "4.2.0"' in text, "requirements.yaml",
                "update requirements.yaml when the Kromacut version changes")
        rep.add(tag, "requirements.yaml registers blender 4.5.3",
                'blender: "4.5.3"' in text, "requirements.yaml",
                "update requirements.yaml when the Blender version changes")
    else:
        rep.fail(tag, "requirements.yaml", "missing", "restore requirements.yaml")


def check_inputs(resolved: dict, rep: Report) -> None:
    tag = "inputs"
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        rep.fail(tag, "Pillow", "not importable in system python3",
                 "install python3-pil")
        return
    for vkey, v in resolved["versions"].items():
        art = v["art"]
        image_path = ROOT / art["image"]
        if not image_path.is_file():
            rep.fail(tag, f"{vkey}: art sheet image", f"file not found: {art['image']}",
                     f"put the sheet at {art['image']} or edit "
                     f"appearance/config/appearance_project.yaml versions.{vkey}.art.image")
            continue
        try:
            im = Image.open(image_path)
            im.load()
        except Exception as exc:  # noqa: BLE001 - report any decode error
            rep.fail(tag, f"{vkey}: art sheet image", f"cannot open {art['image']}: {exc}",
                     "replace the image with a valid PNG/JPG")
            continue
        rep.ok(tag, f"{vkey}: art sheet image", f"{art['image']} {im.size[0]}x{im.size[1]} {im.mode}")
        crop = art["crop"]
        box = [crop[k] for k in ("cx", "cy", "rx", "ry")] if crop["mode"] == "ellipse" else \
              [crop[k] for k in ("x0", "y0", "x1", "y1")]
        if crop["mode"] == "ellipse":
            x0, y0 = box[0] - box[2], box[1] - box[3]
            x1, y1 = box[0] + box[2], box[1] + box[3]
        else:
            x0, y0, x1, y1 = box
        ok = (0 <= x0 < x1 <= im.size[0]) and (0 <= y0 < y1 <= im.size[1])
        rep.add(tag, f"{vkey}: crop inside image", ok,
                f"crop=({x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}) image={im.size[0]}x{im.size[1]}",
                f"edit versions.{vkey}.art.crop: the crop must lie inside "
                f"{art['image']} ({im.size[0]}x{im.size[1]} px)")
        rep.add(tag, f"{vkey}: crop is square-ish",
                abs((x1 - x0) - (y1 - y0)) / max(1.0, x1 - x0) < 0.1,
                f"{x1 - x0:.1f} x {y1 - y0:.1f} px",
                f"an ellipse bbox is naturally slightly non-square; a bbox crop should be "
                f"square, otherwise the art will be stretched (versions.{vkey}.art.crop)")
        plate = ROOT / v["shell"]["plate_step"]
        rep.add(tag, f"{vkey}: plate STEP", plate.is_file(),
                v["shell"]["plate_step"],
                f"put the validated plate at {v['shell']['plate_step']} or edit "
                f"versions.{vkey}.shell.plate_step")
        for dkey in ("art_out", "print_out", "shell_out"):
            parent = ROOT / resolved["paths"][dkey]
            rep.add(tag, f"{vkey}: output root writable: paths.{dkey}",
                    parent.exists() or parent.parent.exists(),
                    str(parent), f"check paths.{dkey} in appearance_project.yaml")


def check_stage_constants(resolved: dict, rep: Report) -> None:
    tag = "stage_constants"
    versions = resolved["versions"]
    paths = resolved["paths"]
    tools = resolved["tools"]

    # ---- appearance/render/scene_common.py VERSIONS -------------------- #
    sc_versions = None
    try:
        sys.path.insert(0, str(ROOT / "appearance" / "render"))
        import scene_common  # noqa: WPS433 - read-only import of a pure-stdlib module
        sc_versions = getattr(scene_common, "VERSIONS", None)
    except Exception as exc:  # noqa: BLE001
        rep.fail(tag, "scene_common.py import", f"{exc}",
                 "fix appearance/render/scene_common.py (it is imported read-only here)")
    if isinstance(sc_versions, dict):
        for vkey, v in versions.items():
            entry = sc_versions.get(vkey)
            if not isinstance(entry, dict):
                rep.fail(tag, f"scene_common VERSIONS.{vkey}", "missing",
                         "edit appearance/render/scene_common.py VERSIONS: this file maps "
                         "version -> mech/art and is NOT config-only (outside compile's "
                         "write scope)")
                continue
            rep.add(tag, f"scene_common VERSIONS.{vkey}.mech",
                    entry.get("mech") == v["shell"]["mech_label"],
                    f"{entry.get('mech')!r} vs {v['shell']['mech_label']!r}",
                    "edit appearance/render/scene_common.py VERSIONS"
                    f"[{vkey!r}]['mech'] (hard-coded mapping, not config-only)")
            rep.add(tag, f"scene_common VERSIONS.{vkey}.art",
                    entry.get("art") == v["art"]["name"],
                    f"{entry.get('art')!r} vs {v['art']['name']!r}",
                    "edit appearance/render/scene_common.py VERSIONS"
                    f"[{vkey!r}]['art'] (hard-coded mapping, not config-only)")
        # button part expectation in the hard-coded part lists
        for vkey, v in versions.items():
            if vkey not in ("round", "square"):
                continue
            names = (getattr(scene_common, "SQUARE_PARTS", []) if vkey == "square"
                     else getattr(scene_common, "ROUND_PARTS", []))
            has_button = "button" in names
            rep.add(tag, f"scene_common part list button ({vkey})",
                    has_button == (v["print"]["button"] == "part"),
                    f"part list has button={has_button}, config button={v['print']['button']}",
                    "edit appearance/render/scene_common.py ROUND_PARTS/SQUARE_PARTS "
                    "(hard-coded part list, not config-only)")

    # ---- appearance/render/config.json --------------------------------- #
    rcfg_path = ROOT / paths["render_cfg"]
    rcfg = None
    if rcfg_path.is_file():
        try:
            rcfg = load_json(rcfg_path)
            rep.ok(tag, "render/config.json", rel(rcfg_path))
        except Exception as exc:  # noqa: BLE001
            rep.fail(tag, "render/config.json", f"cannot parse: {exc}",
                     "fix appearance/render/config.json")
    else:
        rep.fail(tag, "render/config.json", "missing", "restore appearance/render/config.json")
    if isinstance(rcfg, dict):
        rc_versions = rcfg.get("versions") or {}
        for vkey, v in versions.items():
            entry = rc_versions.get(vkey) or {}
            rep.add(tag, f"render/config.json versions.{vkey}.mech",
                    entry.get("mech") == v["shell"]["mech_label"],
                    f"{entry.get('mech')!r} vs {v['shell']['mech_label']!r}",
                    "edit appearance/render/config.json versions"
                    f".{vkey}.mech (camera/version mapping is NOT config-only)")
            rep.add(tag, f"render/config.json versions.{vkey}.art",
                    entry.get("art") == v["art"]["name"],
                    f"{entry.get('art')!r} vs {v['art']['name']!r}",
                    "edit appearance/render/config.json versions"
                    f".{vkey}.art (camera/version mapping is NOT config-only)")
        rp = rcfg.get("print") or {}
        ref = next(iter(versions.values()))
        for field, key in (("pocket_dia_mm", "pocket_dia_mm"),
                           ("print_dia_mm", "print_dia_mm"),
                           ("interference_mm", "interference_mm"),
                           ("top_gap_mm", "top_gap_mm")):
            _eq(rep, tag, f"render/config.json print.{key}", rp.get(field),
                ref["shell"][field], 1e-9,
                f"edit appearance/render/config.json print.{key} (fallback contract, "
                "not config-only)")
        cmf_style = (rcfg.get("cmf") or {}).get("style")
        styles = {v["shell"]["style"] for v in versions.values()}
        rep.add(tag, "render/config.json cmf.style == config shell.style",
                len(styles) == 1 and cmf_style in styles,
                f"render cmf.style={cmf_style!r}, config styles={sorted(styles)}",
                "edit appearance/render/config.json cmf.style (CMF style mapping is NOT "
                "config-only; styles live in render/appearance/styles.json)")
        for vkey, v in versions.items():
            fb = (rcfg.get("shell_fallback") or {}).get(vkey) or {}
            _eq(rep, tag, f"render/config.json shell_fallback.{vkey}.rim_z_mm",
                fb.get("rim_z_mm"), v["shell"]["rim_z_mm"], 1e-9,
                f"edit appearance/render/config.json shell_fallback.{vkey}.rim_z_mm "
                "(fallback contract, not config-only)")
            _eq(rep, tag, f"render/config.json shell_fallback.{vkey}.floor_z_mm",
                fb.get("floor_z_mm"), v["shell"]["floor_z_mm"], 1e-9,
                f"edit appearance/render/config.json shell_fallback.{vkey}.floor_z_mm "
                "(fallback contract, not config-only)")
            _eq(rep, tag, f"render/config.json shell_fallback.{vkey}.thickness_mm",
                fb.get("thickness_mm"), v["shell"]["print_thickness_mm"], 1e-9,
                f"edit appearance/render/config.json shell_fallback.{vkey}.thickness_mm "
                "(fallback contract, not config-only)")
            _eq(rep, tag, f"render/config.json shell_fallback.{vkey}.pocket_dia_mm",
                fb.get("pocket_dia_mm"), v["shell"]["pocket_dia_mm"], 1e-9,
                f"edit appearance/render/config.json shell_fallback.{vkey}.pocket_dia_mm "
                "(fallback contract, not config-only)")

    # ---- appearance/kromacut/run_convert.sh art loop ------------------- #
    convert_sh = ROOT / "appearance" / "kromacut" / "run_convert.sh"
    if convert_sh.is_file():
        text = convert_sh.read_text(encoding="utf-8")
        found = re.findall(r"for\s+name\s+in\s+([A-Za-z0-9_\s]+?)\s*;\s*do", text)
        if found:
            names = sorted(found[0].split())
            expected = sorted(v["art"]["name"] for v in versions.values())
            rep.add(tag, "run_convert.sh art loop", names == expected,
                    f"loop={names} config={expected}",
                    "edit appearance/kromacut/run_convert.sh `for name in ...` "
                    "(line ~93; this loop is hard-coded and NOT config-only)")
        else:
            rep.fail(tag, "run_convert.sh art loop", "could not find `for name in ...; do`",
                     "appearance/kromacut/run_convert.sh changed shape; compile.py cannot "
                     "verify the art loop - update compile.py's validator")
    else:
        rep.fail(tag, "run_convert.sh", "missing", "restore appearance/kromacut/run_convert.sh")

    # ---- run_shell.sh / build_recessed.py hard-coded tools ------------- #
    run_shell = ROOT / "appearance" / "cad" / "run_shell.sh"
    if run_shell.is_file():
        text = run_shell.read_text(encoding="utf-8")
        m = re.search(r'^PY="([^"]+)"', text, re.M)
        want = tools.get("build123d_python", "")
        rep.add(tag, "run_shell.sh PY == tools.build123d_python",
                bool(m) and os.path.abspath(m.group(1)) == os.path.abspath(want),
                f"{m.group(1) if m else 'missing'} vs {want}",
                "edit appearance/cad/run_shell.sh PY constant (hard-coded, outside "
                "compile's write scope) or fix tools.build123d_python")
    recessed = ROOT / "appearance" / "cad" / "build_recessed.py"
    if recessed.is_file():
        text = recessed.read_text(encoding="utf-8")
        m = re.search(r'^BLENDER = "([^"]+)"', text, re.M)
        want = tools.get("blender", "")
        rep.add(tag, "build_recessed.py BLENDER == tools.blender",
                bool(m) and os.path.abspath(m.group(1)) == os.path.abspath(want),
                f"{m.group(1) if m else 'missing'} vs {want}",
                "edit appearance/cad/build_recessed.py BLENDER constant (hard-coded, "
                "outside compile's write scope) or fix tools.blender")

    # ---- print-layout constants ---------------------------------------- #
    layout_py = ROOT / "render" / "print" / "appearance" / "print_layout_appearance.py"
    if layout_py.is_file():
        text = layout_py.read_text(encoding="utf-8")
        consts = {}
        for key in ("BED_MM", "MIN_GAP_MM", "PRINT_NEST_Z_MM"):
            m = re.search(rf"^{key}\s*=\s*([0-9.]+)", text, re.M)
            consts[key] = float(m.group(1)) if m else None
        for vkey, v in versions.items():
            _eq(rep, tag, f"print_layout BED_MM ({vkey})", consts["BED_MM"],
                v["print"]["bed_mm"], 1e-9,
                "edit render/print/appearance/print_layout_appearance.py BED_MM "
                "(hard-coded bed, outside compile's write scope)")
            _eq(rep, tag, f"print_layout PRINT_NEST_Z_MM ({vkey})",
                consts["PRINT_NEST_Z_MM"], v["shell"]["top_gap_mm"], 1e-9,
                "edit render/print/appearance/print_layout_appearance.py "
                "PRINT_NEST_Z_MM (hard-coded top gap, outside compile's write scope)")
        m = re.search(r'^VERSIONS\s*=\s*\(([^)]*)\)', text, re.M)
        if m:
            names = tuple(x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip())
            rep.add(tag, "print stage VERSIONS tuple", set(names) == set(versions.keys()),
                    f"{names} vs {sorted(versions)}",
                    "edit render/print/appearance/print_layout_appearance.py VERSIONS "
                    "(hard-coded, outside compile's write scope)")
    else:
        rep.fail(tag, "print_layout_appearance.py", "missing",
                 "restore render/print/appearance/print_layout_appearance.py")

    # ---- run_all.sh composition ---------------------------------------- #
    run_all = ROOT / "appearance" / "render" / "run_all.sh"
    if run_all.is_file():
        text = run_all.read_text(encoding="utf-8")
        needed = ["build_scene.py", "make_3mf.py", "postprocess.py", "run_print_stage.sh"]
        missing = [n for n in needed if n not in text]
        rep.add(tag, "run_all.sh sub-command set", not missing,
                f"missing {missing}" if missing else "build_scene/make_3mf/postprocess/print",
                "appearance/render/run_all.sh changed: compile.py splits the render+print "
                "stages along its 1/4-3/4-4/4 commands; update the render/print stage "
                "commands in appearance/config/appearance_project.yaml + this validator")

    # ---- Lead-owned acceptance baseline -------------------------------- #
    acc = ROOT / "appearance" / "tools" / "acceptance_check.py"
    if acc.is_file():
        text = acc.read_text(encoding="utf-8")
        owner_fix = ("appearance/tools/acceptance_check.py is Lead-owned/read-only for "
                     "this task: changing this input is NOT config-only. Its baseline "
                     "numbers must be updated by the Lead together with re-verification "
                     "(see appearance/INPUTS.md).")
        exp = None
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "exp" for t in node.targets):
                    exp = ast.literal_eval(node.value)
        except (SyntaxError, ValueError):
            exp = None
        if isinstance(exp, dict):
            for vkey, v in versions.items():
                e = exp.get(vkey)
                if not isinstance(e, dict):
                    rep.fail(tag, f"acceptance baseline ({vkey})", "missing version entry",
                             owner_fix)
                    continue
                rep.add(tag, f"acceptance baseline ({vkey}).variant",
                        e.get("variant") == v["art"]["name"],
                        f"{e.get('variant')!r} vs {v['art']['name']!r}", owner_fix)
                _eq(rep, tag, f"acceptance baseline ({vkey}).rim", e.get("rim"),
                    v["shell"]["rim_z_mm"], 1e-9, owner_fix)
                _eq(rep, tag, f"acceptance baseline ({vkey}).floor", e.get("floor"),
                    v["shell"]["floor_z_mm"], 1e-9, owner_fix)
                _eq(rep, tag, f"acceptance baseline ({vkey}).depth", e.get("depth"),
                    v["shell"]["pocket_depth_mm"], 1e-9, owner_fix)
                _eq(rep, tag, f"acceptance baseline ({vkey}).t", e.get("t"),
                    v["shell"]["print_thickness_mm"], 1e-9, owner_fix)
        else:
            rep.fail(tag, "acceptance baseline", "could not parse `exp` dict",
                     "appearance/tools/acceptance_check.py changed shape; update this "
                     "validator (Lead-owned file)")
        m = re.search(r'art_diameter_mm"\]\s*-\s*([0-9.]+)', text)
        ref_art = next(iter(versions.values()))["art"]["art_diameter_mm"]
        rep.add(tag, "acceptance baseline art diameter",
                bool(m) and abs(float(m.group(1)) - ref_art) <= 0.005,
                f"{m.group(1) if m else 'missing'} vs {ref_art}", owner_fix)
        m = re.search(r'layer_count"\]\s*\*\s*([0-9.]+)\s*-\s*e\["t"\]', text)
        ref_layer = next(iter(versions.values()))["art"]["layer_height_mm"]
        rep.add(tag, "acceptance baseline layer height",
                bool(m) and abs(float(m.group(1)) - ref_layer) <= 1e-9,
                f"{m.group(1) if m else 'missing'} vs {ref_layer}", owner_fix)
        m = re.search(r'pocket_dia_mm"\]\s*==\s*([0-9.]+)\s*and\s*s\["print_dia_mm"\]\s*==\s*([0-9.]+)', text)
        ref = next(iter(versions.values()))["shell"]
        rep.add(tag, "acceptance baseline pocket/print diameter",
                bool(m) and abs(float(m.group(1)) - ref["pocket_dia_mm"]) <= 1e-9
                and abs(float(m.group(2)) - ref["print_dia_mm"]) <= 1e-9,
                f"{m.groups() if m else 'missing'} vs "
                f"{ref['pocket_dia_mm']}/{ref['print_dia_mm']}", owner_fix)
        if exp is None:
            rep.add(tag, "acceptance baseline exp", False, "not parsed", owner_fix,
                    severity="warn")
    else:
        rep.fail(tag, "acceptance_check.py", "missing",
                 "restore appearance/tools/acceptance_check.py")


# ---------------------------------------------------------------------------
# artifact validation
# ---------------------------------------------------------------------------
class ArtifactCtx:
    def __init__(self, resolved: dict, plan: list[str], mode: str):
        self.resolved = resolved
        self.plan = plan
        self.mode = mode  # "dry" (missing pending if producer in plan) | "post"

    def file(self, rep: Report, group: str, path: Path, producer: str,
             fix: str | None = None) -> Path | None:
        name = rel(path)
        if path.is_file():
            return path
        if self.mode == "dry" and producer in self.plan:
            rep.add(group, name + " (pending)", True,
                    "not built yet; stage %r in this plan will produce it" % producer)
            return None
        rep.fail(group, name, "missing: " + name,
                 fix or ("run stage %r (or the full pipeline)" % producer))
        return None

    def state_ok(self, rep: Report, name: str, path: Path, fix: str) -> bool:
        return rep.add("state", name, path.is_file(), rel(path) if path.is_file() else "missing",
                       "" if path.is_file() else fix)


def validate_art(resolved: dict, rep: Report, ctx: ArtifactCtx) -> None:
    tag = "artifacts/art"
    art_roots = {}
    for vkey, v in resolved["versions"].items():
        art = v["art"]
        d = ROOT / art["out_dir"] / art["name"]
        art_roots[vkey] = d
        group = f"{tag}:{art['name']}"
        aj_path = None
        for fname in ("art.json", "layer_counts.bin", "art_rgba.png",
                      "art_source_crop.png", "art_quant_preview.png", "palette.png"):
            path = ctx.file(rep, group, d / fname, "art")
            if fname == "art.json":
                aj_path = path
        if not aj_path:
            continue
        try:
            aj = load_json(aj_path)
        except Exception as exc:  # noqa: BLE001
            rep.fail(group, "art.json parse", str(exc), "re-run stage art")
            continue
        n = art["n_px"]
        _eq(rep, group, "art.json width", aj.get("width"), n, 0, "re-run `make_art.py`")
        _eq(rep, group, "art.json height", aj.get("height"), n, 0, "re-run `make_art.py`")
        _eq(rep, group, "art.json pixel_size_mm", aj.get("pixel_size_mm"),
            art["pixel_size_mm"], 1e-12,
            "re-run `make_art.py` (config pixel_size_mm changed)")
        _eq(rep, group, "art.json layer_height_mm", aj.get("layer_height_mm"),
            art["layer_height_mm"], 1e-12,
            "re-run `make_art.py` (config layer_height_mm changed)")
        _eq(rep, group, "art.json layer_count", aj.get("layer_count"),
            len(art["palette_bottom_up"]), 0,
            "re-run `make_art.py`; palette length must equal physical layer count")
        _eq(rep, group, "art.json print_thickness_mm", aj.get("print_thickness_mm"),
            art["print_thickness_mm"], 1e-6,
            "re-run `make_art.py`; thickness = colours * layer_height")
        _eq(rep, group, "art.json art_diameter_mm", aj.get("art_diameter_mm"),
            art["art_diameter_mm"], 1e-3,
            "re-run `make_art.py`; art diameter = (n_px-0.2)*pixel_size")
        _eq(rep, group, "art.json frame_mm", aj.get("frame_mm"),
            art["frame_mm"], 1e-3, "re-run `make_art.py`; frame = n_px*pixel_size")
        rep.add(group, "art.json palette_bottom_up",
                [norm_hex(h) for h in (aj.get("palette_bottom_up") or [])]
                == [norm_hex(h) for h in art["palette_bottom_up"]],
                f"{len(aj.get('palette_bottom_up') or [])} vs "
                f"{len(art['palette_bottom_up'])} colours",
                "re-run `make_art.py` (palette changed)")
        src = aj.get("source") or {}
        rep.add(group, "art.json source.file", src.get("file") == art["image"],
                f"{src.get('file')!r} vs {art['image']!r}",
                "re-run `make_art.py` (image path changed)")
        if (ROOT / art["image"]).is_file():
            rep.add(group, "art.json source.sha256",
                    src.get("sha256") == sha256_file(ROOT / art["image"]),
                    "source image differs from art.json provenance",
                    "re-run `make_art.py` after changing the art sheet")
        box = art["crop"]
        if box["mode"] == "ellipse":
            exp_box = [box["cx"] - box["rx"], box["cy"] - box["ry"],
                       box["cx"] + box["rx"], box["cy"] + box["ry"]]
        else:
            exp_box = [box["x0"], box["y0"], box["x1"], box["y1"]]
        got = src.get("bbox_xyxy") or []
        rep.add(group, "art.json crop bbox",
                len(got) == 4 and all(abs(float(g) - e) <= 0.006 for g, e in zip(got, exp_box)),
                f"{got} vs {[round(x, 2) for x in exp_box]}",
                "re-run `make_art.py` (crop changed)")
        layers = aj.get("layers") or {}
        trans = layers.get("0 (transparent)")
        rep.add(group, "art.json transparent pixels > 0",
                isinstance(trans, int) and trans > 0, str(trans),
                "re-run `make_art.py`; transparent outside circle expected")
        # layer_counts.bin
        lc = d / "layer_counts.bin"
        if lc.is_file():
            data = lc.read_bytes()
            rep.add(group, "layer_counts.bin size == n*n*2",
                    len(data) == n * n * 2, f"{len(data)} B vs {n * n * 2} B",
                    "re-run `make_art.py`")
            arr = array("H")
            try:
                arr.frombytes(data)
            except ValueError:
                rep.fail(group, "layer_counts.bin parse",
                         f"not uint16 pairs ({len(data)} B)",
                         "re-run `make_art.py`")
                arr = array("H")
            if sys.byteorder != "little":
                arr.byteswap()
            rep.add(group, "layer_counts.bin max index <= palette length",
                    (max(arr) if arr else 0) <= len(art["palette_bottom_up"]),
                    f"max={max(arr) if arr else 0}, K={len(art['palette_bottom_up'])}",
                    "re-run `make_art.py` (palette changed)")
            counts = {}
            for value in arr:
                counts[value] = counts.get(value, 0) + 1
            rep.add(group, "layer_counts.bin transparent count matches art.json",
                    counts.get(0, 0) == trans,
                    f"{counts.get(0, 0)} vs {trans}", "re-run `make_art.py`")
    board = ROOT / resolved["paths"]["art_out"] / "art_board.png"
    ctx.file(rep, tag, board, "art")


def validate_convert(resolved: dict, rep: Report, ctx: ArtifactCtx) -> None:
    tag = "artifacts/convert"
    for vkey, v in resolved["versions"].items():
        art = v["art"]
        d = ROOT / resolved["paths"]["print_out"] / art["name"]
        group = f"{tag}:{art['name']}"
        manifest = ctx.file(rep, group, d / "manifest.json", "convert")
        if not manifest:
            continue
        try:
            man = load_json(manifest)
        except Exception as exc:  # noqa: BLE001
            rep.fail(group, "manifest.json parse", str(exc), "re-run stage convert")
            continue
        thickness = art["print_thickness_mm"]
        palette = [norm_hex(h) for h in art["palette_bottom_up"]]
        layout = man.get("layout") or {}
        _eq(rep, group, "manifest layout.totalHeightMm", layout.get("totalHeightMm"),
            thickness, 1e-6,
            "re-run stage convert (palette/layer height changed)")
        _eq(rep, group, "manifest layout.classCount", layout.get("classCount"),
            len(palette), 0, "re-run stage convert (palette length changed)")
        _truthy(rep, group, "manifest layout.usesFullPalette",
                layout.get("usesFullPalette"),
                "re-run stage convert; the palette must be fully used")
        stls = man.get("stls") or []
        rep.add(group, "manifest one STL per palette colour",
                len(stls) == len(palette), f"{len(stls)} vs {len(palette)}",
                "re-run stage convert (palette length changed)")
        for i, entry in enumerate(stls):
            fname = str(entry.get("file") or "")
            expected_prefix = f"filament_{i + 1}_"
            hexpart = norm_hex(palette[i]).lstrip("#") if i < len(palette) else ""
            rep.add(group, f"manifest stl[{i}] name {expected_prefix}{hexpart}",
                    fname.startswith(expected_prefix) and hexpart in fname.upper(),
                    fname, "re-run stage convert (palette order changed)")
            sp = d / fname
            if sp.is_file():
                expected_size = 84 + 50 * int(entry.get("triangles") or 0)
                rep.add(group, f"{fname} binary STL size", sp.stat().st_size == expected_size,
                        f"{sp.stat().st_size} B vs {expected_size} B",
                        "re-run stage convert")
            else:
                ctx.file(rep, group, sp, "convert")
        export = man.get("export") or {}
        three = export.get("threeMf")
        if three:
            ctx.file(rep, group, d / three, "convert")
        else:
            rep.fail(group, "manifest export.threeMf", "missing field",
                     "re-run stage convert")
        place = (man.get("stlPlacement") or {}).get("recentredBboxMm") or {}
        size = place.get("size") or {}
        _eq(rep, group, "manifest recentred bbox x = print_dia",
            size.get("x"), art["print_dia_mm"], 0.01,
            "re-run stage convert (print diameter changed)")
        _eq(rep, group, "manifest recentred bbox y = print_dia",
            size.get("y"), art["print_dia_mm"], 0.01,
            "re-run stage convert (print diameter changed)")
        _eq(rep, group, "manifest recentred bbox z = thickness",
            size.get("z"), thickness, 1e-3,
            "re-run stage convert (palette changed)")
        zmin = (place.get("min") or {}).get("z")
        _eq(rep, group, "manifest recentred bbox min z = 0", zmin, 0.0, 1e-3,
            "re-run stage convert")
        ver = man.get("verification") or {}
        rep.add(group, "manifest Kromacut self-checks passed", ver.get("passed") is True,
                f"passed={ver.get('passed')!r}",
                "re-run stage convert; see manifest verification checks")


def validate_shell(resolved: dict, rep: Report, ctx: ArtifactCtx) -> None:
    tag = "artifacts/shell"
    shell_root = ROOT / resolved["paths"]["shell_out"]
    shell_json = ctx.file(rep, tag, shell_root / "shell.json", "shell")
    parts_json = ctx.file(rep, tag, shell_root / "parts.json", "shell")
    ctx.file(rep, tag, shell_root / "REPORT.md", "shell")
    for vkey, v in resolved["versions"].items():
        shell = v["shell"]
        group = f"{tag}:{vkey}"
        plate = shell_root / vkey / "plate_recessed.stl"
        ctx.file(rep, group, plate, "shell")
        ctx.file(rep, group, shell_root / vkey / "plate_recessed.step", "shell")
        if vkey == "round":
            for fname in ("plate_recessed_clean.stl", "plate_recessed_clean.step"):
                if (shell_root / vkey / fname).is_file():
                    rep.ok(group, fname, "present")
        if not shell_json:
            continue
        try:
            sh = load_json(shell_json)
        except Exception as exc:  # noqa: BLE001
            rep.fail(group, "shell.json parse", str(exc), "re-run stage shell")
            shell_json = None
            continue
        s = sh.get(vkey) or {}
        for field, expected, tol in (
            ("rim_z_mm", shell["rim_z_mm"], 1e-9),
            ("floor_z_mm", shell["floor_z_mm"], 1e-9),
            ("pocket_dia_mm", shell["pocket_dia_mm"], 1e-9),
            ("print_dia_mm", shell["print_dia_mm"], 1e-9),
            ("interference_mm", shell["interference_mm"], 1e-9),
            ("top_gap_mm", shell["top_gap_mm"], 1e-9),
            ("print_thickness_mm", shell["print_thickness_mm"], 1e-9),
            ("pocket_depth_mm", shell["pocket_depth_mm"], 1e-9),
            ("print_top_z_mm", shell["print_top_z_mm"], 1e-9),
        ):
            _eq(rep, group, f"shell.json {field}", s.get(field), expected, tol,
                f"re-run stage shell; shell.json {field} must match "
                "appearance_project.yaml derived values")
        files = s.get("files") or {}
        if files.get("plate_stl"):
            ctx.file(rep, group, ROOT / files["plate_stl"], "shell")
        valid = (sh.get("validation") or {}).get(vkey) or {}
        _truthy(rep, group, "shell.json bbox_unchanged", valid.get("bbox_unchanged"),
                "re-run stage shell; the pocket cut must not change the plate bbox")
        _eq(rep, group, "shell.json pocket floor flatness",
            valid.get("pocket_floor_flatness_mm"), 0.0, 1e-9,
            "re-run stage shell; the pocket floor must be a flat plane")
        after = valid.get("plate_after") or {}
        _eq(rep, group, "shell.json plate solids after", after.get("solid_count"), 1, 0,
            "re-run stage shell")
        _truthy(rep, group, "shell.json plate valid after", after.get("is_valid"),
                "re-run stage shell; the cut result must be a valid solid")
        art = s.get("art") or {}
        if art:
            rep.add(group, "shell.json art variant", art.get("name") == v["art"]["name"],
                    f"{art.get('name')!r} vs {v['art']['name']!r}",
                    "re-run stage shell + art; the variant mapping changed")
            _truthy(rep, group, "shell.json print thickness == art thickness",
                    art.get("thickness_matches_spec"),
                    "re-run stage shell; shell thickness and art layer count disagree")
    # blanks
    for vkey, v in resolved["versions"].items():
        blank = shell_root / f"print_blank_{vkey}.stl"
        if ctx.file(rep, tag, blank, "shell"):
            rep.ok(tag, f"print_blank_{vkey}.stl", str(blank.stat().st_size) + " B")
    ctx.file(rep, tag, shell_root / "print_blank.stl", "shell")
    # button consistency with parts.json
    if parts_json:
        try:
            parts = load_json(parts_json)
        except Exception as exc:  # noqa: BLE001
            rep.fail(tag, "parts.json parse", str(exc), "re-run stage shell")
            parts = {}
        shapes = parts.get("shapes") or {}
        for vkey, v in resolved["versions"].items():
            entry = shapes.get(vkey) or {}
            names = [p.get("name", "") for p in entry.get("internal_parts") or []]
            buttons = [p for p in entry.get("internal_parts") or []
                       if str(p.get("name", "")).startswith("button")]
            want = v["print"]["button"] == "part"
            rep.add(tag, f"parts.json button ({vkey})", bool(buttons) == want,
                    f"parts.json button parts={[b.get('name') for b in buttons]}, "
                    f"config print.button={v['print']['button']}",
                    "config <-> mechanical parts mismatch: if the mechanical project really "
                    "has a button, set print.button: part; otherwise this version needs a "
                    "different mech_label (re-run stage shell). parts.json is generated from "
                    "mechanical/<mech_label>/build/parts/*.step")
            for b in buttons:
                stl = b.get("stl")
                if stl:
                    ctx.file(rep, tag, ROOT / stl, "shell")
            plate = entry.get("plate") or {}
            if plate.get("source_step"):
                rep.add(tag, f"parts.json plate source ({vkey})",
                        plate.get("source_step") == v["shell"]["plate_step"],
                        f"{plate.get('source_step')!r} vs {v['shell']['plate_step']!r}",
                        "re-run stage shell (plate_step changed)")


def validate_render(resolved: dict, rep: Report, ctx: ArtifactCtx) -> None:
    tag = "artifacts/render"
    views = ("hero", "top", "print_top", "macro_edge", "section_exploded")
    for vkey, v in resolved["versions"].items():
        group = f"{tag}:{vkey}"
        d = ROOT / "appearance" / "render" / vkey
        for view in views:
            p = ctx.file(rep, group, d / f"{view}.png", "render")
            if p:
                rep.add(group, f"{view}.png non-trivial", p.stat().st_size > 50_000,
                        f"{p.stat().st_size} B", "re-run stage render")
        ctx.file(rep, group, d / "scene.blend", "render")
        si_path = ctx.file(rep, group, d / "scene_info.json", "render")
        ctx.file(rep, group, d / "annotations.json", "render")
        for raw in ("macro_edge", "section_seated", "section_exploded"):
            ctx.file(rep, group, ROOT / "appearance" / "build" / "render" / vkey / f"{raw}.png",
                     "render")
        if si_path:
            try:
                si = load_json(si_path)
            except Exception as exc:  # noqa: BLE001
                rep.fail(group, "scene_info.json parse", str(exc), "re-run stage render")
                si = {}
            rep.add(group, "scene_info version/art",
                    si.get("version") == vkey and si.get("art") == v["art"]["name"],
                    f"{si.get('version')!r}/{si.get('art')!r}",
                    "re-run stage render; version/art mapping changed")
            sh = si.get("shell") or {}
            _eq(rep, group, "scene_info floor_z_mm", sh.get("floor_z_mm"),
                v["shell"]["floor_z_mm"], 1e-6,
                "re-run stage render; it read a different shell.json")
            _eq(rep, group, "scene_info print thickness", sh.get("print_thickness_mm"),
                v["shell"]["print_thickness_mm"], 1e-6,
                "re-run stage render; it read a different print manifest")
            rep.add(group, "scene_info no mismatches", not si.get("mismatches"),
                    str(si.get("mismatches")),
                    "re-run stage render after fixing shell.json/print manifest mismatch")
        three = ROOT / "appearance" / "build" / "3mf" / f"{vkey}.3mf"
        ctx.file(rep, group, three, "render")
    val_path = ctx.file(rep, tag, ROOT / "appearance" / "build" / "3mf" / "validation.json",
                        "render")
    if val_path:
        try:
            val = load_json(val_path)
        except Exception as exc:  # noqa: BLE001
            rep.fail(tag, "3mf validation.json parse", str(exc), "re-run stage render")
            val = {}
        rep.add(tag, "3mf validation.json ok", val.get("ok") is True,
                f"ok={val.get('ok')!r}", "re-run stage render; see validation.json")
        for vkey in resolved["versions"]:
            entry = (val.get("versions") or {}).get(vkey) or {}
            rep.add(tag, f"3mf validation ({vkey})", entry.get("ok") is True
                    and not entry.get("errors"),
                    f"ok={entry.get('ok')!r} errors={entry.get('errors')!r}",
                    "re-run stage render; see appearance/build/3mf/validation.json")
    ctx.file(rep, tag, ROOT / "appearance" / "render" / "board.png", "render")
    ctx.file(rep, tag, ROOT / "appearance" / "render" / "RENDER_LOG.md", "render")


def validate_print(resolved: dict, rep: Report, ctx: ArtifactCtx) -> None:
    tag = "artifacts/print"
    stl_dir = ROOT / "render" / "print" / "stl"
    delivery_path = ctx.file(rep, tag, stl_dir / "delivery.json", "print")
    ctx.file(rep, tag, stl_dir / "CHECKSUMS.sha256", "print")
    ctx.file(rep, tag, stl_dir / "README.md", "print")
    if delivery_path:
        try:
            dl = load_json(delivery_path)
        except Exception as exc:  # noqa: BLE001
            rep.fail(tag, "delivery.json parse", str(exc), "re-run stage print")
            dl = {}
        rep.add(tag, "delivery all_min_z_zero", dl.get("all_min_z_zero") is True,
                f"{dl.get('all_min_z_zero')!r}", "re-run stage print")
        rep.add(tag, "delivery all_rigid_checks", dl.get("all_rigid_checks") is True,
                f"{dl.get('all_rigid_checks')!r}", "re-run stage print")
        for vkey, v in resolved["versions"].items():
            group = f"{tag}:{vkey}"
            dv = (dl.get("versions") or {}).get(vkey)
            if not isinstance(dv, dict):
                rep.fail(group, "delivery version entry", "missing", "re-run stage print")
                continue
            shell = v["shell"]
            pose = dv.get("print_pose") or {}
            _eq(rep, group, "print pose pocket_floor_z_mm", pose.get("pocket_floor_z_mm"),
                shell["pocket_depth_mm"], 1e-6,
                "re-run stage print; it read a different shell.json")
            _eq(rep, group, "print pose print_thickness_mm", pose.get("print_thickness_mm"),
                shell["print_thickness_mm"], 1e-6,
                "re-run stage print; it read a different print manifest")
            _eq(rep, group, "print pose print_art_face_z_mm",
                pose.get("print_art_face_z_mm"), shell["top_gap_mm"], 1e-6,
                "re-run stage print; PRINT_NEST_Z_MM/top gap mismatch")
            _eq(rep, group, "print pose plate_outer_face_z_mm ~ 0",
                pose.get("plate_outer_face_z_mm"), 0.0, 1e-3,
                "re-run stage print")
            rep.add(group, "print pose supports_required is False",
                    pose.get("supports_required") is False,
                    f"{pose.get('supports_required')!r}",
                    "re-run stage print; the delivery orientation must not need supports")
            bed = (dv.get("bed_bbox_mm") or {}).get("size") or [0, 0, 0]
            bed_cfg = v["print"]["bed_mm"] or 220.0
            rep.add(group, "print bed fit <= bed_mm",
                    bed[0] <= bed_cfg + 1e-6 and bed[1] <= bed_cfg + 1e-6,
                    f"bed bbox {bed} vs bed {bed_cfg}",
                    "re-run stage print with a smaller layout or fix print.bed_mm "
                    "(print_layout BED_MM is hard-coded 220)")
            entries = dv.get("entries") or []
            expected = 2 + len(v["art"]["palette_bottom_up"]) + (1 if v["print"]["button"] == "part" else 0)
            rep.add(group, "delivered STL count", len(entries) == expected,
                    f"{len(entries)} vs {expected} (shell+plate+filaments"
                    f"{'+button' if v['print']['button'] == 'part' else ''})",
                    "re-run stage print; expected files per version changed")
            expected_names = {f"{vkey}_shell.stl", f"{vkey}_plate_recessed.stl"}
            for i, hx in enumerate(v["art"]["palette_bottom_up"], 1):
                expected_names.add(
                    f"{vkey}_print_filament_{i}_{norm_hex(hx).lstrip('#')}.stl")
            if v["print"]["button"] == "part":
                expected_names.add(f"{vkey}_button.stl")
            for name in sorted(expected_names):
                ctx.file(rep, group, stl_dir / name, "print")
            pd = ROOT / "render" / "print" / "appearance" / vkey
            for fname in ("manifest.json", "README.md", "layout.json", "PRINT_SHEET.png",
                          "print_iso.png", "print_top.png", "PRINT_READY.3mf"):
                ctx.file(rep, group, pd / fname, "print")
            got_entries = {str(e.get("file")) for e in entries}
            rep.add(group, "delivered STL names", got_entries == expected_names,
                    f"missing={sorted(expected_names - got_entries)[:4]}, "
                    f"extra={sorted(got_entries - expected_names)[:4]}",
                    "re-run stage print; delivered file set changed")
            layout_path = pd / "layout.json"
            if layout_path.is_file():
                try:
                    lay = load_json(layout_path)
                except Exception:  # noqa: BLE001
                    lay = {}
                bedsz = (lay.get("bed_bbox_mm") or {}).get("size") or [0, 0, 0]
                gap = lay.get("min_gap_mm")
                rep.add(group, "layout bed fit <= bed_mm & gaps>=5 mm",
                        bedsz[0] <= bed_cfg + 1e-6 and bedsz[1] <= bed_cfg + 1e-6
                        and isinstance(gap, (int, float)) and gap >= 5.0,
                        f"bed_bbox={bedsz}, min_gap={gap}",
                        "re-run stage print; the bed layout must fit the 220 mm bed with "
                        ">=5 mm part gaps (print_layout_appearance.py constants)")
        # checksums
        chk = stl_dir / "CHECKSUMS.sha256"
        if chk.is_file():
            bad = []
            for line in chk.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) != 2:
                    continue
                digest, name = parts[0], parts[1].lstrip("*")
                target = stl_dir / name
                if not target.is_file() or sha256_file(target) != digest:
                    bad.append(name)
            rep.add(tag, "flat STL CHECKSUMS.sha256 verifies", not bad,
                    f"bad/missing: {bad[:5]}", "re-run stage print")
    # no per-version stl subfolders left
    for vkey in resolved["versions"]:
        old = ROOT / "render" / "print" / "appearance" / vkey / "stl"
        rep.add(tag, f"no legacy per-version STL folder ({vkey})", not old.is_dir(),
                rel(old), "remove the stale folder; the flat render/print/stl is canonical")


def validate_acceptance(resolved: dict, rep: Report, ctx: ArtifactCtx) -> None:
    tag = "artifacts/acceptance"
    p = ctx.file(rep, tag, ROOT / "appearance" / "build" / "ACCEPTANCE.json", "acceptance")
    ctx.file(rep, tag, ROOT / "appearance" / "build" / "ACCEPTANCE.md", "acceptance")
    if not p:
        return
    try:
        acc = load_json(p)
    except Exception as exc:  # noqa: BLE001
        rep.fail(tag, "ACCEPTANCE.json parse", str(exc), "re-run stage acceptance")
        return
    total = acc.get("total")
    passed = acc.get("passed")
    failed = acc.get("failed")
    rep.add(tag, "acceptance passed == total", passed == total and failed == 0,
            f"{passed}/{total} passed, {failed} failed",
            "re-run stage acceptance; see appearance/build/ACCEPTANCE.md FAIL details")
    expect_checks = [v["expect"].get("acceptance_checks")
                     for v in resolved["versions"].values()
                     if v["expect"].get("acceptance_checks") is not None]
    if expect_checks:
        _eq(rep, tag, "acceptance total == expect.acceptance_checks", total,
            max(expect_checks), 0,
            "the Lead-owned acceptance check count changed; update "
            "versions.*.expect.acceptance_checks in appearance_project.yaml AND "
            "appearance/tools/acceptance_check.py only with Lead approval")
    rep.add(tag, "acceptance failures empty", not acc.get("failures"),
            f"{len(acc.get('failures') or [])} failure(s)",
            "see appearance/build/ACCEPTANCE.md")


VALIDATORS = {
    "art": validate_art,
    "convert": validate_convert,
    "shell": validate_shell,
    "render": validate_render,
    "print": validate_print,
    "acceptance": validate_acceptance,
}


# ---------------------------------------------------------------------------
# CLI / stage execution
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="One-command compile for the SmartCoaster appearance/print pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--config", default=str(DEFAULT_CONFIG),
                    help="project config (default: appearance/config/appearance_project.yaml)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate inputs/config/prerequisites only; write nothing")
    ap.add_argument("--only", default=None,
                    help="comma-separated stages to run, e.g. --only shell or "
                         "--only art,convert")
    ap.add_argument("--from", dest="from_stage", default=None,
                    help="run this stage and all following stages")
    ap.add_argument("--skip", default=None, help="comma-separated stages to skip")
    ap.add_argument("--no-acceptance", action="store_true",
                    help="do not run the Lead acceptance stage")
    ap.add_argument("--list", action="store_true", help="list stages and commands, then exit")
    ap.add_argument("--verbose", action="store_true", help="print every validation check")
    return ap.parse_args(argv)


def select_stages(args) -> tuple[list[str], str | None]:
    def split(value):
        return [s.strip() for s in (value or "").split(",") if s.strip()]

    only = split(args.only)
    skip = split(args.skip)
    for name in only + skip + ([args.from_stage] if args.from_stage else []):
        if name not in STAGES:
            return [], f"unknown stage {name!r}; valid stages: {', '.join(STAGES)}"
    if only and args.from_stage:
        return [], "--only and --from are mutually exclusive"
    if only:
        sel = set(only)
        plan = [s for s in STAGES if s in sel]
        dropped = sel - set(plan)
        if dropped:
            plan = []
        unknown = dropped
    elif args.from_stage:
        plan = STAGES[STAGES.index(args.from_stage):]
        unknown = set()
    else:
        plan = list(STAGES)
        unknown = set()
    plan = [s for s in plan if s not in set(skip)]
    if args.no_acceptance:
        plan = [s for s in plan if s != "acceptance"]
    if not plan:
        return [], "empty stage selection (after --only/--from/--skip/--no-acceptance)"
    return plan, None


def substitute(cmd: list[str], tools: dict, rep: Report, stage: str) -> list[str]:
    out = []
    for token in cmd:
        m = re.fullmatch(r"\{([a-z_]+)\}", token)
        if m:
            key = m.group(1)
            value = tools.get(key)
            if not value:
                rep.fail("stages", f"{stage}: command placeholder {token}",
                         "unresolved tool", f"set tools.{key} in appearance_project.yaml")
                out.append(token)
            else:
                out.append(value)
        else:
            out.append(token)
    return out


def stage_commands(stage: str, resolved: dict, rep: Report) -> list[list[str]]:
    entry = (resolved.get("stages") or {}).get(stage) or {}
    raw = entry.get("commands") or []
    cmds = [substitute([str(x) for x in cmd], resolved["tools"], rep, stage)
            for cmd in raw]
    if stage in ("art", "shell") and cmds:
        resolved_path = rel(ROOT / resolved["paths"]["compile_out"] / "resolved_config.json")
        cmds[-1] = cmds[-1] + ["--config", resolved_path]
    return cmds


def print_plan(resolved: dict, plan: list[str]) -> None:
    print("Stages (in pipeline order):")
    for i, stage in enumerate(STAGES):
        mark = "->" if stage in plan else "  "
        print(f" {mark} {i + 1}. {stage:<11} {STAGE_DESC[stage]}")
        if stage in plan:
            rep_dummy = Report()
            for cmd in stage_commands(stage, resolved, rep_dummy):
                print("        $ " + " ".join(cmd))


def run_command(cmd: list[str], env: dict, log_fh=None) -> tuple[int, float, list[str]]:
    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, env=env, bufsize=1)
    except OSError as exc:
        return 127, time.monotonic() - t0, [f"cannot start {cmd[0]!r}: {exc}"]
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        print("      " + line)
        if log_fh is not None:
            log_fh.write(line + "\n")
            log_fh.flush()
    rc = proc.wait()
    return rc, time.monotonic() - t0, lines


def write_reports(resolved: dict, rep: Report, plan: list[str], args,
                  stages_report: list[dict], total_seconds: float,
                  result: str, acceptance: dict | None) -> tuple[Path, Path]: 
    paths = resolved["paths"]
    summary = rep.summary()
    doc = {
        "schema": "smartcoaster.appearance.compile-report/v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": result,
        "dry_run": bool(args.dry_run),
        "config": {
            "path": resolved["source_config"],
            "sha256": resolved["source_config_sha256"],
        },
        "project": resolved.get("project") or {},
        "selection": {
            "plan": plan,
            "only": args.only, "from": args.from_stage,
            "skip": args.skip, "no_acceptance": bool(args.no_acceptance),
        },
        "derived": {
            vkey: {
                "art": {
                    "name": v["art"]["name"],
                    "image": v["art"]["image"],
                    "n_px": v["art"]["n_px"],
                    "art_diameter_mm": v["art"]["art_diameter_mm"],
                    "frame_mm": v["art"]["frame_mm"],
                    "palette_layers": len(v["art"]["palette_bottom_up"]),
                    "pixel_size_mm": v["art"]["pixel_size_mm"],
                    "layer_height_mm": v["art"]["layer_height_mm"],
                    "print_thickness_mm": v["art"]["print_thickness_mm"],
                },
                "shell": {
                    "plate_step": v["shell"]["plate_step"],
                    "mech_label": v["shell"]["mech_label"],
                    "rim_z_mm": v["shell"]["rim_z_mm"],
                    "pocket_dia_mm": v["shell"]["pocket_dia_mm"],
                    "print_dia_mm": v["shell"]["print_dia_mm"],
                    "interference_mm": v["shell"]["interference_mm"],
                    "top_gap_mm": v["shell"]["top_gap_mm"],
                    "pocket_depth_mm": v["shell"]["pocket_depth_mm"],
                    "floor_z_mm": v["shell"]["floor_z_mm"],
                    "print_top_z_mm": v["shell"]["print_top_z_mm"],
                },
                "print": v["print"],
            }
            for vkey, v in resolved["versions"].items()
        },
        "validation": {
            "summary": summary,
            "checks": rep.checks,
        },
        "stages": stages_report,
        "acceptance": acceptance,
        "total_seconds": round(total_seconds, 2),
        "limitations": [
            "Config-only inputs: art sheet image/crop, palette contents (same number of "
            "colours), tuning, output dirs, tool paths. Changing colour COUNT, layer "
            "height, rim/floor, pocket/print diameter, interference, top gap or bed is "
            "NOT config-only: the hard-coded stage constants and the Lead-owned "
            "acceptance baseline must be edited too (compile.py fails early with the "
            "exact file/constant).",
            "Changing version names or art NAMES is also not config-only: "
            "appearance/render/scene_common.py VERSIONS, appearance/render/config.json "
            "versions, appearance/kromacut/run_convert.sh art loop and the Lead-owned "
            "acceptance baseline are keyed on round/square + dog/elf.",
            "Acceptance (130/130) is Lead-owned/read-only for this task; compile.py only "
            "invokes it and reads ACCEPTANCE.json.",
            "Bambu Studio slicing/printing and physical print quality are still not "
            "verified (see appearance/PRINT_DELIVERY_SPEC.md).",
        ],
    }
    report_json = ROOT / paths["report_json"]
    report_md = ROOT / paths["report_md"]
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    lines = [
        "# appearance/ 一键编译报告（COMPILE_REPORT）",
        "",
        f"> 生成：{doc['generated_at']} · 结果：**{result}** · "
        f"{'DRY-RUN（未写入产物）' if args.dry_run else '真实编译'} · 总耗时 {total_seconds:.1f} s",
        f"> 配置：`{resolved['source_config']}` sha256 `{resolved['source_config_sha256'][:16]}…`",
        "",
        "## 1. 校验",
        "",
        f"- 检查项：**{summary['passed']}/{summary['total']} PASS**，"
        f"失败 {summary['failed']}，警告 {summary['warnings']}",
        "",
    ]
    groups = {}
    for c in rep.checks:
        g = groups.setdefault(c["group"], [0, 0, 0])
        if c["ok"]:
            g[0] += 1
        elif c["severity"] == "error":
            g[1] += 1
        else:
            g[2] += 1
    lines += ["| 分组 | PASS | FAIL | WARN |", "|---|---|---|---|"]
    for g, (ok, bad, warn) in sorted(groups.items()):
        lines.append(f"| {g} | {ok} | {bad} | {warn} |")
    if rep.failures():
        lines += ["", "### 失败明细（按提示修文件/常量后重跑）", ""]
        for c in rep.failures():
            lines.append(f"- **{c['group']} / {c['name']}**：{c['detail']}")
            if c["fix"]:
                lines.append(f"  - 处置：{c['fix']}")
    if rep.warnings():
        lines += ["", "### 警告", ""]
        for c in rep.warnings():
            lines.append(f"- {c['group']} / {c['name']}：{c['detail']}")

    lines += ["", "## 2. 派生输入（由唯一配置计算）", "",
              "| version | art | colours×layer | print t | rim | floor | depth | pocket/print Ø | interference | top gap |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for vkey, v in resolved["versions"].items():
        a = v["art"]
        s = v["shell"]
        lines.append(
            f"| {vkey} | {a['name']} | {len(a['palette_bottom_up'])} × "
            f"{a['layer_height_mm']:.2f} | {a['print_thickness_mm']:.2f} | "
            f"{s['rim_z_mm']:.2f} | {s['floor_z_mm']:.2f} | {s['pocket_depth_mm']:.2f} | "
            f"{s['pocket_dia_mm']:.1f}/{s['print_dia_mm']:.1f} | {s['interference_mm']:.2f} | "
            f"{s['top_gap_mm']:.2f} |")

    lines += ["", "## 3. 阶段", "",
              "| # | 阶段 | 状态 | 耗时 | 命令 |", "|---|---|---|---|---|"]
    for i, st in enumerate(stages_report, 1):
        cmd = "<br>".join("`" + " ".join(c) + "`" for c in st["commands"]) or "—"
        lines.append(f"| {i} | {st['name']} | {st['status']} | "
                     f"{st['seconds']:.1f} s | {cmd} |")
    lines.append(f"| — | **total** | | **{total_seconds:.1f} s** | |")

    if acceptance:
        lines += ["", "## 4. 验收（Lead 只读复核）", "",
                  f"- `appearance/build/ACCEPTANCE.json`："
                  f"**{acceptance.get('passed')}/{acceptance.get('total')} PASS**，"
                  f"failed {acceptance.get('failed')}"]
    lines += ["", "## 5. 诚实边界（不能靠改配置完成的输入）", ""]
    for note in doc["limitations"]:
        lines.append(f"- {note}")
    lines += ["", "## 6. 复跑", "", "```bash",
              "bash appearance/compile.sh                 # 全流程 + 验收",
              "bash appearance/compile.sh --dry-run       # 只校验，不写文件",
              "bash appearance/compile.sh --list          # 看阶段/命令",
              "```", ""]
    report_md.write_text("\n".join(lines), encoding="utf-8")
    return report_json, report_md


def print_validation(rep: Report, verbose: bool, header: str) -> None:
    print(header)
    if verbose:
        for c in rep.checks:
            if c["ok"]:
                print(f"  [PASS] {c['group']}: {c['name']}")
            else:
                print(f"  [{'WARN' if c['severity'] == 'warn' else 'FAIL'}] "
                      f"{c['group']}: {c['name']} - {c['detail']}")
                if c["fix"]:
                    print(f"         -> {c['fix']}")
    if rep.failures():
        print(f"  validation: {rep.summary()['passed']}/{len(rep.checks)} PASS, "
              f"{len(rep.failures())} FAILED")
        print("")
        for c in rep.failures():
            print(f"  FAIL {c['group']} / {c['name']}")
            print(f"       {c['detail']}")
            if c["fix"]:
                print(f"       -> {c['fix']}")
    else:
        s = rep.summary()
        extra = f", {s['warnings']} warning(s)" if s["warnings"] else ""
        print(f"  validation: {s['passed']}/{s['total']} checks passed{extra}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (ROOT / config_path)
    config_rel = rel(config_path)
    t_start = time.monotonic()

    # ---- --list needs no validation ------------------------------------ #
    if args.list:
        if not config_path.is_file():
            print(f"config not found: {config_rel}", file=sys.stderr)
            return 2
        try:
            resolved, rep = resolve_project(load_yaml(config_path), config_rel)
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if not resolved:
            print_validation(rep, True, "config is invalid:")
            return 2
        plan, err = select_stages(args)
        print_plan(resolved, plan if not err else STAGES)
        return 0

    if not config_path.is_file():
        print(f"compile.py: config not found: {config_rel}", file=sys.stderr)
        print(f"  expected: {rel(DEFAULT_CONFIG)}", file=sys.stderr)
        return 2

    # ---- static validation --------------------------------------------- #
    try:
        doc = load_yaml(config_path)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - YAML syntax errors
        print(f"compile.py: cannot parse {config_rel}: {exc}", file=sys.stderr)
        return 2

    resolved, rep = resolve_project(doc, config_rel)
    if resolved is None:
        print_validation(rep, args.verbose, "=== SmartCoaster appearance compile: config ===")
        print("\nRESULT: FAIL (config cannot be resolved; nothing was run/written)")
        return 2

    plan, err = select_stages(args)
    if err:
        print(f"compile.py: {err}", file=sys.stderr)
        return 2

    check_tools(resolved, rep)
    check_inputs(resolved, rep)
    check_stage_constants(resolved, rep)
    # artifact validators may report "pending" for stages in this plan
    ctx = ArtifactCtx(resolved, plan, mode="dry")
    for stage in plan:
        VALIDATORS[stage](resolved, rep, ctx)
    # dependencies that are NOT rebuilt must already be valid on disk
    deps: list[str] = []
    for stage in plan:
        for dep in REQUIRES[stage]:
            if dep not in plan and dep not in deps:
                deps.append(dep)
    for dep in deps:
        VALIDATORS[dep](resolved, rep, ArtifactCtx(resolved, plan, mode="post"))
    print_validation(rep, args.verbose,
                     "=== SmartCoaster appearance compile: validation ===")

    # ---- dry-run stops here (no writes) -------------------------------- #
    if args.dry_run:
        print("")
        print("plan: " + " -> ".join(plan))
        if rep.failures():
            print("RESULT: FAIL — dry-run made no changes; fix the items above and re-run.")
            return 2
        print(f"RESULT: PASS — dry-run only, no files written "
              f"({rep.summary()['passed']} checks).")
        return 0

    # ---- real run: abort before building a mismatched model ------------ #
    if rep.failures():
        report_json, report_md = write_reports(
            resolved, rep, plan, args, [], 0.0, "FAIL", None)
        print(f"report: {rel(report_md)} , {rel(report_json)}")
        print("RESULT: FAIL — validation failed; stages were NOT run (no mismatched model built).")
        return 2

    # ---- write resolved config + log, then run stages ------------------ #
    compile_out = ROOT / resolved["paths"]["compile_out"]
    compile_out.mkdir(parents=True, exist_ok=True)
    resolved_path = compile_out / "resolved_config.json"
    resolved_path.write_text(json.dumps(resolved, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    log_path = ROOT / resolved["paths"]["log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_path, "w", encoding="utf-8")
    log_fh.write(f"# SmartCoaster appearance compile log {datetime.now().isoformat()}\n")
    log_fh.write(f"# config: {config_rel} sha256 {resolved['source_config_sha256']}\n")
    log_fh.write(f"# plan: {', '.join(plan)}\n\n")
    log_fh.flush()

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["BLENDER"] = resolved["tools"].get("blender", env.get("BLENDER", ""))
    env["PY"] = resolved["tools"].get("python", "python3")
    env["NODE"] = resolved["tools"].get("node", "")
    env["KROMACUT_FLATPAINT"] = resolved["tools"].get("kromacut_cli", "")
    env["ART_DIR"] = str(ROOT / resolved["paths"]["art_out"])
    env["OUT_DIR"] = str(ROOT / resolved["paths"]["print_out"])

    stages_report: list[dict] = []
    acceptance_doc = None
    failed = False
    for idx, stage in enumerate(plan, 1):
        commands = stage_commands(stage, resolved, rep)
        print("")
        print(f"[{idx}/{len(plan)}] {stage} — {STAGE_DESC[stage]}")
        log_fh.write(f"\n===== [{idx}/{len(plan)}] {stage} =====\n")
        checks_start = len(rep.checks)
        any_failed = False
        stage_t0 = time.monotonic()
        for cmd in commands:
            print("    $ " + " ".join(cmd))
            log_fh.write("$ " + " ".join(cmd) + "\n")
            log_fh.flush()
            rc, secs, lines = run_command(cmd, env, log_fh)
            print(f"    -> exit {rc} in {secs:.1f} s")
            log_fh.write(f"-> exit {rc} in {secs:.1f} s\n")
            log_fh.flush()
            if rc != 0:
                any_failed = True
                tail = "\n".join("    " + x for x in lines[-8:])
                print("    --- last output ---")
                if tail:
                    print(tail)
                break
        stage_seconds = time.monotonic() - stage_t0
        if any_failed:
            failed = True
        else:
            # validate what this stage was supposed to produce
            ctx_post = ArtifactCtx(resolved, plan, mode="post")
            n_before = len(rep.failures())
            VALIDATORS[stage](resolved, rep, ctx_post)
            new_failures = rep.failures()[n_before:]
            if stage == "acceptance":
                try:
                    acceptance_doc = load_json(ROOT / "appearance/build/ACCEPTANCE.json")
                except Exception:  # noqa: BLE001
                    acceptance_doc = None
            if new_failures:
                failed = True
                print(f"    -> artifact validation FAILED ({len(new_failures)} check(s))")
                for c in new_failures[:8]:
                    print(f"       FAIL {c['group']}: {c['name']} - {c['detail']}")
                    if c["fix"]:
                        print(f"            -> {c['fix']}")
        stage_checks = rep.checks[checks_start:]
        stage_failures = [c for c in stage_checks
                          if not c["ok"] and c["severity"] == "error"]
        stage_failed = any_failed or bool(stage_failures)
        stages_report.append({
            "name": stage,
            "status": "failed" if stage_failed else "ok",
            "commands": commands,
            "seconds": round(stage_seconds, 2),
            "checks": len(stage_checks),
            "failures": stage_failures,
        })
        if stage_failed:
            failed = True
            print(f"    stage {stage}: FAILED")
            break
        print(f"    stage {stage}: OK in {stage_seconds:.1f} s")

    total_seconds = time.monotonic() - t_start
    result = "PASS" if not failed else "FAIL"
    report_json, report_md = write_reports(
        resolved, rep, plan, args, stages_report, total_seconds, result, acceptance_doc)
    log_fh.write(f"\nRESULT: {result} total {total_seconds:.1f} s\n")
    log_fh.close()

    print("")
    print("=== summary ===")
    for st in stages_report:
        print(f"  {st['name']:<11} {st['status']:<7} {st['seconds']:>7.1f} s")
    if acceptance_doc:
        print(f"  acceptance: {acceptance_doc.get('passed')}/{acceptance_doc.get('total')} "
              f"PASS ({acceptance_doc.get('failed')} failed)")
    print(f"  total: {total_seconds:.1f} s")
    print(f"  report: {rel(report_md)} , {rel(report_json)}")
    print(f"  log:    {rel(log_path)}")
    print(f"RESULT: {result}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
