#!/usr/bin/env python3
"""P10BT: independently audit existing H2 all-step mechanical shape contributions.

Read-only toward input files. No FEM, no Git, no temperature-field reconstruction.
Run with --input-dir, --summary, --cells and --output-dir. Only writes new derived
CSVs and a report into the chosen output directory.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import math
from pathlib import Path

DTS = (150, 75, 50, 25)
HORIZON = 900
COMPONENTS = ("explicit", "equilibrium", "history", "total_mechanical")
HASHES = {
    150: "4652c2def95ec28d36ca68315e18271a9de147560a90f13b012005358aafebd3",
    75: "81d6e884df060ce582075826380ad2e18f0a1c6c1d562e643023c01152cea64f",
    50: "aa8d9f8ca21a0502f51ba6b1f6f7dc5020b5ebad8e014cb6b1f5fa733abb9bd9",
    25: "7c6cbb9d7fd68aec1ac07d4530efa73073fee4e7cf6aed7811ec594969ae29a6",
}
PAIRS = ((150, 75), (75, 50), (50, 25), (150, 25))
TOL = 4e-11


def require_close(got: float, wanted: float, context: str, atol: float = TOL) -> None:
    if not math.isfinite(got) or abs(got - wanted) > atol:
        raise ValueError(f"{context}: {got:.17g} != {wanted:.17g} (atol={atol})")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as inp:
        rows = list(csv.DictReader(inp))
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"Malformed CSV: {path}")
    return rows


def cell_key(row: dict[str, str]) -> tuple[float, float, int, int]:
    return (
        round(float(row["shell_lower_mm"]), 9),
        round(float(row["shell_upper_mm"]), 9),
        int(row["radial_subbin"]),
        int(row["polar_band"]),
    )


def component(row: dict[str, str], name: str) -> float:
    return float(row[name + "_per_m"])


def write_csv(path: Path, records: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def build_input(input_dir: Path) -> tuple[dict, list[tuple], dict]:
    all_steps: dict[int, dict[int, dict]] = {}
    reference_cells = None
    reference_qps = None
    per_step_totals = []
    per_dt_cells = {}
    counts = {}

    for dt in DTS:
        path = input_dir / f"DT{dt}_P10BD_QP_POLAR_RADIAL.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != HASHES[dt]:
            raise ValueError(f"SHA mismatch for dt{dt}: {digest}")
        rows = read_csv(path)
        expected_steps = HORIZON // dt
        if len(rows) != 200 * expected_steps:
            raise ValueError(f"Wrong rows for dt{dt}: {len(rows)}")
        grouped: dict[int, dict] = collections.defaultdict(dict)

        for r in rows:
            if r["mesh"] != "H2":
                raise ValueError(f"Unexpected mesh in dt{dt}: {r['mesh']}")
            step = int(r["time_step"])
            if not 1 <= step <= expected_steps or int(float(r["time_s"])) != step * dt:
                raise ValueError(f"Incorrect physical time dt={dt} step={step}")
            key = cell_key(r)
            if key in grouped[step]:
                raise ValueError(f"Duplicate key dt{dt} step{step} cell{key}")
            if key[0] not in (0.02, 0.05) or key[2] not in range(10) or key[3] not in range(10):
                raise ValueError(f"Unexpected cell geometry: {key}")
            qps = int(r["qp_count"])
            if qps <= 0 or int(r["positive_qp"]) + int(r["negative_qp"]) != qps:
                raise ValueError(f"Bad QP partition dt{dt} cell{key}")
            vals = {c: component(r, c) for c in COMPONENTS}
            volume = float(r["qp_volume_m3"])
            if volume <= 0 or not all(map(math.isfinite, vals.values())):
                raise ValueError(f"Nonfinite or invalid quantities dt{dt} cell{key}")
            require_close(math.fsum(vals[c] for c in COMPONENTS[:3]),
                          vals["total_mechanical"], "Row component closure", 2e-13)
            require_close(float(r["positive_mechanical_per_m"]) +
                          float(r["negative_mechanical_per_m"]),
                          vals["total_mechanical"], "Row signs closure", 2e-13)
            grouped[step][key] = {"components": vals, "qp_count": qps, "volume": volume}

        if set(grouped) != set(range(1, expected_steps + 1)):
            raise ValueError(f"Missing steps dt{dt}")
        signatures = set(grouped[1])
        if len(signatures) != 200 or any(set(g) != signatures for g in grouped.values()):
            raise ValueError(f"Nonconstant cell keys over time, dt{dt}")
        if reference_cells is None:
            reference_cells = signatures
            reference_qps = {k: (grouped[1][k]["qp_count"], grouped[1][k]["volume"])
                             for k in signatures}
        if signatures != reference_cells:
            raise ValueError(f"Physical cell keys vary with dt={dt}")
        for step in sorted(grouped):
            for key, data in grouped[step].items():
                n_ref, v_ref = reference_qps[key]
                if data["qp_count"] != n_ref:
                    raise ValueError(f"QP count differs dt{dt} step{step} cell{key}")
                require_close(data["volume"], v_ref, f"QP volume dt{dt} step{step} cell{key}", 1e-19)
            if step == expected_steps:
                require_close(math.fsum(abs(g["components"]["history"])
                                        for g in grouped[step].values()), 0,
                              f"Terminal history dt{dt}", 1e-13)
            per_step_totals.append(
                {"dt_s": dt, "step": step, "time_s": step * dt, "window_150s": (step * dt - 1) // 150 + 1,
                 **{c: math.fsum(g["components"][c] for g in grouped[step].values())
                    for c in COMPONENTS},
                 "qp_count": sum(g["qp_count"] for g in grouped[step].values()),
                 "qp_volume_m3": math.fsum(g["volume"] for g in grouped[step].values())}
            )
        all_steps[dt] = grouped
        per_dt_cells[dt] = {
            k: {c: math.fsum(grouped[step][k]["components"][c] for step in sorted(grouped))
                for c in COMPONENTS}
            for k in sorted(signatures)
        }
        counts[dt] = len(rows)

    return ({"steps": all_steps, "cells": per_dt_cells, "steps_data": per_step_totals},
            sorted(reference_cells), {"rows": counts, "qp_reference": reference_qps})


def compare_published(primary: dict, keys: list, summary_path: Path, cells_path: Path) -> list[dict]:
    summary = read_csv(summary_path)
    if len(summary) != 4 or {int(row["dt_s"]) for row in summary} != set(DTS):
        raise ValueError("Published P10BE temporal summary missing dt rows")
    summary_by_dt = {int(row["dt_s"]): row for row in summary}
    totals = []
    for dt in DTS:
        row = summary_by_dt[dt]
        if int(row["steps"]) != 900 // dt or float(row["horizon_s"]) != 900:
            raise ValueError(f"Published summary horizon mismatch dt={dt}")
        vals = {c: math.fsum(primary["cells"][dt][k][c] for k in keys) for c in COMPONENTS}
        require_close(vals["total_mechanical"], float(row["nearwall_mechanical_dR"]),
                      f"nearwall vs published summary dt{dt}")
        require_close(float(row["global_mechanical_dR"]) + float(row["global_thermal_dR"]),
                      float(row["global_total_dR"]), "Published global closure")
        qps = primary["steps"][dt][1]
        totals.append({"dt_s": dt, "steps": 900 // dt, **vals,
                       "global_mechanical": float(row["global_mechanical_dR"]),
                       "global_thermal": float(row["global_thermal_dR"]),
                       "global_total": float(row["global_total_dR"]),
                       "local_fraction_of_global": vals["total_mechanical"] /
                                                     float(row["global_mechanical_dR"]),
                       "qp_count_per_step": sum(d["qp_count"] for d in qps.values()),
                       "qp_volume_m3_per_step": math.fsum(d["volume"] for d in qps.values())})

    published = read_csv(cells_path)
    if len(published) != 200 or {cell_key(r) for r in published} != set(keys):
        raise ValueError("Published comparison CSV does not have matching 200 cell keys")
    for r in published:
        key = cell_key(r)
        for dt in DTS:
            require_close(primary["cells"][dt][key]["total_mechanical"],
                          float(r[f"dR_jpeak_dt{dt}_per_m"]),
                          f"Published 200-cell comparison dt{dt}, cell{key}")
    return totals


def difference_metrics(differences: dict, keys: list) -> dict:
    vals = list(differences.values())
    signed = math.fsum(vals)
    l1 = math.fsum(abs(x) for x in vals)
    poles = math.fsum(abs(differences[k]) for k in keys if k[3] in (0, 9))
    south = math.fsum(differences[k] for k in keys if k[3] == 0)
    north = math.fsum(differences[k] for k in keys if k[3] == 9)
    return {"signed_difference": signed, "cell_L1_difference": l1,
            "polar_L1_percent": 100 * poles / l1 if l1 else 0,
            "south_signed": south, "north_signed": north,
            "cancellation_L1_over_abs_signed": l1 / abs(signed) if abs(signed) > 1e-14 else float("nan")}


def analyze_differences(primary: dict, keys: list) -> tuple[list, list, list, list]:
    pairs = []
    polar = []
    radial = []
    for a, b in PAIRS:
        for c in COMPONENTS:
            delta = {k: primary["cells"][a][k][c] - primary["cells"][b][k][c] for k in keys}
            pairs.append({"dt_a": a, "dt_b": b, "component": c, **difference_metrics(delta, keys)})
            for band in range(10):
                v = [delta[k] for k in keys if k[3] == band]
                polar.append({"dt_a": a, "dt_b": b, "component": c, "polar_band": band,
                              "mu_lower": -1 + band * 0.2, "mu_upper": -0.8 + band * 0.2,
                              "signed": math.fsum(v), "L1": math.fsum(abs(x) for x in v)})
            for shell in (0.02, 0.05):
                for sub in range(10):
                    v = [delta[k] for k in keys if k[0] == shell and k[2] == sub]
                    radial.append({"dt_a": a, "dt_b": b, "component": c,
                                   "shell_lower_mm": shell, "radial_subbin": sub,
                                   "signed": math.fsum(v), "L1": math.fsum(abs(x) for x in v)})

    # Properly aligned 150-second *physical* windows, not equal step indices.
    windows = []
    for a, b in PAIRS:
        for window in range(1, 7):
            def window_cells(dt: int, c: str) -> dict:
                return {
                    k: math.fsum(primary["steps"][dt][s][k]["components"][c]
                                 for s in range(1, 900 // dt + 1)
                                 if (s * dt - 1) // 150 + 1 == window)
                    for k in keys
                }
            for c in COMPONENTS:
                ca, cb = window_cells(a, c), window_cells(b, c)
                d = {k: ca[k] - cb[k] for k in keys}
                windows.append({"dt_a": a, "dt_b": b,
                                "window_150s": window, "start_s": (window - 1) * 150,
                                "end_s": window * 150, "component": c,
                                "value_a": math.fsum(ca.values()), "value_b": math.fsum(cb.values()),
                                **difference_metrics(d, keys)})
    return pairs, polar, radial, windows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--cells", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    if args.output_dir.resolve() == args.input_dir.resolve():
        raise ValueError("Output must be separate from original input")
    primary, keys, meta = build_input(args.input_dir)
    totals = compare_published(primary, keys, args.summary, args.cells)
    pairs, polar, radial, windows = analyze_differences(primary, keys)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "P10BT_COMPONENT_TOTALS.csv", totals, list(totals[0]))
    write_csv(args.output_dir / "P10BT_COMPONENT_PAIRS.csv", pairs, list(pairs[0]))
    write_csv(args.output_dir / "P10BT_POLAR_COMPONENTS.csv", polar, list(polar[0]))
    write_csv(args.output_dir / "P10BT_RADIAL_COMPONENTS.csv", radial, list(radial[0]))
    write_csv(args.output_dir / "P10BT_ALIGNED_WINDOWS.csv", windows, list(windows[0]))
    write_csv(args.output_dir / "P10BT_STEP_SERIES.csv", primary["steps_data"],
              list(primary["steps_data"][0]))

    pair = {(r["dt_a"], r["dt_b"], r["component"]): r for r in pairs}
    sel = (150, 25)
    comp_diff_sum = math.fsum(pair[(*sel, c)]["signed_difference"] for c in COMPONENTS[:3])
    require_close(comp_diff_sum, pair[(*sel, "total_mechanical")]["signed_difference"],
                  "Summed component pair difference")
    component_cell_l1 = math.fsum(pair[(*sel, c)]["cell_L1_difference"] for c in COMPONENTS[:3])
    net_cell_l1 = pair[(*sel, "total_mechanical")]["cell_L1_difference"]
    signed_sum_abs = math.fsum(abs(pair[(*sel, c)]["signed_difference"]) for c in COMPONENTS[:3])
    full_signed = abs(pair[(*sel, "total_mechanical")]["signed_difference"])
    report = [
        "P10BT ALL-STEP H2 TEMPORAL COMPONENT AUDIT (READ-ONLY INPUT, NO FEM)",
        "TOOL_REVISION=P10BT_R1_INDEPENDENT_PRIMARY_AND_PUBLISHED_COMPARISON",
        "SOURCE_ZIP_SHA256=66fc611b39f9a04c05a74d79301cf5a8162826ca1b6ed8717126f090dff34e5d",
        *(f"DT{dt}_SOURCE_SHA256={HASHES[dt]} ROWS={meta['rows'][dt]} STEPS={900//dt}"
          for dt in DTS),
        "PRIMARY_CELL_KEYS=200",
        "PHYSICAL_HORIZON_S=900",
        "QP_COUNT_AND_VOLUME_CONSTANT_OVER_TIME_AND_DT=YES",
        "ROW_EXPLICIT_PLUS_EQUILIBRIUM_PLUS_HISTORY_CLOSURE=OK",
        "ROW_POSITIVE_PLUS_NEGATIVE_CLOSURE=OK",
        "TERMINAL_STEP_HISTORY_ZERO=YES",
        "PUBLISHED_NEARWALL_SUMMARY_FOUR_DTS=OK",
        "PUBLISHED_200_CELL_COMPARISON_FOUR_DTS=OK",
        f"DT150_MINUS_25_COMPONENT_SIGNED_EXPLICIT={pair[(*sel,'explicit')]['signed_difference']:+.15g}",
        f"DT150_MINUS_25_COMPONENT_SIGNED_EQUILIBRIUM={pair[(*sel,'equilibrium')]['signed_difference']:+.15g}",
        f"DT150_MINUS_25_COMPONENT_SIGNED_HISTORY={pair[(*sel,'history')]['signed_difference']:+.15g}",
        f"DT150_MINUS_25_LOCAL_SIGNED_TOTAL={pair[(*sel,'total_mechanical')]['signed_difference']:+.15g}",
        f"DT150_MINUS_25_SUM_COMPONENT_L1={component_cell_l1:.15g}",
        f"DT150_MINUS_25_NET_CELL_L1={net_cell_l1:.15g}",
        f"DT150_MINUS_25_COMPONENT_TO_NET_CELL_L1_RATIO={component_cell_l1/net_cell_l1:.9f}",
        f"DT150_MINUS_25_SIGNED_COMPONENT_CANCELLATION_RATIO={signed_sum_abs/full_signed:.9f}",
        "P10BT_INDEPENDENT_READ_ONLY_COMPONENT_AUDIT_OK new_FEM=0",
    ]
    (args.output_dir / "P10BT_RESULT.txt").write_text("\n".join(report)+"\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
