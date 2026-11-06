# 3D 打印交付 — 方形 square_v1 / elf

> PROVISIONAL：打印方向/支撑建议未实物验证；尺寸来自外观管线 STL + `shell.json` + Kromacut manifest。**真实可打印 STL 已复制到 `stl/`，sha256 见 `CHECKSUMS.sha256`。**

## 打印路线（二选一）

### A) 推荐 · 多材料原位粘合（PRINT_READY.3mf）

顶板凹槽朝上 + 印花嵌在槽内，同盘打印（顶板裙边/传力柱需支撑，PROVISIONAL）；外壳单独打印。使用 PRINT_READY.3mf。

### B) 备选 · 无支撑（stl/ 分件）

顶板倒扣打印（表面好）+ 印花单独平打，之后压入/胶接（不是打印时粘合）。使用 stl/ 里的文件。

## 打印件 / STL 文件

| 零件 | STL（相对本目录） | 源文件 | 数量 | 材料/颜色 | 方向 | 支撑 |
|---|---|---|---|---|---|---|
| 外壳（底壳） | `stl/shell.stl` | `mechanical/square_v1/build/parts/shell_v01.stl` | 1 | PLA/PETG · #2A2E35 | 底面朝下平放（按设计） | 无支撑 |
| 开槽顶板 | `stl/plate_recessed.stl` | `appearance/build/shell/square/plate_recessed.stl` | 1 | PLA/PETG · #6B40A0 | 凹槽朝上，与印花嵌套（原位粘合） | PROVISIONAL：需树状支撑（裙边/传力柱悬空） |
| Kromacut 印花（elf） | `stl/print/multimaterial/filament_*.stl` | `appearance/build/print/elf/filament_*.stl` | 1 | 7 色 · 见耗材表 | 面朝上（face-up），嵌套进顶板凹槽 | 无；与顶板同一嵌套打印任务 |
| 按键 | `stl/button.stl` | `mechanical/square_v1/build/parts/button_v01.stl` | 1 | PLA/PETG · #6B40A0 | 底面朝下平放 | 无需；5 mm brim |

### STL 文件清单（交付副本）

| 文件 | 大小 | sha256（前 16 位） | 用途 | 材料 |
|---|---|---|---|---|
| `stl/shell.stl` | 1457284 B | `e98570809fd3e567` | 外壳（底壳），底面朝下打印 | #2A2E35 |
| `stl/plate_recessed.stl` | 221584 B | `1be0a466b2b715e4` | 开槽顶板，凹槽朝上嵌套印花（路线 A）或倒扣（路线 B） | #6B40A0 |
| `stl/button.stl` | 75484 B | `79ef3b49b8a6d169` | 按键，底面朝下 + 5 mm brim | #6B40A0 |
| `stl/print/multimaterial/filament_1_EDE1F0.stl` | 78705284 B | `dd8bbe44ba508d46` | 印花第 1 色（filament 1），与其他色一起导入、每对象一色 | #EDE1F0 |
| `stl/print/multimaterial/filament_2_D9CFE6.stl` | 15596084 B | `cd4d3a74e289421b` | 印花第 2 色（filament 2），与其他色一起导入、每对象一色 | #D9CFE6 |
| `stl/print/multimaterial/filament_3_C3AEDC.stl` | 11601884 B | `ddc795b50e63145d` | 印花第 3 色（filament 3），与其他色一起导入、每对象一色 | #C3AEDC |
| `stl/print/multimaterial/filament_4_F7D2C0.stl` | 7310884 B | `bff5e1ddaa038c22` | 印花第 4 色（filament 4），与其他色一起导入、每对象一色 | #F7D2C0 |
| `stl/print/multimaterial/filament_5_E8A9B8.stl` | 4985284 B | `5c140dd862c25318` | 印花第 5 色（filament 5），与其他色一起导入、每对象一色 | #E8A9B8 |
| `stl/print/multimaterial/filament_6_C9A45B.stl` | 3613284 B | `7b6f9cd0dc6bbbe7` | 印花第 6 色（filament 6），与其他色一起导入、每对象一色 | #C9A45B |
| `stl/print/multimaterial/filament_7_5B4A72.stl` | 3214884 B | `40d0300148eb4452` | 印花第 7 色（filament 7），与其他色一起导入、每对象一色 | #5B4A72 |
| `PRINT_READY.3mf` | 20815189 B | `8aca51d127d1815b` | 路线 A 装配体 | 多色 |

- 单色预览 STL：**未交付**。skipped: the 6/7 per-filament STLs are closed solids with intentional coincident interface faces (parallel caps); a single-colour concatenation would carry internal/overlapping faces and a boolean union of 1.9-2.5 M triangles per version is not a reliable printable preview. Use PRINT_READY.3mf (multi-material) or the per-filament STLs instead.

## Bambu 导入顺序

- 1. 导入 stl/print/multimaterial/filament_*.stl（全部 7 个印花色）
- 2. 印花各对象按原位（XY 0,0 / 底面 z=0）装配，每个对象指定一个 AMS 槽位
- 3. 导入 stl/plate_recessed.stl，凹槽朝上，置于印花下方同一嵌套位置
- 4. 导入 stl/shell.stl（外壳单独打印），stl/button.stl（按键，5 mm brim）
- 5. 或直接使用 PRINT_READY.3mf（路线 A，已按装配位摆好）

## 采购件

OLED 模组 0.91" 128×32（含玻璃）、硅胶垫（防滑）、PCB（2 层，已设计）、HY928D 称重传感器、ESP32-S3 模组、HX711 ADC 模组、USB-C 连接器/线缆、500 mAh 锂电池、M2 螺钉/铜柱

## 耗材表

| # | 色号 | 画面占比 | 三角数 |
|---|---|---|---|
| 1 | #EDE1F0 | 71.1% | 1574104 |
| 2 | #D9CFE6 | 7.1% | 311920 |
| 3 | #C3AEDC | 8.4% | 232036 |
| 4 | #F7D2C0 | 4.9% | 146216 |
| 5 | #E8A9B8 | 2.2% | 99704 |
| 6 | #C9A45B | 0.7% | 72264 |
| 7 | #5B4A72 | 5.5% | 64296 |

## 打印方向 / 支撑（PROVISIONAL）

- 路线 A：顶板凹槽朝上、印花嵌套（原位粘合），印花底面 = 槽底 z = 16.55 mm。
- 该姿态下顶板裙边/传力柱悬空 → 需树状支撑；未实物验证。
- 路线 B：顶板倒扣 + 印花单独平打，后压配/点胶（非原位粘合），无支撑。

## 排版与验证

- 床面：220×220 mm；本版占用 208.0×110.2 mm，最小间距 5.00 mm。
- shell：放置 (-54.00, 0.00) mm，bbox [100.0, 100.0, 14.5] mm。
- plate_unit：放置 (54.00, 0.00) mm，bbox [100.0, 100.0, 12.0] mm。
- 断言全部通过：床面适配、无越界、间距 ≥5 mm、无重叠、印花底面 = 槽底（10.550 mm）、印花厚度 1.40 mm。
- 渲染非黑：iso mean 60.90 / top mean 104.32；sheet 1800×1200。
- 交付 STL：10 个 / 126.8 MB，全部 sha256 与源文件一致。

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
- 源文件：`mechanical/square_v1/build/parts/shell_v01.stl`、`appearance/build/shell/square/plate_recessed.stl`、`appearance/build/print/elf/`

## 未验证

- 未在真实切片器中切片/打印；支撑与 z 间隙未实测。
- 3MF 中电子/玻璃/硅胶垫为参考几何，非打印件。
