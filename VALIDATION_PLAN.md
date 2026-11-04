# 验证计划

## 已完成（几何级 / 数字级，2026-11-04）
- 方形 V1（square_v1）：**21/21**（12 实体、包围盒、间隙、0.5 mm 下压行程无遮挡、37 组干涉、STEP 回读）
- LUMEN：21/21（概念线，不再推进）
- FreeCAD 独立复核：12 solids，包围盒/体积一致（`mechanical/square_v1/build/freecad_verify.log`）
- 电路：ERC **0 error / 0 warning**；2 层 PCB **0 DRC / 0 unconnected**；Gerber/钻孔/坐标 + JLC 2 层 DFM 全 PASS
- 固件：host 11/11（41 checks）+ mock 9/9（198 checks）+ C↔Python 差分 16/16 + pytest 16；`idf.py build` 通过
- S1 机械 FEA（HY928D 本体，通槽）：5 kg 中心 0.3435 mm、支反力 100%、非奇异热点 468 MPa；通槽 vs 0.7 mm 浅腔对比
- S2 电路仿真（部分）：桥路 + HX711 行为前端 DC/AC（3.956 mV → 0.506 V、RC 1.65 kHz、50 Hz −14.2 dB）

## 待做
1. **HY928D 人工检视 + 供应商确认**（U 槽/拱/舌片/桥路/灵敏度/引线）——M2 关闭前置条件。
2. **机械 FEA 对象 B/C**：顶板+传力柱（中心/偏载）、整机装配（限位先接触、旁路力、安全系数）；补 `config/validation_mechanical.yaml` 阈值来源。
3. **S2 补全**：电源、MCU 接口、`.tran`/`.noise`/蒙特卡洛、参数扫描。
4. **S3 补全**：QEMU 在删 halo 后重跑并归档原始日志；BLE 协议/断线重连测试；Wokwi 保持搁置（不传第三方）。
5. **S4 MCP 编排**：一条命令跑完 S1–S4 并生成统一报告（当前只有各域 CLI 脚本）。
6. **S5 实物**（用户侧）：手板装配 + 11 项 bring-up 测试（`docs/05`）+ 砝码标定 + 7 天记录。

> 几何无干涉 ≠ 强度/称重性能通过；仿真通过 ≠ 实物通过。
