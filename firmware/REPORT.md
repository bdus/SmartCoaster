# 固件骨架与本地验证报告

> 日期：2026-11-04 · 目标：ESP32-S3 · ESP-IDF v6.1 · 状态：**可行性骨架通过本机验证**
> 约束：未购买硬件、未 commit/push、未上传任何文件到 Wokwi 云、未使用 `WOKWI_CLI_TOKEN`；
> 未修改 `mechanical/`、`electronics/`、`docs/`（`docs/06_Firmware_Architecture.md`、
> `firmware/model/hx711.py` 等为并行工作区产出，本报告只做集成与对齐）。

> **2026-11-04 更新（用户决定：LED 与光导全部去掉）**：原理图已删 D1、Q1–Q3、R13–R21，
> 固件同步**彻底删除** LED 灯环驱动：`main/halo.{h,c}`、`board.h` 的 `BOARD_HALO_R/G/B_GPIO`、
> `app_main.c` 的 `render_halo()`/`halo_*` 调用/`last_halo_ms` 与主循环 20 ms 灯光动画、
> `main/CMakeLists.txt` 的 `halo.c` 与 `esp_driver_ledc` 依赖。称重/喝水/提醒/OLED 状态机未改。
> 本次实测：host `11/11`（41 checks）+ mock `9/9`（198 checks）+ C↔Python 差分 `16/16`（82 记录）
> + pytest `16 passed`；`idf.py build` 通过，bin **519,184 B（0x7EC10）**，app 分区余 **66%**。
> `build-qemu/`（QEMU 冒烟专用、未入库）已 fullclean 以清掉旧 halo 目标文件，本次未重跑 QEMU；
> 如需重跑按 §5.3 全量重建即可。下文 §0/§2 的 233,360 B 等数字是早期骨架阶段的记录，保留作历史。

## 0. 结论（先看表）

| 项目 | 结果 | 证据 |
|---|---|---|
| `idf.py set-target esp32s3 && idf.py build` | **通过**（0 warning / 0 error） | §2，日志末尾见 §2.3 |
| 应用 bin | **519,184 B**（`0x7EC10`，507.0 KiB；早期骨架为 233,360 B） | 分区 `0x177000`，剩余 **66%** |
| 主机 C 测试（11 个模型场景） | **11/11 通过**，41 条断言 | `host_core_test` |
| HX711 mock 测试 | **9/9 通过**，198 条断言 | `host_mock_test` |
| C ↔ Python 差分 | **16/16 场景、82 条记录全一致** | `differential.py` |
| Python 参考模型 | **16 passed**（11 核心 + 5 个 HX711 行为模型） | `pytest firmware/model` |
| QEMU 冒烟 | **早期骨架阶段通过**（QEMU 专用 mock + battery stub）；2026-11-04 删 halo 后未重跑 | §5；重跑按 §5.3 全量重建 |
| Wokwi 离线 lint | **通过**（exit 0，仅 1 条 info） | §6，**可选、不参与验收** |
| 真实 HX711/OLED | **未验证**（本机无外设模型） | §7 留给实物 bring-up |

一句话：**逻辑层已被主机测试和 QEMU 冒烟覆盖；模拟器不能替代实物标定，HX711/OLED 必须上板验证。**

---

## 1. 架构分层

依赖只向下，硬件收敛到 `weight_sensor.h` 一个接口：

```
┌────────────────────────────────────────────────────────────┐
│ app_main.c：采样循环、OLED 渲染、按键事件分发                  │
├────────────────────────────────────────────────────────────┤
│ ui.c            单击/双击/长按、视图、手动模式（纯 C）       │
├────────────────────────────────────────────────────────────┤
│ hydration.c     门面：组合三层 + 事件历史（纯 C）            │
├────────────────────────────────────────────────────────────┤
│ reminder.c      提醒节奏 / 冷却 / 达标（纯 C，无 GPIO）      │
├────────────────────────────────────────────────────────────┤
│ intake.c        放杯/拿杯、sip/refill、今日 ml、模式（纯 C） │
├────────────────────────────────────────────────────────────┤
│ weight_process.c 中值 + 稳定窗 + 去尖峰（纯 C，无 GPIO）     │
├────────────────────────────────────────────────────────────┤
│ weight_sensor.h HAL：read_counts() / tare() / grams()       │
├──────────────────────────┬─────────────────────────────────┤
│ hx711_hw.c（GPIO 4/5）   │ hx711_mock.c（脚本/噪声/饱和）  │
└──────────────────────────┴─────────────────────────────────┘
```

| 文件 | 职责 | 依赖 |
|---|---|---|
| `core_types.h/.c` | 模式/事件/配置类型与默认值、名称 | 标准 C |
| `weight_process.h/.c` | 5 点中值 → 0.3 s 稳定窗（极差 ≤2 g）→ 去尖峰（>40 g） | 标准 C |
| `intake.h/.c` | `EMPTY/HYDRATION/SCALE`、`cup_placed/removed`、`sip/refill`、今日累计 | `core_types.h` |
| `reminder.h/.c` | `today<goal` 且距上次饮水 >60 min，10 min 冷却 | `core_types.h` |
| `hydration.h/.c` | 把三层按 Python 顺序串起来，记录事件历史 | 上述三层 |
| `ui.h/.c` | 手势 → 动作；视图；手动 SCALE 覆盖 10 min / 放拿杯解除 | `hydration.h` 接口 |
| `weight_sensor.h` | HAL 接口 + 错误码 + counts→grams 公共换算 | 标准 C |
| `hx711_hw.c` | PD_SCK/DOUT 位翻转，25 脉冲，10 Hz，超时/去皮 | ESP-IDF `driver/gpio` |
| `hx711_mock.c` | 段脚本/逐样本/恒定重量 + 噪声/漂移/饱和/量化，确定性 LCG | 标准 C |
| `oled.c` | SSD1306 128×32，I2C 新驱动 API，5×7 ASCII，进度条 | ESP-IDF `esp_driver_i2c` |
| `button.c` | 30 ms 去抖、单击/双击（350 ms 窗）/长按 2 s、5 s | ESP-IDF `driver/gpio` |
| `battery.c` | ADC1 oneshot + curve-fitting 校准（QEMU 可 stub） | ESP-IDF `esp_adc` |
| `ble.c` | **NimBLE GATT（P1，270 行）**：服务 0xFF00（0xFF01 重量/0xFF02 今日/0xFF03 目标/0xFF04 电量/0xFF05 命令/0xFF06 Unix 秒），`ble_update()` 1 Hz notify | ESP-IDF NimBLE |

**分层约束的落实方式**：`weight_process.c`、`intake.c`、`reminder.c`、`ui.c`、
`hydration.c`、`hx711_mock.c` 只 include 标准 C 和彼此的头文件；`rg 'driver/|esp_log|esp_err|freertos'`
在这 6 个文件里为 0 命中（`app_main.c`/驱动层才 include ESP-IDF）。

与 `docs/06_Firmware_Architecture.md` 的接口草图有一处**有意的偏离**：该草图把
`read_counts/tare/grams` 直接放在 `weight_sensor_t` 的函数指针里且 `read_counts` 返回
`int32_t`。本实现用 `ops` 表 + `ws_err_t` 返回值（`WS_OK/TIMEOUT/IO/...`），
因为 HX711 超时、未就绪、无传感器必须能被上层区分；函数名与语义保持一致。
`counts_per_g = 515.4`（HY928D 5 kg、3.3 V、gain 128 的 ±12.9 mV 满量程）
与 `firmware/model/hx711.py` 对齐；注意 `electronics/pinmap.md` 里写的是 ±20 mV
（5 V 情形），该文档按约束未改动，需后续在电子文档中统一。

---

## 2. 构建结果

### 2.1 环境

| 工具 | 版本/路径 |
|---|---|
| ESP-IDF | v6.1（`/home/pi/.espressif/v6.1/esp-idf`） |
| 工具链 | `xtensa-esp32s3-elf-gcc 15.2.0_20251204` |
| 目标 | `esp32s3`（ESP32-S3-MINI-1，8 MB flash，USB Serial/JTAG console） |
| CMake/Ninja | IDF 自带（`idf.py` 驱动） |
| QEMU | `qemu-xtensa esp_develop_9.2.2`（QEMU 9.2.2） |

### 2.2 命令

```bash
source /home/pi/.espressif/tools/activate_idf_v6.1.sh
cd firmware/esp32
idf.py set-target esp32s3
idf.py build
```

首次 `set-target` 从 `sdkconfig.defaults` 生成 `sdkconfig`（未入库）。
最终验证模拟“新克隆”：删除 `sdkconfig` + `idf.py fullclean` → `idf.py set-target esp32s3`
→ `idf.py build`（1093 个构建步骤），结果 **0 warning / 0 error**。

### 2.3 构建日志末尾（原文）

```
Successfully created ESP32-S3 image.
Generated /data/Documents/projects/SmartCoaster/firmware/esp32/build/smartcoaster.bin
[1093/1093] cd /data/Documents/projects/SmartCoaster/firmware/esp32/build && /home/pi/.espressif/tools/python/v6.1/venv/bin/python /home/pi/.espressif/v6.1/esp-idf/components/partition_table/check_sizes.py --offset 0x8000 partition --type app /data/Documents/projects/SmartCoaster/firmware/esp32/build/partition_table/partition-table.bin /data/Documents/projects/SmartCoaster/firmware/esp32/build/smartcoaster.bin
smartcoaster.bin binary size 0x38f90 bytes. Smallest app partition is 0x177000 bytes. 0x13e070 bytes (85%) free.
Executing action: all (aliases: build)
Running ninja in directory /data/Documents/projects/SmartCoaster/firmware/esp32/build
Executing "ninja all"...

Project build complete. To flash, run:
 idf.py flash
or
 idf.py -p PORT flash
or
 python -m esptool --chip esp32s3 -b 460800 --before default-reset --after hard-reset write-flash --flash-mode dio --flash-size 8MB --flash-freq 80m 0x0 build/bootloader/bootloader.bin 0x8000 build/partition_table/partition-table.bin 0x10000 build/smartcoaster.bin
or from the "/data/Documents/projects/SmartCoaster/firmware/esp32/build" directory
 python -m esptool --chip esp32s3 -b 460800 --before default-reset --after hard-reset write-flash "@flash_args"
```

### 2.4 尺寸

| 产物 | 大小 | 说明 |
|---|---|---|
| `build/smartcoaster.bin` | **519,184 B（0x7EC10 / 507.0 KiB）** | 含全部分层、HX711/OLED/BLE 驱动、NVS、OLED 字库 |
| `build/bootloader/bootloader.bin` | 22,608 B（0x5850） | 31% 空闲 |
| app 分区 | 0x177000（1.5 MiB） | 85% 空闲 |
| QEMU 变体 `build-qemu/smartcoaster.bin` | 222,096 B | 仅 QEMU 冒烟用（mock + battery stub） |

> 说明：`sdkconfig.defaults` 里 flash mode 用 **DIO**（8 MB、80 MHz）。QEMU 对 QIO 支持不完整，
> 保持 DIO 可让实物与 QEMU 用同一套 flash 参数；实物若确认可用 QIO 再改。

---

## 3. 主机测试

### 3.1 一键运行

```bash
tests/firmware/run_host_tests.sh
# 实际执行：
#   cmake -S tests/firmware -B /tmp/smartcoaster-host-build && cmake --build ... && ctest ...
#   PYTHONPATH= python tests/firmware/differential.py
#   PYTHONPATH= pytest firmware/model -q
```

本次输出：

```
100% tests passed, 0 tests failed out of 2
16/16 scenarios match, 82 records compared
16 passed in 0.12s
```

### 3.2 C 单测 1：11 个模型场景（`host_core_test`）

把 `firmware/model/test_hydration.py`（7 个）+ `test_ui.py`（4 个）逐条移植为 C 断言，
编译 `hydration.c/ui.c/weight_process.c/intake.c/reminder.c/core_types.c`（无 ESP-IDF）。
测试框架用 CTest + 断言宏（未引入 Unity；原任务允许“Unity 或简单 assert”）：

```
PASS test_cup_place_sip_and_progress
PASS test_refill_is_not_intake
PASS test_noise_does_not_trigger
PASS test_single_spike_rejected
PASS test_foreign_object_switches_to_scale_and_back
PASS test_reminder_fires_after_interval_and_resets_on_sip
PASS test_cup_tare_setup
PASS test_single_click_toggles_view_and_snoozes
PASS test_double_click_manual_scale_and_timeout
PASS test_cup_action_releases_manual_mode
PASS test_long_press_actions

41 checks, 0 failures, 11/11 tests passed
```

### 3.3 C 单测 2：HX711 mock（`host_mock_test`）

```
PASS test_hal_roundtrip_and_tare              # read_counts→grams→tare→grams
PASS test_mock_quantisation                    # 整数 counts 分辨率 + 0.5 g 量化
PASS test_mock_noise_does_not_trigger          # ±1 g 噪声 400 样本
PASS test_mock_drift_does_not_trigger_sip      # 0.005 g/样本 ×600 = 3 g 漂移
PASS test_mock_saturation_switches_to_scale    # 5000 g → 饱和 2000 g → SCALE
PASS test_mock_24bit_saturation                # 20 kg → 0x7FFFFF 码值饱和
PASS test_mock_single_sample_jump_rejected     # 单点 3000 g 被中值吞掉
PASS test_mock_cup_lifecycle                   # 空/放杯/拿走/放回 sip 50/续水 150
PASS test_mock_deterministic_noise             # 同 seed 同输出

198 checks, 0 failures, 9/9 tests passed
```

### 3.4 C ↔ Python 差分（`differential.py`）

协议：`F w t`（喂样本）、`T w`（配杯）、`R t`（跨日）、`C/D/L2/L5`（按键）、`Q t`（查模式/视图）、
`S`（查状态）。C 侧 `host_core_cli` 与 Python 侧 `HydrationTracker + UiController` 吃**同一份**
命令流，逐条比对事件类型/时间/数值/细节、UI 动作、模式与今日累计。

- 前 11 个场景与 11 个 pytest 用例一一对应（含参考实现“每次 `run()` 把 t 归零”的细节）；
- 另加 5 个压力轨迹：长随机行走、阈值边界、提醒冷却、尖峰簇、跨日+配杯；
- 共 16 场景 82 条记录，全部一致（容差 1e-6）。

**差分不是空转**：把 C 的 `sip_threshold` 从 10 g 改成 60 g 重新编译，同一条轨迹下
真实 C 输出 `sip 50 / today 50`，变异版输出 `today 0` —— 差分与单测都会失败。
（变异只在 `/tmp` 副本上做，未改工作区。）

### 3.5 与 `firmware/model` 的关系

会话期间并行工作区给 `firmware/model/` 增加了 `hx711.py` + 5 个测试，因此现在
`pytest firmware/model` 是 **16 passed**（11 核心 + 5 个 HX711 行为模型）。
- 11 个核心场景：C 单测 **逐条移植** + 差分 **逐事件一致**；
- 5 个 HX711 物理模型测试：用高斯噪声（Python `random.gauss`，不可复现），
  C mock 用确定性 LCG，**不要求逐位一致**；C 侧用 §3.3 的 9 个测试覆盖同类性质
  （噪声/漂移/饱和/量化），并与 `hx711.py` 的 5 kg / ±12.9 mV / 515.4 counts/g 对齐。

### 3.6 覆盖边界

主机测试覆盖：滤波/稳定/尖峰、模式切换、sip/refill、提醒/冷却、配杯、按键手势、
手动模式解除、HAL 换算/去皮、mock 的噪声/漂移/饱和/量化。
**不覆盖**：真实时序（ISR/任务调度）、HX711 时钟抖动、OLED 实际显示、按键抖动、
温漂/蠕变/偏载、功耗。

---

## 4. HX711 mock 注入接口

```c
#include "hx711_mock.h"

static hx711_mock_t mock;        // 调用方持有，无堆分配
static weight_sensor_t sensor;

hx711_mock_config_t cfg;
hx711_mock_config_default(&cfg); // counts_per_g=515.4；噪声/漂移/饱和/量化默认 0
cfg.noise_g = 0.5;               // 确定性 LCG，±0.5 g
hx711_mock_init(&sensor, &mock, &cfg);

// A. 段脚本：{重量 g, 采样数}，10 SPS
static const hx711_mock_segment_t script[] = {
    {0.0, 20}, {600.0, 60}, {0.0, 30}, {550.0, 60}, {0.0, 20}, {700.0, 60},
};
hx711_mock_set_segments(&sensor, script, 6, false);

// B. 逐样本数组（可循环）  C. 恒定重量
hx711_mock_set_weights(&sensor, weights, n, true);
hx711_mock_set_weight(&sensor, 600.0);

// 可选损伤
hx711_mock_set_noise(&sensor, 1.0);        // ±1 g 均匀
hx711_mock_set_drift(&sensor, 0.005);      // g / conversion
hx711_mock_set_saturation(&sensor, 2000);  // 机械饱和
hx711_mock_set_quantize(&sensor, 0.5);     // 量化

double g;
if (weight_sensor_grams(&sensor, &g) == WS_OK) {
    hydration_feed(&tracker, g, t, events, 8);
}
```

注入场景：空杯、放杯、加水/续水、喝、拿开、放回、单点跳变、噪声、漂移、
饱和（机械 2000 g + 24-bit 码值）、量化、恒定量、循环序列。
HAL 另有 `read_counts()`（原始 24-bit）与 `tare(samples)`，`data_ready()` 让 target
保持 10 Hz 非阻塞轮询；mock 永远 ready。

---

## 5. QEMU 冒烟（通过，但有 QEMU 专用 stub）

### 5.1 结论

`idf.py qemu` 能启动到 `app_main` 并跑完整称重流水（放杯 → sip → 拿开 → 续水 → 外来物 →
回到饮水），说明**启动、任务循环、OLED/按键初始化失败降级、mock 传感器、状态机、
日志**在真实 target 二进制上可工作。QEMU **没有** HX711/OLED 外设模型，因此它只证明
“固件能启动并处理数字重量输入”，不证明模拟前端。

### 5.2 遇到的问题与定位（重要）

1. 初始直接跑 `idf.py qemu`（主构建，QIO/8 MB）：bootloader 后反复重启，
   停在 `spi_flash` 初始化；换 DIO/40 MHz 后通过 flash init。
2. 之后卡在 `spi_flash: flash io: dio` 之后、**`app_main` 之前**，无任何 `coaster` 日志。
   用 QEMU gdb 附着取 backtrace：

   ```
   #0 adc_oneshot_ll_get_event ... hal/adc_ll.h:1091
   #1 read_cal_channel
   #2 adc_hal_self_calibration
   #3 adc_calc_hw_calibration_code
   #4 adc_hw_calibration            <-- __attribute__((constructor))
   #5 __libc_init_array
   #6 start_cpu0_default
   ```

   **根因**：IDF 6.1 在链接 `esp_adc` 时注册无条件的 ADC 自校准 constructor；
   QEMU 9.2 没实现 S3 SAR ADC 的 done 位，于是死循环在 `adc_oneshot_ll_get_event`。
   对照实验：同一套 sdkconfig 下 hello_world 能打印 `Hello world!`，说明不是 QEMU 整体不可用。
3. 规避：**只给 QEMU 构建**加两个开关（`sdkconfig.qemu.defaults`）：
   - `CONFIG_SMARTCOASTER_WEIGHT_MOCK=y`：用脚本传感器代替 HX711；
   - `CONFIG_SMARTCOASTER_BATTERY_STUB=y`：不链接 ADC 路径，电池固定 3.9 V。
   生产构建（`build/`）**不受影响**，仍是 `hx711_hw.c` + 真实 ADC。

### 5.3 复现命令

```bash
source /home/pi/.espressif/tools/activate_idf_v6.1.sh
cd firmware/esp32
idf.py -B build-qemu -DSDKCONFIG=build-qemu/sdkconfig \
       -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu.defaults" build
export PATH=/home/pi/.espressif/tools/tools/qemu-xtensa/esp_develop_9.2.2_20260417/qemu/bin:$PATH
timeout 45s idf.py -B build-qemu qemu
```

### 5.4 日志摘录（QEMU 串口）

```
I (116) main_task: Calling app_main()
I (116) coaster: SmartCoaster firmware skeleton — ESP32-S3 / ESP-IDF v6.1
W (121) coaster: SCRIPTED weight sensor active (QEMU/demo build, not real hardware)
E (254) coaster: OLED unavailable; continuing headless
W (276) coaster: BLE disabled (stub) — App pairing will not work yet
I (2683) coaster: event=cup_placed t=2.82 value=600.3 detail= mode=HYDRATION today=0.0 ml
I (14680) coaster: event=cup_removed t=14.82 value=600.0 detail= mode=EMPTY today=0.0 ml
I (17679) coaster: event=sip t=17.82 value=49.6 detail= mode=HYDRATION today=49.6 ml
I (17681) coaster: event=cup_placed t=17.82 value=550.3 detail= mode=HYDRATION today=49.6 ml
I (25676) coaster: event=refill t=25.82 value=150.1 detail= mode=HYDRATION today=49.6 ml
I (31680) coaster: event=mode_change t=31.82 value=2000.3 detail=SCALE mode=SCALE today=49.6 ml
I (35674) coaster: event=cup_placed t=35.82 value=700.4 detail= mode=HYDRATION today=49.6 ml
I (41683) coaster: event=cup_removed t=41.83 value=700.1 detail= mode=EMPTY today=49.6 ml
I (40298) coaster: status t=40.4 mode=HYDRATION weight=699.8 g today=50/2200 ml sensor=hx711-mock reads=401
```

（QEMU 运行被 `timeout` 结束，exit 124 属预期。）

### 5.5 QEMU 伪影（已确认，不影响结论）

- **按键**：QEMU 的 GPIO 输入模型不实现内部上拉，GPIO10 读到 0（按下），
  因此日志里 t≈2.3 s 出现 `long_2s`、t≈5.3 s 出现 `long_5s`。实物有内部上拉，不会如此；
  QEMU 下不应把按键行为当验收依据。
- **OLED**：I2C 总线初始化成功但 0x3C 无应答 → `OLED unavailable`，走 headless 路径。
- **ADC**：见 §5.2，QEMU 构建用 battery stub。

---

## 6. Wokwi（可选产物，不参与验收）

按最新决策**不使用 Wokwi 云**；目录保留为可选接线草图，仅做离线 lint：

```bash
wokwi-cli lint --offline firmware/wokwi/diagram.json
# exit 0；Found 1 info
# ℹ [unsupported-part] Part "esp" uses undocumented type "board-esp32-s3-devkitc-1".
```

- `diagram.json`：`board-esp32-s3-devkitc-1` + `wokwi-hx711`（DT=4, SCK=5）+
  `board-ssd1306`（SDA=8, SCL=9）+ 按键 GPIO10 + BOOT；电源脚用 `3V3.1/3V3.2`
  （lint 明确 `3V3` 无效）。
- `wokwi.toml` 指向 `../esp32/build/smartcoaster.{bin,elf}`。
- `SCENARIOS.md` 记录 7 个拟验证场景与能力边界：**Wokwi 只能模拟数字/外设行为，
  不能模拟应变片/桥路/噪声/温漂**；`wokwi-hx711` 的计数与真实标定无关。

未使用 `WOKWI_CLI_TOKEN`，未执行 `wokwi-cli run`，未上传。

---

## 7. 未完成项与风险

### 7.1 明确未做

> **2026-11-04 20:45 更新**：下表原为骨架阶段（早于 BLE/NVS/PM/中文 UI 落地）的记录；
> BLE GATT（`ble.c` NimBLE 0xFF00，270 行）、NVS（`storage.c`）、PM light sleep
> （`app_main.c` `esp_pm_configure(light_sleep_enable=true)`）、OLED 中文
> （`oled.c` `oled_text_cn()` + `font_cn.h`）**均已实现**。现已移出“未做”，当前仍未做的如下表。

| 项 | 状态 | 说明 |
|---|---|---|
| 手机 App / BLE 手机侧 | 未做 | 固件侧 GATT 已实现；无手机 App；单次饮水量/历史/提醒配置特征待补（见 `docs/AUDIT_PRD.md` §7） |
| 实物标定 | 未做 | `counts_per_g=515.4` 为 PROVISIONAL；需砝码标定 + 温漂/蠕变测试 |
| HX711 时序 | 未实测 | 25 脉冲/1 µs 延时需逻辑分析仪确认（<50 µs 要求） |
| 外设仿真 | 无 | QEMU/主机都没有 HX711 模拟前端与 OLED 面板；见 §7.2 |
| 机械/电子集成 | 未做 | 按键/屏位置按 `electronics/pinmap.md` 草案，未上板 |

### 7.2 必须留给实物 bring-up 的

1. **HX711**：称重链路（HY928D 桥路 → HX711 → 24-bit）的噪声、零点漂移、回差、
   温漂、偏载；用参考砝码标定 `counts_per_g` 与 `offset_counts`，替换 PROVISIONAL 值。
2. **OLED**：0x3C 实际应答、对比度、128×32 窗口/字体、刷新率与 I2C 400 kHz 波形。
3. **按键**：30 ms 去抖、单击/双击/长按在真实轻触开关上的手感（QEMU 无法模拟）。
4. **电池**：分压比、ADC 校准、LiPo 曲线、充电/保护板实测。
5. **功耗**：500 mAh 估算需实测（尤其 HX711 与 OLED 峰值）。

### 7.3 已知文档不一致（未改，等确认）

- `electronics/pinmap.md` 写 HX711 满量程 ±20 mV；按 S3 3.3 V / gain 128 应为 **±12.9 mV**
  （±20 mV 是 5 V 情形）。固件与 `firmware/model/hx711.py` 用 ±12.9 mV / 515.4 counts/g，
  建议后续统一电子文档。
- `firmware/model/` 在会话期间从 11 个测试变为 16 个（新增 `hx711.py` + 5 测试），
  本报告的“11 个场景”特指原有的 hydration+UI 权威用例。

---

## 8. 复现清单

```bash
# 0) 主机测试（无需硬件/ESP-IDF）
tests/firmware/run_host_tests.sh

# 1) 目标构建
source /home/pi/.espressif/tools/activate_idf_v6.1.sh
cd firmware/esp32 && idf.py set-target esp32s3 && idf.py build

# 2) QEMU 冒烟（可选，QEMU-only stubs）
idf.py -B build-qemu -DSDKCONFIG=build-qemu/sdkconfig \
       -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu.defaults" build
export PATH=/home/pi/.espressif/tools/tools/qemu-xtensa/esp_develop_9.2.2_20260417/qemu/bin:$PATH
timeout 45s idf.py -B build-qemu qemu

# 3) Wokwi 离线 lint（可选，不跑仿真）
wokwi-cli lint --offline firmware/wokwi/diagram.json
```

---

## 9. 文件清单（本次新增/修改）

```
firmware/esp32/
  CMakeLists.txt, sdkconfig.defaults, sdkconfig.qemu.defaults
  main/CMakeLists.txt, main/Kconfig.projbuild
  main/app_main.c
  main/core_types.{h,c}
  main/weight_sensor.{h,c}
  main/weight_process.{h,c}
  main/intake.{h,c}
  main/reminder.{h,c}
  main/hydration.{h,c}
  main/ui.{h,c}
  main/hx711_hw.{h,c}
  main/hx711_mock.{h,c}
  main/oled.{h,c}, button.{h,c}, battery.{h,c}, ble.{h,c}
  main/board.h
firmware/wokwi/  diagram.json, wokwi.toml, SCENARIOS.md
firmware/README.md, firmware/REPORT.md（本文件）
tests/firmware/  CMakeLists.txt, host_core_test.c, host_mock_test.c,
                 host_core_cli.c, differential.py, run_host_tests.sh, README.md
```

未 commit、未 push；未修改 `mechanical/`、`electronics/`、`docs/`；未上传任何文件。
