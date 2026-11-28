# P10KZ — real M9 R1 Gmsh mesh, independent D029 PASS / D031 partial

**Scientific gate: `D029_GO_ONLY_D031_CANONICAL_PENDING`. No M9 FEM and no full geometry GO.**

## User-native evidence

`P10KY_R1_M9_UNVERIFIED_EVIDENCE.zip`, SHA256 `6b8a8e171853aa53fb551851c3b2056b2f64af5fd38b7bbb208d714c833d0beb`, ZIP CRC PASS, five files. Windows Gmsh API 4.15.2, native worker exit 0, mesh generation 27.565 s, guard wall 29.028 s, peak monitored private 49,004,544 bytes, two 15-second native heartbeats. Persistent profile and local one-shot markers consumed: **NEVER REPEAT P10KY R1 M9**.

M9 candidate SHA256 `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58`: 19,236 nodes, 13,166 Tet10, 734 pore Tri6. Same CAD physical surface tags 2–9 and ten embedded seeds; M8 accepted baseline SHA256 `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d` (18,331 nodes, 12,546 Tet10, 648 pore Tri6). No FEM.

## Independently reconstructed curved Tet10 scan

Raw `.msh` read without Gmsh, using P10HV full-geometry curved Tet10 integration at 27, 343 and 729 volume quadrature points **per element**. Both original mesh SHA identities independently verified.

| Metric | Accepted M8 | Candidate M9 |
|---|---:|---:|
| Curved minDetJ 27 QP (m³) | 6.282765e−13 | 6.117721e−13 |
| Curved minDetJ 343 QP | 6.231845e−13 | 6.016021e−13 |
| Curved minDetJ 729 QP | 6.225989e−13 | **6.002327e−13** |
| Relative CAD volume closure (729 QP) | +6.816e−9 | **+6.881e−9** |

All the sampled curved Jacobians are positive; volume closure and physical tags PASS.

### D029: actual polar integration-cell effective volume

| Near-pole region | M9/M8 effective volume at 729 QP | Reduction | M9 effective QP support | Relative ratio drift 343→729 |
|---|---:|---:|---:|---:|
| North | **0.8044642495** | **19.5536%** | 1160.64 | 0.12544% |
| South | **0.8103755821** | **18.9624%** | 1179.16 | 0.00302% |

Both ratios pass the approved `[0.75, 0.85]` range and the QP-support/integration-order stability gates.

## Remaining D031 and next action

Canonical Gmsh Tet10 `minSICN`, `minSJ`, `gamma`, `minDetJac` have **not** yet been measured for M9, because the independent offline parser is not an implementation of Gmsh's canonical quality API. Do not substitute sampled 729QP detJ for that quality gate. Proposed thresholds: minSICN≥0.20; minSJ≥0.40; gamma≥0.15; minDetJac>0, all physical tags 2–9.

Prepared independent **read-only** P10LA Windows package `P10LA_M9_R1_READONLY_D031_WINDOWS_20261125.zip`, SHA256 `93ff6bd3864a3d1fb270e4906db7e935b2dbe669e77fdc4d5b13c92d159463ce` (4 files, 893,309 bytes). Run `01_P10LA_READONLY_QUALITY.cmd` (5–30 s anticipated), return only `P10LA_M9_R1_GMSH_QUALITY_RESULT.json`. It never generates a mesh, invokes FEM or consumes markers. Only after the returned canonical quality PASS may M9 be accepted for a *separately marked* full4D physical FEM one-shot.

Reproducible offline script `research/tools/p10kz_m9_r1_independent_d029_d031.py`; audit JSON `research/evidence/P10KZ_M9_R1_INDEPENDENT_D029_D031_PARTIAL.json`. No source 4D reanalysis or full FEM occurs in P10KZ.
