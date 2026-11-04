# 渲染记录 — 2026-11-04 无灯重出

> 机器：36 核 CPU / 62 GB，Blender **4.5.3 LTS**（`/data/Documents/tools/blender/blender`，`~/.local/bin/blender` 软链）。
> 几何来源：`mechanical/square_v1/build/parts/*_v01.stl`（mech 已删发光件后重导出，**12 件**）。
> 外观口径：前脸只有 **26×7 屏窗 + 按键**，唯一缝隙是 **顶板-底座 0.5 mm 浮动缝**；无灯、无灯环、无灯缝。

## 复现命令（全部 headless，Cycles CPU）

```bash
cd /data/Documents/projects/SmartCoaster

# 1) 方形 B 四视图（64 samples，48.6 s）
/data/Documents/tools/blender/blender -b --python render/square_b/build_scene.py
#   -> render/square_b/renders/{hero,front,pcb_detail,exploded}.png

# 2) 包装三视图（96 samples，3 × ~22 s）
/data/Documents/tools/blender/blender -b --python render/packaging/build_scene.py
#   -> render/packaging/renders/{closed,open,insert}.png

# 3) CMF 四变体 + 拼图（每变体只渲 hero，48 samples）
python3 render/cmf/make_variants.py
#   -> render/cmf/{lumen_violet,moss,sand,graphite}.png + CMF_variants.png
#   脚本会备份/还原默认 hero，不会把 square_b/renders/hero.png 留成最后一个变体

# 4) 3D 打印参考（布局渲染 + 拼版）
/data/Documents/tools/blender/blender -b --python render/print/print_layout.py
python3 render/print/make_sheet.py
#   -> render/print/renders/{print_iso,print_top}.png + PRINT_SHEET.png

# 5) 提交包（从 1) 2) 复制 4 张图后重排 A3）
cp render/square_b/renders/hero.png        submission/01_hero.png
cp render/square_b/renders/front.png       submission/02_front.png
cp render/square_b/renders/exploded.png    submission/03_exploded.png
cp render/packaging/renders/open.png       submission/04_package.png
python3 submission/make_story.py
#   -> submission/SmartCoaster_Story.png / .pdf（A3 300 dpi）
```

快速迭代开关（square_b 场景）：

```bash
SC_SAMPLES=32 SC_RENDER_ONLY=hero blender -b --python render/square_b/build_scene.py
```

## 本次输出（时间戳 / 尺寸）

| 文件 | 时间 | 像素 | 字节 |
|---|---|---|---|
| `render/square_b/renders/hero.png` | 19:47:57 | 1000×1000 | 1,024,646 |
| `render/square_b/renders/front.png` | 19:44:35 | 1200×600 | 700,143 |
| `render/square_b/renders/pcb_detail.png` | 19:44:51 | 1000×800 | 909,800 |
| `render/square_b/renders/exploded.png` | 19:45:00 | 1200×1000 | 1,228,117 |
| `render/packaging/renders/closed.png` | 19:45:37 | 1000×1000 | 1,023,308 |
| `render/packaging/renders/open.png` | 19:45:58 | 1000×1000 | 1,022,628 |
| `render/packaging/renders/insert.png` | 19:46:20 | 1000×1000 | 988,536 |
| `render/cmf/lumen_violet.png` | 19:46:40 | 1000×1000 | 1,014,249 |
| `render/cmf/moss.png` | 19:46:52 | 1000×1000 | 1,014,306 |
| `render/cmf/sand.png` | 19:47:05 | 1000×1000 | 1,002,984 |
| `render/cmf/graphite.png` | 19:47:17 | 1000×1000 | 1,010,238 |
| `render/cmf/CMF_variants.png` | 19:49:10 | 984×1158 | 503,446 |
| `render/print/renders/print_iso.png` | 19:51:08 | 1400×900 | 1,263,485 |
| `render/print/renders/print_top.png` | 19:50:58 | 1400×1100 | 1,557,443 |
| `render/print/PRINT_SHEET.png` | 19:51:28 | 1800×1200 | 878,077 |
| `submission/01_hero.png` | 19:47:57 | 1000×1000 | 1,024,646 |
| `submission/02_front.png` | 19:47:28 | 1200×600 | 700,143 |
| `submission/03_exploded.png` | 19:47:28 | 1200×1000 | 1,228,117 |
| `submission/04_package.png` | 19:47:28 | 1000×1000 | 1,022,628 |
| `submission/SmartCoaster_Story.png` | 19:47:59 | 4961×3508 | 2,592,499 |
| `submission/SmartCoaster_Story.pdf` | 19:47:58 | A3 300 dpi | 531,613 |

## 场景改动（去灯）

- `render/square_b/build_scene.py`：`PARTS_ORDER` 删发光件；删其自发光材质分支；爆炸图只移动 `screen_ui`（不再有灯环对象）；新增 `SC_SAMPLES` / `SC_RENDER_ONLY`。
- `render/square_b/config.json`：删发光件的颜色与爆炸位移条目。
- `render/cmf/make_variants.py`：不再把发光件当视觉元素；新增 2×2 拼图 `CMF_variants.png`；备份/还原默认 hero。
- `render/packaging/build_scene.py`：包装场景不再导入发光件。
- `render/print/print_layout.py`：修正米/毫米单位错位（原 `place()` 把 mm 当 m，渲染只剩打印床），现在外壳/顶板/按键正确落在 220 打印床上。
- `render/print/make_sheet.py`：新增，合成 `PRINT_SHEET.png`（可复跑）。
- 删除 `render/square_b/` 下的旧发光件标注图（文件名含已删件名，整张图已移除）。

场景里唯一自发光面是 `ui_screen.png` 贴图平面（26×7 屏窗内容），不参与产品外观的发光结构。
