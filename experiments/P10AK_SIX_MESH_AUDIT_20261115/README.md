# P10AK — evidence package (15 November 2026)

Six-mesh, three-functional spatial sensitivity comparison for the Stage3D07 spherical pore study.

- Source: 13 CSV files included in `input` (12 primary P10W files at W4/W5 + one prior five-mesh P10AC registry CSV for W2 rows).
- Run `python BUILD_REPORT.py` from any folder to reproduce tabular results and verify consistency. If `matplotlib` is available, it will also regenerate the figures.
- Scientific interpretation: see `REPORT_RU.md`. **Do not treat a small relative spread as mathematical proof of spatial convergence.**
- No FEM rerun, Qt Creator, Gmsh or Git operations needed.
- `P10AK_SIX_MESH_DERIVATIVES.csv` holds all 18 grid×functional values.
- `P10AK_MESH_INTERACTIONS.csv` shows mixed contrasts of spatial refinement.
- `P10AK_STEP_DELTAS.csv` shows per-step decomposition for four comparisons.
- `P10AK_COMPONENT_DELTAS.csv` lists component changes with cancellation ratios.
- `P10AK_BALANCE_CHECKS.csv` contains the 12 machine-verified algebraic invariants.
