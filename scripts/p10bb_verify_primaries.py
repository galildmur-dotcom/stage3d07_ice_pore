#!/usr/bin/env python3
"""Verify published P10BB tables against the three archived P10BA raw CSV files.

Pure standard-library and read-only: does not execute FEM or rewrite evidence.
The checked values describe *mechanical* terms over two thin shells only.
"""
from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/P10BB_W5B2_SPHERICAL_20261118"
INPUT = EVIDENCE / "input"
ORIGINALS = {
    "W4B2": ("H4W4B2", "219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447"),
    "W4B20": ("H4W4B20", "3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be"),
    "W5B2": ("H4W5B2", "8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def key(row: dict[str, str]) -> tuple[int, float, int, int]:
    return (int(row["time_step"]), float(row["shell_lower_mm"]),
            int(row["radial_subbin"]), int(row["polar_band"]))


def close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, abs_tol=2e-12, rel_tol=2e-10):
        raise AssertionError(f"{label}: computed={actual:.17g}, published={expected:.17g}")


def main() -> None:
    grids: dict[str, dict[tuple[int, float, int, int], dict[str, str]]] = {}
    for name, (mesh, expected_hash) in ORIGINALS.items():
        path = INPUT / f"{mesh}_P10BA_QP_POLAR_RADIAL.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected_hash, f"SHA256 mismatch for {path}"
        rows = read_csv(path)
        assert len(rows) == 400, f"{mesh}: {len(rows)} rows, expected 400"
        assert Counter(int(r["time_step"]) for r in rows) == {5: 200, 6: 200}
        data = {key(r): r for r in rows}
        assert len(data) == 400 and len({k[1:] for k in data}) == 200
        assert all(r["mesh"].startswith(mesh) for r in rows)
        for k, r in data.items():
            components = sum(float(r[x]) for x in
                             ("explicit_per_m", "equilibrium_per_m", "history_per_m"))
            total = float(r["total_mechanical_per_m"])
            close(components, total, f"{mesh} {k} components")
            close(float(r["positive_mechanical_per_m"]) +
                  float(r["negative_mechanical_per_m"]), total, f"{mesh} {k} sign")
            assert int(r["positive_qp"]) + int(r["negative_qp"]) == int(r["qp_count"])
        grids[name] = data

    assert set(grids["W4B2"]) == set(grids["W4B20"]) == set(grids["W5B2"])
    for k in grids["W4B2"]:
        b = grids["W4B2"][k]
        for candidate in ("W4B20", "W5B2"):
            r = grids[candidate][k]
            for col in ("radial_lower_mm", "radial_upper_mm", "mu_lower", "mu_upper"):
                close(float(b[col]), float(r[col]), f"cell geometry {candidate} {k} {col}")

    def values(candidate: str, step: int, zone: str,
               baseline: str = "W4B2") -> tuple[list[tuple], list[float], list[float]]:
        keys = sorted(k for k in grids["W4B2"] if k[0] == step and
                      (zone in ("BOTH", "TWO_SHELLS") or
                       math.isclose(k[1], float(zone.split("-")[0]) if "-" in zone else float(zone))))
        base = [float(grids[baseline][k]["total_mechanical_per_m"]) for k in keys]
        cand = [float(grids[candidate][k]["total_mechanical_per_m"]) for k in keys]
        return keys, base, cand

    def compare(candidate: str, step: int, zone: str,
                baseline: str = "W4B2") -> dict[str, float]:
        ks, base, cand = values(candidate, step, zone, baseline)
        assert len(ks) in (100, 200)
        diffs = [y-x for x, y in zip(base, cand)]
        signed = sum(cand)-sum(base)
        local_l1 = sum(abs(x) for x in diffs)
        return dict(baseline=sum(base), candidate=sum(cand), delta=signed,
                    net_relative=abs(signed)/abs(sum(base)), local_l1=local_l1,
                    local_l1_relative=local_l1/sum(abs(x) for x in base),
                    cancellation=local_l1/abs(signed),
                    pole_fraction=sum(abs(d) for k, d in zip(ks, diffs)
                                      if k[3] in (0, 9))/local_l1)

    compared = 0
    for row in read_csv(EVIDENCE / "P10BB_THREE_MESH_COMPARISON.csv"):
        c = compare(row["candidate_name"], int(row["step"]), row["zone_mm"], row["base"])
        for column, computed in c.items():
            close(computed, float(row[column]), f"three-mesh row={compared} {column}")
        compared += 1
    assert compared == 18

    compared_spatial = 0
    alias = dict(baseline_per_m="baseline", candidate_per_m="candidate",
                 candidate_minus_baseline_per_m="delta", relative_net_abs="net_relative",
                 cell_L1_delta_per_m="local_l1", cell_L1_relative_to_baseline="local_l1_relative",
                 cancellation_factor="cancellation")
    for row in read_csv(EVIDENCE / "P10BB_SPATIAL_COMPARE.csv"):
        zone = row["shell_lower_mm"]
        c = compare("W5B2", int(row["time_step"]), zone)
        for field, column in alias.items():
            close(c[column], float(row[field]), f"spatial row={compared_spatial} {field}")
        compared_spatial += 1
    assert compared_spatial == 6

    compared_bins = 0
    for row in read_csv(EVIDENCE / "P10BB_ANGULAR_RADIAL_L1.csv"):
        candidate = row["candidate"]
        step = int(row["step"])
        ks, base, cand = values(candidate, step, "BOTH")
        diffs = [abs(y-x) for x, y in zip(base, cand)]
        bin_id = int(row["bin"])
        if row["axis"] == "mu":
            selected = [(k,d) for k,d in zip(ks,diffs) if k[3] == bin_id]
            lower,upper = float(grids["W4B2"][selected[0][0]]["mu_lower"]),float(grids["W4B2"][selected[0][0]]["mu_upper"])
        else:
            selected = [(k,d) for k,d in zip(ks,diffs) if k[2] + (10 if k[1] > 0.03 else 0) == bin_id]
            lower,upper = float(grids["W4B2"][selected[0][0]]["radial_lower_mm"]),float(grids["W4B2"][selected[0][0]]["radial_upper_mm"])
        assert len(selected) in (10, 20), row
        close(lower, float(row["lower"]), f"bin {compared_bins} lower")
        close(upper, float(row["upper"]), f"bin {compared_bins} upper")
        close(sum(d for _,d in selected), float(row["L1_abs"]), f"bin {compared_bins} L1")
        close(sum(d for _,d in selected)/sum(diffs), float(row["L1_share"]), f"bin {compared_bins} share")
        compared_bins += 1
    assert compared_bins == 120

    for candidate in ("W4B20", "W5B2"):
        c = compare(candidate, 6, "BOTH")
        print(f"{candidate}: step6 sum={c['candidate']:.12f} /m, "
              f"local_L1_relative={100*c['local_l1_relative']:.6f}%, "
              f"polar_share={100*c['pole_fraction']:.6f}%")
    print(f"P10BB_PRIMARY_EVIDENCE_OK: 3 original SHA256, 1200 raw rows, "
          f"{compared}+{compared_spatial}+{compared_bins} published rows verified")


if __name__ == "__main__":
    main()
