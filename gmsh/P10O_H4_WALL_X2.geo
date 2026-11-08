// Stage 3D-10O: H4 bulk Tet10 refinement in a narrow pore-wall band.
// Based on EXACT H4 CAD domain and original physical tags 1..9.
// Units: metres; sphere a=1mm, centre (0,0,30mm); B6 sphere r=6mm;
// outer box 60 x 60 x 50 mm.  No symmetry constraints or transfinite mesh.
// Generate with Gmsh 4.15.2, -3 -format msh2 -nt 4.
// Reproducibility: the output Tet10 mesh may vary by OS/Gmsh build.

SetFactory("OpenCASCADE");
If(!Exists(nearSize))
  nearSize = 0.000135;   // original H4 first-band characteristic size
EndIf
If(!Exists(farSize))
  farSize = 0.003900;   // original far-field characteristic size
EndIf
If(!Exists(wallSize))
  wallSize = 0.0000675; // 2x smaller near the pore wall
EndIf
If(!Exists(wallFull))
  wallFull = 0.000080;  // full-strength refinement up to 0.08 mm off wall
EndIf
If(!Exists(wallEnd))
  wallEnd = 0.015000;   // ramp to FAR size; not to nearSize!
EndIf

If(wallSize <= 0 || wallSize >= nearSize)
  Error("P10O: wallSize must be positive and < nearSize");
EndIf
If(wallFull <= 0 || wallEnd <= wallFull)
  Error("P10O: invalid wallFull/wallEnd");
EndIf

// Reuse canonical OpenCASCADE construction, size field [1] = pore distance,
// baseline H4 threshold field [2], and ALL physical surface/volume tags.
Include "sphere_pore_B6_refined.geo";

// Localized SECOND field: add a refined band near the pore while reverting
// exactly to the baseline H4 field outside the near-wall region.  In
// particular, do NOT use SizeMax=nearSize: it would refine the whole domain.
Field[3] = Threshold;
Field[3].InField = 1;
Field[3].SizeMin = wallSize;
Field[3].SizeMax = farSize;
Field[3].DistMin = wallFull;
Field[3].DistMax = wallEnd;
Field[4] = Min;
Field[4].FieldsList = {2,3};
Background Field = 4;

// Preserve exactly the tested H4 curved Tet10 settings.
Mesh.MeshSizeExtendFromBoundary = 0;
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm3D = 10;
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 1;
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
Mesh.Optimize = 1;
