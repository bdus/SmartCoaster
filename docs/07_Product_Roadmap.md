# 产品路线：先“能用”，再“红点级”

> 2026-11-04 起。G0（可行性）已完成；下面按 **P1 可用 → P2 可制造 → P3 红点级** 迭代。

## P1 — 能用（当前目标）

**功能**
- [ ] PCB 0 short / 0 unconnected；ERC/DRC 干净（丝印可豁免，需记录）。
- [ ] 手板：按 `tests/handboard/BRINGUP_RECORD.md` 记录（线性/噪声/杯事件/凸台/光导/功耗/BLE）
- [ ] 砝码标定：零点、量程、重复性、噪声、温漂记录。
- [x] NVS 持久化（today/goal/tare/mode，跨重启；`idf.py build` 通过，bin 250 KB）
- [x] BLE GATT（NimBLE 0xFF00：重量/今日/目标/电量/命令）
- [x] 跨日时钟（BLE 0xFF06 写 Unix 秒，自动 reset + NVS）
- [x] OLED 8 s 息屏（按键/放杯/提醒唤醒）
- [x] PM 自动 light sleep + BT modem sleep + 广播占空（预计 2–3 mA，7 天级；实测待手板）
- [x] OLED 中文（16×16 字库子集 26 字 + 混合 2× ASCII，128×32 单行 + 进度条）
- [x] 广播占空（开机 30 s / 配对 120 s / 空闲关）
- [ ] 整机装配：四角凸台共面、+y 预紧、浮动间隙 0.156 mm 余量、限位。
- [ ] 连续 7 天饮水记录不丢数、不误触发。

**外观（可用级）**
- [x] 前脸：屏 26×7、键 x=17
- [x] **光导进 CAD**：窗周 0.8 mm halo 框 + 左前缘 1.5 mm 灯线 + 内部 2×2 mm 导光条（从 D1 到窗），PMMA clear；13 件 **21/21**，导光件 307.5 mm³/0.4 g
- [ ] halo 均匀性实测（单 LED + 57 mm 光导；P3 双灯/匀光）
- [ ] 顶板/底壳配合、无段差、按键手感。
- [ ] 3D 打印首件（外壳 + 顶板）验证屏/键/传感器配合；光导件用 PMMA（非 FDM）。

## P2 — 可制造

- [ ] PCB 层数决策：2 层（成本）vs 4 层（内层 GND/电源，HX711 模拟更干净、布线更稳）。
- [ ] LED/灯导位置与 halo 均匀性（D1/D2 当前远离屏窗，需移到窗两侧或改导光）。
- [ ] DFM：线宽/间距/孔环/阻焊桥；Gerber/钻孔/BOM/坐标文件。
- [ ] EMC/ESD、USB-C、充电、电池保护。
- [ ] 外壳公差、卡扣/螺钉、防水/防滑、跌落。
- [ ] 认证评估（CE/FCC/ RoHS）与包装。

## P3 — 红点级

- [ ] CMF：阳极氧化铝/深紫哑光、石墨灰、荧光绿点缀；材质样板。
- [ ] 光：360° halo 均匀、无热点；屏幕 UI 字体/动效/水位动画。
- [ ] 细节：分模线、logo、隐藏螺钉、导光条、按键字符。
- [ ] 交互：单击看进度、放杯/拿杯事件、提醒节奏、App 视觉。
- [ ] 叙事：场景图、爆炸图、包装、可持续材料说明。
- [ ] 评审：红点申报材料（照片/渲染/说明）。

## 当前 PCB 状态（2026-11-04，P1 4 层版本）

- **P1 板：4 层（F/In1/In2/B），0 short / 0 unconnected**；693 track/via；46 项全部是丝印 warning（位号重叠/压铜），电气性 0 error。
- 关键简化：P1 先用 **1 颗 RGB LED + 光导**（去掉 D2/R22–R24），把 LED 簇放到左臂、Q1–Q3/R19–R21 紧贴 LED；Freerouting 2.5 一次 0 unrouted，导入后仅 6 处 LED pad 未落点，手工补 6 条 2.4–2.7 mm 短线后 **0 unconnected**。
- 光导：D1 在左臂（CAD −32,+7），屏窗在前左（−8,−50），需要 ~57 mm 光导；P1 先用亚克力导光条，P3 再做双 LED/均匀光环。
- 丝印 46 项已按项目 DRC severity 设为 ignore（非电气，记录在案）；USB_DP/DM 0.125 mm 为 90Ω 差分，min_track_width 0.125。
- **DRC 最终：0 violations / 0 unconnected**（`build/DRC_p1_final.rpt`）。
- 制造文件：`build/gerbers/`（F/In1/In2/B + mask/paste/silk/edge）、`.drl`、`.pos`、`smartcoaster_4l_gerbers.zip`。
- **P2 打样就绪**：U1 官方 **ESP32-S3-MINI-1** 封装；U1 移到 (29,−32.0) 与机械 (29,+32.0) 对齐（模块后缘 +39.75 < 壳腔 +40）；4 层 **0 unconnected / 0 short / 0 DRC**；Gerber/drill/pos/zip 已重出。
- 机械：ESP32 占位体同步，`verify_v01.py` **21/21**；渲染已更新。
- **DFM 自查（JLC 4 层）**：线宽 0.125≥0.09、过孔 0.3/0.6 环宽 0.15≥0.13、板边 0.3、4 层——全部 **PASS**（`build/DFM.md`，`scripts/dfm_check.py`）。
- BOM 33 行；17 行 passive 缺 MPN（手焊可用值/封装；贴片需补 LCSC 编号）。
- **装配包**：`docs/09_Assembly.md` + `build/assembly/top.pdf/bottom.pdf` + `.pos`（56 贴装件全在顶面；TP1–6 不贴）；拼板建议 2×2 V-groove。
- 修复：U1 的 footprint 引用原为 `REF**`（pos/BOM/装配图识别不到），已在 `gen_pcb.py` 修正并更新板。
- 2 层历史版本保留在 `smartcoaster_routed.kicad_pcb`（0 short / 12 unconnected），仅作对比。

## 判定

- “能用”：P1 全部勾选 + 手板 7 天数据。
- “红点级”：P1/P2 完成 + P3 的 CMF/光/细节/叙事达到可送审质量。

## Round 2 记录（2026-11-04）

- 尝试 1：把 R19–R24/Q1–Q3 贴到 D1/D2 旁，重布线 → 12 unconnected 不变，且 D1/R15、Q1/R14 等 courtyard 冲突，回退。
- 尝试 2：给 D2 加本地驱动 Q4–Q6（schematic ERC 0、网表 PASS，69 器件/46 网络）→ 右侧臂放不下 3 颗 SOT-23（越界/与 J5/R25 冲突），PCB 未成，回退。
- 结论：**12 unconnected 是 C 环拓扑问题**——D2 在右前，阴极网必须从左下的 Q1–Q3 绕过整个 C 环；2 层/4 层都在最后一跳失败。
- 下一轮方案：**把 D1/D2 都放到同一侧臂**（前左），共用 Q1–Q3 本地驱动，光导把光送到屏窗；再重布线。必要时 Q4–Q6 本地驱动只保留一组。

## P3 进展（2026-11-04）

- CMF：`docs/10_CMF_and_Packaging.md`（Lumen Violet 主色 + Moss/Sand/Graphite 变体）；4 个变体渲染 `render/cmf/`。
- 叙事：`docs/11_Product_Narrative.md`（一句话/问题/洞察/设计/体验/可持续/规格）。
- 包装：120×120×36 天地盖 + 纸浆模塑内衬已出 3D/STEP/STL + 3 张渲染（`render/packaging/`）。
- 光：**Y 光导**（单 LED + 左上/底部两路出光，估算 1.4:1）进 CAD，21/21；双 LED 留 P4。分析见 `docs/12_Light_Analysis.md`。

## P3 提交包（2026-11-04）

- `submission/`：4 张主图 + `SmartCoaster_Story.pdf`（A3 300dpi）+ 可复现 `make_story.py`。
- 故事：问题/洞察/设计（重量即输入 + Y 光导）/体验/可持续/规格/CMF。
