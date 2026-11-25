# P10KX — M9 source-only priority design from actual M8−M7 signed4D

**Status: PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM.** No mesh attempt marker touched. M8 R3 existing FEM one-shot remains consumed and must never be rerun.

## Scientific input and source construction

The independent P10KW comparison identified M8−M7 signed4D L1=0.9539289037416502 m⁻¹, with 60.0970% of L1 originating in steps 31–36. The two user evidence archives (M7 `P10KJ`, M8 `P10KV`) were ZIP-CRC checked, joined exactly on `(step,region,radial_bin,mu_bin,phi_bin)` (43,236 rows), and integrated as 1,200 physical `(r,mu,phi)` cells.

For bin \(b\), let \(A_b=\sum_{n=1}^{36}|g_{M8,b,n}-g_{M7,b,n}|\) and \(L_b=\sum_{n=31}^{36}|g_{M8,b,n}-g_{M7,b,n}|\). Proposed nonnegative priority is

\[
S_b=\left(0.4\frac{A_b}{\max_c A_c}+0.6\frac{L_b}{\max_c L_c}\right)P_b,\qquad
P_b=\begin{cases}1.2,&\mu\text{-bin }0\text{ or }9,\\1,&\text{otherwise}.\end{cases}
\]

Smooth interpolation uses the *existing* compact C² Wendland interpolation of `p10iu_continuous_m4.py` in logarithmic distance from pore wall and 3D Cartesian unit direction, followed by quintic smoothstep. **No direct interpolation of a discontinuous binwise indicator is performed in physical space.** Retain the P10KP C² polar plateau (core `d≤0.5 mm`, `|mu|≥0.8`; taper to `d=1 mm`, `|mu|=0.6`) to prevent polar loss of adaptation. Incremental size law: `h_new/h_M8 = (1−0.20*kappa)^(1/3)`.

This is an *adaptation heuristic*, not an a posteriori discretization-error estimator or rigorous equidistribution. Signed contributions remain in the original 4D evidence; only their absolute mesh-to-mesh change is used for positive refinement priority. The local nominal volume change ranges from **0% to 20%**. Actual curved-element volume change may differ and is not claimed to pass the 15–25% target before Gmsh D029.

## Verified input/output identities

| Input/output | SHA256 |
|---|---|
| User M7 evidence ZIP | `0bc50329078cba02f2a5ad55bfcee1d42ef4cf0475d44430598982c233ba5ec7` |
| User M8 evidence ZIP | `247e6d8f189aaceac1fafdfec4fac9bfbe8df066a1d4f1b82ad65c38028e28cf` |
| Prior M8 1200-bin source | `235fc2e0e31d7e55dbf6d1d3ed4a127ca11903cf12a038ee1561006cc0134766` |
| Pinned spatial coordinate source | `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3` |
| **New M9 source CSV** | **`ddf7adeaeffffdab480c8bee5b234998236c53a1320aed511d6da20f0c09957f`** |

Verified 1,200 source bins, continuous normalized field range `[0,1]`, all nominal volume ratios `[0.8,1]`, full 43,236-row alignment, and no Gmsh or FEM launch. The highest-ranked bins occur in both north and south polar sectors; exact top 10 are in the source QA JSON.

## Next execution gate: P10KY, not yet authorized or attempted

Prepare a **distinct bounded M9 mesh-only Windows one-shot** based on the accepted M8 R3 mesh, exact SHA `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d`, preserving original CAD, Tet10, ten embedded seed points, physical tags 2–9, the full accepted M8 callback, and only multiplying by the new M9 incremental factor. Source pins, negative preflight test, unique persistent one-shot marker, watchdog/progress heartbeats, and a Gmsh version check are mandatory.

Geometry acceptance before M9 FEM: independently compute curved Tet10 detJ at 27/343/729 QP, CAD/physical tags; canonical Gmsh quality minSICN≥0.20, minSJ≥0.40, gamma≥0.15, all positive Jacobians; per-pole near-p0 actual Veff(M9)/Veff(M8) in `[0.75,0.85]`, sufficient effective quadrature support, and 343→729 QP stability. Stop if any criterion fails. Do not fit an asymptotic convergence order before actual M9 full4D evidence.

Reproducer: `research/tools/p10kx_m9_source_only_design.py`. Data: `research/evidence/P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv` and `research/evidence/P10KX_M9_SOURCE_ONLY_QA.json`.
