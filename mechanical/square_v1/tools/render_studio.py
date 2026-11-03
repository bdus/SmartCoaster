#!/usr/bin/env python3
"""
SmartCoaster V1 (square) studio renderer (system python3 + VTK 9.1, offscreen GL).

Renders the square V1 per-part STLs with PBR materials, a studio
gradient, a soft ground shadow and an emissive halo - something the plain
agentcad preview cannot show.

    python3 tools/render_studio.py --shot all
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import vtk

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "build" / "parts"
OUT = ROOT / "build" / "render"

# name: (hex, metallic, roughness, emissive multiplier, opacity)
MAT = {
    "shell":   ("#F4F2EC", 0.04, 0.40, 0.00, 1.0),
    "plate":   ("#C9CCD0", 0.16, 0.32, 0.00, 1.0),
    "pcb":     ("#0E5A34", 0.05, 0.50, 0.00, 1.0),
    "sensor":  ("#B8BEC5", 0.75, 0.32, 0.00, 1.0),
    "esp32":   ("#20242A", 0.15, 0.55, 0.00, 1.0),
    "hx711":   ("#1E3F6E", 0.05, 0.50, 0.00, 1.0),
    "usbc":    ("#A7ADB4", 0.90, 0.25, 0.00, 1.0),
    "battery": ("#C9C6BC", 0.20, 0.45, 0.00, 1.0),
    "oled":    ("#101317", 0.10, 0.30, 0.22, 1.0),
    "button":  ("#E9E6DF", 0.05, 0.38, 0.00, 1.0),
    "glass":   ("#232830", 0.30, 0.06, 0.00, 0.55),
    "pad":     ("#3E4044", 0.00, 0.85, 0.00, 1.0),
}

# exploded view: per-part translation (mm)
EXPLODE = {
    "pad":     (0, 0, -40),
    "shell":   (0, 0, 0),
    "sensor":  (0, 0, 22),
    "pcb":     (0, 0, 48),
    "esp32":   (0, 0, 48),
    "hx711":   (0, 0, 48),
    "usbc":    (0, 0, 48),
    "battery": (0, 0, 70),
    "oled":    (0, -55, 6),
    "button":  (0, -85, 6),
    "glass":   (0, -115, 6),
    "plate":   (0, 0, 110),
}

SHOTS = {
    # name:        (azimuth, elevation, distance, target, fov, width, height)
    "hero":        (33, 22, 360, (0, 0, 9.0), 20, 2000, 1500),
    "hero_low":    (-55, 9, 360, (0, 0, 9.2), 22, 2000, 1200),
    "front":       (0, 4, 265, (0, 0, 9.0), 20, 2000, 1100),
    "back":        (180, 12, 275, (0, 0, 9.0), 20, 2000, 1200),
    "top":         (0, 89, 390, (0, 0, 9.0), 20, 1800, 1500),
    "detail":      (18, 12, 175, (12, -45, 8.0), 24, 1800, 1350),
    "exploded":    (-28, 24, 900, (0, -20, 52), 17, 1800, 2100),
}

hex2rgb = lambda h: tuple(int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))


def make_actor(name: str, explode: bool = False):
    path = PARTS / f"{name}_v01.stl"
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(path))
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(reader.GetOutputPort())
    normals.SetFeatureAngle(32.0)
    normals.SetConsistency(True)
    normals.SetSplitting(True)
    normals.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    mapper.SetScalarVisibility(0)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    hexcol, metal, rough, emis, opacity = MAT[name]
    r, g, b = hex2rgb(hexcol)
    prop = actor.GetProperty()
    prop.SetInterpolationToPBR()
    prop.SetColor(r, g, b)
    prop.SetMetallic(metal)
    prop.SetRoughness(rough)
    prop.SetOpacity(opacity)
    if emis > 0:
        prop.SetEmissiveFactor(emis * r, emis * g, emis * b)

    if explode:
        dx, dy, dz = EXPLODE[name]
        if dx or dy or dz:
            t = vtk.vtkTransform()
            t.Translate(dx, dy, dz)
            actor.SetUserTransform(t)
    return actor


def build_scene(renderer: vtk.vtkRenderer, explode: bool = False):
    renderer.SetBackground(0.985, 0.978, 0.962)
    renderer.SetBackground2(0.935, 0.928, 0.912)
    renderer.GradientBackgroundOn()

    # studio floor
    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(-2500, -2500, -0.05)
    plane.SetPoint1(2500, -2500, -0.05)
    plane.SetPoint2(-2500, 2500, -0.05)
    plane.SetResolution(1, 1)
    pm = vtk.vtkPolyDataMapper()
    pm.SetInputConnection(plane.GetOutputPort())
    pa = vtk.vtkActor()
    pa.SetMapper(pm)
    pp = pa.GetProperty()
    pp.SetInterpolationToPBR()
    pp.SetColor(0.935, 0.928, 0.913)
    pp.LightingOff()
    renderer.AddActor(pa)

    # soft contact shadow: one RGBA radial-gradient quad
    n = 192
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, 1)
    img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 4)
    for j in range(n):
        for i in range(n):
            x = (i - (n - 1) / 2) / ((n - 1) / 2)
            y = (j - (n - 1) / 2) / ((n - 1) / 2)
            r2 = x * x + y * y
            a = int(255 * 0.42 * math.exp(-3.6 * r2))
            for comp, val in ((0, 24), (1, 23), (2, 21), (3, a)):
                img.SetScalarComponentFromDouble(i, j, 0, comp, val)
    tex = vtk.vtkTexture()
    tex.SetInputData(img)
    tex.InterpolateOn()
    shadow = vtk.vtkPlaneSource()
    shadow.SetOrigin(-135, -135, 0.02)
    shadow.SetPoint1(135, -135, 0.02)
    shadow.SetPoint2(-135, 135, 0.02)
    sm = vtk.vtkPolyDataMapper()
    sm.SetInputConnection(shadow.GetOutputPort())
    sm.SetScalarVisibility(0)
    sa = vtk.vtkActor()
    sa.SetMapper(sm)
    sa.SetTexture(tex)
    sp = sa.GetProperty()
    sp.LightingOff()
    sp.SetColor(1, 1, 1)
    renderer.AddActor(sa)

    hidden = {"pad", "oled", "button", "glass"} if explode else set()
    for name in MAT:
        if name not in hidden:
            renderer.AddActor(make_actor(name, explode))

    # lighting: key / fill / rim
    key = vtk.vtkLight()
    key.SetPosition(-320, -420, 620)
    key.SetFocalPoint(0, 0, 10)
    key.SetIntensity(2.60)
    key.SetDiffuseColor(1.0, 0.985, 0.955)
    key.SetLightTypeToSceneLight()

    fill = vtk.vtkLight()
    fill.SetPosition(420, -260, 260)
    fill.SetFocalPoint(0, 0, 10)
    fill.SetIntensity(0.95)
    fill.SetDiffuseColor(0.96, 0.975, 1.0)
    fill.SetLightTypeToSceneLight()

    rim = vtk.vtkLight()
    rim.SetPosition(120, 460, 380)
    rim.SetFocalPoint(0, 0, 20)
    rim.SetIntensity(1.35)
    rim.SetDiffuseColor(0.86, 0.92, 1.0)
    rim.SetLightTypeToSceneLight()

    for light in (key, fill, rim):
        renderer.AddLight(light)
    renderer.SetAmbient(0.22, 0.22, 0.22)


def set_camera(renderer, az, el, dist, target, fov, aspect):
    cam = renderer.GetActiveCamera()
    a, e = math.radians(az), math.radians(el)
    tx, ty, tz = target
    cam.SetFocalPoint(tx, ty, tz)
    cam.SetPosition(
        tx + dist * math.cos(e) * math.sin(a),
        ty - dist * math.cos(e) * math.cos(a),
        tz + dist * math.sin(e),
    )
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(fov)
    renderer.ResetCameraClippingRange()


def render(shot: str, explode: bool, ss: int = 1) -> Path:
    az, el, dist, target, fov, w, h = SHOTS[shot]
    renderer = vtk.vtkRenderer()
    build_scene(renderer, explode)
    set_camera(renderer, az, el, dist, target, fov, w / h)

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(renderer)
    rw.SetSize(w, h)
    rw.SetMultiSamples(8)
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetScale(ss)
    w2i.Update()

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{shot}.png"
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(out))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default="all",
                    help="all | " + " | ".join(SHOTS))
    args = ap.parse_args()
    if args.shot == "all":
        for name in ("hero", "hero_low", "front", "top", "detail",
                     "back", "exploded"):
            print(render(name, explode=(name == "exploded")))
    else:
        print(render(args.shot, explode=(args.shot == "exploded")))


if __name__ == "__main__":
    main()
