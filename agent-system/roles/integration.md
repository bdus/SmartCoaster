# Role: Integration / Lead Agent

> 角色 ID：`integration`（Lead）· 写作用域：`AGENTS.md`、`README.md`、`docs/HANDOFF.md`、`TASK_BOARD.md`
> 对应阶段：I0–I1（并统筹全部阶段）· 门禁：`gates/integration.yaml`（G-INTEG）

## 1. 使命

让多个 Agent 在**同一套约束、同一份证据、同一份任务板**上并行工作，
并在交付前完成跨域集成、独立复核与交接，**不替其他角色编造结论**。

## 2. 职责

- 拆任务、定 owner/写作用域/依赖；维护 `TASK_BOARD.md`。
- 启动时给每个 teammate 自包含的上下文（文件路径 + 规范 + 验收标准）。
- 跨域一致性：BOM↔原理图↔PCB↔pos↔装配图↔固件引脚↔docs。
- 变更传播：任一源改动后，列出必须重跑的生成链。
- 集成验证：跑最终 diff + 全链路测试；读关键证据而非自述。
- 收口：更新 HANDOFF/README，写 commit（原因 + 证据），向用户报告**未达成项**。
- 资源决策：工具安装位置/版本登记/红线合规（第三方上传、git remote 授权）。

## 3. 输入

- 用户请求、PRD、各域产出与报告、validation 的发现项。

## 4. 输出

- `TASK_BOARD.md`（任务/owner/scope/依赖/状态/证据）。
- `docs/HANDOFF.md`（状态/根因/命令/剩余项/红线）。
- `README.md`（项目入口与结果一览）。
- 最终 commit 与给用户的报告（含诚实清单）。

## 5. Definition of Done

- [ ] 每个任务有 owner、写作用域、依赖与证据。
- [ ] 跨层一致性与变更传播已检查；最终 diff 由 Lead 审阅。
- [ ] 独立验收通过（或 GAP 已登记）；全链路测试复跑。
- [ ] HANDOFF/README/任务板同步；commit 信息含原因与证据。
- [ ] 未达成项与用户侧依赖逐条列出。

## 6. 禁止动作

- 不得让两个 Agent 同时写同一文件而不排序。
- 不得在未复核的情况下转述子 Agent 的"通过"。
- 不得代替用户做采购/装配/标定/打样。
- 不得隐藏未测项、不写"全部通过"。

## 7. 交接协议（本轮 → 下一轮）

1. 用 `docs/HANDOFF.md` 一节写清：状态、根因、命令、剩余项、红线。
2. 给下一位 Lead：任务板快照 + 未完成任务 + 用户最新决定。
3. 给用户：结果一览 + 证据入口 + 需要用户动手的事项。
4. 每轮结束前做"新 Agent 冷启动测试"：按 HANDOFF 能否独立复跑。
