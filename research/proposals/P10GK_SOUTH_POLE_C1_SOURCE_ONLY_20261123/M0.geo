// P10FP fresh-series M0: canonical 3D CAD and C1 baseline radial mesh sizing.
// No physical-sensitivity indicator in M0. Not byte-identical to historical H0.
// M0 near/far = P10DG nominal M1 sizes / cbrt(0.8), so M1 can target -20% volume.
nearSize = 0.0004616510070248522;
farSize = 0.0075970525806110575;
Include "sphere_pore_B6_refined.geo";
// C1 50um softplus seams at the original Threshold breakpoints (1.5/18mm).
// This approximates the original linear transition, not a globally cubic ramp.
// The old Gmsh Threshold F2 is superseded, keeping all CAD/physical tags.
Field[3] = MathEval;
// P10FP_F3_GENERATED_BEGIN
Field[3].F = StrCat(
  "(0.00046165100702485221+0.43244858021734583*((max(0,(((sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001))-0.0015)-5.0000000000000002e-05)+5.0000000000000002e-05*(min(1,max(0,((((sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001))-0.0015)+5.0000000000000002e-05)/0.0001)))*(min(1,max(0,((((sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001))-0.0015)+5.0000000000000002e-05)/0.0001))))-(max(0,(((sqr",
  "t(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001))-0.017999999999999999)-5.0000000000000002e-05)+5.0000000000000002e-05*(min(1,max(0,((((sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001))-0.017999999999999999)+5.0000000000000002e-05)/0.0001)))*(min(1,max(0,((((sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001))-0.017999999999999999)+5.0000000000000002e-05)/0.0001))))))"
);
// P10FP_F3_GENERATED_END
Background Field=3;
Mesh.Algorithm=5;
Mesh.Algorithm3D=10;
Mesh.ElementOrder=2;
Mesh.HighOrderOptimize=1;
Mesh.MeshSizeExtendFromBoundary=0;
Mesh.MeshSizeFromPoints=0;
Mesh.MeshSizeFromCurvature=0;
Mesh.MeshSizeFactor=1;
Mesh.MeshSizeMin=0;
Mesh.MeshSizeMax=1e22;
Mesh.MshFileVersion=2.2;
Mesh.Binary=0;
