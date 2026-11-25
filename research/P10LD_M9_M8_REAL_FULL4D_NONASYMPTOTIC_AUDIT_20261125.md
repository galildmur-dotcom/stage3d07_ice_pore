# P10LD — independent M9−M8 signed4D convergence audit (25 Nov 2026)

**Result: M9 real full4D physical PASS; spatial asymptotic convergence NOT ESTABLISHED.** The signed4D mismatch rises from M7→M8 to M8→M9 despite smooth field and accepted D029/D031 geometry. Stop naive repeated mesh refinement until mechanism diagnosed.

## Pinned, genuine single-use physical evidence

User-supplied `P10LC_M9_FIRST_FULL4D_EVIDENCE.zip`, SHA256 `44aa4ef873543787fb3a9f47b53edd14bd138412842ed29d51504e5b5181bdb7`, ZIP CRC PASS. Native M9 full4D exit0, no stop reason, accepted mesh SHA `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58`, 19,236 nodes, 13,166 Tet10, 36×25 s, 4 configured threads, fresh forward and same-mesh analytic adjoint. Independent 4D closure PASS with 43,236 rows. `D_R jpeak(M9)=+2.3732842812517 m⁻¹`; wall 1340.583 s, CPU 2787.297 s, mean busy logical cores 2.07917 (25.99% of 8), peak private 2,809,536,512 bytes, 90 independent progress ticks. **M9 R1 one-shot FEM marker CONSUMED; do not rerun.**

M8 comparison: wall 1246.545 s, CPU 2594.922 s, mean busy cores 2.08169, private peak 2,677,686,272 bytes; M9 wall +94.04 s, CPU +192.375 s, busy-core average essentially unchanged. Requested four threads does not imply 50% whole-machine average because serial/limited-parallel phases, synchronization and memory bandwidth can affect overall utilization. This is an interpretation, not a measured causal diagnosis.

## Cellwise independent full signed4D comparison

Both ZIPs independently CRC-tested; exact 43,236-row one-to-one keys `(step,region,radial_bin,mu_bin,phi_bin)`, physical/time bin boundaries matched, row totals rebuilt as sum of six components; 43,200 physical volume records and 36 top-Robin records. Cross-mesh data are compared on the same 4D *partition bins*, not matched individual Tet10 elements. No PDE rerun or interpolation of physical FE solutions.

| Quantity | M6→M7 | M7→M8 | **M8→M9** |
|---|---:|---:|---:|
| `D_R jpeak` after (m⁻¹) | 2.372527953217 | 2.361333042852 | **2.373284281251** |
| Signed global increment (m⁻¹) | +0.009875165431 | −0.011194910365 | **+0.011951238399** |
| Relative global increment | +0.41797% | −0.47186% | **+0.50612%** |
| 4D signed cellwise L1 (m⁻¹) | 1.066029765758 | 0.953928903742 | **0.964211175178** |
| 4D signed cellwise L2 (m⁻¹) | 0.023373829751 | 0.019466225814 | **0.020890891626** |
| Local cancellation factor L1/abs(global Δ) | 107.95× | 85.21× | **80.68×** |
| Absolute L1 concentrated at steps 31–36 | 60.77% | 60.10% | **60.79%** |

**M9 vs M8 non-asymptotic evidence:** L1 ratio **1.0107788656**, L2 ratio **1.0731865450**; consecutive 4D cell corrections Pearson correlation **−0.210328**, cosine **−0.210334**. Scalar derivative increments oscillate in sign: +0.009875, −0.011195, +0.011951 m⁻¹. Neither mesh-to-mesh local discrepancy nor scalar increment is settling monotonically; Richardson order/error bound and convergence claim are not justified. The observed pattern cannot establish mathematical divergence either.

### M9−M8 signed anatomy (m⁻¹)

| Component | Increment |
|---|---:|
| Mechanical explicit | +0.164433127821 |
| Mechanical equilibrium | −0.071556289150 |
| Mechanical history | −0.082307148199 |
| Thermal mass | +0.000025297455 |
| Thermal diffusion | +0.001356250472 |
| Thermal Robin | 0 |
| **Total** | **+0.011951238399** |

- **South extreme μ-bin:** +0.055827980526; **north extreme μ-bin:** +0.021573754296; nonpolar bins together **−0.065450496423**. Strong polarity/nonpolarity cancellation persists, with more southern bias in the new increment.
- First radial bin alone contributes **+0.1502908 m⁻¹** signed; farther radial bins compensate much of this. In contrast M7→M8 first-bin signed increment was only +0.001272. This is a decisive reason to inspect the near-wall signed derivative anatomy before adding M10.
- Steps 31–36 contribute **+0.052005679703 m⁻¹** signed but 60.785% of total absolute 4D mismatch. Step 35 dominates with L1≈0.146797.

Figure: `research/figures/P10LD_M7_M8_M9_SIGNED4D_ANGULAR_TIME.png` (signed and absolute projections over `(r,phi)` for each `(mu,t)`). This is only a 2D projection of 4D binwise evidence; it cannot replace radial/azimuth-resolved data.

## Scientific next gate: P10LE (diagnosis first; FEM=0)

1. Audit **per-component and per-radial-layer** signed M7→M8 vs M8→M9 increments, especially `radial_bin=0` and both extreme μ-bins at steps 31–36. Quantify whether the anomaly originates in mechanical explicit, equilibrium, or history terms, and check angular/azimuth concentration and near-wall support.
2. Test whether the current M9 adaptivity field, optimized for absolute mismatch, is misaligned with the **signed** wall contribution. Separate sensitivity of normalized field targets from the choice of mesh; do not retune the model physics or reshape the exact response definition.
3. Only after a source-only, read-only explanation/design QA should an M10 *mesh-only* distinct one-shot be considered. Require 15–25% actual per-pole D029 adaptation and complete D031 before any additional expensive physical FEM. No automatic M10 FEM or repeated M9 one-shot.

Reproducer: `research/tools/p10kw_m8_m7_signed4d_audit.py` (generic adjacent-mesh operands with `--m6` preceding mesh) and `research/tools/p10ld_signed4d_angular_time_map.py`. Numeric output: `research/evidence/P10LD_M9_M8_SIGNED4D_AUDIT.json`.
