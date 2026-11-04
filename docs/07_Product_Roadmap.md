# 产品路线：先“能用”，再“红点级”

> 2026-11-04 起。G0（可行性）已完成；下面按 **P1 可用 → P2 可制造 → P3 红点级** 迭代。
>
> **2026-11-04 用户决定（覆盖旧版）**：LED 与所有发光件全部去掉；PCB 最多 2 层。前脸只有 **26×7 屏窗 + 按键**；唯一缝隙是**顶板-底座 0.5 mm 浮动缝**（秤的行程缝），无灯、无灯缝。

## P1 — 能用（当前目标）

**功能**
- [ ] PCB 0 short / 0 unconnected；ERC/DRC 干净（丝印可豁免，需记录）。
- [ ] 手板：按 `tests/handboard/BRINGUP_RECORD.md` 记录（线性/噪声/杯事件/凸台/功耗/BLE）
- [ ] 砝码标定：零点、量程、重复性、噪声、温漂记录。
- [x] NVS 持久化（today/goal/tare/mode，跨重启；`idf.py build` 通过，bin 250 KB）
- [x] BLE GATT（NimBLE 0xFF00：重量/今日/目标/电量/命令）
- [x] 跨日时钟（BLE 0xFF06 写 Unix 秒，自动 reset + NVS）
- [x] OLED 8 s 息屏（按键/放杯提醒唤醒）
- [x] PM 自动 light sleep + BT modem sleep + 广播占空（S2 仿真：连续采样 5.02 mA→4.2 天；**7 天需模拟前端占空/断电，待固件**；实测待手板）
- [x] OLED 中文（16×16 字库子集 26 字 + 混合 2× ASCII，128×32 单行 + 进度条）
- [x] 广播占空（开机 30 s / 配对 120 s / 空闲关）
- [ ] 整机装配：四角凸台共面、+y 预紧、浮动间隙 0.156 mm 余量、限位。
- [ ] 连续 7 天饮水记录不丢数、不误触发。

**外观（可用级）**
- [x] 前脸：26×7 屏窗 @ x=−8、按键 x=17
- [x] 去灯：LED 与全部发光件已删除；原理图 **43 器件 / 28 网络**，机械 **13→12 件**（删发光件）
- [x] 顶板-底座 **0.5 mm 浮动缝**（秤的行程缝，不做灯/不填缝）；机械自检 **21/21**（37 组干涉对 0 干涉）
- [ ] 顶板/底壳配合、无段差、按键手感。
- [ ] 3D 打印首件（外壳 + 顶板）验证屏/键/传感器配合。

## P2 — 可制造

- [x] PCB 层数决策：**2 层（当前主方案，已布通）**；4 层只作兜底（本轮 2 层已 0/0，无需兜底）。
- [x] 2 层布线：Freerouting 2.5.0 → SES 导入 → `kicad-cli pcb drc --severity-all` **0 violation / 0 unconnected**（`build/DRC_2l.rpt`；576 track + 62 via，最小线宽 0.2 mm）。
- [x] 去灯后重画：删 D1/Q1–Q3/R13–R21（62→43 器件），无 LED 布置。
- [x] DFM（2 层）：线宽 0.2≥0.127、过孔 0.3/0.6 环宽 0.15、板边 0.3——全部 **PASS**；Gerber/钻孔/坐标/zip 在 `build/gerbers/`（`build/DFM.md` 为 2 层口径）。
- [ ] EMC/ESD、USB-C、充电、电池保护。
- [ ] 外壳公差、卡扣/螺钉、防水/防滑、跌落。
- [ ] 认证评估（CE/FCC/ RoHS）与包装。

## P3 — 红点级

- [ ] CMF：阳极氧化铝/深紫哑光、石墨灰、荧光绿点缀；材质样板。
- [ ] 显示：屏幕 UI 字体/动效/水位动画、26×7 可读性；**不做灯**。
- [ ] 细节：分模线、logo、隐藏螺钉、按键字符；前脸无灯带、无灯缝。
- [ ] 交互：单击看进度、放杯/拿杯事件、提醒节奏、App 视觉。
- [ ] 叙事：场景图、爆炸图、包装、可持续材料说明。
- [ ] 评审：红点申报材料（照片/渲染/说明）。

## P3.5 — 外观变体（2026-11-04 用户新指示）

- [ ] **冻结机械结构与功能**（`square_v1` 12 件；浮动 0.5 / 传力柱 / 过载限位 / PCB / 屏窗 26×7 / 按键 / USB-C / 天线净空）。
- [ ] 内核/外皮拆分：`build_internals()` + `build_skin(params)`，基线不变量 JSON。
- [ ] 功能确认：方形 **21/21 正常**；圆形 LUMEN 为旧概念（光导/LED/0.49" 屏/无按键/Ø102 圆板）→ **不可直接当外观变体**；真圆需重做 PCB（功能变更，另立项）。
- [ ] 外观变体 A：Soft Square（R28–R32）+ 窗 bezel + CMF；先跑通全流程。
- [ ] 外观变体 B/C：Pill/胶囊、Chamfer 双色；每个跑 21 项功能自检 + 外观专项 + 渲染。
- [ ] CMF 扩展（Moss/Sand/Graphite 已有 + 新色）+ 包装适配。
- [ ] 每变体独立复核 + `docs/10`/HANDOFF/README 更新 + commit。

> 详见 `docs/13_Appearance_Variants_Plan.md`；验收/失败模式见 `docs/01` §16。

## 历史：P1 4 层板状态（2026-11-04 前，已过时，仅存档）

- **旧 P1 板：4 层（F/In1/In2/B），0 short / 0 unconnected**；693 track/via；46 项全部是丝印 warning（位号重叠/压铜），电气性 0 error。
- 旧关键简化：先用 **1 颗 RGB LED**（去掉 D2/R22–R24），把 LED 簇放到左臂、Q1–Q3/R19–R21 紧贴 LED；Freerouting 2.5 一次 0 unrouted，导入后仅 6 处 LED pad 未落点，手工补 6 条 2.4–2.7 mm 短线后 **0 unconnected**。**该方案已随去灯决定终止。**
- 丝印 46 项已按项目 DRC severity 设为 ignore（非电气，记录在案）；USB_DP/DM 0.125 mm 为 90Ω 差分，min_track_width 0.125。
- 旧 DRC：0 violations / 0 unconnected（`build/DRC_p1_final.rpt`）。
- 旧制造文件：`build/gerbers/`（F/In1/In2/B + mask/paste/silk/edge）、`.drl`、`.pos`、`smartcoaster_4l_gerbers.zip`。
- 旧 P2 打样就绪：U1 官方 **ESP32-S3-MINI-1** 封装；U1 移到 (29,−32.0) 与机械 (29,+32.0) 对齐；4 层 0 unconnected / 0 short / 0 DRC。
- **DFM 自查（JLC 4 层）**：线宽 0.125≥0.09、过孔 0.3/0.6 环宽 0.15≥0.13、板边 0.3——全部 **PASS**（`build/DFM.md`）。
- BOM 33 行；17 行 passive 缺 MPN（手焊可用值/封装；贴片需补 LCSC 编号）。
- 装配包：`docs/09_Assembly.md` + `build/assembly/top.pdf/bottom.pdf` + `.pos`；拼板建议 2×2 V-groove。
- 修复：U1 的 footprint 引用原为 `REF**`（pos/BOM/装配图识别不到），已在 `gen_pcb.py` 修正并更新板。

## 本轮状态（2026-11-04 收口）

- **机械**：方形 B **12 件**（13→12，删发光件），`verify_v01.py` **21/21**（37 组干涉对 0 干涉、STEP 回读 12 solids、0.5 mm 浮动缝保留）。
- **原理图**：**43 器件 / 28 网络**，ERC 0 error（1 warning：U1 NC 脚）。
- **PCB**：主方案 **2 层**（43 器件、47 footprint）；布线与 DRC 由本轮 Lead 收口，证据落在 `electronics/kicad/build/DRC_2l.rpt`——**未通过前不写 0/0**；Gerber/DFM 以 `build/gerbers/`、`build/DFM.md` 重出后为准。
- **固件**：去灯效后 `idf.py build` + host/mock/差分测试由本轮固件任务收口（计数见 `docs/HANDOFF.md`）。
- **P3**：方形 B 渲染/CMF/包装/提交包已按“无灯、无灯缝”重出（`render/`、`submission/`）；`docs/12_Light_Analysis.md` 标 **OBSOLETE**，仅存档。
- **唯一未闭环（用户侧）**：手板采购/装配/实物标定 + PCB 打样 + 3D 打印。

## 判定

- “能用”：P1 全部勾选 + 手板 7 天数据。
- “红点级”：P1/P2 完成 + P3 的 CMF/显示/细节/叙事达到可送审质量。

## Round 2 记录（2026-11-04）

- 尝试 1：把 R19–R24/Q1–Q3 贴到 D1/D2 旁，重布线 → 12 unconnected 不变，且 D1/R15、Q1/R14 等 courtyard 冲突，回退。
- 尝试 2：给 D2 加本地驱动 Q4–Q6（schematic ERC 0、网表 PASS，69 器件/46 网络）→ 右侧臂放不下 3 颗 SOT-23（越界/与 J5/R25 冲突），PCB 未成，回退。
- 结论：**12 unconnected 是 C 环拓扑问题**——D2 在右前，阴极网必须从左下的 Q1–Q3 绕过整个 C 环；2 层/4 层都在最后一跳失败。
- 下一轮方案：把 D1/D2 都放到同一侧臂（前左），共用 Q1–Q3 本地驱动，再从左侧臂把出光送到屏窗；**该路线因用户决定去灯而终止**。

## P3 进展（2026-11-04）

- CMF：`docs/10_CMF_and_Packaging.md`（Lumen Violet 主色 + Moss/Sand/Graphite 变体）；4 个变体渲染 + 拼图 `render/cmf/CMF_variants.png`。
- 叙事：`docs/11_Product_Narrative.md`（一句话/问题/洞察/设计/体验/可持续/规格）。
- 包装：120×120×36 天地盖 + 纸浆模塑内衬已出 3D/STEP/STL + 3 张渲染（`render/packaging/`）。
- 显示：不做灯；反馈只在 0.91" 128×32 OLED（26×7 可视窗）上呈现。旧发光方案分析存档于 `docs/12_Light_Analysis.md`（OBSOLETE）。

## P3 提交包（2026-11-04）

- `submission/`：4 张主图 + `SmartCoaster_Story.pdf`（A3 300dpi）+ 可复现 `make_story.py`。
- 故事：问题/洞察/设计（重量即输入 + 前脸只有屏窗与按键）/体验/可持续/规格/CMF。
