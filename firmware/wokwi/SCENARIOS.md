# Wokwi 场景说明（可选产物，不参与验收）

> **状态：可选，当前不作为验收项。**
> 用户已决定搁置 Wokwi 云仿真（不上传第三方、免费档需公开项目且有 50 min 限制）。
> 本目录仅保留一份可离线 lint 的数字/外设接线草图，方便以后需要时直接打开。
> 固件验证以 `tests/firmware/` 的主机测试为准；启动冒烟用 `idf.py qemu`（见 `firmware/REPORT.md`）。

## 1. 工程内容

| 文件 | 作用 |
|---|---|
| `diagram.json` | ESP32-S3 DevKitC-1 + `wokwi-hx711`（DT=4, SCK=5）+ `board-ssd1306`（SDA=8, SCL=9）+ 按键（GPIO10，按下接地）+ BOOT 键 |
| `wokwi.toml` | 指向 `../esp32/build/smartcoaster.{bin,elf}`；仅当本地构建存在时有效 |
| `SCENARIOS.md` | 本文件 |

离线 lint（不需要 token、不上传）：

```bash
wokwi-cli lint --offline firmware/wokwi/diagram.json
# 当前结果：exit 0；1 条 info：[unsupported-part] board-esp32-s3-devkitc-1 是未文档化类型
```

Wokwi 的 HX711 组件名与引脚以 lint 为准：`wokwi-hx711` 的 `DT` / `SCK` / `VCC` / `GND`
均有效；`board-esp32-s3-devkitc-1` 的电源脚是 `3V3.1` / `3V3.2`（不是 `3V3`）。

## 2. 拟验证场景（若以后启用云仿真）

| # | 脚本动作 | 期望（固件日志/OLED） |
|---|---|---|
| 1 | 放上 600 g 杯（杯 300 g + 水 300 g） | `cup_placed`，HYDRATION，TODAY 0 ml |
| 2 | 拿开 3 s 后放回 550 g | `sip 50`，TODAY 50 ml，屏显 "+50 ML" 6 s |
| 3 | 放回 700 g | `refill 150`，TODAY 不变 |
| 4 | 放 2000 g 外来物 | `mode_change SCALE`，不计饮水 |
| 5 | 在 600 g 上叠加 ±2 g 抖动 | 无 sip/refill（稳定窗 2 g + 中值滤波） |
| 6 | 单击 / 双击 / 长按 2 s / 长按 5 s | 视图切换 / 手动 SCALE / 配杯或去皮 / 配对桩 |
| 7 | 空闲 60 min | `reminder_due`（Wokwi 只能看串口日志） |

## 3. 能力边界（必须写清楚）

- Wokwi 只能模拟**数字/外设行为**：GPIO 时序、I2C 帧、按键电平、PWM 占空比。
- **不能**模拟应变片/惠斯通电桥、HX711 模拟前端、噪声/温漂/蠕变/偏载、真实称重精度。
- `wokwi-hx711` 的输出计数与真实标定无关；固件里 `counts_per_g = 515.4`（PROVISIONAL）
  必须在实物上用砝码标定，不能拿 Wokwi 数值当验收。
- OLED 只能看到 I2C 是否应答，字体/布局需实物目视确认。
- 因此：**Wokwi 通过 ≠ 称重通过**；它最多验证"固件能启动、按键和 I2C 总线有动作"。
