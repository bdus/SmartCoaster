# appearance/ — IP 印花 → Lumina-Layers 多材料一体打印线

> 版本：v2.1（2026-11-08，耗材/机型更新：RYBW + Black / Bambu H2D） · 本文是本线的**权威方法/工程要求**文档。
> 状态：**4 色 RYBW 印花几何（+ 黑色外壳/顶板/按键）在 Bambu H2D 上 5 色同打**；外壳开槽、Blender 数字样机、
> 装配 3MF、打印交付均已产出；`compile_lumina.py` 契约校验 **46/46**；独立验收 **194/194 PASS**
> （2026-11-07T23:35，`appearance/build/ACCEPTANCE.{json,md}`）；**Bambu Studio 实际切片与实物打印未验证**。
> 旧 Kromacut Flat Paint 线自 2026-11-07 起 **OBSOLETE**（历史事实归档于 §13，不再用于交付）。
> 配套：[`docs/15_Lumina_Layers_Guide.md`](../docs/15_Lumina_Layers_Guide.md)（独立入门/用法页，本页不重复）、
> [`docs/01` §17](../docs/01_AI_Hardware_Engineering_Pipeline.md)、[`docs/REPORT_技术报告.md`](../docs/REPORT_技术报告.md) §11、
> [`docs/REPORT_成果展示.md`](../docs/REPORT_成果展示.md) §2.6、[`docs/HANDOFF.md`](../docs/HANDOFF.md)。
> **同步状态**：本轮更新本页 + `docs/01` §17 + `requirements.yaml` + [`docs/15`](../docs/15_Lumina_Layers_Guide.md)；
> [`PRINT_DELIVERY_SPEC.md`](PRINT_DELIVERY_SPEC.md)、[`RENDER_HOWTO.md`](RENDER_HOWTO.md)、[`INPUTS.md`](INPUTS.md)、
> [`AGENT_PROMPT.md`](AGENT_PROMPT.md) 与 `appearance_project.yaml` 仍是 Kromacut 口径，**不作 Lumina 参数来源**。

## 0. 结论摘要（先看这里）

**目标**：把 IP 印花插画变成**厚度已知、平背、可多材料打印的印花板**，嵌进外壳浅槽，随外壳同盘（或分开）打印后
形成平整外观面；Blender/3MF 里印花与外壳**始终分离**，融合由 Bambu Studio 在切片阶段完成。

| 项 | 结论 |
|---|---|
| 引擎 | **Lumina-Layers（Lumina Studio 2.0 开源实现）**，AGPL-3.0-only；`core.converter.build_image_model_context` 进程内调用，无 GUI/FastAPI（§3） |
| 配色/耗材 | **4 卷 RYBW**（White `#FFFFFF` / Red `#DC143C` / Yellow `#FFE600` / Blue `#0064F0`）+ **1 卷 Black `#101010`**（外壳/顶板/按键）= **5 卷，H2D 一次同打**；LUT `lut-preset/Custom/lumina_lut.json`（§4.4） |
| 几何 | 864×864 RGBA @ **0.10 mm/px**，画幅 Ø86.4；**5 色层 + 10 背层 × 0.08 = 1.20 mm**；平背（§5） |
| 两版 | 圆形 LUMEN Ø110 + dog；方形 square_v1 100×100 + elf（几何口径完全相同） |
| 印花实测 | dog **680,354** 三角面 / elf **943,734**（RYBW 重跑，2026-11-08）；体积各 **7,018.896 mm³**；4 个逐耗材实体全部 watertight（§5.6） |
| 外壳/配合 | 槽 Ø86.0 × 深 **1.20 mm**；槽底 round **15.80** / square **16.80**；`top_gap=0` → 印花面与沿口齐平；名义 Ø86.2 / 过盈 **0.10 mm**，实测最大径向过盈 **0.219 mm**；CMF **黑壳** `#101010`（§6/§7） |
| 渲染 | 每版 5 张（hero/top/macro_edge/print_top/section_exploded）+ `board.png`；CMF = `bambu_pla_basic_rybw_black`（黑壳）；含 **RENDER-ONLY 预测色 overlay**（§7） |
| 打印交付 | `render/print/stl/{round,square}/`：每版 **16/17 个文件**（6/7 个 STL），打印姿态烘焙；`CHECKSUMS.sha256`（§8） |
| 一键流程 | `bash appearance/compile.sh` → `compile_lumina.py`（A1–A8：art→lumina→shell→render→3mf→postprocess→print→acceptance；dry-run **46/46**，§2.5） |
| 未验证 | Bambu 导入/AMS 映射/逐层切片；实物颜色/层厚/结合强度；开槽顶板 FEA/21 项自检；**H2D 5 色同打/双喷头行为**；见 §12 |

## 1. 设计决策（为什么这样分工）

### 1.1 为什么要从 Kromacut 换到 Lumina-Layers

| 维度 | Kromacut Flat Paint（旧，OBSOLETE） | Lumina-Layers（现） |
|---|---|---|
| 配色 | 逐色板量化，每色一层几何；dog 6 / elf 7 卷 | **光学叠层混色**，LUT 决定 5 个色层；**4 卷 RYBW + 1 卷黑壳**（H2D 5 色同打） |
| 网格/规模 | 576 px @ 0.15 mm/px；三角面 1,941,732 / 2,500,540；3MF 19.7 / 25.6 MB | **864 px @ 0.10 mm/px**；RYBW 重跑后三角面/3MF 见 manifest（随图/LUT 变） |
| 切片负担 | 逐色几何 + 水彩碎片化，AMS 槽位多 | 4 个耗材实体，槽位固定为 4 |

换线原因（工程决策，**不是**许可原因——两条线都是 AGPL）：逐色量化把水彩插画切成大量碎片，三角面/3MF/AMS
负担重；Lumina 用 4 卷叠层混色 + 实测 LUT，几何显著更轻。**2026-11-08 再按用户实际耗材改为 RYBW+黑壳**：
用户只有 Bambu PLA Basic 红/黄/蓝/绿/白/黑，没有青/品红（所以不用 CMYW），H2D 同打 5 色（4 印花 + 1 黑壳）
正好一次成型，Green 备用；一套几何契约（`(color_layers + round(spacer/0.08)) × 0.08`）取代两套厚度。

### 1.2 能力边界与两条硬约束

| 能做 | 不能做 |
|---|---|
| 光栅插画（PNG/JPEG，透明背景）→ 每耗材一个闭合实体 + 一个原生 3MF | 导入 STEP/STL 外壳并在其表面贴图 |
| 4 色 **RYBW** 光学混色、固定 0.10 mm/px、单面平背；圆/方外形由 alpha 决定 | 与 CAD 外壳布尔融合；切片/G-code/打印结果保证；无校准上 6/8 色 |

把它放在 **CAD 外壳之后、Blender 之前**作为"图案几何发生器"，不替代 CAD 或切片器。

**约束 A（不布尔合并）**：合并会丢掉"哪个面属于哪种耗材"的对象边界，切片软件无法按对象分配 AMS；
目标是**机械上一个零件、文件里多材料对象、切片时由 Bambu 解析成一体**，所以 Blender 不做融合裁决。

**约束 B（图案面贴床、`top_gap=0`）**：Lumina 单面件导出姿态是**图案面 z=0**（贴床第一层），背板在上、
平背；本项目槽深 = 印花厚度 + top_gap = **1.20 mm**，背板整面落槽底、**图案面与沿口齐平**（不再保留旧线
0.05 mm 顶差）。打印时顶板+印花整体翻转（凹槽朝下），两件外露面共面于床面 → **第一层 = 图案 + 沿口，无需支撑**；
打完整体翻面露出的才是图案（切片预览看到印花背面是**正确**的）。

### 1.3 许可边界（AGPL-3.0-only）

软件主体 **AGPL-3.0-only**（`LICENSING.md`；运行时依赖 `lumina-svg-core==0.3.4` 同为 AGPL-3.0-only）；
生成物另有上游 `OUTPUT-TERMS`：个人非商业自用免署名，商业销售/公开分享需标注
"Generated with Lumina-Layers / 由 Lumina-Layers 生成"。本项目**只调用、不修改、不嵌入发布物**；
分发修改版/组合程序需履行 AGPL 对应源码义务。旧线 Kromacut 同为 AGPL-3.0，换线不是许可驱动。

## 2. 全流程与数据流

```text
appearance/src/surface.png   原始拼版（1774×887）→ make_art_lumina.py（拆图/回正圆/6px bleed/二值 alpha）
   ▼ appearance/build/art/<art>/   art_rgba.png（864² RGBA）+ art.json
   ▼ lumina_convert.py → core.converter.build_image_model_context（S01–S12，进程内）
appearance/build/print/<art>/   4 个逐耗材 STL（assembly pose）+ 原生 3MF + manifest
   ├── cad/run_shell.sh（顶板开槽）→ appearance/build/shell/
   ▼ appearance/render/run_all.sh（场景/渲染 + render-only 预测色 overlay + make_3mf + postprocess）
   ▼ render/print/appearance/run_print_stage.sh（打印姿态 STL + 床面排版 + 参考图 + checksums）
render/print/stl/{round,square}/  可直接导入切片器的 STL/3MF 套件 → Bambu Studio → 打印 → 整体翻面
```

**阶段职责**：安装（§3）→ 素材（§4）→ 印花几何（§5）→ 外壳开槽（§6）→ 数字样机/渲染/3MF（§7）→
打印交付（§8）→ 验收（§9）；逐阶段命令与一键流程见 §2.5 / §9.2，不在此重复。

### 2.5 一键编译（唯一配置 + 一条命令）

**唯一配置**：[`appearance/config/lumina_project.yaml`](config/lumina_project.yaml)
（引擎、LUT、色层/背层/总厚、圆/方两版的 STEP/rim/槽径/印花径/过盈/top_gap、床面、按键、打印交付约定）。

```bash
cd /data/Documents/projects/SmartCoaster
bash appearance/compile.sh --dry-run   # 只校验输入/配置/工具/阶段常量，零写入
bash appearance/compile.sh             # art -> lumina -> shell -> render -> 3mf -> postprocess -> print -> acceptance
```

- **单一入口**：`appearance/compile.sh` 是薄包装，`exec python3 appearance/tools/compile_lumina.py "$@"`（无 Lua、无 GUI）。
  **已入库并生效**：8 个阶段 `A1 art → A2 lumina convert → A3 shell → A4 render(build_scene) → A5 3mf →
  A6 postprocess → A7 print delivery → A8 acceptance`；只负责"校验 → 调既有阶段脚本 → 回读产物 → 报告"，
  不重实现几何；报告在 `appearance/build/COMPILE_LUMINA_REPORT.{json,md}` + `appearance/build/compile_lumina.log`
  （阶段状态/耗时/每项校验/失败修复建议）；
- **实测入口**：`bash appearance/compile.sh --dry-run` → `== validation: 46/46 PASS ==`（含 RYBW/JSON LUT/H2D/5 色预算/黑壳 CMF；零写入，只写报告）；
  全流程约 **10–12 min**（36-core CPU）；支持 `--only A2`、`--from A4` 单阶段/续跑；RYBW 重跑阶段号 A1–A8 不变；
- **旧编排是 Kromacut 口径**：`appearance/tools/compile.py`、`appearance/config/appearance_project.yaml`、
  `appearance/build/COMPILE_REPORT.*`、`appearance/INPUTS.md`、`appearance/AGENT_PROMPT.md` 均属 OBSOLETE，勿混用。

## 3. 引擎与安装（本机实际）

### 3.1 版本与位置

| 组件 | 实际值 |
|---|---|
| 引擎源码/许可 | `/data/Documents/tools/Lumina-Layers`，git HEAD **`eef88023`**（`eef8802365310ae9de125a485fa4d3854a21a7df`，2026-11-07）；**AGPL-3.0-only**（调用不修改） |
| 解释器 | **独立 CPython 3.12.16**：`/data/Documents/tools/python312/bin/python3.12`（python-build-standalone） |
| 虚拟环境 | `/data/Documents/tools/Lumina-Layers/.venv`（3.12.16；`requirements.txt` 依赖已装齐） |
| LUT（4 色 RYBW） | **`lut-preset/Custom/lumina_lut.json`**（自描述 Keyed-JSON：palette White/Red/Yellow/Blue 带 hex；5 色层、0.08 mm、base 10 层；sha256 `bad3054b…5987`） |
| 打印机/耗材 | **Bambu Lab H2D**（350×320×325，双喷头，同打 5 色；`bambu-h2d` + `BambuStudio:bbl:bambu-lab-h2d:0.4`）；耗材 = Bambu PLA Basic RYBW 4 卷 + Black 1 卷，Green spare |
| 运行时/GUI | `Lumina/output → <repo>/.lumina_runtime/output`、`Lumina/materials → …/materials`（符号链接，`.lumina_runtime/` 已 gitignore）；GUI 可选（Node 24.15.0；pnpm 10.33.2 本机 12.16.1，**未验证**），headless 不需要 |

### 3.2 为什么必须独立 Python 3.12

系统只有 Python 3.10；上游 `requirements.txt` 用 `--only-binary` 钉住 4 个原生包，其中 `lumina-svg-core==0.3.4`、
`fatcat-metadata==0.1.5` 只发布 cp312/cp313/cp314 轮子（`requires_python>=3.12,<3.15`），3.10/3.11 装不上；
Linux 需 glibc ≥ 2.28（本机 2.35）。
重装 = `python312 -m venv <LUM>/.venv` → `pip install -r <LUM>/requirements.txt`。

- **镜像原因**：直连 pypi.org 实测约 **25–50 KB/s**，安装脚本改用 `https://pypi.tuna.tsinghua.edu.cn/simple`
  （`.scratch/install_lumina2.sh` / `.log` 为临时记录，换机时重写）；
- **目录权限**：`import config` 会创建 `output/{models,temp}`、`materials`；做成 §3.1 的符号链接后
  **Lumina 源码目录可保持只读**，所有时间戳产物落在项目 `.lumina_runtime/`。

### 3.3 离线设置（无遥测、无云库）

驱动在 import 前 `setdefault`：`LUMINA_MATERIAL_REGISTRY_URL=""`、`LUMINA_LUT_REGISTRY_URL=""`、
`LUMINA_FEEDBACK_SERVER_URL="off"`、registry/sync 刷新全关、`LUMINA_BACKEND=memory`、`LUMINA_TELEMETRY=0`、
`PYTHONDONTWRITEBYTECODE=1`。**绕过驱动直接 import 的脚本必须自行设置同一组变量**。

### 3.4 安装校验（必须全 OK）

```bash
LUMINA=/data/Documents/tools/Lumina-Layers; PY=$LUMINA/.venv/bin/python
"$PY" -V && "$PY" -c "import lumina_svg_core, neroued_3mf, fatcat_metadata, trimesh, cv2, numpy; print('deps ok')"
readlink -f "$LUMINA/output" "$LUMINA/materials"            # 期望 <repo>/.lumina_runtime/*
sha256sum "$LUMINA/lut-preset/Custom/lumina_lut.json"   # bad3054b…5987
python3 appearance/tools/make_art_lumina.py --check && \
  "$PY" appearance/lumina/lumina_convert.py --art dog,elf --manifest-only   # 只读回归
```

> 2026-11-07 本机实测：依赖 import、LUT sha256、art `--check`、`--manifest-only` 均通过；
> 详细记录见 [`docs/15`](../docs/15_Lumina_Layers_Guide.md) §3。

## 4. 素材规格与数据契约（`make_art_lumina.py`）

### 4.1 输入测量（不要硬编码猜）

- 源图 `appearance/src/surface.png`：**1774×887**，两张圆形印花左右拼版，白底；
- 两枚图形**不是正圆**，是略扁椭圆（脚本 `ARTS`）：dog `cx=449.0, cy=439.5, rx=415.5, ry=406.0`；
  elf `cx=1325.0, cy=439.0, rx=415.5, ry=406.5`；按椭圆包围盒重采样到正方形才能恢复真圆。

### 4.2 处理步骤（固定顺序，可复现）

按椭圆包围盒 `(cx±rx, cy±ry)` 取 `PIL.Image.resize(864×864, LANCZOS, box=bbox)` → 圆外颜色向圆内外扩 6 px
（避免 LANCZOS 白边）→ 以画幅中心 `N/2-0.5 px` 计算圆内 mask → alpha 二值化（圆外 0/圆内 255 = 圆形件）→
**不做颜色量化**（Lumina 下游 LUT 匹配）→ 输出 `art_rgba.png`、`art_thumb.png`、`art_source_crop.png`、
`art.json`、`art_board.png`。

### 4.3 尺度与几何契约（必须与引擎/外壳一致）

| 参数 | 值 | 来源/约束 |
|---|---|---|
| 画幅 / 像素 | **864 × 864 px / 0.10 mm/px** | `int(target_width_mm × 10)`；喂 864 px 使 NEAREST 重采样为恒等 |
| 画幅边长 / alpha 圆盘 | **86.4 mm / 863 px 直径（≈86.3 mm）** | 864 × 0.10；圆内像素 584,908（opaque_ratio 0.783538，两版相同） |
| 层高 / 色层 / 背层 / 总层 | **0.08 mm / 5 / 10 / 15** | Lumina `PrinterConfig.LAYER_HEIGHT`；5×0.08 + 0.80 = **1.20 mm** |
| 印花厚度 | **1.20 mm** | `total_layers × 0.08`，驱动断言 `--expect-thickness 1.20` |

### 4.4 色板（4 卷 RYBW，槽序 = `slot_names`）

| 槽 | 名称 | LUT palette hex（Bambu PLA Basic 实际色） |
|---|---|---|
| 0 | White | `#FFFFFF`（背板 + 高光） |
| 1 | Red | `#DC143C` |
| 2 | Yellow | `#FFE600` |
| 3 | Blue | `#0064F0` |

**LUT = `lut-preset/Custom/lumina_lut.json`**（自描述 Keyed-JSON，`color_mode="4-Color (RYBW)"`，palette 自带 hex，
`max_color_layers=5`、`layer_height_mm=0.08`、`base_layers=10`）。槽序/hex 一律以 `manifest.palette` / `slot_names` 为准；
CMYW（Cyan/Magenta）是 2026-11-08 前的历史配色，用户没有对应耗材，不要再切回。

### 4.5 数据契约：`appearance/build/art/<art>/art.json`

schema `smartcoaster.appearance.art_lumina/v1`；下游只读、不猜参数：

| 字段 | 内容 |
|---|---|
| `width/height/pixel_size_mm` | `864 / 864 / 0.1`（Lumina 目标像素网格必须等宽） |
| `frame_mm/art_diameter_mm/disc_diameter_px` | `86.4 / 86.4 / 863.0`（画幅与 alpha 圆盘口径） |
| `alpha/color_model` | 二值 alpha（圆外 0）；未量化 sRGB（Lumina 下游 LUT 匹配） |
| `layer_height_mm/layer_count/print_thickness_mm` | `0.08 / 5 / 1.2` |
| `orientation` | `face-up (assembly pose); print pose is art-face-down` |
| `palette_bottom_up` | `["#FFFFFF","#DC143C","#FFE600","#0064F0"]`（RYBW；与 `manifest.palette` 一致） |
| `lumine_geometry` | `color_layers/backing_layers/total_layers/target_pixel_grid/structure` |
| `source` | `file/sha256/bbox_xyxy/source_ellipse_rx_ry`（换图时脚本重算，不要手填） |
| `artifacts/pixel_stats` | PNG sha256；`opaque_pixels=584908`、`opaque_ratio=0.783538`（两版相同） |

> 旧线 Kromacut 的 `layer_counts.bin`（uint16 逐像素层数）**已废弃**；Lumina 线不再生成/读取。

## 5. Lumina 转换与几何契约（`appearance/lumina/lumina_convert.py`）

### 5.1 命令与参数

```bash
cd /data/Documents/projects/SmartCoaster
# 必须用 Lumina venv（cp312 原生轮子）；--manifest-only 只读回归、不转换
/data/Documents/tools/Lumina-Layers/.venv/bin/python \
    appearance/lumina/lumina_convert.py --art dog,elf [--manifest-only]
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--art` / `--out-root` / `--spacer` / `--expect-thickness` | `dog,elf` / `appearance/build/print` / `0.80` / `1.20` | 版本列表 / 输出根 / 背板 mm / 总厚断言 |
| `--lut` / `--color-mode` | `lut-preset/Custom/lumina_lut.json` / `4-Color (RYBW)` | **换 LUT 必须同步 color_mode**；优先 JSON（见 §12 发灰坑） |
| `--quantize` / `--git-head` | `48` / 空 | K-Means 颜色数；发布时传上游 HEAD `eef88023…` |
| `--manifest-only` / `--debug` | off | 跳过转换只校验 / 导出原始 print pose 诊断网格 |

### 5.2 无头集成设计（进程内，不起服务）

- 入口：`sys.path.insert(0, LUMINA)` → `from core.converter import build_image_model_context`；
  **不启动 FastAPI/Electron、不做 GUI 自动化**（`docs/01` §14.4）；转换前校验 PNG 必须正好
  `target_width_mm × 10 = 864` px，否则拒绝（避免 Lumina 二次重采样）；
- 固定调用参数（`PARAMS` + kwargs）：`structure_mode="Single-sided"`、`modeling_mode=HIGH_FIDELITY`、
  `color_layers=5`、`spacer_thick=0.80`、LUT/`color_mode`、`quantize_colors=48`、`smooth_sigma=10`、`blur_kernel=0`、
  `enable_cleanup=True`、relief/cloisonne/outline/coating/fridge-magnet 全关、`separate_backing=False`、
  `backing_color_id=0`（White）、`backing_infill_density_percent=100`、`center_on_bed=True`、
  `printer_id="bambu-h2d"`、`device_profile_id="BambuStudio:bbl:bambu-lab-h2d:0.4"`（H2D，5 色同打）；
- Lumina 返回 `ctx["scene"]`（trimesh，已按床居中、已 X 镜像）：按槽名前缀（`__part_N` 归组）聚合，
  **XY 重新居中到 bbox 中心**，z 从 0 起；再做装配姿态检测（§5.4）→ 刚体变换 → 逐耗材导出 STL + 校验 → manifest。

### 5.3 Lumina 的层结构（print pose）与输出物

```text
z = 1.20  ┌──────────────────────────┐  ← 平背（装配时贴槽底）
          │ Backing 10 层 (0.80 mm)  │     slot 0 = White，100% 实心
z = 0.40  ├──────────────────────────┤
          │ Colour 5 层 (0.40 mm)    │     material_matrix[...,0] = 观赏面
z = 0     └──────────────────────────┘  ← 图案面（贴打印床、第一层）
```

厚度 `T = (color_layers + round(spacer_thick/0.08)) × 0.08`；本线 5+10=15 层 → **1.20 mm**。0.08 是几何常量
（`layer_height_mm` 只影响 LUT 匹配）；平背 = 单面 + relief/cloisonne/coating/fridge-magnet 全关 + `separate_backing=False`。

每个 `appearance/build/print/<art>/` 输出：

| 文件 | 内容 |
|---|---|
| `filament_<n>_<HEX>.stl` | **每耗材一个闭合实体**，assembly pose（图案面 +Z、平背 z=0）；RYBW 各 4 个 |
| `plate_lumina.3mf` / `plate_preview.png` / `.glb` | 原生 3MF（Bambu 元数据、print pose）/ 2D 预测色 / 3D 预览（参考，**非打印几何**） |
| `material_matrix.npy` / `matched_rgb.npy` / `mask_solid.npy` | `(H,W,5)` 色层槽号 / 预测打印色 / 实体掩码 |
| `manifest.json` / `lumina_call.json` | 数据契约（§5.5）/ provenance（入参 + 版本） |

重跑幂等：先删 `filament_*.stl` 再写，manifest/plate_* 覆盖。Lumina 时间戳产物（`art_rgba_Lumina_HiFi_4C_<ts>.3mf`、
`art_rgba_Preview_<ts>.glb`、`*_Debug.png`、`*_color_recipe.txt`、`lumina_stats.txt`）落在 `.lumina_runtime/output`，可定期清理。

### 5.4 print pose → assembly pose（驱动做的刚体变换）

Lumina 导出时施加 **X 镜像**，图案面在 z=0；下游统一用 assembly pose：图案面 **+Z 朝上**、平背 `z=0`、
XY 居中、图像顶 **+Y**。`assembly = (sx·x, sy·y, T − z)`（候选 `flip_x=(-1,+1,-1)` / `flip_y=(+1,-1,-1)`），
同一变换再做一次即逆变换。

`(sx, sy)` **由脚本检测，不静默假设**：RYBW 改用**逐槽体积加权 XY 质心**，两个平面内镜像都打分，胜者须
`rms <= 3.0 mm` 且比次优好 **2.5×**。本机：dog rms **1.7399 mm**/margin **4.17**；elf rms **1.6619 mm**/margin **8.69**；
均 `flip_x`、`assembly_sign=[-1,1,-1]`。

> 圆形 alpha 掩码旋转对称，`flip_x`/`flip_y` 命中率接近，**平面内 180° 朝向仍应人工核对
> `plate_preview.png` / `art_rgba.png`**（首次换图必做）。

### 5.5 数据契约：`manifest.json`（schema `smartcoaster.appearance.print_lumina/v1`）

| 字段 | 内容 / 下游用法 |
|---|---|
| `engine` | `name/root/git_head/license/entry/python`（版本溯源；当前 `git_head` 为空，见 §12） |
| `art` | `name/png/png_sha256/width/height/pixel_size_mm/target_width_mm` |
| `params` | `lut/lut_sha256/color_mode/color_layers/spacer_thick_mm/layer_height_mm/total_layers/quantize_colors/…/printer_id/device_profile_id/backing_*` |
| `geometry` | `orientation/assembly_transform/assembly_sign/thickness_mm/print_thickness_mm/diameter_mm/bbox_mm/orientation_volume_centroid_rms_mm/orientation_margin/orientation_method/image_top_axis` |
| `palette` / `palette_bottom_up` | 槽序 hex；渲染/切片对齐用 |
| `slot_names` / `slot_pixel_counts` | 4 槽名（White/Red/Yellow/Blue）与各槽观赏面像素数 |
| `filament_objects[]` | `number/slot/hex/file/triangles/volume_mm3/sha256/parts/watertight`——**下游按此逐耗材加载 STL 并分配 AMS** |
| `artifacts` | 原生 3MF/预览/矩阵的 `file/bytes/sha256` |
| `lumina_transform_metadata` | `x_mirrored` / `mirror_span_mm`（Lumina 导出侧记录） |
| `runtime_s` / `progress` | 转换耗时 / S01–S12 进度序列 |
| `provenance` | `call_kwargs`（Lumina 全参数）+ `generated_at_utc` + `generator` |
| `validation` | `thickness_ok/diameter_ok/slots_ok/watertight{…}/all_watertight/volume_mm3` |

> 读方必须按 `schema` 分支：旧 Kromacut manifest 没有本 schema；本驱动会**覆盖**同目录旧 manifest。
> `filaments`/`parts` 是为兼容旧读方保留的同内容别名，新代码只用 `filament_objects`。

### 5.6 实测规模（2026-11-08 RYBW 重跑）

| 版本 | 耗材 | 印花三角面 | 原生 3MF | 体积 | 转换耗时 | 姿态 rms / margin |
|---|---|---|---|---|---|---|
| dog（round） | 4（RYBW） | **680,354** | **8,909,141 B（≈8.91 MB）** | 7,018.896 mm³ | 27.66 s | 1.7399 mm / 4.17 |
| elf（square） | 4（RYBW） | **943,734** | **12,105,240 B（≈12.11 MB）** | 7,018.896 mm³ | 38.99 s | 1.6619 mm / 8.69 |

> 与 CMYW 旧值（881,214 / 1,399,980 面、11.60/18.11 MB）不同，几何层数/厚度不变但色层分布变了；
> 两版 4 个逐耗材实体 `all_watertight=true`。`validation.diameter_ok=false` 仍是已知口径缺陷
> （轴对齐 bbox 86.2 vs target 86.4 的浮点边界，几何未漂移）。

## 6. 外壳适配规范（`appearance/cad/`）

### 6.1 开槽定义（唯一参数源 = `appearance/build/shell/shell.json`）

配置：[`appearance/config/lumina_project.yaml`](config/lumina_project.yaml) 的 `versions.{round,square}.shell`。
重建：`bash appearance/cad/run_shell.sh --config appearance/config/lumina_project.yaml`
（输出 `plate_recessed.{step,stl}`、`print_blank_*.stl`、`shell.json`、`parts.json`、`REPORT.md`）。

| 项 | 圆形版（round/LUMEN + dog） | 方形版（square/square_v1 + elf） |
|---|---|---|
| 源顶板（只读导入） | `mechanical/lumen/build/parts/plate_v01.step` | `mechanical/square_v1/build/parts/plate_v01.step` |
| 沿口 rim z / 槽底 floor z | 17.00 / **15.80** | 18.00 / **16.80** |
| 槽直径 / 槽深 | **Ø86.0** / **1.20** | **Ø86.0** / **1.20** |
| 印花顶 z（`top_gap=0`） | **17.00（与沿口齐平）** | **18.00（与沿口齐平）** |
| 槽底以下剩余材料 / 平面度 | 1.80 / 0.000000 mm | 1.80 / 0.000000 mm |

原则：**不要重建顶板**，用 `import_step` + 圆柱布尔差保持已验证几何；只切顶面，不碰裙边/传力柱/内部件。
已通过：导入/切后单实体、`is_valid`、包围盒完全不变（round ±52×±52×6..17，square ±50×±50×6..18）；
槽底平面 `normal=(0,0,1)`、面积 5,808.8048 mm²、深度 r=0/20/40 均 1.20；STEP 回读 1 solid、STL 水密；
内部件最高 z（round 13.4 / square 14.5）均低于槽底。

### 6.2 配合与过盈（名义 vs 实测）

| 参数 | 值 | 说明 |
|---|---|---|
| 印花名义直径 / 槽直径 | **Ø86.2 / Ø86.0** | 轴对齐 bbox / 半径 43.000 |
| 名义径向过盈 | **0.10 mm** | 43.100 − 43.000（`interference_mm`） |
| 实测最大顶点半径 / 最大径向过盈 | **43.219 / 0.219 mm** | 3MF 回读网格的像素台阶角点；`validation.json` |
| 顶面落差 | **0.000 mm** | `top_gap=0`，印花顶与沿口齐平 |

> `PROVISIONAL`：0.10 mm 名义过盈是首版工程假设，需按喷嘴/线宽/材料收缩与实物压配标定；
> 0.219 mm 是网格台阶的**上界**，不是所有方向的实际过盈。

### 6.3 放置变换（3MF / Blender / 打印交付共用）与功能缺口

印花 STL 本地坐标：XY 居中 `[-43.1, 43.1]`、底面 `z=0`、顶面 `z=1.20`；装配
`translate (0, 0, floor_z)`，**无旋转**；图像顶部 = **+Y**（前脸 −Y）；`shell.json` 是唯一数值来源。

**`PROVISIONAL` 功能缺口**：开槽把顶板局部厚度从 3.0 减到 **1.80 mm**；**没有重跑**
`mechanical/*/cad/verify_v01.py`（21 项）与 FEA（顶板 B / 整机 C）。顶板是称重浮动板，刚度、传力路径、
过载限位、跌落行为均**未验证**。打样前必须补：① 开槽顶板 FEA（中心/偏载 r=30/45）；② 21 项功能自检；
③ 实物称重/温漂/回差标定。

### 6.4 源模型缺陷（已记录，未改源）

`mechanical/lumen/build/parts/plate_v01.step` 是 **2-shell 实体**，内含封闭锥形空腔
（apex z=16.100 / ceiling z=16.700 / R48 / 1,447.6459 mm³），顶面实际是 z=17.0 平面。切槽会在槽壁
z 16.6375..16.7000（高 **0.0625 mm**）开一圈亚喷嘴环缝。主交付保留**忠实切法** `round/plate_recessed.*`；
另出**填实空腔**的 `round/plate_recessed_clean.*`（外形/包围盒/顶面轮廓不变，壁带干净）；
建议在上游 `<mechanical/lumen>` 修复（本项目对 `mechanical/**` 只读）。

## 7. 渲染与装配 3MF（`appearance/render/`）

### 7.1 场景结构（外壳与印花保持分离）

```text
round/scene.blend     SHELL_ROUND battery…plate（11 件，含开槽顶板）
                      PRINT_ART_DOG  ART_DOG_00..03（4 耗材对象）+ PRINT_FACE_DOG（RENDER-ONLY）
square/scene.blend    SHELL_SQUARE 12 件（含 button / screen_ui）；PRINT_ART_ELF 同上
```

- **没有 join/boolean/父子关系**；`scene_section.blend` 只是渲染用 1/4 剖切副本；CMF 用 `render/appearance/styles.json`
  的 **`bambu_pla_basic_rybw_black`**（壳/顶板/按键 `#101010`）；印花实体按 manifest hex 上色、展示面由 overlay 覆盖（§7.2）。

### 7.2 RENDER-ONLY 预测色 overlay（为什么需要）

Lumina 用半透明 0.08 mm 耗材叠层混色，**可见色 ≠ 最顶层耗材的纯色**（如粉色 = White+Red 叠层），按纯色渲染会错。
`build_scene.py` 的 `add_print_face()` 在印花顶面加薄圆盘 `PRINT_FACE_<ART>`：纹理来自 `matched_rgb.npy`
（`mask_solid.npy` 向外 bleed 6 轮），写成 `appearance/build/render/<v>/print_face_<art>.png`（864×864）；
对象名 **`PRINT_FACE_DOG` / `PRINT_FACE_ELF`**，登记在 `scene_info.json.render_only_objects`。

圆盘半径 = 印花名义半径 43.1 mm，位于印花顶面上方 **30 µm**，`Closest` 插值、`EXTEND` 边缘、sRGB、**关闭阴影**
（避免与槽沿 z-fighting/彩色发丝）。**它不是实物几何**：不在 3MF、不在打印 STL 交付里；section 只保留它看图。
渲染图回答"预期打印出来是什么颜色"；打印交付回答"实际要打哪些几何"——两者不能混。

### 7.3 渲染清单（每版 5 张 + 总对比板）

| 文件 | 内容 | 规格 |
|---|---|---|
| `appearance/render/{round,square}/{hero,top,print_top}.png` | 3/4 主图 / 正交俯视 / 印花单独俯视 | 1000²，48 spp |
| `.../{macro_edge,section_exploded}.png` | 印花边缘微距 / 1/4 剖面 + 爆炸 + 配合数值 | 1600² 64 spp / 2400×1200（raw 1200×1000 面板合成） |
| `appearance/render/board.png` | 两版对比板 | 2276×2406 |

Blender **4.5.3 LTS / Cycles CPU / AgX / denoise**；每版另有 `.blend`、`scene_info.json`、`annotations.json`，
实测 `warnings=[]`/`mismatches=[]`。方法见 [`RENDER_HOWTO.md`](RENDER_HOWTO.md)（旧内容为 Kromacut 线；数值以 `scene_info` 为准）。

### 7.4 装配 3MF（`appearance/build/3mf/`，Bambu Studio 查看用）

`appearance/render/make_3mf.py` 生成**装配姿态** 3MF（单位 mm，core spec）：`basematerials` 每零件/每耗材一个；
外壳零件各自成 object；印花 = 1 个装配 object `PRINT_ART_<art>` + 4 个耗材 component；
`<build>` 里印花平移 `z = 15.80 / 16.80`（槽底），外壳零件在原生装配位姿。

- 回读 `validation.json`（2026-11-08 RYBW）：两版 `ok:true`、`errors:[]`；round 16 objects / 12 build items /
  **721,616** 面（印花 680,354）、square 17 / 13 / **988,820** 面（印花 943,734）；bbox 110×110×17 / 100×100×18；
  `print_top_vs_rim_mm = 0.0`、`actual_max_interference_mm = 0.219`；壳/顶板材料色 **`#101010FF`（黑）**、
  4 个印花材料色 = RYBW；
- **不写** Bambu 专有 `Metadata/model_settings.config`（AMS 槽位由用户分配）；该 3MF 是数字样机/查看用，
  **不是**可直接切片的床面排版件（后者见 §8）。

### 7.5 Bambu Studio 操作步骤（用户侧，本机未验证）

导入 `appearance/build/3mf/{round|square}.3mf` 检查装配/CMF；切片改用 `render/print/stl/<v>/PRINT_READY.3mf`；
给 4 个印花对象分配 RYBW 槽位、黑壳/顶板/按键用 Black 槽，逐层预览；切片 → 打印 → 整体翻面。不要整体缩放或镜像印花（会破坏 0.219 mm
过盈与齐平关系）。

## 8. 打印交付规范（`render/print/stl/`，管线最后一步）

> 完整独立旧规范 [`PRINT_DELIVERY_SPEC.md`](PRINT_DELIVERY_SPEC.md) 是 **v2.0 Kromacut 口径**
> （6/7 耗材、0.05 mm 顶差、槽底 1.25/1.45）——Lumina 线以本节 + 实际 `manifest.json`/`layout.json` 为准。

### 8.1 交付目录（按外壳分类，一个根目录）

```text
render/print/stl/            # CMF：黑壳/黑顶板/黑按键 #101010（Bambu PLA Basic Black）
├── README.md · delivery.json · PRINT_SHEET_BOTH.png（2400×1250）
├── round/   6 STL：shell · plate_recessed · print_filament_1_FFFFFF … _4_F4EE2A
│            + PRINT_READY.3mf · PRINT_ONLY_LUMINA.3mf · PRINT_SHEET/print_iso/print_top.png
│            + layout.json · manifest.json · README.md · CHECKSUMS.sha256
└── square/  7 STL（多 button.stl），其余同上
```

- **每版交付 16 / 17 个文件**（round / square，含 6 / 7 个 STL）；RYBW 重跑后**共 13 个 STL / 84.53 MB**
  （圆 35.59 / 方 48.94 MB）；目录体积 **53.69 / 71.55 MB**；`CHECKSUMS.sha256` 覆盖目录内其余文件（已含 `print_bottom.png`）；
  根另有 `README.md`、`delivery.json`、`PRINT_SHEET_BOTH.png`；
- 当前快照目录含 `print_bottom.png`（1400×1000，`make_bottom_view.py` 的"从床下看第一层"证明图），
  已纳入 `CHECKSUMS.sha256`；版本 `manifest.json` / `README.md` 的文件清单文本尚未列入该图（已知文档债）。

### 8.2 打印姿态（硬断言，已由 STL 烘焙）

| 项 | round | square |
|---|---|---|
| 顶板原始顶面（外表面）贴床 | ≈ **0.000** mm | ≈ **0.000** mm |
| 槽底 z（= 印花背面） | **1.20 mm** | **1.20 mm** |
| 印花正面（第一层） | **0.00 mm** | **0.00 mm** |
| 印花厚度 | 1.20 mm | 1.20 mm |
| 按键 / 支撑 | — / **无需** | 平躺 **9.0 × 8.997 × 5.2 mm**，可见面朝下 / **无需** |
| 在床件严格 z=0 | 壳/顶板/白/红 min z=0 | 壳/顶板/按钮/白 min z=0 |
| 印花逐耗材起始层 | White 0.00 / Blue 0.08 / Yellow 0.16 / Red 0.00 mm | White 0.00 / Red 0.16 / Yellow 0.16 / Blue 0.08 mm |
| 床面占用（220×220） | **218.9354 × 109.995 × 13.4** | **208.0 × 113.9972 × 14.5** |

严格变换（行向量 `v' = v·Rᵀ + t`，mm；排版阶段另加 XY 平移）：`shell` = 单位阵（底朝下）；
`plate` = `diag(1,−1,−1)`（绕 X 180°，t z=17.0 / 18.0）；`print` 同 `diag(1,−1,−1)`（t z=1.2）；
`button` = 绕 X +90°，厚度轴 Z、可见正面朝下。每个交付 STL：三角数/体积与源一致、
bbox = 刚性旋转后的源 bbox；**印花组 min z = 0**（单个耗材可从 0.08/0.16 mm 层开始，不代表悬空）。

### 8.3 床面排版与两条路线

单元 = `shell`（底朝下）+ `plate_unit`（翻面顶板 + 4 印花）；方形另有 `button` 平躺。规则：bbox ≤ 220×220、
所有零件 min z = 0、任意两单元间距 ≥ 5 mm、不越界/不重叠；round shell↔plate_unit 间距 **5.0 mm**，
square 为 **8.0 / 5.0 / 5.0 mm**（`layout.json` 全 true）。

- **路线 A（推荐）**：`PRINT_READY.3mf` 同盘打印——第一层 = 图案 + 沿口，看到印花背面（正确），翻面即成品，**无需支撑**；
- **路线 B（备选）**：顶板与印花分开打印（顶板仍凹槽朝下），取出后压配/点胶。

### 8.4 两个 3MF 与打印参数

| 文件 | 姿态 | 用途 |
|---|---|---|
| `render/print/stl/<v>/PRINT_READY.3mf` | 打印姿态 + 床面排版 | **可直接切片**；round 7 objects/3 build items/**711,848** 面（6,259,708 B）；square 8/4/**978,816** 面（8,603,575 B） |
| `appearance/build/3mf/<v>.3mf` | 装配姿态 | 数字样机（只查看，不直接切片） |
| `render/print/stl/<v>/PRINT_ONLY_LUMINA.3mf` | Lumina print pose | 原生引擎 3MF（Bambu 元数据），与 `plate_lumina.3mf` **逐字节相同**；按 256 床中心摆放，**不能**替代同盘排版件 |

| 参数 | 建议值（`PROVISIONAL` 起始） |
|---|---|
| 层高 / 喷嘴 / 线宽 | **0.08 mm**（颜色层必须 0.08；同盘外壳也按 0.08）/ 0.40 / ≈0.45 mm |
| 墙/顶层/底层/填充；支撑 | 2 / 4 / 3 / 15%；**无**（路线 A，顶板原顶面 + 图案面共面于床） |
| 耗材/AMS | 印花 4 槽 RYBW + 黑壳/顶板/按键 1 槽 Black = **5 卷**；**H2D 同打 5 色，一次成型**（Green spare 不参与） |

> **STL 不带材料信息**：4 个 `print_filament_*` 必须同时导入并逐对象分配 AMS；推荐直接用 `PRINT_READY.3mf`。
> 每版目录内 `cd render/print/stl/<v> && sha256sum -c CHECKSUMS.sha256` 可复核。

## 9. 验收门槛、证据与复现

### 9.1 门槛与实际（Lumina 线，已核对产物）

| 阶段 | 门槛 | 实际 / 证据 |
|---|---|---|
| 引擎/素材 | 3.12.16 venv、6 依赖可导入、HEAD/LUT 可追溯；864² RGBA、alpha 正确 | 6 imports OK；HEAD `eef88023`；LUT `bad3054b…`（JSON）；`art.json` + `--check` |
| 印花几何 | 4 槽 RYBW、厚度 1.20、逐耗材 watertight、姿态 rms≤3 mm | dog/elf `all_watertight=true`，rms 1.7399/1.6619 mm（§5.6） |
| 外壳/配合/3MF | 单实体、bbox 不变、槽底平面度 0、槽深 1.20；过盈 0.1 名义 / 0.219 上界；3MF 结构/材料色/Z/bbox 回读 | `shell.json` §6、`3mf/validation.json` 两版 `ok:true`、`errors:[]` |
| 渲染 | 每版 5 图 + board、非空、场景分离、overlay 记录且非交付几何；CMF 黑壳 | `appearance/render/*/scene_info.json`、`RENDER_LOG.md` |
| 打印交付 | 姿态断言全 true、床面 ≤220、间距 ≥5、刚体等价、3MF 回读、CHECKSUMS、**印花组 min z=0** | `<v>/layout.json` 12/12 true；`stl_delivery.print_min_z_mm`、`all_min_z_zero=true`；manifest、CHECKSUMS |
| 一键/验收 | `compile_lumina.py` 全阶段 + 报告；Lumina 验收 | dry-run **46/46 PASS**（RYBW/LUT/H2D/5 色/黑壳）；独立验收 **194/194 PASS**（`ACCEPTANCE.json`，CMYW 183 项已作废） |

### 9.2 复现（一条命令 + 分阶段）

```bash
cd /data/Documents/projects/SmartCoaster
bash appearance/compile.sh --dry-run && bash appearance/compile.sh   # ≈10–12 min；dry-run 46/46
# 等价分阶段：
python3 appearance/tools/make_art_lumina.py
/data/Documents/tools/Lumina-Layers/.venv/bin/python appearance/lumina/lumina_convert.py --art dog,elf
bash appearance/cad/run_shell.sh --config appearance/config/lumina_project.yaml
bash appearance/render/run_all.sh
bash render/print/appearance/run_print_stage.sh
python3 appearance/tools/acceptance_check_lumina.py        # 只读验收；项数以 ACCEPTANCE.json 为准
```

环境：CPython 3.12.16 venv、build123d 0.10.0（project venv）、Blender 4.5.3；Lumina 源码/venv/运行产物不入库（`.lumina_runtime/` 已 gitignore）。

## 10. 快速改动指南（换图 / 换色 / 换尺寸）

| 想换什么 | 改哪里 | 必须同步 |
|---|---|---|
| 换插画 | `appearance/src/surface.png` + `make_art_lumina.py` 的 `ARTS` bbox（或 `surface` 路径） | 重跑素材 + 转换；检查 `plate_preview.png` 朝向 |
| 换画幅/尺寸 | `make_art_lumina.py` 的 `N`/`FRAME_MM`、`lumina_project.yaml` 的 `art.frame_mm`、驱动 `PARAMS.target_width_mm` | 三处一致；`N = target_mm × 10`；**外壳槽径/槽深同步** |
| 换厚度/换 4 色 | `--spacer` 或 `PARAMS.spacer_thick_mm`；替换 `lut` + 同步 `--color-mode`（当前 JSON RYBW） | 总厚/槽深联动；槽位数与 LUT palette 匹配；5 色预算/AMS 重分配 |
| 上 6/8 色 | 换 JSON LUT + `color_mode` + 色层数/总厚 | H2D 同打上限 5 色；**必须先自建校准 LUT**（§12）；外壳/槽深/AMS 全部联动 |
| 换外壳 | `lumina_project.yaml` 的 `versions.*.shell`（STEP/rim/槽径/印花径/过盈/top_gap） | 重跑 shell → render → 3mf → print；过盈需重新标定 |

> 颜色/尺寸/厚度是**几何契约**：任何一项变化都会同时改印花 STL、外壳槽、3MF 和打印交付，不要只改一处；
> 换图后首件务必看 `plate_preview.png` 与 `art_rgba.png` 的朝向/镜像是否一致。

## 11. 失败模式与排错（本轮踩过的坑）

| 现象 | 根因 | 处置 |
|---|---|---|
| `ModuleNotFoundError: lumina_svg_core / neroued_3mf / fatcat_metadata` | 用错解释器或 venv 依赖没装齐 | 必须用 `Lumina-Layers/.venv/bin/python`；按 §3.2 重装 |
| pip 平台/版本不匹配 / `~/.cache/pip` 不可写 | 非 cp312–314、glibc < 2.28、缓存归属 | 用 `python312`；`PIP_CACHE_DIR/TMPDIR` 指到 `/data/Documents/tools/` |
| `EPERM` 在 `Lumina/output`/`materials` | 符号链接丢失/目标不可写（`import config` 创建目录） | 重建 §3.1 符号链接；确认 `.lumina_runtime` 可写；**不要删链接** |
| `art PNG is WxH but target_width_mm=… needs NxN` | PNG 网格 ≠ `target_mm × 10` | 重跑 `make_art_lumina.py`；三处尺寸同步（§10） |
| `could not establish assembly orientation` | 体积质心 rms > 3 mm 或优势 < 2.5×：图太对称/床心平移 | 看 per-slot 质心；用 `plate_preview.png` 人工核对；低反差图提高对比度/换 LUT |
| `some filament meshes are not watertight` | 几何不闭合（脚本主动失败） | 不要重焊/去重三角面；查引擎版本与输入图；必要时降分辨率 |
| **整图发灰、白不够白** | 用了无 palette hex 的 `.npy` LUT | 换 `lut-preset/Custom/lumina_lut.json`（JSON，白=255）；`bambulab_pla_basic_rybw.npy` 白预测 `[215,210,207]`，不要用 |
| 紫色变蓝/白、粉色偏红 | RYBW 无品红，色域不够 | 换不含紫的图，或加青+品红两卷回 CMYW（仍 5 色） |
| 印花变椭圆/尺寸偏；切片看不到图案 | 源图是略扁椭圆；打印姿态看到印花**背面**（正常） | 按椭圆包围盒重采样回正圆（§4.2）；顶板+印花整体翻面同盘打印，打完整体翻面 |
| STL 只有单色/缺件；按钮站着打印 | STL 不带材料信息；按键未翻 | 4 个逐耗材 STL 同导入并逐对象分配 AMS；按钮绕 X +90° 躺平（厚度轴 Z，可见面朝下） |
| 渲染颜色与实物不像；磁盘快速上涨/新旧混放 | overlay 不是实物；时间戳产物累积；旧文件同目录 | 打小样校准；清 `.lumina_runtime/output`；看 `params.lut`/`slot_names` 区分 |

## 12. 已知限制与未验证项（不得写成已通过）

**未验证（实物/切片）**：Bambu Studio 实际导入、AMS 映射、逐层切片与打印路径（本机未装）；
实物颜色（LUT 预测 ≠ 实物色）、层厚、过盈结合强度、耐热、清洁性；开槽顶板刚度/FEA、21 项功能自检；
打印姿态与 0.219 mm 最大过盈的实物配合、翻面平整度。

**引擎/数据契约缺陷（已知，未修）**

- `manifest.validation.diameter_ok=false`：驱动用 `abs(dia − target_width_mm) <= 0.2`，`dia` 是轴对齐 bbox 86.2、
  `target_width_mm` 是 86.4，差值 0.2000000000000028 触发浮点边界。**实际几何没有漂移**（§5.6/§6.2），
  需把阈值/口径改为"bbox vs 名义印花径"再复跑；`manifest.engine.git_head` 为空（转换未传 `--git-head`），
  发布前应传上游 HEAD `eef88023…`；
- **LUT 发灰坑（重要）**：`bambulab_pla_basic_rybw.npy` 实测不可用——纯白叠层预测仅 `[215,210,207]`，整图发灰；
  改用自描述 **Keyed-JSON** `lut-preset/Custom/lumina_lut.json`（palette 带 hex，白=255）后预览接近源图。
  **优先用带 palette hex 的 JSON LUT**，不要用无 hex 的 npy；预测色仍需实物打样校准；
- 6/8 色能力**受限**：当前 RYBW 4 色；H2D 同打上限 5 色，且没有可用的 Bambu 6 色校准 LUT；6/8 色需自建校准 LUT，
  `lut-preset/Custom/` 下来源不明 npy 不要直接用；Green `#00AE42` 备用、不参与本版。
- **RYBW 色域限制（务必知悉）**：没有品红 → elf 的薰衣草紫背景无法还原（被匹配成蓝/白，粉色偏红）；dog 表现好。
  若必须保紫色：加青+品红两卷回到 CMYW（仍 5 色、H2D 可同打），或换不含紫的插画；不要靠调 LUT 硬凑。
- `plate_preview.glb` 是**预览几何，不是打印体**，不能当几何源；0.08 mm 层高是几何常量：颜色层必须 0.08，
  同盘打印外壳也必须 0.08，否则走路线 B（外壳 0.20 单独打）；
- 4 个印花耗材（RYBW）+ 1 个外壳/顶板/按键耗材（Black）= **5 卷**，正好用满 H2D 的 5 色同打；Green `#00AE42` 备用不参与本版；若换成 6 色则超出 H2D 同打预算，需换色/分盘或自建 LUT。

**源模型/文档债**：LUMEN 顶板 STEP 的封闭空腔缺陷（§6.4）未在上游修复，`plate_recessed_clean.*` 只是外观替代件；
`shell.json` 的 `notes/provisional` 文本仍夹带 Kromacut 旧口径（0.05 mm 顶差、0.2 mm 过盈、1.25/1.45 槽深），
**以 `round/square` 数值段为准**；`PRINT_DELIVERY_SPEC.md`（v2.0）、`RENDER_HOWTO.md`、`INPUTS.md`、`AGENT_PROMPT.md`、
`appearance/tools/compile.py`、`appearance/config/appearance_project.yaml` 仍是 Kromacut 线；
`render/print/stl/<v>/manifest.json` 的 `parts[].material` 文本仍写 lumen_violet 旧 hex，实际 3MF/交付 STL
已是黑壳 `#101010`——**以 `files.print_ready_3mf.materials` / `files.stl_files[].material_hex` 为准**；
`render/print/stl/<v>/{manifest.json,README.md}` 文件清单尚未列入 `print_bottom.png`（CHECKSUMS 已含）；
H2D 双喷头/5 色同打、黑壳 CMF 与 5 卷预算均为**用户侧工艺假设，实物未验证**。

**风险**：三角面/文件体积可能仍偏大（以 RYBW 重跑后的 `du`/manifest 为准），切片器导入较慢，降规模须同步改像素/尺寸/槽径；换图/换色/换尺寸会连锁改外壳与 AMS，不要把 Lumina 输出当作与外壳无关的贴纸。

## 13. OBSOLETE 归档：Kromacut Flat Paint 线（仅历史/回退参考）

> 状态：**OBSOLETE（2026-11-07 起）**。下述事实保留用于追溯，不再用于新交付；旧脚本/产物仍在仓库中，但参数、schema、验收基线都**不适用于 Lumina 线**。
> 另：2026-11-08 起，Lumina 的 CMYW 配色也已**退役**，现行配色为 **RYBW + Black 黑壳 / H2D 5 色**（见 §4.4/§8.5）。

| 项 | 旧线事实（已归档） |
|---|---|
| 引擎/接入/素材 | Kromacut 4.2.0：AppImage 解包 `/data/Documents/tools/Kromacut/app`（免 FUSE）+ `src/Kromacut-4.2.0`；headless 桥接 `tools/kromacut-flatpaint.mjs`（Vite SSR，无官方 CLI）；Node 24.15.0 + three 0.180.0 / jszip 3.10.1 / vite 7.1.2；AGPL-3.0；素材/几何 | `make_art.py`：576×576 @ **0.15 mm/px**，画幅 86.4、印花 Ø86.37，CIELAB 量化到 6/7 色 + 去噪 + `layer_counts.bin`；Flat Paint face-up：dog 6 色 × 0.20 = **1.20 mm**、elf 7 色 × 0.20 = **1.40 mm** |
| 三角面/3MF | dog **1,941,732** 面 / 19.7 MB；elf **2,500,540** 面 / 25.6 MB |
| 外壳旧口径 | 槽 Ø86.0；名义印花 Ø86.4、过盈 0.20 mm、实测最大 0.288 mm；top_gap 0.05 mm；槽底 round 15.75 / square 16.55；槽深 1.25 / 1.45 |
| 渲染/3MF/交付 | 6/7 耗材对象；装配 3MF `appearance/build/3mf/{dog,elf}_kromacut.3mf` 仍作参考副本；旧打印交付 18 个 STL（round 8 / square 10），已被 Lumina 4 色交付覆盖 |
| 验收/旧命令 | 140/140 PASS（2026-11-07 07:40，已被 194 项 Lumina 验收覆盖，**不可引用为本线通过**）；旧命令 `install_kromacut.sh` / `make_art.py` / `kromacut/run_convert.sh` / 旧 `compile.sh`（曾 exec `compile.py`）勿再用于交付；换线原因见 §1.1 |

旧线目录：`appearance/kromacut/`、`appearance/tools/{make_art.py,install_kromacut.sh}`、`appearance/config/appearance_project.yaml`、
`appearance/build/print/REPORT.md`。**回退仅作历史参考**：不要新旧产物混用（看 `manifest.json.schema` 区分）。

## 14. 目录与交付索引

```text
appearance/          src/ · tools/{make_art_lumina.py,compile_lumina.py,acceptance_check.py}
                     lumina/lumina_convert.py（现行驱动） · config/lumina_project.yaml（唯一配置）
                     cad/（开槽） · render/（场景/渲染/3MF/board） · build/{art,print,shell,3mf,render}/
LUT               /data/Documents/tools/Lumina-Layers/lut-preset/Custom/lumina_lut.json（RYBW Keyed-JSON）
render/print/stl/    打印交付（唯一交付根；按 round/square 分类）
render/print/appearance/  交付脚本（只放脚本，不放资产）
appearance/PRINT_DELIVERY_SPEC.md / RENDER_HOWTO.md   旧线规范/渲染方法（历史；Lumina 以本页 §7–§8 为准）
docs/15_Lumina_Layers_Guide.md                        引擎独立入门/用法（安装/参数/排错）
```

外部门入口：`/data/Documents/tools/Lumina-Layers`（引擎）、上游 `LICENSING.md` / `OUTPUT-TERMS`、
[`docs/15`](../docs/15_Lumina_Layers_Guide.md) §10。大二进制（STL/STEP/3MF/blend/npy）由脚本可再生成，默认不入 git
（见根 `.gitignore`）；交付时保留在工作区，按 §9.2 命令复跑即可重建。
