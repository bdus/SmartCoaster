#!/usr/bin/env python3
"""One-command orchestrator for the Lumina-Layers appearance line.

Stages (each one is also runnable on its own; this script only orders them and
validates before spending time):

    A1 art      appearance/tools/make_art_lumina.py
    A2 print    appearance/lumina/lumina_convert.py          (Lumina venv, python3.12)
    A3 shell    appearance/cad/run_shell.sh --config config/lumina_project.yaml
    A4 render   appearance/render/build_scene.py              (Blender)
    A5 3mf      appearance/render/make_3mf.py
    A6 post     appearance/render/postprocess.py
    A7 print    render/print/appearance/run_print_stage.sh
    A8 checks   appearance/tools/acceptance_check_lumina.py

Writes: appearance/build/COMPILE_LUMINA_REPORT.{json,md}, appearance/build/compile_lumina.log

    python3 appearance/tools/compile_lumina.py --dry-run   # validate inputs/config/tools, no writes
    python3 appearance/tools/compile_lumina.py             # full run (~10-12 min)
    python3 appearance/tools/compile_lumina.py --from A4   # resume from a stage
    python3 appearance/tools/compile_lumina.py --only A2   # run a single stage

Exit code 0 only if every executed stage succeeded AND the acceptance gate passes
(at the end of a full run).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LUMINA = "/data/Documents/tools/Lumina-Layers"
PY312 = "/data/Documents/tools/python312/bin/python3.12"
VENV_PY = os.path.join(LUMINA, ".venv", "bin", "python")
BLENDER = os.environ.get("BLENDER", "/data/Documents/tools/blender/blender")
PY = os.environ.get("PY", sys.executable)
CONFIG = os.path.join(ROOT, "appearance", "config", "lumina_project.yaml")
# vector-exported print for the square version (user-authored in the Lumina GUI)
VECTOR_3MF = os.path.join(ROOT, "appearance", "src", "art",
                          "tmprarihgxw_Lumina_Vector_4C_20261108_131917.3mf")
REPORT_JSON = os.path.join(ROOT, "appearance", "build", "COMPILE_LUMINA_REPORT.json")
REPORT_MD = os.path.join(ROOT, "appearance", "build", "COMPILE_LUMINA_REPORT.md")
LOG = os.path.join(ROOT, "appearance", "build", "compile_lumina.log")

# contract constants shared by the stage scripts (validated here, not assumed)
CONTRACT = {
    "pixel_grid": 864,
    "pixel_mm": 0.10,
    "frame_mm": 86.4,
    "print_thickness_mm": 1.20,      # round (raster); square is 1.605 (vector)
    "layer_mm": 0.08,
    "total_layers": 15,
    "color_layers": 5,
    "pocket_dia_mm": 86.0,
    "print_dia_mm": 86.2,
    "top_gap_mm": 0.0,
    # square print is the imported vector 3MF (1.605 mm) -> floor 18.0 - 1.605
    "floors": {"round": 15.80, "square": 16.395},
    "rims": {"round": 17.0, "square": 18.0},
    "filaments": 4,
    "lut": "lut-preset/Custom/lumina_lut.json",
    "color_mode": "4-Color (RYBW)",
    "printer": "bambu-h2d",
    "device_profile": "BambuStudio:bbl:bambu-lab-h2d:0.4",
    "slot_hex": ["#FFFFFF", "#DC143C", "#FFE600", "#0064F0"],
    "color_budget": 5,
}

STAGES = ["A1", "A2", "A2V", "A3", "A4", "A5", "A6", "A7", "A8"]
TITLES = {
    "A1": "art split (864 px RGBA / alpha circle)",
    "A2": "Lumina headless conversion (raster) -> dog print STLs + manifest",
    "A2V": "Lumina VECTOR 3MF import -> elf print STLs + manifest",
    "A3": "recessed shell plates (pocket 86.0 x 1.20)",
    "A4": "Blender assembly renders (hero/top/macro/print_top/section)",
    "A5": "assembled Bambu 3MF + validation",
    "A6": "postprocess (captions/section/board)",
    "A7": "3D-print delivery (baked STLs/3MF/sheets/checksums)",
    "A8": "Lead independent acceptance",
}


def rel(p):
    try:
        return os.path.relpath(p, ROOT)
    except ValueError:
        return p


def run(cmd, log, env=None, timeout=3600):
    t0 = time.time()
    line = " ".join(cmd)
    log.append({"cmd": line, "start": time.strftime("%Y-%m-%dT%H:%M:%S")})
    e = dict(os.environ)
    e.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    # Lumina's numba @njit(cache=True) needs a writable cache dir (checkout is read-only)
    e.setdefault("NUMBA_CACHE_DIR",
                 os.path.join(ROOT, ".lumina_runtime", "numba_cache"))
    os.makedirs(e["NUMBA_CACHE_DIR"], exist_ok=True)
    if env:
        e.update(env)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write("\n$ %s\n" % line)
        fh.flush()
        p = subprocess.run(cmd, cwd=ROOT, env=e, stdout=fh, stderr=subprocess.STDOUT,
                           timeout=timeout)
    ok = p.returncode == 0
    log[-1].update({"rc": p.returncode, "ok": ok,
                    "seconds": round(time.time() - t0, 1)})
    return ok


def load_yaml(path):
    try:
        import yaml
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except ImportError:
        sys.path.append("/usr/lib/python3/dist-packages")
        import yaml
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)


# --------------------------------------------------------------------------- #
# validations (same spirit as the old compile.py: fail before building)
# --------------------------------------------------------------------------- #
def validate(cfg):
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    # tools
    add("tool.python312", os.path.exists(PY312), PY312)
    add("tool.venv_python", os.path.exists(VENV_PY), VENV_PY)
    add("tool.lumina_repo", os.path.isdir(os.path.join(LUMINA, "core")), LUMINA)
    add("tool.blender", os.path.exists(BLENDER), BLENDER)
    add("tool.build123d_venv",
        os.path.exists(os.path.join(ROOT, "mechanical", "square_v1", ".venv", "bin",
                                    "python")),
        "mechanical/square_v1/.venv (build123d 0.10)")
    add("config.exists", os.path.exists(CONFIG), rel(CONFIG))
    if not os.path.exists(CONFIG):
        return checks

    # config vs contract
    engine = cfg.get("engine") or {}
    add("config.layer_mm", abs(float(engine.get("layer_height_mm")) - CONTRACT["layer_mm"])
        < 1e-9, engine.get("layer_height_mm"))
    add("config.pixel_mm", abs(float(engine.get("pixel_size_mm")) - CONTRACT["pixel_mm"])
        < 1e-9, engine.get("pixel_size_mm"))
    pr = cfg.get("print") or {}
    add("config.print_thickness",
        abs(float(pr.get("print_thickness_mm")) - CONTRACT["print_thickness_mm"]) < 1e-6,
        pr.get("print_thickness_mm"))
    add("config.color_layers", int(pr.get("color_layers")) == CONTRACT["color_layers"],
        pr.get("color_layers"))
    add("config.total_layers", int(pr.get("total_layers")) == CONTRACT["total_layers"],
        pr.get("total_layers"))
    add("config.lut", str(pr.get("lut")) == CONTRACT["lut"], pr.get("lut"))
    add("config.lut_file", os.path.exists(os.path.join(LUMINA, CONTRACT["lut"])),
        CONTRACT["lut"])
    inv = (pr.get("spool_inventory") or {})
    add("config.spool_inventory", len(inv) == 6, sorted(inv))
    add("config.color_mode", "RYBW" in str(pr.get("color_mode")), pr.get("color_mode"))
    add("config.printer", str(pr.get("printer_id")) == CONTRACT["printer"],
        pr.get("printer_id"))
    add("config.device_profile",
        str(pr.get("device_profile_id")) == CONTRACT["device_profile"],
        pr.get("device_profile_id"))
    add("config.slot_hex",
        [str(x).upper() for x in (pr.get("slot_hex") or [])] ==
        [x.upper() for x in CONTRACT["slot_hex"]], pr.get("slot_hex"))
    add("config.color_budget",
        int(pr.get("color_budget") or 0) == CONTRACT["color_budget"],
        "%d = 4 print + 1 shell (H2D)" % CONTRACT["color_budget"])
    add("config.structure_single", "Single" in str(pr.get("structure_mode")),
        pr.get("structure_mode"))
    add("config.thickness_formula",
        abs((int(pr.get("color_layers")) +
             round(float(pr.get("spacer_thick_mm")) / CONTRACT["layer_mm"]))
            * CONTRACT["layer_mm"] - CONTRACT["print_thickness_mm"]) < 1e-6,
        "(color_layers + round(spacer/0.08)) * 0.08")
    art = cfg.get("art") or {}
    add("config.frame_mm", abs(float(art.get("frame_mm")) - CONTRACT["frame_mm"]) < 1e-6,
        art.get("frame_mm"))
    add("config.pixel_grid", int(art.get("pixel_grid")) == CONTRACT["pixel_grid"],
        art.get("pixel_grid"))
    add("vector.3mf", os.path.exists(VECTOR_3MF), rel(VECTOR_3MF) if os.path.exists(VECTOR_3MF)
        else VECTOR_3MF)
    add("vector.face_texture",
        os.path.exists(os.path.join(ROOT, "appearance", "src", "vectorized.svg")),
        "appearance/src/vectorized.svg")
    sq_art = ((cfg.get("versions") or {}).get("square") or {}).get("art") or {}
    add("vector.square_source", str(sq_art.get("source")) == "vector_3mf",
        sq_art.get("source"))
    add("vector.square_3mf_config", str(sq_art.get("source_3mf")) != "None",
        sq_art.get("source_3mf"))
    add("vector.importer",
        os.path.exists(os.path.join(ROOT, "appearance", "lumina",
                                    "import_vector_3mf.py")), "import_vector_3mf.py")
    versions = cfg.get("versions") or {}
    for v in ("round", "square"):
        sh = (versions.get(v) or {}).get("shell") or {}
        add("config.%s.pocket" % v,
            abs(float(sh.get("pocket_dia_mm")) - CONTRACT["pocket_dia_mm"]) < 1e-9,
            sh.get("pocket_dia_mm"))
        add("config.%s.print_dia" % v,
            abs(float(sh.get("print_dia_mm")) - CONTRACT["print_dia_mm"]) < 1e-6,
            sh.get("print_dia_mm"))
        add("config.%s.top_gap" % v,
            abs(float(sh.get("top_gap_mm")) - CONTRACT["top_gap_mm"]) < 1e-9,
            sh.get("top_gap_mm"))
        want_t = CONTRACT["print_thickness_mm"] if v == "round" else 1.605
        add("config.%s.thickness" % v,
            abs(float(sh.get("print_thickness_mm")) - want_t) < 1e-6,
            "%s (expected %.3f)" % (sh.get("print_thickness_mm"), want_t))
        add("config.%s.rim" % v,
            abs(float(sh.get("rim_z_mm")) - CONTRACT["rims"][v]) < 1e-9,
            sh.get("rim_z_mm"))
        add("config.%s.floor" % v,
            abs((float(sh.get("rim_z_mm")) - float(sh.get("print_thickness_mm")))
                - CONTRACT["floors"][v]) < 1e-6,
            "rim - thickness = %.3f (expected %.3f)"
            % (float(sh.get("rim_z_mm")) - float(sh.get("print_thickness_mm")),
               CONTRACT["floors"][v]))
        add("config.%s.plate_step" % v,
            os.path.exists(os.path.join(ROOT, str(sh.get("plate_step")))),
            sh.get("plate_step"))
    # cross-check: driver PARAMS + render config + print-layout constants
    drv = open(os.path.join(ROOT, "appearance", "lumina", "lumina_convert.py"),
               encoding="utf-8").read()
    add("driver.pixel_mm", "PIXEL_MM = 0.10" in drv, "PIXEL_MM = 0.10")
    add("driver.layer_mm", "LAYER_MM = 0.08" in drv, "LAYER_MM = 0.08")
    add("driver.expected_thickness", "1.20" in drv, "default --expect-thickness 1.20")
    add("driver.lut", "lumina_lut.json" in drv, "self-describing RYBW JSON LUT pinned")
    add("driver.printer", 'PRINTER_ID = "bambu-h2d"' in drv, "H2D pinned")
    add("driver.slot_hex", '"Red": "#DC143C"' in drv, "RYBW slot hexes pinned")
    lay = open(os.path.join(ROOT, "render", "print", "appearance",
                            "print_layout_appearance.py"), encoding="utf-8").read()
    add("layout.nest_zero", "PRINT_NEST_Z_MM = 0.00" in lay, "art face on the bed")
    rcfg = json.load(open(os.path.join(ROOT, "appearance", "render", "config.json"),
                          encoding="utf-8"))
    add("render.top_gap", abs(float(rcfg["print"]["top_gap_mm"])) < 1e-9,
        rcfg["print"]["top_gap_mm"])
    add("render.palette_rybw",
        rcfg["print"]["fallback_palette"]["dog"][1].upper() == "#DC143C",
        rcfg["print"]["fallback_palette"]["dog"])
    return checks


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="run a single stage (A1..A8)")
    ap.add_argument("--from", dest="from_stage", default=None)
    ap.add_argument("--skip-acceptance", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    cfg = load_yaml(CONFIG) if os.path.exists(CONFIG) else {}
    vals = validate(cfg)
    bad = [c for c in vals if not c["ok"]]
    print("== validation: %d/%d PASS ==" % (len(vals) - len(bad), len(vals)))
    for c in bad:
        print("  FAIL", c["name"], "|", c["detail"])
    if bad:
        print("compile_lumina: aborting before building (fix the FAILs above)")
        return 2

    if args.dry_run:
        rep = {"schema": "smartcoaster.appearance.compile_lumina/v1",
               "mode": "dry-run",
               "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "validations": vals,
               "stages": [], "ok": True}
        json.dump(rep, open(REPORT_JSON, "w", encoding="utf-8"), indent=2,
                  ensure_ascii=False)
        open(REPORT_MD, "w", encoding="utf-8").write(
            "# compile_lumina dry-run\n\n> %s · 校验 %d/%d PASS，未写入任何产物。\n"
            % (rep["generated"], len(vals), len(vals)))
        print("dry-run OK: %d validations, nothing written except the report" % len(vals))
        return 0

    cmds = {
        "A1": [PY, "appearance/tools/make_art_lumina.py"],
        "A2": [VENV_PY, "appearance/lumina/lumina_convert.py", "--art", "dog"],
        "A2V": [VENV_PY, "appearance/lumina/import_vector_3mf.py",
                "--art", "elf", "--three-mf", VECTOR_3MF,
                "--target-diameter-mm", "86.2",
                "--face-texture", "appearance/src/vectorized.svg"],
        "A3": ["bash", "appearance/cad/run_shell.sh", "--config", CONFIG, "--skip-blender"],
        "A4": [BLENDER, "-b", "--python", "appearance/render/build_scene.py"],
        "A5": [PY, "appearance/render/make_3mf.py"],
        "A6": [PY, "appearance/render/postprocess.py"],
        "A7": ["bash", "render/print/appearance/run_print_stage.sh"],
        "A8": [PY, "appearance/tools/acceptance_check_lumina.py"],
    }
    stages = STAGES[:]
    if args.only:
        stages = [args.only.upper()]
    elif args.from_stage:
        start = STAGES.index(args.from_stage.upper())
        stages = STAGES[start:]
    if args.skip_acceptance and "A8" in stages:
        stages.remove("A8")

    log = []
    ok_all = True
    for s in stages:
        print("== %s %-58s ==" % (s, TITLES[s]), flush=True)
        ok = run(cmds[s], log)
        print("   -> %s (%.1fs)" % ("OK" if ok else "FAIL", log[-1]["seconds"]), flush=True)
        if not ok:
            ok_all = False
            print("compile_lumina: stage %s failed; see %s" % (s, rel(LOG)))
            break

    rep = {"schema": "smartcoaster.appearance.compile_lumina/v1",
           "mode": "full",
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "validations": vals,
           "validations_summary": "%d/%d" % (len(vals), len(vals)),
           "stages": log,
           "ok": ok_all,
           "report": rel(REPORT_JSON),
           "log": rel(LOG)}
    json.dump(rep, open(REPORT_JSON, "w", encoding="utf-8"), indent=2,
              ensure_ascii=False)
    md = ["# compile_lumina — one-command build report", "",
          "> %s · 校验 %s · 结论 **%s**" % (rep["generated"],
                                          rep["validations_summary"],
                                          "PASS" if ok_all else "FAIL"),
          "", "| 阶段 | 内容 | 耗时 | 结果 |", "|---|---|---|---|"]
    for st in log:
        md.append("| %s | %s | %.1fs | %s |" % (
            st["cmd"], "", st["seconds"], "OK" if st["ok"] else "FAIL"))
    md += ["", "日志：`%s`" % rel(LOG), ""]
    open(REPORT_MD, "w", encoding="utf-8").write("\n".join(md))
    print("== compile_lumina: %s ==" % ("ALL OK" if ok_all else "FAILED"))
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
