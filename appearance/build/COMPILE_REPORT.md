# appearance/ 一键编译报告（COMPILE_REPORT）

> 生成：2026-11-07T01:03:31+08:00 · 结果：**PASS** · 真实编译 · 总耗时 499.6 s
> 配置：`appearance/config/appearance_project.yaml` sha256 `794fe8bc5382102d…`

## 1. 校验

- 检查项：**410/410 PASS**，失败 0，警告 0

| 分组 | PASS | FAIL | WARN |
|---|---|---|---|
| artifacts/acceptance | 6 | 0 | 0 |
| artifacts/art:dog | 32 | 0 | 0 |
| artifacts/art:elf | 32 | 0 | 0 |
| artifacts/convert:dog | 42 | 0 | 0 |
| artifacts/convert:elf | 46 | 0 | 0 |
| artifacts/print | 10 | 0 | 0 |
| artifacts/print:round | 18 | 0 | 0 |
| artifacts/print:square | 18 | 0 | 0 |
| artifacts/render | 6 | 0 | 0 |
| artifacts/render:round | 18 | 0 | 0 |
| artifacts/render:square | 18 | 0 | 0 |
| artifacts/shell | 12 | 0 | 0 |
| artifacts/shell:round | 30 | 0 | 0 |
| artifacts/shell:square | 26 | 0 | 0 |
| config | 24 | 0 | 0 |
| inputs | 14 | 0 | 0 |
| stage_constants | 46 | 0 | 0 |
| tools | 12 | 0 | 0 |

## 2. 派生输入（由唯一配置计算）

| version | art | colours×layer | print t | rim | floor | depth | pocket/print Ø | interference | top gap |
|---|---|---|---|---|---|---|---|---|---|
| round | dog | 6 × 0.20 | 1.20 | 17.00 | 15.75 | 1.25 | 86.0/86.4 | 0.20 | 0.05 |
| square | elf | 7 × 0.20 | 1.40 | 18.00 | 16.55 | 1.45 | 86.0/86.4 | 0.20 | 0.05 |

## 3. 阶段

| # | 阶段 | 状态 | 耗时 | 命令 |
|---|---|---|---|---|
| 1 | art | ok | 1.9 s | `python3 appearance/tools/make_art.py --config appearance/build/compile/resolved_config.json` |
| 2 | convert | ok | 48.0 s | `bash appearance/kromacut/run_convert.sh` |
| 3 | shell | ok | 14.5 s | `bash appearance/cad/run_shell.sh --config appearance/build/compile/resolved_config.json` |
| 4 | render | ok | 255.5 s | `/data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py`<br>`python3 appearance/render/make_3mf.py`<br>`python3 appearance/render/postprocess.py` |
| 5 | print | ok | 145.8 s | `bash render/print/appearance/run_print_stage.sh` |
| 6 | acceptance | ok | 29.8 s | `python3 appearance/tools/acceptance_check.py` |
| — | **total** | | **499.6 s** | |

## 4. 验收（Lead 只读复核）

- `appearance/build/ACCEPTANCE.json`：**130/130 PASS**，failed 0

## 5. 诚实边界（不能靠改配置完成的输入）

- Config-only inputs: art sheet image/crop, palette contents (same number of colours), tuning, output dirs, tool paths. Changing colour COUNT, layer height, rim/floor, pocket/print diameter, interference, top gap or bed is NOT config-only: the hard-coded stage constants and the Lead-owned acceptance baseline must be edited too (compile.py fails early with the exact file/constant).
- Changing version names or art NAMES is also not config-only: appearance/render/scene_common.py VERSIONS, appearance/render/config.json versions, appearance/kromacut/run_convert.sh art loop and the Lead-owned acceptance baseline are keyed on round/square + dog/elf.
- Acceptance (130/130) is Lead-owned/read-only for this task; compile.py only invokes it and reads ACCEPTANCE.json.
- Bambu Studio slicing/printing and physical print quality are still not verified (see appearance/PRINT_DELIVERY_SPEC.md).

## 6. 复跑

```bash
bash appearance/compile.sh                 # 全流程 + 验收
bash appearance/compile.sh --dry-run       # 只校验，不写文件
bash appearance/compile.sh --list          # 看阶段/命令
```
