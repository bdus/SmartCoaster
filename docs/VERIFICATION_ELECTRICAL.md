# 电路工程验证矩阵（VERIFICATION_ELECTRICAL）

> 目的：回答 **“电路工程到底验证了什么、还差什么”**。把 `docs/01` 的电气验证清单（§9 电气验证 + §13.3 S2 电路仿真）与 `docs/02 PRD` §5 电路需求逐项映射到可复核证据。
> 日期：2026-11-04 · 基线：HEAD `eaf2a95` + 本轮（S2 套件、R3/R4 2.2k、文档校准）
> 配套：[S2_CIRCUIT_SIM.md](S2_CIRCUIT_SIM.md)（28 个 ngspice 结果）· [REVIEW_ELECTRICAL.md](REVIEW_ELECTRICAL.md)（PCB 电气评审）· [VERIFY_REPORT.md](VERIFY_REPORT.md)（独立验收）

---

## 0. 一句话结论

电路工程现在有 **四层证据**：
1. **设计正确性**：design.py = 唯一来源 → 网表逐引脚 PASS、ERC 0/0；
2. **可制造性**：2 层 PCB 0 DRC / 0 unconnected、Gerber/钻孔/坐标、JLC 2 层 DFM 5/5 PASS；
3. **电气性能（模型级）**：S2 四模块 × 六类分析 → 28 个结果（21 PASS / 7 个真实发现）；
4. **PCB 电气评审**：电源完整性/接地/模拟/USB/热/保护/RF → PASS 5 / PARTIAL 5 / 未关闭风险 3。

**剩余缺口只有两类**：① 实物上板测量（噪声/温漂/热/I2C 波形/续航/充电曲线）；② 由 S2/评审发现的结构性整改（模拟前端占空、GND 铺铜、铝顶板天线、TP4056 热）。均已在 `REVIEW_ELECTRICAL.md` §12 与 `REPORT_技术报告.md` §7 登记。

---

## 1. 设计正确性验证

| 检查 | 方法 | 结果 | 证据 |
|---|---|---|---|
| 网表与设计一致 | `verify.py`：kicad-cli 导网表 ↔ design.py 逐引脚 | **PASS**（43 器件 / 28 网络 / 66 网络节点） | `build/smartcoaster.net.xml`、终端 `RESULT: PASS` |
| ERC | `kicad-cli sch erc --severity-all` | **0 error / 0 warning** | `build/ERC.rpt` |
| 器件位号/值 | design.py → sch/BOM/PCB 三方一致（含 R3/R4=2.2k） | **PASS** | `BOM.csv`、`smartcoaster_2l.kicad_pcb`、`build/gerbers/smartcoaster_2l.pos` |
| 连接完整性 | `kicad-cli pcb drc --severity-all` | **0 violation / 0 unconnected** | `build/DRC_2l.rpt` |
| 可制造性 | `dfm_check.py`（JLC 2 层） | **5/5 PASS**（线宽 0.2、孔 0.3/0.6、环宽 0.15、边 0.3、层数 2） | `build/DFM.md` |

## 2. S2 电路仿真（docs/01 §13.3：四模块 × 六类分析）

> 入口：`simulation/electronics/run_s2.py`（ngspice-36，seed=20261104，全量 ≈8 s）。全部为**行为级模型**，不是芯片级。

| 模块 | .op | .dc | .ac | .tran | .noise | 蒙特卡洛 | 结论 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 惠斯通电桥 | ✅ | ✅ | — | — | — | ✅ 200× | 5 kg=3.96 mV、CM 1.65 V、桥流 3.3 mA；0.1% 失配 max 3.82 mV < ±12.89 mV（tare 必须） |
| HX711 前端 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 200× | 增益 128.00、饱和 ±12.8906 mV、噪声 54.7 nVrms≈0.069 g、τ=15.9 ms、稳定 111 ms；外部 RC **530.5 Hz** |
| 电源 | ✅ | ✅ | — | ✅ | — | — | TP4056 CC 0.5 A/CV 4.12–4.18 V；LDO 88.8%@300 mA、负载阶跃 22.4 mV；**功耗 5.02 mA→4.15 天（未达 7 天）** |
| MCU 接口 | ✅ | ✅ | — | ✅ | — | ✅ 200× | EN τ=10.05 ms；分压 21 µA/±1% max 39.8 mV；**I2C 4.7k 超时→已改 2.2k**；漏流风险 20–100 mV |

**结果文件**：`simulation/electronics/results/*.json`（28 个，含 metric/threshold+来源/pass）、`figs/*.png`（15 张）。
**图**：`../simulation/electronics/figs/`（`bridge_mc_offset.png`、`hx711_noise.png`、`power_budget.png`、`i2c_rise.png` 等）。

## 3. docs/01 §9「电气验证」逐项映射

| # | 要求（docs/01 §9） | 模型级证据 | 结果 | 实物仍需 |
|---|---|---|---|---|
| 1 | **电源电压** | S2：LDO 3.275–3.300 V（Vin 3.4–3.7 V，1–500 mA）；TP4056 CV 4.12–4.18 V | PASS（模型） | 万用表测 3V3/VBAT/VBUS 实际值；低电量+BLE 峰值时 3V3 跌落 |
| 2 | **电源电流/功耗** | S2 `power_budget`：5.02 mA 平均、4.15 天；LDO/LED/BLE 分项 | **FAIL 7 天目标**（真实发现）；模型 PASS（明细） | 电流表测 5 状态；与 5.02 mA 对比 |
| 3 | **传感器采集噪声** | S2 `hx711_noise`：54.7 nVrms → 0.069 g rms（HX711 50 + RC 22.2） | PASS（模型） | 500 g 静置 60 s 记录 SD；充电/BLE 时地噪声（REVIEW EL-02） |
| 4 | **ADC 稳定性/精度** | 桥路 MC（0.1%→σ0.97 mV）；分压 ±1% max 39.8 mV；漏流分析 | PARTIAL | 24-bit 计数漂移、零点/量程标定、温漂；分压漏流实测（EL-13） |
| 5 | **OLED 工作状态** | I2C 时序仿真（修复后 400 kHz 可过 ≤150 pF）；EN 时序 | PASS（接口级） | 上板 I2C 波形（tr）、显示完整/刷新/对比度；模块总线电容实测 |
| 6 | **BLE 通信** | 无 SPICE；电气/射频在 REVIEW §9（天线金属顶板风险） | PARTIAL（无 RF 仿真） | BLE 连接/距离/断线重连；RF 实测（REVIEW EL-03） |
| 7 | **低功耗表现** | S2 `power_budget`（同 #2） | **FAIL（4.15 天）**；方案：模拟前端 50% 占空→7.95 天 | 实测睡眠/广播/连接电流；占空策略实测 |

**结论**：docs/01 §9 电气验证在**模型级**已覆盖 1–5、7（#2/#7 暴露真实缺口），#6 的 RF 只能实物；共 **5 项模型 PASS/PARTIAL + 2 项模型 FAIL→已量化整改方案**。

## 4. PRD §5 电路需求映射

| PRD 条目 | 实现 | 验证 | 状态 |
|---|---|---|---|
| §5.1 系统组成（ESP32-S3/HX711/OLED/按键/BLE/USB-C/电池） | 43 器件原理图 | ERC 0/0、网表 PASS、2 层 PCB 0/0 | PASS |
| §5.2 HY928D 电气参数（5 kg/1.2 mV/V/1 kΩ/3–10 V 激励） | HX711 外部 3.3 V 激励 | S2 桥路（3.96 mV、3.3 mA、CM 1.65 V、占 FS 30.7%） | PASS（模型）；**供应商/实物确认仍开放（M2-04/05）** |
| §5.3 HX711（输入接法/激励/PGA/速率/噪声/布局） | gain 128、10 Hz、外部 3.3 V | S2 前端（增益/饱和/噪声/滤波）；REVIEW 模拟布局 | PASS（模型）；实物噪声/INL 待测 |
| §5.4 电源与电池（充电/保护/供电域/待机/电量/低电提示） | TP4056 + DW01A+FS8205A + ME6211 + 分压 | S2 电源（CC/CV/热/纹波/预算）；REVIEW 保护/load-sharing | PARTIAL：**续航未达标**、无低电提示、load-sharing 缺失 |
| §5.2 桥路/引线未确认 | 设计按全桥 1.2 mV/V | — | **GAP（供应商确认）** |

## 5. 本轮由验证触发的修改

| 改动 | 原因 | 证据 |
|---|---|---|
| R3/R4 4.7k → **2.2k** | S2 `i2c_rise`：4.7k@100pF=398 ns > 300 ns（400 kHz 快模式） | `design.py`、`BOM.csv`、`smartcoaster_2l.kicad_pcb`、`build/gerbers/smartcoaster_2l.pos`；ERC/DRC 重跑 0/0 |
| `docs/08` 重写 | S2 `power_budget`：漏算桥路 3.3 mA，实际 5.02 mA→4.15 天 | `docs/08_Power_Sleep_Plan.md` |
| `docs/01 §13.3`、旧 `electronics/simulation/README` 更正 | 真实外部 RC=530.5 Hz（旧 1.65 kHz 错） | `hx711_ac.json` |
| 产品叙事/README/路线图续航口径 | 不能把 4.2 天写成 7 天 | 见各文档 “2026-11-04” 注记 |

## 6. 仍未关闭（按优先级）

| 编号 | 缺口 | 下一步 |
|---|---|---|
| E-01 | **续航 4.15 天 < 7 天** | 固件模拟前端占空（PD_SCK 断电突发采样）或 1000 mAh；实测复核 |
| E-02 | 模拟地与充电/BLE 回流共用细走线（无铺铜） | 下一版双面 GND 铺铜 + 缝合孔；手板充电中测 HX711 漂移 |
| E-03 | 铝顶板在天线上方 ~5.9 mm（CMF 与机械材质矛盾） | 确认材质；铝→开天线窗/移位；BLE 距离实测 |
| E-04 | TP4056 深放 1.0 W、θJA≈120 °C/W → 热调节到 ~0.33 A | 实测充电温度；必要时 Rprog→3.0–3.6k 或铺铜 |
| E-05 | LDO 低电量+峰值电流可能跌出稳压（口径冲突） | 确认 ME6211 dropout 规格；实测 3.3 V 跌落 |
| E-06 | 分压 50 kΩ 源阻抗 + ADC 漏流误差 20–100 mV | 手板校准/实测漏流；或降阻抗到 47k/47k |
| E-07 | HY928D 桥路/灵敏度/引线未供应商确认 | M2 关闭前置（PRD M2-04/05） |
| E-08 | 无 BLE/EMC/RF 仿真与实测 | 手板 BLE 距离/重连测试；下一版铺铜改善 EMC |

> 边界：S2 全部为**行为级模型**（HX711/TP4056/ME6211/DW01A 无公开芯片级 SPICE），仿真通过 ≠ 实物通过；以上“PASS（模型）”只代表量级/趋势/接口裕量成立，最终以手板 11 项测试（`docs/05` §3）为准。
