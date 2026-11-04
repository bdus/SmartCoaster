# electronics/simulation/（历史第一版，已被 `simulation/electronics/` 取代）

> **2026-11-04 更新**：完整 S2 电路仿真套件在 **`simulation/electronics/`**（`run_s2.py`：
> 桥路 / HX711 / 电源 / MCU 接口 × .op/.dc/.ac/.tran/.noise/蒙特卡洛，28 个结果）。
> 本目录只保留最早的单个网表作历史对照。

## 历史文件

- `hy928d_frontend.cir`：桥路等效（1 MΩ 共模 + 500 Ω 桥臂）+ 行为增益 128 + 单极点输出滤波；
  仅 `.dc`/`.ac`。
- `hy928d_frontend.json`：由该网表得出的指标（历史值）。
- `hy928d_frontend.log`：ngspice 原始日志。

## 重要更正（2026-11-04）

1. **外部 RC 截止不是 1.65 kHz，而是 530.5 Hz**：旧网表漏掉了 R25/R26 的 1 kΩ（`HX_A_P/N` 输入滤波）；
   `simulation/electronics/results/hx711_ac.json` 用真实 BOM 值重算 = **530.5 Hz**。
2. **50 Hz 的 −14.2 dB 主要来自 HX711 的 10 Hz ODR 输出极点**，外部 RC 只贡献 −0.04 dB。
3. 该历史网表不含噪声/瞬态/蒙特卡洛，也没有电源与 MCU 接口；不要把它当作完整电路验证。

以 `simulation/electronics/` 与 `docs/S2_CIRCUIT_SIM.md` 为准。
