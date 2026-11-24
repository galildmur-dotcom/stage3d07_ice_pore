# P10JF — first real M4 full4D bounded Windows one-shot PREPARED, NOT RUN (24.11.2026)

## Prerequisite

P10JE real Windows user-returned P10JD PASS: exact P10GY R2 101/101 source SHA; pinned M4 SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, 15141 nodes/10399 Tet10, D031/D029 P10IZ GO, 27QP 280773 positive, no FEM so far. Source manifest SHA `dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc`; time 36×25 approved.

## New private one-shot deliverable

`P10JF_M4_FIRST_REAL_FULL4D_WINDOWS_ONE_SHOT_PREPARED_20261124.zip`, SHA256 `596f05644c6399b4a3db6f78345d232eafcb214def253a5221534dcf0032a19e`, ZIP CRC PASS. Private only (contains M4 and 101 solver source files), not committed to public GitHub. Top-level Windows commands:
1. `01_P10JF_M4_PREFLIGHT_NO_FEM.cmd` repeatable SHA/27QP preflight;
2. `02_P10JF_ONE_M4_FIRST_FULL4D_ONE_SHOT.cmd` **do not run before separate explicit researcher authorization**; one-shot irreversible on native launch, new M4-only marker.

All original 101 source files and manifest are **byte-identical**, check 101 SHA zero mismatch. P10GY temporal audit independently SHA-pinned; only new P10JF Python driver and renamed heartbeat messages changed. No C++ or PDE source modifications. Pinned original 36x25 dynamic whitelist, full4D writer and native marker guard reused. All 101 source files plus historical scripts remain under `P10JF_WORK`; never run historical scripts manually.

Physical regime: `R/EDV_VAR/ξ0/B6 5mm/900s/dt25/36 steps/4 threads`, one fresh forward solve + analytic adjoint **on the same M4**, no finite difference geometry. New one-shot marker `G:\\ildar\\Stage3D07\\LOCAL_RUNS\\P10JF_M4_ONE_SHOT_MARKERS\\M4_R_DT25_STEPS36_a9fff03ca56b92c1.json` created before native process; no reuse on STOP, no automatic retry. WindowsJob hard private memory cap ≤8 GiB (free ≥12 GiB), native wall ≤2400 s, output directory ≤2 GiB and disk free ≥4 GiB. Build `ensure_binary` capped 900s and selftest, 30-second build heartbeats; native FEM 30-second heartbeat prints elapsed, peak private MiB, last native log line or explicit no lines. Estimated native 15–30 min on i7-7700K (M3 902.3s), not guarantee; 40min hard native cap.

Evidence ZIP `P10JF_M4_FIRST_FULL4D_EVIDENCE.zip` includes `P10JF_MANIFEST.json`, `P10JF_NATIVE_LOG.txt`, five compact 4D signed/adjoint CSVs, not forward history or huge VTUs. In worker, independent `P10GY_temporal_series.independent_time_audit(...,'M4',10399,25,36)` checks 43,236 4D rows, 1200 physical bins, 6 signed components, temporal and QP closure before marking PASS. Local history remains pinned by SHA.

## Completed preparation QA

- Python syntax/py_compile PASS.
- All 101 original SHA checks PASS, manifest SHA unchanged.
- Local read-only P10JF source/M4 27QP preflight PASS (Linux environment guard intentionally bypassed **only for local read-only testing**); nodes15141/tet10399/pore310.
- Linux `--run` negative STOP PASS: no compiler/FEM.
- ZIP CRC PASS.
- **Actual Windows compilation and M4 FEM not performed.** No P10JF one-shot marker consumed.

Scientific next step: secure explicit user permission for M4 FEM; user downloads private ZIP, optionally runs preflight 01, and after authorization only once 02. Return single evidence ZIP; independently validate signed closure and compute `D_R jpeak(M4)-D_R jpeak(M3)`, binwise polar support compensation and spatial convergence indicators. No claim of convergence until evidence.
