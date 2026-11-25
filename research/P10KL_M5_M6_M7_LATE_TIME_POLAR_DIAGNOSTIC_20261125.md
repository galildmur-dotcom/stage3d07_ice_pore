# P10KL: independent M5→M6→M7 late-time and polar signed4D diagnostic (2026-11-25)

**SOURCE-ONLY ANALYSIS PASS; FEM attempts=0; spatial convergence not proven.** Reused independently verified 43,236-row signed4D M5/M6 and user M7 R/EDV_VAR/xi0/B6 5mm 36×25s on unchanged pinned meshes. M7 evidence SHA `0bc50329078cba02f2a5ad55bfcee1d42ef4cf0475d44430598982c233ba5ec7`, M7 one-shot consumed, NEVER repeat. Joined exact mode/functional/step/timing/region/radial/mu/phi keys, one-to-one all 43,236 rows. Independent totals Δ76=+0.009875165430846843 1/m and Δ65=−0.0014682036165974965 1/m.

**Late-time concentration**: for M7−M6 the first 24 steps contribute signed −0.0125230669, L1 0.183927652; steps25–30 signed −0.00450976727, L1 0.234291303; steps31–36 signed **+0.0269079996**, L1 **0.647810812**. L1 share last six steps 60.7685% (M6−M5 60.9335%). Step35 has largest signed and L1 intermesh change. Physical time strictly 25 s per step (31–36 covers 750–900 s), no inference about a novel constitutive change. Strong time cancellation persists: early+middle −0.0170328341 vs late +0.0269080.

**Whole-field norms**: L1 Δ76 1.066029765758 vs Δ65 1.929118585642 (ratio .5526), L2 Δ76/Δ65 **0.42793214**. Rowwise 4D difference correlation **0.03509187**, cosine 0.03509154: successive changes are almost orthogonal, not stable asymptotic error shape; cannot extrapolate the observable by Richardson based on two increments or declare convergence.

**Polar convention sensitivity**, for north/south outermost μ bins grouped across all time, radius and azimuth (μ0 south, μ9 north):

| Width bins per pole | Δ76 north | Δ76 south | Δ76 other | Δ65 north | Δ65 south | Δ65 other |
|---|---:|---:|---:|---:|---:|---:|
| 1 | +.041432516 | +.015904201 | −.047461552 | +.277927813 | +.041606430 | −.321002447 |
| 2 | +.015147077 | +.009619122 | −.014891034 | +.218754938 | +.032080435 | −.252303577 |
| 3 | +.016789463 | +.009839198 | −.016753495 | +.135103798 | +.013043045 | −.149615047 |

All rows sum to same global Δ. The polar window definition must be SHA-pinned in all future scientific comparisons. 10 μ-bin angular partitions, 10 radial bins, 36 steps and 12 phi bins are immutable for this comparison; physical region remains near-pore B6 cutoff 5mm.

**Decision:** M8 is scientifically warranted to test non-asymptotic behavior, but not yet authorized to call convergence. Before any M8 native FEM, prepare geometry source-only mesh adaptation from M7 with smooth 0→1 grading and 15–25% characteristic size reduction in priority polar / late-time sensitivity regions, using existing P10KI accepted geometry constraints and D031 curved 27/343/729QP, D029 729QP polar effective-volume, topology integrity; only one unique M8 mesh attempt and later a separate new FEM one-shot after geometry GO. Do not alter Δt25, physics, or analytic adjoint. Next stage P10KM should produce source-only M8 mesh design, no physical run unless user runs it.

Artifact `P10KL_M5_M6_M7_SOURCE_ONLY_POLAR_LATE_TIME_DIAGNOSTIC_20261125.zip` in Library `libfile_b365ad27b79c8191acf3170b3c06a2e6` with independent JSON, time phases, 36-step time CSV, 360 sector×time and 100 radial×polar CSV, and two-pair diverging-heatmaps PNG.
