# P10HP — real P10HN native variable Field[7] PASS; original CAD guarded 1D prepared

Date 2026-11-24. User uploaded P10HN result and Gmsh log. `status=LC_EQUALS_F7_PASS`: 6,140 callback invocations on pinned source `P10GT_HXT10.geo` SHA256 `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`; Gmsh API 4.15.2; independent variable Field[7] range 0.000461651007–0.007597052581 m exactly coincided with native callback `lc` at all recorded points (`lc / F7 ≡ 1`). Original MeshSizeFactor is 0.9378887276834518; therefore it is **not applied to the value of the `lc` callback argument** in this synthetic field-only setting. Whether/when Gmsh applies the factor to final element sizes must be assessed independently.

User Gmsh constructed a single synthetic 1D line, 13 nodes/14 elements, 2.8864 s, κ range 0–0.0242448564, nominal returned size/base ratio 0.998624–1. No original CAD was meshed in P10HN, and no 2D/3D/FEM/M2.

## Next native P10HP: one bounded full original CAD 1D only

Prepared Windows ZIP `research/proposals/P10HP_REAL_CAD_1D_CALLBACK_20261124/P10HP_R1_REAL_CAD_ONE_GUARDED_1D_WINDOWS_20261124.zip`, SHA256 `99bab635a62408fc5d0151e971d203d1e744a2484d973a22480d50fc501abae2`, 213,954 bytes, CRC verified and Python sources syntax-checked. Includes exact P10GT original Field[7] and Gmsh original CAD, preserving B6 sphere, outer ice and smoothing, and the frozen mechanical-only signed 4D κ source.

Driver imports real CAD and verifies the original pinned `MeshSizeFactor`, checks that exactly two geometric volumes (outer ice+B6 shell) are present, installs the exact scalar κ callback, then **calls `gmsh.model.mesh.generate(1)` exactly once**. No 2D/3D and no FEM or M2. External wrapper uses `subprocess.run(..., timeout=120)` to terminate a hung/slow child; further internal 300,000 callback guard records STOP rather than permitting unlimited source evaluations. Pore interior queries remain a hard physical STOP. No `.msh` output is generated; only JSON/log evidence.

Run `01_P10HP_REAL_CAD_ONE_1D_GUARDED.cmd` on Windows. Estimated 5–120 s for native work (plus possible one-time local API install). Return `P10HP_GUARD_RESULT.json`, `P10HP_GMSH_LOG.txt`, and when present `P10HP_RESULT.json` or `P10HP_WORKER_ERROR.txt`. The stage is a **geometry + 1D feasibility test only**. Later independently verify polar/nonpolar near-pore surface field and actual smooth 3D D-025 volume reduction15–25% with quadrature343/729. No M2/FEM yet.
