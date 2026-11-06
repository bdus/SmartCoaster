# render/print — 3D 打印与打印交付

> 本目录有两套互不影响的打印资料：

1. **baseline 方形 B 打印参考（旧，未改动）**：`render/print/PRINT_SHEET.png`、`render/print/renders/`、`print_layout.py`、`make_sheet.py` — 方形 B 的外壳/顶板/按键平放参考，不是本轮外观交付。
2. **外观交付（本轮，task-6/9）**：`render/print/stl/<version>/` — 两种外观版本的真实可打印 STL + 床面排版 3MF + 参考页。

## 结构

```
render/print/
├── PRINT_SHEET.png          # baseline 方形 B 参考页（legacy，勿动）
├── renders/                 # baseline 渲染（legacy，勿动）
├── print_layout.py / make_sheet.py   # baseline 脚本（legacy，勿动）
└── stl/                     # 外观交付根目录
    ├── README.md            # 本文件
    ├── delivery.json        # 全局：姿态/变换/排版/校验/文件 sha256
    ├── PRINT_SHEET_BOTH.png # 两版本对比板 2400×1250
    ├── round/   16 files (8 STL + 3MF + sheet + iso/top + layout/manifest/README/CHECKSUMS)
    └── square/  18 files (10 STL + 3MF + sheet + iso/top + layout/manifest/README/CHECKSUMS)
```

## 打印姿态（重要）

- 顶板+印花**整体翻转**：凹槽朝下、顶板原顶面贴床；印花**正面 = 第一层**（床面上方 0.05 mm 设计顶隙）。切片/打印时看到的是印花**背面**（正确），打完整体翻面 = 成品外观。
- 顶板槽底在打印姿态 z = **1.25 mm（round）/ 1.45 mm（square）**；印花背面坐在槽底。
- 方形按键**平躺**：圆盘平行床面，厚度 5.2 mm 竖直（bbox 9.0×9.0×5.2），可见正面朝下（翻面后为光滑顶面，PROVISIONAL）。
- **路线 A（推荐）无需支撑**；打完整体翻面。路线 B = 分开打印后压配/胶接（非打印时粘合）。

## 两个版本

| 版本 | 外壳 | 印花 | STL 数 | 交付目录 | 床面占用 |
|---|---|---|---|---|---|
| round | LUMEN Ø110 | dog（6 色） | 8 STL | `render/print/stl/round/` | 218.9×110.0 mm |
| square | square_v1 100×100 | elf（7 色） | 10 STL | `render/print/stl/square/` | 208.0×114.0 mm |

## 导入顺序（Bambu Studio）

1. 进入对应版本目录 `render/print/stl/<round|square>/`；
2. 导入 `print_filament_*.stl`（6 / 7 个印花色，已烘焙为翻转姿态）或直接用 `PRINT_READY.3mf`（床面排版）——每个印花对象指定一个 AMS 槽位（6 色需 ≥6 槽位 / 7 色需 ≥7 槽位；4 槽需换料或第二台 AMS）；
3. 导入 `plate_recessed.stl`（凹槽朝下、原顶面贴床），与印花同盘嵌套；
4. 导入 `shell.stl`（底面朝下单独打印）；方形加 `button.stl`（平躺，5 mm brim）；
5. 打印完成后**整体翻面** → 成品外观。

## 命令

```bash
bash render/print/appearance/run_print_stage.sh   # 重新生成整个交付（幂等）
bash appearance/render/run_all.sh                 # 完整外观管线（本阶段为 4/4 最后一步）
```

## 3MF 说明

- `render/print/stl/<v>/PRINT_READY.3mf`：可切片的**床面排版**。
- `appearance/build/3mf/<v>.3mf`：装配完成姿态的数字样机（mockup，不直接切片）。

## 校验与 PROVISIONAL

- `cd render/print/stl/<v> && sha256sum -c CHECKSUMS.sha256`；每个 STL min z = 0，三角数/体积与源一致、bbox=刚性旋转源；3MF 回读校验通过。
- 未在真实切片器切片/打印；0.05 mm 首层融合、按键朝下、支撑策略都需实物验证 — **PROVISIONAL**。
