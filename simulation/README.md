# simulation/

| 子目录 | 内容 | 工具 | 状态 |
|---|---|---|---|
| `mechanical/` | 应力/应变/位移/接触 | CalculiX + Gmsh + FreeCAD FEM | 工具安装中 |
| `electronics/` | 桥路/HX711/电源/噪声 | KiCad + ngspice | 待建 |
| `system/` | 参数→仿真→验收→报告 | Python + pytest | 待建 |

规则：结果落 JSON/CSV + 云图；每个用例写清假设、边界、材料、版本；不确定参数做参数扫描。
详细设计见 `docs/01_AI_Hardware_Engineering_Pipeline.md` §13–14。
