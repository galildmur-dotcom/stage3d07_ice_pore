# P10LM — separate M9 physical one-shot with two-term `mech_explicit` 4D diagnostic

**2026-11-25. Status `SOURCE_ONLY_PREPARED_NOT_EXECUTED`.** This is a **new distinct physical experiment** prepared under research SOP decision D-028, not a replay or restart of P10LC's consumed M9 physical one-shot. The investigator executes Windows buttons; this preparation caused **FEM0, Gmsh0, and no markers**.

## Scientific aim and historical decisions

The actual M8→M9 full-domain `mech_explicit` change is `+0.164433127821205 m^-1`, while first 0–20 μm from cavity wall contributes `+0.196024672712708 m^-1` (offset by other bins). P10LF established normalized geometry vs stress-chain algebra. P10LH independently validated its quotient, P10LI validated the physical writer on C++ synthetic snapshots, and P10LJ called the true 27-QP `mechanical_step` on a nontrivial synthetic Tet10. P10LK found only aggregated CSVs in submitted physical archives. SOP D-028 permits preparing bounded one-click packages without repeated approval; exact physical runs remain the investigator's action.

## Frozen experiment and only source delta

- Exact **accepted M9 R1** Tet10 mesh SHA-256 `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58`, 19,236 nodes / 13,166 Tet10 / 734 cavity Tri6.
- Same physical settings as successful P10LC: R, EDV_VAR, ξ=0, B6 cutoff 5 mm, 36 steps × 25 s = 900 s, 4 threads, original shape velocity and analytic adjoint. No meshing.
- 101-file original P10LC solver pin rechecked; **only** `stage3d10dd_4d_partition.hpp` deliberately changed to P10LG signed split SHA `0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3`. New source manifest SHA `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f`, new revision `P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1`.
- New extra output `P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv` — 43,200 spatial/time rows, 9 columns including both signed physical components and unmodified explicit sum. Original P10DD files retained.
- Independent `P10LM_split_audit.py` compares the two-term sum with separately written original P10DD value for every `(step,r,mu,phi)` bin; also emits 10 radial and three southern/middle/northern aggregate breakdowns to the manifest. Positive and deliberately corrupted negative synthetic tests PASS (7,200 rows).

## One-shot Windows guard

1. Independent **new marker namespace** `P10LM_M9_ONE_SHOT_MARKERS` under `G:\ildar\Stage3D07\LOCAL_RUNS`, and mirrored new profile marker under `%LOCALAPPDATA%\Stage3D07`.
2. Both markers are atomically created **before** the native FEM process. A STOP or failure consumes this new attempt; do not retry.
3. Source manifest SHA 101/101, exact M9 mesh SHA, 27QP positive Jacobian/physical tags and accepted geometry passport, 36×25 C++ guard, 65-second native Windows Job heartbeat selftest required before `02`.
4. Same Windows Job kill-on-close/memory cap (8 GiB), 40-minute hard wall clock, 2-GiB output budget, independent 15-second heartbeats. At ordinary M9 size expected physical wall time ~20–30 min, based on prior P10LC M9 `1,340.58 s` (22.34 min) and the small extra 4D CSV overhead. This is an estimate; compilation adds time.
5. Results are packaged into `P10LM_M9_FIRST_FULL4D_EVIDENCE.zip`; failure packaging includes whatever logs and CSVs exist plus a status manifest. `forward_history.bin` is not copied into evidence.

## Delivery and operation

Archive: `P10LM_M9_TWO_TERM_EXPLICIT_WINDOWS_ONE_SHOT_20261125.zip`; SHA-256 **`dc848985c723eb39a9d7c7793ab5f58cf02fc02595bb47850574a0b212bee895`**, 2,893,895 bytes; ZIP CRC PASS. Isolated work folder contains accepted M9 exact mesh, full pinned source/headers, guarded launcher and independent audit. No executables, old launcher, or consumed markers included.

On the user's Windows 11 computer:

1. Extract into a **new folder**.
2. Double-click `01_P10LM_PREFLIGHT_NO_FEM.cmd`; expected 65–85 seconds. This checks exact sources and mesh and tests silent native watchdog, **no FEM, no marker**. Require `P10LM_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS`.
3. If and only if PASS, double-click **once** `02_P10LM_ONE_M9_EXTENDED_EXPLICIT_FEM.cmd`. No manual PowerShell/Git, no typed confirmation. If failure or STOP occurs after marker consumption, **do not repeat**.
4. Return **one file**, the resulting `P10LM_M9_FIRST_FULL4D_EVIDENCE.zip`, for independent per-bin physical analysis. If preflight stops, return `P10LM_M9_PREFLIGHT_RESULT.json` or the displayed error/log as applicable.

## Verification already performed and limits

The package builder refuses overwriting an existing package; it validates all 101 previous pins before changing the single diagnostic header, and checks ZIP CRC. Linux `g++ -std=c++20 -fopenmp -O0 -fsyntax-only` on the instrumented full4D source PASSED. The P10LM source manifest validator reports the new exact revision. The independent audit positive/negative synthetic tests PASS. **Windows preflight, Windows MinGW build, and real native P10LM FEM are still PENDING.** No measured M9 geometry/stress figures are claimed.

Reproducibility: `research/tools/p10lm_build_windows_m9_diagnostic.py`, `research/tools/p10lm_split_audit.py`, `research/tools/p10lm_split_audit_selftest.py`, `research/P10LM_PREPARED_PACKAGE_QA.json`. After M9 results, a second uniquely marked M8 diagnostic may be justified to form a literal M9–M8 two-term difference; do not call the new M9 split alone a mesh-convergence attribution.
