#!/usr/bin/env python3
"""Render 3D isometric views from the surface VTP written by post_case.py.
Run with the system python3 (VTK 9.1):
  python3 render_vtk.py figs/case_h030_c3d10.vtp figs/fig_3d_h030
"""
import sys, vtk

def render(vtp, prefix, warp_scale=2.0, vm_max=None):
    r = vtk.vtkXMLPolyDataReader(); r.SetFileName(vtp); r.Update()
    pd = r.GetOutput()
    print('points', pd.GetNumberOfPoints(), 'polys', pd.GetNumberOfPolys())

    w = vtk.vtkWarpVector(); w.SetInputData(pd); w.SetScaleFactor(warp_scale)
    w.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, 'U')
    w.Update()
    wpd = w.GetOutput()

    # scalar ranges
    vm = pd.GetPointData().GetArray('vonMises')
    rng = vm.GetRange()
    print('vM range', rng)
    if vm_max is None:
        vm_max = rng[1]
    lut = vtk.vtkLookupTable(); lut.SetHueRange(0.667, 0.0); lut.SetTableRange(0.0, vm_max)
    lut.Build()

    # Uz scalar is written directly into the VTP
    uz = pd.GetPointData().GetArray('Uz')
    uzr = uz.GetRange()
    print('Uz range', uzr)

    def make_window(scalars_name, title, fname, table, rng2, bar_title):
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(wpd)
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray(scalars_name)
        mapper.SetLookupTable(table)
        mapper.SetScalarRange(rng2)
        mapper.ScalarVisibilityOn()
        actor = vtk.vtkActor(); actor.SetMapper(mapper)
        actor.GetProperty().SetInterpolationToPhong()
        actor.GetProperty().SetSpecular(0.15); actor.GetProperty().SetSpecularPower(20)

        ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
        ren.AddActor(actor)
        ren.SetUseDepthPeeling(1)

        # outline for context
        outline = vtk.vtkOutlineFilter(); outline.SetInputData(pd)
        om = vtk.vtkPolyDataMapper(); om.SetInputConnection(outline.GetOutputPort())
        oa = vtk.vtkActor(); oa.SetMapper(om); oa.GetProperty().SetColor(0.2, 0.2, 0.2)
        ren.AddActor(oa)

        bar = vtk.vtkScalarBarActor(); bar.SetLookupTable(table); bar.SetNumberOfLabels(6)
        bar.SetTitle(''); bar.SetWidth(0.045); bar.SetHeight(0.72)
        bar.SetPosition(0.92, 0.14)
        bar.SetTextPositionToPrecedeScalarBar()
        bar.GetLabelTextProperty().SetFontSize(13)
        ren.AddActor2D(bar)

        txt = vtk.vtkTextActor(); txt.SetInput(title)
        txt.GetTextProperty().SetFontSize(24); txt.GetTextProperty().SetColor(0, 0, 0)
        txt.SetPosition(20, 20)
        ren.AddActor2D(txt)

        # camera: isometric from front-right-top
        ren.ResetCamera()
        cam = ren.GetActiveCamera()
        cam.SetPosition(55, -55, 40)
        cam.SetFocalPoint(0, 0, 1)
        cam.SetViewUp(0, 0, 1)
        cam.ParallelProjectionOn()
        ren.ResetCamera()
        cam.Zoom(1.15)

        rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1)
        rw.SetSize(1600, 1200); rw.AddRenderer(ren)
        rw.Render()
        img = vtk.vtkWindowToImageFilter(); img.SetInput(rw); img.SetScale(1)
        img.Update()
        wr = vtk.vtkPNGWriter(); wr.SetFileName(fname); wr.SetInputConnection(img.GetOutputPort())
        wr.Write()
        print('wrote', fname)

    # vM view
    make_window('vonMises', 'von Mises (MPa) | 5 kg | deformation x%.1f' % warp_scale,
                prefix + '_vm.png', lut, (0.0, vm_max), 'MPa')
    # Uz view
    lut2 = vtk.vtkLookupTable(); lut2.SetHueRange(0.667, 0.0)
    lut2.SetTableRange(uzr[0], uzr[1]); lut2.Build()
    make_window('Uz', 'Uz (mm) | 5 kg | deformation x%.1f' % warp_scale,
                prefix + '_uz.png', lut2, uzr, 'mm')

if __name__ == '__main__':
    vtp = sys.argv[1]; prefix = sys.argv[2]
    vm_max = float(sys.argv[3]) if len(sys.argv) > 3 else None
    render(vtp, prefix, vm_max=vm_max)
