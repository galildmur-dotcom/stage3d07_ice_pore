# P10KG — M7 R2 distinct guarded mesh-only Windows package (2026-11-25)

**Status:** `P10KG_SOURCE_ONLY_PREFLIGHT_PASS_PACKAGE_PREPARED_NOT_RUN`. No native Gmsh mesh generated, no FEM. On local source-only QA, **26 immutable SHA-pinned inputs passed**, transitive three-file CAD/GEO include graph passed, Python source `py_compile` passed and ZIP CRC passed. On Windows, separate 65-second real silent-child heartbeat test remains mandatory before the one-shot.

## Scientific hypothesis and caps
Actual M7 R1 was refused: D031 one Tet10 7442 minSICN **0.16262 < 0.20**, isolated internal cell (zero pore surface faces; four face neighbors minSICN ≥0.4045), and D029 actual Veff M7/M6 **0.952659 N / 0.935660 S**, below the desired 15–25% local volume decrease. Independent P10KF local study showed the failed cell lies outside intense local additional κ, so do not infer poor shape from pointwise excessive refinement.

The new source-only P10KE **C² polar collar** broadens radial support to 0.8mm, retaining original CAD, 10 embedded CAD seeds and complete accepted M6 size callback. It applies

`wθ=s5((|μ|−.68)/.18)`, `wr=1−s5((d_mm−.30)/.50)`,

`κ_R2=1−(1−κ_R1)(1−wθ wr)`, `h7R2/h6=0.80^(κ_R2/3)`.

This imposes at most 20% local **source volume proxy** reduction, linear size factor ≥0.92832. P10KE's near-polar M6-QP-weighted cube proxy was ~0.802 N and ~0.802 S. **None of this proves the real M7 R2 will meet D029 or D031**.

## Package and execution
`P10KG_M7_R2_GUARDED_MESH_ONLY_WINDOWS_20261125.zip`, SHA256 `0cc7613858ec72fd49fc71c676ef3217ea0a6e457287e25f47fe96fa424e9fe3`, CRC PASS, 30 files, accepted immutable M6 reference SHA `d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0`, immutable **unaccepted** M7 R1 SHA `6867fbafefa7efbbd00ce4aaa70a673c5bab40385fa2d0abae2be310a6eb4865`. The original consumed P10KB R1 marker is never reset.

1. Extract all files into a **new** folder on Windows 11. Requires Python + NumPy + exact Gmsh Python 4.15.2.
2. Double-click `01_P10KG_PREFLIGHT_AND_HEARTBEAT_NO_MESH.cmd`. SHA26, GEO3, Gmsh API and independent real 65-second silent-child watchdog test. **No Gmsh mesh or FEM, no attempt marker**.
3. On PASS, double-click `02_P10KG_ONE_M7_R2_MESH_ONLY.cmd` exactly **once**. Distinct local + LOCALAPPDATA profile R2 one-shot markers consumed before native Gmsh. Maximum wall 900 s, private memory 8GiB, native heartbeat and independent watchdog every **15s**, even when native Gmsh emits no stdout. Expected Gmsh 20–180 s based on R1 19.9 s, but not guaranteed.
4. Return ONLY `P10KG_R2_M7_UNVERIFIED_EVIDENCE.zip` (contains mesh if successful, and log/guard/error if stopped). **Do not repeat** after one-shot marker consumed.

## Next strict QA
M7 R2 is only a candidate until independent read-only D031 (all Tet10 minSICN ≥.20, minSJ≥.40, gamma≥.15, 27/343/729 QP positive curved detJ, CAD volume closure/physical tags) and *independent* D029 actual 729-QP regional Veff M7 R2/M6, supported North/South/nonpolar. A D029 target miss is not the same as a D031 geometry STOP. If either fails, no FEM and no replay of old marker. Future physics keeps **36×25s**, 4D signed output, CPU-time/wall telemetry and independent progress during the solve.
