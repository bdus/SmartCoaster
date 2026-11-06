# render/print/appearance — 打印交付脚本（scripts only）

> 本目录**只放脚本**。所有用户可见的交付物在
> **`render/print/stl/{round,square}/`**（按外壳版本分类），全局索引在
> `render/print/stl/` 根目录（README.md / delivery.json / PRINT_SHEET_BOTH.png）；
> `render/print/README.md` 是 render/print 总览。
>
> 打印姿态：顶板+印花整体翻转（凹槽朝下），印花正面=第一层贴床（床上方 0.05 mm）；
> 切片看到印花背面（正确），打完整体翻面。方形按键平躺（9.0×9.0×5.2 mm）。无需支撑。
> **PROVISIONAL（未实物验证）。**

## 一条命令

```bash
bash render/print/appearance/run_print_stage.sh     # 幂等，~2.5 min
```

它是 `appearance/render/run_all.sh` 的**最后一步（4/4）**：
床面排版渲染 → 烘焙 STL 交付 → checksums → 床面排版 3MF → sheets → manifests/README → 组合板。

## 脚本

| 脚本 | 作用 |
|---|---|
| `print_layout_appearance.py` | Blender 4.5.3 无头：打印姿态床面排版 + iso/top 渲染 → `render/print/stl/<v>/` |
| `make_stl_delivery.py` | 烘焙翻转姿态 STL（三角数/体积/bbox/min z 校验）+ `PRINT_READY.3mf` + `delivery.json` |
| `make_sheet_appearance.py` | `PRINT_SHEET.png`(1800×1200) + manifest/README + `CHECKSUMS.sha256` + 组合板 `PRINT_SHEET_BOTH.png`(2400×1250) + 根 README |
| `transform_common.py` | 刚性变换 / STL 读写 / 体积 / sha256 工具 |
| `run_print_stage.sh` | 一键编排（幂等） |

## 输出（全部在 render/print/stl/）

```
render/print/stl/
├── README.md · delivery.json · PRINT_SHEET_BOTH.png
├── round/   shell.stl · plate_recessed.stl · print_filament_1_FBF4E8.stl …(6)
│            PRINT_READY.3mf · PRINT_SHEET.png · print_iso.png · print_top.png
│            layout.json · manifest.json · README.md · CHECKSUMS.sha256
└── square/  shell.stl · plate_recessed.stl · button.stl · print_filament_1_EDE1F0.stl …(7)
             PRINT_READY.3mf · PRINT_SHEET.png · print_iso.png · print_top.png
             layout.json · manifest.json · README.md · CHECKSUMS.sha256
```

## 校验

```bash
cd render/print/stl/round  && sha256sum -c CHECKSUMS.sha256
cd render/print/stl/square && sha256sum -c CHECKSUMS.sha256
```

- 每个 STL：min z = 0、三角数/体积=源、bbox=刚性旋转源；变换矩阵 + 源 sha256 在 `delivery.json`。
- 床面 ≤220×220、分离件间距 ≥5 mm；3MF 回读校验 objects/components/颜色/Z 范围/bbox 通过。
- 姿态数字：顶板原顶面 z≈0；槽底 1.25/1.45 mm；印花正面 0.05 mm；印花背面=槽底。
- 按键平躺 bbox 9.0×9.0×5.2 mm（z=厚度），可见正面朝下（PROVISIONAL）。

## 未验证

真实切片/打印、0.05 mm 首层融合、按键朝下外观与装配手感 — **PROVISIONAL**；baseline
`render/print/{print_layout.py,make_sheet.py,PRINT_SHEET.png,renders/}` 未改动。
