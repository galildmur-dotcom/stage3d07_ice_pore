# P10IP — independent P10IO R2 M3 geometry acceptance (24.11.2026)

## Provenance and bounded execution

User-supplied `P10IO_R2_M3_UNVERIFIED_EVIDENCE.zip`, containing one-shot marker, guard/worker JSON, Gmsh log, and `P10IO_M3_CANDIDATE_UNVERIFIED.msh`. Guard `WORKER_FINISHED`, exit 0, wall 7.093 s, polled peak private bytes 40,120,320, `new_mesh_3D_attempts=1`, `FEM_attempts=0`, `one_shot_consumed=true`; Gmsh 4.15.2 generation 5.9544 s. Worker mesh SHA-256 independently confirmed `3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a`. Rotated CAD SHA `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`. 10,063 Tet10, 262 pore Tri6, 10 embedded pore CAD points; physical tags 2–9. No Gmsh mesh generation, marker reuse, or FEM in independent review.

Independent reviewer used previously archived read-only `p10ic_tet10_quality_audit.py` and `p10hv_independent_scan.py`, with installed Python Gmsh 4.15.2 and numpy. Both original M2 and supplied M3 raw .msh were audited afresh, with Gmsh per-element curved qualities and independent Tet10 curved quadrature 27/343/729 QP; no M3 modification.

## D-031 geometric gate

| Gate | Approved threshold | Observed M3 | Status |
|---|---:|---:|---|
| Tet10 minSICN | ≥0.20 | 0.2628032578 | PASS |
| Tet10 minSJ | ≥0.40 | 0.4275135257 | PASS |
| Tet10 gamma | ≥0.15 | 0.2315803460 | PASS |
| Gmsh minDetJac | >0 | 7.423846835e-12 | PASS |
| Independently sampled min detJ, 729QP | >0 | 7.477254280e-12 | PASS |
| Positive independent min detJ 27/343/729 | all >0 | 7.76224e-12 / 7.50830e-12 / 7.47725e-12 | PASS |
| Relative CAD ice volume closure, 729QP | abs ≤1e-6 | 8.2914906e-9 | PASS |
| Max Veff 343→729 drift in supported patches | ≤1% | 0.2458087% | PASS |
| Regional supported N_eff | ≥30 each | N 140.0861, S 185.5945 | PASS |
| Physical surface tags | 2–9 | 2–9 | PASS |

Curved positivity was checked by Gmsh element quality and independent samples, not an interval-arithmetic proof of positivity at every point of each curved element.

## D-029 actual M3/M2 characteristic volume reduction

Exactly the same physical near-polar support regions as accepted P10IE M2: `d=0..0.5 mm`, `|μ|≥0.8`, north/south separated, containing all 10 source-bin centers with high κ; regions are **not** asserted to have uniformly κ≥0.8. These are supported spatial averages, **not** per-tetrahedron mandatory volume ratios.

| Region | M2 Veff m³ (729QP) | M3 Veff m³ (729QP) | M3/M2 | Actual volume decrease | Target 25–50% |
|---|---:|---:|---:|---:|---|
| N | 1.0286573110420831e-11 | 7.097563908023805e-12 | 0.6899658 | 31.0034% | PASS |
| S | 9.155496548304182e-12 | 5.363985695542142e-12 | 0.5858750 | 41.4125% | PASS |

M2 SHA-256 `d1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b`, M2 N_eff N 96.6986 / S 108.6407, M3 N_eff N 140.0861 / S 185.5945. The count of Tet10 grows only 2.27% because the adaptation is localized and not an indiscriminate global uniform refinement.

Neighbour-volume ratios remain **diagnostic not gates** per D-030: M3 all-neighbour p95 2.474, max 7.773; near-polar p95 2.551, max 4.220. These values are not a reason to reject otherwise passing curved Tet10.

## Decision and next scientific gate

**P10IP: M3 GEOMETRY_QUALITY_GO / D-029_TARGET_GO.** Release M3 as geometrically admissible for a separately authorized, bounded physical FEM pilot, pinned to SHA `3d6ce765...`. This is not a GO for full physical convergence, exact-gradient convergence, mesh-independent observables, or production. No M3 FEM was run in this stage. Next: source-only Windows FEM compatibility/guard preflight, pin solver and parameters against accepted M2 physical run, establish one-shot memory/time limits and progress messages, then request the researcher's approval before any first M3 physical run. Preserve consumed P10IO R1 and R2 markers, never re-run these one-shot mesh generations.

Evidence ZIP and raw candidate mesh remain user-supplied/private; GitHub records only their cryptographic identifiers and this reproducible textual audit, not the large binary mesh.
