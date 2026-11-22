#!/usr/bin/env python3
"""Plot reproducible signed 4D projections of real M0/M1/M2 R gradients."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "research/evidence/P10FM_M0_M1_M2_R_4D_20261122/derived"

with (DERIVED / "P10FM_AXIS_PROJECTIONS.csv").open(newline="") as handle:
    rows = list(csv.DictReader(handle))

fig, axes = plt.subplots(2, 4, figsize=(16, 7), layout="constrained")
axes_order = ("r", "mu", "phi", "t")
titles = {"r": "Radial bins (distance from pore)",
          "mu": "Polar bins (south → north)",
          "phi": "Azimuth bins", "t": "Time steps (150 s each)"}
colors = {"M0": "#5c6bc0", "M1": "#ff8f00", "M2": "#00897b"}
for col, axis in enumerate(axes_order):
    data = sorted((r for r in rows if r["axis"] == axis and
                   r["component"] == "total_per_m"), key=lambda r: int(r["bin"]))
    xs = [int(r["bin"]) + (1 if axis == "t" else 0) for r in data]
    for name in ("M0", "M1", "M2"):
        axes[0, col].plot(xs, [float(r[name]) for r in data], "o-", ms=3.5,
                          lw=1.3, color=colors[name], label=name)
    axes[1, col].bar(xs, [float(r["M2_minus_M1"]) for r in data],
                     color="#3f83c5", alpha=.85)
    axes[0, col].set_title(titles[axis], fontsize=10)
    axes[0, col].axhline(0, color="black", lw=.65)
    axes[1, col].axhline(0, color="black", lw=.65)
    axes[1, col].set_xlabel({"r": "r bin", "mu": "mu bin", "phi": "phi bin", "t": "step"}[axis])
    axes[0, col].grid(alpha=.2)
    axes[1, col].grid(axis="y", alpha=.2)
    if col == 0:
        axes[0, col].set_ylabel("Signed contribution, m$^{-1}$")
        axes[1, col].set_ylabel("M2 − M1, m$^{-1}$")
axes[0, 0].legend(loc="best")
fig.suptitle("Stage3D07: REAL M0/M1/M2, R / EDV_VAR / ξ=0, jpeak, 6×150 s\n"
             "Common physical bins; top Robin excluded from projections", fontsize=12)
fig.savefig(DERIVED / "P10FM_M0_M1_M2_ALL_AXES.png", dpi=160)
print("P10FM_ALL_AXES_PLOT_OK")
