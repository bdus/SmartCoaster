# SmartCoaster — EasyEDA Pro 第二实现（电路 / PCB 重做）

> 状态（2026-11-05）：**离线生成 + 原理图 + 已布线 PCB（铜从已验证 KiCad 2 层布线 1:1 移植）+ 独立几何检查 全部 PASS**；客户端 live 链路（原生 ERC/DRC、自动布线、铺铜、Gerber）**被 EasyEDA 登录/激活墙阻塞**，详见 [`/data/Documents/tools/EASYEDA_INSTALL_NOTES.md`](../../../../tools/EASYEDA_INSTALL_NOTES.md) §4 与本文 §5。
> 本目录是**新增的第二实现**：`electronics/kicad/` 原交付保持只读、未改动。

## 1. 目标与边界

用户要求：在 EasyEDA（嘉立创EDA专业版）技术栈上，基于 SmartCoaster 把电路/PCB 工作**重做一遍**，新建目录、不破坏原 KiCad 交付。

做法：把已冻结的 KiCad 设计（`electronics/kicad/scripts/design.py` + `smartcoaster.net` + `smartcoaster_2l.kicad_pcb`）当作**只读的电气/机械事实源**，通过 `scripts/extract_kicad.py` 提取成 `inputs/canonical.json`，再用官方 `easyeda-eprj3-skill` 的 `design.json` 管道生成 **EasyEDA 原生文件夹工程 `smartcoaster_easyeda.eprj3`**：

1. 原理图：47 器件 / 7 功能块 / 28 网络，全部重新布局与连线；
2. PCB：47 footprint 按 `gen_pcb.py` 的机械坐标摆放，板框换成机械 C 形，pad 形状恢复为 KiCad 的圆角矩形/椭圆/圆；
3. 铜：把已验证的 KiCad 2 层布线 **576 tracks + 62 vias 1:1 移植**为 EasyEDA `LINE`/`VIA` 记录（同坐标、同层、同线宽、同网络）；
4. 验证：KiCad 网表逐脚对账 + 独立子代理审计 + 独立 GEOS 几何 DRC。

- **不是**格式转换/导入向导：`design.py` 是 263 行 canonical，重做的本质是“再写一个后端”。
- **不是**替换 KiCad 主链：原有 ERC/DRC/Gerber/DFM 证据仍在 `electronics/kicad/`；本目录是第二实现与对比基线。
- **铜的边界**：铜是“已验证结果的移植”，不是 EasyEDA 客户端里新布的线；没有铺铜（GND plane），也没有客户端保存/重载/回读。见 §6。

## 2. 工具链（全部在 `/data/Documents/tools/`）

| 工具 | 版本 | 位置 |
|---|---|---|
| LCEDA Pro（EasyEDA Pro）客户端 | **4.1.97**（`4.1.97.04b092ac`） | `/data/Documents/tools/easyeda-pro/lceda-pro/lceda-pro` |
| easyeda-agent CLI/daemon | **v1.16.0**（connector 1.16.0） | `/data/Documents/tools/easyeda-agent/`（`~/.local/bin/easyeda`） |
| easyeda-eprj3-skill（官方离线生成） | **v2.2.1** | `/data/Documents/tools/easyeda-eprj3-skill/` |
| easyeda-pro-format-skill（官方格式参考） | **v1.0.0** | `/data/Documents/tools/easyeda-pro-format-skill/` |
| KiCad（只读输入） | 9.0.9 | `/data/Documents/tools/kicad` |
| shapely（独立铜检查，复用 `sim-venv`） | 2.1.2 | `/data/Documents/tools/sim-venv/bin/python` |

安装/版本/哈希/限制：`/data/Documents/tools/EASYEDA_INSTALL_NOTES.md`。
技术栈横向调研（11 款 EDA + AI 接口）：[`docs/EDA_TOOLCHAIN_SURVEY.md`](../../../docs/EDA_TOOLCHAIN_SURVEY.md)。

## 3. 目录结构

```text
electronics/easyeda/
├── README.md                     # 本文件
├── REPORT.md                     # 验证报告（数据链 + 证据 + 限制）
├── design/design.json            # eprj3 skill 的声明式输入（47 parts / 7 blocks）
├── inputs/
│   ├── canonical.json            # KiCad 的 canonical（器件/焊盘/网络/摆放/板框/孔/铜）
│   └── built_netlist.json        # 生成后的 EasyEDA 原理图网表
├── scripts/
│   ├── extract_kicad.py          # KiCad → canonical.json（只读；含 tracks/vias、pad 形状/圆角）
│   ├── gen_design.py             # canonical → design.json
│   ├── patch_board.py            # 机械板框 + 真实 pad 形状 + NPTH M2 孔
│   ├── port_copper.py            # KiCad 布线 1:1 → EasyEDA LINE/VIA（幂等）
│   ├── check_copper.py           # 独立 GEOS 铜检查 C1–C5（shapely）
│   ├── check_parity.py           # EasyEDA 网表 vs KiCad 网表逐脚对账
│   ├── render_pcb.py             # 离线渲染 routed PCB 图（无客户端）
│   ├── build.sh                  # 一条命令：提取→生成→门禁→补丁→铜→对账→报告
│   └── client_checks.sh          # 客户端 live 检查（需已登录/激活的客户端）
├── smartcoaster_easyeda/         # 生成的 .eprj3 工程（原理图 + PCB + project-report.md）
├── reports/                      # build.json / build.log / validate*.log / drc_placement.log / copper_check.* / parity.*
└── render/pcb_routed.png         # 已布线 PCB 预览（顶层红 / 底层蓝 / 过孔黄）
```

## 4. 一条命令复现

前置：`/data/Documents/tools/easyeda-eprj3-skill`、KiCad 9 运行库、Node ≥ 18、`sim-venv`（shapely）。
`build.sh` 默认 `EPRJ3_DETERMINISTIC=1`：连续两次构建的 `.esch2` / `.epcb2` **字节一致**（已实测）。

```bash
cd electronics/easyeda
bash scripts/build.sh
# 或只重跑某步（顺序重要）：
python3 scripts/extract_kicad.py && python3 scripts/gen_design.py
node /data/Documents/tools/easyeda-eprj3-skill/scripts/build.js \
  --design design/design.json --dir smartcoaster_easyeda --force --report reports/build.json
python3 scripts/patch_board.py
python3 scripts/port_copper.py
/data/Documents/tools/sim-venv/bin/python scripts/check_copper.py
python3 scripts/check_parity.py
python3 scripts/render_pcb.py
```

产物：
- `smartcoaster_easyeda/smartcoaster_easyeda.eprj3`（folder 工程索引）
- `smartcoaster_easyeda/sch/SmartCoaster/…esch2`（1 页原理图，47 器件、272 段导线、32 电源 flag、7 个跨块 net port）
- `smartcoaster_easyeda/pcb/PCB1.epcb2`（47 footprint、229 pad 实例、28 net、576 track + 62 via、板框 = 机械 C 形、4×M2 NPTH）
- `smartcoaster_easyeda/project-report.md`（BOM/信号流/门禁；其“板框”一行是生成时自动尺寸，已被机械板框补丁取代）
- `reports/*`、`render/pcb_routed.png`

## 5. 当前状态矩阵

| 检查 | 结果 | 证据 |
|---|---|---|
| 结构 validate（放置后 / 布线后） | **0 error / 0 warning**（两轮） | `reports/validate.log`、`reports/validate_routed.log` |
| 5 门禁（format/E001–E008/布局 lint/placement DRC/intent） | **全部通过**；lint 100/100，placement DRC 100/100 | `reports/build.log`、`reports/build.json` |
| 原理图 ↔ PCB 网表 | **netcheck OK，213 pins / 0 unconnected** | `reports/build.json.netcheck` |
| 与 KiCad 网表逐脚对账 | **168 connected pins / 28 nets 完全一致**；NC 脚一致（45）；4 个 M2 孔为机械附加 | `reports/parity.log`、`inputs/built_netlist.json` |
| 独立网表审计（全新子代理 ×2） | **ok: true**（唯一 warn：`PROT_VDD` 未画电源 flag，advisory） | `reports/audit_verdict.json`、`reports/netlist-audit.json` |
| 机械板框 / 孔 | 93.2×93.2 mm，R6，38×38 开口，80° 前 C 口；4×M2 NPTH @(±40,±24) mm | `inputs/canonical.json`、`scripts/patch_board.py` |
| 铜记录 round-trip（C1） | 576/576 线段、62/62 过孔与 canonical 逐字段一致 | `reports/copper_check.json` |
| 铜间距（C2） | **最小 7.938 mil ≥ 0.2 mm (7.874 mil)**，无违规 | 同上 |
| 铜连通性（C3，D004 等价） | **所有多 pad 网络单一铜岛，0 未连通** | 同上 |
| 板边/孔边净距（C4） | 最小 13.917 mil ≥ 0.3 mm (11.811 mil)，无违规 | 同上 |
| 过孔钻孔/环宽（C5） | 0.3 mm / 0.15 mm 均满足 | 同上 |
| 铺铜（GND plane） | **无**（D006 类）；留给客户端 | — |
| 客户端 GUI 启动 | 可用（Xvfb + `lceda-pro`），`doctor` connected | install notes §2 |
| 客户端 live ERC/DRC/route/Gerber | **BLOCKED**：未登录/未激活 → 激活窗；`pro.lceda.cn` 被 CloudWAF 418；`eda.js` 报 `BRIDGE_NOT_READY … command-space-missing` | install notes §4；`/data/Documents/LCEDA-Pro/logs/warn/20261105.log` |

**一句话**：EasyEDA 格式下的原理图、PCB 摆放、机械板框、带铜 2 层布线、网表与几何检查都已可复现地做完并独立对账；但铜是 KiCad 已验证布线的移植，**没有铺铜、没有客户端保存/重载/原生 DRC、没有 Gerber**，这些仍需已登录/激活的客户端。

## 6. 能证明 / 不能证明

**能证明**
- 用 EasyEDA 原生 `.eprj3` 数据结构重建了同一套电气连接（28 网络、168 连接脚、45 个 NC 与 KiCad 完全一致）。
- 原理图分 7 个功能块、跨块用 net port/网标；PCB 47 个 footprint 按 `gen_pcb.py` 的机械坐标摆放，pad 形状（圆角矩形/椭圆/圆）与 KiCad 一致，板框/孔与 `mechanical/square_v1` 的 PCB 接口一致。
- 带 2 层铜：576 track + 62 via，与已验证 KiCad 布线的坐标/层/线宽/网络逐项一致（C1），并通过独立 GEOS 几何检查：0.2 mm 间距、连通性、0.3 mm 板边、过孔钻孔/环宽全部满足（C2–C5）。
- 网表、几何、机械三项都有独立证据；`project-report.md` 自动生成。

**不能证明**
- 铜是**移植**而非 EasyEDA 客户端重新布线；没有铺铜（GND plane），所以不是完整的“可制造成品板”。
- 未做 EasyEDA 客户端保存/重载/回读，故所有结论是 **offline-verified**，不是 live-verified；客户端原生 DRC 的规则口径未复核。
- 原理图符号/封装来自 KiCad 几何的 inline 定义，**不是** EasyEDA 官方库器件；没有 LCSC C 号，不能直接下 SMT 单。
- 板框 R6 为 61 点多边形（每 90° 圆弧 12 段弦近似，sagitta < 0.05 mm），不是原生 ARC。
- 未做 Gerber/坐标/DFM（client 导出被登录墙阻塞）；也未做热/EMC/电源完整性复算（沿用 `docs/REVIEW_ELECTRICAL.md`）。

**关于 eprj3 skill 的 DRC**：它在有铜的板上仍按**轴对齐包围盒**算 track 间距，45° 走线会产生大量假阳性（本板实测 587 条假 D001，而 KiCad 原板 `kicad-cli pcb drc` 为 0/0）。因此本目录只用它做 **placement** 判定，布线后的铜间距用独立 GEOS 检查（C2）。这个工具边界已写进 `REPORT.md`，不冒充“客户端 DRC 通过”。

## 7. 下一步（按优先级）

1. **解锁客户端**（用户侧）：在可访问 `pro.lceda.cn` 的网络登录一次，或放激活文件到 `/data/Documents/LCEDA-Pro/lceda-pro-activation.txt`；然后 `bash scripts/client_checks.sh` 跑：client sch DRC → `eda.js netlist` 复核 → 客户端 PCB DRC / 铺铜 / 截图 / Gerber。
2. 客户端里补 GND 铺铜并重建 fill（`eda.js pour --net GND`），再跑一次原生 DRC。
3. 若目标要可采购：补 43 个器件的 LCSC C 号，改用 `"ic": "<device>"` + `eda.js pins/search`，让客户端放置官方符号/封装。
4. 板框若需严格 ARC：在客户端用「板框」工具重画 R6（或后续把 61 点路径替换为 `"ARC"` 段，需先做客户端往返验证）。
