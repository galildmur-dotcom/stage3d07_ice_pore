# P10IS — real P10IR M3 full4D acceptance and independently compared M2/M3, 24.11.2026

## Evidence and immutable run identity

User supplied `P10IR_M3_FIRST_FULL4D_EVIDENCE.zip` containing `P10IR_MANIFEST.json`, `P10IR_NATIVE_LOG.txt` and all five 4D CSV files. Native manifest records `P10IR_M3_REAL_FULL4D_PASS`, exit0, one-shot marker consumed at `G:\ildar\Stage3D07\LOCAL_RUNS\P10IR_M3_ONE_SHOT_MARKERS\M3_R_DT25_STEPS36_3d6ce765dced7d14.json`, **one FEM attempt**; wall **902.316719 seconds**, polled peak private **2,150,174,720 bytes** (2.002GiB), limit 8GiB, stop_reason empty. Solver EXE SHA `9cbe31f74346001851d54616837340422cc5c0629fcdfae1f5164004d5cc46f5`; approved M3 mesh SHA `3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a`. M3 14,653 nodes, 10,063 Tet10, 262 pore Tri6, curved27QP nonpositive=0, canonical surface tags2..9. Parameters EXACT parity with M2 P10IJ: R/EDV_VAR/ξ0/B6 5mm/900s/dt25/36steps/4threads; fresh direct+analytic same-mesh adjoint; no FD geometry. History SHA `5d997bd08ef1890bf9beebd6653d562d2af2130f63cea92b851d56f84538ce2c`. History itself excluded from evidence, as intended.

Independent read-only re-run of original `P10GY_temporal_series.independent_time_audit` against returned CSV (not trusting manifest) PASS: 43,236 rows/36 steps/1200 bins+Robin each, exact bin uniqueness, source geometry, complete 27-point mechanical and 64-point thermal support per Tet10 per step, correct times, closure of mechanical/thermal rows/steps/global analytic adjoint. No new FEM was run by reviewer.

## Side-by-side direct objectives and full analytic radius derivatives

| Functional | M2 objective | M3 objective | Δobjective % (signed baseline) | M2 D_R | M3 D_R | Δ D_R % |
|---|---:|---:|---:|---:|---:|---:|
| j6 | .0021724429966990095 | .0021722560195199195 | −.008607 | .025871400912997677 | .025827363799795382 | −.170215 |
| jpeak | .04802054026941494 | .04774387542248166 | −.576139 | 2.5598510250834945 | 2.473214870917888 | −3.384422 |
| jen | .0008248993824586126 | .0008248215369034457 | −.009437 | .01546708780281385 | .01547030975863825 | +.020831 |

The criterion for full spatial convergence has NOT been met merely because two global functionals look stable. The global jpeak radius derivative is ~3.38% lower on M3.

## M2/M3 signed 4D components for jpeak

Read-only independently re-aggregated M2 and M3 across **identical 43,236 physical spatiotemporal bin keys**, exact matching radial and angular bounds; contributor values add to the adjoint objective.

| Contribution | M2 | M3 | ΔM3−M2 |
|---|---:|---:|---:|
| mechanical explicit | −13.625454301975080 | −11.616555391311971 | +2.008898910663109 |
| mechanical equilibrium | +10.001428570997493 | +9.356754821043990 | −.644673749953503 |
| mechanical history | +6.111107553415890 | +4.663146554819881 | −1.447960998596009 |
| thermal mass | +.001224939584942 | +.001786006390976 | +.000561066806035 |
| thermal diffusion | +.071544263060234 | +.068082879974991 | −.003461383085243 |
| thermal Robin | 0 | 0 | 0 |
| total | **+2.559851025083480** | **+2.473214870917867** | **−.086636154165613** |

Mechanical signed total 2.487081822438304→2.403345984551899 (−3.367%); thermal 0.072769202645176→0.069868886365968 (−3.986%). Individual signed components vary more because of cancellation. Sum across all bin-times of absolute total per-bin differences **4.958849816455888**, versus the signed net shift only **.086636154165613** (cancellation factor **57.24**). A 3.38% global difference is therefore inadequate proof of robust local convergence.

## Pole-specific fixed spatial bins, all 36 steps

Using identical source geometry bins, latitude criterion polar cap θ≤acos(.8) in north, θ≥acos(−.8) in south; near wall first 0.5mm. These are signed **integrated derivative contributions**, NOT κ, not local stress maxima and not a direct estimator of mesh error norms.

| Region | M2 total signed jpeak D_R contribution | M3 | Δ | relative reduction of absolute magnitude |
|---|---:|---:|---:|---:|
| North polar cap and d≤0.5mm | −2.572704811738712 | −1.849557900150468 | +.723146911588244 | 28.108% |
| South polar cap and d≤0.5mm | −1.847041960687414 | −1.321921035201413 | +.525120925486002 | 28.430% |
| Whole near-wall d≤0.1mm | −4.698240129339053 | −3.206772074978582 | +1.491468054360471 | 31.745% |
| Whole near-wall d≤0.5mm | −4.243445769539960 | −3.122037878723904 | +1.121407890816056 | 26.427% |

These show **remaining substantial sensitivity in the very poles targeted for M3 refinement**. Note that the polar d≤0.5mm figures are only signed sums, potentially with further cancellation; do not interpret their ~28% reduction as a positive accuracy metric. Late steps 34–36 individually differ by +.1411, +.2119, +.1398 in signed jpeak D_R contribution; time-resolved investigation is still useful even though the physical time grids agree.

## Scientific verdict and proposed next gate

**P10IR M3 REAL FULL4D PASS** (valid computed solution and internally closed adjoint on the accepted geometry). **M2→M3 GLOBAL SPATIAL CONVERGENCE NOT ESTABLISHED**, most notably polar local jpeak derivative and individual sign-cancelling history/mechanical contributions. Do not claim M3 converged or replace M2 with M3 final paper data. Do not regenerate M2/M3, repeat consumed one-shots, or start M4 FEM without a separate source-only plan.

Next recommended stage **P10IT source-only physical-error calibration for M4**: use actual signed 4D M2/M3 source bins and fixed geometry on the same 900s/36 steps; form a non-negative local change indicator (e.g. robust bin-wise absolute signed Δ contributions with near-polar support) that does not erase cancellation, distinguish time steps and north/south, compare with the earlier P10IN C² κ (βthermal=.10), enforce spatial smoothing and physical-volume reduction target 25–50% in well-supported maximum κ regions, preserve CAD rotation/HXT10 quality D031 and no-neighbour-q hard gate D030. Before another native Gmsh/FEM present source-only map/design and expected resource caps to researcher for approval.
