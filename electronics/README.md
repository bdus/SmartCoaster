# electronics/

电路设计（KiCad 9.0.9）。**当前状态（2026-11-04）：43 器件 / 28 网络，ERC 0 error/0 warning；2 层 PCB 已布通，`kicad-cli pcb drc --severity-all` 0 DRC / 0 unconnected；Gerber/钻孔/坐标/DFM 已出。**

- `kicad/` KiCad 工程（原理图、网表、2 层 PCB、BOM、制造文件）
- `kicad/scripts/` 唯一来源：`design.py`（原理图）、`gen_pcb.py`（未布线 PCB）、`route_2l.sh`（Freerouting 布线 + DRC）
- `simulation/` ngspice 网表与结果：`hy928d_frontend.cir` + `.json`（桥路 + HX711 行为前端，DC/AC；电源/噪声/蒙特卡洛仍是 GAP）
- `pinmap.md` 引脚与电源树（无 LED/光导）

关键证据：`kicad/build/DRC_2l.rpt`（0/0）、`kicad/build/ERC.rpt`（0/0）、`kicad/build/DFM.md`（JLC 2 层全 PASS）、`kicad/build/gerbers/`。

依据：`docs/02_Smart_Coaster_PRD.md` §5、`docs/HANDOFF.md`、`ref/HX711_数据手册_海芯.md` §14。
