# appearance/ 印花一体打印 — 独立验收（Lead 只读复核）

> 生成：2026-11-07T00:41:29 · 共 130 项，**130 PASS / 0 FAIL**
> 由 `python3 appearance/tools/acceptance_check.py` 生成；只读已交付产物，不重跑队友脚本。

| 分组 | PASS | FAIL |
|---|---|---|
| tools | 6 | 0 |
| art | 10 | 0 |
| shell | 14 | 0 |
| print | 21 | 0 |
| 3mf | 20 | 0 |
| render | 26 | 0 |
| print_delivery | 23 | 0 |
| docs | 10 | 0 |

## 未由本脚本验证 / 边界

- Bambu Studio 实际导入、耗材映射、逐层切片：本机无 Bambu Studio，未测。
- 实物打印（颜色、层厚、翘曲、结合强度、耐热、清洁）：未打样。
- 开槽顶板刚度/FEA、21 项功能自检：未重跑（`PROVISIONAL`）。
- Kromacut GUI 人工操作路径：只在 Xvfb 下验证可启动；本流水线走 headless 引擎。
- 打印交付（render/print/stl）：交付 STL 是**按打印姿态烘焙**的刚体变换副本（三角数/体积与源一致、
  bbox=旋转后源 bbox、min z=0、CHECKSUMS 通过）；床面适配与落槽已断言，但未实际切片/打印。
  印花正面贴床（第一层）、按钮躺平为 PROVISIONAL 工艺选择。
- 圆形 LUMEN 源 STEP 的封闭空腔缺陷：已记录并给出 clean 变体，未改源文件。

