# appearance/render — RENDER_LOG（Lumina-Layers 线）

> 真实外壳 + 开槽顶板 + **Lumina-Layers 多材料印花**，圆形（LUMEN + dog）与方形
> （square_v1 + elf）两版，外加 Bambu 可直接排版的装配 3MF。
> 机器：36 核 / 62 GB。Blender **4.5.3 LTS**（`/data/Documents/tools/blender/blender`），
> headless `blender -b --python …`；Cycles CPU、AgX、OpenImageDenoise、三点棚拍沿用
> `render/square_b`。
> 日期：2026-11-07（Lumina 线首次完整出图；Kromacut 线的旧日志见 git 历史，已 OBSOLETE）。

## 一条命令复现

```bash
cd /data/Documents/projects/SmartCoaster
bash appearance/compile.sh            # 全链路 art → lumina → shell → render → 3mf → post → print → acceptance
bash appearance/compile.sh --only A4  # 只重出渲染

# 分步（等价）
/data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py
python3 appearance/render/make_3mf.py
python3 appearance/render/postprocess.py
bash render/print/appearance/run_print_stage.sh
```

快速预览：`SC_SAMPLES=16 SC_RENDER_ONLY=hero bash …`（见 build_scene.py 头部）。

输入（只读，其它阶段产出）：
`appearance/build/shell/shell.json` + `parts.json` + `{round,square}/plate_recessed.stl`；
`appearance/build/print/{dog,elf}/filament_*.stl` + `manifest.json` + `matched_rgb.npy`；
`appearance/build/art/*/art.json`；`render/appearance/styles.json`；`render/square_b/ui_screen.png`。

输出：`appearance/render/{round,square}/*.png` + `.blend`、`appearance/build/render/**`（raw）、
`appearance/build/3mf/**`、`render/print/stl/**`（打印交付）。

## 场景结构（外壳与印花始终分开）

```
SHELL_ROUND / SHELL_SQUARE : shell, pcb, sensor, esp32, hx711, usbc, battery, oled, glass, pad
                             (+ button, screen_ui for square) + plate（开槽顶板）
PRINT_ART_DOG              : ART_DOG_00..03   —— 4 个物理耗材各一个闭合实体
PRINT_ART_ELF              : ART_ELF_00..03
PRINT_FACE_DOG / _ELF      : **渲染专用**贴图圆盘（见下），不在 3MF/STL 交付里
STUDIO                     : ground + 3 area lights + cameras
```

- **印花与外壳不做布尔合并**，融合由 Bambu Studio 切片时完成（这是本线的前提）。
- 印花组放在槽底（round 15.80 / square 16.80），XY 居中，无旋转；
  `image TOP = +Y`，从 −Y 正面看图案是正的。
- 印花实测：厚度 **1.20 mm**、标称 Ø86.2、最大顶点半径 **43.219 mm**（像素台阶），
  与 Ø86.0 槽的名义过盈 0.10 mm、实测最大 **0.219 mm**；印花顶 **与沿口齐平（top gap 0）**。
- CMF：两版都用 `lumen_violet`（壳 `#2A2E35`、顶板/按键 `#6B40A0`）。

## 为什么多了一个“渲染专用”贴图面

Lumina 的颜色是**分层光学混色**：可见色 ≠ 最上层耗材的平涂色（例如粉脸颊是
White+Magenta 的叠层效果）。若直接用 4 个耗材的平色渲染，画面会明显偏色。
因此 `build_scene.py` 额外生成 `PRINT_FACE_<ART>`：

- 几何：Ø86.2 的薄圆盘，落在印花顶面 +30 µm（`visible_shadow=False`，避免沿口出现投影细线）；
- 材质：贴图 = `matched_rgb.npy`（Lumina 的**预测打印色**）经 6 px 外扩重建的
  `appearance/build/render/<v>/print_face_<art>.png`（Lumina 自带 `plate_preview.png` 圆外
  RGB 不可靠，直接采样会在边沿出彩色碎点，故自己重建）；
- UV 按 86.4 mm 画幅对齐，`interpolation=Closest`、`extension=EXTEND`；
- **只用于渲染**：不进 3MF、不进 STL 交付；`scene_info.json` 的
  `render_only_objects` 明确记录，验收脚本会断言这一点。

> 边界：贴图展示的是**预测色**（LUT 模型的预测），不是实测色；实物颜色必须打样校准。

## 渲染清单（Cycles CPU / AgX / denoise）

| view | 分辨率 | round | square | 说明 |
|---|---|---|---|---|
| `hero.png` | 1000×1000 | ✅ | ✅ | 3/4 俯视，印花与沿口齐平 |
| `top.png` | 1000×1000 | ✅ | ✅ | 正交顶视（图案 + CMF） |
| `macro_edge.png` | 1600×1600 | ✅ | ✅ | 印花沿口/槽壁特写，170 mm 镜头，postprocess 加注尺寸 |
| `print_top.png` | 1000×1000 | ✅ | ✅ | 纯印花正交顶视（外壳/顶板/地面隐藏） |
| `section_exploded.png` | 2400×1200（合成） | ✅ | ✅ | 1/4 剖切（1600×1200）+ 爆炸插页（1200×1000）合成 |
| `board.png` | 2276×2406 | — | — | 两版 hero + macro 对比板 |

分阶段耗时（本机实测，两版合计）：build_scene ≈ 3 min 20 s（含 .blend 保存）、
make_3mf ≈ 38 s、postprocess ≈ 30 s、打印交付 ≈ 2 min 30 s（含底部视角）。

## 变更点（相对 Kromacut 线）

1. 印花厚度 1.20 mm **两版统一**（Lumina 15 层 × 0.08 mm），槽深 1.20，先前 1.25/1.45；
2. `top_gap` 0.05 → **0.00**：印花顶与沿口齐平，打印时**印花正面与顶板外表面同为第一层**；
3. 印花颜色不再是“每像素一种耗材”，而是 4 耗材叠层 → 渲染必须用预测色贴图面；
4. 交付新增 `print_bottom.png`（从床底看第一层 = 图案面）作为方向证据；
5. 文件名/对象名随之变化：`PRINT_ART_*` 下只有 4 个 `ART_*_0x`。

## 已知边界

- Bambu Studio 实际导入/AMS 映射/切片未在本机验证（无 Bambu Studio）。
- 实物颜色、层间结合、翘曲、耐热/清洗未打样。
- 开槽顶板未重跑 21 项机械自检与 FEA（`PROVISIONAL`）。
- 贴图面为预测色；`macro_edge` 沿口的像素台阶是**真实几何**（0.10 mm 像素 + 0.4 mm 喷嘴）。
