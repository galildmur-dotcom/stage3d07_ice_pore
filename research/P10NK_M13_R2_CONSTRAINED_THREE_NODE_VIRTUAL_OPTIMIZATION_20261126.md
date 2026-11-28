# P10NK — constrained three-node near-pore virtual optimization on M13 R2

2026-11-26. **Source-only; no Gmsh, no mesh write, no FEM, no marker use.** The experiment uses exact M13 R2 SHA `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`, read-only canonical R2 bad-element locator and inherited quadratic Tet10 729-QP shape derivatives. It extends the one-node P10NJ study, without replacing any historical evidence.

Three interior nodes were chosen based on proximity/shared-edge incidence: pivot **8680** and its nearby interior nodes **8681** and **9115**. Their small radial displacements are independent in a 4×3×3 grid (36 variants). All incident Tet10 to *any* of these corners were included: **67 Tet10**, **47 changed global nodes** (3 corner nodes plus their incident edge midside nodes), and no modified node belongs to a pore-surface Tri6. Explicit closure checks verified that no outside element references a modified midside/corner node, and all shared midside displacements agree across tets. Therefore every trial is nodally conforming on this complete vertex-star union, and the spherical pore surface remains fixed.

Acceptance for source-only screening: positive sampled detJ at all 729 integration points in **every** affected Tet10 and individual curved volume ratios within [0.9,1.1] versus original M13 R2. 27 of 36 candidates meet these constraints. This is *not* the canonical Gmsh D031 threshold; sample positivity is not a proof between samples, and canonical minSICN/minSJ must be evaluated before any physical run.

| Candidate displacement (mm) for nodes 8680 / 8681 / 9115 | Worst min σ3/σ1 over 67 Tet10 | Improvement | Individual curved volume ratio range | Count of elements with decreased min σ3/σ1 | Worst neighbor relative decrease |
|---|---:|---:|---:|---:|---:|
| 0 / 0 / 0 | 0.044827 | — | 1.000–1.000 | 0 | 0% |
| +0.010 / 0 / 0 | 0.051984 | **+16.0%** | 0.9313–1.0729 | 14 | 7.66% |
| **+0.010 / +0.005 / +0.005** | **0.051984** | **+16.0%** | **0.9313–1.0721** | 36 | **4.73%** |

The sum of curved volumes over the affected region is preserved numerically (ratio 1.0) for these shared-node conforming perturbations, and the worst Tet10 remains tag 9478 while its geometry proxy improves. Moving two neighbors does **not** further improve the worst value, but reduces the maximum fractional harm to any other element from 7.66% to 4.73%, at the expense of spreading smaller harm to more elements (36 instead of 14). This is a genuine **minimax-vs-distribution** tradeoff, not clear dominance of a unique optimum.

**Scientific conclusion:** the local curved geometry has an accessible, CAD-surface-fixed, topologically conforming perturbation direction that improves the worst sampled singular-value ratio without large individual element-volume changes. This is considerably more informative than repeated attempts to reduce the size field around a bad element. Nevertheless **neither the global mesh nor the canonical Gmsh quality metrics have been changed or validated**. Preserve R1/R2 markers and do not start M13 R3/FEM based on this proxy alone.

Next step should validate an *independent native Gmsh quality evaluation on a distinct diagnostic copy of the modified M13 R2 node coordinates* (never overwrite the user evidence or source mesh), including all minSICN/minSJ/gamma/minDetJac and physical tags. Creating this copy **is a new mesh-file write**, even though no Gmsh remeshing or physical FEM is intended; it therefore needs its own explicitly described diagnostic scope and safeguards. Such a diagnostic copy is not automatically an accepted M13 R3 and must not consume a physical FEM marker; any final geometry must still pass D029/D031 and distinct mesh-acceptance rules. Before that, a separate preflight should ensure exact application of shared-node displacements to all 47 global nodes and prohibit moves of any pore Tri6 node. If no native mesh-quality measurement is authorized, continue source-only optimization.

Full 36-candidate reproducible data: `p10nk_m13_three_nodes/P10NK_M13_R2_THREE_NODE_CONSTRAINED_729QP.json`; source: `research/tools/p10nk_m13_r2_three_node_constrained_virtual_search.py`.
