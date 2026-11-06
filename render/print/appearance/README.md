# render/print/appearance — 3D 打印交付阶段

> 两种外观版本的**真实可打印文件**（外壳 + 开槽顶板 + 印花 + 方形按键）与打印参考。
> 由 `appearance/render/run_all.sh` 的最后一步调用；也可单独运行。
> 打印方向/支撑建议为 **PROVISIONAL（未实物验证）**。

## 一条命令

```bash
bash render/print/appearance/run_print_stage.sh
```

（`appearance/render/run_all.sh` 已把该步骤作为第 4/4 步：渲染 → 3MF → 贴图 → **打印交付**）

## 输出

```
render/print/appearance/
├── print_layout_appearance.py     Blender 4.5.3 headless：220×220 床面排版 + iso/top 渲染
├── make_sheet_appearance.py       Pillow：STL 交付 + checksums + sheet + manifest + README + 组合板
├── run_print_stage.sh             一键编排（幂等）
├── PRINT_SHEET_APPEARANCE.png     组合板（两种版本）
├── round/  square/
│   ├── stl/                                     ← 真实可打印 STL（cp 副本）
│   │   ├── shell.stl
│   │   ├── plate_recessed.stl
│   │   ├── button.stl                           （仅 square）
│   │   └── print/multimaterial/filament_<n>_<HEX>.stl   （6 / 7 个，每色一个闭合实体）
│   ├── PRINT_READY.3mf                          路线 A 装配体 3MF（推荐）
│   ├── PRINT_SHEET.png                          1800×1200 参考页
│   ├── manifest.json / README.md / layout.json 交付清单 / 说明 / 排版验证
│   ├── CHECKSUMS.sha256                         交付文件 sha256
│   ├── print_iso.png / print_top.png            床面渲染
```

## 两种打印路线（sheet/manifest/README 内均注明）

* **A) 推荐 · 多材料原位粘合**：顶板凹槽朝上 + 印花嵌在槽内同盘打印；该姿态顶板裙边/传力柱
  悬空，**需树状支撑（PROVISIONAL）**；外壳单独打印。使用 `PRINT_READY.3mf`。
* **B) 备选 · 无支撑**：顶板倒扣打印 + 印花单独平打，取出后压配/点胶（**不是打印时粘合**）。
  使用 `stl/` 分件。

## 印花（Kromacut）导入顺序（Bambu Studio）

1. 导入 `stl/print/multimaterial/filament_*.stl`（6 / 7 个色彩对象，均按原位 XY 0,0 / 底面 z=0）；
2. 每个对象指定一个 AMS 槽位（色号见 manifest `filaments`）；
3. 导入 `stl/plate_recessed.stl`，凹槽朝上，与印花同一嵌套位置（路线 A）；
4. 外壳 `stl/shell.stl` 单独打印；方形再加 `stl/button.stl`（5 mm brim）；
5. 或直接用 `PRINT_READY.3mf`（已按装配位摆好）。

## 验证（脚本自动断言，输出见 manifest/README）

* 床面占用 ≤220×220、无越界、无重叠，分离件间距 ≥5 mm；
* 印花底面 = 顶板槽底（round 15.75 mm / square 16.55 mm 相对顶板；床面坐标 9.75 / 10.55 mm）；
* 渲染非黑（mean/std/unique colors），sheet 1800×1200；
* 每个交付 STL 的 sha256 与源文件一致（`CHECKSUMS.sha256` 可 `sha256sum -c`）。
* 单色预览 STL **未交付**：6/7 个印花 STL 是带“同面异向界面”的闭合实体，单色拼接会残留内部面，
  大三角数布尔并不可靠；单色试装请用 3MF 或分件 STL。
