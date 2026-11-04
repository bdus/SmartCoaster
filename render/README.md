# render/ — 数字样机可视化（Blender）

> Blender **4.5.3 LTS** 装在 `/data/Documents/tools/blender`（`~/.local/bin/blender`），后台渲染：
> `blender -b --python render/square_b/build_scene.py`

## 流水线

```
mechanical/square_v1/.venv/bin/python cad/export_v01.py     # STEP + STL（零件级）
        │
        ▼  STL（mm，世界坐标；仅可视化）
render/square_b/build_scene.py  ── 材质/灯光/相机/爆炸位移
        │
        ▼
render/square_b/renders/{hero,front,pcb_detail,exploded}.png
```

- **STEP / STL 是打印与尺寸源；STL 只用于渲染**，不反向导出打印件。
- 传感器用 `mechanical/hy928d/build/hy928d_v2.stl`（通槽真实形状），不是方形 V1 里的简化占位。
- 屏幕 UI 是 `ui_screen.png` 贴在窗前的自发光平面；halo 是 0.6 mm 自发光边框（视觉件，实物需导光条）。
- 颜色/材质是**视觉参数**，不代表 3D 打印耗材能达到的颜色。

## 关键发现：零件级 GLB 不保位置

`build123d.export_gltf()` 可以逐零件导出 GLB，但**导入 Blender 后装配位置丢失**（各零件回到原点/错位）。因此渲染用 **STL 逐件导入**（STL 带世界坐标，位置正确）。如果以后需要单文件 GLB 场景，用 trimesh 把 STL 合成一个 Scene 再导出，而不是逐件导出 GLB。

## 输出

| 文件 | 内容 |
|---|---|
| `renders/hero.png` | 45° 产品外观 |
| `renders/front.png` | 正视（屏/键/halo） |
| `renders/pcb_detail.png` | 去掉顶板后的 PCB/传感器细节 |
| `renders/exploded.png` | 顶板/传感器/PCB/电池/底壳分层 |

## 待做

- KiCad 3D 导出：当前 PCB 未布线、封装无 3D 模型，暂用机械 CAD 的电子占位；布线后可用 `kicad-cli pcb export step/glb`。
- LUMEN 圆形版本独立渲染（复用同一套材质/相机脚本）。
- 3D 打印参考图：零件拆分、方向、支撑、螺柱/卡扣标注。
- 颜色/材质微调（当前紫色偏亮、halo 偏白）。
