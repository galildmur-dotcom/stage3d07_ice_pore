# P10HS — real P10HR matched native 2D verdict and bounded 3D M2 candidate preparation

Date 2026-11-24. User uploaded P10HR paired Gmsh and guard results. `MATCHED_2D_PAIR_CREATED_NEEDS_INDEPENDENT_VERDICT`, `WORKER_FINISHED`, code0, original pinned P10GT CAD and `Field[7]` identical. Native baseline 0.0982 s, adapted 0.2073 s, 5,093 adaptation callbacks, guard 1.25 s; no 3D/FEM/M2.

| Real native 2D measure | Baseline Field[7] | Direct 4D mechanical κ | Difference |
|---|---:|---:|---:|
| All surface triangles | 1,520 | 1,510 | −0.66% |
| Pore-wall triangles | 180 | 178 | −1.11% |
| B6 interface triangles | 350 | 342 | −2.29% |
| North polar wall triangles by corner-centroid group | 16 | 19 | +18.75% |
| South polar wall triangles | 19 | 19 | 0 |
| Nonpolar wall triangles | 145 | 140 | −3.45% |
| North median straight corner edge, mm | .4249716 | .4132121 | −2.77% |
| South median straight corner edge, mm | .3940391 | .3776014 | −4.17% |
| Nonpolar median straight corner edge, mm | .3940168 | .4084763 | +3.67% |
| Native worst gamma in log | .248937 | .438976 | improves |

No Gmsh error, wall coordinates lie on the original exact sphere. **Adjudication:** adaptation has a measured redistribution toward both poles, particularly north, and stable/improved native surface quality. It does **not** imply global densification; indeed overall triangles decrease. Two 2D runs are not evidence for the required 15–25% reduction of *actual local 3D curved Tet10 volume* at κ=1. There is no scientific basis to label an accepted M2 or start any FEM yet.

## P10HS once-only 3D candidate

The next necessary observation is the real 3D volume response. Prepared ZIP `research/proposals/P10HS_REAL_M2_CANDIDATE_3D_20261124/P10HS_R1_ONE_3D_M2_UNVERIFIED_CANDIDATE_WINDOWS_20261124.zip` (SHA256 `934851eaac0950b242400315ce04b0068b6e18e1a70d3da575e5d97640207420`, 214,897 bytes, CRC and source syntax verified) from exact original P10GT two-volume CAD, `Field[7]`, α=.17, direct original signed mechanical-only 4D κ. Exactly **one** `gmsh.model.mesh.generate(3)` for an *unverified candidate*, with a 600-second external process timeout and 4,000,000 callback cap, pore domain guards and Tet10-only structural check. Never FEM and never automatically accept M2.

On success, program saves `P10HS_M2_UNVERIFIED_CANDIDATE_EVIDENCE.zip`, bundling MSH2 ASCII Tet10 candidate, original-source fingerprints, Gmsh log, worker/guard reports. Do not hand it to any physical solver. If stopped, send guard/log/worker error. Estimated on user's i7-7700K 1–10 minutes and progress lines every 15 s, plus potential local Gmsh API wheel setup. Future independent audit must compare pinned original M1 and candidate with curved Tet10 QP343/729, geometry quality, both poles and nonpolar regions, actual volume reduction 15–25% near κ≈1, and smoothness before any scientific GO. No thermal adaptation coefficient is introduced.
