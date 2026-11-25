# P10LJ — actual Tet10 27-QP mechanical-step two-term split, source-only

**Date:** 2026-11-25. **State:** PASS for the actual C++ `ice3d::p10dd::mechanical_step`, on a standalone synthetic quadratic tetrahedron. **FEM0 / MESH0**; M9 one-shot remains consumed.

## Test setup

The test in `research/tools/p10lj_cpp_tet10_mechanical_fixture.cpp` compiles the pinned source environment of the isolated P10LG variant. It constructs one properly oriented straight-sided Tet10, six midpoint nodes, 27 true production quadrature points (`volume_q(3)`), a material `p10c::Step` (constitutive `EDV` linearization from the production source), one active B6 observation element, and non-affine variations of nodal displacement and shape velocity at two mid-edge nodes. Temperature offsets, history and adjoint equilibrium load are zero in this deliberately local fixture. The physical solver is not invoked: **`mechanical_step` is called directly**.

## Observed values

| Quantity | Actual C++ output |
| --- | ---: |
| Mechanical quadrature points | 27 |
| Occupied signed4D bins | 9 |
| Observation volume | `1.3333333333333285e-9 m^3` |
| Signed geometry/normalization component | `+0.24616897823341907` |
| Signed stress-chain component | `-5.2706365989942645` |
| Original signed `explicit_objective` | `-5.0244676207608459` |

The actual per-cell P10LG closure executed internally for each cell. Independently accumulated geometry + stress also agrees with the original explicit sum. Both contributions are demonstrably nonzero and substantially of opposite sign. The test repeats the same physical state with the **opposite shape-velocity field** and checks that both signed contributions negate; with zero shape velocity, all per-cell contributions are exactly zero. All tests PASS.

Machine-readable QA: `research/P10LJ_CPP_TET10_MECHANICAL_QP_QA.json`.

## Interpretation and limits

This evidence confirms that the C++ Tet10 quadrature path actually computes two nontrivial terms in the opt-in diagnostic; P10LH separately checked the normalized quotient against independent complex-step, and P10LI exercised the actual CSV writer. Taken together they provide three different kinds of verification, without additional native FEM or Gmsh runs.

The local synthetic state is **not** globally equilibrated, does not reproduce the transient EDV adjoint field, and is not a reconstructed M8/M9 computation. These unit-test values are not meaningful physical ice sensitivities, and cannot explain the pole-localized M8→M9 difference. This fixture has zero `lambda` and zero future-history adjoint so equilibrium/history branches are intentionally outside its scope. No central finite differences were used.

## Next scientific gate: P10LK

Inventory the already collected physical evidence and determine whether the complete QP states and adjoints required by the now-tested split are available for deterministic read-only replay. If not, prepare a properly guarded **new** explicitly authorized physical attempt; do not treat the consumed M9 one-shot as reusable. Only physically observed spatial bins can distinguish polar mesh quality, normalized volume effects, and the stress-law chain contribution.
