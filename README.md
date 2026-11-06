# Smart Coaster — AI 驱动的硬件研发流水线

> 一个真实产品（智能饮水杯垫）为载体，建立 **本地 AI Agent + 参数化设计 + 自动化验证 + 数字样机可视化** 的硬件研发流程。
>
> **当前（2026-11-04，去灯 / 2 层收口轮）**：
> - **产品定义变更（以此为准）**：LED 与所有发光件全部去掉；PCB 最多 2 层。前脸只有 **26×7 屏窗 + 按键**，唯一缝隙是**顶板-底座 0.5 mm 浮动缝**（秤的行程缝）；无灯、无灯缝。
> - **P1 设计闭环**：方形 B 机械 **12 件 21/21**（37 组干涉 0）；原理图 **43 器件 / 28 网络**、ERC 0 error；**2 层 PCB 已布通：`kicad-cli pcb drc --severity-all` 0 violation / 0 unconnected**（576 track + 62 via，证据 `electronics/kicad/build/DRC_2l.rpt`；47 footprint = 43 器件 + 4 安装孔）；固件 ESP-IDF v6.1，灯效代码已删（测试计数见 `docs/HANDOFF.md`）。
> - **P2 可制造**：2 层 Gerber/钻孔/坐标/zip（`build/gerbers/`）、JLC 2 层 DFM **全 PASS**（`build/DFM.md`）、BOM（43 器件 / 24 行）；拼板建议 2×2 V-groove。
> - **P3 红点水平**：CMF 4 变体、120×120×36 包装、产品叙事、**Red Dot 2026 提交包**（`submission/`），渲染已全部按“无灯”重出。
> - **仍需用户动手**：采购 ESP32-S3-DevKitC-1 / 0.91" OLED / HY928D / HX711 模块 / 砝码，按 `docs/09` 装配并按 `tests/handboard/BRINGUP_RECORD.md` 标定；PCB 打样与 3D 打印下单。
> - **下一阶段（2026-11-04 用户新指示）**：冻结结构与功能，只做**外观变体**。功能确认：**方形 square_v1 正常（21/21，与当前电子/固件一致）**；**圆形 LUMEN 为旧概念（光导/LED/0.49" 屏/无按键）→ 不能直接当外观变体**；当前方形 PCB 对角线 131.8 mm > Ø110，**真圆需重做 PCB（功能变更）**。计划见 [`docs/13_Appearance_Variants_Plan.md`](docs/13_Appearance_Variants_Plan.md)，验收经验见 [`docs/01` §16](docs/01_AI_Hardware_Engineering_Pipeline.md)。
> - **报告与审计（2026-11-04）**：[技术报告](docs/REPORT_技术报告.md) · [成果展示](docs/REPORT_成果展示.md) · 逐条审计 [PRD](docs/AUDIT_PRD.md) / [流水线](docs/AUDIT_PIPELINE.md) / [环境](docs/AUDIT_ENV.md) · [独立验收](docs/VERIFY_REPORT.md) · **电路** [S2 仿真](docs/S2_CIRCUIT_SIM.md) / [电气评审](docs/REVIEW_ELECTRICAL.md) / [电气验证矩阵](docs/VERIFICATION_ELECTRICAL.md)
> - **EasyEDA 第二实现（2026-11-05）**：工具装到 `/data/Documents/tools/`（easyeda-agent **v1.16.0** / LCEDA Pro **4.1.97** / 官方 eprj3 skill **2.2.1**）；新建 [`electronics/easyeda/`](electronics/easyeda/README.md)，从冻结 KiCad 设计重建 `.eprj3`：**47 器件 / 7 块 / 28 网络 / 168 连接脚与 KiCad 逐脚一致**、5 门禁 + netcheck 全绿；**2 层铜（576 track + 62 via）从已验证 KiCad 布线 1:1 移植**，独立 GEOS 检查 C1–C5 全 PASS。**客户端 live DRC/铺铜/Gerber 仍被登录/激活墙阻塞**（`pro.lceda.cn` 对本机 418）；技术栈调研见 [`docs/EDA_TOOLCHAIN_SURVEY.md`](docs/EDA_TOOLCHAIN_SURVEY.md)。

## 结果一览

| 层 | 状态 |
|---|---|
| 提交包 | `submission/`：4 张主图 + A3 故事页（Red Dot 2026），无灯版 |
| 包装 | 120×120×36 天地盖 + 纸浆内衬 + 腰封；3D + 3 张渲染 |
| CMF | 4 个配色变体（Lumen Violet / Moss / Sand / Graphite）+ `render/cmf/CMF_variants.png` + `docs/10_CMF_and_Packaging.md` |
| 机械 | **方形 B 12 件 21/21**（当前功能基线，前脸 26×7 屏窗 + 按键，0.5 mm 浮动缝）；LUMEN 圆形 21/21 但为**旧概念**（含已删光导/LED、0.49" 屏、无按键），只作外观语言参考 |
| FEA | HY928D 5 kg 中心 **0.3435 mm**（k≈142.8 N/mm）、支反力 100%、+y 两颗 99.4%、非奇异热点 468 MPa |
| 电路 | ngspice：3.956 mV → 0.506 V（×128）；HX711 3.3 V 满量程 ±12.9 mV（30.7%）；**S2 四模块×六类分析 28 结果（21 PASS / 7 个真实发现）** |
| PCB | 主方案 **2 层已布通**：**43 器件 / 28 网络**（删 LED 13 + TP 6）；47 footprint、576 track + 62 via；**0 DRC / 0 unconnected**（`build/DRC_2l.rpt`）；官方 S3-MINI-1 封装（U1 与机械对齐） |
| EasyEDA 第二实现 | [`electronics/easyeda/`](electronics/easyeda/README.md)：`.eprj3`（原理图 + 已布线 2 层 PCB）47 器件 / 28 网络 / 168 连接脚与 KiCad 对账一致，5 门禁 + netcheck 全绿；铜 576 track + 62 via 由已验证 KiCad 布线移植，独立 C1–C5 几何检查全 PASS；**无铺铜 / 无客户端保存回读 / 无 Gerber**，client live 待登录；工具与限制见 [`/data/Documents/tools/EASYEDA_INSTALL_NOTES.md`](../../tools/EASYEDA_INSTALL_NOTES.md) |
| 固件 | ESP-IDF v6.1 build 通过（**519,184 B / 507 KiB**，含 NVS + NimBLE GATT 0xFF00 + 时间/跨日 + 中文 UI；删 halo 后 −13.8 KB）；host 11/11 + mock 9/9 + C↔Python 差分 16/16；PM light sleep + BLE modem sleep；**连续采样功耗预算 5.02 mA → 约 4.2 天**（S2 仿真），7 天需模拟前端占空（待固件） |
| 渲染 | Blender 4.5.3 LTS：方形 B 4 张（外观/正视/PCB 细节/爆炸图）+ CMF 4 变体 + 包装 3 张；无灯、无发光件 |
| 仿真工具 | ccx 2.22 + gmsh 4.13.1（FreeCAD 自带）、ngspice 36、QEMU 9.2.2、Blender 4.5.3 |
| IP 印花多材料 | `appearance/`：Kromacut 4.2.0 印花→多材料几何、外壳开槽、Blender 数字样机、Bambu 床面排版 3MF；**18 个可打印 STL（打印姿态：印花正面贴床/第一层、按钮躺平、无需支撑）**，130/130 只读验收 |
| 可复用 Agent 系统 | `agent-system/`：8 角色 / 28 阶段 / 7 组 145 条门禁 / 9 模板 / 脚手架 + 自校验；`check_system.py` PASS，`new_project.py` 15/15 |

## 目录

```
SmartCoaster/
├── docs/                  01 流程（含 §16 验收经验）· 02 PRD · 05–13 设计文档 · HANDOFF · AUDIT_* · VERIFY · REPORT_*
├── ref/                   原始图纸/照片/PDF + 无损 Markdown 转录
├── config/                参数与验收阈值
├── mechanical/
│   ├── lumen/             圆形 LUMEN（Ø110×17，概念线，13 零件）
│   ├── square_v1/         方形 B（100×100×18，12 零件，无灯）
│   ├── hy928d/            HY928D 传感器 v2（PROVISIONAL 重建）
│   ├── legacy/ original_cad/
├── electronics/           pinmap/电源树 · kicad/（原理图/PCB/BOM）· easyeda/（EasyEDA 第二实现）· simulation/（ngspice）
├── firmware/              model/（Python 参考）· esp32/（ESP-IDF）· wokwi/（可选）
├── simulation/            mechanical/hy928d/（FEA 网格/结果/云图）
├── tests/firmware/        C host 测试 + C↔Python 差分
├── tests/handboard/       手板 bring-up 记录表
├── submission/            Red Dot 2026 提交包（4 图 + A3 故事页）
├── render/                Blender 场景（square_b / lumen / cmf / packaging）
│   └── print/             3D 打印交付：stl/（18 个打印姿态 STL）+ appearance/（3MF/参考图/manifest）
├── appearance/            IP 印花多材料线：方法/规范/素材/印花几何/开槽/渲染/打印交付
├── agent-system/          可复用 Agent 系统：SYSTEM.yaml + roles/workflows/gates/templates/scripts
├── packaging/             包装参数化模型 + STEP/STL
├── scripts/ build/
```

## 两条产品线（几何互相独立）

| | 圆形 LUMEN | 方形 B |
|---|---|---|
| 目录 | `mechanical/lumen/` | `mechanical/square_v1/` |
| 外形 | Ø110 × 17 | 100 × 100 × 18 |
| 零件 | 13（概念线，不再推进） | **12**（13→12，删发光件） |
| 自检 | **21/21**，38 组干涉 0 | **21/21**，37 组干涉 0 |
| 特征 | 圆形概念（发光方案已废弃） | 0.91" 128×32（窗 26×7）、单键；前脸只有屏窗 + 按键，0.5 mm 浮动缝 |
| 体积/质量 | 63,796.9 mm³ / 129.8 g | 78,338.1 mm³ / 155.3 g |

> 14 mm 概念装不下 12 mm 高的 OLED 模组；普通版按 18 mm 方形，14 mm 留给极简方向。

## 快速开始

```bash
# 机械
cd mechanical/square_v1 && .venv/bin/python cad/export_v01.py && .venv/bin/python cad/verify_v01.py
cd mechanical/lumen     && .venv/bin/python cad/export_v01.py && .venv/bin/python cad/verify_v01.py

# 传感器重建
cd mechanical/hy928d && /data/Documents/tools/agentcad-venv/bin/python src/hy928d_v2.py

# 电路
cd electronics/kicad/scripts && ./build.sh            # 原理图/布线/DRC/BOM/Gerber/DFM 全流程

# 固件
bash tests/firmware/run_host_tests.sh
PYTHONPATH= /data/Documents/tools/sim-venv/bin/pytest firmware/model -q

# 渲染（无灯版）
/data/Documents/tools/blender/blender -b --python render/square_b/build_scene.py
/data/Documents/tools/blender/blender -b --python render/packaging/build_scene.py
python3 render/cmf/make_variants.py                   # 4 配色 + 拼图
python3 submission/make_story.py                      # A3 故事页（先放好 01–04 图）
```

## 关键文档

- [流程 V1.1（含仿真工程 / MCP 编排）](docs/01_AI_Hardware_Engineering_Pipeline.md)
- [产品需求 PRD](docs/02_Smart_Coaster_PRD.md)
- [可行性验证与 bring-up 计划](docs/05_Bringup_and_Verification_Plan.md)
- [固件架构（HAL + Mock + 主机测试）](docs/06_Firmware_Architecture.md)
- [B 版交互设计](docs/design/2026-11-04-ui-interaction-b-design.md)
- [CMF 与包装](docs/10_CMF_and_Packaging.md) · [产品叙事](docs/11_Product_Narrative.md)
- [HY928D 图纸转录](ref/HY928D_5kg_称重传感器_图纸转录.md) / [HX711](ref/HX711_数据手册_海芯.md) / [Hydrate 参考](ref/Hydrate_AI_拆解与结构参考.md)
- [环境安装记录](docs/环境安装记录-agentcad-freecad.md) · [两版交付说明](docs/交付说明-两个版本.md)
- [IP 印花 → 多材料一体打印（方法/工程要求）](appearance/README.md) · [3D 打印交付规范](appearance/PRINT_DELIVERY_SPEC.md)
- **一键编译**：[输入清单](appearance/INPUTS.md) · [唯一配置](appearance/config/appearance_project.yaml) · [`bash appearance/compile.sh`](appearance/compile.sh) · [Agent 提示词](appearance/AGENT_PROMPT.md)
- [可复用 Agent 系统（下一项目起点）](agent-system/README.md) · [本项目证据映射](agent-system/MAPPING_SMARTCoaster.md)

## 路线

- [产品路线：先“能用”，再“红点级”](docs/07_Product_Roadmap.md)

## 待办

- **PCB 2 层已收口**：**0 DRC / 0 unconnected**（`build/DRC_2l.rpt`）+ 2 层 Gerber/钻孔/坐标/zip（`build/gerbers/`）+ JLC 2 层 DFM 全 PASS（`build/DFM.md`）+ 布线预览 `build/pcb_2l.png`。
- 手板采购：ESP32-S3-DevKitC-1、0.91" 128×32 OLED、HY928D、HX711 模块、砝码；按 `docs/05` 矩阵测。
- 固件：BLE GATT、NVS/跨日、低功耗休眠、OLED 中文（灯效代码已删）。
- 渲染：KiCad 3D（待 3D 模型）、3D 打印参考图（拆分/方向/支撑）。
