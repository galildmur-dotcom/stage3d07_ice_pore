# P10NN — measured native Gmsh directional diagnostic results

User-provided Windows Gmsh 4.15.2 output: `P10NN_M13_DIRECTIONAL_GMSH_QUALITY_RESULT.json`. No diagnostic candidate passes D031.

| Case | minSICN | minSJ | violator |
|---|---:|---:|---|
| M13 R2 original | 0.16294478890105799 | 0.28115937433961596 | 9478 |
| control (+0.0125 radial) | 0.1981413170001225 | 0.3259889096413908 | 9478 |
| tangent −0.003 mm | 0.1997515453156264 | 0.32769396084300884 | 9478 |
| tangent +0.003 mm | 0.19652848060288458 | 0.3242834918106211 | 9478 |

`minSICN` almost crosses its limit 0.20 but `minSJ` remains far below its limit 0.40. The fixed-pivot tangential scan does not resolve the bottleneck. This **does not prove** that more general node movements or a CAD-conforming remesh cannot resolve it.

Next step P10NO: test the Gmsh native `HighOrder` and `HighOrderElastic` optimizers on independently loaded original M13 R2 *in memory*. Use `Mesh.HighOrderFixBoundaryNodes=1`, but independently compare **all** boundary coordinates and all Tet10 connectivity. No optimized mesh is saved; no generation, FEM, marker, or M13 R3 acceptance. Source documentation: https://gmsh.info/doc/texinfo/.
