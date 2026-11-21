// P10DB M1: the SECOND globally quasi-uniform mesh, after the U0/M0 solve.
// Constant size in the WHOLE physical ice volume; NO adaptive size field.
// User decision D-018C: nominal per-element volume ratio M1/M0 = 0.8.
// Assuming V ~ h^3: 2.0 mm * cbrt(0.8) = 1.8566355334451116 mm.
// Gmsh will remesh: actual individual Tet10 volumes are NOT forced to 0.8.
uniformSize = 0.0018566355334451116;
Include "P10CS_U0_UNIFORM_VOLUME.geo";
