# 装配说明（2 层板，2026-11-04 去灯版）

> 本版对应 **2 层主方案**：**43 器件 / 28 网络**，无 LED、无发光件、无测试点；前脸只有 26×7 屏窗 + 按键。
> 器件与位号以 `electronics/kicad/BOM.csv` 为准；装配图/坐标以 `electronics/kicad/build/assembly/` 重出文件为准。

## 1. 贴装面

- **全部贴装器件在顶面**；底面 0 个（B.Cu 只走线/地）。
- 板级统计（2 层板文件）：47 footprint（43 器件 + H1–H4 安装孔）、**211 SMD pad / 12 PTH / 6 NPTH**。
- 顶面主要器件：U1 ESP32-S3-MINI-1 (0°)、U2 HX711 (90°)、U3 TP4056、U4 DW01A、U5 FS8205A、U6 ME6211、U7 USBLC6；J1 USB-C、J2 电池座 (90°)、J3 称重传感器 (JST-SH 4P)、J4 OLED 排针 (90°)、J5 按键座 (90°)；SW2/SW3、R/C。
- 关键旋转：**U1 (29,32,0°)**、J1 (0°)、J2/J4/J5 (90°)。JLC 贴片前需按 JLC 封装库核对 USB-C/JST 的 0°/180° 约定。
- **注意**：不再有 D1 RGB、Q1–Q3/R13–R21 等 LED 驱动器件；BOM 中也不含 TP1–TP6。

## 2. 不贴 / 手焊

- H1–H4：安装孔，不贴。
- J2/J4/J5、J3：连接器，手焊（或选贴）。
- U1、HY928D、OLED、电池：外购/模块，最后装配。

## 3. 装配顺序

1. 顶面 SMT（先小后大：R/C → IC → U1 → 连接器）。
2. 手焊 J3/J2/J4/J5。
3. 装 HY928D 传感器 + 硅胶垫，锁 M2×4。
4. 装 OLED（FPC/排线到 J4）、按键（J5）、电池（J2）。
5. 烧录/校准（见 `docs/05`），填 `tests/handboard/BRINGUP_RECORD.md`。

## 4. 拼板

- 单板 93.25 × 93.25 mm；建议板厂代拼 **2×2 V-groove + 5 mm 工艺边 + 4 个 fiducial + 4 个 tooling hole**。
- 本仓库只出单板 Gerber；拼板由板厂完成（或另做 panel 工程）。

## 5. 文件

- Gerber/钻孔/坐标/zip：`electronics/kicad/build/gerbers/`（本轮 2 层版重出）。
- 装配图：`electronics/kicad/build/assembly/top.pdf` / `bottom.pdf`（顶面有件、底面空）。
- BOM：`electronics/kicad/BOM.csv`（43 器件；部分 passive 缺 MPN，手焊按值/封装即可）。
- DFM：`electronics/kicad/build/DFM.md`（2 层版，JLC 工艺对照）。
- DRC 证据：`electronics/kicad/build/DRC_2l.rpt`。
