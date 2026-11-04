# ESP32-S3-MINI-1 footprint gap（P2 打样前必须解决）

- 当前板 U1：`RF_Module:ESP32-S2-MINI-1`（**65 pads**），作为 S3-MINI-1 的临时共板替代。
- 官方 Espressif `ESP32-S3-MINI-1` footprint：**65 pads**（已下载到 `footprints/ESP32-S3-MINI-1.kicad_mod`）。
- 实测 pad 1：官方 S3 本地坐标 (-7.0, -5.95)、0.4×0.8；当前板 U1 pad 1 本地 (-7.0, -3.4)、0.8×0.4 —— **位置/尺寸/数量都不同，不兼容**。
- 两者焊盘数量/间距/引脚定义不同，**不能直接替换**；当前 Gerber 不能作为最终打样文件。

## 替换步骤（P2）

1. 用官方 S3-MINI-1 符号/封装替换 U1（`design.py` 的符号、引脚映射）。
2. 复核 pin map：GPIO4/5（HX711）、8/9（I2C）、10（按键）、11-13（halo）、1（电池 ADC）、USB D+/D-、EN/BOOT；避开 strapping（0/3/45/46）。
3. 重跑 ERC/网表比对 → 4 层布线 → DRC。
4. 重新出 Gerber/钻孔/坐标；打样。

## 为什么 P1 不受影响

P1 手板用 **ESP32-S3-DevKitC-1**，不贴这块板；PCB 是 P2 的产物。S3 替换 + 重布线作为 P2 的第一件事。
