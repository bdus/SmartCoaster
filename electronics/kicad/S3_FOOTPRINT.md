# ESP32-S3-MINI-1 footprint（已切换，2026-11-04）

## 结论

- 原理图符号：`RF_Module:ESP32-S3-MINI-1`（设计一开始就是 S3 符号，引脚号/IO 名正确）。
- 封装：原 `RF_Module:ESP32-S2-MINI-1`（65 pad）→ **官方 Espressif `ESP32-S3-MINI-1`**（65 pad，`footprints/SmartCoaster.pretty/`）。
- 兼容性：两者 **65 个焊盘中心布局完全一致**，仅封装原点相差 **2.55 mm**；U1 放 (29, −33.25) 使焊盘中心与旧板重合，旧走线可直接复用。
- 结果：4 层、**0 unconnected / 0 short**；DRC 剩 **1 项已知 clearance**：`HALO_R_PWM` via 与 `D1 pad 3` 间距 **0.064 mm**（< 0.2）。

## 已知项（下一版修）

- `HALO_R_PWM` 的过孔（−35.62, −4.46）离 D1 的 LED_B_K 焊盘太近。下一版把 R13 从 LED 簇移开 1–2 mm，或给 D1 加 keepout 后重布；不影响“0 short / 0 unconnected”判定，但打样前建议修掉。
- 机械模型里的 ESP32 占位体仍在 mech y=+35.8；电气 U1 移到 +33.25，机械侧需同步 2.55 mm（下一轮 `cad/verify_v01.py` 复跑时一起改）。

## 制造文件

- `build/gerbers/`（F/In1/In2/B + mask/paste/silk/edge）、`.drl`、`.pos`、`smartcoaster_4l_gerbers.zip`（已用官方 S3 land pattern 重出）。
