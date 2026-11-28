# P10PP M21 physical PASS, P10PQ independent signed 4D comparison M20→M21 (2026-11-28)

Input P10PP M21 evidence SHA-256: `78c40462b9d4aed113555a6d0bdf211cd724f1517852290a3ef0d5b7e7f0924d` (CRC PASS). Exact mesh SHA `0908d7f66e3db2e3880089f245872a854c22f67dc6bee3ec87924131e7039dee`. Status `P10PP_M21_REAL_FULL4D_PASS`, forward and analytic adjoint 36/36, independent full signed 4D and explicit geometry/stress two-term audits PASS, source SHA pinned 101 files. Wall 6670.8013s, peak private 9322917888 bytes, no repeated FEM.

| Mesh | dR jpeak (m^-1) | delta from previous (m^-1) |
|---|---:|---:|
| M18 | 2.367014709423416 | — |
| M19 | 2.3593864685556034 | -0.0076282408678127744 |
| M20 | 2.356542538474087 | -0.0028439300815166213 |
| M21 | 2.356187074565611 | -0.00035546390847596143 |

M21-M20 relative -0.0151%; global delta falls by factor ~8 compared to M20-M19. This followed the actually verified narrow-polar M21 refinement, which reduced surface median edges 0-10° by ~15%, with no reduction at equator.

**Caution: global cancellation is severe and pointwise 4D convergence not established.** Independent signed 4D 43,200 matching volume cells: M20→M21 signed positive +0.16100172047769917, negative -0.16135718438617347, abs sum 0.32235890486387264 m^-1, cancellation ratio 906.8681719263452. Prior M19→M20 abs sum 0.345573538799881 m^-1, only 6.7177% reduction. Fraction abs differences: final steps31-36 52.3527%, first four radial bins 44.6234%, mu polar bins0/9 23.1829%.

P10PQ independent read-only comparison ZIP `P10PQ_M20_M21_INDEPENDENT_SIGNED_4D_20261128.zip` SHA-256 `36c7500e81eb9e6e6a80fbf583248b27a98094bbc39331454fa7cc7b8fe2d504` contains original P10PL/P10PP physical evidence, SHA-pinned script, JSON and spatial aggregates. No new mesh/FEM; no generic M22 kappa recommended.

## Next scientific gate
Current 10 latitude bins (mu width 0.2) mix the near-pole 0-8°, 8-23° and remainder of the polar cap up to ~36.9°. Cannot infer fine polar 4D convergence from these aggregates. Before specifying M22, plan a finer-angle **physically grounded** per-element/local signed4D polar audit with consistent time/radial/angular bins and validation against coarse bins. New physical run must be separately one-shot and authorized when necessary; never rerun consumed M21.

Any future mesh must enforce narrow-polar incremental refinement, actual edge-size localization, obligatory `HighOrderElastic`, and full independent QA before FEM.