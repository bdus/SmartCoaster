# simulation/electronics/ — S2 电路仿真套件

> 状态：**已建立并可复跑**（2026-11-04，HEAD `eaf2a95`）。
> 工具：本地 **ngspice-36**（`~/.local/bin/ngspice`），Python `/data/Documents/tools/sim-venv/bin/python`
> （numpy/matplotlib）。随机种子固定 `20261104`。
> 入口：`run_s2.py`；汇总报告：[`docs/S2_CIRCUIT_SIM.md`](../../docs/S2_CIRCUIT_SIM.md)。
> 本目录取代 `electronics/simulation/`（旧第一版：仅桥路 + 行为增益，只有 .dc/.ac）；
> 旧版保留为历史证据，不再作为 S2 验收依据。

## 1. 一句话结论

四个模块（惠斯通电桥 / HX711 前端 / 电源 / MCU 接口）× 六类分析
（`.op` / `.dc` / `.ac` / `.tran` / `.noise` / 蒙特卡洛）都有可复跑的 ngspice 结果，
共 **28 个结果：21 PASS / 7 FAIL**。**7 个 FAIL 全部是真实设计问题或"压力工况"，
不是仿真失败**，详见 [`docs/S2_CIRCUIT_SIM.md`](../../docs/S2_CIRCUIT_SIM.md) §4：

| 关键发现 | 结论 |
|---|---|
| **I2C 400 kHz**：4.7 k 上拉 + 100 pF → tr=398 ns > Fast-mode 300 ns | **不达标**；需降速 100 kHz 或改 2.2 k（并控制总线电容） |
| **续航**：连续 HX711 + 桥路 4.8 mA 已超 3 mA 目标；总平均 5.02 mA | **4.2 天 < 7 天**；docs/08 漏算桥路 3.3 mA |
| **TP4056 热**：5 V→3.0 V@500 mA，耗散 1.0 W，θJA=120 °C/W → Tj≈145/160 °C | 会触发 ~120 °C 热调节，充电电流折返到 ~0.33 A；需降流/铺铜 |
| **桥路零点**：0.1% 四臂失配 MC（200 次）σ=0.97 mV、max 2.36 mV；叠加手册零点 ±1.98 mV 后 max 3.82 mV | 在 HX711 ±12.89 mV 内，但 **tare 必须做**；1% 失配压力工况 20.5% 超量程 |
| **HX711 噪声**：HX711 50 nVrms + 外部 RC 22.2 nVrms = 54.7 nVrms | 折合 0.069 g rms（<1 g 目标 10 倍余量）；RC 约占噪声功率 16% |
| **外部 RC 截止频率**：实际 BOM（R25/R26=1 k，C16=100 nF，桥路 1 k）→ **530 Hz** | 旧 README/§13.3 的 **1.65 kHz 与 BOM 不符**；530 Hz 对 10 Hz ODR 仍足够 |
| **电池分压漏电流**：50 kΩ Thevenin，1 µA 漏流 → 电池误差 100 mV（2.4%） | 属未验证风险，需实测/校准 |

> **边界（必须遵守）**：全部模型是**行为级，不是芯片级**；HX711/TP4056/ME6211/DW01A
> 没有可用的公开芯片级 SPICE 模型。**仿真通过 ≠ 实物通过**：噪声、温漂、I2C 实际波形、
> 充电热行为都必须上板实测。本目录**不修改任何硬件值**，整改只以建议形式给出。

## 2. 复跑

```bash
cd /data/Documents/projects/SmartCoaster
/data/Documents/tools/sim-venv/bin/python simulation/electronics/run_s2.py
# 只跑某几个模块（bridge,hx711,power,mcu）
/data/Documents/tools/sim-venv/bin/python simulation/electronics/run_s2.py --only bridge,hx711
```

- 运行时间：约 8 s（含 4 组 200 次桥路 MC、200 次 HX711 RC MC、200 次分压 MC）。
- 产物：`netlists/*.cir`、`logs/*.log`、`results/*.json`、`figs/*.png`；
  中间数据在 `.work/`（可删，`run_s2.py` 会重建）。
- 终端最后打印 PASS/FAIL 表和总数；退出码恒为 0（有 FAIL 时也会打印"FAIL / findings"，
  这是设计问题报告，不是脚本错误）。

## 3. 目录

```
simulation/electronics/
├── run_s2.py                 # 唯一入口：生成网表→跑 ngspice→解析→JSON/图→PASS/FAIL 表
├── README.md                 # 本文件
├── models/
│   ├── hx711_amp.lib         # HX711 行为前端（gain 128、±12.89 mV、10 Hz 单极点、饱和）
│   ├── ldo_me6211.lib        # ME6211 行为 LDO（3.3 V/500 mA/100 mV dropout 口径/40 µA Iq）
│   ├── charger_tp4056.lib    # TP4056 CC/CV 包线 + C/10 终止（无热折返/定时器）
│   ├── protect_dw01_fs8205.lib # DW01A+FS8205A 平滑理想开关（4.3 V/2.5 V）
│   └── battery.lib           # 单节 LiPo Thevenin（Voc+Rint）
├── netlists/                 # run_s2.py 生成的网表（可复跑）
├── logs/                     # ngspice 原始日志（含 .op 打印、.noise 总量）
├── results/                  # 每个分析一个 JSON + s2_summary.json
├── figs/                     # 15 张 PNG
└── .work/                    # 中间 wrdata / MPL 缓存（可删）
```

**模型诚实标注**：所有 `models/*.lib` 文件头都写明"BEHAVIOURAL ONLY / 不是芯片级模型"，
并列出模型包含/不包含什么、参数来源、以及哪些参数是 ASSUMPTION。

## 4. 模块 × 分析覆盖

| 模块 | .op | .dc | .ac | .tran | .noise | 蒙特卡洛 |
|---|---|---|---|---|---|---|
| 惠斯通电桥 | ✅ 0/5 kg 工作点、CM、桥流 | ✅ 0–5 kg 载荷扫描、线性度 | —（桥路无源，无必要） | — | —（RC/噪声放在 HX711） | ✅ 4 组 × 200 次（失调 0.1%/1%、+零点规格、灵敏度） |
| HX711 前端 | ✅ 零点/偏置 | ✅ ±15 mV 输入饱和 | ✅ 10 Hz ODR + 外部 RC、50 Hz | ✅ 1 mV 阶跃稳定 | ✅ 输入/输出等效噪声 | ✅ 200 次 R/C 容差 → 截止频率/增益 |
| 电源 | —（用 .dc 工作包线） | ✅ TP4056 3.0–4.2 V；ME6211 1–500 mA；电池+保护 | — | ✅ 负载阶跃（OLED+BLE 脉冲） | —（LDO 噪声用数据手册 50 µVrms 预算，行为模型不产生可信噪声） | —（无随机参数；用参数扫描/敏感性代替） |
| MCU 接口 | — | ✅ 电池分压 3.0–4.2 V；漏流扫描 | — | ✅ I2C 上升沿；EN 上电 RC | — | ✅ 分压电阻 ±1% × 200 次 |

> 六类分析在四个模块之间是完整覆盖的；"模块 × 六类全矩阵"并非每格都有物理意义
> （例如无源桥路做 `.noise`、纯数字 I2C 做 `.noise`），未做的格子在上面标了原因。

## 5. 结果索引

### 5.1 JSON（`results/`）

| JSON | 模块/分析 | 关键指标 | PASS/FAIL |
|---|---|---|---|
| `bridge_op.json` | 桥路 .op | 5 kg=3.960 mV，CM=1.650 V，桥流 3.30 mA，占 HX711 FS 30.7% | PASS |
| `bridge_dc_load.json` | 桥路 .dc | 灵敏度 0.792 mV/kg，非线性 0%FS | PASS |
| `bridge_mismatch_single_arm_0.1pct.json` | 单臂 0.1% | 失调 −0.825 mV | PASS |
| `bridge_mismatch_worst_0.1pct.json` | 最坏四臂 0.1% | 失调 3.30 mV（25.6% FS） | PASS |
| `bridge_mismatch_single_arm_1pct.json` | 单臂 1% | 失调 −8.21 mV（63.7% FS） | PASS（<12.89） |
| `bridge_mismatch_worst_1pct.json` | 最坏四臂 1% | 失调 33.0 mV（256% FS） | **FAIL**（压力工况，非密封传感器真实公差） |
| `bridge_mc_offset_0p1pct.json` | 桥路 MC 0.1% | σ=0.97 mV，max 2.36 mV，超 12.89 mV：0/200 | PASS |
| `bridge_mc_offset_0p1pct_plus_zero.json` | 0.1% + 零点规格 | σ=1.58 mV，max 3.82 mV，0/200 超量程 | PASS |
| `bridge_mc_offset_1pct.json` | 桥路 MC 1% | σ=9.36 mV，max 27.8 mV，**20.5% 超 ±12.89 mV** | **FAIL**（压力工况） |
| `bridge_mc_sensitivity.json` | 5 kg 灵敏度 MC | 1.52–6.66 mV（含失配尾部），200/200 < 12.89 | PASS |
| `hx711_op.json` | HX711 .op | 输出代理中点 1.650 V | PASS |
| `hx711_dc.json` | HX711 .dc | 增益 128.00，饱和 ±12.8906 mV，线性 0%FS | PASS |
| `hx711_ac.json` | HX711 .ac | 增益 128（42.14 dB）；外部 RC −3 dB=530.5 Hz；50 Hz 总衰减 −14.18 dB | PASS |
| `hx711_tran.json` | HX711 .tran | τ=15.90 ms，10–90% 34.9 ms，0.1% 稳定 111 ms | PASS |
| `hx711_noise.json` | HX711 .noise | 输入 54.7 nVrms（HX711 50 + RC 22.2）；输出 7.00 µVrms；折合 0.069 g rms | PASS |
| `hx711_mc_rc.json` | HX711 R/C MC | 200/200 收敛；截止 480–591 Hz（σ=32 Hz）；增益 128.00 | PASS |
| `tp4056_dc.json` | TP4056 .dc | CC 0.500 A；CV 起 4.12 V、终止 4.18 V；Pmax=1.0 W@3.0 V | PASS |
| `tp4056_thermal.json` | TP4056 热 | Tj(25/40/60 °C, θ=120)=145/160/180 °C；热调节需降流到 0.33 A | **FAIL**（设计风险，见 §4） |
| `ldo_dc.json` | ME6211 .dc | Vin=3.7 V：1–500 mA 稳压 3.275–3.300 V；η=88.8%@300 mA | PASS |
| `ldo_dropout_sensitivity.json` | LDO 压差敏感性 | 悲观口径（1 Ω）Vin=3.4 V/500 mA → 2.879 V | **FAIL**（口径冲突/需实测） |
| `ldo_tran.json` | LDO .tran | 基线 3.300 V；OLED 跌落 2.4 mV；BLE 100 mA 脉冲跌落 22.4 mV | PASS |
| `battery_load.json` | 电池+保护 .dc | 500 mA 时端压 3.6375 V，sag 62.5 mV | PASS |
| `battery_protection.json` | 保护门限 .dc | 过放检出 2.48 V，过充检出 4.34 V（10 mV 平滑过渡） | PASS |
| `power_budget.json` | 功耗预算 | 平均 5.019 mA → 500 mAh **4.15 天**；目标 ≤3 mA/7 天 | **FAIL**（核心发现） |
| `mcu_i2c_rise.json` | I2C .tran | 4.7 k+100 pF：398 ns；4.7 k+200 pF：796 ns；2.2 k+100 pF：186 ns | **FAIL**（400 kHz 不达标，见 §4） |
| `mcu_en_powerup.json` | EN .tran | τ=10.05 ms；t(VIH)=13.9 ms；带内部 45 k 时 11.4 ms | PASS |
| `mcu_battery_divider.json` | 分压 .dc+MC | 比例 0.500，pin 2.10 V@4.2 V，21 µA；R ±1% 误差 max 39.8 mV | PASS |
| `mcu_battery_divider_leakage.json` | 分压漏流 | 0.2/0.5/1 µA → 电池误差 20/50/100 mV | **FAIL**（未验证风险，需实测/校准） |
| `results/s2_summary.json` | 全量汇总 | 21 PASS / 7 FAIL，含 git HEAD、ngspice 版本、seed、全部结果 | — |

> 每个 JSON 都含：`module / analysis / inputs / metrics / thresholds(with source) / pass / notes / ngspice_version`（多数还含 `seed`、`artifacts`）。

### 5.2 图（`figs/`）

| 文件 | 内容 |
|---|---|
| `bridge_dc_load.png` | 桥路 0–5 kg 输出 + 线性拟合残差 |
| `bridge_mc_offset.png` | 200 次 MC 失调分布 vs ±12.89 mV |
| `hx711_dc.png` | 输入 ±15 mV → 输出代理，增益/饱和 |
| `hx711_ac.png` | 全链路与外部 RC 的频响，50 Hz 标记 |
| `hx711_tran.png` | 1 mV 阶跃响应 |
| `hx711_noise.png` | 噪声预算（HX711 / RC / 总） |
| `hx711_mc_rc.png` | 200 次 R/C 容差的截止频率分布 |
| `tp4056_charge.png` | CC/CV 包线 + TP4056 耗散 |
| `ldo_dc.png` | 1–500 mA 负载扫描（3 个 Vin） |
| `power_load_step.png` | 3V3 对 OLED/BLE 负载阶跃的响应 |
| `battery_protection.png` | 保护窗口/负载电流 vs 电池 OCV |
| `power_budget.png` | 各域平均电流 vs 3 mA 目标 |
| `i2c_rise.png` | 4.7 k/2.2 k × 100/200 pF 上升沿 |
| `en_powerup.png` | EN RC 上电时序（含内部 45 k 变体） |
| `battery_divider_mc.png` | 分压电阻 ±1% MC → 推算电池电压误差 |

## 6. 阈值来源（每个 PASS/FAIL 都有出处）

| 阈值 | 值 | 来源 |
|---|---|---|
| HY928D 灵敏度/阻抗/零点/非线性 | 1.2±0.2 mV/V，1000±10 Ω，±0.6 mV/V，0.05%FS | [`ref/HY928D_5kg_称重传感器_图纸转录.md`](../../ref/HY928D_5kg_称重传感器_图纸转录.md) §2/§6 |
| HX711 满量程/噪声/稳定时间/CM/PSRR | ±12.89 mV@3.3 V，50 nVrms，400 ms，1.2–2.0 V，100 dB | [`ref/HX711_数据手册_海芯.md`](../../ref/HX711_数据手册_海芯.md) §5/§6/§7/§10/§14 |
| I2C 上升时间 | Standard ≤1000 ns，Fast ≤300 ns（30–70% VDD） | [NXP UM10204](https://www.nxp.com/docs/en/user-guide/UM10204.pdf) |
| ESP32-S3 供电/IO 门限 | 3.0–3.6 V；VIH=0.75·VDD，VIL=0.25·VDD | [Espressif ESP32-S3 Datasheet](https://documentation.espressif.com/esp32-s3_datasheet_en.html) |
| ME6211 | 3.3 V ±2%，500 mA，100 mV dropout，Iq 40 µA，PSRR 70 dB@1 kHz，50 µVrms | `electronics/kicad/BOM.csv`；[厂商页 fanhaiic.com](http://fanhaiic.com/h-nd-3323.html) |
| TP4056 | Ibat=1200/Rprog，4.2 V CV，Iterm=C/10，热调节~120 °C，θJA~120 °C/W（**ASSUMPTION**） | `BOM.csv`；TP4056 常见数据手册（本仓库未转录原件，已标注） |
| DW01A/FS8205A | 过充 4.3 V，过放 2.5 V（任务口径；手册常见 2.4 V），Ron~25 mΩ（ASSUMPTION） | task-10；DW01A 常见数据手册 |
| 电池 | 500 mAh，3.7 V，Rint 0.1 Ω（**ASSUMPTION**） | `electronics/pinmap.md`；Rint 为假设 |
| 续航目标 | 500 mAh ≥7 天 ⇒ 平均 ≤3 mA | [`docs/08_Power_Sleep_Plan.md`](../../docs/08_Power_Sleep_Plan.md) |
| 滤波器设计规则 | 外部 RC 截止 ≥10× 10 Hz ODR = 100 Hz | 项目设计规则（本套件定义） |

## 7. 假设与边界（哪些是"模型选择"，不是事实）

1. **桥路**：HY928D 内部 4 片应变片用 4 个 1 kΩ 电阻等效；1.2 mV/V 用 ±1.2 Ω/臂的应变量表示。
   四臂失配的 0.1%/1% 是**压力工况**（真实传感器是密封/修调过的，工厂零点规格 ±0.6 mV/V 才是量产边界）。
2. **HX711**：增益/满量程/10 Hz 单极点/饱和为行为近似；**不含** INL、失调温漂、1/f 噪声、
   50/60 Hz 数字陷波、内部时钟、片内稳压。输出是 0–3.3 V 模拟"代理"，真机是 24-bit 数字码。
3. **HX711 噪声**：数据手册 50 nVrms 已经包含芯片数字滤波的 10 Hz 带宽，所以 `.noise` 里
   **旁路行为 10 Hz 极点**（否则重复计算），用 0.1–10 Hz 频段积分；这是本套件的建模约定。
4. **LDO**：理想 3.3 V + RDO=0.333 Ω + 40 µA Iq；不含环路稳定性、限流折返、真实 PSRR 频响。
   负载阶跃的 0.2 Ω/11 µF 是**下限模型**，实际瞬态可能更差。
5. **TP4056**：CC/CV 折线包线（RCV=0.2 Ω 是模型选择，不是芯片参数）；不含热折返瞬态、
   定时器、再充电、软启动。θJA 与热调节门限是 ASSUMPTION（本仓库无原件转录）。
6. **DW01A/FS8205A**：tanh 平滑开关（过渡 10 mV）；不含过流锁存/延时/释放滞环。
7. **电池**：Rint=0.1 Ω 假设；无 SoC 表；不模拟老化。
8. **MCU 接口**：I2C 总线电容 100/200 pF 是假设（模块+走线），需实测；驱动 Ron=50 Ω 假设；
   ADC 12 dB 衰减满量程 3.1 V 是假设；ESP32-S3 ADC 漏流没有本地数据手册依据 → 按 0–1 µA 扫描。
9. **温度**：默认 ngspice TEMP=27 °C；没有做温度扫描（TCR 为可选，未做）。

## 8. 复跑一致性与版本

- `results/s2_summary.json` 头部记录：`ngspice-36`、`seed=20261104`、`git_head=eaf2a95`、
  生成时间、PASS/FAIL 计数。
- 随机性只来自蒙特卡洛：所有 MC 用 `numpy.random.default_rng(20261104)` 固定种子，
  同一 Python/ngspice 版本下结果可复现。
- 修改模型/阈值后重跑即可重新生成全部 JSON/图；旧结果会被覆盖（无隐藏状态）。
- 本目录**没有** `git commit`；是否提交由 Lead 统一处理。

## 9. 与旧版 `electronics/simulation/` 的关系

- 旧版 `hy928d_frontend.cir`：只有 `.dc` + `.ac`，桥臂用 500 Ω、**漏掉了 R25/R26 的 1 k 输入滤波**，
  所以它的 RC 截止是 1.65 kHz；按实际 BOM 应为 **530 Hz**。本套件修正了这一点，
  并在 `hx711_ac.json` / `docs/S2_CIRCUIT_SIM.md` 里记录了文档口径差异。
- 旧版 README 中"50 Hz 总衰减 −14.2 dB"与本套件 −14.18 dB 一致——但这个衰减主要来自
  **10 Hz 输出数据率极点**，外部 RC 只贡献 −0.04 dB；不要把 −14.2 dB 归功于外部 RC。
