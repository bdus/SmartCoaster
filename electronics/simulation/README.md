# electronics/simulation/

模拟前端仿真（ngspice 36）。输入：HY928D 5 kg 桥 + RC + HX711 行为模型（增益 128、10 Hz 一阶输出滤波）。

```bash
ngspice -b -o hy928d_frontend.log hy928d_frontend.cir
```

## 结果（`hy928d_frontend.json`）

| 项 | 值 |
|---|---|
| 5 kg 差分输出 | **3.956 mV**（3.3 V 激励 × 1.2 mV/V） |
| 增益 128 后 | **0.5064 V** |
| 占 HX711 满量程（AVDD=3.3 V：**±12.9 mV**） | **30.7%**（5 V 时 ±20 mV → 19.8%） |
| RC（1k + 100n）−3 dB | **≈1.6 kHz** |
| 50 Hz 总衰减（含 10 Hz 行为滤波） | **−14.2 dB** |
| 1 kHz / 10 kHz 输出 | −47.4 dB / −82.0 dB |

## 说明

- 这是**行为级**模型：HX711 没有公开的芯片级 SPICE 模型，增益/滤波是等效的，不代表芯片内部。
- 噪声未用 ngspice `.noise`：HX711 自身 50 nVrms（128/10 Hz）大于 RC 热噪声（≈58 nVrms/200 Hz），以数据手册为准。
- 下一步：把桥路换成 HY928D 的 4 电阻模型（1 kΩ±10%）做蒙特卡洛，验证零点/灵敏度分布。
