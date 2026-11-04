# SmartCoaster PRD 合规审计报告

> **审计快照注记（2026-11-04 20:45 由 Lead 追加）**：本报告基于 HEAD `ae17e10` 与其时实测（bin 519,152 B）。此后 Lead 修复了 BLE 0xFF04 电量特征（bin → 519,184 B / 0x7EC10）、重出 2 层装配图、校准部分文档口径；这些改动**不改变本报告任何判定**，最新状态以 `docs/REPORT_技术报告.md` 与 `docs/VERIFY_REPORT.md` §8 为准。


> 审计对象：`docs/02_Smart_Coaster_PRD.md`（M1.2 基线，2026-11-03，485 行）全文。
> 审计人：teammate `prd-audit`（只读审计；除本报告外未修改任何源码/文档）。
> 审计基线：**HEAD = ae17e10**，任务开始时工作区干净。
> 审计时间：2026-11-04 20:25–20:33（Asia/Shanghai）。
> 用户 2026-11-04 变更口径（覆盖旧设计）：**无 LED / 无光导；PCB 最多 2 层；前脸只留 26×7 屏窗 + 按键；0.5 mm 只有称重浮动缝**。

---

## 0. 结论摘要

### 0.1 判定统计

| 判定 | 数量 | 占比 | 含义 |
|---|---:|---:|---|
| **PASS** | 91 | 49.2% | 仓库内有实现/设计且有可复核证据 |
| **PARTIAL** | 50 | 27.0% | 部分实现，或实现与 PRD 数值/描述不一致，或只有仿真/主机测试而缺实物证据 |
| **GAP** | 28 | 15.1% | 需求未实现、未关闭，或实现与需求方向性不符 |
| **SUPERSEDED** | 3 | 1.6% | 旧条目被用户 2026-11-04 变更覆盖，不计缺陷 |
| **N/A** | 13 | 7.0% | 当前阶段不适用（Solar 未立项、量产、整机浸水等） |
| **合计** | **185** | 100% | 覆盖 PRD §1–§10 全部可核对条目 |

> 说明：PRD 本文里**并没有** LED/光导/4 层 PCB 的正文条目（这些出现在后续 design/CMF/PCB 文档中）。因此被用户变更直接判 SUPERSEDED 的只有 §8.1 的“总装 13 个实体”（删光导件后为 12）。另外 §3.2 中两个按键位置的 A 版数值（x=5、z=8）也按“2026-11-04 前脸 B 版布局（26×7 屏窗 + 屏右按键 x=17）”判 SUPERSEDED。详见各节与附录 A。

### 0.2 关键结论（最影响交付的 3 个 GAP）

1. **手机端闭环未实现（§7）**：仓库里没有任何手机 App；固件 BLE GATT 只做了骨架（0xFF01 重量、0xFF02 今日、0xFF03 目标、0xFF05 命令、0xFF06 时间）。**0xFF04 电量特征被硬编码为 100 且从未更新**；**没有“单次饮水量”“历史记录”“提醒间隔配置”“连接状态”特征**（`firmware/esp32/main/ble.c:31,160-177,249-261`）。设备→手机的方向有雏形，手机端→用户的功能闭环（PRD §7 第一阶段 7 项）实际未完成。
2. **M2 机械/传感器工程核实未关闭（§8.2、§9 M2）**：HY928D 的 U 形腔/拱槽仍是“图纸像素比例 + 照片估算”（`config/mechanical_params.yaml:13`、`mechanical/hy928d/notes.md`），全桥/半桥与引线未确认（`ref/HY928D_5kg_称重传感器_图纸转录.md:160-166` 8 个问题未回答），M2-01/04/05/07/08/09 仍开放；**用户要求“M2 评审通过后再开始 M3”，而 M3（原理图/PCB）已先行完成**（§10-06 流程偏离）。这直接决定“称重机构是否成立”这一产品前提。
3. **关键机械/装配收口项缺失（§4.5-03、§4.6-10、§4.6-08、§8.2 M2-09/M2-11）**：**线缆隔离/运动余量**没有设计或建模；**电池固定、绝缘、热安全、连接器线束**未设计；**USB-C 实际在“后缘居中”，与 PRD 的“前右侧 r=40、320°”相反**（`mechanical/square_v1/cad/square_model.py:207`、`electronics/kicad/scripts/gen_pcb.py:35`）。这三项都落在 M2 必须关闭的清单里，也是“唯一称重路径”和装配可靠性的直接风险。

另：M5 样机验证 6 项全部未做（无实物），属**用户侧外部依赖**，不计为设计缺陷，但仍是产品化最大剩余风险（`docs/HANDOFF.md:109-113`）。

---

## 1. 审计基线、判定口径与复跑证据

### 1.1 基线

- 被审 PRD：`docs/02_Smart_Coaster_PRD.md`（485 行，M1.2，2026-11-03）。
- 代码/制造状态基线：`git log -1` = **ae17e10**（"2-layer PCB routed to 0 DRC / 0 unconnected; remove LED & light guide everywhere"）。任务开始时 `git status --short` 为空。
- **并发改动声明**：审计期间工作区被其他并行 teammate 修改（早期观察到的 7 个文件：`config/mechanical_params.yaml`、`docs/05`、`docs/06`、`firmware/REPORT.md`、`firmware/esp32/main/app_main.c`、`mechanical/square_v1/cad/square_model.py`、`mechanical/square_v1/build/assembly/meta.json`；后续又出现构建脚本/装配图/新增产物，完整清单见附录 A）。经逐条 diff 核对，均为文档/注释修正（如 0.49in→0.91in 显示、FR-4 4-layer→2-layer、BLE/NVS 已实现的注释），**不改变本报告任何判定**；本报告引用以当前工作区版本为准，必要时注明“并发改动已修正”。清单见附录 A。
- 用户变更依据：`docs/HANDOFF.md:17-23`、`docs/07_Product_Roadmap.md:3-5`、`docs/10_CMF_and_Packaging.md:3-5`；旧设计稿 `docs/design/2026-11-04-ui-interaction-b-design.md:3-5` 已标 **OBSOLETE**。

### 1.2 判定口径

| 判定 | 判定规则 |
|---|---|
| **PASS** | 需求在仓库内有对应实现/文件/测试，且本审计实际打开文件或复跑命令确认；数值/口径与 PRD 一致。 |
| **PARTIAL** | 已做一部分；或实现存在但数值/位置/描述与 PRD 不一致；或只有 CAD/仿真/主机测试，缺实物或供应商依据（PRD 自己标 PROVISIONAL/待核实的，不因“未实测”判 GAP）。 |
| **GAP** | PRD 要求的功能/结构/文档在仓库中缺失，或实现方向与需求相反，或里程碑验收项未关闭且无证据。 |
| **SUPERSEDED** | 旧条目已被用户 2026-11-04 变更覆盖，**不计为缺陷**。 |
| **N/A** | 当前阶段不适用：Solar 未立项、M6 产品化未到、量产工艺/整机浸水等非要求项。 |

### 1.3 本次实际复跑证据（非引用文档结论）

| # | 检查 | 命令 | 结果 |
|---|---|---|---|
| E1 | 机械自检 | `cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py` | **exit 0，21/21 PASS**：12 solids、bbox 100×100×18、37 对干涉 0、0.5 浮动缝、STEP 回读 12 solids |
| E2 | PCB DRC | `kicad-cli pcb drc --format report --severity-all --units mm -o /tmp/prd_DRC_2l.rpt smartcoaster/smartcoaster_2l.kicad_pcb` | **exit 0；Found 0 violations / 0 unconnected pads / 0 Footprint errors**（2026-11-04T20:26:33） |
| E3 | 原理图 ERC | `kicad-cli sch erc --severity-all --format report` | **exit 0；ERC messages: 0 Errors 0 Warnings** |
| E4 | 固件主机测试 | `BUILD_DIR=/tmp/prd-host-build2 bash tests/firmware/run_host_tests.sh` | **exit 0**：CTest 2/2 passed；差分 **16/16 场景、82 条记录**；pytest **16 passed** |
| E5 | ESP-IDF 构建 | `source activate_idf_v6.1.sh; cd firmware/esp32 && idf.py build` | **exit 0 / Project build complete**；`build/smartcoaster.bin` = **519,152 B** |
| E6 | PCB 实体统计 | 解析 `smartcoaster_2l.kicad_pcb` | 47 footprint、576 segment、63 个 `(via`（verifier 口径 62 via）、**仅 F.Cu/B.Cu 两层**、28 信号网 + net0；refs 无 D1/Q1–Q3/R13–R21/TP |
| E7 | BLE 电量缺陷 | `grep -n 's_batt' firmware/esp32/main/ble.c` | 仅 `:31 static uint8_t s_batt = 100;`、`:118-119` 读、`:171` 注册；**无任何赋值/更新路径**（`ble_update()` 无 battery 参数，见 `ble.c:249-261`） |
| E8 | 手机 App 缺失 | `find . -maxdepth 2 -type d` | 无 `app/`、`mobile/`、`android/`、`ios/` 等目录；仅固件 BLE 外设侧 |
| E9 | Solar 未启动 | `grep -rIil -e solar -e 光伏 -e 能量采集 docs firmware electronics` | 仅 PRD/管线/旧文档提及；无 Solar 代码/硬件 |

> 注：E1 的 `verify_v01.py` 会按其脚本尾部固定行为重写 `mechanical/square_v1/build/verify_report.json`（内容与 21/21 结果一致）。本审计未修改任何源码或 PRD；唯一新增写入为 `docs/AUDIT_PRD.md`。

---

## 2. 分节明细

### §1 产品概述（PRD 10–43 行）

| 编号 | 需求摘要 | 判定 | 证据（路径:行 / 输出） | 差距与说明 |
|---|---|---|---|---|
| PRD-1.1-01 | 定位：称重饮水提醒 + 饮水量估算的桌面设备 | PASS | `firmware/esp32/main/hydration.c`、`intake.c`、`reminder.c`；`firmware/model/` 16 passed；E4 | 功能定义已由固件逻辑层+主机测试落地 |
| PRD-1.1-02 | 极简、融入家居/办公外观 | PASS | `mechanical/square_v1/README.md:10-20`；`docs/10_CMF_and_Packaging.md:5-10`（前脸只有屏窗+按键） | 风格满足；配色见 PRD-3.1-05 |
| PRD-1.1-03 | 无需用户每次手动记录 | PASS | `intake.c:34-94`（重量变化自动累计）；E4 差分场景 py01 | 自动 sip/refill/累计 |
| PRD-1.1-04 | 基于重量变化估算饮水量 | PASS | `firmware/model/hx711.py`、`hydration.py`；`firmware/esp32/main/hx711_hw.h:21-23`（counts/g 换算） | 质量→体积近似换算已实现 |
| PRD-1.1-05 | 低干扰提醒方式 | PASS | `reminder.c:6-23`（60 min + 10 min 冷却）；`app_main.c` render_frame 仅屏上提示；`ui.c:57-63` 单击 snooze | 无蜂鸣/振动/灯，符合低干扰 |
| PRD-1.1-06 | 设备与手机无线同步 | PARTIAL | `ble.c:160-177`（GATT 0xFF00 外设）；但无手机 App（E8），电量特征恒 100（E7），单次/历史/提醒配置缺特征 | 外设侧骨架有；端到端同步未闭环 |
| PRD-1.1-07 | 结构简单、可维护、可迭代 | PASS | `mechanical/square_v1/cad/square_model.py:307-320`（PARTS 12 件，单实体）；E1；`mechanical/square_v1/v1..v6_square_v1` 版本快照 | 可拆顶板/12 件/版本化 |
| PRD-1.2-01 | 核心闭环 7 步（放杯→基线→检测→事件→估算→累计→提示/BLE） | PASS | `hydration.c:70-113` 串联三层；E4 场景 py01/py02/py05；QEMU 日志 `firmware/REPORT.md:329-343` | 逻辑闭环已被差分测试覆盖 |

### §2 产品版本规划（PRD 47–79 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-2.1-01 | 主控 ESP32-S3 | PASS | `electronics/kicad/scripts/design.py:110-113`（U1 ESP32-S3-MINI-1）；`firmware/esp32/CMakeLists.txt`；E5 | 选型与固件目标一致（esp32s3） |
| PRD-2.1-02 | 称重传感器 HY928D，5 kg 量程候选 | PARTIAL | `config/mechanical_params.yaml:2-13`（capacity_kg 5，status provisional）；`mechanical/hy928d/notes.md` | 选型/建模有；桥路、量程、灵敏度待供应商确认 |
| PRD-2.1-03 | 称重 ADC HX711 候选 | PASS | `design.py:127-130`（U2 HX711 SOP-16）；`firmware/esp32/main/hx711_hw.c` | 芯片级集成（非模块）已设计+驱动 |
| PRD-2.1-04 | 供电 USB-C + 可充电电池 | PASS | `design.py:54-107`（J1、TP4056、DW01A+FS8205A、LDO）；`BOM.csv` J1/J2/U3/U4/U5 | 500 mAh LiPo + 充电 + 保护 |
| PRD-2.1-05 | 通信 BLE | PARTIAL | `ble.c`（NimBLE GATT 已实现）；E5 | 外设侧有；手机 App 无；电量/单次/历史特征缺（同 PRD-7.x） |
| PRD-2.1-06 | 显示小尺寸 OLED | PASS | `square_model.py:79-80,92`（0.91" 128×32，窗 26×7）；`oled.h:19-20`（128×32）；`design.py:156-159`（J4） | PRD 只说“小尺寸”，实现 0.91" |
| PRD-2.1-07 | 一个实体圆形按键 | PASS | `square_model.py:81,288-292`（Ø8.2 圆键）；`button.h`（单击/双击/长按）；`design.py:164-167`（J5） | 单键+手势 |
| PRD-2.1-08 | 方形、极简家居外壳 | PASS | `square_model.py:30-38`（100×100，R8，18 mm）；`README.md:10-12` | 方形 V1 |
| PRD-2.1-09 | HY928D/HX711 兼容性未验证，不得当既成事实 | PASS | `config/mechanical_params.yaml:13`（provisional）；`square_model.py:52-56`（PROVISIONAL 注释）；`firmware/REPORT.md:386-388` | 未越界声称兼容 |
| PRD-2.2-01 | Solar 版无屏幕 | N/A | — | 未立项，PRD 明确“普通版闭环后再立项”（PRD:68-79）；E9 无 Solar 工件 |
| PRD-2.2-02 | Solar 低功耗 BLE MCU | N/A | — | 同上 |
| PRD-2.2-03 | Solar 光伏/能量采集 | N/A | — | 同上 |
| PRD-2.2-04 | Solar 重评采样/唤醒/能量预算 | N/A | — | 同上 |
| PRD-2.2-05 | Solar 不复用普通版方案、闭环后再立项 | PASS | E9：仓库无 Solar 代码/硬件；`docs/07_Product_Roadmap.md` 仅普通版 P1–P3 | 未提前启动 Solar，约束被遵守 |

### §3 外观与人机交互（PRD 85–118 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-3.1-01 | 外形正方形 | PASS | `square_model.py:30-32`（L=W=100，R8）；E1 bbox | — |
| PRD-3.1-02 | 初始外廓 100×100 mm | PASS | `square_model.py:30-31`；E1 `100.000 x 100.000 x 18.000` | — |
| PRD-3.1-03 | 外轮廓圆角 R8 | PASS | `square_model.py:32`（CORNER_R=8.0） | — |
| PRD-3.1-04 | 总高度 18 mm | PASS | `square_model.py:34-38`；E1 bbox | — |
| PRD-3.1-05 | 配色白色或浅灰色 | PARTIAL | `square_model.py:114-116`（shell `#EFEDE6` 暖白渲染）；但 `docs/10_CMF_and_Packaging.md:20-32` 主色 Lumen Violet（紫/炭灰） | CAD 颜色与 CMF 主色不一致；PRD 白/浅灰未同步到 P3 CMF，需用户确认最终配色 |
| PRD-3.1-06 | 极简、克制风格 | PASS | `docs/10_CMF_and_Packaging.md:5-10`；`submission/02_front.png` 目视仅屏窗+按键 | — |
| PRD-3.1-07 | 高度构成：底座 15 mm + 顶板 3 mm | PARTIAL | `square_model.py:34-37`（BASE_H=14.5 + GAP 0.5 + PLATE_T 3）；`README.md:11`；E1 | 总高 18 一致，但“底座 15”实为 14.5 壳 + 0.5 浮动缝；PRD 未说明该缝 |
| PRD-3.2-01 | 以前缘 Y 负方向布局控件 | PASS | `square_model.py:19`（front=-Y）、`:202-204`（窗/键在 -Y）；`gen_pcb.py:9-10` | — |
| PRD-3.2-02 | 左侧圆形实体按键 Ø8.2，中心 x=5 | SUPERSEDED | 实现 `square_model.py:81`（BTN_X=17）；`README.md:13`；`docs/07:24` 记 x=17；A 版 x=5 见 PRD 原文 | Ø8.2 保留；x=5 为 A 版坐标，被 2026-11-04 前脸 B 版布局（屏右 x=17）覆盖，不计缺陷 |
| PRD-3.2-03 | 右侧 OLED 0.91" 128×32、窗口 26×7、中心 x=−8 | PASS | `square_model.py:79-80,92`；`design.py:156-159`；`oled.h:19-20` | 与 B 版口径一致 |
| PRD-3.2-04 | 屏与键同一水平线，基准 z=8 mm | SUPERSEDED | 实现 `square_model.py:79`（OLED_Z=8.0）、`:81`（BTN_Z=7.2）；`README.md:13`（同一水平线 z=7.2） | A 版 z=8 被 B 版 z=7.2（避让裙边）覆盖；不计缺陷 |
| PRD-3.2-05 | 控件固定底壳，不与浮动顶板连接、不参与称重路径 | PASS | `square_model.py:201-210`（前壁开窗/按键孔，控件在壳侧）；E1 第 10–13 项：OLED 14.00<14.50、按键 11.70<12.40、行程 11.70<11.90、notch volume 0 | 几何 clear 证明；实际固定支架/线束仍属 M2-10/M2-11 待办（见 §8.2） |
| PRD-3.3-01 | OLED 尽量小 | PASS | `square_model.py:79-92`（0.91"，可视窗 26×7）；`oled.h:19-20` | — |
| PRD-3.3-02 | 按键用于主动交互，逻辑固件阶段定义 | PASS | `button.h`（30 ms 去抖/单击/双击/长按 2 s/5 s）；`ui.c:57-103` | 交互逻辑已定义并测试 |
| PRD-3.3-03 | 屏幕少量有用信息、不复杂 UI | PASS | `app_main.c` render_frame（2 行 + 进度条）；`oled.c:19-20`（128×32） | — |
| PRD-3.3-04 | 显示内容/刷新策略兼顾可读性与功耗 | PARTIAL | `app_main.c:422`（8 s 息屏）；`oled.c` 局部刷新；`docs/08_Power_Sleep_Plan.md` 估算 2–3 mA | 策略已实现；可读性（26×7 窗/中文字号）与功耗**均未实物实测** |

### §4 机械结构需求（PRD 121–239 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-4.1-01 | 结构组成：底壳/浮动顶板/HY928D/四角支撑/中央传力/C 形 PCB/前缘屏键/电池+USB-C | PASS | `square_model.py:307-320`（PARTS 12 键）；E1 12 solids | 8 类结构均有对应件 |
| PRD-4.1-02 | 总高 18、顶板 3、底座 15 | PARTIAL | `square_model.py:34-38`；`README.md:11` | 同 PRD-3.1-07：底座实为 14.5+0.5 缝 |
| PRD-4.2-01 | 四角固定、中央受力、传力柱、载荷经应变梁到四角/底壳 | PASS | `square_model.py:188-194`（四角 boss/中央Ø12 垫块）、`:224-235`（顶板+Ø6 柱）；E1 第 6 项 column lands z=6.00；FEA `simulation/mechanical/hy928d/README.md`（支反力 100%） | CAD 设计与 FEA 趋势支持该路径 |
| PRD-4.2-02 | 该路径尚待 HY928D 真实结构/供应商要求核实 | PASS | `mechanical/hy928d/notes.md:3-5`；`docs/VERIFY_REPORT.md:19`；`config/mechanical_params.yaml:13` | 文档未把设计意图当已核实事实 |
| PRD-4.3-01 | 外形 34×34×1.0 mm | PASS | `square_model.py:57-58`；`config/mechanical_params.yaml:7,9`；`ref` 图纸 | 与图纸硬尺寸一致 |
| PRD-4.3-02 | 外角 4-R3 | PASS | `square_model.py:239`（RectangleRounded 34, R3） | — |
| PRD-4.3-03 | 安装孔 4×Ø3.1 | PASS | `square_model.py:60,245-248` | 图纸硬尺寸 |
| PRD-4.3-04 | 孔位 X/Y=±14、孔距 28 | PASS | `square_model.py:61,247`（HOLE_PITCH/2=14） | — |
| PRD-4.3-05 | 中心孔 Ø5 | PASS | `square_model.py:62,243`；`config/mechanical_params.yaml:10` | 孔存在；功能含义仍开放（M2-01） |
| PRD-4.3-06 | 应变区中央 U 形腔；梁宽 2.5 / 腔宽 10 / 腔长 29 / 腔深 0.7 / 2-R9（推算） | PARTIAL | 总装仍用 `square_model.py:238-249`（`SlotOverall(29,10)`，无 R9）；重建版 `mechanical/hy928d/src/hy928d_v2.py` + `notes.md:3-5`（通槽 2.5 宽 + 拱槽，待检视）；`config/mechanical_params.yaml:11-13` | PRD 表与两版模型均不完全对应；v2 重建未替换总装、未经供应商确认 |
| PRD-4.3-07 | 量程 5 kg（候选/待实物确认） | PARTIAL | `config/mechanical_params.yaml:3`；`ref` 图纸；FEA 5 kg | 选型候选，无供应商批次数据 |
| PRD-4.3-08 | 上述参数只描述 CAD，不得据模型认定实物 | PASS | `square_model.py:52-56`；`mechanical/hy928d/notes.md:3-5`；`docs/VERIFY_REPORT.md:227-232` | PROVISIONAL 保留 |
| PRD-4.4-01 | 四角 boss Ø6、高 3、顶面 z=5.0 | PARTIAL | `square_model.py:189-193`（实际 `Cylinder(3.5,3.0)` → **Ø7**，顶面 z=5.0） | 直径 Ø7 vs PRD Ø6；高度/顶面一致 |
| PRD-4.4-02 | 固定孔 Ø2.8 沉孔占位（螺钉方案待确认） | GAP | `square_model.py:192-193`（实际挖 Ø2.1 通孔，无沉孔）；`README.md:10` 未提螺钉规格 | 无 Ø2.8、无沉孔、无螺钉规格；M2-07 同项开放 |
| PRD-4.4-03 | 中央垫块 Ø12、高 0.8（作用待核实） | PARTIAL | `square_model.py:194`（`cyl(6.0, 2.2, FLOOR)` → Ø12、顶面 z=4.2；距传感器底面 0.8） | 直径一致；PRD 的“高 0.8”实为**间隙 0.8**，高实为 2.2；语义需统一 |
| PRD-4.4-04 | 传力柱 Ø6，z=6.0→15.0 | PASS | `square_model.py:49`（COL_R=3→Ø6）、`:227`（z 6..14），顶部 Ø16 boss 至 15；E1 第 6 项 | 柱主体 Ø6，顶部过渡到Ø16 与顶板相连 |
| PRD-4.4-05 | 浮动顶板 100×100×3，底面 z=15.0 | PASS | `square_model.py:35-37,216-217`；E1 bbox | — |
| PRD-4.4-06 | 过载限位间隙 0.5 mm | PASS | `square_model.py:36`；E1 第 5、15、16、18 项：gap 0.500、5 kg 余 0.157 mm、7.28 kg 接触 | 有 CAD 依据，但额定形变仍缺（M2-06） |
| PRD-4.4-07 | 传力柱端部形状（平底/球头）未冻结；中央垫块功能待确认 | PASS | `square_model.py:228-229`（仅 0.4 倒角，未冻结）；`notes.md`/FEA README 明确边界假设 | 状态如实，无虚假冻结 |
| PRD-4.5-01 | 螺钉/铜柱、屏及支架、按键、PCB、电池、线缆、外壳边缘不得形成额外刚性连接 | PARTIAL | E1 第 14–19 项（行程畅通、37 对 0 干涉、0.05 下无件）；`square_model.py:188-210` | 屏/键/PCB/电池/壳边 clear 已证；**螺钉/铜柱、线缆未建模**，无法证其不旁路 |
| PRD-4.5-02 | 过载限位允许到规定位移后接触，正常行程不得提前接触 | PASS | E1 第 14、16、18 项（down-travel blocked []；7.28 kg 才接触；接触体积 30.47 mm³） | — |
| PRD-4.5-03 | 线缆留运动余量，不得跨越浮动间隙形成支撑 | GAP | 机械 PARTS 无 cable/线束件（`square_model.py:307-320`）；`README.md`/`docs/09_Assembly.md` 无走线设计 | 完全未设计/未验证 |
| PRD-4.6-01 | 板形：内腔 93.2×93.2、R6 | PASS | `square_model.py:68-69`；`gen_pcb.py:14-16`；E6 板框 | — |
| PRD-4.6-02 | 中央开口 38×38 方形 | PASS | `square_model.py:72,253`；`gen_pcb.py:18-19`；E6 | 非圆形，符合要求 |
| PRD-4.6-03 | 前缘开口 70° C 形缺口 | PARTIAL | `square_model.py:73`（PCB_GAP_DEG=80.0）、`:254`；`gen_pcb.py:27`（GAP_DEG=80.0）；`README.md:12` | 实际 **80°**，与 PRD 70° 不符；PRD/机械/PCB 未同步更新 |
| PRD-4.6-04 | 板厚 1.6 mm | PASS | `square_model.py:70`（PCB_T=1.6）；`smartcoaster_2l.kicad_pcb` 叠层；`build/DFM.md`（厚度 1.6） | — |
| PRD-4.6-05 | 层级：与传感器同层 z=5.0 | PASS | `square_model.py:71`（PCB_Z=5.0）；E1 第 8 项 PCB 开口清传感器 2.00 mm/side | — |
| PRD-4.6-06 | ESP32-S3 占位 18×25，后右约 (32,31) | PARTIAL | `square_model.py:85-86`（ESP_POS=(29,32)）；`gen_pcb.py:32`（U1 (29,-32)）；`S3_FOOTPRINT.md` | 尺寸 18×25 一致；位置 (29,32) vs PRD (32,31)，差 3 mm/1 mm（为壳腔收敛，见 S3_FOOTPRINT.md） |
| PRD-4.6-07 | HX711 12×15，右侧约 (36,0) | PARTIAL | `square_model.py:87-88`（HX_POS=(40,0)）；`gen_pcb.py:33`（U2 (39,0)） | 尺寸一致；模型 x=40 vs PRD 36；PCB x=39；三处未统一 |
| PRD-4.6-08 | USB-C 8.94×7.5，前右侧约 r=40、320° | GAP | 机械 `square_model.py:206-207` 后缘居中（`Pos(0, L/2, 8.4)`）；PCB `gen_pcb.py:35`（J1 rear edge）；`README.md:14`（后缘 USB-C） | **位置与 PRD 相反**：PRD 前右，实际后中；PRD 未更新 |
| PRD-4.6-09 | 电池 25×30×5，后左约 (−32,24)，z=6.6 | PASS | `square_model.py:90-91`（BAT_POS=(-32,24)，z 6.6）；E1 第 9 项 battery clears skirt 11.60<12.40 | — |
| PRD-4.6-10 | 电池固定/绝缘/热安全/连接器/线缆布置 | GAP | 机械仅电池占位体（`square_model.py:277-280`）；无电池仓/压板/绝缘件；`README.md`/`docs/09` 无 | M2-09 同项开放；属安全项 |
| PRD-4.7-01 | 顶板表面便于日常擦拭 | PASS | `square_model.py:215-235`（平板+细蚀刻槽）；`docs/10:11-14`（阳极氧化铝/哑光） | — |
| PRD-4.7-02 | 不要求整机浸水 | N/A | — | 非要求项 |
| PRD-4.7-03 | 适合 3D 打印原型 | PASS | `mechanical/square_v1/build/parts/*.stl`（12 件）；`build/assembly/assembly_v01.stl` | 打印件已出 |
| PRD-4.7-04 | 关键螺钉柱、壁厚、装配间隙需 M2 核实 | PARTIAL | `square_model.py:40-41`（WALL 2.4/FLOOR 2.0）、`:188-199`（boss/standoff 占位 Ø7/Ø6.5） | 壁厚已定；螺钉柱/装配间隙无 M2 核实记录 |
| PRD-4.7-05 | 量产工艺和材料不在 M1.2 冻结范围 | N/A | — | 非当前阶段要求 |

### §5 电子系统需求（PRD 243–306 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-5.1-01 | 系统组成：HY928D→HX711→ESP32-S3；OLED/按键/BLE/电池管理/USB-C | PASS | `design.py:52-176`（43 器件，含 J1/U7/U3/U4/U5/U6/U1/U2/J4/J5/R6/R7）；E3 ERC 0/0；`pinmap.md` | 功能框图全部落地 |
| PRD-5.1-02 | 框图是功能架构，不代表原理图已完成 | PASS | 实际已完成原理图；文档未越界 | 状态已前进，无虚假声明 |
| PRD-5.2-01 | 记录候选电气参数（5 kg、1.2/0.6 mV/V、3–10 V、1 kΩ±10%、线色） | PASS | `config/mechanical_params.yaml:2-13`；`ref/HY928D_5kg_称重传感器_图纸转录.md`；`pinmap.md` | 参数已集中记录 |
| PRD-5.2-02 | 桥路/灵敏度/引线以供应商资料或实测为准 | GAP | `notes.md`/`ref:160-166` 8 个问题未回答；`config:13` provisional；`hx711_hw.h:23` counts/g PROVISIONAL | 尚无供应商确认或实测 |
| PRD-5.2-03 | 不得默认 HY928D 为全桥，不得仅凭线色接线 | PARTIAL | 设计实际按**全桥 1.2 mV/V** 做前端（`design.py:127-150` J3 四线；`simulation/.../README.md`）；文档同时声明待确认 | 架构已押注全桥；若实物半桥需补桥/改前端（M2-04） |
| PRD-5.3-01 | 输入接法（结合最终桥路确认） | PARTIAL | `design.py:230-234`（HX_S_P/N → 1k+100nF RC → A+/A-）；`simulation/.../hy928d_frontend.json` | 全桥差分输入已设计；半桥/引线未确认 |
| PRD-5.3-02 | 激励供电 | PASS | `pinmap.md:1-38`（VSUP=DVDD=AVDD=3.3V、VFB=GND、BASE=NC）；`design.py:203-208`（3V3 接 U2.1/3/16）；`NETLIST.md` 3V3 网 | 3.3 V 外部激励，方案明确 |
| PRD-5.3-03 | 是否需要补桥 | PARTIAL | `design.py` 无补桥元件（假设全桥）；`pinmap.md:38` | 未确认半桥前无法定论 |
| PRD-5.3-04 | PGA 增益 | PASS | `design.py:130`（gain 128）；`pinmap.md:31`；`hx711_hw.h` | 固定 128 |
| PRD-5.3-05 | 输出采样速率 | PASS | `design.py:130`（10 Hz）；`NETLIST.md`（U2.14 RATE→GND）；`board.h`（10 Hz）；`app_main.c` 100 ms 采样 | RATE=GND 10 SPS，固件匹配 |
| PRD-5.3-06 | 电源与模拟地布局 | PARTIAL | 2 层板无铺铜分区（`VERIFY_REPORT.md:60` ZONES=0）；`design.py` 无模拟域/磁珠隔离；`DFM.md` 未评估 | 模拟/数字地未做专门分区或电源完整性分析 |
| PRD-5.3-07 | 噪声、漂移、稳定时间 | PARTIAL | `hy928d_frontend.json`（50 nVrms 数据手册引用、RC 1.65 kHz）；`firmware/model/hx711.py`（噪声/温漂模型）；无实测 | 只有行为级仿真/模型，无实物噪声/漂移/稳定时间 |
| PRD-5.3-08 | HX711 配置应在传感器电气参数确认后冻结 | GAP | `design.py` REV=0.1-DRAFT（`:13`）；`hx711_hw.h:23` PROVISIONAL | 传感器参数未确认，配置已按假设冻结在设计中 |
| PRD-5.4-01 | 充电管理 | PASS | `design.py:69-72`（TP4056 ESOP-8，Rprog 2.4k/500 mA）；`BOM.csv` U3 | — |
| PRD-5.4-02 | 电池保护 | PASS | `design.py:85-96`（DW01A+FS8205A+R11/C4/R12）；`BOM.csv` U4/U5 | — |
| PRD-5.4-03 | 供电路径 | PARTIAL | `pinmap.md:7-18`（USB→TP4056→LiPo→LDO→3V3；5 V 仅充电）；`design.py` 无负载共享/理想二极管 | 无真正 power-path/负载共享；仅“充电时由电池供电” |
| PRD-5.4-04 | ESP32-S3 与 HX711 的电源域 | PASS | `pinmap.md:12-16`（HX711 DVDD/AVDD/VSUP=3.3V）；`NETLIST.md` 3V3 网 | 同域 3.3 V，已文档化 |
| PRD-5.4-05 | 待机功耗 | PARTIAL | `app_main.c:338`（PM light sleep 160/80 MHz）；`docs/08_Power_Sleep_Plan.md`（估算 2–3 mA → 7 天级） | 只有估算，未实测（M5） |
| PRD-5.4-06 | 电量检测 | PASS | `design.py:170-175`（R6/R7 100k 分压 + C13）；`battery.c`（ADC curve fitting） | 分压→GPIO1，ADC 校准 |
| PRD-5.4-07 | 低电量提示 | GAP | `app_main.c:145-150` 仅显示 `BAT %`；全仓无低电量阈值/告警逻辑（grep `low_batt/低电量` 仅 battery_percent 定义）；`docs/10:53` 声称“低电量=屏上角标” | 无低电量判定与主动提示 |
| PRD-5.4-08 | USB-C 插拔空间与机械固定 | PARTIAL | `square_model.py:206-207`（壳后壁开窗 9.2×3.3）；`gen_pcb.py:35`（J1 rear）；无固定/加固结构 | 开窗有；位置在后缘（见 4.6-08），无机械固定设计 |

### §6 固件与算法需求（PRD 310–347 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-6.1-01 | HX711 数据读取 | PASS | `hx711_hw.c`（GPIO4/5 位翻转、25 脉冲、超时）；`hx711_mock.c`；E4 mock 9/9 | 驱动已实现；时序未实测（M5） |
| PRD-6.1-02 | 上电稳定与初始化 | PARTIAL | `app_main.c:308-336`（初始化顺序）；`hx711_hw.c:118-163`（GPIO/漂移）；启动未做自动零点/预热 | 有初始化；无上电自动稳零/预热流程 |
| PRD-6.1-03 | 零点校准 | PARTIAL | 手动长按 2 s 去皮 `ui.c:78-86`→`app_main.c:214-219`；`hx711_hw.c:156` 默认 offset=0 | 仅手动 tare；自动零点/砝码量程校准未做（M4-02） |
| PRD-6.1-04 | 滤波与异常值处理 | PASS | `weight_process.c`（5 点中值 + 0.3 s 稳定窗 + 40 g 尖峰门）；E4 py03/py04/x04 | 有测试覆盖 |
| PRD-6.1-05 | 空杯/有杯状态判断 | PASS | `intake.c:34-58`（EMPTY/HYDRATION/SCALE）；E4 py01/py05 | — |
| PRD-6.1-06 | 杯子放置和拿起检测 | PASS | `intake.c:34-45,60-94`（cup_removed/cup_placed）；E4 py01 | — |
| PRD-6.1-07 | 稳定重量基线维护 | PASS | `intake.c`（last_weight/last_stable）；`weight_process.c` 稳定窗 | — |
| PRD-6.2-01 | 识别杯子稳定放置 | PASS | `intake.c:60-94`；E4 py01 | — |
| PRD-6.2-02 | 建立当前重量基线 | PASS | `intake.c:60-94`（last_weight）；`hydration_tare_cup` | 配杯长按可设杯皮重 |
| PRD-6.2-03 | 检测持续的重量下降 | PARTIAL | `intake.c:66-72`（用“拿开前基线 − 放回后重量”的差值，非连续下降斜率） | 语义可实现饮水识别，但实现方式与 PRD 字面“持续下降”不同 |
| PRD-6.2-04 | 区分饮水/拿杯/移动杯子/外部碰撞 | PASS | `intake.c` 模式/阈值；E4 py03（噪声）/py04（尖峰）/py05（外来物）/py02（refill） | 主机/差分测试覆盖 |
| PRD-6.2-05 | 判断事件结束 | PASS | `intake.c:60-94`（放回并稳定后结算）；`weight_process.c` 稳定窗 | — |
| PRD-6.2-06 | 估算本次饮水量 | PASS | `intake.c:66-72`（delta 计为 ml）；E4 py01（50 g） | 水质量≈体积近似 |
| PRD-6.2-07 | 更新当日累计饮水量 | PASS | `intake.c:69`（today_ml += delta）；`hydration.c` | — |
| PRD-6.2-08 | 处理杯重、加水/补水、移动、重新放置 | PASS | `core_types.c:33-48`（cup_tare 300 g/max 1500 g）；`intake.c` refill 不计入；E4 py02/py07 | 杯皮重可配；refill 不计量 |
| PRD-6.3-01 | 按时间间隔提醒 | PASS | `reminder.c:6-23`（reminder_min=60）；`core_types.c:41`；E4 py06 | 60 min 默认 |
| PRD-6.3-02 | 用户主动饮水后调整下一次提醒 | PASS | `intake.c:69`（last_drink_t）；`reminder.c:16` | sip 后重新计时 |
| PRD-6.3-03 | 避免短时间重复提醒 | PASS | `reminder.c:19-21`（cooldown 600 s）；`core_types.c:47`；E4 x03 | — |
| PRD-6.3-04 | 提醒方式低干扰 | PASS | `app_main.c` 屏上“该喝水了”；`ui.c:57-63` 单击 snooze；无蜂鸣/LED | — |
| PRD-6.3-05 | 后续允许手机端调整提醒策略 | PARTIAL | `ble.c:167-169`（0xFF03 goal 可写）；无 reminder interval/snooze 特征；无 App（E8） | 只能改目标，不能改提醒间隔/静音策略 |
| PRD-6.3-06 | 具体间隔与配置方式待固件阶段定义 | PASS | 已定义：60 min、2200 ml、10 min 冷却（`core_types.c:33-48`） | 状态已前进，无虚假声明 |

### §7 手机端需求（PRD 350–364 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-7.1-01 | 设备发现与连接 | PARTIAL | `ble.c:65-107`（GAP 广播，开机 30 s/配对 120 s/空闲关）；`app_main.c:338-345`；无手机 App（E8） | 外设可被扫描连接；手机侧无实现 |
| PRD-7.1-02 | 当前杯子重量或饮水状态 | PARTIAL | `ble.c:161-166`（0xFF01 weight read+notify）；模式（EMPTY/HYDRATION/SCALE）未作为特征暴露 | 有重量；饮水状态/模式未在 GATT 暴露 |
| PRD-7.1-03 | 单次饮水量 | GAP | `ble.c:160-177` 无“last sip”特征；sip 仅在内部事件（`hydration.h` events[256]） | 手机取不到单次饮水量 |
| PRD-7.1-04 | 当日累计饮水量 | PARTIAL | `ble.c:164-166`（0xFF02 today read+notify）；无 App（E8） | 外设有；手机端无 |
| PRD-7.1-05 | 历史记录 | GAP | `hydration.h` events[256] 仅内存；`storage.c` 只存 today/goal/tare/mode；BLE 无历史特征；无 App | 断连/重启即丢历史，手机无记录 |
| PRD-7.1-06 | 提醒配置 | GAP | `ble.c:167-169` 仅 goal 可写；reminder_min 不可写；无 App | 无法通过手机配置提醒策略 |
| PRD-7.1-07 | 设备电量与连接状态 | GAP | `ble.c:31` `s_batt = 100` 硬编码且无更新；`ble_update()` 无 battery 参数（`:249-261`）；连接状态无特征 | 电量恒报 100%，连接状态只能靠 GATT 链路间接判断 |
| PRD-7.1-08 | 优先核心数据同步；不引入复杂云/账号 | PASS | `ble.c` 本地 GATT；`storage.c` NVS；无云端依赖（E8/E9） | 架构符合本地优先 |
| PRD-7.1-09 | 数据存储策略/跨设备同步后续评估 | N/A | — | PRD 明确“后续再评估” |

### §8 当前设计状态与风险（PRD 368–408 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-8.1-01 | M1.2 完成 100×100×18 外壳 | PASS | E1 bbox；`square_model.py:30-38` | — |
| PRD-8.1-02 | R8 外轮廓 | PASS | `square_model.py:32` | — |
| PRD-8.1-03 | HY928D 真实外形占位模型 | PARTIAL | 总装仍用简化 `make_load_cell`（`square_model.py:238-249`）；v2 重建 `mechanical/hy928d/`（notes.md:3-5 “待人工检视，不替换总装”） | 真实外形模型已重建但未集成/未确认 |
| PRD-8.1-04 | 四角支撑与中央传力结构 | PASS | `square_model.py:188-194,224-235`；E1 第 6 项 | — |
| PRD-8.1-05 | 浮动顶板 | PASS | `square_model.py:215-235`；E1（plate skirt 0.80 mm/side） | — |
| PRD-8.1-06 | C 形环绕 PCB | PASS | `square_model.py:252-258`；`gen_pcb.py` 板框；E6 | C 环（80°，见 4.6-03） |
| PRD-8.1-07 | ESP32-S3/HX711/USB-C/电池空间占位 | PASS | `square_model.py:261-285`；`gen_pcb.py:29-55`；E6 | 占位齐全 |
| PRD-8.1-08 | 总装 13 个实体 | SUPERSEDED | 现为 **12 件**（`square_model.py:307-320`；E1；`config:23`）；用户 2026-11-04 删除光导件 | 被用户变更覆盖，不计缺陷 |
| PRD-8.1-09 | XY/Z 几何无干涉检查 | PASS | E1 第 19 项 37 pairs []；第 20–21 项 STEP 回读 | — |
| PRD-8.2-01 | M2-01 中心 Ø5 孔功能含义 | GAP | `ref/HY928D...图纸转录.md:160-166` 问题 3 未答；`mechanical/hy928d/notes.md` 仍为待检视 | 未关闭 |
| PRD-8.2-02 | M2-02 U 形腔真实尺寸/应变梁结构 | PARTIAL | `mechanical/hy928d/notes.md:6-17`（图像比例/照片推断）；v2 待人工检视 | 有重建，无供应商/剖视确认 |
| PRD-8.2-03 | M2-03 应变梁方向 | PARTIAL | `ref/HY928D...:84-100`（两种受力结构“必须二选一”）；FEA 采用假设 A | 方向未最终确认 |
| PRD-8.2-04 | M2-04 全桥/半桥及引线定义 | GAP | `config:5-6`（1.2/0.6 候选）；`ref/HY928D...:158` “⚠待确认”；8 问题第 4 条未答 | 未关闭 |
| PRD-8.2-05 | M2-05 实际灵敏度与激励范围 | PARTIAL | `hy928d_frontend.json`（3.956 mV@5 kg，理论）；`ref` 图纸 1.2 mV/V 候选 | 只有理论/仿真，无批次数据 |
| PRD-8.2-06 | M2-06 额定形变量与安全位移 | PARTIAL | FEA `simulation/mechanical/hy928d/README.md:1-8`（5 kg 0.3435 mm）；E1 第 15 项（余 0.157 mm） | 有 FEA 趋势；额定值仍待供应商（8 问题第 5 条） |
| PRD-8.2-07 | M2-07 螺钉规格及固定方式 | GAP | `square_model.py:192-193`（占位 Ø2.1 通孔，无规格）；PRD 4.4-02 待确认 | 未关闭 |
| PRD-8.2-08 | M2-08 传力柱端部结构 | GAP | `square_model.py:228-229`（仅倒角 0.4）；无平底/球头冻结 | 未关闭 |
| PRD-8.2-09 | M2-09 电池固定与绝缘 | GAP | `square_model.py:277-280` 仅占位体；无电池仓/绝缘/热设计 | 未关闭 |
| PRD-8.2-10 | M2-10 C 形 PCB 走线及固定 | PARTIAL | PCB 已布线 0 DRC/0 unconnected（E2/E6）；机械有 4 个 standoff（`square_model.py:196-199`）；无螺钉/线束设计 | 走线已通；固定/线束未定 |
| PRD-8.2-11 | M2-11 USB-C 前右壁开窗 | PARTIAL | 开窗存在但在**后壁居中**（`square_model.py:206-207`）；`gen_pcb.py:35` | 开窗有；位置与 PRD 前右不符（4.6-08） |
| PRD-8.3-01 | 风险边界：几何无干涉不能证明 7 项（受力方式/预弯/旁路/0.5 间隙/电气兼容/精度/量产） | PASS | `docs/VERIFY_REPORT.md:243-247`（无硬性不达标）；`firmware/REPORT.md:386-388`（PROVISIONAL）；FEA README“趋势分析，不是定型” | 文档未越界声称，风险边界被保留 |

### §9 验收标准与开发里程碑（PRD 412–468 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-9-M2-01 | M2：HY928D 关键机械参数有图纸/供应商确认/实测依据 | PARTIAL | 有图纸转录 `ref/HY928D_5kg_称重传感器_图纸转录.md`；U 槽/拱为像素比例+照片估算（`config:13`） | 有图纸无供应商/实测 |
| PRD-9-M2-02 | M2：中央孔和 U 形腔含义明确 | GAP | `ref/HY928D...:160-166` 问题 1/3 未答；`notes.md` 待检视 | 未关闭 |
| PRD-9-M2-03 | M2：应变梁方向和安装方式明确 | GAP | `ref/HY928D...:84-100` 两种结构“必须二选一”；FEA 用假设 A | 未关闭 |
| PRD-9-M2-04 | M2：传感器桥路和电气参数明确 | GAP | `ref/HY928D...:158` 待确认；`config:5-6` 候选 | 未关闭 |
| PRD-9-M2-05 | M2：传力柱、中央垫块、四角固定方式通过评审 | GAP | 端部未冻结（`square_model.py:228-229`）；无评审记录 | 未评审 |
| PRD-9-M2-06 | M2：过载限位间隙有依据 | PARTIAL | E1 第 5/15/16/18 项；FEA 5 kg 下沉 0.3435 mm（`simulation/.../README.md`） | 有 CAD/FEA 依据；无额定形变/公差依据 |
| PRD-9-M2-07 | M2：线缆、PCB、控件没有形成未预期称重旁路 | PARTIAL | E1 第 10–19 项（屏/键/PCB/电池 clear）；线缆未建模 | 线缆旁路未验证 |
| PRD-9-M2-08 | M2：关键装配尺寸和公差已记录 | GAP | 无公差记录文件；`docs/09_Assembly.md` 未含公差 | 未记录 |
| PRD-9-M3-01 | M3：传感器与 HX711 接口原理图 | PASS | `design.py:127-150,228-234`；E3 ERC 0/0；`NETLIST.md` HX_* 网 | — |
| PRD-9-M3-02 | M3：ESP32-S3/电源/充电/OLED/按键/USB-C 原理图 | PASS | `design.py:52-176`；E3；`smartcoaster.kicad_sch` | 43 器件/28 网络 |
| PRD-9-M3-03 | M3：完成 PCB 布局和布线 | PASS | E2 0 DRC/0 unconnected；E6 47 footprint/576 track/62 via；`DRC_2l.rpt` | — |
| PRD-9-M3-04 | M3：检查模拟信号路径/电源完整性/机械安装空间 | PARTIAL | 模拟路径 ngspice（`electronics/simulation/hy928d_frontend.json`）；机械空间有 U1 (29,32) 与壳腔 0.25 mm 余量（`S3_FOOTPRINT.md`）；电源完整性无专门分析 | 模拟/机械有；电源完整性未做 |
| PRD-9-M3-05 | M3：输出可制造文件和 BOM | PARTIAL | `build/gerbers/` 13 文件 + `smartcoaster_2l_gerbers.zip`；`DFM.md` 5 项 PASS；`BOM.csv` 24 行 | BOM 有 **10 行缺 MPN**（`DFM.md` 备注），下单前需补齐 |
| PRD-9-M4-01 | M4：稳定读取重量 | PARTIAL | `hx711_hw.c` + `hx711_mock.c`；E4 mock 9/9；E5 | 逻辑/模拟通过；真实 HX711 未 bring-up |
| PRD-9-M4-02 | M4：完成零点和量程校准 | PARTIAL | 手动 tare（`ui.c:78-86`）；`hx711_hw.h:23` counts/g PROVISIONAL；无量程/砝码校准流程与记录 | 未完成真实校准 |
| PRD-9-M4-03 | M4：识别基本饮水事件 | PASS | `intake.c`；E4 py01/py02/py05；QEMU 日志 `firmware/REPORT.md:329-343` | — |
| PRD-9-M4-04 | M4：估算单次和每日饮水量 | PASS | `intake.c`；E4 py01（50 g）、py06（跨日） | — |
| PRD-9-M4-05 | M4：完成提醒功能 | PASS | `reminder.c`；E4 py06/x03 | — |
| PRD-9-M4-06 | M4：BLE 数据同步稳定 | PARTIAL | `ble.c` 外设 GATT；无 App；电量恒 100（E7）；无实物 BLE 测试 | 外设代码有，稳定性未验证 |
| PRD-9-M5-01 | M5：3D 打印外壳可装配 | GAP | 无打印实物/装配记录；`tests/handboard/BRINGUP_RECORD.md` 为空表模板 | 用户侧未做 |
| PRD-9-M5-02 | M5：PCB 与传感器完成实物安装 | GAP | 无实物；`HANDOFF.md:109-113` | 用户侧未做 |
| PRD-9-M5-03 | M5：USB-C/电池/屏幕/按键可正常使用 | GAP | 无实物测试 | 用户侧未做 |
| PRD-9-M5-04 | M5：进行砝码校准 | GAP | 无校准记录；`BRINGUP_RECORD.md` 未填 | 用户侧未做 |
| PRD-9-M5-05 | M5：测试重复性/零点漂移/响应/杯型 | GAP | 无实测数据 | 用户侧未做 |
| PRD-9-M5-06 | M5：记录失败案例并迭代设计 | GAP | 无样机失败记录 | 用户侧未做 |
| PRD-9-M6-01 | M6：按样机结果决定结构尺寸/材料调整 | N/A | — | 未到 M6 |
| PRD-9-M6-02 | M6：传感器和 ADC 调整 | N/A | — | 未到 M6 |
| PRD-9-M6-03 | M6：低功耗策略调整 | N/A | — | 未到 M6 |
| PRD-9-M6-04 | M6：外观和交互调整 | N/A | — | 未到 M6 |
| PRD-9-M6-05 | M6：生产工艺调整 | N/A | — | 未到 M6 |
| PRD-9-M6-06 | M6：Solar 版可行性 | N/A | — | 未到 M6 |

### §10 当前执行计划（PRD 472–485 行）

| 编号 | 需求摘要 | 判定 | 证据 | 差距与说明 |
|---|---|---|---|---|
| PRD-10-01 | 保留 M1.2 Git 版本和完整设计源 | PASS | `git log` ae17e10 及历史提交；`mechanical/square_v1/v1..v6_square_v1/` 快照；STEP/STL 齐全 | 无 tag，但历史+快照可用 |
| PRD-10-02 | 整理 HY928D 供应商问题清单（中心孔/U 形腔/桥路/灵敏度/形变） | PASS | `ref/HY928D_5kg_称重传感器_图纸转录.md:160-166`（8 问，覆盖 5 项）；`mechanical/hy928d/notes.md:4 检视清单` | 清单已存在（供内部/供应商使用） |
| PRD-10-03 | 根据确认结果修订传感器模型和传力结构 | PARTIAL | v2 模型 `mechanical/hy928d/`（按图纸+照片重建，待检视）；传力结构未改（`square_model.py:224-235`） | 模型重建≠按供应商确认修订；未替换总装 |
| PRD-10-04 | 对称重路径/浮动间隙/过载限位做工程核实 | PARTIAL | E1 21/21；FEA `simulation/mechanical/hy928d/`（0.3435 mm、7.28 kg 接触）；`docs/05:37` | CAD+FEA 趋势完成；无装配级/实物核实 |
| PRD-10-05 | 完成 PCB 固定/电池固定/USB-C 开窗/线缆隔离设计 | PARTIAL | PCB standoff `square_model.py:196-199`；USB-C 开窗（后壁）；电池仅占位；线缆无 | 4 项中 2 项有骨架，电池固定/线缆隔离缺失 |
| PRD-10-06 | M2 评审通过后，再开始 M3 电路设计 | GAP | M3 已完成（E2/E3/E5/E6，43 器件/2 层 0/0），而 M2 未评审（§8.2） | 流程顺序偏离：电子先于机械核实闭环；需在 M2 评审时回溯风险 |
| PRD-10-07 | 阶段原则：先证明称重机构，再固定电子；先普通版闭环，再 Solar | PARTIAL | 普通版电子已做、称重机构未证明（§8.2）；Solar 未启动（E9） | 后半句符合；前半句顺序未遵守 |

---

## 3. 未达成清单（GAP，共 28 项，按影响排序）

> 与 §2 明细一一对应（共 28 个 GAP，全部列出，不合并遗漏）。优先级依据：产品核心闭环 → 称重机构成立 → 装配/安全 → 文档一致性。

| 优先级 | 编号 | 缺口与证据 | 影响 | 建议 |
|---|---|---|---|---|
| **P0** | PRD-7.1-03 | BLE 无“单次饮水量”特征（`ble.c:160-177`；sip 仅存内部 events） | 手机端拿不到单次饮水数据 | 新增 0xFF07 last_sip（u16 ml，notify） |
| **P0** | PRD-7.1-05 | 无历史记录特征/持久化（`hydration.h` events[256] 仅内存；`storage.c` 只存 today/goal/tare/mode） | 断连/重启丢历史，手机无记录 | 环形历史 + NVS + 0xFF08 分页读取特征 |
| **P0** | PRD-7.1-06 | 提醒配置仅 goal 可写（`ble.c:167-169`），reminder interval/snooze 不可配，无 App | PRD §7“提醒配置”不成立 | 新增 0xFF09 reminder 配置（可写） |
| **P0** | PRD-7.1-07 | 0xFF04 电量恒 100：`ble.c:31` `s_batt=100` 且无任何赋值；`ble_update()` 无 battery 参数（`ble.c:249-261`） | 手机端永远读到满电 | 把 `battery_percent()` 结果传入 `ble_update()` 并 notify |
| **P0** | PRD-8.2-04 | 全桥/半桥及引线未确认（`ref/HY928D...:158` 待确认；8 问第 4 条未答） | HX711 前端/增益/补桥可能返工 | 供应商接线图或到货实测 |
| **P0** | PRD-9-M2-04 | M2 验收“传感器桥路和电气参数明确”未达成（同上） | M2 无法通过 | 同 PRD-8.2-04 |
| **P0** | PRD-4.6-10 | 电池固定/绝缘/热安全/连接器线束未设计（仅占位体 `square_model.py:277-280`） | 安全与可靠性；M2-09 未关闭 | 电池仓/压板/绝缘片/线束固定并进总装 |
| **P0** | PRD-8.2-09 | M2-09 电池固定与绝缘未关闭 | 同 PRD-4.6-10 | 同 PRD-4.6-10 |
| **P0** | PRD-4.5-03 | 线缆运动余量/隔离未设计（PARTS 无线缆件；无走线图） | 线缆可能跨越浮动缝形成称重旁路 | 出线束路径（J4/J5/J2/J3）并标注弯曲半径与浮动余量 |
| **P1** | PRD-4.6-08 | USB-C 实际在后缘居中（`square_model.py:206-207`；`gen_pcb.py:35`），PRD 要求前右 r=40/320° | 接口位置与 PRD/壳体设计不一致 | 明确“后缘 USB-C”为新基线并更新 PRD/M2-11，或改回前右重跑 DRC/自检 |
| **P1** | PRD-8.2-01 | M2-01 中心 Ø5 孔功能含义未定（`ref/HY928D...:160-166` 问题 3） | 传力柱端部/中央结构无法冻结 | 供应商确认或剖切 |
| **P1** | PRD-9-M2-02 | M2 验收“中央孔/U 形腔含义明确”未达成 | M2 无法通过 | 同 PRD-8.2-01 |
| **P1** | PRD-8.2-07 | M2-07 螺钉规格/固定方式未定（`square_model.py:192-193` Ø2.1 通孔占位） | 真实装配/维护未闭合 | 选 M2 螺钉 + 沉孔并改模型/PRD |
| **P1** | PRD-4.4-02 | 固定孔 Ø2.8 沉孔未实现（实际 Ø2.1 通孔，无沉孔） | 模型与 PRD 不符，装配依据缺失 | 同 PRD-8.2-07 |
| **P1** | PRD-8.2-08 | M2-08 传力柱端部（平底/球头）未冻结（`square_model.py:228-229` 仅 0.4 倒角） | 接触状态/受力稳定性不确定 | 结合传感器真实结构定端部 + 接触/预压 FEA |
| **P1** | PRD-9-M2-03 | M2 验收“应变梁方向和安装方式明确”未达成（`ref/HY928D...:84-100` 二选一未决） | FEA 边界/顶板支撑拓扑不定 | 优先确认“四角固定+中央受力”是否成立 |
| **P1** | PRD-9-M2-05 | M2 验收“传力柱/中央垫块/四角固定通过评审”未达成 | M2 无法通过 | 组织 M2 评审并留记录 |
| **P1** | PRD-9-M2-08 | M2 验收“关键装配尺寸和公差已记录”未达成（无公差文档） | 装配/打样依据缺失 | 补关键尺寸公差表 |
| **P1** | PRD-10-06 | 未等 M2 评审即完成 M3（E2/E3/E5/E6 vs §8.2 未关闭） | 机械假设未验证就固化电子设计 | M2 评审时把电子设计作“条件通过”复核 |
| **P2** | PRD-5.2-02 | 桥路/灵敏度/引线未以供应商或实测为准（`config:13` provisional；`hx711_hw.h:23` PROVISIONAL） | 前端/量程存在假设风险 | 传感器到货先测桥路/线序/灵敏度 |
| **P2** | PRD-5.3-08 | 传感器参数未确认即冻结 HX711 配置（`design.py:13` REV 0.1-DRAFT） | 可能需要改板 | 确认后冻结 REV 并重跑 ERC/DRC |
| **P2** | PRD-5.4-07 | 无低电量阈值提示（`app_main.c:145-150` 仅显示 BAT%；全仓无阈值逻辑；`docs/10:53` 称有角标） | 用户不会被主动提醒充电 | 加 <20% 屏上提示/角标并更新 docs/10 |
| **P2** | PRD-9-M5-01 | M5 3D 打印外壳可装配未验证（`tests/handboard/BRINGUP_RECORD.md` 空表） | 实物未验证 | 用户侧采购/打印/装配 |
| **P2** | PRD-9-M5-02 | M5 PCB 与传感器实物安装未做 | 实物未验证 | 同上 |
| **P2** | PRD-9-M5-03 | M5 USB-C/电池/屏幕/按键可用未验证 | 实物未验证 | 同上 |
| **P2** | PRD-9-M5-04 | M5 砝码校准未做 | 灵敏度/零点未标定 | 用户侧砝码标定，回填 `BRINGUP_RECORD.md` |
| **P2** | PRD-9-M5-05 | M5 重复性/零点漂移/响应/杯型未测 | 无实测性能数据 | 同上 |
| **P2** | PRD-9-M5-06 | M5 失败案例记录/迭代未做 | 无法闭环 | 建失败案例表并迭代 |

---

## 4. 部分达成清单（PARTIAL，共 50 项，按影响排序）

> 与 §2 明细一一对应（共 50 个 PARTIAL，全部列出）。证据行号见 §2 对应条目。

| 优先级 | 编号 | 已达成部分 | 缺口 | 建议 |
|---|---|---|---|---|
| P0 | PRD-1.1-06 | 无线同步：BLE 外设 GATT 已实现 | 无手机 App；电量/单次/历史/提醒配置缺 | 见 §3 P0 前四条 |
| P0 | PRD-2.1-05 | BLE 通信外设侧（NimBLE 0xFF00） | 无 App；特征不全；电量恒 100 | 同上 |
| P0 | PRD-7.1-01 | 设备可发现/连接（广播占空、GAP 回调） | 手机侧无实现 | 最小 BLE 调试页/App |
| P0 | PRD-7.1-02 | 0xFF01 重量 read+notify | 饮水状态/模式未暴露；无 App | 增模式特征 |
| P0 | PRD-7.1-04 | 0xFF02 今日累计 read+notify | 无 App | 随 App 一起补 |
| P0 | PRD-9-M4-06 | BLE 数据同步代码骨架 | 无 App；电量缺陷；未实物稳定性测试 | 联调+手板 |
| P0 | PRD-9-M4-01 | 重量读取逻辑 + mock 9/9 | 真实 HX711 未 bring-up | 手板 HX711 时序/噪声实测 |
| P0 | PRD-9-M4-02 | 手动 tare；counts/g 换算 | 无自动零点、无量程/砝码校准流程 | 加 boot 自动零点 + 校准模式 |
| P0 | PRD-6.1-02 | init/采样循环/稳定窗 | 无上电自动稳零/预热 | 启动阶段自动零位 |
| P0 | PRD-6.1-03 | 长按 2 s 去皮 | 仅手动；无自动零点 | 同 PRD-9-M4-02 |
| P1 | PRD-2.1-02 | HY928D 5 kg 选型 + 占位模型 | 桥路/量程/灵敏度待供应商 | 供应商确认 |
| P1 | PRD-5.2-03 | 记录“不得默认全桥”原则 | 设计实际已按全桥 1.2 mV/V 做前端 | 若实物半桥需补桥改板 |
| P1 | PRD-5.3-01 | 全桥差分输入 + RC 滤波已设计 | 半桥/引线未确认 | 到货核对 |
| P1 | PRD-5.3-03 | 当前按“不需要补桥”设计 | 未确认 | 同 PRD-5.2-03 |
| P1 | PRD-5.3-06 | 3V3 单域、2 层板 GND 走线 | 无模拟/数字分区、无电源完整性分析 | 做 2 层板回流/噪声评估 |
| P1 | PRD-5.3-07 | 行为级仿真：50 nVrms、RC 1.65 kHz | 无实测噪声/漂移/稳定时间 | 手板实测 |
| P1 | PRD-8.1-03 | v2 真实外形模型已重建 | 未集成总装、未供应商确认 | 检视通过后替换 |
| P1 | PRD-8.2-02 | v2 U 槽/拱按图纸+照片重建 | 像素比例推断，待确认 | 供应商剖视图/STEP |
| P1 | PRD-8.2-03 | FEA 已按“四角固定中央受力”假设建模 | 应变梁方向未最终确认 | 供应商确认后重跑 FEA |
| P1 | PRD-8.2-05 | 理论灵敏度 1.2 mV/V、激励 3–10 V | 无批次实测 | 手板标定 |
| P1 | PRD-8.2-06 | FEA：5 kg 中心 0.3435 mm；7.28 kg 接触 | 额定形变/安全位移无供应商值 | 索要额定形变 + 公差复核 |
| P1 | PRD-8.2-10 | PCB 已布通 0 DRC/0 unconnected；4 个 standoff | 固定方式/线束未定 | 定 PCB 螺钉与线束 |
| P1 | PRD-8.2-11 | USB-C 开窗存在 | 位置后壁、与前右要求不符 | 同步 PRD 或改回 |
| P1 | PRD-9-M2-01 | 有 HY928D 图纸转录与硬尺寸 | U 槽/拱为估算，无供应商确认/实测 | 8 问清单推进 |
| P1 | PRD-9-M2-06 | 0.5 mm 间隙 + FEA 过载接触 7.28 kg | 无额定形变/公差依据 | 同 PRD-8.2-06 |
| P1 | PRD-9-M2-07 | 屏/键/PCB/电池/壳边 clear 已证 | 线缆未建模验证 | 同 PRD-4.5-03 |
| P1 | PRD-9-M3-04 | 模拟前端 ngspice；机械空间 U1 余 0.25 mm | 电源完整性无专门分析 | 补 3V3/GND 回流评估 |
| P1 | PRD-9-M3-05 | Gerber/DRL/POS/zip/DFM 全 PASS | BOM 10 行缺 MPN | 下单前补 LCSC/MPN |
| P1 | PRD-10-03 | v2 传感器模型已按图纸+照片重建 | 非按供应商确认修订；未替换总装/传力结构 | 确认后替换并复跑 verify+FEA |
| P1 | PRD-10-04 | CAD 21/21 + FEA 趋势 | 无装配级/实物核实 | 手板装配后复测 |
| P1 | PRD-10-05 | PCB standoff + USB-C 开窗 | 电池固定、线缆隔离缺失 | 补 2 项 |
| P1 | PRD-10-07 | Solar 未启动（符合后半句） | 电子先于机械核实完成 | M2 评审条件通过 |
| P2 | PRD-3.1-05 | CAD 渲染暖白壳（#EFEDE6） | CMF 主色 Lumen Violet 紫/炭灰，两文档不一致 | 用户确认最终配色 |
| P2 | PRD-3.1-07 | 总高 18 一致 | “底座 15”实为 14.5+0.5 浮动缝 | 统一 PRD/README 口径 |
| P2 | PRD-3.3-04 | 8 s 息屏 + 局部刷新 | 26×7 可读性/功耗未实测 | 手板评估 |
| P2 | PRD-4.1-02 | 总高 18 一致 | 同 PRD-3.1-07 | 同上 |
| P2 | PRD-4.3-06 | 总装 / v2 两版传感器模型 | PRD 表与两版均不完全对应（无 2-R9、腔宽解释不同） | 统一传感器参数表 |
| P2 | PRD-4.3-07 | 5 kg 选型 | 无批次数据 | 供应商确认 |
| P2 | PRD-4.4-01 | 四角 boss 高 3、顶面 z=5.0 | 直径 Ø7 vs PRD Ø6 | 改模型或改 PRD |
| P2 | PRD-4.4-03 | Ø12 中央停止块、距传感器 0.8 | PRD“高 0.8”实为间隙，实际高 2.2 | 统一定义 |
| P2 | PRD-4.5-01 | 屏/键/PCB/电池/壳边无接触已证 | 螺钉/铜柱/线缆未建模 | 补建模或书面风险接受 |
| P2 | PRD-4.6-03 | C 形缺口存在 | 实际 80° vs PRD 70° | 同步 PRD/README |
| P2 | PRD-4.6-06 | ESP32 尺寸 18×25 一致 | 位置 (29,32) vs PRD (32,31) | 统一坐标口径 |
| P2 | PRD-4.6-07 | HX711 尺寸 12×15 一致 | 模型 x=40 / PCB x=39 vs PRD 36 | 统一坐标口径 |
| P2 | PRD-4.7-04 | 壁厚 2.4/底 2.0 已定 | 螺钉柱/装配间隙无 M2 记录 | 补 M2 装配核实 |
| P2 | PRD-5.4-03 | TP4056+保护+LDO 供电链 | 无真正 power-path/负载共享 | 评估理想二极管或声明限制 |
| P2 | PRD-5.4-05 | PM light sleep 已配置 | 功耗只有估算 2–3 mA | 手板测电流 |
| P2 | PRD-5.4-08 | 后壁 USB-C 开窗 | 位置与 PRD 不符、无机械固定 | 同 PRD-4.6-08 |
| P2 | PRD-6.2-03 | 可识别 sip（基线差值） | 非“连续下降”实现 | PRD 措辞对齐实现或改算法 |
| P2 | PRD-6.3-05 | goal 可写（0xFF03） | reminder interval/snooze 不可配；无 App | 同 PRD-7.1-06 |

---

## 5. 建议（给 Lead / 下一轮）

1. **先补手机端最小闭环**（P0）：一个 BLE 调试页即可覆盖“发现/连接、重量、今日、目标、电量、单次、提醒配置”；同时修 `ble.c` 的 0xFF04 电量恒 100 缺陷（这是当前最容易验证、影响 PRD §7 最大的单点）。
2. **M2 关闭清单**（P0/P1）：把 `ref/HY928D_5kg_称重传感器_图纸转录.md:160-166` 的 8 问作为 M2 入口；供应商确认后替换 `mechanical/hy928d` v2 进总装、冻结螺钉/端部/电池固定/线束，再跑 `verify_v01.py` + FEA。
3. **文档口径对齐**（P1/P3）：PRD 仍是 M1.2 口径，建议单独提交一次“PRD → 当前 B 版”同步，至少改 §3.1（底座 14.5+0.5）、§3.2（按键 x=17/z=7.2）、§4.4（Ø7/Ø2.1、中央垫块）、§4.6（80°、USB-C 后缘、ESP32/HX711 坐标）、§8.1（13→12 已由变更覆盖）；否则后续审计会重复报同一批偏差。
4. **保持 PROVISIONAL 纪律**：`counts_per_g=515.4`、U 槽/拱参数、传感器量程均未实测，任何“已达成”表述必须限定为“主机测试/仿真”。当前文档整体做得较好（`VERIFY_REPORT.md` 7/7 且未越界），继续维持。
5. **M5 属用户侧**：AI 不能代替采购/装配/标定；建议在 HANDOFF 中把 M5 明确成“用户动作 + 验收判据”，避免被误读为设计未完成。

---

## 附录 A：审计期间工作区并发改动（非本审计所写）

`git status --short`（审计开始时为干净工作区；审计期间观察到以下改动，全部来自其他并行任务，非本审计所写）。早期 7 个文件经 diff 核对为文档/注释修正，不改变本报告判定；其余文件（构建脚本/装配图/新增产物）不在本报告判定路径上。

| 文件 | 改动摘要 |
|---|---|
| `config/mechanical_params.yaml` | display 0.49in→0.91in；electronics status concept→designed |
| `docs/05_Bringup_and_Verification_Plan.md` | 固件 bin 233 KB→519,152 B |
| `docs/06_Firmware_Architecture.md` | 同上 + 说明含 NimBLE/NVS/时间同步 |
| `firmware/REPORT.md` | BLE 桩→NimBLE GATT；bin 大小；QEMU 状态 |
| `firmware/esp32/main/app_main.c` | 顶部注释：BLE/NVS/PM 已实现，未实现项改为手机 App/实物 bring-up |
| `mechanical/square_v1/cad/square_model.py` | 材料注释 FR-4 4-layer→2-layer |
| `mechanical/square_v1/build/assembly/meta.json` | 构建元数据 |
| `electronics/kicad/scripts/build.sh`、`route_2l.sh`、`requirements.yaml` | 其他并行任务的构建脚本/依赖调整（审计只直接调用 kicad-cli，不依赖这两个脚本） |
| `electronics/kicad/build/assembly/*`（top/bottom 的 pdf/png/svg） | 其他并行任务重出的装配图 |
| 新增未跟踪：`docs/AUDIT_ENV.md`、`electronics/kicad/scripts/render_assembly.py`、`freerouting.settings.json` | 其他并行任务的产物（非本审计写入） |

> 本审计自身只写了 `docs/AUDIT_PRD.md`；E1 复跑按脚本固定行为刷新了 `mechanical/square_v1/build/verify_report.json`（内容与 21/21 结果一致）。

## 附录 B：证据路径索引

- PRD：`docs/02_Smart_Coaster_PRD.md`
- 用户变更：`docs/HANDOFF.md:17-23`、`docs/07_Product_Roadmap.md:3-5`、`docs/10_CMF_and_Packaging.md:3-5`
- 机械：`mechanical/square_v1/cad/square_model.py`、`cad/verify_v01.py`、`build/verify_report.json`、`build/verify_v01.log`、`README.md`；传感器：`mechanical/hy928d/notes.md`、`build/params.json`、`src/hy928d_v2.py`、`ref/HY928D_5kg_称重传感器_图纸转录.md`
- 电子：`electronics/kicad/scripts/design.py`、`gen_pcb.py`、`smartcoaster/smartcoaster_2l.kicad_pcb`、`build/DRC_2l.rpt`、`build/ERC.rpt`、`build/DFM.md`、`BOM.csv`、`NETLIST.md`、`S3_FOOTPRINT.md`、`DECISIONS.md`、`electronics/pinmap.md`、`electronics/simulation/hy928d_frontend.json`
- 固件/算法：`firmware/esp32/main/{app_main,ble,hx711_hw,hx711_mock,weight_process,intake,reminder,hydration,ui,oled,button,battery,storage,core_types}.c/h`、`firmware/model/`、`tests/firmware/`、`firmware/REPORT.md`、`docs/06_Firmware_Architecture.md`
- 验收/里程碑：`docs/VERIFY_REPORT.md`、`docs/05_Bringup_and_Verification_Plan.md`、`docs/08_Power_Sleep_Plan.md`、`tests/handboard/BRINGUP_RECORD.md`
- 复跑命令原始输出：E1（21/21）、E2（0/0）、E3（ERC 0/0）、E4（2/2 + 16/16 + 16 passed）、E5（bin 519,152 B）。
