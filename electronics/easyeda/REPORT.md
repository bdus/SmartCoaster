# REPORT — SmartCoaster EasyEDA 重做（数据链、验证与边界）

> 日期：2026-11-05 ｜ 基线：KiCad 交付 commit `9bcfd9d`（`electronics/kicad/` 只读）
> 结论摘要：离线 `.eprj3` 生成 + 5 门禁 + 逐脚网表对账 **PASS**；客户端 live DRC/布线/制造导出 **BLOCKED（登录/激活）**。

## 1. 方法：canonical → design.json → eprj3

```text
electronics/kicad/scripts/design.py   (263 行，唯一电气来源)
electronics/kicad/smartcoaster/smartcoaster.net   (KiCad 9 XML 网表：43 comps / 28 nets)
electronics/kicad/smartcoaster/smartcoaster_2l.kicad_pcb  (摆放 + 焊盘 + 板框 + 孔)
        │  extract_kicad.py（只读；pcbnew 9.0.9 读焊盘几何）
        ▼
electronics/easyeda/inputs/canonical.json
  · 47 个 footprint（43 器件 + 4 个 M2 孔）
  · 每个 pad：本地坐标（mil, y-up）、宽高、形状、drill、net、pin 名
  · placement：EasyEDA PCB mil 坐标 + 角度（y-up；x=(mech_x+46.6)/0.0254）
  · outline_mil：93.2×93.2 / R6 / 38×38 开口 / 80° 前 C 口（61 点，圆弧 12 段弦近似）
        │  gen_design.py
        ▼
design/design.json  （47 parts / 7 blocks / powers=GND,3V3,VBUS,VBAT / pcb.place 全量显式）
        │  easyeda-eprj3-skill v2.2.1 build.js（官方离线引擎）
        ▼
smartcoaster_easyeda/  (.eprj3 + 1 页原理图 + 1 块 PCB)
        │  patch_board.py（只改 .epcb2：BOARD_OUTLINE → 机械 C 形；M2 pad → NPTH）
        │  validate / drc / netlist / report
        ▼
reports/*  与  render/pcb_placement.png
```

坐标与旋转约定（已用 pcbnew 库 local pad 交叉验证）：

- 机械坐标 y-up、前脸 −Y；KiCad `kicad_y = −mech_y`。
- EasyEDA PCB：`x_eda=(x_kicad+46.6)/0.0254`，`y_eda=(−y_kicad+46.6)/0.0254`（mil，y-up）。
- 器件角度：`angle_eda = GetOrientationDegrees()`；焊盘本地坐标 = `M·R(θ)·Δ_kicad`（与 KiCad 库 local pad 一致）。

## 2. 生成结果

| 指标 | 值 |
|---|---|
| 原理图 | 1 页 `SmartCoaster`，**47 器件 / 7 功能块**，272 段导线，32 个电源 flag，7 个跨块 net port |
| 网络 | **28 个电气网络 + 1 个 `NC` 分组（45 个 NC 脚）** |
| PCB | 1 块 `PCB1`，**47 footprint / 229 pad / 28 net**，placement-only（0 track / 0 via / 0 pour） |
| 板框 | 93.2×93.2 mm，R6，38×38 中心开口，80° 前 C 口；4×M2 NPTH 2.2 mm @(±40,±24) mm |
| 文件 | `smartcoaster_easyeda.eprj3` 索引 + `sch/` + `pcb/`（文本格式，可 diff） |

门禁（`reports/build.log`）：

```text
layout(shelf): 0 cross-net contact(s), 4 pin(s) with no clean exit → 170% looser grid
schematic: 47 parts in 7 blocks across 1 sheet(s), 272 wire segments, 32 power flags, 7 net ports
pcb: 47 footprints · placement-only (this skill never routes or pours)
  rats: 28 net(s) to connect by hand in the client
validate: 0 errors, 0 warnings
lint score 100/100 (0 error(s), 0 warning(s))
drc score 100/100 (0 error(s), 0 warning(s))
netcheck: OK — schematic ↔ PCB netlists match (213 pins)
```

板框补丁后复跑（`reports/validate.log`、`reports/drc.log`）：

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

> 该对账证明的是“同一张网表”，不证明布线质量；且 EasyEDA 侧是从本项目生成的原理图记录反推，属于**离线**证据。

## 4. 独立网表审计（eprj3 skill 要求）

- 审计包：`reports/netlist-audit.json`（schema `eprj3-netlist-audit/1`；spec = design.json，built = 生成网表，mechanical = 工具自对账；md5 `56cb5087fb4b366d22f44a4bd91912c2`）。
- 由**无上下文的全新子代理**按 rubric 重算（不采信 mechanical 块）：
  - `spec.parts`：47 器件 / 29 个网名 / 213 pin 成员，无 pin 被两个网占用；
  - `built.nets`：29 网 / 213 成员 / 213 unique pin，无重复、无 `N$` 自动网、无单脚网、`unconnected` 空；
  - 29 个网名逐一集合相等（含 `NC`），0 missing / 0 extra；
  - NC 纪律：45 个 NC 脚全部只在 `NC` 网；4 个 `powers` 网 flag 数 GND 14 / 3V3 11 / VBUS 2 / VBAT 5；
  - PCB：229 pad 实例 → 213 unique pad / 29 网组；重复 pad 均为正常多焊盘封装（J1.S1×4、U1.61×9、H 孔等）。
- **判决：`ok: true`，无 error**。唯一 `warn`（advisory，不改 netlist）：`PROT_VDD`（C4.1 / R11.2 / U4.5）像供电轨但未在 `spec.powers` 里，故未画电源 flag；属可读性建议，电气上通过 net port 连接无误。留作后续可选项，不在本轮改设计（避免破坏已审计基线）。
- 审计 JSON 落盘：`reports/audit_verdict.json`。

> 该对账证明的是“同一张网表”，不证明布线质量；且 EasyEDA 侧是从本项目生成的原理图记录反推，属于**离线**证据。

## 5. 与 KiCad 原板的差异 / 风险（诚实清单）

| # | 差异 / 风险 | 级别 | 处置 |
|---|---|---|---|
| 1 | **0 铜**：28 网仍为 ratsnest；未布线 | 高 | 客户端 `eda.js pcb --route` 或人工布线；在此之前不能称“PCB 完成” |
| 2 | 符号/封装为 inline（来自 KiCad 焊盘几何），非官方库；无 LCSC C 号 | 中 | 后续换 `"ic": "<device>"` + LCSC；当前可打开/检查，不宜直接下 SMT 单 |
| 3 | R6 圆角为 12 段弦近似（61 点），非原生 ARC | 低 | 客户端板框工具重画或后续格式支持 ARC；弦高 <0.05 mm |
| 4 | 板框补丁在 build 之后执行，`project-report.md` 的“板框 3860×3680 mil”是自动尺寸旧值 | 低 | 以本文/`inputs/canonical.json` 为准（README 已注明） |
| 5 | 器件值/网络名沿用 KiCad；`grep` 过 KiCad 网表；无独立“实物”验证 | 中 | 实物仍按 `tests/handboard/BRINGUP_RECORD.md` 标定 |
| 6 | 客户端 live 链路未跑通（登录/激活墙） | 高 | 见 install notes §4；用户登录后跑 `scripts/client_checks.sh` |
| 7 | 未做热/EMC/电源完整性复算 | 中 | 沿用 `docs/REVIEW_ELECTRICAL.md`，EasyEDA 侧不重复 |

## 6. 后续验收清单（client live 解锁后）

- [ ] `eda.js sch-drc`：0 fatal/error（记录 rule/net/designator）
- [ ] `eda.js netlist`：与 `built_netlist.json` 再对一次
- [ ] `eda.js pcb --route`：记录 track/via 数；`pcb drc` 0 error / 0 unconnected
- [ ] `eda.js screenshot --doc pcb`：目检板框/丝印/连接器
- [ ] 导出 Gerber/坐标/BOM → 与 KiCad 的 `build/gerbers/`、`BOM.csv` 对比
- [ ] 板框 ARC 化 + 保存重载回读
