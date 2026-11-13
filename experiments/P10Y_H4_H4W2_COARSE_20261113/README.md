# P10Y H4/H4W2 - mechanical shell aggregation on fixed B6

This folder holds derived CSV files and vector figures for the report
`docs/STAGE3D10Y_H4_H4W2_COARSE_AGGREGATION_20261113.md`.

Source input files are intentionally **not duplicated**. Use:
`experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4_SHELL_SUMMARY.csv`
and
`experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4W2_SHELL_SUMMARY.csv`.
SHA-256 is recorded in VERIFICATION.txt.

Rebuild from repository root with Python3 + optional matplotlib:

```
python tools/p10y_coarse_aggregation.py --h4 experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4_SHELL_SUMMARY.csv --h4w2 experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4W2_SHELL_SUMMARY.csv --out P10Y_REBUILD
```

The heat adjoint is NOT split by shells. Analysis is not proof of convergence.
