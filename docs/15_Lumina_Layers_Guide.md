# Lumina-Layers 外观打印引擎指南（Lumina Studio 2.0）

> 版本 v1.1（2026-11-08，耗材/机型改为 RYBW + Black / Bambu H2D） · 状态：**现行**（替代 `appearance/kromacut/` Kromacut Flat Paint 线）
> 读者：AI agent / 工程师。目标：一张插画 PNG → **无头**产出已知厚度、平背、多材料、可直接进 Bambu Studio 与外壳同盘打印的"印花板"。
> 用户实际硬件：Bambu Lab **PLA Basic 红/黄/蓝/绿/白/黑 6 卷** + **Bambu Lab H2D（同打 5 色）**；印花 = RYBW 4 卷，外壳/顶板/按键 = Black 1 卷。
> 配套：[`.scratch/LUMINA_SPEC.md`](../.scratch/LUMINA_SPEC.md)（file:line 证据）、[`lumina_convert.py`](../appearance/lumina/lumina_convert.py)、[`lumina_project.yaml`](../appearance/config/lumina_project.yaml)、[docs/01](01_AI_Hardware_Engineering_Pipeline.md) §17、[`appearance/README.md`](../appearance/README.md)。

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

> 本页数据以 **RYBW/JSON LUT/H2D 重跑后的 `appearance/build/print/*/manifest.json` 与 `COMPILE_LUMINA_REPORT.json` 为准**；三角面/体积/验收数会随素材与 LUT 变化，不沿用 CMYW 旧值。
> 本机状态：CPython 3.12.16 + venv 依赖已装齐；Bambu Studio 切片与实物打印**尚未验证**。

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
| 耗材数 | dog 6 卷 / elf 7 卷（旧报告实测） | **4 卷 RYBW**（White/Red/Yellow/Blue）+ 1 卷 Black 外壳 = **H2D 同打 5 色** |
| 输入网格 | 576 px @ 0.15 mm/px | **864 px @ 0.10 mm/px** |
| 切片负担 | 逐色几何，水彩碎片化；三角面 1.94M/2.50M、3MF 19.7/25.6 MB | 4 个耗材对象；当前 RYBW 重跑的三角面/3MF 见 `manifest.json`（随图/LUT 变） |
| 许可 | AGPL-3.0（只调用不修改） | **AGPL-3.0-only**（只调用不修改） |

换线原因（工程决策，**不是**许可原因——两条线都是 AGPL）：① 旧线"逐色几何"路线切片碎片多、
逐耗材 STL/AMS 负担重，Lumina 用 4 卷光学混色取代逐色量化；② 用户实际只有 RYBW+黑+绿（无青/品红），
所以不用 CMYW；③ 4 印花 + 1 黑壳正好用满 H2D 的 **5 色同打**，一次成型；④ 一套几何契约（5 色层 + 10 背层 =
1.20 mm）取代两套；⑤ 上游是活跃 2.0 项目，cp312 轮子可无头调用。

### 1.2 许可要点（事实陈述，非法律意见）

- 软件主体 **AGPL-3.0-only**（`LICENSING.md`；运行时依赖 `lumina-svg-core==0.3.4` 同为 AGPL-3.0-only）。
- 生成物另有 [OUTPUT-TERMS](https://github.com/lumina-layer-studio/Lumina-Layers/blob/main/OUTPUT-TERMS.md)：
  个人非商业自用免署名；**商业销售/公开分享生成物需标注 "Generated with Lumina-Layers / 由 Lumina-Layers 生成"**。
- 本项目**只调用、不修改、不把 Lumina 代码嵌入发布物**；若分发修改版/组合程序需履行 AGPL 对应源码义务，
  需要闭源集成或署名豁免时联系上游取得书面授权。

---

## 2. 能力边界

**能做**：光栅插画（PNG/JPEG，透明背景）→ 多材料平面件（每耗材一个闭合实体 + 一个 Bambu 原生 3MF）；
**4 色 RYBW** 光学混色（JSON LUT 带 palette hex）、固定 0.10 mm/px 高保真网格、单面结构（颜色面贴床 + 平背）、圆/方外形由 alpha 决定；
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
| LUT（4 色 RYBW） | **`lut-preset/Custom/lumina_lut.json`**（自描述 Keyed-JSON：palette White/Red/Yellow/Blue 带 hex，5 色层、0.08 mm、base 10 层；sha256 `bad3054b…5987`） |
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
sha256sum "$LUMINA/lut-preset/Custom/lumina_lut.json"   # bad3054b…5987
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
| `--lut` / `--color-mode` | 版本内 `lut-preset/Custom/lumina_lut.json` / `4-Color (RYBW)` | 换 LUT 必须同步 color_mode；**优先 JSON LUT**（见 §7 的 npy 发灰坑） |
| `--quantize` | 版本内 `48` | K-Means 颜色数（高保真模式） |
| `--git-head` | 空 | 写入 manifest 的引擎版本；发布时传 `$(git -C $LUMINA rev-parse HEAD)` |
| `--manifest-only` | off | 不转换，只校验已有 manifest（快速回归） |

### 4.3 版本参数（脚本 `PARAMS`）

| 参数 | dog / elf | 备注 |
| --- | --- | --- |
| `target_width_mm` | `86.4` | `int(86.4×10)=864 px`，0.10 mm/px |
| 色层 / 背层 / 总层 | `5` / `10`（0.80 mm）/ `15` | 15×0.08 = **1.20 mm** |
| `lut` / `color_mode` | `lut-preset/Custom/lumina_lut.json` / `4-Color (RYBW)` | 槽位 White/Red/Yellow/Blue（JSON 内 palette hex） |
| `quantize_colors` / `smooth_sigma` / `blur_kernel` | `48` / `10` / `0` | 高保真滤波与量化 |
| 结构 / 建模 | `Single-sided` / `HIGH_FIDELITY` | 单面、光栅 |
| 打印机 | `bambu-h2d` + `BambuStudio:bbl:bambu-lab-h2d:0.4` | 用户 H2D（350×320×325，双喷头，同打 5 色）；0.4 喷嘴 |
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
| 换色数 | 换自描述 JSON LUT + 同步 `--color-mode` | **必须先有对应校准 LUT**（§7）；H2D 同打上限 5 色，色层数可能随 LUT 变 |
| 换配色 | 换 JSON LUT + `color_mode`（当前 RYBW） | 槽位数必须与 LUT palette 条目匹配；无青/品红耗材，不要切回 CMYW |

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

`sx/sy` 由脚本**检测**：RYBW 重跑用**逐槽体积加权 XY 质心**，两个平面内镜像都打分，胜者须 `rms <= 3.0 mm`
且至少比次优好 **2.5×**（不静默假设）。结果写入 `manifest.geometry.assembly_sign/assembly_transform/
orientation_volume_centroid_rms_mm/orientation_margin/orientation_method`；本机 dog rms 1.7399 mm、elf rms 1.6619 mm。
交付侧再按打印姿态烘焙 STL（plate+print 整体翻转）。

### 5.3 为什么适合"印花先打、外壳后融"

① 图案面贴床：首层直接压 PEI/纹理板，表面最平整致密；背板朝上无需支撑。② 平背是明确配合面：`T=1.20 mm` 恒定，
外壳槽深 = `T + top_gap`（当前 top_gap=0），背板整面落槽底、图案面与沿口齐平。③ 两块几何保持分离：印花（4 耗材实体）
与外壳各自独立，由 Bambu Studio 在切片阶段融合，不依赖 CAD 布尔、不改已验证外壳；换图/换色不碰机械。④ 口径统一：
像素 0.10、层高 0.08、总厚 1.20 贯穿素材/几何/槽深/交付，改一处必须联动（§4.5）——参数集中在 `lumina_project.yaml` + `PARAMS`。

> **RYBW 实测失败模式**：低反差图（elf）在旧的"顶层色块面积质心"判据下可能只剩 1 个有效槽而失败
> （`orientation detection needs >=2 common colour slots`）；升级为**体积加权质心**后通过（elf rms 1.6619 / margin 8.69）。
> 若再遇到：提高素材对比度/饱和度、换 LUT，或对单色图显式给姿态（不要靠质心猜）；圆形掩码仍建议人工核对预览。

---

## 6. 4 色 RYBW + 黑壳：H2D 5 色一次打印

### 6.1 槽位（RYBW，JSON LUT 自带 palette hex）

| 槽 | 名称 | JSON LUT hex（Bambu PLA Basic 实际色） |
| --- | --- | --- |
| 0 | White | `#FFFFFF`（背板 + 高光） |
| 1 | Red | `#DC143C` |
| 2 | Yellow | `#FFE600` |
| 3 | Blue | `#0064F0` |

LUT 文件 = `lut-preset/Custom/lumina_lut.json`（自描述 Keyed-JSON，`color_mode="4-Color (RYBW)"`；
`max_color_layers=5`、`layer_height_mm=0.08`、`base_layers=10`）。**它带 palette hex，可直接映射到耗材**；
不再使用 CMYW 的 `.npy`（见 §7 发灰坑）。

### 6.2 H2D 5 色预算（谁打什么）

| 用途 | 耗材 | 卷数 |
| --- | --- | --- |
| 印花 4 色 | White / Red / Yellow / Blue（RYBW） | 4 |
| 外壳 + 开槽顶板 + 按键 | **Black `#101010`**（Bambu PLA Basic 黑） | 1 |
| 合计 | — | **5 卷 = H2D 一次同打** |
| 备用 | Green `#00AE42`（本版不参与；换用需重配 LUT） | spare |

- H2D 同时 5 色 → 路线 A（顶板 + 印花同盘）无需中途换料/第二台 AMS；**这是选 RYBW+黑 而不是 CMYW/6 色的原因**；
- 床面排版仍按 **220×220 保守** 排（交付 `218.9×110.0 / 208.0×114.0`），H2D 实际 350×320 更大；
- 路线 B（分开打印后压配/胶接）只需印花 4 色一盘 + 外壳单独一盘，5 色预算更宽松。

### 6.3 打印参数

| 参数 | 值 | 说明 |
| --- | --- | --- |
| 层高 | **0.08 mm** | 颜色层必须 0.08；同盘打印外壳/顶板也按 0.08 |
| 背板填充 | **100%** | 保证平背强度与平整 |
| 底板层高修改器 / 擦料塔自动摆位 | **关**（工程仍含默认擦料塔） | 避免切片器改背板层高/自动改布局 |
| 打印板 | **textured PEI** | 用户 H2D 默认；要光面可换 `smooth-pei-plate`，但驱动未暴露 `build_plate_id` |
| 支撑 / 摆放 | 无需支撑；3MF 对象居中于机床 | 不要缩放/镜像/旋转（会破坏 86.4 mm 与槽径配合） |
| 机型 | `bambu-h2d` + `BambuStudio:bbl:bambu-lab-h2d:0.4` | registry 350×320×325、双喷头；0.4 喷嘴 |

> 两条路线：**Route A** 同盘 0.08 打"顶板 + 印花"（前 1.20 mm 是印花层）；**Route B** 外壳 0.20 单独打、
> 再压配/胶接。二者均**未在本机切片验证**（PROVISIONAL）。

## 7. 已知限制与未验证项

| 项 | 状态 | 说明 |
| --- | --- | --- |
| **npy LUT 发灰（重要）** | 已知坑 | `bambulab_pla_basic_rybw.npy` 的纯白叠层预测仅 `[215,210,207]`，整张图被预测成灰；**优先用带 palette hex 的 Keyed-JSON LUT**（`lumina_lut.json`，白=255，预览接近源图） |
| 6/8 色能力 | **受限** | 当前 4 色 RYBW；H2D 同打上限 5 色，且没有可用的 Bambu 6 色校准 LUT。6/8 色需自建校准 LUT（固定色卡→拍照→提取），不要直接用来源不明 npy |
| 颜色准确性 | **未验证** | 预测色 ≠ 实物色（耗材批次/层高/温度/拍摄影响）；必须打小样确认；Green 备用未参与本版 |
| RYBW 色域限制 | **已知** | 无品红：elf 薰衣草紫背景无法还原（蓝/白替代，粉偏红）；dog 表现好。保紫需加青+品红回 CMYW（仍 5 色），或换图 |
| Bambu Studio 导入/切片 | **未验证** | 本机未装 Bambu Studio；AMS 映射、擦料塔、逐层预览、与外壳同盘均待实机验证 |
| 姿态检测 | 已实现（有边界） | 体积加权质心，rms 阈值 3.0 mm、胜者需比次优好 2.5×；低反差图仍可能退化（见 §5.2/§5.3）；首跑建议人工核对 `plate_preview.png` |
| 三角面规模 | 实测（RYBW 重跑） | dog **680,354** 面 / 8.91 MB / 27.66 s；elf **943,734** 面 / 12.11 MB / 38.99 s（CMYW 旧值已作废） |
| 厚度步进 | 已知 | 只能 0.08 整数倍；1.20 mm = 15 层，槽深/结构改动须联动 |
| 外壳/下游适配 | 已适配 | 唯一配置 `lumina_project.yaml`；`compile_lumina.py` 已接线（46 项契约校验），外壳/渲染/打印交付均读 `shell.json`/manifest |
| AGPL 边界 / 生成物署名 | 已知 | 只调用不修改；分发修改版需履行 AGPL；生成物按 OUTPUT-TERMS 署名（§1.2） |
| 口径同步 | 本轮已同步 | `docs/01` §17、`appearance/README.md`、`requirements.yaml` 已改为 Lumina/RYBW/H2D；旧 Kromacut 仅历史归档 |

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
| `geometry.*` | `thickness_mm`/`print_thickness_mm`/**1.20**、`diameter_mm`、`bbox_mm{min,max,size}`、`orientation/assembly_transform/assembly_sign/orientation_volume_centroid_rms_mm/orientation_margin/orientation_method/image_top_axis` |
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
| 外壳开槽 | `appearance/cad/build_recessed.py --config appearance/config/lumina_project.yaml` | 读 `print_thickness_mm=1.20`、`pocket_dia_mm=86.0`、`print_dia_mm=86.2` | 已适配（`shell.json` 为准） |
| 装配/渲染 | `appearance/render/run_all.sh` | 逐耗材 STL（assembly pose）+ palette；CMF 黑壳（`bambu_pla_basic_rybw_black`） | 已适配 |
| 打印交付 | `render/print/appearance/run_print_stage.sh` | 翻转 print pose、4 耗材 STL、床面排版、CHECKSUMS | 已适配（16/17 文件；round 53.69 MB / square 71.55 MB；含 bottom 视图） |
| 独立验收 | `appearance/tools/acceptance_check_lumina.py` | 只读回验 manifest/STL/3MF/交付/文档 | 已入库；RYBW 重跑 **194/194 PASS**（`appearance/build/ACCEPTANCE.json`） |
| 一键编译 | `appearance/compile.sh` → `tools/compile_lumina.py` | A1 art→A2 lumina→A3 shell→A4 render→A5 3mf→A6 postprocess→A7 print→A8 acceptance | 已入库并接线（46 项契约校验；旧 `compile.py` OBSOLETE） |

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
| 缺块/错色/槽位缺失 | LUT 与 color_mode 不匹配 | 用 `4-Color (RYBW)` + `lut-preset/Custom/lumina_lut.json`；换 LUT 同步 `--color-mode`；检查 manifest `slot_names` = White/Red/Yellow/Blue |
| **整图发灰、白不够白** | 用了无 palette hex 的 `.npy` LUT | 换自描述 JSON LUT；`bambulab_pla_basic_rybw.npy` 实测白 `[215,210,207]`，不要用 |
| `orientation detection needs >=2 common colour slots` | 低反差图只剩 1 个有效颜色槽 | 提高素材对比度/饱和度或换 LUT；单色图显式给姿态；见 §5.2 |
| `could not establish assembly orientation` | 体积质心 rms > 3.0 mm 或优势 < 2.5×：掩码/图太对称 | 核对 bbox 是否重居中；用 `plate_preview.png` 人工核对朝向；低反差图提高对比度/换 LUT |
| `some filament meshes are not watertight` | 几何不闭合（脚本主动失败，杜绝坏件） | 不要重焊/去重三角面；查引擎版本与输入图（孔洞/极细线），必要时降分辨率 |
| 内存/耗时过大 | 864²×5 层精确网格 + 3MF 写入 | 记录 `runtime_s`/triangles；降分辨率须连锁改尺寸/槽径；可试 `LUMINA_RASTER_PARALLELISM=1` |
| 磁盘快速上涨 | 时间戳产物累积在 `.lumina_runtime/output` | 定期清旧 `models/*.3mf`、`*_Preview_*.glb`、`*_Debug.png`；`lumina_stats.txt` 可删 |
| GUI 打不开/端口占用 | 前端未装、pnpm 版本不符、残留服务 | 无头不需要 GUI；`corepack prepare pnpm@10.33.2 --activate`；`start_all.py --kill` |
| 分不清新旧产物 | 旧 CMYW/Kromacut 文件仍在同目录 | 看 `manifest.json` 的 `params.lut`/`slot_names`；RYBW JSON LUT 才是本版 |

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
  配置 [`../appearance/config/lumina_project.yaml`](../appearance/config/lumina_project.yaml)；素材 [`../appearance/tools/make_art_lumina.py`](../appearance/tools/make_art_lumina.py)；
  LUT：`/data/Documents/tools/Lumina-Layers/lut-preset/Custom/lumina_lut.json`（RYBW Keyed-JSON，sha256 `bad3054b…5987`）
- 旧线（历史参考）：[`../appearance/kromacut/README.md`](../appearance/kromacut/README.md)、
  [`docs/01`](01_AI_Hardware_Engineering_Pipeline.md) §17
- 打印交付：[`../appearance/PRINT_DELIVERY_SPEC.md`](../appearance/PRINT_DELIVERY_SPEC.md)；渲染：[`../appearance/RENDER_HOWTO.md`](../appearance/RENDER_HOWTO.md)

---

*本页"实测"数据均为 2026-11-07 本机采样；标注 PROVISIONAL/未验证的条目在首次实跑与 Bambu 实机切片前不得当作已验证结论。*
