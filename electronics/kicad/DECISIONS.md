# V1-B PCB 决策记录（2026-11-04）

1. **前脸模组离线，不加板舌**
   - OLED 走 J4（4P，GND/3V3/SCL/SDA），按键走 J5（2P），1.25 mm 线束到前壁模组。
   - 理由：屏/键固定在**底壳前壁**，不随浮动顶板运动；C 口保持 clearance；线束短、可维护。
   - 机械侧：`square_model.py` 仍是 A 版参数（OLED_X=27、BTN_X=5）；B 版前脸（窗 26×7、屏模组 38×12、键 x=17、顶板裙边前 C 口）需下一步更新并复跑 20/20 自检。
2. **ESP32-S3-MINI-1 封装为 PROVISIONAL**
   - KiCad 9.0.9 库缺 S3-MINI-1，初稿借用 S2-MINI-1 共板封装（20×15.4，65 pad）。
   - 打样前必须替换为 Espressif 官方 `ESP32-S3-MINI-1` footprint 并复跑 DRC；手板阶段用 DevKitC，不受影响。
3. **不布线、不覆铜**
   - 初稿只做板框 + placement；186 个未连接是预期。
   - 布线与 GND 覆铜放在机械前脸/器件封装冻结之后。
4. **待采购件复核**
   - FS8205A 引脚序；OLED 4P 引脚序（各家不同）；带保护板电芯时 DW01A+8205A 可 DNP。
