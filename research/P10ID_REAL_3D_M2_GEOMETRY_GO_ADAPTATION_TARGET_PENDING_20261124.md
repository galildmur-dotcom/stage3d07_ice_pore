# P10ID — one original-CAD Linux Gmsh4.15.2 3D M2 candidate, independent QA (24.11.2026)

## Status and exact scope

**One successful local Linux native 3D Tet10 mesh-only candidate** (not Windows replication, not FEM): P10ID new one-shot marker consumed. Original pinned P10GT HXT10 GEO SHA `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`, accepted M1 SHA `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`, P10HA C2 mechanical κ, `α=.40`, 10/10 original P10IB surface embedded seed points. All original CAD physical tag topology unchanged. Size callback common wall/3D, Gmsh HXT10 high-order optimization. Source files under [P10ID proposal](proposals/P10ID_M2_ORIGINAL_CAD_3D_20261124) (P10ID worker/guard and independent acceptance) depend on pinned P10IB R1 source bundle.

A first guard preflight found no locally importable gmsh due to wrong development environment path; **marker absent, native runs=0**. After correcting local Python environment, one guarded actual 3D attempt was completed: guard `WORKER_FINISHED` exit0, Tet10 count **9884**, pore Tri6 **200**, new MSH SHA256 **`8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5`**, mesh generation **1.0096 s**, callbacks **26649**, 13 nonphysical interior size queries safely clamped to sphere for κ evaluation, 0 FEM. Total native mesh nodes **14343** (Gmsh log); pore node radius maximum deviation **4.99e−18 m**; original ice CAD volume closure below. ZIP evidence private, intentionally **not publicly committed**. P10ID one-shot marker is consumed and must not be reset.

## D-031 independent quality against approved M1

| Metric | Pinned M1 | P10ID 3D candidate | Approved lower bound | Verdict |
|---|---:|---:|---:|---|
| Tet10 | 9623 | **9884** | n/a | report |
| pore Tri6 | 176 | **200** | n/a | report |
| minSICN min | .283801 | **.289574** | ≥.20 | PASS |
| minSJ min | .572036 | **.532343** | ≥.40 | PASS |
| gamma min | .248198 | **.267108** | ≥.15 | PASS |
| Gmsh `minDetJac` min (m³) | 1.85468e−11 | **1.81979e−11** | >0 | PASS |
| Independent 729QP min curved detJ (m³) | 1.92252e−11 | **1.87839e−11** | >0 | PASS |
| Relative CAD ice volume closure 729QP | +1.22093e−8 | **+1.06445e−8** | ≤1e−6 absolute | PASS |
| Max supported 343→729QP Veff relative drift | .44884% | **.39731%** | ≤1% | PASS |
| Near highκ north/south N_eff (0–0.5mm, |μ|≥.8) | 58.32/76.51 | **61.46/86.24** | ≥30 each | PASS |

All 10 independent approved numerical checks in `p10id_independent_acceptance.py` PASS; no nonpositive sampled curved Jacobian at 27/343/729QP, every element positive Gmsh adaptive minDetJac. **GEOMETRY_QUALITY_GO=YES for these checks**. This is not a formal mathematical certification of detJ positivity at every continuous point of a quadratic element, nor evidence of convergence of mechanics/adjoint. `q` is only diagnostic under D-030: 3D neighbour volume ratio all-pairs p95 M1 2.495→candidate 2.491 and max6.118→6.483; no q gate. Pore wall Tri6 actual shape and remaining physical groups need normal production QA on Windows before FEM.

## D-029 independent fixed physical 3D comparison (not per-element)

The following identical physical cap regions are computed from independent 729QP curved Tet10 integration, NOT arbitrary matching of element ids:

| Fixed physical region | M1 N_eff | Candidate N_eff | Veff(new)/Veff(M1) | Reduction |
|---|---:|---:|---:|---:|
| Pole N, d0–0.1mm, |μ|≥.8 | 12.42 | 13.96 | **.89957** | **10.04%** |
| Pole S, d0–0.1mm, |μ|≥.8 | 15.80 | 18.62 | **.84869** | **15.13%** |
| Pole N, d0–0.5mm, |μ|≥.8 | 58.32 | 61.46 | **.94846** | **5.15%** |
| Pole S, d0–0.5mm, |μ|≥.8 | 76.51 | 86.24 | **.88682** | **11.32%** |

These broad physical caps are **proxies** for priority regions, not identical to full source-C2 `κ≥.8` masks. The narrow first row cap has low N_eff, so not a sufficient standalone hard gate; N/S should not be aggregated to disguise disparity. Regardless, **the expected D-029 target actual −25…−50% is NOT DEMONSTRATED** with this candidate: measured reductions in all inspected north/south physical caps are much smaller. Surface size improvement alone did not translate into prescribed 3D characteristic volume shrinkage.

## Scientific verdict

- **Local original CAD 3D mesh-only generation SUCCESS.**
- **All approved measured Tet10 quality thresholds PASS**; geometry quality candidate accepted *as an element-quality check* under D-030.
- **D-029 adaptation-target status NOT DEMONSTRATED**; the actual target cannot be claimed for M2.
- **Physical convergence NOT TESTED; FEM=0** and no production M2 GO.
- The problem is no longer local 3D element shape: it is inadequate transfer of prescribed `κ` sizing / surface seeding to real near-wall 3D density. Next minimal step: source-only calibration of near-wall and volume sizing control against actual M1/P10ID; test a new 3D candidate in a distinct guard if warranted, with predeclared physical region support. Do not rerun P10ID, do not alter old M1 or declare an FEM GO prematurely.
