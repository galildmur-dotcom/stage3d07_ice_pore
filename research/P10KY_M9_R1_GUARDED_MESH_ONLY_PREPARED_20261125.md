# P10KY — M9 R1 distinct guarded Windows mesh-only (25 Nov 2026)

**PREPARED, NOT EXECUTED.** No M9 Gmsh or FEM run; no Windows one-shot marker consumed. M8 R3 FEM and earlier M8 R3 mesh one-shots remain **CONSUMED**, never repeat them.

## Inputs

- Accepted M8 R3 mesh: `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d` SHA256, 12,546 Tet10 and 648 pore Tri6 (geometry accepted P10KU).
- New P10KX M9 1200-bin positive signed4D priority source: `ddf7adeaeffffdab480c8bee5b234998236c53a1320aed511d6da20f0c09957f` SHA256.
- Preserve exact original rotated CAD + three-include closure, ten embedded pore seed directions, physical tags 2–9, and **full cumulative previously accepted M8 callback**. Append only `incremental_m9 = (1−0.20*kappa9)^(1/3)` with the established C² polar plateau and compact smooth positive 3D field.
- Guard source pins: 34/34; files in package: 38; no solver binary or FEM invocation. The user will need Windows Python with NumPy and Gmsh Python API 4.15.2 as before.

## Package and computer resource limits

`P10KY_M9_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip` SHA256 `6e65d4c512a15a50928fe2d7c9ddab5ec7b91cd28c28765bb79bc5bf2422b10b`.

1. Extract into a **new folder**. Run `01_P10KY_M9_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd` first. It checks pins, includes, Gmsh Python API version, existing marker/output, and 65-s silent native-child heartbeat monitor. It **must** produce `P10KY_WATCHDOG_SELFTEST_PASS` and exit 0; it neither generates a mesh nor consumes any marker.
2. Only after pass, run `02_P10KY_ONE_M9_R1_MESH_ONLY.cmd` **exactly once**. Expected mesh generation 20–240 s on i7-7700K (estimate only; prior M8 R3 was ~23.5 s), *hard cap 1200 s*, max monitored private 8 GiB, 4 Gmsh threads, max mesh file 250 MiB and native log 32 MiB. Independent watchdog 15 s and separate Gmsh heartbeat 15 s. Unique per-folder **and** persistent user-profile marker is created before Gmsh launch. After a STOP, do not retry this one-shot.
3. Return exactly one `P10KY_R1_M9_UNVERIFIED_EVIDENCE.zip` (includes mesh, guard/worker results, markers/logs); do not return VTU or raw solver data. No FEM involved.

## Geometry gate after the user return

M9 mesh remains *unverified* until independent D029/D031: canonical Gmsh minSICN≥0.20, minSJ≥0.40, gamma≥0.15, positive curved Tet10 Jacobian at 27/343/729 QP, CAD volume/tag parity, 343→729 drift, and actual regional near-p0 effective volume ratio **M9/M8 ∈ [0.75,0.85] on each pole**. One-shot marker may not be reset to repair a rejected candidate; a new distinct revision is required. The nominal size factor alone cannot establish geometry GO.

## Preflight disposition

- 34/34 SHA and 3 GEO includes source-only preflight PASS (no Gmsh imported).
- Python compile/AST worker and guard PASS; distinct marker names and output paths asserted by builder.
- Linux `--run` negative test STOP before any marker/Gmsh (Python Gmsh unavailable, no mesh).
- Real 65.1-s silent-child monitor/heartbeat test **PASS**: four independent 15-s watchdog beats, plus Gmsh-monitor simulation beats at 0/15/30/45/60 s; no marker, mesh or Gmsh run. The same resource polling was exercised while native child produced zero output.
- ZIP CRC PASS, Python compile PASS, 38 files, 4,874,036 bytes, SHA256 as pinned above.

Builder: `research/tools/p10ky_build_m9_r1_guarded_windows.py`. The full package is a user-facing immutable artifact; do not commit its binary M8 mesh or Windows ZIP to the public repository.
