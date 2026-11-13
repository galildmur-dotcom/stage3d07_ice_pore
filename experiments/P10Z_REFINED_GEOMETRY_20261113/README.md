# P10Z H4 / H4W2 / H4W2B20 / H4W4B2 — four-mesh geometric comparison

- Read `REPORT_RU.md`: observations, verification, limitations, proposed preflight.
- `sources/`: the two original ZIP archives, preserved unchanged.
- `input/BASE` and `input/REFINED`: exact uploaded CSV/TXT and SHA-256 manifests.
- `derived/`: Q3/Q4 tables and `VERIFICATION.txt` with numerical and hash checks.
- `figures/`: PNG and SVG visualizations.
- `make_report.py`: reproduce tables and figures using Python 3 with optional matplotlib.

From this directory, run (into a **new** output directory):

```
python make_report.py --base sources/RUN_H4_H4W2_Q3_Q4_20261113_083721_20261113_083729.zip --refined sources/RUN_H4W4B2_H4W2B20_Q3_Q4_20261113_154536_20261113_154549.zip --out VERIFICATION_REBUILD
```

NOTE: The script reproduces derived tables and graphics, not the narrative report. No FEM solve is performed. Do not equate Q3/Q4 geometry convergence with spatial shape-derivative convergence.
