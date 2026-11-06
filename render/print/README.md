# render/print — 3D 打印资料总览

> 本目录包含**两套互不影响**的打印资料。外观交付（本轮）在 `render/print/stl/<version>/`；
> 旧 baseline 方形 B 参考页保持原样未改动。

## 1. baseline 方形 B 打印参考（legacy，未改动）

| 文件 | 说明 |
|---|---|
| `PRINT_SHEET.png` | 方形 B（square_v1）外壳/顶板/按键平放打印参考（2026-11-04） |
| `renders/print_iso.png`, `renders/print_top.png` | baseline 打印排版渲染 |
| `print_layout.py`, `make_sheet.py` | baseline 脚本（Blender + Pillow） |
| `print_layout.blend` | baseline 场景 |

## 2. 外观交付（本轮：两种外观版本的“印花 + 外壳”）

交付根目录：**`render/print/stl/`**（按外壳版本分类，不是扁平目录）：

```
render/print/stl/
├── README.md              # 交付索引（两版本、导入顺序、校验）
├── delivery.json          # 全局：姿态/变换/床面排版/校验/文件 sha256
├── PRINT_SHEET_BOTH.png   # 两版本对比板 2400×1250
├── round/                 # LUMEN Ø110 + dog 印花（6 色）
│   ├── shell.stl, plate_recessed.stl, print_filament_1_FBF4E8.stl … (6)
│   ├── PRINT_READY.3mf    # 可切片床面排版 3MF
│   ├── PRINT_SHEET.png    # 1800×1200 参考页
│   ├── print_iso.png, print_top.png
│   ├── layout.json, manifest.json, README.md, CHECKSUMS.sha256
└── square/                # square_v1 100×100 + elf 印花（7 色）
    ├── shell.stl, plate_recessed.stl, button.stl, print_filament_1_EDE1F0.stl … (7)
    ├── PRINT_READY.3mf, PRINT_SHEET.png, print_iso.png, print_top.png
    └── layout.json, manifest.json, README.md, CHECKSUMS.sha256
```

### 打印姿态（物理事实）

- 顶板 + 印花**整体翻转**（凹槽朝下）同盘打印：第一层 = **印花正面 / 顶板外表面贴床**；
  印花正面在床面上方 **0.05 mm**（设计顶隙）。切片/打印时看到的是印花**背面**（正确），
  打印完成后**整体翻面** = 成品外观。
- 顶板槽底 z = **1.25 mm（round）/ 1.45 mm（square）**；印花背面坐在槽底。
- 方形按键**平躺**（圆盘平行床面，厚度 5.2 mm 竖直，bbox 9.0×9.0×5.2），可见正面朝下
  （翻面后为光滑顶面，PROVISIONAL）。
- **路线 A（推荐）无需支撑**；路线 B = 分开打印后压配/胶接（非打印时粘合）。

### Bambu Studio 导入顺序

1. 打开 `render/print/stl/<round|square>/`；
2. 导入 `print_filament_*.stl`（6 / 7 色，已烘焙翻转姿态）或直接导入 `PRINT_READY.3mf`
   （床面排版）；每个印花对象指定一个 AMS 槽位（6 色需 ≥6 槽位 / 7 色需 ≥7 槽位；
   4 槽需换料或第二台 AMS）；
3. 导入 `plate_recessed.stl`（凹槽朝下、顶面贴床）与印花同盘嵌套；
4. 导入 `shell.stl`（底面朝下单独打印）；方形加 `button.stl`（平躺，5 mm brim）；
5. 打印完成后整体翻面。

### 命令

```bash
bash render/print/appearance/run_print_stage.sh   # 重新生成交付（幂等，~2.5 min）
bash appearance/render/run_all.sh                 # 完整外观管线（本阶段为 4/4 最后一步）
```

### 校验

```bash
cd render/print/stl/round  && sha256sum -c CHECKSUMS.sha256
cd render/print/stl/square && sha256sum -c CHECKSUMS.sha256
```

### 两个 3MF

- `render/print/stl/<v>/PRINT_READY.3mf`：可切片的**床面排版**；
- `appearance/build/3mf/<v>.3mf`：装配完成姿态的数字样机（mockup，不直接切片）。

**PROVISIONAL**：未在真实切片器切片/打印；0.05 mm 首层融合、按键朝向、床面附着力需实物验证。
