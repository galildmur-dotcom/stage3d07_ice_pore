# P10LN — first physical two-term explicit derivative on accepted M9

**2026-11-25. Status:** `PASS_REAL_M9_WITH_INDEPENDENT_CSV_AND_PRIOR_RUN_PARITY`.

## 1. Original native evidence

Investigator-provided `P10LM_M9_FIRST_FULL4D_EVIDENCE.zip`, SHA256 `28e7134ade06f62dd2f72f18497909fcaa7a2fbd1fb5dcc6814771b76b668608`, ZIP CRC PASS (10 files). `P10LM_MANIFEST.json` reports `P10LM_M9_REAL_FULL4D_PASS`, native exit0, no stop reason, exactly one new physical attempt (one-shot now **CONSUMED — NEVER REPEAT**). Same M9 mesh SHA `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58`, 19,236 nodes, 13,166 Tet10, 27 QP per tet, R/EDV_VAR/xi0/B6=5 mm/36×25 s/4 threads. P10LG instrumented C++ header SHA `0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3`.

Wall time 1,325.707 s (22.10 min), process CPU 2,809.406 s, mean 2.119 busy logical CPUs (26.49% of 8), peak private 2,810,986,496 bytes (~2.62 GiB), monitored hard cap 8 GiB, 89 independent heartbeats, Windows native silent-65s preflight passed. Original signed4D 43,236 rows PASS. Extra P10LG two-term sidecar 43,200 rows PASS.

## 2. Independent raw 4D reanalysis

`research/tools/p10ln_audit_m9_physical_two_term.py` streamed the actual two CSVs from the ZIP, reconstructed every key `(time_step,r_bin,mu_bin,phi_bin)`, independently compared `geometry+stress=original P10DD mech_explicit` for **all 43,200 cells**, rejected duplicates and nonfinite cells and verified the two global sums against the production manifest. No FEM, mesh generation or read/write of Windows markers in this audit.

| Region | Geometry + normalization (m⁻¹) | Stress chain (m⁻¹) | Original explicit (m⁻¹) |
| --- | ---: | ---: | ---: |
| **Entire B6** | **+1.315537551010** | **−10.943598456674** | **−9.628060905664** |
| First 0–20 μm wall shell, all angles | +0.341827696944 | −2.609203760259 | −2.267376063314 |
| Southmost μ bin 0, all radii | +0.443314265159 | −3.457148319614 | −3.013834054456 |
| Mid-latitudes μ bins 1…8, all radii | +0.256808323880 | −0.851363046376 | −0.594554722495 |
| Northmost μ bin 9, all radii | +0.615414961971 | −6.635087090684 | −6.019672128714 |
| First shell **south** μ bin 0 | +0.129560308620 | −1.036827657345 | −0.907267348724 |
| First shell **mid-latitudes** | +0.036743726256 | −0.182976971010 | −0.146233244754 |
| First shell **north** μ bin 9 | +0.175523662068 | −1.389399131904 | −1.213875469836 |

The stress-chain term is negative and greatly exceeds the positive geometry/normalization term on this accepted M9. In the first 0–20 μm shell, the northmost μ bin (approximately 53.5% of its negative explicit sum in absolute terms) exceeds the southmost bin (~40.0%) and the eight central μ bins combined (~6.4%). Here the 10 latitude bins are equal in **μ=cos θ**, not in θ; numerical pole percentages describe only the explicitly defined partition, not a continuum singularity. All results retain signed units of m⁻¹.

## 3. Frozen-mesh reproducibility versus previously accepted M9

The physically separate P10LM instrumentation run reproduces prior uninstrumented P10LC M9:

| Observable (m⁻¹) | Prior P10LC | New P10LM | Difference |
| --- | ---: | ---: | ---: |
| `D_R jpeak` | +2.373284281251736 | +2.373284281246059 | −5.6763×10⁻¹² |
| `mech_explicit` | −9.628060905664032 | −9.628060905664373 | −3.41×10⁻¹³ |

Independent original global component checks for equilibrium, history and all thermal partials are each within `1e-8` absolute per metre. This is strong frozen-mesh parity evidence that the instrumentation did not perturb the primary physical output; it is not a discretization convergence proof.

## 4. Scientific conclusion and next experiment

On M9, the **negative explicit mechanical derivative is dominated by the stress-chain term**, both globally and within the first-wall-shell/polar bins. This identifies the composition of the M9 result, **not** the cause of its change from M8: the old M8 data contained only their sum, and the mesh difference M9−M8 is not identifiable by two separate terms until M8 is also instrumented.

Prior M8→M9 difference in `mech_explicit` was +0.164433128 m⁻¹ over B6, +0.196024673 m⁻¹ in the first 0–20 μm shell. Do **not** attribute either difference solely to stress-chain effects yet; an offset in geometry term may dominate the difference even when its absolute M9 magnitude is smaller.

**Next P10LO**: prepare a **new distinct M8 R3** one-shot with precisely the same diagnostic, 36×25 s and physics, uniquely marked and protected; use existing exact accepted M8 SHA `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d`, never rerun consumed P10KV. After user returns the new physical evidence, form actual signed M9−M8 maps separately for geometry and stress, especially both poles and first 0–20 μm shell. The preparation is allowed under SOP D-028; do not claim new physical M8 values without original native evidence.

Machine-readable detailed radial/latitude/time aggregates: `research/P10LN_M9_PHYSICAL_TWO_TERM_INDEPENDENT_QA.json`.
