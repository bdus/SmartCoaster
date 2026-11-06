# 3D 打印交付 — 圆形 LUMEN / dog

> PROVISIONAL：打印方向/支撑建议未实物验证；尺寸来自外观管线 STL + `shell.json` + Kromacut manifest。**真实可打印 STL 已复制到 `stl/`，sha256 见 `CHECKSUMS.sha256`。**

## 打印路线（二选一）

### A) 推荐 · 多材料原位粘合（PRINT_READY.3mf）

顶板凹槽朝上 + 印花嵌在槽内，同盘打印（顶板裙边/传力柱需支撑，PROVISIONAL）；外壳单独打印。使用 PRINT_READY.3mf。

### B) 备选 · 无支撑（stl/ 分件）

顶板倒扣打印（表面好）+ 印花单独平打，之后压入/胶接（不是打印时粘合）。使用 stl/ 里的文件。

## 打印件 / STL 文件

| 零件 | STL（相对本目录） | 源文件 | 数量 | 材料/颜色 | 方向 | 支撑 |
|---|---|---|---|---|---|---|
| 外壳（底壳） | `stl/shell.stl` | `mechanical/lumen/build/parts/shell_v01.stl` | 1 | PLA/PETG · #2A2E35 | 底面朝下平放（按设计） | 无支撑 |
| 开槽顶板 | `stl/plate_recessed.stl` | `appearance/build/shell/round/plate_recessed.stl` | 1 | PLA/PETG · #6B40A0 | 凹槽朝上，与印花嵌套（原位粘合） | PROVISIONAL：需树状支撑（裙边/传力柱悬空） |
| Kromacut 印花（dog） | `stl/print/multimaterial/filament_*.stl` | `appearance/build/print/dog/filament_*.stl` | 1 | 6 色 · 见耗材表 | 面朝上（face-up），嵌套进顶板凹槽 | 无；与顶板同一嵌套打印任务 |

### STL 文件清单（交付副本）

| 文件 | 大小 | sha256（前 16 位） | 用途 | 材料 |
|---|---|---|---|---|
| `stl/shell.stl` | 1370684 B | `60e44f2cb8417d9a` | 外壳（底壳），底面朝下打印 | #2A2E35 |
| `stl/plate_recessed.stl` | 204184 B | `d2c4e1630f5a9137` | 开槽顶板，凹槽朝上嵌套印花（路线 A）或倒扣（路线 B） | #6B40A0 |
| `stl/print/multimaterial/filament_1_FBF4E8.stl` | 61801284 B | `af91f80cf94353e7` | 印花第 1 色（filament 1），与其他色一起导入、每对象一色 | #FBF4E8 |
| `stl/print/multimaterial/filament_2_CBE0F5.stl` | 16238884 B | `70c2746eb58a6289` | 印花第 2 色（filament 2），与其他色一起导入、每对象一色 | #CBE0F5 |
| `stl/print/multimaterial/filament_3_9FB2DA.stl` | 7267084 B | `d76f2b795316078d` | 印花第 3 色（filament 3），与其他色一起导入、每对象一色 | #9FB2DA |
| `stl/print/multimaterial/filament_4_F9CD72.stl` | 5689884 B | `9c6cf1747f883e42` | 印花第 4 色（filament 4），与其他色一起导入、每对象一色 | #F9CD72 |
| `stl/print/multimaterial/filament_5_F09FAF.stl` | 3137484 B | `7d950c065952e739` | 印花第 5 色（filament 5），与其他色一起导入、每对象一色 | #F09FAF |
| `stl/print/multimaterial/filament_6_6C574C.stl` | 2952484 B | `18a0419375b78ea5` | 印花第 6 色（filament 6），与其他色一起导入、每对象一色 | #6C574C |
| `PRINT_READY.3mf` | 15947545 B | `d0f9aeb95466edbf` | 路线 A 装配体 | 多色 |

- 单色预览 STL：**未交付**。skipped: the 6/7 per-filament STLs are closed solids with intentional coincident interface faces (parallel caps); a single-colour concatenation would carry internal/overlapping faces and a boolean union of 1.9-2.5 M triangles per version is not a reliable printable preview. Use PRINT_READY.3mf (multi-material) or the per-filament STLs instead.

## Bambu 导入顺序

- 1. 导入 stl/print/multimaterial/filament_*.stl（全部 6 个印花色）
- 2. 印花各对象按原位（XY 0,0 / 底面 z=0）装配，每个对象指定一个 AMS 槽位
- 3. 导入 stl/plate_recessed.stl，凹槽朝上，置于印花下方同一嵌套位置
- 4. 导入 stl/shell.stl（外壳单独打印）
- 5. 或直接使用 PRINT_READY.3mf（路线 A，已按装配位摆好）

## 采购件

OLED 模组 0.91" 128×32（含玻璃）、硅胶垫（防滑）、PCB（2 层，已设计）、HY928D 称重传感器、ESP32-S3 模组、HX711 ADC 模组、USB-C 连接器/线缆、500 mAh 锂电池、M2 螺钉/铜柱

## 耗材表

| # | 色号 | 画面占比 | 三角数 |
|---|---|---|---|
| 1 | #FBF4E8 | 57.5% | 1236024 |
| 2 | #CBE0F5 | 25.9% | 324776 |
| 3 | #9FB2DA | 2.7% | 145340 |
| 4 | #F9CD72 | 6.7% | 113796 |
| 5 | #F09FAF | 0.4% | 62748 |
| 6 | #6C574C | 6.7% | 59048 |

## 打印方向 / 支撑（PROVISIONAL）

- 路线 A：顶板凹槽朝上、印花嵌套（原位粘合），印花底面 = 槽底 z = 15.75 mm。
- 该姿态下顶板裙边/传力柱悬空 → 需树状支撑；未实物验证。
- 路线 B：顶板倒扣 + 印花单独平打，后压配/点胶（非原位粘合），无支撑。

## 排版与验证

- 床面：220×220 mm；本版占用 218.9×110.0 mm，最小间距 5.00 mm。
- shell：放置 (-54.47, 0.00) mm，bbox [110.0, 109.995, 13.4] mm。
- plate_unit：放置 (57.50, 0.00) mm，bbox [103.935, 103.968, 11.0] mm。
- 断言全部通过：床面适配、无越界、间距 ≥5 mm、无重叠、印花底面 = 槽底（9.750 mm）、印花厚度 1.20 mm。
- 渲染非黑：iso mean 60.61 / top mean 104.47；sheet 1800×1200。
- 交付 STL：8 个 / 98.7 MB，全部 sha256 与源文件一致。

## 打印参数建议

- **printer_profile**: generic FDM, 220 x 220 mm bed (Bambu Studio example)
- **layer_height_mm**: 0.2
- **nozzle_mm**: 0.4
- **line_width_mm**: 0.45
- **walls**: 2
- **top_bottom_layers**: 4 / 3
- **infill_pct**: 15
- **infill_pattern**: grid (shell) / gyroid (plate)
- **supports**: tree supports under the plate body (route A, recess-up nested print)
- **brim**: 5 mm for the button; none for shell; plate uses supports
- **filament_slots**: one filament per AMS slot: dog needs 6 slots, elf needs 7; a 4-slot AMS requires spool swaps or a second AMS / AMS lite
- **first_layer**: 0.2 mm, 200 mm/s max, part cooling off first layer
- **notes**: PROVISIONAL starting point; not physically tested. Screen window / button hole may need local support or bridging checks.

## 文件

- `PRINT_SHEET.png`（1800×1200）
- `manifest.json` / `layout.json` / `CHECKSUMS.sha256`
- 源文件：`mechanical/lumen/build/parts/shell_v01.stl`、`appearance/build/shell/round/plate_recessed.stl`、`appearance/build/print/dog/`

## 未验证

- 未在真实切片器中切片/打印；支撑与 z 间隙未实测。
- 3MF 中电子/玻璃/硅胶垫为参考几何，非打印件。
