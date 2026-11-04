# HANDOFF — SmartCoaster（2026-11-04 第二轮，交接给下一个 AI）

> 先读：`AGENTS.md` → `docs/01_AI_Hardware_Engineering_Pipeline.md` → `docs/07_Product_Roadmap.md` → 本文件。
> 上一份 HANDOFF 的卡点（DSN pad 类型 / Freerouting 空 SES）**已解决**，本轮把 2 层 PCB 布到了 **0 DRC / 0 unconnected**，并清完了 LED/光导在机械、固件、P3、文档里的残留。详见下文。

## 0. 执行摘要（先看这里）

- 产品：方形智能杯垫 100×100×18。用户最终决定：**光导全部去掉、LED 全部去掉、PCB 最多 2 层**，前脸只留 **26×7 屏窗 + 按键**；顶板-底座 0.5 mm 是秤的浮动缝，不放光。
- **P1 设计闭环**：原理图 **43 器件 / 28 网络**、ERC **0 error / 0 warning**；2 层 PCB **47 footprint（43 器件 + H1–H4）、576 track + 62 via、28 网络、0 DRC / 0 unconnected**（`build/DRC_2l.rpt`）。
- **P2 可制造**：2 层 Gerber/钻孔/坐标/zip（`build/gerbers/`、`build/smartcoaster_2l_gerbers.zip`）、JLC 2 层 DFM 全 PASS（`build/DFM.md`）、布线预览 `build/pcb_2l.png`。
- **机械**：12 件（删光导件），壳体前脸灯槽/过孔已删，`verify_v01.py` **21/21**、37 组干涉 0、0.5 mm 浮动缝与过载限位保留。
- **固件**：halo（RGB PWM 灯环）代码全删；`idf.py build` 通过，bin **519,152 B**（删前 532,992 B）；host **11/11**、mock **9/9**、C↔Python 差分 **16/16**、pytest **16**。
- **P3**：外观/CMF/包装/提交包全部按“无灯”用 Blender 4.5.3 重渲（`render/`、`submission/`），文档同步 43 器件。
- **独立验收**：`docs/VERIFY_REPORT.md`（verifier 本机复跑，非口头结论）**7/7 项 PASS**：PCB 0/0、ERC 0/0、Gerber/DFM、机械 21/21、固件测试与 bin、P3 无灯、事实性/红线。
- **唯一未完成（用户侧）**：手板采购/装配/实物标定 + PCB 打样 + 3D 打印。仿真与主机测试通过 **≠** 实物通过。

## 1. 用户最新决定（以此为准，覆盖旧文档）

1. **光导全部去掉**：窗周 halo、前缘灯线、底部灯线、Y 分光、顶板-底座缝隙光环——都不要；
2. **LED 也去掉**（D1、Q1–Q3、R13–R21 已从原理图/PCB/BOM/固件删除）；
3. **PCB 最多 2 层**，必须清到 **0 DRC / 0 unconnected**（已达成）；
4. 前脸只留 26×7 屏窗 + 按键；顶板与底座那 0.5 mm 是秤的浮动缝，不放光；
5. 用户希望“在前端持续看到过程”，所以每步都留了命令结果/图。

## 2. 仓库与工具链

- 工作区：`/data/Documents/projects/SmartCoaster`
- 机械：agentcad 0.7.1 + build123d 0.10.0（`mechanical/square_v1/.venv`）；版本快照 **v6_square_v1**
- PCB：KiCad 9.0.9（`/data/Documents/tools/kicad`，`~/.local/bin/kicad-cli`、`~/.local/bin/kicad-cli`）
- 布线：Freerouting **2.5.0**（自带 Java 25 runtime，`/data/Documents/tools/kicad` 之外的 `.tools/freerouting/`）+ Xvfb（`.tools/xvfb/usr/bin/Xvfb`，无系统 Xvfb）
- 固件：ESP-IDF v6.1（`source /home/pi/.espressif/tools/activate_idf_v6.1.sh`）
- 仿真/渲染：FreeCAD 自带 ccx 2.22 + gmsh 4.13.1、ngspice 36、Blender 4.5.3
- KiCad Python 环境（DRC 以外的脚本会用到）：
  ```bash
  export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
  export XDG_CONFIG_HOME=$PWD/.tools/kicad-config
  export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
  ```
- **沙箱注意（本机 DSH 环境）**：每次 bash 调用有独立 `/tmp` tmpfs，所以 **Xvfb 必须和 Freerouting 在同一次调用里启动**；`XDG_*` 必须指到工作区内（`.tools/fr-home/...`），否则写 `/home/pi` 被拒。

## 3. 当前已验证状态（全部带证据）

| 项 | 状态 | 证据 |
|---|---|---|
| 原理图 | **43 器件 / 28 网络**；ERC **0 error / 0 warning** | `electronics/kicad/build/ERC.rpt` |
| 2 层 PCB | 47 footprint、211 SMD / 12 PTH / 6 NPTH、576 track + 62 via、28 网络、最小线宽 0.2 mm、过孔 0.6/0.3 | `smartcoaster/smartcoaster_2l.kicad_pcb` |
| 2 层 DRC | **0 violation / 0 unconnected**（`--severity-all`） | `electronics/kicad/build/DRC_2l.rpt` |
| 2 层 ERC/DRC 口径 | silk 重叠/压铜按项目 severity 豁免（与旧 4 层一致）；U1 的 `SmartCoaster` footprint 库已用 `fp-lib-table` 正确挂上（所以库告警也消失了） | `smartcoaster/fp-lib-table`、`smartcoaster.kicad_pro` |
| Gerber/钻孔/坐标 | 2 层 9 层 Gerber + `.drl` + `.pos` + `.gbrjob` + zip | `build/gerbers/`、`build/smartcoaster_2l_gerbers.zip` |
| DFM（JLC 2 层） | 线宽 0.2≥0.127、过孔钻 0.3≥0.2、环宽 0.15≥0.13、板边 0.3≥0.3、层数 2 —— 全 PASS | `build/DFM.md` |
| 机械 | **12 件**；21/21 checks、37 组干涉 0、0.5 mm 浮动缝、过载限位 | `mechanical/square_v1/build/verify_v01.log`、`verify_report.json` |
| 固件 | halo 已删；bin 519,152 B（0x7EBF0）；host 11/11（41 checks）、mock 9/9（198 checks）、差分 16/16（82 records）、pytest 16 | `firmware/REPORT.md` |
| P3 | 渲染/提交包/CMF/包装全部按无灯重出；`grep 光导\|light_guide` 在 render/submission/packaging/README/BOM/docs(07,09,10,11) 为 0 | `render/RENDER_LOG.md`、`submission/` |
| 历史文档 | `docs/12_Light_Analysis.md` 保留 OBSOLETE 横幅；`electronics/kicad/REPORT.md`（P1 初稿 66 器件）加历史横幅 | 同文件 |

## 4. 本轮定位到的根因（重要，别再踩）

1. **上一份 HANDOFF 的“DSN 159 pin 全是 `[T]`、没有 `[S]`”是误判**：`grep "Rect\[.\]Pad"` 会把 `RoundRect[T]Pad` 里的 `Rect[T]Pad` 也匹配上，造成“162 个全是 [T]”的假象。DSN 里 SMD/THT 由 `[T]/[A]` 区分，Freerouting 能识别；**真正的问题是别的东西**（见 2）。
2. **真正的 DSN 解析错误：J4 的 value 里带双引号**（`OLED 0.91"`）。KiCad 写出 `(PN "OLED 0.91""")` 未转义，Freerouting 解析器错位后**静默错放了下一个 footprint（U2/HX711）**：U2 的 pad 被当成在别处，路由器把 3V3 直接穿过 U2 焊盘，并在导入后留下 U2 周边 14 个 unconnected。修复：`design.py` 里 J4 value 改成 `OLED 0.91in`，`route_2l.py export` 现在会断言 DSN 引号平衡。
3. **Freerouting 会输出少量 0.1874 mm 短线**（低于 0.2 mm 工程最小线宽）和 1 根悬空短线。`route_2l.py import` 把 <0.2 mm 统一加宽到 0.2；`clean` 用“同网络几何连通性”删悬空 stub（不是按 DRC 坐标盲删，盲删会误删相邻合法线段）。
4. **Xvfb + XDG 沙箱**：见 §2 注意。
5. **旧 4 层板能拿“0 DRC”是因为 4L 项目把 silk 类 warning 设成 ignore**；2 层沿用同一口径，并把 U1 的 footprint 库真正挂上（`fp-lib-table`），所以本轮 ERC 也变成 0 warning。

## 5. 关键文件与管线

| 文件 | 作用 |
|---|---|
| `electronics/kicad/scripts/design.py` | 原理图/网表唯一来源（43 器件 / 28 网络） |
| `electronics/kicad/scripts/gen_sch.py` | 生成 `.kicad_sch` + `.kicad_pro` + `sym-lib-table` + `fp-lib-table` |
| `electronics/kicad/scripts/gen_pcb.py` | 生成未布线 PCB（placement + footprint，2 层） |
| `electronics/kicad/scripts/route_2l.sh` | **2 层布线总入口**：导出 DSN → Xvfb+Freerouting → 导入 SES → 加宽/清悬空 → DRC |
| `electronics/kicad/scripts/route_2l.py` | 上者的 export / import / clean 三段（含 DSN 引号自检） |
| `electronics/kicad/scripts/build.sh` | **全流程**：原理图→ERC→PCB→布线→DRC→BOM→Gerber/钻孔/坐标→DFM→预览 |
| `electronics/kicad/scripts/dfm_check.py` | JLC **2 层** DFM 自查（已从 4 层切到 2 层） |
| `electronics/kicad/scripts/render_routed.py` | 布线预览 `build/pcb_2l.png`（F.Cu 红 / B.Cu 蓝 / via 黄） |
| `electronics/kicad/smartcoaster/smartcoaster_2l.kicad_pcb` | **当前 2 层已布线板（主交付）** |
| `electronics/kicad/smartcoaster/smartcoaster_4l.kicad_pcb` | 历史 4 层板（含 TP，**仅存档，不是主方案**；其 gerber 已从 `build/gerbers/` 移除） |
| `mechanical/square_v1/cad/square_model.py` | 机械唯一来源（12 件） |
| `mechanical/square_v1/cad/verify_v01.py` | 21 项自检（12 件 / 37 对干涉） |
| `firmware/esp32/` | ESP-IDF 固件（halo 已删） |
| `tests/firmware/run_host_tests.sh` | host + mock + 差分 + pytest |
| `tests/handboard/BRINGUP_RECORD.md` | 手板记录表（已无灯光项） |
| `docs/07_Product_Roadmap.md` | 阶段与判定 |
| `submission/` | Red Dot 提交包（无灯版） |

## 6. 常用命令

```bash
# 全流程：原理图 → ERC → 未布线 PCB → 2 层布线 → DRC 0/0 → BOM → Gerber/DFM → 预览
cd electronics/kicad/scripts && PATH=$HOME/.local/bin:$PATH ./build.sh

# 只重布线（沿用已生成 DSN/SES 可加 --keep）
cd electronics/kicad/scripts && ./route_2l.sh

# 独立 DRC
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export XDG_CONFIG_HOME=$PWD/.tools/kicad-config
~/.local/bin/kicad-cli pcb drc --format report --severity-all --units mm \
    -o build/DRC_2l.rpt smartcoaster/smartcoaster_2l.kicad_pcb

# 机械
cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py

# 固件
source /home/pi/.espressif/tools/activate_idf_v6.1.sh && cd firmware/esp32 && idf.py build
bash tests/firmware/run_host_tests.sh
```

## 7. 未完成任务（用户侧，AI 不能代替）

1. **手板**：采购 ESP32-S3-DevKitC-1、0.91" OLED、HY928D、HX711 模块、砝码；按 `docs/09_Assembly.md` 装配，按 `tests/handboard/BRINGUP_RECORD.md` 标定（灵敏度/温漂/回差必须实物标定，`counts_per_g=515.4` 仍是 PROVISIONAL）。
2. **打样**：PCB 用 `build/smartcoaster_2l_gerbers.zip` 下单（JLC 2 层常规工艺）；外壳/顶板用 `mechanical/square_v1/build/parts/*.stl` 3D 打印；打印后目检前脸（旧灯槽位置现在是实心 2.4 mm 前壁）。
3. 若要做认证/红点送审，按 `docs/10`、`docs/11`、`submission/` 补充实物照片。

## 8. 用户偏好与红线

- 只用本地/免费工具；不把项目文件传到第三方；不装 CalculiX/Gmsh（用 FreeCAD 自带 ccx/gmsh）。
- 机械版本独立（`mechanical/lumen`、`mechanical/square_v1`），不跨项目改几何；`ref/`、`mechanical/original_cad/` 只读。
- 未确认尺寸标 `PROVISIONAL`，改完必须复跑 `verify_v01.py`。
- 仿真通过 ≠ 实物通过；灵敏度/温漂/回差必须手板标定。
- 外观：前脸干净，不要白色灯缝；唯一缝隙是顶板-底座浮动缝。
- **不要做**：
  - 不要把 LED/光导加回来（用户明确不要）；
  - 不要把 4 层当主方案（用户要求最多 2 层；4 层文件只作存档）；
  - 不要在没有 DRC 报告证据时说“0/0”；
  - 不要把空 SES / 0 unrouted 当成“布通”（本轮用 SES 大小 + track/via 数 + DRC 0/0 三重校验）；
  - 不要代替用户做手板采购/装配/标定。

## 9. 验收标准（本轮已达成，下一位 AI 交回时以此为准）

- [x] `smartcoaster_2l.kicad_pcb`：`kicad-cli pcb drc --severity-all` **0 DRC / 0 unconnected**（`build/DRC_2l.rpt`，复制自 `build.sh` 末次运行）；
- [x] 原理图 ERC **0 error**（实际 0 error / 0 warning，`build/ERC.rpt`）；
- [x] 2 层 Gerber/钻孔/坐标/zip 已重出（`build/gerbers/`、`build/smartcoaster_2l_gerbers.zip`），`build/DFM.md` 为 2 层版本；
- [x] 机械删光导后 `verify_v01.py` **21/21**（12 件 / 37 对）；
- [x] 固件 `idf.py build` 通过、host 11/11 + mock 9/9 + 差分 16/16，halo 已删；
- [x] `render/square_b`、`render/cmf`、`render/packaging`、`submission/` 不再出现光导/LED；
- [x] 工作区已 commit（见 `git log` 最新一条；本轮为一次性收口提交）。
