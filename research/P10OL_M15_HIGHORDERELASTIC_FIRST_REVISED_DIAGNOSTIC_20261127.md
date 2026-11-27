# P10OL — HighOrderElastic-first M15 Gmsh optimizer diagnosis (replaces unrun P10OK)

User correctly recalled previous M13 evidence that `HighOrderElastic` was useful. The earlier P10OK two-method test omitted it. The corrected package starts with a **fresh-copy HighOrderElastic trial**, before the volume optimizers. Since M15 remains unaccepted (minSICN 0.150975 < 0.20, minSJ 0.314690 < 0.40, 2 and 5 failing Tet10), no FEM is permitted.

[Download revised P10OL Windows ZIP](https://chatgpt.com/library?file_id=libfile_1fd071e1703c81918f30e00100d14e21&account_id=personal)

Artifact: `P10OL_M15_THREE_OPTIMIZERS_WINDOWS_20261127.zip`, 1,426,664 bytes, SHA256 `19d7d7ea86c240be14a4dc6f7bc34048a62ce04728724d65d1bb86b81878025d`.

For each method, reopens the exact original M15 mesh SHA `fe16a9a0cff4a6496030e5b9c02dd7cadacaa8a2ac7754a5395518e98fe2eeb9` independently:

1. `HighOrderElastic` only;
2. `Netgen`, then `HighOrder`;
3. `Relocate3D`, then `HighOrder`.

Captures native quality metrics, worst-12 Tet10 with centroid/polar coordinates, physical Tri6 boundary connectivity and boundary coordinates before and after, candidate mesh SHA per method. Rejected candidates are not promoted automatically even if the native gate passes: independent curved 27/343/729QP, surface topology, physical tags and reimport remain required. No FEM, no CAD mesh generation. Three isolated subprocesses, each max 900 s, 15 s heartbeat, new distinct one-shot markers.

Operator: if **P10OK has not been run**, use P10OL *instead*, not both. Double-click `01_P10OL_PREFLIGHT_NO_GMSH.cmd` then after PASS once `02_P10OL_ONE_THREE_OPTIMIZERS.cmd`. Return `P10OL_M15_THREE_OPTIMIZERS_DIAGNOSTIC_EVIDENCE.zip`.

Local Python syntax and ZIP CRC passed. Native Windows optimizer behavior not yet tested.
