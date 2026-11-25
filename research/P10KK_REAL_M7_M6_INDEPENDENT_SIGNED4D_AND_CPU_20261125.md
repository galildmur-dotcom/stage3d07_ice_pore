# P10KK — независимый M7−M6 full signed4D, 2026-11-25

**Outcome: real M7 FEM PASS; full4D comparison PASS; spatial convergence NOT proven.** Received actual user `P10KJ_M7_FIRST_FULL4D_EVIDENCE.zip` SHA256 `0bc50329078cba02f2a5ad55bfcee1d42ef4cf0475d44430598982c233ba5ec7`, CRC PASS, 9 files. Native exit=0, wall 1137.464 s, private peak 2,562,580,480 bytes, consumed new M7 FEM marker; never retry. Exact M7 SHA `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d`, 17558 nodes, 12001 Tet10. R/EDV_VAR/xi0/B6 5mm, 36x25s, fresh forward and analytic same-M7 adjoint, 4 requested threads. Independent 4D temporal audit 43,236 rows PASS.

Independent key-join by (mode,functional,step,time starts/ends,region,radial_bin,mu_bin,phi_bin), comparing **all 43,236 signed4D rows** with preserved M6 and M5 source CSV SHA256 `dd6e248d5410a18c9821d36e544028d7b64a028fddf1e125e234f24965a3bb1f` and `0241992ca09dcb4f04acbcfac96be910c07a99a3ad9d68868692cc49023b114b`:

| Quantity (1/m) | M5 | M6 | M7 |
| --- | ---: | ---: | ---: |
| D_R J_peak | +2.36412099140283 | +2.36265278778623 | +2.37252795321708 |

- Signed Δ(M6−M5) = −0.00146820361660; signed Δ(M7−M6) = **+0.00987516543085**. Ratio of magnitudes 6.726019. Sign reverses: cannot claim monotone convergence.
- Full signed4D L1 across all bins/time: M6−M5 **1.929118585642**; M7−M6 **1.066029765758** (0.5526 ratio). Absolute 4D field change declines, but remains large relative to global signed Δ.
- Cancellation (L1/|signed Δ|): M6−M5 **1313.931**; M7−M6 **107.951**. Significant cancellation persists.
- Using *exactly pole-most mu bins* (mu9 north, mu0 south): M7−M6 north +0.0414325162163, south +0.0159042014234, nonpolar −0.0474615522088. The preceding difference in the same definition gives M6−M5 north +0.2779278133903, south +0.0416064301594, nonpolar −0.3210024471663. These single-bin polar definitions are distinct from some previous multi-bin polar audit definitions; do not compare them as identical without matching bin sets.
- Component Δ(M7−M6) [1/m]: explicit +0.094648586; equilibrium −0.054713113; history −0.029805503; thermal mass −0.000004083; thermal diffusion −0.000250722. Last physical step 35 gives largest per-step signed and L1 change, pointing to late-time dynamics.

**Measured CPU:** Windows GetProcessTimes aggregate CPU=2338.65625 s / wall=1137.464 s = **2.056 average busy logical CPUs**, 25.70% of 8-logical host, well below potential 4/8=50%. Independent progress 76 ticks at 15 s and 65 s silent-child preflight 5 ticks; performance bottleneck reason unproven, no physical model changes. The coarse native log first saw forward at 17.04 s and adjoint at 424.11 s; not exact internal timers.

Machine-readable evidence + time, polar, radial CSV and PNG stored in `P10KK_M7_M6_INDEPENDENT_FULL4D_ANALYSIS_20261125.zip`, Library `libfile_427f3dcaa0d081919761e3fb4c0c6f1a`.

**Next scientific step P10KL:** source-only diagnostic of the M5→M6→M7 discrepancy, late-time step 35 and polar/nonpolar signed cancellation; inspect sector-level evolution and compare single-/multi-bin pole definitions. Then decide scientifically if mesh M8 is needed, without launching new FEM automatically. Existing consumed M7 marker must not be repeated. User authorizes self-run Windows program, no repeated permission requests.
