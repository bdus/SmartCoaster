# SmartCoaster — EasyEDA Pro 第二实现（电路 / PCB 重做）

> 状态（2026-11-05）：**离线生成与校验 PASS**；客户端 live 链路（原生 ERC/DRC、自动布线、Gerber）**被 EasyEDA 登录/激活墙阻塞**，详见 [`/data/Documents/tools/EASYEDA_INSTALL_NOTES.md`](../../../../tools/EASYEDA_INSTALL_NOTES.md) §4 与本文 §5。
> 本目录是**新增的第二实现**：`electronics/kicad/` 原交付保持只读、未改动。

## 1. 目标与边界

用户要求：在 EasyEDA（嘉立创EDA专业版）技术栈上，基于 SmartCoaster 把电路/PCB 工作**重做一遍**，新建目录、不破坏原 KiCad 交付。

做法：把已冻结的 KiCad 设计（`electronics/kicad/scripts/design.py` + `smartcoaster.net` + `smartcoaster_2l.kicad_pcb`）当作**只读的电气/机械事实来源**，通过 `electronics/easyeda/scripts/extract_kicad.py` 提取成 `inputs/canonical.json`，再用官方 `easyeda-eprj3-skill` 的 `design.json` 管道生成 **EasyEDA 原生文件夹工程 `smartcoaster_easyeda.eprj3`**（原理图 + 已按机械位置摆放的 PCB），并用 KiCad 网表做独立逐脚对账。

- **不是**格式转换/导入向导：`design.py` 是 263 行 canonical，重做的本质是“再写一个后端”，而不是把 `.kicad_pcb` 转格式。
- **不是**替换 KiCad 主链：原有 ERC/DRC/Gerber/DFM 证据仍在 `electronics/kicad/`；本目录是第二实现与对比基线。

## 2. 工具链（全部在 `/data/Documents/tools/`）

| 工具 | 版本 | 位置 |
|---|---|---|
| LCEDA Pro（EasyEDA Pro）客户端 | **4.1.97**（`4.1.97.04b092ac`） | `/data/Documents/tools/easyeda-pro/lceda-pro/lceda-pro` |
| easyeda-agent CLI/daemon | **v1.16.0**（connector 1.16.0） | `/data/Documents/tools/easyeda-agent/`（`~/.local/bin/easyeda`） |
| easyeda-eprj3-skill（官方离线生成） | **v2.2.1** | `/data/Documents/tools/easyeda-eprj3-skill/` |
| easyeda-pro-format-skill（官方格式参考） | **v1.0.0** | `/data/Documents/tools/easyeda-pro-format-skill/` |
| KiCad（只读输入） | 9.0.9 | `/data/Documents/tools/kicad` |

安装/版本/哈希/限制：`/data/Documents/tools/EASYEDA_INSTALL_NOTES.md`。
技术栈横向调研（11 款 EDA + AI 接口）：[`docs/EDA_TOOLCHAIN_SURVEY.md`](../../../docs/EDA_TOOLCHAIN_SURVEY.md)。

## 3. 目录结构

```text
electronics/easyeda/
├── README.md                     # 本文件
├── REPORT.md                     # 验证报告（数据链 + 证据 + 限制）
├── design/design.json            # eprj3 skill 的声明式输入（47 parts / 7 blocks）
├── inputs/
│   ├── canonical.json            # 从 KiCad 提取的 canonical（器件/焊盘/网络/摆放/板框/孔）
│   └── built_netlist.json        # 生成后的 EasyEDA 原理图网表
├── scripts/
│   ├── extract_kicad.py          # KiCad → canonical.json（只读）
│   ├── gen_design.py             # canonical → design.json
│   ├── patch_board.py            # 板框换成机械 C 形 + 4 个 NPTH M2 孔
│   ├── check_parity.py           # EasyEDA 网表 vs KiCad 网表逐脚对账
│   ├── render_pcb.py             # 离线渲染 placement 图（无客户端）
│   ├── build.sh                  # 一条命令：提取→生成→5 门禁→板框补丁→对账→报告
│   └── client_checks.sh          # 客户端 live 检查（需已登录/激活的客户端）
├── smartcoaster_easyeda/         # 生成的 .eprj3 工程（原理图 + PCB + project-report.md）
├── reports/                      # build.json / build.log / validate.log / drc.log / parity.log
└── render/pcb_placement.png      # 摆放 + ratsnest 预览（无铜）
```

## 4. 一条命令复现

前置：`/data/Documents/tools/easyeda-eprj3-skill`、KiCad 9 运行库、Node ≥ 18（本机 v24.15.0）。

```bash
cd electronics/easyeda
bash scripts/build.sh
# 或只重跑某步：
python3 scripts/extract_kicad.py && python3 scripts/gen_design.py
node /data/Documents/tools/easyeda-eprj3-skill/scripts/build.js \
  --design design/design.json --dir smartcoaster_easyeda --force --report reports/build.json
python3 scripts/patch_board.py
python3 scripts/check_parity.py
python3 scripts/render_pcb.py
```

产物：
- `smartcoaster_easyeda/smartcoaster_easyeda.eprj3`（folder 工程索引）
- `smartcoaster_easyeda/sch/SmartCoaster/…esch2`（1 页原理图，47 器件、272 段导线、32 电源 flag、7 个跨块 net port）
- `smartcoaster_easyeda/pcb/PCB1.epcb2`（47 footprint、229 pads、28 net、板框 = 机械 C 形）
- `smartcoaster_easyeda/project-report.md`（BOM/信号流/门禁；注意其“板框”一行是生成时自动尺寸，已被机械板框补丁取代）
- `reports/*`、`render/pcb_placement.png`

## 5. 当前状态矩阵

| 检查 | 结果 | 证据 |
|---|---|---|
| 结构 validate | **0 error / 0 warning** | `reports/validate.log` |
| 5 门禁（format/E001–E008/布局 lint/placement DRC/intent） | **全部通过**；lint 100/100，DRC 100/100（placement-only） | `reports/build.log`、`reports/build.json` |
| 原理图 ↔ PCB 网表 | **netcheck OK，213 pins / 0 unconnected** | `reports/build.json.netcheck` |
| 与 KiCad 网表逐脚对账 | **168 connected pins / 28 nets 完全一致**；NC 脚一致（45 个）；4 个 M2 孔为机械附加 | `reports/parity.log`、`inputs/built_netlist.json` |
| 机械板框 | 93.2×93.2 mm，R6，38×38 开口，80° 前 C 口；4×M2 NPTH @(±40,±24) mm | `inputs/canonical.json`、`scripts/patch_board.py` |
| 离线渲染 | `render/pcb_placement.png`（板框/焊盘/位号/ratsnest） | 本目录 |
| 客户端 GUI 启动 | 可用（Xvfb + `lceda-pro`），`doctor` connected | install notes §2 |
| 客户端 live ERC/DRC/route/Gerber | **BLOCKED**：未登录/未激活 → `Regist` 窗；`pro.lceda.cn` 被 CloudWAF 418；`eda.js` 报 `BRIDGE_NOT_READY … command-space-missing` | install notes §4；`/data/Documents/LCEDA-Pro/logs/warn/20261105.log` |

**一句话**：EasyEDA 侧的**数据模型、原理图、机械板框、网表一致性**已经可复现地做完并独立对账；**铜（布线/铺铜）与制造文件**必须在已登录/激活的 EasyEDA Pro 客户端里完成，本机当前环境不满足，不能用离线结果冒充。

## 6. 能证明 / 不能证明

**能证明**
- 用 EasyEDA 原生 `.eprj3` 数据结构重建了同一套电气连接（28 网络、168 连接脚、45 个 NC 与 KiCad 完全一致）。
- 原理图可读、分 7 个功能块、跨块用 net port/网标；PCB 47 个 footprint 按 `gen_pcb.py` 的机械坐标摆放，板框/孔与 `mechanical/square_v1` 的 PCB 接口一致。
- 离线格式闸门、布局 lint、placement DRC、netcheck 全绿，且 `project-report.md` 自动生成。

**不能证明**
- 没有铜：28 个网络的 ratsnest 尚未布线，故**不能**声称 0 DRC / 0 unconnected 的成品板。
- 原理图符号/封装来自 KiCad 焊盘几何的 inline 定义，**不是** EasyEDA 官方库器件；没有 LCSC C 号，不能直接下 SMT 单。
- 板框 R6 为 61 点多边形（每 90° 圆弧 12 段弦近似，sagitta < 0.05 mm），不是原生 ARC。
- 未做 EasyEDA 客户端保存/重载/回读，故所有结论是 **offline-verified**，不是 live-verified。
- 未做 Gerber/坐标/DFM（client 导出被登录墙阻塞）。

## 7. 下一步（按优先级）

1. **解锁客户端**（用户侧）：在可访问 `pro.lceda.cn` 的网络登录一次，或放激活文件到 `/data/Documents/LCEDA-Pro/lceda-pro-activation.txt`；然后 `bash scripts/client_checks.sh` 跑：client sch DRC → `eda.js netlist` 复核 → `pcb --route` 自动布线 → PCB DRC → 截图/导出。
2. 若目标要可采购：把 43 个器件补 LCSC C 号，改用 `"ic": "<device>"` + `eda.js pins/search`，让客户端放置官方符号/封装。
3. 布线后的 DRC/DFM 与 Gerber 一律以客户端报告为准；通过后再与 `electronics/kicad/build/` 的 0/0 对比。
4. 板框若需严格 ARC：在客户端用「板框」工具重画 R6（或后续把 61 点路径替换为 `"ARC"` 段，需先做客户端往返验证）。
