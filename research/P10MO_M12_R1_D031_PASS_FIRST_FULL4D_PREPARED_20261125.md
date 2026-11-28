# P10MO — M12 R1 fully geometrically accepted; first FEM package prepared

Date 2026-11-25, research branch `research/p10bb-w5b2-20261118`.

User-provided canonical Gmsh 4.15.2 D031 `P10MN_M12_R1_GMSH_QUALITY_RESULT.json` matches exactly M12 R1 SHA256 `e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13`, 16,333 Tet10, physical surface tags 2–9, no Gmsh generation, no FEM. Quality minima: minSICN `0.22608267408471253` >=0.20, minSJ `0.4219885719105649` >=0.40, gamma `0.22417081405846132` >=0.15, minDetJac `2.323514461821726e-13` >0. No nonpositive qualities. D031 PASS.

Prior independent D029 27/343/729QP curved Tet10 geometry PASS. M12 R1 729QP detJ `2.3272344438727416e-13`, CAD closure relative `6.777452155048991e-09`, actual near-pole Veff ratios M12/M11: north `0.8278868903845451`, south `0.7780359129672213` (17.21% / 22.20% reduction).

**M12 R1 FULL_GEOMETRY_GO.** This is a geometric decision only; no FEM or spatial convergence established for M12 yet. Consumed M12 R1 mesh-generation marker must not be rerun.

`research/tools/p10mo_build_m12_r1_first_full4d_windows.py` produced separately guarded Windows ZIP `P10MO_M12_R1_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261125.zip`. It contains the exact accepted M12 mesh, immutable geometry passport, unchanged 101 SHA-pinned solver sources, distinct P10MO local/profile one-shot FEM marker, independent 65-second Windows Job heartbeat preflight, signed 4D temporal audit and explicit geometry-vs-stress sidecar closure. Regime unchanged: R/EDV_VAR, xi0, B6=5 mm, 36×25 s, 4 threads; 2400 s hard wall, 8 GiB RAM, 2 GiB output. Expected completed user archive: `P10MO_M12_FIRST_FULL4D_EVIDENCE.zip`.

Offline complete source and mesh preflight PASS; C++20/OpenMP syntax-only compile PASS; archive integrity PASS. Actual Windows watchdog **pending**; physical FEM attempts 0, P10MO marker unconsumed. No repeat of consumed physical markers P10MI/M11 or mesh markers P10ML/M12.
