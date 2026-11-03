#!/usr/bin/env python3
"""
Half-section render of the LUMEN assembly (y = 0 plane, front half removed).

    python3 tools/render_section.py

vtkClipClosedSurface caps every cut, so wall thickness, the force column,
the load cell, PCB, battery and the light-guide slot are all readable.
"""

from __future__ import annotations

import math
from pathlib import Path

import vtk

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "build" / "parts"
OUT = ROOT / "build" / "render" / "section.png"

import sys
sys.path.insert(0, str(ROOT / "tools"))
from render_studio import MAT, hex2rgb  # noqa: E402

CAP = {
    "shell":   (0.66, 0.64, 0.60),
    "plate":   (0.56, 0.57, 0.59),
    "guide":   (0.58, 0.76, 0.90),
    "ledflex": (0.15, 0.38, 0.24),
    "pcb":     (0.16, 0.32, 0.21),
    "sensor":  (0.42, 0.44, 0.47),
    "esp32":   (0.16, 0.17, 0.19),
    "hx711":   (0.16, 0.24, 0.36),
    "usbc":    (0.48, 0.50, 0.52),
    "battery": (0.62, 0.60, 0.54),
    "oled":    (0.12, 0.13, 0.15),
    "glass":   (0.12, 0.13, 0.15),
    "pad":     (0.24, 0.25, 0.27),
}


def actor(name):
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(PARTS / f"{name}_v01.stl"))

    plane = vtk.vtkPlane()
    plane.SetOrigin(0.0, 0.0, 0.0)
    plane.SetNormal(0.0, 1.0, 0.0)      # keep y > 0 (rear half)

    planes = vtk.vtkPlaneCollection()
    planes.AddItem(plane)

    clip = vtk.vtkClipClosedSurface()
    clip.SetInputConnection(reader.GetOutputPort())
    clip.SetClippingPlanes(planes)
    clip.SetScalarModeToColors()
    clip.SetBaseColor(*hex2rgb(MAT[name][0]))
    clip.SetClipColor(*CAP.get(name, (0.7, 0.7, 0.7)))
    clip.Update()

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(clip.GetOutputPort())
    normals.SetFeatureAngle(25.0)
    normals.SetConsistency(True)
    normals.SetSplitting(True)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    mapper.SetScalarVisibility(1)
    a = vtk.vtkActor()
    a.SetMapper(mapper)
    prop = a.GetProperty()
    prop.SetInterpolationToPBR()
    prop.SetMetallic(0.1)
    prop.SetRoughness(0.45)
    return a


def main():
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.985, 0.978, 0.962)
    ren.SetBackground2(0.935, 0.928, 0.912)
    ren.GradientBackgroundOn()

    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(-2000, -2000, -0.05)
    plane.SetPoint1(2000, -2000, -0.05)
    plane.SetPoint2(-2000, 2000, -0.05)
    pm = vtk.vtkPolyDataMapper()
    pm.SetInputConnection(plane.GetOutputPort())
    pa = vtk.vtkActor()
    pa.SetMapper(pm)
    pp = pa.GetProperty()
    pp.SetColor(0.935, 0.928, 0.913)
    pp.LightingOff()
    ren.AddActor(pa)

    for name in MAT:
        ren.AddActor(actor(name))

    for pos, intensity, color in (
        ((-260, -420, 520), 1.9, (1.0, 0.985, 0.955)),
        ((420, -180, 240), 0.8, (0.96, 0.975, 1.0)),
        ((60, 420, 340), 1.0, (0.86, 0.92, 1.0)),
    ):
        L = vtk.vtkLight()
        L.SetPosition(*pos)
        L.SetFocalPoint(0, 0, 8)
        L.SetIntensity(intensity)
        L.SetDiffuseColor(*color)
        L.SetLightTypeToSceneLight()
        ren.AddLight(L)
    ren.SetAmbient(0.18, 0.18, 0.18)

    cam = ren.GetActiveCamera()
    a, e = math.radians(20), math.radians(9)
    dist = 275
    fx, fy, fz = 0, 0, 8.2
    cam.SetFocalPoint(fx, fy, fz)
    cam.SetPosition(fx + dist * math.cos(e) * math.sin(a),
                    fy - dist * math.cos(e) * math.cos(a),
                    fz + dist * math.sin(e))
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(24)
    ren.ResetCameraClippingRange()

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(2000, 1300)
    rw.SetMultiSamples(8)
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(OUT))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    print(OUT)


if __name__ == "__main__":
    main()
