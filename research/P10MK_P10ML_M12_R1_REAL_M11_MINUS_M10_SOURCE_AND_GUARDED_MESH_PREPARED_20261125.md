# P10MK/P10ML — M12 R1 real M11−M10 4D source and Gmsh-only package

Date 2026-11-25. Based on accepted M11 R2 full4D `P10MI` and independent P10MJ real 4D alignment.

## Adaptation source P10MK

Physical source: aligned M11 R2−M10 true signed 4D data (36×25 s, 43,200 volume bins, 1200 spatial bins). M10→M11 L1 0.7222589721609709 per m, and last six temporal steps 57.2866% of L1. Script `research/tools/p10mk_m12_source_from_real_m11_m10.py` uses established P10KX source-only builder and pinned coordinates and retains established C2 compact interpolation.

Indicator per spatial bin is `(0.4 * all-time_L1/max + 0.6 * last-six_L1/max) * (1.2 near either pole else 1.0)`; normalized, positivity-preserving and C2. The 10 strongest source bins are `[0,0,9]`, `[0,9,7]`, `[1,9,3]`, `[0,0,6]`, `[1,0,6]`, `[1,9,9]`, `[0,0,7]`, `[1,0,1]`, `[2,9,8]`, `[0,9,11]`, indexed by radial, mu, phi. Source CSV SHA256 `e779145ae4ffd37677b3d05c2b214d4b2f09520504c20bd4e8271f96e4b3c03f`. Output source-only QA PASS without Gmsh, FEM or markers.

## One-shot mesh candidate P10ML

Builder `research/tools/p10ml_build_m12_r1_mesh_only_windows.py` creates `P10ML_M12_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip`. It preserves all cumulative M1–M11 size factors including the local C2 M11 R2 collar repair and adds `incremental_m12=(1−0.20*kappa12)^(1/3)`, making the **nominal** volume reduction 0–20% relative to prior size law. The actual polar curved Tet10 effective volume ratio must be measured independently by D029; no per-element volume-reduction guarantee is claimed.

Accepted input M11 R2 mesh SHA256 `b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726` pinned. Source manifest has 45 pinned files and new unique marker namespace `P10ML_R1_ONE_M12_ATTEMPT_CONSUMED` plus profile marker tied to accepted M11 SHA. Source SHA and transitive GEO include preflight PASS (offline, without Gmsh API). Python syntax and ZIP integrity pass. Actual Windows Gmsh-API check and 65-second native heartbeat test **pending user execution**. No mesh generation or physical FEM has been performed here; all markers unconsumed.

Windows workflow: `01_P10ML_M12_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd` (read-only, ~65–90 sec) then **one** `02_P10ML_ONE_M12_R1_MESH_ONLY.cmd` (Gmsh attempt, 20 minute hard guard). Return one `P10ML_R1_M12_UNVERIFIED_EVIDENCE.zip`. No FEM until separate D029 27/343/729QP and canonical Gmsh D031 quality PASS. Never repeat the consumed M12 R1 mesh attempt.
