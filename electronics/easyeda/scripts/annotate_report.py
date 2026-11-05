#!/usr/bin/env python3
"""Prepend a provenance note to the auto-generated project-report.md."""
from pathlib import Path
P = Path(__file__).resolve().parents[1] / 'smartcoaster_easyeda' / 'project-report.md'
NOTE = """
> **注（2026-11-05）**：本报告由 eprj3 skill 自动生成，其中“板框 3860×3680 mil（自动）”是生成时的临时自动尺寸；
> 构建后 `scripts/patch_board.py` 已把板框替换为机械 C 形（93.2×93.2 mm、R6、38×38 开口、80° 前 C 口、
> 4×M2 NPTH @(±40,±24) mm）。PCB 仍是 placement-only（无铜），DRC 100/100 只评价摆放。
> 机械与网表事实以 `inputs/canonical.json`、`reports/parity.log` 和 `REPORT.md` 为准。

"""
def main():
    if not P.exists():
        raise SystemExit(f'missing {P}')
    text = P.read_text()
    if 'patch_board.py 已把板框' in text:
        return
    P.write_text(NOTE + text)
    print(f'annotated {P}')
if __name__ == '__main__':
    main()
