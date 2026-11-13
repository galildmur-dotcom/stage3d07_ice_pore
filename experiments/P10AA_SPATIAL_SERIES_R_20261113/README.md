# P10AA / Stage3D07 — spatial-series assessment, R / EDV_VAR

**13 November 2026.** Seven mesh results H0, H2, H3, H4, H4W2, H4W2B20, H4W4B2. No new FEM calculation and no claimed continuum convergence proof.

- `REPORT_RU.md`: scientific interpretation, source hierarchy and next necessary lightweight control.
- `input/`: archived earlier mesh values, H0/H2/H3 entries from SOP, primary H4W4B2 CSVs, and prior P10Z QP metrics.
- `derived/`: seven-mesh series, seven pairwise refinements, jpeak-component differences, verification log.
- `figures/`: two plots as PNG/SVG; illustrative discrete mesh comparisons only.
- `tools/rebuild.py`: fully reproduce the derived numerical data; `--no-figures` uses only Python standard library.
- `tools/p10aa_surface_identity.py` and `tools/P10AA_SURFACE_CHECK_ONE_CLICK.cmd`: optional next one-click light audit comparing real curved pore surfaces H4W2 and H4W2B20. Choose files in Explorer dialogs. The program creates a small ZIP under `G:\ildar\PORE_CHATGPT_EXPORTS` and never modifies meshes.
- `tests/`: tiny artificial Tri6 examples in `.msh.txt` (plain-text test fixtures, not production mesh files). Their contents can be parsed directly by `p10aa_surface_identity.py`; they are **not real H4W2/H4W2B20 data**.

To register via Git, apply the **separate add-only `.patch`** using existing PORE ONE CLICK. There is no need to reinstall PORE ONE CLICK or re-run P10W. Confirm whether the previous P10W/H4W4B2 evidence patch was committed independently; this new patch will not replace or conflict with it.
