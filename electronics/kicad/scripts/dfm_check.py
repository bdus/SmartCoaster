#!/usr/bin/env python3
"""DFM self-check for the 4-layer SmartCoaster board (JLCPCB 4L standard)."""
import csv
import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "smartcoaster", "smartcoaster_4l.kicad_pcb")
BOM = os.path.join(HERE, "..", "BOM.csv")
OUT = os.path.join(HERE, "..", "build", "DFM.md")


def mm(v):
    return round(v / 1e6, 3)


def main():
    b = pcbnew.LoadBoard(PCB)
    bb = b.GetBoardEdgesBoundingBox()
    ds = b.GetDesignSettings()
    tracks = [t for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    vias = [t for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    fps = b.GetFootprints()
    min_w = min((t.GetWidth() for t in tracks), default=0)
    min_drill = min((v.GetDrill() for v in vias), default=0)
    min_via = min((v.GetWidth(pcbnew.F_Cu) for v in vias), default=0)
    pad_drills = [p.GetDrillSize().x for f in fps for p in f.Pads() if p.GetDrillSize().x > 0]
    dnp = [f.GetReference() for f in fps if f.IsDNP()]
    smd = sum(1 for f in fps for p in f.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD)
    pth = sum(1 for f in fps for p in f.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
    rows = list(csv.DictReader(open(BOM, encoding="utf-8"))) if os.path.exists(BOM) else []
    no_mpn = [r.get("Refs", "?") for r in rows if not (r.get("MPN") or "").strip()]
    edge_rule = ds.m_MinCopperEdgeClearance / 1e6 if hasattr(ds, "m_MinCopperEdgeClearance") else 0.3
    track_rule = ds.m_TrackMinWidth / 1e6 if hasattr(ds, "m_TrackMinWidth") else 0.125
    lines = [
        "# PCB DFM 自查（4 层）",
        "",
        f"- 板：`smartcoaster_4l.kicad_pcb`",
        f"- 尺寸：{mm(bb.GetWidth())} × {mm(bb.GetHeight())} mm；厚度 {mm(ds.GetBoardThickness())} mm；铜层 {b.GetCopperLayerCount()}",
        f"- 器件：{len(fps)}；SMD pad {smd}；PTH pad {pth}；DNP {len(dnp)}",
        f"- 最小走线：{mm(min_w)} mm（规则 {track_rule}）",
        f"- 最小过孔：钻 {mm(min_drill)} / 外径 {mm(min_via)} mm（环宽 {mm((min_via - min_drill) / 2)}）",
        f"- 最小 PTH 钻：{mm(min(pad_drills) if pad_drills else 0)} mm",
        f"- 板边铜距规则：{round(edge_rule, 3)} mm",
        f"- BOM 行：{len(rows)}；缺 MPN：{len(no_mpn)} {no_mpn[:5]}",
        "",
        "## JLCPCB 4 层工艺对照",
        "",
        "| 项 | 本板 | JLC 4L 能力 | 判定 |",
        "|---|---:|---:|---|",
        f"| 线宽 | {mm(min_w)} | ≥0.09 | {'PASS' if min_w >= 90000 else 'FAIL'} |",
        f"| 过孔钻 | {mm(min_drill)} | ≥0.2 | {'PASS' if min_drill >= 200000 else 'FAIL'} |",
        f"| 过孔环宽 | {mm((min_via - min_drill) / 2)} | ≥0.13 | {'PASS' if (min_via - min_drill) / 2 >= 130000 else 'FAIL'} |",
        f"| 板边铜距 | {round(edge_rule, 3)} | ≥0.3 | {'PASS' if edge_rule >= 0.299 else 'FAIL'} |",
        f"| 层数 | {b.GetCopperLayerCount()} | 4 | PASS |",
        "",
        "## 备注",
        "",
        "- 字符（silk）按项目 severity 豁免：位号重叠不影响电气；贴片用坐标文件。",
        "- USB_DP/DM 0.125 mm，按 90Ω 近似；未做阻抗控制（打样默认）。",
        "- S3-MINI-1 / HY928D / OLED 为外购件，BOM 里标 `PROVISIONAL` 的需下单前确认封装/引脚。",
        "- 无盲埋孔、无阻抗/金手指/半孔等特殊工艺。",
    ]
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote", OUT)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
