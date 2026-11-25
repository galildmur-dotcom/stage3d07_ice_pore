# P10LI — real C++ signed4D CSV writer integration (no FEM)

**Date:** 2026-11-25. **Outcome:** PASS on the real instrumented C++ `p10dd::write_csv` path, without launching physical computation. M9 one-shot remains consumed.

## Integration performed

The new standalone source `research/tools/p10li_cpp_writer_fixture.cpp` compiles the existing `stage3d10w_analytic_adjoint.cpp` translation-unit environment with `STAGE3D10DD_FULL4D` and `STAGE3D10DK_M1_FULL4D`, against the isolated P10LG `stage3d10dd_4d_partition.hpp`. It calls the **actual** P10LG-added signed split writer, not a Python reproduction. No solver entrypoint is called. Synthetic C++ `Snapshot` instances directly populate two nonzero signed geometry/stress cells per time step.

Compilation: `g++ -std=c++20 -fopenmp -O0 -DSTAGE3D06_ROOT_DIR='"."'` plus include paths to `P10LG_WORK`, `P10LG_WORK/tests`, `P10LG_WORK/src`. The standard C++ compile and link both passed.

## Test evidence

| Time discretization | P10LG split data rows | Original P10DD data rows | Nonzero split rows | Σ geometry | Σ stress | Σ original explicit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 × 150 s | 7,200 | 7,206 | 12 | +0.35 | −0.175 | +0.175 |
| 36 × 25 s | 43,200 | 43,236 | 72 | +1.85 | −0.925 | +0.925 |

Writer emits correct 9-column P10LG schema, all 4D bin indices, time stamps, signed terms and their original sums. A parser rereads each output and checks total and bin-specific values. The existing P10DD signed4D CSV output row count remains intact, including 1,200 bins plus a TOP_ROBIN row per step. A deliberately corrupted stress term in one cell is **rejected** by the actual writer on each time grid.

Machine-readable results: `research/P10LI_CPP_WRITER_QA.json`.

## Reproducibility, boundaries and next work

Do not compile/run any physical `P10FN` executable for this test. The fixture uses the P10LG detached work copy; it writes only synthetic CSVs to `p10li_cpp_writer_csv_output` under the temporary directory. The build artifact is not committed. The physical P10DD header pinned by P10LF remains untouched.

The test **does not call `mechanical_step`**, so the Tet10 quadrature geometry and stress-law chain extraction remain untested at the integration level. Mathematical quotient algebra was independently tested by P10LH. Neither test provides new M8/M9 physical component values, and the M9 one-shot marker must never be reused.

**Next stage P10LJ:** design a deterministic small Tet10 mechanical-step fixture whose QP source is physically nonzero, using pinned states/laws and the same mesh geometry or a validated complete saved-state replay. Establish feasibility and data prerequisites before any new native physical one-shot authorization.
