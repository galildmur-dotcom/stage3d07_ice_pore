#!/usr/bin/env python3
"""P10BS: read-only component and global/local compensation audit, no FEM.

The P10BB QP polar data contain mechanical components, whereas the P10BE
comparison data retain only their sum. No missing component or thermal field
is reconstructed or imputed.
"""
from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BB = ROOT / "experiments/P10BB_W5B2_SPHERICAL_20261118/input"
BE = ROOT / "research/evidence/P10BE_H2_20261118/input"
FILES = {
    "W4B2": (BB / "H4W4B2_P10BA_QP_POLAR_RADIAL.csv", "219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447"),
    "W5B2": (BB / "H4W5B2_P10BA_QP_POLAR_RADIAL.csv", "8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c"),
    "W4B20": (BB / "H4W4B20_P10BA_QP_POLAR_RADIAL.csv", "3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be"),
    "summary": (BE / "P10BE_TEMPORAL_SUMMARY.csv", "cad940f94f5e8819fd547fc73cded038b4cd7b5691fdb37ae05659c0abdcffc9"),
    "cells": (BE / "P10BE_CELL_TEMPORAL_COMPARE.csv", "e16a580d4935580b6b5228ce3f10edd80e67534b2306ef73c8b9fb77df0ffc7e"),
}
COMPONENTS = ("explicit_per_m", "equilibrium_per_m", "history_per_m")
TOL = 3e-11


def read(name: str) -> list[dict[str, str]]:
    path, expected = FILES[name]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"SHA mismatch {path}: {digest} != {expected}")
    with path.open(newline="", encoding="utf-8-sig") as inp:
        rows = list(csv.DictReader(inp))
    if not rows or any(None in row for row in rows):
        raise ValueError(f"Bad CSV: {path}")
    print(f"INPUT_OK {name} rows={len(rows)} sha256={digest}")
    return rows


def near(actual: float, expected: float, what: str, tol: float = TOL) -> None:
    if not math.isfinite(actual) or abs(actual - expected) > tol:
        raise ValueError(f"{what}: {actual:.17g} != {expected:.17g} (tol {tol})")


def key(row: dict[str, str]) -> tuple[float, float, int, int]:
    return (round(float(row["shell_lower_mm"]), 8),
            round(float(row["shell_upper_mm"]), 8),
            int(row["radial_subbin"]), int(row["polar_band"]))


def get_step_six(name: str) -> dict[tuple[float, float, int, int], dict[str, str]]:
    all_rows = read(name)
    if len(all_rows) != 400 or sorted({int(r["time_step"]) for r in all_rows}) != [5, 6]:
        raise ValueError(f"{name}: expected 400 rows from steps 5 and 6")
    rows = [row for row in all_rows if int(row["time_step"]) == 6]
    result = {key(row): row for row in rows}
    if len(result) != 200 or len(rows) != 200:
        raise ValueError(f"{name}: not 200 unique step-6 cells")
    for row in rows:
        if int(row["qp_count"]) != int(row["positive_qp"]) + int(row["negative_qp"]):
            raise ValueError("QP count partition failed")
        near(math.fsum(float(row[c]) for c in COMPONENTS),
             float(row["total_mechanical_per_m"]), "three-component closure", 2e-13)
        near(float(row["positive_mechanical_per_m"]) + float(row["negative_mechanical_per_m"]),
             float(row["total_mechanical_per_m"]), "signed QP closure", 2e-13)
    return result


def sum_field(rows: list[dict[str, str]], field: str) -> float:
    return math.fsum(float(row[field]) for row in rows)


def compare_spatial(base: dict, other: dict, label: str) -> None:
    if base.keys() != other.keys():
        raise ValueError(f"{label}: different physical cell keys")
    print(f"SPATIAL {label} cells=200 step=6 mechanical_only=YES")
    all_diffs = []
    for component in (*COMPONENTS, "total_mechanical_per_m"):
        differences = {k: float(other[k][component]) - float(base[k][component]) for k in base}
        all_diffs.append(differences)
        signed = math.fsum(differences.values())
        l1 = math.fsum(abs(d) for d in differences.values())
        poles = math.fsum(abs(d) for k, d in differences.items() if k[3] in (0, 9))
        print(f"  {component} signed={signed:+.12f} L1={l1:.12f} pole_L1_pct={poles/l1*100:.4f}" if l1 else
              f"  {component} signed={signed:+.12f} L1=0 pole_L1_pct=UNDEFINED")
    for k in base:
        near(math.fsum(diff[k] for diff in all_diffs[:3]), all_diffs[3][k],
             f"{label} pointwise component difference", 2e-13)
    count = sum(int(r["qp_count"]) for r in base.values())
    pole_count = sum(int(r["qp_count"]) for k, r in base.items() if k[3] in (0, 9))
    volume = sum_field(list(base.values()), "qp_volume_m3")
    pole_volume = sum_field([r for k, r in base.items() if k[3] in (0, 9)], "qp_volume_m3")
    print(f"  BASE_POLAR_QP count={count} pole_count_pct={pole_count/count*100:.4f} "
          f"pole_volume_pct={pole_volume/volume*100:.4f}")


def analyze_temporal() -> None:
    summary = read("summary")
    cells = read("cells")
    if len(summary) != 4 or len(cells) != 200:
        raise ValueError("P10BE summary/cell row count mismatch")
    by_dt = {int(r["dt_s"]): r for r in summary}
    if set(by_dt) != {150, 75, 50, 25} or len(by_dt) != 4:
        raise ValueError("P10BE schedule mismatch")
    if len({key(r) for r in cells}) != 200:
        raise ValueError("P10BE cell keys not unique")
    for dt in by_dt:
        col = f"dR_jpeak_dt{dt}_per_m"
        near(sum_field(cells, col), float(by_dt[dt]["nearwall_mechanical_dR"]),
             f"P10BE local mechanical closure dt={dt}")
        row = by_dt[dt]
        near(float(row["global_mechanical_dR"]) + float(row["global_thermal_dR"]),
             float(row["global_total_dR"]), f"P10BE global closure dt={dt}")
    print("TEMPORAL_COMPENSATION H2 jpeak R horizon=900 mechanical_local_window=0.020-0.100mm")
    for dta, dtb in ((150, 75), (75, 50), (50, 25), (150, 25)):
        a, b = by_dt[dta], by_dt[dtb]
        diff = lambda field: float(a[field]) - float(b[field])
        local = diff("nearwall_mechanical_dR")
        global_mech = diff("global_mechanical_dR")
        rest = global_mech - local
        thermal = diff("global_thermal_dR")
        total = diff("global_total_dR")
        near(local + rest + thermal, total, f"dt {dta}-{dtb} global closure")
        print(f"  dt{dta}-dt{dtb} local_mech={local:+.12f} "
              f"rest_mech={rest:+.12f} thermal_global={thermal:+.12f} "
              f"full_dR={total:+.12f}")
    deltas = [float(r["difference_150_minus_25_per_m"]) for r in cells]
    s, l1 = math.fsum(deltas), math.fsum(abs(v) for v in deltas)
    near(s, float(by_dt[150]["nearwall_mechanical_dR"]) -
         float(by_dt[25]["nearwall_mechanical_dR"]), "dt150-dt25 local signed")
    print(f"  CELL_L1_150-25={l1:.12f} signed={s:+.12f} compensation={l1/abs(s):.6f}")


def main() -> None:
    spatial = {label: get_step_six(label) for label in ("W4B2", "W5B2", "W4B20")}
    compare_spatial(spatial["W4B2"], spatial["W5B2"], "W4B2_to_W5B2")
    compare_spatial(spatial["W4B2"], spatial["W4B20"], "W4B2_to_W4B20")
    analyze_temporal()
    print("P10BS_READ_ONLY_COMPONENT_SCOPE_OK spatial_pairs=2 cells_per_pair=200 "
          "time_schedules=4 new_FEM=0")


if __name__ == "__main__":
    main()
