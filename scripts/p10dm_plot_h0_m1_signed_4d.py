#!/usr/bin/env python3
"""Static scientific diagnostic plot of verified H0/M1 signed 4D bin groups."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/evidence/P10DM_P10DL_REAL_M1_H0_PAIR_20261121/derived/P10DM_REAL_M1_H0_PAIR_AUDIT.json"
TARGET = SOURCE.with_name("P10DM_H0_M1_SIGNED_4D_TIME_RADIAL_POLAR.png")


def main() -> None:
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    profiles = {x["group"]: x for x in report["group_profiles"]}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
    series = [
        ("Вклад временных шагов", [f"time_step_{i}" for i in range(1, 7)],
         ["150", "300", "450", "600", "750", "900"], "t, с"),
        ("Радиальные слои от поры", [f"radial_bin_{i}" for i in range(8)],
         ["0–.02", ".02–.05", ".05–.1", ".1–.25", ".25–.5",
          ".5–1", "1–2", "2–5"], "Отступ от стенки, мм"),
        ("Угловые полосы", [f"mu_bin_{i}" for i in range(10)],
         [str(i) for i in range(10)], "Номер μ-интервала"),
    ]
    for ax, (title, groups, labels, xlabel) in zip(axes, series):
        x = np.arange(len(groups))
        h0 = [profiles[g]["h0_signed_per_m"] for g in groups]
        m1 = [profiles[g]["m1_signed_per_m"] for g in groups]
        ax.axhline(0, color="#6b7280", linewidth=0.8)
        if title == "Угловые полосы":
            ax.axvspan(-.4, .4, facecolor="#e11d48", alpha=.07)
            ax.axvspan(8.6, 9.4, facecolor="#e11d48", alpha=.07)
        ax.plot(x, h0, marker="o", markersize=5, color="#2563eb", label="M0 = H0")
        ax.plot(x, m1, marker="s", markersize=4.7, color="#ea580c", label="M1")
        ax.set_xticks(x, labels, rotation=45 if title == "Радиальные слои от поры" else 0)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=15)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Знаковый вклад в $D_R j_{peak}$, м$^{-1}$")
        ax.grid(axis="y", color="#e5e7eb", linewidth=.8)
        ax.legend(frameon=False, fontsize=9, loc="best")
    fig.suptitle("Сферическая пора в льду: H0 → M1, физический расчет, 6 × 150 с",
                 fontsize=14, weight="bold")
    fig.text(.5, -.025,
             "Суммы дискретных подписанных 4D вкладов, а не поточечные погрешности. "
             "Полярные края: μ = 0 и 9. R, EDV_VAR, ξ = 0, jpeak, B6.",
             ha="center", fontsize=9, color="#4b5563")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(TARGET, dpi=190, bbox_inches="tight", facecolor="white")
    print("P10DM_H0_M1_SIGNED_4D_FIGURE_OK", TARGET, TARGET.stat().st_size)


if __name__ == "__main__":
    main()
