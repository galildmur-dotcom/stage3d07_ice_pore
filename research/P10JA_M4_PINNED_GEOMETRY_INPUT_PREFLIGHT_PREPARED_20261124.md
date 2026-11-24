# P10JA — M4 pinned geometry/FEM-input preflight prepared, no FEM (24.11.2026)

P10IZ independently accepted M4: SHA256 `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, 10399 curved Tet10, 310 pore Tri6, D031/D029 GO. The next limited stage P10JA prepares a **self-contained, read-only M4 mesh input preflight**, no solver-source compatibility assertion yet.

Private Windows package `P10JA_M4_GEOMETRY_INPUT_PREFLIGHT_NO_FEM_WINDOWS_20261124.zip`, SHA256 `9321412331889d02ba48b8ddfdc6f51fa495f687e146be13840d89f3afdf8f9a`. ZIP CRC all 4 entries PASS; contains pinned M4.msh privately plus `01_P10JA_M4_PREFLIGHT_NO_FEM.cmd`, `P10JA_M4_PREFLIGHT_NO_FEM.py`, `README_P10JA_RU.md`. **Do not commit raw M4 mesh or ZIP to public GitHub.**

Locally tested on Python+Gmsh 4.15.2: `P10JA_CHECK_1_PINNED_SHA_OK`, `P10JA_CHECK_2_D031_CURVED_TET10_PASS`, `P10JA_PREFLIGHT_PASS_NO_FEM`. Checks mesh SHA, Tet10 count, pore Tri6 count, physical surface groups 2..9, all curved Tet10 qualities minSICN≥.2, minSJ≥.4, gamma≥.15, minDetJac>0. No mesh.generate, compiler, or solver execution. Script writes `P10JA_M4_PREFLIGHT_RESULT.json` on PASS or STOP, with explicit FEM=0; repeatable and does not consume marker. Explicitly **not** a full 101-source P10FN solver verification; source compatibility remains an open gate.

User instructions: extract into fresh Windows folder and double-click only `01_P10JA_M4_PREFLIGHT_NO_FEM.cmd`; 10–60 seconds estimated on i7-7700K; return only `P10JA_M4_PREFLIGHT_RESULT.json`. Later verify the pinned solver-source bundle and compile interface before requesting separate authorization of an M4 direct+adjoint one-shot FEM (R/EDV_VAR/ξ0/B6 5mm/900s/dt25/36 steps/4 threads). Do not repeat M3 or M4 previous one-shot markers. No M4 FEM result or Δ3 is available yet.

The preparatory code is intentionally only in the private ZIP pending full-source integration. The independent M4 geometry GO remains documented in `P10IZ_M4_SECOND_REAL_INDEPENDENT_D031_D029_GEOMETRY_GO_20261124.md`.
