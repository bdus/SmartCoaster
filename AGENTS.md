# AGENTS.md — 项目级协作约定

1. 先读 `docs/01_AI_Hardware_Engineering_Pipeline.md`、`docs/02_Smart_Coaster_PRD.md` 和 `ref/*.md`。
2. 原始资料（`ref/` 下未转录的原件、`mechanical/original_cad/`）**只读**，不覆盖。
3. 机械版本各自是独立 agentcad 项目：`mechanical/lumen/`、`mechanical/square_v1/`，不要跨项目改几何。
4. 不要把推测写成事实：未确认的尺寸在代码/文档里标 `PROVISIONAL`，并写进 `config/mechanical_params.yaml` 的 status。
5. 改完必须复跑自检：`cad/verify_v01.py`（几何/行程/干涉/STEP 回读）；仿真结果必须落 JSON/CSV。
6. 新工具装到 `/data/Documents/tools/<tool>`，版本写进 `requirements.yaml`；不装收费软件、不传项目文件到第三方。
7. 仿真通过 ≠ 实物通过；最终灵敏度、温漂、回差必须实物标定。
8. **FEA 求解器复用 FreeCAD 1.0.2 自带的 ccx 2.22 / gmsh 4.13.1**（`~/.local/bin` 软链），不重复安装。
