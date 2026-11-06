# 印花素材处理报告（appearance/build/art）

> 由 `appearance/tools/make_art.py` 生成；一行命令复跑：`python3 appearance/tools/make_art.py`。

## dog

- 输出：`art_rgba.png`（576×576，圆外透明）、`layer_counts.bin`、`art.json`、`palette.png`、`art_quant_preview.png`
- 印花直径：86.37 mm（画幅 86.4 mm，px 0.15 mm）
- 物理层数：6 × 0.2 mm = **1.2 mm** 厚（face-up Flat Paint）
- 透明像素：71368；不透明：260408；孤立像素（8 邻域无同色）= **0**
- 调色板（bottom-up，0=foundation）：`#FBF4E8`, `#CBE0F5`, `#9FB2DA`, `#F9CD72`, `#F09FAF`, `#6C574C`
- 各色像素数：`#FBF4E8`=149779，`#CBE0F5`=67546，`#9FB2DA`=7089，`#F9CD72`=17443，`#F09FAF`=1093，`#6C574C`=17458
- sha256：layer_counts.bin `10da7da67993a6fc3e78ac71d01fde0aefae9cb7a7ce2bf8ec904f498dbd41b3`
- sha256：art_rgba.png `a3157f0dde492463b64336af348b1b0b7dfb824bae61562fa01adea3db328de1`
- 来源：surface.png sha256 `93e6f87e789c755d09d7d4442bbfb0195fc2a6bc2a99a0542a7ac56f6d3912ed`，裁切框 [33.5, 33.5, 864.5, 845.5]（源图椭圆 rx/ry=[415.5, 406.0]，重采样回正圆）

## elf

- 输出：`art_rgba.png`（576×576，圆外透明）、`layer_counts.bin`、`art.json`、`palette.png`、`art_quant_preview.png`
- 印花直径：86.37 mm（画幅 86.4 mm，px 0.15 mm）
- 物理层数：7 × 0.2 mm = **1.4 mm** 厚（face-up Flat Paint）
- 透明像素：71368；不透明：260408；孤立像素（8 邻域无同色）= **0**
- 调色板（bottom-up，0=foundation）：`#EDE1F0`, `#D9CFE6`, `#C3AEDC`, `#F7D2C0`, `#E8A9B8`, `#C9A45B`, `#5B4A72`
- 各色像素数：`#EDE1F0`=185163，`#D9CFE6`=18479，`#C3AEDC`=21967，`#F7D2C0`=12756，`#E8A9B8`=5759，`#C9A45B`=1918，`#5B4A72`=14366
- sha256：layer_counts.bin `cc8627dc3a8846bc045c4640780761a7e738fde7ca18bf0acbf28facf9cd5919`
- sha256：art_rgba.png `a6905575f120b6efc535974cd9d6f51e01fde014bceac6026ab8fe2fb70eb0b1`
- 来源：surface.png sha256 `93e6f87e789c755d09d7d4442bbfb0195fc2a6bc2a99a0542a7ac56f6d3912ed`，裁切框 [909.5, 32.5, 1740.5, 845.5]（源图椭圆 rx/ry=[415.5, 406.5]，重采样回正圆）

## 方法（可复现）

1. 源图 `appearance/src/surface.png` 两张圆形印花左右拼版（白底，源图形状略扁：rx≈415.5 / ry≈406）。
2. 按各自包围盒 + 椭圆→正方形重采样（LANCZOS）到 576×576，恢复真圆。
3. 圆外颜色向圆内「外扩」6 px 后再量化，避免 LANCZOS 下采样把白边带进印花边缘。
4. CIELAB 最近邻量化到固定耗材色板（不是 k-means 平均色，保证可复现），再做 3 轮 3×3 多数去噪 + 孤立像素清除。
5. alpha 二值化（圆外全透明），输出 `layer_counts.bin`：`0=透明`，`1..N=该像素的物理层数`（即 palette index+1）。
6. Kromacut face-up Flat Paint 语义：第 k 层像素列共 k 层，顶面看到 palette[k-1]；更矮的列由 foundation（palette[0]）垫平 → 顶面平整、多色同层并排。

## 已知限制 / 未验证

- 印花细节受 FDM 限制：0.15 mm/像素的几何边长 < 0.4 mm 喷嘴，细于约 0.4–0.5 mm 的线条无法可靠打印；渲染看起来比实物更细腻。
- 6/7 色需要多材料（AMS/CFS）：4 槽 AMS 需换料或第二台 AMS。
- 精灵（7 色）原画反差很低，量化后比狗（6 色）损失更多明暗层次；如需更好保真可增到 8–9 色（厚度同步增加）。
- 未做实物打印验证（颜色/层厚/结合强度需打样）。
