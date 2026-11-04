# SmartCoaster — Red Dot 2026 提交包

## 文件

| 文件 | 内容 |
|---|---|
| `01_hero.png` | 主图：Lumen Violet + Y 光导（前缘灯线 + 底部灯线 + 窗周 halo） |
| `02_front.png` | 正视图：26×7 屏 + 按键 + 灯线 |
| `03_exploded.png` | 爆炸图：13 件结构（壳体/顶板/PCB/传感器/光导） |
| `04_package.png` | 包装：天地盖 + 纸浆内衬 + 杯垫 |
| `SmartCoaster_Story.pdf` | A3 横版 300 dpi：问题/洞察/设计/体验/可持续/规格/CMF |
| `make_story.py` | 可复现的排版脚本 |

## 故事（一页）

**SmartCoaster — A coaster that knows when you drink.**

- 问题：提醒在“另一个屏幕”上，容易被忽略；杯子不知道自己被喝了多少。
- 洞察：喝水是“放下杯子”的动作；杯垫是唯一一直在场的位置。
- 设计：重量即输入；放杯/拿起/放回差值即一口；续水不计；单 RGB + Y 光导。
- 体验：该喝水时光呼吸；26×7 屏只在需要时亮，8 s 息屏；7 天续航；按需 BLE。
- 可持续：30% PCR、FSC 纸浆、无胶、可换电池、4 颗 M2 可维修。

## 复现

```bash
# 主图/结构图
blender -b --python render/square_b/build_scene.py
# 包装图
blender -b --python render/packaging/build_scene.py
# 一页故事
python3 submission/make_story.py
```
