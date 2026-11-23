// P10GL: separately user-approved ONE native Windows Gmsh4.15.2 -3 mesh-only trial.
// Entire CAD, original C1 M0 F3, and southern F4/F5/F6 sizes are byte-pinned
// inside the already independently tested P10GK source-only release archive.
// This wrapper adds NO fields or geometry and NEVER runs FEM.
Include "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo";
Mesh.Algorithm3D = 10;
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 1;
Mesh.MeshSizeFactor = 0.9378887276834518;
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
