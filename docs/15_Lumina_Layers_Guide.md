# Lumina-Layers 外观打印引擎指南（Lumina Studio 2.0）

> 版本 v1.0（2026-11-07） · 状态：**现行**（替代 `appearance/kromacut/` Kromacut Flat Paint 线）
> 读者：AI agent / 工程师。目标：一张插画 PNG → **无头**产出已知厚度、平背、多材料、可直接进 Bambu Studio 与外壳同盘打印的"印花板"。
> 配套：[`.scratch/LUMINA_SPEC.md`](../.scratch/LUMINA_SPEC.md)（file:line 证据）、[`lumina_convert.py`](../appearance/lumina/lumina_convert.py)、[`lumina_project.yaml`](../appearance/config/lumina_project.yaml)、[docs/01](01_AI_Hardware_Engineering_Pipeline.md) §17（旧 Kromacut 描述，**以本页为准**）。

---

## 0. 快速开始

```bash
cd /data/Documents/projects/SmartCoaster
# 1) 素材：surface.png -> appearance/build/art/{dog,elf}/art_rgba.png (864x864, 86.4 mm)
python3 appearance/tools/make_art_lumina.py
# 2) 引擎：Lumina-Layers headless -> appearance/build/print/{dog,elf}/
/data/Documents/tools/Lumina-Layers/.venv/bin/python appearance/lumina/lumina_convert.py --art dog,elf
# 3) 只读校验已有结果（不重跑转换）
/data/Documents/tools/Lumina-Layers/.venv/bin/python appearance/lumina/lumina_convert.py --art dog,elf --manifest-only
```

> 本机状态（2026-11-07 22:5x 复测）：CPython 3.12.16 + venv，`requirements.txt` 依赖**已装齐**（§3.4 六项全 OK）；art 输入已生成且 `--check` 通过。
> `.lumina_runtime/output/` 已有一次**直接调用引擎**的冒烟产物（3MF/GLB/预览/配方 txt）；但走驱动的 `appearance/build/print/` 与 Bambu 切片/实物打印**尚未验证**。

---

## 1. 它是什么 / 为什么换掉 Kromacut

**Lumina-Layers 即 Lumina Studio 2.0 的开源实现**（Python + FastAPI 后端、React 前端、Electron 外壳；
上游 <https://github.com/lumina-layer-studio/Lumina-Layers>，本地 `/data/Documents/tools/Lumina-Layers`）。
它用实测校准 LUT 把每个像素匹配成"几层不同耗材叠起来混出什么颜色"的配方，再拼成逐耗材闭合几何，
写成带 Bambu 工程元数据的 3MF。本项目**只调用 core 转换库**（`core.converter.build_image_model_context`），
不开服务、不开 Electron、不做 GUI 自动化（与 `docs/01` §14.4 一致）。

### 1.1 旧线（Kromacut）的问题

| 维度 | Kromacut Flat Paint（旧） | Lumina-Layers（现） |
| --- | --- | --- |
| 配色原理 | 图片先量化成**逐色板**（每色一层） | **光学叠层混色**：实测 LUT 决定 5 层耗材叠放配方 |
| 耗材数 | dog 6 卷 / elf 7 卷（旧报告实测） | **4 卷**（White/Cyan/Magenta/Yellow） |
| 输入网格 | 576 px @ 0.15 mm/px | **864 px @ 0.10 mm/px** |
| 切片负担 | 逐色几何，水彩碎片化；三角面 1.94M/2.50M、3MF 19.7/25.6 MB | 4 个耗材对象；本机一次冒烟实测约 88 万三角面、3MF 11.6 MB |
| 许可 | AGPL-3.0（只调用不修改） | **AGPL-3.0-only**（只调用不修改） |

换线原因（工程决策，**不是**许可原因——两条线都是 AGPL）：① 旧线"逐色几何"路线切片碎片多、
逐耗材 STL/AMS 负担重（旧线水彩碎片化、1.94M/2.50M 三角面），Lumina 用 4 卷光学混色取代逐色量化；
② 4 色正好占满 X1C 单台 AMS（旧线 6–7 色必须加 AMS/换料）；③ 一套几何契约（5 色层 + 10 背层 =
1.20 mm）取代两套；④ 上游是活跃的 2.0 项目，有 cp312 预编译轮子、可无头调用。

### 1.2 许可要点（事实陈述，非法律意见）

- 软件主体 **AGPL-3.0-only**（`LICENSING.md`；运行时依赖 `lumina-svg-core==0.3.4` 同为 AGPL-3.0-only）。
- 生成物另有 [OUTPUT-TERMS](https://github.com/lumina-layer-studio/Lumina-Layers/blob/main/OUTPUT-TERMS.md)：
  个人非商业自用免署名；**商业销售/公开分享生成物需标注 "Generated with Lumina-Layers / 由 Lumina-Layers 生成"**。
- 本项目**只调用、不修改、不把 Lumina 代码嵌入发布物**；若分发修改版/组合程序需履行 AGPL 对应源码义务，
  需要闭源集成或署名豁免时联系上游取得书面授权。

---

## 2. 能力边界

**能做**：光栅插画（PNG/JPEG，透明背景）→ 多材料平面件（每耗材一个闭合实体 + 一个 Bambu 原生 3MF）；
4 色 CMYW 光学混色、固定 0.10 mm/px 高保真网格、单面结构（颜色面贴床 + 平背）、圆/方外形由 alpha 决定；
厚度 `(color_layers + round(spacer/0.08)) × 0.08 mm`，当前恒为 **1.20 mm**。

**不做**：外壳开槽/CAD 布尔（`appearance/cad/`）、印花与外壳**融合**（Bambu Studio 切片阶段完成）、
装配/渲染（`appearance/render/`，Blender 4.5.3）、切片/G-code/打印结果保证、无校准上 6/8 色、曲面贴图。

---

## 3. 安装（本机实际）

| 组件 | 本机实际值 |
| --- | --- |
| 引擎源码 | `/data/Documents/tools/Lumina-Layers`，HEAD `eef88023`（2026-11-07，上游 main） |
| 解释器 | **独立 CPython 3.12.16**：`/data/Documents/tools/python312/bin/python3.12`（python-build-standalone） |
| 虚拟环境 | `/data/Documents/tools/Lumina-Layers/.venv`（`home=/data/Documents/tools/python312`，3.12.16） |
| LUT（4 色 CMYW） | `lut-preset/bambulab/bambulab_pla_basic_cmyw.npy`（1024 色，sha256 `950e1008…f7309`） |
| 输出/耗材目录 | `Lumina/output → SmartCoaster/.lumina_runtime/output`、`Lumina/materials → …/.lumina_runtime/materials`（符号链接，`.lumina_runtime/` 已 gitignore） |
| GUI（可选） | Node.js v24.15.0；上游要求 **pnpm 10.33.2**（本机 `pnpm 12.16.1`，见 §3.5） |

### 3.1 为什么必须单独装 Python 3.12

系统只有 Python 3.10；上游 `requirements.txt` 用 `--only-binary` 钉死 4 个原生包，其中
`lumina-svg-core==0.3.4`、`fatcat-metadata==0.1.5` 在 PyPI 上**只发布 cp312/cp313/cp314 轮子**
（`lumina-svg-core` 元数据 `requires_python>=3.12,<3.15`），3.10/3.11 装不上。Linux 要求 glibc ≥ 2.28
（本机 2.35，满足）。这就是"独立 Python 3.12"的唯一原因。

### 3.2 重装 / 换机步骤

```bash
TOOLS=/data/Documents/tools; PY=$TOOLS/python312; LUM=$TOOLS/Lumina-Layers
export TMPDIR=$TOOLS/.tmp PIP_CACHE_DIR=$TOOLS/.pip-cache XDG_CACHE_HOME=$TOOLS/.cache
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$XDG_CACHE_HOME"            # ~/.cache/pip 可能不可写
"$PY/bin/python3.12" -V                                          # 期望 Python 3.12.16
"$PY/bin/python3.12" -m venv "$LUM/.venv"
"$LUM/.venv/bin/python" -m pip install --upgrade pip wheel setuptools
"$LUM/.venv/bin/python" -m pip install -r "$LUM/requirements.txt"
mkdir -p /data/Documents/projects/SmartCoaster/.lumina_runtime/output/{models,temp} \
         /data/Documents/projects/SmartCoaster/.lumina_runtime/materials
ln -sfn /data/Documents/projects/SmartCoaster/.lumina_runtime/output    "$LUM/output"
ln -sfn /data/Documents/projects/SmartCoaster/.lumina_runtime/materials "$LUM/materials"
```

Python 3.12 用 python-build-standalone 安装（首次记录见 `.scratch/install_lumina.sh`，临时目录不入库）；
URL 形如 `…/20261026/cpython-3.12.16+20261026-x86_64-unknown-linux-gnu-install_only.tar.gz`。
驱动每次运行前会 `setdefault` 离线变量，无需手工 export。

### 3.3 离线设置（无遥测、无云库）

驱动在 import Lumina 前设置：`LUMINA_MATERIAL_REGISTRY_URL=""`、`LUMINA_LUT_REGISTRY_URL=""`、
`LUMINA_FEEDBACK_SERVER_URL="off"`、`LUMINA_MATERIAL_SYNC_STARTUP_REFRESH=false`、
`LUMINA_MATERIAL_SYNC_REFRESH_INTERVAL_S=0`、`LUMINA_BACKEND=memory`、`LUMINA_TELEMETRY=0`、
`PYTHONDONTWRITEBYTECODE=1`。**绕过驱动**直接 import Lumina 的脚本请自行设置同一组变量
（否则可能读到 `.env.local` 里的联网配置）。

### 3.4 安装校验（必须全 OK）

```bash
LUMINA=/data/Documents/tools/Lumina-Layers; PY=$LUMINA/.venv/bin/python
cd /data/Documents/projects/SmartCoaster
"$PY" -V                                                   # 期望 3.12.16
"$PY" -c "import lumina_svg_core, neroued_3mf, fatcat_metadata, trimesh, cv2, numpy; print('deps ok')"
readlink -f "$LUMINA/output" "$LUMINA/materials"           # 期望落在 SmartCoaster/.lumina_runtime/*
test -w "$LUMINA/output/models" && echo output-writable
sha256sum "$LUMINA/lut-preset/bambulab/bambulab_pla_basic_cmyw.npy"   # 950e1008…f7309
python3 appearance/tools/make_art_lumina.py --check        # 期望 OK dog / OK elf
```

> 2026-11-07 22:5x 实测：六项全部 OK（此前依赖未装齐属安装中断，已补装）。任何一项失败先修环境，再跑 §0。

### 3.5 GUI（可选，日常不需要）

```bash
cd /data/Documents/tools/Lumina-Layers
.venv/bin/python start_all.py      # 前端 http://localhost:4174 + 后端 :8000（需前端依赖）
.venv/bin/python api_server.py     # 只要后端 :8000
.venv/bin/python start_all.py --kill
```

GUI 需 `pnpm --dir frontend install --frozen-lockfile` 且 pnpm **10.33.2**
（`corepack prepare pnpm@10.33.2 --activate`；本机 12.16.1，**未验证**）。无头转换完全不需要 Node/pnpm。

---

## 4. 无头用法

### 4.1 两条命令

```bash
cd /data/Documents/projects/SmartCoaster
python3 appearance/tools/make_art_lumina.py     # art 预处理：裁 bbox→正方形→圆外 alpha=0→6px bleed
/data/Documents/tools/Lumina-Layers/.venv/bin/python \
    appearance/lumina/lumina_convert.py --art dog,elf
```

`make_art_lumina.py` 不做颜色量化（Lumina 下游用 LUT 匹配）；`--check` 只校验不写。

### 4.2 `lumina_convert.py` 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--art` | `dog,elf` | 版本列表，逗号分隔；须在脚本 `PARAMS` 中定义 |
| `--out-root` | `appearance/build/print` | 输出版本目录根 |
| `--spacer` | 版本内 `0.80` | 背板 mm；总厚 = `(5+round(spacer/0.08))×0.08` |
| `--expect-thickness` | `1.20` | 总厚断言，不符即失败（防几何漂移） |
| `--lut` / `--color-mode` | 版本内 CMYW npy / `4-Color (CMYW)` | 换 LUT 必须同步 color_mode |
| `--quantize` | 版本内 `48` | K-Means 颜色数（高保真模式） |
| `--git-head` | 空 | 写入 manifest 的引擎版本；发布时传 `$(git -C $LUMINA rev-parse HEAD)` |
| `--manifest-only` | off | 不转换，只校验已有 manifest（快速回归） |

### 4.3 版本参数（脚本 `PARAMS`）

| 参数 | dog / elf | 备注 |
| --- | --- | --- |
| `target_width_mm` | `86.4` | `int(86.4×10)=864 px`，0.10 mm/px |
| 色层 / 背层 / 总层 | `5` / `10`（0.80 mm）/ `15` | 15×0.08 = **1.20 mm** |
| `lut` / `color_mode` | `bambulab_pla_basic_cmyw.npy` / `4-Color (CMYW)` | 槽位 White/Cyan/Magenta/Yellow |
| `quantize_colors` / `smooth_sigma` / `blur_kernel` | `48` / `10` / `0` | 高保真滤波与量化 |
| 结构 / 建模 | `Single-sided` / `HIGH_FIDELITY` | 单面、光栅 |
| 打印机 | `bambu-x1c` + `BambuStudio:bbl:bambu-lab-x1-carbon:0.4` | 0.4 喷嘴 |
| 背板 | slot 0=White、100% 实心、不分离 | `backing_infill_density_percent=100` |

### 4.4 输出物（每个 `appearance/build/print/<art>/`）

| 文件 | 内容 |
| --- | --- |
| `filament_<n>_<HEX>.stl` | 每耗材一个闭合实体，**assembly pose**（图案面 +Z、平背 z=0） |
| `plate_lumina.3mf` | Lumina 原生 3MF（Bambu 工程元数据、4 个材料槽），**print pose**（图案面 z=0） |
| `plate_preview.png` / `.glb` | 2D 颜色预测 / 3D 预览（参考，非打印几何/非实物保证） |
| `material_matrix.npy` | `(H,W,5)` int32：每像素 5 个色层的槽号，-1=空气 |
| `matched_rgb.npy` / `mask_solid.npy` | 预测打印色 / 实体掩码 |
| `manifest.json` | 数据契约（§8.2）：bbox、厚度、逐耗材 sha256、watertight、校验 |
| `lumina_call.json` | 实际入参 + 版本（可复现） |

重跑幂等：先删 `filament_*.stl` 再写；`manifest.json`/`plate_*` 覆盖；**旧 `*_kromacut.3mf` 不会删**（迁移期并存，别混用）。
`.gitignore` 已忽略 `*/*.3mf` 与 `filament_*.stl`；`plate_preview.png`、`*.npy`、`lumina_call.json` 暂未忽略。Lumina 自己的时间戳产物
（实测命名：`art_rgba_Lumina_HiFi_4C_<ts>.3mf`、`art_rgba_Preview_<ts>.glb`、`art_rgba_High-Fidelity_Debug.png`、`…_color_recipe.txt`、`lumina_stats.txt`）落在 `Lumina/output`（即 `.lumina_runtime/output`），可定期清理。
本机已有一次**直接调用引擎**的冒烟产物（非驱动，`print/<art>/` 未更新）：3MF 为 Production 扩展，根对象含 4 个 component → `3D/Objects/object_1.model`，另有 `Metadata/project_settings.config` 等 Bambu 工程文件与缩略图（共 18 个成员）。

### 4.5 换图 / 换色数 / 换尺寸

| 想换什么 | 改哪里 | 必须同步 |
| --- | --- | --- |
| 换插画 | `appearance/src/surface.png` + `make_art_lumina.py` 的 `ARTS` bbox | 重跑素材 + 转换 |
| 换尺寸 | `make_art_lumina.py` 的 `N`/`FRAME_MM`、`lumina_project.yaml`、驱动 `target_width_mm` | 三处一致；`N=target_mm×10`，PNG 必须 `N×N`（否则驱动报错） |
| 换厚度 | `--spacer` 或 `PARAMS` | 总厚公式联动；外壳槽深同步 |
| 换色数 | 换 LUT + `--color-mode`（如 `6-Color (CMYWGK 1296)`） | **必须先有对应校准 LUT**（§7）；色层数可能随 LUT 变 |
| 换配色 | 换 LUT（如 RYBW）+ `color_mode` | 槽位数必须与 LUT 条目数匹配 |

---

## 5. 几何语义（print pose ↔ assembly pose）

### 5.1 Lumina 打印姿态：图案面在 z=0

```text
z = 1.20 mm  ┌──────────────────────────────┐  ← 平背（背板顶面 = 嵌入口袋的配合面）
             │  Backing 10 层 (0.80 mm)      │     slot 0 = White
z = 0.40 mm  ├──────────────────────────────┤
             │  Colour 5 层 (0.40 mm)        │     material_matrix[...,0] = 观赏面
z = 0 mm     └──────────────────────────────┘  ← 图案面（贴打印床、第一层）
```

- 导出时施加 **X 镜像**（左右翻转），所以切片器里看到的是镜像件。
- 厚度：`T = (color_layers + round(spacer_thick/0.08)) × 0.08`；本线 `5+10=15` 层 → **1.20 mm**。
- 层高 0.08 是几何常量：`layer_height_mm` 参数只影响 LUT 匹配，不改几何。
- 平背条件：relief/cloisonne/coating/fridge-magnet 全关、`separate_backing=False`（当前配置即如此）。
  底板足迹跟随可见剪影：圆外 alpha=0 → **圆形件**。

### 5.2 print pose → assembly pose（驱动所做的刚体变换）

下游外壳/渲染/交付统一用 assembly pose：图案面 **+Z 朝上**、平背 `z=0`、图像顶 `+Y`。

```text
assembly = ( sx·x , sy·y , T − z )     # sign 候选 flip_x=(-1,+1,-1) 或 flip_y=(+1,-1,-1)
print    = ( sx·X , sy·Y , T − Z )     # 同一变换再做一次 = 逆变换（自逆）
```

`sx/sy` 由脚本**检测**：候选姿态顶点投影回像素网格，与 `material_matrix` 实体掩码比对，取命中率高者；
命中率 < 0.90 直接失败（不静默假设）。结果写入 `manifest.geometry.assembly_sign/assembly_transform/
vertex_match_rate`。交付侧再用 `PRINT_DELIVERY_SPEC.md` §1.1 的变换把 plate+print 整体翻回打印姿态。

### 5.3 为什么适合"印花先打、外壳后融"

① 图案面贴床：首层直接压 PEI/纹理板，表面最平整致密；背板朝上无需支撑。② 平背是明确配合面：`T=1.20 mm` 恒定，
外壳槽深 = `T + top_gap`（当前 top_gap=0），背板整面落槽底、图案面与沿口齐平。③ 两块几何保持分离：印花（4 耗材实体）
与外壳各自独立，由 Bambu Studio 在切片阶段融合，不依赖 CAD 布尔、不改已验证外壳；换图/换色不碰机械。④ 口径统一：
像素 0.10、层高 0.08、总厚 1.20 贯穿素材/几何/槽深/交付，改一处必须联动（§4.5）——参数集中在 `lumina_project.yaml` + `PARAMS`。

> **PROVISIONAL（首次走驱动前必读）**：本机冒烟 3MF 实测对象网格 X/Y ∈ `[84.9, 171.1]`，即 Lumina 按 256 床
> 中心 `(128,128)` 居中（`center_on_bed=True`）；而驱动姿态匹配按"原点居中"网格计算——**首次走驱动预期会报
> `could not establish assembly orientation` 或输出 bbox 偏移**。处理：关 bed centering，或在检测/导出前先减床心平移。
> 另外圆形 alpha 掩码旋转对称，`flip_x`/`flip_y` 命中率会接近，**平面内 180° 朝向存在歧义**——首跑必须用
> `plate_preview.png` 对照 `art_rgba.png` 人工核对，不能只看命中率。

---

## 6. 4 色 CMYW 的 AMS 与打印参数

### 6.1 槽位

| 槽 | 名称 | 预览 hex（Lumina `ColorSystem.CMYW`，**非厂商官方色**） |
| --- | --- | --- |
| 0 | White | `#FFFFFF`（背板 + 高光） |
| 1 | Cyan | `#0086D6` |
| 2 | Magenta | `#EC008C` |
| 3 | Yellow | `#F4EE2A` |

⚠️ `.npy` LUT 只含 RGB 读数、不含厂商色号；3MF 槽名/颜色来自 Lumina 元数据（上述通用色）。
切片前必须把 4 槽**映射到实际 Bambu 耗材**，并接受"预测色需实物打样确认"（§7）。

### 6.2 AMS 需求

- 只打印花：**4 槽**（X1C 单台 AMS 恰好 4 卷）。
- 与外壳同盘（in-situ，Route A）：+1 卷外壳耗材 → **5 槽** → X1C 需第二台 AMS 或中途换料
  （`lumina_project.yaml` 的 `ams_slots_needed: 4` 注释："print only; +1 shell spool if co-printed in place"）。
- 分开打（Route B）：印花 4 色一盘、外壳 0.20 mm 另一盘，打印后压配/胶接 → 4 槽即可。
- 4 色混色每层可能多次换料，擦料塔/冲刷会使打印时间与废料明显高于单色件（未实测）。

### 6.3 打印参数

| 参数 | 值 | 说明 |
| --- | --- | --- |
| 层高 | **0.08 mm** | 颜色层必须 0.08；实测 3MF `project_settings.config` 层高/首层均为 0.08。不要用 0.20 打花层 |
| 背板填充 | **100%** | 保证平背强度与平整 |
| 底板层高修改器 / 擦料塔自动摆位 | **关**（工程仍含默认擦料塔） | 避免切片器改背板层高/自动改布局；`enable_prime_tower=1` 是切片器默认，不要删成 0 除非确认废料可接受 |
| 打印板 | **textured PEI**（X1C 设备默认） | 要光面可换 `smooth-pei-plate`，但驱动未暴露 `build_plate_id` |
| 支撑 / 摆放 | 无需支撑；3MF 对象居中于 256 床 | 不要缩放/镜像/旋转（会破坏 86.4 mm 与槽径配合） |

> 两条路线（YAML `bed.note`）：**Route A** 同盘 0.08 打"顶板 + 印花"（前 1.20 mm 是印花层）；
> **Route B** 外壳 0.20 单独打、再压配/胶接。二者均**未在本机切片验证**（PROVISIONAL）。

---

## 7. 已知限制与未验证项

| 项 | 状态 | 说明 |
| --- | --- | --- |
| `.npy` LUT 无厂商色号 | 已知 | 4 色 hex 是 Lumina 通用预览色；切片器里需映射真实 Bambu 耗材 |
| 6/8 色能力 | **受限** | 只带 4 色 CMYW/RYBW（Bambu PLA）。6/8 色需自建校准 LUT（打固定色卡→拍照→提取）；`lut-preset/Custom/` 下 Bambu 命名的 6/8 色 npy 来源/槽序不可验证，不要直接用 |
| 颜色准确性 | **未验证** | 预测色 ≠ 实物色（耗材批次/层高/温度/拍摄影响）；必须打小样确认 |
| Bambu Studio 导入/切片 | **未验证** | 本机未装 Bambu Studio；AMS 映射、擦料塔、逐层预览、与外壳同盘均待实机验证 |
| 装配姿态原点/镜像歧义 | **PROVISIONAL** | 见 §5.3 注记；首跑人工核对 `plate_preview.png` 朝向与 manifest bbox |
| 三角面规模 | 部分实测 | 本机一次冒烟：4 对象合计 881,214 三角面、3MF 11.6 MB；走驱动后记录 `filament_objects[].triangles`、`runtime_s` |
| 厚度步进 | 已知 | 只能 0.08 整数倍；1.20 mm = 15 层，槽深/结构改动须联动 |
| 外壳/下游适配 | **适配中** | YAML 已写 `print 86.4 / pocket 86.0 / 1.20 mm`，但下游当前仍部分读旧 `appearance_project.yaml` 口径（PROVISIONAL，以重跑后的 `shell.json`/delivery 为准） |
| AGPL 边界 / 生成物署名 | 已知 | 只调用不修改；分发修改版需履行 AGPL；生成物按 OUTPUT-TERMS 署名（§1.2） |
| 口径同步 | 已知 | `docs/01` §17、`requirements.yaml` 仍写 Kromacut 旧线；本页为 Lumina 线现行说明，待同步 |

---

## 8. 与 SmartCoaster 流水线的接口

### 8.1 数据流

```text
appearance/src/surface.png
 └─(make_art_lumina.py)→ appearance/build/art/<art>/{art_rgba.png(864²), art.json}
     └─(lumina_convert.py → Lumina build_image_model_context)→ appearance/build/print/<art>/
         ├─ filament_<n>_<HEX>.stl ×4   (assembly pose)
         ├─ plate_lumina.3mf            (print pose, Bambu 工程)
         ├─ plate_preview.png/.glb、material_matrix.npy、matched_rgb.npy、mask_solid.npy
         ├─ manifest.json               (契约, §8.2)
         └─ lumina_call.json            (全入参 + 版本)
```

### 8.2 `manifest.json` 契约（schema `smartcoaster.appearance.print_lumina/v1`）

| 字段 | 内容 / 下游用法 |
| --- | --- |
| `engine` | `name/root/git_head/license/entry/python`（版本溯源） |
| `art` | `png/png_sha256/width/height/pixel_size_mm/target_width_mm` |
| `params` | 生效参数：`lut/lut_sha256/color_mode/color_layers/spacer_thick_mm/layer_height_mm/total_layers/quantize_colors/…/printer_id/device_profile_id/backing_*` |
| `geometry.*` | `thickness_mm`/`print_thickness_mm`/**1.20**、`diameter_mm`、`bbox_mm{min,max,size}`、`orientation/assembly_transform/assembly_sign/vertex_match_rate/image_top_axis` |
| `slot_names`/`palette`/`palette_bottom_up` | 槽序与 hex（Bottom-up 供渲染/切片对齐） |
| `filament_objects[]` | `number/slot/hex/file/triangles/volume_mm3/sha256/parts/watertight`——**下游按此逐耗材加载 STL 并分配 AMS** |
| `slot_pixel_counts` | 各槽观赏面像素数（用量/调色核对） |
| `artifacts` | 3MF/预览/矩阵文件 sha256 |
| `validation` | `thickness_ok/diameter_ok/slots_ok/watertight{…}/all_watertight/volume_mm3` |
| `provenance` | `call_kwargs`（Lumina 全参数）+ `generated_at_utc` + `generator` |

> 迁移注意：驱动会**覆盖** `appearance/build/print/<art>/manifest.json`（旧 Kromacut 契约 → 新 schema）；
> 读取方必须按 `schema` 分支，不能假设旧字段。`--manifest-only` 只校验此文件。

### 8.3 下游脚本（实现状态）

| 下游 | 入口 | 接口 | 状态 |
| --- | --- | --- | --- |
| 外壳开槽 | `appearance/cad/build_recessed.py --config appearance/config/lumina_project.yaml` | 读 `print_thickness_mm=1.20`、`pocket_dia_mm=86.0`、`print_dia_mm=86.4` | **适配中/未验证**（脚本当前仍期待旧 config schema） |
| 装配/渲染 | `appearance/render/run_all.sh` | 逐耗材 STL（assembly pose）+ palette；`render/config.json` 已写 Lumina 4 色回退色板 | 部分适配（PROVISIONAL） |
| 打印交付 | `render/print/appearance/run_print_stage.sh` | 翻转 print pose、逐耗材 STL、床面排版、CHECKSUMS | 旧产物仍是 Kromacut 口径（6–7 耗材、1.20/1.40 mm），需按 4 耗材/1.20 mm 重跑 |
| 独立验收 | `appearance/tools/acceptance_check.py` | 只读回验 manifest/STL/3MF | 旧线 140 项；Lumina 专用验收脚本在 YAML 中为计划项，尚未入库 |
| 一键编译 | `appearance/compile.sh` / `tools/compile.py` | art→convert→shell→render→print→acceptance | 尚未接入 Lumina 阶段（`compile_lumina.py` 未入库） |

> 接口原则不变：**CLI + JSON 契约**，下游只读、不猜参数；换线期间以重跑结果为准。

---

## 9. 故障排查

| 现象 | 诊断 | 处理 |
| --- | --- | --- |
| `ModuleNotFoundError: lumina_svg_core/neroued_3mf/fatcat_metadata` | 用错解释器或 venv 依赖没装齐 | 必须用 `.venv/bin/python`；`pip install -r requirements.txt` |
| pip 平台/版本不匹配 | 非 cp312–314 或 glibc<2.28 | 用 `/data/Documents/tools/python312`；确认 `python3.12 -V` |
| `~/.cache/pip` 不可写 | 缓存目录归属问题 | `PIP_CACHE_DIR=/data/Documents/tools/.pip-cache TMPDIR=/data/Documents/tools/.tmp` |
| `EPERM/PermissionError` 在 `Lumina/output`/`materials` | 符号链接丢失或目标不可写（import config 会创建 output/{models,temp}、materials） | 重建 §3.2 符号链接、确认 `.lumina_runtime` 可写；**不要删链接** |
| `art PNG is WxH but target_width_mm=… needs NxN` | PNG 网格 ≠ `target_mm×10` | 重跑 `make_art_lumina.py`；尺寸三处同步（§4.5） |
| 缺块/错色/槽位缺失 | LUT 与 color_mode 不匹配（4 色须 1024 条目 npy；6 色 npy 可能被推断成 4 色） | 只用 `4-Color (CMYW)` + `bambulab_pla_basic_cmyw.npy`；换 LUT 同步 `--color-mode`；检查 manifest `slot_names` 是否 4 项 |
| `could not establish assembly orientation` | 姿态匹配率<0.90：床心平移假设/掩码对称歧义 | 见 §5.3：核对 bbox 是否在床心；考虑关 `center_on_bed`/减平移；用预览图人工核对 |
| `some filament meshes are not watertight` | 几何不闭合（脚本主动失败，杜绝坏件） | 不要重焊/去重三角面；查引擎版本与输入图（孔洞/极细线），必要时降分辨率 |
| 内存/耗时过大 | 864²×5 层精确网格 + 3MF 写入 | 记录 `runtime_s`/triangles；降分辨率须连锁改尺寸/槽径；可试 `LUMINA_RASTER_PARALLELISM=1` |
| 磁盘快速上涨 | 时间戳产物累积在 `.lumina_runtime/output` | 定期清旧 `models/*.3mf`、`*_Preview_*.glb`、`*_Debug.png`；`lumina_stats.txt` 可删 |
| GUI 打不开/端口占用 | 前端未装、pnpm 版本不符、残留服务 | 无头不需要 GUI；`corepack prepare pnpm@10.33.2 --activate`；`start_all.py --kill` |
| 分不清新旧产物 | Kromacut 旧文件仍在同目录 | 看 `manifest.json` 的 `schema`/`engine`；`plate_lumina.3mf` 才是新线 |

---

## 10. 参考

**上游（Lumina-Layers / Lumina Studio 2.0）**

- GitHub：<https://github.com/lumina-layer-studio/Lumina-Layers>（AGPL-3.0-only）；中文 README：`/data/Documents/tools/Lumina-Layers/README_CN.md`
- 3MF 元数据导出：`docs/3mf-metadata-export.md`；运行时支持：`docs/runtime-support.md`；原生依赖：`docs/desktop-electron.md`
- 许可：[LICENSE](https://github.com/lumina-layer-studio/Lumina-Layers/blob/main/LICENSE) / [LICENSING.md](https://github.com/lumina-layer-studio/Lumina-Layers/blob/main/LICENSING.md) / [OUTPUT-TERMS.md](https://github.com/lumina-layer-studio/Lumina-Layers/blob/main/OUTPUT-TERMS.md)
- 官方 Wiki / 使用教程：<https://wiki.luminastudio.com.cn/>

**本项目内**

- 源码级分析（file:line、风险、未验证项）：[`../.scratch/LUMINA_SPEC.md`](../.scratch/LUMINA_SPEC.md)
- 驱动 [`../appearance/lumina/lumina_convert.py`](../appearance/lumina/lumina_convert.py)（docstring 提到的 `appearance/lumina/README.md` 尚未创建，以本页为准）；
  配置 [`../appearance/config/lumina_project.yaml`](../appearance/config/lumina_project.yaml)；素材 [`../appearance/tools/make_art_lumina.py`](../appearance/tools/make_art_lumina.py)
- 旧线（历史参考）：[`../appearance/kromacut/README.md`](../appearance/kromacut/README.md)、
  [`docs/01`](01_AI_Hardware_Engineering_Pipeline.md) §17
- 打印交付：[`../appearance/PRINT_DELIVERY_SPEC.md`](../appearance/PRINT_DELIVERY_SPEC.md)；渲染：[`../appearance/RENDER_HOWTO.md`](../appearance/RENDER_HOWTO.md)

---

*本页"实测"数据均为 2026-11-07 本机采样；标注 PROVISIONAL/未验证的条目在首次实跑与 Bambu 实机切片前不得当作已验证结论。*
