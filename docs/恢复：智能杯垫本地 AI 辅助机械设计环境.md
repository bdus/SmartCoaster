阅读https://agentcad.dev/ 和附件“恢复：智能杯垫本地 AI 辅助机械设计环境”提示词，帮我安装这个工具 所有目录下都可用，如果需要clone就安装到/data/Documents/tools目录下，实现基于代码绘制模型的能力。全部完成后帮我进行实验测试，就在/data/Documents/projects/SmartCoaster 目录下新建目录和 .venv ，参考附件提示词 “docs/恢复：智能杯垫工程（自包含参数手册）.md” 开始绘制模型，帮我画一个智能杯垫，可以测量我一天喝水的量，结构外表美观实用，要能拿红点奖的水平。


# 恢复：智能杯垫本地 AI 辅助机械设计环境


> 目标：在一台**非华为内网**的新电脑上，重建"AI 代理写代码 → 生成 CAD（STEP/STL/GLB）→ 渲染/查看"的工具链。
> 通用环境，无内网代理/镜像依赖。Python/uv/Xvfb 等细节不赘述（用系统包管理/官方安装器即可）。
> 配套文档：`docs/恢复项目-智能杯垫工程.md`（项目的自包含参数手册）。


---


## 1. 需要什么（仅 3 项）


| 工具 | 作用 | 版本要求 |
|---|---|---|
| **Python 3.10+** | 运行环境 | 3.10（推荐）~3.12 |
| **agentcad** | AI 代理 CAD CLI（build123d 内核） | ≥0.7（本项目按 0.7 工作流） |
| **build123d** | CAD 建模库（agentcad 内核依赖） | **必须 0.10.x**（本项目脚本按 0.10 API 编写，0.11 不兼容） |


> 可选：**FreeCAD**（STEP 复核/查看，推荐）。任何能打开 STEP 的 CAD 均可替代。


---


## 2. 安装（3 条命令）


```bash
# 1) 建 venv（用 uv、venv 或 conda 均可）
python3.10 -m venv .venv


# 2) 装 agentcad + build123d（0.10 锁定）
.venv/bin/pip install "agentcad[mcp]" build123d==0.10.0


# 3) 验证
.venv/bin/python -c "import build123d, OCP; print('OK')"
.venv/bin/agentcad --help
```


- **版本锁定是关键**：build123d 必须 0.10.x，否则 cad/ 脚本 API 不兼容（0.10 的 `extrude` 无 `align`、面构造方式等）。
- 内核自带 cadquery-ocp（OCP），**不要**另装系统 OpenCASCADE。


---


## 3. 常用命令


```bash
# 生成模型（每个 cad/*.py 输出 STEP/STL 到 build/）
.venv/bin/python cad/assembly_v01.py # 主装配 13 实体


# 渲染 PNG（需要图形环境；无显示服务器时用 xvfb-run 前缀）
.venv/bin/agentcad render build/assembly/assembly_v01.step --view iso --name assy
# 注意：--name 一次只能配一个 --view


# 查看：任何 STEP 查看器（FreeCAD / 在线查看器等）
freecad build/assembly/assembly_v01.step
```


---


## 4. 验证清单


```bash
.venv/bin/python -c "import build123d; print(build123d.__version__)" # 0.10.0
.venv/bin/python cad/assembly_v01.py # 应打印 13 实体 / 总高 18.0 / FLOAT_GAP 0.5
# 用 STEP 查看器确认：13 实体，包围盒 100×100×18
```


---


## 5. 本机参考快照（非新机操作）


- OS：Ubuntu 22.04 x86_64；Python 3.10.12；agentcad v0.7.x；build123d 0.10.0。
- FreeCAD 1.0.2（AppImage 解压免 sudo，`~/.local/bin/freecadcmd`）。
- 项目：`/home/pi/projects/smart-coaster/`，git 仓库（无 remote，异地用 `git bundle` 或加 remote）。




## 3. 各工具安装细节


### 3.1 agentcad + build123d（核心，必须）


```bash
uv pip install --python .venv/bin/python 'agentcad[mcp]'==0.7.1 build123d==0.10.0
```


- **版本锁定**：build123d 必须 0.10.x（本项目所有 cad/ 脚本按 0.10 API 编写）。0.10 与 0.11 的 API 不兼容（`extrude` 无 `align`、面构造方式不同）。
- 内核依赖 `cadquery-ocp`（OCP）随 agentcad 自动装上，**不要**单独装系统 OpenCASCADE。
- 无 pip 的环境（本机 venv 无 pip），一律用 `uv pip install --python .venv/bin/python ...`。


### 3.2 FreeCAD 1.0.2（AppImage 解压，免 sudo，无 FUSE）


```bash
cd /home/pi/tools && mkdir -p freecad && cd freecad
# 官方 release：https://github.com/FreeCAD/FreeCAD-Bundle/releases/tag/1.0.2
# 文件名：FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage (~796MB)
# 校验：SHA256 e00be00ad9fdb12b05c5002bfd1aa2ea8126f2c1d4e2fb603eb7423b72904f61
./FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage --appimage-extract
# 解压出 squashfs-root/，可执行文件在 squashfs-root/usr/bin/{freecad,freecadcmd}
ln -s /home/pi/tools/freecad/squashfs-root/usr/bin/freecadcmd ~/.local/bin/freecadcmd
ln -s /home/pi/tools/freecad/squashfs-root/usr/bin/freecad ~/.local/bin/freecad
```


- **免 sudo 关键**：`--appimage-extract` 解压后直接跑内部二进制，不需要 FUSE、不需要挂载、不需要 root。
- 运行 `freecadcmd` 需要 wrapper 设置环境（`PYTHONHOME`、`LD_LIBRARY_PATH`、`SSL_CERT_FILE`）——见 `/home/pi/tools/freecad/freecad-wrapper.sh` 和 `README.md`。本机用软链到 `~/.local/bin` 即可直接 `freecadcmd --version`。
- **无头脚本用 `freecadcmd`；`freecad` 是 GUI**（无显示会挂起，属正常）。
- 可删掉原始 AppImage 省 ~800MB，只需保留 `squashfs-root/`。


### 3.3 Xvfb（无头 PNG 渲染必需）


```bash
# 免 sudo 解压 xvfb deb 到 ~/.local/bin：
# xvfb 二进制 + xvfb-run 脚本 + 依赖（libx* 等）一起放 ~/.local/bin
ls ~/.local/bin/Xvfb ~/.local/bin/xvfb-run # 确认
```


### 3.4 bin/agentcad-xvfb（本项目无头渲染包装）


```bash
# 内容要点：Xvfb + --no-daemon 强制前台，避免复用无显示环境的旧 daemon
xvfb-run -a "$VENV/agentcad" "$@" --no-daemon
# 用法：bin/agentcad-xvfb render X.step --view iso --name N --zoom Z
# 注意：--name 不能与多 view 同用（一次一个 view）
```


---


## 4. agentcad 无头渲染要点（易踩坑）


| 坑 | 规避 |
|---|---|
| PNG 渲染需要 X11/GLX | 必须 `xvfb-run -a` + `--no-daemon`（daemon 会复用旧显示环境导致黑图） |
| `--name` 与多 view 冲突 | 一次一个 view：`--view iso --name X`；多视角要分开跑 |
| `run` 内嵌 GLB 可能 fail | 但独立 `export stl,glb` 是 pass 的，两者互不影响 |
| 渲染 1mm 薄板/浅腔效果差 | 几何正确但渲染看不清时，用 FreeCAD `section` 或剖面脚本验证（如 `cad/hy928d_section_v02.py`） |


---



## 6. 验证清单（装完逐条跑）


```bash
# 工具版本
.venv/bin/python --version # 3.10.x
.venv/bin/python -c "import build123d; print(build123d.__version__)" # 0.10.0
agentcad --help # 有 command 列表
freecadcmd --version # FreeCAD 1.0.2 Rev 39319
which Xvfb xvfb-run # 无头渲染可用


# 核心闭环（建一个 1mm 薄板+浅腔，看 U 形腔是否渲染/导出）
.venv/bin/python cad/hy928d_real_v01.py # 生成 build/hy928d/*.step
freecadcmd 读 STEP 看 solid 数 = 1、BB 34×34×1.0 # FreeCAD 复核
timeout 200 bin/agentcad-xvfb render build/hy928d/hy928d_real_v01.step --view iso --name ok
```



