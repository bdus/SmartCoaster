# firmware/

固件（ESP-IDF，第二阶段）。当前只有 PRD/流程，**尚无代码**。

规划：`main/`、`components/`（HX711、OLED、按键、BLE）、`tests/`（pytest 算法测试）。
行为基线：100 ms 采样、滑动平均 + 稳定判定、放杯/喝水/续水/拿走状态机（见 `ref/Hydrate_AI_拆解与结构参考.md` §1.4）。
