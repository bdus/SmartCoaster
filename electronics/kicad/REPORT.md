# SmartCoaster V1-B — KiCad 9 原理图 / PCB 初稿报告

> 日期：2026-11-04 · 版本 `0.1-DRAFT` · 工具：KiCad **9.0.9**（`/data/Documents/tools/kicad`，`kicad-cli` 在 `~/.local/bin`）+ Python 3.10（`/data/Documents/tools/sim-venv`）
> 状态：**设计初稿，未打样、未布线**。所有"通过"仅指 EDA 检查通过，不代表实物验证。

---

## 0. 结论摘要

| 项目 | 结果 |
|---|---|
| 原理图 `.kicad_sch` | **已生成**（A2，单页，66 器件 / 43 网络 / 194 条网络标签） |
| 网表一致性 | **PASS** — 导出的 KiCad 网表与 `design.py` 逐引脚比对，43 个网络全部一致，无多接/漏接 |
| ERC (`kicad-cli sch erc --severity-all`) | **0 violations（0 error / 0 warning）** |
| 板框 | **已生成** — 93.2×93.2 R6 C 环，中央 38×38 方孔，前缘 80° C 口，4×M2 孔，`Edge.Cuts` 全部闭合 |
| Placement | **已生成** — 70 个 footprint（66 器件 + 4 安装孔），2 层；几何自检 0 重叠 / 0 出界 |
| DRC (`kicad-cli pcb drc`) | **除"未连接"外 0 violation**；未连接 **186 项**（未布线，预期）；丝印 warning **44 条** |
| BOM | **33 行 / 66 器件**（`BOM.csv`） |
| 未完成 | 布线、覆铜（GND 平面未灌）、电源完整性、EMC、实物验证 |

---

## 1. 交付物

```
electronics/kicad/
├── BOM.csv                       33 行物料表（型号/封装/数量/关键参数）
├── NETLIST.md                    人可读连接表（43 网络 + 按器件速查）
├── REPORT.md                     本报告
├── build/                        ERC.rpt / DRC.rpt / sch.pdf / pcb_layout.png / *.net.xml
├── scripts/                      生成与校验脚本（build.sh 一键重建）
│   ├── design.py                 ★ 唯一设计源：器件、网络、原理图坐标
│   ├── ksexpr.py / kicadlib.py   KiCad S-expression 解析 + 符号库读取（含 extends 解析）
│   ├── gen_sch.py                生成 .kicad_sch / .kicad_pro / .kicad_sym / sym-lib-table
│   ├── verify.py                 导出网表并与 design.py 逐引脚比对（关键闸门）
│   ├── gen_pcb.py                生成 .kicad_pcb（板框 + 70 footprint + 网络）
│   ├── check_pcb.py              shapely 几何自检（板内、courtyard 重叠）
│   ├── gen_bom.py                BOM.csv / NETLIST.md
│   └── render_pcb.py             布局预览图
└── smartcoaster/
    ├── smartcoaster.kicad_pro    工程（2 层、DRC 严重度、网络类）
    ├── smartcoaster.kicad_sch    原理图
    ├── smartcoaster.kicad_pcb    PCB 初稿
    ├── smartcoaster.kicad_sym    工程符号库（FS8205A）
    ├── smartcoaster.net          KiCad XML 网表
    └── sym-lib-table
```

重建：`cd electronics/kicad/scripts && ./build.sh`（重生成 + 自检 + BOM，约 20 s）。

---

## 2. 原理图

### 2.1 生成方式（为什么是"标签式"原理图）

`design.py` 是唯一设计源；`gen_sch.py` 用 KiCad 官方符号库（`Device`、`Analog_ADC`、`RF_Module`、
`Battery_Management`、`Regulator_Linear`、`Connector`、`Power_Protection`、`Switch`、`Transistor_FET`）
把每个符号实例化，给**每个引脚加 5.08 mm 引线 + 网络标签**，再由 KiCad 的连接引擎按标签名合并网络。
FS8205A 在官方库里不存在，自建 `smartcoaster.kicad_sym`（工程库，不是伪造封装）。

这样做的代价是图面偏"网表化"（每个引脚都挂标签），换来的是**可机器校验**：

1. `kicad-cli sch export netlist --format kicadxml`
2. `verify.py` 把导出网表按网络逐引脚与 `design.py` 比对 → **PASS**
3. `kicad-cli sch erc --severity-all` → **0 violations**

即：图上任何一处悬空/短接/标签写错，第 2 步就会报出来；不存在"ERC 通过但网络是错的"的盲区。

### 2.2 电路内容（对照 `electronics/pinmap.md`）

| 功能块 | 器件 |
|---|---|
| USB-C 输入 | J1 16P 受电、R9/R10 5.1k CC1/CC2、U7 USBLC6-2SC6（D+/D- ESD）、C1 10 µF |
| 充电 | U3 TP4056（ESOP-8，EPAD 接地）、R8 2.4 k（Iprog=500 mA）、C3 10 µF / C2 1 µF |
| 电池保护 | J2 JST-PH、U4 DW01A、U5 FS8205A（共漏双 N-MOS）、R11 100 Ω + C4 100 nF、R12 1 k |
| 3.3 V | U6 ME6211C33M5（Vin=VBAT，CE 常使能）、C5/C6 1 µF、C7 10 µF |
| MCU | U1 ESP32-S3-MINI-1、R1 10 k + C9 1 µF（EN）、SW2 RESET、R2 10 k + SW3 BOOT、C10 100 nF |
| 称重前端 | U2 HX711（SOP-16 芯片级）、J3 4P 传感器座、R25/R26 1 k + C16 100 nF、C11/C12/C14/C15、R5 10 k、TP1–TP6 |
| 显示/按键 | J4 OLED 4P、R3/R4 4.7 k I2C 上拉、J5 按键座 |
| Halo | D1/D2 共阳 RGB 5050、Q1–Q3 2N7002、R13–R15 100 Ω 栅极、R16–R18 100 k 下拉、R19–R24 47 Ω 限流 |
| 电量 | R6/R7 100 k 分压 + C13 100 nF → GPIO1 |

### 2.3 GPIO 映射（与 pinmap.md 一致，已写入网表）

| 功能 | GPIO | 模块引脚 | 网络名 |
|---|---|---|---|
| HX711 DOUT | GPIO4 | 8 | `HX_DOUT` |
| HX711 PD_SCK | GPIO5 | 9 | `HX_PD_SCK` |
| OLED SDA / SCL | GPIO8 / GPIO9 | 12 / 13 | `I2C_SDA` / `I2C_SCL` |
| 按键 K1 | GPIO10 | 14 | `KEY_K1` |
| Halo R/G/B | GPIO11/12/13 | 15/16/17 | `HALO_*_PWM` |
| 电池电压 | GPIO1 (ADC1_CH0) | 5 | `VBAT_SENSE` |
| USB D- / D+ | GPIO19 / GPIO20 | 23 / 24 | `USB_DM` / `USB_DP` |
| EN / BOOT | EN / GPIO0 | 45 / 4 | `ESP_EN` / `ESP_BOOT` |

未用 GPIO（含 strapping 3/45/46、TXD0/RXD0）全部打 **no_connect**，这是 ERC 0 warning 的前提。

### 2.4 ERC 结果

```
kicad-cli sch erc --format report --severity-all --units mm
→ ** ERC messages: 0  Errors 0  Warnings 0 **
```
**没有需要"接受"的库/封装缺失 warning** —— 唯一一条 `lib_symbol_issues`（smartcoaster 工程库未加载）
通过随工程输出 `sym-lib-table` + `smartcoaster.kicad_sym` 消除；`footprint_link_issues` 通过改用库中
真实存在的封装（`SW_SPST_B3U-1000P`、`JST_SH_BM04B-SRSS-TB`、`SOIC-8-1EP_..._EP2.41x3.81mm`）消除。

---

## 3. HX711 芯片级集成（按要求确认）

**HX711 以 SOP-16 芯片直接贴装在主板上，没有使用外接模块。**

| 项目 | 实现 |
|---|---|
| 封装 | `Package_SO:SOIC-16_3.9x9.9mm_P1.27mm`（SOP-16，1.27 mm 脚距） |
| 供电方案 | **外部 3.3 V 激励，不用片内稳压**：VSUP(1)=AVDD(3)=DVDD(16)=3V3 |
| 内部稳压禁用 | VFB(4)=GND、BASE(2)=NC、VBG(6) 仅挂 C14 100 nF 到 GND（基准旁路，不外接分压） |
| 时钟 | XI(14)=GND（片内振荡器）、XO(13)=NC |
| 速率 | RATE(15)=GND → **10 SPS** |
| 通道 B | INB+(10)/INB−(9) 接地（不用） |
| 去耦 | AVDD：C11 100 nF + C12 1 µF；DVDD：C15 100 nF（均在 HX711 旁） |
| 输入滤波 | R25/R26 **1 kΩ 串联** + C16 **100 nF 差分**（A+/A−），滤后接 INA+(8)/INA−(7) |
| 数字 | DOUT(12)→GPIO4（R5 10 k 下拉）、PD_SCK(11)→GPIO5 |
| 激励 | E+ = 3V3、E− = GND，经 J3 送到传感器 |

### 3.1 测试点清单（TP1–TP6，`TestPoint:TestPoint_Pad_D1.5mm`）

| 测试点 | 网络 | 位置（PCB, mm） | 用途 |
|---|---|---|---|
| TP1 | `3V3`（AVDD） | (30.0, 5.0) | 模拟电源 / 激励电压 |
| TP2 | `GND`（AGND） | (28.0, 11.0) | 模拟地参考（差分测量用） |
| TP3 | `HX_A_P`（滤波后 INA+） | (43.0, 18.0) | 桥路正输出 |
| TP4 | `HX_A_N`（滤波后 INA−） | (44.0, 19.0) | 桥路负输出 |
| TP5 | `HX_DOUT` | (25.0, 4.0) | 数据/就绪 |
| TP6 | `HX_PD_SCK` | (25.0, -2.0) | 时钟 |

> 标定建议：TP3/TP4 差分 + TP1/TP2 可四线测激励；A+/A− 走线在 R25/R26→INA± 段**等长、成对、包地**。

### 3.2 HX711 的 PCB 隔离（初稿已按此摆放）

- 传感器座 **J3 距 HX711 12.0 mm**（同一区域，走线短）。
- HX711 位于**板右侧**，距 USB-C **56.6 mm**、距 TP4056 **44.4 mm**、距 LDO 62.7 mm、距最近 RGB（D2）**28.2 mm**，
  远离 ESP32 天线端（U1 天线朝后缘）。
- **地平面连续性**：初稿未做分割，PCB 上只有一个 `GND` 网络（无模拟/数字地分割、无地缝）；
  B.Cu 整片 GND 覆铜列为下一步（见 §8）。这是有意的选择：HX711 在 10 SPS 下对地平面分割不敏感，
  分割反而容易被 USB/充电回流切割，**连续地平面 + 器件分区**更稳。

---

## 4. PCB 初稿

### 4.1 板框（与机械模型一致）

由 `mechanical/square_v1/cad/square_model.py::make_pcb()` 复现（未修改 mechanical 任何文件）：

- 外框 93.2 × 93.2 mm，四角 **R6**，`Edge.Cuts` 由 16 段直线 + 4 段真圆弧闭合
- 中央 **38 × 38** 方孔
- 前缘 **80° C 口**（270°±40°，切到中央方孔，形成 C 环）
- 安装孔 4 × **Ø2.2（M2）** 于 (±40, ±24)（机械模型为 Ø2.4；标准 M2 间隙孔取 2.2，见 §8）
- 2 层（F.Cu / B.Cu），板厚 1.6 mm

### 4.2 主要器件放置（KiCad 坐标，mm，Y 向下 = 机械 -Y）

| 器件 | 位置 | 说明 |
|---|---|---|
| J1 USB-C 16P | (0, -41.0) | 后缘正中，口朝板外 |
| U1 ESP32-S3-MINI-1 | (29.0, -35.8) | 后右，**天线端朝后缘**（footprint 自带 Antenna keepout） |
| U2 HX711 | (39.0, 0) | 右侧，远离充电/USB/LED |
| J3 传感器座 | (39.5, 12) | HX711 下方 12 mm |
| J2 电池 JST-PH | (-34, -25) | 后左 |
| U3 TP4056 | (13, -36) | 紧邻 USB-C |
| U4 DW01A / U5 FS8205A | (-24,-33) / (-30,-38) | 靠电池 |
| U6 ME6211（LDO） | (-13, -35) | 靠 USB-C / 电池 |
| J4 OLED 4P | (-28.5, 20) | 前左（C 口内是屏模组，见 §7） |
| J5 按键座 | (24, 21) | 前右，靠近按键 x=17 的走线出口 |
| D1 / D2 RGB | (-32, -7) / (31, 27) | halo，分别靠左右前臂 |
| TP1–TP6 | 见 §3.1 | HX711 周边 |

**"OLED 前左、按键 x=17"的处理**：B 版设计的屏（x −27…11）与按键（x=17）都落在 C 环的**缺口里**，
板上没有铜——这一点与 `square_model.py` 现版（OLED_X=27 / BTN_X=5，仍是 A 版参数）也不一致。
因此 PCB 上放的是**屏/按键的连接器**（J4/J5，模组固定在前壳、软线进板），并在 §7 列为机械-电气待确认项。

### 4.3 DRC 结果

```
kicad-cli pcb drc --severity-all --units mm
→ Found 44 DRC violations  (0 error, 44 warning：30 silk_overlap + 14 silk_over_copper)
→ Found 186 unconnected items
```

| 类别 | 数量 | 严重度 | 说明 |
|---|---|---|---|
| 未连接（ratsnest） | **186** | error（DRC 单列） | **未布线**（本初稿不做布线），每网络 (N−1) 条 |
| 丝印重叠 / 压焊盘 | 44 | warning | 位号自动摆放导致，属外观问题（KiCad 默认即 warning） |
| 短路 / 间距 / 焊盘越界 / courtyard / 焊盘桥连 | **0** | — | 已逐项修掉（含 SOIC 旋转后焊盘角度、天线 keepout 坐标、C 环内边界） |

补充自检（`check_pcb.py`，shapely）：70 个 footprint 的焊盘**全部在 C 环板内**，**courtyard 两两不重叠**。

> 注意：DRC 里 `unconnected_items` 单独计数，不计入 44 条 violations。**布线后必须复跑 DRC 到 0。**

---

## 5. BOM

`BOM.csv`：**33 行 / 66 器件**（4 个 M2 安装孔为机械件，不计入 BOM；TP1–TP6 为板上焊盘测试点，计入）。
关键料：ESP32-S3-MINI-1-N8R2、HX711(SOP-16)、TP4056(ESOP-8)、DW01A、FS8205A、ME6211C33M5G、
USBLC6-2SC6、HRO TYPE-C-31-M-12、JST-PH / JST-SH、5050 共阳 RGB、2N7002。

---

## 6. 已知缺口 / 未完成项（按优先级）

1. **没有布线**（186 未连接）。下一步：先布 HX711 模拟段（A± 等长包地）与电源，再布 USB 差分对，最后 GND 覆铜。
2. **没有覆铜**。B.Cu 整片 GND、F.Cu 局部 GND 需在 pcbnew 里灌铜；本环境 `kicad-cli` 无 zone fill 命令，
   故 `.kicad_pcb` 内没有 zone（不写未灌铜的 zone 以免 DRC 误判）。
3. **ESP32-S3-MINI-1 封装**：KiCad 9.0.9 官方库只有 `ESP32-S2-MINI-1` / `ESP32-C6-MINI-1` / `WROOM`，
   没有 S3-MINI-1。初稿借用 `RF_Module:ESP32-S2-MINI-1`（20×15.4 mm、65 pad，其库描述本身就引用
   ESP32-S3-MINI-1 数据手册，MINI-1 系列共板）。**打样前必须按 Espressif 官方 footprint 核对/替换**（标记 PROVISIONAL）。
4. **机械-电气冲突（需要拍板）**：B 版屏（x −27…11）与按键（x=17）在 C 口缺口内，板上无铜；
   现 `square_model.py` 仍是 A 版参数（OLED_X=27、BTN_X=5）。两条路：① 屏/键固定前壳 + 软线（本稿假设）；
   ② 机械加"舌板"让屏/键上板（需改板框与结构）。
5. **OLED 模组引脚顺序**未定（GND/VCC/SCL/SDA 各家不同），J4 按 GND-3V3-SCL-SDA 定义，采购后必须核对。
6. **FS8205A 引脚定义**（1=S1,2=G1,3=S2,4=G2,5-8=D）按常见规格书写，采购件需复核；错了会反接保护管。
7. **电池保护冗余**：J2 接"带保护板"的电芯时，板载 DW01A+8205A 是二次保护；如需省成本可 DNP（要加跳线/0 Ω）。
8. **TP4056 无温度检测**（TEMP 接地）、**无充电状态灯**（CHRG/STDBY 悬空）——B 版外壳无窗口，符合预期。
9. **未做**：电源完整性/压降核算、ESR/纹波、EMC 预审、热（TP4056 500 mA 时 ESOP 散热）、
   `kicad-cli pcb drc --schematic-parity`（板由脚本独立生成，网络名无 `/` 前缀，parity 报 net_conflict，属工具链限制，未作为验收项）。
10. **未做实物验证**：灵敏度、温漂、回差、续航均需打样后标定（AGENTS.md §7）。

---

## 7. 与输入文档的一致性

| 输入 | 状态 |
|---|---|
| `electronics/pinmap.md` §2 引脚表 | 全部落实（含 EN/BOOT、USB D±、电池分压） |
| `pinmap.md` §1 电源树 | 落实；**未加升压**、**未加 USB 供电路径**（与 V1 决定一致），系统始终由电池经 LDO 供电 |
| `pinmap.md` §3 器件表 | 落实；OLED/按键改为"模组在前壳 + 板载连接器"（见 §6.4） |
| `pinmap.md` §1 HX711 外部 3.3 V 方案 | 落实（§3） |
| B 版设计文档 §8 机械改动 | 未改 mechanical；B 版尺寸（窗 26×7 @x=−8、键 @x=17、C 口 40 mm）**尚未进入 CAD**，本 PCB 按现板框设计并标注冲突 |
| `ref/HX711 数据手册` | VSUP/AVDD/DVDD、VFB、BASE、XI、RATE、VBG 均按手册 |

---

## 8. 下一步（建议顺序）

1. 拍板 §6.4（屏/键上板 or 前壳），据此改板框/连接器位置 —— 需要机械侧同步。
2. 换成官方 ESP32-S3-MINI-1 footprint，复核 FS8205A / OLED 引脚序。
3. 布线：HX711 模拟段（包地、等长）→ 电源（VBUS/VBAT/3V3 加宽 0.6–1.0 mm）→ USB 差分（90 Ω）→ 其余。
4. B.Cu 整片 GND + F.Cu 补铜；复跑 DRC 到 0 error / 0 unconnected。
5. 生成 Gerber/钻孔/贴片文件前，做一次人工 review（本稿未出制造文件）。
