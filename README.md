# Smart Coaster — AI 驱动的硬件研发流水线

> 一个真实产品（智能饮水杯垫）为载体，建立 **本地 AI Agent + 参数化设计 + 自动化验证 + 数字样机可视化** 的硬件研发流程。
>
> **当前（2026-11-04）**：G0 可行性验证完成——两版机械 21/21、HY928D FEA、ngspice 前端、KiCad 原理图/PCB 初稿、ESP-IDF 固件 + 主机测试、Blender 渲染都已跑通。**尚未开始实物手板、PCB 打样和 3D 打印。**

## 结果一览

| 层 | 状态 |
|---|---|
| 机械 | LUMEN 圆形 **21/21**；方形 B **21/21**（B 前脸：屏 26×7 @ x=−8、键 x=17） |
| FEA | HY928D 5 kg 中心 **0.3435 mm**（k≈142.8 N/mm）、支反力 100%、+y 两颗 99.4%、非奇异热点 468 MPa |
| 电路 | ngspice：3.956 mV → 0.506 V（×128）、RC 1.65 kHz；HX711 3.3 V 满量程 ±12.9 mV（30.7%） |
| PCB | **P1 板：4 层、0 short / 0 unconnected**；62 器件 / 40 网络、ERC 0；46 项丝印 warning 暂缓；单 RGB + 光导；S3 封装 PROVISIONAL |
| 固件 | ESP-IDF v6.1 build 通过（**530 KB**，含 NVS + NimBLE BLE GATT 0xFF00）；host 11/11 + mock 9/9；C↔Python 差分 16/16 |
| 渲染 | Blender 4.5.3 LTS：方形 B / LUMEN 各 4 张（外观/正视/PCB 细节/爆炸图） |
| 仿真工具 | ccx 2.22 + gmsh 4.13.1（FreeCAD 自带）、ngspice 36、QEMU 9.2.2、Blender 4.5.3 |

## 目录

```
SmartCoaster/
├── docs/                  01 流程 · 02 PRD · 05 bring-up · 06 固件架构 · design/（B 版交互）
├── ref/                   原始图纸/照片/PDF + 无损 Markdown 转录
├── config/                参数与验收阈值
├── mechanical/
│   ├── lumen/             圆形 LUMEN（Ø110×17，13 零件）
│   ├── square_v1/         方形 B（100×100×18，12 零件）
│   ├── hy928d/            HY928D 传感器 v2（PROVISIONAL 重建）
│   ├── legacy/ original_cad/
├── electronics/           pinmap/电源树 · kicad/（原理图/PCB/BOM）· simulation/（ngspice）
├── firmware/              model/（Python 参考）· esp32/（ESP-IDF）· wokwi/（可选）
├── simulation/            mechanical/hy928d/（FEA 网格/结果/云图）
├── tests/firmware/        C host 测试 + C↔Python 差分
├── render/                Blender 场景（square_b / lumen）
├── scripts/ build/
```

## 两条产品线（几何互相独立）

| | 圆形 LUMEN | 方形 B |
|---|---|---|
| 目录 | `mechanical/lumen/` | `mechanical/square_v1/` |
| 外形 | Ø110 × 17 | 100 × 100 × 18 |
| 零件 | 13 | 12 |
| 自检 | **21/21**，38 组干涉 0 | **21/21**，37 组干涉 0 |
| 特征 | 360° 光晕、前缘 0.49" 窗口、无实体键 | 0.91" 128×32（窗 26×7）、单键、窗口 halo |
| 体积/质量 | 63,796.9 mm³ / 129.8 g | 78,338.1 mm³ / 155.3 g |

> 14 mm 概念装不下 12 mm 高的 OLED 模组；普通版按 18 mm 方形，14 mm 留给“灯环 + App”的极简方向。

## 快速开始

```bash
# 机械
cd mechanical/square_v1 && .venv/bin/python cad/export_v01.py && .venv/bin/python cad/verify_v01.py
cd mechanical/lumen     && .venv/bin/python cad/export_v01.py && .venv/bin/python cad/verify_v01.py

# 传感器重建
cd mechanical/hy928d && /data/Documents/tools/agentcad-venv/bin/python src/hy928d_v2.py

# 电路
cd electronics/kicad/scripts && ./build.sh            # 原理图/PCB/BOM + ERC/DRC

# 固件
bash tests/firmware/run_host_tests.sh
PYTHONPATH= /data/Documents/tools/sim-venv/bin/pytest firmware/model -q

# 渲染
/data/Documents/tools/blender/blender -b --python render/square_b/build_scene.py
/data/Documents/tools/blender/blender -b --python render/lumen/build_scene.py
```

## 关键文档

- [流程 V1.1（含仿真工程 / MCP 编排）](docs/01_AI_Hardware_Engineering_Pipeline.md)
- [产品需求 PRD](docs/02_Smart_Coaster_PRD.md)
- [可行性验证与 bring-up 计划](docs/05_Bringup_and_Verification_Plan.md)
- [固件架构（HAL + Mock + 主机测试）](docs/06_Firmware_Architecture.md)
- [B 版交互设计](docs/design/2026-11-04-ui-interaction-b-design.md)
- [HY928D 图纸转录](ref/HY928D_5kg_称重传感器_图纸转录.md) / [HX711](ref/HX711_数据手册_海芯.md) / [Hydrate 参考](ref/Hydrate_AI_拆解与结构参考.md)
- [环境安装记录](docs/环境安装记录-agentcad-freecad.md) · [两版交付说明](docs/交付说明-两个版本.md)

## 路线

- [产品路线：先“能用”，再“红点级”](docs/07_Product_Roadmap.md)

## 待办

- P1 PCB 已 **0 short / 0 unconnected**（4 层，单 RGB + 光导）；下一步：S3-MINI-1 官方 footprint 复核、丝印清理、Gerber/打样。
- 手板采购：ESP32-S3-DevKitC-1、0.91" 128×32 OLED、HY928D、HX711 模块、砝码；按 `docs/05` 矩阵测。
- 固件：BLE GATT、NVS/跨日、低功耗休眠、OLED 中文。
- 渲染：KiCad 3D（待布线/3D 模型）、3D 打印参考图（拆分/方向/支撑）。
