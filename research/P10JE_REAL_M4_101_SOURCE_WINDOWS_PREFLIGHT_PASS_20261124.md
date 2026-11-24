# P10JE — real Windows P10JD 101-source + M4 input preflight PASS (24.11.2026)

User returned private `P10JD_M4_FULL_SOURCE_PREFLIGHT_RESULT.json`: `status=PASS_FULL_SOURCE_AND_M4_INPUT_NO_FEM`, protocol `P10JD_REAL_P10IR_101_SOURCE_M4_27QP_PREFLIGHT_V1`, wall=2.659s, no build/mesh generation/FEM or marker consumed.

Exact P10GY R2 source revision `P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS`, **101/101 pinned sources SHA PASS**, source manifest SHA256 `dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc`. Solver interface R/EDV_VAR/ξ0/B6 5mm/900s/**36×25s**/4 threads.

M4 SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, nodes15141, Tet10=10399, pore Tri6=310, top Tri6=184, physical tags 2..9, curved 27QP count280773, nonpositive samples0, min curved detJ=4.061288199266529e−12, min corner detJ=4.388972373392662e−12, 27QP volume=.00017999581275238377 m³. Independent P10IZ 729QP all-Tet10 geometry/D029 polar GO remains valid.

**Decision: FEM_SOURCE_AND_MESH_PREFLIGHT_GO for preparation, not authorization to execute.** Next scientific step: prepare a distinct guarded Windows M4 one-shot direct+adjoint FEM using the exact same 101 files (never rewrite) with only mesh reference and guard/manifest labels changed, fresh one-shot marker unique to M4, job private ≤8GiB, free RAM≥12GiB, disk≥4GiB, wall ≤2400s (baseline M3 physical wall 902s; estimate M4 ≈15–30min), output ≤2GiB, heartbeat ≤30s during build and FEM. User must explicitly authorize actual M4 physical execution after inspecting package. Single evidence ZIP with manifest, log, five signed-4D CSVs; independent M3→M4 global/1200 polar-bin comparison afterwards. Old M2/M3 and mesh markers remain consumed. No M4 physical derivative exists yet.
