# render/print/stl — 3D 打印交付 STL（两种外观版本）

> **打印姿态：顶板+印花整体翻转（凹槽朝下）**。第一层 = 印花正面 / 顶板外表面贴床；印花正面在床面上方 0.05 mm（设计顶隙）。打印完成后整体翻面即为成品外观。

所有文件为 `cp` 副本/烘焙件（非软链）；每件均通过 triangle-count / volume / bbox=刚性旋转源 / min z=0 校验，变换矩阵与源 sha256 见 `delivery.json`。

## 文件

| 文件 | 版本 | 零件 | 材料 | 三角数 | 体积 mm³ | min z | 字节 |
|---|---|---|---|---|---|---|---|
| `round_shell.stl` | round | shell | #2A2E35 | 27412 | 17161.3 | 0.000000 | 1370684 |
| `round_plate_recessed.stl` | round | plate_recessed | #6B40A0 | 4082 | 19336.2 | 0.000000 | 204184 |
| `round_print_filament_1_FBF4E8.stl` | round | print_filament | #FBF4E8 | 1236024 | 6015.3 | 0.000000 | 61801284 |
| `round_print_filament_2_CBE0F5.stl` | round | print_filament | #CBE0F5 | 324776 | 497.8 | 0.000000 | 16238884 |
| `round_print_filament_3_9FB2DA.stl` | round | print_filament | #9FB2DA | 145340 | 193.9 | 0.000000 | 7267084 |
| `round_print_filament_4_F9CD72.stl` | round | print_filament | #F9CD72 | 113796 | 162.0 | 0.000000 | 5689884 |
| `round_print_filament_5_F09FAF.stl` | round | print_filament | #F09FAF | 62748 | 83.5 | 0.000000 | 3137484 |
| `round_print_filament_6_6C574C.stl` | round | print_filament | #6C574C | 59048 | 78.6 | 0.000000 | 2952484 |
| `square_shell.stl` | square | shell | #2A2E35 | 29144 | 28421.9 | 0.000000 | 1457284 |
| `square_plate_recessed.stl` | square | plate_recessed | #6B40A0 | 4430 | 22220.4 | 0.000000 | 221584 |
| `square_button.stl` | square | button | #6B40A0 | 1508 | 196.6 | 0.000000 | 75484 |
| `square_print_filament_1_EDE1F0.stl` | square | print_filament | #EDE1F0 | 1574104 | 7215.1 | 0.000000 | 78705284 |
| `square_print_filament_2_D9CFE6.stl` | square | print_filament | #D9CFE6 | 311920 | 338.6 | 0.000000 | 15596084 |
| `square_print_filament_3_C3AEDC.stl` | square | print_filament | #C3AEDC | 232036 | 255.4 | 0.000000 | 11601884 |
| `square_print_filament_4_F7D2C0.stl` | square | print_filament | #F7D2C0 | 146216 | 156.6 | 0.000000 | 7310884 |
| `square_print_filament_5_E8A9B8.stl` | square | print_filament | #E8A9B8 | 99704 | 99.2 | 0.000000 | 4985284 |
| `square_print_filament_6_C9A45B.stl` | square | print_filament | #C9A45B | 72264 | 73.3 | 0.000000 | 3613284 |
| `square_print_filament_7_5B4A72.stl` | square | print_filament | #5B4A72 | 64296 | 64.6 | 0.000000 | 3214884 |

## 变换（打印姿态，mm，行向量 v' = v @ R.T + t）

- **round**：plate = 180° about X；print = 180° about X（同一变换用于 6/7 个印花件，保持相对位置）；shell 不变；无按键
  - plate R=[[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]] t=[-0.03232, -0.0, 17.0]
  - print R=[[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]] t=[-0.0, -0.0, 1.2]
- **square**：plate = 180° about X；print = 180° about X（同一变换用于 6/7 个印花件，保持相对位置）；shell 不变；button = 90° about Z（轴水平沿 X，侧躺）
  - plate R=[[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]] t=[-0.0, -0.0, 18.0]
  - print R=[[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]] t=[-0.0, -0.0, 1.4]

## Bambu Studio 导入顺序

1. 导入本目录全部 `*_print_filament_*.stl`（6 / 7 个印花色），或直接使用 `render/print/appearance/<v>/PRINT_READY.3mf`（已排好床面）；
2. 每个印花对象指定一个 AMS 槽位（6 色需 ≥6 槽位 / 7 色需 ≥7 槽位；4 槽需换料或第二台 AMS）；
3. `*_plate_recessed.stl` 为翻转后姿态（凹槽朝下、原顶面贴床），与印花同盘嵌套打印（第一版 0.05 mm 在床面上方）；
4. `*_shell.stl` 底面朝下单独打印；方形加 `square_button.stl`（侧躺，轴水平，5 mm brim）；
5. 打印完成后整体翻面 → 成品外观。

## 两个 3MF 的用途

- `render/print/appearance/<v>/PRINT_READY.3mf`：可切片**床面排版**（本交付）。
- `appearance/build/3mf/<v>.3mf`：装配完成姿态的数字样机（mockup，不用于直接切片）。

## 备注

- 本姿态无需支撑（第一层贴床）；PROVISIONAL：尚未实物打印验证。
- 印花各色件为带“同面异向界面”的闭合实体，全部三角形保留（不删面）。
