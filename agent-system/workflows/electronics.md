# Workflow: Electronics + PCB / Fab (E0–E4 + PCB-FAB)

> 门禁：`gates/electronics.yaml`（G-ELEC）· 唯一来源：`<eda>/scripts/design.py`
> 一条命令：`cd electronics/kicad/scripts && ./build.sh`

## 1. 阶段表

| 阶段 | 输入 | 动作 | 输出 | 证据 / 门禁 |
|---|---|---|---|---|
| E0 架构 | PRD、机械占位、手册 | MCU/传感器/ADC/显示/电源/接口框图、电源树 | `pinmap.md`、`config/electronics.yaml` | 引脚/电压/电流定义完整 |
| E1 选型 | E0 | 型号/手册/电气参数/封装/原因/风险/替代 | `design.py`、`BOM.csv` | BOM 行齐全；缺 MPN 登记 |
| E2 原理图 | E1 + 机械接口 | 生成 `.kicad_sch`/网表；逐脚核对 | 原理图、`NETLIST.md`、PDF/PNG | **ERC 0 error/0 warning** |
| E3 PCB | E2 网表 + 板框 | 布局/布线（自动 + 手工修正） | `.kicad_pcb`、布线预览 | **DRC 0 violation/0 unconnected** |
| E4 验证 | E3 + 模型 | ERC/DRC/网表/DFM/SPICE；双 EDA 对账 | 报告 + JSON | G-ELEC 全绿/部分 |
| PCB-FAB | 已验证 PCB | Gerber/钻孔/坐标/装配图/zip + DFM | `build/gerbers/`、`DFM.md` | **DFM 5/5；时间戳顺序** |

## 2. 生成链（顺序不能乱）

```text
design.py（唯一来源）
  → gen_sch.py  → .kicad_sch / .kicad_pro / 符号库
  → ERC         → build/ERC.rpt
  → gen_pcb.py  → 未布线 .kicad_pcb（placement + footprint）
  → DSN 导出（断言引号平衡）
  → Freerouting（无头 Xvfb，-mt 1，关闭遥测）
  → SES 导入 + 线宽归一 + 悬空清理
  → DRC（--severity-all）→ build/DRC*.rpt
  → BOM / Gerber / 钻孔 / 坐标 / zip
  → DFM 自查 → build/DFM.md
  → 渲染/装配图（同一版板）
```

## 3. 复用清单

- [ ] 板框/安装孔/接插件/最高元件与机械一致。
- [ ] 电源树每条轨 + 每类连续负载列全（功耗预算不能漏桥路激励）。
- [ ] 模拟走线/地回流/去耦/天线净空单独列风险。
- [ ] 规则策略显式化：silk 类豁免写进项目配置与 DFM。
- [ ] 第二实现（如 EasyEDA）只做数据契约层对账，不降级主工程。
- [ ] 所有文本值不带未转义引号（`OLED 0.91"` 事故）。

## 4. 已知失败模式

| 现象 | 根因 | 预防 |
|---|---|---|
| DRC 里 pad 全 `[T]` | grep 子串假象 | 结构化解析复核 |
| 空 SES / 0 unrouted | DSN 引号/坐标错位 | 导出断言 + track/via 数 + DRC 三重 |
| 器件值改了装配图没变 | 没重跑生成链 | 时间戳顺序 + 变更传播清单 |
| 7 天续航实际 4 天 | 功耗漏连续负载 | 每条轨逐项列全 + 场景表 |
| I2C 偶发失败 | 上拉 vs 总容 vs 速率 | 公式 + 仿真 + 示波器三步 |
| BLE 距离短 | 金属顶板压天线 | 天线净空 + 非金属窗 + 实测 |
| 两套 EDA 结果打架 | 规则口径不同 | 分别记录、各自收敛 |

## 5. 边界

- ERC/DRC/DFM/网表是"设计正确性 + 可制造性"证据，**不是**电气性能实测。
- SPICE 是行为级（HX711 无芯片级模型）；噪声/温漂/EMC 必须手板测。
- 没有报告文件时禁止说"0/0"。
