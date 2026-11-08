# Stage3D06-P3 delta from Stage3D06-P2

* `src/p3_mcsgs.hpp`: greedy deterministic block graph coloring and symmetric multi-color forward/backward substitution, persistent OpenMP team for all colors in an application, reusable work buffers.
* `src/mechanical.cpp`: BCSRTopology stores coloring; BCSR applies MC-SGS; PCG switches Jacobi/SGS/MC-SGS; P2 SpMV preserved.
* `src/spatial_reology.cpp`: CLI `--preconditioner mcsgs`, profiling labels.
* `src/qt_benchmark_p.cpp`: accepts MC-SGS and separate P3 output target; reuses native, shell-free 2-stage thermal/mechanics launcher.
* `tests/p3_mcsgs_unit.cpp`, `scripts/p3_test_h0.py`: SPD, symmetry, deterministic OpenMP, constraints, H0 6-physics comparison and full checkpoint.
* `CMakeLists.txt`: 2 native P3 Qt targets, unit and real FEM CTest entries, and no-OpenMP fallback.
* Source P2 baseline kept in `baseline_serial/`; previous P2 target names remain supported.
