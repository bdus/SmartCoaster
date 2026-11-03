# 任务：搭建智能杯垫本地 AI 辅助机械设计环境

你是我的本地 AI 硬件研发环境工程师。请在当前 Ubuntu Linux 环境中，逐步搭建智能杯垫项目的机械设计工具链。

## 一、项目背景

项目名称：smart-coaster

目标：使用 AI Agent + MCP + 参数化 CAD 的方式，以文本交互完成智能杯垫的机械设计。优先使用本地、开源、免费工具，不依赖收费 IDE 或云端 CAD 服务。

我的工作方式：

- 我通过自然语言向 Agent 描述设计要求。
- Agent 使用 CAD 工具生成参数化模型。
- 我审查模型、尺寸、结构和设计假设。
- 通过迭代修改模型。
- 最终导出 STEP、STL 等文件，进入 3D 打印和装配阶段。

## 二、工具选择

第一阶段必须搭建：

1. AgentCAD：作为 AI Agent 驱动的参数化机械设计入口。
2. build123d：作为 Python 参数化 CAD 几何建模内核。
3. Python 3.10–3.12：使用独立虚拟环境。
4. MCP：为后续其他本地 Agent 提供 CAD 工具调用能力。
5. Git：版本管理。

第二阶段再考虑：

- FreeCAD：装配、STEP 检查、工程图。
- KiCad：电路板设计。
- ngspice：电路仿真。
- ESP-IDF：固件开发。

不要在第一阶段安装所有工具。

## 三、执行规则

1. 首先检查操作系统版本、Python 版本、磁盘空间、Git 状态。
2. 如果 Python 版本是 3.10、3.11 或 3.12，优先使用现有 Python。
3. 如果是 Python 3.13，不要强行安装不兼容的依赖，应单独配置 Python 3.12。
4. 使用项目独立虚拟环境 `.venv`，禁止污染系统 Python。
5. 安装 AgentCAD 时优先使用官方项目及官方文档。
6. 如果项目中已经存在 AGENTS.md，必须先备份，禁止覆盖。
7. 配置 AgentCAD 项目目录和 build 输出目录。
8. 配置 MCP 时使用项目 `.venv` 内的 Python 解释器，避免依赖系统 PATH。
9. 每完成一个阶段，检查命令是否成功，再继续下一步。
10. 不要擅自安装收费软件，不要上传项目文件到第三方服务。

## 四、分阶段执行

### Phase E0：环境检查

输出：

- Ubuntu 版本
- Python 版本
- Git 版本
- 是否有现成的 CAD 软件
- 项目目录是否存在
- 是否存在 AGENTS.md

### Phase E1：基础依赖

安装必要的 Git、Git LFS、build-essential、python3-venv01_AI_Hardware_Engineering_Pipeline.md、python3-pip 等依赖。

### Phase E2：AgentCAD

在 `~/projects/smart-coaster` 下创建项目。

创建 Python 虚拟环境，安装 AgentCAD 及其 MCP 依赖。

检查：

- agentcad 命令是否正常
- build123d 是否可导入
- 能否生成简单立方体
- 能否导出 STEP 和 STL

### Phase E3：MCP

提供 MCP 配置示例，确保其他 Agent 可以调用 AgentCAD。

不要假设所有 Agent 的 MCP 配置格式相同，应分别说明通用配置和需要根据客户端调整的部分。

### Phase E4：最小验证

创建一个 100×100mm、厚度参数化的简单方形圆角板。

验证：

- 参数修改有效
- 3D 模型可以生成
- STEP 文件能够导出
- STL 文件能够导出
- 模型能够预览

## 五、交付要求

完成后输出：

1. 环境安装记录。
2. 工具版本。
3. 项目目录结构。
4. MCP 配置。
5. 最小验证模型。
6. STEP/STL 导出结果。
7. 尚未解决的问题。

**重要：采用逐步执行模式。先完成 E0，将检查结果和建议方案发给我，等待确认后再执行安装。不要一次性执行全部步骤。**

