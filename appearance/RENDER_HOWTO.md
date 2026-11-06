# 渲染实现与手动复现（RENDER_HOWTO）

> 适用：`appearance/render/`（Blender 4.5.3 LTS，headless Cycles CPU）
> 目的：把数字样机渲染（hero / top / print_top / macro_edge / section_exploded / board）的**做法和参数**写清楚，
> 便于手动复现、改机位、改材质后重渲。渲染是**示意/评审图**，不是计量证据。

---

## 0. 一句话流程

```bash
# 前置：先有几何/材质输入（分离的 shell 装配 + 开槽顶板 + 印花逐耗材 + shell.json/manifest）
bash appearance/render/run_all.sh          # = build_scene.py → make_3mf.py → postprocess.py → 打印交付

# 只渲染（不动 3MF / 打印交付）
/data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py
python3 appearance/render/postprocess.py   # 微距字幕 / 剖面合成 / 两版对比板
```

单版本 / 单视图 / 低采样预览：

```bash
# 只渲圆形版
/data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py -- --version round
# 只渲 hero（16 spp 快速预览）
SC_SAMPLES=16 SC_RENDER_ONLY=hero \
  /data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py -- --version square
# 只跑后处理的一部分
python3 appearance/render/postprocess.py --skip-board        # 只做微距/剖面
python3 appearance/render/postprocess.py --skip-section      # 只做板
```

---

## 1. 文件与职责

| 文件 | 作用 |
|---|---|
| `appearance/render/build_scene.py` | 主脚本：读 `config.json` + `shell.json` + 印花 manifest → 建场景 → 逐视图渲染 → 存 `.blend`/`scene_info.json` |
| `appearance/render/scene_common.py` | 共享层：解析装配/零件、读 STL、材质（CMF/印花）、灯光、相机、剖面工具 |
| `appearance/render/config.json` | **唯一渲染配置**：engine/samples/resolution/AgX、CMF style、每版相机、剖面参数、回退值 |
| `appearance/render/postprocess.py` | 后处理：微距图字幕、1/4 剖面 + 爆炸合成、两版对比板 `board.png` |
| `appearance/render/make_3mf.py` | 装配 3MF（与渲染无关，但同属 `run_all.sh`） |
| `appearance/render/<ver>/scene.blend` | 保存的装配场景（可 GUI 打开手渲） |
| `appearance/render/<ver>/{hero,top,print_top,macro_edge,section_exploded}.png` | 交付图 |
| `appearance/render/board.png` | 两版对比板 |
| `appearance/build/render/<ver>/` | 剖面/微距的中间渲染（合成输入） |

输入依赖（由前面阶段生成，缺了会报错）：

```
appearance/build/art/<art>/art.json              # 印花尺寸/色板/层高
appearance/build/print/<art>/manifest.json + STL # 印花逐耗材几何
appearance/build/shell/shell.json + {round,square}/plate_recessed.stl
mechanical/{lumen,square_v1}/build/parts/*.stl   # 外壳装配零件（只读）
render/appearance/styles.json + config_base.json # CMF 颜色
render/square_b/ui_screen.png                    # 方形版屏幕贴图
```

---

## 2. 场景构建（build_scene.py 做了什么）

### 2.1 Collection 结构（外壳与印花保持分离）

```text
SHELL_<VERSION>      外壳零件（含开槽顶板），无 join/boolean/父子
PRINT_ART_<ART>      每耗材一个对象（ART_DOG_00..05 / ART_ELF_00..06）
LIGHTS / GROUND / CAMERAS / SECTION（渲染辅助）
```

### 2.2 材质（Principled BSDF）

- **外壳/顶板/按键**：读 `render/appearance/styles.json` 的 `cmf.style`（默认 `lumen_violet`），
  壳 `#2A2E35`、顶板/按键 `#6B40A0`；roughness/metallic 来自该 style 或 `config_base.json`。
  颜色是 sRGB hex，赋给 Blender 前**转线性**（`srgb_hex_to_linear`）。
- **印花**：每个耗材对象用 `manifest.json` 里的 hex，同样 sRGB→linear；roughness≈0.5、metallic=0。
- **地面**：`M_ground` = 深灰 `(0.055,0.055,0.060)`，rough 0.85、metallic 0（避免高光变成硬亮矩形）。
- **屏幕（仅方形）**：`render/square_b/ui_screen.png` 贴到屏幕平面（自发光/基础色），圆形版玻璃保持中性暗色。
- **玻璃/OLED/PCB 等**：中性深色材质，不追求真实光学。

### 2.3 灯光（三点面积光，`studio()`）

```text
world  背景色 (0.035,0.038,0.045) × 0.6
key    AREA loc(0.22,-0.22,0.30) rot(55°,0,45°)  size 0.35  power 6.5  白色
fill   AREA loc(-0.28,-0.18,0.18) rot(70°,0,-50°) size 0.30 power 2.2  白色
rim    AREA loc(0.02,0.28,0.22)  rot(110°,0,180°) size 0.28 power 3.5  冷白 (0.75,0.85,1.0)
```

光源 `visible_camera=False`（不出现在画面里）。这套参数从 `render/square_b/build_scene.py` 沿用，
保证与既有外观渲染可比。

### 2.4 渲染设置（`config.json.render`）

| 项 | 值 |
|---|---|
| 引擎/设备 | `CYCLES` / `CPU` |
| 色彩管理 | `AgX`，look `AgX - Medium High Contrast`，曝光 `-1.0` |
| 降噪 | 开（OpenImageDenoise） |
| 采样/分辨率 | hero 48/1000² · top 48/1000² · print_top 48/1000² · macro_edge 64/1600² · section_exploded 48/1600×1200（再合成到 2400×1200） |

### 2.5 相机（`config.json.versions.<v>.cameras`，单位 m，Z 上）

| 视图 | 圆形版 | 方形版 |
|---|---|---|
| `hero` | loc (0.185,-0.225,0.17) → target (0,0,0.01)，62 mm | loc (0.17,-0.21,0.16)，62 mm |
| `top` | 正交，ortho_scale 0.138 | 正交 0.128 |
| `macro_edge` | target 槽壁附近 (-0.0306,-0.0306,0.0172) + offset (-0.038,-0.038,0.048)，170 mm 长焦（近距微距，`clip_start=1 mm`） | 同位置，offset (-0.038,-0.038,0.048) |
| `print_top` | 正交 0.10（只渲印花） | 正交 0.10 |
| `section_exploded` | loc (0.15,0.15,0.16) → target (0,0,0.013)，68 mm | loc (0.14,0.14,0.15) |

> 改机位只需要改 `config.json` 里对应视图的 `loc/target/lens/ortho_scale`，然后重跑 `build_scene.py`。

### 2.6 剖面（`section`）

- 1/4 剖切：布尔切掉 `x>0 且 y>0` 象限（只作用于渲染副本 `scene_section.blend`，不影响 `.blend` 与 3MF）；
- 印花沿 +Z 抬升 `explode_print_mm=6.0` 得到"嵌合/分离"说明图；
- 标签锚点 `section.label_points_mm` 的 x/y 是 mm，z 从 `shell.json`/`manifest.json` 实时填；
- 主图 + 爆炸小图由 `postprocess.py` 合成，标注数值会做**一致性断言**（数字从 JSON 取，不手写）。

---

## 3. 输出与后处理

`build_scene.py` 每版输出：

```text
appearance/render/<ver>/hero.png            1000×1000  3/4 俯视主图
appearance/render/<ver>/top.png             1000×1000  正交俯视
appearance/render/<ver>/print_top.png       1000×1000  印花单独俯视
appearance/render/<ver>/macro_edge.png      1600×1600  印花边缘/槽壁微距（可见 0.15 mm 像素台阶）
appearance/render/<ver>/scene.blend         装配场景（可 GUI 打开）
appearance/render/<ver>/scene_info.json     本次渲染参数/耗时/材质/警告（供复现与审计）
appearance/render/<ver>/annotations.json    剖面标签投影锚点
appearance/build/render/<ver>/section_seated.png / section_exploded.png   合成素材
```

`postprocess.py` 再生成：

- `appearance/render/<ver>/macro_edge.png` 的字幕（数值来自 `scene_info.json`）；
- `appearance/render/<ver>/section_exploded.png`（2400×1200：1/4 剖面主图 + 爆炸小图 + 配合数值）；
- `appearance/render/board.png`（两版 hero/micro 对比板）。

---

## 4. 手动渲染（GUI / 命令行两条路）

### 4.1 打开已保存场景（最快）

```bash
/data/Documents/tools/blender/blender appearance/render/round/scene.blend
```

1. 在 Outliner 里选 `CAMERAS` collection 下的相机（`cam_hero` / `cam_top` / `cam_macro_edge` / …），
   `Ctrl+Numpad0` 切到该相机；
2. Render Properties 确认：Cycles / CPU、Samples=48、Denoise 开；Color Management = AgX、Look = AgX - Medium High Contrast、Exposure=-1.0；
3. `F12` 渲染，`Alt+S` 保存图像（建议 PNG，与脚本输出同名以便对照）。

> `scene.blend` 是**装配整机**场景；`scene_section.blend` 是剖切渲染副本（只用于剖面图）。

### 4.2 命令行单视图（可脚本化）

```bash
# 只渲 hero；采样降到 16 快速预览；带版本参数要用 -- 分隔 Blender 与脚本参数
SC_SAMPLES=16 SC_RENDER_ONLY=hero \
  /data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py -- --version round
```

`--render-only` 支持逗号分隔：`hero,top`；脚本会把结果写到 `appearance/render/round/`。

### 4.3 改参数后重渲

| 想改什么 | 改哪里 | 然后 |
|---|---|---|
| 机位/焦距/正交范围 | `config.json` → `versions.<v>.cameras.<view>` | 重跑 `build_scene.py` |
| 采样/分辨率/曝光/AgX | `config.json` → `render` | 同上（或 `SC_SAMPLES` 临时覆盖采样） |
| 材质/CMF 颜色 | `render/appearance/styles.json`（style 名在 `config.json.cmf.style`） | 同上 |
| 印花颜色 | `appearance/build/print/<art>/manifest.json`（由 Kromacut 阶段生成） | 同上（重跑渲染即可，不需重转） |
| 灯光/地面 | `appearance/render/scene_common.py` 的 `studio()` | 同上 |
| 剖面位置/爆炸量 | `config.json` → `section` | 重跑 `build_scene.py` + `postprocess.py` |

> 注意：改 `config.json` 属于**渲染配置**，不需要重跑前处理；反过来，改了印花/外壳几何必须先重跑
> `compile.sh`（或对应阶段）再渲。

### 4.4 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 微距图全黑 | 相机 `clip_start` 太大（默认 0.1 m，微距距离 40–70 mm） | 脚本内已设 `clip_start=1 mm`；手改场景记得改 |
| 地面出现硬亮矩形 | 高光地面反射三点光 | 地面用 rough 0.85 哑光（脚本已处理） |
| 画面灰/对比弱 | 色彩管理不是 AgX 或曝光不对 | 按 §2.4 设置，或直接跑脚本 |
| GUI 渲染很慢 | Cycles CPU 48 spp / 1600² | 预览用 `SC_SAMPLES=16`、`SC_RENDER_ONLY=hero`；最终图再用 48/64 |
| 渲染和 3MF 不一致 | 渲染用的是渲染时的 STL；几何已重跑但没重渲 | 先 `bash appearance/compile.sh`（或 `run_all.sh`）再出图 |

---

## 5. 边界

- 渲染是**示意/评审图**（材质为近似 Principled 参数，不是实测 BRDF；屏幕内容是贴图，不是真实驱动）；
- 渲染的"齐平/嵌合"观感来自真实几何（shell.json/manifest 的槽底、过盈、顶差），但**不能当计量证据**；
- 所有关键数字（槽底/顶差/过盈/公差）以 `shell.json`/`manifest.json`/`delivery.json` 和验收报告为准；
- 实物颜色、表面、结合强度仍需打样验证。
