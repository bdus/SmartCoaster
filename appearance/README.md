# appearance/ — 图片印花 → 多材料一体打印（Kromacut 接入）

> 日期：2026-11-06
> 目标：把「IP 印花图片」变成**有厚度的多材料几何**，嵌入外壳浅槽，随外壳**一次多材料打印**成型。
> 关键判断（已核实）：**Kromacut 只负责图片→多材料几何，不负责与外壳布尔融合**；
> 外壳与印花在 Blender/3MF 里保持**两个独立对象**（嵌合关系），由 **Bambu Studio 在切片时**
> 合并材料路径、一次打印粘合。因此本目录的工作流是：

```text
appearance/src/surface.png          原始拼版（两枚圆形印花）
        │  appearance/tools/make_art.py        拆开 / 透明背景 / 定量到耗材色板
        ▼
appearance/build/art/<art>/         art_rgba.png + layer_counts.bin + art.json
        │  Kromacut v4.2.0 headless Flat Paint（face-up，无透明承载层）
        ▼
appearance/build/print/<art>/       多材料 3MF + 每耗材 STL + manifest.json
        │
        ├── appearance/cad/         外壳顶板开浅槽（适配印花厚度）→ 顶板 STL/STEP
        ▼
appearance/render/                  Blender 数字样机：印花与外壳分开、嵌入对位、渲染/.blend
        │
        ▼
appearance/build/3mf/               装配好的 3MF（外壳零件 + 印花每耗材对象），交 Bambu Studio
        │  Bambu Studio：多零件装配 / 耗材映射 / 逐层检查 / 切片
        ▼
一次多材料 FDM 打印：外壳表面平整、印花顶面与外壳齐平（或低 0.05 mm）
```

## 1. 两版设计（本轮）

| 版本 | 外壳 | 印花 | 印花层数 × 层高 | 印花厚度 | 槽深 / 槽底 z | 顶面 |
|---|---|---|---|---|---|---|
| **圆形** | LUMEN Ø110×17（旧概念外形，仅作外观语言） | 狗（蓝白） | 6 × 0.2 mm | **1.20 mm** | 1.25 / 15.75 | 16.95（比 17.0 沿口低 0.05） |
| **方形** | square_v1 100×100×18 | 精灵（紫白） | 7 × 0.2 mm | **1.40 mm** | 1.45 / 16.55 | 17.95（比 18.0 沿口低 0.05） |

共同参数：

- 印花直径 **Ø86.4 mm**（576 px × 0.15 mm/px），外壳浅槽 **Ø86.0 mm**；
- 径向 **0.2 mm 名义干涉**（实际最大 0.288 mm，含 0.15 mm 像素台阶的角点），过盈嵌入保证侧面结合，
  允许切片软件按材料优先级解析重叠；
- 印花在槽内**不悬空**：底面坐在槽底，顶面与外壳沿口差 0.05 mm（视觉平整）；
- 印花是 **face-up、无透明承载层** 的 Flat Paint 平板：每层多材料并排，foundation 垫平短列；
- 外壳/印花**不做布尔合并**（保持多对象），由切片软件完成融合；
- 装配 3MF 里印花是**一个装配对象 + 每耗材一个 component**（与 Kromacut 自己的导出结构一致），
  这样 Bambu Studio 里是"一个印花件、N 个材料 part"，仍可与外壳分开选择。

> `PROVISIONAL`：开槽深度/过盈量是按 0.4 mm 喷嘴、0.2 mm 层高的首版工程假设；
> 开槽会降低顶板刚度（顶板是称重浮动板），**未重跑 FEA/21 项功能自检**，打样前必须补。
> 印花层数增加会直接增加槽深（6 色 1.2 → 7 色 1.4 mm）。

## 2. 目录与数据契约

```text
appearance/
├── src/surface.png                 原始素材（只读）
├── tools/make_art.py               素材 → 印花层网格（唯一来源）
├── tools/install_kromacut.sh       Kromacut 安装脚本（/data/Documents/tools/Kromacut）
├── kromacut/                       headless 桥接的项目入口（run_convert.sh、README）
├── cad/                            外壳顶板开槽（build123d，复用已验证 STEP）
├── render/                         Blender 场景/渲染/board（build_scene.py、config.json）
└── build/
    ├── art/<art>/                  art.json + layer_counts.bin + PNG 证据
    ├── print/<art>/                Kromacut 3MF + 每耗材 STL + manifest.json
    ├── shell/{round,square}/       plate_recessed.stl/.step + shell.json
    ├── 3mf/                        Bambu Studio 用装配 3MF
    └── render/                     渲染产物（或 render/<version>/）
```

**数据契约**（下游只读这些，不猜参数）：

- `build/art/<art>/art.json`：`width/height`、`pixel_size_mm`、`layer_height_mm`、
  `layer_count`、`palette_bottom_up`（index 0 = foundation）、`print_thickness_mm`、
  `art_diameter_mm`；`layer_counts.bin` = uint16 LE、行优先（y=图像顶行起）、
  `0=透明`、`1..N=层数`（即 palette index+1）。
- `build/shell/shell.json`：每形状 `rim_z`、`pocket_diameter_mm`、`pocket_floor_z`、
  `print_thickness_mm`、放置变换（XY 中心 0,0、底面 = floor z）、干涉量、校验数值。
- `build/print/<art>/manifest.json`：调色板、每耗材 STL + hex、bbox、三角数、
  厚度、平滑强度、sha256。

## 3. 一键复跑

```bash
python3 appearance/tools/make_art.py          # 素材 → 印花层网格
bash appearance/kromacut/run_convert.sh       # Kromacut 引擎 → 多材料 3MF/STL
bash appearance/cad/run_shell.sh              # 外壳顶板开槽
blender -b --python appearance/render/build_scene.py   # 装配 + 渲染 + 装配 3MF
```

Kromacut 安装/验证：`/data/Documents/tools/KROMACUT_INSTALL_NOTES.md`；
headless 桥接用法：`appearance/kromacut/README.md`。

## 4. 为什么这样分工（设计决策）

1. **Kromacut 不做外壳融合**：它输出的是「按耗材分组的几何」，不是 CAD 曲面贴图；
   强行在 Blender 里布尔合并会**丢失耗材对象边界**，切片软件无法分配多材料。
2. **外壳开槽是必须的适配**：印花本身有厚度（1.2/1.4 mm），而外壳顶面必须平整；
   槽底 = 沿口 − (印花厚度 + 0.05)，印花底面落槽底、顶面与沿口齐平。
3. **过盈而非间隙**：两网格面恰好共面会产生缝隙/结合不牢；首版取 0.2 mm 径向过盈，
   让切片软件把交界处解析为材料邻接（具体值需按喷嘴/材料收缩标定，属 `PROVISIONAL`）。
4. **不在 Blender 里合并**：Blender 只负责数字样机与对位；材料分配与几何交叠裁定
   必须在切片软件里完成（`docs/01` §14.4）。

## 5. 验证与已知限制

> 独立只读验收：`python3 appearance/tools/acceptance_check.py` → **107/107 PASS**
> （工具/素材/开槽/印花/3MF/渲染/文档 7 组；证据 `appearance/build/ACCEPTANCE.{json,md}`）。

- 已验证（本机、可复跑）：素材拆分/透明、量化层网格（孤立像素 0/两张）、Kromacut 引擎产物
  （独立 Python 回读、逐文件 sha256、两次运行 STL 逐字节一致）、外壳槽几何（94/94）、
  装配 Z 变换（3MF build transform z=floor）、3MF 对象/材料/包围盒、渲染。
- **未验证**：Bambu Studio 实际导入/耗材映射/逐层切片、实物颜色/层厚/结合强度。
- 细节下限：3D 打印线条 ≥ 约 0.45–0.6 mm（3–4 px）才可靠；渲染比实物更锐利。
- **贴合界面不是重复面**：同一耗材内相邻 part 的相接端盖是一对**反向绕序的重合面**
  （狗 foundation 261,777 对 / 精灵 325,697 对），这是"每个材料件都是闭合实体"的正常表示；
  切片软件会忽略内部界面，**不能去重**（去掉一侧会让该材料件不再闭合）。
- 3MF 装配件保留 Kromacut 原始三角面（不去重）；逐 component 三角数 == 对应 STL == manifest 记录。
- 6/7 色需要 AMS/CFS 多材料；4 槽 AMS 需换料或第二台 AMS。
- 开槽降低了顶板刚度，**FEA/称重功能未重跑**（见 §1 PROVISIONAL）。

## 6. 交付索引（本轮）

> 具体命令/时间戳/校验值见各 REPORT / RENDER_LOG。

- 素材板：`appearance/build/art/art_board.png`（原始 vs 量化对照）
- 印花层报告：`appearance/build/art/REPORT.md`
- 外壳开槽报告：`appearance/build/shell/REPORT.md`（94/94 独立校验）
- Kromacut 产物报告：`appearance/build/print/REPORT.md`（22/22 自检）
- 印花预览：`appearance/build/print/{dog,elf}/preview_top.png`
- 数字样机渲染：`appearance/render/{round,square}/{hero,top,print_top,macro_edge,section_exploded}.png`，
  场景 `appearance/render/{round,square}/scene.blend`，对比板 `appearance/render/board.png`
- 渲染日志：`appearance/render/RENDER_LOG.md`
- Bambu 3MF：`appearance/build/3mf/{round,square}.3mf`（装配；含 PRINT_ART_* 装配对象 + 每耗材 component）
  + 参考 `appearance/build/3mf/{dog,elf}_kromacut.3mf`（Kromacut 原始 print-only 3MF，带 Bambu metadata）
  + 校验 `appearance/build/3mf/validation.json` + 说明 `appearance/build/3mf/README.md`
- 工具安装/验证：`/data/Documents/tools/KROMACUT_INSTALL_NOTES.md`
