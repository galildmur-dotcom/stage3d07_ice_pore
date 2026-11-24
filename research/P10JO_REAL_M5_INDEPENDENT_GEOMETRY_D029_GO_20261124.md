# P10JO — independent real M5 geometry and D029 adaptation audit (2026-11-24)

## Evidence identity and one-shot provenance

User-supplied private `P10JN_R1_M5_UNVERIFIED_EVIDENCE.zip` contains the local/profile consumed marker, guard JSON, Gmsh log, worker JSON and **real M5 Tet10 mesh**. Exact candidate SHA256 `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`. P10JN Windows Gmsh4.15.2 native mesh-only exit0, wall 14.016s (worker meshing 12.8233s), 1 mesh generation attempt, **FEM_attempts=0**, accepted_M5=false was the deliberate pre-audit status. P10JN R1 one-shot consumed; **never rerun R1**. Original accepted M4 SHA256 `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`.

## D031: independent ALL curved Tet10 geometry GO

Read-only independent audit using `p10ic_tet10_quality_audit.py` and native Gmsh getElementQualities; independent curved isoparametric Gauss 27/343/729 QP. M5: 10,826 Tet10; 386 pore Tri6; physical surface tags [2,3,4,5,6,7,8,9] present. MinGmsh SICN **0.2133043815483 ≥ .20**, minSJ **0.4515527104406 ≥ .40**, gamma **0.1953846025110 ≥ .15**; Gmsh minDetJac **1.8169281068646333e−12 >0**, no nonpositive elements. Independent min detJ at [27,343,729] QP [1.8192158971589525e−12, 1.817220823850317e−12, 1.8170951671085506e−12], all positive. CAD volume closure relative at 729QP **9.871955697349222e−9**, ≤1e−6. Maximum 343→729 relative Veff difference over supported regions .005812526 (diagnostic). Neighbour volume ratio diagnostic global p95 2.5002, max 11.5666; polar p95 2.5747, max 5.3623; **not a hard rejection under D030**.

**D031 result: PASS, M5 geometry GO.** Do not conflate geometry with physical convergence.

## D029: independent actual M5/M4 N/S polar Veff PASS

Same independent MSH2 Tet10 reader / physical CAD regions d≤.5mm, |μ|≥.8, independent 729QP (crosschecked 343QP). Accepted M4 baseline verified with SHA.

| Region | M4 Veff729 m³ | M5 Veff729 m³ | M5/M4 729 | M5/M4 343 | Reduction % | M4 Neff | M5 Neff | D029 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| N | 4.6000692068178764e−12 | 2.8181925371808008e−12 | .6126413343964234 | .6130346264777305 | 38.73586656035766 | 216.05094342047963 | 352.9415205509003 | PASS |
| S | 3.5675151777455907e−12 | 2.259408361813149e−12 | .6333283109508535 | .6335351904753588 | 36.66716890491465 | 279.1801501196662 | 440.15898209325826 | PASS |

Both 729QP ratios in preregistered [.50,.75], Neff≥30. 343→729 ratio drift N≈.0642%, S≈.0327%. **D029 result: PASS, M5 physical polar refinement GO.**

## Status and obligatory next stage

**Accepted M5 as geometry / adaptation only** (not yet physically converged). No FEM has been performed on M5. M4 physical derivative `D_R j_peak=+2.388080130362648 m^-1`, M3 `+2.4732148709178685 m^-1`, M3→M4 global signed `−0.08513474055522016 m^-1` vs M2→M3 `−0.08663615416561332`; therefore spatial convergence **NOT established**. Next P10JP: prepare independent **new** guarded Windows M5 FEM full signed4D run on this exact accepted SHA, regime R/EDV_VAR/ξ0/B6 5mm, **36×25s**, same-mesh forward/analytic adjoint, 4 threads, pinned sources, ≤30s all-phase user-visible heartbeats including silent native solver, source-only negative tests, one-shot unique M5 FEM marker; user executes locally and returns evidence. No repeat of consumed M4 FEM or M5 mesh marker; no hypothetical FEM result. Then independent signed 4D QA, D_R peak M5−M4 and spatial convergence check. Large/private raw mesh, Gmsh logs and 4D rows remain out of public GitHub.
