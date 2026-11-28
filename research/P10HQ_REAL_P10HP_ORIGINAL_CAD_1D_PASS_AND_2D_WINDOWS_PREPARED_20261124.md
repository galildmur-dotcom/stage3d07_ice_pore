# P10HQ — real original CAD P10HP 1D PASS; bounded original CAD 2D prepared

Date 2026-11-24. User supplied `P10HP_GUARD_RESULT.json`, `P10HP_GMSH_LOG.txt`, and `P10HP_RESULT.json`.

Real Windows Gmsh 4.15.2 loaded pinned original `P10GT_HXT10.geo` SHA256 `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`, plus original M0/B6 rotated CAD. Actual entities were 12 vertices, 18 curves, 8 surfaces and 2 volumes (outer ice and B6 shell). Native `mesh.generate(1)` finished without errors, 0.329 s, 244 nodes, 123 one-dimensional elements (the native Gmsh log reports 135 total 0D+1D elements). Source direct mechanical κ callback called 4,193 times; κ∈[0,0.15786775088323313], `lc`∈[0.0004616510070248522,0.007597052580611059] m. Guard `WORKER_FINISHED`, code 0, total wall 1.2 s. No 2D/3D/FEM or M2.

**Verdict: original CAD + continuous direct C2 mechanical κ native 1D feasibility PASS.** This does not imply actual spatial surface refinement, nor true local D-025 volume. The maximum sampled κ along 1D curves is not representative of the whole pore surface (north/south/nonpolar).

## Next P10HQ bounded original CAD 2D test

Prepared Windows source-only ZIP `research/proposals/P10HQ_REAL_CAD_2D_CALLBACK_20261124/P10HQ_R1_REAL_CAD_ONE_GUARDED_2D_WINDOWS_20261124.zip`, SHA256 `a287bc599c4eff6d141a86e0e5e3e58de5293ebb18260348a4f0e0d8e49e19f1`, 214,401 bytes, verified CRC, byte identity and Python syntax. Uses original two-volume CAD, Field[7], and signed M0/M1 4D mechanical-only κ.

Driver performs exactly one `gmsh.model.mesh.generate(2)` on real 2D CAD surfaces. External timeout 180 s kills the child; 1,000,000 callback cap flags STOP. No `generate(3)`, no FEM, no M2, no `.msh` output. Native 2D Tri6 triangles are counted by physical surface (including PORE_WALL 8 and B6_INTERFACE 9). κ is evaluated at actual wall mesh nodes (not straight-chord centroids potentially inside the cavity); north μ≥0.8, south μ≤−0.8, and nonpolar groups are reported separately together with distance from ideal pore-wall sphere.

On user's i7‑7700K, estimated native runtime 10–180 s, plus possible local API wheel installation 1–5 minutes. Send `P10HQ_GUARD_RESULT.json`, `P10HQ_GMSH_LOG.txt`, `P10HQ_RESULT.json` (or worker error/installation log on STOP). Independently audit polar/nonpolar, surface element quality and actual candidate before any future 3D M2; D-025 still pending curved Tet10 343/729QP and local 15–25% volume ratio at κ=1.
