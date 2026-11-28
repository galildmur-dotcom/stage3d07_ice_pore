# P10OC — M12→M13 signed4D local error-proxy and smooth κ diagnostic (2026-11-26)

Status **SOURCE-ONLY P10OC PASS; FEM=0, GMSH=0, M14 mesh NOT generated**. P10OB raw M13 physical accepted and P10NZ full comparator re-verified independently.

Exact P10NZ source archive SHA256 `a5b6964b0e30f742e1605a8a3c79600edf3df68fff18dfc2a26cf12e0af8be3a`. Reparsed all 43,200 (36×10×10×12) signed4D difference cells, unique keys, finite values, global component closure against P10NZ summary. Direct unsigned localization:

- `sum_cells abs(Delta D_R jpeak) = 0.6376773168552733 m^-1` vs global signed `-0.0036150294320163 m^-1`, cancellation factor `176.396` (bin L1, not a certified error norm).
- **56.1889%** of unsigned local difference in radial shells 0–3 (0–250 µm); this is distinct from sign-compensating radial signed sums.
- **34.2282%** in μ polar bins0 south +9 north (20% of angular bins); however these are unweighted bin aggregates, not area-integrated physical error estimates.
- **55.9438%** in last six steps31–36 (t_end 775–900s).
- Largest unsigned single-step difference step35; strongest proposed smooth κ in radial shell0 at north polar μ9, also high south cap.
- Important caveat: radial shell7 (2–5mm) also contributes `~0.084304/0.637677=13.22%` of unsigned differences; proposed radial attenuation prioritizes near-wall physics and should not be mistaken for a rigorous error optimum.

Proposed `P10OC_M14_PROPOSED_KAPPA_1200.csv` is a **smooth diagnostic field**, not a mesh-size instruction ready to apply. Source proxy `sum_t(|Delta total| + .25|Delta mechanical explicit|)`, 3D separable 3-cell smoothing in radial, μ and cyclic φ, enforce φ-invariance at μ0/μ9 caps after smoothing, apply radial attenuation weights (1,.85,.6,.4,.24,.1,.06,.03,0,0), κ range [0,1]. No central FD and no geometry modification. User target 25–50% reduction of characteristic volume in κ≈1 regions is a *future* mapping subject to element-quality/smoothness gates; no attempt to impose it here.

Deliverable `P10OC_M12_M13_LOCAL_ADAPTATION_DIAGNOSTIC_20261126.zip`, SHA256 `f5bc3ccef915a0687c05f9beae0f85fc6f3620f815f21be2bb6053d9ca50326e`, Library `libfile_530ff38ef9e08191ac2a05ebb90eec62`. Contains pinned P10NZ evidence, executable Python stdlib source and one-click Windows CMD, JSON diagnostic, 1200-cell κ CSV, and shell×latitude signed/unsigned table. ZIP CRC PASS; source-only run PASS.

Next gate P10OD: conduct *geometric feasibility* of M14 proposal, choosing smooth physical size/volume mapping from κ with high-order Tet10 boundaries preserved, then D029/D031 geometry acceptance before any new physical run. Do not claim M12→M13 converged merely from global −0.1525%.
