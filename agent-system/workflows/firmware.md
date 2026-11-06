# Workflow: Firmware (F0–F4)

> 门禁：`gates/firmware.yaml`（G-FW）· 一条命令：`bash tests/firmware/run_host_tests.sh`

## 1. 阶段表

| 阶段 | 输入 | 动作 | 输出 | 证据 / 门禁 |
|---|---|---|---|---|
| F0 架构 | 电子 pinmap、状态机需求 | Application/Logic/HAL 分层；HAL 单接口 | `docs/06`、`main/` 骨架 | 纯逻辑层不依赖 SDK |
| F1 采集 | ADC 时序/数据手册 | 读取/零点/换算/滤波/异常/稳定窗 | 驱动 + mock | host + mock 测试 |
| F2 行为 | F1 + 事件定义 | 放杯/拿杯/sip/refill/干扰/外来物 | `intake.c` / `hydration.c` | C↔Python 差分 |
| F3 交互 | F2 + 屏/键规格 | 显示/刷新/息屏/手势 | `ui.c` / `oled.c` / `button.c` | pytest + host |
| F4 通信/功耗 | F2 数据模型、功耗预算 | GATT 表/notify/广播/BLE 重连/sleep | `ble.c`、PM 配置 | 构建 0 warning + 预算 |

## 2. 测试金字塔（本项目实际）

```text
pytest（Python 参考模型）        16 passed
C host 核心场景                  11/11（41 checks）
HX711 mock                       9/9（198 checks：噪声/漂移/饱和/量化/确定性）
C↔Python 差分                    16/16 场景 / 82 条记录
ESP-IDF 构建                     0 warning，bin 519,184 B
QEMU 启动冒烟                    骨架阶段（外设缺失，注明阶段）
实物 bring-up                    用户侧，11 项（未做）
```

## 3. 复用清单

- [ ] 纯逻辑层（滤波/状态机/提醒/UI 逻辑）与 SDK 解耦。
- [ ] HAL 硬件/mock 同一接口，错误码可区分。
- [ ] 标定系数集中管理并标 `PROVISIONAL`。
- [ ] 事件覆盖 happy path + 边界/异常/去抖/长按。
- [ ] 差分要有变异测试证明非空转。
- [ ] 记录 bin 大小与分区余量。
- [ ] 通信协议表（UUID/属性/频率/占空）与实现一致。

## 4. 已知失败模式

| 现象 | 根因 | 预防 |
|---|---|---|
| 测试全绿功能不对 | 只覆盖 happy path | 变异测试 + 差分 + 异常注入 |
| 电量特征恒 100 | 未接 ADC/百分比逻辑错 | 端到端特征验证 |
| host 通过当实物通过 | 无外设模型 | 报告写"待实物" |
| 灯效删除不彻底 | 遗留文件/宏 | 全仓 grep + 构建验证 |

## 5. 边界

- host/mock/差分只证明**逻辑**；HX711/OLED/BLE 射频必须上板。
- QEMU 只能做启动/逻辑冒烟（S3 SAR ADC 自校准未实现）。
