# Smart Coaster — AI 驱动的硬件研发流水线

> 一个真实产品（智能饮水杯垫）为载体，建立 **本地 AI Agent + 参数化设计 + 自动化验证 + 数字样机可视化** 的硬件研发流程。
>
> **当前（2026-11-04，去灯 / 2 层收口轮）**：
> - **产品定义变更（以此为准）**：LED 与所有发光件全部去掉；PCB 最多 2 层。前脸只有 **26×7 屏窗 + 按键**，唯一缝隙是**顶板-底座 0.5 mm 浮动缝**（秤的行程缝）；无灯、无灯缝。
> - **P1 设计闭环**：方形 B 机械 **12 件 21/21**（37 组干涉 0）；原理图 **43 器件 / 28 网络**、ERC 0 error；**2 层 PCB 已布通：`kicad-cli pcb drc --severity-all` 0 violation / 0 unconnected**（576 track + 62 via，证据 `electronics/kicad/build/DRC_2l.rpt`；47 footprint = 43 器件 + 4 安装孔）；固件 ESP-IDF v6.1，灯效代码已删（测试计数见 `docs/HANDOFF.md`）。
> - **P2 可制造**：2 层 Gerber/钻孔/坐标/zip（`build/gerbers/`）、JLC 2 层 DFM **全 PASS**（`build/DFM.md`）、BOM（43 器件 / 24 行）；拼板建议 2×2 V-groove。
> - **P3 红点水平**：CMF 4 变体、120×120×36 包装、产品叙事、**Red Dot 2026 提交包**（`submission/`），渲染已全部按“无灯”重出。
> - **仍需用户动手**：采购 ESP32-S3-DevKitC-1 / 0.91" OLED / HY928D / HX711 模块 / 砝码，按 `docs/09` 装配并按 `tests/handboard/BRINGUP_RECORD.md` 标定；PCB 打样与 3D 打印下单。

## 结果一览

| 层 | 状态 |
|---|---|
| 提交包 | `submission/`：4 张主图 + A3 故事页（Red Dot 2026），无灯版 |
| 包装 | 120×120×36 天地盖 + 纸浆内衬 + 腰封；3D + 3 张渲染 |
| CMF | 4 个配色变体（Lumen Violet / Moss / Sand / Graphite）+ `render/cmf/CMF_variants.png` + `docs/10_CMF_and_Packaging.md` |
| 机械 | LUMEN 圆形（概念线，**21/21**，不再推进）；方形 B **12 件 21/21**（前脸 26×7 屏窗 + 按键，0.5 mm 浮动缝） |
| FEA | HY928D 5 kg 中心 **0.3435 mm**（k≈142.8 N/mm）、支反力 100%、+y 两颗 99.4%、非奇异热点 468 MPa |
| 电路 | ngspice：3.956 mV → 0.506 V（×128）、RC 1.65 kHz；HX711 3.3 V 满量程 ±12.9 mV（30.7%） |
| PCB | 主方案 **2 层已布通**：**43 器件 / 28 网络**（删 LED 13 + TP 6）；47 footprint、576 track + 62 via；**0 DRC / 0 unconnected**（`build/DRC_2l.rpt`）；官方 S3-MINI-1 封装（U1 与机械对齐） |
| 固件 | ESP-IDF v6.1 build 通过（**519,152 B / 507 KiB**，含 NVS + NimBLE GATT 0xFF00 + 时间/跨日 + 中文 UI；删 halo 后 −13.8 KB）；host 11/11 + mock 9/9 + C↔Python 差分 16/16；PM light sleep + BLE modem sleep（2–3 mA 估算） |
| 渲染 | Blender 4.5.3 LTS：方形 B 4 张（外观/正视/PCB 细节/爆炸图）+ CMF 4 变体 + 包装 3 张；无灯、无发光件 |
| 仿真工具 | ccx 2.22 + gmsh 4.13.1（FreeCAD 自带）、ngspice 36、QEMU 9.2.2、Blender 4.5.3 |

## 目录

```
SmartCoaster/
├── docs/                  01 流程 · 02 PRD · 05 bring-up · 06 固件架构 · design/（B 版交互）
├── ref/                   原始图纸/照片/PDF + 无损 Markdown 转录
├── config/                参数与验收阈值
├── mechanical/
│   ├── lumen/             圆形 LUMEN（Ø110×17，概念线，13 零件）
│   ├── square_v1/         方形 B（100×100×18，12 零件，无灯）
│   ├── hy928d/            HY928D 传感器 v2（PROVISIONAL 重建）
│   ├── legacy/ original_cad/
├── electronics/           pinmap/电源树 · kicad/（原理图/PCB/BOM）· simulation/（ngspice）
├── firmware/              model/（Python 参考）· esp32/（ESP-IDF）· wokwi/（可选）
├── simulation/            mechanical/hy928d/（FEA 网格/结果/云图）
├── tests/firmware/        C host 测试 + C↔Python 差分
├── tests/handboard/       手板 bring-up 记录表
├── submission/            Red Dot 2026 提交包（4 图 + A3 故事页）
├── render/                Blender 场景（square_b / lumen / cmf / packaging）
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

## 路线

- [产品路线：先“能用”，再“红点级”](docs/07_Product_Roadmap.md)

## 待办

- **PCB 2 层已收口**：**0 DRC / 0 unconnected**（`build/DRC_2l.rpt`）+ 2 层 Gerber/钻孔/坐标/zip（`build/gerbers/`）+ JLC 2 层 DFM 全 PASS（`build/DFM.md`）+ 布线预览 `build/pcb_2l.png`。
- 手板采购：ESP32-S3-DevKitC-1、0.91" 128×32 OLED、HY928D、HX711 模块、砝码；按 `docs/05` 矩阵测。
- 固件：BLE GATT、NVS/跨日、低功耗休眠、OLED 中文（灯效代码已删）。
- 渲染：KiCad 3D（待 3D 模型）、3D 打印参考图（拆分/方向/支撑）。
