# P10JP — accepted M5 full4D FEM Windows one-shot PREPARED, NOT RUN (2026-11-24)

## Scientific boundary

P10JO accepted M5 geometry D031 and polar adaptation D029 **PASS**, M5 SHA256 `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`, 15,780 nodes, 10,826 curved Tet10, 386 pore Tri6, physical surface tags 2–9; read-only 27QP M5 no inverted elements. Prior M4 SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, accepted physical signed derivative M4 +2.388080130362648 m⁻¹; global M3→M4 increment −.08513474055522016 m⁻¹ remains insufficient for convergence claim.

**P10JP objective** = obtain physically real M5 signed4D derivative and independent compare `D_R j_peak(M5) - D_R j_peak(M4)`. No hypothetical derivative, no mesh regeneration. Regime exact **R/EDV_VAR/ξ0/B6=5mm, 36×25s (900s), 4 threads, fresh forward and same-M5 analytic adjoint**, signed 4D 1200 spatial bins × 36 steps + summary, 101 pinned solver files. Unchanged verified P10JF M4 C++ solver source inventory SHA `dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc`, source revision `P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS`, independent temporal checker SHA `547ebec5955c882507e707fe2604f43713ec15a4bf4323b659c3e1c6ff100`.

## Private user-deliverable

`P10JP_M5_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261124.zip`, SHA256 **`be0a89c4a9cb4f607f94552c403b44562744b17bdd7a23a4f1bf91b37b589f04`**, ZIP integrity PASS (113 entries). Delivered privately via conversation/Library, **do not push M5 mesh or raw 4D to public git**. Includes the exact accepted M5, trusted solver sources and own P10JP driver and heartbeat, *no M4 mesh or physical results*. Requires Windows11, user project folder `G:\ildar\Stage3D07` for runtime artifacts, Qt MinGW compiler as in P10JF.

User clicks in a fresh unzipped folder:
1. `01_P10JP_M5_PREFLIGHT_NO_FEM.cmd` repeatable; needs `P10JP_M5_PREFLIGHT_PASS_NO_FEM` and exit0; checks 101 pinned files and curved M5 with 27QP, **no FEM/marker/compile**.
2. `02_P10JP_ONE_M5_FULL4D_FEM.cmd` **exactly once**, distinct consumed marker `G:\ildar\Stage3D07\LOCAL_RUNS\P10JP_M5_ONE_SHOT_MARKERS\M5_R_DT25_STEPS36_91b26a9a5dcc054e.json` written **before native**; no retry even after STOP. Runs native solver fresh forward/adjoint. One result archive `P10JP_M5_FIRST_FULL4D_EVIDENCE.zip` from new `LOCAL_RUNS\P10JP_M5_R_DT25_*`; send only this.

Guards: MinGW C++ compile + native selftest, native 2400s wall, hard Windows job private cap 8GiB adjusted for free RAM (at least 12GiB before run), output 2GiB, free disk≥4GiB, no automatic rerun, no mesh generation. Estimated i7-7700K ≈20–40min uncertain. P10JH visible all-phase immediate START and independent ≤30s heartbeat for preflight, compile/selftest, native FEM (PID/alive/RAM/log tail and explicit step_unknown when native silent), signed4D QA, ZIP packaging, final STOP/END. Windows CMD preserves output window.

## Source-only acceptance

- Archive integrity zip PASS 113 entries.
- Exact M5 SHA source match; independently run packaged legacy mesh QA: nodes 15780/Tet10 10826/pore Tri6 386/tags2–9/min curved detJ 1.8192e−12/no nonpositive.
- In-memory platform-bypassed **preflight only** source SHA101 + mesh QA PASS; no native, no marker.
- Actual Linux `--run` negative STOP (platform guard) before marker/FEM.
- Real silent 65-second phase heartbeat regression PASS **2 messages at 30/60 seconds**, source-only.
- Python `py_compile` PASS.
- **No Windows compile or FEM performed by assistant**. Candidate statuses: P10JP prepared PASS, M5 FEM not attempted, physics/convergence unknown.

Next: user runs two CMD; independent P10JQ audit of returned signed4D archive + M5−M4 delta, nonpolar signed compensation, spatial convergence under fixed 25s.
