# SmartCoaster 独立验收报告（VERIFY_REPORT）

- **验收人**：verifier（独立复核，未参与本轮实现；所有结论均为本机复跑所得）
- **验收时间**：2026-11-04 20:07–20:15（Asia/Shanghai）
- **被验收对象**：**未提交工作区**（`git log -1` = `495e7ba`；`git status --porcelain` 共 128 项：126 项本轮改动 + 2 项验收产物）
- **环境**：KiCad 9.0.9（`/data/Documents/tools/kicad`，`~/.local/bin/kicad-cli`）· ESP-IDF v6.1 · build123d venv（`mechanical/square_v1/.venv`）· Blender 4.5.3 · 36C/62GB
- **原则**：只读验收；不修改被验收源码；所有 PASS 均附复跑命令与原始输出摘要。

## 结论总表

| # | 验收项 | 结论 | 关键证据 |
|---|--------|------|----------|
| 1 | PCB：2 层 / DRC 0/0 / 47 footprint / 无删件残留 / 有布线 / pad 211·12·6 | **PASS** | `build/DRC_verify.rpt` 独立复跑：`Found 0 DRC violations` + `Found 0 unconnected pads`；pcbnew：copper=2、footprint=47、576 track + 62 via、pad 211 SMD/12 PTH/6 NPTH、FORBIDDEN_REFS=[] |
| 2 | 原理图/ERC：0 error、43 器件/28 网络、design.py ↔ kicad_sch 一致 | **PASS** | 独立 ERC 复跑 0 Errors/0 Warnings；netlist 43 comps / 28 intended nets；`verify.py` 逻辑复跑 `RESULT: PASS`（components=43 nets=66 intended_nets=28） |
| 3 | Gerber/DFM：2 层产物齐全、DFM.md 2 层、dfm_check PASS、pcb_2l.png 为布线预览 | **PASS** | `build/gerbers/` 13 文件（8 层 + drl + drl_map + gbrjob + pos）且 gbrjob=`Copper,L1,Top`/`Copper,L2,Bot`；`dfm_check.py` 复跑输出与 `build/DFM.md` **逐字节一致**、5 项 PASS；`pcb_2l.png` 目视 + 像素统计确认有红/蓝走线与黄 via |
| 4 | 机械：verify_v01 21/21、无光导几何、12 件 | **PASS** | `.venv/bin/python cad/verify_v01.py` → `21/21 checks passed`（12 solids、37 对干涉 0、STEP 回读 12 solids）；`grep "light_guide\|光导"` 仅 README 中「无光导」否定句；PARTS=12 无发光件 |
| 5 | 固件：host 11/11(41) + mock 9/9(198) + 差分 16/16 + pytest 16、halo 0 命中、idf build、bin≈519,152 B | **PASS** | `run_host_tests.sh` exit 0；直接跑二进制：`41 checks, 0 failures, 11/11` / `198 checks, 0 failures, 9/9`；差分 `16/16 scenarios, 82 records`；pytest `16 passed`；`grep -i halo firmware/esp32 firmware/model tests/` 0 命中；`idf.py build` → `Project build complete`，bin **519,152 B** |
| 6 | P3/文档：光导/light_guide 0 命中、4 张新图、无 LED 卖点、docs/12 OBSOLETE | **PASS** | 指定范围 `grep` **0 命中**（exit 1）；`submission/0[1-4]_*.png` 均存在且 mtime 2026-11-04 19:47（当日新图），目视无灯环/光导；README/BOM/docs 中 LED 均为「已去掉/无灯」，`grep 卖点` 0 命中；docs/12 有 OBSOLETE 横幅 |
| 7 | 事实性/红线：无「实物已标定」、PROVISIONAL 保留、ref/ 与 original_cad/ 未改、无 LED/光导加回 | **PASS**（附 1 项事实性偏差，见 F4） | `git diff` 中「实物/标定/实测」均为「待做/未完成/仿真≠实物」；PROVISIONAL 仍标于 `config/mechanical_params.yaml`、`square_model.py`、`hx711_hw.c`、`firmware/REPORT.md`；`git status ref/ mechanical/original_cad/` 为空；PCB/网表/原理图/固件/机械均无 LED/光导件 |

**硬性判定：7/7 项 PASS，未发现放宽标准才能通过的不达标项。** 但存在 7 条非阻塞的「证据/文案一致性」发现（F1–F7），其中 **F1、F4** 建议在 commit 前处理（详见文末）。

---

## 1. PCB：2 层 0/0、器件/布线/pad 核对 —— PASS

```bash
cd electronics/kicad
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu \
       XDG_CONFIG_HOME=/data/Documents/projects/SmartCoaster/.tools/kicad-config
~/.local/bin/kicad-cli pcb drc --format report --severity-all --units mm \
  -o build/DRC_verify.rpt smartcoaster/smartcoaster_2l.kicad_pcb
```
输出摘要（exit 0）：

```
Found 0 violations
Found 0 unconnected items
Saved DRC Report to build/DRC_verify.rpt
```
`build/DRC_verify.rpt`（2026-11-04T20:07:20+0800）原文：

```
** Found 0 DRC violations **
** Found 0 unconnected pads **
** Found 0 Footprint errors **
```

> 注：kicad-cli 向 stderr 打印 `Error: schema file '/usr/share/kicad/schemas/api.v1.schema.json' not found`，属该解包版 KiCad 的已知打包噪音，**退出码 0、报告正常生成，不影响结论**。

pcbnew 复核（`LD_LIBRARY_PATH` + `PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages`，`pcbnew.LoadBoard`）：

```
COPPER_LAYERS: 2
FOOTPRINT_COUNT: 47
REFS: ['C1'…'C16'(无C8),'H1','H2','H3','H4','J1'…'J5','R1'…'R12','R25','R26','SW2','SW3','U1'…'U7']
FORBIDDEN_REFS: []          # 无 D1 / Q1–Q3 / R13–R21 / TP1–TP6
TRACKS: 576  VIAS: 62  TOTAL: 638
PAD_TOTAL: 229   SMD: 211  PTH: 12  NPTH: 6
ZONES: 0    NETS: 29        # 29 = 28 信号网 + net0；2 层板无铺铜，GND 走线实现
```

- 47 = **43 器件 + H1–H4 安装孔**（43 个非 H 位号与 `design.py PARTS=43` 完全一致）。
- 有布线：576 track + 62 via > 0。
- pad 211 SMD / 12 PTH / 6 NPTH 与 DFM/HANDOFF 声称完全一致。
- 信息性：2 层板 ZONES=0（无 GND 铺铜），任务书未要求铺铜，不作判定项。

## 2. 原理图 / ERC —— PASS

**独立重跑 ERC**（不覆盖工程内 `build/ERC.rpt`，输出到临时路径）：

```bash
kicad-cli sch erc --severity-all --format report -o /tmp/ERC_verify.rpt \
  smartcoaster/smartcoaster.kicad_sch
# → Found 0 violations；报告正文：** ERC messages: 0  Errors 0  Warnings 0
```
工程内 `build/ERC.rpt`（2026-11-04T20:02:54，晚于 sch mtime 20:02:51）：

```
** ERC messages: 0  Errors 0  Warnings 0
```

**器件/网络计数**（三条独立来源一致）：

| 来源 | 结果 |
|---|---|
| `build/smartcoaster.net.xml` | comps **43**；nets 66 = **28** 信号网 + 38 `unconnected-*` |
| `electronics/kicad/NETLIST.md` | 网络表 **28** 行 |
| `electronics/kicad/BOM.csv` | 24 行 / **43** 个唯一位号 |

**design.py ↔ kicad_sch 一致性**（按 `build.sh` 的 `verify.py` 同一逻辑复跑：把验证脚本的 OUT/SCH 指向 `/tmp`，重新用 kicad-cli 从 `.kicad_sch` 导出网表，再与 `design.py` 逐引脚比对）：

```bash
# 关键输出
components=43 nets=66 intended_nets=28
RESULT: PASS
# design.py: PARTS=43  NETS=28  NC_PINS=6
```
原理图实例数复核：`(lib_id` 47 处 = **43 器件实例 + 4 PWR_FLAG**；无 LED/驱动符号（无 `Device:LED` 等）。

## 3. Gerber / DFM / 布线预览 —— PASS

**Gerber 产物**（`build/gerbers/`，全部 mtime 20:06:47–48，**晚于** pcb mtime 20:06:42；旧 4L 文件 14 个已从该目录删除）：

```
smartcoaster_2l-F_Cu.gtl        37,163 B   D03 flash 281
smartcoaster_2l-B_Cu.gbl        10,730 B   D03 flash  74
smartcoaster_2l-F_Paste.gtp / B_Paste.gbp / F_Silkscreen.gto / B_Silkscreen.gbo
smartcoaster_2l-F_Mask.gts / B_Mask.gbs / Edge_Cuts.gm1
smartcoaster_2l.drl              1,877 B   (80 个钻孔)
smartcoaster_2l.pos              3,021 B   (43 器件坐标, 44 行含表头)
smartcoaster_2l-job.gbrjob / smartcoaster_2l-drl_map.gbr
build/smartcoaster_2l_gerbers.zip 51,202 B (13 entries，含 .drl/.pos)
```
`job.gbrjob` 层定义确认 **2 铜层**：`Copper,L1,Top` + `Copper,L2,Bot`（另有 Top/Bot Paste、Legend、SolderMask、Profile）。

**DFM**（`dfm_check.py` 复跑写到 `/tmp/DFM_verify.md`，**不覆盖**工程文件）：

```bash
diff /tmp/DFM_verify.md build/DFM.md   # → 无差异（IDENTICAL）
```
`build/DFM.md` 标题为「PCB DFM 自查（2 层）」，JLC 2L 对照 5 项全 PASS：
线宽 0.2≥0.127 · 过孔钻 0.3≥0.2 · 环宽 0.15≥0.13 · 板边铜距 0.3≥0.3 · 层数 2。

**布线预览** `build/pcb_2l.png`（1760×1760，mtime 20:06:50 > pcb 20:06:42）：
- 像素统计：3,184 种颜色；红 (182,54,41)/蓝 (39,83,154)/黄 via 均大量存在 → 非空白、非仅板框。
- 目视：`F.Cu(红)/B.Cu(蓝)/via(黄)` 标题 + 实际走线、器件焊盘、C 形板框，确认是**已布线预览**。

## 4. 机械（square_v1） —— PASS

```bash
cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py
```
输出（exit 0，21 条全 PASS，摘要）：

```
[PASS] assembly solids == 12                  12 solids
[PASS] bbox 100 x 100 x 18                    100.000 x 100.000 x 18.000
[PASS] all parts valid                        12/12
[PASS] every part is one solid                []
[PASS] overload float gap == 0.5              0.500 mm
[PASS] pairwise interference == 0             37 pairs []
[PASS] STEP re-import: 12 solids              12 solids
[PASS] STEP re-import: bbox                   100.000 x 100.000 x 18.000
21/21 checks passed -> .../mechanical/square_v1/build/verify_report.json
```

**光导残留**（排除 `build/` 历史快照与 `.venv`，并额外检查 `v1…v6_square_v1`）：

```bash
grep -rn "light_guide\|光导" mechanical/square_v1/ --exclude-dir=build --exclude-dir=.venv
# 仅 3 条，全部是「无光导」否定说明：
#   README.md:17  无光导（用户 2026-11-04 决定）…全部取消
#   README.md:62  v6_square_v1 版本快照（最新：12 件，无光导）
#   README.md:99  无光导：…全部取消
grep -rniE "light[- ]?guide|\bguide\b|halo" mechanical/square_v1/cad/
# → 全部是 "no light guide / halo" 注释，无实际几何引用
```
**件数=12**：`PARTS` 字典 12 键（shell/plate/pcb/sensor/esp32/hx711/usbc/battery/oled/button/glass/pad），无发光件；`config/mechanical_params.yaml` square_v1：`parts: 12`、`status: verified_geometry`。

> 说明（F1）：复跑前工作区里被提交跟踪的 `build/verify_report.json` 仍是 HEAD 的**旧 13 件版本**（`git diff`：`assembly solids == 13` → `12`）；本次按验收命令复跑后已刷新为 `ok:true / 12 solids / 21 checks`。复跑命令本身 PASS，但「证据文件未随几何更新」见 F1。

## 5. 固件 —— PASS

**host 测试**（`bash tests/firmware/run_host_tests.sh`，exit 0）：

```
[1/3] CMake host build + CTest → 2/2 Test passed (host_core_test, host_mock_test)
[2/3] C vs Python differential → 16/16 scenarios match, 82 records compared
[3/3] Python reference model → 16 passed in 0.13s
```
**直接运行测试二进制**（CTest 成功时不回显内部计数，故另跑一次取原始计数）：

```
host_core_test:  41 checks, 0 failures, 11/11 tests passed
host_mock_test:  198 checks, 0 failures, 9/9 tests passed
```
与任务要求 **host 11/11（41 checks）、mock 9/9（198 checks）、差分 16/16、pytest 16** 完全一致。

**halo 残留**：

```bash
grep -rn -i "halo" firmware/esp32 firmware/model tests/   # → 0 命中（exit 1）
```
（全仓其余 halo 提及均为「已删除」说明或历史 OBSOLETE 文档；固件代码无 LED/PWM 驱动，仅 `app_main.c` 注释说明已移除。）

**idf.py build**：

```bash
source /home/pi/.espressif/tools/activate_idf_v6.1.sh
cd firmware/esp32 && idf.py build     # exit 0
# → Project build complete. To flash, run: idf.py flash
# → smartcoaster.bin binary size 0x7ebf0 bytes = 519,152 B；app 分区余 66%
```
bin 实测 `519152 bytes`（0x7EBF0），与「约 519,152 B」一致。

> 环境注意：`activate_idf_v6.1.sh` 脚本**结束时返回码为 1**（脚本内部末尾非零，激活本身成功）。若写成 `source … && cd … && idf.py build` 会因 `&&` 短路而「看起来没输出/失败」；应使用 `;` 分步执行。本报告已按分步方式复跑成功——**这是环境脚本缺陷，不是固件构建失败**。

## 6. P3 / 文档 —— PASS

**指定范围精确 grep（0 命中）**：

```bash
grep -rn "光导\|light_guide" render/ submission/ packaging/ README.md BOM.md \
     docs/07* docs/09* docs/10* docs/11*
# → 0 命中（exit 1）
```
docs/12 保留 `> **⚠ OBSOLETE（2026-11-04 起废弃…）**` 历史横幅（允许）。

**提交包 4 图**（均为 2026-11-04 当日新图）：

| 文件 | mtime | 目视复核 |
|---|---|---|
| `submission/01_hero.png` | 2026-11-04 19:47:57 | 紫色顶板 + 深灰壳，前脸仅 26×7 屏窗 + 圆按键，无灯环/灯缝 |
| `submission/02_front.png` | 2026-11-04 19:47:28 | 正视：仅屏窗 + 按键，无灯带/光导 |
| `submission/03_exploded.png` | 2026-11-04 19:47:28 | 爆炸图：顶板/玻璃/PCB/壳/电池/垫，无发光件 |
| `submission/04_package.png` | 2026-11-04 19:47:28 | 包装渲染，无发光件 |

另：`submission/SmartCoaster_Story.pdf/.png` 同为 19:47 新出；`render/RENDER_LOG.md` 记录「2026-11-04 无灯重出」。

**无「LED/光导是卖点」表述**：`grep -rn "卖点"` 0 命中；README/BOM/docs/07/09/10/11 中 LED/灯 的提及全部是「已去掉 / 无灯 / 无灯缝 / 无灯环」的否定口径；`grep "光导"` 在 docs 正文（除 docs/12 OBSOLETE 与 design 历史稿）无正面描述。

## 7. 事实性 / 红线 —— PASS（附 F4）

**a) 无「仿真/主机测试写成实物已标定」**：`git diff` 新增行中「实物/标定/实测/已验证」逐条核对，全部是「待做 / 用户侧未完成 / 仿真与主机测试通过 ≠ 实物通过 / 必须实物标定」，无一处声称已实物标定。`firmware/REPORT.md` 的「本次实测」明确限定为 host/mock/差分测试，不是实物测量。

**b) 未确认尺寸仍标 PROVISIONAL**：
- `config/mechanical_params.yaml` → `hy928d.status: provisional`（U 槽/拱为像素比例+照片估算）
- `mechanical/square_v1/cad/square_model.py:53` → `# PROVISIONAL: ...`
- `firmware/esp32/main/hx711_hw.c:160` → `counts_per_g ... (PROVISIONAL)`；`hx711_mock.c:153` 同
- `firmware/REPORT.md` → 「实物标定 | 未做 | `counts_per_g=515.4` 为 PROVISIONAL」
- `docs/HANDOFF.md` → 「`counts_per_g=515.4` 仍是 PROVISIONAL」

**c) `ref/`、`mechanical/original_cad/` 未被改**：
```bash
git status --porcelain ref/ mechanical/original_cad/   # → 空
git diff --stat -- ref/ mechanical/original_cad/       # → 空
```

**d) 没有把 LED/光导加回来**：PCB refs 无 D1/Q1–Q3/R13–R21/TP1–TP6；网表 43 comps 无删除件；原理图 lib_id 47 = 43 实例 + 4 PWR_FLAG（无 LED/驱动符号）；固件无 LED/PWM 驱动；机械 12 件无发光件；BOM 不含这些位号。
**e) 0/0 有 DRC 证据**：`build/DRC_2l.rpt`（20:06:44，0 violation/0 unconnected，晚于 board mtime 20:06:42）+ 本报告 §1 独立 `DRC_verify.rpt`（20:07:20，同样 0/0）。README/HANDOFF/docs 的 0/0 表述均有这些证据支撑。

---

## 失败/不达标项

**无硬性不达标项。** 7 项验收标准全部满足，未发现需要放宽标准才能通过的问题。

## 附加发现与建议（不改变上述 PASS 判定，但建议处理）

| 编号 | 级别 | 发现（证据） | 建议 |
|---|---|---|---|
| **F1** | 中 | 被验收工作区里 **`mechanical/square_v1/build/verify_report.json` 是旧版**：与 HEAD 一致为 `assembly solids == 13`；`docs/HANDOFF.md` 却把它作为「12 件/21/21」的证据引用。按验收命令复跑后才刷新为 `12 solids / 21 checks / ok:true`。 | 本轮 commit 时**把刷新后的 `verify_report.json` 一并提交**（现已刷新，勿 `git checkout` 回旧版）。 |
| **F2** | 低 | 原理图仍有一处旧文案：`electronics/kicad/scripts/design.py:259` 的 BLOCKS 标签 `'UI: OLED header, key, RGB halo'` 被写入 `smartcoaster.kicad_sch:9567` 的文本标注「UI: OLED header, key, RGB halo」。**无电气影响**（非器件/网络），但与「无 LED/光导」口径不一致。 | 建议把标签改为 `UI: OLED header, key` 后重生成 sch（`gen_sch.py` + `verify.py` + ERC）。 |
| **F3** | 低 | `electronics/kicad/scripts/gen_bom.py` 的 `NOTE` 字典仍保留死键 `HALO_*`、`LED_*`（HEAD 已有，本轮未引入，且 NETLIST.md 输出不含这些网络——仅旧标签残留）。 | 顺手删除这些死映射，避免后续误读。 |
| **F4** | 中 | `docs/HANDOFF.md` §9 末条勾选「`[x]` 工作区已 commit（见 git log 最新一条；本轮为一次性收口提交）」**与事实不符**：验证时 `git log -1` 仍是 `495e7ba`（上一轮提交），`git status` 有 126 项未提交改动。 | 本轮 commit 后该勾选才成立；若不在本轮提交，请改为「待提交」。 |
| **F5** | 低 | `build/DFM.md` 备注「BOM 里标 `PROVISIONAL` 的需下单前确认封装/引脚」，但 `electronics/kicad/BOM.csv` 中 **0 处 PROVISIONAL**（缺 MPN 的行有 10 行）。 | 改措辞为「缺 MPN 的 10 行需下单前补齐」，或给 BOM 加 PROVISIONAL 标记。 |
| **F6** | 低 | `build/` 下仍保留旧的 4 层 `smartcoaster_4l_gerbers.zip`（tracked、未改）；`build/gerbers/` 已纯 2 层（14 个旧 4L 文件已删）。 | 建议把旧 4L zip 移到归档目录或删除，避免打样时误用。 |
| **F7** | 低（范围外） | `docs/design/2026-11-04-ui-interaction-b-design.md`（不在本轮验收列举文件内）仍描述 halo 灯效；`render/lumen/`、`mechanical/lumen/` 仍有旧 LUMEN 概念线文案（README 已标「不再推进」）。 | 如对外发布/交付，建议给这些历史文件加 OBSOLETE/历史横幅。 |

## 写入声明（只读审计）

- 本次验收**只写**了：
  1. `docs/VERIFY_REPORT.md`（本报告，唯一允许的文档写入）；
  2. `electronics/kicad/build/DRC_verify.rpt`（任务书指定的 DRC 验证输出）；
  3. `mechanical/square_v1/build/verify_report.json` —— 由**任务书指定的复跑命令** `verify_v01.py` 自身写出（该脚本尾部固定写此文件）；复跑前它是旧 13 件版本，复跑后为正确的 12 件版本（见 F1）。
- 其余验证产物（独立 ERC 报告、核对过的网表、DFM 重生成、host 测试构建、idf 构建日志）均写入 `/tmp` 等临时位置，未落回工程目录。
- **未修改任何被验收源码/文档**（`git diff` 中除上述产物外无本会话新增改动）。

## 复跑命令清单（可复现）

```bash
# 1) PCB DRC（本报告 §1）
cd electronics/kicad && export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu \
  XDG_CONFIG_HOME=/data/Documents/projects/SmartCoaster/.tools/kicad-config
~/.local/bin/kicad-cli pcb drc --format report --severity-all --units mm \
  -o build/DRC_verify.rpt smartcoaster/smartcoaster_2l.kicad_pcb

# 2) ERC（独立）
~/.local/bin/kicad-cli sch erc --severity-all --format report -o /tmp/ERC_verify.rpt \
  smartcoaster/smartcoaster.kicad_sch

# 3) design.py ↔ sch 一致性（verify.py 逻辑，OUT 改 /tmp）
PYTHONPATH=$PWD/scripts /data/Documents/tools/sim-venv/bin/python <verify.py 副本>

# 4) DFM（脚本副本，OUT 改 /tmp）
PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages /usr/bin/python3 <dfm_check.py 副本>

# 5) 机械
cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py

# 6) 固件
bash tests/firmware/run_host_tests.sh
source /home/pi/.espressif/tools/activate_idf_v6.1.sh; cd firmware/esp32; idf.py build
```

# §8 最终状态增量复核（2026-11-04 20:34–20:46）

> **范围**：只复核 Lead 列出的「HEAD `ae17e10` 之后、未提交工作区」增量项；§1–§7 的 7/7 结论**保持不变**（本轮未重跑全量验收，只跑受影响项）。
> **基线**：HEAD = `ae17e10`（上一轮验收已提交，含本报告 §1–§7）；复核开始时 `git status` = 20 个已修改 + 5 个新文件（与 Lead 清单一致）。
> **注意**：复核窗口内观察到 **7 个并发改动**（见 §8.3），均为文档/README 类收尾（mtime 20:34:35–20:36:33），不涉及本轮构建/测试输入；被测输入文件 mtime 均早于复跑（固件源码 20:33:33、板 20:06:42、机械模型 20:26:49）。
> **bin 数字说明**：本报告 §5 的 519,152 B 是**上一轮**结果；本轮修复 BLE 0xFF04 后为 **519,184 B（0x7EC10）**，以下 §8 为准。

## 8.1 逐项结论

| # | 增量复核项 | 结论 | 关键证据（本机复跑原始输出摘要） |
|---|---|---|---|
| 8-1 | `idf.py build` 通过、bin=519,184 B | **PASS** | `IDF_EXIT=0`；`Project build complete`；`smartcoaster.bin binary size 0x7ec10 bytes`；`stat` = **519,184 B**（0x7EC10，app 分区余 66%）。与 Lead 声称一致（上一轮 519,152 → +32 B） |
| 8-2 | host 11/11 + mock 9/9 + 差分 16/16 + pytest 16 仍通过 | **PASS** | `run_host_tests.sh` exit 0：CTest `2/2 passed`；直接跑二进制 `41 checks, 0 failures, 11/11`、`198 checks, 0 failures, 9/9`；差分 `16/16 scenarios, 82 records compared`；pytest `16 passed in 0.17s` |
| 8-3 | 机械 `verify_v01.py` 仍 21/21；FR-4 标签已改、meta 已刷新 | **PASS** | `.venv/bin/python cad/verify_v01.py` → `21/21 checks passed`（12 solids、37 对干涉 0、STEP 回读 12）；`build/verify_report.json` 与 HEAD 一致（无脏 diff）；`square_model.py` `"FR-4 2-layer"` → `build/assembly/meta.json` 同值，meta mtime 20:26:56 **晚于**模型 20:26:49 |
| 8-4 | 新装配图：无 D1/Q1–Q3/TP1–TP6 且 47 footprint | **PASS** | 见 §8.2：`top.svg` 反解出**恰好 47 个位号**（43 器件 + H1–H4，与 pcbnew 完全一致），`FORBIDDEN=[]`；`top.png` 目视标题即「47 footprints (43 devices + 4 mounting holes)·28 nets·no LED / no test points」；`bottom.svg` 仅 8 个 THT 位号（H1–H4/J1/J2/J4/J5，装配面「mirrored, no parts」）；图 mtime 20:28 > 板 20:06 |
| 8-5 | `requirements.yaml` 的 freerouting/java/xvfb 可解析、无重复键 | **PASS** | PyYAML 6.0.2 + 自定义「重复键即报错」Loader：`parsed OK, no duplicate keys`；`freerouting='2.5.0'`、`java='25.0.4.1'`、`xvfb='2:21.1.4'`（`xvfb` 为带冒号字符串，解析正常） |
| 8-6 | `config/mechanical_params.yaml` 可解析、`electronics.display=0.91in_OLED` | **PASS** | 同一重复键 Loader：`parsed OK, no duplicate keys`；`electronics.display = '0.91in_OLED'`；`electronics.status = 'designed'` |
| 8-7 | DRC/ERC 结论未变（板未改） | **PASS** | 板 mtime 仍 20:06:42（与 commit 一致）；DRC 复跑 `Found 0 violations` + `Found 0 unconnected items`，`build/DRC_verify.rpt`（20:34:27）`** Found 0 DRC violations ** / ** Found 0 unconnected pads ** / ** Found 0 Footprint errors **`；ERC 独立复跑 0 Errors / 0 Warnings（sch 内容与 commit 一致） |
| 8-8 | 新文件存在且被正确引用 | **PASS** | `scripts/render_assembly.py`：`ast.parse OK`；`BOARD=…/smartcoaster_2l.kicad_pcb`（存在）、`OUT=…/build/assembly`、`if __name__` 保护；在 build.sh 解释器环境下 `import pcbnew, matplotlib` 均 OK；`build.sh:49` = `$PY render_assembly.py \| tail -1`（`PY=/data/Documents/tools/sim-venv/bin/python`）。`scripts/freerouting.settings.json`：合法 JSON（`profile.allow_telemetry=false`、`usage_and_diagnostic_data.disable_analytics=true`、`api_server/mcp_server.enabled=false`）；`route_2l.sh:48-52` 首跑守卫 `if [ ! -f … ] cp …/freerouting.settings.json → …/freerouting.json` |
| 8-9 | BLE 0xFF04 电量修复（附加代码核对） | **PASS** | `ble.h/ble.c`：`ble_update(..., uint8_t battery_pct)` + `s_batt = battery_pct > 100 ? 100 : battery_pct`；`app_main.c:392` 传入 `battery_percent(app->bat.millivolts)`；bin +32 B 与「修复 +32 B」记录自洽 |
| 8-10 | 文档/配置校准（`firmware/REPORT.md` 的 ble.c「桩」旧表述等） | **PASS（Lead 修复后复检；修复前曾 FAIL，见 §8.6）** | 修复前 FAIL 证据存于 §8.4；复检证据见 §8.6：§7.1 的 4 条旧「桩/未做」已移出并加 20:45 注记，`docs/06:111` 已同步，全文 `grep "桩"`=0 |

**增量复核小结（最终，含 8-10 修复后复检）：10/10 PASS。** 此前 §1–§7 的 7/7 PASS 结论不变。

## 8.2 装配图 47 footprint / 无删件残留的客观证据

装配图 SVG 是 matplotlib 路径字体（正文为 `<use>` 字形 id `DejaVuSans-<hex>`；位号为 Bold 字形）。按字形码反解 `top.svg`/`bottom.svg`：

```
top.svg    bold ref tokens: 47
['C1','C10','C11','C12','C13','C14','C15','C16','C2','C3','C4','C5','C6','C7','C9',
 'H1','H2','H3','H4','J1','J2','J3','J4','J5',
 'R1','R10','R11','R12','R2','R25','R26','R3','R4','R5','R6','R7','R8','R9',
 'SW2','SW3','U1','U2','U3','U4','U5','U6','U7']
FORBIDDEN refs in drawing: []
bottom.svg bold ref tokens: 8  ['H1','H2','H3','H4','J1','J2','J4','J5']
FORBIDDEN refs in drawing: []
```
- 47 = **43 器件 + H1–H4**，与 pcbnew 读板结果完全一致：`COPPER_LAYERS: 2 | FOOTPRINTS: 47 | FORBIDDEN: [] | TRACKS: 576 VIAS: 62`。
- 标题文字亦反解为：`SmartCoaster 2-layer — TOP assembly / 47 footprints (43 devices + 4 mounting holes) · 28 nets · no LED / no test points · 1:1 mm`，来源注明 `from smartcoaster_2l.kicad_pcb`。
- 结论：旧 4L 时代带 D1/Q1–Q3/TP1–TP6 的装配图已被 2 层 47 footprint 版替换。

## 8.3 并发改动观察（不影响本轮 PASS/FAIL，但 commit 前需 Lead 确认）

复核窗口内（20:34:35–20:36:33）工作区新增/变化了以下 **Lead 清单之外**的文件（复核开始时 `git status`=25 项，结束时=32 项）：

| 文件 | mtime | 说明 |
|---|---|---|
| `VALIDATION_PLAN.md` | 20:34:35 | 文本收尾（+「S5 实物（用户侧）」待做项，事实口径正确） |
| `docs/01_AI_Hardware_Engineering_Pipeline.md` | 20:34:35 | 文本收尾；bin 已同步为 **519,184 B** |
| `docs/02_Smart_Coaster_PRD.md` | 20:34:40 | 文本收尾 |
| `electronics/README.md` | 20:34:35 | 文本收尾 |
| `electronics/kicad/DECISIONS.md` | 20:34:35 | 文本收尾 |
| `mechanical/hy928d/notes.md` | 20:34:35 | 文本收尾 |
| `docs/REPORT_技术报告.md` | 20:36:33 | 新文件（并发审计产物，未跟踪） |

另：`docs/AUDIT_ENV.md`、`docs/AUDIT_PIPELINE.md`、`docs/AUDIT_PRD.md` 为并发审计 agent 的产物（开始于 HEAD `ae17e10`、工作区干净时）；其中记录的 bin 为 **519,152 B（修复前快照）**，与当前 519,184 B 相差 +32 B。若这些文件要提交，建议标注「审计时快照，bin 随后 +32 B」，避免与最终状态冲突。

## 8.4 8-10 修复前 FAIL 详情（Lead 已按建议修复，复检 PASS 见 §8.6）

**证据（只读检查，均为当前工作区内容）**：

1. `firmware/REPORT.md:384`（§7.1「明确未做」表）：

   ```
   | BLE GATT | **桩** | `ble_init` 返回 `ESP_ERR_NOT_SUPPORTED`；App 配对/同步不可用 |
   | NVS 持久化 | 未做 | 今日累计、杯皮重、目标、提醒间隔重启即丢；跨日清零未接 |
   | 功耗/休眠 | 未做 | 未启用 light sleep；HX711 连续供电（设计估算 ~42 mAh/日） |
   | OLED 中文 | 未做 | 仅 5×7 ASCII；设计稿的中文标签需要字库模块 |
   ```
   但同一轮已把该文件 §2 表的 `ble.c` 行改成「NimBLE GATT（P1，270 行）…」；代码事实：
   - `firmware/esp32/main/ble.c:1-20,161`：NimBLE GATT，Service `0xFF00`（0xFF01 重量 / 0xFF02 今日 / 0xFF03 目标 / 0xFF04 电量 / 0xFF05 命令 / 0xFF06 时间）；
   - `firmware/esp32/main/storage.c:13,20,38`：`nvs_flash_init()` / `nvs_get_u32("today"/"goal")` → NVS 已实现；
   - `firmware/esp32/main/app_main.c:336-338`：`esp_pm_configure(... .light_sleep_enable = true)` → 休眠已实现（`sdkconfig` 亦有 `CONFIG_PM_*`）；
   - `firmware/esp32/main/oled.c:183` / `font_cn.h`：`oled_text_cn()` 中文已实现。

2. `docs/06_Firmware_Architecture.md:111`：

   ```
   - 待做：低功耗休眠、OLED 中文、真实 HX711/OLED/按键/电池 bring-up + 砝码标定。
   ```
   与同文件 107–110 行（BLE GATT / NVS / OLED 中文 / 时间跨日「已实现」表述）自相矛盾。

**影响**：纯文档一致性；本轮构建、host 测试、机械几何、装配图、DFM 均不受影响。
**建议（commit 前修）**：
- `firmware/REPORT.md` §7.1 把 BLE GATT / NVS 持久化 / 功耗休眠 / OLED 中文 移出「明确未做」（改标「已实现，见 §2/§5」），保留「实物标定 / HX711 时序未实测 / 外设仿真无 / 机械电子集成」等真实未做项；
- `docs/06:111` 的待做列表删去「低功耗休眠、OLED 中文」，只保留实物 bring-up 与标定项。

## 8.5 写入声明（本轮）

- 本轮只**追加**本节到 `docs/VERIFY_REPORT.md`；未改写 §1–§7。
- 复跑 DRC 按允许范围刷新 `electronics/kicad/build/DRC_verify.rpt`（内容 `0 violations / 0 unconnected / 0 footprint errors` 不变，仅 `Created on` 时间戳变为 20:34:27）。
- 复跑 `mechanical/square_v1/cad/verify_v01.py` 后 `build/verify_report.json` 内容与 HEAD 一致（`git status` 无 diff），即上一轮 F1 的刷新已被 commit `ae17e10` 包含。
- 其它复核产物（ERC 独立报告、host 构建、idf 构建日志）均在 `/tmp` 等临时位置，未落回工程目录；未修改任何被验收源码。

## 8.6 8-10 复检（Lead 修复后）：PASS

**8-10 复检（Lead 修复后，2026-11-04 20:45–20:47，只读）：PASS。** 逐条证据：

1. **`firmware/REPORT.md` §7.1 已无「桩/未做」矛盾**：
   - 原「BLE GATT（桩）/ NVS 持久化（未做）/ 功耗休眠（未做）/ OLED 中文（未做）」4 行已移除；
   - 新增 **20:45 更新注记**，明示 BLE GATT（`ble.c` NimBLE 0xFF00，270 行）、NVS（`storage.c`）、PM light sleep（`app_main.c` `esp_pm_configure(light_sleep_enable=true)`）、OLED 中文（`oled.c` `oled_text_cn()` + `font_cn.h`）**均已实现、已移出「未做」**；
   - 当前「明确未做」表只剩真实未做项：手机 App/BLE 手机侧、实物标定、HX711 时序（未实测）、外设仿真（无）、机械/电子集成。
2. **`grep -n "桩\|未做" firmware/REPORT.md` 与代码不矛盾**（实测输出）：
   ```
   380:### 7.1 明确未做
   385:> （`oled.c` `oled_text_cn()` + `font_cn.h`）**均已实现**。现已移出“未做”，当前仍未做的如下表。
   389:| 手机 App / BLE 手机侧 | 未做 | 固件侧 GATT 已实现；无手机 App；… |
   390:| 实物标定 | 未做 | `counts_per_g=515.4` 为 PROVISIONAL；… |
   393:| 机械/电子集成 | 未做 | 按键/屏位置按 `electronics/pinmap.md` 草案，未上板 |
   ```
   全文 `grep -c "桩"` = **0**；另 391/392 行「HX711 时序 | 未实测」「外设仿真 | 无」亦为真实未做，与代码一致（不涉及已实现的 BLE/NVS/PM/中文）。
3. **`docs/06_Firmware_Architecture.md:111` 已同步**：
   `- 待做：**手机 App / BLE 手机侧**、真实 HX711/OLED/按键/电池 bring-up + 砝码标定（PM light sleep 与 OLED 中文已实现，见上）。`
   与同文件 107–110 行（BLE GATT / NVS / OLED 中文 / 时间跨日「已实现」）一致，无内部矛盾。
4. **AUDIT 快照注记已加**：`docs/AUDIT_PRD.md:3`、`docs/AUDIT_PIPELINE.md:3` 顶部均有「审计快照注记（2026-11-04 20:45 由 Lead 追加）：… bin 519,152 B… 现 → 519,184 B / 0x7EC10，不改变本报告任何判定」；`docs/AUDIT_ENV.md` 不含 bin 数字（无需注记）。
5. **bin 数字已统一为 519,184 B**：出现在 `README.md`、`firmware/REPORT.md`、`docs/HANDOFF.md`、`docs/01`、`docs/05`、`docs/06`、`docs/REPORT_技术报告.md`、`docs/REPORT_成果展示.md`、`docs/AUDIT_PRD/PIPELINE.md`（注记）、`docs/VERIFY_REPORT.md` §8（共 11 个 md）。`519,152` 仅存于：AUDIT 快照注记与审计表（已注明「审计时值」）、以及本报告 §5（上一轮历史记录；§8.1 已声明「以下 §8 为准」，符合「不改写 §1–§7」要求）。
6. **报告引用的链接/图片路径均可解析**（脚本解析 markdown `[](...)` 并校验相对路径存在性）：
   - `docs/REPORT_技术报告.md`：13/13 本地链接存在（含 5 张图：机械前脸、`pcb_2l.png`、`ui_screen.png`、`CMF_variants.png`、FEA 图）；
   - `docs/REPORT_成果展示.md`：19/19 本地链接存在（含 12 张图：hero/front/exploded/CMF/sch/pcb/assembly top/FEA/UI/packaging/print 等）；
   - `README.md`：19/19 存在（含指向 `docs/REPORT_技术报告.md`/`REPORT_成果展示.md`/`AUDIT_*`/`VERIFY_REPORT.md` 的索引链接）；
   - `docs/HANDOFF.md`：无本地 markdown 链接（仅行内路径文字，抽查 `docs/REPORT_技术报告.md` §7 存在）。
7. **报告索引已加入**：`README.md` 顶部「报告与审计（2026-11-04）」列出技术报告/成果展示/3 份审计/独立验收；`docs/HANDOFF.md:15` 新增「报告与审计（20:40 追加）」索引段。

**8-10 复检结论：PASS；§8 最终 10/10 PASS。**
