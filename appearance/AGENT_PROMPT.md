# appearance/AGENT_PROMPT — 给未来 AI agent 的一键编译提示词

> 用法：把下面「主提示词」整段复制给新 agent（本仓库会话即可），再按需附加一个「变体」。
> 提示词假设 agent 能读写本仓库；**工具/字段名保持英文**，其余中文。
> 事实来源：[`appearance/INPUTS.md`](INPUTS.md)、[`appearance/config/appearance_project.yaml`](config/appearance_project.yaml)、
> [`appearance/README.md`](README.md)。

---

## 主提示词（复制这段）

```text
你在 SmartCoaster 仓库（/data/Documents/projects/SmartCoaster）负责 appearance/ 的 IP 印花 →
多材料打印流水线。目标：把用户要的输入补齐到唯一配置，然后用一条命令编译出全部产物，
并用真实命令输出作为证据。不要凭记忆编数字。

【先读，不要跳过】
1. appearance/INPUTS.md                 —— 输入契约、什么能只改配置、什么不能
2. appearance/config/appearance_project.yaml —— 唯一输入源（schema 在文件头）
3. appearance/README.md                 —— 全流程原理/工程要求/失败模式
4. appearance/PRINT_DELIVERY_SPEC.md    —— 打印姿态与验收断言
5. docs/HANDOFF.md §10–11               —— 验收边界与已知限制

【第一步：向用户要输入】
按 INPUTS.md §1 逐项确认，缺一不可：
- 印花拼版图（PNG/JPG，RGB）路径；两枚/多枚图形各自的 crop（ellipse: cx,cy,rx,ry 或 bbox: x0,y0,x1,y1）。
  如果用户只给图不给 crop，你必须用脚本量出真实 bbox，不要目测猜。
- 每版色板（bottom-up，index 0 = 底料；数量 = 物理层数）与量化 tuning（contrast/saturation）。
- 顶板 STEP 路径（必须已在 mechanical/<project>/build/parts/，只读导入，不重建）。
- rim_z、pocket_dia、print_dia、interference、top_gap、CMF style、bed 尺寸、是否有按键。
- 目标：只换印花（config-only）还是要换外壳/几何（非 config-only，见 INPUTS.md §4）。

【第二步：放文件 + 改 YAML】
- 图放到 appearance/src/（或用户给的位置），把路径写进 versions.<v>.art.image。
- 顶板 STEP 放到 mechanical/<project>/build/parts/plate_v01.step，路径写进
  versions.<v>.shell.plate_step，同时写 mech_label / label / rim_z_mm。
- 只改 appearance/config/appearance_project.yaml；不要手工拼阶段命令，不要改
  mechanical/**、render/print/**、appearance/render/**、appearance/kromacut/**、
  appearance/tools/acceptance_check.py（冻结/Lead 所有/只读）。
- 若用户要改色数、layer_height、rim/floor、pocket/print 直径、interference、top gap、bed、
  CMF style 或版本名/印花名：这些不是 config-only。先按 INPUTS.md §4 列出需要同步的硬编码
  文件/常量，向用户说明并等待确认；不要假装只改 YAML 就能过验收。

【第三步：先 dry-run】
cd /data/Documents/projects/SmartCoaster
bash appearance/compile.sh --dry-run
- 必须看到 validation 全 PASS 且 RESULT: PASS（dry-run 不写任何文件）。
- 失败时按报错里的 "-> 处置" 修；报错会点名「改哪个文件哪个常量」。修到 dry-run 通过为止。

【第四步：一条命令编译】
bash appearance/compile.sh
- 会依次跑 art → convert → shell → render (run_all 1/4–3/4) → print (4/4) → acceptance。
- 必须真实等到结束；每阶段状态/耗时记录在 appearance/build/COMPILE_REPORT.json / .md，
  完整日志 appearance/build/compile.log。

【必须达到的 gates（缺一不算完成）】
- bash appearance/compile.sh --dry-run 通过（报告 validation N/N，零写入）。
- bash appearance/compile.sh 退出码 0；6 个阶段全部 ok。
- 最终 acceptance = 140/140 PASS（appearance/build/ACCEPTANCE.json passed==total，failed==0）。
- 关键产物存在且与配置一致：
  appearance/build/art/<art>/art.json、layer_counts.bin；
  appearance/build/print/<art>/manifest.json + 3MF + 逐耗材 STL；
  appearance/build/shell/shell.json（rim/floor/pocket/print/thickness/depth 与配置派生一致）；
  appearance/render/{round,square}/ 5 张 PNG + scene.blend；
  render/print/stl/ 18 个 STL + CHECKSUMS.sha256 + delivery.json；
  appearance/build/COMPILE_REPORT.json / .md。
- 若改了任何数字，必须重新核对 shell.json/manifest 与 YAML 派生值一致。

【汇报格式（给 Lead/用户）】
- 输入：改了哪些 YAML 键（旧值 → 新值）；新增/替换的文件路径。
- 命令：实际执行的完整命令 + 退出码。
- 证据：dry-run 校验数、每阶段耗时、total、acceptance 140/140、COMPILE_REPORT 路径。
- 兼容性：若改了脚本，说明无 --config 路径是否仍复现旧输出（art.json / shell.json 数值不变）。
- 限制：哪些改动不是 config-only、哪些仍未实物验证（打印/切片/颜色/强度/FEA）。
- 不要声称“已验证实物/切片”，除非真的跑过。

【停止条件（遇到就停下并报告，不要猜/绕过）】
1. 缺输入（图/crop/色板/STEP/rim 等）或用户要求与冻结清单冲突（docs/HANDOFF.md §7.5.2）。
2. 需要改不可写/冻结文件，或需要改 Lead 验收基线（acceptance_check.py）。
3. 工具缺失/版本不符（Node ≥22、Blender 4.5.3、build123d 0.10.0 venv、Kromacut 4.2.0 桥接）。
4. dry-run 的阶段常量校验指出 config 与硬编码不一致，而用户不接受同步这些文件。
5. 全量编译后验收不是 140/140：保留报告与日志，报告失败项，不要修改验收脚本让它变绿。
```

---

## 变体 A：只换印花（最小动作）

```text
只换印花，不改外壳/几何。按 appearance/INPUTS.md §2 的 5 步走：
1) 把新拼版图放 appearance/src/；
2) 只改 appearance/config/appearance_project.yaml 的 versions.<v>.art
   （image / crop / palette_bottom_up / tuning；色数尽量保持 6/7 不变）；
3) bash appearance/compile.sh --dry-run 通过；
4) bash appearance/compile.sh 全跑，确认 140/140；
5) 汇报量化对照图（art_source_crop/art_rgba/art_board）、每阶段耗时、COMPILE_REPORT。
若用户要改色数（6↔7）：先按 INPUTS.md §4 说明这不是 config-only（需同步 expect、
验收基线、槽深/打印姿态），等用户确认后再动。
```

## 变体 B：换外壳 / 新顶板

```text
换外壳/顶板。前提：外观变体不得改动 docs/HANDOFF.md §7.5.2 冻结清单，顶板必须是已验证 STEP。
按 appearance/INPUTS.md §3 的 5 步走：
1) 顶板 STEP 放 mechanical/<project>/build/parts/plate_v01.step（只读导入，不重建）；
2) 改 versions.<v>.shell：plate_step / mech_label / label / rim_z_mm；
   若 pocket_dia/print_dia/interference/top_gap 不变，保持原值；
3) bash appearance/compile.sh --dry-run：
   - STEP 顶面必须等于 rim_z_mm，否则 build_recessed 会 assert rim top mismatch；
   - 若 mech_label 不是 lumen/square_v1，说明 scene_common VERSIONS / render config 映射
     需要改（非 config-only），先报告停止条件；
4) bash appearance/compile.sh；
5) 汇报 shell.json 的 rim/floor/pocket/depth、render/print 姿态断言、140/140 结果与限制
   （新外壳的 FEA/21 项功能自检未做，标 PROVISIONAL）。
```

---

## 备注

- 所有命令都在仓库根目录执行；`bash appearance/compile.sh` 会自己 `cd` 到仓库根。
- 失败模式测试可用：`bash appearance/compile.sh --config /tmp/bad.yaml --dry-run`（exit 2 + 精确报错）。
- 判断“完成”的唯一标准是 compile 的退出码 0 + acceptance 140/140 + 报告文件落盘，不是“看起来跑完了”。
