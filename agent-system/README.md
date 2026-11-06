# README — AI-Native Hardware Engineering Agent System

> **一句话**：把 SmartCoaster 项目跑通的"AI 原生硬件研发闭环"蒸馏成一套可复用
> 的 Agent 系统——8 个角色、28 个阶段、7 组门禁、145 条检查、9 个模板、2 个脚本。
>
> **来源**：SmartCoaster 智能杯垫（方形 V1，2026-11-03 … 2026-11-06）。
> **证据映射**：[MAPPING_SMARTCoaster.md](MAPPING_SMARTCoaster.md)（每个数字对应仓库文件）。
> **机器规范**：[SYSTEM.yaml](SYSTEM.yaml)（`python3 scripts/check_system.py` 校验）。

---

## 0. 这是什么 / 不是什么

**是**：一套可直接 drop 到下一个硬件项目的工程操作系统——
角色契约、工作流、门禁阈值、产物契约、模板、脚手架、验收脚本、复用清单。

**不是**：不是"AI 一键生成产品"的营销模板；不是某个模型的 prompt 集合；
不是替代专业工具（CAD/EDA/FEA/编译器）。原则见 `SYSTEM.yaml: decision_rules`。

**核心原则**：AI 负责理解/规划/生成/编排；专业工具负责求解；
**人负责关键决策与验收**。每个"通过"必须能指到文件/命令输出/时间戳。

---

## 1. 30 分钟实例化（新项目）

```bash
# 0) 复制整个 agent-system/ 到新项目（或作为 sibling 目录保留）
# 1) 干跑，看要生成什么
python3 agent-system/scripts/new_project.py my-product --dry-run

# 2) 真正生成（默认 ./my-product；不要生成在 agent-system/ 里）
python3 agent-system/scripts/new_project.py my-product --root /path/to/my-product

# 3) 按 REUSE_CHECKLIST.md 改 8 处项目特定值
# 4) 跑骨架验收
cd /path/to/my-product && python3 scripts/acceptance_check.py
```

详细步骤与"改什么/不改什么"见 [REUSE_CHECKLIST.md](REUSE_CHECKLIST.md)。

---

## 2. 目录地图

```text
agent-system/
├── README.md                     ← 本文件
├── SYSTEM.yaml                   ← 单一机器可读规范（角色/阶段/门禁/产物/工具链/约束）
├── REUSE_CHECKLIST.md            ← 每项目要改什么 + 红线
├── MAPPING_SMARTCoaster.md       ← 系统元素 → 本项目真实证据（含未达成项）
├── roles/                        ← 8 个角色 charter
│   ├── product.md · mechanical.md · electronics.md · firmware.md
│   ├── simulation.md · appearance.md · validation.md · integration.md
├── workflows/                    ← 8 个域工作流（阶段表 + 清单 + 失败模式）
│   ├── mechanical.md · electronics.md · firmware.md · simulation.md
│   ├── appearance.md · ip-print.md · validation.md · integration.md
├── gates/                        ← 7 组可执行式门禁（id + 判据 + 证据 + 严重度）
│   ├── mechanical.yaml · electronics.yaml · firmware.yaml · simulation.yaml
│   ├── appearance.yaml · ip-print.yaml · integration.yaml
├── artifacts/contracts.md        ← 产物类型/字段/命名/目录/机器可读边界
├── templates/                    ← 9 个脚手架模板
│   ├── AGENTS.md.tmpl · HANDOFF.md.tmpl · requirements.yaml.tmpl
│   ├── task-board.md.tmpl · acceptance_check.py.tmpl · PRD-outline.md.tmpl
│   ├── repo-layout.md.tmpl · gate-run.md.tmpl · config-mechanical_params.yaml.tmpl
└── scripts/
    ├── new_project.py            ← 脚手架（--dry-run / --root / --force）
    └── check_system.py           ← SYSTEM.yaml + 文件引用 + md 链接校验
```

---

## 3. 系统规模（机器可读，由 check_system.py 输出）

| 项 | 数量 |
|---|---|
| 角色 roles | 8 |
| 域 domains | 7 |
| 阶段 stages | 28（M0–M3 / E0–E4+PCB-FAB / F0–F4 / S1–S4 / A0–A2 / P3.5–P3.6 / V0–V1 / I0–I1） |
| 工作流 workflows | 8 |
| 门禁组 gates | 7 |
| 门禁检查 checks | 145（G-MECH 21 / G-ELEC 23 / G-FW 16 / G-SIM 26 / G-APPEAR 15 / G-PRINT 28 / G-INTEG 16） |
| 模板 templates | 9 |

> 实际数字以 `python3 scripts/check_system.py` 输出为准（本文件不手写重复值）。

---

## 4. 怎么用（三个层次）

### 4.1 人类负责人

1. 读本文件 + `SYSTEM.yaml: constraints`（红线）+ `MAPPING_SMARTCoaster.md`（哪些做过/没做过）。
2. 用 `REUSE_CHECKLIST.md` 判断哪些要改、哪些不要改。
3. 每个阶段结束看 `docs/gate-run.md` 与本项目验收输出，不看"口头通过"。

### 4.2 Lead / 集成 Agent

1. 用 `TASK_BOARD.md` 拆任务，登记 owner + 写作用域 + 依赖。
2. 每个 teammate 的 prompt 自包含（路径 + 规范 + 验收 + 禁止事项）。
3. 收口：跨层一致性 + 最终 diff + 全链路测试 + HANDOFF。

### 4.3 领域 Agent

1. 先读对应 `roles/<role>.md` + `workflows/<domain>.md`。
2. 门禁在 `gates/<domain>.yaml`；每条有判据/证据/严重度。
3. 产物契约在 `artifacts/contracts.md`；下游只读契约、不猜参数。

---

## 5. 成熟度与限制（诚实清单）

**本项目真正验证过**（详见 `SYSTEM.yaml: maturity.verified` 与 MAPPING）：

- 机械 21/21、37 对干涉 0、STEP 回读 12 solids；
- ERC 0/0、2 层 PCB DRC 0/0、DFM 5/5、双 EDA 对账 X1–X5；
- 固件 host 11/11 + mock 9/9 + 差分 16/16 + pytest 16、bin 519,184 B；
- S1 FEA（对象 A）、S2 28 结果 21 PASS / 7 发现；
- P3.5 印花线 129/129 只读验收。

**明确未验证**（不得在下一个项目继承成"已完成"）：

- 手板 bring-up 与砝码标定（用户侧）；
- Bambu Studio 实际切片与实物多材料打印；
- FEA 对象 B/C（顶板+传力柱 / 整机限位）；
- S4 / MCP 编排；
- 手机 App / BLE 数据面、开槽顶板 FEA、EasyEDA live DRC、铝顶板 RF 实测。

> **仿真通过 ≠ 实物通过。** 这是本系统最重要的一条边界。

---

## 6. 系统自检

```bash
python3 scripts/check_system.py            # 结构/引用/链接校验（exit 0 = 通过）
python3 scripts/check_system.py --json     # 机器可读
python3 scripts/new_project.py demo --dry-run
python3 -c "import yaml; yaml.safe_load(open('SYSTEM.yaml'))"
```

`check_system.py` 校验：SYSTEM.yaml 可解析、必备段存在、每个 role/workflow/gate/template
文件存在、stage↔workflow↔gate 双向一致、产物引用存在、门禁 check 的 id/severity/status
合法、所有 `.md` 无悬空相对链接、工具链条目完整、成熟度清单非空。

---

## 7. 与 SmartCoaster 仓库的关系

- 本目录**只读引用**原项目证据，不改 `docs/`、`mechanical/`、`electronics/`、
  `firmware/`、`appearance/`、`render/`、`AGENTS.md`、`README.md`。
- 原项目入口仍见仓库根 `README.md` 与 `docs/HANDOFF.md`。
- 新项目应复制本目录（或保留为 sibling），按 REUSE_CHECKLIST 改写。
