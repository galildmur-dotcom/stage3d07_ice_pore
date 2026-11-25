# P10LE — signed4D mechanical component, polar and first-wall-layer diagnosis

**Status `PASS_DESCRIPTIVE_DIAGNOSIS_NO_FEM_NO_MESH`.** P10LD conclusion stands: M6→M9 asymptotic spatial convergence of `D_R jpeak` is not established. No M9 one-shot rerun, no M10 mesh or FEM attempted.

## Evidence and reproducibility

Full user-native ZIPs: M7 `P10KJ`, M8 `P10KV`, M9 `P10LC`. All three ZIP CRCs PASS; 43,236 keyed signed4D records per mesh, 43,200 volume cells, same 36×25-s time grid and 1,200 `(r,mu,phi)` bins. Each six-component total closes to row sum, and comparisons use exact bin/time keys. Reproducer `research/tools/p10le_component_polar_wall_diagnosis.py` and comprehensive QA `research/evidence/P10LE_COMPONENT_POLAR_WALL_DIAGNOSIS.json`.

## Main diagnostic: M8→M9 first 20 μm wall layer

| Partition | Signed Δ (m⁻¹) | L1 of cellwise Δ (m⁻¹) |
|---|---:|---:|
| Entire physical B6 volume | +0.011951238399 | 0.964211175178 |
| **0–20 μm from wall** (`radial_bin=0`) | **+0.150290623141** | **0.215760820071** |
| Outside first 20 μm | **−0.138339384742** | 0.748450355107 |
| 0–20 μm, extreme north μ-bin | +0.071134256514 | 0.084136016127 |
| 0–20 μm, extreme south μ-bin | +0.074803305999 | 0.092693426197 |
| 0–20 μm, other μ-bins | +0.004353060627 | 0.038931377746 |
| Steps 31–36, 0–20 μm | +0.129024084521 | 0.156670647162 |

First wall layer contributes **22.377% of full cellwise L1**, yet a **+0.150291 m⁻¹** signed increment, almost cancelled by **−0.138339 m⁻¹** in other radial layers. This is not a residual in one element; all 4,320 first-layer signed4D cells were independently summed. The first layer spans 0–0.02 mm and both extreme pole sectors contribute nearly equally to its signed change. Approximately **85.85%** of the first-layer signed delta (+0.129024 / +0.150291) arises in steps 31–36, demonstrating late-time localization.

### Mechanical component attribution in first wall layer

| Component Δ in 0–20 μm (m⁻¹) | M7→M8 | **M8→M9** |
|---|---:|---:|
| Mechanical explicit | +0.033399630 | **+0.196024673** |
| Mechanical equilibrium | −0.012220368 | **−0.022842855** |
| Mechanical history | −0.019895388 | **−0.022897048** |
| Thermal terms (combined) | small | +0.000005853 |
| **Total** | +0.001272069 | **+0.150290623** |

This identifies the **explicit mechanical derivative contribution in the closest wall layer** as the principal *descriptive source* of M8→M9 signed shift. It does **not** establish a coding error or continuum singularity. Equilibrium and history terms partially compensate it within the same layer; the full outer-volume compensation is mostly mechanical.

In extreme north first wall bin, explicit Δ=+0.1103810, equilibrium −0.0257166, history −0.0135261 m⁻¹. Extreme south: explicit Δ=+0.0829069, equilibrium **+0.0041351**, history −0.0122466 m⁻¹. The different equilibrium sign between the poles is a specific item for a subsequent 3D geometry derivative/adjoint source audit. Largest M8→M9 individual bin/time changes occur in steps 33–35 at `radial_bin` 0–1, extreme poles, and select φ-sectors; accompanying mechanical quadrature support differs between the meshes, so these are not elementwise matched solution samples.

## Did the previously designed P10KX adaptation field target the wrong places?

Using the 1,200-bin P10KX *predetermined* positive priority score and **subsequent** observed M8→M9 L1 (no post-hoc score retuning):

- Across spatial bins Pearson correlation **+0.653247**, Spearman **+0.742344**.
- Top 10% (120) source-priority bins contain **43.319%** of the observed M8→M9 absolute 4D mismatch.
- 75 of the top 120 source bins overlap the top 120 observed mismatch bins (random intersection expectation ≈12 under a uniform unordered null, for orientation only).

Thus the source field did prioritize spatial regions that remain influential. The failure of the global L1/L2 to decrease cannot be explained simply by a totally unrelated adaptation target. However these *observational correlations* do not verify whether the size field achieved optimal error reduction; more rigorous a posteriori error estimation would require different data.

## What is still unknown and next scientific step

1. The binned signed4D files group all *explicit* mechanical terms into `mech_explicit_per_m`. They cannot distinguish wall surface, transformed volume Jacobian, strain/normal geometric variation, or constitutive derivative subterms on their own. Therefore **do not infer the exact analytic source or a bug from this partition**.
2. P10LF should inspect the pinned `stage3d10fn_any_mesh_full4d`/analytic Tet10 shape derivative implementation and design a **read-only or source-only fine-grained explicit-term diagnostic** for the first 20 μm and poles. If new instrumented outputs require a full PDE solve, require a separately scoped, resource-budgeted one-shot approval; no automatic rerun of M9.
3. Before any M10 generation, test whether a finer breakdown can separate geometric explicit vs adjoint history/equilibrium terms and reveal a stable directional prediction. Keep the same R/EDV_VAR/ξ0/B6 5-mm physical model, exact signed4D partition and same-mesh analytic derivative.

Figure: `research/figures/P10LE_MECHANICAL_COMPONENTS_RADIAL_TIME.png`. Each panel aggregates the full 4D signed gradient difference over θ and φ; it shows where radial/time component compensation forms. It is not a pointwise stress plot or error bound.
