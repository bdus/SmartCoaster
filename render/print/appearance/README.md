# render/print/appearance — 3D 打印交付阶段（task-6 修正版）

> **打印姿态：顶板+印花整体翻转（凹槽朝下）**。印花正面 = 第一层贴床，顶板原顶面贴床；
> 切片/打印时看到的是印花背面（正确）；打印完成后整体翻面 = 成品外观。方形按键**平躺**
> （圆盘平行床面，厚度 5.2 mm 竖直）。**本姿态无需支撑。**
> 全部 18 个可打印 STL 在**一个扁平目录** `render/print/stl/`。
> 打印方向/首层/按键朝向建议为 **PROVISIONAL（未实物验证）**。

## 一条命令

```bash
bash render/print/appearance/run_print_stage.sh     # 幂等；~2.5 min
```

`appearance/render/run_all.sh` 的第 4/4 步（最终步）调用本阶段：
渲染 → 烘焙 STL 交付 → checksums → 床面 3MF → sheets → manifests/README → 组合板。

## 输出

```
render/print/stl/                              ← 唯一扁平 STL 交付目录（18 个）
├── round_shell.stl / round_plate_recessed.stl / round_print_filament_<n>_<HEX>.stl ×6
├── square_shell.stl / square_plate_recessed.stl / square_button.stl
│   / square_print_filament_<n>_<HEX>.stl ×7
├── CHECKSUMS.sha256
├── README.md
└── delivery.json        # 每件：源/大小/sha256/三角数/体积/bbox/min z/刚性变换
render/print/appearance/
├── print_layout_appearance.py    床面排版 + 打印姿态渲染（iso/top）
├── make_stl_delivery.py          烘焙 STL + 床面排版 3MF + 校验
├── make_sheet_appearance.py      sheets + manifest/README + 组合板
├── run_print_stage.sh            一键编排
├── PRINT_SHEET_APPEARANCE.png    组合板（两种版本）
└── round/ square/
    ├── PRINT_READY.3mf           可切片**床面排版** 3MF
    ├── PRINT_SHEET.png           1800×1200 参考页
    ├── layout.json               排版/姿态/变换/断言
    ├── manifest.json / README.md 交付清单 / 说明
    └── print_iso.png / print_top.png
```

## 打印姿态关键尺寸（实测，见各 version/layout.json）

| | 圆形 LUMEN | 方形 square_v1 |
|---|---|---|
| 顶板原顶面贴床 z | −0.000 mm | −0.000 mm |
| 顶板槽底 z（凹槽朝下后） | 1.25 mm | 1.45 mm |
| 印花正面 z（第一层上方） | **0.05 mm** | **0.05 mm** |
| 印花背面 z（坐在槽底） | 1.25 mm | 1.45 mm |
| 按键（平躺 bbox） | 无按键 | **9.0 × 9.0 × 5.2 mm**，正面朝下 |
| 床面占用 | 218.9 × 110.0 mm | 208.0 × 114.0 mm |

## 两个 3MF

- `render/print/appearance/<v>/PRINT_READY.3mf`：**可切片床面排版**（外壳底面朝下、
  顶板翻转凹槽朝下 + 印花各色嵌套、按键平躺）。
- `appearance/build/3mf/<v>.3mf`：装配完成姿态的数字样机（mockup，不用于直接切片）。

## 两种打印路线（sheet/manifest/README 内一致）

* **A) 推荐**：顶板+印花整体翻转（凹槽朝下）同盘打印；第一层 = 印花正面/顶板外表面贴床；
  **无需支撑**；打完整体翻面。
* **B) 备选**：顶板与印花分开打印（顶板仍凹槽朝下；印花正面朝下单独平打），取出后压配/点胶
  （不是打印时粘合）。

## 校验（脚本自动断言）

- 每个交付 STL：**min z = 0**、三角数 / 体积与源一致、bbox = 刚性旋转后的源 bbox；
  变换矩阵 (R,t) + 源 sha256 写入 `render/print/stl/delivery.json`。
- 床面 ≤220×220、无越界/重叠、分离件间距 ≥5 mm。
- 3MF 回读：objects/components/颜色/世界 Z 范围/床面 bbox 校验通过。
- 渲染非黑；sheet 1800×1200；`sha256sum -c render/print/stl/CHECKSUMS.sha256` 通过。

**未验证**：真实切片/打印、0.05 mm 首层融合、按键正面朝下的外观与装配手感 — PROVISIONAL。
