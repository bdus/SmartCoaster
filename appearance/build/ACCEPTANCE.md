# appearance/ Lumina-Layers 印花线 — 独立验收（Lead 只读复核）

> 生成：2026-11-07T23:51:52 · 共 194 项，**194 PASS / 0 FAIL**
> 由 `python3 appearance/tools/acceptance_check_lumina.py` 生成；只读已交付产物，不重跑阶段脚本。

| 分组 | PASS | FAIL |
|---|---|---|
| A_tool | 14 | 0 |
| B_art | 18 | 0 |
| C_print | 48 | 0 |
| D_shell | 18 | 0 |
| E_render | 30 | 0 |
| F_3mf | 10 | 0 |
| G_delivery | 47 | 0 |
| H_docs | 9 | 0 |

## 未由本脚本验证 / 边界

- Bambu Studio import / AMS mapping / layer-by-layer slicing / printing were NOT verified on this machine.
- Physical colour (LUT calibration), layer bonding, flatness, heat and washability were NOT tested.
- The recessed plates were NOT re-run through the 21 mechanical self-checks or FEA (PROVISIONAL).
- The render-only PRINT_FACE overlay shows Lumina's PREDICTED colour (matched_rgb); it is not print geometry and is not in any 3MF/STL.
- Delivered STLs are rigid-baked copies in the print pose, not byte copies of the sources.

