# 3D 打印参考 — 方形 B

> 打印件由 `mechanical/square_v1` 参数化 CAD 生成；STL 在 `mechanical/square_v1/build/parts/`。
> **不要从 Blender 反向导出 STL 作为打印源**；STEP/STL 以 CAD 为准。

## 打印件

| 件 | 尺寸 | 数量 | 方向 / 支撑 |
|---|---|---|---|
| Shell 底壳 | 100×100×18 | 1 | 底面朝下；无需支撑 |
| Top plate 顶板 | 100×100×14.5（含裙边/柱） | 1 | 翻转，顶面贴床；裙边/柱朝上；无需支撑 |
| Button 按键 | Ø8.2×5 | 1 | 加 5 mm brim |

## 不打印

OLED 玻璃（PMMA）、硅胶垫、PCB、HY928D、电池、螺钉、0.91" 屏模组；按键帽可打印也可采购。

## 参数（起步）

- PLA / PETG，0.2 mm 层高，3 墙，15% 填充。
- 外壳/顶板平放，无支撑；按键 brim 5 mm。
- 0.2 mm 配合间隙（屏窗、按键孔）。
- 首件先打外壳 + 顶板验证屏/键/传感器配合，再打按键。
- 前脸装配后应只有屏窗 + 按键；顶板-底座 0.5 mm 是秤的浮动缝，不要填/不要加灯。

## 装配要点

- B 版前脸：只有 26×7 屏窗 @ x=−8 与按键 x=17；无灯、无灯带（用户 2026-11-04 决定去掉 LED 与灯带）。顶板前缘裙边有 40 mm C 口让屏。
- 四角传感器凸台共面度是关键（FEA：+y 两颗承担 99.4%）。
- 屏幕/按键固定在底壳前壁，不随浮动顶板运动。

## 图

- `render/print/PRINT_SHEET.png`（本页图；由 `render/print/make_sheet.py` 合成）
- `render/print/renders/`（Blender 打印布局渲染：`print_top.png` / `print_iso.png`）
- 复现：
  ```bash
  blender -b --python render/print/print_layout.py   # 出打印布局渲染
  python3 render/print/make_sheet.py                 # 合成 PRINT_SHEET.png
  ```
