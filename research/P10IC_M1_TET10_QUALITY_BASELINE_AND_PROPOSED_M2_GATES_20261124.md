# P10IC — read-only M1 Tet10 quality baseline and proposed pre-registered M2 gates, 24.11.2026

**Status:** source-only quantitative baseline DONE; proposed M2 numerical thresholds below **NOT YET RATIFIED**. No new 1D/2D/3D Gmsh mesh generation, no FEM, no new M2, no P10IB rerun.

## Exact pinned input and reproducibility

- Original P10GT HXT10 M1 MSH SHA256 `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`; independent 9623 physical ICE_VOLUME Tet10, 176 PORE_WALL Tri6, physical surface groups tags2–9.
- Gmsh4.15.2 Python `getElementQualities`, plus independent P2 Tet10 Jacobian and volume integration at **27 / 343 / 729** tensor-Duffy points. Reproducible scripts [quality](proposals/P10IC_TET10_QUALITY_BASELINE_20261124/p10ic_tet10_quality_audit.py) and [independent quadrature](proposals/P10IC_TET10_QUALITY_BASELINE_20261124/p10hv_independent_scan.py), using Python numpy/gmsh4.15.2. Command: `python p10ic_tet10_quality_audit.py P10GT_HXT10.msh` with scripts in one folder, `OPENBLAS_NUM_THREADS=1` optional.
- Program is **read only** and sets no GO: any candidate path must separately pass exact CAD/physical-group provenance and user-confirmed numeric quality gates.

## Measured accepted M1 baseline (all 9623 Tet10)

| Gmsh quality | min | p01 | p05 | median | count≤0 |
|---|---:|---:|---:|---:|---:|
| minSICN | **.28380132** | .39565238 | .49629416 | .80300179 | 0 |
| minSJ | **.57203605** | .76464453 | .87227831 | 1.00000000 | 0 |
| gamma | **.24819827** | .37622595 | .46686068 | .76828589 | 0 |
| minDetJac (m³) | **1.8546799e−11** | 4.6241121e−11 | 8.0425543e−11 | 1.2992435e−9 | 0 |

Independent sampled curved P2 detJ minima: 27QP `2.28684696e−11`, 343QP `1.96200380e−11`, 729QP `1.92252376e−11` m³; all positive at inspected QP. Total CAD ice-volume closure at 729QP relative `+1.2209341e−8`. Max relative 343-vs-729 discrepancy of supported `Veff` regions `0.44884%`. Paired physical near-highκ north/south (0–0.5mm, |μ|≥.8): `N_eff=58.320/76.509`; baseline `Veff=1.70759e−11/1.30165e−11` m³.

**Important:** adaptive `minDetJac` Gmsh and 729 sample test are complementary but finite sampling alone is not a mathematical proof of positive Jacobian everywhere. Need independent checker and retain high-order quality analysis.

## What does not belong in a hard gate under D-030

Diagnostic adjacent *curved-volume* ratios of M1: all 18663 internal pairs p95=2.495, max=6.118, 57.21% >1.25. In near-polar pairs (n297) p95=2.181, max=2.801. **These are Veff ratios, not h ratios**, and the histogram only describes the mesh; no limit is imposed. Surface P10IB neighbour **linear** h-ratio p95=1.3399 (M1 1.2387) likewise does not block the next step. Never compare raw q_V with q_h as if the same measure.

## Proposed numerical gates for **scientific approval before** a new M2 3D experiment

The following are deliberately conservative *working proposals*, calibrated against actual M1 minima (rather than adopted as universal FEM theorems):

1. Every curved Tet10: `minSICN>=0.20` and `minSJ>=0.40`; positive independently sampled curved detJ on 27/343/729 and Gmsh `minDetJac>0` (check for finite values, no nonpositive elements). These floors are about 70% of accepted M1 observed worst normalized quality; it remains to justify acceptability for solver/shape adjoint.
2. Auxiliary corner-shape `gamma>=0.15`, which may diagnose slivers but does not replace the curved tests. CAD / sphere / B6 / physical surfaces1–9 / shared faces and pore-wall curved geometry must match original.
3. Total 729QP integrated ICE volume closure `|Vmesh/Vcad−1|<=1e−6` (M1 actual `1.22e−8`). For aggregated supported highκ north/south physical regions, propose `N_eff>=30` each and 343→729 regional Veff change ≤1%; for narrower signed 18 zones report coverage/N_eff rather than falsely enforce all 18.
4. Publish both distinct statuses: `GEOMETRY_QUALITY_GO` based on 3D curved quality, `ADAPTATION_TARGET_STATUS` based on D-029 measured highκ `Veff(M2)/Veff(M1)∈[.50,.75]`, north/south separately. Target miss is not automatically bad geometry. **No q threshold.**
5. All run resources/one-shot markers pre-registered and new source SHA pinned. No FEM from mesh-only GO. Solver conditioning and physical convergence follow in separate experiment.

**Rationale for pending approval:** hard `minSICN/minSJ/gamma` numbers are proposed, not yet user-approved; their direct solver relevance and adaptive `minDetJac` semantics should be checked before heavy M2. If researcher rejects numbers, preserve measured baseline and derive alternate gates without rerunning P10IB.

## Next action

Ask researcher to approve/adjust numerical quality gates; then develop a **new, bounded, isolated** M2 3D mesh-only one-click package from original CAD and P10IB highκ 10-point surface mechanism, with original mesh-size callback and continuous 3D field. Do not transfer the P10IB 2D success to an automatic 3D GO. Physical FEM only following independent geometry QA and a separate resource decision. Revisit proper physics-based κ after full M0/M1 derivative error data; current P10HA κ is provisional.
