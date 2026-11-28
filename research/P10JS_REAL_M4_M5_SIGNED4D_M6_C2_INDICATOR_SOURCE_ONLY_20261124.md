# P10JS — real M4→M5 signed4D adaptive M6 C² κ source-only (2026-11-24)

## Status

**PASS_SOURCE_ONLY_NO_NEW_MESH_NO_FEM**. This stage processes real accepted M4 and M5 physical fixed-bin signed space-time data from P10JK/P10JR; **no M6 mesh, no M6 FEM, no actual M6 D029/D031**. Program published as [research/scripts/p10js_m6_signed_source_only.py](../scripts/p10js_m6_signed_source_only.py). Private `P10JS_M6_C2_SOURCE_ONLY_PRIVATE_20261124.zip` SHA256 **`277afcaf12175c20469e5ee977a60f77df02cb40e6d4149e26ad9f5a00975789`** includes source-only script, QA JSON and 1200-bin adaptive CSV, but not raw 4D/meshes. Private QA SHA `08a27d63d3d840a02f302ccb34c20fd0a0fb2c0fad1701f1bef4dd91834dae77`; 1200-bin CSV SHA `3ad57340cf3972e30126cd42c289e263bcdcb91e60e5d27a71e3933fbca53645`.

## Exact pinned provenance

M4 signed4D SHA `6c64dcb98f135cad24d8e8eb26b17d9cdfc92b38d385b6475f85a12b743595a2`, M5 signed4D SHA `0241992ca09dcb4f04acbcfac96be910c07a99a3ad9d68868692cc49023b114b`, P10HA 1200 centers SHA `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`, P10JL prior M5 κ source CSV SHA `0c5c475ff1986359d28fd0c4539353b9af5f221069f346008cac7be4ac149a61`. Geometry SHA M4 `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, M5 `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`. 36×25 s per mesh, 1200 common spatial bins, input signed sum `D_R jpeak(M5)-D_R jpeak(M4)=−0.023959138959437354 m⁻¹`; L1 signed space-time 2.1364740016941726 m⁻¹.

## Positive localized score and C² prolongation

For every bin k and 36 times, compute absolute difference in five nonzero signed4D components (three mechanical + two thermal), sum per component/time, normalize by total for each component, take average of three mechanical normalized values and two thermal normalized values; score `s_β=(1−β) mechanical + β thermal`. Main **β=.10**, diagnostics β0/.25. Source-only positive compact Wendland C² reconstruction in log radial distance and Cartesian angular unit direction, normalized and mapped by quintic smoothstep S5; 0≤κ≤1; seam max **4.4408920985e−16**, exact pole deviation **0**. No C² derivative numerical test; analytically constructed continuation and sampled seam/pole only.

| β | Dörfler θ=.5 selected bins | selected polar bins | total score fraction polar | N | S |
|---|---:|---:|---:|---:|---:|
| 0 | 75 | 61 | .51909180 | .32995584 | .18913596 |
| **.10** | **93** | **68** | **.47616283** | **.30206010** | **.17410273** |
| .25 | 127 | 75 | .41176938 | .26021648 | .15155289 |

For β=.10 the **nonpolar 52.38371694%** of total score is slightly dominant, and 25 of 93 selected bins are outside supported polar regions (all 120 polar bins use 0≤radial_bin≤4 and μ-bin 0 or 9). This confirms **do not restrict M6 refinement to polar caps**. Old P10JL M3→M4 Dörfler vs new M4→M5 selection Jaccard .5289256198347108, κ center mean absolute difference .016919986733220486; adaptation pattern evolves nontrivially despite similar global derivative.

## Limits and next

**κ(M6) is only the source indicator; it is not h6/h5 and does not predict actual M6 polar effective element volumes.** P10JT must calibrate a smooth additional size profile using accepted M5/M4 actual N/S Veff ratios .6126413344/.6333283110 plus old source-size proxy experience, explicitly marking any response extrapolation empirical and sensitivity scenarios; preserve old M5 wall C² repair and full nonpolar κ. Only after separate source preflight prepare a **distinct Windows guarded M6 mesh-only one-shot**, D031 all curved Tet10 threshold minSICN≥.20/minSJ≥.40/gamma≥.15/detJ27/343/729QP>0/CAD closure≤1e−6 and D029 actual N/S M6/M5 Veff [.50,.75], Neff≥30. No FEM M6 before M6 geometry GO. Step dt=25s in future FEM. **P10JQ missing native progress is still outstanding**: next Windows guarded job requires genuinely independent ≤30s progress and native Windows Job silent-child regression (not Python phase-only), 4 threads, pinned source/marker, user local execution; no ask repeat permission. No raw private evidence in public GitHub.
