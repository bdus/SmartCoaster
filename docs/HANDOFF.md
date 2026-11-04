# HANDOFF — SmartCoaster（2026-11-04，交接给下一个 AI）

> 先读：`AGENTS.md` → `docs/01_AI_Hardware_Engineering_Pipeline.md` → `docs/07_Product_Roadmap.md` → 本文件。

## 0. 执行摘要（先看这里）

- 目标：智能杯垫；P1 设计（机械/PCB/固件）、P2 可制造、P3 Red Dot 视觉/包装/叙事都已做过，但**用户改了需求**：光导和 LED 全部不要，PCB 最多 2 层并清到 0/0。
- 已做：删 LED（D1、Q1–Q3、R13–R21）与测试点 TP1–TP6；原理图 **43 器件 / 28 网络**，ERC 0 error；2 层板 47 footprint、0 track。
- 卡点：Freerouting 因 DSN 里 159 个 pin 全是 `[T]`（通孔）、没有 `[S]`，报 `no SMD pins` / `0 unrouted nets`，返回空 SES。**先修 DSN pad 类型，再布线。**
- 下一步：修 pad 类型 → Freerouting → 导入 SES → DRC 到 **0 DRC / 0 unconnected** → Gerber/DFM；然后清掉 LED/光导在机械/固件/P3 里的残留。
- 手板（采购/装配/标定）与打样/3D 打印是用户侧，不能代替。
- 本文件是唯一交接入口；详细状态、文件、命令见下文。

## 1. 背景与用户最新决定

- 产品：方形智能杯垫（100×100×18，称重喝水、OLED、BLE、Red Dot 级外观）。
- 前 20 轮已完成 P1 设计、P2 DFM、P3 CMF/包装/叙事/提交包；目标曾因“手板需用户采购/装配”被标记 blocked。
- **用户最新决定（以此为准，覆盖旧文档）**：
  1. **光导全部去掉**：窗周 halo、前缘灯线、底部灯线、Y 分光、顶板-底座缝隙光环——都不要；
  2. **LED 也去掉**（D1、Q1–Q3、R13–R21 已从设计删除）；
  3. **PCB 最多 2 层**，必须清到 **0 DRC / 0 unconnected**；
  4. 前脸只留 26×7 屏窗 + 按键；顶板与底座那 0.5 mm 是秤的浮动缝，不放光。
- 用户希望“在前端持续看到过程”，所以尽量每步贴出命令结果/图。

## 2. 仓库与工具链

- 工作区：`/data/Documents/projects/SmartCoaster`
- 机械：agentcad 0.7.1 + build123d 0.10.0（`mechanical/square_v1/.venv`）
- PCB：KiCad 9.0.9（`/data/Documents/tools/kicad`，`~/.local/bin/kicad-cli`）
- 布线：Freerouting 2.5.0（`.tools/freerouting/...`，Java 25）
- 固件：ESP-IDF v6.1（`source /home/pi/.espressif/tools/activate_idf_v6.1.sh`）
- 仿真/渲染：FreeCAD 自带 ccx 2.22 + gmsh 4.13.1、ngspice 36、Blender 4.5.3
- KiCad Python 环境：
  ```bash
  export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
  export XDG_CONFIG_HOME=$PWD/.tools/kicad-config
  export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
  ```

## 3. 当前已验证状态

| 项 | 状态 |
|---|---|
| 原理图 | **43 器件 / 28 网络**（删 LED 13 个 + TP 6 个后）；ERC **0 error / 1 warning**（U1 的 NC 脚） |
| 机械 | 13 件、`verify_v01.py` **21/21**（光导件仍在 CAD 里，待删；壳体前脸浅槽/过孔也还在） |
| 固件 | 531 KB；host 11/11 + mock 9/9；C↔Python 差分 **16/16**（halo 代码仍在，待 disabled） |
| 2 层 PCB | 47 footprint、0 track；**未布通** |
| 4 层 PCB | 53 footprint（TP 时代的旧板）、0 track |
| 2 层（删 TP 前） | 8 unconnected + 5 DRC，全部指向 **TP6** |
| 4 层（删 LED 前） | 曾 **0 DRC / 0 unconnected**（旧设计，带 LED、带铺铜） |
| 4 层（删 LED 后重跑） | **3 unrouted + 14 violations**，未收口 |

**当前 2 层卡点**：TP 已删，但 Freerouting 报

```
Fanout stage ... skipped because the board has no SMD pins
Auto-routing stage started ... with 0 unrouted items
```

返回 303 B 空 SES。DSN 里：

- `grep -c "(pin "` = 159；
- pad 类型：162 个 `Rect[T]Pad`（通孔）+ 4 个 `[A]`，**0 个 `[S]`（SMD）**；
- 而 PCB 实际是 **211 SMD / 12 PTH / 6 NPTH**。

→ 根因在 `gen_pcb.py` 生成 footprint 的 pad 属性，或 `ExportSpecctraDSN` 读取的 pad 类型。修好后 DSN 应出现 `[S]`，路由器才会真正布 149 个连接。

## 4. 当前工作区状态

- git：最后提交 `0db47df`（4 层 GND 铺铜）；**LED/TP 删除、4L/2L 重生成、文档均在未提交的工作区**。
- PCB 文件：
  - `smartcoaster.kicad_pcb`：2 层、47 footprint、0 track（未布线）；
  - `smartcoaster_2l.kicad_pcb`：2 层、47 footprint、0 track（空 SES，未布）；
  - `smartcoaster_4l.kicad_pcb`：4 层、53 footprint（TP 时代的旧板）、0 track。
- DSN：`electronics/kicad/build/smartcoaster_2l.dsn`（28 net、159 pin，全 `[T]`）。
- 调试报告：`build/DRC_2l2.rpt`、`build/pcb_2l.png`、`build/DFM.md`、`build/DRC_pour3.rpt`。

## 5. 未完成任务（按优先级）

1. **修 DSN 的 pad 类型 → 2 层 0/0 → 新 Gerber/DFM（当前最高优先级）**
   - 先定位：`gen_pcb.py` 的 `load_footprint()` 把库 footprint 的 pad 节点搬过来，`board_footprint()` 里给 pad 加 net/角度；检查 pad 的 `(pad "1" smd ...)` 是否保留了 `smd`，以及 `(layers ...)` 是否含 `F.Paste`/`F.Mask`。
   - 验证点：重新导出 DSN 后 `grep -o "Rect\[.\]Pad" build/smartcoaster_2l.dsn | sort | uniq -c` 必须出现 `[S]`；同时 Freerouting 不再报 `no SMD pins`。
   - 布线：Freerouting → 导入 SES → `kicad-cli pcb drc`，目标 **0 DRC / 0 unconnected**；把 DRC 报告贴出来作为证据。
   - 收口：`kicad-cli pcb export gerbers/drill/pos` + `scripts/dfm_check.py`，更新 `build/DFM.md`。
   - 若 2 层确实布不通：明确写出是哪几个 net，再用 4 层 0/0 兜底；**不要用空 SES 当结果**。
2. **删 LED/光导的连锁清理**
   - 机械：删 `make_light_guide`、壳体前脸浅槽/过孔，复跑 `cad/verify_v01.py`（21/21）并重渲染；
   - 固件：`firmware/esp32/main/board.h` 的 HALO_*、`app_main.c` 的 `render_halo`/`halo_*`、`halo.c` 标 disabled 或删；`idf.py build` + host 测试；
   - P3：`render/square_b`、`render/cmf`、`submission/` 里的光导图要更新（旧图仍带光导）；
   - BOM/装配图/README 同步（器件从 62→43）。
3. **提交当前工作区**（删 LED/TP 的改动、2 层板、文档）。
4. **手板**（用户侧）：采购 ESP32-S3-DevKitC-1、0.91" OLED、HY928D、HX711 模块、砝码；按 `docs/09_Assembly.md` 装配、`tests/handboard/BRINGUP_RECORD.md` 标定；PCB 打样 + 3D 打印。

## 6. 关键文件

| 文件 | 作用 |
|---|---|
| `electronics/kicad/scripts/design.py` | 原理图/网表唯一来源（43 器件/28 网络） |
| `electronics/kicad/scripts/gen_pcb.py` | 生成 PCB（placement + footprint） |
| `electronics/kicad/scripts/build.sh` | 原理图→ERC→网表→PCB→BOM |
| `electronics/kicad/scripts/check_pcb.py` | placement 检查 |
| `electronics/kicad/scripts/dfm_check.py` | JLC 4 层 DFM |
| `electronics/kicad/smartcoaster/smartcoaster_2l.kicad_pcb` | 当前 2 层板 |
| `mechanical/square_v1/cad/square_model.py` | 机械唯一来源（13 件，光导待删） |
| `mechanical/square_v1/cad/verify_v01.py` | 21 项自检 |
| `firmware/esp32/` | ESP-IDF 固件 |
| `tests/firmware/run_host_tests.sh` | host + 差分测试 |
| `tests/handboard/BRINGUP_RECORD.md` | 手板记录表 |
| `docs/07_Product_Roadmap.md` | 阶段与判定 |
| `submission/` | Red Dot 提交包（光导图待更新） |

## 7. 常用命令

```bash
# 原理图/PCB 重建 + 检查
cd electronics/kicad/scripts && PATH=$HOME/.local/bin:$PATH ./build.sh
/data/Documents/tools/sim-venv/bin/python check_pcb.py

# 2 层 DSN 导出（注意：当前导出 pad 类型是 [T]，需先修）
export LD_LIBRARY_PATH=... XDG_CONFIG_HOME=$PWD/.tools/kicad-config
export PYTHONPATH=.../python3/dist-packages
python3 - <<'EOF'
import pcbnew
b=pcbnew.LoadBoard(".../smartcoaster_2l.kicad_pcb")
pcbnew.ExportSpecctraDSN(b, ".../build/smartcoaster_2l.dsn")
EOF

# Freerouting
export XDG_CONFIG_HOME=$PWD/.tools/fr-home/config XDG_STATE_HOME=$PWD/.tools/fr-home/state \
       XDG_CACHE_HOME=$PWD/.tools/fr-home/cache
export JAVA_TOOL_OPTIONS="-Dgui.enabled=false -Djava.awt.headless=true"
DISPLAY=:99 .tools/freerouting/freerouting-2.5.0-linux-x64/bin/freerouting \
  -de electronics/kicad/build/smartcoaster_2l.dsn \
  -do electronics/kicad/build/smartcoaster_2l.ses -mt 8 -mp 300

# DRC
~/.local/bin/kicad-cli pcb drc --severity-all -o build/DRC_2l.rpt smartcoaster/smartcoaster_2l.kicad_pcb

# 机械
cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py

# 固件
source /home/pi/.espressif/tools/activate_idf_v6.1.sh && cd firmware/esp32 && idf.py build
bash tests/firmware/run_host_tests.sh
```

## 8. 用户偏好与红线

- 只用本地/免费工具；不把项目文件传到第三方；不装 CalculiX/Gmsh（用 FreeCAD 自带 ccx/gmsh）。
- 机械版本独立（`mechanical/lumen`、`mechanical/square_v1`），不跨项目改几何。
- 未确认尺寸标 `PROVISIONAL`，改完必须复跑 `verify_v01.py`。
- 仿真通过 ≠ 实物通过；灵敏度/温漂/回差必须手板标定。
- 外观：前脸干净，不要白色灯缝；唯一缝隙是顶板-底座浮动缝。
- **不要做**：
  - 不要把 LED/光导加回来（用户明确不要）；
  - 不要把 4 层当主方案（用户要求最多 2 层，4 层只做兜底）；
  - 不要在没有 DRC 报告证据时说“0/0”；
  - 不要把空 SES / 0 unrouted 当成“布通”；
  - 不要代替用户做手板采购/装配/标定。

## 9. 验收标准（下一个 AI 交回时）

- [ ] `smartcoaster_2l.kicad_pcb`：`kicad-cli pcb drc --severity-all` 输出 **0 DRC / 0 unconnected**（附 `build/DRC_2l.rpt`）；
- [ ] 原理图 ERC **0 error**（附 `build/ERC.rpt`）；
- [ ] Gerber/钻孔/坐标/zip 已重出（`build/gerbers/`），`build/DFM.md` 为 2 层版本；
- [ ] 机械删光导后 `verify_v01.py` **21/21**；
- [ ] 固件 `idf.py build` 通过、host 差分 **16/16**，halo 已 disabled；
- [ ] `render/square_b`、`render/cmf`、`submission/` 不再出现光导；
- [ ] 工作区已 commit（当前有一批未提交改动）。
