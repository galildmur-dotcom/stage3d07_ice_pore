# P10KQ — distinct M8 R2 guarded Windows mesh-only candidate (2026-11-25)

**PACKAGE PREPARED, REAL WINDOWS GMSH NOT RUN; FEM=0.** This is a wholly new M8 R2 attempt, not a retry of P10KN M8 R1 (consumed/STOP). Preserve exact accepted M7 R2 SHA `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d`, original CAD, ten embedded seeds, physical tags, and cumulative M2–M7 callback. Only the incremental M8 multiplier changes from `(1-0.2*kappa0)^(1/3)` to `(1-0.2*kappa_R2)^(1/3)` using P10KP's C2 plateau.

Packaged input contains exact P10KM priority SHA `235fc2e0e31d7e55dbf6d1d3ed4a127ca11903cf12a038ee1561006cc0134766` and P10KP real-field QA, 31 source SHA preflight checks, three GEO includes. Unique local `P10KQ_R2_ONE_M8_ATTEMPT_CONSUMED.marker` and cross-directory LOCALAPPDATA marker `P10KQ_R2_M8_875c9177de24612d_ONE_ATTEMPT.marker`; former P10KN R1 marker unaffected. Guard performs only mesh creation (never FEM), independent 15-second progress, wall 900s, RAM 8 GiB, log 32 MiB, mesh 250 MiB, Windows Gmsh Python API 4.15.2 requirement.

Source-only checks: 31/31 pinned inputs PASS, three GEO includes PASS, Python compile PASS, archive CRC PASS, non-Windows/absent-Gmsh `--run` STOP before marker (no attempt). Linux independent actual native-monitor 65.1s silent-child regression **PASS: four watchdog beats at 15/30/45/60s**, no marker or mesh. This Linux test does not substitute for native Windows result. The expected mesh run is approximately 15–180 s on the user's i7-7700K but has a hard 900s bound. No new mesh/FEM result has yet been produced.

Prepared archive: `P10KQ_R2_M8_GUARDED_MESH_ONLY_WINDOWS_20261125.zip`, SHA256 `591a31cd3fbc185b776b557d322b115f47ffb8eac193abeb5a819b3d4f9fd29b`, 35 files, size 3,990,978 bytes; no FEM code or one-shot marker included.

User instructions after delivery:

1. Extract to a NEW folder, leaving all earlier run folders and consumed markers intact.
2. Execute `01_P10KQ_M8_R2_PREFLIGHT_AND_HEARTBEAT_TEST.cmd` (about 65–80 seconds). Demand `P10KQ_WATCHDOG_SELFTEST_PASS` and exit0. No Gmsh, FEM or marker is consumed by this test.
3. Only after preflight PASS execute **exactly once** `02_P10KQ_ONE_M8_R2_MESH_ONLY.cmd`, then never retry after marker consumption, even on STOP.
4. Return only `P10KQ_R2_M8_UNVERIFIED_EVIDENCE.zip` for independent D031 curved 27/343/729QP, Gmsh SICN/SJ/gamma, CAD closure and tags; D029 actual near-pole Veff M8R2/M7 N and S must each be in `[0.75,0.85]`. FEM remains blocked until independent GO.

Reproducible package builder: `research/tools/p10kq_build_m8_r2_windows.py`, with exact pinned P10KN archive and P10KP QA as inputs. No private raw 4D state/large physical outputs are published in Git.
