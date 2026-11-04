# 装配说明（P1 4 层板，2026-11-04）

## 1. 贴装面

- **全部 56 个贴装器件在顶面**；底面 0 个（B.Cu 只走线/地）。
- 顶面：U1 S3-MINI-1 (0°)、U2 HX711 (90°)、U3 TP4056、U4 DW01A、U5 FS8205A、U6 ME6211、U7 USBLC6、D1 RGB、J1 USB-C、J2 电池座 (90°)、J4 OLED 排针 (90°)、J5 按键座 (90°)、SW2/SW3、R/C。
- 关键旋转：**U1 (29,32,0°)**、J1 (0°)、D1 (0°)、J2/J4/J5 (90°)。JLC 贴片前需按 JLC 封装库核对 USB-C/JST 的 0°/180° 约定。

## 2. 不贴 / 手焊

- TP1–TP6 测试点：`exclude from pos/BOM`，只做探针，不贴。
- J2/J4/J5 连接器、TP：手焊（或选贴）。
- U1、HY928D、OLED、电池：外购/模块，最后装配。

## 3. 装配顺序

1. 顶面 SMT（先小后大：R/C → IC → U1 → 连接器）。
2. 手焊 J2/J4/J5/TP。
3. 装 HY928D 传感器 + 硅胶垫，锁 M2×4。
4. 装 OLED（FPC/排线到 J4）、按键（J5）、电池（J2）。
5. 烧录/校准（见 `docs/05`），填 `tests/handboard/BRINGUP_RECORD.md`。

## 4. 拼板

- 单板 93.25 × 93.25 mm；建议板厂代拼 **2×2 V-groove + 5 mm 工艺边 + 4 个 fiducial + 4 个 tooling hole**。
- 本仓库只出单板 Gerber；拼板由板厂完成（或另做 panel 工程）。

## 5. 文件

- Gerber/钻孔/坐标/zip：`electronics/kicad/build/gerbers/`。
- 装配图：`build/assembly/top.pdf` / `bottom.pdf`（顶面有件、底面空）。
- BOM：`electronics/kicad/BOM.csv`（33 行；17 行 passive 缺 MPN，手焊按值/封装即可）。
- DFM：`build/DFM.md`（JLC 4 层全部 PASS）。
