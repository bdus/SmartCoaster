# appearance/ — IP 印花 → 多材料一体打印（Kromacut 接入）

> 版本：v1.0（2026-11-06） · 负责人：Lead（实现由 shell-cad / kroma / render 三个 teammate + Lead 集成）
> 状态：**数字样机 / 多材料装配 / 渲染 / 3MF / 可打印 STL 交付已完成并通过 Lead 独立只读验收 130/130**；
> **实物打印与 Bambu Studio 实际切片未验证**。
> 相关：`/data/Documents/tools/KROMACUT_INSTALL_NOTES.md`（安装）、`docs/01` §17（流水线定位）、
> `docs/REPORT_技术报告.md` §11（技术汇总）、`docs/REPORT_成果展示.md` §2.5（成果图）、`docs/HANDOFF.md` §10。

---

## 0. 结论摘要（先看这里）

**目标**：把 IP 印花图片变成**有厚度的多材料几何**，嵌进外壳浅槽，随外壳**一次多材料打印**成型；
Blender 里印花与外壳**始终是两个对象**，真正的"融合"发生在 Bambu Studio 切片阶段。

| 项 | 结论 |
|---|---|
| Kromacut 的定位 | **只做"图片 → 多材料几何"**；不做外壳融合、不做曲面贴图、不做 CAD（见 §1.1） |
| 接入方式 | 调用 Kromacut v4.2.0 **自身 TypeScript 引擎**（Flat Paint + 3MF 导出）做 headless 转换，**不点 GUI、不改源码**（见 §3） |
| 融合方式 | 外壳开浅槽 → 印花过盈嵌入 → 3MF 里两个独立对象 → Bambu 切片时按材料解析交界（见 §1.2–1.4、§7） |
| 两版交付 | 圆形 LUMEN Ø110 + 狗（6 色/1.20 mm）；方形 square_v1 100×100 + 精灵（7 色/1.40 mm） |
| 验收 | Kromacut 25/25、外壳 94/94、3MF 两版 `ok:true`、渲染 11 张；**Lead 只读验收 130/130 PASS** |
| 3D 打印交付 | **`render/print/stl/` 一个平坦目录：18 个可打印 STL**（外壳/开槽顶板/按键/印花逐耗材，按**打印姿态**烘焙：印花正面贴床第一层）+ `PRINT_READY.3mf`（床面排版）+ 参考图/manifest/CHECKSUMS；床面 218.9×110.0 / 208.0×114.0 mm（≤220，**无需支撑**） |
| 未验证 | Bambu 实际导入/耗材映射/逐层切片；实物颜色/层厚/结合强度；开槽顶板 FEA 与 21 项功能自检 |

---

## 1. 设计决策（为什么这样分工）

### 1.1 Kromacut 的能力边界（本机实测）

| 能做 | 不能做 |
|---|---|
| 图片 → Auto-paint 叠层浮雕 | 导入 STEP/STL 外壳并在其表面贴图 |
| 图片 → **Flat Paint 多材料平板**（face-down 透明承载 / face-up 无承载） | 与任意 CAD 外壳布尔融合 |
| 按**物理耗材**分组导出 3MF（每耗材一个对象 + 3MF 装配） | 直接输出带外壳的一体 CAD |
| 2D 调色/减色/Dedither、隐藏距离标定、层预览 | 稳定官方 CLI/API（4.2.0 无；本项目自建薄桥接） |

结论：把它放在 **CAD 外壳之后、Blender 之前**，作为"图案几何发生器"；不要指望它替代 CAD 或切片器。

### 1.2 为什么不在 Blender 里布尔合并外壳与印花

- 布尔合并会把不同耗材的几何**合并成一个 mesh**，丢掉"哪个面属于哪种耗材"的对象边界，
  切片软件就无法按对象分配 AMS 槽位；
- 我们要的是：**机械上成为一个零件、文件里保留多材料对象、切片时解析成一体**；
- 因此 Blender 只做数字样机/对位/渲染，**不做融合裁决**。融合由 Bambu Studio 完成。

### 1.3 为什么外壳必须开浅槽（"表面平整"的来源）

- 印花本身有厚度 `t`（本次 1.20 / 1.40 mm）；
- 外壳沿口（rim）必须平整，因此顶板挖一个 `Ø86.0`、深 `t + 0.05` 的浅槽；
- 印花底面坐在槽底，顶面 = `floor + t = rim − 0.05 mm`，即**比沿口低 0.05 mm**；
- 顶板剩余肉厚：方形 1.55 mm、圆形 1.75 mm（见 §6.5 的功能影响与风险）。

### 1.4 过盈（interference）而不是零间隙

两个网格面恰好共面会产生缝隙/结合不牢。首版取：

| 参数 | 值 | 说明 |
|---|---|---|
| 印花直径 | **Ø86.4 mm** | 576 px × 0.15 mm/px（几何边界 86.37） |
| 槽直径 | **Ø86.0 mm** | 半径 43.000 |
| 名义径向过盈 | **0.20 mm** | 印花 r43.2 vs 槽 r43.0 |
| 实测最大过盈 | **0.288 mm** | 含 0.15 mm 像素台阶角点（r_max 43.288） |
| 顶面落差 | **0.05 mm** | 印花顶 16.95 / 17.95 vs 沿口 17.00 / 18.00 |

> `PROVISIONAL`：0.2 mm 过盈与 0.05 mm 顶差是首版工程假设，需按喷嘴、线宽、材料收缩
> 和实际切片结果标定；不是通用公差。

### 1.5 为什么用 headless 桥接，而不是 GUI 自动化

- 项目红线（`docs/01` §14.4）：**不用 GUI 自动化（点菜单/拖窗口）调专业软件**；
- Kromacut 是 AGPL-3.0 开源 TS 应用，几何/导出逻辑在 `src/lib/*`，上游 CI 本身就在 Node 下跑；
- 我们只**调用其公开模块**（`flatPaint.ts` / `flatPaintMeshing.ts` / `export3mf.ts`），
  不修改、不 fork；图片→几何因此是**一条命令、可复现、可批量**的流水线步骤；
- GUI 仍保留给人工调色/试排（`kromacut` 命令）。

### 1.6 许可边界（AGPL-3.0）

- 独立调用 Kromacut 生成设计文件，**不等于**设计文件必须开源；
- 若日后修改 Kromacut 或把其代码嵌入自家发布软件，需重新评估 AGPL 义务；
- 安装/版本/校验记录：`/data/Documents/tools/KROMACUT_INSTALL_NOTES.md`。

---

## 2. 全流程与数据流

```text
appearance/src/surface.png                 原始拼版（两枚圆形印花，1774×887，白底）
        │  appearance/tools/make_art.py           拆开 / 椭圆回正圆 / 圆外透明 / Lab 量化
        ▼
appearance/build/art/<art>/                  art_rgba.png + layer_counts.bin + art.json
        │  Kromacut v4.2.0 headless Flat Paint（face-up，无透明承载层）
        ▼
appearance/build/print/<art>/                多材料 3MF + 每耗材 STL + manifest.json
        │
        ├── appearance/cad/run_shell.sh      顶板开浅槽（从已验证 STEP 导入 + 布尔切）
        │                                    → plate_recessed.stl/.step + shell.json
        ▼
appearance/render/build_scene.py            Blender 数字样机：外壳与印花分开 collection
        │                                    hero/top/print_top/macro_edge/section + .blend
        ▼
appearance/render/make_3mf.py               装配 3MF：外壳零件 + PRINT_ART 装配对象（每耗材 component）
        │                                    validation.json（只读回验）
        ▼
render/print/appearance/run_print_stage.sh  打印交付：可打印 STL 套件（外壳/顶板/按键/印花逐耗材）
        │                                    + 220 床面排版 + 打印参考图 + manifest/checksums
        ▼
Bambu Studio                                导入 → 装配/耗材映射 → 逐层检查 → 切片 → 打印
```

**阶段职责与验收**

| # | 阶段 | 命令（工作区根目录） | 输入 | 输出 | 验收 |
|---|---|---|---|---|---|
| 0 | 工具安装 | `bash appearance/tools/install_kromacut.sh` | GitHub 官方 release | `/data/Documents/tools/Kromacut` | GUI 可启动（Xvfb 截屏）、headless 模块可加载 |
| 1 | 素材 | `python3 appearance/tools/make_art.py` | `appearance/src/surface.png` | `build/art/<art>/` | 尺寸/色板/层数一致、孤立像素 0、透明正确 |
| 2 | 印花几何 | `bash appearance/kromacut/run_convert.sh` | `build/art/<art>/` | `build/print/<art>/` | 25/25 自检、bbox/厚度/逐耗材对象、STL 字节确定性 |
| 3 | 外壳开槽 | `bash appearance/cad/run_shell.sh` | `mechanical/*/build/parts/plate_v01.step` | `build/shell/` | 94/94 校验、槽底平面度 0、单实体、包围盒不变 |
| 4 | 数字样机 | `bash appearance/render/run_all.sh` | 上面两者 | `appearance/render/` | 11 张 PNG + .blend、shell/print 分离、3MF 回读 ok |
| 5 | **打印交付** | `bash render/print/appearance/run_print_stage.sh` | 外壳/开槽顶板/印花 STL | `render/print/stl/`（18 STL）+ `render/print/appearance/`（3MF/参考图/manifest） | 床面 ≤220、间距 ≥5、印花正面贴床第一层、无需支撑、刚体变换校验、CHECKSUMS |
| 6 | 独立验收 | `python3 appearance/tools/acceptance_check.py` | 全部产物 | `build/ACCEPTANCE.{json,md}` | **130/130 PASS** |

---

## 2.5 一键编译 + 输入清单（2026-11-07 新增）

上面 6 个阶段现在有**唯一配置 + 一条命令**；阶段脚本本身不变，compile.py 只做编排、校验和报告。

```bash
cd /data/Documents/projects/SmartCoaster
bash appearance/compile.sh --dry-run   # 只校验输入/配置/工具/阶段常量，零写入
bash appearance/compile.sh             # art -> convert -> shell -> render -> print -> acceptance
```

- **唯一配置**：[`appearance/config/appearance_project.yaml`](config/appearance_project.yaml)（schema 注释在文件头；
  图像/crop/色板/tuning/像素/层高/顶板 STEP/rim/槽径/印花径/过盈/顶差/CMF/床/按键/阶段与工具路径）。
- **输入契约**：[`appearance/INPUTS.md`](INPUTS.md)（每个输入放哪、格式、示例、校验规则；
  “什么能只改配置、什么必须改硬编码阶段常量/Lead 验收基线”；5 步新印花 / 5 步新外壳 quick-start）。
- **给 AI agent 的复制粘贴提示词**：[`appearance/AGENT_PROMPT.md`](AGENT_PROMPT.md)。
- **产物**：`appearance/build/COMPILE_REPORT.{json,md}`（逐阶段状态/耗时/校验明细）、
  `appearance/build/compile.log`、`appearance/build/compile/resolved_config.json`。
- **失败行为**：dry-run 或编译前就把「配置 vs 硬编码阶段常量（render/config.json、scene_common.py
  VERSIONS、run_convert.sh art 循环、print_layout 常量、Lead 验收基线）」不一致拦下，打印
  “改哪个文件哪个常量”，不会静默造出与 130/130 验收不一致的模型。

> 诚实边界：**换图/换 crop/换色值/改 tuning/改路径 = config-only；改色数、layer_height、rim/floor、
> 槽径/过盈/顶差/床、CMF style、版本名/印花名 = 非 config-only**（还要改硬编码阶段常量与 Lead 验收基线）。
> 详见 INPUTS.md §4 与 §9。

---

## 3. 工具与安装（技术栈）

### 3.1 版本与位置

| 组件 | 版本 | 位置 | 用途 |
|---|---|---|---|
| Kromacut（桌面） | **4.2.0** | `/data/Documents/tools/Kromacut/app`（AppImage 解包，免 FUSE） | GUI 调色/试排；`~/.local/bin/kromacut` |
| Kromacut 源码 | **v4.2.0 tag** | `/data/Documents/tools/Kromacut/src/Kromacut-4.2.0` | headless 引擎（只读 import） |
| headless 桥接 CLI | 1.0.0（本项目） | `/data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs` | 层网格 → 3MF/STL |
| Node.js | 24.15.0 | `/usr/bin/node` | 跑桥接 |
| three / jszip / vite | 0.180.0 / 3.10.1 / 7.1.2 | `/data/Documents/tools/Kromacut/node_modules` | 桥接运行时（Vite SSR 加载 TS） |
| build123d | 0.10.0 | `mechanical/square_v1/.venv` | 外壳开槽 |
| Blender | 4.5.3 LTS | `/data/Documents/tools/blender/blender` | 装配/渲染 |
| Python（素材） | 3.10 + numpy 2.2.6 + Pillow 12.3.0 | 系统 python3 | 拆图/量化 |

安装脚本：`appearance/tools/install_kromacut.sh`（下载官方 AppImage + v4.2.0 源码 → 解包 →
启动器/桌面项 → `npm install` 三个桥接依赖 → sanity）。校验摘要：AppImage sha256
`c1cb1bfa…495ca`、源码 sha256 `74ae596f…126a`；GUI 在 Xvfb `:99` 下截屏
`/data/Documents/tools/Kromacut/logs/gui_offscreen.png`。

### 3.2 桥接实现原理（为什么要 Vite SSR）

- Kromacut 的 `export3mf.ts` 使用**无扩展名 import**（`./slicerDefaults`），原生 Node ESM 不能解析；
- 上游自己的测试用 `tests/helpers/viteModule.ts`：`createServer({configFile:false, appType:'custom',
  server:{middlewareMode:true, hmr:false}, optimizeDeps:{noDiscovery:true}})` + `ssrLoadModule()`；
- 桥接完全复用这条路（root = 源码目录），因此**加载的是 Kromacut 的真实代码**，
  且模块 sha256 记录进 manifest 以便追溯；
- 调用面（不二次实现几何）：`flatPaint.orientFlatPaintLayerCounts` / `buildFlatPaintLayout`、
  `flatPaintMeshing.createFlatPaintMesher`、`export3mf.exportObjectTo3MFBlob`、
  `exportStl.exportObjectToStlBlob`。

### 3.3 桥接 CLI 用法

```bash
node /data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs \
  --art appearance/build/art/dog --out appearance/build/print/dog \
  --smooth none --name dog --require-full-palette
# 项目封装（两版一起）：
bash appearance/kromacut/run_convert.sh            # ~44 s
DETERMINISM=1 bash appearance/kromacut/run_convert.sh   # 另加两次转换比对 STL 字节，~90 s
SMOOTH=medium bash appearance/kromacut/run_convert.sh   # 可选平滑（未作为交付默认）
```

退出码非 0 = 自检失败。转换时间实测 dog 18.5 s / elf 23.4 s（smooth=none）。

---

## 4. 素材规格与量化方法（`make_art.py`）

### 4.1 输入测量（必须重测，不要硬编码猜）

- 源图 `appearance/src/surface.png`：1774×887，两张圆形印花左右拼版，白底；
- 两枚图形**不是正圆**，是略扁椭圆：左 rx≈415.5 / ry≈406.0、右 rx≈415.5 / ry≈406.5；
- 因此按各自椭圆包围盒重采样到正方形，才能恢复真圆（否则印花会成椭圆/尺寸差 1–2%）。

### 4.2 处理步骤（固定顺序，可复现）

1. 以每枚印花中心/椭圆半径取包围盒；
2. `PIL.Image.resize(576×576, LANCZOS, box=bbox)` → 椭圆→正圆 + 降采样；
3. **圆外颜色向圆内"外扩" 6 px**（迭代邻域平均）后再量化，避免 LANCZOS 把白边带进印花边缘；
4. 计算圆内 mask（半径 287.9 px，对应 86.37 mm）；
5. CIELAB 最近邻量化到**固定耗材色板**（不是 k-means 平均色，保证可复现）；可带 contrast/saturation 微调；
6. 3 轮 3×3 多数去噪 + 孤立像素清除（保证没有 0.15 mm 单点，孤立像素最终 = 0）；
7. 输出 alpha 二值化（圆外全透明）与 `layer_counts.bin`。

### 4.3 尺度公式（必须与切片参数一致）

| 参数 | 值 | 公式/约束 |
|---|---|---|
| 画幅 | 576 × 576 px | |
| 像素尺寸 | **0.15 mm/px** | `< 喷嘴 0.4 mm`，几何比打印细，渲染更锐利 |
| 画幅边长 | 86.4 mm | 576 × 0.15 |
| 印花直径 | 86.37 mm | (576 − 0.2) × 0.15 |
| 层高 | **0.20 mm** | 与切片 0.20 mm 层高一致 |
| 层数 | dog **6** / elf **7** | = 色板数量 |
| 印花厚度 | **1.20 / 1.40 mm** | 层数 × 层高 |
| 槽深 | **1.25 / 1.45 mm** | 厚度 + 0.05 |

> **耦合关系（重要）**：色数 → 层数 → 印花厚度 → 槽深，四者必须一起改。
> 增加一种耗材 = 印花厚 0.2 mm、槽深 0.2 mm、顶板剩余肉厚 −0.2 mm。

### 4.4 色板（bottom-up，index 0 = foundation）

| 版本 | 色板（顺序 = Kromacut `layerFilamentHexes`） |
|---|---|
| 狗（6） | `#FBF4E8` cream · `#CBE0F5` sky · `#9FB2DA` periwinkle · `#F9CD72` yellow · `#F09FAF` pink · `#6C574C` brown |
| 精灵（7） | `#EDE1F0` pale-lavender · `#D9CFE6` hair-shadow · `#C3AEDC` purple · `#F7D2C0` skin · `#E8A9B8` blush · `#C9A45B` gold · `#5B4A72` deep-purple |

- 精灵原画反差很低（58% 是浅薰衣草/白），7 色明显比 6 色保真；量化前对精灵做
  CIELAB 对比度 1.05 / 饱和度 1.10 微调，狗 1.08 / 1.15。
- 色值即"理想耗材颜色"；实物可换等价 Bambu PLA，但会改变观感，需要重新出渲染对照。

### 4.5 数据契约（下游只读，不猜参数）

`build/art/<art>/art.json`

```json
{
  "width": 576, "height": 576,
  "pixel_size_mm": 0.15, "layer_height_mm": 0.2, "first_layer_mm": 0.2,
  "orientation": "face-up", "layer_count": 6,
  "print_thickness_mm": 1.2, "art_diameter_mm": 86.37, "frame_mm": 86.4,
  "palette_bottom_up": ["#FBF4E8", "..."],
  "source": {"file": "appearance/src/surface.png", "bbox_xyxy": [...], "sha256": "..."}
}
```

`layer_counts.bin`：**uint16 LE、行优先（y = 图像顶行起）**，`0 = 透明`，
`1..N = 该像素的物理层数`（= palette index + 1）。文件大小 = 576×576×2 = 663,552 B。

---

## 5. Kromacut Flat Paint 几何原理与参数要求

### 5.1 face-up Flat Paint 的语义（本项目采用）

- 每个像素列是**从下到上的材料叠层**，顶层可见；
- 像素层数 k = 该像素的 `layer_counts` 值；可见顶色 = `palette[k-1]`；
- 矮列由 **foundation（palette[0]）** 从下方垫到统一高度 → **整个平板顶面平整**、多色同层并排；
- 没有透明承载层（省一种耗材，也不需要翻面看）；对比 face-down 模式的区别见 Kromacut 文档。

### 5.2 逐耗材对象（3MF 的核心）

- 同一物理耗材的所有 part 合并成**一个导出对象**（`flatPaint:filament:<HEX>`）；
- 3MF 里再包一层**装配对象**（每个耗材一个 component）→ 切片器看到"一个印花件、N 个材料 part"；
- 每层可能同时有多个耗材（AMS/CFS/换头必需；单喷头一次换料做不到同层多色）。

### 5.3 尺寸/精度要求（打印可行性）

| 约束 | 值/规则 |
|---|---|
| 像素尺寸 | 0.15 mm（几何）；小于喷嘴线宽，**靠几何保证形状，实际细节受 0.4 mm 线宽限制** |
| 最小可打印线条 | 约 **0.45–0.6 mm**（3–4 px）；渲染比实物锐利 |
| 层高 | 必须与切片层高一致（本例 0.20 mm）；不一致会让可见色层厚度/位置错位 |
| 图案尺寸 | Ø86.4（本例）；更小的图案按同一公式缩放，但最小特征别低于 0.45 mm |
| 平滑（Smooth Meshing） | `none` 为交付默认（最忠实像素边界）；`medium` 实测三角面 +0.007%、3MF +10%、耗时 +2–5% |
| 减色/Dedither | 生成端已做 Lab 量化 + 去噪；实测再叠加 3×3 多数去噪仅 −0.6% 三角面 |

### 5.4 三角面与"界面面"（**不得去重**）

- Flat Paint 的每个 part 是**闭合实体**，相邻 part 相接的端盖是**一对反向绕序的重合面**；
- 本项目的重合面只出现在 foundation（因为只有它会以相同像素 mask 在多个高度相邻出现）：
  狗 **261,777 对**、精灵 **325,697 对**；全部水平、反向绕序、重数恰为 2；
- 这是"每个材料件都是闭合实体"的正常表示，**切片器忽略内部界面**；
- 去重会删掉一侧端盖 → 该材料件不再闭合，**不能做**。3MF 装配件按 STL 原样保留三角面，
  逐 component 三角数 == STL == manifest。

### 5.5 性能与规模（本机实测）

| 版本 | 耗材数 | 三角面（印花） | 3MF 大小 | 转换耗时 |
|---|---|---|---|---|
| 狗 | 6 | 1,941,732 | 19.7 MB | 18.5 s |
| 精灵 | 7 | 2,500,540 | 25.6 MB | 23.4 s |

> 三角面偏大（尤其 foundation 1.24M/1.57M）来自 0.15 mm 像素 + 水彩区域碎片化。
> 已测的降规模旋钮：**像素尺寸**最有效（0.30 mm 网格 → 574,208 面，−70%，6.1 s）；
> 去噪 −0.6%；平滑不降面。对切片器偏慢时可重出较低分辨率素材，但要同步改外壳槽径/印花直径。

---

## 6. 外壳适配规范（`appearance/cad/`）

### 6.1 开槽定义（唯一参数源 = `build/shell/shell.json`）

| 项 | 圆形版 | 方形版 |
|---|---|---|
|---|---|
| 源顶板（只读导入） | `mechanical/lumen/build/parts/plate_v01.step` | `mechanical/square_v1/build/parts/plate_v01.step` |
| 沿口 rim z | 17.00 | 18.00 |
| 槽直径 | Ø86.0（r43.000） | Ø86.0 |
| 槽底 floor z | **15.75** | **16.55** |
| 槽深 | 1.25 | 1.45 |
| 印花厚度 | 1.20 | 1.40 |
| 印花顶 z | 16.95（rim −0.05） | 17.95（rim −0.05） |
| 剩余肉厚（槽底以下） | 1.75 | 1.55 |
| 槽底平面度 | 0.000000 mm | 0.000000 mm |

原则：**不要重建顶板**，用 `import_step` + 圆柱布尔差保持已验证几何；只切顶面，不碰裙边/传力柱/内部件。

### 6.2 放置变换（3MF / Blender 共用）

- 印花 STL 本地坐标：XY 居中 `[-43.2, 43.2]`、底面 `z=0`、顶面 `z=t`；
- 装配：`translate (0, 0, floor)`，**无旋转**；
- 朝向：图像顶部 = **+Y**（前脸 −Y，用户从正面看印花是正的）；XYZ 轴 = 机构坐标（Z 上）。

### 6.3 必须通过的校验（94/94，`appearance/cad/verify_shell.py`）

- 导入/切后：单实体、`is_valid`、包围盒**完全不变**；
- 体积差 = 槽底以上实际材料（用 `pi·r²·h` 只能作参考：圆形源板内部空腔/刻线本来就是空气，
  实测差 −19.5%，方形 +0.0000%）；
- 槽底平面 `normal=(0,0,1)`、面积 = `pi·43²`、平面度 0；
- 槽壁直径 86.0000；沿口/中心深度一致（圆形顶面是平 z=17.0）；
- 与刻线/顶面圆角/外缘间隙 >1 mm；内部件最高点 z（圆 13.4 / 方 14.5）与槽底的余量（2.35/2.05）；
- STEP 回读 1 solid；STL 水密（0 boundary / 0 non-manifold edge）；Blender 导入 1 对象。

### 6.4 源模型缺陷（已记录，未改源）

`mechanical/lumen/build/parts/plate_v01.step` 是 **2-shell 实体**：内含封闭锥形空腔
（apex z=16.100 / ceiling z=16.700 / R48 / 1,447.6459 mm³），**顶面实际是 z=17.0 平面**
（任务简报里"0.9 mm 浅碟"在 STEP 里不存在；导出的 STL 反而有碟形，STEP/STL 不一致）。

- 按原样切槽会在槽壁 `z 16.6375..16.7000`（高 0.0625 mm）开一圈**亚喷嘴环缝**；
- 处置：主交付保留**忠实切法**（`plate_recessed.*`），另出**填实空腔**的
  `plate_recessed_clean.*`（外形/包围盒/顶面轮廓不变，墙带 15.75..17.0 干净）；
- 建议在上游 `<mechanical/lumen>` 修复建模（本项目对 `mechanical/**` 只读）。

### 6.5 功能影响与缺口（`PROVISIONAL`）

- 开槽把顶板局部厚度从 3.0 减到 1.75/1.55 mm；
- **没有重跑** `mechanical/*/cad/verify_v01.py`（21 项）与 FEA（顶板 B/整机 C 对象）；
- 顶板是称重浮动板：刚度、传力路径、过载限位、跌落行为均**未验证**；
- 打样前必须补：① 开槽顶板 FEA（中心/偏载 r=30/45）；② 21 项功能自检；
  ③ 实物称重精度/温漂/回差标定。

---

## 7. 装配与 Bambu 融合（`appearance/render/` + `appearance/build/3mf/`）

### 7.1 Blender 场景结构（保持分离）

```text
round/scene.blend
├── SHELL_ROUND       battery … plate（11 件，含开槽顶板）
└── PRINT_ART_DOG     ART_DOG_00..05（每耗材一个对象）
square/scene.blend
├── SHELL_SQUARE      12 件（含 button / screen_ui）
└── PRINT_ART_ELF     ART_ELF_00..06
```

- **没有 join、没有 boolean、没有父子关系**；`scene_section.blend` 只是渲染用的 1/4 剖切副本；
- 印花材质：Principled BSDF，颜色 = manifest hex 的 sRGB→linear；roughness≈0.5、metallic=0；
- 外壳/顶板 CMF 用 `render/appearance/styles.json` 的 `lumen_violet`（壳 #2A2E35 / 顶板 #6B40A0），
  与既有外观轮次一致，便于横向比较。

### 7.2 装配 3MF 结构（`make_3mf.py`，3MF core spec）

```text
<resources>
  <basematerials id="1">           每零件/每耗材一个 <base displaycolor>
  <object> shell / pcb / …         外壳零件（各自网格）
  <object> plate_recessed          开槽顶板
  <object> filament_1_<HEX> …      印花逐耗材对象（不作为 build item 单独摆放）
  <object id=K name="PRINT_ART_dog">
      <components>                 印花作为一个装配对象
          <component objectid=filament_1_<HEX>>
          …
<build>
  <item objectid=shell/> …         外壳零件在原生装配位姿
  <item objectid=PRINT_ART_dog transform="… z=15.75">   印花落槽底
```

- 单位 **millimeter**；`PRINT_ART_*` 的 build transform 平移 `z = floor`；
- 不写 Bambu 专有的 `Metadata/model_settings.config`（格式私有），**AMS 槽位由用户在 Bambu 里分配**；
  Kromacut 原始 print-only 3MF 自带 Bambu 元数据，可作为参考/备选路径；
- 回读校验（`validation.json`，两版 `ok:true`）：包结构、单位、装配/component 数、
  逐 component 三角数 == STL == manifest、材料色 == manifest、世界 Z 在 `[floor, floor+t]`、
  整体包围盒（110×110×17 / 100×100×18）。

### 7.3 Bambu Studio 操作步骤（用户侧，未在本机验证）

1. 导入 `appearance/build/3mf/{round|square}.3mf`；
2. 确认外壳零件与 `PRINT_ART_*` 的相对位置（应已装配好，勿再移动/缩放/镜像）；
3. 给 `PRINT_ART_*` 的每个 material part 分配 AMS 槽位（6/7 色；Kromacut 原始 3MF 已带 extruder 映射）；
4. 外壳分配结构材料（PC/ABS 或 PLA 打样）；
5. **逐层预览**：检查印花与槽壁交界、顶面是否齐平、内部界面是否被正确解析；
6. 切片；打印后检查颜色/层厚/结合/表面。

> 注意：不要导入后整体缩放（会破坏 0.2 mm 过盈与 0.05 mm 顶差）；不要对印花再做镜像（face-up 已按正向导出）。

### 7.4 渲染清单（11 张交付图）

| 文件 | 内容 |
|---|---|
| `appearance/render/{round,square}/hero.png` | 3/4 俯视主图（1000²，48 spp） |
| `.../top.png` | 正交俯视（1000²） |
| `.../print_top.png` | 印花单独俯视（1000²） |
| `.../macro_edge.png` | 印花边缘/槽壁微距（1600²，64 spp；可见 0.15 mm 像素台阶） |
| `.../section_exploded.png` | 1/4 剖面 + 爆炸 + 配合数值（2400×1200） |
| `appearance/render/board.png` | 两版对比板（2276×2406） |

Blender 4.5.3 / Cycles CPU / AgX / denoise；两版总计 ~3 min 19 s（详见 `appearance/render/RENDER_LOG.md`）。

### 7.5 打印交付（`render/print/stl/` + `render/print/appearance/`，管线最后一步）

> **完整规范见 [`PRINT_DELIVERY_SPEC.md`](PRINT_DELIVERY_SPEC.md)**（方向/断言/文件清单/门槛/导入顺序/失败模式）。
> 关键物理事实：**印花正面（图案面）必须贴床、作为第一层打印**，所以顶板与印花整体翻转（凹槽朝下）同盘打印；
> 切片/打印时看到的是印花**背面**（正确），打印后**整体翻面**才露出图案。该姿态**不需要支撑**。

```bash
bash render/print/appearance/run_print_stage.sh     # ≈2.5 min，幂等；已是 appearance/render/run_all.sh 的第 4/4 步
```

**唯一交付 STL 目录（平坦）：`render/print/stl/`**

| 版本 | STL | 体积 | 印花耗材 |
|---|---|---|---|
| 圆形（LUMEN+狗） | 8：`round_shell.stl`、`round_plate_recessed.stl`、`round_print_filament_1..6_<HEX>.stl` | 98.66 MB | 6 |
| 方形（square_v1+精灵） | 10：+ `square_button.stl`、`square_print_filament_1..7_<HEX>.stl` | 126.78 MB | 7 |
| 合计 | **18 个** | **225.44 MB** | — |

附 `CHECKSUMS.sha256`（`sha256sum -c` 通过）、`delivery.json`（方向变换矩阵/断言/源 sha/体积）、`README.md`（文件↔材料↔用途）。
每版另有 `render/print/appearance/<v>/`：`PRINT_SHEET.png`（1800×1200）、`print_iso/top.png`、`layout.json`、
`manifest.json`、`README.md`、`PRINT_READY.3mf`（**床面排版可切片 3MF**）；合并板 `render/print/appearance/PRINT_SHEET_APPEARANCE.png`（2400×1250）。

**打印姿态（脚本硬断言）**

| | 圆形 | 方形 |
|---|---|---|
| 顶板原始顶面 z | ≈0（贴床） | ≈0 |
| 槽底 z（=印花背面） | 1.25 mm | 1.45 mm |
| 印花正面 z（第一层） | 0.05 mm | 0.05 mm |
| 印花厚度 | 1.20 mm | 1.40 mm |
| 按钮 | — | 躺平 9.0×8.997×5.2 mm（厚度轴 Z，可见面朝下） |
| 支撑 | **无** | **无** |
| 床面占用（220 床） | 218.935×109.995×13.4，最小间距 5.0 | 208.0×113.997×14.5，间距 8/5/5 |

**两种打印路线**

| | A · 推荐（原位粘合，无需支撑） | B · 备选（分开打印后装） |
|---|---|---|
| 做法 | 顶板+印花整体翻转（凹槽朝下）同盘打印，第一层=印花正面/顶板外表面贴床；外壳单独打印 | 顶板倒扣打、印花单独平打，之后压入/胶接 |
| 粘合 | 打印过程中粘结为一体 | 后装压配/胶接（不是打印时粘合） |
| 文件 | `PRINT_READY.3mf` | `render/print/stl/` 分件 |

**打印参数建议**：0.20 mm 层高、0.40 喷嘴、≈0.45 线宽、2 墙、15% 填充、无支撑、方形按键 5 mm brim；
AMS：狗需 6 槽位、精灵 7 槽位，4 槽需换料或第二台 AMS。

> **STL 不带材料信息**：印花必须把 6/7 个 `print_filament_*` STL **同时导入**并逐对象分配 AMS；
> 单色合并预览未提供（各耗材件是闭合实体、界面面刻意保留，布尔合并不可靠）。推荐直接用 `PRINT_READY.3mf`。
>
> `PROVISIONAL`：0.05 mm 首层贴合、床面附着、0.2 mm 过盈的实际配合、翻面后平整度均**未实际切片/打印验证**。

---

## 8. 参数总表（唯一来源标注）

| 参数 | 圆形版 | 方形版 | 来源 |
|---|---|---|---|
| 外壳 | LUMEN Ø110×17 | square_v1 100×100×18 | 机械基线（只读） |
| 印花 | dog | elf | `art.json` |
| 色数 / 层数 | 6 | 7 | `art.json` |
| 像素 / 层高 | 0.15 / 0.20 mm | 同 | `art.json` |
| 印花直径 / 厚度 | 86.37 / 1.20 mm | 86.37 / 1.40 mm | `art.json` |
| 槽径 / 槽深 / 槽底 | 86.0 / 1.25 / 15.75 | 86.0 / 1.45 / 16.55 | `shell.json` |
| 沿口 / 印花顶 | 17.00 / 16.95 | 18.00 / 17.95 | `shell.json` |
| 名义/最大过盈 | 0.20 / 0.288 mm | 同 | `shell.json` + 实测 |
| 印花三角面 / 3MF | 1,941,732 / 19.7 MB | 2,500,540 / 25.6 MB | `manifest.json` |
| 装配 3MF | 18 对象 / 12 build item / 15.95 MB | 20 / 13 / 20.82 MB | `validation.json` |
| 打印交付 STL | 8 个 / 98.66 MB（外壳/顶板/印花 6） | 10 个 / 126.78 MB（+按键/印花 7） | `render/print/stl/delivery.json` |
| 床面占用（220 床） | 218.94×110.00×13.4，最小间距 5.0 | 208.0×114.00×14.5，最小间距 5.0 | `render/print/appearance/<v>/layout.json` |

**`PROVISIONAL` 标记**：过盈 0.2 mm、顶差 0.05 mm、槽深、开槽顶板刚度、25 项印花自检之外的
切片行为，均为首版假设/未验证项，不得当作已验证规格引用。

---

## 9. 验收门槛与证据

| 阶段 | 门槛 | 实际 |
|---|---|---|
| 工具 | GUI 可启动 + headless 三模块可加载 + 版本入 requirements | 通过（Xvfb 截屏 + manifest 记录模块 sha256） |
| 素材 | 尺寸/色板/层数自洽、透明正确、孤立像素 0 | 10/10 检查通过 |
| 印花 | 25/25 自检、逐耗材对象、bbox/厚度、STL 确定性、界面面校验 | 25/25 ×2；两次运行 13 个 STL 逐字节一致 |
| 外壳 | 94/94、单实体、槽底平面度 0、包围盒不变、内部件余量 | 94/94 |
| 3MF | 结构/单位/component/材料色/Z 范围/包围盒 | 两版 `ok:true`、errors [] |
| 打印交付 | 床面 ≤220、间距 ≥5、印花正面贴床第一层、无需支撑、刚体变换（三角数/体积/bbox=源）、CHECKSUMS | 18 STL / 225.44 MB；床面 218.9×110.0 / 208.0×114.0 mm；130/130 验收 |
| 渲染 | 11 图存在且非空、blend 分离、RENDER_LOG | 11/11 + sha256 稳定 |
| 总验收 | Lead 只读独立复核 | **130/130 PASS**（`build/ACCEPTANCE.{json,md}`） |

**证据入口**：`build/art/REPORT.md`、`build/print/REPORT.md`、`build/shell/REPORT.md`、
`build/3mf/README.md` + `validation.json`、`render/RENDER_LOG.md`、`build/ACCEPTANCE.md`。

---

## 10. 复现（一条命令级）

**推荐：一键编译**（读唯一配置、自动校验、逐阶段报告、最后跑 130 项验收）：

```bash
cd /data/Documents/projects/SmartCoaster
bash appearance/compile.sh --dry-run   # 先校验（零写入）
bash appearance/compile.sh             # 全流程 + 验收
```

下面是等价的**分阶段手跑**（排错/单阶段重跑时用；compile.sh 只是把它们串起来并加校验）：

```bash
cd /data/Documents/projects/SmartCoaster
bash appearance/tools/install_kromacut.sh          # 仅首次/换机
python3 appearance/tools/make_art.py               # ≈2 s
bash appearance/kromacut/run_convert.sh            # ≈44 s
bash appearance/cad/run_shell.sh                   # ≈25 s（含 Blender 导入检查）
bash appearance/render/run_all.sh                  # ≈3.5 min 渲染 + 1.3 min 3MF（含第 4/4 步打印交付）
bash render/print/appearance/run_print_stage.sh    # 仅打印交付 STL/排版/参考图（≈82 s；幂等）
python3 appearance/tools/acceptance_check.py       # 只读复核（130 项）
```

环境要求：Node ≥ 22（实测 24.15.0）、Blender 4.5.3、build123d 0.10.0（项目 venv）、
`/data/Documents/tools/Kromacut` 安装完整。Kromacut 源码/依赖不要放进项目仓库。

---

## 11. 失败模式与排错（本轮踩过的坑）

| 现象 | 根因 | 处置 |
|---|---|---|
| `app/usr/bin/kromacut` 直接跑崩（gtk::rt::init） | 没走 AppImage 的 `AppRun` 库路径 | 用 `kromacut` 启动器 / `app/AppRun` |
| headless 加载 `export3mf.ts` 失败 | 上游有无扩展名 import | Vite SSR（`configFile:false` + `optimizeDeps.noDiscovery`） |
| `createServer` 扫描整个应用报错 | 缺 `noDiscovery` / `appType:'custom'` | 按上游 `tests/helpers/viteModule.ts` 配置 |
| 渲染微距图全黑 | 相机 `clip_start=0.1 m`，微距距离 40–70 mm | `clip_start=1 mm` + 长焦 |
| 3MF 三角面比 STL 少 26 万 | 误把"反向绕序界面面"当重复面删掉 | **禁止去重**；校验 component 三角数 == STL |
| 圆形槽深与 `pi r² h` 对不上（−19.5%） | 源板内部空腔/刻线本来就是空气 | 用"槽底以上实际材料"对账，不用理论圆柱体积 |
| 圆形顶板 STEP/STL 不一致 | STEP 建模缺陷（空腔，顶面平） | 记录 + clean 变体；未改源 |
| 印花变椭圆/尺寸偏 | 源图两枚图形是略扁椭圆 | 按椭圆包围盒重采样回正圆 |
| 颜色发灰/发糊 | 低反差原画 + 色数不足 | 提高色数（6→7）或 Lab 对比度/饱和度微调 |
| Bambu 里位置/尺寸不对 | 导入后缩放/镜像 | 导入后不缩放、不镜像；用 3MF 自带装配变换 |
| 切片里看不到印花图案/以为放反了 | 印花正面贴床、翻面后才可见（正常） | 顶板+印花整体翻转（凹槽朝下）同盘打印，无需支撑；打完整体翻面 |
| STL 打开只有单色/缺件 | STL 不携带材料信息 | 印花 6/7 个逐耗材 STL 同时导入，逐对象分配 AMS；推荐 `PRINT_READY.3mf` |
| 按钮站着打印 | 只绕 Z 旋转 | 绕 X +90°，厚度轴竖直（bbox z=5.2），可见正面朝下 |

---

## 12. 已知限制与下一步

**未验证（不得写成已通过）**

- Bambu Studio 实际导入、AMS 耗材映射、逐层切片与打印路径；
- 实物颜色、层厚、过盈结合强度、耐热、清洁性；
- 开槽顶板的刚度/FEA、21 项功能自检（称重功能）；
- 打印姿态（印花正面贴床第一层、按钮可见面朝下）与 0.2 mm 过盈的实物配合、首层 0.05 mm 贴合、
  翻面后平整度（`render/print/` 只是交付与排版，不是切片验证）。
- Kromacut `face-down`、`smooth=minimal/aggressive` 路径未在本项目实测。

**风险**

- 6/7 色需要 ≥6 槽位多材料；4 槽 AMS 需换料或第二台 AMS；
- 印花尺寸若从 86.4 改大/改小，槽径、底板图形、包装都要同步；
- 三角面规模对切片器偏重（尤其 foundation），可选降像素尺寸重出（需同步改槽径）。

**下一步**

1. Bambu Studio 实机导入 + 切片检查（逐层材料边界、内部界面解析）；
2. 打样：先单色测试件验证过盈/顶差，再打印两版；
3. 补开槽顶板 FEA + 21 项功能自检；
4. 4 槽 AMS 版本：压到 4 色并同步改槽深（可作为下一轮 SKU 变体）；
5. 上游修复 LUMEN 顶板 STEP 空腔缺陷。

---

## 13. 目录与交付索引

```text
appearance/
├── src/surface.png                 原始素材（只读）
├── tools/
│   ├── make_art.py                 素材 → 印花层网格（唯一来源）
│   ├── install_kromacut.sh         Kromacut 安装（/data/Documents/tools/Kromacut）
│   ├── check_print_top.py          印花俯视快速检查（Blender workbench）
│   └── acceptance_check.py         Lead 只读验收（130 项）
├── kromacut/                       headless 桥接项目入口（run_convert.sh、README）
├── cad/                            外壳开槽（build123d，源 STEP 只读导入）
├── render/                         Blender 场景/渲染/3MF/board/RENDER_LOG
└── build/
    ├── art/<art>/                  art.json + layer_counts.bin + PNG + REPORT
    ├── print/<art>/                Kromacut 3MF + 每耗材 STL + manifest + REPORT
    ├── shell/                      plate_recessed.* + shell.json + parts.json + REPORT
    ├── 3mf/                        Bambu 装配 3MF + validation + README
    ├── render/                     原始剖面/微距渲染（中间证据）
    └── ACCEPTANCE.{json,md}        Lead 独立验收
render/print/stl/                   打印交付（管线最后一步）：18 个可打印 STL（打印姿态烘焙）+ CHECKSUMS + delivery.json
render/print/appearance/            打印交付：3MF/床面排版/参考图/manifest/README
appearance/PRINT_DELIVERY_SPEC.md   3D 打印交付独立规范（方向/断言/门槛/导入/失败模式）

```

外部门入口：`/data/Documents/tools/KROMACUT_INSTALL_NOTES.md`（安装/校验/限制）、
`/data/Documents/tools/Kromacut/tools/kromacut-flatpaint.mjs`（通用 CLI）。

> 大二进制（STL/STEP/3MF/blend）由脚本可再生成，默认不入 git（见根 `.gitignore`）；
> 交付时它们保留在工作区对应目录，按 §10 命令复跑即可重建。
