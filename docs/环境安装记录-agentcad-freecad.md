# 智能杯垫 · 本地 AI 辅助机械设计环境 — 安装与验证记录

> 日期：2026-11-03
> 主机：Ubuntu 22.04.5 LTS (x86_64, kernel 6.8)，Python 3.10.12
> 目标：agentcad + build123d（代码建模）→ STEP/STL/GLB → 渲染/查看
> 工作区：`/data/Documents/projects/SmartCoaster`

---

## 0. 结论（TL;DR）

| 项 | 结果 |
|---|---|
| agentcad | **0.7.1**，全局可用（`~/.local/bin/agentcad` 软链） |
| build123d | **0.10.0**（锁定；0.11 不兼容） |
| OCP（cadquery-ocp） | **7.8.1.1**，随包安装，未装系统 OCC |
| Python | 3.10.12（系统自带，直接用） |
| 项目环境 | `lumen/.venv`（独立，不污染系统 Python） |
| 无头渲染 | **不需要 Xvfb**：本机有 NVIDIA GLX，agentcad render 直接可用 |
| 工作室渲染 | 系统 python3 + VTK 9.1（PBR / 灯光 / 软阴影 / 爆炸图） |
| FreeCAD | 1.0.2（AppImage 解压，免 sudo）— 见 §6 |
| MCP | `.mcp.json.example`，指向项目 `.venv/bin/python -m agentcad.mcp` |

---

## 1. 环境检查（E0）

| 项 | 值 |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| Python | 3.10.12 (`/usr/bin/python3.10`) |
| pip | 26.3（venv 内） |
| Git | 已安装（本项目未初始化 git 仓库） |
| 磁盘 | `/data` 5.5T 可用 5.2T；`/home` 938G 可用 844G |
| 已有 CAD | 无（无 FreeCAD / 无 Xvfb） |
| AGENTS.md | 项目内**不存在**，`agentcad init` 新生成（无需备份） |
| 网络 | PyPI 直连约 100 KB/s；清华镜像约 15 MB/s，安装统一走镜像 |

> 说明：`/home` 与 `/data` 在会话沙箱外默认为只读，需要完整文件权限才能写
> `/data/Documents/tools` 与 `~/.local/bin`。本次以完整访问权限执行安装。

---

## 2. agentcad + build123d（E2）

```bash
python3.10 -m venv /data/Documents/tools/agentcad-venv
/data/Documents/tools/agentcad-venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    "agentcad[mcp]==0.7.1" "build123d==0.10.0"

# 全局可用（~/.local/bin 已在 PATH 中）
ln -sf /data/Documents/tools/agentcad-venv/bin/agentcad ~/.local/bin/agentcad
ln -sf /data/Documents/tools/agentcad-venv/bin/python  ~/.local/bin/agentcad-python
```

验证：

```
$ agentcad --help          # 列出 20+ 子命令
$ agentcad-python -c "import build123d, OCP; print(build123d.__version__, OCP.__version__)"
0.10.0 7.8.1.1
```

要点：

- **build123d 必须 0.10.x**：本项目脚本按 0.10 API 编写（`extrude` 无 `align`、
  面构造方式不同）。agentcad 0.7.1 的依赖约束正好是 `build123d>=0.10,<0.11`。
- 不要另装系统 OpenCASCADE；`cadquery-ocp` 随包带入。
- 本机 `~/.local/bin` 在 PATH 中，所以软链后**任意目录**都能直接 `agentcad`。

---

## 3. 项目环境与 MCP（E3）

```bash
cd /data/Documents/projects/SmartCoaster/lumen
python3.10 -m venv .venv
.venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    "agentcad[mcp]==0.7.1" "build123d==0.10.0"
agentcad init --name lumen
```

`agentcad init` 生成：`agentcad.json`、`AGENTS.md`、`.claude/skills/agentcad/SKILL.md`、`.agentcad/`。

MCP 配置（Claude Code / Cursor 等）：

```json
{
  "mcpServers": {
    "agentcad": {
      "command": "/data/Documents/projects/SmartCoaster/mechanical/lumen/.venv/bin/python",
      "args": ["-m", "agentcad.mcp"]
    }
  }
}
```

- 不同客户端字段名不同：Claude Code 用 `mcpServers`，部分客户端用 `mcp.servers`
  或 `context.mcpServers`；`command/args` 不变。
- 必须指向**项目 `.venv` 的 python**，不要依赖 `agentcad` 命令所在的 PATH。
- 本文件已存为 `lumen/.mcp.json.example`（未直接启用，避免影响当前会话）。

---

## 4. 无头渲染

```bash
agentcad render build/assembly/assembly_v01.step --view iso --name assy --size 1400x1000 --msaa 8 --no-daemon
```

- **本机不需要 Xvfb**：`vtkWindowToImageFilter` 走 NVIDIA GLX 离屏，直接出图。
  （恢复手册里 Xvfb 的方案适用于无 GLX 的机器。）
- `--name` 一次只能配一个 `--view`；多视角分开跑。
- 若 daemon 报 `daemon_response_lost`，加 `--no-daemon` 即可（本次遇到一次）。

工作室渲染（更好看，带材质/灯光/阴影/爆炸图）：

```bash
python3 tools/render_studio.py --shot all     # 需要系统 python3 + VTK 9.1
python3 tools/render_compare.py                # V1 方形 vs LUMEN 圆形
```

---

## 5. 最小闭环验证（E4）

`lumen/examples/minimal_plate.py`：100 × 100 圆角板，厚度参数化。

```bash
agentcad run examples/minimal_plate.py --label plate_t6  --no-daemon
agentcad run examples/minimal_plate.py --label plate_t10 --params T=10 --no-daemon
agentcad export v6_plate_t6/output.step --format stl,glb --no-daemon
```

| 版本 | 尺寸 | 体积 | is_valid |
|---|---|---|---|
| T=6 | 100 × 100 × 6 | 59 670 mm³ | true |
| T=10 | 100 × 100 × 10 | 99 450 mm³ | true |

→ 参数修改有效；STEP / STL / GLB / preview 全部通过。

真实项目模型（LUMEN）：

```bash
agentcad run cad/lumen_assembly_v01.py --label lumen_v3 --no-daemon
# output_type=assembly, 13 named parts, 110x110x17, 63 849 mm³, is_valid=true
```

---

## 6. FreeCAD 1.0.2（已安装并验证）

### 6.1 安装

```bash
# 官方 AppImage（GitHub 直连 5.6 MB/s，2m18s）
curl -L -C - -o FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage \
  https://github.com/FreeCAD/FreeCAD-Bundle/releases/download/1.0.2/FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage
sha256sum FreeCAD_*.AppImage   # e00be00a...4f61 ✓
chmod +x FreeCAD_*.AppImage
./FreeCAD_*.AppImage --appimage-extract   # 免 sudo / 免 FUSE，解压 3.1 GB
```

- 安装根：`/data/Documents/tools/freecad/`（`squashfs-root/` + 原 AppImage 保留）
- 入口：`~/.local/bin/freecad`（GUI）、`~/.local/bin/freecadcmd`（CLI），都指向
  `/data/Documents/tools/freecad/freecadcmd-wrapper.sh`（按 `$0` basename 分派）
- 版本：`FreeCAD 1.0.2 Revision: 39319`，内置 Python 3.11.13 / OCCT 7.8.1

### 6.2 STEP 验证（LUMEN 总装）

| 指标 | 期望 | FreeCAD 实测 |
|---|---|---|
| Shape | Compound | Compound |
| Solids | 13 | **13** |
| 包围盒 | 110 × 110 × 17 | **109.99 × 110.00 × 17.00**（三角化） |
| 总体积 | ≈63 797 mm³ | **63 796.935 mm³**（0.000%） |

逐件体积与 `lumen/build/assembly/meta.json` 的 13 条记录完全一致。
预览：`/data/Documents/tools/freecad/assembly_preview.png`。

方形 V1 也做了同样的复核（`square_v1/tools/freecad_verify.py`）：

| 指标 | 期望 | FreeCAD 实测 |
|---|---|---|
| Solids | 12 | **12** |
| 包围盒 | 100 × 100 × 18 | **100.00 × 100.00 × 18.00** |
| 体积 | 78 086 mm³ | **78 086.3 mm³**（−0.000%） |
完整记录：`/data/Documents/tools/freecad/INSTALL_NOTES.md`。

### 6.3 两个 FreeCAD 坑（重要）

1. **`Shape.BoundBox` 会因环面高估**：解析 bbox 报 119.063 mm（plate 112.569），
   这是 OCCT 用未裁剪 torus 曲面片范围算 bbox 的已知行为。模型实际是
   110×110×17（三角化顶点统计准确）。用 FreeCAD 做尺寸校验时按三角化顶点算。
2. **`freecadcmd script.py` 里 `__name__ != "__main__"`**：用
   `if __name__ == "__main__":` 会静默跳过整个脚本。直接写顶层代码，并
   `sys.stdout.flush()`；不要 `sys.exit()`（会丢缓冲输出）。

### 6.4 GUI 与无头

- GUI（`freecad`）需要 X：本机桌面 `DISPLAY=:0` 可用（subagent 实测导入
  141 objects / 125 shapes、等轴测 + ViewFit + 截图成功）。
- `QT_QPA_PLATFORM=offscreen` 无 GL，会报 `No valid GL context found!`。
- 会话后段桌面 X 退出、GLX 不可用；已在 `square_v1/.tools/xvfb/` 放了
  解压版 Xvfb（~2 MB，免 sudo），任何需要 GL 的命令可这样跑：

```bash
cd /data/Documents/projects/SmartCoaster/square_v1
./.tools/xvfb/usr/bin/Xvfb :99 -screen 0 1600x1200x24 &
DISPLAY=:99 agentcad run cad/square_assembly_v01.py --label square_v1 --no-daemon
DISPLAY=:99 python3 tools/render_studio.py --shot all
```

---

## 7. 旧版 V1 方形脚本（保留）

原始 `cad/*.py`（M1.2 基线）**未改动**。这些文件从旧机恢复时带了 440 处
U+00A0 不可见空格，Python 3.10 直接报 `SyntaxError: invalid non-printable character`。

处理：保留原件，另存可运行副本到 `legacy/src/`（仅替换 U+00A0 → 空格）：

```bash
cd /data/Documents/projects/SmartCoaster
python3 - <<'PY'
from pathlib import Path
for f in Path("cad").glob("*.py"):
    s = f.read_text(encoding="utf-8").replace("\u00a0", " ")
    Path("legacy/src", f.name).write_text(s, encoding="utf-8")
PY
cd legacy && for f in src/*.py; do ../lumen/.venv/bin/python "$f"; done
```

结果：四个脚本全部成功（方形壳 100×100×18、HY928D、C 环 PCB、包装研究），
输出在 `legacy/` 与 `build/` 下。

---

## 8. 已知问题 / 注意事项

1. **agentcad 脚本不能自己写 STEP**：`export_step` 会被静态校验拒绝；脚本只
   `show_object`，STEP 由 agentcad 写。因此本项目拆成：
   - `cad/lumen_model.py`（几何源，无 I/O）
   - `cad/lumen_assembly_v01.py`（agentcad 入口）
   - `cad/export_v01.py`（独立 python 导出 13 件 STEP/STL）
2. **agentcad 以非 `__main__` 模块名执行脚本**，入口脚本末尾不能写
   `if __name__ == "__main__":`。
3. **GLB 网格校验**：agentcad 导出的 GLB 曾报 1 条 open edge / 1 条非流形边
   （STEP 本身 13 个闭合壳、全部 valid）。这属于网格化伪影，不影响 STEP；
   若交付打印用 STL，请用 `verify_report.json` + 切片软件双重确认。
4. **daemon**：多次连续 render 时出现过 `daemon_response_lost`，加
   `--no-daemon` 稳定。
5. **版本锁定**：不要 `pip install -U build123d`；会拉到 0.11 导致 API 不兼容。
