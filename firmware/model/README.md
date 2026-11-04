# firmware/model — 饮水状态机参考模型

纯 Python（无硬件依赖），作为 C/ESP-IDF 实现的**可测试规范**。

```bash
PYTHONPATH= /data/Documents/tools/sim-venv/bin/pytest firmware/model -q
```

## 逻辑

- **模式由重量自动切换**：稳定重量落在杯范围 `[皮重−5g, 皮重+最大水量]` → `HYDRATION`；空载/超范围 → `EMPTY`/`SCALE`。按钮不切模式。
- **滤波**：5 点中值（去尖峰）+ 0.3 s 稳定窗（极差 ≤2 g）；未稳定不产生事件。
- **事件**：
  - 放杯 → `cup_placed`；
  - 拿杯 → `cup_removed`（记下最后一次稳定重量）；
  - 放回且轻了 ≥10 g → `sip`（计入今日 ml，触发“刚喝了多少”）；
  - 放回且重了 ≥10 g → `refill`（更新基线，不计入）；
  - 稳定重量超出杯范围（>皮重+1.5 kg）→ `mode_change: SCALE`。
- **提醒**：`now − last_drink > 60 min` 且未达标 → `reminder_due`，10 min 冷却；喝水后重置。
- **配杯**：`tare_cup(empty_weight)`（App 或长按 2 s）。

## UI 层（`ui.py`）

`HydrationTracker` 只管重量状态；`UiController` 叠加按键与显示：

- 单击：进度 ↔ 重量；提醒中 = 静音；
- **双击：手动切模式**（覆盖自动 10 min，或到下一次拿杯/放杯解除）；
- 长按 2 s：饮水=配杯 / 秤=去皮；长按 5 s：配对。
- 默认仍是“杯垫模式 + 重量自动切”；按键多状态功能保留，只是日常低频。

11 个测试覆盖：sip/refill/噪声/尖峰/自动切秤/提醒/配杯 + 单击/双击/长按/手动模式解除。

## 已知局限

- 外来物体重量恰好落在杯范围内时，单靠重量无法区分（需要 App/配杯/手动秤模式兜底）。
- 模型是 10 Hz 采样；实际 HX711 10 Hz + 固件可能 5 Hz 滤波，参数可调。
- 温漂/蠕变/偏载未建模，留给实物标定。
