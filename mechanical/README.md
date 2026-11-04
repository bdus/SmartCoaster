# mechanical/

每个版本一个**自包含的 agentcad 项目**（自带 `.venv`、`cad/`、`build/`、自检脚本），互不共用几何。

| 目录 | 内容 | 状态 |
|---|---|---|
| `lumen/` | 圆形 LUMEN（Ø110×17，13 零件） | 几何验证 21/21 |
| `square_v1/` | 方形 V1（100×100×18，12 零件，无光导） | 几何验证 21/21 |
| `hy928d/` | HY928D 5 kg 传感器 v2（按新图纸/照片重建） | **待人工检视** |
| `legacy/` | 旧脚本可运行副本（去 U+00A0） | 参考 |
| `original_cad/` | M1.2 原始脚本（只读，不覆盖） | 参考 |

## HY928D v2

```bash
cd hy928d
/data/Documents/tools/agentcad-venv/bin/python src/hy928d_v2.py
# 输出 build/hy928d_v2.step|stl, params.json；渲染见 renders/
```

参数与"图纸原文 / 推断"对照见 `hy928d/notes.md`；检视通过后再进入 FEA。
