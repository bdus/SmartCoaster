# S2 电路仿真报告（SmartCoaster V1 / B 版）

> 日期：2026-11-04 · HEAD `eaf2a95` · 工具：本地 **ngspice-36** + `/data/Documents/tools/sim-venv/bin/python`
> 入口：`simulation/electronics/run_s2.py` · 结果：`simulation/electronics/results/*.json`（28 个 + summary）
> 随机种子：`20261104`（所有蒙特卡洛固定）· 复跑时间：约 8 s
> 本报告回答用户提出的 **"电路工程的仿真和验证"**：把 S2 从审计的 **PARTIAL** 补齐为
> **四模块 × 六类分析可复跑**，并如实列出发现的设计问题。
>
> **Lead 后续动作（2026-11-04 21:15 追加，已执行）**：① I2C 已按 §4 建议把 R3/R4 由 4.7k 改 **2.2k**（同封装，无布局变化），并重跑 ERC/DRC/BOM/Gerber；② `docs/08` 已按 §4 的功耗发现重写（补桥路 3.3 mA、5.02 mA→4.2 天、7 天方案）；③ `docs/01 §13.3` 与旧 `electronics/simulation/README.md` 的 1.65 kHz 口径已更正为 530.5 Hz；④ TP4056 热、LDO dropout、电池分压漏流列为手板必测/下一版整改（见 `docs/REVIEW_ELECTRICAL.md` EL-07/EL-11/EL-13）。本报告的 PASS/FAIL 与原始 JSON 未改动。

## 0. 证据一览

| 项 | 值 |
|---|---|
| 结果 JSON | 28 个分析 + `results/s2_summary.json`（含全部指标/阈值/来源） |
| 判定 | **21 PASS / 7 FAIL**（7 个 FAIL 均为真实设计问题或压力工况，见 §4） |
| 图 | `simulation/electronics/figs/` 15 张 |
| 可复跑 | `cd 项目根 && /data/Documents/tools/sim-venv/bin/python simulation/electronics/run_s2.py` |
| 模型 | `simulation/electronics/models/*.lib`（**全部行为级，文件头已标注非芯片级**） |
| 旧版 | `electronics/simulation/` 保留为历史；存在口径差异（见 §4.7） |
| 未做 | 未改任何硬件值、未 commit、未把文件传第三方、未装新工具 |

## 1. 方法与边界

### 1.1 方法

```
Python 生成参数化网表 (.cir)
   → ~/.local/bin/ngspice -b （.op/.dc/.ac/.tran/.noise + 控制块 alter 循环）
   → 解析 wrdata/print/meas
   → results/*.json + figs/*.png + 终端 PASS/FAIL
```

- 每个结果 JSON 统一字段：`module / analysis / inputs / metrics / thresholds(with source) / pass / notes / ngspice_version`。
- 阈值来源逐条写进 JSON 的 `thresholds[].source`；本报告 §5 汇总。
- 随机种子固定，MC 可复现；每次重跑覆盖旧结果，无隐藏状态。

### 1.2 边界（重要）

- **行为级 ≠ 芯片级**：HX711 / TP4056 / ME6211 / DW01A 没有可用的公开芯片级 SPICE 模型；
  本套件只验证**信号链量级、滤波、噪声预算、功耗包线、接口时序趋势**。
- **仿真通过 ≠ 实物通过**：噪声、温漂、回差、I2C 实际波形、充电热行为、电池内阻都必须上板实测；
  最终灵敏度/温漂/回差按 AGENTS.md §7 仍需实物标定。
- **未改硬件**：所有整改建议仅为建议，是否改 BOM/固件由 Lead/用户决定。
- 行为模型里明确标注的 ASSUMPTION：TP4056 θJA≈120 °C/W 与热调节 120 °C、电池 Rint=0.1 Ω、
  I2C 总线电容 100/200 pF、ESP32-S3 ADC 12 dB 满量程≈3.1 V、ADC 漏流 0–1 µA、
  ESP32-S3 EN 内部 45 kΩ 上拉、BLE 脉冲 100 mA。

## 2. 四个模块的模型

| 模型文件 | 内容 | 不包含 |
|---|---|---|
| `models/hx711_amp.lib` | gain 128、±12.89 mV@3.3 V、10 Hz 单极点输出滤波、0–3.3 V 饱和代理 | INL、失调温漂、1/f、50/60 Hz 数字陷波、内部时钟/稳压 |
| `models/ldo_me6211.lib` | 3.3 V、500 mA、RDO=0.333 Ω（100 mV@300 mA 口径）、Iq 40 µA | 环路稳定性、限流折返、真实 PSRR 频响 |
| `models/charger_tp4056.lib` | CC 500 mA / CV 4.2 V / C/10 终止的行为包线 | 热折返瞬态、定时器、再充电、软启动 |
| `models/protect_dw01_fs8205.lib` | 过充 4.3 V / 过放 2.5 V 平滑理想开关（Ron 25 mΩ） | 过流锁存/延时/释放滞环、CS 检测细节 |
| `models/battery.lib` | 单节 LiPo Thevenin（Voc+Rint），可选参数 | SoC 表、老化、温度 |

## 3. 分析结果总表

> 判定列：PASS/FAIL 是**该分析项在给定阈值下**的结果；FAIL 的说明见 §4。
> 表中"阈值来源"缩写：HX=HX711 手册转录、HY=HY928D 图纸转录、I2C=NXP UM10204、ES=ESP32-S3 数据手册、BOM/08=本地文件。

### 3.1 惠斯通电桥（HY928D）

| 分析 | 关键指标 | 阈值 | 来源 | 判定 |
|---|---|---|---|---|
| `.op` 0/5 kg | 5 kg 输出 **3.960 mV**；CM **1.650 V**；桥流 **3.30 mA**；占 HX711 FS **30.7%** | 3.96±1%；CM 1.2–2.0 V；桥流 3.3±10% | HY；HX | PASS |
| `.dc` 0–5 kg | 灵敏度 **0.792 mV/kg**；非线性 **0%FS**（理想模型） | 非线性 ≤0.05%FS | HY | PASS |
| 失配 0.1%（单臂/最坏） | 失调 −0.825 / **+3.30 mV** | ≤±12.89 mV | HX | PASS |
| 失配 1%（单臂/最坏） | −8.21 / **+33.0 mV**（256% FS） | ≤±12.89 mV | HX | 单臂 PASS；**最坏 FAIL（压力工况）** |
| MC 200×0.1% | 均值 −0.046 mV，σ=0.966 mV，max 2.36 mV，超量程 **0/200** | 无样本超 ±12.89 mV | HX | PASS |
| MC 200×0.1%+零点规格 | σ=1.576 mV，max **3.82 mV**，0/200 超量程 | 同上；零点 ±0.6 mV/V=±1.98 mV | HX；HY | PASS |
| MC 200×1% | σ=9.36 mV，max **27.8 mV**，**41/200（20.5%）超量程** | 同上 | HX | **FAIL（压力工况）** |
| MC 200×5 kg 灵敏度 | FS 1.52–6.66 mV（含失配尾部），200/200 在 ±12.89 mV 内 | ≤±12.89 mV | HX | PASS |

**结论**：
1. 5 kg 只用 HX711 量程的 **30.7%**（±12.89 mV），信号链量级成立；4.8 mA 桥路+HX711 电流也核对为 3.3 mA 桥流。
2. 0.1% 四臂失配（MC 200 次）σ≈1 mV、最坏 3.3 mV；叠加传感器自身零点 ±1.98 mV 后 max 3.82 mV，
   **不会超 HX711 输入范围**。但零点会吃掉约 15–30% 的动态范围，**tare（零点标定）必须做**，
   且 HX711 手册 §14 明确"每颗传感器零点不同"。
3. **1% 四臂失配是压力工况**：密封的 HY928D 内部应变片不是板上 1% 电阻，量产边界是手册零点
   ±0.6 mV/V；但若未来改用未修调的离散桥臂，MC 显示 20.5% 会超量程 → 必须在来料/标定端控制。

### 3.2 HX711 前端（行为模型）

| 分析 | 关键指标 | 阈值 | 来源 | 判定 |
|---|---|---|---|---|
| `.op` | 输出代理中点 1.650 V，无饱和 | 1.65±0.01 V | 行为模型定义 | PASS |
| `.dc` ±15 mV | 增益 **128.00**；饱和 **±12.8906 mV**；线性 0%FS | 128±1%；±12.89 mV±1% | HX | PASS |
| `.ac` | DC 增益 42.14 dB（128）；外部 RC −3 dB=**530.5 Hz**；50 Hz 总衰减 **−14.18 dB**（外部 RC 仅 −0.04 dB） | 增益 128±1%；RC 截止 ≥100 Hz；50 Hz ≤−10 dB | HX；项目设计规则 | PASS |
| `.tran` | 1 mV 阶跃：τ=15.90 ms；10–90%=34.9 ms；0.1% 稳定 **111 ms** | ≤400 ms（单极点模型乐观） | HX | PASS |
| `.noise` | 输入 **54.7 nVrms** = HX711 50 + 外部 RC **22.19**；输出 7.00 µVrms；折合 **0.069 g rms** | RC ≤30 nVrms；总 ≤60 nVrms；重量噪声 ≤0.1 g rms | HX；设计规则 | PASS |
| MC 200×R/C | 截止 480.3–590.9 Hz（σ=32.2 Hz）；增益 128.000（σ≈7e-5） | 截止 ≥100 Hz | 设计规则 | PASS |

**结论**：
- 噪声预算成立：HX711 自身 50 nVrms 为主，外部 3 kΩ+100 nF 网络贡献 22.2 nVrms（功率占 16%），
  总 54.7 nVrms ≈ **0.069 g rms**（峰峰约 0.46 g），相对 1 g 分辨率目标有 ~10 倍余量。
- HX711 数据手册 400 ms 稳定时间来自数字滤波器；行为的 10 Hz 单极点只给出 111 ms，
  **是乐观近似** → 固件必须按手册 ≥400–500 ms 等待，不要按仿真值缩短。
- 外部 RC 实际截止 **530 Hz**，不是旧文档的 1.65 kHz（旧网表漏了 R25/R26 的 1 k，见 §4.7）。

### 3.3 电源

| 分析 | 关键指标 | 阈值 | 来源 | 判定 |
|---|---|---|---|---|
| TP4056 `.dc`（5 V→3.0–4.2 V） | CC **0.500 A**；CV 起 4.12 V、终止 4.18 V；Pmax=**1.0 W**@3.0 V；3.0 V 效率 60% | CC 0.5±5%；Iterm≤50 mA；4.2 V | BOM；TP4056 手册 | PASS |
| TP4056 热 | θJA=120 °C/W：Tj=**145/160/180 °C**@Tamb 25/40/60；热调节需把电流降到 **~0.333 A** | Tj ≤120 °C（热调节门限） | TP4056 手册（ASSUMPTION） | **FAIL** |
| ME6211 `.dc` | Vin=3.7 V：1–500 mA 输出 **3.275–3.300 V**；η=88.8%@300 mA；Vin=3.4 V/500 mA 时 3.209 V（进入 dropout） | 3.3±2%；500 mA | ME6211 手册；BOM | PASS |
| LDO 压差敏感性 | 若按厂商网页"100 mV@100 mA"（≈1 Ω），Vin=3.4 V/500 mA → **2.879 V** | ≥3.0 V（ESP32-S3） | ES | **FAIL（口径冲突）** |
| LDO 负载阶跃 `.tran` | 基线 3.300 V；OLED 12 mA 跌落 **2.4 mV**；BLE 100 mA 脉冲跌落 **22.4 mV**；p-p 22.4 mV | 3.0–3.6 V；纹波 ≤100 mV | ES；设计规则 | PASS |
| 电池+保护 `.dc` | 500 mA 端压 **3.6375 V**，sag **62.5 mV**；LDO 输入余量 172.5 mV | sag ≤100 mV | 假设 Rint 0.1+25 mΩ | PASS |
| 保护门限 `.dc` | 过放检出 **2.48 V**、过充检出 **4.34 V**（10 mV 平滑过渡 + 0.1 Ω 内阻导致偏移） | 4.30±0.10 / 2.50±0.10 V | task-10；DW01A 手册 | PASS |
| 功耗预算 | 平均 **5.019 mA** → 500 mAh **4.15 天**；目标 ≤3 mA/7 天 | ≤3 mA；≥7 天 | docs/08 | **FAIL（核心发现）** |

**结论**：
- 充电 CC/CV 功能包线成立；但**深放（3.0 V）@500 mA 耗散 1.0 W**，2 层板无专铜时 θJA~120 °C/W，
  结温会超过 TP4056 的 ~120 °C 热调节点 → 芯片会**自动折返电流**（约 0.33 A），
  充电时间变长但一般不会损坏（另有 ~150 °C 热关断兜底）。建议：Rprog 改 ~3.0–3.6 k
  （330–400 mA）、ESOP 焊盘下加铜/过孔、或接受折返并在 bring-up 测温。
- LDO 在 3.7 V 标称下 1–500 mA 全程稳压；但 **dropout 规格冲突**（BOM "100 mV@300 mA" vs
  厂商网页 "100 mV@100 mA"）。按悲观口径，3.4 V 电池 + 500 mA 会掉出稳压；实际系统峰值
  通常 <200 mA，风险主要在电池末端。必须实测 dropout。
- **续航是最大问题**：连续 HX711(1.5 mA) + 桥路(3.3 mA) = 4.8 mA，已经超过 3 mA 目标；
  加其它域平均 5.02 mA → **4.15 天，达不到 7 天**。`docs/08` 与 `docs/design/...` §7 的预算
  只算了 HX711 1.5 mA，**漏掉了桥路激励 3.3 mA**（42 mAh/日估算里少了 ~79 mAh/日）。
  - 场景 A（实测口径连续）：5.02 mA → 4.15 天 ❌
  - 场景 B（模拟前端 50% 占空比、PD_SCK 断电、1 Hz 突发采样）：2.62 mA → **7.95 天** ✅
    （代价：HX711 每次唤醒需等 400 ms，10 Hz 连续更新变为 ~1 Hz）
  - 场景 C（模拟前端 20% 占空比）：1.18 mA → 17.7 天 ✅（更激进）
  - 场景 D（1000 mAh 电池）：5.02 mA → 8.3 天 ✅
  - **建议**：优先做 B（固件改 HX711 断电+突发采样），否则换 1000 mAh 或降低桥路激励。
    这三条都只写建议，未改硬件/固件。

### 3.4 MCU 接口

| 分析 | 关键指标 | 阈值 | 来源 | 判定 |
|---|---|---|---|---|
| I2C `.tran` | 4.7 k+100 pF：**398 ns**；4.7 k+200 pF：796 ns；2.2 k+100 pF：**186 ns**；2.2 k+200 pF：373 ns | 100 kHz ≤1000 ns；400 kHz ≤300 ns | I2C (UM10204) | 100 kHz 全过；**400 kHz 不达标** → **FAIL** |
| EN `.tran` | τ=**10.05 ms**；t(VIH)=**13.91 ms**；t(VIL)=2.93 ms；带内部 45 kΩ 时 τ=8.23 ms、t(VIH)=11.39 ms | 0<t(VIH)≤100 ms；τ≈10 ms | ES；pinmap | PASS |
| 电池分压 `.dc`+MC | 比例 0.500；pin **2.10 V**@4.2 V；分压电流 **21 µA**；R±1% MC 误差 max **39.8 mV** | ADC 0–3.1 V；误差 ≤2%；电流 ≤30 µA | ES（满量程为假设） | PASS |
| 分压漏流 | 0.2/0.5/1 µA → 电池误差 **20/50/100 mV**（1 µA 时 2.4%） | ≤42 mV（1%） | 项目电量计需求；漏流为假设 | **FAIL（未验证风险）** |

**结论**：
- **I2C 400 kHz 不成立**：BOM 是 4.7 k 上拉，即使按乐观 100 pF 总线电容，30–70% 上升时间
  398 ns > Fast-mode 300 ns 上限；200 pF 时 796 ns。**固件当前按 400 kHz 使用**（pinmap 写
  OLED SCL 400 kHz）。整改（二选一，建议 Lead 决定）：
  1. **固件降到 100 kHz**（标准模式，4.7 k/100–200 pF 全过，最省事、不用改板）；或
  2. 把 R3/R4 改 **2.2 k**：100 pF 时 186 ns 过 400 kHz；但 200 pF 仍 373 ns ❌，
     需同时保证实际总线电容 ≤~150 pF（模块+走线），并实测 SDA/SCL 波形与 VOL/IOL。
  建议先测实际总线电容，再决定；在实测前不要把 400 kHz 当已达标。
- EN RC 正常：3V3 上电后约 13.9 ms 释放 EN，且 3V3 上升期间 EN 保持低；复位键把 EN 拉低。
  内部 45 kΩ 上拉是假设，若存在则 ~11.4 ms，仍然安全。
- 电池分压 DC/电阻容差合格；但 **50 kΩ Thevenin + ADC 漏流**是未验证项：0.2 µA 就有 20 mV
  电池误差，1 µA 有 100 mV（2.4%）。C13=100 nF 只帮 SAR 采样，去不掉 DC 漏流。
  建议：实测/校准（用已知电压对比万用表），或改低阻分压（10k/10k 会多耗 ~210 µA，不推荐），
  或加缓冲。当前"100k/100k 足够精确"的假设**不成立到 1% 量级**，必须用标定/实测确认。

## 4. 发现的问题与建议（不改硬件，仅建议）

按影响排序。每条给出证据、影响、建议、以及"仿真能证明/不能证明"。

### 4.1 I2C 400 kHz 时序不达标（P1，功能风险）
- 证据：`results/mcu_i2c_rise.json`：4.7 k/100 pF = 398.2 ns（限 300 ns）；200 pF = 796.5 ns。
  与解析式 0.8473·Rp·C 完全吻合，说明是 RC 物理限制，不是仿真噪声。
- 影响：400 kHz 下上升沿超 Fast-mode 上限，可能造成 OLED 通信偶发错误/初始化失败；
  100 kHz 可正常工作。
- 建议：固件改 100 kHz，或 R3/R4→2.2 k + 控制 Cb≤150 pF；改后实测波形。
- 不能证明：实际总线电容、SSD1306 模块输入电容、上拉电阻精度；需实测。

### 4.2 7 天续航目标不成立（P1，产品指标）
- 证据：`results/power_budget.json`：5.019 mA → 4.15 天；桥路 3.3 mA + HX711 1.5 mA = 4.8 mA
  已超 3 mA 目标；docs/08 漏算桥路，docs/design §7 的 42 mAh/日对应 ~1.75 mA，与实测口径差 ~3 倍。
- 影响：按当前"连续采样"策略，500 mAh 只能撑 ~4 天，不是 7–12 天。
- 建议：模拟前端突发采样（PD_SCK 断电），50% 占空比 → 7.95 天；或 1000 mAh 电池（8.3 天）；
  或降低桥路激励（牺牲灵敏度）。需固件配合（HX711 400 ms 稳定等待）。
- 不能证明：实际 ESP32-S3 light sleep/BLE 平均电流、电池实际容量/老化；需实测。

### 4.3 TP4056 深放充电热折返（P1，热/充电时间）
- 证据：`results/tp4056_thermal.json`：Pmax=1.0 W@3.0 V；θJA=120 °C/W → Tj=145 °C@25 °C、
  160 °C@40 °C，超过 ~120 °C 热调节；折返后电流 ~0.333 A。
- 影响：深放后充电变慢；长期高温加速老化；一般不会损坏（热关断 150 °C 兜底），但需要实测。
- 建议：Rprog 2.4 k → ~3.0–3.6 k（330–400 mA）；ESOP 焊盘下铺铜+过孔；或接受折返并在
  bring-up 记录壳温/充电时间。
- 不能证明：真实 θJA（依赖 PCB 铜面积/风冷/外壳）、TP4056 实际热调节门限；必须测温。

### 4.4 桥路零点：在量程内，但 tare 必须做（P1，标定）
- 证据：`results/bridge_mc_*.json`：0.1% 失配 σ=0.97 mV、max 2.36 mV；+零点规格 max 3.82 mV；
  均 <±12.89 mV。1% 压力工况 20.5% 超量程（不是量产边界）。
- 影响：不标定会导致每次上电零点漂移，占 15–30% 动态范围；但不会超 HX711 输入范围。
- 建议：保持每颗传感器零点+满量程标定（HX711 手册 §14 要求）；固件已有稳定窗，需保留 tare。
- 不能证明：实物零点分布/温漂；必须用砝码标定。

### 4.5 HX711 稳定时间：行为模型 111 ms 偏乐观（P2）
- 证据：`results/hx711_tran.json` 111 ms（0.1%）vs 手册 400 ms。
- 建议：固件初始化/换通道后等待 ≥400–500 ms，不要按仿真值缩短。

### 4.6 外部 RC 截止频率与文档不一致（P2，文档口径）
- 证据：实际 BOM R25/R26=1 k、C16=100 nF、桥路 Thevenin 1 k → 3 k/100 nF = **530.5 Hz**；
  旧 `electronics/simulation/README.md` 与 `docs/01 §13.3` 写 1.65 kHz（旧网表用 500 Ω 桥臂且
  漏掉 1 k 输入滤波）。`hx711_ac.json` 记录了两者。
- 影响：530 Hz 仍 ≥50× 10 Hz ODR，功能没问题；但 50 Hz 衰减 −14.2 dB 主要来自 10 Hz ODR 极点，
  外部 RC 只贡献 −0.04 dB，不能把 −14.2 dB 当成 RC 的功劳。
- 建议：Lead 更新 docs/01 §13.3 的"本机状态"和旧 README 的口径（本任务写入范围不含 docs/01，
  未改）；保留旧 `electronics/simulation/` 作为历史。

### 4.7 LDO dropout 规格冲突（P2，选型证据）
- 证据：BOM 注"100 mV@300 mA"（→RDO 0.333 Ω），厂商网页摘要"100 mV@100 mA"（→≈1 Ω）。
  按悲观口径 Vin=3.4 V/500 mA 只有 2.879 V（<3.0 V）。
- 影响：电池末端 + 大负载时可能掉出 3.3 V 稳压；系统峰值通常 <200 mA，风险中等。
- 建议：实测 ME6211 在 100/300/500 mA、Vin 3.3–3.7 V 的 dropout；以实测替换 BOM/网页口径。

### 4.8 电池分压 ADC 漏流风险（P2，精度）
- 证据：`results/mcu_battery_divider_leakage.json`：50 kΩ Thevenin，0.2 µA→20 mV、1 µA→100 mV
  电池电压误差；ESP32-S3 ADC 漏流没有本地数据手册支撑（ASSUMPTION 扫描）。
- 建议：实测（已知电池电压 vs ADC 读数）或出厂校准；不要假设"100k/100k 精度足够"。
- 不能证明：真实 ADC 漏流/输入阻抗；必须实测。

### 4.9 保护门限/系统工作点（P3）
- 证据：`results/battery_protection.json`：模型检出 2.48 V/4.34 V（10 mV 平滑过渡 + 0.1 Ω 内阻
  造成偏移）；系统在 LDO dropout（约 3.1–3.4 V 电池）就先掉压，DW01A 2.5 V 只是最后兜底。
- 建议：bring-up 实测保护板动作点；不要把 DW01A 当系统低压关机。
- 未建模：过流锁存/延时。

## 5. 阈值来源汇总

| 类别 | 阈值 | 来源 |
|---|---|---|
| 传感器 | 3.96 mV FS、1000 Ω、±0.6 mV/V 零点、0.05%FS 非线性 | [`ref/HY928D_5kg_称重传感器_图纸转录.md`](../ref/HY928D_5kg_称重传感器_图纸转录.md) |
| HX711 | ±12.89 mV、50 nVrms、400 ms、CM 1.2–2.0 V、CMRR/PSRR 100 dB | [`ref/HX711_数据手册_海芯.md`](../ref/HX711_数据手册_海芯.md) |
| I2C | 100 kHz tr≤1000 ns；400 kHz tr≤300 ns | [NXP UM10204](https://www.nxp.com/docs/en/user-guide/UM10204.pdf) |
| ESP32-S3 | 3.0–3.6 V；VIH=0.75·VDD、VIL=0.25·VDD | [Espressif ESP32-S3 Datasheet](https://documentation.espressif.com/esp32-s3_datasheet_en.html) |
| ME6211 | 3.3 V±2%、500 mA、100 mV dropout、Iq 40 µA、PSRR 70 dB@1 kHz、50 µVrms | `electronics/kicad/BOM.csv` + [厂商页](http://fanhaiic.com/h-nd-3323.html)（与 BOM 口径冲突已标注） |
| TP4056 | 1200/Rprog、4.2 V CV、C/10、热调节 ~120 °C、θJA ~120 °C/W（ASSUMPTION） | `BOM.csv` + TP4056 常见手册（本仓库未转录） |
| DW01A/FS8205A | 4.3 V/2.5 V、Ron 25 mΩ（ASSUMPTION） | task-10；DW01A 常见手册 |
| 电池/续航 | 500 mAh、3.7 V、≤3 mA/≥7 天 | `electronics/pinmap.md`、[`docs/08_Power_Sleep_Plan.md`](08_Power_Sleep_Plan.md)；Rint 为假设 |
| 设计规则 | 外部 RC ≥10× ODR；3V3 纹波 ≤100 mV；重量噪声 ≤0.1 g rms；分压电流 ≤30 µA | 本套件定义（已在 README §6 写明） |

## 6. 结论：S2 现在处于什么状态

| 审计项 | 之前 | 现在 |
|---|---|---|
| 13.3.1 桥路等效 + 灵敏度量级 | PASS（旧 .dc/.ac） | PASS（+ .dc 扫描 + 失配 + MC 200×4） |
| 13.3.2 HX711 行为前端 | PARTIAL | **PASS**（.op/.dc/.ac/.tran/.noise/MC 全做） |
| 13.3.3 电源 | GAP | **PASS（有 FAIL 发现）**（TP4056/ME6211/电池+保护/功耗预算） |
| 13.3.4 MCU 接口 | GAP | **PASS（有 FAIL 发现）**（I2C/EN/分压+漏流） |
| 13.3.5 分析类型 .op/.dc/.ac/.tran/.noise/MC | PARTIAL | **PASS**（六类全覆盖） |
| 13.3.6 §13.3「本机状态」一致性 | PARTIAL | **已关闭**：Lead 已把 docs/01 §13.3 更新为 530.5 Hz / 28 结果 / 21 PASS，并修正旧 `electronics/simulation/README.md` |

**边界重申**：以上"PASS"仅表示**行为级模型 + 给定阈值**下通过；HX711/TP4056/ME6211/DW01A
没有芯片级 SPICE 模型，**不能**据此声称芯片性能或实物性能已达标。噪声/温漂/热/I2C 波形/
电池内阻必须上板实测。本任务**未修改**任何硬件值、**未 commit**；Lead 随后按 §4 建议改了 R3/R4（4.7k→2.2k）并重跑 ERC/DRC/BOM/Gerber（见顶部“Lead 后续动作”）。

## 7. 复跑与产物

```bash
cd /data/Documents/projects/SmartCoaster
/data/Documents/tools/sim-venv/bin/python simulation/electronics/run_s2.py
# 选择性复跑
/data/Documents/tools/sim-venv/bin/python simulation/electronics/run_s2.py --only bridge
```

- 产物：`simulation/electronics/{netlists,logs,results,figs}/`、`results/s2_summary.json`。
- README（模块/假设/边界/复跑/索引/阈值来源）：[`simulation/electronics/README.md`](../simulation/electronics/README.md)
- 模型：`simulation/electronics/models/*.lib`（文件头均标注"行为级，非芯片级"）
- 本报告写入范围：`docs/S2_CIRCUIT_SIM.md`；未改 `electronics/` 源码/PCB，未 git commit。
