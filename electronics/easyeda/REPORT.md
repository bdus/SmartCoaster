# REPORT — SmartCoaster EasyEDA 重做（数据链、验证与边界）

> 日期：2026-11-05 ｜ 基线：KiCad 交付 commit `9bcfd9d`（`electronics/kicad/` 只读）
> 结论摘要：离线 `.eprj3` 生成 + 5 门禁 + 逐脚网表对账 + **铜 1:1 移植 + 独立 GEOS 几何检查** 全部 PASS；
> 客户端 live DRC/铺铜/Gerber **BLOCKED（登录/激活）**。

## 1. 方法：canonical → design.json → eprj3 → 铜

```text
electronics/kicad/scripts/design.py                 (263 行，唯一电气来源)
electronics/kicad/smartcoaster/smartcoaster.net     (KiCad 9 XML 网表：43 comps / 28 nets)
electronics/kicad/smartcoaster/smartcoaster_2l.kicad_pcb (摆放 + 焊盘 + 板框 + 孔 + 已验证布线)
        │  extract_kicad.py（只读；pcbnew 9.0.9）
        ▼
inputs/canonical.json
  · 47 个 footprint（43 器件 + 4 个 M2 孔）
  · 每个 pad：本地坐标（mil, y-up）、宽高、形状（ROUNDRECT/OVAL/CIRCLE/RECT/CUSTOM）、
    圆角半径、drill、net、pin 名
  · placement：EasyEDA PCB mil 坐标 + 角度（y-up）
  · outline_mil：93.2×93.2 / R6 / 38×38 开口 / 80° 前 C 口（61 点，圆弧 12 段弦近似）
  · copper：576 tracks + 62 vias（坐标/层/线宽/网络）
        │  gen_design.py
        ▼
design/design.json  （47 parts / 7 blocks / powers=GND,3V3,VBUS,VBAT / pcb.place 全量显式）
        │  easyeda-eprj3-skill v2.2.1 build.js（官方离线引擎）
        ▼
smartcoaster_easyeda/  (.eprj3 + 1 页原理图 + 1 块 PCB，初始 placement-only)
        │  patch_board.py：BOARD_OUTLINE → 机械 C 形；pad → 真实形状/圆角；M2 pad → NPTH
        │  port_copper.py：KiCad tracks/vias → EasyEDA LINE/VIA（幂等）
        │  validate / placement DRC / check_copper(C1–C5) / netlist / report
        ▼
reports/*  与  render/pcb_routed.png
```

坐标与旋转约定（已用 pcbnew 库 local pad 交叉验证，绝对焊盘中心误差 < 1.3×10⁻⁵ mm）：

- 机械坐标 y-up、前脸 −Y；KiCad `kicad_y = −mech_y`。
- EasyEDA PCB：`x_eda=(x_kicad+46.6)/0.0254`，`y_eda=(−y_kicad+46.6)/0.0254`（mil，y-up）。
- 器件角度：`angle_eda = GetOrientationDegrees()`；焊盘本地坐标 = `M·R(θ)·Δ_kicad`。
- KiCad B.Cu 的 layer id 为 2（不是 31），映射到 EasyEDA bottom = 2。

## 2. 生成结果

| 指标 | 值 |
|---|---|
| 原理图 | 1 页 `SmartCoaster`，**47 器件 / 7 功能块**，272 段导线，32 个电源 flag，7 个跨块 net port |
| 网络 | **28 个电气网络 + 1 个 `NC` 分组（45 个 NC 脚）** |
| PCB | 1 块 `PCB1`，**47 footprint / 229 pad 实例 / 28 net** |
| 铜 | **576 track（440 top + 136 bottom）+ 62 via**，0.2 mm 最小线宽、0.6/0.3 mm 过孔 |
| 焊盘 | 119 圆角矩形（圆角按 KLC 25% 最小边）、94 矩形、9 圆、6 椭圆、1 自定义（按矩形近似） |
| 板框 | 93.2×93.2 mm，R6，38×38 中心开口，80° 前 C 口；4×M2 NPTH 2.2 mm @(±40,±24) mm |
| 文件 | `smartcoaster_easyeda.eprj3` 索引 + `sch/` + `pcb/`（文本格式，可 diff） |

门禁（`reports/build.log`）：

```text
schematic: 47 parts in 7 blocks across 1 sheet(s), 272 wire segments, 32 power flags, 7 net ports
pcb: 47 footprints · placement-only (before port_copper.py)
validate: 0 errors, 0 warnings
lint score 100/100 (0 error(s), 0 warning(s))
drc score 100/100 (0 error(s), 0 warning(s))
netcheck: OK — schematic ↔ PCB netlists match (213 pins)
```

打补丁后复跑（`reports/validate.log`、`reports/drc_placement.log`）：

```text
validate: OK (0 errors, 0 warning(s))
drc: 229 pads, 0 tracks, 0 vias, 0 pours · placed-only mode (D004/D006 skipped)
drc score 100/100 (0 error(s), 0 warning(s))
```

## 3. 与 KiCad 主链的独立对账

`scripts/check_parity.py` 用 `smartcoaster.net`（KiCad 9 XML）与 `inputs/built_netlist.json`（从生成原理图恢复）逐脚比较：

| 项 | KiCad | EasyEDA | 判定 |
|---|---|---|---|
| 器件 | 43 | 47（+4 个 M2 孔） | 机械附加，已登记 |
| 连接脚 | 168 | 168 | **完全一致** |
| 网络 | 28 | 28（+`NC` 分组） | **完全一致** |
| NC 脚 | 45（`unconnected-*`） | 45（net=`NC`） | 一致 |
| 机械焊盘 | —（不在网表） | J1 `MH`×2、J3 `MP`、H1–H4 `MH` | 白名单，非电气 |

输出：

```text
parity: kicad 43 comps / 168 connected pins / 28 nets; easyeda 47 comps (incl. 4 mechanical holes) / 168 connected pins / 29 nets
PARITY OK: every connected pin carries the same net name in both netlists
```

## 4. 独立网表审计（eprj3 skill 要求）

- 审计包：`reports/netlist-audit.json`（schema `eprj3-netlist-audit/1`；spec = design.json，built = 生成网表，mechanical = 工具自对账；md5 `56cb5087fb4b366d22f44a4bd91912c2`）。
- 由**无上下文的全新子代理 ×2**按 rubric 重算（不采信 mechanical 块），两轮结论一致：
  - `spec.parts`：47 器件 / 29 个网名 / 213 pin 成员，无 pin 被两个网占用；
  - `built.nets`：29 网 / 213 成员 / 213 unique pin，无重复、无 `N$` 自动网、无单脚网、`unconnected` 空；
  - 29 个网名逐一集合相等（含 `NC`），0 missing / 0 extra；NC 纪律：45 个 NC 脚全部只在 `NC` 网；
  - 4 个 `powers` 网 flag 数 GND 14 / 3V3 11 / VBUS 2 / VBAT 5；
  - PCB：229 pad 实例 → 213 unique pad / 29 网组；重复 pad 均为正常多焊盘封装（J1.S1×4、U1.61×9、H 孔等）。
- **判决：`ok: true`，无 error**。唯一 `warn`（advisory）：`PROT_VDD`（C4.1 / R11.2 / U4.5）像供电轨但未在 `spec.powers` 里，故未画电源 flag；电气上通过 net port 连接无误，留作后续可选项。
- 判决 JSON：`reports/audit_verdict.json`。

## 5. 独立铜检查（C1–C5，shapely/GEOS）

> 为什么不用 eprj3 skill 的 DRC 判铜：它把 track 当**轴对齐包围盒**算间距，45° 走线产生大量假阳性
> （本板实测 587 条假 D001、71 条宽度假 D002，而 KiCad 原板 `kicad-cli pcb drc --severity-all` 为 0/0）。
> 因此 skill DRC 只用于 placement；铜用独立 GEOS 检查（`scripts/check_copper.py`，真实线段/圆角矩形/圆）。

| 检查 | 结果 |
|---|---|
| **C1** 记录 round-trip | 576/576 LINE、62/62 VIA 与 canonical 的坐标/层/线宽/网络逐字段一致 |
| **C2** 不同网铜间距（0.2 mm） | 最小 **7.938 mil**（≥7.874），0 违规；同网/同封装内焊盘按规则豁免 |
| **C3** 网络连通性（D004 等价） | 所有多 pad 网络的 pad 与铜属于**同一铜岛**，0 未连通 |
| **C4** 板边/孔边净距（0.3 mm） | 最小 **13.917 mil**（≥11.811），NPTH 孔边也检查，0 违规 |
| **C5** 过孔钻孔/环宽 | 钻孔 0.3 mm（11.811 mil）、环宽 0.15 mm（5.906 mil）均满足 |
| **D006 类** | 无铺铜（GND plane），明确留给客户端；不计为已通过 |

输出：`reports/copper_check.json`、`reports/copper_check.log`。

## 6. 与 KiCad 原板的差异 / 风险（诚实清单）

| # | 差异 / 风险 | 级别 | 处置 |
|---|---|---|---|
| 1 | 铜是**移植**（KiCad 布线 → EasyEDA LINE/VIA），不是客户端重新布线；无铺铜 | 中 | 客户端登录后可重布/补 GND pour；当前结果可打开、可检查、可对比 |
| 2 | 未在客户端保存/重载/回读；客户端原生 DRC 口径未复核 | 高 | 登录后跑 `scripts/client_checks.sh`；在此之前标 offline-verified |
| 3 | 符号/封装为 inline（来自 KiCad 几何），非官方库；无 LCSC C 号 | 中 | 后续换 `"ic": "<device>"` + LCSC；当前不宜直接下 SMT 单 |
| 4 | R6 圆角为 12 段弦近似（61 点），非原生 ARC | 低 | 客户端板框工具重画或后续 ARC 化；弦高 <0.05 mm |
| 5 | 圆角矩形 pad 的圆角按 KLC 默认 25% 最小边（未逐个读封装文件） | 低 | 对 0.2 mm 间距检查保守；若改成实际 radius 需重跑 C2 |
| 6 | `project-report.md` 的“板框”一行是生成时自动尺寸旧值 | 低 | 以本文/`inputs/canonical.json` 为准（已加横幅） |
| 7 | 器件值/网络名沿用 KiCad；无独立“实物”验证 | 中 | 实物仍按 `tests/handboard/BRINGUP_RECORD.md` 标定 |
| 8 | 未做 Gerber/坐标/DFM、热/EMC/PI 复算 | 中 | Gerber 由客户端导出；电气评审沿用 `docs/REVIEW_ELECTRICAL.md` |

## 7. 后续验收清单（client live 解锁后）

- [ ] `eda.js sch-drc`：0 fatal/error（记录 rule/net/designator）
- [ ] `eda.js netlist`：与 `built_netlist.json` 再对一次
- [ ] 客户端打开工程：板框/焊盘/铜/网络可视化核对，**保存 → 重载 → 回读**
- [ ] `eda.js pour --net GND` 铺铜 + rebuild fill，再跑原生 `pcb drc`（目标 0 error / 0 unconnected）
- [ ] `eda.js screenshot --doc pcb` 目检；必要时 `pcb --route` 重布对比
- [ ] 导出 Gerber/坐标/BOM → 与 KiCad 的 `build/gerbers/`、`BOM.csv` 对比
- [ ] 板框 ARC 化 + 保存重载回读
