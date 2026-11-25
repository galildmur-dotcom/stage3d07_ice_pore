# P10MR — M12 first real full4D PASS; local convergence stalls on M11→M12

Date 2026-11-25. Physical M12 R1 user evidence `P10MO_M12_FIRST_FULL4D_EVIDENCE.zip`: 10 original files, native exit 0, `P10MO_M12_REAL_FULL4D_PASS`, exact accepted SHA256 `e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13`, 16,333 Tet10, 23,732 nodes; 36×25 s, R/EDV_VAR, xi0, B6=5mm, fresh forward + same-mesh analytic adjoint, 101-file pinned solver. One and only one physical FEM attempt, consumed P10MO marker. Wall 1913.378 s; peak polled private 3,483,779,072 bytes; 128 independent 15s heartbeats. Independent signed 4D and two-term mechanical explicit closures PASS. This physical attempt must never be rerun.

Independent script `research/tools/p10mr_m11_m12_three_convergence_indicators.py` parses original M11 P10MI and M12 P10MO ZIP, CRC tests, verifies 43,236 unique aligned signed-bin rows and identical boundaries, reconstructs six-component totals, verifies 43,200 two-term explicit rows, then computes the three obligatory P10MQ indicators. Output JSON `research/P10MR_M11_M12_REAL_FULL4D_THREE_INDICATORS.json`.

| P10MQ indicator | M10→M11 | M11→M12 | interpretation |
| --- | ---: | ---: | --- |
| `D_R j_peak` on new mesh, m^-1 | 2.376941218513 | **2.370838129490** | decrease on M12 |
| global signed `Δ`, m^-1 | +0.003883977665 | **−0.006103089023** | sign changes |
| `E^(J)=|Δ|/|D_new|` | 0.16367% | **0.25742%** | global stability worsens |
| full matched signed 4D `L1`, m^-1 | 0.722258972161 | **0.715341830509** | only **−0.9577%** |
| full matched signed 4D `L2`, m^-1 | 0.011676416505 | **0.011714987689** | **+0.3303%** |
| `C=L1/|Δ|` | 185.9586 | **117.2098** | high cancellation persists |
| `K=1−1/C` | 0.994622 | **0.9914683** | high cancellation persists; not quality measure |

**Scientific decision: M12 is a valid passed physical calculation, but spatial convergence is NOT established, and improvement of the full4D local mismatch appears nearly stalled from M11 to M12.** L1 decreases by <1% despite >15% per-pole curved-volume refinement; L2 grows slightly. Do not infer asymptotic convergence, error bars or Richardson rate from the global derivative's narrow range.

## Where the 4D mismatch persists

M11→M12 L1 by latitude (m^-1): south `0.15072977`, middle `0.41678102`, north `0.14783104`. Radial layers 0..7 (m^-1): `0.120503`, `0.115858`, `0.114444`, `0.084566`, `0.074076`, `0.057800`, `0.061813`, `0.086282` (8–9 zero). Last six steps contain **57.2368%** of L1; step 35 has L1 `0.102623` m^-1. The late-time and near-wall effects are still strong.

Six signed-component increments (m^-1): mechanical explicit `+0.103967846890`, equilibrium `−0.033824113616`, history `−0.075997580600`, thermal mass `+0.000031002504`, thermal diffusion `−0.000280244201`, Robin zero; sum `−0.006103089023`. Separate *local* two-term explicit L1: geometry normalization `0.115078`, stress chain `0.849222`, signed sum `0.767263`. As for M9–M11, change in explicit mechanical contribution is stress-chain dominated locally; there is no evidence that inter-element stress-derivative jumps are the cause.

M12 all-step two-term explicit totals (m^-1): geometry `+1.270584395262`, stress chain `−10.671486637517`, explicit `−9.400902242255`. Nearest radial layer: geometry `+0.316668181`, stress chain `−2.443436979`, total `−2.126768798`. These agree with prior M11 diagnosis and show persistence of a substantial negative stress-chain wall term.

## Mandatory next scientific action

**Diagnostic/source-only before M13 mesh generation.** Independently map the new M11→M12 4D L1/L2 by `(radial_bin,mu_bin,phi_bin)` and late steps, compare with preceding M10→M11 to identify whether M12's added resolution overlaps the actually persistent discrepancies. Separate stress-chain vs equilibrium/history and test polar vs intermediate-latitude saturation. Validate 3D C2 indicator predictions and curved D029 near-wall/pole effective volumes. Do not launch another expensive mesh/FEM just because the integrated derivative is close to 2.37.
