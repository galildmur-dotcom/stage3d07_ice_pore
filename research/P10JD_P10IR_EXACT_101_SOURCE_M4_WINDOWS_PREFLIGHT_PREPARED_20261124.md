# P10JD — exact P10IR 101-source pinned M4 no-FEM Windows preflight prepared (24.11.2026)

## Closed source-provenance blocker

Researcher privately supplied exact `P10IR_M3_FIRST_REAL_FULL4D_WINDOWS_ONE_SHOT_20261124.zip`. SHA-256: `d81388462a2bee0c7f96d085f00c789d05008da2ff86b9316a9d6c2d73b0b609`, matches prior published P10IR preparation. ZIP CRC all entries PASS. Its `P10IR_WORK/P10FN_SOURCE_SHA256.json` is **revision `P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS` with exactly 101 pinned source files**; all 101 hashes pass, 0 mismatches. The C++ source explicitly allows `36x25`, and the 4D writer guards 900 s with 6–36 steps. This resolves P10JC's old 113-versus-101 provenance mismatch: P10FN R1 was a different historical revision. Never alter the 101 pinned sources.

## New P10JD delivery

Private ZIP `P10JD_M4_FULL_101_SOURCE_PREFLIGHT_NO_FEM_WINDOWS_20261124.zip`; SHA256 `b9ae147589fcbae58e3dae36fc4fe9a2cb5d652140af2dce592b0cd9d9661fd2`, ZIP CRC PASS. Contains: original byte-identical 101 source files plus manifest, the exact unpinned-by-manifest P10GY temporal audit `P10GY_temporal_series.py` separately pinned SHA `547ebec5955c882507e707fe2604f43713ec15a4bf4323b659619c3e1c6ff100`, exact accepted M4.msh SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c` (private only), new read-only preflight script and CMD, README.

The 101 original files (including historical scripts not to execute) are nested under `PINNED_P10IR_SOURCE_DO_NOT_LAUNCH`; only top-level double-click `01_P10JD_M4_FULL_SOURCE_PREFLIGHT_NO_FEM.cmd` should be used. No source is recompiled or executed as FEM. New script validates 101 source SHA, exact revision, C++ authorized one-shot and `36x25` whitelist, dynamic writer 900s, P10GY temporal audit SHA, solver compiler-wrapper textual interface, pinned M4 SHA, and 10399 Tet10 / 310 pore Tri6 / tags 2–9 / all positive 27QP curved detJ. Full independent D031/D029/729QP GO already completed P10IZ.

**Local test:** `P10JD_CHECK_1_101_PINNED_SOURCE_SHA_PASS`, `P10JD_CHECK_2_36x25_SOURCE_INTERFACE_PASS`, `P10JD_CHECK_3_M4_27QP_INPUT_PASS`, `P10JD_FULL_SOURCE_AND_M4_PREFLIGHT_PASS_NO_FEM`. No Gmsh generation, source compilation, FEM or one-shot marker consumption.

Researcher should unzip in fresh folder, double click only `01_P10JD_M4_FULL_SOURCE_PREFLIGHT_NO_FEM.cmd` (~15–90 s on i7-7700K), send **one** `P10JD_M4_FULL_SOURCE_PREFLIGHT_RESULT.json`. Result must be independently checked before any explicit authorization of M4 FEM. Physical regime is fixed R/EDV_VAR/ξ0/B6 5mm/dt25/36 steps/900s/4 threads, same-mesh direct+adjoint, no analytic shape FD. Next single new M4 FEM one-shot must be explicitly authorized and bounded, with informative ≤30s heartbeat; M2/M3 markers never reused. No full physical convergence claimed yet.

Private source ZIP and raw mesh are not published to public GitHub.
