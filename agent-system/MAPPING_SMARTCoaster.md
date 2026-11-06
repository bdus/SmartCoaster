# MAPPING — 系统元素 ↔ SmartCoaster 真实证据

> 本文件是"这套系统不是凭空写的"的证明：每个系统元素指向本项目真实文件/数字。
> **最后更新**：2026-11-07（P3.5 印花线 129/129 验收后）。
> 规则：数字只引用仓库证据；未达成项单列，不混入"已通过"。

## 0. 一句话映射

| 系统概念 | SmartCoaster 里的实体 | 结果 |
|---|---|---|
| 机械阶段 M0–M3 + G-MECH | `mechanical/square_v1/`（12 件） | **21/21**、37 对干涉 0、STEP 回读 12 solids |
| 电子阶段 E0–E4 + G-ELEC | `electronics/kicad/`（43 器件 / 28 网络） | ERC **0/0**、DRC **0/0**、DFM **5/5** |
| 固件阶段 F0–F4 + G-FW | `firmware/` + `tests/firmware/` | host **11/11**、mock **9/9**、差分 **16/16**、pytest **16** |
| 仿真 S1–S3 + G-SIM | `simulation/mechanical/hy928d/`、`simulation/electronics/` | FEA 0.3435 mm；S2 **28 结果 / 21 PASS / 7 发现** |
| 外观 A0–A2 + G-APPEAR | `docs/13_Appearance_Variants_Plan.md` | 冻结清单 + CMF 4 变体；B/C/D 变体未做 |
| 印花 P3.5–P3.6 + G-PRINT | `appearance/` + `render/print/appearance/` | **129/129** 只读验收 |
| 验证/集成 V/I + G-INTEG | `docs/VERIFY_REPORT.md`、`docs/AUDIT_*.md` | 独立验收 **7/7 + 10/10**；审计 PRD 185 条 / 流水线 146 项 |

## 1. 角色映射

| 系统角色 | 本项目对应 | 产出/证据 |
|---|---|---|
| `product` | 需求与 PRD 维护（Lead + 用户决定） | [docs/02_Smart_Coaster_PRD.md](../docs/02_Smart_Coaster_PRD.md)、[docs/REPORT_技术报告.md](../docs/REPORT_技术报告.md) §6 |
| `mechanical` | 机械 teammate | [mechanical/square_v1/cad/square_model.py](../mechanical/square_v1/cad/square_model.py)、[build/verify_report.json](../mechanical/square_v1/build/verify_report.json) |
| `electronics` | 电子 teammate；EasyEDA 第二实现 | [electronics/kicad/scripts/design.py](../electronics/kicad/scripts/design.py)、[build/DRC_2l.rpt](../electronics/kicad/build/DRC_2l.rpt) |
| `firmware` | 固件 teammate | [firmware/REPORT.md](../firmware/REPORT.md)、[tests/firmware/run_host_tests.sh](../tests/firmware/run_host_tests.sh) |
| `simulation` | 仿真 teammate | [simulation/mechanical/hy928d/README.md](../simulation/mechanical/hy928d/README.md)、[simulation/electronics/run_s2.py](../simulation/electronics/run_s2.py) |
| `appearance` | shell-cad / kroma / render teammates | [appearance/README.md](../appearance/README.md)、[appearance/build/ACCEPTANCE.json](../appearance/build/ACCEPTANCE.json) |
| `validation` | verifier + 3 个审计 teammate | [docs/VERIFY_REPORT.md](../docs/VERIFY_REPORT.md)、[docs/AUDIT_PIPELINE.md](../docs/AUDIT_PIPELINE.md) |
| `integration` | Team Lead | [docs/HANDOFF.md](../docs/HANDOFF.md)、[README.md](../README.md) |

## 2. 阶段 / 门禁 → 证据

| 阶段/门禁 | 关键动作 | 证据文件 | 真实结果 |
|---|---|---|---|
| M0 设计输入 | HY928D 图纸转录/参考拆解/参数清单 | [docs/02](../docs/02_Smart_Coaster_PRD.md) §4、[config/mechanical_params.yaml](../config/mechanical_params.yaml) | 参数表 + PROVISIONAL 登记 |
| M1–M2 建模 | `square_model.py` → 12 件装配 | [build/parts/](../mechanical/square_v1/build/parts) | 100×100×18，78,338 mm³ |
| M3 机械验证 | `verify_v01.py` 21 项 | [verify_v01.log](../mechanical/square_v1/build/verify_v01.log) | **21/21 PASS**，37 对干涉 0，STEP 回读 12 |
| E2 原理图 | `design.py` → ERC | [ERC.rpt](../electronics/kicad/build/ERC.rpt) | **0 Errors 0 Warnings** |
| E3 PCB | 2 层布线 → DRC | [DRC_2l.rpt](../electronics/kicad/build/DRC_2l.rpt) | **0 DRC violations / 0 unconnected pads / 0 footprint errors** |
| E4 制造 | Gerber/钻孔/坐标/DFM | [DFM.md](../electronics/kicad/build/DFM.md)、[build/gerbers/](../electronics/kicad/build/gerbers) | **5/5 PASS**，9 层 Gerber + zip |
| PCB-FAB 交叉验证 | KiCad↔EasyEDA 数据契约 | [cross_tool.json](../electronics/easyeda/reports/cross_tool.json)、[parity.log](../electronics/easyeda/reports/parity.log) | X1–X5 一致（168 pins / 28 nets） |
| F1–F4 固件 | host/mock/差分/pytest/构建 | [firmware/REPORT.md](../firmware/REPORT.md) | **11/11 + 9/9 + 16/16 + 16**；bin 519,184 B |
| S1 FEA | HY928D 本体（对象 A） | [results_h035_c3d10.json](../simulation/mechanical/hy928d/results_h035_c3d10.json) | 5 kg 中心 **0.3435 mm**，支反力 **100%**，非奇异热点 **467.7 MPa** |
| S2 SPICE | 四模块×六类分析 | [s2_summary.json](../simulation/electronics/results/s2_summary.json) | **28 结果 / 21 PASS / 7 发现** |
| S3 固件仿真 | host 测试 + QEMU 冒烟 | [firmware/REPORT.md](../firmware/REPORT.md) §5 | host 全绿；QEMU 骨架阶段 |
| A0 冻结 | 冻结清单/允许变化 | [docs/13](../docs/13_Appearance_Variants_Plan.md) | 12 类冻结项；真圆不可行（131.8 > Ø110） |
| A2 CMF | 4 变体渲染 | [render/cmf/CMF_variants.png](../render/cmf/CMF_variants.png) | 4 变体（无灯） |
| P3.5 印花 | Kromacut→开槽→3MF→渲染 | [appearance/build/ACCEPTANCE.json](../appearance/build/ACCEPTANCE.json) | **129/129 PASS** |
| P3.6 打印交付 | STL+床面+参考图+checksums | [render/print/appearance/square/manifest.json](../render/print/appearance/square/manifest.json)、[layout.json](../render/print/appearance/square/layout.json) | 8/10 STL；床面 218.94×110.00 / 208.0×110.2 mm |
| V0 独立验收 | verifier 只读复跑 | [docs/VERIFY_REPORT.md](../docs/VERIFY_REPORT.md) | **7/7 + 增量 10/10 PASS** |
| V1 审计 | PRD 185 条 / 流水线 146 项 | [docs/AUDIT_PRD.md](../docs/AUDIT_PRD.md)、[docs/AUDIT_PIPELINE.md](../docs/AUDIT_PIPELINE.md) | 91/50/28/3/13 与 71/46/28/1 |
| I1 交接 | HANDOFF + 风险登记 | [docs/HANDOFF.md](../docs/HANDOFF.md) | R1–R19 风险登记 |

## 3. 数字证据（可直接抽查）

| 数字 | 含义 | 文件 |
|---|---|---|
| **21/21** | 机械自检通过数 | [verify_v01.log](../mechanical/square_v1/build/verify_v01.log) |
| **37 pairs** | 关键零件两两干涉对数（0 干涉） | 同上 |
| **12 solids** / 100×100×18 | 装配实体数与包围盒 | 同上 |
| **43 / 28** | 原理图器件 / 网络 | [ERC.rpt](../electronics/kicad/build/ERC.rpt) |
| **0 / 0** | ERC error / warning | 同上 |
| **0 / 0** | DRC violation / unconnected | [DRC_2l.rpt](../electronics/kicad/build/DRC_2l.rpt) |
| **5/5** | JLC 2 层 DFM 项 | [DFM.md](../electronics/kicad/build/DFM.md) |
| **576 track + 62 via** | 2 层布线规模 | [smartcoaster_2l.kicad_pcb](../electronics/kicad/smartcoaster/smartcoaster_2l.kicad_pcb) |
| **11/11 · 9/9 · 16/16 · 16** | host · mock · 差分 · pytest | [firmware/REPORT.md](../firmware/REPORT.md) |
| **519,184 B** | 固件 bin（0x7EC10） | 同上 |
| **0.3435 mm** | 5 kg 中心位移 | [simulation/mechanical/hy928d/README.md](../simulation/mechanical/hy928d/README.md) |
| **467.7 MPa** | 非奇异热点（竖槽端 R1.25） | 同上 |
| **54.7 nVrms ≈ 0.069 g** | HX711 输入噪声 | [s2_summary.json](../simulation/electronics/results/s2_summary.json) |
| **530.5 Hz** | 外部 RC 截止（真实 BOM） | 同上 |
| **5.019 mA → 4.15 天** | 连续采样功耗预算 | 同上 |
| **129/129** | P3.5 只读验收 | [ACCEPTANCE.json](../appearance/build/ACCEPTANCE.json) |
| **94/94** | 外壳开槽校验 | [appearance/build/shell/REPORT.md](../appearance/build/shell/REPORT.md) |
| **25/25 ×2** | 印花几何自检 | [appearance/build/print/REPORT.md](../appearance/build/print/REPORT.md) |
| **218.94×110.00 / 208.0×110.2 mm** | 220 床面占用 | [layout.json](../render/print/appearance/square/layout.json) |

## 4. 明确 NOT achieved（下一个项目不要继承成"已完成"）

| 项 | 状态 | 真实情况 | 证据/说明 |
|---|---|---|---|
| 手板 bring-up + 砝码标定 | ⛔ 未做 | 采购/装配/标定属用户侧；记录表为空 | [tests/handboard/BRINGUP_RECORD.md](../tests/handboard/BRINGUP_RECORD.md)、[docs/05](../docs/05_Bringup_and_Verification_Plan.md) |
| 灵敏度/温漂/回差标定 | ⛔ 未做 | `counts_per_g=515.4` 仍是 PROVISIONAL | [docs/REPORT_技术报告.md](../docs/REPORT_技术报告.md) §7 R1 |
| Bambu 切片 / 实物多材料打印 | ⛔ 未做 | 本机无 Bambu Studio；只验证 3MF/STL 几何与床面排版 | [appearance/README.md](../appearance/README.md) §12 |
| FEA 对象 B/C | ⛔ 未做 | 只完成 HY928D 本体（对象 A）；顶板+传力柱/整机限位未做 | [simulation/mechanical/](../simulation/mechanical) |
| S4 / MCP 编排 | ⛔ 未实现 | 只有各域 CLI，没有统一 JSON 契约与一条命令 | [docs/REPORT_技术报告.md](../docs/REPORT_技术报告.md) §3.5 |
| QEMU 复跑（删 halo 后） | ⚠️ 部分 | QEMU 证据为骨架阶段，删 halo 后未重跑 | [firmware/REPORT.md](../firmware/REPORT.md) §5 |
| 手机 App / BLE 数据面 | ⛔ 未做 | 无 App；缺单次/历史/提醒配置特征 | [docs/REPORT_技术报告.md](../docs/REPORT_技术报告.md) §7 R8 |
| 开槽顶板 FEA + 21 项自检 | ⛔ 未做 | 顶板肉厚 3.0→1.55 mm，刚度/传力未证 | [appearance/README.md](../appearance/README.md) §6.5 |
| EasyEDA live DRC/铺铜/Gerber | 🚫 阻塞 | 登录/激活墙（`pro.lceda.cn` 418）；离线 PASS ≠ 客户端验证 | [docs/HANDOFF.md](../docs/HANDOFF.md) §0.0 |
| 铝顶板 RF 实测 | ⛔ 未做 | 铝顶板压天线，距离未实测 | [docs/REPORT_技术报告.md](../docs/REPORT_技术报告.md) §7 R15 |
| B/C/D 外观变体 | ⛔ 未做 | 只有 CMF 4 变体与冻结清单；变体建模未开始 | [docs/13](../docs/13_Appearance_Variants_Plan.md) §5 |
| HY928D 供应商核实（M2） | ⛔ 未关闭 | U 槽/中心孔/桥路/灵敏度/额定形变等 8 问未答 | [config/mechanical_params.yaml](../config/mechanical_params.yaml) |
| git remote 授权 | ⚠️ 未确认 | 发现历史 27 次 push 到 GitHub remote；授权状态未知 | [docs/REPORT_技术报告.md](../docs/REPORT_技术报告.md) §2.5 |

## 5. 解释 vs 引用（诚实标注）

以下内容是**从源材料归纳/解释**，不是源文件里的原句（使用时可回查）：

1. **28 阶段编号**（M0–M3 / E0–E4+PCB-FAB / F0–F4 / S1–S4 / A0–A2 / P3.5–P3.6 / V0–V1 / I0–I1）
   是对 docs/01 阶段与门禁的**重新编号/扩展**；原项目没有"PCB-FAB""A0–A2""V0–V1"这些独立编号。
2. **7 组门禁**的分组是我按域归纳的；原项目门禁分散在脚本（`verify_v01.py` 21 项、
   `acceptance_check.py` 129 项、ERC/DRC/DFM 报告等），没有统一的 `gates/*.yaml`。
3. **角色 8 个**基于 docs/01 §3.1 的 6 个 Agent + 本项目实际使用的 appearance/validation/lead；
   原项目实际是"Team Lead + 4 teammate + 3 审计 teammate"。
4. **工具链许可字段**多数来自上游常见许可；`agentcad`/`easyeda-agent`/`easyeda-eprj3-skill`
   在本仓库未记录许可，已在 `SYSTEM.yaml` 标 `license_source: upstream` 并写"未在仓库记录"。
5. **模板/脚手架**是新写的（原项目没有脚手架），但内容均从本项目真实文件蒸馏。
6. **"30–60 分钟实例化"**是估算，不是实测数字。

## 6. 复核方式

```bash
# 系统结构自检
python3 agent-system/scripts/check_system.py

# 抽查任意数字
cat mechanical/square_v1/build/verify_v01.log | tail -3
cat electronics/kicad/build/DRC_2l.rpt
cat electronics/kicad/build/DFM.md
python3 -c "import json;d=json.load(open('simulation/electronics/results/s2_summary.json'));print(d['n_results'],d['n_pass'],d['n_fail'])"
python3 -c "import json;d=json.load(open('appearance/build/ACCEPTANCE.json'));print(d['total'],d['passed'],d['failed'])"
```
