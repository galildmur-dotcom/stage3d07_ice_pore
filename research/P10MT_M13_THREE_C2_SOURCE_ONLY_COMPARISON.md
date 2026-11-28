# P10MT — M13: three source-only C2 adaptation hypotheses (A/B/C)

Status: **SOURCE ONLY**. No M13 Gmsh generation, no M13 D029/D031, no FEM, no marker use. Branch: `research/p10bb-w5b2-20261118`.

## Evidence and research question

P10MS compares the common 1200 spatial bins between M11 and M12. Of these, the 20% targeted most strongly by the M12 field reduced local integrated L1 by 17.39%, whereas the other 80% increased it by 24.03%; net L1 decreased just 0.96%. A smoother, less concentrated M13 source may therefore be worth testing, but this observation does **not** establish the cause of the error nor establish FEM convergence.

For each bin define `e = new_L1`, `l = late_new_actual`, `g = max(new_L1 - old_L1, 0)`, and `N(x)=x/max(x)` across 1200 bins. `p` is one at the north/south extreme angular bin and zero elsewhere. Define three **distinct prospective source hypotheses**:

* **A (residual continuation)**: `sA = (0.40 N(e) + 0.60 N(l)) (1+0.20 p)`.
* **B (growth awareness)**: `sB = (0.45 N(e) + 0.25 N(l) + 0.30 N(g)) (1+0.20 p)`.
* **C (balanced coverage)**: `sC = (0.40 N(e) + 0.25 N(l) + 0.20 N(g) + 0.15) (1+0.08 p)`.

The coefficients are **engineering test settings, not inferred physical constants**. In particular the 0.15 floor in C intentionally tests coverage against local growth, at the expense of potentially many more elements. The `+0.20 p` in A/B echoes previous polar soft priority; C reduces this extra bias because the existing independently prescribed C2 polar collar is already retained.

## Result: reconstructed source-center κ (no actual mesh)

`κ` uses the existing positive compact Wendland C2 field and quintic smoothstep, with the P10KP C2 polar-core plateau. Hypothetical `Veff_M13/Veff_M12 = 1 - 0.20 κ`, which is only a size-law proxy and **not a measured Tet10 volume ratio**. The column `mean κ` is unweighted across 1200 source centers; other columns are L1- or positive-growth-weighted κ.

| Hypothesis | Mean κ | L1-weighted κ | Positive-growth-weighted κ | Middle angular bins mean κ | Old unselected 80% mean κ | Source-center nominal Veff min–max |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.1750 | 0.4431 | 0.4405 | 0.0805 | 0.1086 | 0.8000–1.0000 |
| B | 0.1774 | 0.4483 | 0.4516 | 0.0829 | 0.1112 | 0.8000–1.0000 |
| C | 0.2813 | 0.5392 | 0.5527 | 0.1969 | 0.2181 | 0.8000–0.9846 |

North extreme-angular mean κ = A 0.5538 / B 0.5575 / C 0.6241; south = 0.5524 / 0.5532 / 0.6135. Polar near-wall bins (`radial_bin≤2` and `mu_bin ∈ {0,9}`) retain κ=1 in **all** three variants. C is not a pure polar over-refinement proposal: its broadening is especially visible at middle latitudes and in formerly unselected regions. B only modestly differs from A after interpolation.

## Interpretation and provisional choice

**Prefer C as the next controlled mesh-design hypothesis**, but do **not** approve its full 0.15 floor for production based solely on these metrics. First run the dedicated M13 geometry-only one-shot preflight / D029 / D031 quality gate, comparing element-count and actual shell/polar volume ratios against M12. A is the conservative control and B is a low-cost sensitivity control. C risks excessive total Tet10 count because even minimum source-center κ exceeds zero; this risk is intentionally measurable in a future M13 geometry-only stage. If the budget is exceeded, reduce the C floor in a *new, explicitly versioned source-only* candidate before meshing, not via retry of the same M13 attempt.

## Reproducibility and limits

Run `python research/tools/p10mt_m13_three_c2_source_only_design.py` from the repository root only when `p10mt_m13_source_only/` does not already exist (the script refuses to overwrite). Inputs: `p10ms_m12_diagnostic/P10MS_1200_BIN_SOURCE_VS_4D_OUTCOME.csv`, `p10mk_m12_source/P10MK_M12_M11_MINUS_M10_REAL_SIGNED4D_1200_BINS.csv` for M3 QP, and `p10mf_package_final/P10HA_SPATIAL_KAPPA_1200_BINS.csv` for bin centers. Machine-readable results and source hashes: `p10mt_m13_source_only/P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json` and three variant CSVs.

All three pass sampled exact azimuth seam equality at tolerance 1e-10 and pole repeatability at 1e-12. Analytic C2 comes from the inherited positive Wendland kernel, S5 cutoff and C2 polar plateau; **sampling is not a proof of C2 across the full physical mesh geometry**. No M13 solver output, convergence claim, D029 probe or D031 volume distribution exists here. The next action is an explicitly separate geometry-only assessment, not a FEM run.
