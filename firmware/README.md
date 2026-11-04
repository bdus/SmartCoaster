# firmware/

固件可行性骨架（ESP-IDF v6.1 / ESP32-S3）。本阶段目标：**不买硬件也能验证逻辑**，
硬件相关只留薄薄一层 HAL。

```
firmware/
├── model/          纯 Python 权威参考模型 + 测试（hydration / ui / hx711）
├── esp32/          ESP-IDF 工程（app_main + 分层固件 + 驱动桩）
│   ├── main/
│   │   ├── weight_sensor.h   HAL 接口 read_counts()/tare()/grams()
│   │   ├── hx711_hw.c        真实 GPIO4/5 位翻转
│   │   ├── hx711_mock.c      脚本化重量序列（host/QEMU）
│   │   ├── weight_process.c  中值 + 稳定窗 + 去尖峰
│   │   ├── intake.c          sip/refill/今日累计/模式
│   │   ├── reminder.c        提醒节奏
│   │   ├── hydration.c       门面 + 事件历史
│   │   ├── ui.c              按键手势/视图/手动模式
│   │   └── oled/button/battery/ble 驱动（BLE 为桩）
│   ├── sdkconfig.defaults
│   └── sdkconfig.qemu.defaults   QEMU 冒烟专用（UART console + 传感器 mock）
├── wokwi/          可选接线草图（离线 lint 通过；不参与验收）
└── REPORT.md       构建/测试/未完成项报告
```

## 快速开始

```bash
# 1) 主机测试：11 个模型场景 + HX711 mock + C↔Python 差分 + pytest
tests/firmware/run_host_tests.sh

# 2) 目标构建
source /home/pi/.espressif/tools/activate_idf_v6.1.sh
cd firmware/esp32 && idf.py set-target esp32s3 && idf.py build

# 3) QEMU 冒烟（UART 启动日志；可选）
idf.py -B build-qemu -DSDKCONFIG=build-qemu/sdkconfig \
       -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu.defaults" build
idf.py -B build-qemu qemu
```

详细结果、bin 大小、QEMU 结论与未完成项见 [`REPORT.md`](REPORT.md)。

## 约束

- 行为基线是 `firmware/model/`（Python），C 实现必须与之一致；
  `tests/firmware/differential.py` 逐事件比对。
- 标定系数 `counts_per_g = 515.4` 是 **PROVISIONAL**（HY928D 5 kg / 3.3 V / gain 128），
  必须实物砝码标定后才能当精度依据。
- 不上传 Wokwi 云、不使用 `WOKWI_CLI_TOKEN`。
