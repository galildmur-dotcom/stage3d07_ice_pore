# P10OW M16 first full signed-4D physical run — prepared 2026-11-27

M16 accepted after P10OT independent audit and P10OU native serialized reimport:
- M16 exact SHA-256 `b417aeb71193f38f706e11bf64a365cdc5708ff14580d9460f9bfc3bdf95b972`;
- 21,683 Tet10, 32,155 nodes, 2,286 pore Tri6;
- minSICN 0.263428; minSJ 0.749768; gamma 0.228039; minDetJac 5.379367e-14, 0 violations;
- independent 23,829,617 curved detJ evaluations all positive; boundary and topology PASS;
- Gmsh 4.15.2 P10OU reimport PASS.

## Scientific sequence

Before any M17 adaptation, **run M16 physical signed-4D FEM** so a true M16−M15 signed mechanical sensitivity indicator can be derived. No fabricated M17 κ from mesh data alone.

P10OW prepares a Windows 11 one-shot physical run derived from the existing independently guarded P10OP M15 full4D:
- Exact existing 101 pinned solver files (source revision `P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1`), unchanged native C++.
- Accepted M16 serialized mesh embedded and exact SHA; the P10OT and P10OU JSON attestation hashes embedded and checked.
- R / EDV_VAR / ξ=0 / j_peak / B6=5mm / 36×25s (900s) / 4 threads.
- Fresh forward and analytic same-mesh Tet10 adjoint, signed full4D mechanical+thermal and two explicit geometry/stress components. No geometric central FD.
- No Gmsh optimization/generation or FEM during preflight; distinct M16 persistent FEM one-shot marker in LOCALAPPDATA and LOCAL_RUNS before actual native invocation.
- Prior Windows native silent watchdog selftest 65s (15s independent heartbeat), 5400s time, 12GiB memory, 3GiB output cap.
- Strict independent postrun 36×1200-bin 4D temporal and explicit two-term closure QA. On failure, marker remains consumed; no automatic retry.
- Preflight locally verified source revision and full source hashes; accepted M16 SHA exact, 27-QP mesh QA 0 bad. Native Windows compile/FEM **not run here**.

One-click ZIP `P10OW_M16_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127.zip`, SHA-256 `5238ac8bdddd3eb306dfc2f07c448d0ded56c7a3283e16d0384d1d182be2ae68`.

[Download Windows P10OW](https://chatgpt.com/library?file_id=libfile_7bacbc58b900819196c1e7aa03c81922&account_id=personal)

User runs 01 preflight then 02 FEM **once**, returns P10OW M16 first full4D evidence archive. After verification and acceptance, prepare consolidated one-run M17 construction + mandatory HighOrderElastic + all independent gates as adopted in P10OV.
