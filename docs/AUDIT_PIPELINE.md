# SmartCoaster 研发流水线合规审计（docs/01 全文逐条）

> **审计快照注记（2026-11-04 20:45 由 Lead 追加）**：本报告基于 HEAD `ae17e10` 与其时实测（bin 519,152 B）。此后 Lead 修复了 BLE 0xFF04 电量特征（bin → 519,184 B / 0x7EC10）、重出 2 层装配图、校准部分文档口径；这些改动**不改变本报告任何判定**，最新状态以 `docs/REPORT_技术报告.md` 与 `docs/VERIFY_REPORT.md` §8 为准。


> **审计人**：pipeline-audit（独立审计，只读）  
> **审计时间**：2026-11-04 20:33 CST  
> **审计基线**：HEAD = `ae17e10`（审计开始时 `git status --porcelain` 为空）  
> **审计对象**：`docs/01_AI_Hardware_Engineering_Pipeline.md` 全文 879 行、15 个章节  
> **产出**：本文件（唯一写入）；`/tmp` 下临时复核产物  
> **原则**：先打开文件/跑命令核对，再判定；不采信 README 自述。

## 0. 执行摘要

**总体结论**：仓库已经形成 **P0–P3 数字设计闭环**（机械 12 件 21/21、原理图 43 器件/28 网络 ERC 0/0、2 层 PCB DRC 0/0、Gerber/DFM、固件主机测试 41+198 checks/16 场景），并完成了 **S1 首轮机械 FEA（HY928D 本体）**；但 docs/01 V1.1 定义的完整流水线 **尚未实现**：

- **S2 电路仿真**只有桥路+HX711 行为前端 DC/AC，缺电源/MCU/噪声/瞬态/蒙特卡洛；
- **S1 只做了对象 A**（HY928D 本体），对象 B（顶板+传力柱）与对象 C（整机/限位）未做；
- **S3 固件仿真**主机侧完整，QEMU 冒烟为历史证据且未在删 halo 后复跑，Wokwi 搁置；
- **S4 / §14 MCP 编排层完全未实现**（无 MCP server、无统一接口契约、无一条命令编排、无 artifacts 归档）；
- **§9 电气实测与整机验证未开始**（用户侧硬件未采购/未打样），属 GAP 但 AI 不可代替。

### 0.1 判定统计（146 个检查项）

| 判定 | 数量 | 占比 |
|---|---:|---:|
| PASS | 71 | 48.6% |
| PARTIAL | 46 | 31.5% |
| GAP | 28 | 19.2% |
| N/A | 1 | 0.7% |
| **合计** | **146** | 100% |

### 0.2 最关键 3 个 GAP

1. **§14 / §13.5 / §13.7-S4：MCP 编排层与系统级自动化未实现**。`scripts/` 为空、`simulation/system/` 仅 3 行 README；没有统一工具接口、统一 JSON 契约、一条命令跑 S1–S4、artifacts 版本归档。docs/01 的「AI 原生硬件流水线」核心承诺之一目前只有各域手工脚本。
2. **§13.2 对象 B/C 机械 FEA 缺失 + 验收阈值无来源**。只完成 HY928D 本体（5 kg 0.3435 mm、支反力 100%、热点 468 MPa）；顶板+传力柱（中心/偏载）与整机装配（0.5 mm 限位是否先接触、旁路力、安全系数）没有结果；§13.2 验收 YAML 全为 null，`config/validation_mechanical.yaml` 不存在。
3. **§13.3/S2 电路仿真不完整**。仅 `hy928d_frontend.cir` 一个网表（DC/AC）；电源模块、MCU 接口模块、`.tran`/`.noise`/蒙特卡洛均缺；因此「电源/滤波/噪声预算」只有量级估算。

### 0.3 可快速见效的修复

- 文档状态校准：PRD 当前状态横幅、electronics/README、DECISIONS、docs/01 §13.3/§13.4、docs/05、VALIDATION_PLAN、mechanical/hy928d notes（附录 F1–F9）。
- `config/electronics.yaml`、`config/firmware.yaml`、`config/validation_mechanical.yaml`、`requirements.yaml` 补 Freerouting/Xvfb/poppler。
- BLE 断线重广播（ble.c）；QEMU 复跑并把原始日志入库；补 8 要素任务模板与评审记录。
- 统一 artifacts 目录与一条命令编排（最小 CLI 版）——这是投入产出比最高的结构性缺口（见 §14.6）。

---

## 1. 汇总统计（按章节）

| 章节 | PASS | PARTIAL | GAP | N/A | 小计 |
|---|---:|---:|---:|---:|---:|
| §1 项目目标 | 6 | 1 | 0 | 0 | 7 |
| §2 总体研发架构 | 0 | 2 | 1 | 0 | 3 |
| §3.1 本地 AI Agent | 4 | 2 | 0 | 0 | 6 |
| §3.2 机械设计工具 | 4 | 1 | 0 | 0 | 5 |
| §3.3 电路设计工具 | 4 | 1 | 0 | 0 | 5 |
| §3.4 固件开发工具 | 2 | 2 | 0 | 1 | 5 |
| §4 项目目录结构 | 0 | 5 | 4 | 0 | 9 |
| §5 需求驱动开发 | 2 | 2 | 0 | 0 | 4 |
| §6 机械设计工作流 M0–M3 | 6 | 3 | 1 | 0 | 10 |
| §7 电路设计工作流 E0–E4 | 5 | 3 | 0 | 0 | 8 |
| §8 固件设计工作流 F0–F4 | 4 | 1 | 1 | 0 | 6 |
| §9 验证与质量管理 | 0 | 3 | 2 | 0 | 5 |
| §10 AI Agent 执行规范 | 6 | 2 | 0 | 0 | 8 |
| §11 开发里程碑 | 3 | 3 | 3 | 0 | 9 |
| §12 核心原则 | 5 | 2 | 0 | 0 | 7 |
| §13 仿真工程 | 14 | 13 | 11 | 0 | 38 |
| §14 MCP 仿真编排层 | 1 | 0 | 5 | 0 | 6 |
| §15 参考资料 ref/ | 5 | 0 | 0 | 0 | 5 |
| **合计** | **71** | **46** | **28** | **1** | **146** |

**判定口径**：

- **PASS**：文档要求的产物/机制存在，且本审计通过打开文件或只读命令独立核实（证据列给路径/行号/命令结果）。
- **PARTIAL**：存在但要素不全、只覆盖部分范围，或文档口径与实际不符。
- **GAP**：未实现/未做/无证据。
- **N/A**：当前范围不适用（已注明原因）。

---

## 2. 分节明细

### §1 项目目标

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 1.1 | 自然语言需求 → 机械/电路/固件/验证任务拆解 | **PASS** | docs/01 §1、docs/02 PRD、AGENTS.md；git log 31 次提交按 M/E/F/P 阶段拆分 |
| 1.2 | Agent 通过 MCP 调用本地专业工具 | **PARTIAL** | 实际由 shell/脚本直调 kicad-cli、ccx、gmsh、ngspice、idf.py；MCP 仅 mechanical/lumen/.mcp.json.example 指向 agentcad.mcp，未启用、无编排层 |
| 1.3 | 文本/代码驱动参数化设计 | **PASS** | mechanical/square_v1/cad/square_model.py 顶部参数块；electronics/kicad/scripts/design.py 单一设计源；firmware/model Python 参考模型 |
| 1.4 | 先完成数字样机、仿真和自动化检查 | **PASS** | verify_v01.py 21/21（本审计复跑）；DRC/ERC 0/0（本审计复跑）；host 41/198 checks + 16/16 差分（本审计复跑）；FEA results.json |
| 1.5 | 验证通过后再 3D 打印、PCB 打样、实物组装 | **PASS** | 未下打样/打印单；docs/05 §2 购买清单为前置；HANDOFF §7 列为用户侧待办 |
| 1.6 | Git 管理设计文件、需求、验证结果与版本 | **PASS** | git log 31 条、git ls-files 404 个文件；HEAD=ae17e10；PROVISIONAL 状态与验证报告入库 |
| 1.7 | 不将 AI 生成结果直接视为已验证 | **PASS** | config/mechanical_params.yaml hy928d.status=provisional；firmware/REPORT §7；docs/VERIFY_REPORT 独立复核；FEA README §5 局限 |

### §2 总体研发架构

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 2.1 | 三层架构：本地 Agent → MCP 工具调用层 → 机械/电路/软件工具 | **PARTIAL** | 机械/电路/固件工具链齐备且被使用，但 §2 图中央的 MCP 工具调用层缺失（见 §14）；实际是脚本/CLI 串联 |
| 2.2 | 几何检查/电气检查/软件测试汇入验证与集成闭环 | **PARTIAL** | 各域有自动闸门（verify_v01、ERC/DRC、host tests），但无跨域统一入口、统一 artifacts、统一报告 |
| 2.3 | 实物打样 → 实际测试与迭代 | **GAP** | 无 PCB 打样/3D 打印/实物测试记录；tests/handboard/BRINGUP_RECORD.md 为空表；用户侧未采购 |

### §3.1 本地 AI Agent

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 3.1.1 | 能读取和修改项目文件 | **PASS** | 本会话多 Agent 直接读写仓库；HANDOFF/VERIFY_REPORT 记录文件级改动 |
| 3.1.2 | 能执行本地命令 | **PASS** | kicad-cli/ccx/gmsh/ngspice/idf.py/pytest 均出现在仓库脚本（build.sh、route_2l.sh、run_host_tests.sh）并被本次审计复跑部分命令 |
| 3.1.3 | 支持 MCP 工具调用 | **PARTIAL** | agentcad[mcp] 0.7.1 已安装（mechanical/square_v1/.venv 内 agentcad.mcp 可导入）；仅 .mcp.json.example 示例，无启用配置、无工具调用证据 |
| 3.1.4 | 读取 PRD、设计规范和验证记录 | **PASS** | AGENTS.md 第 1 条强制先读 docs/01、docs/02、ref/*.md；HANDOFF §0 先读清单 |
| 3.1.5 | 支持多个专业 Agent 协作 | **PASS** | docs/05 §5 并行 subagent 分工；docs/VERIFY_REPORT 独立 verifier；HANDOFF 交接给下一个 AI |
| 3.1.6 | 六角色（产品/机械/电子/固件/验证/集成）落地 | **PARTIAL** | 机械/电子/固件/验证可按 HANDOFF 与 VERIFY_REPORT 对应；仓库无角色职责表；集成角色无产物 |

### §3.2 机械设计工具

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 3.2.1 | AgentCAD/build123d/Python + FreeCAD/CalculiX/Gmsh 工具链 | **PASS** | agentcad 0.7.1、build123d 0.10.0、OCP 7.8.1.1、FreeCAD 1.0.2、ccx 2.22、gmsh 4.13.1（本审计核对版本/软链）；FEA 已实际运行 |
| 3.2.2 | 参数化建模、关键尺寸集中、模型生成与参数配置分离 | **PARTIAL** | 关键尺寸集中在 square_model.py 顶部（符合集中管理），但 config/mechanical_params.yaml 只是人工摘要、不参与生成（生成与配置未真正分离） |
| 3.2.3 | 关键结构有明确设计依据 | **PASS** | HY928D 参数逐项对照 ref 图纸/照片（mechanical/hy928d/notes.md §1–3）；FEA/verify 数据支撑通槽、方案 A、0.5 mm 限位决策 |
| 3.2.4 | 未确认尺寸不伪装成已验证尺寸 | **PASS** | PROVISIONAL 标注：config/mechanical_params.yaml、square_model.py:53、hx711_hw.c counts_per_g、FEA results.json provisional 字段 |
| 3.2.5 | 每次修改可通过 Git 追溯 | **PASS** | 31 次提交按阶段拆分；验证产物（verify_report/DRC/ERC/results.json）入库 |

### §3.3 电路设计工具

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 3.3.1 | KiCad + ngspice + Python 工具链 | **PASS** | kicad-cli 9.0.9、ngspice-36（本审计复跑前端网表）；design.py/gen_sch.py/verify.py 脚本化 |
| 3.3.2 | 电路设计流程：需求→架构→选型→原理图→ERC→PCB→DRC→Gerber/BOM | **PASS** | electronics/kicad/scripts/build.sh 全链；ERC.rpt 0/0、DRC_2l.rpt 0/0、build/gerbers/、BOM.csv、DFM.md、装配图 pdf/png |
| 3.3.3 | 保留器件型号、数据手册、关键参数和选型依据 | **PARTIAL** | BOM.csv 有型号/封装/描述，但无 datasheet 链接、无工作电压/电流/接口字段；风险与替代方案散在 DECISIONS/pinmap；10 行 passive 缺 MPN |
| 3.3.4 | 声明 HX711 无芯片级 SPICE 模型，只做等效/行为仿真 | **PASS** | docs/01 §3.3、§13.3；electronics/simulation/README §说明；hy928d_frontend.json caveats |
| 3.3.5 | 原理图、PCB、Gerber、BOM 等交付物齐备 | **PASS** | smartcoaster.kicad_sch、smartcoaster_2l.kicad_pcb、8 层 Gerber+drl+pos+gbrjob+zip、BOM.csv、装配图 |

### §3.4 固件开发工具

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 3.4.1 | ESP-IDF、C/C++、pytest 工具链 | **PASS** | ESP-IDF v6.1；bin 519,152 B（审计时存在）；pytest 9.2.0；host C 测试 2/2（41+198 checks） |
| 3.4.2 | Wokwi ESP32-S3+HX711+OLED 虚拟样机 | **PARTIAL** | firmware/wokwi/ 保留 diagram/SCENARIOS，仅离线 lint；云仿真因限额/不传第三方搁置（docs/05 §0 有决策记录），不参与验收 |
| 3.4.3 | BLE 协议栈 | **PARTIAL** | ble.c 270 行 NimBLE GATT 服务 0xFF00（6 特征）；无 BLE 自动化测试、无手机端、无实物验证；断线后不自动重新广播（ble.c:52-59） |
| 3.4.4 | 固件功能：采集/滤波/校准/事件/OLED/按键/BLE/低功耗 | **PASS** | firmware/esp32/main/ 18 个模块；docs/06 分层；app_main.c 已启用 esp_pm light sleep + BT modem sleep |
| 3.4.5 | 普通版与 Solar 版共享业务逻辑 | **N/A** | Solar 版尚未立项（PRD §2.2 明确后续独立评估），当前无共享对象可核 |

### §4 项目目录结构

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 4.1 | docs/architecture、docs/decisions 目录 | **GAP** | 不存在；决策散落 electronics/kicad/DECISIONS.md、docs/design/、HANDOFF |
| 4.2 | config/electronics.yaml、config/firmware.yaml | **GAP** | config/ 仅 mechanical_params.yaml + README；电子/固件参数散在 pinmap.md、design.py、Kconfig |
| 4.3 | mechanical/{src,assemblies,exports,reports} 映射 | **PARTIAL** | 实际为 cad/（源+自检）、build/parts、build/assembly、build/render、build/verify_report.json；命名不同但功能等效 |
| 4.4 | electronics/{schematic,pcb,simulation,fabrication} 映射 | **PARTIAL** | 实际 kicad/smartcoaster/（sch+pcb）、kicad/build/（制造/装配）、electronics/simulation/（SPICE）；simulation/electronics/ 仅 README |
| 4.5 | firmware/{main,components,tests,config} 映射 | **PARTIAL** | esp32/main 与 sdkconfig.defaults 对应 main/config；无 components/；测试在根 tests/firmware/ |
| 4.6 | simulation/{mechanical,electronics,system} 四层目录 | **PARTIAL** | mechanical/ 有完整 FEA；electronics/、system/ 仅 3 行 README（电路仿真实际在 electronics/simulation） |
| 4.7 | tests/{mechanical,electronics,firmware} | **PARTIAL** | firmware 测试完整；mechanical/、electronics/ 只有标题 README，验证脚本在各自工程内 |
| 4.8 | scripts/ 跨项目脚本 | **GAP** | scripts/README.md 规划了 STEP→FEA、结果汇总、Xvfb/渲染三类脚本，目录为空 |
| 4.9 | build/ 跨项目汇总产物 | **GAP** | build/ 只有 README；无总装索引/总报告/发布包 |

### §5 需求驱动开发

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 5.1 | 产品需求统一维护在 PRD | **PASS** | docs/02 PRD 485 行：定位/版本/外观/机械/电子/固件/手机端/验收；BOM.md、README 同步口径 |
| 5.2 | 结构化配置文件记录目标与状态 | **PARTIAL** | config/mechanical_params.yaml 有效并含 status；PRD §5 示例中的 electronics/firmware 结构化配置缺失（见 4.2） |
| 5.3 | 不确定参数明确标记 | **PASS** | mechanical_params.yaml hy928d.status=provisional；PRD §8.2 M2-01..11；FEA/固件均有 PROVISIONAL 标记 |
| 5.4 | 需求变更同步更新相关文档 | **PARTIAL** | LED/2 层变更已同步 README/HANDOFF/docs07/09/10/11/12/VERIFY；但 HEAD 上 PRD、electronics/README、DECISIONS、pipeline §13.3、config 仍留旧口径（见附录 F1–F9） |

### §6 机械设计工作流 M0–M3

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| M0.1 | M0 输入：需求/外观参考/HY928D 图纸/实物照片/供应商资料 | **PASS** | docs/02、ref/design.png、ref.jpeg、ref/hy928d/*.webp、HY928D 图纸转录、HX711 手册转录 |
| M0.2 | M0 输出：结构方案、传感器安装分析、受力路径图 | **PASS** | PRD §4.1/4.2 称重路径图；ref/HY928D §4.1 安装方案 A/B 分析；ref/Hydrate §6 A/B/C 取舍 |
| M0.3 | M0 输出：参数清单、未确认事项 | **PASS** | docs/恢复：…自包含参数手册 §1/§3；ref/HY928D §7/§8；PRD §8.2 共 11 项 |
| M1.1 | HY928D 参数化参考模型 | **PASS** | mechanical/hy928d/src/hy928d_v2.py + build/params.json；config u_slot/arch 参数同步 |
| M1.2 | 传感器安装接口/浮动顶板/底壳安装区/过载保护结构 | **PASS** | square_model.py make_shell（4 cell bosses + 4 PCB standoffs）、make_plate（裙边+Ø6 传力柱）、0.5 mm 过载限位；verify 21/21 |
| M1.3 | 传感器真实安装方式必须先确认（方案 A/B/C） | **GAP** | 采用假设 A；ref/HY928D §4.1 标为最关键未决项，PRD §8.2 M2-02/03 开放；无供应商确认/实物剖解记录 |
| M2.1 | 完整建模：顶板/底壳/OLED 区/圆键/PCB 固定/USB-C 开孔/脚垫/排线通道 | **PARTIAL** | 12 件含 shell/plate/oled/button/pcb/usbc/pad/glass；无排线/软线通道几何（J4/J5 1.25 mm 线束仅在 DECISIONS 文字假设） |
| M3.1 | 尺寸/装配干涉/顶板运动/过载限位验证 | **PASS** | verify_v01.py 21/21 复跑：bbox 100×100×18、37 对干涉 0、0.5 mm 满行程无遮挡、限位 7.28 kg 先接触、STEP 回读 12 solids |
| M3.2 | 传感器可达性/螺钉装配空间/排线活动空间/称重旁路检查 | **PARTIAL** | 已有 button/OLED/battery 间隙与「顶板下 0.05 mm 内无零件」检查；无螺钉工具空间、无排线活动空间、无装配级旁路刚度/接触验证 |
| M3.3 | 输出 STEP、STL 和装配报告 | **PARTIAL** | STEP/STL + verify_report.json（21 条）+ README 齐备；无工程图/装配图/公差与对齐报告 |

### §7 电路设计工作流 E0–E4

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| E0.1 | 系统架构明确：MCU/传感器/ADC/OLED/按键/电源/USB-C/BLE | **PASS** | electronics/pinmap.md §1–4；PRD §5；NETLIST.md 28 网络；docs/06 §7 |
| E1.1 | 每个器件记录型号/手册/电压/电流/接口/封装/选型原因/风险与替代 | **PARTIAL** | BOM.csv 有型号/封装/描述，缺 datasheet、电压电流接口字段、选型原因/替代（只在 DECISIONS/pinmap 零散出现）；10 行缺 MPN |
| E2.1 | 原理图完成：电源输入/管理/称重/MCU/OLED/按键/USB-C/调试接口 | **PASS** | NETLIST.md 28 网络覆盖：J1+U7、U3、U4/U5、U6、U1+EN/BOOT、U2+J3、J4、J5；调试走 S3 原生 USB；ERC 0/0 |
| E3.1 | PCB 检查：布局/电源回路/模拟走线/接地/接插件/安装孔/外形匹配 | **PARTIAL** | DRC 0/0、DFM 5 项 PASS、47 footprint/576 track/62 via/29 net（本审计 pcbnew 复核）；但 2 层 ZONES=0 无铺铜，无电源完整性/电流密度/阻抗复核文档 |
| E4.1 | 完成 ERC | **PASS** | 本审计独立重跑 kicad-cli sch erc → 0 Errors / 0 Warnings（/tmp/ERC_audit.rpt） |
| E4.2 | 完成 DRC | **PASS** | 本审计独立重跑 kicad-cli pcb drc --severity-all → 0 violations / 0 unconnected（/tmp/DRC_audit.rpt） |
| E4.3 | 完成必要的电路仿真 | **PARTIAL** | ngspice 前端 DC/AC：3.956 mV→0.5064 V（×128）、RC −3 dB 1655 Hz、50 Hz −14.2 dB；无电源、MCU 接口、.noise/.tran/蒙特卡洛 |
| E4.4 | 不将仿真结果替代真实硬件测试 | **PASS** | docs/01 §13.3 边界；docs/05 §0 四类仿真边界；FEA README §5；固件 REPORT §7.2 |

### §8 固件设计工作流 F0–F4

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| F0.1 | 软件架构分层：Application/Hydration/Weight/Display/Button/BLE/Power + Drivers | **PASS** | docs/06 §1 依赖图；firmware/esp32/main/ 模块划分；纯逻辑层不 include ESP-IDF |
| F1.1 | 传感器采集：原始读取/零点校准/重量换算/数字滤波/异常值/稳定性 | **PASS** | hx711_hw.c read_counts/tare、weight_sensor.h grams、weight_process.c 中值+稳定窗+去尖峰；host_mock 9/9 覆盖噪声/漂移/饱和/量化 |
| F2.1 | 饮水行为识别：放杯/移走/饮水下降/加水上升/移动干扰/稳定状态 | **PASS** | intake.c 事件与模式；hydration.c 门面；host_core 11/11、C↔Python 16/16 场景（本审计复跑） |
| F3.1 | 显示与交互：重量/饮水量/状态/按键 | **PASS** | ui.c 视图与手势；oled.c 128×32 + 中文子集；button.c 30 ms 去抖/单击/双击/长按 |
| F4.1 | BLE：发现/配对连接/数据同步/断线重连/手机接收 | **PARTIAL** | ble.c 实现广播/连接/0xFF00 六特征 notify；DISCONNECT 后未自动重新广播（ble.c:52-59），无手机端；无 BLE 测试 |
| F4.2 | BLE 验证 | **GAP** | 无 BLE 单元/协议/实物测试；仅 tests/handboard/BRINGUP_RECORD.md §5 手工勾选框 |

### §9 验证与质量管理

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 9.1 | 机械验证：尺寸/装配/干涉/顶板活动/过载保护/称重路径 | **PARTIAL** | 前五项由 verify_v01 21/21 覆盖；称重路径仅几何间隙检查，无装配级载荷/旁路验证（依赖 §13.2 C） |
| 9.2 | 电气验证：电源电压/电流/传感器噪声/ADC 稳定性/OLED/BLE/低功耗 | **GAP** | 无任何实物测量；仅有设计值/仿真估算（docs/08 功耗估算、pinmap 电流表、ngspice 前端）；BRINGUP_RECORD 为空表 |
| 9.3 | 固件验证：单元/驱动/事件识别/BLE/异常恢复/长时间运行 | **PARTIAL** | 单元 41 checks、mock 198 checks、事件 16 场景、pytest 16 均通过；BLE 测试、异常恢复注入测试、长跑测试缺失 |
| 9.4 | 整机验证：不同杯型/杯底/空满杯/少量大量饮水/移动/重新放置/静置/温湿度 | **GAP** | 未开始；依赖手板采购/装配（用户侧） |
| 9.5 | 所有功能都有可验证的验收条件 | **PARTIAL** | PRD §9、docs/05 §3 测试矩阵、tests/handboard 验收清单存在；但 config/validation_mechanical.yaml 缺失、电气/整机阈值未回填（docs/01 §13.2 验收 YAML 全 null） |

### §10 AI Agent 执行规范

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 10.1 | 先读 PRD/AGENTS.md/设计文档再分析修改 | **PASS** | AGENTS.md 第 1 条；HANDOFF 先读清单；本审计亦遵循 |
| 10.2 | 重要结构先给方案，等待人工确认 | **PARTIAL** | 有方案与待确认记录（PRD §8.2、DECISIONS、docs/交付说明 §6），但无正式评审/签署记录；M1.3 未确认即进入 FEA/PCB |
| 10.3 | 不得虚构器件参数、不得把推测当事实 | **PASS** | ref 转录区分「图纸原文/推断」；PROVISIONAL 标注；FEA README §5 局限 |
| 10.4 | 每次修改记录原因 | **PASS** | 31 次提交信息可读；DECISIONS.md、VERIFY_REPORT F1–F7、HANDOFF §4 根因记录 |
| 10.5 | 生成文件后必须执行检查 | **PASS** | build.sh 末尾 DRC/DFM；verify_v01.py；run_host_tests.sh；FEA 收敛检查 |
| 10.6 | 对无法验证的结论明确标记 | **PASS** | docs/05 §0、FEA README §5、firmware/REPORT §7、HANDOFF §8 红线 |
| 10.7 | 不允许未经确认进入高成本打样 | **PASS** | 未下打样/打印单；HANDOFF §7 将采购/打样列为用户侧 |
| 10.8 | 每个任务输出八要素（目标/输入/假设/文件/过程/结果/未解决/下一步） | **PARTIAL** | HANDOFF、VERIFY_REPORT、FEA README、固件 REPORT 基本齐备；非所有任务统一模板（如 PCB 报告为历史版、DECISIONS 过简） |

### §11 开发里程碑

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| P0 | 环境搭建（AgentCAD、build123d、MCP） | **PARTIAL** | 工具齐备且版本锁定（requirements.yaml + 安装记录）；agentcad 自带 MCP 可导入，但 MCP 未启用、无调用证据 |
| P1 | 产品结构方案（结构图、参数表） | **PASS** | PRD §3/§4、恢复手册 §1、square_v1/lumen 模型与渲染、config 参数表 |
| P2 | 机械设计（3D 模型、STEP、STL） | **PASS** | square_v1 12 件 STEP/STL + 装配；lumen 13 件；FreeCAD 复核 12/13 solids 与 bbox 一致 |
| P3 | 电路设计（原理图、PCB、BOM） | **PASS** | 原理图 43 器件/28 网络、2 层 PCB 0/0、Gerber/drl/pos/zip、BOM 24 行/43 器件、装配图 |
| P4 | 固件开发（传感器、显示、BLE） | **PARTIAL** | 代码与主机测试完成（采集/滤波/事件/OLED/按键/BLE GATT/PM）；未上板，BLE/OLED/HX711 真实外设未验证 |
| P5 | 数字验证（S1 机械 FEA → S2 电路 SPICE → S3 固件仿真 → S4 MCP 编排） | **PARTIAL** | S1 完成 HY928D 本体；S2 仅前端 DC/AC；S3 host+QEMU 基本完成（QEMU 未复跑）；S4 未开始 |
| P6 | 实物打样（3D 打印、PCB） | **GAP** | 未下单；仅制造文件与打印布局就绪 |
| P7 | 整机验证（测试报告） | **GAP** | 未开始；依赖 P6 |
| P8 | 产品迭代（V1.1 / Solar 版） | **GAP** | 未开始；PRD §2.2 明确 Solar 后续立项 |

### §12 核心原则

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 12.1 | 可复现 | **PASS** | 脚本化生成（build.sh、export_v01.py、run_host_tests.sh）；requirements.yaml 版本锁定；FEA 有复跑命令与结果 JSON |
| 12.2 | 可验证 | **PASS** | verify_v01 21/21、ERC/DRC 0/0、host 测试、FEA 收敛；docs/VERIFY_REPORT 独立复核 7/7 |
| 12.3 | 可修改 | **PASS** | 参数化模型 + 单一设计源（design.py / square_model.py）；模块化固件分层 |
| 12.4 | 可追溯 | **PARTIAL** | git 31 提交与验证报告可追溯；但多处文档与实测状态漂移（附录 F1–F9），削弱从文档到证据的可追溯性 |
| 12.5 | 可迁移 | **PARTIAL** | 恢复手册 + requirements.yaml 支持迁移；但脚本/文档大量硬编码 /data/Documents/... 绝对路径（build.sh、route_2l.sh、README 命令） |
| 12.6 | 工具链开放 | **PASS** | 全部本地/免费工具；无云依赖（Wokwi 主动搁置）；未上传第三方 |
| 12.7 | 设计不绑定单一 Agent 或模型 | **PASS** | agentcad/build123d/ESP-IDF/KiCad 均为开源或官方工具；仓库无厂商锁定配置 |

### §13 仿真工程

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 13.1.1 | 四层仿真之机械层 | **PASS** | simulation/mechanical/hy928d/：CalculiX 结果 .dat/.frd、results*.json、6 张云图、README 含假设/收敛/局限 |
| 13.1.2 | 四层仿真之电路层 | **PARTIAL** | electronics/simulation/：桥路+HX711 行为增益 DC/AC；仅一个网表，无电源/MCU/噪声/蒙卡（见 §13.3） |
| 13.1.3 | 四层仿真之固件层 | **PARTIAL** | ESP-IDF build + host 测试 + QEMU 冒烟；Wokwi 搁置；QEMU 在删 halo 后未复跑，无原始日志入库 |
| 13.1.4 | 四层仿真之系统层（参数→仿真→验收→报告→归档一条命令） | **GAP** | 无系统级脚本/编排；scripts/ 为空、simulation/system/ 仅 README；各域需手工按序执行 |
| 13.2.1 | 对象 A：HY928D 本体 FEA（4 孔固定+中央力） | **PASS** | 5 kg 中心 0.3435 mm、支反力 49.05 N(100%)、非奇异热点 468 MPa；h=0.28 收敛（0.35/0.30/0.28 差<0.1%）；通槽 vs 0.7 mm 浅腔对比 |
| 13.2.2 | 对象 B：顶板+传力柱 FEA（中心/偏载 r=30/45，1/5 kg） | **GAP** | simulation/mechanical/ 下无顶板/传力柱算例（仅 hy928d/）；无偏载倾角、柱端接触应力数据 |
| 13.2.3 | 对象 C：整体装配 FEA（过载限位先接触/旁路/安全系数） | **GAP** | 无装配级 FEA；0.5 mm 限位先接触仅有几何检查（verify）与手算 7.28 kg，无接触/预紧/底座柔度模型 |
| 13.2.4 | 前置条件冻结：U 槽形式/安装方案 A-B-C/材料/灵敏度与安全位移 | **PARTIAL** | U 槽通槽已按照片选定并做了浅腔对比；材料 65Mn 标准值；但供应商未确认 U 槽曲线/安装方案（假设 A）/实际灵敏度与安全位移 |
| 13.2.5 | 验收指标与阈值来源（§13.2 验收 YAML） | **GAP** | docs/01 §13.2 验收 YAML 全 null、status=pending_material_and_sensor_data；config/validation_mechanical.yaml 不存在；verify 脚本内阈值无来源引用 |
| 13.2.6 | 记录 assumptions/边界/材料/版本/局限 | **PASS** | FEA README §2/§5；results.json meta/material/assumptions/limitations；SIGSEGV 网格失败档也记录 |
| 13.3.1 | 模块：惠斯通电桥等效 + 灵敏度量级 | **PASS** | hy928d_frontend.cir：3.3 V×1.2 mV/V=3.956 mV；本审计复跑 ngspice 得 v(nout)=0.5064 V（×128） |
| 13.3.2 | 模块：HX711 前端行为模型（增益/输入范围/滤波） | **PARTIAL** | 行为级增益 128 + 一阶 10 Hz 输出滤波 + RC；未建模 INL/offset/共模限制（results caveats 已注明） |
| 13.3.3 | 模块：电源仿真（USB-C/充电/LDO/电池/纹波） | **GAP** | 无电源网表；仅 pinmap 电流表与 docs/08 估算 |
| 13.3.4 | 模块：MCU 接口仿真（GPIO/I2C/复位/电平/上电时序） | **GAP** | 无相关网表或时序分析 |
| 13.3.5 | 分析类型：.op/.dc/.ac/.tran/.noise/蒙特卡洛 | **PARTIAL** | 已做 .dc 与 .ac；.op 隐含；.tran/.noise/蒙卡缺失（README 说明噪声以数据手册为准） |
| 13.3.6 | §13.3「本机状态」与实际一致 | **PARTIAL** | docs/01 §13.3 仍写 66 器件/43 网络/186 未连接（历史 P1 初稿），与当前 43/28、2 层 0/0 不符（见 F2） |
| 13.4.1 | ESP-IDF 构建 | **PASS** | firmware/esp32/build/smartcoaster.bin=519,152 B（审计时存在）；REPORT §2 有 0 warning/0 error 与 66% 分区余量记录 |
| 13.4.2 | QEMU 9.2.2 启动冒烟 | **PARTIAL** | firmware/REPORT §5 有启动日志摘录与根因；QEMU 9.2.2 可执行文件存在；但删 halo 后未复跑、无原始日志入库（见 F10） |
| 13.4.3 | 主机测试（HX711 mock/状态机/pytest/差分） | **PASS** | 本审计复跑：host_core 41 checks 11/11、host_mock 198 checks 9/9、差分 16/16（82 records）、pytest 16 passed |
| 13.4.4 | Wokwi 7 场景自动化 | **PARTIAL** | 未使用（云/限额/不传第三方，docs/05 §0 有决策）；firmware/wokwi/ 仅离线 lint，SCENARIOS 记录 7 场景设想 |
| 13.4.5 | 固件仿真边界声明（无 HX711/OLED 外设模型） | **PASS** | docs/05 §0、docs/06 §6、firmware/REPORT §5.1/§7.2 |
| 13.5.1 | 统一工具接口（mechanical.*/electronics.*/firmware.*/validation.*） | **GAP** | 无 Python 包装层；各域仅有独立 shell/python 脚本，无统一函数名/参数/返回结构 |
| 13.5.2 | 一条命令跑 S1–S3 并生成统一报告 | **GAP** | 不存在；需分别执行 mechanical export/verify、kicad build.sh、FEA 脚本、run_host_tests.sh |
| 13.5.3 | 统一 artifacts 归档（STEP/CSV/JSON/PNG/JUnit） | **GAP** | 无 artifacts 目录/索引/版本哈希；产物分散在各子项目 build/ 与 simulation/ |
| 13.6.1 | 工具安装位置与版本锁定（§13.6 表 + requirements.yaml） | **PARTIAL** | §13.6 表内工具均已安装（软链/版本本审计核对）；但 Freerouting 2.5.0（布线必需）未写入 requirements.yaml，Xvfb/poppler 也未锁定 |
| 13.7.1 | S1 状态（机械 FEA 打通） | **PARTIAL** | HY928D 中心加载完成；顶板中心/偏载未做；应力/位移 JSON+云图已交付 |
| 13.7.2 | S2 状态（电路 SPICE 打通） | **PARTIAL** | 桥路+行为前端 DC/AC 打通；电源/噪声/蒙卡/参数扫描报告未做 |
| 13.7.3 | S3 状态（固件仿真打通） | **PARTIAL** | host+ESP-IDF+QEMU 冒烟基本完成；Wokwi 7 场景未做（搁置）；QEMU 未复跑 |
| 13.7.4 | S4 状态（MCP 编排） | **GAP** | 未开始；无最小编排脚本/MCP server/统一报告 |
| 13.8.1 | 仿真结果落机器可读指标（JSON/CSV） | **PASS** | results.json/results_*.json/comparison_slot_vs_shallow.json/hy928d_frontend.json；mesh_*_quality.json |
| 13.8.2 | 每个仿真任务写明假设/边界/材料/版本 | **PASS** | FEA README §2/§5 与 results.json meta/assumptions；SPICE README caveats；固件 REPORT 环境/复现命令 |
| 13.8.3 | 不确定参数用参数扫描/对比表达 | **PASS** | 网格 h=0.15/0.20/0.25/0.28/0.30/0.35 收敛族 + C3D4/C3D10 交叉；通槽 vs 0.7 mm 浅腔对比 |
| 13.8.4 | 仿真不替代实物标定 | **PASS** | docs/01 §13.2/§13.8；FEA README §5；HANDOFF §8；AGENTS.md §7 |
| 13.8.5 | 任何「通过」都有阈值来源（PRD/标准/供应商/实测） | **PARTIAL** | 机械 verify 阈值硬编码且无来源注释；FEA 屈服强度/安全位移待供应商；docs/01 §13.2 阈值 null |
| 13.9.1 | Blender 工具/后台脚本/场景配置 | **PASS** | Blender 4.5.3；render/{square_b,lumen,cmf,packaging,print}/build_scene.py + config.json；RENDER_LOG 有复现命令与时间戳 |
| 13.9.2 | 输出 hero/front/pcb_detail/exploded.png（方形 B 与 LUMEN 各一套） | **PASS** | render/square_b/renders/{hero,front,pcb_detail,exploded}.png；render/lumen/renders/ 同四项；cmf/packaging/print 附加产物 |
| 13.9.3 | KiCad 3D 导出（kicad-cli pcb export step/glb） | **GAP** | 未做；render/README §待做 明确「封装无 3D 模型，暂用机械 CAD 电子占位」 |
| 13.9.4 | STEP 为尺寸/打印源，STL 仅渲染；GLB 坑记录 | **PASS** | render/README 说明；build123d 逐件 GLB 丢位置问题已记录并改用 STL |

### §14 MCP 仿真编排层

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 14.1 | MCP 分层：mechanical/electronics/firmware/validation 四类工具 | **GAP** | 无 MCP server、无四类工具注册；仅 mechanical/lumen/.mcp.json.example 示例（agentcad 自带 MCP，未启用） |
| 14.2 | 统一接口契约 JSON（tool/status/inputs/artifacts/metrics/warnings/duration_s） | **GAP** | 各域脚本无统一返回结构；无契约实现/测试 |
| 14.3 | 失败返回 error_kind/stderr 摘要/可复现命令 | **GAP** | 无 MCP 层；脚本失败仅 shell 退出码/日志 |
| 14.4 | 路径相对项目根、产物进 simulation\|build、版本+参数哈希写入报告 | **GAP** | 产物分散；无 commit/参数哈希入报告机制 |
| 14.5 | 不建议做法：GUI 自动化、看图验收、默认值当设计值、未冻结边界给精度结论 | **PASS** | 全流程无 GUI 点击自动化；验收用 DRC 报告/JSON/数值断言；FEA 明确假设与趋势边界 |
| 14.6 | 若做最小 MCP 实现，当前缺什么 | **GAP** | 缺：①统一 CLI/Python 包装（generate_model/export_step/run_fea/run_erc/run_spice/run_drc/run_unit_tests/run_suite）；②统一 JSON 结果 schema+artifacts 索引；③编排入口（一条命令串 S1–S4）；④MCP stdio server 暴露上述工具；⑤失败结构/版本哈希；⑥审批门与报告模板。估计 4–6 人日（不含等待仿真时长） |

### §15 参考资料 ref/

| # | 检查项 | 判定 | 证据 / 说明 |
|---|---|---|---|
| 15.1 | ref 资料齐备并有无损 Markdown 转录 | **PASS** | ref/README.md；HY928D 图纸转录 190 行、HX711 手册转录 298 行、Hydrate 拆解 243 行；原件保留 |
| 15.2 | HY928D 参数已消费到 config/机械模型/FEA | **PASS** | config/mechanical_params.yaml u_slot/arch/孔位；mechanical/hy928d/src/hy928d_v2.py + notes.md；FEA 几何即 v2（U 槽/拱/竖槽） |
| 15.3 | HX711 手册参数已消费到电路/固件 | **PASS** | design.py：SOP-16、3.3 V 外部激励、gain 128、10 SPS、R25/R26 1k+C16 100nF；固件 counts_per_g=515.4/±12.9 mV；pinmap §3 |
| 15.4 | Hydrate/design.png 已消费到结构/交互/包装 | **PASS** | 浮动顶板、C 形 PCB、前缘屏+按键、100 ms 采样+稳定窗、砝码标定流程；包装/CMF 参考；docs/10、docs/11、submission/ |
| 15.5 | 参考与设计的差异有记录（14→18 mm、双键→单键、非 SC134 安装） | **PASS** | ref/Hydrate §3.1/§5/§6；docs/02 §4.3；docs/10；docs/07；README「14 mm 装不下」 |

---

## 3. 未达成清单 — GAP（28 项，含补救建议与工作量）

| # | 缺口 | 补救建议 | 工作量估计 | 优先级 |
|---|---|---|---|---|
| 2.3 | 实物打样与实际测试未开始 | 用户采购/打样后按 docs/09 装配、按 BRINGUP_RECORD 标定；AI 可先出下单包与测试脚本 | 用户 2–4 周（含采购/打样周期）；AI 1 日准备 | P0 |
| 4.1 | docs/architecture、docs/decisions 缺失 | 把 pinmap/电源树/架构图归入 docs/architecture；DECISIONS 提升到 docs/decisions 并在 README/HANDOFF 链接 | 0.5–1 人日 | P2 |
| 4.2 | config/electronics.yaml、firmware.yaml 缺失 | 从 design.py/Kconfig 生成结构化 electronics/firmware 配置（只读摘要），或在 config/README 明确声明单一真值位置 | 0.5–1 人日 | P2 |
| 4.8 | scripts/ 跨项目脚本为空 | 补 scripts/{run_all,collect_results,render_all}.py 或并入 §14 编排层统一实现，避免两份 | 随 §14 一起 4–6 人日 | P1 |
| 4.9 | build/ 无跨项目汇总 | 生成 build/index.md：总装 STEP、FEA/SPICE/固件结果、DRC/ERC、版本哈希 | 0.5 人日 | P2 |
| M1.3 | HY928D 真实安装方式未确认 | 向供应商发 8 问清单（ref/HY928D §8）或剖开/实测；确认后重跑 FEA 并更新 verify/PRD | 等待供应商；确认后重算 1–2 人日 | P0 |
| F4.2 | BLE 无验证 | 加 host 侧 GATT 协议单测（若有 HCI mock 难度大）或至少加硬件 bring-up 脚本+日志模板；手机端可用 nRF Connect 记录 | 1–2 人日 + 手板 0.5 日 | P2 |
| 9.2 | 电气实测全部缺失 | 手板到手后按 BRINGUP_RECORD 测电压/电流/噪声/漂移/功耗；把结果回填 config/validation_electronics.yaml | 用户 1–2 日（需硬件）；AI 准备脚本 0.5 日 | P0（用户侧） |
| 9.4 | 整机验证缺失 | 按 docs/05 §3 11 项矩阵与 PRD §9 执行 7 天记录；结果入库 | 用户 5–10 人日（含 7 天静置） | P0（用户侧） |
| P6 | PCB/3D 打印未打样 | 用 build/smartcoaster_2l_gerbers.zip 下单 JLC 2 层；STL 打印外壳/顶板；首批 3 套 | 用户 1–2 周（板厂/打印周期） | P0（用户侧） |
| P7 | 整机验证未做 | 同 9.4 | 用户 5–10 人日 | P0（用户侧） |
| P8 | 产品迭代未开始 | 按样板结果决定 V1.1；Solar 版另行立项 | 后续项目 | P3 |
| 13.1.4 | 系统层一条命令编排缺失 | 实现 scripts/orchestrate.py：参数→机械 export→verify→FEA→ERC/DRC→host tests→汇总 report.md/JSON；先 CLI 后 MCP | 2–3 人日（最小 CLI） | P1 |
| 13.2.2 | 顶板+传力柱 FEA 未做 | 以 square_v1 顶板+Ø6 柱为对象，中心/偏载 r=30/45、1/5 kg；输出挠度、倾角、柱端接触应力 JSON+云图 | 2–3 人日 | P1 |
| 13.2.3 | 整机装配 FEA 未做 | 装配级模型：传感器+4 角柱+底壳+限位；过载 0.5/0.6 mm 接触顺序、旁路力、安全系数；需接触非线性 | 3–5 人日 | P1 |
| 13.2.5 | 仿真验收阈值无来源 | 向供应商确认屈服/额定形变；把阈值写进 config/validation_mechanical.yaml 并在 verify/FEA 中引用来源 | 0.5–1 人日（数据到手后） | P0 |
| 13.3.3 | 电源模块仿真缺失 | 补 ngspice 电源网表：USB-C→TP4056→电池→ME6211，.op/.tran 纹波与压降；落 JSON | 1–2 人日 | P2 |
| 13.3.4 | MCU 接口仿真缺失 | 补 GPIO/I2C 上拉、EN/BOOT 上电时序、电平兼容的简易 .tran 检查或文档化计算 | 0.5–1 人日 | P3 |
| 13.5.1 | 统一工具接口缺失 | 按 docs/01 §13.5 的 12 个接口名实现 Python 包装（返回统一 JSON） | 2–3 人日 | P1 |
| 13.5.2 | 一条命令跑全流程缺失 | 与 13.1.4 合并实现 | （已含） | P1 |
| 13.5.3 | 统一 artifacts 归档缺失 | 约定 artifacts/{mech,elec,fw,sys}/<case>.json + index.json（commit/参数哈希） | 1 人日 | P1 |
| 13.7.4 | S4 MCP 编排未开始 | 在 13.5 基础上加 MCP stdio server（stdio JSON-RPC）暴露 12 工具；先只读、加审批门 | 3–4 人日 | P1 |
| 13.9.3 | KiCad 3D 导出未做 | 补关键封装 3D 模型后 kicad-cli pcb export step/glb，替换机械占位并重渲 pcb_detail | 0.5–1 人日 | P3 |
| 14.1 | MCP 四类工具层未实现 | 同 13.7.4；按 mechanical/electronics/firmware/validation 四组注册 | （含在 13.7.4） | P1 |
| 14.2 | 统一接口契约未实现 | 定义 JSON Schema 并在包装层校验；失败带 error_kind/stderr/command | 1 人日 | P1 |
| 14.3 | 失败结构缺失 | 包装层统一捕获 stderr 摘要与可复现命令 | 0.5 人日 | P1 |
| 14.4 | 产物路径/版本哈希机制缺失 | 所有工具输出相对路径；report 头部写 git commit + 输入参数哈希 | 0.5 人日 | P1 |
| 14.6 | 最小 MCP 实现缺口 | 按 14.1–14.4 实施；建议先 CLI（2–3 日）再 MCP（3–4 日） | 合计 4–6 人日 | P1 |

> 工作量口径：1 人日 = 熟悉本仓库的工程师 1 个有效工作日；仿真/打样等待时间未计入。硬件相关项标注「用户侧」：AI 只能准备脚本/文档，不能代替采购、装配与实测。

---

## 4. 部分达成整改清单 — PARTIAL（46 项，按主题分组）

| 覆盖检查项 | 问题 | 补救建议 | 工作量估计 |
|---|---|---|---|
| 1.2, 2.1, 3.1.3, 3.1.6 | MCP/角色层只到示例与口头分工 | 启用 .mcp.json 并在 HANDOFF 记录一次 MCP 调用；补 6 角色职责表（产品/机械/电子/固件/验证/集成） | 0.5 人日 + MCP 任务 |
| 2.2 | 跨域验证闭环未统一 | 并入 §14 编排：一条命令汇总三类检查并生成总报告 | 含 §14 |
| 3.2.2, 5.2 | 模型生成与参数配置未分离、电子/固件配置缺失 | 把 config 变为由脚本读取的机器配置（或明确「模型文件即唯一真值，config 只读摘要」）；补 electronics/firmware 配置 | 1 人日 |
| 3.3.3, E1.1 | 选型记录字段不全（datasheet/电压电流/替代/MPN） | BOM.csv 增列：Datasheet、Vmin/Vmax、Ityp、Interface、Alternates；补齐 10 行 MPN（采购后） | 0.5–1 人日 |
| 3.4.2 | Wokwi 未用 | 维持「搁置」决策并写入 VALIDATION_PLAN；不再列为待办，或改用 QEMU+host 覆盖 | 0（决策已记录） |
| 3.4.3, F4.1 | BLE 断线重连与验证不足 | DISCONNECT 事件里按广播占空策略重开广播；加连接状态日志与手板测试项 | 0.5 人日 |
| 4.3, 4.4, 4.5, 4.6, 4.7 | 目录映射与 §4 不一致 | 在 docs/01 §4 或 README 增加「实际目录映射表」；或按规范迁移（不推荐大搬迁） | 0.5–1 人日 |
| 5.4, 12.4 | 文档状态漂移（详见附录 F1–F9） | 一次性文档校准：PRD 加当前状态横幅、electronics/README、DECISIONS、pipeline §13.3/13.4、docs/05、VALIDATION_PLAN、mechanical/hy928d notes、config | 1–2 人日 |
| M2.1, M3.2 | 排线通道/螺钉工具空间/旁路验证缺失 | CAD 增加 FPC/线束走线槽与螺钉工具空间检查项；旁路刚度并入 13.2.3 装配 FEA | 1–2 人日 + 装配 FEA |
| M3.3 | 无工程图/装配图/公差报告 | FreeCAD 出顶板/底壳/装配三视图 PDF + 关键公差表；入库 docs/design/ | 0.5–1 人日 |
| E3.1 | PCB 电源/接地/阻抗复核与铺铜决策缺失 | 补一份 P2 布局评审：电源回路宽度/电流密度、A+/A− 包地与单点地、2 层无铺铜的取舍；必要时灌铜后复跑 DRC | 1 人日 |
| E4.3, 13.3.2, 13.3.5, 13.3.6 | S2 深度不足与文档口径不一致 | 补 .noise/.tran/蒙特卡洛与电源/MCU 模块（分项见 GAP）；更新 §13.3 本机状态 | 2–4 人日 |
| 9.1, 9.5 | 机械验证缺称重路径/阈值来源 | verify 增「唯一载荷路径」装配检查（受力件清单+旁路间隙）；把阈值移入 config/validation_mechanical.yaml 并引用来源 | 0.5–1 人日 |
| 9.3 | 固件验证缺 BLE/异常恢复/长跑 | 加 BLE 协议测试（手板日志）、HX711 超时/IO 错误注入、24 h 长跑脚本；结果落 JSON | 1–2 人日 |
| 10.2, 10.8 | 人工确认记录与任务模板不统一 | 加 docs/decisions/REVIEW_LOG.md（方案/确认人/日期）；统一任务输出模板 8 要素 | 0.5 人日 |
| P0 | MCP 环境未启用 | 同 1.2/3.1.3：启用并记录一次调用 | 0.5 人日 |
| P4, P5, 13.1.2, 13.1.3, 13.4.2, 13.4.4, 13.7.1, 13.7.2, 13.7.3 | 数字验证/仿真阶段性未闭环 | 按 S1→S2→S3 补齐：FEA B/C、SPICE 全模块、QEMU 复跑并保存日志、S3 场景清单；Wokwi 维持搁置 | S1 5–8、S2 2–4、S3 1–2 人日 |
| 13.2.4, 13.8.5 | 前置条件与阈值未冻结 | 供应商确认 U 槽/安装/灵敏度/屈服/安全位移；更新 config 与 FEA 重算 | 等待供应商 + 1–2 人日 |
| 13.6.1 | requirements.yaml 未锁定 Freerouting/Xvfb/poppler | 补 freerouting: 2.5.0、xvfb: 21.1.4、poppler 版本；注明本地 .tools 路径 | 0.25 人日 |
| 12.5 | 绝对路径硬编码 | 脚本改用 ROOT=$(git rev-parse --show-toplevel) 与环境变量；文档命令加「按本机路径替换」 | 0.5 人日 |

---

## 5. 参考资料（ref/）消费核对

| 资料 | 关键结论 | 已被消费到 | 判定 |
|---|---|---|---|
| ref/hy928d*.webp + 转录 | 5 kg/H=1.0/全桥 1.2 mV/V/4×Ø3.1@28/Ø5/U 形通槽（照片）/拱槽 | config u_slot/arch；mechanical/hy928d/src/hy928d_v2.py；FEA 几何；provisional 状态 | PASS |
| ref/hx711官方资料(海芯).pdf + 转录 | 24-bit/gain 128 ±20 mV@5V/10-80 Hz/25-27 脉冲/片内稳压/SOP-16 | design.py（SOP-16/gain 128/10 SPS/3.3 V 外部激励/RC）；firmware counts_per_g=515.4/±12.9 mV；pinmap §3 | PASS |
| ref/ref.jpeg + Hydrate 拆解 | SC134 单点+斜向悬臂；浮动顶板/C 形 PCB/前缘屏+键/100 ms 状态机/砝码标定 | square_v1 浮动顶板+C 形 PCB+前缘屏键；firmware 稳定窗；docs/05 标定流程；明确不采用单点安装 | PASS |
| ref/design.png | 100×100×14、双按键、四层爆炸 | 方形 100×100×18（14 mm 高度预算结论：装不下屏）；单键（B 版交互文档）；四层爆炸渲染 | PASS（差异有记录） |

> 结论：ref 的 4 份资料均已转录并进入设计输入（参数、结构、交互、校准方法），差异（14→18 mm、双键→单键、不用 SC134 单点安装）都有书面记录，未发现「参考了但没落到设计」的项。

---

## 6. 附加发现：证据/文档一致性（不改变阶段判定，但影响可追溯性）

| # | 级别 | 发现 | 证据 |
|---|---|---|---|
| F1 | 中 | HEAD 上 config/mechanical_params.yaml 仍显示 display: 0.49in_OLED、electronics.status: concept，与 0.91 吋屏/已设计 PCB 不符 | git show HEAD:config/mechanical_params.yaml；审计期间已有并发修改（未提交） |
| F2 | 中 | docs/01 §13.3/§13.4 仍写「66 器件/43 网络/186 未连接」「bin 233,360 B」，与实际 43/28、2 层 0/0、519,152 B 不符 | docs/01:701、docs/01:705 |
| F3 | 中 | electronics/README.md 仍写「尚无原理图/PCB」，与已交付原理图/2 层 PCB 矛盾 | electronics/README.md:3 |
| F4 | 中 | electronics/kicad/DECISIONS.md 仍写「不布线、不覆铜」「186 未连接是预期」，与 2 层已布线 0/0 矛盾 | DECISIONS.md:10-12 |
| F5 | 中 | firmware/REPORT.md §7.1 仍写「BLE GATT=桩」「NVS 未做」「功耗/休眠未做」，与 ble.c/storage.c/app_main.c 实际实现矛盾；§2.4 与构建日志仍写分区余 85%（实际 66%） | firmware/REPORT.md:384-386、120、141 |
| F6 | 低 | docs/05 与 VALIDATION_PLAN 计数过期：方形 20/20、18/18（实际 21/21）、233 KB、ERC 1 条 warning（实际 0/0） | docs/05:27,32；VALIDATION_PLAN.md:5 |
| F7 | 低 | docs/07 P1 仍把「PCB 0 short/0 unconnected、ERC/DRC 干净」列为未勾选，并把 ERC 写成 1 warning | docs/07:10,65 |
| F8 | 低 | mechanical/README.md 与 mechanical/hy928d/notes.md 仍写「HY928D 待人工检视/检视通过后再进 FEA」，但 S1 FEA 已完成并有结果 | mechanical/README.md:9,21；mechanical/hy928d/notes.md:4,70 |
| F9 | 中 | PRD 仍为 M1.2 基线（13 实体、U 腔 0.7 mm、C 环 70°、尚未进入 M2），未加「当前状态」链接；需求变更未回流 PRD | docs/02:5-6,173,379；docs/01 §5「需求变更同步」 |
| F10 | 中 | QEMU 冒烟证据只有 REPORT 摘录、无原始日志；REPORT 明示删 halo 后未复跑；build-qemu 已 fullclean | firmware/REPORT.md:14；firmware/esp32/sdkconfig.qemu.defaults 存在 |
| F11 | 低 | Freerouting 2.5.0 是 2 层布线必需工具，但不在 requirements.yaml 版本锁定清单内 | requirements.yaml；route_2l.sh:9,27 |
| F12 | 提示 | 审计期间其他 Agent 并发修改工作区：config、docs/05/06、firmware/REPORT、app_main.c、square_model.py、build.sh、装配图、新增 render_assembly.py 等；本报告以 HEAD=ae17e10 为基线，涉及文件均已读实际内容 | 审计开始 git status 为空；20:26 后 git status 出现未提交改动 |

> 说明：审计开始（20:25）工作区干净；20:26 起其他 Agent 开始并发修改（F12）。本报告判定以 HEAD + 已读实际文件为基线；若这些并发修改随后提交，F1/F2/F5/F6 中的部分问题可能已被修掉，但审计时点确实存在。

---

## 7. 审计方法与复跑证据（只读）

### 7.1 本审计独立复跑的命令

```bash
# 0) 工具入口（本机需 PATH 补 ~/.local/bin）
export PATH=$HOME/.local/bin:$PATH
cd electronics/kicad

# 1) DRC（2 层板，输出 /tmp，不改工程文件）
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export XDG_CONFIG_HOME=$PWD/../.tools/kicad-config
kicad-cli pcb drc --format report --severity-all --units mm \
  -o /tmp/DRC_audit.rpt smartcoaster/smartcoaster_2l.kicad_pcb
# -> Found 0 violations / Found 0 unconnected items

# 2) ERC
kicad-cli sch erc --severity-all --format report -o /tmp/ERC_audit.rpt \
  smartcoaster/smartcoaster.kicad_sch
# -> ERC messages: 0 Errors 0 Warnings

# 3) pcbnew 计数（2 层/47 footprint/576 track/62 via/29 net/229 pad）
LD_LIBRARY_PATH=... PYTHONPATH=... /usr/bin/python3 - <<'PY'
import pcbnew; b=pcbnew.LoadBoard('.../smartcoaster_2l.kicad_pcb') ...
PY

# 4) 机械自检（本审计复跑；verify_report.json 内容不变，git status 无该文件）
cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py   # 21/21 checks passed

# 5) 固件主机测试（本审计复跑）
bash tests/firmware/run_host_tests.sh
# -> CTest 2/2；host_core 41 checks 11/11；host_mock 198 checks 9/9；差分 16/16；pytest 16 passed

# 6) ngspice 前端（本审计复跑）
ngspice -b -o /tmp/hy.log electronics/simulation/hy928d_frontend.cir
# -> DC 3.960 mV 激励时 v(nout)=5.063736e-01 V（增益 128）

# 7) 工具版本核对
kicad-cli --version; ngspice -v; ccx -v; gmsh --version; blender --version; freecadcmd --version
```

### 7.2 未执行的检查（及原因）

| 未执行 | 原因 |
|---|---|
| `electronics/kicad/scripts/build.sh` 全量重建 | 任务书明确「会重新布线约 6 分钟，没必要」；DRC/ERC/Gerber 等以只读方式独立复核 |
| `idf.py build` 全量重建 | 审计期间其他 Agent 正在修改 `app_main.c`（并发写），构建会与并发改动竞争；改为核对现有 `smartcoaster.bin`（519,152 B）与 REPORT 记录 |
| Blender 重渲 / FEA 重解 | 产物（PNG/blend config/日志/JSON）已在库；重跑耗时且不改判定；FEA 结果 JSON 已读并核对与 README 数值一致 |
| 实物验证 | 无硬件（PCB/外壳/传感器未采购/打样），属用户侧 |
| LUMEN 全量机械自检 | LUMEN 已标「概念线不再推进」；方形与审计重点相关，已复跑 |

### 7.3 只读声明

- 本审计唯一写入：`docs/AUDIT_PIPELINE.md`（本文件）。
- 其余复核产物写到 `/tmp`（每次 bash 调用独立 tmpfs，故命令自带解析）；未修改源码、未改动配置、未 commit。
- `cad/verify_v01.py` 会固定重写 `mechanical/square_v1/build/verify_report.json`；本审计复跑后该文件内容与 HEAD 一致（`git status` 未显示它），等价于未改动。
- 审计期间工作区出现其他 Agent 的未提交修改（见 F12）；非本会话产生，本报告未触碰。

---

## 8. 附录：工具版本与关键计数核对

### 8.1 工具链（requirements.yaml ↔ 本机实测）

| 工具 | requirements.yaml | 本机实测 | 核对 |
|---|---|---|---|
| python | 3.10.12 | 3.10.12 | PASS |
| agentcad | 0.7.1 | 0.7.1（import 核对） | PASS |
| build123d | 0.10.0 | 0.10.0 | PASS |
| ocp | 7.8.1.1 | 7.8.1.1 | PASS |
| freecad | 1.0.2 | 1.0.2 Rev 39319 | PASS |
| calculix (ccx) | 2.22 | Version 2.22 | PASS |
| gmsh | 4.13.1 | 4.13.1 | PASS |
| kicad | 9.0.9 | 9.0.9（kicad-cli） | PASS |
| ngspice | 36 | ngspice-36 | PASS |
| esp-idf | 6.1 | v6.1 激活脚本存在；bin 519,152 B | PASS |
| pytest | 9.2.0 | 9.2.0 | PASS |
| wokwi-cli | 0.29.1 | 0.29.1 | PASS |
| blender | 4.5.3 | 4.5.3 LTS | PASS |
| qemu | 9.2.2 | qemu-system-xtensa esp_develop_9.2.2 存在 | PASS |
| freerouting | 未锁定 | 2.5.0（.tools/freerouting） | PARTIAL（未入 requirements） |
| xvfb / poppler | 未锁定 | 21.1.4 / pdftoppm 可用 | PARTIAL（未入 requirements） |

已安装位置：`/data/Documents/tools/{freecad,kicad,ngspice,blender,wokwi-cli,agentcad-venv,sim-venv}`，`~/.local/bin` 软链；ESP-IDF v6.1 在 `~/.espressif`，QEMU 9.2.2 在 `~/.espressif/tools/tools/qemu-xtensa/esp_develop_9.2.2_20260417/qemu/bin`。

### 8.2 关键计数（本审计核对）

| 项 | 值 | 来源 |
|---|---|---|
| git 提交 / 跟踪文件 | 31 / 404 | git log --oneline、git ls-files |
| 机械（方形 B）实体 / 自检 | 12 / 21-21 | verify_v01.py 复跑；37 对干涉 0；STEP 回读 12 solids |
| 机械（LUMEN）实体 / 自检 | 13 / 21-21 | mechanical/lumen/build/verify_report.json（概念线） |
| 原理图器件 / 网络 | 43 / 28 | NETLIST.md、BOM.csv、smartcoaster.net.xml |
| ERC | 0 Errors / 0 Warnings | 本审计复跑 /tmp/ERC_audit.rpt |
| PCB 铜层 / footprint / track / via / net | 2 / 47 / 576 / 62 / 29 | 本审计 pcbnew.LoadBoard 复核 |
| PCB pad | 229（211 SMD / 12 PTH / 6 NPTH） | 本审计 pcbnew 复核 |
| DRC | 0 violations / 0 unconnected | 本审计复跑 /tmp/DRC_audit.rpt |
| DFM（JLC 2L） | 5/5 PASS（线宽 0.2、钻孔 0.3、环宽 0.15、板边 0.3、层数 2） | electronics/kicad/build/DFM.md |
| Gerber 产物 | 8 层 + drl + drl_map + gbrjob + pos + zip | electronics/kicad/build/gerbers/ |
| 固件 bin | 519,152 B（0x7EBF0） | firmware/esp32/build/smartcoaster.bin（审计时存在） |
| 固件主机测试 | 41 checks/11 用例；198 checks/9 用例；差分 16/16（82 records）；pytest 16 | 本审计复跑 run_host_tests.sh |
| FEA 主结果 | 5 kg 中心 0.3435 mm；k≈142.8 N/mm；支反力 49.050 N=100%；+y 两颗 99.4%；非奇异热点 467.7 MPa | simulation/mechanical/hy928d/results.json 与 README 表 1 一致 |
| FEA 网格 | 304,892 节点 / 182,289 C3D10（h=0.28） | results_h028_c3d10.json、README 表 4 |
| SPICE 前端 | 3.956 mV → 0.5064 V（×128）；RC −3 dB 1655 Hz | hy928d_frontend.json；本审计复跑 DC 得 0.5063736 V |
| 渲染产物 | square_b 4 张 + LUMEN 4 张 + CMF 4 变体 + 包装 3 张 + 打印 2 张 | render/**/renders/、render/cmf/、render/print/ |

### 8.3 审计证据索引（主要路径）

- 阶段/流程文档：docs/01、docs/02、docs/05、docs/06、docs/HANDOFF.md、docs/VERIFY_REPORT.md、VALIDATION_PLAN.md
- 机械：mechanical/square_v1/{cad,build}、mechanical/hy928d/{src,build,notes.md}、mechanical/lumen/、config/mechanical_params.yaml
- 电路：electronics/{pinmap.md,kicad/BOM.csv,kicad/NETLIST.md,kicad/DECISIONS.md,kicad/build/*,simulation/*}
- 固件：firmware/{README.md,REPORT.md,esp32/main/*,model/*,wokwi/*}、tests/firmware/*、docs/08_Power_Sleep_Plan.md
- 仿真：simulation/mechanical/hy928d/*（results/JSON/图/脚本）、electronics/simulation/hy928d_frontend.{cir,json,log}
- 渲染/交付：render/{square_b,lumen,cmf,packaging,print}、submission/、packaging/
- 参考：ref/*.md + 原图

---

## 9. 审计结论（给 Lead 的决策建议）

1. **不要把当前状态对外表述为「docs/01 流水线已实现」**。准确表述是：*P0–P3 数字设计闭环 + S1 首轮机械 FEA 已落地；S2/S3 部分；S4/MCP 未开始；实物验证未开始。*
2. **优先补 §14 编排层（4–6 人日）**：它把已有的 21/21、0/0、41+198 checks、FEA JSON 串成「一条命令 + 统一报告」，是流水线叙事与实际工程价值的最大缺口。
3. **机械侧优先补对象 B/C FEA（5–8 人日）**：0.3435 mm 已用掉 0.5 mm 间隙的 69%，限位/偏载/旁路必须在装配级复核；否则「能当秤」仍只是趋势结论。
4. **电路侧 S2 收口（2–4 人日）**：电源与噪声是电池版最大风险，现只有估算；补电源 .tran、桥路蒙特卡洛、噪声预算，即可对齐 §13.3 四模块。
5. **文档一致性（1–2 人日）先做**：成本最低、对评审可信度影响最大；F1–F9 均为 HEAD 上可复现的「文档说 A、仓库是 B」。
6. **实物验证只能用户侧推进**：采购/打样/标定/7 天记录；AI 可先交下单包、标定脚本和结果回填模板，不能替代实测。

