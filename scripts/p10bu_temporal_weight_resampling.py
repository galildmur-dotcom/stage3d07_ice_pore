#!/usr/bin/env python3
"""P10BU: inspect existing P10BS H2 data using the verified P10K time weights.

This is an algebraic resampling diagnostic of the *explicit* geometric partial,
not a re-solve, a true time-error estimate, or a claim about equilibrium/history
instantaneous values. No files in the input directory are changed.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import math
from pathlib import Path

DTS = (150, 75, 50, 25)
HASHES = {
    150: "4652c2def95ec28d36ca68315e18271a9de147560a90f13b012005358aafebd3",
    75: "81d6e884df060ce582075826380ad2e18f0a1c6c1d562e643023c01152cea64f",
    50: "aa8d9f8ca21a0502f51ba6b1f6f7dc5020b5ebad8e014cb6b1f5fa733abb9bd9",
    25: "7c6cbb9d7fd68aec1ac07d4530efa73073fee4e7cf6aed7811ec594969ae29a6",
}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        data = list(csv.DictReader(f))
    if not data or any(None in r or None in r.values() for r in data):
        raise ValueError(f"Bad CSV: {path}")
    return data


def close(a: float, b: float, name: str, tol: float = 4e-11) -> None:
    if not math.isfinite(a) or abs(a - b) > tol:
        raise ValueError(f"{name}: {a:.17g} != {b:.17g}")


def weights(dt: int, t: int) -> float:
    n = 900 // dt
    if t not in range(dt, 901, dt):
        raise ValueError(f"Time {t} not on dt{dt} grid")
    return (0.5 if t == 900 else 1.0) / n


def write_csv(path: Path, data: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--reference-totals", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.resolve() == args.input_dir.resolve():
        raise ValueError("Output folder must differ from source folder")
    summary = {int(r["dt_s"]): r for r in read(args.summary)}
    reference = {int(r["dt_s"]): r for r in read(args.reference_totals)}
    if set(summary) != set(DTS) or set(reference) != set(DTS):
        raise ValueError("Missing one of the four published schedules")
    series = {}
    terminal = []
    for dt in DTS:
        path = args.input_dir / f"DT{dt}_P10BD_QP_POLAR_RADIAL.csv"
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != HASHES[dt]:
            raise ValueError(f"Source SHA mismatch dt={dt}")
        data = read(path)
        groups = collections.defaultdict(list)
        for r in data:
            t = int(r["time_s"])
            if t != int(r["time_step"]) * dt:
                raise ValueError(f"Wrong t in dt{dt}")
            groups[t].append(r)
        if set(groups) != set(range(dt, 901, dt)):
            raise ValueError(f"Wrong time grid for dt{dt}")
        if any(len(v) != 200 for v in groups.values()):
            raise ValueError(f"Wrong per-step cell count for dt{dt}")
        for t, group in groups.items():
            cell_keys = {(r["shell_lower_mm"], r["radial_subbin"], r["polar_band"])
                         for r in group}
            if len(cell_keys) != 200:
                raise ValueError(f"Duplicate/missing QP cells dt{dt} t={t}")
        J = float(summary[dt]["objective_jpeak"])
        if not J > 0:
            raise ValueError("Nonpositive peak norm")
        chain = J**(-7) / 8
        exp_raw = {t: math.fsum(float(r["explicit_per_m"]) for r in group)
                   for t, group in groups.items()}
        hist_raw = {t: math.fsum(float(r["history_per_m"]) for r in group)
                    for t, group in groups.items()}
        explicit_moment = {t: exp_raw[t] / (chain * weights(dt, t))
                           for t in groups}
        moment_integrated = math.fsum(weights(dt, t) * explicit_moment[t]
                                     for t in groups)
        original_sum = math.fsum(exp_raw.values())
        close(moment_integrated * chain, original_sum,
              f"Explicit moment reconstruction dt{dt}")
        close(original_sum, float(reference[dt]["explicit"]),
              f"P10BT explicit matching dt{dt}")
        if abs(hist_raw[900]) > 2e-12:
            raise ValueError(f"Nonzero history on terminal dt{dt}")
        if any(float(r["history_per_m"]) != 0.0 for r in groups[900]):
            raise ValueError(f"Nonzero per-cell terminal history dt{dt}")
        terminal.append({"dt_s": dt, "terminal_time_s": 900,
                         "terminal_explicit": exp_raw[900],
                         "terminal_history": hist_raw[900],
                         "prior_step_history": hist_raw[900 - dt],
                         "terminal_half_weight": weights(dt, 900),
                         "interior_full_weight": weights(dt, 900 - dt)})
        series[dt] = {"J": J, "chain": chain, "moment": moment_integrated,
                      "explicit": original_sum, "trace": explicit_moment}

    fine = series[25]
    rows = []
    for dt in (150, 75, 50):
        coarse = series[dt]
        n = 900 // dt
        q_fine_on_coarse = math.fsum(
            weights(dt, t) * fine["trace"][t]
            for t in range(dt, 901, dt)
        )
        # Exact telescoping identity for the selected fine-trace reference.
        normalization = (coarse["chain"] - fine["chain"]) * fine["moment"]
        sampled_trace = coarse["chain"] * (coarse["moment"] - q_fine_on_coarse)
        resampled_quadrature = coarse["chain"] * (q_fine_on_coarse - fine["moment"])
        signed = coarse["explicit"] - fine["explicit"]
        closure = normalization + sampled_trace + resampled_quadrature - signed
        close(closure, 0, f"Telescoping explicit dt{dt}-25", 1e-12)
        rows.append({
            "coarse_dt_s": dt, "fine_dt_s": 25, "coarse_steps": n,
            "coarse_explicit_per_m": coarse["explicit"],
            "fine_explicit_per_m": fine["explicit"],
            "explicit_difference_per_m": signed,
            "chain_normalization_per_m": normalization,
            "sampled_forward_trace_per_m": sampled_trace,
            "fine_trace_resampled_quadrature_per_m": resampled_quadrature,
            "telescoping_closure_per_m": closure,
        })

    matched = []
    for t in range(150, 901, 150):
        values = [series[dt]["trace"][t] for dt in DTS]
        pct = 100 * (max(values) - min(values)) / max(1e-30, abs(values[-1]))
        matched.append({
            "time_s": t,
            **{f"unweighted_explicit_moment_dR_dt{dt}": series[dt]["trace"][t]
               for dt in DTS},
            "max_minus_min_percent_vs_dt25": pct,
        })
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "P10BU_EXPLICIT_DECOMPOSITION.csv", rows)
    write_csv(args.out / "P10BU_MATCHED_TIME_EXPLICIT.csv", matched)
    write_csv(args.out / "P10BU_TERMINAL_HISTORY.csv", terminal)
    report = [
        "P10BU READ-ONLY TEMPORAL WEIGHT AND EXPLICIT MOMENT RESAMPLING",
        "HORIZON_S=900",
        "FORMULA_JPEAK=EIGHTH_ROOT_OF_TRAPEZOIDAL_MEAN_PEAK_POWER",
        "FORMULA_CHAIN=JPEAK_POWER_MINUS_SEVEN_DIVIDED_BY_EIGHT",
        "FORMULA_WEIGHT_INTERIOR=1/STEPS",
        "FORMULA_WEIGHT_TERMINAL=0.5/STEPS",
        "SOURCE_INITIAL_MOMENT_SHAPE_DERIVATIVE=ZERO_BY_CONSTANT_INITIAL_VALUE",
        *(f"DT{dt}_CHAIN={series[dt]['chain']:.15g}"
          for dt in DTS),
        *(f"DT{dt}_SOURCE_SHA256={HASHES[dt]}"
          for dt in DTS),
        *(f"DT{r['coarse_dt_s']}_MINUS_25 "
          f"explicit={r['explicit_difference_per_m']:+.12f} "
          f"chain={r['chain_normalization_per_m']:+.12f} "
          f"common_trace={r['sampled_forward_trace_per_m']:+.12f} "
          f"fine_trace_quadrature={r['fine_trace_resampled_quadrature_per_m']:+.12f}"
          for r in rows),
        "P10BU_READ_ONLY_TEMPORAL_WEIGHT_RECONSTRUCTION_OK",
        "NOTE=RESAMPLING IS AN EXACT ALGEBRAIC DIAGNOSTIC NOT A CAUSAL OR TRUE_ERROR ESTIMATE",
        "FEM=0",
    ]
    (args.out / "P10BU_RESULT.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
