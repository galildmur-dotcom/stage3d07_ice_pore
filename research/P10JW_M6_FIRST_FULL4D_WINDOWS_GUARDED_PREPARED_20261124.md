# P10JW — first accepted M6 full4D FEM guarded Windows one-shot PREPARED (2026-11-24)

## State and scientific run

P10JV real M6 D031 and D029 geometry/adaptation **GO**, exact M6 mesh SHA `d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0`; nodes **16988**, Tet10 **11628**, pore Tri6 **526**, surface tags2–9, nonpositive curved 27QP detJ **0**. **M6 FEM NOT RUN.** Prior M5 derivative `D_R jpeak(M5)=+2.364120991403208 m⁻¹` M4 +2.388080130362648, M3 +2.4732148709178685, M2 +2.5598510250834945; global signed cancellation remains high (~89 on last M4→M5), spatial convergence NOT established. This distinct M6 physical FEM will permit independent `ΔM6−M5` calculation and local 4D convergence diagnostics.

Exact regime **R/EDV_VAR/ξ=0/B6 5mm, 36×25s (900s), 4 threads**, fresh forward and same-mesh analytic Tet10 adjoint, signed4D 1200 bins×36 + 36 Robin; **no central FD**. Reuses successful unchanged P10JP M5 C++ solver/101-file source manifest revision `P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS`, source inventory SHA `dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc`, independent temporal QA SHA `547ebec5955c882507e707fe2604f43713ec15a4bf4323b659c3e1c6ff100`. **Only mesh and driver/watchdog changed, no physics parameters changed.**

## Private Windows package

`P10JW_M6_FIRST_FULL4D_WINDOWS_ONE_SHOT_PREPARED_20261124.zip`, SHA256 **`18055f52a095cd35b993bfd88752c93329db9c2741d695e46bf8ad017d6e77bf`**, ZIP CRC PASS 113 entries, size ~1.19MB. Delivered privately, M6 raw mesh not committed to public GitHub. Two one-click Windows CMDs:

1. `01_P10JW_M6_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd`: SHA101, exact M6 mesh, 27QP physical tags; then **real 65-second silent child through same Windows Job+PSAPI+output monitor as intended FEM**, independent watchdog thread every15s and persisted progress log. Must produce `P10JW_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS` with ≥4 ticks at approximately 0/15/30/45/60s and `P10JW_PREFLIGHT_AND_WATCHDOG_EXIT=0`. Repeatable (validated prior record reused); no FEM, no compilation, no one-shot marker. Writes `P10JW_WINDOWS_NATIVE_HEARTBEAT_SELFTEST.json`, with exact M6 SHA, watchdog source SHA, tick count, status; 02 independently checks it.
2. `02_P10JW_ONE_M6_FIRST_FULL4D_FEM.cmd`: **exactly once** after 01 PASS, separate new marker `G:\ildar\Stage3D07\LOCAL_RUNS\P10JW_M6_ONE_SHOT_MARKERS\M6_R_DT25_STEPS36_d581a498f79564e.json`, written **before native** and never rerun. Compiles unchanged MinGW C++ solver, runs native selftest, then fresh M6 forward/analytic adjoint, per-step signed4D QA and output ZIP.

Hard caps: native wall≤2400s, Windows Job private≤8GiB (free RAM≥12GiB, disk≥4GiB), output≤2GiB, 4 threads. Estimated user i7-7700K ~20–40min (not guaranteed). Archive to return **only `P10JW_M6_FIRST_FULL4D_EVIDENCE.zip`** from new `G:\ildar\Stage3D07\LOCAL_RUNS\P10JW_M6_R_DT25_*`; includes native log, 4D signed CSVs, analytic result/closure, manifest, **P10JW_PROGRESS_LOG.txt**, **P10JW_WINDOWS_NATIVE_HEARTBEAT_SELFTEST.json**. No M6 Gmsh, old M6 mesh R1 and M5 FEM one-shot remain consumed/never rerun.

## P10JQ heartbeat correction

M5 P10JP console heartbeat failure was a true defect: native progress from same thread as Windows Job attachment, private memory and output file enumeration. P10JW `P10JW_heartbeat.IndependentPulse` thread starts **before** creating Job and process, records 15-second ticks on disk and console, never calls Job/PSAPI/disk scan/log tail, has honest `native_step=unknown progress_unknown`. Main monitor also has 30s PID/RAM/log tails; phase preflight, compile, signed QA, ZIP have their own heartbeat wrappers. Preflight **real Windows Job silent 65s integration** must pass BEFORE marker; the same implementation is used for FEM. Actual assistant-side non-Windows source-only silent65s regression PASS **5 visible ticks** at 0/15/30/45/60s, persisted line audit; source-only 101 SHA and M6 27QP QA PASS, `py_compile` PASS, Linux --run negative STOP before marker, ZIP CRC PASS. **Windows native selftest and FEM have not run yet, so success on user machine remains unverified**.

Next P10JX upon private evidence: independent 43236-row closure QA and exact signed spatial M6−M5, polar N/S and nonpolar L1/cancellation, compare sequential M2…M6; no premature convergence claim. Preserve dt25s.
