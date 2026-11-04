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
