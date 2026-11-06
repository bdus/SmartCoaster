# Kromacut Flat Paint → 多材料打印模型（appearance/build/print）

> **English summary.** Two art plates (`dog`, `elf`) were converted headlessly with
> Kromacut v4.2.0's own Flat Paint engine (not the GUI): `dog` → 6 filaments,
> 86.4 × 86.4 × 1.2 mm; `elf` → 7 filaments, 86.4 × 86.4 × 1.4 mm. Each plate
> yields one multi-material 3MF (one 3MF object per filament, slicer metadata
> included) plus one binary STL per filament (XY centred on 0,0, bottom at z=0),
> a manifest with sha256/geometry numbers, and 25/25 CLI self-checks. An
> independent Python read-back (zipfile + ElementTree + struct, no shared code)
> re-verified object/triangle counts, materials, extruders, bboxes and every
> file sha256. Two consecutive conversions produced byte-identical STLs. **Not**
> tested: opening the 3MF in a slicer/Bambu Studio, and any physical print.
>
> Generated: 2026-11-06 · Kromacut v4.2.0 · Node v24.15.0 · bridge
> `kromacut-flatpaint.mjs` v1.0.0 · exported choice `smooth=none`.
>
> **Revision 2 (post-review, geometry bytes unchanged):** the earlier "duplicate
> triangles" report was re-diagnosed. Those faces are NOT duplicates: they are
> **opposite-winding coincident interface caps between abutting parts of the same
> filament** (intended closed per-material solids). No STL/3MF byte changed; only
> `manifest.json` (two new analysis blocks + 3 new checks) and this report were
> updated. See §4.4 and §5.3 for the full diagnosis and the new edge-incidence
> analysis of ALL objects (including the large foundation objects).

## 1. 命令（一条命令复跑）

```bash
# from the SmartCoaster project root
appearance/kromacut/run_convert.sh                 # both arts, smooth=none (shipped choice)
DETERMINISM=1 appearance/kromacut/run_convert.sh   # same + rerun each art and compare geometry/STL bytes
SMOOTH=medium appearance/kromacut/run_convert.sh   # optional smoothed variant (not shipped)
```

Under the hood:

```bash
node /data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs \
  --art  appearance/build/art/dog \
  --out  appearance/build/print/dog \
  --smooth none --name dog --require-full-palette
# same for elf
```

实测（本机，串行，含 CLI 自带回读自检）：单 art **dog 18.5 s / elf 23.4 s**，
两 art 一条 `run_convert.sh` 共 **约 44 s**（取重复两次的稳定值，见 §3.3）。

Inputs are the Lead-owned art files; **nothing in `appearance/build/art` was modified**
and the input sha256 values below match `appearance/build/art/REPORT.md`.

| art | art dir | `layer_counts.bin` sha256 | palette (bottom-up) | layers | thickness |
|---|---|---|---|---|---|
| dog | `appearance/build/art/dog` | `10da7da67993a6fc3e78ac71d01fde0aefae9cb7a7ce2bf8ec904f498dbd41b3` | `#FBF4E8, #CBE0F5, #9FB2DA, #F9CD72, #F09FAF, #6C574C` | 6 × 0.2 mm | **1.20 mm** |
| elf | `appearance/build/art/elf` | `cc8627dc3a8846bc045c4640780761a7e738fde7ca18bf0acbf28facf9cd5919` | `#EDE1F0, #D9CFE6, #C3AEDC, #F7D2C0, #E8A9B8, #C9A45B, #5B4A72` | 7 × 0.2 mm | **1.40 mm** |

Both plates: 576 × 576 px, `pixel_size_mm=0.15`, `layer_height_mm=0.2`,
`first_layer=0.2`, `orientation=face-up`, opaque footprint 260 408 px (71368
transparent). The dog/elf thickness difference is intentional (Lead decision:
round LUMEN version = 6-colour dog, square version = 7-colour elf).

## 2. 交付文件

```
appearance/build/print/
├── dog/  dog_kromacut.3mf + filament_{1..6}_<HEX>.stl + manifest.json   (112 MB)
├── elf/  elf_kromacut.3mf + filament_{1..7}_<HEX>.stl + manifest.json   (144 MB)
└── REPORT.md
```

> 注：`dog/preview_top.png`、`elf/preview_top.png` 由下游渲染/预览步骤添加，不是本桥接 CLI 的产物；
> `run_convert.sh` 重跑时不会删除它们（只替换 3MF/STL/manifest）。

- 3MF = native Kromacut exporter output (`3D/3dmodel.model` +
  `Metadata/model_settings.config`, `project_settings.config`, `kromacut.config`),
  **one object per physical filament** + one assembly object, sliced-coordinate
  bbox `0,0,0 … 86.4,86.4,thickness` (mm, z=0 at the build plate).
- STL = one binary STL per filament, header `Kromacut Binary STL`, **XY bbox
  centred on (0,0), print bottom at z=0**.
- `filament_<n>_<HEX>.stl` where `n` is the same 1-based order as the 3MF base
  materials / slicer extruders — `filament_1` is the foundation filament that
  touches the plate.

## 3. 结果 — 导出选择 `smooth=none`

### 3.1 dog（LUMEN round 版，Ø86.4 × 1.2 mm，6 材料）

3MF: **`dog_kromacut.3mf`**, 19 706 638 B (uncompressed model XML 136 777 682 B),
sha256 `0b310d5d4a1b699daf5297399a8ea81caae11d4edd3de8f029e29d9c623cc5c6`.

| # | hex | 3MF object | 3MF tris | STL tris | STL bbox (mm) | STL bytes | STL sha256 (16) |
|---|---|---|---|---|---|---|---|
| 1 | `FBF4E8` | Flat Paint filament (#FBF4E8) | 1 236 024 | 1 236 024 | −43.200…43.200 × −43.200…43.200 × 0…1.2 | 61 801 284 | `af91f80cf94353e7` |
| 2 | `CBE0F5` | Flat Paint filament (#CBE0F5) | 324 776 | 324 776 | −43.200…43.200 × −43.050…43.200 × 0.2…1.2 | 16 238 884 | `70c2746eb58a6289` |
| 3 | `9FB2DA` | Flat Paint filament (#9FB2DA) | 145 340 | 145 340 | −38.100…43.050 × −43.050…38.550 × 0.4…1.2 | 7 267 084 | `d76f2b795316078d` |
| 4 | `F9CD72` | Flat Paint filament (#F9CD72) | 113 796 | 113 796 | −38.100…38.850 × −37.500…38.550 × 0.6…1.2 | 5 689 884 | `9c6cf1747f883e42` |
| 5 | `F09FAF` | Flat Paint filament (#F09FAF) | 62 748 | 62 748 | −38.100…38.850 × −34.050…31.050 × 0.8…1.2 | 3 137 484 | `7d950c065952e739` |
| 6 | `6C574C` | Flat Paint filament (#6C574C) | 59 048 | 59 048 | −38.100…38.850 × −34.050…31.050 × 1.0…1.2 | 2 952 484 | `18a0419375b78ea5` |

- 3MF: 6 mesh objects (+1 assembly), total **1 941 732 triangles / 971 992 vertices**.
- 3MF native bbox: **86.4 × 86.4 × 1.2 mm**, min z = 0.
- STL union bbox: **−43.2…43.2 × −43.2…43.2 × 0…1.2 mm** (size 86.400002 × 86.400002 × 1.2).
- STL total 97 087 104 B, zero zero-area triangles.

### 3.2 elf（square_v1 版，Ø86.4 × 1.4 mm，7 材料）

3MF: **`elf_kromacut.3mf`**, 25 632 180 B (uncompressed model XML 177 078 180 B),
sha256 `db56539616d53de66d691d7614c7b54c0c75f641eb9845230995462845b76e46`.

| # | hex | 3MF object | 3MF tris | STL tris | STL bbox (mm) | STL bytes | STL sha256 (16) |
|---|---|---|---|---|---|---|---|
| 1 | `EDE1F0` | Flat Paint filament (#EDE1F0) | 1 574 104 | 1 574 104 | −43.200…43.200 × −43.200…43.200 × 0…1.4 | 78 705 284 | `dd8bbe44ba508d46` |
| 2 | `D9CFE6` | Flat Paint filament (#D9CFE6) | 311 920 | 311 920 | −39.450…43.200 × −43.050…43.050 × 0.2…1.4 | 15 596 084 | `cd4d3a74e289421b` |
| 3 | `C3AEDC` | Flat Paint filament (#C3AEDC) | 232 036 | 232 036 | −39.450…43.200 × −40.200…37.950 × 0.4…1.4 | 11 601 884 | `ddc795b50e63145d` |
| 4 | `F7D2C0` | Flat Paint filament (#F7D2C0) | 146 216 | 146 216 | −38.250…42.900 × −39.600…34.650 × 0.6…1.4 | 7 310 884 | `bff5e1ddaa038c22` |
| 5 | `E8A9B8` | Flat Paint filament (#E8A9B8) | 99 704 | 99 704 | −37.350…42.900 × −36.900…34.650 × 0.8…1.4 | 4 985 284 | `5c140dd862c25318` |
| 6 | `C9A45B` | Flat Paint filament (#C9A45B) | 72 264 | 72 264 | −37.350…42.900 × −36.750…34.650 × 1.0…1.4 | 3 613 284 | `7b6f9cd0dc6bbbe7` |
| 7 | `5B4A72` | Flat Paint filament (#5B4A72) | 64 296 | 64 296 | −37.350…42.900 × −36.750…28.800 × 1.2…1.4 | 3 214 884 | `40d0300148eb4452` |

- 3MF: 7 mesh objects (+1 assembly), total **2 500 540 triangles / 1 257 078 vertices**.
- 3MF native bbox: **86.4 × 86.4 × 1.4 mm**, min z = 0.
- STL union bbox: **−43.2…43.2 × −43.2…43.2 × 0…1.4 mm** (size 86.400002 × 86.400002 × 1.4).
- STL total 125 027 588 B, zero zero-area triangles.

> Full 64-char sha256 for every file is in each art's `manifest.json`
> (`export.threeMfSha256`, `stls[].sha256`); the 16-hex prefixes above are for
> quick diffing. 3MF bytes are **not** reproducible run-to-run (Kromacut embeds
> random `p:UUID`s + JSZip timestamps); the current on-disk file sha is listed.

### 3.3 运行时间（单 art，含 CLI 自带回读自检；本机，Node 24.15.0，CPU 串行）

| art | 2 次实测 total | 其中 mesh(布局+网格) | 3MF 导出 | STL 导出 | 自检回读 |
|---|---|---|---|---|---|
| dog | 18 489 ms / 18 745 ms | 4 247 ms | 6 169 ms | 978 ms | 6 456 ms |
| elf | 23 411 ms / 23 849 ms | 5 281 ms | 7 812 ms | 1 180 ms | 8 458 ms |

整条 `run_convert.sh`（两 art，含启动 Node/Vite 各一次）：**约 44 s**；
`DETERMINISM=1`（再各跑一遍 + 逐字节/几何比对）：约 **90 s**。若只要几何文件
（不做回读自检），单 art ≈ 12.0 s（dog）/ 15.0 s（elf）。`smooth` 的代价见 §6。
**Revision 2 说明**：上表是交付那次转换的实测值；CLI 现在额外对 13 个 STL 做全量
边入射/重合面分析（`timingsMs.meshIntegrityMs`），在交付文件上单独实测为 dog
**7.3 s** / elf **10.1 s**，因此今后一条命令重跑预计约 **26 s / 33 s**
（交付文件本身未重跑、未改动）。

### 3.4 三角数为什么高、可调旋钮实测（measure, not guess）

Flat Paint 网格由 Kromacut 的「每行最大矩形 + 矩形边界三角化」生成，三角数 ≈
O(周长 × 行数)，因此 **0.15 mm/pixel 的 576² 格子 + 水彩画碎片化色块** 会天然产生
百万级三角：dog 合计 1 941 732 tris（foundation object 1 236 024 = 63.7%）、
elf 合计 2 500 540 tris（foundation 1 574 104 = 62.9%）。3MF 内 model XML 解压后
137/177 MB；STL 合计 97/125 MB。对 render 无压力，对切片器偏重。

为不猜数字，用**从 dog 层数网格派生的对照网格**（仅 `/tmp`，未改动/未替换交付 art）
量化各旋钮效果（`smooth=none`，同机串行）：

| 试验 | 网格 | 相邻像素颜色跳变数* | 三角数 | Δ三角 | 转换 wall time |
|---|---|---|---|---|---|
| 基线（交付 art） | 576² @0.15 mm | 20 207 | 1 941 732 | — | 18.7 s |
| 更强 dedither（额外 1 轮 3×3 多数滤波，同 576²） | 576² @0.15 mm | 19 813（−1.9%） | 1 929 920 | **−0.61%** | 18.2 s |
| 更大 pixel（2× 多数下采样 → 288² @0.30 mm） | 288² @0.30 mm | 9 828（−51.4%） | **574 208** | **−70.4%** | 6.1 s |
| smooth meshing（交付 art，`medium`） | 576² @0.15 mm | 20 207 | 1 941 872 | **+0.007%** | 19.5 s |

\* 4-邻域相邻像素值不同的边数，衡量色块碎片化程度。

结论（实测）：**有效的旋钮是更大的 pixel size**（0.30 mm 时三角数 −70%、转换 −67%
时间），即在 `appearance/tools/make_art.py` 重新出图；**更强 dedither 几乎没有收益**
（art 生成时已做 3 轮多数滤波 + 孤立像素清除，跳变只再降 1.9%）；**smooth meshing
不会减三角数**（反而 +0.007% 三角、+10% 3MF 体积，只是把边界圆角化）。当前交付按
Lead 指定的 0.15 mm art 原样导出，不做减面（减面会改变 slicer 预览/实际轮廓）。

## 4. 验证 — 实际做了什么

### 4.1 CLI 自检（每次转换自动执行，失败即 exit 1）

两个 art 均 **25/25 PASS**（22 项几何/导出检查 + 3 项新增网格完整性检查）。
检查项（实际数字见 manifest `verification.checks`）：

- 输入：`layer_counts.bin` 大小/取值合法；`layer_count == palette.length`；不透明像素 > 0；全色板被使用。
- 3MF：zip 可解、6 个必需 entry 存在；`3dmodel.model` / `model_settings.config` XML 良构；`project_settings.config` JSON 可解析；**mesh object 数 == 材料数**（dog 6 / elf 7，另 1 个 assembly object）；每个 object 三角形 > 0、0 个零面积三角形；object 名称/`pindex`/`base materials`/`filament_colour`/`extruder 1..N` 与调色板逐项对应。
- 3MF 几何与源网格**逐 object 相等**（无丢弃/合并错误）：dog 1 941 732 tris / 971 992 verts；elf 2 500 540 / 1 257 078。
- bbox：3MF == 不透明像素足迹 × pixel size，`z = 0 … totalHeight`，dog 86.4×86.4×1.2、elf 86.4×86.4×1.4（误差 ≤ 1e-3 mm）。
- STL：每 filament 一个文件；三角数 == 源网格；逐文件 bbox == 源网格平移后的 bbox；union bbox 居中于 0,0、底 z=0；零面积三角形 = 0。
- 元数据：3MF 内 `Kromacut:SmoothMeshingStrength=none`、`slicer layer_height=0.2`、`first_layer_height=0.2`。
- **网格完整性（Revision 2 新增，覆盖全部 13 个 object，不跳过 foundation）**：
  `mesh.edges.boundary-free`（0 条边界边）、`mesh.edges.even-incidence`（所有边入射
  次数为偶数）、`mesh.interface-faces.opposite-winding`（所有重合面都是同一 filament
  相邻实体之间的反向绕制水平 cap）。详见 §4.4。

### 4.2 独立回读（第三方实现，不复用桥接代码）

`python3`（`zipfile` + `xml.etree.ElementTree` + `struct` + `hashlib`）重新解析两个
art 的 3MF 与全部 13 个 STL，**全部 PASS**：

- 3MF XML 良构，`unit="millimeter"`；object 数 + assembly 数正确；逐 object 三角/顶点数与 manifest 一致；总三角数 dog 1 941 732 / elf 2 500 540；**无零面积三角形**；base materials / extruders / layer-height 元数据一致；bbox 分别 (0,0,0)…(86.4,86.4,1.2) 与 (0,0,0)…(86.4,86.4,1.4)。
- 边入射/闭合性：Revision 1 的 Python 独立回读只对 ≤300k tris 的对象做「每条边恰好 2 次使用」检查（dog 4/6、elf 5/7）；Revision 2 起 CLI 用精确 float32 焊接 + 边入射直方图把 **全部 13 个 object（含 1.24M/1.57M tris 的 foundation）** 都检查了：0 条边界边、所有边入射为偶数、最大入射 6（三个实体接合边）。Python 侧仍只做抽样，CLI 侧已全覆盖，见 §4.4。
- 每个 STL：header、三角数、bbox 与 manifest 一致，sha256 与 manifest 一致；union bbox 正确。
- 输入 `art.json` / `layer_counts.bin` sha256 与 manifest、与 `appearance/build/art/REPORT.md` 一致（输入未被修改）。

### 4.3 复跑确定性

连续两次转换（各自独立进程）：

- **13 个 STL 逐字节相同**（sha256 全部一致），三角数、bbox、3MF 每 object 的三角/顶点数完全一致；
- 3MF sha256 **不同**（预期：Kromacut 给每个 object/build 注入随机 `p:UUID`，JSZip 带时间戳），几何内容一致；
- `manifest.json` 因 `generatedAt` + timings 不同而不同，几何字段一致。

`DETERMINISM=1 appearance/kromacut/run_convert.sh` 自动做上述比对，结果
`dog: PASS`、`elf: PASS`。

### 4.4 重合界面面片与网格完整性（Revision 2 复核；**几何未改动**）

复核结论：**先前被当作「重复三角形」的面片不是重复，也不是退化几何，绝对不能删。**
它们是**同一 filament、上下相邻的闭合实体之间的公共界面 cap**：一对三角形拥有完全相同
的 3 个顶点，但**绕制方向相反**（一个法线 +Z、一个 −Z），因此从「无序顶点三元组」看
像重复，从流形/封闭实体看是两份闭合壳体的内部贴合面。

**成因（用 layout 结构 + 实测不变量确认，非推测）**：face-up 布局对每个层数类别 `k`
输出若干**各自闭合**的实体（`backing` + `zone…` + `face`）。只有 foundation
（palette[0]）会在**同一像素掩码**上出现多个上下相邻的实体（`backing class k` 之上紧接
`zone class k` 或 `face class k`），所以只有 foundation 有重合面对；其他颜色同一掩码上
只出现一次，实测 pairs = 0。每对 cap 的 z 正好等于 Kromacut `levelBase()` 生成的层边界。

**实测不变量（两个 art、全部 13 个 filament）**：

| art | 有重合面的 filament | 对数 | 反向绕制 | 同向绕制 | 非水平 | 多重度>2 | 按 z 分布 |
|---|---|---|---|---|---|---|---|
| dog | #1 `FBF4E8`（foundation） | **261 777** | 261 777（100%） | 0 | 0 | 0 | z=1.0: 147 510；0.8: 80 909；0.6: 10 994；0.4: 20 916；0.2: 1 448 |
| dog | #2–#6 其他颜色 | 0 | — | — | — | — | — |
| elf | #1 `EDE1F0`（foundation） | **325 697** | 325 697（100%） | 0 | 0 | 0 | z=1.2: 233 910；1.0: 30 352；0.8: 32 112；0.6: 17 487；0.4: 9 197；0.2: 2 639 |
| elf | #2–#7 其他颜色 | 0 | — | — | — | — | — |

（数字来自 manifest 新字段 `coincidentInterfaceFaces.perFilament[].pairs / pairsByZ`。）

**为什么保留**：每个 material 的 3MF object 是「多个闭合实体」的并集，不是单一流形；
相邻实体的公共界面在切片器里属于实体内部界面，不参与外表面。删掉每对中的一个会让
该 material 的 object 失去封闭性（本体反而变差），因此 **不做任何去重/去面**——交付的
STL/3MF 字节与 Revision 1 完全相同（见 §4.5）。

**边入射（全部 object，取代原先 ≤300k tris 的抽样）**：对每个 filament 用精确 float32
顶点焊接后统计每条边被多少三角形使用：

| filament | triangles | distinct edges | incidence 2 | incidence 4 | incidence 6 | boundary | max |
|---|---|---|---|---|---|---|---|
| dog #1 foundation | 1 236 024 | 1 419 108 | 991 947 | 419 394 | 7 767 | **0** | **6** |
| dog #2–#5 | 324 776 / 145 340 / 113 796 / 62 748 | — | 见 manifest | 3 522 / 1 304 / 342 / 147 | 0 | 0 | 4 |
| dog #6 | 59 048 | 88 572 | 88 572 | 0 | 0 | 0 | 2 |
| elf #1 foundation | 1 574 104 | 1 807 235 | 1 262 985 | 534 579 | 9 671 | **0** | **6** |
| elf #2–#6 | 311 920 / 232 036 / 146 216 / 99 704 / 72 264 | — | 见 manifest | 4 814 / 2 459 / 1 737 / 373 / 161 | 0 | 0 | 4 |
| elf #7 | 64 296 | 96 444 | 96 444 | 0 | 0 | 0 | 2 |

- **所有边入射都是偶数，0 条边界边（incidence 1）** → 每个 material object 无开放边界。
- incidence 2 = 普通流形边；4 = 两个相邻实体的贴合边；**6 = 三个实体在同一条边接合**。
  预期中的「max ≤ 4」在本模型**不成立**：dog foundation 有 7 767 条、elf foundation 有
  9 671 条 incidence-6 边。抽样定位到具体边（如 dog 在 z=1.0、x∈[−3.00,−2.85]、
  y≈−42.45 的水平边）：参与该边的 6 个三角形面片来自 z 范围 `0..1`、`0.8..1`、
  `1..1.2` 的 3 个同一 filament 实体，另有 z=1.0 处的水平 cap —— 即 3 个实体在此接合，
  属正常多实体接合，不是缺陷。自检因此按「偶数入射 + 无边界」判定
  （`mesh.edges.even-incidence`），并把每条边的直方图写进 manifest，而不是强加 ≤4。

### 4.5 Revision 2 前后对比（证明交付几何字节未变）

| 项 | Revision 1（交付） | Revision 2（本次） | 变化 |
|---|---|---|---|
| STL 文件（13 个）字节 / sha256 | 交付值 | **完全相同**（脚本 before/after 逐文件 sha256 比对） | 无 |
| 3MF 文件（2 个）字节 / sha256 | dog `0b310d5d…`、elf `db565396…` | **完全相同** | 无 |
| STL/3MF 三角数、bbox、z 范围 | 见 §3 | 相同 | 无 |
| `manifest.json` | 22 checks，无完整性块 | 25 checks + `coincidentInterfaceFaces` + `meshIntegrity` | 仅新增文档/检查数据 |
| 转换是否重跑 | — | **未重跑**（按要求） | — |
| STL 逐字节确定性 | 已验证 | 结论不变（本次未产生新 STL） | — |

新增分析耗时（在交付文件上实测，Node 24.15.0）：dog **7.3 s**、elf **10.1 s**。

## 5. 与下游（shell / render）的关系

### 5.1 外壳（shell）配合

- dog 打印件：Ø86.4 × **1.20 mm**，用于 round/LUMEN 版（shell 侧 pocket floor 15.75）。
- elf 打印件：Ø86.4 × **1.40 mm**，用于 square_v1 版（Lead 更新后的 pocket：floor z=16.55、depth 1.45）。
  `floor_z` 属于 `appearance/build/shell/` 的 shell.json，**不写入本目录 manifest**。
- 本目录 manifest 提供打印件自身 bbox（native 0…86.4 XY、z=0…thickness；STL 为居中坐标）供 render 校验摆放。

### 5.2 朝向契约（render 必须按此判断「图是否正」）

坐标链（`face-up`，全程无镜像）：

1. 输入 `layer_counts.bin`：`row 0 = 图像顶行`，`col 0 = 图像左列`。
2. Kromacut `orientFlatPaintLayerCounts(..., 'face-up')` **只翻转 scene Y**：
   图像行 `r` → 网格行 `H-1-r`；X 不变（左列仍是左）。
3. 网格单元 `(c, r)` → 世界坐标 `x ∈ [c·ps, (c+1)·ps]`、`y ∈ [r·ps, (r+1)·ps]`，
   所以**图像顶边 = 世界 +Y 最大侧，图像左边 = 世界 X 最小侧**；z 向上。
4. **3MF（native）**：`x ∈ [0, 86.4]`、`y ∈ [0, 86.4]`、`z ∈ [0, 1.2/1.4]`。
5. **STL**：整体平移 `(−W·ps/2, −H·ps/2, −minZ)` → `x,y ∈ [−43.2, 43.2]`、
   `z ∈ [0, thickness]`。Blender 4.5 的 STL 导入器不做轴变换（Z-up 原样），因此
   **俯视（沿 −Z 看，视图 +Y 向上）应看到正的图像，图像顶部朝 +Y，不镜像**。

数值校验（独立从 `layer_counts.bin` 推期望，再与 STL 实测比）：可见顶层的颜色
= pixels with `count == layerCount`，即最后一个 filament object（dog `#6C574C`、
elf `#5B4A72`，其 z 只占最高 0.2 mm 层）：

| art | 顶色 object | 期望 bbox（图像 Y 翻转 + 居中，mm） | 实测 STL bbox（mm） | 最大偏差 |
|---|---|---|---|---|
| dog | `filament_6_6C574C.stl` | x −38.100…38.850，y −34.050…31.050，z 1.0…1.2 | 同左 | < 1e-3 |
| elf | `filament_7_5B4A72.stl` | x −37.350…42.900，y −36.750…28.800，z 1.2…1.4 | 同左 | < 1e-3 |

若 render 看到图像上下颠倒或左右镜像，即与上述契约不符（bbox 对不上可立即发现：
这两个顶色区域在图像中不对称）。

### 5.3 给 render / 3MF 装配的通知

- print-only 3MF 与 per-filament STL 每个 material object 都是「多个闭合实体的并集」，
  内部存在**反向绕制的重合界面 cap**（dog foundation 261 777 对、elf 325 697 对）。
  这是正常且必要的结构；装配/验证时**不要**把它们当重复面去重（去重会破坏封闭性）。
  render 的装配器若自行 weld/dedupe，请在报告中注明其三角数下降属于该内部界面合并，
  不是几何丢失。
- 打印件 bbox / z 范围 / 朝向契约与 Revision 1 相同（§5.1、§5.2），无需重新摆放。

## 6. `smooth=medium` 对比（可行，但**未作为导出选择**）

`SMOOTH=medium` 在真实 576×576 art 上完整跑通并自检 PASS（工程实现上与 none 同一路径，
仅 `createFlatPaintMesher` 的 strength 参数不同）：

| art | total time | Δ vs none | 三角数 | 3MF size | bbox | STL 零面积三角（float32） |
|---|---|---|---|---|---|---|
| dog | 18 908 ms（wall 19.5 s） | +~2% | 1 941 872（+140） | 21 697 333 B（+10%） | 86.4×86.4×1.2（不变） | 8（仅 filament 1） |
| elf | 24 488 ms（wall 25.2 s） | +~4.6% | 2 500 656（+116） | 28 388 195 B（+10.8%） | 86.4×86.4×1.4（不变） | 62（分布 7 个文件） |

结论：576×576 下 `medium` 并不慢（+2~5%），但对本来就 45° 直边的 Flat Paint 平板
只带来圆角化收益，且平滑后的 cap 三角化会在 binary STL 的 float32 精度下产生
**8~62 个亚微米零面积三角形**（切片器会忽略；3MF 内为 0）。因此导出选择保持
`smooth=none`（0 零面积三角、逐字节可复现、bbox 精确）；需要圆滑轮廓时可随时用
`SMOOTH=medium appearance/kromacut/run_convert.sh` 重出。`minimal/aggressive` 未实测。

## 7. 未验证 / 已知限制（重要）

1. **没有切片器验证**：3MF 未导入 Bambu Studio / OrcaSlicer / Creality Print，
   未验证多材料映射、换料塔、打印时间/耗材估算；也没有任何**实物打印**。
   （Kromacut 的 3MF 结构本身就是 Bambu/Orca 兼容格式，但导入行为未实测。）
2. **没有颜色管理**：palette hex 按原样写入，未做 ICC/耗材光谱校准；实物颜色会与
   渲染/原画不同。
3. **面朝上（face-up）单一路径**：CLI 支持 `face-down`（Kromacut carrier 代码路径存在），
   但本流水线只跑 face-up，未做 face-down 验证。
4. **模型很重**：Flat Paint 几何由 Kromacut 的矩形 cap 贪心算法生成，0.15 mm/576²
   天然三角数高（dog 1.94M、elf 2.50M；3MF 内 model XML 解压后 137/177 MB）。这是
   Kromacut 原生几何，未做减面（减面会改变 slicer 预览与实际打印轮廓）。§3.4 实测了
   可调旋钮：0.30 mm pixel（288²）可把三角数降到 574 208（−70%）、转换 6.1 s，但需要
   重新生成 art；更强 dedither 收益 <1%；smooth meshing 不减三角。下游 Blender/render
   与 Bambu 需要能承受该体量；6/7 色需要 AMS/换料器。
5. **输入数据不在本次验证范围**：art 的量化/调色板/像素层数由
   `appearance/tools/make_art.py` 负责（见 `appearance/build/art/REPORT.md`）；
   本桥接不修改 art，也不修复 art 的孤立像素/边缘问题。
6. **版本锁定**：桥接针对 Kromacut v4.2.0 源码 tag；三个核心模块 sha256 已写入
   manifest（`tool.kromacutModules`）。升级 Kromacut 需重新验证 API 与输出。
7. 未验证 3MF 在非 Bambu 系切片器中的 `model_settings.config` 解释；未验证
   从 3MF 重新导出的 STL 与本目录 STL 的逐字节一致性（本目录 STL 由同一网格对象
   经 Kromacut `exportObjectToStlBlob` 独立导出，几何数值与 3MF 逐 object 三角数/bbox 已核对）。
8. `smooth=minimal/aggressive`、`face-down`、非整数 `first_layer_thickness` 未实测。

## 8. 环境快照

| 项 | 值 |
|---|---|
| Kromacut | v4.2.0（AppImage sha256 `c1cb1bfac14199a3…44495ca`；源码 tag tarball sha256 `74ae596f0d80a34e…17df126a`；`src/Kromacut-4.2.0`，未修改） |
| Node.js | v24.15.0（`/usr/bin/node`） |
| three / jszip / vite | 0.180.0 / 3.10.1 / 7.1.2 |
| 桥接 CLI | `/data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs` v1.0.0 |
| 项目封装 | `appearance/kromacut/run_convert.sh`、`appearance/kromacut/README.md` |
| 关键模块 sha256 | flatPaint.ts `e87fa95f…82b2d6`、flatPaintMeshing.ts `94edbaea…3db58ee`、export3mf.ts `62541b91…c9604`、exportStl.ts `76e784f3…a55`、meshing.ts `a81f6b50…862a2`（全量见 manifest） |
| 本目录总量 | ≈257 MB（dog 112 MB + elf 144 MB，含 13 个 STL + 2 个下游预览 PNG） |
