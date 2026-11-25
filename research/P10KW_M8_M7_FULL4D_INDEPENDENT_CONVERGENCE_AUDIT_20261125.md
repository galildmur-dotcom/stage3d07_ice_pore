# P10KW — independent M8−M7 signed4D audit (25 Nov 2026)

**Scientific verdict: REAL M8 FEM PASS; spatial convergence NOT ESTABLISHED.**

## Immutable input evidence

- M6: `P10JW_M6_FIRST_FULL4D_EVIDENCE.zip`, user Library `libfile_2bb1501d98b881919af6cc07af3c63a0`.
- M7: `P10KJ_M7_FIRST_FULL4D_EVIDENCE.zip`, user Library `libfile_1ad17d309aa081918240a4f44745ac4d`.
- M8: `P10KV_M8_FIRST_FULL4D_EVIDENCE.zip` (user-supplied, ZIP CRC PASS), accepted M8 R3 mesh SHA256 `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d`.
- M8 native exit 0; 36 steps × 25 s, 4 configured threads, 84 watchdog heartbeats, independent signed4D closure PASS; wall 1246.545 s, CPU 2594.921875 s (mean ~2.082 busy logical cores), peak private 2,677,686,272 bytes. The M8 R3 FEM one-shot marker is **CONSUMED; never rerun this same one-shot**.

## Independent row-aligned comparison

Script: `research/tools/p10kw_m8_m7_signed4d_audit.py`. Each evidence ZIP was CRC-tested, the 43,236 finite rows checked for unique `(step,region,radial_bin,mu_bin,phi_bin)` keys, all six signed components reconstructed into each row total, and M7/M8 spatial and time bin boundaries matched. 43,200 volume rows and 36 top-Robin rows. No interpolated cell matching, no re-executed FEM.

| Quantity | M6→M7 | M7→M8 |
|---|---:|---:|
| Global `D_R j_peak` before → after (m⁻¹) | 2.362652787786 → 2.372527953217 | 2.372527953217 → **2.361333042852** |
| Global increment (m⁻¹) | +0.009875165431 | **−0.011194910365** |
| Global relative increment | +0.41797% | **−0.47186%** |
| Sum of absolute signed4D cell increments (L1; m⁻¹) | 1.066029765758 | **0.953928903742** |
| Signed4D increment L2 norm (m⁻¹) | 0.023373829751 | **0.019466225814** |
| L1 / absolute global increment | 107.95× | **85.21×** |
| L1 concentrated in last six time steps | 60.77% | **60.10%** |

The successive L1 and L2 ratios are 0.89484 and 0.83282 respectively: localization mismatch decreases, but not rapidly. Crucially, the cellwise M6→M7 vs M7→M8 increments are **anticorrelated** (Pearson −0.40237, cosine −0.40237); the signed global increment reverses sign and increases in magnitude. Thus the global ~0.47% difference does not certify spatial convergence, and Richardson extrapolation from this non-asymptotic mesh sequence is not justified.

### M8−M7 resolved diagnostics (m⁻¹)

| Signed component increment | Value |
|---|---:|
| Mechanical explicit | +0.090390796943 |
| Mechanical equilibrium | −0.002065790700 |
| Mechanical history | −0.099033930610 |
| Thermal mass | +0.000029381966 |
| Thermal diffusion | −0.000515367964 |
| Thermal Robin | 0 |
| **Sum** | **−0.011194910365** |

One most-northern angular bin changes by +0.015542503780; one most-southern bin by +0.005196090874, while all nonpolar bins combined change by −0.031933505019. Late steps 31–36 alone change by +0.033270171254 and account for 60.10% of total absolute 4D differences. These are significant spatial, temporal and component-level cancellations hidden by the scalar result.

## Research gate and next step

1. Record **`P10KW_M8_REAL_FULL4D_AUDITED_NONCONVERGED`** ("nonconverged" means *not established*, not a theorem that the continuum sequence diverges). Preserve all M6/M7/M8 raw ZIP evidence unchanged.
2. Freeze the present R/EDV_VAR/ξ0/B6 5-mm 36×25-s model and signed4D response definition. Do **not** claim an asymptotic spatial limit, or fit a Richardson order to M6/M7/M8.
3. Design a **new and uniquely marked M9 mesh-only quality/adaptation gate** first: explicit curved Tet10 Jacobian and canonical Gmsh quality, near-pole D029 volume-efficiency on both poles, CAD/tag parity; use independent preflight and bounded one-shot marker. Do not execute M9 FEM before geometry GO or without a user-visible resource-safe run package.
4. After geometry GO, one separately marked M9 full4D FEM and the same cellwise signed4D analysis will test whether L1/L2 decrements and pole/late-time cancellation genuinely stabilize. M9 must be proposed with predicted resource envelope; avoid escalating a full FEM merely to chase agreement in the global sum.

No new FEM or mesh generation was run in P10KW. The raw 4D evidence is not committed to this repository. Audit results are reproducible from the user-held ZIPs using the above read-only script.
