# P10BD — H2 temporal sensitivity of the local shape derivative

Date of evidence: 2026-11-18. Project: Stage3D07 — freshwater ice with a spherical pore.

## Status and provenance

**Observed campaign marker:** `P10BD_H2_FULL_CAMPAIGN_OK` in the supplied
`RESULT.txt`, from local run `P10BD_H2_LOGS_20261118_145403`.

- Mesh: `G:\ildar\Stage3D07\P10M_MESHES\H2.msh` in each of the three run paths.
- Model: EDV_VAR; mode `R`; regularized `jpeak`; analytic Tet10 geometry partials.
- Fixed physical horizon: 900 s; steps/dt pairs (6, 150 s), (12, 75 s), (18, 50 s).
- The runner was designed to solve forward and adjoint on the *same mesh* within
  each full run, in accordance with methodological decision P10AO.
- Available evidence: campaign summary, integrated polar-by-radial cells
  (200 rows), radial aggregate (20 rows), and protocol `RESULT.txt`.
- **Not supplied:** individual `RUN_MANIFEST.json` files, detailed execution
  logs, full time-step QP exports, temperature profiles. The source SHA and
  per-run parameter hashes have therefore not been independently audited.

This is reported computational evidence, **not** a proof of spatial convergence.
Research status remains `SPATIAL_CONVERGENCE_NOT_PROVEN`.

## Global results, independent re-check from supplied CSV

| Quantity | dt=150 s | dt=75 s | dt=50 s |
| --- | ---: | ---: | ---: |
| `jpeak` | 0.047495362731 | 0.047531402079 | 0.047593195560 |
| Global mechanical `D_R jpeak` | 2.272853790148 | 2.263565305441 | 2.264034382380 |
| Global thermal `D_R jpeak` | 0.066782474417 | 0.069661715002 | 0.070467838120 |
| Global total `D_R jpeak` | 2.339636264565 | 2.333227020443 | 2.334502220500 |
| Mechanical sum in 0.020–0.100 mm | -1.313825465861 | -1.303407771319 | -1.302180771441 |

Relative to dt=50 s, the full total differs by +0.219920% at 150 s and
-0.054624% at 75 s. The thermal partial differs by -5.229852% and -1.143959%
respectively. The global total is **nonmonotonic** across the three dt values.

Worst reported mechanical equilibrium relative residual = 1.020656e-7;
worst thermal equilibrium relative residual = 4.963399e-11.

## Full-history spatially localized mechanical term

The exported cells partition only the mechanical derivative. They are
**contributions to the derivative of the history-dependent functional**,
not independent snapshot functionals at each physical time.

Physical cells: `s=r-R=0.020–0.050` and `0.050–0.100 mm`, 10 radial subbins
per shell, 10 equal-area `mu=cos(theta)` bands, azimuth `phi` integrated.
Every one of the 200 cells has at least one quadrature point (14–128 QPs).

The independent recalculation recovered each published near-wall total by
summation of the 200 cell contributions with discrepancy below 1e-9.

Define `L1_reference=sum_i |C_50,i| = 1.3259856521391074` and
`E_L1(a,b)=sum_i |C_a,i-C_b,i|/L1_reference`.

| Pair | Sum of local absolute differences | `E_L1` |
| --- | ---: | ---: |
| dt=150 vs 75 | 0.079013493221 | 5.958850% |
| dt=75 vs 50 | 0.024085556838 | 1.816427% |
| dt=150 vs 50 | 0.103097386538 | 7.775151% |

The ratio of successive local `L1` changes is 3.280534. This is compatible
with an approximately first-order temporal pattern for the step ratios used,
but **does not establish an asymptotic convergence rate**. In 194/200 cells,
the signed contributions change monotonically between 150, 75 and 50 s.

The near-wall *signed* difference between 150 and 50 s is -0.01164469442,
so the absolute-sum / absolute-net cancellation factor is 8.8536.
For 75 vs 50 s the factor is 19.6296. A small net change can hide much
larger compensating local changes.

### Polar concentration and strongest cell

- The two extreme mu bands, [-1,-0.8] and [0.8,1], contain 94.1956% of
  the dt=150-vs-50 absolute cell differences.
- Those same bands contain 88.8792% of the dt=50 absolute contribution
  baseline: concentration of differences alone does **not** prove an
  unusually high *relative* error at the poles.
- Largest single absolute difference occurs at
  `s=0.029–0.032 mm`, `mu=0.8–1`:
  `C_150-C_50 = -0.0120129135405` per metre of radius perturbation.

### Radial sign changes sensitive to dt

| Distance from wall | dt=150 | dt=75 | dt=50 |
| --- | ---: | ---: | ---: |
| 0.085–0.090 mm | +0.006538317 | +0.001156011 | -0.000576469 |
| 0.095–0.100 mm | +0.001503116 | -0.002082923 | -0.003254165 |

These sign changes indicate sensitivity of some weak radial features to dt.
The present quasistatic mechanical model has **no inertial elastic waves**.
Transient Fourier heat diffusion and EDV rheology can influence spatial
gradients, but the data do **not** identify a propagating physical wave.
An attribution requires matched radial/polar `T`, `dT/dr`, and mechanical
diagnostics across the same physical times.

## Scientific interpretation and research decision

1. Time discretization materially affects the *local* shape-derivative
   distribution, even where the full derivative differs by only ~0.22%.
2. A mesh-refinement indicator based on intermesh local differences at
   dt=150 s may be contaminated by temporal error. Do not begin adaptive
   M1/M2/M3 refinement on that basis yet.
3. Cell differences at distinct dt values are **diagnostics**, not a proven
   error against the unknown continuous-time limit.
4. The distribution of a volumetric shape derivative also depends on the
   chosen interior extension of the boundary velocity field. Future mesh
   comparisons must preserve that extension and compare common physical cells.
5. Decision: run an additional consistent H2 full-history experiment at
   dt=25 s, steps=36, horizon=900 s (proposed stage P10BE), then compare
   50/25, temporal `L1` reduction, and radial sign structure. Proposed time
   on the user's i7-7700K / four threads: about 2.5–4 h; this is an estimate.
6. Only after temporal uncertainty is controlled should the adaptive spatial
   series M1/M2/M3 be used to assess shape-derivative convergence.

## Attached evidence and SHA-256 of original user uploads

- `RESULT.txt` (uploaded as `RESULT(3).txt`):
  `d077acf8d44f5826895a5c7cd999b535482aff7b9ebdecadf66b05d3dd70e3ea`
- `P10BD_TEMPORAL_SUMMARY.csv`:
  `de1c91ca4c7b7c0584e9866731a7eb749a23f52fe6d2d91fbda1d6bbb0aec4f5`
- `P10BD_RADIAL_TEMPORAL_COMPARE.csv`:
  `74c1ebc835edecd7ba22da1df3a845f809841562061f891f1853b53c50c41cd2`
- `P10BD_CELL_TEMPORAL_COMPARE.csv`:
  `63d74737b2bf3b9e1a6fed917485903673399a4e1dfa1a6e6b2e72baac49b591`

The above scientific findings may be cited as numerical pilot evidence in
the manuscript only with the limitations and provenance stated here.
