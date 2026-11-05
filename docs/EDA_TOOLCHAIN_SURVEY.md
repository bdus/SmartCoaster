# 其他 EDA 工具技术栈调研（供「用 EasyEDA 重做电路/PCB」决策）

> **日期**：2026-11-05 ｜ **作者**：调研子代理 ｜ **状态**：调研稿（未做任何工程改动）
> **目的**：回答三件事——① 除 KiCad 外还有哪些 EDA 技术栈；② 它们的脚本/Agent 接口能否离线、headless 地生成与校验；③ SmartCoaster 要不要、以及怎样切到 EasyEDA Pro。
> **范围**：主流 EDA 文件格式、数据模型、脚本能力、许可、生态、AI 入口；重点核查 EasyEDA Pro 客户端的离线能力与 eprj3 路线。
> **红线（本文件所有结论都受其约束）**：只用本地/免费工具；不把项目文件上传第三方；不虚构版本与能力。

## 证据等级（全文标注口径）

| 标注 | 含义 | 例子 |
|---|---|---|
| **实测** | 本机命令输出，或本次抓取到的官方页面原文（附 URL 与抓取日期） | `kicad-cli version` → 9.0.9；官方 FAQ 原文 |
| **文档** | 官方文档/README 的声明，未在本机复现 | 客户端「半离线模式」说明 |
| **仓库自述** | easyeda-agent 仓库自身的实测记录（二手证据，可能过时） | `docs/ecosystem-survey.md`、`docs/upstream-issues.md` |
| **推测** | 由上述证据推断，未直接证实 | 「3.2.209 可能打不开 eprj3」 |
| **待验证** | 现有证据不足，必须实机确认 | Linux headless 能否跑客户端 |

---

## 0. 结论速览

| 候选 | 离线生成工程 | headless ERC/DRC | 免费/开源 | 对本项目一句话结论 |
|---|---|---|---|---|
| **KiCad 9 / 10** | ✅ 纯文本工程 | ✅ `kicad-cli` | ✅ GPL，本机已装 | **保留为主链**，没有换掉的技术理由 |
| **EasyEDA Pro + eprj3 1.x** | ✅ 官方 Skill 离线写文件 | ❌ 需客户端打开 | ✅ 客户端免费 | **值得做第二实现**（B1 路线） |
| **EasyEDA Pro + lceda-pro CLI 4.1.x** | ✅/半自动 | ✅ `--headless`（待验证） | ✅ 客户端免费 | **值得小规模验证**（B2 路线），可能是最优 EasyEDA 路线 |
| **easyeda-agent live（Web 版）** | ⚠️ 需登录、工程在云端 | ❌ 依赖 GUI 窗口 | ✅ 工具开源 | **与红线冲突**，不推荐做主路线 |
| **Altium Designer** | ❌ 商业授权 | ❌ 脚本跑在 GUI 内 | ❌ 订阅制 | 不投入 |
| **Cadence Allegro / OrCAD** | ❌ 商业授权 | ⚠️ SKILL 可批处理但需授权 | ❌ | 不投入 |
| **Siemens Xpedition** | ❌ 商业授权 | ❌ | ❌ | 不投入 |
| **Horizon EDA** | ✅ 文本 + Python | ⚠️ 有 CLI，DRC 入口在 Python | ✅ GPL | 观望，不作主线 |
| **LibrePCB** | ✅ 文本 `.lp` | ✅ `librepcb-cli` | ✅ GPL | 备选，生态弱于 KiCad |
| **gEDA / Lepton** | ✅ 文本 | ⚠️ Scheme 脚本 | ✅ GPL | 停滞项目，不投入 |
| **tscircuit / Circuit JSON** | ✅ TS/Circuit JSON | ✅ CLI | ✅ MIT | 观望，适合「电路即代码」实验，不适合本版交付 |

---

## 1. 现状基线与本机事实

### 1.1 项目现有 KiCad 链路（实测）

```text
$ kicad-cli version          → 9.0.9        （本机 /data/Documents/tools/kicad）
electronics/kicad/build/ERC.rpt  → ERC messages: 0  Errors 0  Warnings 0
electronics/kicad/build/DRC_2l.rpt → 0 violation / 0 unconnected
```

- 原理图 **43 器件 / 28 网络**、2 层 PCB **0 DRC / 0 unconnected**、Gerber/DFM 均已产出（`docs/HANDOFF.md` §3）。
- **关键结构性事实（实测）**：`electronics/kicad/scripts/design.py` 只有 **263 行**，是原理图/网表唯一来源；`gen_sch.py`（370 行）/`gen_pcb.py`（321 行）是它的两个后端。
  → **换 EDA 的本质不是「格式转换」，而是「再写一个后端」**。这大幅降低迁移成本，也意味着不该走「导入向导」路线。
- **关键缺口（实测）**：`electronics/kicad/BOM.csv` 只有 8 列（Item/Qty/Refs/Value/MPN/Footprint/Description/Note），**没有 LCSC C 号**；`design.py` 里 `lcsc` 命中数 = 0。
  → EasyEDA 最大的卖点（立创商城/LCSC 直通）在本项目**目前是空账**，要先补 43 个器件的供应商编号才有价值。

### 1.2 本机 EasyEDA 侧现状（实测）

| 项 | 状态 |
|---|---|
| `tools/easyeda-agent/` | 已 clone，`package.json` version **1.13.1**，含 `docs/ecosystem-survey.md`（795 行）等 |
| `tools/easyeda-pro/` | **空目录**，未发现客户端二进制 |
| 全盘 `*.eext` | 未发现（连接器未安装） |
| `/usr/local/bin/easyeda` | 未安装（CLI/daemon 未部署） |
| `lceda-pro` / `easyeda` 在 PATH、Flatpak 列表 | 均无命中（`command -v` + `flatpak list` 实测） |

→ **本机没有 EasyEDA 客户端**，下文所有「客户端行为」都不是本机实测，只能标 **文档/仓库自述/待验证**。这一点必须写进决策前提。

---

## 2. 主流 EDA 技术栈对比

### 2.1 总表

| 工具 | 文件格式 / 数据模型 | 脚本/扩展机制 | 命令行 / headless | 开源与许可 | 库与供应链 | AI Agent 入口 |
|---|---|---|---|---|---|---|
| **KiCad 9/10** | S-expression 文本（`.kicad_sch`/`.kicad_pcb`/`.kicad_pro`），Git 友好 | `pcbnew`/`eeschema` Python（SWIG）、IPC API（kipy）、Action Plugin | ✅ `kicad-cli`（sch erc / pcb drc / 全套导出） | ✅ GPLv3+ | 官方库 + 第三方；**无 LCSC 号** | 一级：CLI + Python + 文本 diff |
| **EasyEDA Pro** | 闭源；在线为云工程（epro），离线为 `.eprj`（单文件）或 `.eprj3`（文件夹：JSON 索引 + `.esch2`/`.epcb2` 文本容器） | 官方 `eda.*` JS API（0.2.63 类型时点 86 个命名空间）、`.eext` 扩展、`lceda-pro` 内置 CLI | ⚠️ 需运行编辑器；4.1.60+ 支持 `open --headless` | ❌ 闭源，客户端免费 | ✅ LCSC C 号 / 立创库 / 嘉立创下单 | 二级：官方 CLI+API、easyeda-agent、eprj3 生成 |
| **Altium Designer** | `.SchDoc`/`.PcbDoc` 为 OLE 复合二进制（可另存 ASCII） | DelphiScript（默认）/VBScript/JScript、X2 Object Model、Altium 365 REST API | ❌ 脚本在 GUI 内跑；无官方 headless | ❌ 商业订阅 | 厂商库 + 365 生态 | 弱：需 Windows + 授权 + GUI |
| **Cadence Allegro/OrCAD** | `.brd`/`.dsn` 二进制私有格式 | SKILL（Lisp 方言）+ Allegro PCB Editor API | ⚠️ 可 batch，但需授权与 Windows/Linux 商业环境 | ❌ 商业 | 厂商库 | 弱：SKILL 学习/授权成本高 |
| **Siemens Xpedition** | 私有二进制工程库 | COM/自动化接口、第三方 Python 包装 | ❌ 无免费 headless | ❌ 商业（企业级） | 厂商库 | 弱：不适用本项目 |
| **Horizon EDA** | 文本 JSON + YAML pool（`pool.json` + SQLite 索引） | ✅ Python 模块（`import horizon`）、参数化 part program | ✅ `horizon-imp/pool/prj`；DRC 走 Python `run_checks` | ✅ GPLv3 | 自建 pool，无供应链 | 中：Python 可编排，但生态小 |
| **LibrePCB** | 文本 `.lp`（S-expression 风格）+ `.lplib` 库 | 无通用脚本 API；以 CLI/输出作业为主 | ✅ `librepcb-cli`（ERC/DRC/Gerber，官方 Docker） | ✅ GPLv3 | 官方库 + 自建 | 中：CLI 适合 CI，扩展性弱 |
| **gEDA / Lepton EDA** | 文本（`.sch`/`.pcb`），gEDA 用 Scheme 脚本 | Scheme (guile) | ⚠️ `gnetlist`/`pcb` 命令 | ✅ GPL | 老库，维护停滞 | 低 |
| **Fritzing** | `.fzz`（zip + XML） | 无正式脚本 API | ❌ | ⚠️ 开源但许可需核实（GitHub 显示 NOASSERTION） | 面包板/教学库 | 低：教学玩具定位 |
| **tscircuit** | TypeScript/React 组件 → **Circuit JSON** | npm 包 + CLI（`tsci`） | ✅ 本地 CLI，可导出 KiCad/Gerber/STEP/SPICE | ✅ MIT | 可导入 JLCPCB/KiCad 库 | 高：天然「电路即代码」，但项目年轻 |

### 2.2 开源阵营要点

- **KiCad 10**：2026-03-20 发布 10.0.0（[官方博客](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)）；新增 Allegro/PADS/gEDA 导入器、图形化 DRC 规则编辑器、变体（Variants）。GitHub 镜像最新 **10.0.7**（2026-10-16，GitHub API 实测）。CLI 文档：<https://docs.kicad.org/10.0/en/cli/cli.html>。
- **Horizon EDA**：最新 **v2.7.2**（2025-12-05，GitHub API 实测）；Python 模块能开工程、导出 PDF/BOM/Gerber/STEP 并 `run_checks`（[文档](https://docs.horizon-eda.org/en/stable/python.html)），但 CLI 依赖 `HORIZON_POOL` 环境变量、偏开发者工具（[CLI 文档](https://docs.horizon-eda.org/en/stable/cli-usage.html)）。
- **LibrePCB**：最新 **2.1.1**（2026-06-12，GitHub API 实测）；官方明确以 `librepcb-cli` 做 headless ERC/DRC + Gerber，并提供 CI Docker 镜像（[CLI 说明](https://librepcb.org/_branches/release-2_1_1/features/cli/)）。**这是「开源 + 真 headless」最干净的一个**，但库/生态远小于 KiCad。
- **gEDA/Lepton**：Lepton 最新 **1.9.18**（2022-05-29，GitHub API 实测），已长期停滞；KiCad 10 反而提供 gEDA/Lepton 导入器，说明其定位已变成「历史格式」。
- **Fritzing**：仓库仍在更新（2026-08 有提交），但定位是教学/面包板，`.fzz` 不适合工程项目；许可证在 GitHub 显示为 `NOASSERTION`，**具体条款待核实**。

### 2.3 商业阵营要点

- **Altium**：默认脚本语言 **DelphiScript**，也支持 VBScript/JScript；脚本存于 `*.PrjScr`，在 GUI 内运行/调试，通过 X2 Object Model 操作文档（[官方文档，2026-11-02 更新](https://www.altium.com/documentation/altium-designer/scripting)）。**没有官方 headless CLI**；Altium 365 提供的是云端 REST API（[Altium 365 API](https://www.altium.com/documentation/altium-developer-center/altium-365/api)），与「本地离线」相悖。
- **Cadence**：Allegro/OrCAD 的自动化语言是 **SKILL**（Lisp 方言，[Wikipedia](https://en.wikipedia.org/wiki/SKILL)），可在 PCB Editor 内批处理，但必须持有商业授权；官方文档站对本机抓取返回 403，**具体 API 细节未核实（待验证）**。
- **Siemens Xpedition**：企业级私有工程库，自动化靠 COM/厂商 API；社区存在第三方 Python 包装（如 [SiemensEDA_Python_Interface](https://github.com/jabijker/SiemensEDA_Python_Interface)），但**无免费/离线路径**。

> 商业三家的共同结论：**授权费 + Windows/GUI + 私有二进制**，与「本地/免费/可 diff/可 CI」四条全部冲突。除非客户强制要求交付 Altium 源文件，否则不进入候选。

### 2.4 云 / 新范式

- **EasyEDA Pro**：闭源但免费；在线版工程在云端，离线版工程在本地（`.eprj`/`.eprj3`）。官方 API 是 `eda.*` JS 命名空间 + `.eext` 扩展；客户端 4.1.60+ 内置 `lceda-pro` CLI。详见 §5。
- **tscircuit**：MIT，用 TypeScript/React 写电路，产物是 **Circuit JSON**，CLI 可导出 KiCad/Gerber/STEP/SPICE，并能导入 JLCPCB/KiCad 库（[官方文档](https://docs.tscircuit.com/)）。**它是「AI 原生」程度最高的**，但版本号仍是 `v0.0.3095`（2026-11-05，GitHub API 实测），工程成熟度不足以承接本项目的交付责任。

---

## 3. AI / Agent 可编程接口横评

### 3.1 KiCad：目前最完整的「离线可编程」栈

| 入口 | 能力 | 证据 |
|---|---|---|
| `kicad-cli sch erc` / `pcb drc` | headless ERC/DRC；DRC 支持 `--format json`、`--severity-all`、`--exit-code-violations`（有违规时退出码 5） | **文档**：[CLI 手册](https://docs.kicad.org/10.0/en/cli/cli.html) |
| `kicad-cli pcb export ...` | Gerber/钻孔/坐标/IPC-2581/ODB++/STEP/PDF/SVG 等全套 | 同上 |
| `kicad-cli fp upgrade` | 可读 **Altium `.PcbLib`/`.IntLib`、EAGLE `.lbr`、EasyEDA 标准版 `.json`、EasyEDA Pro `.elibz`/`.epro`/`.zip`** | 同上（**这是 EasyEDA→KiCad 的反向通道**） |
| `pcbnew` / `eeschema` Python | 直接建板、放封装、赋网、存盘（本项目已在用） | **实测**：`design.py`/`gen_pcb.py` 的既有管线 |
| IPC API（`kipy`） | KiCad 9+ 的进程间 API，可驱动运行中的编辑器 | **文档**（本机未装 `kipy`） |
| `skidl` | 用 Python 描述网表，输出 KiCad 网表 | **实测**：PyPI/GitHub 最新 **3.0.0**（2026-10-16，GitHub API） |
| `kicad-skip` | 直接改 `.kicad_sch`/`.kicad_pcb` 的 S-expression | **实测**：最新 **v0.2.5**（2024-02-16，已两年未更新） |

**已知坑（仓库自述，2026-08-01）**：`pcbnew` 的 SWIG 绑定几乎没有生命周期保护——footprint 未 `board.Add()` 就 `Flip()` 会 **SIGSEGV、退出码 139、无 traceback**；KiCad 10 的 `Flip()` 第二参已从 bool 改为 `FLIP_DIRECTION` 枚举，旧脚本会静默漂移（`tools/easyeda-agent/docs/ecosystem-survey.md` §9.4）。本项目脚本简单，尚未踩到，但**换大版本时必须回归**。

**结论**：KiCad 侧的「生成 + 校验 + 制造输出」三件事都能在无 GUI、无网络下完成，且**退出码可门禁**。这是它相对 EasyEDA 的结构性优势。

### 3.2 EasyEDA Pro：一个平台，三条自动化路线

| 路线 | 机制 | 是否离线 | 是否 headless | 证据等级 |
|---|---|---|---|---|
| **L1 在线 Web + easyeda-agent** | 浏览器打开 `pro.lceda.cn/editor` → `.eext` 连接器 → WebSocket → daemon → `eda.*` | ❌ 需登录、工程在云 | ❌ 必须有活 GUI 窗口 | 仓库自述 + 文档 |
| **L2 eprj3 离线文件生成** | 官方 `easyeda-eprj3-skill` 用 Node 直接写 `.eprj3` 文件夹 | ✅ 纯离线写文件 | ✅ 生成阶段无编辑器 | 官方 README + 仓库自述 |
| **L3 客户端 + `lceda-pro` CLI** | 客户端 4.1.60+ 内置 CLI，`open --headless` → `invoke` 执行任意 `eda.*` JS | ✅ 半离线/全离线模式 | ✅ 文档明确支持 `--headless` | **文档**（本机未装，待验证） |

**L2 的关键细节（官方 README，v2.2.1）**：

- **1.x 是纯离线生成器**：零 npm 依赖，生成原理图（布局+连线+电源符号）+ PCB **仅放置**（封装、pad↔net、板框），**不布线、不铺铜**；已冻结在 **v1.36.1**。
- **2.x 改为「客户端做它该做的」**：要求客户端 **V4.1.94+**，通过隐藏模式（`--owner`）调客户端自己的库搜索、符号放置、SCH→PCB 更新、自动布局/布线、原理图 DRC、铺铜、网表导出与截图。
- 五道门（format/ERC/layout lint/DRC+DFM/design intent）是**生成器自检**，不是宿主的 ERC/DRC 结论。

**L3 的关键细节（官方文档，2026-11-05 抓取）**：

- `lceda-pro` 与 GUI 是**同一个可执行文件**，版本 **V4.1.60+** 起内置；`doctor` 探测端点。
- `open --path x.eprj3` 打开工程并返回 session id；**`.eprj3` 文件夹工程与编辑器双向同步**（磁盘改动自动重载、编辑器保存自动落盘）；`--headless` 表示**无可见窗口的隐藏渲染**。
- `invoke --ext-uuid eda` 在编辑器内执行任意 JS；另有 `--mcp stdio|http` 可**直接作为 MCP server**。
- **原文明确**：「命令行客户端要求使用客户端版本的嘉立创 EDA 专业版，浏览器/在线版本不支持本文档描述的会话与桥接功能」。

→ 这条 L3 是本次调研**最重要的新信息**：EasyEDA 已经有官方、可脚本、可 headless、可离线的入口，不再只有「必须开窗口点按钮」这一条路。但要用它，**必须装 4.1.x 客户端，而不是 3.2.209**。

**EasyEDA API 的已知边界（仓库自述，标注日期）**：

- 原理图 DRC 只返回聚合布尔，拿不到逐条明细（issue #27，2026-08-22 仍 open；官方称 EDA v4.2 会支持，但 web 通道未部署）。
- PCB DRC 在 3.2.148 上能返回嵌套明细 `{count, list:[...]}`（仓库自述），`pcb_Drc.check` 可用。
- `pcb_Document.autoRouting` 在 3.2.x 是 `undefined`，Web **4.1.78** 上已可用（仓库自述，2026-10-17）；**能力随版本漂移，必须按当前 build probe**。
- 官方 API 类型包 `@jlceda/pro-api-types` 最新 **0.4.27**（npm，2026-10-16 实测）；仓库调研基于 0.2.63，命名空间数量（86 个）**需按 0.4.27 复核**。

### 3.3 商业 EDA 的脚本接口

- **Altium**：DelphiScript 默认、VBScript/JScript 需开 `Legacy.Scripts.SupportOldLanguages`；脚本项目 `*.PrjScr`，在 GUI 内 `File » Run Script` 执行。**没有官方 CLI/headless**；所谓「自动化」= 在已授权、已登录的 Windows GUI 里跑脚本。
- **Cadence**：SKILL 可在 Allegro PCB Editor 内做批量操作，但 API 文档需授权账号，**本机无法核实具体方法（待验证）**；无免费授权即无法自动化。
- **Siemens**：企业级，无免费路径。

→ 三家的共同点：**自动化能力与 license 绑定**。对「本地/免费」红线是硬冲突，本文件不再展开。

### 3.4 其它可编程栈

- **Horizon EDA**：Python 能开工程、跑 `run_checks(rules, ids)`、导出 Gerber/STEP/PNG，适合做「研究型」自动化；但 pool 是 YAML+SQLite、无供应链，学习成本高。
- **LibrePCB**：`librepcb-cli` 是**真正为 CI 设计**的（ERC/DRC/Gerber + Docker 镜像），但库生态与封装覆盖不足以承接 43 器件项目。
- **tscircuit / Circuit JSON**：最适合「让 LLM 直接写电路」的范式，CLI 可导出 KiCad/Gerber，但版本年轻、库覆盖未知，**本版不作为交付链**。
- **IPC-2581 / ODB++**：是「制造数据交换」层，不是「可编辑工程」层；EasyEDA 与 KiCad 都能导出 ODB++/IPC-2581，可作为**跨工具验收的中间格式**（本机 `kicad-cli` 已支持）。

### 3.5 横评（按「Agent 友好度」排序）

| 维度 | KiCad | EasyEDA L2 (eprj3) | EasyEDA L3 (lceda-pro) | EasyEDA L1 (Web) | Altium/Cadence |
|---|---|---|---|---|---|
| 无 GUI 生成 | ✅ | ✅ | ⚠️ 需启动客户端进程 | ❌ | ❌ |
| 无 GUI 校验（ERC/DRC） | ✅ | ❌（只有生成器自检） | ✅（`--headless`，待验证） | ❌ | ❌ |
| 无网络 | ✅ | ✅ | ✅（离线模式） | ❌ | ⚠️ 需激活 |
| 工程可 diff | ✅ 文本 | ✅ 文本容器 | ✅ 文件夹 | ❌ 云 | ⚠️ ASCII 另存 |
| 供应链 | ❌ | ⚠️ 需手工映射 | ✅ LCSC | ✅ LCSC | ✅ 厂商库 |
| 退出码/CI 门禁 | ✅ | ⚠️ 自定义 | ⚠️ JSON `ok` 字段 | ❌ | ❌ |

---

## 4. 关键判断：每个候选值不值得投入

| 候选 | 离线生成工程 | headless 校验 | 元件库从哪来 | JLC/LCSC 耦合 | 迁移成本 | 结论 |
|---|---|---|---|---|---|---|
| **KiCad 9/10** | ✅ 已有 | ✅ 已有 0/0 证据 | 官方库 + 自建 | 无（DFM 自查替代） | 0 | **保留主链** |
| **EasyEDA eprj3 1.x** | ✅ | ❌ | Skill 内置 21 符号/9 封装（仓库自述）+ 自建 | 中（可手填 C 号） | 中：写 eprj3 后端 + 43 器件符号/封装 | **值得做第二实现** |
| **EasyEDA 客户端 4.1.x + CLI** | ✅ | ✅（待验证 Linux） | 客户端库/立创库 | 高（可在线搜 C 号） | 中 | **值得做小规模验证** |
| **easyeda-agent Web** | ⚠️ | ❌ | 立创在线库 | 高 | 中 | **不推荐**（云端 + GUI） |
| **Altium** | ❌ | ❌ | 厂商库 | 低 | 高（授权/Windows） | 不投入 |
| **Cadence/Siemens** | ❌ | ⚠️ | 厂商库 | 低 | 极高 | 不投入 |
| **Horizon** | ✅ | ⚠️ Python | 自建 pool | 无 | 很高（重画库） | 观望 |
| **LibrePCB** | ✅ | ✅ CLI | 官方库 | 无 | 高（库覆盖不足） | 备选，不作主线 |
| **tscircuit** | ✅ | ✅ CLI | JLCPCB/KiCad 导入 | 中 | 高（重写电路为 TS） | 观望 |

**五条硬判断**：

1. **不要为了「换工具」而换**。当前 KiCad 链已拿到 ERC 0/0、DRC 0/0、Gerber/DFM 全 PASS；EasyEDA 重做若不能带来「LCSC 直通 + 嘉立创下单 + 中文生态」之外的增量，就是净亏损。
2. **EasyEDA 的价值点只有一个**：43 个器件 → LCSC C 号 → 立创库 → 一键下单/SMT。而本项目 BOM **没有 C 号**，这个价值目前是 0，必须先补映射才谈得上收益。
3. **技术可行性已不是问题**：eprj3 离线生成（L2）+ 客户端 `--headless` 校验（L3）理论上能构成「本地、免登录、可脚本」的闭环；**缺的是本机实测**。
4. **红线直接排除 L1**：Web 版工程在云端、需登录，等于把项目文件交给第三方。即使 easyeda-agent 本身开源，也不改变数据去向。
5. **迁移成本被低估的部分是库，不是格式**：43 器件要重新绑定符号/封装（尤其 HY928D、ESP32-S3-MINI-1、OLED 模组、USB-C），eprj3 Skill 自带库远不够；这部分是**人工+核对**成本，不是脚本能消掉的。

---

## 5. EasyEDA 特有问题的事实核查

> 核查时间：2026-11-05。**本机未安装客户端**，除特别注明外均为官方文档原文。

### 5.1 客户端版本：3.2.209 存在，但已不是当前版

| 命题 | 核查结果 | 证据 | 等级 |
|---|---|---|---|
| Linux 客户端 3.2.209 存在 | ✅ 有 `lceda-pro-linux-x64-3.2.209.zip`、`lceda-pro-linux_3.2.209_amd64.deb` 等 4 架构 | [客户端历史版本](https://prodocs.lceda.cn/cn/faq/client-version/) | **实测**（页面抓取） |
| 3.2.209 是当前版 | ❌ 当前下载页是 **4.1.97**（Win/Linux/macOS，含 arm64/loong64/sw64） | [下载页](https://lceda.cn/page/download) | **实测** |
| 3.2.209 有官方 CLI | ⚠️ 官方 CLI 要求 **V4.1.60+**，按版本推断 3.2.209 **不具备**（未实机确认） | [命令行客户端](https://prodocs.easyeda.com/cn/api/guide/cli.html) | **文档 + 推测** |
| 3.2.209 能打开 eprj3 | **待验证**；eprj3 Skill 2.x 要求 V4.1.94+，仓库称打开需 V4.1+ 客户端 | [eprj3 Skill README](https://github.com/easyeda/easyeda-eprj3-skill)（v2.2.1） | 文档 + 待验证 |

**结论**：如果决定走 EasyEDA，**应直接装 4.1.97（或 ≥4.1.94）**，3.2.209 只能作为「eprj3 1.x 离线生成 + 手工打开」的降级方案。

### 5.2 离线/半离线：三种模式 + 激活文件（官方文档）

官方 FAQ 原文（[客户端常见问题](https://prodocs.lceda.cn/cn/faq/client/index.html)）：

- **全在线**：需登录，库/工程在云端，支持协作与自动备份。
- **半离线**：**不需要登录**，库/工程在本地，**可用云端系统库**（即仍需联网取库）。
- **全离线**：**不需要登录**，库/工程全本地，**不能用云端系统库**，内置 **1w+ 常用系统库**。
- **激活文件**：免费下载，首次打开客户端导入或粘贴内容；激活文件存于 `Documents/LCEDA-Pro/lceda-pro-activation.txt`，删除即取消激活。
- **库搜索限制**：半离线/全离线本地库**只支持模糊搜索，不支持多条件搜索**，建议关键词 ≥3 字符。

→ **「3.2.209 能否离线/半离线运行」答案是肯定的（文档层面）**：激活文件是本地文件，FAQ 未提及与账号绑定（具体条款待核）；半离线/全离线均免登录。真正限制是**云端库不可用/搜索弱**，以及**下单必须在线模式**（FAQ：「客户端模式是离线模式的，不支持在线下单」）。

### 5.3 Web 版是否强制登录

- 官方 FAQ 在「如何进入专业版网页版」中写：「专业版网址，使用谷歌或火狐浏览器登录」（同页）。
- 网页版编辑器入口 `pro.lceda.cn/editor` 属于云端工作区，工程存云。
- **结论**：Web 版**需要登录**（文档），且数据在云端（与红线冲突）。**未在本机浏览器实测登录墙**，标 **文档**。

### 5.4 eprj3 文件夹工程 vs 在线工程

| 概念 | 说明 | 证据 |
|---|---|---|
| `.eprj` | 离线/半离线模式的**单文件**工程 | [客户端 FAQ](https://prodocs.lceda.cn/cn/faq/client/index.html) |
| `.eprj3` | **文件夹**工程：JSON 索引 + `.esch2`/`.epcb2` 文本容器；与编辑器**双向同步** | 官方 CLI 文档 + eprj3 Skill README |
| 在线工程（epro） | 云端工程；可「文件 → 另存为本地」得到 epro 包，再导入离线客户端 | FAQ |
| 转换方向 | 在线 → 离线：另存为 epro → 导入；离线 → 在线：epro 压缩包导入 | FAQ |

- **注意**：`docs/concepts.md`（仓库自述）记录，2026-10-13 在 Web 4.1.71 上把 `.eprj3` 文件夹**直接打 ZIP 交给 `project import` 不被接受**；需重新封装为 `project2.json` + 单个 `.epru` 才能导入，且导入后官方 blink 样例报 Netlist Error（源文件 SCH 导线无网名、PCB 网络另写）。→ **eprj3 的「能生成」不等于「能导入 Web」**；L3 客户端路线才是正解。
- 另一条仓库实测：Web 4.1.60 的 SCH_PAGE 源码**不含内嵌 SYMBOL/DEVICE/FOOTPRINT 容器**，只是当前页记录；且文件坐标 Y=-410 与 API 回读 Y=+410 相反。→ **不要把 document source 当成自含工程包**。

### 5.5 官方支持导入 KiCad / Altium 的范围

| 来源 | 官方说法 | 证据 | 等级 |
|---|---|---|---|
| **KiCad** | 仅支持导入 **KiCad 5.1 和 5.9** 格式；更低版本先另存 5.1 再打包；必须用 KiCad 自带「压缩」打包（含所用库）；PCB 导入后**自动重建铺铜，结果会有差异** | [导入 KiCad](https://prodocs.lceda.cn/cn/import-export/import-kicad/) | **实测**（页面原文） |
| **Altium** | 基于 **Altium 17** 格式兼容；需在 AD 中另存为 **ASCII** 的 `.SchDoc`/`.PcbDoc` 再打 zip；图元有差异，「不承担任何因格式转换差异产生的损失」；库文件加密，不能直接导入提取 | [导入 Altium](https://prodocs.lceda.cn/cn/import-export/import-altium-designer/) | **实测**（页面原文） |
| **KiCad 9/10 工程** | 文档**未提及**；按「5.1/5.9」表述推断**不能直接导入** | 同上 | **推测/待验证** |

→ 对本项目：现有工程是 **KiCad 9 格式**（`kicad_sch` 新语法），走官方导入大概率失败；**正确做法是用 `design.py` 的 canonical 数据直接生成 eprj3**，绕开导入器。这也是「不该做格式转换」判断的直接依据。

### 5.6 官方 `lceda-pro` CLI（新增能力，2026 文档）

- 内置版本要求：**V4.1.60+**；只支持**客户端**，浏览器/在线版不支持。
- 命令面：`open`（`--path` / `--headless`）、`session.*`、`invoke --ext-uuid eda`、`doc/api/format` 查询、`--mcp stdio|http`。
- 语义：`open --headless` 是**隐藏窗口渲染**，不是无进程；仍需一个运行中的编辑器进程（`doctor` 的 `connected` 字段）。
- **这意味着**：EasyEDA 侧首次出现「官方、本地、JSON 返回、可 MCP」的自动化面，且能直接读写 `.eprj3`。

### 5.7 「官方文档」vs「easyeda-agent 仓库自述」对照

| 主题 | 官方文档 | 仓库自述 | 判读 |
|---|---|---|---|
| 客户端离线 | 三模式 + 激活文件，免登录 | 「必须有活 GUI 窗口」（2026-08 时点） | 仓库结论**已被官方 CLI 部分推翻**（4.1.60+ 有 headless） |
| 原理图 DRC 明细 | 未承诺 | 只返回 boolean（#27） | 以仓库实测为准，标「版本相关」 |
| 自动布线 | 未单列 | 3.2.x 不可用；Web 4.1.78 可用 | 版本相关，必须 probe |
| eprj3 | 官方 Skill 可离线生成；客户端可双向同步 | 「能生成≠能导入 Web/≠有 DRC」 | 两者不矛盾：**生成与验收是两层** |
| 库 | 离线库模糊搜索、全离线 1w+ | 立创库 API 可搜 C 号（需在线） | 离线场景下 C 号搜索不可用 |

---

## 6. 对本项目的建议路线

### 6.1 三条路线

| | **A：EasyEDA 在线 + easyeda-agent live** | **B：eprj3 离线生成 + 客户端验证** | **C：KiCad 主链 + EasyEDA 第二实现** |
|---|---|---|---|
| 做法 | Web 4.1.x 登录 → 装 `.eext` → daemon/CLI 驱动 | `design.py` → eprj3 生成器 → 4.1.97 客户端打开/`--headless` 跑 DRC | 保留现有 KiCad 交付；另写 eprj3 导出器做对照 |
| 前置条件 | 账号、联网、工程上传云端、开启「允许外部交互」 | 装 4.1.97 Linux、激活文件、43 器件符号/封装、eprj3 格式库 | 仅需 eprj3 生成器 + 可选的客户端截图 |
| 能证明 | 编辑器里对象/网络正确；可跑平台 DRC | 工程可打开、SCH/PCB 可回读、可跑客户端 DRC/布线 | 两套工具网表一致；EasyEDA 工程可作为交付物 |
| 不能证明 | 离线可用；数据不外流 | 生成器自检 ≠ 宿主 DRC；铺铜需客户端重算 | EasyEDA 侧 DRC/Gerber 未验证 |
| 主要风险 | **违反红线**（云端上传）；GUI 依赖；版本漂移 | Linux headless/GPU 兼容性（待验证）；库映射工作量大 | 双份维护；易出现「两套网表漂移」 |
| 成本 | 低（工具现成） | 中（2–4 人日 + 库核对） | 低–中（1–2 人日） |
| 结论 | **不推荐** | **推荐做验证（B1 生成 → B2 headless 校验）** | **推荐作为兜底/并行** |

### 6.2 推荐组合

1. **主线不动**：KiCad 继续作为唯一「可验收」链路（ERC/DRC/Gerber/DFM 证据齐全）。
2. **并行做 C**：把 `design.py` 的 canonical 数据加一个 `gen_eprj3.py` 后端，生成 `.eprj3`；用 4.1.97 客户端打开、截图、回读。**这一步不依赖登录、不传云端**，直接产出「EasyEDA 能打开的工程」。
3. **小规模验证 B2**：在 C 的产物上跑 `lceda-pro open --headless` + `invoke` 调 `pcb_Drc.check`，确认 Linux 下能否 headless、DRC 结果是否可解析。**只在这条验证通过后**，才讨论「用 EasyEDA 重做 PCB」。
4. **A 仅在用户明确同意上传云端时**才考虑；当前红线下属禁止项。

### 6.3 决策触发条件（建议写进下一轮 HANDOFF）

- 若 B2 在 Linux 上能稳定 `--headless` 跑 DRC → EasyEDA 可升级为「第二可验收链」；
- 若 B2 失败（GPU/显示/版本） → 停在 C，EasyEDA 仅作展示/交付格式；
- 若用户坚持「必须用 EasyEDA 出 Gerber 并下单」→ 需先补 43 个 LCSC C 号 + 库核对，单独立项。

---

## 7. 未决问题（待验证清单）

1. **Linux 4.1.97 客户端能否在无显示器/无独显环境 `--headless` 运行**（是否需要 Xvfb/GPU）——本机未装，必须实测。
2. **3.2.209 能否打开 `.eprj3`**；4.1.97 首次启动是否必须联网激活/登录一次。
3. **eprj3 1.x 的 21 符号/9 封装能否覆盖本项目 43 器件**；HY928D、ESP32-S3-MINI-1、OLED、USB-C 的自建符号/封装工作量。
4. **EasyEDA 侧 ERC/DRC 口径**与 KiCad 的差异（silk 豁免、未连接判定、铺铜重算），能否复现 0/0。
5. **官方 KiCad 导入是否真的只到 5.9**；KiCad 9/10 工程能否被 4.1.97 导入（文档未更新，需实测）。
6. **激活文件/离线模式的法律条款**（是否允许商业使用、是否允许自动化），官方 FAQ 未涉及。
7. **easyeda-agent 与官方 `lceda-pro` CLI 的取舍**：前者有 typed action/审计/journal，后者是官方原生 + MCP；两者能否共存、端口/会话是否冲突。
8. **tscircuit / Circuit JSON** 是否值得作为「AI 生成 → KiCad 复核」的中间层（本版不投入，仅观察）。

---

## 8. 来源

**KiCad**
- [KiCad 10.0.0 Released（2026-03-20）](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- [KiCad 10 CLI 手册](https://docs.kicad.org/10.0/en/cli/cli.html)
- 本机 `kicad-cli version` → 9.0.9（2026-11-05 实测）

**EasyEDA Pro**
- [客户端常见问题（三模式/激活/库/eprj）](https://prodocs.lceda.cn/cn/faq/client/index.html)
- [客户端历史版本（3.2.209 等）](https://prodocs.lceda.cn/cn/faq/client-version/)
- [客户端下载页（当前 4.1.97）](https://lceda.cn/page/download)
- [导入 KiCad（仅 5.1/5.9）](https://prodocs.lceda.cn/cn/import-export/import-kicad/)
- [导入 Altium（AD17 ASCII）](https://prodocs.lceda.cn/cn/import-export/import-altium-designer/)
- [命令行客户端 lceda-pro（V4.1.60+，--headless，MCP）](https://prodocs.easyeda.com/cn/api/guide/cli.html)
- [For AI: CLI 硬约束（纯文本版）](https://prodocs.lceda.cn/storage/texts/api/guide/cli-for-ai.md)
- [接口稳定性（开发阶段 API）](https://prodocs.easyeda.com/cn/api/guide/stability.html)
- [easyeda-eprj3-skill（v2.2.1）](https://github.com/easyeda/easyeda-eprj3-skill)
- npm `@jlceda/pro-api-types` 0.4.27（2026-10-16，registry 实测）

**easyeda-agent（仓库自述，二手）**
- `tools/easyeda-agent/docs/ecosystem-survey.md`（§7.9 自动布线、§9 KiCad 对比、§12 eprj3）
- `tools/easyeda-agent/docs/upstream-issues.md`（#27/#28/#29 状态）
- `tools/easyeda-agent/docs/dsh-integration.md`（DSH 接入方式）
- [easyeda-agent 仓库](https://github.com/zhoushoujianwork/easyeda-agent)

**商业与其他**
- [Altium Scripting（DelphiScript，2026-11-02）](https://www.altium.com/documentation/altium-designer/scripting)
- [Altium 365 API](https://www.altium.com/documentation/altium-developer-center/altium-365/api)
- [SKILL 语言（Wikipedia）](https://en.wikipedia.org/wiki/SKILL)
- [SiemensEDA_Python_Interface（第三方）](https://github.com/jabijker/SiemensEDA_Python_Interface)
- [Horizon EDA Python 模块](https://docs.horizon-eda.org/en/stable/python.html) ｜ [CLI](https://docs.horizon-eda.org/en/stable/cli-usage.html)
- [LibrePCB CLI](https://librepcb.org/_branches/release-2_1_1/features/cli/)
- [tscircuit 文档](https://docs.tscircuit.com/)
- GitHub API：Horizon v2.7.2、LibrePCB 2.1.1、Lepton 1.9.18、skidl 3.0.0、kicad-skip v0.2.5、KiCad 10.0.7（2026-11-05 实测查询）

---

> **本文件不改变任何工程文件**；所有「建议」均为决策输入，落地前需按 §7 逐项实测。
