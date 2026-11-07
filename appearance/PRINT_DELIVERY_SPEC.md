# appearance/PRINT_DELIVERY_SPEC — 3D 打印交付规范（Lumina-Layers 线）

> 版本：v2.0（2026-11-08，Lumina-Layers 线；v1.x 的 Kromacut 规范已 OBSOLETE）
> 适用：`render/print/stl/{round,square}/` 的全部交付件；生成脚本在
> `render/print/appearance/`，由 `appearance/compile.sh` 的 **A7** 阶段调用。
> 独立验收：`python3 appearance/tools/acceptance_check_lumina.py`（G_delivery 组）。
> **实物切片/打印未在本机验证**，本规范的门槛都是几何/格式级。

---

## 0. 一句话规则

**印花正面（图案面）必须作为打印的第一层贴床；外壳/顶板按设计姿态分别摆件；两者在
Bambu Studio 里保持独立对象，切片时按材料交界融合。交付 STL 是"按打印姿态烘焙"的刚体
副本，不是源文件。**

Lumina 单面模式的几何天然满足这条：颜色面就在 z=0、背面平、底板在上方。因此印花件
**不需要翻转**，需要翻转的是**顶板**（凹槽朝下），让顶板外表面与印花正面共面于 z=0。

---

## 1. 交付根与文件清单

```
render/print/stl/                      ← 唯一交付根（按外壳版本分类）
├── README.md                          交付索引（导入顺序/耗材/校验）
├── delivery.json                      全局：姿态/变换/床面/校验/逐文件 sha256
├── PRINT_SHEET_BOTH.png               两版对比板
├── round/   (16 files)                LUMEN Ø110 + dog
└── square/  (17 files)                square_v1 100×100 + elf（多 button.stl）
```

每版目录内容（`<v>` = round | square）：

| 文件 | 作用 | 必须性 |
|---|---|---|
| `shell.stl` | 底壳，底面朝下（原姿态） | 必须 |
| `plate_recessed.stl` | 开槽顶板，**绕 X 翻转 180°**：原顶面贴床、凹槽朝下 | 必须 |
| `button.stl` | 方形按键，**躺平**（9.0×9.0×5.2，可见面朝下） | 仅 square |
| `print_filament_{1..4}_{HEX}.stl` | 印花逐耗材闭合实体（CMYW），已翻转姿态 | 必须 |
| `PRINT_READY.3mf` | 220×220 床面排版，含全部件 + 印花 4 个 component | 必须 |
| `PRINT_ONLY_LUMINA.3mf` | Lumina 原生印花 3MF（Bambu 工程元数据/AMS 材料参考，**不含外壳**） | 参考 |
| `PRINT_SHEET.png` | 1800×1200 打印参考页（姿态/清单/耗材/路线/尺寸） | 必须 |
| `print_iso.png` / `print_top.png` | 床面排版渲染（打印姿态） | 必须 |
| `print_bottom.png` | **床底视角**：看到图案面 = 第一层（方向证据） | 必须 |
| `layout.json` | 姿态/变换/摆放/间距/包围盒/断言结果 | 必须 |
| `manifest.json` | 逐件清单：材料色、姿态、sha256、三角面、体积 | 必须 |
| `README.md` | 本版导入说明 | 必须 |
| `CHECKSUMS.sha256` | 目录内全部文件的 sha256（含上述所有文件） | 必须 |

> 旧 Kromacut 线的 `*_kromacut.3mf`、6/7 个 `print_filament_*` 已删除；如目录里还有
> `print_filament_5_*` 之类，说明没有重跑 A7。

---

## 2. 姿态约定（打印姿态，Z 向上）

```
z = 13.4 ┬ 底壳上沿
         │  ┌───────────── 顶板（翻转后）─────────────┐
         │  │  凹槽朝下，印花嵌在槽内                   │
z = 1.20 ├──┤  槽底（= 印花背面 z）                     │
         │  │  印花 1.20 mm（5 色层 + 10 背层 × 0.08）  │
z = 0.00 └──┴── 印花正面（图案）= 顶板原顶面 = 第一层 ───┴── 床面
```

| 项 | round | square |
|---|---|---|
| 顶板原顶面（贴床） | z = 0.000 | z = 0.000 |
| 槽底（= 印花背面） | 1.20 mm | 1.20 mm |
| 印花正面（第一层） | **0.00 mm** | **0.00 mm** |
| 顶板/印花厚度 | 1.20 mm | 1.20 mm |
| 支撑 | **无** | **无** |
| 底壳 | 底面朝下（原姿态） | 底面朝下（原姿态） |
| 按键 | — | 躺平，可见面朝下 |

### 2.1 为什么 top gap = 0

旧线把印花顶做成"比沿口低 0.05 mm"，翻转到打印姿态后印花正面在 z=0.05，悬空 0.05 mm
（远小于 0.2 mm 首层，靠首层压合）。Lumina 线改成 **top gap = 0.00**：印花顶与沿口
齐平，打印姿态下**印花正面和顶板外表面同时落在 z=0**，都是第一层，不存在悬空；
成品表面仍是平的。

### 2.2 烘焙语义

交付 STL 由源 STL 经**刚体变换**（旋转 + 平移，无缩放）得到：

- 三角面数不变、体积不变、`min z == 0`；
- 每件的 `(R, t)`、源 sha256、目标 sha256 写入 `delivery.json` / `manifest.json`；
- `R` 只有三种：单位阵（底壳）、`diag(1,−1,−1)`（顶板与印花，绕 X 180°）、
  按键的 RX90（躺平）。

---

## 3. 床面排版

| 规则 | 值 |
|---|---|
| 床 | 220×220 mm（X1C/P1S 256 床可用；交付按 220 保守排） |
| 件间距 | ≥ 5.0 mm（实测 5.000） |
| 占用（round） | 218.9 × 110.0 mm |
| 占用（square） | 208.0 × 114.0 mm |
| 摆位（round） | shell (−54.47, 0)，plate_unit (+57.50, 0) |
| 摆位（square） | shell (−54.47, 0)，plate_unit (+57.50, 0)，button 另行居中 |
| 全件最低点 | z = 0（校验断言） |

> 床面尺寸、间距、摆放都在 `layout.json`；改床/改机型时必须重跑 A7 并复跑验收 G 组。

---

## 4. 3MF 结构

`PRINT_READY.3mf`（3MF core spec，mm，Bambu Studio 可直接打开）：

```
<resources>
  <basematerials id="1">  每件一个 base（颜色 = CMF/耗材色）
  <object> SHELL                       mesh，build item
  <object> PLATE_RECESSED_FLIPPED      mesh，build item
  <object> BUTTON_LYING                mesh，build item（square）
  <object> print_filament_N_HEX ×4     mesh，**不是** build item
  <object> PRINT_ART_<art>>            assembly：4 个 <component>
<build>
  <item objectid=SHELL ...>            +
  <item objectid=PLATE ...>            +
  <item objectid=PRINT_ART_<art>>      transform z = 印花正面 z（0.00）
```

- **一个印花 = 一个装配对象，4 个耗材 component**；切片器按 component 分配 AMS。
- 印花 component 三角面 == 对应 STL（不去重、不合并）。
- `PRINT_ONLY_LUMINA.3mf` 是 Lumina 原生工程（含 Bambu 工程设置/材料预设），只含印花；
  需要原生 AMS 元数据时可参考，但它**没有外壳/顶板**，不能单独作为整机打印文件。

---

## 5. 切片参数（起始值，`PROVISIONAL`）

| 参数 | 值 | 理由 |
|---|---|---|
| 层高 | **0.08 mm**（至少前 1.20 mm） | Lumina 配色层的校准基准；颜色/厚度都依赖它 |
| 喷嘴 | 0.4 mm | — |
| 首层 | 0.08 mm；印花正面 + 顶板外表面贴床 | 两者共面于 z=0 |
| 背层填充 | **100%**（印花底板） | 嵌入件要实心、表面平整 |
| 支撑 | 无 | 无悬空（凹槽朝下 + 印花填满） |
| 板 | Textured PEI / 高附着力板 | 大面积首层 |
| 擦料塔 | 按切片器自动；注意 4 色 + 外壳 5 个槽位 | — |
| AMS | **4 色印花 + 1 卷外壳 = 5 卷** → 需 2×AMS(8 槽) 或走路线 B | 比旧线 6/7 色省 2–3 卷 |

> 同时打印外壳时全局层高 0.08 会使 14 mm 高的底壳 ~180 层（较慢）。可选：
> 用 Bambu 的"高度区间修改器"把 z > 1.20 mm 设回 0.20 mm；或走路线 B。

### 5.1 两条打印路线

- **A（推荐，原位粘合）**：`PRINT_READY.3mf` 一盘打印（顶板+印花+底壳+按键）。
  顶板与印花在切片里保持独立对象，打印时材料交界熔合；打完把顶板+印花整体翻面即成
  （此时才看到图案）。**无需支撑**。
- **B（备选，分开打印 + 压配/胶接）**：印花单独平打（图案面仍朝下贴床），顶板凹槽朝下
  打印，底壳正常打印，取出后压配/点胶。适合只有 4 槽 AMS 或不想整机 0.08 层高的场景。

---

## 6. 门槛（A7 结束即断言，A8 独立复核）

| # | 门槛 | 判据 | 证据 |
|---|---|---|---|
| 1 | 每件 STL `min z == 0` | 绝对误差 < 1e-6 | `delivery.json` / `manifest.json` |
| 2 | 刚体等价 | 三角面数相等；体积差 ≤ 1e-6 相对或 0.01 mm³ | 同上 |
| 3 | 印花正面在第一层 | `print_pose.print_art_face_z_mm == 0.000` | `layout.json` |
| 4 | 槽底/厚度 | `pocket_floor_z_mm == 1.200`，印花厚度 1.200 | 同上 |
| 5 | 顶板翻转 | `plate_unit.orientation` 含 "recess DOWN" | `layout.json` |
| 6 | 底壳姿态 | `shell.orientation` 含 "bottom down" | 同上 |
| 7 | 按键躺平 | bbox z = 5.2 ± 0.2、x/y = 9.0 ± 0.3、可见面朝下 | `manifest.json:button` |
| 8 | 无需支撑 | `supports_required == False` | `layout.json` |
| 9 | 床面适配 | bbox ≤ 220×220；最小间距 ≥ 5 mm | `manifest.json` |
| 10 | 3MF 回读 | `ok: true`；印花 4 components；材料色 == manifest | `delivery.json:three_mf` |
| 11 | 校验和 | `CHECKSUMS.sha256` 全部匹配 | A7/A8 |
| 12 | 方向证据 | `print_bottom.png` 存在（床底看到图案面） | 文件 + 验收 G 组 |

`acceptance_check_lumina.py` 的 **G_delivery** 组逐条覆盖以上门槛；整体基线 **183/183 PASS**
（`appearance/build/ACCEPTANCE.json`）。

---

## 7. 在 Bambu Studio 里的导入顺序

1. 打开 `render/print/stl/<v>/PRINT_READY.3mf`（已含床面排版与 4 个印花 component）。
2. 维护件：`shell`（暗色 CMF）→ AMS 槽；`PLATE_RECESSED_FLIPPED`、`BUTTON_LYING` → 紫色槽。
3. `PRINT_ART_<art>` 的 4 个 component → 4 个 CMYW 槽（白/青/品红/黄，按耗材实际颜色微调）。
4. 核对：层高 0.08、首层 0.08、印花背层 100% 填充、无支撑、板温/首层温度。
5. **逐层检查**：前 1.20 mm 内应看到 4 色印花与顶板沿口同层出现；看到印花"背面"是对的。
6. 切片 → 预览（从上看是印花背面）→ 打印 → **整体翻面**即见图案。

> 若改用分件（路线 B）：导入 4 个 `print_filament_*.stl` 到独立盘，逐个指定 AMS 槽；
> 不要缩放、不要镜像（已烘焙）。

---

## 8. 失败模式与排查

| 现象 | 根因 | 处理 |
|---|---|---|
| 切片里印花在第一层之上悬空 | 用了旧线 STL / top gap 0.05 | 重跑 A7；`print_pose.print_art_face_z_mm` 必须是 0.000 |
| 从上看不到图案就以为装反 | 正常：打印姿态印花正面朝下 | 看 `print_bottom.png`；打完翻面 |
| 图案左右反了 | 用了**装配姿态**的源 STL，而不是烘焙件 | 只用 `render/print/stl/<v>/` 里的件 |
| 只有 4 个印花 STL、没有外壳融合 | STL 不带装配/材料信息 | 用 `PRINT_READY.3mf`；或逐件导入但保持相对位置 |
| AMS 槽位不够 | 4 色印花 + 外壳 = 5 卷 | 2×AMS，或路线 B，或外壳与某色共用（不推荐，改 CMF） |
| 颜色与渲染差很多 | 渲染用 Lumina 预测色；LUT 是原厂 PLA Basic | 打样后按实物重校准 LUT（`docs/15_Lumina_Layers_Guide.md` §7） |
| 首层不粘 | 大面积共面首层 + 0.08 mm | 洗板、加 5 mm brim、提高首层温度/流量 |
| 印花边缘有锯齿 | 0.10 mm 像素 + 0.4 mm 线宽的物理下限 | 属真实几何；要更细需换 0.2 mm 喷嘴并重出 art/print |

---

## 9. 边界（不能由本规范证明的事）

- 未在 Bambu Studio 实际导入/切片；本机无 Bambu Studio。
- 未实物打印：颜色、层间结合、0.08 mm 层高的效率、首层附着、翻面后的平整度、耐热/清洗。
- 顶板开槽后未重跑 21 项机械自检与 FEA（`PROVISIONAL`）。
- 交付 STL 是烘焙副本（不是源的逐字节拷贝）；源、变换、sha256 都可追溯。
- `PRINT_ONLY_LUMINA.3mf` 是**参考**，不含外壳，不能替代 `PRINT_READY.3mf`。
