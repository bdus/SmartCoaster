# appearance/ 输入清单与一键编译契约（INPUTS）

> 适用：`appearance/` IP 印花 → Kromacut 多材料 → 顶板浅槽 → Blender 数字样机/3MF → 打印交付
> 唯一配置：`appearance/config/appearance_project.yaml` · 唯一命令：`bash appearance/compile.sh`
> 本文回答三件事：**要准备哪些输入、放到哪里、什么能只改配置、什么不能**。

---

## 0. 一句话

```bash
cd /data/Documents/projects/SmartCoaster

# 1) 只校验（不写任何文件）：先看配置/输入/工具/阶段常量是否自洽
bash appearance/compile.sh --dry-run

# 2) 全流程编译 + Lead 只读验收（art → convert → shell → render → print → acceptance）
bash appearance/compile.sh
```

成功判据：最后出现 `130/130 PASS`（来自 `appearance/build/ACCEPTANCE.json`），
并生成 `appearance/build/COMPILE_REPORT.json` / `.md`（每阶段状态/耗时/校验项）与
`appearance/build/compile.log`（完整流式日志）。

相关文件：

| 文件 | 作用 |
|---|---|
| [`appearance/config/appearance_project.yaml`](config/appearance_project.yaml) | **唯一输入源**（schema 注释在文件头） |
| [`appearance/tools/compile.py`](tools/compile.py) | 编排器：校验 → 跑现有阶段脚本 → 校验产物 → 报告 |
| [`appearance/compile.sh`](compile.sh) | 薄包装：`bash appearance/compile.sh [flags]` |
| [`appearance/INPUTS.md`](INPUTS.md) | 本文：输入契约 / 改动边界 |
| [`appearance/AGENT_PROMPT.md`](AGENT_PROMPT.md) | 给未来 AI agent 的复制粘贴提示词 |
| [`appearance/README.md`](README.md) | 全流程原理、工程要求、失败模式 |

常用 flags：

```bash
bash appearance/compile.sh --dry-run              # 只校验，零写入
bash appearance/compile.sh --list                 # 列出阶段与将执行的命令
bash appearance/compile.sh --only shell           # 只跑某个阶段（可逗号分隔）
bash appearance/compile.sh --from render          # 从某阶段跑到结尾
bash appearance/compile.sh --skip convert         # 跳过某阶段（保留其已有产物）
bash appearance/compile.sh --no-acceptance        # 不跑 Lead 验收
bash appearance/compile.sh --verbose              # 打印每一条校验
bash appearance/compile.sh --config /tmp/x.yaml   # 用另一份配置（失败模式测试用）
```

---

## 1. 输入清单（总表）

> “config-only” 列：✅ = 只改 YAML 即可；❌ = 还要改硬编码阶段文件/Lead 验收基线（compile.py 会
> **提前失败并打印“改哪个文件哪个常量”**，不会偷偷造出与验收不一致的模型）。

### 1.1 素材（art sheet）

| 输入 | 必填 | 放置位置 / 名称 | 格式 | 本项目示例 | 校验规则 | 配置键 | config-only |
|---|---|---|---|---|---|---|---|
| 印花拼版图 | 是 | `appearance/src/surface.png`（或任意仓库内路径） | PNG/JPG，RGB | 1774×887，白底，两枚圆形印花左右拼版 | 文件存在、可解码、crop 在图像范围内 | `versions.<v>.art.image` | ✅（换图/换路径） |
| 裁切区域 | 是 | 配置里写，不产生文件 | `ellipse: {cx,cy,rx,ry}` 或 `bbox: {x0,y0,x1,y1}` | 狗 `(449.0, 439.5, 415.5, 406.0)`；精灵 `(1325.0, 439.0, 415.5, 406.5)` | crop 完全落在图像内；bbox 模式要求近似正方形（否则会拉伸）；椭圆按 bbox 重采样回正圆 | `versions.<v>.art.crop` | ✅ |
| 印花名 | 是 | `appearance/build/art/<name>/` 的目录名 | 小写字母/数字/下划线 | `dog`、`elf` | 与 `run_convert.sh` 的 art 循环、`scene_common.py VERSIONS`、验收基线一致 | `versions.<v>.art.name` | ❌（改名要同步 4 处硬编码） |

### 1.2 量化（palette / tuning / 尺度）

| 输入 | 必填 | 放置位置 / 名称 | 格式 | 本项目示例 | 校验规则 | 配置键 | config-only |
|---|---|---|---|---|---|---|---|
| 耗材色板（由底到顶） | 是 | 配置 | `#RRGGBB` 列表，**index 0 = 打底层** | 狗 6 色：`#FBF4E8 #CBE0F5 #9FB2DA #F9CD72 #F09FAF #6C574C`；精灵 7 色：`#EDE1F0 #D9CFE6 #C3AEDC #F7D2C0 #E8A9B8 #C9A45B #5B4A72` | 每项合法 hex；**数量 = 物理层数 = 印花厚度/层高**；`len(palette) == expect.print_layers` | `versions.<v>.art.palette_bottom_up` | ✅ 只换色值；❌ 改数量 |
| 量化微调 | 否 | 配置 | `{contrast, saturation}`，1.0 = 不变 | 狗 1.08 / 1.15；精灵 1.05 / 1.10 | 数值 | `versions.<v>.art.tuning` | ✅ |
| 像素尺寸 | 是 | 配置 | mm/px | `0.15` | >0；且 `print_dia_mm / pixel_size_mm` 必须是整数（86.4/0.15 = 576） | `versions.<v>.art.pixel_size_mm` | ❌（验收基线写死 86.37 / 0.15） |
| 层高 | 是 | 配置 | mm | `0.20` | >0；与切片层高一致；验收基线写死 0.2 | `versions.<v>.art.layer_height_mm` | ❌（验收基线写死 0.2） |
| 输出根目录 | 否 | 配置 | 仓库相对路径 | `appearance/build/art` | 可创建 | `paths.art_out` / `art.out_dir` | ✅ |

由上述自动派生（**不要**在 YAML 里重复写，`expect` 段除外）：

```
n_px            = print_dia_mm / pixel_size_mm            = 86.4 / 0.15 = 576
print_thickness = len(palette_bottom_up) * layer_height   = 6×0.2 / 7×0.2 = 1.20 / 1.40 mm
art_diameter    = (n_px - 0.2) * pixel_size_mm           = (576-0.2)×0.15 = 86.37 mm
frame           = n_px * pixel_size_mm                   = 86.4 mm = print_dia_mm
```

### 1.3 外壳（顶板 STEP + 浅槽）

| 输入 | 必填 | 放置位置 / 名称 | 格式 | 本项目示例 | 校验规则 | 配置键 | config-only |
|---|---|---|---|---|---|---|---|
| 已验证顶板 STEP | 是 | `mechanical/<project>/build/parts/plate_v01.step`（**只读**，不重建） | STEP，单实体 | 圆：`mechanical/lumen/build/parts/plate_v01.step`；方：`mechanical/square_v1/build/parts/plate_v01.step` | 文件存在；导入后单实体；其顶面 z 必须 == `rim_z_mm`（否则 build_recessed 明确报 mismatch） | `versions.<v>.shell.plate_step` | ✅ 换同尺寸 STEP；❌ 改变外形/沿口 |
| 机械项目名 | 是 | 配置 | `lumen` / `square_v1` | `lumen`、`square_v1` | 决定 `mechanical/<mech_label>/build/parts/`；与 render 映射一致 | `versions.<v>.shell.mech_label` | ❌（scene_common / render config 有硬编码映射） |
| 报告显示名 | 否 | 配置 | 字符串 | 见 YAML | — | `versions.<v>.shell.label` | ✅ |
| 沿口 z | 是 | 配置 | mm | 圆 `17.0`；方 `18.0` | 必须等于 STEP 实测顶面；`floor = rim - top_gap - thickness` | `versions.<v>.shell.rim_z_mm` | ❌（验收基线写死 17.0/18.0） |
| 槽直径 | 是 | 配置 | mm | `86.0` | `pocket_dia == print_dia - 2*interference`；两版必须相同 | `versions.<v>.shell.pocket_dia_mm` | ❌（验收/阶段常量写死 86.0） |
| 印花直径 | 是 | 配置 | mm | `86.4` | 同上；`n_px = print_dia/pixel` 为整数 | `versions.<v>.shell.print_dia_mm` | ❌（验收/阶段常量写死 86.4） |
| 径向过盈 | 是 | 配置 | mm | `0.2` | 同上等式 | `versions.<v>.shell.interference_mm` | ❌ |
| 顶差（印花顶低于沿口） | 是 | 配置 | mm | `0.05` | `floor = rim - top_gap - thickness`；打印阶段 `PRINT_NEST_Z_MM` 写死 0.05 | `versions.<v>.shell.top_gap_mm` | ❌（print_layout 常量写死） |
| CMF 风格 | 是 | 配置 | 字符串 | `lumen_violet` | 必须 == `appearance/render/config.json` 的 `cmf.style` | `versions.<v>.shell.style` | ❌（CMF 映射在 render/config.json + styles.json） |

派生：`pocket_depth = top_gap + print_thickness`（1.25 / 1.45），
`floor_z = rim_z - pocket_depth`（15.75 / 16.55），`print_top_z = rim_z - top_gap`（16.95 / 17.95）。

### 1.4 打印（床 / 按键）

| 输入 | 必填 | 放置位置 / 名称 | 格式 | 本项目示例 | 校验规则 | 配置键 | config-only |
|---|---|---|---|---|---|---|---|
| 打印床 | 是 | 配置 | mm | `220` | 必须与 `print_layout_appearance.py` 的 `BED_MM` 一致；产物床面 bbox ≤ bed、间距 ≥ 5 mm | `versions.<v>.print.bed_mm` | ❌（阶段常量写死 220） |
| 按键 | 是 | 配置 | `none` / `part` | 圆 `none`；方 `part` | 必须与 `appearance/build/shell/parts.json` 里该版本是否有 `button_*` 一致；`part` 时交付 `square_button.stl` | `versions.<v>.print.button` | ✅ 在机械件已存在的前提下切换；❌ 机械项目本身没有/多出按键时 |

### 1.5 阶段脚本 / 工具 / 环境

| 输入 | 必填 | 位置 | 本项目值 | 校验规则 | 配置键 |
|---|---|---|---|---|---|
| Python（系统） | 是 | PATH | `python3` 3.10.12 | 可执行；有 PyYAML / numpy / Pillow | `tools.python` |
| Node | 是 | PATH 或绝对路径 | `auto` → `/home/pi/.nvm/.../node` 24.15.0 | ≥ 22（Kromacut headless 桥接需要） | `tools.node` |
| Blender | 是 | `/data/Documents/tools/blender/blender` | 4.5.3 LTS | 可执行 + `--version` 含 4.5.3 | `tools.blender` |
| build123d venv Python | 是 | `mechanical/square_v1/.venv/bin/python` | build123d 0.10.0 | 可执行；能 import build123d 0.10.0；`run_shell.sh` 的 `PY` 常量必须与之一致 | `tools.build123d_python` |
| Kromacut headless CLI | 是 | `/data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs` | v4.2.0 桥接 | 文件存在 | `tools.kromacut_cli` |
| 阶段命令 | 是 | 配置 `stages.*.commands` | 见 YAML | 每条命令是字符串列表；`{python}/{bash}/{node}/{blender}` 占位符可解析；脚本路径存在 | `stages` |
| 工具版本登记 | 是 | `requirements.yaml` | kromacut 4.2.0 / blender 4.5.3 | 文本包含对应版本 | —（只读校验） |

> 工具安装位置是 `/data/Documents/tools/<tool>`（项目约定 AGENTS.md §6），**不要**把 Kromacut/Blender
> 源码或依赖放进仓库。首次/换机安装：`bash appearance/tools/install_kromacut.sh`。

### 1.6 回归基线（expect，可选但建议保留）

`versions.<v>.expect` 是当前仓库**已验证数字**。compile.py 同时校验
“输入派生值 == expect” 和 “产物 == 派生值”，这样配置手误（少一个色、rim 打错）会在
`--dry-run` 就报错，而不是跑 6 分钟后在验收阶段才发现。

| 键 | 圆 | 方 | 含义 |
|---|---|---|---|
| `n_px` | 576 | 576 | 画幅像素 |
| `art_diameter_mm` | 86.37 | 86.37 | 印花直径 |
| `print_layers` | 6 | 7 | 物理层数 = 色数 |
| `print_thickness_mm` | 1.20 | 1.40 | 印花厚度 |
| `pocket_depth_mm` | 1.25 | 1.45 | 槽深 |
| `floor_z_mm` | 15.75 | 16.55 | 槽底 z |
| `acceptance_checks` | 130 | 130 | Lead 验收总项数 |

故意改输入时：**要么同步更新 expect 并重跑验收，要么删掉对应键**；否则编译按“expect 与派生值不一致”报错。

---

## 2. 5 步：只换印花（最常用）

以换一张新图、沿用 dog 的 6 色为例：

1. **放图**：把新拼版图放到 `appearance/src/`（例如 `appearance/src/surface_v2.png`）。
2. **改 YAML**（`appearance/config/appearance_project.yaml`）：
   ```yaml
   versions:
     round:
       art:
         image: appearance/src/surface_v2.png
         crop: {mode: ellipse, cx: 449.0, cy: 439.5, rx: 415.5, ry: 406.0}  # 用真实测量值
         palette_bottom_up: [...]   # 6 个颜色，顺序仍是“由底到顶”
         tuning: {contrast: 1.08, saturation: 1.15}
   ```
   > 强烈建议先用小脚本量 crop：不要用肉眼猜中心/半径（源图两枚图形是略扁椭圆，见 README §4.1）。
3. **试跑校验**：`bash appearance/compile.sh --dry-run`
   - 期望：`validation: N/N checks passed`，`RESULT: PASS — dry-run only, no files written`。
4. **真正编译**：`bash appearance/compile.sh`
   - 期望：6 个阶段全 `ok`；最后 `acceptance: 130/130 PASS`。
5. **看结果**：
   - 量化对照：`appearance/build/art/dog/art_source_crop.png`、`art_rgba.png`、`art_board.png`
   - 多材料：`appearance/build/print/dog/`（3MF + 逐耗材 STL + manifest）
   - 数字样机：`appearance/render/round/{hero,top,print_top,macro_edge,section_exploded}.png`
   - 打印交付：`render/print/stl/` + `render/print/appearance/`
   - 报告：`appearance/build/COMPILE_REPORT.md`

> 只改“颜色值”不改数量 = ✅ config-only；**改颜色数量**（6→7）= ❌ 需要同步：
> `expect.print_layers / print_thickness / pocket_depth / floor_z`、印花厚度、`appearance/tools/acceptance_check.py`
> 的基线（Lead 所有，只读）以及重新验证槽深/过盈。compile.py 会在 dry-run 阶段精确列出要改的键。

---

## 3. 5 步：换外壳 / 新顶板

前提：**外观变体不得改动冻结功能区**（见 `docs/HANDOFF.md` §7.5.2），顶板必须是已验证 STEP。

1. **放 STEP**：把验证过的顶板放到 `mechanical/<project>/build/parts/plate_v01.step`
   （`mechanical/**` 只读导入，不重建；项目约定见 AGENTS.md §3）。
2. **改 YAML**：
   ```yaml
   versions:
     round:
       shell:
         plate_step: mechanical/<project>/build/parts/plate_v01.step
         mech_label: <project>        # lumen / square_v1 之外的 project 名不是 config-only
         label: "<project> plate"
         rim_z_mm: <STEP 实测顶面 z>
         pocket_dia_mm: 86.0
         print_dia_mm: 86.4
         interference_mm: 0.2
         top_gap_mm: 0.05
         style: lumen_violet
   ```
3. **试跑校验**：`bash appearance/compile.sh --dry-run`
   - 若 STEP 顶面与 `rim_z_mm` 不符，`build_recessed.py` 会断言失败并打印 `rim top mismatch`；
     compile.py 的阶段常量校验也会先提示 render/验收基线需要改哪些数字。
   - 若 `mech_label` 不是 `lumen`/`square_v1`：`appearance/render/scene_common.py VERSIONS` 和
     `appearance/render/config.json versions` 的硬编码映射需要改（❌ 非 config-only）。
4. **真正编译**：`bash appearance/compile.sh`
   - `shell` 阶段会从 STEP 导入 + 布尔切槽，并输出 `appearance/build/shell/{shell.json,parts.json,REPORT.md}`。
5. **验收**：`appearance/build/ACCEPTANCE.md` + `appearance/build/COMPILE_REPORT.md`。
   - 若 rim/floor/厚度变化：Lead 验收基线（`acceptance_check.py` 的 `exp` 与打印姿态断言）必须由 Lead 更新，
     否则验收会 FAIL；compile.py 会提前在 dry-run 报 `acceptance baseline (...) .rim/floor/...` 失败。

> 结论：**同尺寸换 STEP = config-only；改外形/沿口/槽径/厚度 = 非 config-only**，必须同步硬编码阶段常量 +
> Lead 验收基线。`--dry-run` 会直接告诉你要改哪个文件的哪个常量。

---

## 4. 什么能改 vs 什么不能（诚实版）

| 改动 | 只改 YAML？ | 还必须改什么（compile.py 会点名） |
|---|---|---|
| 换印花图 / 改 crop | ✅ | — |
| 换色值（色数不变） | ✅ | — |
| 改 tuning | ✅ | — |
| 改输出目录 / 工具路径 | ✅ | 若工具路径与阶段脚本硬编码不一致：`run_shell.sh PY`、`build_recessed.py BLENDER` |
| 改印花名 / 版本名 | ❌ | `appearance/kromacut/run_convert.sh` art 循环；`appearance/render/scene_common.py VERSIONS`；`appearance/render/config.json versions`；`appearance/tools/acceptance_check.py` 基线；打印阶段 `VERSIONS` 元组 |
| 改色数（层数/厚度） | ❌ | 同上 + `expect.*` + 验收基线 + 槽深/打印姿态断言 |
| 改 rim / floor | ❌ | `appearance/render/config.json shell_fallback.*`；`appearance/tools/acceptance_check.py` 基线；打印姿态断言 |
| 改 pocket/print 直径 / 过盈 | ❌ | `appearance/render/config.json print.*` + `shell_fallback.*`；验收基线；打印姿态断言；`verify_shell.py`（Lead 校验工具） |
| 改 top gap | ❌ | `render/print/appearance/print_layout_appearance.py PRINT_NEST_Z_MM`；验收基线；打印姿态断言 |
| 改打印床 | ❌ | `render/print/appearance/print_layout_appearance.py BED_MM`；验收基线 |
| 按键 none/part（机械件已存在） | ✅ | 需重跑 shell 阶段刷新 `parts.json`（compile 会校验一致性） |
| 换 CMF 风格 | ❌ | `appearance/render/config.json cmf.style` + `render/appearance/styles.json` |
| 换外壳 STEP（同尺寸） | ✅ | 若机械项目名变化，同上 render 映射 |
| 改 `mechanical/**`、`render/print/**`、`appearance/render/**`、`appearance/kromacut/**`、`render/print/appearance/**`、`appearance/tools/acceptance_check.py` | — | **本任务写权限之外**；这些是冻结/Lead 所有/只读导入，改它们需要单独任务与重新验收 |

---

## 5. compile.py 到底校验什么（清单）

### 5.1 静态校验（`--dry-run` 全做，零写入）

1. **schema / 结构**：`schema`、`versions == round+square`、`paths`、`tools`、`stages.commands`。
2. **每个版本**：art（name/image/crop/palette/tuning/pixel/layer）、shell（plate_step/mech_label/label/rim/pocket/print_dia/interference/top_gap/style）、print（bed/button）、expect（可选）。
3. **派生几何**：`n_px` 整数；`thickness = 色数×层高`；`pocket = print - 2×interference`；`floor = rim - top_gap - thickness`；两版共享的 pocket/print/interference/top_gap 必须相同。
4. **expect 回归基线**：派生值 vs `expect.*`（含 `acceptance_checks: 130`）。
5. **输入文件**：图片存在/可解码、crop 在图像内且近似正方形；顶板 STEP 存在；输出根目录合法。
6. **工具链**：Python（yaml/numpy/Pillow）、Node ≥22、Blender 4.5.3、build123d 0.10.0 venv、Kromacut CLI、`requirements.yaml` 版本登记、阶段脚本存在/可执行。
7. **配置 vs 硬编码阶段常量**（不一致时失败并点名文件/常量）：
   - `appearance/render/scene_common.py`：`VERSIONS`（mech/art）、`ROUND_PARTS`/`SQUARE_PARTS` 的 button；
   - `appearance/render/config.json`：`versions.*.mech/art`、`print.*`、`shell_fallback.*`、`cmf.style`；
   - `appearance/kromacut/run_convert.sh`：`for name in ...` art 循环；
   - `appearance/cad/run_shell.sh`：`PY` 常量；`appearance/cad/build_recessed.py`：`BLENDER` 常量；
   - `render/print/appearance/print_layout_appearance.py`：`BED_MM`、`PRINT_NEST_Z_MM`、`VERSIONS`；
   - `appearance/render/run_all.sh`：仍包含 build_scene/make_3mf/postprocess/print 四个子命令（compile 的 render/print 拆分依据）；
   - `appearance/tools/acceptance_check.py`（Lead 所有，只读）：`exp` 基线的 variant/rim/floor/depth/t、art 直径、层高、pocket/print 直径。
8. **阶段产物**：配置里每个阶段命令的脚本路径存在；`--only/--from/--skip` 选择后，**不重建的上游阶段产物必须已存在且与配置一致**。

### 5.2 阶段产物校验（每个阶段跑完后；`--dry-run` 对已有产物做同样校验）

| 阶段 | 主要校验 |
|---|---|
| `art` | `art.json` 的 width/height/pixel/layer/layer_count/thickness/art_diameter/frame/palette/crop/source sha；`layer_counts.bin` 大小=576×576×2、索引≤色数、透明像素一致；6 个产物文件 + `art_board.png` |
| `convert` | `manifest.json`：厚度、classCount、usesFullPalette、逐耗材 STL 数/命名/二进制大小、3MF、recentred bbox（x/y=print_dia、z=厚度、min z=0）、Kromacut 自检 `verification.passed` |
| `shell` | `shell.json` 的 rim/floor/pocket/print/interference/top_gap/thickness/depth/print_top、bbox 不变、槽底平面度 0、单实体 valid；`parts.json` 的 button 与配置一致；plate STL/STEP、blank STL |
| `render` | 每版 5 张 PNG（>50 KB）+ `scene.blend` + `scene_info.json`（version/art/floor/thickness、无 mismatches）+ `annotations.json`；`build/3mf/{round,square}.3mf` + `validation.json` ok/errors；`board.png`、`RENDER_LOG.md` |
| `print` | `render/print/stl/delivery.json`（all_rigid_checks / all_min_z_zero / 逐版条目数 / 打印姿态 pocket_floor=槽深、印花厚、art face=top_gap、无需支撑、床面 fit、18 个 STL 名称）；`CHECKSUMS.sha256` 逐文件重算；`render/print/appearance/<v>/` 7 件；无旧版逐版 STL 子目录 |
| `acceptance` | `ACCEPTANCE.json`：passed==total、failed==0、total==`expect.acceptance_checks`（130） |

---

## 6. 产物地图（跑完去哪找）

```text
appearance/build/
  art/<art>/                       art.json, layer_counts.bin, art_rgba.png, art_source_crop.png,
                                   art_quant_preview.png, palette.png
  art/art_board.png
  print/<art>/                     <art>_kromacut.3mf, filament_<n>_<HEX>.stl, manifest.json
  shell/                           shell.json, parts.json, REPORT.md, print_blank*.stl
  shell/round/plate_recessed.{step,stl} (+ plate_recessed_clean.*)
  shell/square/plate_recessed.{step,stl}
  render/<v>/                      macro_edge.png, section_seated.png, section_exploded.png（原始渲染）
  3mf/{round,square}.3mf           + validation.json（装配 3MF）
  ACCEPTANCE.json / ACCEPTANCE.md  Lead 只读验收（130/130）
  COMPILE_REPORT.json / .md        本次一键编译：配置 sha、派生数字、逐阶段状态/耗时、校验明细
  compile.log                      完整流式日志（gitignored）
  compile/resolved_config.json     compile 从 YAML 生成的规范化配置（阶段脚本实际读它）

appearance/render/{round,square}/   hero/top/print_top/macro_edge/section_exploded.png + scene.blend
appearance/render/board.png
render/print/stl/                  18 个打印姿态 STL + CHECKSUMS.sha256 + delivery.json + README.md
render/print/appearance/{round,square}/  layout.json, manifest.json, PRINT_READY.3mf, PRINT_SHEET.png,
                                   print_iso.png, print_top.png, README.md
render/print/appearance/PRINT_SHEET_APPEARANCE.png
```

---

## 7. 报错怎么读（示例）

compile.py 的失败信息统一是“**哪个校验 + 实际值 vs 期望值 + 改哪个文件/常量**”。例如：

```text
FAIL config / versions.round: expect.print_layers
     6 vs expected 5
     -> palette has 5 colours but expect.print_layers=6; either fix
        versions.round.art.palette_bottom_up or update expect.print_layers AND all
        downstream constants (see appearance/INPUTS.md)
```

```text
FAIL stage_constants / render/config.json shell_fallback.round.floor_z_mm
     15.75 vs expected 16.25
     -> edit appearance/render/config.json shell_fallback.round.floor_z_mm
        (fallback contract, not config-only)
```

```text
FAIL inputs / round: art sheet image
     file not found: appearance/src/surface_v2.png
     -> put the sheet at appearance/src/surface_v2.png or edit
        appearance/config/appearance_project.yaml versions.round.art.image
```

修完后再 `--dry-run`，通过后再整跑；整跑失败时报告仍有每阶段的命令、耗时和失败明细，日志在
`appearance/build/compile.log`。

---

## 8. 当前验证基线（2026-11-07，130/130 PASS）

| 项 | 圆 round (LUMEN) | 方 square (square_v1) |
|---|---|---|
| 印花 | dog（6 色） | elf（7 色） |
| 顶板 STEP | `mechanical/lumen/build/parts/plate_v01.step` | `mechanical/square_v1/build/parts/plate_v01.step` |
| rim z | 17.00 | 18.00 |
| 印花厚度 | 6×0.2 = 1.20 mm | 7×0.2 = 1.40 mm |
| 槽深 / 槽底 | 1.25 / 15.75 | 1.45 / 16.55 |
| 印花顶 z | 16.95 | 17.95 |
| 共用 | 印花 Ø86.4 · 槽 Ø86.0 · 过盈 0.20 · 顶差 0.05 · 像素 0.15 · 层高 0.20 · 床 220 | 同左 |
| 交付 | `render/print/stl/` 18 个 STL + `delivery.json` + `CHECKSUMS.sha256` | 同左 |
| Lead 验收 | `appearance/build/ACCEPTANCE.json` **130/130** | 同左 |

---

## 9. 已知限制（不要假装 config-only）

1. **验收脚本是 Lead 所有、本任务只读**：`appearance/tools/acceptance_check.py` 内写死了
   dog/elf、86.37、0.2、17.0/18.0、15.75/16.55、1.2/1.4 等基线。compile.py 只调用/读它，
   并把不一致提前转成 dry-run 失败；改这些数字必须由 Lead 更新验收并重新复核。
2. **版本名/印花名不在配置里真正自由**：`scene_common.py VERSIONS`、`render/config.json versions`、
   `run_convert.sh` 的 art 循环、打印阶段 `VERSIONS` 元组都是硬编码 round/square + dog/elf。
3. **数值几何（rim/floor/色数/槽径/过盈/顶差/床）不是纯配置**：阶段脚本大多已从
   `shell.json`/`manifest.json` 动态读取，但仍有上表列出的硬编码常量 + Lead 基线；compile.py 会
   逐个对照并提前失败，指向“编辑文件 X 常量 Y”。
4. **实物验证仍未做**：Bambu Studio 切片/打印、颜色/层厚/结合强度/耐热/清洁性、开槽顶板刚度/FEA、
   21 项功能自检均未验证（见 `appearance/README.md` §12 与 `PRINT_DELIVERY_SPEC.md`）。
5. **`--config` 直调**：`make_art.py --config` 可直接读 YAML（系统 python3 有 PyYAML）；
   `build_recessed.py --config` 走 build123d venv（无 PyYAML），优先用 compile.py 生成的
   `appearance/build/compile/resolved_config.json`；若 venv 能借到系统 PyYAML 也支持 YAML。
   推荐永远用 `bash appearance/compile.sh`，不要手工拼阶段命令。
6. **compile.py 不重跑不选中的阶段**：`--only/--from/--skip` 时，不重建的上游产物必须已存在且与
   配置一致（脚本会校验），否则直接失败，避免用旧产物拼新配置。

---

## 10. 相关文档

- 全流程原理 / 工程要求 / 踩坑：[`appearance/README.md`](README.md)
- 打印交付方向与断言：[`appearance/PRINT_DELIVERY_SPEC.md`](PRINT_DELIVERY_SPEC.md)
- 交接与验收边界：[`docs/HANDOFF.md`](../docs/HANDOFF.md) §10–11
- 给 AI agent 的复制粘贴提示词：[`appearance/AGENT_PROMPT.md`](AGENT_PROMPT.md)
