#!/usr/bin/env python3
"""P10BR: independent, read-only P10BB/P10BE angular-localization audit.

Compare only dimensionless spatial/temporal *patterns* of absolute local
mechanical contribution differences on the same physical bins; never interpret
their magnitude ratio as a discretization error estimate or convergence rate.
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPATIAL = ROOT / "experiments/P10BB_W5B2_SPHERICAL_20261118"
TEMPORAL = ROOT / "research/evidence/P10BE_H2_20261118/input"
POLES = {0, 9}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No CSV rows: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"SOURCE={path.relative_to(ROOT)} ROWS={len(rows)} SHA256={digest}")
    return rows


def bin_key(row: dict[str, str]) -> tuple[float, float, float, int]:
    # Bin edges are exact nominal decimal physical mm values, but encoded in
    # CSV as floating values (0.050000000000000003, for example).
    return (
        round(float(row["shell_lower_mm"]), 8),
        round(float(row["radial_lower_mm"]), 8),
        round(float(row["radial_upper_mm"]), 8),
        int(row["polar_band"]),
    )


def spatial_map(path: Path, step: int) -> dict[tuple[float, float, float, int], dict[str, str]]:
    rows = read_csv(path)
    if len(rows) != 400:
        raise ValueError(f"P10BB expected 400 rows: {path}")
    selected = [row for row in rows if int(row["time_step"]) == step]
    if len(selected) != 200:
        raise ValueError(f"P10BB expected 200 cells in step={step}: {path}")
    result = {bin_key(row): row for row in selected}
    if len(result) != 200:
        raise ValueError(f"P10BB duplicated physical bins: {path}")
    if {float(row["time_s"]) for row in selected} != {step * 150.0}:
        raise ValueError(f"Unexpected P10BB time label: {path}")
    return result


def temporal_map(path: Path) -> dict[tuple[float, float, float, int], dict[str, str]]:
    rows = read_csv(path)
    if len(rows) != 200:
        raise ValueError("P10BE must contain exactly 200 spatial cells")
    result = {bin_key(row): row for row in rows}
    if len(result) != 200:
        raise ValueError("P10BE has duplicated physical bins")
    return result


def require_matching_keys(
    left: dict[tuple[float, float, float, int], dict[str, str]],
    right: dict[tuple[float, float, float, int], dict[str, str]],
) -> None:
    if left.keys() != right.keys():
        raise ValueError("Spatial bins not equal across the given datasets")
    radial_bins = {(key[0], key[1], key[2]) for key in left}
    if (len(radial_bins) != 20
            or min(key[1] for key in left) != 0.02
            or max(key[2] for key in left) != 0.1):
        raise ValueError("Expected 20 matching radial bins in physical [0.02,0.10] mm window")
    if {key[3] for key in left} != set(range(10)):
        raise ValueError("Expected ten matching polar bands")
    for key in left:
        l, r = left[key], right[key]
        if abs(float(l["mu_lower"]) - float(r["mu_lower"])) > 1e-10:
            raise ValueError(f"Polar lower edge mismatch: {key}")
        if abs(float(l["mu_upper"]) - float(r["mu_upper"])) > 1e-10:
            raise ValueError(f"Polar upper edge mismatch: {key}")


def metrics(
    name: str,
    items: list[tuple[int, float, int]],
) -> dict[str, object]:
    if len(items) != 200:
        raise ValueError(f"Expected 200 matched cells in {name}")
    by_band = defaultdict(float)
    signed_by_band = defaultdict(float)
    counts = defaultdict(int)
    for band, delta, qp_count in items:
        if band not in range(10) or qp_count < 0 or not math.isfinite(delta):
            raise ValueError(f"Invalid data in {name}")
        by_band[band] += abs(delta)
        signed_by_band[band] += delta
        counts[band] += qp_count
    signed_sum = math.fsum(item[1] for item in items)
    l1 = math.fsum(abs(item[1]) for item in items)
    if l1 <= 0:
        raise ValueError(f"Zero absolute change in {name}")
    weights = [by_band[band] / l1 for band in range(10)]
    qp_sum = sum(counts.values())
    pole_share = weights[0] + weights[9]
    pole_qp_share = (counts[0] + counts[9]) / qp_sum
    return {
        "name": name,
        "S": signed_sum,
        "A": l1,
        "kappa": l1 / abs(signed_sum) if signed_sum else math.inf,
        "pole_share": pole_share,
        "pole_qp_share": pole_qp_share,
        "enrichment": pole_share / pole_qp_share,
        "weights": weights,
        "signed_weights": [signed_by_band[band] / l1 for band in range(10)],
        "qp": qp_sum,
    }


def check_close(actual: float, expected: float, name: str, tolerance: float = 2e-11) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise ValueError(f"{name}: {actual:.17g} != expected {expected:.17g}")


def main() -> None:
    p10be_cells = temporal_map(TEMPORAL / "P10BE_CELL_TEMPORAL_COMPARE.csv")
    p10be_summary = read_csv(TEMPORAL / "P10BE_TEMPORAL_SUMMARY.csv")
    temporal = metrics(
        "H2_dt150_minus_dt25_accumulated",
        [
            (key[-1], float(row["difference_150_minus_25_per_m"]), int(row["qp_count"]))
            for key, row in p10be_cells.items()
        ],
    )
    dt_150 = next(row for row in p10be_summary if int(row["dt_s"]) == 150)
    dt_25 = next(row for row in p10be_summary if int(row["dt_s"]) == 25)
    check_close(
        temporal["S"],
        float(dt_150["nearwall_mechanical_dR"]) - float(dt_25["nearwall_mechanical_dR"]),
        "P10BE global near-wall versus cell sum",
    )

    base = spatial_map(SPATIAL / "input/H4W4B2_P10BA_QP_POLAR_RADIAL.csv", 6)
    alt_w5 = spatial_map(SPATIAL / "input/H4W5B2_P10BA_QP_POLAR_RADIAL.csv", 6)
    alt_b20 = spatial_map(SPATIAL / "input/H4W4B20_P10BA_QP_POLAR_RADIAL.csv", 6)
    published = read_csv(SPATIAL / "P10BB_SPATIAL_COMPARE.csv")

    spatial = []
    for name, candidate in (
        ("H4_W4B2_to_W5B2_t900", alt_w5),
        ("H4_W4B2_to_W4B20_t900", alt_b20),
    ):
        require_matching_keys(base, candidate)
        require_matching_keys(base, p10be_cells)
        case = metrics(
            name,
            [
                (
                    key[-1],
                    float(candidate[key]["total_mechanical_per_m"])
                    - float(row["total_mechanical_per_m"]),
                    int(row["qp_count"]),
                )
                for key, row in base.items()
            ],
        )
        if name.endswith("W5B2_t900"):
            published_w5 = next(
                row for row in published
                if row["time_step"] == "6" and row["shell_lower_mm"] == "TWO_SHELLS"
            )
            check_close(case["S"], float(published_w5["candidate_minus_baseline_per_m"]), "P10BB signed sum")
            check_close(case["A"], float(published_w5["cell_L1_delta_per_m"]), "P10BB absolute sum")
        spatial.append(case)

    print("CASE S_m-1 A_m-1 kappa pole_A_pct pole_QP_pct pole_enrichment QP")
    for case in (*spatial, temporal):
        print(
            f"{case['name']} {case['S']:.12g} {case['A']:.12g} {case['kappa']:.7f} "
            f"{100*case['pole_share']:.6f} {100*case['pole_qp_share']:.6f} "
            f"{case['enrichment']:.6f} {case['qp']}"
        )

    temporal_weights = temporal["weights"]
    temporal_signed_weights = temporal["signed_weights"]
    for case in spatial:
        spatial_weights = case["weights"]
        spatial_signed_weights = case["signed_weights"]
        overlap = math.fsum(min(a, b) for a, b in zip(spatial_weights, temporal_weights))
        cosine = math.fsum(a*b for a,b in zip(spatial_weights, temporal_weights)) / (
            math.sqrt(math.fsum(a*a for a in spatial_weights))
            * math.sqrt(math.fsum(b*b for b in temporal_weights))
        )
        signed_cosine = math.fsum(
            a*b for a,b in zip(spatial_signed_weights, temporal_signed_weights)
        ) / (
            math.sqrt(math.fsum(a*a for a in spatial_signed_weights))
            * math.sqrt(math.fsum(b*b for b in temporal_signed_weights))
        )
        print(f"ANGULAR_PROFILE_COMPARE={case['name']} vs H2_dt150_minus_dt25_accumulated "
              f"unsigned_overlap={overlap:.8f} unsigned_cosine={cosine:.8f} "
              f"signed_cosine={signed_cosine:.8f}")

    print("BAND mu_range spatial_W5_share_pct spatial_B20_share_pct temporal_share_pct")
    for band in range(10):
        lo, hi = -1+band*.2, -1+(band+1)*.2
        print(f"{band} [{lo:.1f},{hi:.1f}] "
              f"{100*spatial[0]['weights'][band]:.6f} "
              f"{100*spatial[1]['weights'][band]:.6f} "
              f"{100*temporal_weights[band]:.6f}")
    print("P10BR_CROSS_AXIS_READ_ONLY_OK cases=3 common_cells=200 polar_bands=10")


if __name__ == "__main__":
    main()
