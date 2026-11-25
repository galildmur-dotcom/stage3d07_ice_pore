# P10MJ — real M11 R2 physical full4D; M9/M10/M11 independent spatial comparison

2026-11-25; authoritative research branch `research/p10bb-w5b2-20261118`.

## Physical evidence and one-shot execution

User-returned `P10MI_M11_FIRST_FULL4D_EVIDENCE.zip` contains 10 files, including the source-locked `P10MI_MANIFEST.json`, independent signed 4D and two-term mechanical explicit sidecar. The manifest reports `P10MI_M11_REAL_FULL4D_PASS`, native exit 0, one physical attempt, no STOP. Same solver revision `P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1` (101 SHA-pinned source files). Geometry M11 R2 SHA256 `b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726` (15,055 Tet10 and 21,943 nodes). The direct 36-step forward and adjoint share this mesh. R/EDV_VAR, xi0, B6=5 mm, 36×25 s, 4 threads. Native wall 1865.665 s, peak polled private bytes 3,212,775,424, 125 independent progress heartbeat ticks. Signed 4D QA and the 43,200-bin two-term explicit equality PASS.

## Independent physical spatial comparison

Independent script `research/tools/p10mj_m9_m10_m11_real_signed4d_audit.py` reads the original M9 `P10LM`, M10 `P10LY`, and M11 `P10MI` ZIP evidence, verifies 43,236 aligned signed bins, 36 time steps, all coordinates, six-component reconstruction and 43,200-bin explicit stress/geometry closure. Full machine-readable output: `research/P10MJ_M9_M10_M11_REAL_SIGNED4D_AUDIT.json`.

| Indicator | M9→M10 | M10→M11 R2 | change |
| --- | ---: | ---: | ---: |
| full signed 4D L1 per m | 0.8079903924 | 0.7222589722 | -10.61% |
| full signed 4D L2 per m | 0.01510924882 | 0.01167641650 | -22.72% |
| full signed 4D integrated delta per m | -0.0002270404 | +0.0038839777 | opposite sign |
| D_R j_peak per m | M9=2.373284281246, M10=2.373057240848 | M11=2.376941218513 | M10→M11 +0.1637% |

Cosine between sequential 43,236-dimensional corrections is **-0.43377438** (Pearson -0.43377482). Thus the local 4D error decreases in these two norms, but successive corrections partly oppose one another; the results **do not establish an asymptotic rate or pointwise convergence**. The integrated derivative's small change is less informative than the signed field norms because of large cancellation: M10→M11 L1 / |signed| ~186.

M10→M11 signed 4D L1 by latitude: south 0.14040, middle 0.42404, north 0.15782. By near-pore radial index 0..7: 0.12229, 0.10974, 0.10625, 0.09185, 0.08185, 0.06642, 0.06331, 0.08055; bins 8–9 zero. Temporal distribution is strongly late: last six steps account for **57.29%** of full L1; step 35 alone ~0.10285. Next adaptation should inspect late-time, near-wall and pole-resolved errors, not use integrated D_R j_peak alone.

## Two-term explicit mechanical diagnosis

All-step contributions M11 R2 (per m): geometry/normalization +1.2923559611, stress chain -10.7972260502, sum -9.5048700891. On radial index 0 (closest wall): geometry +0.3220952234, stress chain -2.4826263570, sum -2.1605311336. This independently reproduces the prior scientific diagnosis: the negative near-wall `mech_explicit` is stress-chain dominated, **without identifying stress derivative jumps as a demonstrated cause**.

M10→M11 local L1 of explicit split: geometry/normalization 0.12200, stress chain 0.86077, sum 0.77246. Thermal local changes remain much smaller (thermal mass 0.00353, diffusion 0.01198). These are unweighted bin-level L1 sums in the project's canonical signed 4D partition, not an independent physical norm over continuous space/time.

## Decision and next stage

**M11 R2 physical FULL4D PASS**. Improve the spatial refinement by building M12 from the independently aligned real M11−M10 4D error field (mechanical dominant, signed absolute indicators). Respect user-required smooth C2 spatial transitions, preserve pole and near-wall attention, perform geometry D029 curved 27/343/729QP then canonical Gmsh D031 before any M12 FEM. M11 physical one-shot marker is consumed; it must never be rerun. Avoid claiming asymptotic convergence from current data alone.
