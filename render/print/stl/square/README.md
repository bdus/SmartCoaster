# 3D 打印交付 — 方形 square_v1 / elf

> **打印姿态：顶板+印花整体翻转（凹槽朝下）**。第一层 = 印花正面 / 顶板外表面贴床；切片时看到印花背面（正确），打印完成后整体翻面即为成品。STL 已烘焙到此姿态并放在 `render/print/stl/square/`（sha256 校验）。

## 打印姿态关键尺寸

| 项 | 值 |
|---|---|
| 顶板外表面（原顶面）贴床 | z = -0.000 mm |
| 顶板槽底（凹槽朝下后的顶面） | z = 1.45 mm |
| 印花正面（第一层） | z = 0.05 mm（床上方 0.05 设计顶隙）
| 印花背面（坐在槽底） | z = 1.45 mm |
| 印花厚度 | 1.40 mm |
| 支撑 | 不需要（第一层贴床） |

## 按键（平躺）

- bbox ≈ 9.0 × 9.0 × 5.2 mm（z = 厚度 5.2 mm，圆盘平行床面）
- 可见正面（原 -Y 帽面）**朝下贴床**；翻面后可见面为光滑顶面（PROVISIONAL）。

## 打印件 / STL

| 零件 | STL（render/print/stl/square/） | 材料 | 打印方式 | 方向 |
|---|---|---|---|---|
| 外壳（底壳） | `shell.stl` | PLA/PETG · #2A2E35 | 打印 | 底面朝下（不变） |
| 开槽顶板 | `plate_recessed.stl` | PLA/PETG · #6B40A0 | 打印 | 翻转：凹槽朝下、原顶面贴床 |
| Kromacut 印花（elf） | `7 × square_print_filament_*.stl` | 7 色 · 见耗材表 | 打印 | 翻转：印花正面朝下（第一层贴床） |
| 按键 | `button.stl` | PLA/PETG · #6B40A0 | 打印 | 平躺（圆盘贴床，厚度 5.2 mm 竖直，正面朝下） |

## STL 文件清单（18 个文件，扁平目录）

| 文件 | 三角数 | 体积 mm³ | min z | 字节 | sha256(16) |
|---|---|---|---|---|---|
| `shell.stl` | 29144 | 28421.9 | 0.000000 | 1457284 | `676262c1ebc3e51a` |
| `plate_recessed.stl` | 4430 | 22220.4 | 0.000000 | 221584 | `33e27291959e80eb` |
| `button.stl` | 1508 | 196.6 | 0.000000 | 75484 | `b8c1e13c47924d73` |
| `print_filament_1_EDE1F0.stl` | 1574104 | 7215.1 | 0.000000 | 78705284 | `612a9481c1d42ca3` |
| `print_filament_2_D9CFE6.stl` | 311920 | 338.6 | 0.000000 | 15596084 | `039b80af1cad5633` |
| `print_filament_3_C3AEDC.stl` | 232036 | 255.4 | 0.000000 | 11601884 | `b030a1967992893d` |
| `print_filament_4_F7D2C0.stl` | 146216 | 156.6 | 0.000000 | 7310884 | `1889ce5bccdeba2a` |
| `print_filament_5_E8A9B8.stl` | 99704 | 99.2 | 0.000000 | 4985284 | `e0bfcad97406a2f4` |
| `print_filament_6_C9A45B.stl` | 72264 | 73.3 | 0.000000 | 3613284 | `688ddc4a993cdfc8` |
| `print_filament_7_5B4A72.stl` | 64296 | 64.6 | 0.000000 | 3214884 | `d3ec3eadf41d0c34` |

## 两种打印路线

- **A（推荐）**：第一层 = 印花正面 / 顶板外表面贴床；打印中看到的是印花背面（正确）；无需支撑；打完整体翻面即成品。用 PRINT_READY.3mf。
- **B（备选）**：顶板与印花分开打印（顶板仍凹槽朝下贴床；印花正面朝下单独平打），取出后压配/点胶（不是打印时粘合）。用 stl/ 分件。

## 排版与验证

- 床面 220×220；本版占用 208.0×114.0 mm，最小间距 5.00 mm，无越界/重叠。
- shell：放置 (-54.00, 0.00) mm，bbox [100.0, 100.0, 14.5] mm。
- plate_unit：放置 (54.00, 0.00) mm，bbox [100.0, 100.0, 12.0] mm。
- 每个交付 STL：三角数/体积与源一致、bbox = 刚性旋转源、min z = 0。
- 3MF 回读校验：OK（objects 11 / build items 4 / tris 2535622 / bbox [208.0, 113.998, 14.5]）。
- 渲染非黑；sheet 1800×1200。

## Bambu 导入顺序

- 1. 导入 render/print/stl/square/print_filament_*.stl（7 个印花色，按翻转姿态已烘焙）
- 2. 每个印花对象指定一个 AMS 槽位（7 色需 ≥7 槽位；4 槽需换料/第二台 AMS）
- 3. 导入 square_plate_recessed.stl（凹槽朝下、原顶面贴床），与印花同盘嵌套（印花正面在床面上方 0.05 mm）
- 4. 导入 square_shell.stl（底面朝下单独打印），square_button.stl（平躺，正面朝下 + 5 mm brim）
- 5. 或直接用 render/print/stl/square/PRINT_READY.3mf（床面排版）
- 6. 打印完成后整体翻面 → 成品外观（本姿态看到的是印花背面，正确）

## 两个 3MF

- `render/print/stl/square/PRINT_READY.3mf`：可切片床面排版。
- `appearance/build/3mf/square.3mf`：装配完成姿态 mockup（不直接切片）。

## 未验证

- 未在真实切片器切片/打印；0.05 mm 首层、按键朝向为 PROVISIONAL。

