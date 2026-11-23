# P10GO R1 — self-contained C¹ Gmsh sizing field, bounded Windows 1D

Date: 2026-11-23. **SOURCE PREPARED / NATIVE PENDING.** No new 2D, 3D, M1 or FEM data.

## Why this is the next scientifically isolated test

Pinned native P10GM found direct original `Background Field=3` complete in
0.510056 s, but its F6 and F7 composed-field cases stopped at 30 s.
Independent pinned P10GN D (`Field[7].F="F3"`) and E
(`Field[7].F="F3*0.94"`) each stopped at 30 s during 1D on circles 14/17.
Hence nested evaluation is an experimentally supported suspected trigger,
**not** proof of any general Gmsh implementation bug.

P10GO keeps the original rotated CAD and unchanged M0 size-field expression,
expanding the entire original 732-character `Field[3].F` expression directly
into the new 1198-character `Field[7].F` together with the P10GK alpha=0.06
C¹ south fade. The new size expression contains no `F3`, `F4` or `F5`
references. Gmsh `StrCat` assembles three literal pieces; original
`Mesh.MeshSizeFactor=0.9378887276834518` applies once. Original source and
frozen M0.msh remain untouched.

## Byte identity / source QA

- Frozen M0.msh SHA256: `926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6`.
- P10GK source ZIP SHA256: `4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05`.
- Gmsh 4.15.2 Windows EXE SHA256: `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`.
- Frozen D-027 SHA256: `2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea`.
- P10GO deterministic ZIP SHA256: `f9693dd164f70951321bfcc134e0b9b7f7bc65f9e291c684a3ec28ec693a1837`.
- `--selftest`: 10,201 samples; original F3 analytical error ≤3.036e-18 m;
  expanded field versus pinned original/P10GK exactly equal at all samples;
  south factor min=0.94/max=1.0; four C¹ seam tests PASS; minimum final
  target h=0.00040699863907558346 m; no cross-field references.
- Five independent mocked/source unit tests PASS (source tamper, reference
  removal, 30s RAM-capped `-1`, evidence ZIP without meshes, preflight age).

## One-shot Windows protocol and decision boundary

Download package `research/packages/P10GO_R1_SELF_CONTAINED_C1_1D_WINDOWS_20261123.zip`.
Extract to new `G:\ildar\Stage3D07\P10GO_TOOLS_R1`.
First run `01_P10GO_PREFLIGHT_NO_MESH.cmd` and verify `P10GO_PREFLIGHT_PASS_NO_MESH`;
within 24 hours run `02_P10GO_ONE_1D_SINGLE_FIELD_TEST.cmd` exactly once.
Two cases in fresh isolated directories: A direct original `Background Field=3`,
B single inlined `Background Field=7`. Each `-1 -nopopup -nt 2` at most 30s,
Windows job private RAM 8 GiB, live native log + 2s heartbeat. Independent
one-shot markers are consumed before native work. Do not retry even on STOP.

Submit exactly one `LOCAL_RUNS/P10GO_SINGLE_MATHEVAL_1D_*/P10GO_1D_PROBE_EVIDENCE.zip`.
Both 1D completions imply only a provisional **1D sizing-evaluator PASS**;
they do not certify mesh cardinality, element geometry, polar local effect,
3D HXT, or FEM. Timeouts preserve STOP. No -2/-3/FEM invocation authorized.

Frozen D-027 continues: global QV729 ratio 0.80–0.85, physical north/south
near-polar QV hard max 0.98 with sufficient N_eff, strict CAD/Tri6/Tet10 and
27/343/729QP positive detJ/gradation gates. Historical signed 18/18 is
diagnostic only, **not** an M0→M1 hard criterion. Until future independent
evidence and explicit approval: **M1 STOP; FEM 0**.
