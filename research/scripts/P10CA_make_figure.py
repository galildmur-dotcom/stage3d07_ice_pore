#!/usr/bin/env python3
"""Reproducible small scientific visualization of audited P10CA H0 CSV."""
import csv
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter


def main(zip_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_script = Path(__file__).with_name("P10CA_offline_audit.py")
    data = json.loads(subprocess.check_output(
        [sys.executable, str(audit_script), str(zip_path)], text=True))

    intervals = [("0–0.02", 0, .02), (".02–.05", .02, .05),
                 (".05–.10", .05, .10), (".10–.25", .10, .25),
                 (".25–.50", .25, .5), (".5–1", .5, 1),
                 ("1–2", 1, 2), ("2–5", 2, 5),
                 ("5–15", 5, 15), ("≥15", 15, None)]
    radial = data["radial_shells"]
    with (output_dir / "P10CA_RADIAL_H0_THERMAL_D_R_JPEAK.csv").open(
            "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["shell_bin", "wall_distance_mm", "total_per_m",
                         "mass_per_m", "diffusion_per_m", "qp_count_6steps",
                         "volume_m3_6steps"])
        for i, row in enumerate(radial):
            writer.writerow([i, intervals[i][0], row["total"], row["mass"],
                             row["diffusion"], row["qp"], row["volume"]])

    polar = data["polar_bands"]
    with (output_dir / "P10CA_POLAR_H0_THERMAL_D_R_JPEAK.csv").open(
            "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["polar_bin", "cos_theta_lower", "cos_theta_upper",
                         "total_per_m"])
        for i, row in enumerate(polar):
            writer.writerow([i, f"{-1+.2*i:.1f}", f"{-1+.2*(i+1):.1f}",
                             row["total"]])

    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "axes.titlesize":12, "axes.labelsize":10})
    fig, ax = plt.subplots(1,2,figsize=(12.5,5.2),gridspec_kw={"wspace":.30})
    signed = lambda y: ["#c5563b" if v>0 else "#34769e" for v in y]
    rv = [float(Decimal(row["total"])) for row in radial]
    pv = [float(Decimal(row["total"])) for row in polar]
    ax[0].bar(range(10),rv,color=signed(rv),width=.75)
    ax[0].axhline(0,color="#555555",linewidth=.85)
    ax[0].set_xticks(range(10),[x[0] for x in intervals],rotation=40,ha="right")
    ax[0].set_xlabel("Расстояние от стенки поры, мм")
    ax[0].set_ylabel(r"Вклад в $D_R j_{peak}$, м$^{-1}$")
    ax[0].set_title("а) Радиальные оболочки")
    ax[0].text(7.0,max(rv)*.73,"2–5 мм:\n+0,06916 м⁻¹",ha="center",fontsize=9)

    ax[1].bar(range(10),pv,color=signed(pv),width=.75)
    ax[1].axhline(0,color="#555555",linewidth=.85)
    ax[1].set_xticks(range(10),[str(i) for i in range(10)])
    ax[1].set_xlabel("Угловой интервал (0: cosθ∈[−1;−0,8], …, 9: [0,8;1])")
    ax[1].set_ylabel(r"Вклад в $D_R j_{peak}$, м$^{-1}$")
    ax[1].set_title("б) Полярные пояса")
    fig.suptitle("H0 · EDV/VAR · R · 6×150 с · тепловая часть геометрической производной",
                 fontsize=13,y=.975)
    fig.text(.5,.005,
             "Сумма по 6 шагам: +0,06637955 м⁻¹. За 5 мм вклад равен нулю по определению поля скорости; сеточная сходимость не проверялась.",
             ha="center",va="bottom",fontsize=9)
    fig.subplots_adjust(bottom=.24,top=.86,left=.085,right=.985)
    fig.savefig(output_dir / "P10CA_H0_THERMAL_RADIAL_POLAR.png",dpi=175)
    plt.close(fig)
    print(f"FIGURE_CREATED rows={len(radial)}+{len(polar)} at {output_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
