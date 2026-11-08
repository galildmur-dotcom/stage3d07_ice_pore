// Stage 3D-10U: H4W4B2 mesh-size field.
// Independent pilot: 4x smaller prescribed pore-surface size than H4;
// additional, modest volume refinement across distance 0..2 mm from pore.
// Exact OCC geometry, boundaries, physical tags and Tet10 settings are kept
// identical to P10O H4W2. Units: SI (metres).
//
// This is a NESTED size field: h_H4W4B2(d) <= h_H4W2(d) for all d>=0.
// It is NOT a claim of actual mesh nesting, element-size ratios or FEM
// convergence. These must be checked from the generated MSH2.2 Tet10 mesh.

SetFactory("OpenCASCADE");
If(!Exists(nearSize))
  nearSize = 0.000135;
EndIf
If(!Exists(farSize))
  farSize = 0.003900;
EndIf
If(!Exists(wallSize))
  wallSize = 0.0000675; // H4W2 wall prescribed size, NOT H4W4B2
EndIf
If(!Exists(wallFull))
  wallFull = 0.000080;
EndIf
If(!Exists(wallEnd))
  wallEnd = 0.015000;
EndIf

// Relative to H4W2, halve the size AT the pore boundary. The extra
// near-surface refinement decays over 0.06 mm, leaving the existing H4W2
// field unchanged outside that narrow part, modulo the separate band field.
If(!Exists(wallExtra))
  wallExtra = 0.50;
EndIf
If(!Exists(wallDecay))
  wallDecay = 0.000060;
EndIf

// To investigate the measured 0.25..2 mm contribution of D_y20(jpeak),
// decrease the H4 base size by 10% through most of that region, tapering
// smoothly back to H4 beyond 2 mm (essentially equal by 5 mm).
// Moderate reduction keeps the P10N 8-GiB state-buffer budget plausible.
If(!Exists(bandReduction))
  bandReduction = 0.10;
EndIf
If(!Exists(bandEnd))
  bandEnd = 0.002000;
EndIf
If(!Exists(bandTaper))
  bandTaper = 0.000200;
EndIf

If(nearSize<=0 || farSize<=nearSize || wallSize<=0 || wallSize>=nearSize)
  Error("P10U: invalid H4/H4W2 size parameters");
EndIf
If(wallFull<=0 || wallEnd<=wallFull)
  Error("P10U: invalid wallFull/wallEnd");
EndIf
If(wallExtra<=0 || wallExtra>=1 || wallDecay<=0)
  Error("P10U: invalid wallExtra/wallDecay");
EndIf
If(bandReduction<=0 || bandReduction>=1 || bandEnd<=0 || bandTaper<=0)
  Error("P10U: invalid band parameters");
EndIf

// Defines full geometry and canonical size fields:
// Field[1] = Distance from pore (m), Field[2] = H4 base Threshold.
Include "sphere_pore_B6_refined.geo";

// Reproduce H4W2 without changing its prescribed size profile.
Field[3] = Threshold;
Field[3].InField = 1;
Field[3].SizeMin = wallSize;
Field[3].SizeMax = farSize;
Field[3].DistMin = wallFull;
Field[3].DistMax = wallEnd;

// Additional 2x refinement right at the wall, decaying outward.
// Gmsh MathEval may refer to other field values as F1, F2, F3.
Field[4] = MathEval;
Field[4].F = Sprintf("F3*(1-%g*exp(-F1/%g))", wallExtra, wallDecay);

// Smooth support-band refinement: 10% smaller than H4 across most of
// 0.25..2 mm; returns continuously to H4 beyond 2 mm.
Field[5] = MathEval;
Field[5].F = Sprintf("F2*(1-%g/(1+exp((F1-%g)/%g)))",
                     bandReduction, bandEnd, bandTaper);

// Min guarantees we NEVER request larger elements than H4W2.
Field[6] = Min;
Field[6].FieldsList = {2, 3, 4, 5};
Background Field = 6;

// Preserve the P10O/H4 order, geometric treatment, tags and ASCII output.
Mesh.MeshSizeExtendFromBoundary = 0;
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm3D = 10;
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 1;
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
Mesh.Optimize = 1;
