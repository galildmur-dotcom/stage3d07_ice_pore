#!/usr/bin/env python3
"""P10Y: recreate 90 radial differences and 9 metrics on four grids (stdlib)."""
import csv
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / "derived"
SOURCES = {
    "H4": (
        "experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4_SHELL_SUMMARY.csv",
        "experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4_PARTITION_AUDIT.csv",
        "H4",
        ("95fb2456b98367c24b8fc47581ac4eab8a094368", "0672fdcb7f26a01052357b8d1a37520efb285237")),
    "W2B2": (
        "experiments/P10Y_H4W2_R_20261112/data/P10Y_SHELL_SUMMARY.csv",
        "experiments/P10Y_H4W2_R_20261112/data/P10Y_PARTITION_AUDIT.csv",
        "H4W2",
        ("9aca73e1ee02bcaedad43cbd60c89edefa5959ba", "47036e345c5fcf167b76daada339cd0a6bea573c")),
    "W4B2": (
        "experiments/P10Y_W4_PAIR_ANALYSIS_20261117/input/W4B2_P10Y_SHELL_SUMMARY.csv",
        "experiments/P10Y_W4_PAIR_ANALYSIS_20261117/input/W4B2_P10Y_PARTITION_AUDIT.csv",
        "H4W4B2",
        ("cde6927eecc7eab690c54ea673c1e1aba0c057d1", "208c78659e61d63cb1bec51f665ff2e6d6cd5f5d")),
    "W4B20": (
        "experiments/P10Y_W4_PAIR_ANALYSIS_20261117/input/W4B20_P10Y_SHELL_SUMMARY.csv",
        "experiments/P10Y_W4_PAIR_ANALYSIS_20261117/input/W4B20_P10Y_PARTITION_AUDIT.csv",
        "H4W4B20_P10AB",
        ("748324b15d8def2ae8dc772d956daad2c0ac88e9", "216a8f4ddb20d8b841b1b84a0e3cfeca95bbfacd")),
}
COMPONENTS = ("explicit", "equilibrium", "history", "mechanical")
SHELL_COLS = ("sum_explicit_objective_per_m", "sum_equilibrium_residual_per_m",
              "sum_internal_history_per_m", "sum_mechanical_per_m")
AUDIT_COLS = ("global_explicit_objective_per_m", "global_equilibrium_residual_per_m",
              "global_internal_history_per_m", "global_mechanical_per_m")
PAIRS = (("H4", "W2B2", "surface_first"), ("W2B2", "W4B2", "surface_second"),
         ("W4B2", "W4B20", "bulk_at_W4"))
FUNCTIONALS = ("j6", "jpeak", "jen")

def read(path, blob_sha):
    b = (ROOT / path).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
    assert actual == blob_sha, ("source mismatch", path, actual)
    return list(csv.DictReader(b.decode("utf-8-sig").splitlines()))

def fmt(x):
    return format(x, ".16e")

def write(name, records):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    return path

meshes = {}
for key, (shell_path, audit_path, name, hashes) in SOURCES.items():
    shell, audit = read(shell_path, hashes[0]), read(audit_path, hashes[1])
    assert len(shell) == 30 and len(audit) == 3
    assert all(r["mesh"] == name and r["mode"] == "R" and float(r["delta_um"]) == 0
               for r in shell + audit)
    for f in FUNCTIONALS:
        sr = [r for r in shell if r["functional"] == f]
        ar = [r for r in audit if r["functional"] == f]
        assert len(sr) == 10 and len(ar) == 1
        for cs, ca in zip(SHELL_COLS, AUDIT_COLS):
            assert abs(math.fsum(float(r[cs]) for r in sr) - float(ar[0][ca])) < 3e-12
        assert float(ar[0]["max_partition_relative_error"]) < 1e-10
    meshes[key] = (shell, audit)

detail, summary = [], []
for a, b, kind in PAIRS:
    pair = a + "_to_" + b
    for f in FUNCTIONALS:
        first = [r for r in meshes[a][0] if r["functional"] == f]
        second = [r for r in meshes[b][0] if r["functional"] == f]
        d, cumulative = [], 0.0
        for i, (x, y) in enumerate(zip(first, second)):
            assert x["distance_lower_mm"] == y["distance_lower_mm"]
            assert x["distance_upper_mm"] == y["distance_upper_mm"]
            row = {
                "pair": pair, "kind": kind, "from_mesh": a, "to_mesh": b,
                "functional": f, "shell_index": i,
                "lower_mm": x["distance_lower_mm"], "upper_mm": x["distance_upper_mm"],
            }
            for component, column in zip(COMPONENTS, SHELL_COLS):
                before, after = float(x[column]), float(y[column])
                row[component + "_from_per_m"] = fmt(before)
                row[component + "_to_per_m"] = fmt(after)
                row["delta_" + component + "_per_m"] = fmt(after - before)
            delta = float(y[SHELL_COLS[3]]) - float(x[SHELL_COLS[3]])
            d.append(delta)
            cumulative += delta
            row["cumulative_delta_mechanical_per_m"] = fmt(cumulative)
            detail.append(row)
        ref_a = next(r for r in meshes[a][1] if r["functional"] == f)
        ref_b = next(r for r in meshes[b][1] if r["functional"] == f)
        gd = float(ref_b[AUDIT_COLS[3]]) - float(ref_a[AUDIT_COLS[3]])
        assert abs(math.fsum(d) - gd) < 3e-12
        dc = [float(ref_b[k]) - float(ref_a[k]) for k in AUDIT_COLS]
        assert abs(sum(dc[:3]) - gd) < 3e-12
        abs_d = [abs(v) for v in d]
        L1 = math.fsum(abs_d)
        idx = max(range(10), key=lambda i: abs_d[i])
        summary.append({
            "pair": pair, "kind": kind, "functional": f,
            "global_mechanical_a_per_m": fmt(float(ref_a[AUDIT_COLS[3]])),
            "global_mechanical_b_per_m": fmt(float(ref_b[AUDIT_COLS[3]])),
            "global_delta_mechanical_per_m": fmt(gd),
            "global_delta_explicit_per_m": fmt(dc[0]),
            "global_delta_equilibrium_per_m": fmt(dc[1]),
            "global_delta_history_per_m": fmt(dc[2]),
            "L1_delta_mechanical_per_m": fmt(L1),
            "Linf_delta_mechanical_per_m": fmt(abs_d[idx]),
            "max_shell_lower_mm": first[idx]["distance_lower_mm"],
            "max_shell_upper_mm": first[idx]["distance_upper_mm"],
            "intermesh_cancellation_ratio": fmt(L1 / abs(gd)),
            "signed_first_0p25_mm_per_m": fmt(math.fsum(d[:4])),
            "abs_fraction_first_0p25_mm": fmt(math.fsum(abs_d[:4]) / L1),
        })
assert len(detail) == 90 and len(summary) == 9
f1 = write("P10Y_FOUR_MESH_90_SHELL_DIFFS.csv", detail)
f2 = write("P10Y_FOUR_MESH_9_METRICS.csv", summary)
print("P10Y_FOUR_MESH_RADIAL_OK shell_rows=90 metric_rows=9")
print(f1)
print(f2)
