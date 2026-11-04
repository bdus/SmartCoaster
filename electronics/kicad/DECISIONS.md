# V1-B PCB 决策记录（2026-11-04）

> **2026-11-04 状态注记**：本文件是 V1-B 初稿期的决策记录；其中第 2/3 条已被后续实现取代（封装已换官方、2 层板已布线到 0/0），第 1 条机械参数已按 B 版更新。最新状态以 `docs/HANDOFF.md` 为准。

1. **前脸模组离线，不加板舌**
   - OLED 走 J4（4P，GND/3V3/SCL/SDA），按键走 J5（2P），1.25 mm 线束到前壁模组。
   - 理由：屏/键固定在**底壳前壁**，不随浮动顶板运动；C 口保持 clearance；线束短、可维护。
   - 机械侧：`square_model.py` 仍是 A 版参数（OLED_X=27、BTN_X=5）；B 版前脸（窗 26×7、屏模组 38×12、键 x=17、顶板裙边前 C 口）需下一步更新并复跑 20/20 自检。
2. ~~**ESP32-S3-MINI-1 封装为 PROVISIONAL**~~ → **已关闭**：已换官方 Espressif `ESP32-S3-MINI-1` footprint（`footprints/SmartCoaster.pretty/`，65 pad），并重布线/复跑 DRC 到 0/0。
3. ~~**不布线、不覆铜**~~ → **已关闭**：封装/前脸冻结后已用 Freerouting 2.5.0 布通 2 层板（0 DRC / 0 unconnected，`route_2l.sh` 可复跑）。当前 2 层板未铺铜，GND 以走线实现（见 `build/DFM.md`）。
4. **待采购件复核**
   - FS8205A 引脚序；OLED 4P 引脚序（各家不同）；带保护板电芯时 DW01A+8205A 可 DNP。
