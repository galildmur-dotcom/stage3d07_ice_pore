# P10NE — M13 R1/R2: failing Tet10 belong to pore boundary, defects migrate

Date: 2026-11-26. User-returned native canonical `P10ND_M13_R2_BAD_TET10_LOCATIONS.json` establishes **one** bad R2 Tet10, tag 9478, after the previous R1's two bad Tet10 (tags 13346, 9035). R2 quality minima remain below strict thresholds: minSICN 0.16294478890105799 < 0.20 and minSJ 0.28115937433961596 < 0.40. Full FEM geometrical acceptance remains **HOLD**.

The independent Gmsh2 connectivity read-only tool `research/tools/p10ne_m13_r1_r2_bad_tet_topology_readonly.py` checks exact pinned mesh SHA against both reports, identifies Tet10 vertices and shared pore-surface Tri6 nodes, and measures six straight corner-edge lengths. Machine-readable result: `p10ne_m13_bad_topology/P10NE_M13_R1_R2_BAD_TET10_TOPOLOGY.json`.

| Mesh/tag | Wall distance (mm) | mu | Pore-boundary corners | Pore-boundary Tet10 nodes | Corner edge max/min | minSJ |
|---|---:|---:|---:|---:|---:|---:|
| R1 / 13346 | 0.019686 | -0.638720 | 3 of 4 | 6 of 10 | 2.3886 | 0.322163 |
| R1 / 9035 | 0.023168 | +0.638184 | 3 of 4 | 6 of 10 | 2.6044 | 0.366875 |
| R2 / 9478 | 0.027316 | +0.625773 | 3 of 4 | 6 of 10 | 1.8108 | 0.281159 |

The R2 defect is **not within either 0.25-mm R2 local C2 repair support**. Distances from the R2 defect centroid to original R1 bad-element centers: 2.04371 mm (13346) and 1.06278 mm (9035). Thus the failing location has migrated after a new Gmsh discretization. Despite a more favorable raw corner-edge ratio, R2's minSJ is worse. A change to local element-size alone should not be assumed sufficient to resolve the quality mechanism; the connection to curved pore surface geometry is directly observed.

**Interpretation, not established causation:** All bad elements share a full curved Tri6 face on the pore boundary and occur near the transition of the polar collar (|mu|~.63). The pore surface tessellation, curved Jacobian near the face, and interaction with polar size transition are candidates for focused examination. The two radius-0.25-mm local changes were *not* adjacent to the new failed element; global surface/volume tessellation likely changed, but a direct causal chain is not demonstrated by this evidence.

**Next scientifically controlled step:** independent read-only pore Tri6 face-angle, curvature, and adjacency audit at the three failure locations, with comparison to the distribution of all pore surface triangles on R1/R2. Verify whether R2's bad Tet10 is attached to a distinctly poor Tri6 face or whether the issue lies in the off-surface fourth vertex and high-order interior geometry. Only after that design any separate, uniquely guarded M13 R3 geometry-only intervention. Keep normal M13 A source, the original spherical CAD and full M1–M13 adaptation factors. Do not reuse consumed R1/R2 markers, run FEM or silently relax D031 thresholds.

**P10NF follow-up, completed read-only:** the surface-facing Tri6 of R1 bad elements has minimum corner angles 36.42° (4.48th percentile of all R1 pore Tri6) and 32.77° (1.38th percentile), suggesting those surface triangles are relatively skewed. **In contrast, R2's sole bad Tet10 (9478) shares an excellent near-equilateral pore face**, minimum 56.05° (65.58th percentile among R2 pore triangles), while its minSJ is worse at 0.28116. Thus a poor surface triangle is **not a necessary cause** of the D031 failure. The off-surface fourth vertex, its orientation/height relative to the sphere and the curved Tet10 mapping should be examined next. Data: `p10nf_m13_pore_faces/P10NF_R1_R2_PORE_TRI6_FACE_QUALITY.json`, tool `research/tools/p10nf_m13_pore_tri6_face_audit_readonly.py`. No native meshing or FEM.
