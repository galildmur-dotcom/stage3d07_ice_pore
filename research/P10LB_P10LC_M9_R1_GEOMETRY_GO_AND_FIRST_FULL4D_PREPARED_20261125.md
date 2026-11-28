# P10LB/P10LC — accepted M9 R1 geometry and pinned first full4D Windows FEM

**Geometry GO; FEM package PREPARED, not executed; spatial convergence NOT established.**

## P10LA final canonical quality evidence

User supplied `P10LA_M9_R1_GMSH_QUALITY_RESULT.json`, SHA256 `32deaa36728a6ae02e75fe68cac75ec08fbe9a581b2eed91d1970dace62bf3c9`, Gmsh 4.15.2 exact M9 SHA256 `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58`, 13,166 Tet10, tags2–9, `quality_gate_pass=true`.

| Canonical Gmsh quality | M9 minimum | Gate | Verdict |
|---|---:|---:|---|
| minSICN | 0.2624622995 | ≥0.20 | PASS |
| minSJ | 0.4478454150 | ≥0.40 | PASS |
| gamma | 0.2414201891 | ≥0.15 | PASS |
| minDetJac | 5.9787468072e−13 | >0 | PASS |

No nonpositive quality entries. Independently P10KZ curved 27/343/729QP detJ positivity, CAD closure +6.881e−9 and exact physical tags PASS. Actual D029 M9/M8 near-p0 `Veff` ratio north **0.8044642495**, south **0.8103755821** (both `[0.75,0.85]` PASS); QP support and 343→729 stability PASS. The new `P10LB_M9_R1_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json` is derived from *both* independent reports, SHA256 `0aaf1fffb247717ef91f75472c79bc8e8fa7f4b4219b3ba8b4512373d93017b7`. Decision `GEOMETRY_GO_ONLY_NO_FEM`. M9 R1 Gmsh marker consumed; never rebuild the same one-shot.

## P10LC first real M9 full4D design

Package `P10LC_M9_R1_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261125.zip`, SHA256 `6726ae3db375818c86ac7d1e4407f2c96ef71c3f3e115afcc7b7d90cd49e958c`, **127 files**. It copies the pinned M8 P10KV C++ source/101-file solver SHA manifest and exact analytic geometry adjoint, replaces only the accepted mesh with M9 (`19,236 nodes/13,166 Tet10/734 pore Tri6`), pins the P10LB geometry passport and creates a *new M9-specific physical one-shot marker*.

- Regime **R/EDV_VAR/ξ0/B6 5 mm**, `steps=36`, `dt=25 s` (900s), `threads=4`, fresh forward + analytic same-mesh adjoint, six signed4D components `(r,theta,phi,t)`, independently checked full4D closure.
- i7-7700K predicted wall **20–35 min**; prior real M8 wall 1246.545 s and 12,546 Tet10, M9 13,166 Tet10 (~4.94% increase). Estimate only, not a guaranteed bound.
- Hard process wall cap **2400 s (40 min)**, 8 GiB private RAM and 2 GiB output cap, 15-s independent progress watchdog, Windows Job process containment + CPU telemetry (prior M8 mean ~2.08 busy logical cores ≈26% of eight, not proof of failure to request four threads).
- 101/101 solver pins PASS, Python compile/AST PASS, 27QP M9 mesh audit PASS (`nonpositive_samples=0`), ZIP CRC PASS, source-only preflight PASS; Linux `--run` STOP before marker/FEM. No FEM launched while preparing this package.

## Exact user instructions

1. Unpack ZIP into a **new folder**. First run `01_P10LC_M9_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd` (~65–80 s). Must print `P10LC_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS` and exit 0. This tests an actual silent native child for 65 s without compiling or launching FEM and without consuming a physical one-shot marker.
2. On success, run **exactly once** `02_P10LC_ONE_M9_FIRST_FULL4D_FEM.cmd`. The new M9 physical marker is consumed immediately before native launch. **After an error/STOP, do not repeat this same one-shot.**
3. Return only `P10LC_M9_FIRST_FULL4D_EVIDENCE.zip` from the new `LOCAL_RUNS/P10LC_M9_R_DT25_*` folder. No VTU/checkpoint/forward history uploads.

Next research gate after user evidence: independent M9−M8 signed4D cellwise differences, sign/cancellation, polar vs nonpolar, 31–36 late-time, and CPU telemetry versus M8. **Geometry GO does not imply spatial convergence.**

Tools: `research/tools/p10lb_m9_r1_final_geometry_gate.py`, `research/tools/p10lc_build_m9_full4d_windows.py`.
