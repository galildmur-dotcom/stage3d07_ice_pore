# P10KC/P10KD — real M7 mesh-only independent D031/D029 STOP (2026-11-24)

**Status: M7 GEOMETRY_STOP_D031, independent D029 ADAPTATION_TARGET_MISS. NO FEM.** User supplied `P10KB_R1_M7_UNVERIFIED_EVIDENCE.zip`; CRC PASS, exact five files and one-shot marker CONSUMED. Native guarded Gmsh 4.15.2 exit0, 19.899s mesh, 21.022s guarded wall, 11,673 Tet10, 542 curved pore Tri6, 10 CAD embedded seeds, 31,070 size callbacks, zero FEM. M7 SHA256 `6867fbafefa7efbbd00ce4aaa70a673c5bab40385fa2d0abae2be310a6eb4865`; accepted M6 `d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0`. **Never rerun P10KB R1 or delete one-shot marker.** Gmsh's success means generated mesh, NOT geometry acceptance.

## Independent read-only geometry
Our standalone parser + independent full Tet10 27/343/729 QP + Gmsh read-only minSICN/minSJ/gamma evaluated both actual M6 and M7.

| Metric | accepted M6 | M7 candidate | D031 |
|---|---:|---:|---|
| Tet10 | 11,628 | 11,673 | informative |
| minSICN | **0.282766** | **0.162623** | **FAIL** (threshold ≥0.20) |
| minSJ | 0.547626 | 0.412089 | PASS ≥0.40 |
| gamma | 0.158995 | 0.225483 | PASS ≥0.15 |
| all 27/343/729 QP Jacobians | positive | positive | PASS |
| CAD integrated volume closure | PASS | PASS | PASS |

Exactly **one** M7 element has minSICN below 0.20. Independently located element **7442**: SICN 0.1626225147, corner centroid `(0.0008776081, -0.0000833623, 0.0293257186) m`; distance to spherical pore wall **0.109865 mm**, polar μ **−0.607535** (southern intermediate latitude, **not** at the polar tip). Tet10 corner node IDs `7889,7548,932,1117`. The 6 corner-edge lengths are about `[0.490,0.441,0.515,0.562,0.268,0.380] mm`. No M6 element violates SICN 0.20.

This single bad cell is a **hard geometric STOP**, even though the minimum Jacobians remain positive; the independent curvature check must not be weakened.

## Independent physical D029 size target
M7 uses source-only 20% *local cell volume* reduction nominal `h7/h6=0.8^(κ/3)`, which is merely an input target; actual local Tet10 Veff measured using 729QP. The requested physical 15–25% relative reduction corresponds to actual ratios **[0.75,0.85]** in sufficiently supported source-priority regions. Observed:

| region | actual Veff(M7)/Veff(M6) | actual size change | sampled Neff M7 |
|---|---:|---:|---:|
| Near-pore north polar cap (r≤0.5 mm, |μ|≥0.8) | **0.952659** | **−4.73%** volume | 633.9 |
| Near-pore south polar cap | **0.935661** | **−6.43%** volume | 654.5 |

Both are **D029 target MISS**, *separate* from the D031 geometric STOP. 343QP/729QP relative drift around 0.1% in the northern cap, sufficiently stable numerically. At nonpolar and farther shells some actual Veff even increased despite source field refinement, owing to remeshing.

## Next safe scientific step P10KE (source-only)
1. Localize local CAD and Gmsh transitions around element 7442 and node set; propose a smooth **separate** C² mitigation *without claiming a priori that it repairs Tet10*.
2. Diagnose why existing maximum 20% cube proxy led to only 4.7–6.4% actual pole response; empirical response and indirect Gmsh topology redistribution cannot be equated with source proxy. Do not automatically crank up amplitudes to force 20%; user requested 15–25% volume adaptation and geometry smoothness.
3. Keep the original CAD, accepted M6 mesh SHA and prior physical source immutable. New **distinct** guarded mesh-only candidate, after fresh source preflight, then independently D031 and D029. No M7 FEM and no reuse of consumed P10KB marker.
4. Later legitimate FEM runs must use 36×25s, display independent heartbeat every 15s and process CPU-time/wall telemetry; four-thread underutilization from M6 remains unproven until profiled.

Independent script: `p10kc_independent_m7_geometry_audit.py`; bad-cell localization: `p10kd_local_bad_tet10_diagnosis.py`. Outputs: `P10KC_M6_M7_INDEPENDENT_D031_D029.json`, `P10KD_LOCAL_BAD_TET10_D031.json`.
