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

## 3. 已启用：PM 自动 light sleep + BT modem sleep

- `CONFIG_PM_ENABLE=y` + `CONFIG_FREERTOS_USE_TICKLESS_IDLE=y`；`esp_pm_configure(light_sleep_enable=true, 160/80 MHz)`。
- `CONFIG_BT_CTRL_MODEM_SLEEP=y`：BLE 广播/连接事件之间控制器休眠；OLED 8 s 息屏。
- **BLE 广播占空**：开机广播 30 s；长按 5 s 进入配对广播 120 s；其余时间**关广播**（连接后也不广播）。
- 预计平均：**2–3 mA**（广播只在窗口期 + HX711 1.5 mA）→ **7 天级**；连接期间 ~10 mA 属正常。
- App 同步方式：长按 5 s → 手机在 120 s 窗口内连接 → 同步/设目标/设时间；断开后广播关闭。
- 风险：light sleep 下 esp_timer/I2C 的时序、BLE 连接保持需实测；QEMU 不支持 PM，冒烟只作启动检查。

## 4. 测量方法

- 万用表 µA 档串在电池正极；分别测 息屏/亮屏/BLE 连接/提醒。
- 记录到 `tests/handboard/BRINGUP_RECORD.md` §5。

## 5. 判定

- 平均 < 3 mA → 7 天；3–6 mA → 3–7 天（可接受，记录）；> 6 mA → 需要更大电池或更激进休眠。
