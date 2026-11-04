# 环境与工具链审计（AUDIT_ENV）

> 审计人：env-audit（共享任务 `task-9`） · 日期：2026-11-04 · 工作区：`/data/Documents/projects/SmartCoaster`（审计开始时 HEAD = `ae17e10`）
>
> **审计方式：只读**。全部版本号由本次审计**实际执行命令**获得（不抄安装记录）；只读取安装树、配置、日志和 git 元数据。
> **未安装/升级任何工具，未修改 `requirements.yaml`，未改源码。** 本仓库唯一新增文件就是本报告。
>
> 交叉核对材料：`requirements.yaml`、`AGENTS.md`、`docs/环境安装记录-agentcad-freecad.md`、`/data/Documents/tools/{FEA_INSTALL_NOTES.md,SIM_INSTALL_NOTES.md,SIM_VERIFY.log,verify_sim_tools.sh}`、`/data/Documents/tools/freecad/INSTALL_NOTES.md`、`docs/恢复：*.md`、`docs/HANDOFF.md`、`docs/VERIFY_REPORT.md`。

---

## 0. 结论（TL;DR）

1. **版本号：`requirements.yaml` 列出的 15 项全部与实测一致（15/15，无版本偏差）。** 逐项证据见 §1。
2. 但存在 **3 类"不一致/缺口"**（详见 §2）：
   - **requirements 缺项**：实际在用的 **Freerouting 2.5.0（自带 Java 25.0.4.1）**、**Xvfb（xorg-server 2:21.1.4）** 未写入 `requirements.yaml`；
   - **同名命令版本歧义**：登录 shell PATH 上的 `pytest` 是 **9.1.0**（与 requirements 的 **9.2.0** 不同名同命令、不同版本），项目正确的 9.2.0 在 `sim-venv`，入口是 `pytest-sim`；
   - **文档与现实不一致**（3 处，见 §2.3）：恢复文档称仓库"无 remote"、称 ESP-IDF `version.txt` = v6.1、称 Xvfb 在 `~/.local/bin`，均与实测不符。
3. **合规发现（需 Lead/项目负责人决策，审计只记录不处理）**：
   - ⚠️ **有项目文件上传第三方（GitHub）的痕迹**：`origin = git@github.com:bdus/SmartCoaster.git`，`.git/logs/refs/remotes/origin/master` 记录 **27 条 `update by push`**，最新推送 `495e7ba`（2026-11-04 19:36）。这与 `AGENTS.md` 第 6 条"不传项目文件到第三方"及恢复文档"无 remote"直接冲突。当前 HEAD `ae17e10` 尚未推送（`ahead 1`）。**是否合规取决于项目负责人是否授权过该 GitHub 仓库**，审计无法从本机判定授权状态。
   - ⚠️ **Freerouting 2.5.0 遥测默认开启**：`allow_telemetry: true`、`disable_analytics: false`；布线日志出现 `Analytics tracking: ... /v1/analytics/identify - SocketTimeoutException`（**已尝试向第三方发送匿名分析数据**，本次因超时失败）。未发现上传原理图/PCB 等项目文件，但建议显式关闭。
   - ✅ **Wokwi 未上传**：仓库无 `WOKWI_CLI_TOKEN`，只使用了 `wokwi-cli lint --offline`。pip 仅经清华 PyPI 镜像**下载**依赖，GitHub 仅**下载** FreeCAD/Blender/Wokwi 二进制，均为下载而非上传项目文件。
4. **安装位置（AGENTS.md 第 6 条）**：主力工具都在 `/data/Documents/tools/<tool>`，`~/.local/bin` 的 11 个工具软链**全部有效、无断链**；**唯一偏差**是 Freerouting/Xvfb 放在项目 `.tools/`（非 `/data/Documents/tools`）。ESP-IDF/QEMU 是用户级既有安装（`~/.espressif`），非本次新增。
5. **可复现性**：依赖关系已理清，最短复现路径见 §6（含每步验证命令）；已知坑 18 条见 §7。

---

## 1. 版本对照表（实测）

> 时间：2026-11-04 20:25–20:30。`实际版本` 一列均来自本表"实测命令"的输出。平台：Ubuntu 22.04.5 LTS x86_64，kernel `6.8.0-138-generic`。

| 工具 | `requirements.yaml` | **实测版本** | 实测命令（关键输出） | 安装位置 | 入口 |
|---|---|---|---|---|---|
| Python | `python: "3.10.12"` | **3.10.12** ✅ | `python3 --version` → `Python 3.10.12` | `/usr/bin/python3.10` | `python3` |
| agentcad | `agentcad: "0.7.1"` | **0.7.1** ✅ | `pip show agentcad` → `Version: 0.7.1`（`--version` 不被支持） | `/data/Documents/tools/agentcad-venv` + 项目 `mechanical/{lumen,square_v1}/.venv` | `~/.local/bin/agentcad`、`agentcad-python` |
| build123d | `build123d: "0.10.0"` | **0.10.0** ✅ | `python -c "import build123d; print(build123d.__version__)"` | 同上 venv | venv 内 |
| OCP (cadquery-ocp) | `ocp: "7.8.1.1"` | **7.8.1.1** ✅ | `python -c "import OCP; print(OCP.__version__)"` | 同上 venv | venv 内 |
| FreeCAD | `freecad: "1.0.2"` | **1.0.2 Rev 39319** ✅ | `~/.local/bin/freecadcmd --version` → `FreeCAD 1.0.2 Revision: 39319 (Git)`；内置 Python 3.11.13 | `/data/Documents/tools/freecad/squashfs-root`（AppImage 解压） | `~/.local/bin/{freecad,freecadcmd}` |
| CalculiX ccx | `calculix: "2.22"` | **2.22** ✅ | `~/.local/bin/ccx -v` → `This is Version 2.22`（**注意 rc=201**） | FreeCAD 树 `.../usr/bin/ccx` | `~/.local/bin/ccx` |
| Gmsh | `gmsh: "4.13.1"` | **4.13.1** ✅ | `~/.local/bin/gmsh --version` → `4.13.1` | FreeCAD 树 `.../usr/bin/gmsh` | `~/.local/bin/gmsh` |
| VTK | `vtk: "9.1.0"` | **9.1.0** ✅ | `python3 -c "import vtk; print(vtk.vtkVersion.GetVTKVersion())"` | 系统 `/usr/lib/python3/dist-packages/vtkmodules` | 系统 `python3` |
| KiCad | `kicad: "9.0.9"` | **9.0.9** ✅ | `~/.local/bin/kicad-cli version` → `9.0.9`（**stderr 有 schema 警告，rc=0**） | `/data/Documents/tools/kicad`（deb 解包，未注册 dpkg） | `~/.local/bin/{kicad,kicad-cli}` |
| ngspice | `ngspice: "36"` | **ngspice-36**（deb `36+ds-1ubuntu0.1`）✅ | `~/.local/bin/ngspice -v` → `** ngspice-36 : Circuit level simulation program` | `/data/Documents/tools/ngspice` | `~/.local/bin/ngspice` |
| ESP-IDF | `esp-idf: "6.1"` | **6.1.0（显示 `ESP-IDF v6.1`）** ✅ | `source /home/pi/.espressif/tools/activate_idf_v6.1.sh; idf.py --version` → `ESP-IDF v6.1`；`tools/cmake/version.cmake` = 6.1.0 | `/home/pi/.espressif/v6.1/esp-idf`（EIM 管理，既有） | `activate_idf_v6.1.sh` → `idf.py` |
| pytest | `pytest: "9.2.0"` | **9.2.0**（sim-venv）✅ / 系统 `pytest` **9.1.0** ⚠️ | `/data/Documents/tools/sim-venv/bin/python -m pytest --version` → `pytest 9.2.0`；`~/.local/bin/pytest --version` → `pytest 9.1.0` | `/data/Documents/tools/sim-venv` | `~/.local/bin/pytest-sim`（**推荐**）；`~/.local/bin/pytest`（9.1.0） |
| Wokwi CLI | `wokwi-cli: "0.29.1"` | **0.29.1 (0aa185144b92)** ✅ | `~/.local/bin/wokwi-cli --version` | `/data/Documents/tools/wokwi-cli/wokwi-cli`（static-pie） | `~/.local/bin/wokwi-cli` |
| Blender | `blender: "4.5.3"` | **4.5.3 LTS** ✅ | `~/.local/bin/blender --version` → `Blender 4.5.3 LTS` | `/data/Documents/tools/blender-4.5.3-linux-x64`（`blender` 软链） | `~/.local/bin/blender` |
| QEMU | `qemu: "9.2.2"` | **9.2.2 (esp_develop_9.2.2_20260417)** ✅ | `.../qemu-xtensa/esp_develop_9.2.2_20260417/qemu/bin/qemu-system-xtensa --version` | `/home/pi/.espressif/tools/tools/qemu-xtensa/...`（ESP-IDF 组件） | `idf.py qemu` 或绝对路径（**不在 PATH**） |
| **Freerouting** | **（缺项）** | **v2.5.0 (build-date 2026-10-05)** | 运行 `bin/freerouting` 日志 → `Freerouting v2.5.0`（`--version` 不被支持） | 项目 `.tools/freerouting/freerouting-2.5.0-linux-x64`（89 MB zip 解压） | `electronics/kicad/scripts/route_2l.sh` |
| **Java（Freerouting 自带）** | **（缺项）** | **25.0.4.1** | `.../lib/runtime/release` → `JAVA_VERSION="25.0.4.1"` | 同上 `lib/runtime` | 由 Freerouting 启动器自用 |
| **Xvfb** | **（缺项）** | **xorg-server 2:21.1.4-2ubuntu1.7~22.04.16** | Xvfb 启动后 `xdpyinfo` → `version number: 11.0`；版本取自包内 `changelog.Debian.gz` | 项目 `.tools/xvfb`（**系统未安装 Xvfb**） | `.tools/xvfb/usr/bin/Xvfb` |
| Node / npm | （未列，非必需） | **v24.15.0 / 11.12.1** | `node --version` / `npm --version` | `~/.nvm/.../v24.15.0` | — |

**结论：`requirements.yaml` 15/15 与实测一致；缺项与歧义见 §2。**

---

## 2. 不一致项清单

### 2.1 requirements.yaml 缺项（严重度：中）

| 缺项 | 实际状态 | 影响 |
|---|---|---|
| **Freerouting 2.5.0** | 已安装并在用（2 层板布线成功：`route_2l.sh` 日志 `Freerouting v2.5.0`，最终 0 unrouted / 0 violations，SES 50 KB） | 换机复现时只按 requirements 装会**无法复现 PCB 布线** |
| **自带 Java 25.0.4.1** | Freerouting AppImage 自带运行时 | 同上；避免误装系统 Java |
| **Xvfb（xorg-server 21.1.4）** | 系统无 Xvfb；项目 `.tools/xvfb` 提供 | Freerouting（AWT 窗口）与无头渲染需要；ARL 无它则布线/渲染不可复现 |

> 建议（由 Lead/维护者执行，本次未改）：在 `requirements.yaml` 增补 `freerouting: "2.5.0"`、`java: "25.0.4.1"`、`xvfb: "2:21.1.4-2ubuntu1.7~22.04.16"`，或在安装记录中显式声明"缺项以此为准"（`SIM_INSTALL_NOTES.md` §0 已有类似声明）。

### 2.2 同名命令版本歧义（严重度：中，易误导自动化）

- `requirements.yaml` 写 `pytest: 9.2.0`；`pytest-sim` → **9.2.0 ✅**，但登录 shell 里 `pytest`（`~/.local/bin/pytest`）→ **9.1.0**。
- 因此"`pytest --version` 是否等于 requirements"取决于用哪个入口。**项目测试请固定用 `pytest-sim`。**
- 相关事实：`tests/` 下目前没有 pytest 用例（只有 README 和 C 测试），所以本次无法用项目用例反证 9.2.0 的行为；sim-venv 自带 3 个冒烟测试为 9.2.0 证据。

### 2.3 文档与实测不一致（严重度：低—中，影响复现准确性）

| 文档表述 | 实测 | 位置 |
|---|---|---|
| 恢复文档："本项目…git 仓库（**无 remote**，异地用 `git bundle` 或加 remote）" | **有 remote**：`origin git@github.com:bdus/SmartCoaster.git`，27 次 push 记录 | `docs/恢复：智能杯垫本地 AI 辅助机械设计环境.md` §5 |
| `SIM_INSTALL_NOTES.md`："IDF 源码…（`version.txt` = `v6.1`）" | `~/.espressif/v6.1/esp-idf/version.txt` **不存在**；版本实际来自 `tools/cmake/version.cmake` = **6.1.0** | `SIM_INSTALL_NOTES.md` §1 |
| 恢复文档 §3.3："xvfb 解压到 **`~/.local/bin`**"；`环境安装记录` §6.4 也提 `square_v1/.tools/xvfb` | 系统无 Xvfb；入口为 **项目 `.tools/xvfb`**（`~/.local/bin` 下无 Xvfb） | 两份恢复/安装文档 |
| `SIM_INSTALL_NOTES.md` §4.2：deb 名 `kicad_9.0.9~ubuntu22.04.1_amd64.deb` | 实际缓存文件名 `kicad_9.0.9_amd64.deb`（版本同为 9.0.9，仅包名不同） | `/data/Documents/tools/kicad-debs/` |
| `环境安装记录` §6.1：安装根 `/data/Documents/tools/freecad` | ✅ 一致；AppImage 保留 795,892,216 B，**sha256 = `e00be00a…4f61` 与文档完全一致** | — |

### 2.4 版本一致性结论

**没有发现任何 `requirements.yaml` 已列工具的版本号与实测不符。** 所有差异都属于"缺项 / 同名入口 / 文档陈旧"，不是"装错版本"。

---

## 3. 安装位置 / 许可 / 免费本地核对（AGENTS.md 第 6 条）

### 3.1 位置与入口

| 工具 | 安装位置 | 是否在 `/data/Documents/tools/<tool>` | `~/.local/bin` 入口 | 软链有效 |
|---|---|---|---|---|
| agentcad / build123d / OCP | `/data/Documents/tools/agentcad-venv`；项目 venv 在 `mechanical/*/.venv` | ✅ | `agentcad`、`agentcad-python` | ✅ |
| FreeCAD 1.0.2（+ ccx + gmsh） | `/data/Documents/tools/freecad`（3.8 GB） | ✅ | `freecad`、`freecadcmd`、`ccx`、`gmsh` | ✅ |
| KiCad 9.0.9 | `/data/Documents/tools/kicad`（833 MB）+ deb 缓存 `kicad-debs`（122 MB） | ✅ | `kicad`、`kicad-cli` | ✅ |
| ngspice 36 | `/data/Documents/tools/ngspice`（7.8 MB）+ `ngspice-debs` | ✅ | `ngspice` | ✅ |
| pytest/科学栈 | `/data/Documents/tools/sim-venv`（271 MB） | ✅ | `pytest-sim`（普通脚本，非软链） | ✅ |
| Wokwi CLI 0.29.1 | `/data/Documents/tools/wokwi-cli`（54 MB） | ✅ | `wokwi-cli` | ✅ |
| Blender 4.5.3 | `/data/Documents/tools/blender-4.5.3-linux-x64`（1.2 GB，另保留 360 MB tar.xz） | ✅ | `blender` | ✅ |
| ESP-IDF 6.1 / QEMU 9.2.2 | `/home/pi/.espressif/{v6.1/esp-idf,tools}`（EIM，**既有安装**） | —（非新增；用户级） | 无（activate 脚本进 PATH） | — |
| **Freerouting 2.5.0 + Java 25** | **项目 `.tools/freerouting/`**（157 MB） | ❌ **偏差** | 无 | — |
| **Xvfb 21.1.4** | **项目 `.tools/xvfb/`**（2.3 MB） | ❌ **偏差** | 无 | — |
| node 24.15.0 / npm 11.12.1 | `~/.nvm/...`（既有） | —（非项目必需） | — | — |

- **软链核对**：`find ~/.local/bin -xtype l` 无输出（**无断链**）；11 个工具软链逐项 `readlink -f` + 存在性检查全部 OK（`agentcad`、`agentcad-python`、`blender`、`ccx`、`freecad`、`freecadcmd`、`gmsh`、`kicad`、`kicad-cli`、`ngspice`、`wokwi-cli`）。
- **偏差说明**：Freerouting/Xvfb 放在项目 `.tools/`（且 `.gitignore` 忽略）便于按项目隔离、避免污染全局工具目录；但严格按 AGENTS.md 第 6 条"新工具装到 `/data/Documents/tools/<tool>`"属**偏差**。建议：要么迁移到 `/data/Documents/tools/{freerouting,xvfb}` 并改 `route_2l.sh` 路径，要么在 `requirements.yaml`/安装记录中显式登记为"项目内本地工具"。
- **未安装收费软件**：逐项核对均为免费/自由软件或免费 CLI（Wokwi CLI 免费但**非开源**、云仿真需免费账号 token）；无任何订阅/授权型付费工具。

### 3.2 许可证核对（以安装树内 license/copyright/包元数据为准）

| 工具 | 许可证（证据） | 免费 | 本地 |
|---|---|---|---|
| agentcad | **Apache-2.0**（dist-info `License-Expression: Apache-2.0`） | ✅ | ✅ |
| build123d | **Apache-2.0**（`pip show License: Apache-2.0`） | ✅ | ✅ |
| OCP (cadquery-ocp) | **LGPL-2.1（OCCT 系）**；wheel 内未附 license 文件、元数据未声明 → 以 OCCT 上游为准 | ✅ | ✅ |
| pytest | **MIT**（dist-info `License-Expression: MIT`） | ✅ | ✅ |
| VTK 9.1.0 | **BSD-3-clause**（`/usr/share/doc/python3-vtk9/copyright`） | ✅ | ✅（系统包） |
| FreeCAD 1.0.2 | **LGPL-2.1+**（`.../share/doc/FreeCAD/LICENSE.html`：`LGPL2+ license`） | ✅ | ✅ |
| CalculiX ccx 2.22 | FreeCAD 自带；上游 **GNU GPL**（二进制 banner：`CalculiX Version 2.22, Copyright(C) 1998-2024 Guido Dhondt`） | ✅ | ✅ |
| Gmsh 4.13.1 | **GPL-2.0-or-later + 例外**（`.../doc/gmsh/LICENSE.txt`） | ✅ | ✅ |
| KiCad 9.0.9 | **GPL**（`/data/Documents/tools/kicad/usr/share/doc/kicad/copyright` 标注 `GPL v2`） | ✅ | ✅ |
| ngspice 36 | **GPL-2+ 为主**（Debian `copyright` 同时列出 `GPL-2+`、`LGPL-2.1+`、`BSD-3/4`、`Expat` 等，属多许可组合） | ✅ | ✅ |
| Wokwi CLI 0.29.1 | 二进制未随附 license 文件；**免费使用，非开源**；云仿真需 token | ✅ | ✅（仅离线 lint） |
| Blender 4.5.3 | **GNU GPL**（`copyright.txt`："subject to the GNU GPL license"） | ✅ | ✅ |
| ESP-IDF 6.1 | **Apache-2.0**（`~/.espressif/v6.1/esp-idf/LICENSE`） | ✅ | ✅ |
| QEMU 9.2.2 | 随 ESP-IDF 分发；上游 QEMU 为 **GNU GPL** | ✅ | ✅ |
| Freerouting 2.5.0 | **GPL-3.0**（解压目录 `LICENSE`） | ✅ | ✅ |
| 自带 Java 25.0.4.1 | OpenJDK 运行时（随 Freerouting，`lib/runtime/legal/*` 许可证文本齐全；OpenJDK 为 GPL-2.0+CE） | ✅ | ✅ |
| Xvfb (xorg-server 21.1.4) | **MIT/X11 系**（`.../doc/xvfb/copyright`） | ✅ | ✅ |

> 未发现任何需付费/需联网授权的工具。唯一"第三方服务"是 Wokwi 云仿真（**未启用**，只跑离线 lint）。

---

## 4. 第三方上传 / 网络痕迹核查

> 依据 `AGENTS.md` 第 6 条"**不传项目文件到第三方**"。

### 4.1 ⚠️ 发现：项目已推送到 GitHub（需负责人确认授权）

实测证据（`git` 只读命令）：

```
$ git remote -v
origin  git@github.com:bdus/SmartCoaster.git (fetch)
origin  git@github.com:bdus/SmartCoaster.git (push)

$ git branch -vv
* master ae17e10 [origin/master: ahead 1] 2-layer PCB routed to 0 DRC / 0 unconnected; ...

$ git reflog show refs/remotes/origin/master
495e7ba refs/remotes/origin/master@{0}: update by push
0db47df ...@{1}: update by push
...（共 27 条）
```

- `.git/logs/refs/remotes/origin/master` 的 27 条记录全部是 **`update by push`**（非 fetch），最早 `02dab415…`、最新 `495e7ba`（时间戳 `1793792170` = 2026-11-04 19:36:10 +0800）。`FETCH_HEAD` 不存在、`packed-refs` 为空。
- **结论**：至少到 `495e7ba` 为止的仓库内容曾被 push 到 `github.com/bdus/SmartCoaster`；**当前 HEAD `ae17e10` 尚未推送（ahead 1）**。
- **不写推测**：审计无法判断该 GitHub 仓库是私有还是公开、项目负责人是否明确授权过。若该 remote 是项目负责人有意设置（私有仓库、自有账号），则需在报告中如实说明并保留；若属误配，应 `git remote remove origin`（**审计未执行**，留待负责人决策）。
- 与文档冲突：`docs/恢复：智能杯垫本地 AI 辅助机械设计环境.md` §5 明确写"无 remote"，建议更新该文档或删除 remote。

### 4.2 ⚠️ Freerouting 2.5.0 遥测：默认开启且已尝试外发

- 配置（`/.tools/fr-home/config/freerouting/freerouting.json`）：
  ```json
  "profile": { "allow_telemetry": true, "allow_contact": true },
  "usage_and_diagnostic_data": { "disable_analytics": false, ... }
  ```
- 布线日志（`electronics/kicad/build/freerouting_2l.log`）：
  ```
  WARN Analytics tracking: first delivery failure in this window -
       /v1/analytics/identify - SocketTimeoutException: Read timed out.
  ```
  → **确实发起了向 Freerouting 第三方的匿名分析上报**（本次网络超时失败）。
- 未发现上传 `.kicad_pcb/.dsn/.ses/原理图` 等**项目文件**的内容；上报的是匿名 usage 事件。但为严格满足"不传第三方"，建议在 `route_2l.sh` 的隔离配置中预置 `allow_telemetry:false` + `disable_analytics:true`（**本次只读审计未改**）。
- 另：Freerouting 1.9.0 的旧日志（`logs/freerouting.log`）也见到 `FRAnalytics` 调用（因 `analytics` 为 null 抛 NPE），旧版本同样尝试过分析上报。

### 4.3 ✅ 其余网络行为

| 检查项 | 结论 |
|---|---|
| `WOKWI_CLI_TOKEN` / 任何 API key 是否存在于仓库/环境 | **无**（`env` 无 token；仓库 grep 无 `WOKWI_CLI_TOKEN=...`、无 API key）；Wokwi 只跑 `lint --offline` |
| Wokwi 云仿真是否运行过 | **未运行**（无 token；`firmware/wokwi/wokwi.toml` 注释明确只做 offline lint） |
| pip 依赖来源 | 清华 PyPI 镜像（**下载**依赖包，非上传项目文件）；属常规镜像，不涉及项目内容 |
| 二进制下载来源 | GitHub Releases（FreeCAD/Blender/Wokwi CLI）——**下载**，非上传 |
| 仓库内是否硬编码外发脚本 | 未发现 `curl -F/--upload`、S3/OSS、云 API 调用等把项目文件发出去的代码；`route_2l.sh` 只调用本地 Freerouting |

---

## 5. 关键环境变量 / 封装脚本核对

### 5.1 `~/.local/bin` 与 PATH（**重要坑**）

- `~/.profile`（login shell）把 `~/.local/bin` 加进 PATH；**但 DSH 的非登录 `bash -c`（Agent 每次调用）PATH 里没有 `~/.local/bin`**：

  ```
  # 非登录 shell（Agent 工具调用）
  $ echo $PATH
  /home/pi/.npm/_npx/.../.bin:/node_modules/.bin:.../nvm/.../bin:/usr/local/bin:/usr/bin:/bin
  $ command -v kicad-cli   # → 空
  # 登录 shell
  $ bash -lc 'echo $PATH'
  /home/pi/.local/bin:/home/pi/.npm/...:...:/bin:/snap/bin
  $ bash -lc 'kicad-cli version'   # → 9.0.9 ✅
  ```
- **影响**：`/data/Documents/tools/verify_sim_tools.sh` 里直接写 `ngspice -v`、`kicad-cli version`、`wokwi-cli --version`、`pytest-sim`；在非登录 shell 下这些会 `command not found`（脚本 `set -u` 不退出，但会静默产出一堆空结果）。**复跑必须 `bash -lc` 或补 PATH。**
- 软链清单（全部有效）：`agentcad`、`agentcad-python`、`blender`、`ccx`、`freecad`、`freecadcmd`、`gmsh`、`kicad`、`kicad-cli`、`ngspice`、`pytest`（9.1.0）、`pytest-sim`、`wokwi-cli`。

### 5.2 KiCad `env.sh` 与 wrapper

`/data/Documents/tools/kicad/bin/env.sh`（实测内容）：

```bash
export KICAD_ROOT=/data/Documents/tools/kicad
export LD_LIBRARY_PATH="$KICAD_ROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export KICAD9_SYMBOL_DIR="$KICAD_ROOT/usr/share/kicad/symbols"
export KICAD9_FOOTPRINT_DIR="$KICAD_ROOT/usr/share/kicad/footprints"
export KICAD9_TEMPLATE_DIR="$KICAD_ROOT/usr/share/kicad/template"
export KICAD9_3DMODEL_DIR="$KICAD_ROOT/usr/share/kicad/3dmodels"
export KICAD_CONFIG_HOME="${KICAD_CONFIG_HOME:-$KICAD_ROOT/config}"
export KICAD_USER_TEMPLATE_DIR="$KICAD_ROOT/usr/share/kicad/template"
```

- 包装脚本 `bin/kicad-cli`、`bin/kicad` 均先 `source .../env.sh` 再 `exec` 真二进制；`~/.local/bin/{kicad,kicad-cli}` 指向包装脚本。✅
- 配置隔离在 `/data/Documents/tools/kicad/config`（默认）；项目里还使用 `XDG_CONFIG_HOME=$ROOT/.tools/kicad-config`（`electronics/kicad/scripts/build.sh`）与 `electronics/.tools/kicad-config`，共三处配置目录并存——**不是错误，但换机时需知道用哪个**。
- **`kicad-cli` schema 警告**（每次调用必现，rc=0）：
  ```
  Error: schema file '/usr/share/kicad/schemas/api.v1.schema.json' not found
  ```
  因 KiCad 把 IPC API schema 路径编译成 `/usr/share/kicad`，而解包在 `/data/Documents/tools/kicad`；不影响 ERC/DRC/导出，**自动化不要以 stderr 非空判失败**。
- `kicad --version` 不被支持（wx 参数解析器打印 `Unknown long option 'version'`，rc=0）；版本统一用 `kicad-cli version`。
- **未安装 `kicad-packages3d`**（数 GB）：3D Viewer / `pcb render` 会缺模型；ERC/DRC/Gerber 不受影响。

### 5.3 Xvfb（系统无 → 项目内）

- `command -v Xvfb` → **无系统 Xvfb**。
- 项目自带：`.tools/xvfb/usr/bin/Xvfb`（xorg-server `2:21.1.4-2ubuntu1.7~22.04.16`，免 sudo 解包）+ `xvfb-run`。
- 实测启动 `:98` 后 `xdpyinfo` 连接成功（`version number: 11.0`）；日志有 `_XSERVTransmkdir: ERROR: euid != 0 ... /tmp/.X11-unix will not be created`，但显示仍可用（TCP 回退）。
- 注意：`/tmp` 每次 bash 调用都是**独立 tmpfs**（见 §7 坑 1），所以 `route_2l.sh` 必须在同一次调用内 `mkdir -p /tmp/.X11-unix` + 起 Xvfb + 跑 Freerouting。

### 5.4 ESP-IDF activate 脚本退出码坑（**根因已定位**）

- 实测：`source /home/pi/.espressif/tools/activate_idf_v6.1.sh` 后 **`$? = 1`**，但 `idf.py --version`、`IDF_PATH`、`IDF_TOOLS_PATH`、venv 均正常。
- **根因**（`bash -x` 追踪 + 单独复现）：脚本末尾

  ```bash
  if [ -n "$_EIM_BIN" ] && [ -x "$_EIM_BIN" ]; then
      "$_EIM_BIN" select "v6.1" >>/dev/null 2>&1 && printf '%s\n' "eim select v6.1"
  fi
  ```

  `_EIM_BIN=/usr/bin/eim` 存在，但 `eim select v6.1` 失败（单独执行：`Error executing CLI: Failed to setup logging`，rc=1），而 `&&` 短路使 `if` 体返回 1 → `source` 返回 1。
- **影响**：写 `source ... && cd firmware/esp32 && idf.py build` 会因 `&&` 短路"看起来什么都没发生"。**正确写法**：用 `;` 分步，或 `source ... ; true`。`docs/VERIFY_REPORT.md` 已记录该坑，本次确认根因。
- 补充：activate 脚本**不会把 QEMU 加进 PATH**（脚本内无 qemu 相关 PATH 项）；QEMU 通过 `idf.py qemu` 或绝对路径调用。

### 5.5 XDG / HOME 只读与缓存

- 本机 sandbox 下 `~/.config`、`~/.local/state`、`~/.cache` **均不可写**（实测 `RO`）：
  - matplotlib 首次 import 报 `~/.config/matplotlib is not a writable directory`，自动退到 `/tmp` 临时目录并给警告；
  - Freerouting 默认要写 `~/.config/freerouting`、`~/.local/state/freerouting/logs` → 报 `Could not create directory`。
- **正确做法**（项目脚本已采用）：把 `XDG_CONFIG_HOME`/`XDG_STATE_HOME`/`XDG_CACHE_HOME`/`MPLCONFIGDIR` 指到工作区 `.tools/{fr-home,mp-config,...}`。项目 `.tools/mplconfig/fontlist-v390.json` 已生成（matplotlib 缓存）。
- `/tmp` 为 32 GB tmpfs，且**每次 bash 调用独立**：本次写入的 `/tmp/audit_marker.txt` 在下一次调用中已不存在。

---

## 6. "从零复现本环境"最短步骤（按依赖顺序）

> 前提：Ubuntu 22.04.5 x86_64、`python3.10` 存在、**无 sudo**、可写 `/data/Documents/tools` 与 `~/.local/bin`。
> 约定：`T=/data/Documents/tools`，`PPA`/GitHub 可访问（或预先把安装包/二进制放在 `$T` 下离线安装）。每步给"验证命令"，**全部通过再进入下一步**。

### 步骤 0：目录与 PATH 前置

```bash
mkdir -p /data/Documents/tools ~/.local/bin
# 登录 shell 的 ~/.profile 已包含 ~/.local/bin；非登录 shell 需显式:
export PATH="$HOME/.local/bin:$PATH"
```
验证：`bash -lc 'echo $PATH | grep -q "$HOME/.local/bin" && echo PATH_OK'`

### 步骤 1：Python CAD 栈（agentcad 0.7.1 + build123d 0.10.0 + OCP 7.8.1.1）

```bash
python3.10 -m venv /data/Documents/tools/agentcad-venv
/data/Documents/tools/agentcad-venv/bin/pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple "agentcad[mcp]==0.7.1" "build123d==0.10.0"
ln -sf /data/Documents/tools/agentcad-venv/bin/agentcad ~/.local/bin/agentcad
ln -sf /data/Documents/tools/agentcad-venv/bin/python  ~/.local/bin/agentcad-python
# 每个机械项目独立 venv（不要污染系统 Python）：
python3.10 -m venv mechanical/square_v1/.venv
mechanical/square_v1/.venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
  "agentcad[mcp]==0.7.1" "build123d==0.10.0"
```
验证：`agentcad-python -c "import build123d, OCP; print(build123d.__version__, OCP.__version__)"` → `0.10.0 7.8.1.1`

### 步骤 2：FreeCAD 1.0.2（同时获得 ccx 2.22 / gmsh 4.13.1，不另装）

```bash
cd /data/Documents/tools/freecad
curl -L -C - -o FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage \
  https://github.com/FreeCAD/FreeCAD-Bundle/releases/download/1.0.2/FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage
sha256sum FreeCAD_*.AppImage   # 必须 = e00be00ad9fdb12b05c5002bfd1aa2ea8126f2c1d4e2fb603eb7423b72904f61
chmod +x FreeCAD_*.AppImage && ./FreeCAD_*.AppImage --appimage-extract   # 免 sudo/FUSE
# 写 wrapper（复刻 AppRun 环境：PREFIX/PYTHONHOME/LD_LIBRARY_PATH/SSL_CERT_FILE/FONTCONFIG，按 basename 分派 freecad/freecadcmd）
ln -sf /data/Documents/tools/freecad/freecadcmd-wrapper.sh ~/.local/bin/freecad
ln -sf /data/Documents/tools/freecad/freecadcmd-wrapper.sh ~/.local/bin/freecadcmd
ln -sf /data/Documents/tools/freecad/squashfs-root/usr/bin/ccx  ~/.local/bin/ccx
ln -sf /data/Documents/tools/freecad/squashfs-root/usr/bin/gmsh ~/.local/bin/gmsh
```
验证：
```bash
freecadcmd --version    # FreeCAD 1.0.2 Revision: 39319 (Git)
ccx -v                  # This is Version 2.22   （注意 rc=201！）
gmsh --version          # 4.13.1
```
> 复用策略：FreeCAD 升级时求解器随附升级，**不要**再装系统 calculix/gmsh（`AGENTS.md` 第 8 条）。

### 步骤 3：KiCad 9.0.9（官方 PPA jammy deb 解包）

```bash
cd /data/Documents/tools
# 用 apt-get download 从 ppa:kicad/kicad-9.0-releases 取 kicad 9.0.9 及依赖（libwxgtk3.2、libocct7.5、libngspice0、kicad-symbols/footprints/demos 等）
# 逐个 dpkg -x 到 /data/Documents/tools/kicad；deb 缓存到 kicad-debs/
# 写 bin/env.sh（见 §5.2）+ bin/kicad-cli、bin/kicad 两个 wrapper
ln -sf /data/Documents/tools/kicad/bin/kicad     ~/.local/bin/kicad
ln -sf /data/Documents/tools/kicad/bin/kicad-cli ~/.local/bin/kicad-cli
# 把 template/sym-lib-table 复制到 config/9.0/sym-lib-table（标准库解析）
```
验证：
```bash
kicad-cli version            # 9.0.9（stderr 必有 schema 警告，rc=0）
kicad-cli sch erc --output /tmp/erc.rpt --severity-all --exit-code-violations <sch>
kicad-cli pcb drc --output /tmp/drc.rpt --severity-all --exit-code-violations <pcb>
```

### 步骤 4：ngspice 36

```bash
cd /data/Documents/tools
apt-get download ngspice        # 36+ds-1ubuntu0.1
mkdir -p ngspice && dpkg -x ngspice_36+ds-1ubuntu0.1_amd64.deb ngspice
# 写 bin/ngspice wrapper：export SPICE_SCRIPTS=.../usr/share/ngspice/scripts
#                         export SPICE_LIB_DIR=.../usr/lib/x86_64-linux-gnu/ngspice
# 并把解包 spinit 里硬编码的 /usr/lib/x86_64-linux-gnu/ngspice 前缀改为解包路径
ln -sf /data/Documents/tools/ngspice/bin/ngspice ~/.local/bin/ngspice
```
验证：`ngspice -v` → `** ngspice-36 ...`；再跑 `.op` 分压 + `.ac` 低通测试（`$T/ngspice/tests/verify.py` 应全 `true`）。

### 步骤 5：pytest 9.2.0 + 科学栈（sim-venv + `pytest-sim`）

```bash
python3 -m venv /data/Documents/tools/sim-venv
/data/Documents/tools/sim-venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
  pytest pytest-json-report numpy pandas matplotlib pyyaml junit-xml
# 写 ~/.local/bin/pytest-sim：unset PYTHONPATH（避开本机 ROS 插件）+ exec sim-venv/bin/python -m pytest
```
验证：
```bash
pytest-sim --version      # pytest 9.2.0
cd /data/Documents/tools/sim-venv/tests && pytest-sim -q   # 3 passed
```

### 步骤 6：Wokwi CLI 0.29.1（只用于离线 lint）

```bash
curl -4 -L --retry 3 -o /data/Documents/tools/wokwi-cli/wokwi-cli \
  https://github.com/wokwi/wokwi-cli/releases/download/v0.29.1/wokwi-cli-linuxstatic-x64
chmod +x /data/Documents/tools/wokwi-cli/wokwi-cli
ln -sf /data/Documents/tools/wokwi-cli/wokwi-cli ~/.local/bin/wokwi-cli
```
验证：`wokwi-cli --version` → `0.29.1 (0aa185144b92)`；`wokwi-cli lint --offline firmware/wokwi/diagram.json`。
> **不要**运行云仿真（需 `WOKWI_CLI_TOKEN` 且会上传项目到 Wokwi 云端，违反"不传第三方"）。

### 步骤 7：Blender 4.5.3

```bash
cd /data/Documents/tools
curl -L -o blender-4.5.3-linux-x64.tar.xz https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz
tar xf blender-4.5.3-linux-x64.tar.xz
ln -sfn /data/Documents/tools/blender-4.5.3-linux-x64 /data/Documents/tools/blender
ln -sf /data/Documents/tools/blender/blender ~/.local/bin/blender
```
验证：`blender --version` → `Blender 4.5.3 LTS`

### 步骤 8：ESP-IDF v6.1 + QEMU 9.2.2（复用既有 EIM 安装，**勿重装**）

```bash
ls ~/.espressif/v6.1/esp-idf ~/.espressif/tools   # 已存在则跳过安装
source /home/pi/.espressif/tools/activate_idf_v6.1.sh ; true   # 注意返回码 1，用 ; 不用 &&
```
验证：
```bash
idf.py --version            # ESP-IDF v6.1
grep -E 'IDF_VERSION_(MAJOR|MINOR|PATCH)' ~/.espressif/v6.1/esp-idf/tools/cmake/version.cmake  # 6 1 0
Q=~/.espressif/tools/tools/qemu-xtensa/esp_develop_9.2.2_20260417/qemu/bin/qemu-system-xtensa
"$Q" --version              # QEMU emulator version 9.2.2 (esp_develop_9.2.2_20260417)
```
> 若目标机没有 ESP-IDF：用 Espressif EIM 安装 v6.1（会自带 xtensa 工具链 + QEMU 9.2.2）；不要用系统 apt。

### 步骤 9：Freerouting 2.5.0 + Xvfb（项目本地）

```bash
cd /data/Documents/projects/SmartCoaster
mkdir -p .tools && cd .tools
curl -L -o freerouting-2.5.0-linux-x64.zip \
  https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0-linux-x64.zip
unzip -q freerouting-2.5.0-linux-x64.zip       # 自带 Java 25.0.4.1（lib/runtime）
# Xvfb（系统无，无 sudo）：apt-get download xvfb xserver-common 后 dpkg -x 到 .tools/xvfb
```
验证：
```bash
# Freerouting 无 --version；用隔离 XDG + 一次真实布线或启动日志确认
HOME=$PWD/fr-home XDG_CONFIG_HOME=$PWD/fr-home/config \
XDG_STATE_HOME=$PWD/fr-home/state XDG_CACHE_HOME=$PWD/fr-home/cache \
  ./.tools/freerouting/freerouting-2.5.0-linux-x64/bin/freerouting   # 日志首行含 Freerouting v2.5.0
grep JAVA_VERSION .tools/freerouting/freerouting-2.5.0-linux-x64/lib/runtime/release   # 25.0.4.1
# Xvfb 冒烟：
.tools/xvfb/usr/bin/Xvfb :99 -screen 0 1280x1024x24 & sleep 2; DISPLAY=:99 xdpyinfo | head -3
```
> 只需复现 PCB 布线时才需要；`.tools/` 已在 `.gitignore` 中。

### 步骤 10（可选）：Node/npm + Wokwi VS Code 扩展

```bash
node --version   # v24.15.0（既有 nvm）
npm --version    # 11.12.1
code --list-extensions --show-versions | grep -i wokwi   # wokwi.wokwi-vscode@4.1.0
```
> 纯 CLI 工作流**不需要** Node；仅 VS Code 扩展用。

### 步骤 11：整体复验

```bash
bash -lc '/data/Documents/tools/verify_sim_tools.sh'        # 必须登录 shell（PATH）
# 或逐项：见 §1 的实测命令
# 项目自检（AGENTS.md 第 5 条）：
cd /data/Documents/projects/SmartCoaster
source /home/pi/.espressif/tools/activate_idf_v6.1.sh ; true
bash -lc 'kicad-cli pcb drc --output /tmp/drc.rpt --severity-all --exit-code-violations electronics/kicad/build/smartcoaster_2l.kicad_pcb'
mechanical/square_v1/.venv/bin/python mechanical/square_v1/cad/verify_v01.py
```
> 期望：`verify_sim_tools.sh` 全部通过（pytest 3 passed / ngspice 4 项 true / KiCad 0 violations / wokwi 1 info）；PCB DRC `0 violations / 0 unconnected`。

---

## 7. 已知坑清单（按影响排序）

| # | 坑 | 现象 | 规避 |
|---|---|---|---|
| 1 | **`/tmp` 每次 bash 调用独立 tmpfs** | 上一调用写的 `/tmp/x` 下一次消失；`/tmp/.X11-unix` 不存在 | 需要跨步骤共享的文件写到**工作区**（如 `.tools/`）；Xvfb + Freerouting 必须在**同一次**调用内启动（`route_2l.sh` 已如此） |
| 2 | **`~/.config`、`~/.local/state`、`~/.cache` 只读** | matplotlib 警告 `~/.config/matplotlib is not a writable directory`；Freerouting `Could not create directory .../freerouting/logs` | 显式设 `XDG_CONFIG_HOME` / `XDG_STATE_HOME` / `XDG_CACHE_HOME` / `MPLCONFIGDIR` 到工作区 `.tools/*` |
| 3 | **`~/.local/bin` 只在登录 shell PATH** | 非登录 `bash -c` 里 `kicad-cli/ngspice/pytest-sim/ccx` 均 `command not found`；`verify_sim_tools.sh` 静默失败 | 用 `bash -lc`，或脚本内显式 `export PATH="$HOME/.local/bin:$PATH"`，或用绝对路径 |
| 4 | **ESP-IDF `activate_idf_v6.1.sh` 返回码 1** | `source ... && idf.py build` 被 `&&` 短路，看起来什么都没做 | 根因是脚本末尾 `eim select v6.1` 失败（`Failed to setup logging`）；激活本身成功。用 `source ... ; ...`（分号）或 `source ... ; true` |
| 5 | **`kicad-cli` 每次 stderr 打印 schema 警告** | `Error: schema file '/usr/share/kicad/schemas/api.v1.schema.json' not found`，rc=0 | 看 rc / 报告文件，不要以 stderr 非空判失败；消除需系统级安装（有 sudo） |
| 6 | **`ccx -v` 退出码 201** | 版本正常打印但 rc≠0；`ccx -v && next` 短路 | 用 `;` 或忽略 rc；`ccx -i job` 正常求解 rc=0 |
| 7 | **`kicad --version` 不支持** | `Unknown long option 'version'`（rc=0） | 用 `kicad-cli version` |
| 8 | **`agentcad --version` 不支持** | 输出错误 JSON（`unknown_option`） | 用 `pip show agentcad` 或 `agentcad-python -c "import ..."` |
| 9 | **FreeCAD `Shape.BoundBox` 环面高估** | 解析 bbox 报 119.063 mm（实际 110） | 尺寸校验用三角化顶点统计；见 `环境安装记录` §6.3 |
| 10 | **`freecadcmd script.py` 的 `__name__ != "__main__"`** | `if __name__ == "__main__":` 整段静默跳过；`sys.exit()` 丢缓冲输出 | 直接写顶层代码 + `sys.stdout.flush()`；不要 `sys.exit()` |
| 11 | **`QT_QPA_PLATFORM=offscreen` 无 GL** | `No valid GL context found!` | 需要 GL 的命令用 Xvfb（`DISPLAY=:99`）或真实桌面 `DISPLAY=:0` |
| 12 | **系统无 Xvfb** | `command -v Xvfb` 空 | 用项目 `.tools/xvfb`；或 `xvfb-run`（同目录） |
| 13 | **Freerouting 遥测默认开** | `allow_telemetry:true`，日志 `/v1/analytics/identify` 超时 | 隔离配置里预置 `allow_telemetry:false` + `disable_analytics:true`；GUI 需 AWT display → 配 Xvfb |
| 14 | **Freerouting `-mt` 多线程优化有已知违规** | 官方警告 "Multi-threaded route optimization is broken"，会生成 clearance violations | 用 `-mt 1`（`route_2l.sh` 已用） |
| 15 | **`pytest` 入口版本错位** | PATH 上 `pytest` 是 9.1.0，requirements 要 9.2.0 | 固定用 `pytest-sim`（sim-venv 9.2.0） |
| 16 | **本机有 ROS 2 Humble，`PYTHONPATH` 污染 pytest** | venv 里 pytest 自动加载 ROS `launch_testing`，报 `No module named 'lark'` | `pytest-sim` 默认 `unset PYTHONPATH`；确需保留时设 `PYTEST_SIM_KEEP_PYTHONPATH=1`（自负风险） |
| 17 | **KiCad 未装 3D 模型** | `pcb render` / 3D Viewer 缺模型 | ERC/DRC/Gerber 不受影响；需要再解包 `kicad-packages3d`（数 GB） |
| 18 | **依赖树绑定路径** | ccx/gmsh 依赖 FreeCAD 自带库（RPATH `$ORIGIN/../lib`）；KiCad/ngspice 依赖解包树的 `LD_LIBRARY_PATH`/`SPICE_*` | 不要移动/删除 `/data/Documents/tools/{freecad,kicad,ngspice}`；移动后用 wrapper 重建环境 |

---

## 8. 审计边界与未覆盖项

- 本次**只读**：未安装/升级工具、未改 `requirements.yaml`、未改源码；除本报告外未新增/修改仓库跟踪文件。
- 未复核：GUI 长时间交互稳定性、KiCad 3D 模型、Wokwi 云仿真（按约定禁用）、Freerouting 对外网络是否最终可达（只看到超时失败）。
- 审计时工作区存在他人未提交改动（`config/mechanical_params.yaml`、`docs/05_*`、`docs/06_*`、`firmware/REPORT.md`），**与本次审计无关**，本次未触碰。
- 本报告不替项目负责人做合规决策；§4.1 的 GitHub remote 需人工确认授权状态。

---

## 9. 证据位置索引

| 证据 | 路径 |
|---|---|
| 版本命令原始输出（本次） | 见 §1 "实测命令"列；可直接复跑 |
| FEA 求解器复用记录 | `/data/Documents/tools/FEA_INSTALL_NOTES.md` |
| 仿真/EDA 安装记录 | `/data/Documents/tools/SIM_INSTALL_NOTES.md` |
| 一键复验脚本 + 历史输出 | `/data/Documents/tools/verify_sim_tools.sh`、`SIM_VERIFY.log` |
| FreeCAD 安装/STEP 验证 | `/data/Documents/tools/freecad/INSTALL_NOTES.md` |
| 机械环境安装记录 | `docs/环境安装记录-agentcad-freecad.md` |
| 布线脚本（Freerouting/Xvfb 用法） | `electronics/kicad/scripts/route_2l.sh` |
| Freerouting 运行日志 | `electronics/kicad/build/freerouting_2l.log`、`logs/freerouting.log` |
| git push 痕迹 | `.git/logs/refs/remotes/origin/master`、`.git/config` |
| Freerouting 遥测配置 | `.tools/fr-home/config/freerouting/freerouting.json` |
| ESP-IDF activate 根因 | `/home/pi/.espressif/tools/activate_idf_v6.1.sh`（末尾 `eim select`） |
| 交付验收环境说明 | `docs/HANDOFF.md` §1、`docs/VERIFY_REPORT.md` §环境 |
