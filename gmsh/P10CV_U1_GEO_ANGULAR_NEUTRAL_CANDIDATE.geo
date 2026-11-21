// P10CV: GEO source only; no physical FEM authorized.
// Canonical CAD/physical tags come from included source; all sizes are metres.
// Nominal radial distance-to-PORE_WALL size field, no theta/phi preference.
If(!Exists(p10cvWallSize))
  p10cvWallSize = 0.00002;
EndIf
If(!Exists(p10cvBandSize))
  p10cvBandSize = 0.00020;
EndIf
If(!Exists(p10cvFarSize))
  p10cvFarSize = 0.0020;
EndIf
If(p10cvWallSize <= 0 || p10cvWallSize > p10cvBandSize || p10cvBandSize > p10cvFarSize)
  Error("P10CV: require 0 < wallSize <= bandSize <= farSize");
EndIf

Include "sphere_pore_B6_refined.geo";

// Field[1] is the sampled distance to pore() of the canonical source.
// Near-wall transition to 0.2 mm. The second threshold broadens to 2 mm.
Field[3] = Threshold;
Field[3].InField = 1;
Field[3].SizeMin = p10cvWallSize;
Field[3].SizeMax = p10cvBandSize;
Field[3].DistMin = 0.00002;
Field[3].DistMax = 0.00080;

Field[4] = Threshold;
Field[4].InField = 1;
Field[4].SizeMin = p10cvWallSize;
Field[4].SizeMax = p10cvFarSize;
Field[4].DistMin = 0.00080;
Field[4].DistMax = 0.01200;

// Larger of two size envelopes: near pore wallSize, in B6 graded, far farSize.
Field[5] = Max;
Field[5].FieldsList = {3,4};
Background Field = 5;
Mesh.MeshSizeMin = p10cvWallSize;
Mesh.MeshSizeMax = p10cvFarSize;
Mesh.MeshSizeExtendFromBoundary = 0;
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
