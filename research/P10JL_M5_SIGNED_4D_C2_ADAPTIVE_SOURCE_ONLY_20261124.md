# P10JL — M5 source-only signed4D error indicator from real M3→M4 (24.11.2026)

## Scientific input and limits

Previous P10JK real M4 FEM and independent signed4D PASS. M3 and M4 original private 43,236-row CSV each, unchanged physical 1200 bins × 36 time steps, source-only Python 27/343/729QA previously done. Source data pin: M3 signed4D SHA `6ec0dfb8b5e0bffa7336ba2695044811ed872219f5e175d156d6922f81b0e8cf`; M4 signed4D SHA `6c64dcb98f135cad24d8e8eb26b17d9cdfc92b38d385b6475f85a12b743595a2`; original P10HA coordinate-reference CSV SHA `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`, M2→M3 source P10IT CSV SHA `e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06`. M4 exact accepted SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`.

**No new Gmsh, FEM, mesh, CAD or source model mutation.** The new field is only a design indicator for a possible future M5. No actual M5 regional volume, D031 Tet10 quality, FEM or convergence claim.

## Reproducible construction

For each physical bin, compute six signed `M4-M3` component differences over all 36 steps. The TOP_ROBIN component is zero here; mechanical three and thermal mass/diffusion two have nonzero L1 weights. Compute per-component `sum_t|Δc|`, normalize each of five nonzero components by its whole-domain L1 (important against mechanical dominating thermal solely by units), average 3 mechanical components and 2 thermal components, and mix `score_β=(1−β)mech + β thermal` with primary previously approved β=0.10 and diagnostics β=0/0.25. This is an error *indicator* not a posteriori upper error bound. Apply Dörfler θ=.5 on physical bins.

For each position outside pore, construct directional/radial positive normalized compact Wendland C² smoothing of bin source scores in `u=log(1+d_mm/.05)` and Cartesian unit sphere direction, with previous P10IU widths (.75 radial u, .60 directional chord). Use quintic s5 smooth normalization to obtain bounded `0≤κ≤1`. This makes a global smooth adaptive κ field with exact geometrical seam and poles. No h5/h4 or actual Veff calibration has been applied yet; those belong to next P10JM.

## Quantitative result

| β | Dörfler selected bins θ=.5 | supported polar bins | polar score share | N share | S share |
|---:|---:|---:|---:|---:|---:|
| .00 | 74 | 63 | .540463 | .353833 | .186630 |
| **.10** | **92** | **74** | **.495526** | **.323526** | **.172000** |
| .25 | 127 | 87 | .428120 | .278065 | .150055 |

For primary β=.10: 74/92 selected bins lie in supported polar regions; **50.45% of total score lies outside polar regions** (this is consistent with P10JK signed compensation), important to preserve nonpolar mesh adaptation rather than focusing exclusively on pole caps. New vs prior M2→M3 β=.1 Dörfler selected-set Jaccard=.5655737705 and center smoothed κ MAE=.0481826357. New κ mean over 1200 centers .03795572, polar mean .33581184. Highest κ bins all near N pole. κ center min/max [0,1], seam numerical difference `4.44e−16`, exact polar-coordinate difference 0.

Checks: independent 4D bins 1200, 36 steps, source total Δ`D_Rjpeak` `−0.08513474055522016 m⁻¹`; `Σ|Δtotal|` 2.6693487289923374; all source-score weights finite and positive, 27QP support nonzero in M3/M4. β=.1 approved by previous user; not tuned post-hoc to current result. Do not interpret 0.4955 polar share as polar contribution of the global *signed* Δ.

## Artifacts and next scientific stage

Private QA `P10JL_M5_SOURCE_ONLY_QA.json` SHA256 `3a7eb77555032b76fc00121bcef4d0b1e408faec84257e43647fbe2f9fecf1e4`; private compact 1200-bin source `P10JL_M5_SIGNED_SOURCE_1200_BINS.csv` SHA256 `0c5c475ff1986359d28fd0c4539353b9af5f221069f346008cac7be4ac149a61`. No private raw CSV in public GitHub. Reproducible source code in `research/scripts/p10jl_m5_signed_source_only.py` with helpers `p10it_compare.py`, `p10iu_continuous_m4.py`. The scripts do not execute Gmsh/FEM.

**Next P10JM**: source-only M5 h5/h4 polar and nonpolar C² size calibration against observed M3→M4 actual N/S supported regional volume ratios (.648119/.665087), keeping D029 preregistered actual ratio [.50,.75] and D031 all curved Tet10 thresholds minSICN≥.2, minSJ≥.4, gamma≥.15, detJ>0, CAD closure≤1e−6, neighbour q only diagnostic D030. A single new guarded M5 mesh-only Windows package may be prepared only after source profile/QA, with P10JH mandatory **real** all-phase heartbeat≤30s. Never repeat consumed P10IY mesh or P10JF FEM markers.
