// Stage 3D-01 v4: 3D-only, SI metres; Gmsh OCC exact CAD surfaces.
// Mesh parameter sizefac CLI: -setnumber sizefac 1.0 (H0), 0.72 (H1), 0.52 (H2).
SetFactory("OpenCASCADE");
If(!Exists(sizefac))
  sizefac = 1;
EndIf
If(!Exists(nearSize))
 nearSize = 0.00019;
EndIf
If(!Exists(farSize))
 farSize = 0.0039;
EndIf
If(!Exists(poreR))
  poreR = 0.001;
EndIf
If(!Exists(poreCX))
  poreCX = 0;
EndIf
If(!Exists(poreCY))
  poreCY = 0;
EndIf
If(!Exists(poreCZ))
  poreCZ = 0.03;
EndIf
r0=poreR; r6=0.006; eps=0.0000001;
Box(1) = {-0.03,-0.03,0,0.06,0.06,0.05};
Sphere(2) = {0,0,0.03,r6};
Sphere(3) = {poreCX,poreCY,poreCZ,r0};
// Partition: exterior ice + B6 shell around spherical pore.
outer() = BooleanDifference{Volume{1}; Delete;}{Volume{2};};
shell() = BooleanDifference{Volume{2}; Delete;}{Volume{3}; Delete;};
Coherence;
Physical Volume("ICE_VOLUME",1) = {outer(),shell()};
// Physical surface IDs conform to canonical contract; B6 is an additional internal tag 9.
ptop()   = Surface In BoundingBox{-0.03001,-0.03001,0.05-eps,0.03001,0.03001,0.05+eps};
pbottom()= Surface In BoundingBox{-0.03001,-0.03001,-eps,0.03001,0.03001,eps};
pxm()    = Surface In BoundingBox{-0.03-eps,-0.03001,-eps,-0.03+eps,0.03001,0.05001};
pxp()    = Surface In BoundingBox{0.03-eps,-0.03001,-eps,0.03+eps,0.03001,0.05001};
pym()    = Surface In BoundingBox{-0.03001,-0.03-eps,-eps,0.03001,-0.03+eps,0.05001};
pyp()    = Surface In BoundingBox{-0.03001,0.03-eps,-eps,0.03001,0.03+eps,0.05001};
pore() = Surface In BoundingBox{poreCX-r0-eps,poreCY-r0-eps,poreCZ-r0-eps,poreCX+r0+eps,poreCY+r0+eps,poreCZ+r0+eps};
b6surf()= Surface In BoundingBox{-r6-eps,-r6-eps,0.03-r6-eps,r6+eps,r6+eps,0.03+r6+eps};
b6surf() -= pore(); // exclude pore surface located inside the larger bounding box
Physical Surface("TOP_ROBIN",2) = {ptop()};
Physical Surface("BOTTOM_INSULATED",3) = {pbottom()};
Physical Surface("X_MINUS",4) = {pxm()};
Physical Surface("X_PLUS",5) = {pxp()};
Physical Surface("Y_MINUS",6) = {pym()};
Physical Surface("Y_PLUS",7) = {pyp()};
Physical Surface("PORE_WALL",8) = {pore()};
Physical Surface("B6_INTERFACE",9) = {b6surf()};
// Refine near the pore & B6 and transition continuously to distant boundaries.
Field[1] = Distance;
Field[1].SurfacesList={pore()};
Field[1].Sampling=100;
Field[2] = Threshold;
Field[2].InField=1;
Field[2].SizeMin=nearSize;
Field[2].SizeMax=farSize;
Field[2].DistMin=0.0015;
Field[2].DistMax=0.018;
Background Field=2;
Mesh.MeshSizeExtendFromBoundary=0;
Mesh.MeshSizeFromPoints=0;
Mesh.MeshSizeFromCurvature=0;
Mesh.Algorithm3D=10;
Mesh.ElementOrder=2;
Mesh.HighOrderOptimize=1;
Mesh.MshFileVersion=2.2;
Mesh.Binary=0;
Mesh.Optimize=1;
