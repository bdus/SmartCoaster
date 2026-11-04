// HY928D v2 plate mesh
// gmsh -3 -format msh2 -setnumber hmax 0.3 -setnumber hmin 0.1 -setnumber order 2 \
//       -o mesh_h030_c3d10.msh mesh_hy928d.geo
SetFactory("OpenCASCADE");
Merge "../../../mechanical/hy928d/build/hy928d_v2.step";
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
