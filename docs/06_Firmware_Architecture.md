# 固件架构：HAL + Mock + 主机测试

> 目标：**不依赖 Wokwi/云/实物**也能验证重量处理、饮水累计、提醒、按键逻辑；硬件相关只留薄薄一层。
> 对应 `docs/05_Bringup_and_Verification_Plan.md` 的 G0/G1；Python 参考实现见 `firmware/model/`。

## 1. 分层（依赖只向下）

```
┌──────────────────────────────────────────────┐
│ UI / BLE / App                               │
├──────────────────────────────────────────────┤
│ reminder（提醒节奏、静音）                     │
├──────────────────────────────────────────────┤
│ intake（sip/refill、今日累计、目标）           │
├──────────────────────────────────────────────┤
│ weight_process（中值、稳定窗、去尖峰）          │
├──────────────────────────────────────────────┤
│ weight_sensor.h（接口：read_counts/tare/grams）│
├───────────────────────┬──────────────────────┤
│ hx711_hw.c（GPIO4/5）  │ hx711_mock.c（脚本）  │
└───────────────────────┴──────────────────────┘
```

- `weight_process` / `intake` / `reminder` / `ui` **不 include** `driver/gpio.h`、`esp_log.h` 等；只依赖 `weight_sensor.h` 与标准 C。
- 这样 host 编译时链接 `hx711_mock.c`，target 编译时链接 `hx711_hw.c`。

## 2. 接口

```c
typedef enum { WS_OK = 0, WS_TIMEOUT, WS_IO } ws_err_t;

typedef struct {
    ws_err_t (*read_counts)(void *ctx, int32_t *counts);
    ws_err_t (*tare)(void *ctx);
    ws_err_t (*grams)(void *ctx, float *g);
    bool     (*data_ready)(void *ctx);
    void     *ctx;
} weight_sensor_t;   /* 实现见 firmware/esp32/main/weight_sensor.h */
```

- `read_counts()`：原始 24-bit 有符号计数（HX711 10 SPS）。
- `tare()`：把当前重量设为零点（秤模式去皮）。
- `grams()`：计数 → 克（标定系数 `counts_per_gram`，出厂/砝码校准）。

Mock 注入：

```c
typedef struct {
    float weight_g;       /* 当前脚本重量 */
    float noise_g;        /* 高斯噪声 */
    float drift_g_per_s;  /* 漂移 */
} hx711_mock_t;
void hx711_mock_set_weight(hx711_mock_t *m, float g);
```

## 3. 模块与测试

| 模块 | 输入 | 输出 | 测试方式 |
|---|---|---|---|
| `weight_process` | counts/grams @10 Hz | 稳定重量、稳定标志 | host 单测（噪声/尖峰/阶跃） |
| `intake` | 稳定重量 + 时间 | sip/refill/今日 ml | host 单测（放杯/喝 50/续水/外来物） |
| `reminder` | 今日 ml、last_drink、目标 | 提醒/snooze | host 单测（60 min/冷却/达标） |
| `ui` | 按键事件 + 状态 | 视图/手动模式 | host 单测（单击/双击/长按） |
| `hx711_hw` | GPIO | counts | 实物 + 逻辑分析仪（可选） |
| `hx711_mock` | 脚本 | counts | host（HX711 行为模型） |

## 4. 主机测试（已可跑）

```bash
# C 侧：CTest 2/2（core 11/11、41 checks；mock 9/9、198 checks）
bash tests/firmware/run_host_tests.sh

# C↔Python 差分：16/16 场景、82 条记录一致
# （同一命令流分别喂 C 与 Python，逐事件/累计比对）

# Python 参考 + HX711 行为模型：16 passed
PYTHONPATH= /data/Documents/tools/sim-venv/bin/pytest firmware/model -q
```

- `idf.py build`（ESP32-S3，v6.1）0 warning / 0 error，bin **233,360 B**（app 分区余 85%）。
- QEMU 冒烟：`idf.py qemu` 跑通（QEMU 构建加 `CONFIG_SMARTCOASTER_WEIGHT_MOCK` + `BATTERY_STUB`；QEMU 9.2 未实现 S3 SAR ADC done 位，生产构建不受影响）。
- 变异测试：sip 阈值 10→60 g，真实输出仍 sip 50、变异版 today 0 —— 差分测试非空转。

`firmware/model/hx711.py` 复现：24-bit 码值、AVDD=3.3 V 满量程 **±12.9 mV**、50 nVrms 噪声、偏移/温漂、量化、饱和；`run_trace()` 可把重量脚本直接灌进状态机。

## 5. 测试矩阵

| # | 场景 | 期望 |
|---|---|---|
| 1 | 空载 | 0 g ±噪声，EMPTY |
| 2 | 放 600 g 杯 | cup_placed，HYDRATION |
| 3 | 拿走 3 s 放回 550 g | sip 50 g ±1.5 g，today +50 |
| 4 | 放回 700 g | refill 100，不计入 |
| 5 | 2000 g 外来物 | mode→SCALE，不计入 |
| 6 | ±2 g 抖动/轻敲 | 无 sip/refill |
| 7 | 单点 1100 g 尖峰 | 被中值拒绝 |
| 8 | 5 kg 满载 | 不饱和（3.96 mV < 12.9 mV） |
| 9 | 20 kg 过载 | 码值饱和到 ±2^23−1 |
| 10 | 温漂 +0.002 mV/°C | 零点缓慢漂移，不误触发 |
| 11 | 单击/双击/长按 | 视图/手动秤/配杯/配对 |
| 12 | 提醒 60 min | reminder_due，snooze 生效 |

## 6. 明确不做 / 待做

- 不做 HX711 晶体管级仿真；芯片级噪声/线性度只能实物标定。
- 不在 host 上跑完整 ESP-IDF 应用；只 host 编译纯逻辑模块。
- 待做：BLE GATT（现为桩）、NVS/跨日清零、低功耗休眠、OLED 中文、真实 HX711/OLED/按键/halo/电池 bring-up + 砝码标定。
- Wokwi 仅保留可选 `firmware/wokwi/`（离线 lint），不作为依赖。

## 7. 与硬件的关系

- HX711 **芯片级集成**在主板上（SOP-16），不是模块；原理图/PCB 见 `electronics/kicad/`。
- 传感器 HY928D 是 **4 线惠斯通电桥**（1.2 mV/V，5 kg），HX711 直接适配，不需要 FSR 分压电路。
- 3.3 V 激励、VSUP=DVDD=AVDD、VFB=GND、BASE=NC；满量程 ±12.9 mV，5 kg 用 30.7%。
