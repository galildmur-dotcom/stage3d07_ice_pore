# P10LH — independent nonzero two-term quadrature fixture

**Date:** 2026-11-25. **State:** PASS on synthetic quadrature fixture; **FEM0/MESH0**. No M9 one-shot replay.

## Purpose

P10LG introduced a signed decomposition of the normalized `PeakMoment` mechanical explicit derivative into a volume/normalization component and a stress-chain component. P10LH checks this mathematical decomposition against a separately constructed full objective, avoiding reuse of its own split as the sole reference.

The new file `research/tools/p10lh_test_two_term_explicit_fixture.py` represents four deliberately nonidentical quadrature points distributed across three bins. Their volumes, sources, volume derivatives and local source derivatives are exact rational numbers; neither component vanishes in any bin. The reference computes the imaginary part of the *unsplit* complex-perturbed quotient `J(h)=weight * sum(v(h)*s(h))/sum(v(h))` at `h=1e-24`.

## Actual results

| Observable | Exact or evaluated value |
| --- | --- |
| Geometry/normalization | `-2150/6069` |
| Stress-chain | `3425/12852` |
| Sum | `-19175/218484` |
| Independent complex-step full quotient derivative | `-0.08776386371542086` |
| Absolute discrepancy | `5.551115123125783e-17` |

Seven checks PASS: (1) exact per-bin decomposition, (2) independent complex-step quotient, (3) permutation and spatial regrouping invariance, (4) invariance under uniform source shift, (5) removing shape-volume derivative zeros only the geometry term, (6) removing source derivative zeros only the stress term, (7) deliberately omitting quotient normalization is demonstrably wrong (>1e-3 discrepancy).

Machine-readable output: `research/P10LH_SYNTHETIC_QP_QA.json`.

## Limitations and next gate

This is an **independent scalar QP algebra test**, not an integration test for the C++ Tet10 function `mechanical_step`, nor a physical EDV/PeakMoment simulation. It validates the quotient decomposition and catches its principal normalization failure mode, but cannot attribute the observed M8→M9 near-wall `+0.19602467 m^-1` change to geometry or stress. The raw physical states needed for such attribution are not demonstrated available.

**Next: P10LI.** Add a C++-level deterministic fixture, preferably using a small separately testable normalization/splitting helper called by `mechanical_step`, while pinning and preserving the physical P10DD code. Test that both bin terms are exported correctly, without starting a physical solve. Only after that determine if a new separately authorized physical attempt or complete saved-state replay is essential.
