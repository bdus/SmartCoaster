# Smart Coaster — AI 驱动的硬件研发流水线

> 一个真实产品（智能饮水杯垫）为载体，建立 **本地 AI Agent + MCP + 参数化设计 + 自动化验证** 的硬件研发流程。
> 当前：机械结构与几何验证完成；HY928D 传感器 v2 待人工检视；FEA 工具（ccx 2.22 + gmsh 4.13.1）可用；KiCad 9.0.9 / ngspice 36 / pytest 9.2.0 / Wokwi CLI 0.29.1 已就绪。

## 目录

```
SmartCoaster/
├── docs/                  流程、PRD、安装记录、任务书
├── ref/                   原始资料 + 无损 Markdown 转录（HY928D/HX711/Hydrate）
├── config/                参数与验收阈值的集中入口
├── mechanical/            机械设计（每个版本一个自包含 agentcad 项目）
│   ├── lumen/             圆形 LUMEN（Ø110×17，13 零件，21/21 自检）
│   ├── square_v1/         方形 V1（100×100×18，12 零件，18/18 自检）
│   ├── hy928d/            HY928D 传感器 v2（按图纸+照片重建，待检视）
│   ├── legacy/            旧版脚本的可运行副本（去 NBSP）
│   └── original_cad/      原始 M1.2 脚本（未改动）
├── electronics/           电路设计（KiCad，待建）
├── firmware/              固件（ESP-IDF，待建）
├── simulation/            机械 FEA / 电路 SPICE / 系统仿真
├── tests/                 自动化验收
├── scripts/               跨项目脚本
├── build/                 跨项目汇总产物
└── .tools/                共享工具（Xvfb 等）
```

## 两个机械版本（互相独立）

| | 圆形 LUMEN | 方形 V1 |
|---|---|---|
| 目录 | `mechanical/lumen/` | `mechanical/square_v1/` |
| 外形 | Ø110 × 17 | 100 × 100 × 18 |
| 零件 | 13 | 12 |
| 自检 | 21/21，38 组干涉 0 | 18/18，37 组干涉 0 |
| 特征 | 360° 光晕、无实体键 | 前缘 OLED + Ø8.2 按键 |

## 快速开始

```bash
cd mechanical/lumen && .venv/bin/python cad/export_v01.py && .venv/bin/python cad/verify_v01.py
cd mechanical/square_v1 && .venv/bin/python cad/export_v01.py && .venv/bin/python cad/verify_v01.py
cd mechanical/hy928d && /data/Documents/tools/agentcad-venv/bin/python src/hy928d_v2.py
```

## 关键文档

- [流程 V1.1（含仿真工程 / MCP 编排）](docs/01_AI_Hardware_Engineering_Pipeline.md)
- [产品需求 PRD](docs/02_Smart_Coaster_PRD.md)
- [环境安装记录](docs/环境安装记录-agentcad-freecad.md)
- [两版交付说明](docs/交付说明-两个版本.md)
- [HY928D 图纸转录](ref/HY928D_5kg_称重传感器_图纸转录.md) / [HX711](ref/HX711_数据手册_海芯.md) / [Hydrate 参考](ref/Hydrate_AI_拆解与结构参考.md)

## 当前状态

- ✅ agentcad 0.7.1 + build123d 0.10.0 + FreeCAD 1.0.2，全局可用
- ✅ 圆形 / 方形两版总装 + 几何/行程/干涉自检
- 🟡 HY928D v2：按新图纸/照片重建，**等人工检视**后再做应力仿真
- ✅ CalculiX 2.22 + Gmsh 4.13.1（FreeCAD 1.0.2 自带，`~/.local/bin`）
- ✅ KiCad 9.0.9（含 kicad-cli，ERC/DRC 0 violations）、ngspice 36、pytest 9.2.0、Wokwi CLI 0.29.1（仅本地 lint）
- ⚠️ Wokwi 云仿真需 token 且会上传文件；默认不使用，除非你明确授权
- ⬜ 形态 C：14 mm 超薄 + 前缘 OLED + 双/三按键的方形重构（待 HY928D 冻结）
