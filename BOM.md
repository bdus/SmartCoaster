# BOM（当前概念版）

> **2026-11-04 起：LED 与所有发光件全部去掉。** 原理图 **43 器件 / 28 网络**（由 62 器件删去 LED 13 个 + 测试点 TP 6 个）；PCB 最多 2 层。前脸只有 26×7 屏窗 + 按键，无灯、无灯缝。

机械两版的物料与估价见：
- [LUMEN 设计说明 §6](mechanical/lumen/docs/design_brief.md)（圆形为概念线，发光方案已废弃，不推进）
- 方形 V1：`mechanical/square_v1/README.md`（器件占位同 LUMEN，按键/屏幕不同；发光件已从 CAD 删除，13→12 件）

关键件：HY928D 5 kg、HX711、ESP32-S3-MINI-1、0.91" OLED（26×7 可视窗）、USB-C、500 mAh LiPo、6063 铝顶板、PC/ABS 壳、PMMA 窗玻璃、硅胶垫、M2 螺丝。

> 价格与封装为概念级估价，打样前按实际采购更新。
> 板上器件清单以 `electronics/kicad/BOM.csv` 为准（43 器件，无 D1/Q1–Q3/R13–R21/TP1–TP6）。
