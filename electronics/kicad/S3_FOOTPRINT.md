# ESP32-S3-MINI-1 footprint（已切换，0 DRC，2026-11-04）

## 结论

- 符号：`RF_Module:ESP32-S3-MINI-1`（设计一开始就是 S3，引脚号/IO 名正确）。
- 封装：官方 Espressif `ESP32-S3-MINI-1`（65 pad，`footprints/SmartCoaster.pretty/`）。
- 焊盘：与 S2-MINI-1 布局一致，仅封装原点差 2.55 mm。
- U1 位置：KiCad `(29, −32.0)` = 机械 `(29, +32.0)`；模块后缘 **+39.75**，壳腔 **+40**（0.25 mm 余量）。
  - 相比旧板 `(29, −35.8)` 前移 3.8 mm（S3 原点 2.55 + 壳腔 1.25），旧走线不复用，已重新布线。
- 结果（2026-11-04 重跑）：**2 层**布线，`kicad-cli pcb drc --severity-all` **0 violation / 0 unconnected**（`build/DRC_2l.rpt`；silk 非电气项按项目 severity 豁免）。
- 机械：ESP32 占位体同步 `(29, 32.0)`，`cad/verify_v01.py` **21/21**。
- 制造文件：`build/gerbers/`、`.drl`、`.pos`、`build/smartcoaster_2l_gerbers.zip`（官方 S3 land pattern，2 层）。

## 备注

- 之前“S3 65 pad vs S2 73 pad 不兼容”是误判：实际两者都是 65 pad，焊盘中心一一对应。
- 旧 U1 位于 (29,−35.8) 时模块后缘会进入壳壁 3.5 mm；这次机械同步把电气/机械都收敛到 (29,32.0)。
