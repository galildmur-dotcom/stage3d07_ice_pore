# P10OS — M16 RAW recovery, prepared 2026-11-27

## P10OR evidence (received)

- P10OR one-shot is **consumed**, no repeat.
- Gmsh 4.15.2 generated RAW M16: **21,683 Tet10**, **32,155 nodes**.
- RAW SHA-256: `eb34e68c82c042bba6f9a77830983412cba319d0d3fdfdb8fad14dded714256a`.
- RAW native minima: SICN 0.25141610, SJ 0.47836067, gamma 0.23039052, detJ 5.1397174e-14 (all thresholds pass).
- `HighOrderElastic` ran successfully: SICN 0.26342805, SJ 0.74976751, gamma 0.22803947, detJ 5.3793672e-14 (all pass).
- **Previous P10OR worker bug**: `NameError: before_groups is not defined` in boundary comparison, before optimized mesh write. This is not mesh rejection. The recovered optimized mesh is not in P10OR evidence.

## P10OS execution protocol (not yet executed)

P10OS reimports the exact saved RAW MSH and applies mandatory `gmsh.model.mesh.optimize('HighOrderElastic',force=False)` **once**, without `mesh.generate()`, CAD remeshing, or FEM. It checks native metric gates and the Tri6 physical-boundary coordinate invariants, writes an **unverified** M16 mesh, and packages evidence. Independent curved Tet10 detJ/topology/reimport acceptance remains pending.

- One-click Windows archive: `P10OS_M16_RAW_HIGHORDERELASTIC_RECOVERY_WINDOWS_20261127.zip`.
- ZIP SHA-256: `bd22ff3c901a4cdd13cdfdb115319e6677f028d4db2da2ef8fa5bcdff46c9f63`.
- User delivery: https://chatgpt.com/library?file_id=libfile_aebd2671852c8191a28f8bd3d7b6c099&account_id=personal
- Windows preflight, cross-folder persistent one-shot marker, 15s heartbeat, 900s timeout, evidence ZIP.
- Original P10OR marker and original evidence must be preserved. No M16 accepted; no FEM.

## Next

Wait for `P10OS_M16_ELASTIC_RECOVERY_EVIDENCE.zip`, verify the optimized SHA and source, audit curved Jacobians at multiple quadrature grids, physical boundary and combinatorial topology, then independent Gmsh reimport. Proceed with M17 field only on accepted M16.
