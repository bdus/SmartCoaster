# 3D 打印交付规范（Print Delivery Spec）

> 版本：v2.0（2026-11-07，修正打印方向：印花正面贴床 / 第一层） · 适用：`appearance/` 印花多材料线的最后一环
> 状态：**数字交付完成并通过 130/130 只读验收；实物打印未验证**。
> 本文是"3D 打印交付"这一阶段的**独立规范**；方法总览见 [`README.md`](README.md)，执行脚本在 `render/print/appearance/`。
> 一键复跑：`bash render/print/appearance/run_print_stage.sh`（≈2.5 min，幂等；已是 `appearance/render/run_all.sh` 第 4/4 步）。

---

## 0. 一句话

**印花正面（图案面）必须朝下贴床、作为第一层打印**；因此顶板与印花整体翻转（凹槽朝下）同盘打印，
切片/打印时看到的是印花**背面**（正确）；打印完成后**整体翻面**，露出的才是图案，且与顶板沿口齐平。
所有交付 STL 都按这个打印姿态烘焙好，统一放在 **`render/print/stl/` 一个平坦目录**里。

---

## 1. 物理原理与方向约定（最容易错的一步）

```text
最终成品（装配姿态，Z 上）              打印姿态（本次交付，Z 上）
  z=18/17  顶板沿口（可见面）              z=0     顶板沿口 + 印花正面（第一层，贴床）
  z=17.95/16.95 印花正面（图案）           z=0.05  印花正面（设计上比沿口低 0.05）
  z=16.55/16.75 印花背面 = 槽底            z=1.45/1.25 印花背面 = 槽底
  z=15/14  顶板底面/裙边/传力柱            z=2.45/2.25 → 顶板裙边/传力柱朝上（无支撑）
```

- 为什么必须这样：印花正面要**贴在打印床上**才能获得平整表面，且它必须是**最先打印的一层**；
  若凹槽朝上（上一版错误），印花正面成了最后一层，而且顶板裙边/传力柱悬空、需要支撑；
- 翻转后：`plate` 与 `print` 都绕 X 轴 180°（`diag(1,−1,−1)`），`shell` 不变（底面朝下），
  按钮绕 X 轴 +90° 躺平；
- **不需要支撑**（顶板原始顶面与印花正面都是第一层），这是纠正上一版"需树状支撑"的关键结论。

### 1.1 严格变换（mm，行向量 `v' = v·Rᵀ + t`）

| 对象 | R | t（圆形 / 方形） | 结果 |
|---|---|---|---|
| shell | `I` | `(0, 0.002493, 0)` / `(0, 0, 0)` | 底面朝下，XY 居中 |
| plate | `diag(1, −1, −1)`（绕 X 180°） | `(−0.03232, 0, 17.0)` / `(0, 0, 18.0)` | 原始顶面 → z=0 贴床，凹槽朝下 |
| print（6/7 个耗材同一变换，保持相对位置） | `diag(1, −1, −1)` | `(0, 0, 1.2)` / `(0, 0, 1.4)` | 印花正面 → z≈0.05，背面 → 槽底 |
| button（仅方形） | `[[1,0,0],[0,0,−1],[0,1,0]]`（绕 X +90°） | `(−17.0, 7.2, 50.0)` | 圆片躺平：厚度轴 Z，可见正面朝下 |

### 1.2 打印姿态断言值（脚本内硬断言，验收复核）

| 断言 | 圆形 | 方形 |
|---|---|---|
| 顶板原始顶面 z | −0.000004 mm ≈ 0 | −0.000006 mm ≈ 0 |
| 槽底 z（= 印花背面 z） | **1.25 mm** | **1.45 mm** |
| 印花正面 z（第一层） | **0.0500 mm** | **0.0500 mm** |
| 印花厚度 | 1.20 mm | 1.40 mm |
| 槽底平面顶点数（每块顶板） | 372 | 372 |
| 需要支撑 | **否** | **否** |
| 按钮 bbox | — | **9.0 × 8.997 × 5.2 mm**，min z=0，厚度轴 Z，可见正面朝下 |

> 印花正面比床面高 0.05 mm 是成品"印花顶面比沿口低 0.05 mm"的设计值在打印姿态下的直接映射：
> 0.05 mm 远小于 0.2 mm 首层，切片时视为贴床第一层；`PROVISIONAL`，实物首层附着需打样确认。

---

## 2. 交付物结构

```text
render/print/
├── stl/                                  ← 【唯一交付 STL 文件夹】18 个可打印 STL
│   ├── round_shell.stl                   外壳（PLA/PETG）
│   ├── round_plate_recessed.stl          开槽顶板（已翻转：顶面贴床）
│   ├── round_print_filament_1_FBF4E8.stl 印花逐耗材 1..6（已翻转：图案面朝下）
│   ├── ... round_print_filament_6_6C574C.stl
│   ├── square_shell.stl
│   ├── square_plate_recessed.stl
│   ├── square_button.stl                 方形按键（躺平）
│   ├── square_print_filament_1_EDE1F0.stl ... 7 个
│   ├── CHECKSUMS.sha256                  sha256sum -c 自校验
│   ├── delivery.json                     方向变换/断言/源 sha/体积/文件清单
│   └── README.md                         文件↔版本↔材料↔用途 对照 + Bambu 导入顺序
└── appearance/
    ├── PRINT_SHEET_APPEARANCE.png        两版打印交付对比板（2400×1250）
    ├── run_print_stage.sh                一键复跑（幂等）
    ├── print_layout_appearance.py        床面排版 + 渲染
    ├── make_stl_delivery.py              烘焙打印姿态 STL + CHECKSUMS + delivery.json
    ├── make_sheet_appearance.py          参考图 + manifest/README + 板
    ├── transform_common.py               方向变换/刚体校验工具
    └── {round,square}/
        ├── PRINT_SHEET.png               1800×1200 打印参考图（零件/耗材/路线/参数/文件）
        ├── print_iso.png · print_top.png 床面排版渲染
        ├── layout.json                   床面占用/间距/12 项断言
        ├── manifest.json · README.md     交付清单/方向/支撑/文件索引
        └── PRINT_READY.3mf               【切片用】床面排版 3MF（含逐耗材 component）
```

> 数字样机/最终装配姿态的 3MF 仍在 `appearance/build/3mf/{round,square}.3mf`（只用于查看，不可直接切片）。

---

## 3. 文件与数量

| 版本 | STL | 体积 | 印花耗材 | 备注 |
|---|---|---|---|---|
| 圆形（LUMEN + 狗） | 8 | 98.66 MB | 6 | 无按键 |
| 方形（square_v1 + 精灵） | 10 | 126.78 MB | 7 | 含按键 |
| 合计 | **18** | **225.44 MB** | — | 全部在 `render/print/stl/` |

命名规则：`<version>_<part>[_<HEX>].stl`；`part ∈ {shell, plate_recessed, button, print_filament_<n>_<HEX>}`。
控制台会输出每个文件的 min z / 三角数 / 体积 / sha256；`delivery.json` 记录源文件 sha256 与变换矩阵。

---

## 4. 校验门槛（未全部满足 = 不交付）

| # | 检查 | 门槛 | 证据 |
|---|---|---|---|
| 1 | 每个 STL 贴床 | `min z == 0`（±0.002 mm） | `delivery.json:all_min_z_zero`、验收复核 |
| 2 | 刚体变换正确 | 三角数 == 源；体积 == 源；bbox == 旋转后源 bbox（≤0.002 mm） | `delivery.json` 每文件条目 |
| 3 | 打印姿态 | 顶板顶面 z≈0、槽底 1.25/1.45、印花正面 0.05、背面=槽底、厚度 1.2/1.4 | `manifest.json:print_pose` |
| 4 | 无需支撑 | `supports_required == false` | `print_pose` |
| 5 | 按钮躺平 | bbox ≈ 9.0×9.0×5.2，厚度轴 Z，可见面朝下（记录） | `manifest.json:button` |
| 6 | 床面适配 | bbox ≤ 220×220；不同零件最小间距 ≥ 5 mm；无越界/无重叠 | `layout.json` 12 项 checks |
| 7 | 3MF 可切片 | 床面排版、单位 mm、逐耗材 component、材料色=manifest、回读 errors [] | `delivery.json:three_mf` |
| 8 | 文件完整性 | `sha256sum -c CHECKSUMS.sha256` 全 OK | `CHECKSUMS.sha256` |
| 9 | 参考图/清单 | 1800×1200、包含方向/支撑/参数/STL 索引 | `PRINT_SHEET.png` |
| 10 | 总验收 | Lead 只读验收 **130/130 PASS** | `appearance/build/ACCEPTANCE.{json,md}` |

---

## 5. 床面排版（220×220）

| | 圆形 | 方形 |
|---|---|---|
| 床面占用 | **218.9354 × 109.995 × 13.4 mm** | **208.0 × 113.9972 × 14.5 mm** |
| 摆放 | 外壳 (−54.468, 0)；顶板/印花单元 (57.5, 0) | 外壳 (−54, 0)；顶板/印花单元 (54, 0)；按钮 (0, −59.499) |
| 最小间距 | 5.00 mm | 8.00 / 5.00 / 5.00 mm |
| 越界/重叠 | 无 | 无 |

---

## 6. 两种打印路线

| | A · 推荐（原位粘合） | B · 备选（无同盘粘合） |
|---|---|---|
| 做法 | 顶板+印花**整体翻转**（凹槽朝下）同盘打印，第一层 = 印花正面/顶板外表面（贴床）；外壳单独打印 | 顶板按打印姿态单独打、印花单独平打，之后压入/胶接 |
| 粘合 | 印花与顶板在打印过程中粘结为一体 | 后装压配/胶接（不是打印时粘合） |
| 支撑 | **无需支撑** | 无需支撑 |
| 文件 | `render/print/appearance/<v>/PRINT_READY.3mf` | `render/print/stl/` 分件 |
| 后处理 | 整体翻面 → 图案朝上、与沿口齐平 | 翻面后压入印花 → 需控制过盈/胶量 |

---

## 7. Bambu Studio 导入顺序（用户侧，本机未验证）

**优先：3MF（路线 A）**

1. 导入 `render/print/appearance/<v>/PRINT_READY.3mf`（床面排版已摆好）；
2. 保持相对位置/缩放；不要自动重新摆盘把顶板与印花分开；
3. 逐材料 part 分配 AMS 槽位（狗 6 色 / 精灵 7 色；4 槽需换料或第二台 AMS）；
4. 外壳分配结构材料；**不需要支撑**；
5. 逐层预览：确认第一层同时包含"印花正面 + 顶板沿口"，印花位于凹槽内、与槽壁 0.2 mm 过盈；
6. 切片打印 → **整体翻面** → 检查图案与沿口齐平。

**备选：STL**

1. 从 `render/print/stl/` 导入该版本全部文件（外壳 + 顶板 + 按键 + 6/7 个印花耗材 STL）；
2. 印花 6/7 个 STL 必须**同时导入**并保持相对位置（它们是同一个印花件的不同材料 part）；
3. 每个印花 STL 按文件名里的 HEX 分配 AMS 槽位；
4. 不要缩放、不要镜像（STL 已按打印姿态烘焙）；
5. 其余同 3MF 流程。

---

## 8. 打印参数建议（起始值，非标定）

0.20 mm 层高 · 0.40 mm 喷嘴 · ≈0.45 mm 线宽 · 2 墙 · 15% 填充 · 无支撑 ·
方形按键 5 mm brim · AMS 6/7 色（≥6/7 槽位）。

---

## 9. 已知限制 / PROVISIONAL

- **未实际切片/打印**：本规范的门槛都是几何/格式级；首层 0.05 mm 贴合、床面附着、
  0.2 mm 过盈的实际配合、翻面后平整度都必须打样确认；
- 按钮"可见正面朝下"是工艺选择（翻面后正面平整），也可改为背面朝下，需同一版重出；
- 3MF 未写 Bambu 专有 `model_settings.config`（AMS 槽位由用户分配），
  如需全自动耗材映射请用 Kromacut 原始 print-only 3MF 参考；
- 印花 STL 不带材料信息；单色合并预览未提供（界面面是闭合实体的刻意特征，布尔合并不可靠）。

---

## 10. 失败模式（本轮踩过/已防）

| 现象 | 根因 | 规范处置 |
|---|---|---|
| 印花图案在切片预览里看不到/是反的 | 印花正面贴床、翻面后才可见（**正常**） | 参考图与 §1 已明确；不要"修正"成凹槽朝上 |
| 上一版要求树状支撑 | 凹槽朝上导致裙边/传力柱悬空 | 本版整体翻转（凹槽朝下）→ 无支撑 |
| 按钮"站着" | 只绕 Z 旋转 | 绕 X 90°，使厚度轴竖直（bbox z=5.2） |
| 印花 STL 打开是单色/缺件 | STL 无材料信息 | 逐耗材多文件同时导入、逐对象分配 AMS |
| 导入后位置/尺寸错 | 缩放/镜像 | 不缩放不镜像；用 3MF 已排版位姿 |
| 交付件与源文件 sha 不一致 | 打印姿态烘焙 = 刚体变换副本 | 用三角数/体积/bbox 校验，源 sha 记录在 `delivery.json` |

---

## 11. 复现与证据

```bash
bash render/print/appearance/run_print_stage.sh   # 排版渲染 → 烘焙 STL → CHECKSUMS → 3MF → 参考图 → 板
python3 appearance/tools/acceptance_check.py      # 130 项只读验收（含 print_delivery 组）
```

证据：`render/print/stl/{delivery.json,CHECKSUMS.sha256,README.md}`、`render/print/appearance/<v>/{layout.json,manifest.json,PRINT_SHEET.png,PRINT_READY.3mf}`、
`render/print/appearance/PRINT_SHEET_APPEARANCE.png`、`appearance/build/ACCEPTANCE.{json,md}`。
