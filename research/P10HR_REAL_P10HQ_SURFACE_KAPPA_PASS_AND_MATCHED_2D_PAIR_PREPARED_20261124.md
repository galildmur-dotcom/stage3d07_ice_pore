# P10HR — real P10HQ surface κ PASS; matched baseline/adapted 2D pair prepared

Date 2026-11-24. User evidence `P10HQ_GUARD_RESULT.json`, `P10HQ_GMSH_LOG.txt`, `P10HQ_RESULT.json`. `WORKER_FINISHED`, exit 0, total 1.204 s, native 2D Gmsh 4.15.2 wall 0.269 s, 3026 nodes and 1510 Tri6 surface triangles; no 3D/M2/FEM. Pinned CAD has 12 vertices, 18 curves, 8 surfaces, 2 volumes. Original P10GT GEO SHA256 `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`.

Physical surface counts: `PORE_WALL` tag8 178 triangles; B6 interface tag9 342 triangles; six outer faces counts 156, 156, 184, 156, 182, 156 (total 990). Exactly 358 real wall nodes, all on ideal sphere within ~1.74e−15 mm radial deviation. Gmsh 5,093 callback calls with κ∈[0,1], source `lc` range [0.0004201024,0.0075970526] m. Native Gmsh log reports high-order surface worst distortion 0.859315 and worst gamma 0.438976; 0 triangles in low-distortion interval ]0,0.2].

| Pore wall region | actual wall nodes | median κ | p95 κ | max κ |
|---|---:|---:|---:|---:|
| North μ≥0.8 | 35 | 0.566868 | 0.848333 | 0.892491 |
| South μ≤−0.8 | 40 | 0.446774 | 0.981851 | 1.000000 |
| Nonpolar |μ|<0.8 | 283 | 0.0136282 | 0.0947085 | 0.261188 |

**Verdict: real CAD source-driven 2D native operation PASS.** This confirms polar hotspot coverage but NOT the amount of actual spatial refinement. Even κ=1 gives only a nominal **6.02% linear edge-size decrease** for α=.17 (`(1−.17)^(1/3)≈0.9399`), potentially too small to change the number of deterministic surface triangles. A field value is not itself evidence of mesh adaptation.

## Next P10HR experiment: matched original 2D baseline vs κ-adapted

Windows ZIP `research/proposals/P10HR_MATCHED_REAL_CAD_2D_PAIR_20261124/P10HR_R1_MATCHED_REAL_CAD_2D_BASELINE_KAPPA_WINDOWS_20261124.zip`, SHA256 `be880c3ccf0b449a693a02798d0dbd24a34e60540ce6d1748352bcb2ee8685c2`, 214,711 bytes; CRC and file byte identity checked, Python sources syntax-checked. The program uses exact original CAD and `Field[7]`, runs one native `gmsh.model.mesh.generate(2)` baseline, then clears only the mesh, installs direct mechanical-only C2 κ, and runs one native adapted `generate(2)`. Reports exact counts and straight corner edge lengths for pore-wall Tri6 north/south/nonpolar, baseline and adapted; no 3D M2 or FEM.

External timeout 180 s for the pair, 500k adaptive callback cap. Expected 5–180 s on user's i7-7700K plus possible local Python Gmsh wheel installation. Return `P10HR_GUARD_RESULT.json`, `P10HR_GMSH_LOG.txt`, `P10HR_RESULT.json` (or worker/installation error). Only after independent matched-pair 2D adjudication consider a bounded 3D candidate followed by strict actual Tet10 curved 343/729 quadrature D-025 (15–25% actual local volume decrease near κ=1, continuous transitions). Signed M0/M1 4D physics unchanged.
