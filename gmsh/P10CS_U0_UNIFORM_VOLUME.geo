// Stage3D07 / P10CS U0: exploratory quasi-uniform whole-volume candidate.
// No FEM, no adaptive polar/radial bias; h is the constant requested size in m.
// Default h=2mm is MESH-ONLY geometry QA, NOT physical convergence evidence.

If(!Exists(uniformSize))
  uniformSize = 0.002;
EndIf
If(uniformSize <= 0)
  Error("P10CS_U0: uniformSize must be positive");
EndIf

// Canonical OCC 3D geometry, B6 partition, physical groups 1..9.
Include "sphere_pore_B6_refined.geo";

// Override original distance/threshold field for this U0 control.
Field[3] = MathEval;
Field[3].F = Sprintf("%g", uniformSize);
Background Field = 3;
Mesh.MeshSizeMin = uniformSize;
Mesh.MeshSizeMax = uniformSize;
Mesh.MeshSizeExtendFromBoundary = 0;
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm3D = 10;
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 1;
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
Mesh.Optimize = 1;
