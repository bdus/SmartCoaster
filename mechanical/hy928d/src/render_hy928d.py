#!/usr/bin/env python3
"""Render the HY928D v2 STL (top + iso) with VTK offscreen."""
import math, sys
from pathlib import Path
import vtk

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "build" / "hy928d_v2.stl"
GAUGES = ROOT / "build" / "hy928d_v2_gauges.stl"
OUT = ROOT / "renders"
OUT.mkdir(exist_ok=True)


def load(path, color, metal=0.35, rough=0.35, opacity=1.0):
    r = vtk.vtkSTLReader(); r.SetFileName(str(path))
    n = vtk.vtkPolyDataNormals(); n.SetInputConnection(r.GetOutputPort())
    n.SetFeatureAngle(30); n.SetConsistency(True); n.SetSplitting(True)
    m = vtk.vtkPolyDataMapper(); m.SetInputConnection(n.GetOutputPort())
    a = vtk.vtkActor(); a.SetMapper(m)
    p = a.GetProperty(); p.SetInterpolationToPBR()
    p.SetColor(*color); p.SetMetallic(metal); p.SetRoughness(rough)
    p.SetOpacity(opacity)
    return a


def scene():
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.985, 0.982, 0.975)
    ren.SetBackground2(0.90, 0.895, 0.885)
    ren.GradientBackgroundOn()
    ren.AddActor(load(STL, (0.72, 0.74, 0.76), 0.35, 0.32))
    if GAUGES.exists():
        ren.AddActor(load(GAUGES, (0.15, 0.42, 0.72), 0.10, 0.45))
    for pos, intensity, col in (
        ((-40, -60, 90), 2.1, (1.0, 0.98, 0.95)),
        ((70, -40, 40), 0.8, (0.95, 0.97, 1.0)),
        ((0, 70, 50), 1.0, (0.90, 0.94, 1.0)),
    ):
        L = vtk.vtkLight(); L.SetPosition(*pos); L.SetFocalPoint(0, 0, 0.5)
        L.SetIntensity(intensity); L.SetDiffuseColor(*col)
        L.SetLightTypeToSceneLight(); ren.AddLight(L)
    ren.SetAmbient(0.18, 0.18, 0.18)
    return ren


def render(name, top=False):
    ren = scene()
    cam = ren.GetActiveCamera()
    if top:
        cam.ParallelProjectionOn()
        cam.SetPosition(0, 0, 100); cam.SetFocalPoint(0, 0, 0.5)
        cam.SetViewUp(0, 1, 0); cam.SetParallelScale(19.5)
    else:
        cam.SetPosition(58, -72, 58); cam.SetFocalPoint(0, 0, 0.5)
        cam.SetViewUp(0, 0, 1); cam.SetViewAngle(24)
    ren.ResetCameraClippingRange()
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren); rw.SetSize(1600, 1600 if top else 1200)
    rw.SetMultiSamples(8); rw.Render()
    w = vtk.vtkWindowToImageFilter(); w.SetInput(rw); w.Update()
    p = OUT / f"{name}.png"
    wr = vtk.vtkPNGWriter(); wr.SetFileName(str(p))
    wr.SetInputConnection(w.GetOutputPort()); wr.Write()
    print(p)


if __name__ == "__main__":
    render("top", top=True)
    render("iso", top=False)
