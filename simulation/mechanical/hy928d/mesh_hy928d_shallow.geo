// HY928D v2 with 0.7 mm deep U-slot cavity (0.3 mm web), C3D10 mesh
SetFactory("OpenCASCADE");
Merge "hy928d_v2_shallow07.step";
Mesh.MeshSizeMax = hmax;
Mesh.MeshSizeMin = hmin;
Mesh.ElementOrder = order;
Mesh.Algorithm3D = 10;
Mesh.Optimize = 1;
Mesh.OptimizeNetgen = 0;
If(order == 2)
  Mesh.HighOrderOptimize = 2;
  Mesh.HighOrderNumLayers = 6;
EndIf
