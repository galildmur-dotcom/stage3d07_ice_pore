// Stage 3D-09D4: HP4 graded wall refinement of the validated HP size field.
// Identical geometric domain, physical groups and Tet10 settings to H3/H4.
// SI units; pore radius=1mm, fixed B6 observation surface.
// The extra threshold decreases characteristic h only within approximately 0.7 mm of the wall.
SetFactory("OpenCASCADE");
If(!Exists(nearHP))
  nearHP = 0.000085;
EndIf
If(!Exists(nearH3))
  nearH3 = 0.000190;
EndIf
If(!Exists(farH3))
  farH3 = 0.003900;
EndIf
If(!Exists(localFull))
  localFull = 0.00030;
EndIf
If(!Exists(localEnd))
  localEnd = 0.01500;
EndIf
If(nearHP >= nearH3 || nearHP <= 0)
  Error("HP must be smaller than H3 near-wall size");
EndIf
If(localEnd <= localFull)
  Error("localEnd must exceed localFull");
EndIf
r0=0.001; r6=0.006; eps=0.0000001;
Box(1) = {-0.03,-0.03,0,0.06,0.06,0.05};
Sphere(2) = {0,0,0.03,r6};
Sphere(3) = {0,0,0.03,r0};
outer() = BooleanDifference{Volume{1}; Delete;}{Volume{2};};
shell() = BooleanDifference{Volume{2}; Delete;}{Volume{3}; Delete;};
Coherence;
Physical Volume("ICE_VOLUME",1) = {outer(),shell()};
ptop() = Surface In BoundingBox{-0.03001,-0.03001,0.05-eps,0.03001,0.03001,0.05+eps};
pbottom() = Surface In BoundingBox{-0.03001,-0.03001,-eps,0.03001,0.03001,eps};
pxm() = Surface In BoundingBox{-0.03-eps,-0.03001,-eps,-0.03+eps,0.03001,0.05001};
pxp() = Surface In BoundingBox{0.03-eps,-0.03001,-eps,0.03+eps,0.03001,0.05001};
pym() = Surface In BoundingBox{-0.03001,-0.03-eps,-eps,0.03001,-0.03+eps,0.05001};
pyp() = Surface In BoundingBox{-0.03001,0.03-eps,-eps,0.03001,0.03+eps,0.05001};
pore() = Surface In BoundingBox{-r0-eps,-r0-eps,0.03-r0-eps,r0+eps,r0+eps,0.03+r0+eps};
b6surf() = Surface In BoundingBox{-r6-eps,-r6-eps,0.03-r6-eps,r6+eps,r6+eps,0.03+r6+eps};
b6surf() -= pore();
Physical Surface("TOP_ROBIN",2) = {ptop()};
Physical Surface("BOTTOM_INSULATED",3) = {pbottom()};
Physical Surface("X_MINUS",4) = {pxm()};
Physical Surface("X_PLUS",5) = {pxp()};
Physical Surface("Y_MINUS",6) = {pym()};
Physical Surface("Y_PLUS",7) = {pyp()};
Physical Surface("PORE_WALL",8) = {pore()};
Physical Surface("B6_INTERFACE",9) = {b6surf()};
// Baseline H3 background field: unchanged away from the pore.
Field[1] = Distance;
Field[1].SurfacesList={pore()};
Field[1].Sampling=100;
Field[2] = Threshold;
Field[2].InField=1;
Field[2].SizeMin=nearH3;
Field[2].SizeMax=farH3;
Field[2].DistMin=0.0015;
Field[2].DistMax=0.018;
// Extra pore-wall band: min with Field[2] returns exactly to H3 at ~0.70mm.
// SizeMax must be farH3 (not nearH3), otherwise the entire domain is refined!
Field[3] = Threshold;
Field[3].InField=1;
Field[3].SizeMin=nearHP;
Field[3].SizeMax=farH3;
Field[3].DistMin=localFull;
Field[3].DistMax=localEnd;
Field[4] = Min;
Field[4].FieldsList={2,3};
// Additional smooth growth from h_wall = 85 um / 4.
// The ratio applies at the pore wall; the layer is graded, not uniformly refined.
Field[5] = Threshold;
Field[5].InField = 1;
Field[5].SizeMin = 2.125e-05;
Field[5].SizeMax = farH3;
Field[5].DistMin = 0.00006;
Field[5].DistMax = 0.004;
Field[6] = Min;
Field[6].FieldsList = {4,5};
Background Field = 6;
Mesh.MeshSizeExtendFromBoundary=0;
Mesh.MeshSizeFromPoints=0;
Mesh.MeshSizeFromCurvature=0;
Mesh.Algorithm3D=10;
Mesh.ElementOrder=2;
Mesh.HighOrderOptimize=1;
Mesh.MshFileVersion=2.2;
Mesh.Binary=0;
Mesh.Optimize=1;
