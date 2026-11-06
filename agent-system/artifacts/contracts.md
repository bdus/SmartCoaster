# 产物契约（Artifacts & Contracts）

> 规则：**下游只读上游契约文件，不猜参数**；图片只做辅助证据，判定必须基于
> JSON/CSV/报告。所有产物路径相对项目根；命名小写下划线 + 版本号。
> 机器可读登记见 `SYSTEM.yaml: artifacts.types`；本文件说明每个阶段的契约。

## 1. 通用规则

| 规则 | 说明 |
|---|---|
| 命名 | `小写_下划线` + `_vNN`；同源的数据产物同名 `.json`，图同名 `.png`；禁止 `final/new/final2` |
| 版本 | 每个产物可追溯到源文件 hash / git commit / 工具版本 |
| 机器可读优先 | 指标、阈值、校验结果必须 JSON/CSV；图只做辅助 |
| 只读契约 | 下游脚本读取契约文件（如 `art.json`/`shell.json`/`manifest.json`），不硬编码猜参数 |
| 不变量 | 契约字段一旦被下游依赖，变更必须同步下游并重跑 |
| 大二进制 | STEP/STL/3MF/blend 可再生成，默认不入 git（`.gitignore`），交付时保留在工作区 |

## 2. 产物类型

| ID | 扩展名 | 机器可读 | 用途 |
|---|---|---|---|
| ART-STEP | `.step` | ✅ | 几何唯一来源/打印尺寸源 |
| ART-STL | `.stl` | ✅ | 打印/渲染几何 |
| ART-3MF | `.3mf` | ✅ | 多材料装配/切片输入 |
| ART-GLB | `.glb` | ✅ | 单文件场景/可视化 |
| ART-PCB | `.kicad_pcb` | ✅ | PCB 原生工程 |
| ART-JSON | `.json` | ✅ | 指标/校验/清单/契约 |
| ART-CSV | `.csv` | ✅ | BOM/坐标/扫描数据 |
| ART-YAML | `.yaml` | ✅ | 参数/阈值/状态 |
| ART-BIN | `.bin` | ✅ | 层网格等二进制契约 |
| ART-INP / ART-MSH / ART-FRD | `.inp/.msh/.frd` | ✅ | CalculiX/Gmsh 输入/网格/结果 |
| ART-GERBER / ART-ZIP | `.gbr/.zip` | ✅ | 制造文件/打包 |
| ART-MD | `.md` | ❌ | 报告/说明/交接 |
| ART-PNG / ART-PDF | `.png/.pdf` | ❌ | 渲染/云图/参考图/图纸 |
| ART-BLEND | `.blend` | ✅ | Blender 场景 |

## 3. 分阶段契约

### 3.1 机械（M0–M3）

| 产物 | 路径（本项目示例） | 关键字段 |
|---|---|---|
| 唯一几何源 | `mechanical/<v>/cad/<model>.py` | 参数表 + `build_assembly()` |
| 零件 | `build/parts/<name>_v01.step|.stl` | 单实体、valid |
| 装配 | `build/assembly/assembly_v01.step|.stl` | 12 solids、bbox |
| 自检 | `build/verify_report.json` | `{ok, checks:[{check, ok, detail}]}` |
| 材质/质量 | `build/assembly/meta.json` | 材质、密度、体积、质量 |
| 渲染 | `build/render/*.png` | 同一版 STL |
| 参数状态 | `config/mechanical_params.yaml` | `status: verified/provisional/tbd` |

### 3.2 电子（E0–E4 + PCB-FAB）

| 产物 | 路径 | 关键字段 |
|---|---|---|
| 唯一电气源 | `electronics/*/scripts/design.py` | 器件 + 网络 |
| 原理图/网表 | `smartcoaster.kicad_sch`、`NETLIST.md`、`BOM.csv` | 43 器件 / 28 网络 |
| ERC | `build/ERC.rpt` | `0 Errors 0 Warnings` |
| PCB | `*.kicad_pcb` | 47 footprint、576 track + 62 via |
| DRC | `build/DRC_2l.rpt` | `0 DRC violations` / `0 unconnected pads` |
| DFM | `build/DFM.md` | 逐项 PASS + 工厂能力 |
| 制造 | `build/gerbers/` + `*.zip` | 9 层 Gerber + drl + pos + gbrjob |
| 第二实现 | `electronics/easyeda/reports/*.json` | 对账 X1–X5 |

### 3.3 固件（F0–F4）

| 产物 | 路径 | 关键字段 |
|---|---|---|
| 固件源 | `firmware/esp32/main/*` | 分层 + HAL |
| 参考模型 | `firmware/model/*.py` | Python 基线 |
| 构建 | `firmware/esp32/build/smartcoaster.bin` | 519,184 B |
| 测试 | `firmware/REPORT.md` | 11/11 + 9/9 + 16/16 + 16 |

### 3.4 仿真（S1–S4）

| 产物 | 路径 | 关键字段 |
|---|---|---|
| FEA 输入/网格/结果 | `simulation/mechanical/<case>/{*.inp,*.msh,*.frd}` | 单元类型/节点/边界/载荷 |
| FEA 指标 | `results*.json` | `results`, `regions`, `mesh`, `load`, `clamp` |
| SPICE 结果 | `simulation/electronics/results/*.json` | `{module, analysis, inputs, metrics, thresholds, pass, notes}` |
| 汇总 | `s2_summary.json` | `{n_results, n_pass, n_fail, honesty_boundary}` |
| 统一契约 | 任意仿真工具 | `{tool, status, inputs, artifacts, metrics, warnings, duration_s}` |

### 3.5 外观 / IP 印花（A/P3.5/P3.6）

| 产物 | 路径 | 关键字段 |
|---|---|---|
| 素材契约 | `appearance/build/art/<art>/art.json` | 画幅/像素/层高/层数/色板/厚度/直径/sha256 |
| 层网格 | `.../layer_counts.bin` | uint16 LE、行优先、0=透明、1..N=层数 |
| 印花几何 | `appearance/build/print/<art>/manifest.json` | 逐耗材 STL+hex/bbox/三角面/厚度/sha256 |
| 外壳开槽 | `appearance/build/shell/shell.json` | rim/floor/槽径/槽深/厚度/变换/校验 |
| 装配 3MF | `appearance/build/3mf/validation.json` | 对象/component/材料/Z 范围/bbox |
| 打印交付 | `render/print/stl/<v>/{manifest.json,layout.json,CHECKSUMS.sha256}` | 零件/耗材/方向/支撑/床面/校验 |
| 验收 | `appearance/build/ACCEPTANCE.{json,md}` | 129 项分组结果 |

### 3.6 验证 / 集成（V/I）

| 产物 | 路径 | 关键字段 |
|---|---|---|
| 独立验收 | `docs/VERIFY_REPORT.md` | 基线 commit/时间戳/逐项 PASS |
| 审计 | `docs/AUDIT_*.md` | PASS/PARTIAL/GAP/SUPERSEDED/N-A 统计 |
| 风险登记 | `docs/REPORT_技术报告.md` §7 | R1–R19 |
| 任务板 | `TASK_BOARD.md` | owner/scope/依赖/状态/证据 |
| 交接 | `docs/HANDOFF.md` | 状态/根因/命令/剩余项/红线 |

## 4. 必须机器可读 vs 可以图片

| 必须 JSON/CSV（判定依据） | 可以图片（辅助） |
|---|---|
| 机械自检逐项结果 | 装配截图/爆炸图 |
| ERC/DRC/DFM 报告 | PCB 布线预览 |
| 固件测试计数 | UI 屏幕图 |
| FEA 指标/SPICE 阈值与结果 | 应力云图/曲线图 |
| 印花 bbox/厚度/三角面/sha256 | 渲染图/微距图 |
| 3MF 回读/床面排版 | 打印参考图 |
| 验收/审计结果 | 提交包照片 |

## 5. 反模式（不要把图当证据）

- 只给渲染图就说"外观通过"（必须配不变量 diff + 功能自检）。
- 只给 DRC 截图就说"0/0"（必须给 `.rpt` 原文与时间戳）。
- 只给测试总数就说"全绿"（必须给分组与阈值）。
- 契约文件用自由文本（下游无法解析）。
