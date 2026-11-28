# P10IE — calibrated M2 accepted by geometry quality and supported D-029 physical-region target, 24.11.2026

## Experimental design, source and scope

**One new bounded local Linux 3D Gmsh4.15.2 HXT10 mesh-only candidate, no FEM.** Distinct P10IE one-shot marker consumed; no repeats of P10ID/P10IB. Original CAD GEO SHA `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`, accepted M1 MSH SHA `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`, P10HA/P10HB real M0/M1 signed 4D mechanical C2 κ, `α=.40`, ten already verified CAD-embedded pore points. Original P10ID control SHA `8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5`.

**New scientific information before native attempt:** exact physical `κ≥.8` 343/729QP support in first 0.5mm polar cone of M1 and P10ID is **<1 equivalent Tet10 per side** (M1 343QP north .88915, south .47514; 729QP north .84253, south .57745). 27/343/729 ratios were not stable; D-029 cannot reliably certify this vanishingly small threshold mask. Therefore calibration uses **fixed, adequately supported north/south physical patches** `d=0..0.5mm, |μ|≥.8` around the mechanical κ maxima, with their `N_eff` reported. All **10/10 source spatial bin centers with κ≥.8** lie inside these physical patches (7 northern, 3 southern; bins d≤0.1mm). Do not re-interpret the entire patch as uniformly κ≥.8.

Based on **actual curved Tet10 729QP** P10ID/M1 patch ratios north `.9484586`, south `.8868231`, propose midrange D-029 `q_target=.625`. The *hypothetical* faithful cube-law correction `m=(q_target/q_observed)^(1/3)` gives extra linear size factors north **.87020295**, south **.88991324**, i.e. log decreases `δ_N=.13902882`, `δ_S=.11663131`. This is empirical source-only calibration, **not** an expectation proven about native Gmsh.

Apply a positive bounded C¹ patch:
`h_new=lc(1-.40κ)^(1/3)exp[-δ_side S((|μ|-.6)/.2)(1-S((d_mm-.3)/.7))]`,
with `S(t)=clamp(t,0,1)^2(3-2clamp(t,0,1))`. Angular patch |μ|≥.8 full effect, radial full effect through d=.3mm then fades to zero at d=1mm. North/south differences vanish smoothly away from polar cones. Common size callback for surface and volume; original M1 CAD, ten seeds, Gmsh3D10, curved Tet10 remain unchanged.

## Native result

P10IE `P10IE_patch_3D_guard.py` status `WORKER_FINISHED`, exit0, local original-CAD native 3D generation **1.4307s** (machine-dependent); callback 26556, ghost inside-pore sizing queries11 safely projected; **9840 Tet10, 216 pore Tri6**. New unverified raw mesh SHA256 **`d1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b`**. Private raw MSH/evidence retained outside GitHub; no physical FEM. Source scripts [P10IE proposal](proposals/P10IE_CALIBRATED_ORIGINAL_CAD_M2_20261124) (worker, guard, calibration, highκ preflight, independent acceptance). Original previous one-shot markers untouched.

## Independent D-031 all-Tet10 quality gate

| Metric | Approved gate | P10IE observed | Verdict |
|---|---:|---:|---|
| minSICN all Tet10 | ≥.20 | **.283813** | PASS |
| minSJ all Tet10 | ≥.40 | **.444146** | PASS, modest margin |
| gamma all Tet10 | ≥.15 | **.235419** | PASS |
| Gmsh adaptive minDetJac | >0 | **1.01788e−11m³** | PASS |
| Independent curved min detJ 729QP | >0 | **1.02968e−11m³** | PASS |
| Relative CAD ice volume closure (729QP) | ≤1e−6 absolute | **9.28458e−9** | PASS |
| Supported regional Veff drift 343→729 | ≤1% | **.55935% max** | PASS |
| N_eff in supported near-polar N/S patches | ≥30 each | **96.70 / 108.64** | PASS |
| Physical surfaces | tags 2–9 | **2–9** | PASS |

All **10/10** programmed independent numerical gate checks PASS: **GEOMETRY_QUALITY_GO** under D-030/D-031. No unconditional claim of mathematically continuous positivity of every Tet10 Jacobian; the Gmsh-adaptive and sampled tests complement each other. Neighbour-size ratios are only diagnostic (D-030), not a hard stop.

## D-029 actual regional characteristic volume comparisons

Fixed physical regions, not matching individual elements, actual curved 343 and 729 QP, north and south shown separately:

| Physical region | M1 N_eff | P10IE N_eff | P10ID/M1 Veff | P10IE/M1 Veff 729QP | Reduction | D-029 target |
|---|---:|---:|---:|---:|---:|---|
| N: d0–0.5mm, abs(μ)≥.8 | 58.32 | **96.70** | .94846 | **.602401** | **39.76%** | PASS |
| S: d0–0.5mm, abs(μ)≥.8 | 76.51 | **108.64** | .88682 | **.703376** | **29.66%** | PASS |
| N: d0–0.1mm, abs(μ)≥.8 | 12.42 | 22.72 | .89957 | **.544803** | 45.52% | in band, LOW SUPPORT diagnostic |
| S: d0–0.1mm, abs(μ)≥.8 | 15.80 | 25.03 | .84869 | **.629934** | 37.01% | in band, LOW SUPPORT diagnostic |

The two **adequately supported** 0–0.5mm patches are in [0.50,0.75] and stable at 343→729: north q343 `.601931` vs q729 `.602401`, south `.703706` vs `.703376`. Narrow 0–0.1mm patches are reported but **not used as hard gates** because N_eff<30. Separate explicit `κ≥.8` mask is still under-supported in the coarser M1; its direct element-volume ratio must not be treated as robust. All ten source highκ centers nevertheless lie inside the supported anchor patches.

**Verdict:** P10IE produced the **first 3D M2 candidate whose curved Tet10 quality and independently measured D-029 targeted regional volume decrease both PASS** for defined sufficiently supported physical north/south neighborhoods of high mechanical κ. However this is **not** evidence of complete goal-oriented adaptation convergence: P10HA mechanical-only κ is an interim M0/M1 intermesh difference estimator for a limited R/EDV_VAR/ξ0 900s pilot, not a validated multigoal estimator for all j6/jpeak/jen and R/tz/y20; FEM on P10IE=0. No published physical forward/adjoint results on this mesh.

## Follow-up scientific gate

Next propose a resource-scoped physical direct+adjoint same-mesh pilot with exact P10IE mesh SHA, R/EDV_VAR/ξ0/B6 and 900s horizon, signed 4D mechanical+thermal, checks of exact analytic gradient and temporal error, comparing to original M1. Before any new FEM need version-pinned solver EXE, compatible mesh tags and DOF count, estimate wall/memory and researcher physical GO. Do not rerun consumed P10IE; avoid full GH3/multimodel heavy production before pilot.
