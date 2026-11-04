# tests/firmware — 主机侧固件测试

不接硬件、不依赖 Wokwi/云，验证 `firmware/esp32/main/` 的纯逻辑层与 HX711 mock。

## 一键运行

```bash
tests/firmware/run_host_tests.sh
# 或自定义构建目录：
BUILD_DIR=/tmp/scoaster-host tests/firmware/run_host_tests.sh
```

三步：

1. **CMake host build + CTest**
   - `host_core_test`：`firmware/model` 的 11 个场景（7 个 hydration + 4 个 UI）逐条移植为 C 断言；
   - `host_mock_test`：HX711 mock 的 9 个场景（HAL 往返/去皮、量化、噪声、漂移、饱和、24-bit 饱和、单点跳变、整段杯生命周期、噪声确定性）。
2. **differential.py**：同一批命令轨迹分别跑 Python 权威模型与 C 实现，逐条比对事件/UI 动作/状态（16 个场景，82 条记录）。
3. **pytest firmware/model**：Python 参考模型基线（当前 16 个：11 个核心 + 5 个 HX711 行为模型）。

当前结果：

```
100% tests passed, 0 tests failed out of 2
16/16 scenarios match, 82 records compared
16 passed
```

## 分层与依赖方向

```
weight_sensor.h   HAL: read_counts() / tare() / grams() / data_ready()
   ├── hx711_hw.c    GPIO4/5 位翻转（仅 target 编译，随 app 一起 build）
   └── hx711_mock.c  脚本化重量序列（host / QEMU）
           ↓ grams
weight_process.c  中值 + 稳定窗 + 去尖峰        （纯 C，无 GPIO/ESP-IDF）
           ↓ 稳定克数
intake.c          放杯/拿杯、sip/refill、今日 ml、EMPTY/HYDRATION/SCALE（纯 C）
           ↓
reminder.c        60 min / 冷却 / 达标           （纯 C）
           ↓ events
hydration.c       门面：组合三层 + 事件历史
           ↓
ui.c              单击/双击/长按、视图、手动模式（纯 C）
```

`weight_process.c` / `intake.c` / `reminder.c` / `ui.c` / `hydration.c` / `hx711_mock.c`
只 include 标准 C 与彼此的头文件，不 include `driver/gpio.h` 或 `esp_log.h`。

## HX711 mock 注入接口

```c
#include "hx711_mock.h"

static hx711_mock_t mock;      /* caller-owned state, no heap */
static weight_sensor_t sensor;

hx711_mock_config_t cfg;
hx711_mock_config_default(&cfg);       /* counts_per_g=515.4 (5 kg, 3.3 V) */
cfg.noise_g = 0.5;                     /* 确定性 LCG 噪声 ±0.5 g */
hx711_mock_init(&sensor, &mock, &cfg);

/* 方式 A：按段脚本（最常用；每段是「重量, 采样数」，10 SPS） */
static const hx711_mock_segment_t script[] = {
    {0.0, 20}, {600.0, 60}, {0.0, 30}, {550.0, 60}, {700.0, 60},
};
hx711_mock_set_segments(&sensor, script, 5, false);

/* 方式 B：逐样本数组（可循环） */
static const double weights[] = {600.0, 600.0, 0.0, 550.0};
hx711_mock_set_weights(&sensor, weights, 4, true);

/* 方式 C：恒定重量 */
hx711_mock_set_weight(&sensor, 600.0);

/* 可选损伤模型 */
hx711_mock_set_noise(&sensor, 1.0);        /* ±1 g 均匀噪声 */
hx711_mock_set_drift(&sensor, 0.005);      /* g / conversion */
hx711_mock_set_saturation(&sensor, 2000);  /* 机械/电气饱和 */
hx711_mock_set_quantize(&sensor, 0.5);     /* 量化到 0.5 g */

while (...) {
    double g;
    if (weight_sensor_grams(&sensor, &g) == WS_OK) {
        hydration_feed(&tracker, g, t, events, 8);
    }
    t += 0.1;
}
```

覆盖的注入场景：空杯、放杯、加水/续水、喝、拿开、放回、单点跳变、噪声、漂移、
饱和（机械 + 24-bit）、量化、恒定量、循环序列。

## 说明

- 没有用 ESP-IDF 的 `linux` target：纯逻辑层是 C11，直接系统编译器更快；
  target 构建仍由 `firmware/esp32` 的 `idf.py build` 覆盖（同一批源文件）。
- `differential.py` 自己用 `cc` 编译 `host_core_cli.c`（临时目录），不依赖 CMake 产物。
- Python 的 `firmware/model/hx711.py` 用高斯噪声（不可复现），C mock 用确定性 LCG；
  两者都覆盖噪声/漂移/饱和/量化，但**不要求逐位一致**。
