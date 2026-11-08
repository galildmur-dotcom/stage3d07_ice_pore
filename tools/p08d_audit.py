#!/usr/bin/env python3
"""Independent read-only GH3 audit for P08D report CSVs; stdlib only.

Usage: python tools/p08d_audit.py PATH_TO_FOLDER_CONTAINING_FOUR_P08D_FILES
Does not launch FEM, modify results or require local VTU/mesh files.
"""
import argparse
import csv
import math
from collections import Counter
from pathlib import Path

MODES = ("R", "tz", "y20")
XIS = (-math.sqrt(3), 0.0, math.sqrt(3))
WEIGHTS = (1/6, 2/3, 1/6)


def need(flag, message):
    if not flag:
        raise ValueError(message)


def close(a, b, what, *, atol=1e-13, rtol=1e-9):
    need(math.isfinite(a) and math.isfinite(b), f"{what}: nonfinite")
    need(math.isclose(a, b, abs_tol=atol, rel_tol=rtol),
         f"{what}: actual {a:.17g}, saved {b:.17g}")


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def audit(directory):
    status = dict(line.strip().split("=", 1) for line in
                  (directory / "P08D_STATUS.txt").read_text(encoding="utf-8-sig").splitlines() if line.strip())
    need(status.get("status") == "SUCCESS", "P08D_STATUS is not SUCCESS")
    need(status.get("modes") == "R,tz,y20", "modes mismatch")
    need(int(status["tend"]) % int(status["dt"]) == 0, "inconsistent time steps")
    expected_steps = int(status["tend"]) // int(status["dt"])
    sensitivities = rows(directory / "P08D_SENSITIVITIES.csv")
    nodes = rows(directory / "P08D_NODES.csv")
    samples = rows(directory / "P08D_SAMPLES.csv")
    need(len(sensitivities) == 3 and len(nodes) == 9 and len(samples) == 18, "incorrect row counts")
    need(Counter(r["mode"] for r in sensitivities) == Counter(MODES), "bad sensitivity modes")
    need(Counter((r["mode"], r["sign"], r["xi"]) for r in samples) ==
         Counter((m, s, n["xi"]) for m in MODES for s in ("plus", "minus")
                 for n in nodes if n["mode"] == m), "missing or duplicate FEM samples")
    for s in samples:
        need(int(s["steps"]) == expected_steps, "incomplete trajectory in sample")
        need(s["source"] in {"LOCAL_FEM", "EXTERNAL_XI0"}, "unknown source type")
        need(math.isfinite(float(s["j6"])) and math.isfinite(float(s["Phi6_final"])), "bad sample value")
    rows_out = []
    for mode in MODES:
        selected = [s for s in sensitivities if s["mode"] == mode]
        need(len(selected) == 1, f"expected one summary row for {mode}")
        summary = selected[0]
        group = sorted((n for n in nodes if n["mode"] == mode), key=lambda n: float(n["xi"]))
        need(len(group) == 3, f"expected three nodes for {mode}")
        for k, n in enumerate(group):
            need(n["mesh"] == status["mesh"], "mesh disagrees with STATUS")
            need(int(n["dt_s"]) == int(status["dt"]) and
                 int(n["tend_s"]) == int(status["tend"]), "time mismatch")
            close(float(n["xi"]), XIS[k], "GH node", atol=1e-14)
            close(float(n["weight"]), WEIGHTS[k], "GH weight", atol=1e-14)
            for sign in ("plus", "minus"):
                ss = [s for s in samples if s["mode"] == mode and s["sign"] == sign and
                      abs(float(s["xi"]) - XIS[k]) < 1e-13]
                need(len(ss) == 1, "missing sample matching node")
                close(float(n[f"j6_{sign}"]), float(ss[0]["j6"]), "sample/node j6")
                close(float(ss[0]["delta_um"]), float(n["delta_um"]), "sample delta")
                close(float(ss[0]["weight"]), float(n["weight"]), "sample/node weight")
        for sign in ("plus", "minus"):
            hashes = {s["mesh_fnv64"] for s in samples if s["mode"] == mode and s["sign"] == sign}
            need(len(hashes) == 1, f"mesh hash changes across GH nodes: {mode} {sign}")
        delta = float(summary["delta_um"]) * 1e-6
        need(delta > 0, "non-positive shape perturbation")
        plus = [float(n["j6_plus"]) for n in group]
        minus = [float(n["j6_minus"]) for n in group]
        dj = [(p-m)/(2*delta) for p,m in zip(plus, minus)]
        mid = [(p+m)/2 for p,m in zip(plus, minus)]
        for k,n in enumerate(group):
            close(dj[k], float(n["D_j6_per_m"]), "node shape derivative", atol=1e-11)
            close(mid[k], float(n["j6_midpoint"]), "node midpoint")
        mp = sum(w*v for w,v in zip(WEIGHTS, plus))
        mm = sum(w*v for w,v in zip(WEIGHTS, minus))
        mean = (mp+mm)/2
        vp = sum(w*(v-mp)**2 for w,v in zip(WEIGHTS, plus))
        vm = sum(w*(v-mm)**2 for w,v in zip(WEIGHTS, minus))
        var_mid = sum(w*(v-mean)**2 for w,v in zip(WEIGHTS, mid))
        dmean = sum(w*v for w,v in zip(WEIGHTS, dj))
        dvar = 2*sum(w*(v-mean)*(deriv-dmean) for w,v,deriv in zip(WEIGHTS, mid, dj))
        close(dmean, (mp-mm)/(2*delta), "Dmean independent formula", atol=5e-12)
        close(dvar, (vp-vm)/(2*delta), "Dvariance independent formula", atol=5e-12)
        for key, value in (("mean_plus", mp), ("mean_minus", mm), ("mean_midpoint", mean),
                           ("variance_plus", vp), ("variance_minus", vm),
                           ("variance_midpoint", var_mid),
                           ("D_mean_per_m", dmean), ("D_variance_per_m", dvar),
                           ("xi0_D_j6_per_m", dj[1])):
            close(value, float(summary[key]), f"{mode} {key}", atol=5e-12)
        need(vp >= 0 and vm >= 0 and var_mid >= 0, "negative GH variance")
        rows_out.append((mode, dmean, dvar, mean, var_mid, dj[1],
                         (dmean/dj[1]-1)*100 if dj[1] != 0 else float("nan")))
    modes_means = [r[3] for r in rows_out]
    print(f"P08D AUDIT PASS: {status['mesh']}, dt={status['dt']} s, t_f={status['tend']} s")
    print(f"Sources: {dict(Counter(s['source'] for s in samples))}; 9 GH nodes, 18 samples")
    for mode, dm, dv, m, v, d0, percentage in rows_out:
        print(f"{mode:4}  Dmean={dm:+.12e}  Dvariance={dv:+.12e}  "
              f"mean_mid={m:.12e}  variance_mid={v:.12e}  "
              f"D_xi0={d0:+.12e}  (Dmean/Dxi0-1)={percentage:+.4f}%")
    print(f"Spread of three baseline means: {max(modes_means)-min(modes_means):.6e}")
    print("NOTE: output CSV consistency only; solver residuals and VTU contents not independently checked")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    args = p.parse_args()
    try:
        audit(args.directory)
    except (ValueError, KeyError, OSError) as exc:
        p.error(f"P08D AUDIT FAIL: {exc}")
