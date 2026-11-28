# P10HI R1 — independent real M1 Tet10 κ/PostView interpolation audit (2026-11-24)

## Decision: NO-GO for adaptive M2 construction

Scope: read-only verification of P10HG R3 evidence and pinned original P10GT M1 Tet10. No 1D/2D/3D mesh generation, no FEM, no alteration of signed M0/M1 physics.

P10HG R3 returned `P10HE_SOURCE_POSTVIEW_BUILD_AND_GMSH_PARSE_PASS_NO_MESH`: 13,978 M1 nodes, 9,623 Tet10, 9,623 `SS` PostView records, κ within [0,1], native Gmsh read/parse PASS. The P10HG R3 correction to the official six Tet10 edge ordering makes its interpolation QA valid; it does not modify the previously generated `.pos` source. Evidence ZIP SHA256 `a2e69596d49efcde97326386fd15c0290d788614b538a992acade3e9f2ad48c6`.

The independent `scripts/p10hi_independent_m1_kappa_subtet_qa.py` uses pinned original M1 ZIP SHA256 `7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3`, mesh SHA256 `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`, recomputes original κ at all actual M1 nodes, and performs 57,738 edge checks.

| M1 original corner-only `SS` approximation | Absolute κ discrepancy |
|---|---:|
| Median at true Tet10 midsides | 0.00061347 |
| P95 | 0.01834966 |
| Max | 0.36655209 |
| Incidences > 0.05 | 869 / 57,738 (1.505%) |
| North polar μ≥0.8, incidences > 0.05 | 294 / 4,513 |
| South polar μ≤−0.8, incidences > 0.05 | 219 / 5,536 |
| Nonpolar |μ|<0.8, incidences > 0.05 | 356 / 47,689 |
| High κ>0.5, incidences > 0.05 | 70 / 87 |

Therefore the successful *native parse* does **not** certify adequacy of the actual spatial adaptation driver. The source is C2 by construction, but its corner-only scalar-tetra PostView representation is C0 and omits six nodal samples from every physical Tet10.

### Independent eight-subtet candidate (rejected for automatic use)

One candidate divided every original Tet10 into four corner tetrahedra and four tetrahedra splitting the central octahedron. This introduces 76,984 visualization-only scalar subtetrahedra and interpolates all ten κ nodal samples exactly, but the original curved Tet10 map is **not** generally recovered by straight subtetrahedra.

- Absolute subtet volume sum / original four-corner tetra volume: min **0.8801**, median **1.0000**, p95 **1.0253**, max **1.1906**. These are diagnostic ratios to the *corner tetra*, not rigorous curved-element-volume conservation checks.
- Maximum true curved midside displacement relative to its straight corner chord: **0.264 mm**.
- Quarter-edge κ interpolation check at points in the physically valid ice domain: median **0.0001535**, p95 **0.0076448**, max **0.53705**; **370/57,008** errors >0.05. Tests at **730** quarter-edge chord points inside the spherical pore were excluded by the original physical-domain guard (they were not silently evaluated as ice).
- Zero negative signed subtet determinants for the chosen local orientation is **not** proof of conformity to the curved original element or valid 3D adaptive meshing.

## Next guarded step: source-only field fidelity first

Before any proposed M2 generation: investigate native Gmsh higher-order PostView representation (or another explicit curved Tet10 sample/evaluation method), preserving original ten-node physical geometry and nodal scalar κ. Verify at original midside nodes and independent interior ice points, across north/south/nonpolar groups, while explicitly checking near-pore spatial domain, view evaluation behavior and deterministic source hashes. Only then consider a **bounded** 1D field evaluation and separate audited D-025 remeshing; never confuse native parse PASS with M2 GO.

The mechanical-only κ selection and signed 4D M0/M1 basis remain unchanged. No thermal contribution is required in the adaptation indicator under the recorded decision.
