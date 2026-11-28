# P10JU — M6 guarded first distinct Windows Gmsh 3D mesh-only PREPARED (2026-11-24)

## Scientific state and exact candidate source

P10JR accepted real M5 FEM and P10JS/JT β=.10 signed4D M6 κ and empirical smooth size calibration completed source-only. P10JU prepares **first distinct M6 mesh-only Gmsh** on exact original CAD; **NO M6 geometry is accepted and NO M6 FEM exists**. CAD files pinned original 3 GEO Include graph and same ten embedded pore CAD seeds as successful P10JN M5. Exact accepted M5 SHA `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`, carried as `M5.msh` only to verify the source predecessor. M5 itself is **not remeshed or reused as a volume template**; callback regenerates original CAD with cumulative factors CAD→M2→M3→M4→M5→M6. No M4.msh included; historical source fields are pinned. M6 incremental h6/h5 `exp(−.1435943053641514 κ_M6 −.14988856005128548 W_N −.12933181019892748 W_S −.10 L_wall)` from P10JT; h6/h5 source proxy .75…1 at 396 samples. Target polar effective volume **.65 empirical only** until real M6 evidence audit.

Source hashes pinned in guard for 20 files, including P10JS adaptive bins SHA `3ad57340cf3972e30126cd42c289e263bcdcb91e60e5d27a71e3933fbca53645`, P10JT QA SHA `caef6571afe27e28584327e342456bb1e4437961b0c3ca319e1419f1d427b914`, worker SHA `f268be1fec2a89a05accfa02e5904d3007793a0c226e6872a524661285c7823d`; exact GEO transitive include graph expected three, source check occurs **before** marker/native.

## Private user-deliverable

`P10JU_R1_M6_GUARDED_MESH_ONLY_WINDOWS_20261124.zip`, SHA256 **`e271c343537339d482697010ca760f37ca175b5483bf9ce9c7e3d12a3f7a0640`**, ZIP CRC PASS, 24 files, ~1.48MB. Private download to user, not public GitHub. Contains accepted M5, original three CAD files, 10 preserved seeds in source, cumulative size source, P10JT M6 QA and P10JS κ source, two CMD and guard, no FEM. User Windows11 Python Gmsh API4.15.2:

1. In **fresh folder**, double-click `01_P10JU_PREFLIGHT_AND_NATIVE_HEARTBEAT_TEST_NO_GMSH_NO_FEM.cmd`. SHA20/GEO3/API check, then a real silent Python child 65s run through **the same process monitor** while a **separate watchdog thread** prints at 15s, 30s, 45s, 60s; requires `P10JU_WATCHDOG_SELFTEST_PASS` and exit0, **no marker/Gmsh/FEM**, repeatable. Takes ~65–75s.
2. Only after PASS, double-click `02_P10JU_ONE_M6_MESH_ONLY.cmd` **exactly once**. New local `P10JU_R1_ONE_M6_ATTEMPT_CONSUMED.marker` and cross-folder LOCALAPPDATA profile marker `P10JU_R1_M6_91b26a9a5dcc054e_ONE_ATTEMPT.marker`; consumed before native. **NEVER REPEAT R1**; old P10JN M5 mesh and P10JP M5 FEM markers also consumed and unrelated.
3. Return only `P10JU_R1_M6_UNVERIFIED_EVIDENCE.zip` created next to CMD. Contains marker, guard result, Gmsh log, worker JSON or error and candidate mesh; still **unverified**.

Gmsh native4.15.2, 4 threads, expected ~15–180s on i7-7700K (not guaranteed); wall≤900s, monitored private≤8GiB, log≤32MiB, mesh≤250MiB, callback≤1.5e6, FEM=0.

## P10JQ robust watchdog implementation and checks

P10JP previous FEM heartbeat absent in user's real Windows despite phase-only synthetic tests. P10JU uses **independent Python thread** `p10ju_progress.Watchdog` (15s) that never calls native monitor, RAM API, disk stats, Gmsh callback or stdout, and starts **before** source preflight and child Popen. Main monitor separately prints PID/RAM/actual log tail and enforces resource limits. Independent watchdog outputs honest `native_step=unknown` when native is silent. Actual Linux 65.1s subprocess silent-child test **PASS 4 independent beats**, main native monitor ~30s/60s, no marker/mesh/FEM. `py_compile` of guard/worker/progress PASS, source SHA20 and GEO3 preflight PASS, Linux `--run` negative STOP before marker, ZIP CRC PASS. **Windows integration has not been run by assistant**; the user's 01 preflight explicitly tests live Windows 65s child in the new package before allowing 02. Do not claim Windows heartbeat already observed.

## Geometric acceptance only after evidence

Independent **all curved Tet10 D031**: Gmsh minSICN≥.20, minSJ≥.40, gamma≥.15, minDetJac>0, independent detJ at27/343/729QP>0, CAD closure relative ≤1e−6, physical surface tags2–9, pore Tri6; neighbour size-jump diagnostic only under D030. Independent **D029**: same fixed physical polar regions d≤.5mm |μ|≥.8 60 bins each; actual curved 729QP M6/M5 effective-volume ratios N,S each [.50,.75], Neff≥30 and quadrature stability. If passes accept M6 as geometry only, then independently prepare signed4D M6 FEM on 36×**25s**, same-mesh direct+analytic adjoint. Never declare spatial convergence from global signed cancellation alone. Large private raw mesh/4D remain out of GitHub.
