# P10JT — M6 h6/h5 empirical C² size calibration SOURCE-ONLY (2026-11-24)

## Scope

**PASS_SOURCE_ONLY_NO_M6_MESH_NO_FEM**. P10JS accepted β=.10 1200-bin smooth positive κ(M6) reconstructed from actual M4/M5 signed4D; P10JT combines that with the **measured independent real M5/M4** polar effective-volume responses. No M6 Gmsh or FEM has run. All predicted M6/M5 polar volume ratios are **empirical source-center cube proxies**, not verified D029 results or guarantees. Reproducible code [research/scripts/p10jt_m6_size_field_source_only.py](../scripts/p10jt_m6_size_field_source_only.py).

## Exact pinned inputs and parametrization

P10HA coordinates SHA `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`; old P10JL M5 κ source SHA `0c5c475ff1986359d28fd0c4539353b9af5f221069f346008cac7be4ac149a61`; new P10JS M6 κ source SHA `3ad57340cf3972e30126cd42c289e263bcdcb91e60e5d27a71e3933fbca53645`. Accepted M4 SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, accepted M5 SHA `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`.

Candidate source incremental size field:

```
h6/h5 = exp( −0.1435943053641514*κ_M6
              −0.14988856005128548*W_N
              −0.12933181019892748*W_S
              −0.10*L_wall )
```

κ_M6 same positive normalized C² Wendland/smoothstep source as P10JS; W_N/S positive C² polar taper with smooth transition in d,|μ|; localized C² wall patch `L_wall` at original M4 repair direction `(0.4179124587379918,0.7804360648608903,−0.46504701428566836)`; original CAD, ten embedded seeds, previous full M4→M5 cumulative size factors are **retained**, nothing remeshed.

Calibration formula: old M5/M4 source-center weighted proxy with measured M5/M4 729QP regional Veff yields per-side transfer `T_side=observed_actual / old_proxy`. New M6/M5 source-center cube proxy then scaled by same T; numerical solve smooth polar δ for **nominal target .65**. Old field weights = correct **M4_QP N214236/S270000**, new field weights = correct **M5_QP N339984/S418896** (not legacy M3_QP fallback). No claim of error bounds from just one real response.

| Quantity | North N | South S |
|---|---:|---:|
| Real accepted M5/M4 Veff729 | .6126413343964234 | .6333283109508535 |
| Old M5/M4 proxy | .5360719712156294 | .6352555892414398 |
| Empirical transfer factor | **1.1428341105153486** | .9969661372159077 |
| M6/M5 unpatched transferred proxy | 1.0170579647318125 | .9564608359460807 |
| Chosen extra polar logsize δ | **.14988856005128548** | **.12933181019892748** |
| Calibrated M6/M5 target proxy | .6500000000000000 | .6500000000000001 |
| δ for alternative proxy target .75 | .10197833263940681 | .08141798801056013 |
| δ for alternative proxy target .50 | .23772870933918877 | .2171785524347366 |

North T≈1.143 is a **material empirical-model uncertainty**, so do not treat target .65 as forecast precision. Required real D029 M6/M5 effective-volume interval remains [.50,.75] (25–50% volume reduction) in each of N/S with Neff≥30; it is **not yet assessed**.

## Source-only checks

396 physical coordinate samples across both hemispheres, d=0…5mm, |μ|=.3…1, φ=0/π/2/π; positive incremental `h6/h5∈[0.752537597942222,0.9999986297759638]` on sampled points, κ∈[0,1], seam max `1.1102230246251565e−16`, pole max0. Python compile PASS, ZIP CRC PASS. Neither actual curved Tet10 quality nor real 729QP volume can be inferred from these checks. Private QA SHA `caef6571afe27e28584327e342456bb1e4437961b0c3ca319e1419f1d427b914`; samples SHA `6ae1bd15f1e583d31a2174fad965505ed9caa13a5e076b288d698c6738a15576`. Private `P10JT_M6_C2_SIZE_FIELD_SOURCE_ONLY_PRIVATE_20261124.zip` SHA `4070a2fb61bcd4106d53a3a28e9a7f5e36e95a5cc64118a604e3808ed77a1450`, code+QA+396 samples, not raw meshes/4D.

## Next distinct step

**P10JU** = prepare new guarded Windows Gmsh 4.15.2 mesh-only M6 run, exact original CAD + ten seeds, cumulative accepted field CAD→M2→M3→M4→M5→M6; pin prior accepted M5 SHA and all source SHA; no FEM until independently all curved M6 Tet10 D031 PASS and N/S M6/M5 actual D029 PASS. **Do not repeat P10JN consumed mesh marker nor P10JP consumed FEM marker.** M6 one-shot and distinct profile marker. **P10JQ critical**: separate independent watchdog/controller process or thread heartbeat≤30s across preflight, compile, Gmsh, QA, packaging; actual Windows native silent-child >60s regression observed with ≥2 beats, and status unknown if child silent. User runs locally; do not ask repeat authorization. Future physics dt25s.
