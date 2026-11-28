# P10JQ — P10JP observed FEM heartbeat failure, nonintrusive live monitor (2026-11-24)

## User observation, live state

On actual user PC during **already running one-shot P10JP M5 FEM**, console displayed:

```
P10JP_ONE_SHOT_M5_FEM_START do not run a second time
P10JP_START stage=source_and_mesh_preflight
P10JP_PREFLIGHT_START elapsed_s=0
P10JP_M5_PREFLIGHT_PASS_NO_FEM ... tet10=10826 dt_s=25 steps=36
P10JP_PREFLIGHT_END elapsed_s=2.5
P10JP_BUILD_PHASE: first compile/selftest, no FEM yet
P10JP_BUILD_START: compiling or verifying native solver
P10FR_COMPILING: Qt MinGW bin added to PATH: C:\mingw64\bin
P10FR_COMPILER_LOG: G:\ildar\Stage3D07\LOCAL_RUNS\P10FN_BUILD\P10FN_BUILD_20261124_152238_031179.txt
P10FR_COMPILE_SUCCESS: running EXE guard selftest
P10JP_BUILD_READY elapsed_s=21
P10JP_FEM_START: one-shot M5 900s physical 36x25s wall_limit_s=2400 memory_limit_GiB=8.0
```

User reports no further text during active FEM. If ≥30s elapsed this **violates mandatory P10JH heartbeat**; regard the P10JP all-phase visible progress claim as **NOT VALIDATED ON WINDOWS NATIVE FEM**. Native FEM exit status and completed steps are **UNKNOWN**, not claim STOP nor PASS. **Do not rerun consumed P10JP M5 FEM** and do not ask user to stop currently running FEM.

## Root-cause analysis, not established

Inspected exact P10JP_heartbeat.py. During native FEM, `P10JP_FEM_START` prints before spawning; subsequent `job.assign(proc.pid)`, `private_bytes(proc.pid)`, recursive output enumeration and log-tail are executed **on same thread as heartbeat**. A slow/stalled monitor call can prevent any `P10JP_FEM_HEARTBEAT` even while native child runs. This is a concrete design flaw but **not evidence of which exact call stalled** on the user's Windows session. Earlier 65-second synthetic source-only heartbeat test exercised `phase_with_heartbeat`, NOT the Windows Job / native run monitor; calling that test proof of native progress was incorrect.

## Immediate safe workaround: independent separate monitoring window

Private read-only `P10JP_READ_ONLY_LIVE_MONITOR_20261124.zip` SHA256 **`8e77f0b21f207443f14663ce48b93ab7a7fdf72118025ca5c78f74d1d31a1de9`**, CRC PASS. Includes `01_P10JP_START_READ_ONLY_MONITOR.cmd` and `P10JP_LIVE_MONITOR.py`. User can run **in a second window while original FEM keeps running**. Every **15 seconds** independent process prints timestamp, elapsed, latest `G:\ildar\Stage3D07\LOCAL_RUNS\P10JP_M5_R_DT25_*` run, file count/size, P10JP native log byte count and latest text line, and OS `tasklist` process status/PID/memory (best effort). `none_reported` not proof of completion. Once P10JP_MANIFEST.json appears, reports final status and quits. **Read-only**, no Gmsh, no compilation, no FEM, no one-shot marker, no signals to native process, no files written.

Validation: `py_compile` PASS, Linux 2-second smoke test yields immediate status with no launch, ZIP CRC PASS. Actual Windows monitor output and underlying FEM state **not yet observed**.

## Permanent requirement for next guarded Windows FEM package

P10JH must be enforced as *Windows native integrated test* and independent dedicated heartbeat thread/process, not merely a sequential poll in the same loop. In particular:
- Immediately after printing FEM START, spawn a watchdog heartbeat independent from potentially blocking `Popen`, Windows Job attach, RAM query, directory scans and native stdout; heartbeat continues ≤30s while child is silent.
- All monitor calls bounded, exceptions isolated; never claim exact steps unless parsed real output, use `step_unknown`. Include PID/alive and log bytes / last change.
- 65s silent native child **under the real Windows Job and native monitor implementation** must yield ≥2 externally observed beats, in addition to phase-only test. P10JP earlier synthetic test not sufficient.
- Preserve exact M5 one-shot marker and never run fresh FEM without a genuinely new sanctioned scientific stage; do not alter active run.
- Upon returned P10JP evidence, independently audit signed4D and M5−M4 (D_R jpeak), do not conclude convergence prematurely.
