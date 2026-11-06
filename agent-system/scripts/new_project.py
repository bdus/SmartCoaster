#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new_project.py — scaffold a new hardware project from the reusable agent system.

Creates a project skeleton from agent-system/templates:
    AGENTS.md, README.md, requirements.yaml, TASK_BOARD.md,
    docs/01_AI_Hardware_Engineering_Pipeline.md, docs/02_PRD.md,
    docs/gate-run.md, docs/HANDOFF.md,
    config/mechanical_params.yaml, scripts/acceptance_check.py
plus the standard directory layout (mechanical / electronics / firmware /
simulation / tests / render / packaging / build).

Templates use ``{{TOKEN}}`` placeholders; the scaffold substitutes:
    PROJECT_NAME, PROJECT_SLUG, PROJECT_TITLE, DOMAIN, DATE, SYSTEM_ID,
    SYSTEM_VERSION, ROOT_NAME.

Examples
--------
    python3 agent-system/scripts/new_project.py demo-coaster --dry-run
    python3 agent-system/scripts/new_project.py demo-coaster --root /tmp/demo-coaster
    python3 agent-system/scripts/new_project.py demo-coaster --root /tmp/x --force
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEM_DIR = HERE.parent

# Fallback mapping if PyYAML / SYSTEM.yaml is unavailable.
FALLBACK_MAP = {
    "templates/AGENTS.md.tmpl": "AGENTS.md",
    "templates/HANDOFF.md.tmpl": "docs/HANDOFF.md",
    "templates/requirements.yaml.tmpl": "requirements.yaml",
    "templates/task-board.md.tmpl": "TASK_BOARD.md",
    "templates/acceptance_check.py.tmpl": "scripts/acceptance_check.py",
    "templates/PRD-outline.md.tmpl": "docs/02_PRD.md",
    "templates/repo-layout.md.tmpl": "docs/01_AI_Hardware_Engineering_Pipeline.md",
    "templates/gate-run.md.tmpl": "docs/gate-run.md",
    "templates/config-mechanical_params.yaml.tmpl": "config/mechanical_params.yaml",
}

DIRECTORIES = [
    "config", "docs", "docs/design",
    "mechanical", "mechanical/src", "mechanical/build",
    "electronics", "electronics/schematic", "electronics/pcb", "electronics/build",
    "firmware", "firmware/esp32", "firmware/model",
    "simulation", "simulation/mechanical", "simulation/electronics",
    "tests", "tests/firmware", "tests/handboard",
    "render", "packaging", "scripts", "build", "logs",
]

README_TEXT = """# {{PROJECT_TITLE}}

> 由 `agent-system` 脚手架生成（{{DATE}}）。系统版本 {{SYSTEM_VERSION}}（{{SYSTEM_ID}}）。

## 快速开始

1. 读 `AGENTS.md` 与 `docs/01_AI_Hardware_Engineering_Pipeline.md`。
2. 填 `docs/02_PRD.md` 与 `config/mechanical_params.yaml`（未确认值标 `PROVISIONAL`）。
3. 按 `docs/gate-run.md` 逐阶段运行门禁；结果落 `build/` 与各域报告。
4. 每轮结束更新 `docs/HANDOFF.md` 与 `TASK_BOARD.md` 并 commit。

## 目录

见 `docs/01_AI_Hardware_Engineering_Pipeline.md` 的仓库布局章节。

## 自检

```bash
python3 scripts/acceptance_check.py            # 骨架级检查 + build/ACCEPTANCE.json
python3 ../agent-system/scripts/check_system.py  # 系统自身校验（若在仓库内）
```
"""

GITIGNORE_TEXT = """# build / generated
build/
*.pyc
__pycache__/
.venv/
.tools/
# large binaries are regenerable; keep them out of git by default
*.step
*.stl
*.3mf
*.blend
*.glb
*.frd
*.inp
*.msh
# local logs
logs/
"""

TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "new-project"


def load_template_map() -> dict[str, str]:
    """Read the template registry from SYSTEM.yaml, else use the fallback map."""
    spec = SYSTEM_DIR / "SYSTEM.yaml"
    try:
        import yaml  # type: ignore
        doc = yaml.safe_load(spec.read_text(encoding="utf-8"))
        mapping = {}
        for t in doc.get("templates", []):
            if t.get("file") and t.get("output"):
                mapping[t["file"]] = t["output"]
        if mapping:
            return mapping
    except Exception:  # noqa: BLE001 - fall back to the static map
        pass
    return dict(FALLBACK_MAP)


def render(text: str, tokens: dict[str, str]) -> str:
    def sub(m: re.Match) -> str:
        return tokens.get(m.group(1), m.group(0))
    return TOKEN_RE.sub(sub, text)


def build_tree(paths: list[Path], root: Path, dir_paths=()) -> str:
    """ASCII tree of directories + files (dir_paths are rendered as directories)."""
    class Node(dict):
        pass

    dir_set = {Path(p) for p in dir_paths}
    tree = Node()
    for p in sorted(paths):
        rel = p.relative_to(root)
        cur = tree
        for i, part in enumerate(rel.parts):
            last = i == len(rel.parts) - 1
            if last:
                node = Node() if p in dir_set else None
                cur.setdefault(part, node)
            else:
                nxt = cur.get(part)
                if not isinstance(nxt, Node):
                    nxt = Node()
                cur[part] = nxt
                cur = nxt

    lines: list[str] = [root.name + "/"]

    def walk(node: Node, prefix: str):
        items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0]))
        for i, (name, child) in enumerate(items):
            last = i == len(items) - 1
            conn = "└── " if last else "├── "
            suffix = "/" if isinstance(child, Node) else ""
            lines.append(prefix + conn + name + suffix)
            if isinstance(child, Node):
                walk(child, prefix + ("    " if last else "│   "))

    walk(tree, "")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Scaffold a new hardware project from the reusable agent system.")
    ap.add_argument("name", help="project name (used for slug/dir name)")
    ap.add_argument("--root", default=None,
                    help="output directory (default: ./<slug> relative to CWD)")
    ap.add_argument("--system-dir", default=str(SYSTEM_DIR),
                    help="agent-system directory (default: parent of this script)")
    ap.add_argument("--title", default=None, help="human-readable project title")
    ap.add_argument("--domain", default="hardware", help="project domain tag")
    ap.add_argument("--date", default=None, help="date stamp YYYY-MM-DD")
    ap.add_argument("--force", action="store_true",
                    help="write into a non-empty existing directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the tree; write nothing")
    args = ap.parse_args(argv)

    system_dir = Path(args.system_dir).resolve()
    if not (system_dir / "SYSTEM.yaml").exists():
        print(f"ERROR: {system_dir} is not an agent-system directory "
              f"(SYSTEM.yaml not found)", file=sys.stderr)
        return 2

    slug = slugify(args.name)
    title = args.title or args.name
    date = args.date or _dt.date.today().isoformat()
    target = Path(args.root).resolve() if args.root else (Path.cwd() / slug).resolve()

    # Guard: never scaffold inside agent-system itself.
    try:
        target.relative_to(system_dir)
        print(f"ERROR: refusing to scaffold inside the system directory: {target}",
              file=sys.stderr)
        return 2
    except ValueError:
        pass
    if target == Path(target.anchor):
        print("ERROR: refusing to use a filesystem root as project dir", file=sys.stderr)
        return 2

    tokens = {
        "PROJECT_NAME": args.name,
        "PROJECT_SLUG": slug,
        "PROJECT_TITLE": title,
        "DOMAIN": args.domain,
        "DATE": date,
        "SYSTEM_ID": "smartcoaster-agent-system",
        "SYSTEM_VERSION": "1.0.0",
        "ROOT_NAME": target.name,
    }

    template_map = load_template_map()
    plan_files: list[tuple[Path, str]] = []   # (absolute target, rendered content)
    missing_templates: list[str] = []
    for relpath, output in sorted(template_map.items()):
        src = system_dir / relpath
        if not src.exists():
            missing_templates.append(relpath)
            continue
        text = src.read_text(encoding="utf-8")
        plan_files.append((target / output, render(text, tokens)))
    plan_files.append((target / "README.md", render(README_TEXT, tokens)))
    plan_files.append((target / ".gitignore", GITIGNORE_TEXT))
    plan_dirs = [target / d for d in DIRECTORIES]

    if missing_templates:
        print("ERROR: missing templates:", file=sys.stderr)
        for m in missing_templates:
            print(f"  - {system_dir / m}", file=sys.stderr)
        return 2

    all_paths = plan_dirs + [p for p, _ in plan_files]
    print(f"project : {title}")
    print(f"slug    : {slug}")
    print(f"target  : {target}")
    print(f"source  : {system_dir}")
    print(f"mode    : {'DRY-RUN (no writes)' if args.dry_run else 'WRITE'}")
    print()
    print(build_tree(all_paths, target, plan_dirs))
    print()
    total_bytes = sum(len(c.encode("utf-8")) for _, c in plan_files)
    print(f"plan: {len(plan_dirs)} directories, {len(plan_files)} files, "
          f"{total_bytes} bytes of UTF-8 text")
    for p, content in sorted(plan_files, key=lambda x: str(x[0])):
        print(f"  + {p.relative_to(target)}  ({len(content.encode('utf-8'))} B)")

    if args.dry_run:
        print("\nDRY-RUN: nothing written. Re-run without --dry-run to create.")
        return 0

    # Existence / emptiness checks -----------------------------------------
    if target.exists():
        if not target.is_dir():
            print(f"ERROR: target exists and is not a directory: {target}", file=sys.stderr)
            return 2
        non_empty = any(target.iterdir())
        if non_empty and not args.force:
            print(f"ERROR: target directory is not empty: {target}\n"
                  f"       use --force to write into it", file=sys.stderr)
            return 2

    for d in plan_dirs:
        d.mkdir(parents=True, exist_ok=True)

    written = 0
    for path, content in plan_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not args.force:
            print(f"WARN: exists, not overwritten: {path.relative_to(target)}")
            continue
        path.write_text(content, encoding="utf-8")
        if path.suffix == ".py":
            os.chmod(path, 0o755)
        written += 1

    # Verify the scaffold ------------------------------------------------
    missing = [str(p.relative_to(target)) for p, _ in plan_files if not p.exists()]
    if missing:
        print("ERROR: scaffold incomplete; missing:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    print(f"\nOK: created {written} file(s) + {len(plan_dirs)} directory(ies) under {target}")
    print("\nNext steps:")
    print(f"  cd {target}")
    print("  # 1) fill docs/02_PRD.md + config/mechanical_params.yaml")
    print("  # 2) edit AGENTS.md / TASK_BOARD.md / requirements.yaml")
    print("  python3 scripts/acceptance_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
