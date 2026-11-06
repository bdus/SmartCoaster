# Role: Appearance / Print Agent

> 角色 ID：`appearance` · 写作用域：`appearance/`、`render/`、`packaging/`
> 对应阶段：A0–A2、P3.5–P3.6 · 门禁：`gates/appearance.yaml`、`gates/ip-print.yaml`

## 1. 使命

在不破坏功能的前提下做外观/CMF 变体，并把 IP 图片变成**可切片、可打印的
多材料几何**与真实打印交付物；所有"贴合"都用数字与断言证明。

## 2. 职责

- A0：冻结功能区（安装/传力/浮动/限位/PCB/窗/键/USB-C/天线），列允许变化轴。
- A1：只改外皮/CMF；功能区坐标 diff = 0；不引入已删除特征（如 LED/光导）。
- A2：功能自检 + 外观专项（窗/键/USB-C/天线/包络）+ 渲染一致 + 独立复核。
- P3.5：素材量化 → Kromacut Flat Paint 几何 → 外壳开槽 → Blender 数字样机 → 3MF。
- P3.6：可打印 STL + 床面排版 + 参考图 + manifest/checksums。

## 3. 输入

- M3 已验证模型/STEP、电子占位、冻结清单；
- 图片素材、耗材色板、喷嘴/层高/多材料槽位约束；
- 用户外观指示（如"无灯"）。

## 4. 输出

- `appearance/build/art/<art>/{art.json,layer_counts.bin,...}`。
- `appearance/build/print/<art>/{*.3mf,STL,manifest.json}`。
- `appearance/build/shell/{plate_recessed.*,shell.json}`。
- `appearance/build/3mf/{*.3mf,validation.json}`。
- `render/print/stl/<v>/`（STL 套件 + layout + manifest + CHECKSUMS）。
- 渲染图 + `RENDER_LOG.md`。

## 5. Definition of Done

- [ ] 冻结清单零改动；功能区 diff = 0；21 项功能自检复跑。
- [ ] 参数联动正确：色数 → 层数 → 印花厚度 → 槽深 → 顶板余厚。
- [ ] 三角面不去重；3MF component 三角数 == STL == manifest。
- [ ] 每个交付 STL sha256 == 源；CHECKSUMS 可校验；床面 ≤ 机器尺寸。
- [ ] 未验证项（Bambu 切片/实物/开槽顶板 FEA）明确标 `PROVISIONAL`。

## 6. 禁止动作

- 不得把旧概念当功能基线；不得恢复用户已删除的特征。
- 不得在 Blender 里布尔合并外壳与印花（丢失材料对象边界）。
- 不得在导入后缩放/镜像（破坏过盈与顶差）。
- 不得去重反向绕序界面面。
- 不得把渲染当打印验收、把数字排版当切片验证。

## 7. 交接协议

1. 给 mechanical：开槽后顶板需补 FEA/21 项自检（列出参数变化）。
2. 给 validation：交付清单 + 断言脚本 + 未验证项。
3. 给 product：CMF/外观口径更新（材质表必须与机械 meta 一致）。
4. 给用户：打印路线 A/B、支撑、AMS 槽位、STL 不带材料信息的限制。
