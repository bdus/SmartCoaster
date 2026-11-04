# SmartCoaster V1-B — 人可读连接表 (NETLIST)

> 由 `design.py` 生成，经 `verify.py` 与 KiCad 导出的网表逐引脚比对通过。
> 机器可读版本：`smartcoaster/smartcoaster.net`（KiCad XML）。

| # | 网络 | 连接 (器件.引脚) | 说明 |
|---|---|---|---|
| 1 | `3V3` | U6.5, C6.1, C7.1, U1.3, C10.1, R1.1, R2.1, R3.1, R4.1, U2.1, U2.3, U2.16, C11.1, C12.1, C15.1, TP1.1, J3.1, J4.2, R19.1, R20.1, R21.1, R22.1, R23.1, R24.1 | LDO 输出 |
| 2 | `BAT_MID` | U5.5, U5.6, U5.7, U5.8 | 双 MOSFET 共漏 |
| 3 | `CELL_N` | J2.2, U5.1, U4.6, C4.2 | 电芯负极（保护前） |
| 4 | `ESP_BOOT` | U1.4, R2.2, SW3.1 | GPIO0 下载模式 |
| 5 | `ESP_EN` | U1.45, R1.2, C9.1, SW2.1 | ESP32 EN 复位 |
| 6 | `GND` | J1.A1, J1.A12, J1.B1, J1.B12, J1.S1, U7.2, U3.3, U3.9, U3.1, C3.2, C1.2, C2.2, R8.2, U5.3, R12.2, U6.2, C5.2, C6.2, C7.2, R9.2, R10.2, C9.2, C10.2, SW2.2, SW3.2, U2.5, U2.4, U2.9, U2.10, U2.14, U2.15, C11.2, C12.2, C14.2, C15.2, R5.2, J3.2, TP2.1, J4.1, J5.2, R16.2, R17.2, R18.2, Q1.2, Q2.2, Q3.2, R7.2, C13.2, U1.1, U1.2, U1.42, U1.43, U1.46, U1.47, U1.48, U1.49, U1.50, U1.51, U1.52, U1.53, U1.54, U1.55, U1.56, U1.57, U1.58, U1.59, U1.60, U1.61, U1.62, U1.63, U1.64, U1.65 | 系统地 / 保护后负极 P- |
| 7 | `HALO_B_GATE` | R15.2, Q3.1, R18.1 | Q3 栅极 |
| 8 | `HALO_B_PWM` | U1.17, R15.1 | GPIO13 |
| 9 | `HALO_G_GATE` | R14.2, Q2.1, R17.1 | Q2 栅极 |
| 10 | `HALO_G_PWM` | U1.16, R14.1 | GPIO12 |
| 11 | `HALO_R_GATE` | R13.2, Q1.1, R16.1 | Q1 栅极 |
| 12 | `HALO_R_PWM` | U1.15, R13.1 | GPIO11 |
| 13 | `HX_A_N` | U2.7, R26.2, C16.2, TP4.1 | HX711 INA- (滤波后) |
| 14 | `HX_A_P` | U2.8, R25.2, C16.1, TP3.1 | HX711 INA+ (滤波后) |
| 15 | `HX_DOUT` | U2.12, U1.8, R5.1, TP5.1 | HX711 数据输出 (GPIO4) |
| 16 | `HX_PD_SCK` | U2.11, U1.9, TP6.1 | HX711 时钟 (GPIO5) |
| 17 | `HX_S_N` | J3.4, R26.1 | 传感器 S- (连接器侧) |
| 18 | `HX_S_P` | J3.3, R25.1 | 传感器 S+ (连接器侧) |
| 19 | `HX_VBG` | U2.6, C14.1 | HX711 基准 1.25 V |
| 20 | `I2C_SCL` | U1.13, J4.3, R4.2 | OLED SCL (GPIO9) |
| 21 | `I2C_SDA` | U1.12, J4.4, R3.2 | OLED SDA (GPIO8) |
| 22 | `KEY_K1` | U1.14, J5.1 | 用户按键 |
| 23 | `LED1_BA` | R21.2, D1.4 |  |
| 24 | `LED1_GA` | R20.2, D1.5 |  |
| 25 | `LED1_RA` | R19.2, D1.6 |  |
| 26 | `LED2_BA` | R24.2, D2.4 |  |
| 27 | `LED2_GA` | R23.2, D2.5 |  |
| 28 | `LED2_RA` | R22.2, D2.6 |  |
| 29 | `LED_B_K` | D1.3, D2.3, Q3.3 | 蓝通道共阴 |
| 30 | `LED_G_K` | D1.2, D2.2, Q2.3 | 绿通道共阴 |
| 31 | `LED_R_K` | D1.1, D2.1, Q1.3 | 红通道共阴 |
| 32 | `PROG` | U3.2, R8.1 | TP4056 充电电流设定 |
| 33 | `PROT_CS` | U4.2, R12.1 | DW01A 电流检测 |
| 34 | `PROT_OC` | U4.3, U5.4 | DW01A 充电控制 |
| 35 | `PROT_OD` | U4.1, U5.2 | DW01A 放电控制 |
| 36 | `PROT_VDD` | U4.5, R11.2, C4.1 | DW01A 供电(经100Ω) |
| 37 | `USB_CC1` | J1.A5, R9.1 | USB-C CC1 |
| 38 | `USB_CC2` | J1.B5, R10.1 | USB-C CC2 |
| 39 | `USB_DM` | J1.A7, J1.B7, U7.3, U7.4, U1.23 | USB D- |
| 40 | `USB_DP` | J1.A6, J1.B6, U7.1, U7.6, U1.24 | USB D+ |
| 41 | `VBAT` | U3.5, J2.1, C2.1, U6.1, U6.3, R11.1, R6.1, C5.1 | 电池正极（保护前） |
| 42 | `VBAT_SENSE` | U1.5, R6.2, R7.1, C13.1 | 电池分压 → GPIO1 |
| 43 | `VBUS` | J1.A4, J1.A9, J1.B4, J1.B9, U7.5, U3.4, U3.8, C3.1, C1.1 | USB 5 V（仅充电） |

## 引脚级速查（按器件）

- **J1** (USB_C_16P): A4→VBUS, A9→VBUS, B4→VBUS, B9→VBUS, A1→GND, A12→GND, B1→GND, B12→GND, S1→GND, A6→USB_DP, B6→USB_DP, A7→USB_DM, B7→USB_DM, A5→USB_CC1, B5→USB_CC2
- **U7** (USBLC6-2SC6): 5→VBUS, 2→GND, 1→USB_DP, 6→USB_DP, 3→USB_DM, 4→USB_DM
- **U3** (TP4056): 4→VBUS, 8→VBUS, 3→GND, 9→GND, 1→GND, 5→VBAT, 2→PROG
- **J2** (BATT 3.7V): 1→VBAT, 2→CELL_N
- **U4** (DW01A): 6→CELL_N, 1→PROT_OD, 3→PROT_OC, 5→PROT_VDD, 2→PROT_CS
- **U5** (FS8205A): 3→GND, 1→CELL_N, 5→BAT_MID, 6→BAT_MID, 7→BAT_MID, 8→BAT_MID, 2→PROT_OD, 4→PROT_OC
- **U6** (ME6211C33M5): 2→GND, 5→3V3, 1→VBAT, 3→VBAT
- **U1** (ESP32-S3-MINI-1): 1→GND, 2→GND, 42→GND, 43→GND, 46→GND, 47→GND, 48→GND, 49→GND, 50→GND, 51→GND, 52→GND, 53→GND, 54→GND, 55→GND, 56→GND, 57→GND, 58→GND, 59→GND, 60→GND, 61→GND, 62→GND, 63→GND, 64→GND, 65→GND, 3→3V3, 24→USB_DP, 23→USB_DM, 45→ESP_EN, 4→ESP_BOOT, 14→KEY_K1, 8→HX_DOUT, 9→HX_PD_SCK, 12→I2C_SDA, 13→I2C_SCL, 15→HALO_R_PWM, 16→HALO_G_PWM, 17→HALO_B_PWM, 5→VBAT_SENSE
- **SW2** (RESET): 2→GND, 1→ESP_EN
- **SW3** (BOOT): 2→GND, 1→ESP_BOOT
- **U2** (HX711): 5→GND, 4→GND, 9→GND, 10→GND, 14→GND, 15→GND, 1→3V3, 3→3V3, 16→3V3, 12→HX_DOUT, 11→HX_PD_SCK, 8→HX_A_P, 7→HX_A_N, 6→HX_VBG
- **J3** (LOAD CELL): 2→GND, 1→3V3, 3→HX_S_P, 4→HX_S_N
- **J4** (OLED 0.91"): 1→GND, 2→3V3, 4→I2C_SDA, 3→I2C_SCL
- **J5** (KEY K1): 2→GND, 1→KEY_K1
- **D1** (RGB): 1→LED_R_K, 2→LED_G_K, 3→LED_B_K, 6→LED1_RA, 5→LED1_GA, 4→LED1_BA
- **D2** (RGB): 1→LED_R_K, 2→LED_G_K, 3→LED_B_K, 6→LED2_RA, 5→LED2_GA, 4→LED2_BA
- **Q1** (2N7002): 2→GND, 1→HALO_R_GATE, 3→LED_R_K
- **Q2** (2N7002): 2→GND, 1→HALO_G_GATE, 3→LED_G_K
- **Q3** (2N7002): 2→GND, 1→HALO_B_GATE, 3→LED_B_K
- **TP1** (AVDD): 1→3V3
- **TP2** (AGND): 1→GND
- **TP3** (A+): 1→HX_A_P
- **TP4** (A-): 1→HX_A_N
- **TP5** (DOUT): 1→HX_DOUT
- **TP6** (PD_SCK): 1→HX_PD_SCK
