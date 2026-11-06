#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_system.py — validate the reusable agent system spec.

Checks (exit non-zero on any failure):
  1. SYSTEM.yaml parses (PyYAML; JSON fallback if YAML is unavailable).
  2. Required top-level sections exist.
  3. Every role / workflow / gate / template file exists (no dangling references).
  4. Stage <-> workflow <-> domain references are consistent and bidirectional.
  5. Stage -> gate references exist; gate registry files exist, parse, and declare
     the same gate_id / stage list.
  6. Stage artifact references exist in artifacts.types.
  7. Every gates/*.yaml has unique check ids and a valid status/severity.
  8. Every .md file under the system has no dangling relative links.
  9. Toolchain entries have id/version/location/license.
 10. maturity.verified / maturity.not_verified are non-empty and well-formed.
 11. (optional) Evidence files referenced by --evidence-mode exist in the source
     workspace; default is warn-only so the folder stays portable.

Usage:
    python3 agent-system/scripts/check_system.py
    python3 agent-system/scripts/check_system.py --strict-evidence
    python3 agent-system/scripts/check_system.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEM_DIR = HERE.parent
SPEC = SYSTEM_DIR / "SYSTEM.yaml"

REQUIRED_TOP = [
    "schema", "system", "roles", "domains", "stages", "workflows",
    "gates", "artifacts", "templates", "toolchain", "constraints",
    "decision_rules", "write_scopes", "maturity", "instantiation",
]
VALID_STATUS = {"pass", "partial", "fail", "not_run", "provisional"}
VALID_SEVERITY = {"blocker", "major", "minor", "finding", "provisional"}


def load_spec():
    text = SPEC.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - environment dependent
        # Minimal YAML fallback: a JSON companion is required in that case.
        companion = SYSTEM_DIR / "SYSTEM.json"
        if not companion.exists():
            raise SystemExit(
                "ERROR: PyYAML unavailable and no SYSTEM.json companion. "
                "Install PyYAML or generate the JSON companion."
            )
        print("WARN: PyYAML unavailable -> validated SYSTEM.json companion only")
        return json.loads(companion.read_text(encoding="utf-8"))
    return yaml.safe_load(text)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(SYSTEM_DIR))
    except ValueError:
        return str(path)


def md_links(md: Path):
    """Yield (line, target) for relative markdown links; skip http/anchor/code-ish."""
    text = md.read_text(encoding="utf-8", errors="replace")
    # strip fenced code blocks so examples don't produce false positives
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    for i, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", line):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = target.split("#", 1)[0].strip()
            if not target:
                continue
            yield i, target


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the agent-system spec.")
    ap.add_argument("--strict-evidence", action="store_true",
                    help="fail if a evidence path in maturity.verified is missing")
    ap.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, int] = {}

    # 1. parse ---------------------------------------------------------------
    try:
        spec = load_spec()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: cannot parse {rel(SPEC)}: {exc}")
        return 2
    if not isinstance(spec, dict):
        print("FAIL: SYSTEM.yaml root is not a mapping")
        return 2

    # 2. required top-level --------------------------------------------------
    for key in REQUIRED_TOP:
        if key not in spec:
            errors.append(f"missing top-level section: {key}")
    if spec.get("schema") != "dsh-hardware-agent-system/1":
        errors.append(f"unexpected schema: {spec.get('schema')!r}")

    roles = spec.get("roles", [])
    domains = spec.get("domains", [])
    stages = spec.get("stages", [])
    workflows = spec.get("workflows", [])
    gates = spec.get("gates", [])
    templates = spec.get("templates", [])
    artifacts = spec.get("artifacts", {})
    stats.update(roles=len(roles), domains=len(domains), stages=len(stages),
                 workflows=len(workflows), gates=len(gates),
                 templates=len(templates))

    role_ids = {r.get("id") for r in roles}
    domain_ids = {d.get("id") for d in domains}
    stage_ids = [s.get("id") for s in stages]
    stage_by_id = {s.get("id"): s for s in stages}
    workflow_ids = {w.get("id") for w in workflows}
    gate_ids = {g.get("id") for g in gates}
    artifact_ids = {a.get("id") for a in artifacts.get("types", [])}

    # 3. file existence ------------------------------------------------------
    def must_exist(relpath: str, label: str):
        p = SYSTEM_DIR / relpath
        if not p.exists():
            errors.append(f"{label}: missing file {relpath}")
        return p

    for r in roles:
        if not r.get("file"):
            errors.append(f"role {r.get('id')} has no file")
        else:
            must_exist(r["file"], f"role {r.get('id')}")
    for w in workflows:
        must_exist(w.get("file", ""), f"workflow {w.get('id')}")
    for g in gates:
        must_exist(g.get("file", ""), f"gate {g.get('id')}")
    for t in templates:
        must_exist(t.get("file", ""), f"template {t.get('id')}")
    must_exist(artifacts.get("contracts", ""), "artifacts.contracts")
    must_exist(spec.get("instantiation", {}).get("checklist", ""), "instantiation.checklist")
    must_exist(spec.get("instantiation", {}).get("evidence_mapping", ""), "instantiation.evidence_mapping")
    must_exist(spec.get("instantiation", {}).get("scaffold_script", ""), "instantiation.scaffold_script")

    # 4. domain / workflow / stage consistency -------------------------------
    if len(set(stage_ids)) != len(stage_ids):
        errors.append("duplicate stage ids in SYSTEM.yaml")
    for d in domains:
        for sid in d.get("stages", []):
            if sid not in stage_by_id:
                errors.append(f"domain {d.get('id')} references unknown stage {sid}")
            elif stage_by_id[sid].get("domain") != d.get("id"):
                errors.append(f"stage {sid} domain != domain entry {d.get('id')}")
    for w in workflows:
        for sid in w.get("stages", []):
            if sid not in stage_by_id:
                errors.append(f"workflow {w.get('id')} references unknown stage {sid}")
            elif stage_by_id[sid].get("workflow") != w.get("id"):
                errors.append(f"stage {sid} workflow != workflow entry {w.get('id')}")
    for s in stages:
        if s.get("domain") not in domain_ids:
            errors.append(f"stage {s.get('id')} unknown domain {s.get('domain')!r}")
        if s.get("workflow") not in workflow_ids:
            errors.append(f"stage {s.get('id')} unknown workflow {s.get('workflow')!r}")
    covered = {sid for d in domains for sid in d.get("stages", [])}
    for sid in stage_ids:
        if sid not in covered:
            errors.append(f"stage {sid} not listed in any domain")

    # 5. gates ---------------------------------------------------------------
    gate_stage_map: dict[str, set] = {}
    all_check_ids: set[str] = set()
    total_checks = 0
    for g in gates:
        gid = g.get("id")
        path = SYSTEM_DIR / g.get("file", "")
        if not path.exists():
            continue
        try:
            import yaml  # type: ignore
            gdoc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"gate {gid}: cannot parse {g.get('file')}: {exc}")
            continue
        if not isinstance(gdoc, dict):
            errors.append(f"gate {gid}: {g.get('file')} root is not a mapping")
            continue
        if gdoc.get("gate_id") != gid:
            errors.append(f"gate {gid}: file declares gate_id={gdoc.get('gate_id')!r}")
        gstages = set(gdoc.get("stages", []))
        gate_stage_map[gid] = gstages
        if gstages != set(g.get("stages", [])):
            errors.append(f"gate {gid}: registry stages {g.get('stages')} != file stages {sorted(gstages)}")
        for sid in gstages:
            if sid not in stage_by_id:
                errors.append(f"gate {gid}: unknown stage {sid}")
            elif gid not in stage_by_id[sid].get("gates", []):
                errors.append(f"stage {sid} does not reference gate {gid}")
        checks = gdoc.get("checks", [])
        if not checks:
            errors.append(f"gate {gid}: no checks")
        stats[f"checks_{gid}"] = len(checks)
        total_checks += len(checks)
        for c in checks:
            cid = c.get("id")
            if not cid:
                errors.append(f"gate {gid}: check without id")
                continue
            if cid in all_check_ids:
                errors.append(f"duplicate check id {cid} (gate {gid})")
            all_check_ids.add(cid)
            if not c.get("criterion"):
                errors.append(f"check {cid}: missing criterion")
            if not c.get("evidence") and not c.get("detail"):
                # evidence may be implied by the gate-level `evidence`; warn only
                pass
            if c.get("severity") not in VALID_SEVERITY:
                errors.append(f"check {cid}: bad severity {c.get('severity')!r}")
            if c.get("status") not in VALID_STATUS:
                errors.append(f"check {cid}: bad status {c.get('status')!r}")
    stats["total_checks"] = total_checks
    for s in stages:
        for gid in s.get("gates", []):
            if gid not in gate_ids:
                errors.append(f"stage {s.get('id')} references unknown gate {gid}")
            elif s.get("id") not in gate_stage_map.get(gid, set()):
                errors.append(f"stage {s.get('id')} references gate {gid} which does not list it")

    # 6. artifact references -------------------------------------------------
    for s in stages:
        for aid in s.get("artifacts", []):
            if aid not in artifact_ids:
                errors.append(f"stage {s.get('id')} references unknown artifact {aid}")
    for aid in (a.get("id") for a in artifacts.get("types", [])):
        if not aid:
            errors.append("artifact type without id")
    if not artifacts.get("types"):
        errors.append("artifacts.types is empty")

    # 7. templates -----------------------------------------------------------
    for t in templates:
        if not t.get("output"):
            errors.append(f"template {t.get('id')}: missing output")
        if t.get("used_by") and not (SYSTEM_DIR / t["used_by"]).exists():
            errors.append(f"template {t.get('id')}: used_by {t['used_by']} missing")

    # 8. toolchain -----------------------------------------------------------
    for tool in spec.get("toolchain", []):
        for key in ("id", "version", "location", "license"):
            if not tool.get(key):
                errors.append(f"toolchain {tool.get('id')}: missing {key}")

    # 9. maturity ------------------------------------------------------------
    mat = spec.get("maturity", {})
    verified, not_verified = mat.get("verified", []), mat.get("not_verified", [])
    if not verified:
        errors.append("maturity.verified is empty")
    if not not_verified:
        errors.append("maturity.not_verified is empty (honesty rule requires gaps)")
    stats["verified_claims"] = len(verified)
    stats["not_verified_claims"] = len(not_verified)
    for item in verified + not_verified:
        if not item.get("id") or not item.get("claim"):
            errors.append(f"maturity item malformed: {item!r}")
    src = spec.get("system", {}).get("source_workspace", "")
    for item in verified:
        ev = item.get("evidence")
        if ev and "://" not in ev:
            p = (SYSTEM_DIR.parent / ev) if (SYSTEM_DIR.parent / ev).exists() else None
            if p is None and args.strict_evidence:
                errors.append(f"maturity {item.get('id')}: evidence missing {ev}")
            elif p is None:
                warnings.append(f"maturity {item.get('id')}: evidence not found relative to source: {ev}")

    # 10. markdown link check ------------------------------------------------
    md_files = sorted(SYSTEM_DIR.glob("**/*.md"))
    stats["markdown_files"] = len(md_files)
    for md in md_files:
        for line, target in md_links(md):
            if target.startswith(("static/", "assets/")) and not (md.parent / target).exists():
                errors.append(f"{rel(md)}:{line}: dangling link {target}")
                continue
            # external-to-system paths (../) resolve against the repo root
            base = md.parent
            ok = (base / target).exists() or (SYSTEM_DIR.parent / target).exists()
            if not ok:
                errors.append(f"{rel(md)}:{line}: dangling link {target}")

    # 11. scenarios / write scopes ------------------------------------------
    ws = spec.get("write_scopes", [])
    if not ws:
        errors.append("write_scopes is empty")
    for item in ws:
        if not item.get("id") or not item.get("owner"):
            errors.append(f"write_scope malformed: {item!r}")
        owner = item.get("owner")
        if owner not in role_ids and owner != "integration":
            errors.append(f"write_scope {item.get('id')}: unknown owner {owner!r}")

    # report -----------------------------------------------------------------
    if args.json:
        print(json.dumps({
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }, indent=2, ensure_ascii=False))
    else:
        print("agent-system check")
        print(f"  spec           : {rel(SPEC)}")
        print(f"  roles          : {stats['roles']}")
        print(f"  domains        : {stats['domains']}")
        print(f"  stages         : {stats['stages']}")
        print(f"  workflows      : {stats['workflows']}")
        print(f"  gate groups    : {stats['gates']}  (checks: {stats['total_checks']})")
        print(f"  templates      : {stats['templates']}")
        print(f"  markdown files : {stats['markdown_files']}")
        print(f"  verified claims: {stats['verified_claims']}")
        print(f"  not verified   : {stats['not_verified_claims']}")
        if warnings:
            print("\nWARNINGS")
            for w in warnings:
                print(f"  - {w}")
        if errors:
            print("\nFAILURES")
            for e in errors:
                print(f"  ✗ {e}")
            print(f"\nRESULT: FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        else:
            print(f"\nRESULT: PASS ({len(warnings)} warning(s))")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
