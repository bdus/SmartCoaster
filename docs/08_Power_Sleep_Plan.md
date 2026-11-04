# 功耗与休眠计划（P1）

> 目标：500 mAh 电池 ≥ 7 天（平均 < 3 mA）。

## 1. 当前

| 状态 | 典型电流 | 说明 |
|---|---:|---|
| ESP32-S3 活跃（10 ms loop） | 40–60 mA | 主循环 + HX711 轮询 + OLED |
| OLED 亮 | 12–15 mA | 0.91" 128×32 |
| HX711 | 1.5 mA | 连续 |
| halo | 10–20 mA | 提醒时 |
| **合计（无休眠）** | **~55 mA** | **500 mAh ≈ 9 h** |

## 2. 已做：息屏

- 8 s 无事件 → `oled_display_off()`（0xAE）；按键/放杯/拿杯/提醒立即 `oled_display_on()`。
- 省 ~12–15 mA，但仍 ~40 mA。

## 3. 待做：light sleep

- 采样节拍：HX711 DRDY（GPIO4 下降沿）或 20 ms 定时唤醒；两次采样间 `esp_light_sleep_start()`。
- 按键 GPIO10、DRDY 配置 GPIO 唤醒；OLED 息屏；halo 关闭。
- BLE：连接时用 modem sleep / 较长连接间隔；广播间隔 1 s。
- 目标平均：HX711 间歇供电 + 20 ms 唤醒 → **~2–4 mA**；若 BLE 常连则 ~5–8 mA（7 天需 1–2 s 连接间隔）。
- 风险：light sleep 下 I2C/OLED 需重新初始化；BLE 连接可能断；需实测。

## 4. 测量方法

- 万用表 µA 档串在电池正极；分别测 息屏/亮屏/BLE 连接/提醒。
- 记录到 `tests/handboard/BRINGUP_RECORD.md` §5。

## 5. 判定

- 平均 < 3 mA → 7 天；3–6 mA → 3–7 天（可接受，记录）；> 6 mA → 需要更大电池或更激进休眠。
