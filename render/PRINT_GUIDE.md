# 3D 打印参考 — 方形 B

> 打印件由 `mechanical/square_v1` 参数化 CAD 生成；STL 在 `mechanical/square_v1/build/parts/`。
> **不要从 Blender 反向导出 STL 作为打印源**；STEP/STL 以 CAD 为准。

## 打印件

| 件 | 尺寸 | 数量 | 方向 / 支撑 |
|---|---|---|---|
| Shell 底壳 | 100×100×18 | 1 | 底面朝下；无需支撑 |
| Top plate 顶板 | 100×100×14.5（含裙边/柱） | 1 | 翻转，顶面贴床；裙边/柱朝上；无需支撑 |
| Button 按键 | Ø8.2×5 | 1 | 加 5 mm brim |

## 光导件（非 FDM）

- `light_guide`：PMMA clear，0.9 mm 厚，窗周 halo 框 + 左前灯线 + 2×2 内部导光条；激光切割/透明树脂，不要用不透光耗材。

## 不打印

OLED 玻璃（PMMA）、硅胶垫、PCB、HY928D、电池、螺钉、0.91" 屏模组；按键帽可打印也可采购。

## 参数（起步）

- PLA / PETG，0.2 mm 层高，3 墙，15% 填充。
- 外壳/顶板平放，无支撑；按键 brim 5 mm。
- 0.2 mm 配合间隙（屏窗、按键孔）。
- 首件先打外壳 + 顶板验证屏/键/传感器配合，再打按键。

## 装配要点

- B 版前脸：屏窗 26×7 @ x=−8，按键 x=17；顶板前缘裙边有 40 mm C 口让屏。
- 四角传感器凸台共面度是关键（FEA：+y 两颗承担 99.4%）。
- 屏幕/按键固定在底壳前壁，不随浮动顶板运动。

## 图

- `render/print/PRINT_SHEET.png`（本页图）
- `render/print/renders/`（Blender 打印布局渲染，可选）
