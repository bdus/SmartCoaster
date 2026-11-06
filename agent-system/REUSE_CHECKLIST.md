# REUSE CHECKLIST — 下一个硬件项目怎么用这套系统

> 目标：**30–60 分钟**把系统实例化到新项目；只改"项目特定值"，不动"通用机制"。
> 红色标记 = 红线，不允许为了省事删掉。

## 0. 6 步实例化

```bash
# 1) 复制 agent-system/ 到新仓库（或作为 sibling 保留）
# 2) 干跑
python3 agent-system/scripts/new_project.py <name> --dry-run
# 3) 真实生成（不要生成在 agent-system/ 内）
python3 agent-system/scripts/new_project.py <name> --root /path/to/<name>
# 4) 按 §1 改 8 处项目特定值
# 5) 填 PRD / config / TASK_BOARD
# 6) 跑自检
python3 scripts/acceptance_check.py
python3 agent-system/scripts/check_system.py   # 若 agent-system 在新仓库内
```

## 1. 必须改（8 处）

| # | 位置 | 改什么 | 例子（SmartCoaster → 你的项目） |
|---|---|---|---|
| 1 | `SYSTEM.yaml: system.*` | id/name/derived_from/source_workspace | `smartcoaster-agent-system` → `<yours>` |
| 2 | `SYSTEM.yaml: maturity` | verified/not_verified 换成你的真实状态；**不许空** | 把"21/21"换成你的自检计数 |
| 3 | `roles/*.md` | 角色名/职责里项目特定部分 | `HY928D/ESP32-S3` → 你的器件 |
| 4 | `workflows/*.md` | 阶段表里的路径/命令/器件 | `verify_v01.py` → 你的自检脚本 |
| 5 | `gates/*.yaml` | 判据里的**数值/阈值/证据路径** | `0.5 mm`、`ERC 0/0`、`211 SMD` |
| 6 | `templates/*` | 项目名/器件/命令占位 | `{{PROJECT_NAME}}` 等 token（脚手架替换） |
| 7 | `MAPPING_SMARTCoaster.md` | 换成你的证据映射（或删除后重建） | 文件路径 + 真实数字 |
| 8 | `README.md` | 来源与规模数字 | 不要手写重复计数，交给 check_system 输出 |

## 2. 不要改（通用机制）

- **门禁结构**：`gate_id / stages / checks[{id, criterion, severity, status}]` 的 schema。
- **check_system.py 的校验逻辑**（可以加检查，不要删校验）。
- **产物契约规则**：唯一来源、下游只读契约、机器可读优先、图片只辅助。
- **决策规则**：PROVISIONAL、单一来源、证据优先、阈值来源、独立复核。
- **红线**（见 §5）。
- **模板占位符命名**：`{{PROJECT_NAME}}` / `{{PROJECT_SLUG}}` / `{{PROJECT_TITLE}}` /
  `{{DOMAIN}}` / `{{DATE}}` / `{{SYSTEM_ID}}` / `{{SYSTEM_VERSION}}` / `{{ROOT_NAME}}`。

## 3. 领域特定 vs 通用（判断表）

| 内容 | 通用 | 领域特定（必须改） |
|---|---|---|
| 角色划分 | ✅ 8 角色 | 角色名可换，职责结构保留 |
| 阶段编号（M/E/F/S/A/P/V/I） | ✅ | 可裁剪（如无印花线可删 P3.5/P3.6，但要在 SYSTEM.yaml 同步） |
| 门禁 schema | ✅ | 判据数值/证据路径 |
| 自检脚本 | ✅ 结构（check/JSON/exit code） | 具体检查项 |
| 工具链 | ✅ 组织方式 | 版本/位置/许可 |
| 产物契约 | ✅ 类型/命名/只读规则 | 字段名与例子 |
| 失败模式清单 | ⚠️ 大部分通用 | 器件/工艺特定条目 |
| 红线 | ✅ | 项目附加红线（如"不得恢复 LED"） |

## 4. 新项目第一周建议顺序

1. **PRD + config**（product）：需求、未确认项、阈值来源。
2. **机械最小闭环**（mechanical）：单文件参数化 → 导出 → 自检 → JSON。
3. **电子最小闭环**（electronics）：design.py → 原理图 → ERC → PCB → DRC → DFM。
4. **固件分层**（firmware）：纯逻辑 + HAL + host 测试（先不接硬件）。
5. **仿真**（simulation）：先做最成熟的输入（通常是结构/前端），落 JSON。
6. **集成**（integration）：任务板 + 跨层一致性 + HANDOFF。
7. 之后才做外观/印花/打印等下游阶段。

## 5. 红线（删掉任何一条都视为系统失效）

- [ ] 只用本地/免费工具；不传第三方；遥测关闭。
- [ ] 原始资料只读；不覆盖。
- [ ] 未确认参数标 `PROVISIONAL` 并进 config。
- [ ] 每个域只有一个唯一来源；生成物可重跑。
- [ ] 没有证据不说"通过"；没有阈值来源不判定。
- [ ] 仿真通过 ≠ 实物通过。
- [ ] 不做 GUI 自动化。
- [ ] 不经确认不进入高成本打样；git remote 推送需授权。
- [ ] 用户侧采购/装配/标定/打样不由 AI 代做。
- [ ] 不写"全部通过"；必须列未测项。

## 6. 裁剪指南（项目不需要某域时）

| 删除 | 必须同步 |
|---|---|
| appearance / ip-print 阶段 | `SYSTEM.yaml` 的 domains/stages/workflows/gates + `gates/` 文件 + 链接 |
| simulation 阶段 | `roles/simulation.md` 可保留但标 N/A；门禁标 `not_run` |
| 某域 | `check_system.py` 会因悬空引用报错——所以先删引用再删文件 |

> 原则：**门禁可以标 `not_run`/`N/A`，但不能悬空引用**。`check_system.py` 就是防这个。

## 7. 复用前自检（复制到新项目后立刻跑）

```bash
python3 agent-system/scripts/check_system.py     # 结构必须 PASS
python3 agent-system/scripts/new_project.py t --dry-run   # 脚手架必须能跑
python3 -c "import yaml; yaml.safe_load(open('agent-system/SYSTEM.yaml'))"
```
