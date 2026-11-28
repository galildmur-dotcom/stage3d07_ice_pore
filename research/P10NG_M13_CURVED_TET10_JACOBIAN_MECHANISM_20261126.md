# P10NG — local geometric mechanism of M13 R1/R2 D031 failures

Date 2026-11-26. **READ ONLY:** the script `research/tools/p10ng_m13_curved_tet10_local_jacobian_diagnostic.py` used exact pinned Gmsh2 Tet10 connectivity and nodes, the existing verified `p10hv_independent_scan.rule(9)` quadratic Tet10 polynomial, and 729 quadrature points per element. For each canonical D031 failing element, the script computed curved mapping Jacobians and compared them to 24 closest pore-boundary Tet10 neighbors by centroid. No new Gmsh calls, meshing, FEM or one-shot markers.

| Geometric metric | M13 R1 tag 13346 | M13 R1 tag 9035 | M13 R2 tag 9478 | Median of 24 R2 local neighbors |
|---|---:|---:|---:|---:|
| `min curved detJ / abs(straight corner detJ)` | 0.3584 | 0.3768 | **0.3165** | 0.9338 |
| `min sigma3/sigma1` over 729QP | 0.0596 | 0.0942 | **0.0448** | 0.2060 |
| `curved integrated volume / straight corner volume` | 0.8880 | 0.871 | **0.8261** | 0.9692 |
| Face-normal height / mean face edge | 0.8126 | (see JSON) | 0.4294 | 0.5463 |
| Maximum deviation of Tet10 midside node from its straight-edge midpoint (mm) | 0.0141 | 0.0208 | **0.0212** | (see JSON) |

For the R2 failing element, all 24 nearest pore-boundary neighbors have **larger** normalized minimum curved Jacobian and **larger** minimum singular-value ratio than the failing element. The four corner vertices of that R2 element give a relatively regular pore Tri6 face with minimum angle 56.05° (65.6th percentile of all R2 pore surface triangles, P10NF), while the curved Jacobian falls to only 31.65% of its straight-corner value at its worst sampled point. The defect is therefore associated with the **quadratic mapping** rather than demonstrably poor surface corner angles or simply uneven straight corner-edge lengths.

Interpretation and limits:

1. This is strong numerical evidence for exceptional **curved Tet10 metric distortion** and a plausible explanation of low canonical minSJ/minSICN. The 729QP minimum and singular-value ratios are not the exact canonical Gmsh definitions; they are independent geometrical proxies and should not be substituted for D031.
2. The cause of that distortion (surface edge midside location, off-surface edge midside location, fourth-vertex geometry, or mesher topology) remains unresolved. Relative curved volume distortion alone does **not** isolate which midside nodes cause the small singular value.
3. P10NF already demonstrated that a good boundary Tri6 face does not guarantee good adjacent Tet10 quality; a purely local scalar size shrink was insufficient and moved the worst element in R2.

**Next action before any M13 R3:** perform a *read-only, per-edge midside sensitivity test* on the existing bad Tet10: replace selected curved midside coordinates by their straight-edge midpoint in virtual copies, while preserving the original mesh unchanged, to identify which edge groups dominate the Jacobian degeneration. This is a diagnostic thought experiment, **not** an admissible final mesh, especially when the changed nodes lie on the spherical pore CAD surface. Design any future mesh improvement around canonical high-order geometry quality while preserving CAD and FEM interpolation. No M13 FEM or R3 mesh attempt is authorized.

Exact values and neighboring statistics: `p10ng_m13_jacobian/P10NG_M13_R1_R2_CURVED_TET10_LOCAL_729QP.json`. Source SHA is inherited and independently validated for both R1 and R2.

## P10NH virtual midside ablation (performed; still read-only)

The new script `research/tools/p10nh_m13_virtual_midside_ablation_readonly.py` repeats the 729QP singular-value calculation for each exact failed Tet10, **virtually** replacing only selected midside nodes by straight-edge midpoints in an in-memory copy. It never writes or alters a `.msh`; virtual pore-edge straightening is **not CAD-valid** and cannot be used for physical FEM.

| Failed Tet10 | Original min σ3/σ1 | Virtual flatten three pore-surface edges | Factor | Virtual flatten three remaining edges |
|---|---:|---:|---:|---:|
| R1 / 13346 | 0.05962 | 0.16431 | ×2.76 | 0.05962 |
| R1 / 9035 | 0.09415 | 0.22251 | ×2.36 | 0.09415 |
| R2 / 9478 | 0.04483 | 0.15162 | **×3.38** | 0.04483 |

This isolates **curved pore-surface edge midnodes**, not straight off-surface edges, as the dominant source of the sampled singular-value deterioration in these three tets. It does not establish that Gmsh's canonical `minSJ` would meet threshold in a legal CAD-conforming alternative, nor prove that the issue is due to incorrect midnode placement: the positions may accurately represent the sphere but require a different adjacent fourth-vertex geometry, surface triangle size/shape, or high-order optimization strategy. A geometry-conforming next design must preserve the sphere.

Machine-readable per-edge data: `p10nh_m13_virtual_ablation/P10NH_M13_BAD_TET10_MIDSIDE_VIRTUAL_ABLATION.json`. **Still no M13 R3 mesh/FEM; R1/R2 one-shot markers remain consumed.**
