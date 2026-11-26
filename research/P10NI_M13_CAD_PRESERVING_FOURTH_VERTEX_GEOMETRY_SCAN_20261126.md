# P10NI — virtual radial position of off-pore fourth Tet10 corner, CAD face fixed

2026-11-26. Independent source-only study of the three canonically bad M13 R1/R2 Tet10, from exact SHA-pinned user meshes. No native Gmsh, meshing, physical FEM or one-shot marker use.

The tool `research/tools/p10ni_m13_cad_preserving_fourth_vertex_virtual_scan.py` holds the six nodes of the actual curved pore face **exactly fixed**, displaces only the **fourth off-surface corner** along the radius from sphere center through the pore-face centroid, and displaces each of its three incident midside nodes by **one-half the same vector**. Thus the pore-surface quadratic geometry is unchanged in every virtual copy. It evaluates 729-point quadratic Tet10 Jacobians and singular values, including positivity of sampled detJ, but **does not update neighboring tets** sharing the fourth corner or edges. These virtual copies are *not conforming legal meshes* and cannot serve as physical FEM geometry.

| Defective element | Base min(σ3/σ1) | Virtual +0.015 mm factor | Virtual +0.015 mm local element volume ratio | Virtual +0.030 mm factor | Virtual +0.030 mm volume ratio |
|---|---:|---:|---:|---:|---:|
| M13 R1 / 13346 | 0.05962 | 1.328 | 1.146 | 1.633 | 1.292 |
| M13 R1 / 9035 | 0.09415 | 1.218 | 1.111 | 1.417 | 1.223 |
| M13 R2 / 9478 | **0.04483** | **1.239** | **1.095** | **1.473** | **1.189** |

Virtual inward movement −0.015 mm worsens the minimum singular-value ratio in all three cases (R2 0.04483→0.034; R1 / 13346 0.05962→0.039). The relationship is strongly directional: moving the fourth corner **outward** can reduce the singular-value degeneration while leaving the CAD face unchanged.

**Scientific interpretation:** The strong pore-surface curvature effect isolated by P10NH can be mitigated *geometrically* via the height/placement of the off-pore vertex and its incident straight-edge midside nodes, rather than flattening the spherical face or forcing more dense mesh sizes. The slope is meaningful but the virtual ratio is **not canonical Gmsh minSJ**, so it does not prove a quality gate will pass. A 0.015-mm perturbation changes individual Tet10 volume by 9.5–14.6%, and a 0.030-mm perturbation by 18.9–29.2%; the actual constrained patch-wise change must be checked against adjacent element shape and size smoothness.

The next algorithmic test should be **quality-driven, CAD-conforming near-wall mesh-node optimization**: pin pore-surface nodes, move/select off-surface volume nodes as a mutually conforming patch, update their incident midside nodes and evaluate *all* neighboring tets. Before planning a new one-shot M13 R3, develop a source-only graph of shared nodes and incident elements, and examine the effect of small radial patch-wide moves on the minimum curved Jacobian and singular-value ratio throughout the patch. Do not treat the single-tet virtual optimal +0.15–0.20 mm as a mesh prescription: it increases one element's volume by more than 100% and ignores its neighbors.

Full reproducible trial coordinates and results: `p10ni_m13_virtual_fourth_vertex/P10NI_M13_FOURTH_VERTEX_RADIAL_SCAN.json`. The exact sphere CAD, physical shape derivative method, A adaptation source and all historical mesh evidence are unchanged.
