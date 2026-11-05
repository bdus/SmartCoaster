# HANDOFF — SmartCoaster（2026-11-04 第二轮，交接给下一个 AI）

> 先读：`AGENTS.md` → `docs/01_AI_Hardware_Engineering_Pipeline.md` → `docs/07_Product_Roadmap.md` → 本文件。
> 上一份 HANDOFF 的卡点（DSN pad 类型 / Freerouting 空 SES）**已解决**，本轮把 2 层 PCB 布到了 **0 DRC / 0 unconnected**，并清完了 LED/光导在机械、固件、P3、文档里的残留。详见下文。
>
> **2026-11-05 增补（EasyEDA 第二实现，见 §0.0）**：新增 `electronics/easyeda/`，用 EasyEDA Pro 重做电路/PCB；原 KiCad 交付未动。

## 0.0 2026-11-05 增补：EasyEDA Pro 第二实现（电路/PCB 重做）

- **工具安装**（用户指定 `/data/Documents/tools/`）：`easyeda-agent` **v1.16.0**（CLI/daemon + connector 1.16.0）、LCEDA Pro **4.1.97**（4.1.97.04b092ac，Linux x64 便携）、官方 `easyeda-eprj3-skill` **2.2.1**、`easyeda-pro-format-skill` **1.0.0**、Node 24.15.0；详见 [`/data/Documents/tools/EASYEDA_INSTALL_NOTES.md`](../../tools/EASYEDA_INSTALL_NOTES.md)。
- **新目录** [`electronics/easyeda/`](../electronics/easyeda/README.md)（**不改** `electronics/kicad/`）：从冻结 KiCad 设计（`design.py` / `smartcoaster.net` / `2l.kicad_pcb`，只读）重建 EasyEDA `.eprj3`：
  - 原理图 47 器件 / 7 功能块 / 272 线 / 28 网络 + 45 个 NC；
  - validate **0/0**、lint **100/100**、placement DRC **100/100**、netcheck **213 pins / 0 unconnected**；
  - 与 KiCad 网表**逐脚对账一致**（168 connected pins / 28 nets），证据 `electronics/easyeda/reports/parity.log`；
  - 板框补丁为机械 C 形（93.2×93.2、R6、38×38 开口、80° 前 C 口）+ 4×M2 NPTH @(±40,±24)；pad 形状恢复为 KiCad 圆角矩形/椭圆/圆；预览 `electronics/easyeda/render/pcb_routed.png`；
  - **2 层铜 1:1 移植**：576 track（440 top + 136 bottom）+ 62 via，来自已验证的 KiCad 布线；独立 GEOS 检查 C1–C5 **全部 PASS**（C2 最小间距 7.938 mil ≥ 0.2 mm；C3 连通性 0 未连通；C4 板边最小 13.917 mil；C5 过孔 0.3/0.15 mm），证据 `electronics/easyeda/reports/copper_check.json`；
  - 独立网表审计（fresh reviewer ×2）`ok: true`（唯一 warn：`PROT_VDD` 未画电源 flag，advisory），证据 `electronics/easyeda/reports/audit_verdict.json`。
- **明确边界**：铜是**移植**，不是 EasyEDA 客户端重新布线；**无铺铜（GND plane）**、无客户端保存/重载/回读、无 Gerber/坐标。EasyEDA 客户端 live 链路（原生 ERC/DRC、自动布线、铺铜、导出）被**登录/激活墙**阻塞：客户端停在激活/Regist 窗、`pro.lceda.cn` 对本机 IP 返回 CloudWAF 418、`eda.js` 报 `BRIDGE_NOT_READY … command-space-missing`。**不要**把离线 PASS 当成客户端 live-verified 或成品板 PASS。
- **下一步（用户登录/激活后）**：`bash electronics/easyeda/scripts/client_checks.sh` → client sch DRC → netlist 复核 → 客户端打开/保存重载 → GND 铺铜 → 原生 PCB DRC → 截图/Gerber；再与 `electronics/kicad/build/` 的 0/0 对比。
- **技术栈调研**：[`docs/EDA_TOOLCHAIN_SURVEY.md`](EDA_TOOLCHAIN_SURVEY.md)（11 款 EDA + AI 接口；结论：KiCad 主链不动，EasyEDA 做第二实现，Web 在线版违反红线）。
- **复现**：`bash electronics/easyeda/scripts/build.sh`（提取→生成→5 门禁→板框/pad 补丁→移植铜→独立铜检查→对账→审计包→报告→渲染）。

## 0. 执行摘要（先看这里）

- 产品：方形智能杯垫 100×100×18。用户最终决定：**光导全部去掉、LED 全部去掉、PCB 最多 2 层**，前脸只留 **26×7 屏窗 + 按键**；顶板-底座 0.5 mm 是秤的浮动缝，不放光。
- **P1 设计闭环**：原理图 **43 器件 / 28 网络**、ERC **0 error / 0 warning**；2 层 PCB **47 footprint（43 器件 + H1–H4）、576 track + 62 via、28 网络、0 DRC / 0 unconnected**（`build/DRC_2l.rpt`）。
- **P2 可制造**：2 层 Gerber/钻孔/坐标/zip（`build/gerbers/`、`build/smartcoaster_2l_gerbers.zip`）、JLC 2 层 DFM 全 PASS（`build/DFM.md`）、布线预览 `build/pcb_2l.png`。
- **机械**：12 件（删光导件），壳体前脸灯槽/过孔已删，`verify_v01.py` **21/21**、37 组干涉 0、0.5 mm 浮动缝与过载限位保留。
- **固件**：halo（RGB PWM 灯环）代码全删；`idf.py build` 通过，bin **519,184 B / 0x7EC10**（删 halo 后 −13,808 B；修 BLE 电量特征 +32 B）；host **11/11**、mock **9/9**、C↔Python 差分 **16/16**、pytest **16**。
- **P3**：外观/CMF/包装/提交包全部按“无灯”用 Blender 4.5.3 重渲（`render/`、`submission/`），文档同步 43 器件。
- **独立验收**：`docs/VERIFY_REPORT.md`（verifier 本机复跑，非口头结论）**7/7 项 PASS**：PCB 0/0、ERC 0/0、Gerber/DFM、机械 21/21、固件测试与 bin、P3 无灯、事实性/红线。
- **报告与审计（20:40 追加）**：新增 `docs/REPORT_技术报告.md`（环境/设计/验证/**手动验收**/资产 + docs/01↔02 达成矩阵）与 `docs/REPORT_成果展示.md`；三份逐条审计 `docs/AUDIT_{ENV,PRD,PIPELINE}.md`（环境 15 版本一致；PRD 185 条 91 PASS/50 PARTIAL/28 GAP；流水线 146 项 71/46/28）。同时：修 BLE 0xFF04 电量特征（bin 519,184 B）、重出 2 层装配图（`render_assembly.py`）、补 `requirements.yaml`（Freerouting/Java/Xvfb）、关闭 Freerouting 遥测、校准 PRD/electronics README/DECISIONS/docs01 §13.3 等旧口径。
- **电路仿真与验证（21:15 追加）**：**S2 补齐**为四模块（桥路/HX711/电源/MCU 接口）× 六类分析（`.op/.dc/.ac/.tran/.noise/蒙特卡洛`），`simulation/electronics/run_s2.py` 约 8 s 复跑，28 结果 **21 PASS / 7 个真实发现**（详见 `docs/S2_CIRCUIT_SIM.md`）。由此：① **I2C 4.7k@400kHz 超时 → R3/R4 已改 2.2k**（同封装，ERC/DRC/BOM/Gerber 已重跑）；② **续航实际 5.02 mA→4.15 天**（旧 docs/08 漏算桥路 3.3 mA，已重写；7 天需模拟前端占空/断电或 1000 mAh）；③ 外部 RC 实际 530.5 Hz（旧 1.65 kHz 错）；④ TP4056 深放热调节、LDO dropout、电池分压漏流、铝顶板挡天线列为手板/下一版整改（`docs/REVIEW_ELECTRICAL.md`）。电气验证映射见 `docs/VERIFICATION_ELECTRICAL.md`。
- **下一阶段（2026-11-04 用户新指示）**：冻结机械结构与功能，只做外观变体。功能确认：**方形 square_v1 正常（21/21、12 件，与当前 43 器件/2 层板/0.91" 屏/无灯一致）**；**圆形 LUMEN 只是旧概念（含光导+12-LED 软板、0.49" 屏、无按键、17 mm、圆形 Ø102 PCB），不能直接当外观变体**；当前方形 PCB 对角线 **131.8 mm > Ø110**，真圆外观需重做 PCB（属功能变更）。冻结清单/允许变化/验收流程见 `docs/13_Appearance_Variants_Plan.md`；可迁移验收经验见 `docs/01` §16。
- **技术风险排序**：① M5 实物未做（用户侧）；② HY928D 供应商核实未关闭 + 线缆/电池固定收口缺失（M2）；③ S4/MCP 编排与 FEA 对象 B/C、S2 全量未做。逐条见 `docs/REPORT_技术报告.md` §7。
- **唯一未完成（用户侧）**：手板采购/装配/实物标定 + PCB 打样 + 3D 打印。仿真与主机测试通过 **≠** 实物通过。

## 1. 用户最新决定（以此为准，覆盖旧文档）

1. **光导全部去掉**：窗周 halo、前缘灯线、底部灯线、Y 分光、顶板-底座缝隙光环——都不要；
2. **LED 也去掉**（D1、Q1–Q3、R13–R21 已从原理图/PCB/BOM/固件删除）；
3. **PCB 最多 2 层**，必须清到 **0 DRC / 0 unconnected**（已达成）；
4. 前脸只留 26×7 屏窗 + 按键；顶板与底座那 0.5 mm 是秤的浮动缝，不放光；
5. 用户希望“在前端持续看到过程”，所以每步都留了命令结果/图。

## 2. 仓库与工具链

- 工作区：`/data/Documents/projects/SmartCoaster`
- 机械：agentcad 0.7.1 + build123d 0.10.0（`mechanical/square_v1/.venv`）；版本快照 **v6_square_v1**
- PCB：KiCad 9.0.9（`/data/Documents/tools/kicad`，`~/.local/bin/kicad-cli`、`~/.local/bin/kicad-cli`）
- 布线：Freerouting **2.5.0**（自带 Java 25 runtime，`/data/Documents/tools/kicad` 之外的 `.tools/freerouting/`）+ Xvfb（`.tools/xvfb/usr/bin/Xvfb`，无系统 Xvfb）
- 固件：ESP-IDF v6.1（`source /home/pi/.espressif/tools/activate_idf_v6.1.sh`）
- 仿真/渲染：FreeCAD 自带 ccx 2.22 + gmsh 4.13.1、ngspice 36、Blender 4.5.3
- KiCad Python 环境（DRC 以外的脚本会用到）：
  ```bash
  export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
  export XDG_CONFIG_HOME=$PWD/.tools/kicad-config
  export PYTHONPATH=/data/Documents/tools/kicad/usr/lib/python3/dist-packages
  ```
- **沙箱注意（本机 DSH 环境）**：每次 bash 调用有独立 `/tmp` tmpfs，所以 **Xvfb 必须和 Freerouting 在同一次调用里启动**；`XDG_*` 必须指到工作区内（`.tools/fr-home/...`），否则写 `/home/pi` 被拒。

## 3. 当前已验证状态（全部带证据）

| 项 | 状态 | 证据 |
|---|---|---|
| 原理图 | **43 器件 / 28 网络**；ERC **0 error / 0 warning** | `electronics/kicad/build/ERC.rpt` |
| 2 层 PCB | 47 footprint、211 SMD / 12 PTH / 6 NPTH、576 track + 62 via、28 网络、最小线宽 0.2 mm、过孔 0.6/0.3 | `smartcoaster/smartcoaster_2l.kicad_pcb` |
| 2 层 DRC | **0 violation / 0 unconnected**（`--severity-all`） | `electronics/kicad/build/DRC_2l.rpt` |
| 2 层 ERC/DRC 口径 | silk 重叠/压铜按项目 severity 豁免（与旧 4 层一致）；U1 的 `SmartCoaster` footprint 库已用 `fp-lib-table` 正确挂上（所以库告警也消失了） | `smartcoaster/fp-lib-table`、`smartcoaster.kicad_pro` |
| Gerber/钻孔/坐标 | 2 层 9 层 Gerber + `.drl` + `.pos` + `.gbrjob` + zip | `build/gerbers/`、`build/smartcoaster_2l_gerbers.zip` |
| DFM（JLC 2 层） | 线宽 0.2≥0.127、过孔钻 0.3≥0.2、环宽 0.15≥0.13、板边 0.3≥0.3、层数 2 —— 全 PASS | `build/DFM.md` |
| 机械 | **12 件**；21/21 checks、37 组干涉 0、0.5 mm 浮动缝、过载限位 | `mechanical/square_v1/build/verify_v01.log`、`verify_report.json` |
| 固件 | halo 已删；bin 519,184 B（0x7EC10）；host 11/11（41 checks）、mock 9/9（198 checks）、差分 16/16（82 records）、pytest 16 | `firmware/REPORT.md` |
| P3 | 渲染/提交包/CMF/包装全部按无灯重出；`grep 光导\|light_guide` 在 render/submission/packaging/README/BOM/docs(07,09,10,11) 为 0 | `render/RENDER_LOG.md`、`submission/` |
| 历史文档 | `docs/12_Light_Analysis.md` 保留 OBSOLETE 横幅；`electronics/kicad/REPORT.md`（P1 初稿 66 器件）加历史横幅 | 同文件 |

## 4. 本轮定位到的根因（重要，别再踩）

1. **上一份 HANDOFF 的“DSN 159 pin 全是 `[T]`、没有 `[S]`”是误判**：`grep "Rect\[.\]Pad"` 会把 `RoundRect[T]Pad` 里的 `Rect[T]Pad` 也匹配上，造成“162 个全是 [T]”的假象。DSN 里 SMD/THT 由 `[T]/[A]` 区分，Freerouting 能识别；**真正的问题是别的东西**（见 2）。
2. **真正的 DSN 解析错误：J4 的 value 里带双引号**（`OLED 0.91"`）。KiCad 写出 `(PN "OLED 0.91""")` 未转义，Freerouting 解析器错位后**静默错放了下一个 footprint（U2/HX711）**：U2 的 pad 被当成在别处，路由器把 3V3 直接穿过 U2 焊盘，并在导入后留下 U2 周边 14 个 unconnected。修复：`design.py` 里 J4 value 改成 `OLED 0.91in`，`route_2l.py export` 现在会断言 DSN 引号平衡。
3. **Freerouting 会输出少量 0.1874 mm 短线**（低于 0.2 mm 工程最小线宽）和 1 根悬空短线。`route_2l.py import` 把 <0.2 mm 统一加宽到 0.2；`clean` 用“同网络几何连通性”删悬空 stub（不是按 DRC 坐标盲删，盲删会误删相邻合法线段）。
4. **Xvfb + XDG 沙箱**：见 §2 注意。
5. **旧 4 层板能拿“0 DRC”是因为 4L 项目把 silk 类 warning 设成 ignore**；2 层沿用同一口径，并把 U1 的 footprint 库真正挂上（`fp-lib-table`），所以本轮 ERC 也变成 0 warning。

## 5. 关键文件与管线

| 文件 | 作用 |
|---|---|
| `electronics/kicad/scripts/design.py` | 原理图/网表唯一来源（43 器件 / 28 网络） |
| `electronics/kicad/scripts/gen_sch.py` | 生成 `.kicad_sch` + `.kicad_pro` + `sym-lib-table` + `fp-lib-table` |
| `electronics/kicad/scripts/gen_pcb.py` | 生成未布线 PCB（placement + footprint，2 层） |
| `electronics/kicad/scripts/route_2l.sh` | **2 层布线总入口**：导出 DSN → Xvfb+Freerouting → 导入 SES → 加宽/清悬空 → DRC |
| `electronics/kicad/scripts/route_2l.py` | 上者的 export / import / clean 三段（含 DSN 引号自检） |
| `electronics/kicad/scripts/build.sh` | **全流程**：原理图→ERC→PCB→布线→DRC→BOM→Gerber/钻孔/坐标→DFM→预览 |
| `electronics/kicad/scripts/dfm_check.py` | JLC **2 层** DFM 自查（已从 4 层切到 2 层） |
| `electronics/kicad/scripts/render_routed.py` | 布线预览 `build/pcb_2l.png`（F.Cu 红 / B.Cu 蓝 / via 黄） |
| `electronics/kicad/smartcoaster/smartcoaster_2l.kicad_pcb` | **当前 2 层已布线板（主交付）** |
| `electronics/kicad/smartcoaster/smartcoaster_4l.kicad_pcb` | 历史 4 层板（含 TP，**仅存档，不是主方案**；其 gerber 已从 `build/gerbers/` 移除） |
| `mechanical/square_v1/cad/square_model.py` | 机械唯一来源（12 件） |
| `mechanical/square_v1/cad/verify_v01.py` | 21 项自检（12 件 / 37 对干涉） |
| `firmware/esp32/` | ESP-IDF 固件（halo 已删） |
| `tests/firmware/run_host_tests.sh` | host + mock + 差分 + pytest |
| `simulation/electronics/` | **S2 电路仿真**：`run_s2.py` + `models/` + `results/`（28 JSON）+ `figs/`（15 图） |
| `docs/S2_CIRCUIT_SIM.md` / `docs/REVIEW_ELECTRICAL.md` / `docs/VERIFICATION_ELECTRICAL.md` | S2 汇总 / PCB 电气评审 / docs/01 §9 电气验证矩阵 |
| `docs/13_Appearance_Variants_Plan.md` | **下一阶段外观变体计划**：功能确认、冻结清单、允许变化、圆形可行性、每变体验收流程 |
| `docs/01` §16 | **跨产品验收注意事项/失败模式清单**（环境/机械/电子/固件/视觉/一致性/合规） |
| `tests/handboard/BRINGUP_RECORD.md` | 手板记录表（已无灯光项） |
| `docs/07_Product_Roadmap.md` | 阶段与判定 |
| `submission/` | Red Dot 提交包（无灯版） |

## 6. 常用命令

```bash
# 全流程：原理图 → ERC → 未布线 PCB → 2 层布线 → DRC 0/0 → BOM → Gerber/DFM → 预览
cd electronics/kicad/scripts && PATH=$HOME/.local/bin:$PATH ./build.sh

# 只重布线（沿用已生成 DSN/SES 可加 --keep）
cd electronics/kicad/scripts && ./route_2l.sh

# 独立 DRC
export LD_LIBRARY_PATH=/data/Documents/tools/kicad/usr/lib/x86_64-linux-gnu
export XDG_CONFIG_HOME=$PWD/.tools/kicad-config
~/.local/bin/kicad-cli pcb drc --format report --severity-all --units mm \
    -o build/DRC_2l.rpt smartcoaster/smartcoaster_2l.kicad_pcb

# 机械
cd mechanical/square_v1 && .venv/bin/python cad/verify_v01.py

# 固件
source /home/pi/.espressif/tools/activate_idf_v6.1.sh && cd firmware/esp32 && idf.py build
bash tests/firmware/run_host_tests.sh
```

## 7. 未完成任务（用户侧，AI 不能代替）

1. **手板**：采购 ESP32-S3-DevKitC-1、0.91" OLED、HY928D、HX711 模块、砝码；按 `docs/09_Assembly.md` 装配，按 `tests/handboard/BRINGUP_RECORD.md` 标定（灵敏度/温漂/回差必须实物标定，`counts_per_g=515.4` 仍是 PROVISIONAL）。
2. **打样**：PCB 用 `build/smartcoaster_2l_gerbers.zip` 下单（JLC 2 层常规工艺）；外壳/顶板用 `mechanical/square_v1/build/parts/*.stl` 3D 打印；打印后目检前脸（旧灯槽位置现在是实心 2.4 mm 前壁）。
3. 若要做认证/红点送审，按 `docs/10`、`docs/11`、`submission/` 补充实物照片。

## 7.5 下一阶段：外观变体（2026-11-04 用户新指示）

> 用户决定：**冻结机械结构与功能，只针对外观多设计几个风格**。细化计划见 `docs/13_Appearance_Variants_Plan.md`。

### 7.5.1 功能确认结果（已实测）

| 外观线 | 自检 | 是否当前功能 | 结论 |
|---|---|---|---|
| 方形 `square_v1` | **21/21**（12 件、100×100×18、0.5 mm、37 对干涉 0） | ✅ 与 43 器件/2 层板/0.91" 屏/单键/无灯一致 | **作为冻结功能基线** |
| 圆形 `lumen` | 21/21（13 件、110×110×17、0.6 mm、38 对干涉 0） | ❌ 含 `guide` 光导 + `ledflex` 12-LED、0.49" 屏、**无按键**、圆形 Ø102 PCB、60° C 口 | **旧概念，仅供外观语言参考，禁止当功能基线** |

**关键结论**：当前方形 PCB 93.2×93.2 对角线 **131.8 mm**；真正圆形外壳装下它至少 Ø≈138 mm（含壁/间隙），与 Ø110 目标矛盾 → **真圆 = 重做 PCB + 重新验证（功能变更，另立项）**；本轮外观变体限定在“同一包络内的外形语言 + CMF/窗/键/表面”。

### 7.5.2 冻结清单（不可变）

- 总高 18.0（底壳 14.5 + **浮动 0.5** + 顶板 3.0）；过载限位 0.5 mm 先接触（≈7.28 kg）。
- HY928D 34×34×1.0 @z5、4 角 boss Ø6、Ø6 传力柱 z6→15、中央垫块 Ø12×0.8。
- PCB 93.2×93.2×1.6、R6、38×38 开口、80° C 口、4×M2 @(±40,±24)、z5。
- OLED 模组 38×12、**可视窗 26×7、中心 x=−8、窗中心 z=8.0**；按键 Ø8.2、x=17、z=7.2；USB-C 后缘居中 z6.6；电池 25×30×5 @(−32,24)。
- 天线净空：U1 @(29,32) 天线区不得有金属（或必须实测证明）；**无 LED/光导/灯缝**。
- 外观件不得跨浮动缝、不得成为称重旁路、不得遮挡窗/键/USB-C。

### 7.5.3 允许变化（外观轴）

外轮廓（方形 R8 / 方圆 R20–R40 / 倒角 / 胶囊，≤110×110 包络）、顶板材质与 CMF、窗 bezel/玻璃、按键帽、底壳腰线/垫脚、logo/纹理、包装图形。**每个变体必须保持冻结清单不变**。

### 7.5.4 每变体验收流程

① 把 `square_model.py` 拆成 `build_internals()`（冻结）+ `build_skin(params)`（可变）；② 与基线做功能区坐标 diff（容差 0）；③ 复用 21 项功能自检（浮/行程/限位/干涉/STEP 回读）；④ 外观专项（窗可视区、按键可达、USB-C 插头、天线金属、包络/包装、桌面稳定）；⑤ 渲染 + `docs/10`；⑥ 独立复核；⑦ 更新文档并 commit。详见 `docs/13` §6。

### 7.5.5 待用户决策

1. 外观路线：**squircle/胶囊（推荐，纯外观）** 还是 **真圆（需重做 PCB，另立项）**？
2. 变体优先级：建议先做 1 个（Soft Square R28）跑通全流程，再批量 C/D + CMF。

## 8. 用户偏好与红线

- 只用本地/免费工具；不把项目文件传到第三方；不装 CalculiX/Gmsh（用 FreeCAD 自带 ccx/gmsh）。
- 机械版本独立（`mechanical/lumen`、`mechanical/square_v1`），不跨项目改几何；`ref/`、`mechanical/original_cad/` 只读。
- 未确认尺寸标 `PROVISIONAL`，改完必须复跑 `verify_v01.py`。
- 仿真通过 ≠ 实物通过；灵敏度/温漂/回差必须手板标定。
- 外观：前脸干净，不要白色灯缝；唯一缝隙是顶板-底座浮动缝。
- **不要做**：
  - 不要把 LED/光导加回来（用户明确不要）；
  - 不要把 4 层当主方案（用户要求最多 2 层；4 层文件只作存档）；
  - 不要在没有 DRC 报告证据时说“0/0”；
  - 不要把空 SES / 0 unrouted 当成“布通”（本轮用 SES 大小 + track/via 数 + DRC 0/0 三重校验）；
  - 不要代替用户做手板采购/装配/标定；
  - **外观变体不得改动 §7.5.2 冻结清单**（浮动/传力/限位/PCB/屏/键/USB-C/天线）；不得引入 LED/光导；
  - 不要直接把 `mechanical/lumen` 当当前功能基线（它是旧概念）。

## 9. 验收标准（本轮已达成，下一位 AI 交回时以此为准）

- [x] `smartcoaster_2l.kicad_pcb`：`kicad-cli pcb drc --severity-all` **0 DRC / 0 unconnected**（`build/DRC_2l.rpt`，复制自 `build.sh` 末次运行）；
- [x] 原理图 ERC **0 error**（实际 0 error / 0 warning，`build/ERC.rpt`）；
- [x] 2 层 Gerber/钻孔/坐标/zip 已重出（`build/gerbers/`、`build/smartcoaster_2l_gerbers.zip`），`build/DFM.md` 为 2 层版本；
- [x] 机械删光导后 `verify_v01.py` **21/21**（12 件 / 37 对）；
- [x] 固件 `idf.py build` 通过、host 11/11 + mock 9/9 + 差分 16/16，halo 已删；
- [x] `render/square_b`、`render/cmf`、`render/packaging`、`submission/` 不再出现光导/LED；
- [x] 工作区已 commit（见 `git log` 最新一条；本轮为一次性收口提交）。

### 9.1 外观变体阶段（下一轮）验收

- [ ] 冻结清单（`docs/13` §2）零改动：功能区坐标 diff = 0；
- [ ] 每个变体通过 21 项功能自检（浮 0.5 / 行程 / 限位 / 干涉 0 / STEP 回读）；
- [ ] 窗可视区 26×7 无遮挡、按键可达、USB-C 插头空间、天线区无金属；
- [ ] 外轮廓在包装 120×120 内、桌面稳定；
- [ ] 渲染与 CMF/`docs/10` 一致，独立复核通过，文档/HANDOFF/README 更新并 commit。
