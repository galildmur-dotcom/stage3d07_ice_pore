# P10JN — first distinct M5 guarded Windows 3D mesh-only PREPARED, NOT RUN (24.11.2026)

## State and scientific parameters

P10JK real M4 FEM full4D PASS, global M3→M4 signed increment −.08513474055522 m⁻¹ not yet converged. P10JL source-only β=.10 continuous normalized C² Wendland κ(M5) calculated from 1200 bins×36 steps, P10JM calibrated independent C² size profile for M4→M5:
`h5/h4=exp(-.1435943053641514 κ_M5−.16557590838083475 W_N−.13829670885440187 W_S−.10 L_wall)`. Nonpolar κ remains active. The empirical proxy ratio .65 N/S has **not** been verified as actual M5/M4 supported Veff. Original CAD and ten embedded surface seeds unchanged. Old mesh profile exact M4 from successful P10IY is preserved and multiplied by M5 factor, i.e. callback reconstructs base CAD→M2→M3→M4→M5 cumulative size rather than trying to remesh existing M4 directly. M4 SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`.

## User-deliverable private package

`P10JN_R1_M5_GUARDED_MESH_ONLY_WINDOWS_20261124.zip`, SHA256 `eacf9a54adf33f12258bd653a64cb61e40172915a11f828139eb8dcd1e931296`, ZIP CRC 22 entries PASS. Private only, includes pinned M4.msh, 3 original GEO includes, 10 embedded seeds hardcoded unmodified, source P10HA/P10IM/P10IT/P10IX/P10JL/P10JM and guarded worker, no private raw M5 candidate yet. **No M2/M3 mesh files needed in this new archive**; the base cumulative callback is reconstructed from pinned source fields. P10JN guard checks exact 17 SHA files and recursive 3 GEO Include graph before marker/native.

Top-level Windows CMDs:
- `01_P10JN_PREFLIGHT_NO_GMSH_NO_FEM.cmd`: repeatable SHA17/GEO3/Gmsh Python4.15.2 verification, no marker, no mesh, no FEM.
- `02_P10JN_ONE_M5_MESH_ONLY.cmd`: **one time** Windows only after 01 PASS, distinct local/profile one-shot marker `P10JN_R1_ONE_M5_ATTEMPT_CONSUMED.marker`, unique across folders; 3D native Gmsh4.15.2, Tet10 only, physical pore Tri6, 10 embedded points, 4 threads.

Hard resource policy: wall ≤900s, native observed private≤8GiB, log≤32MiB, mesh≤250MiB, callbacks≤1.5 million; FEM=0, accepted_M5=false until independent audit. Expected native Gmsh ≈10–120s on i7-7700K, not guarantee. Worker candidate `P10JN_M5_R1_CANDIDATE_UNVERIFIED.msh`; guard creates one `P10JN_R1_M5_UNVERIFIED_EVIDENCE.zip` with marker, JSON, log, worker report/error and candidate mesh. Return only this ZIP.

## P10JH real all-phase visible progress

P10JN guard emits immediate START before checksum scanning, sha i/17 progress on preflight, Gmsh START and native-independent heartbeat at t≈0,30,60… seconds with phase, pid/alive, elapsed, measured peak private MiB, log/mesh bytes, time since last log change and real log tail or explicit `native_step=unknown`; END/STOP and package START/END. Uses Python unbuffered `-u`; CMD leaves window open. This closes prior silent-window problem for M5 even if native Gmsh writes no new lines.

**Local source-only tests PASSED**, without Gmsh generation or FEM:
- `py_compile` guard/worker/heartbeat tester PASS;
- P10JN preflight 17/17 SHA, 3 GEO includes, Gmsh Python 4.15.2 API check PASS;
- intentionally silent child 2.5s at compressed 1s heartbeat emitted 3 distinct heartbeats, native stdout lines0, PASS;
- Linux negative `--run` STOP before marker, no mesh, PASS;
- ZIP CRC PASS. **Native M5 Gmsh=0, native M5 FEM=0** as of preparation.

## Mandatory next independent audit

When user returns evidence, independent read-only QA all curved Tet10:
- Gmsh `minSICN≥.20`, `minSJ≥.40`, `gamma≥.15`, minDetJac>0 all elements;
- independent 27/343/729QP detJ>0, CAD volume closure |rel|≤1e−6, surface physical tags2–9, pore Tri6;
- regional D029 actual `Veff(M5)/Veff(M4)` supported physical polar N and S ∈[.50,.75], N_eff≥30 each, 343→729 QP stable;
- D030 neighbour q only diagnostic, not a hard gate.
If either D031 quality or D029 adaptation fails, distinguish statuses; do **not** automatically FEM. Source-only repair and new independent one-shot marker if necessary. If both pass, M5 geometric GO allows preparation of next full4D R/dt25 FEM; one-shot markers P10IY/P10JF/P10JN must never be reused.

Private mesh/ZIP not committed to public GitHub; reviewed worker, guard and heartbeat selftest published in `research/scripts`.
