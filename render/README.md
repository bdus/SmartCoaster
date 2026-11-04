# render/ — 数字样机可视化（Blender）

> Blender **4.5.3 LTS** 装在 `/data/Documents/tools/blender`（`~/.local/bin/blender`），后台渲染：
> `blender -b --python render/square_b/build_scene.py`
>
> **外观口径（2026-11-04 用户决定）**：LED 与全部发光件已去掉。方形 B 前脸只有 **26×7 屏窗 + 按键**，唯一缝隙是**顶板-底座 0.5 mm 浮动缝**；无灯环、无灯带、无灯缝。渲染脚本里已不再导入任何发光件。

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
- 屏幕 UI 是 `ui_screen.png` 贴在窗前的自发光平面；这是场景里唯一自发光面（无灯、无灯环）。
- 颜色/材质是**视觉参数**，不代表 3D 打印耗材能达到的颜色。
- 环境变量：`SC_SAMPLES`（Cycles 采样，默认 64）、`SC_RENDER_ONLY=hero|front|pcb_detail|exploded`（只渲一个视图，CMF 变体用它加速）。

## 关键发现：零件级 GLB 不保位置

`build123d.export_gltf()` 可以逐零件导出 GLB，但**导入 Blender 后装配位置丢失**（各零件回到原点/错位）。因此渲染用 **STL 逐件导入**（STL 带世界坐标，位置正确）。如果以后需要单文件 GLB 场景，用 trimesh 把 STL 合成一个 Scene 再导出，而不是逐件导出 GLB。

## 输出

| 文件 | 内容 |
|---|---|
| `renders/hero.png` | 45° 产品外观 |
| `renders/front.png` | 正视（26×7 屏窗 / 按键 / 0.5 mm 浮动缝） |
| `renders/pcb_detail.png` | 去掉顶板后的 PCB/传感器细节 |
| `renders/exploded.png` | 顶板/传感器/PCB/电池/底壳分层 |

其他场景：`render/cmf/`（4 配色 + `CMF_variants.png`）、`render/packaging/`（天地盖 3 视图）、`render/print/`（打印布局）。

## 待做

- KiCad 3D 导出：当前 PCB 封装无 3D 模型，暂用机械 CAD 的电子占位；等 PCB 定版后可用 `kicad-cli pcb export step/glb`。
- LUMEN 圆形版本是独立概念线（`render/lumen/`），几何不再推进。
- 3D 打印参考图：零件拆分、方向、支撑、螺柱/卡扣标注。
- 颜色/材质微调（当前紫色偏亮）。
