# render/appearance — 外观风格迭代（几何冻结）

> 目的：机械结构与功能已固化，后续**只改外观**。本目录负责“多风格外观”的配置、渲染与版本对照，
> 不改 `mechanical/square_v1` 的任何几何，也不改 `render/square_b` 的相机与灯光。
> 日期：2026-11-04

---

## 1. 已有外观资产（基线盘点）

盘点图：`00_inventory_existing.png`（`make_inventory.py` 可复跑）。

### 方形 B（100×100×18，12 件，无灯）

| 版本 | 顶板 / 壳体 / 按键 | 资产 | 状态 |
|---|---|---|---|
| **Lumen Violet** | `#6B40A0` / `#2A2E35` / 同顶板 | `render/cmf/lumen_violet.png`、`render/square_b/renders/*`、`submission/*` | **当前默认** |
| Moss | `#4F6B4A` / `#2B302B` / 同顶板 | `render/cmf/moss.png` | 备选 |
| Sand | `#C9B79A` / `#3A3530` / 同顶板 | `render/cmf/sand.png` | 备选 |
| Graphite | `#3A3D42` / `#1E2024` / 红 `#942826` | `render/cmf/graphite.png` | 备选 |
| （拼图） | — | `render/cmf/CMF_variants.png` | 2×2 对照 |

- 4 款只改 `shell / plate / button`；其余件（玻璃、硅胶垫、PCB、传感器等）沿用中性色。
- 前脸只有 **26×7 屏窗（x=−8）+ Ø8.2 按键（x=17）**，唯一缝隙是 **0.5 mm 浮动缝**。
- 屏内容贴图为 `render/square_b/ui_screen.png`（256×64，「今日 1250 ml」+ 进度条）。

### 方形 P1 基线（M1.2 白/浅灰）

- `mechanical/square_v1/build/render/{hero,front,back,top,detail,exploded,hero_low}.png`
- VTK 工作室渲染；屏窗是无贴图的暗窗。**PRD §3.1 的“白或浅灰”只有这一版**，不是 B 版 CMF。

### 圆形 LUMEN（Ø110×17，13 件，概念线）

| 版本 | 外观 | 资产 | 备注 |
|---|---|---|---|
| LUMEN 白 / 银 | 暖白壳 + 银铝顶板 + 青色光晕 | `mechanical/lumen/build/render/*`（8 张，含 `section`） | VTK 工作室 |
| LUMEN 石墨黑 | 深灰壳 + 金属顶板 + 青色光缝 | `render/lumen/renders/{hero,front,pcb_detail,exploded}.png` | Blender，**仍导入光导/LED** |

- 圆形**没有** 4 配色 CMF 组；以上是两种渲染处理，不是正式色号。
- 圆形屏内容贴图：`render/lumen/ui_lumen.png`（128×64）。

### 这些不是外观版本（别混淆）

- `mechanical/square_v1/v1..v6`、`mechanical/lumen/v1..v9`：几何迭代快照（agentcad preview），v6 / v9 只是当前几何。
- `mechanical/legacy/`、`mechanical/original_cad/`：M1.2 原始脚本，无现行外观渲染。
- `pcb_detail` / `exploded` / 包装 / 打印拼版：视图或交付物，不是独立风格。
- 方形 LED/光导时代的 halo 渲染已在 `ae17e10` 删除，工作区无残留方形发光外观。

---

## 2. 一轮外观迭代怎么做

唯一配置源：`styles.json`。一个 style = `id` + `label` + `note` + 按零件的颜色/材质参数。

```json
{
  "id": "style_name",
  "label": "风格名",
  "note": "一句话说明",
  "parts": {
    "plate":  {"hex": "#RRGGBB", "rough": 0.5, "metallic": 0.0},
    "shell":  {"hex": "#RRGGBB", "rough": 0.6, "metallic": 0.0},
    "button": {"hex": "#RRGGBB"}
  }
}
```

只需写要改的零件，其余沿用 `config_base.json`（即当前方形 B 场景的默认材质）。

```bash
# 整轮：所有 style，hero + front，出风格板
python3 render/appearance/make_styles.py

# 快速看单款（约 12 s）
python3 render/appearance/make_styles.py --only style_name --views hero

# 只换风格板标题
python3 render/appearance/make_styles.py --title "第 1 轮 · 6 个方向"
```

输出：

- `render/appearance/styles/<id>/hero.png`、`front.png`
- `render/appearance/01_style_board.png`（拼板，带色块标注）

> 现有 4 款也写在 `styles.json` 里，作为基线可复跑；新风格往后追加即可。

---

## 3. 几何冻结（硬约束）

- 几何哈希：`frozen_geometry_square.sha256`（12 件 + 传感器，共 13 个 STL）。
- 每次渲染前校验；任一哈希不符即中止，**外观轮次不可能夹带几何改动**。
- 场景沿用 `render/square_b`（相机、三点光、AgX、曝光 −1.0、48 samples），保证跨轮次可比。
- 一致性验证：用本流程重渲 `lumen_violet`，与 `render/cmf/lumen_violet.png` 像素
  **mean abs diff = 0.0（1000×1000，完全一致）**；证据在 `proof/lumen_violet/hero.png`。

---

## 4. 可改 / 不可改

**可改（外观）**

- 颜色、明度、饱和度、双色/三色关系；
- 材质感：roughness / metallic（哑光、缎面、亮面、金属）；
- 按键/屏窗边框/顶板/壳体的强调关系；
- 后续可扩展：表面纹理、图案、双色分割、微标（需要扩展 Blender 场景，不改几何）。

**不可改（本轮固定）**

- 100×100×18、R8、零件数与几何；
- 26×7 屏窗与 Ø8.2 按键的位置/尺寸；
- 称重路径、0.5 mm 浮动缝、USB-C 位置；
- 相机、灯光、渲染参数（保证风格间只比较外观）；
- 屏内容（属功能/固件资产，不随外观改）。

---

## 5. 待决策（会影响外观）

1. **顶板材质矛盾**：`docs/10` 写顶板 PC/ABS + 30% PCR（哑光紫色，Pantone 2665C），
   机械模型按 6063 铝（82.7 g）。二者影响外观（哑光塑料 vs 阳极氧化金属）、重量（155 vs ≈110 g）
   与 BLE 天线（`docs/REVIEW_ELECTRICAL.md` EL-03）。风格里“金属/塑料”必须先定。
2. **圆形 LUMEN 是否纳入外观线**：现有两稿都带光导/LED 光晕，与 2026-11-04 “去灯”口径冲突；
   若纳入，需先把光缝改成“无光装饰缝”，否则外观稿会暗示已删除的功能。
3. **主色方向**：当前紫色在 AgX 下偏亮偏饱和（`render/README.md` 待做项也提到“紫色偏亮”）；
   是否保留 Lumen Violet 作为默认，或换更克制的主色。
4. **风格范围**：先扩数量（6–8 款配色），还是先钻材质/表面质感（磨砂、金属、纹理），或两者并行。

---

## 6. 文件

```
render/appearance/
├── README.md                      本文件
├── 00_inventory_existing.png      已有外观盘点（8 格）
├── 01_style_board.png             当前风格板（4 款基线）
├── styles.json                    ★ 每轮外观的唯一配置源
├── config_base.json               方形 B 场景材质基线（styles 的默认值）
├── frozen_geometry_square.sha256  几何冻结哈希
├── make_inventory.py              盘点图生成
├── make_styles.py                 ★ 风格渲染 + 风格板
├── proof/lumen_violet/hero.png    一致性验证渲染
└── styles/<id>/{hero,front}.png   各风格渲染
```
