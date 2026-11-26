# P10NY — first optimized M13 physical full4D prepared (2026-11-26)

Status: **WINDOWS ONE-SHOT PREPARED; NO M13 FEM EXECUTED**.

## Locked physical target

- Accepted optimized serialized **M13** mesh SHA256: `cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca`.
- 26,099 nodes, 18,004 Tet10, 1,168 pore Tri6; physical surfaces 2–9.
- Regime: `R / EDV_VAR / ξ=0 / jpeak / B6=5 mm / 36×25 s / 4 threads`.
- Same-mesh direct + analytic adjoint; signed 4D CSV, independent temporal audit and explicit geometry/stress two-term split audit.
- Solver pinned to 101 exact source files of previously used P10LM M9 production revision; no solver physics source modification.

## Package

`P10NY_M13_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261126.zip`

- SHA256: `c419f2a64968bb3fbf2c77bb2dcbe5bb838672f8cc7f14e1c569c8fb893ccc32`.
- Size: 1,656,598 bytes.
- Contains native Windows 11 double-click `01_P10NY_PREFLIGHT_AND_WATCHDOG_TEST.cmd` (no FEM), then `02_P10NY_ONE_M13_FULL4D_FEM.cmd` (unique one-shot FEM, never repeat).
- Separate P10NY local and persistent Windows profile markers written BEFORE FEM; no automatic retry. Independent native 15-s heartbeat; 65-s silent watchdog test before marker.
- Windows Job wall 5,400 s, private memory 12 GiB, output 3 GiB.
- Physical output `P10NY_M13_FIRST_FULL4D_EVIDENCE.zip` to return for evaluation and subsequent M9↔M13 comparison.

## Preparation QA

- Linux source-only preflight: **PASS** (101-file source manifest, exact M13 SHA, 27QP physical-group mesh QA).
- Minimum 27-point curved detJ: **1.7454418527270142e-13 m³** (diagnostic finite samples, not a global algebraic proof).
- Python launcher compiled; delivery ZIP CRC test passed.
- Native Windows watchdog, toolchain build, FEM, and signed-4D outputs: **NOT RUN / NOT CLAIMED**.

## Next gate

User runs 01 on Windows and, only after PASS, runs 02 exactly once; then supplies the generated evidence ZIP. Analyze physically computed M13 versus already-consumed M9 without prematurely claiming spatial convergence. Avoid creating a central FD counterfactual mesh.
