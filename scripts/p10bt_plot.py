#!/usr/bin/env python3
"""Two figures from independently verified P10BT derived CSVs (no FEM)."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--derived-dir", type=Path,
                    default=Path(__file__).resolve().parents[1] /
                    "research/evidence/P10BT_H2_TEMPORAL_20261119/derived")
ROOT = parser.parse_args().derived_dir
def rows(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

components = ["explicit", "equilibrium", "history", "total_mechanical"]
labels = ["Explicit", "Equilibrium", "History", "Total mechanical"]
colors = ["#d05c45", "#397ac2", "#a777be", "#17212d"]
windows = [r for r in rows("P10BT_ALIGNED_WINDOWS.csv")
           if r["dt_a"] == "150" and r["dt_b"] == "25"]
pairs = [r for r in rows("P10BT_COMPONENT_PAIRS.csv")
         if r["dt_a"] == "150" and r["dt_b"] == "25"]
p_by_c = {r["component"]: r for r in pairs}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.5),
                              gridspec_kw={"width_ratios": [1.65, 1]})
x = np.arange(6)
width = 0.20
for i, c in enumerate(components):
    vals = [float(next(r["signed_difference"] for r in windows
                       if r["component"] == c and int(r["window_150s"]) == w))
            for w in range(1, 7)]
    ax1.bar(x + (i - 1.5) * width, vals, width=width,
            color=colors[i], label=labels[i])
ax1.axhline(0, color="#888", linewidth=0.9)
ax1.set_xticks(x, ["0–150", "150–300", "300–450", "450–600",
                   "600–750", "750–900"], rotation=25, ha="right")
ax1.set_xlabel("Временной интервал, с")
ax1.set_ylabel("Разность накопленных вкладов (150 с − 25 с), м⁻¹")
ax1.set_title("Изменение компонент по общим интервалам")
ax1.grid(axis="y", alpha=0.2)
ax1.legend(loc="upper left", ncol=2, fontsize=8, frameon=False)
shares = [float(p_by_c[c]["polar_L1_percent"]) for c in components]
ax2.barh(np.arange(4), shares, color=colors)
ax2.axvline(19.621879, linestyle="--", color="#777", linewidth=1.3,
            label="Доля объёма QP 19,62%")
ax2.set_yticks(np.arange(4), labels)
ax2.invert_yaxis()
ax2.set_xlim(0, 100)
ax2.set_xlabel("Доля L₁ в двух полярных поясах, %")
ax2.set_title("Локализация различий\n(пунктир — 19,62% объёма QP)")
for i, share in enumerate(shares):
    ax2.text(share + 1, i, f"{share:.1f}%", va="center", fontsize=9)
ax2.grid(axis="x", alpha=0.2)
fig.suptitle("P10BT • H2, EDV_VAR, R, ξ=0, 900 с • аналитическая геометрическая производная", fontsize=11)
fig.tight_layout()
fig.savefig(ROOT / "P10BT_TIME_COMPONENTS_AND_POLAR.png", dpi=170, bbox_inches="tight")
plt.close(fig)

totals = rows("P10BT_COMPONENT_TOTALS.csv")
ts = [int(r["dt_s"]) for r in totals]
fig, ax = plt.subplots(figsize=(9.5, 4.5))
for i, c in enumerate(components):
    vs = [float(r[c]) for r in totals]
    ax.plot(ts, vs, "o-", linewidth=1.8 if i < 3 else 2.8,
            color=colors[i], label=labels[i])
ax.invert_xaxis()
ax.set_xticks(ts)
ax.set_xlabel("Шаг времени Δt, с (сгущение вправо)")
ax.set_ylabel("Накопленный вклад, м⁻¹")
ax.set_title("P10BT • Механические компоненты и их взаимная компенсация")
ax.axhline(0, color="#888", linewidth=0.8)
ax.grid(alpha=0.18)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.52), fontsize=9, frameon=False)
fig.tight_layout()
fig.savefig(ROOT / "P10BT_COMPONENT_TOTALS.png", dpi=170, bbox_inches="tight")
plt.close(fig)
print("P10BT_PLOTS_OK plots=2 no_FEM=1")
