# P10MU — M13 ordinary adaptive sequence: A selected

**Decision**: After comparing A/B/C at P10MT, select **A_existing_residual**, not C, for M13. Do not replace the M13 source by C or reinterpret C as a proven error estimator. Keep B/C as source-only alternatives.

**Parent physical geometry**: M12 R1, 16,333 Tet10; accepted independent D031 quality, geometry SHA-256 `e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13`.

**Exact M13 source**: `p10mt_m13_source_only/P10MT_M13_A_existing_residual_1200_BINS.csv`, SHA-256 `5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383`, 1200 bins. Priority uses the updated M11→M12 absolute and late 4D data: `(0.4*N(new_L1)+0.6*N(late_new_actual))*(1+0.2*polar)`. Its spatial continuation follows inherited positive Wendland C2, quintic cutoff and C2 polar plateau. Incremental nominal volume multiplier `1-0.20*kappa13`, range 0.8–1.0. This is **not measured** Tet10 volume contraction.

**Source lock**: `python research/tools/p10mu_m13_a_source_lock.py` verifies selected field, accepted parent mesh SHA, observed D031 quality and analytic-source C2 QA without calling Gmsh, FEM or touching one-shot markers.

## Next execution gate: dedicated new M13 geometry-only package

1. Package must contain *all* prior source and geometry files required by the inherited M12 callback, the exact locked M13 A source, and the accepted M12 mesh. Verify the transitive GEO graph, source SHA and native `gmsh 4.15.2` before any marker consumption.
2. Preserve original rotated spherical CAD, ten pinned pore surface seeds and M11 R2 local smooth repair; append only `kappa13 = polar_blend_m8(m13.kappa(position),dmm,mu)` and `(1-0.20*kappa13)**(1/3)` after the M12 multiplier. Do not change previous M1–M12 multipliers.
3. Provide independent 15-second heartbeat, time/memory/output limits, an exclusive **M13-specific cross-folder one-shot marker** and one-click Windows preflight and mesh-only wrappers. Do not reuse the M12 marker or worker source. Record exact hashes and a uniquely named evidence ZIP.
4. Produce one M13 R1 *unverified* 3D Tet10 mesh only. Follow with separate read-only D029 (curved 729-QP and near-wall/polar volume checks) and D031 (Gmsh minSICN, minSJ, gamma, minDetJac) before any physical FEM attempt.
5. Compare M12→M13 full 4D fields on exactly aligned bins and time steps. Track L1, L2, global derivative gap and cancellation coefficient. Do not claim convergence from global derivative agreement alone.

**Current status**: only source A and preflight provenance pinned. **No M13 mesh generated, no native one-shot package yet issued, no FEM.** Do not run a partially repurposed M12 mesh script.
