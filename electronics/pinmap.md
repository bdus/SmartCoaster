# 电子系统引脚 / 电源树（B 版草案）

> 状态：**草案**，作为 KiCad 原理图与固件的共同输入。屏 0.91" 128×32 SSD1306 I2C；单键。
> **2026-11-04 用户决定：光导与 LED 全部去掉**（D1、Q1–Q3、R13–R21 已从原理图/PCB 删除），本文件已无灯光通道。

## 1. 电源树

```
USB-C 5V ── ESD ── TP4056 ── LiPo 3.7V (500mAh, JST-PH)
                      │            │
                      │            └── DW01A + 8205A 保护
                      └── 5V 仅充电时（可选升压，V1 不用）
LiPo ── ME6211C33 (3.3V, 500mA) ──┬── ESP32-S3-MINI-1
                                  ├── HX711 (DVDD/AVDD/VSUP = 3.3V)
                                  ├── OLED 0.91" (3.3V)
                                  └── 分压 → GPIO1 (电池电压)
```

- HX711 用**外部 3.3 V 激励**（不用片内稳压）：`VSUP=DVDD=AVDD=3.3V`、`VFB=GND`、`BASE=NC`、`XI=GND`、`RATE=GND`（10 Hz）。
- 桥流 ≈ 3.3 mA；HX711 自身 ≈ 1.5 mA；OLED ≈ 12 mA（仅亮屏）；ESP32-S3 睡眠 ≈ 50 µA。
- 500 mAh 估算 ~12 天（见 `docs/design/2026-11-04-ui-interaction-b-design.md` §7）。

## 2. ESP32-S3-MINI-1 引脚

| 功能 | GPIO | 方向 | 备注 |
|---|---|---|---|
| HX711 DOUT | GPIO4 | 输入 | 上电默认高；内部无上下拉，外部 10k 下拉可选 |
| HX711 PD_SCK | GPIO5 | 输出 | 空闲低；脉冲 25–27 个，宽度 <50 µs |
| OLED SDA | GPIO8 | 双向 | I2C 0x3C，**板上 2.2k 上拉**（400 kHz 上升沿；S2 仿真 EL-01） |
| OLED SCL | GPIO9 | 输出 | 400 kHz |
| 按键 K1 | GPIO10 | 输入 | 内部上拉，按下接地；30 ms 去抖 |
| （未用） | GPIO11/12/13 | — | 原 halo 三路 PWM，2026-11-04 随 LED 一并删除，现悬空 |
| 电池电压 | GPIO1 | 模拟 | 1:2 分压（100k/100k）+ 100nF |
| USB D− | GPIO19 | 双向 | 原生 USB |
| USB D+ | GPIO20 | 双向 | 原生 USB |
| EN | EN | 输入 | 10k 上拉 + 1µF + 复位键 |
| BOOT | GPIO0 | 输入 | 10k 上拉 + 按键 |

> 具体 GPIO 以 ESP32-S3-MINI-1 数据手册的可用引脚为准；避开 strapping 脚（0/3/45/46）与 USB 专用脚。

## 3. 外设

| 器件 | 接口 | 关键参数 |
|---|---|---|
| HX711 | 2-wire (DOUT/PD_SCK) | 增益 128，10 Hz，±12.9 mV@3.3 V（±20 mV@5 V），SOP-16 |
| OLED | I2C | 0.91" 128×32，SSD1306，3.3 V，0x3C，模组 38×12×1.2 |
| 按键 | GPIO | Ø8.2 轻触，行程 0.6 mm |
| 灯光 | — | **无 LED/光导**（用户 2026-11-04 决定）；反馈只有 0.91" 屏 |
| 电池 | JST-PH | 3.7 V 500 mAh，带保护板 |
| USB-C | 16P | CC1/CC2 5.1k，ESD USBLC6-2SC6 |

## 4. 称重链路

```
HY928D (1.2 mV/V, 3.3V) → 3.96 mV FS → HX711 gain 128 → 0.506 V FS → 24-bit
```

- 量程占 ±12.9 mV 的 **30.7%**；理论分辨力远小于 1 g，实际受噪声/温漂限制。
- 采样 10 Hz；固件 5 点中值 + 0.3 s 稳定窗（见 `firmware/model/`）。

## 5. 待定

- 充电 IC：TP4056（便宜、SOP-8）vs BQ24075（更好但 QFN）；V1 先 TP4056 + DW01A。
- ~~Halo：3 路 PWM + MOSFET vs WS2812~~ → **已取消**（用户不要灯光）。
- 电池电量：分压 ADC 精度足够，还是用 MAX17048？V1 先用 ADC。
- USB-C 是否要 CC 逻辑/角色切换：V1 只做受电。
