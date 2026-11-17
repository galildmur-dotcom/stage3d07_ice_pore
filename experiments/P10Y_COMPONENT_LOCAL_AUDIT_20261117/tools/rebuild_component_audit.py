#!/usr/bin/env python3
"""P10Y jpeak component and radial cancellation audit, stdlib only.

Read the upstream 90-row P10Y four-mesh shell-difference CSV and regenerate
three derived CSVs. No FEM; no third-party dependencies.
"""
import csv
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "experiments/P10Y_FOUR_MESH_RADIAL_20261117/derived/P10Y_FOUR_MESH_90_SHELL_DIFFS.csv"
OUT = Path(__file__).resolve().parents[1] / "derived"
SOURCE_GIT_BLOB = "49308dd144249840eb75c825133ef67ebe4a8a6e"
COMPS = ("explicit", "equilibrium", "history", "mechanical")
PAIRS = ("H4_to_W2B2", "W2B2_to_W4B2", "W4B2_to_W4B20")
REGIONS = {
    "near_0_to_0p10": (0, 1, 2),
    "near_0_to_0p25": (0, 1, 2, 3),
    "intermediate_0p25_to_2": (4, 5, 6),
    "outer_2_to_5": (7,),
    "all_0_to_5": tuple(range(8)),
}

def number(x):
    return float(x)

def fmt(x):
    return "%.15e" % x

def delta(row, component):
    return number(row["delta_" + component + "_per_m"])

def write(name, records):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fd:
        w = csv.DictWriter(fd, fieldnames=list(records[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        w.writerows(records)
    return path

def main():
    raw = SRC.read_bytes()
    git_sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert git_sha == SOURCE_GIT_BLOB, "Source data changed; rerun scientific audit"
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    assert len(rows) == 90
    data = {
        p: sorted((r for r in rows if r["pair"] == p and r["functional"] == "jpeak"),
                  key=lambda r: int(r["shell_index"]))
        for p in PAIRS
    }
    assert all(len(v) == 10 and all(int(x["shell_index"]) == i for i, x in enumerate(v))
               for v in data.values())
    norms, shells, regions = [], [], []
    for ip, pair in enumerate(PAIRS):
        rr = data[pair]
        for c in COMPS:
            vv = [delta(x, c) for x in rr]
            ab = list(map(abs, vv))
            maxi = max(range(10), key=lambda i: ab[i])
            first_decrease = ""
            sign_flips = ""
            bulk_exceed = ""
            if ip == 1:
                prior = [delta(x, c) for x in data[PAIRS[0]]]
                first_decrease = sum(abs(x) < abs(prior[i]) for i, x in enumerate(vv[:8]))
                sign_flips = sum(x * prior[i] < 0 for i, x in enumerate(vv[:8]))
            if ip == 2:
                prior = [delta(x, c) for x in data[PAIRS[1]]]
                bulk_exceed = sum(abs(x) > abs(prior[i]) for i, x in enumerate(vv[:8]))
            norms.append(dict(pair=pair, component=c,
                global_delta_per_m=fmt(math.fsum(vv)),
                L1_per_m=fmt(math.fsum(ab)), Linf_per_m=fmt(ab[maxi]),
                max_bin_index=maxi, max_shell_lower_mm=rr[maxi]["lower_mm"],
                max_shell_upper_mm=rr[maxi]["upper_mm"],
                decrease_count_vs_first_wall=first_decrease,
                sign_flip_count_vs_first_wall=sign_flips,
                bulk_exceeds_last_wall_count=bulk_exceed,
                intermesh_cancellation_ratio=(fmt(math.fsum(ab)/abs(math.fsum(vv)))
                                               if c == "mechanical" else "")))
        for rr0 in rr[:8]:
            i = int(rr0["shell_index"])
            compvals = [delta(rr0, c) for c in COMPS[:3]]
            mechanical = delta(rr0, "mechanical")
            assert abs(math.fsum(compvals) - mechanical) < 5e-12
            dom = max(range(3), key=lambda j: abs(compvals[j]))
            exceed = ""
            if ip == 2:
                p = data[PAIRS[1]][i]
                exceed = ";".join(c for c in COMPS
                    if abs(delta(rr0, c)) > abs(delta(p, c)))
            improved = ""
            if ip == 1:
                p = data[PAIRS[0]][i]
                improved = sum(abs(delta(rr0, c)) < abs(delta(p, c)) for c in COMPS)
            shells.append(dict(pair=pair, shell_index=i,
                distance_lower_mm=rr0["lower_mm"],
                distance_upper_mm=rr0["upper_mm"],
                delta_explicit_per_m=fmt(compvals[0]),
                delta_equilibrium_per_m=fmt(compvals[1]),
                delta_history_per_m=fmt(compvals[2]),
                delta_mechanical_per_m=fmt(mechanical),
                sum_abs_three_components_per_m=fmt(math.fsum(map(abs,compvals))),
                component_cancellation_ratio=fmt(math.fsum(map(abs,compvals))/
                                                 abs(mechanical)),
                dominant_abs_component=COMPS[dom],
                bulk_components_exceed_last_wall=exceed,
                wall_improved_components_count=improved))
        for region, inds in REGIONS.items():
            selected = [x for x in rr if int(x["shell_index"]) in inds]
            signed = {c:math.fsum(delta(x,c) for x in selected) for c in COMPS}
            ab = {c:math.fsum(abs(delta(x,c)) for x in selected) for c in COMPS}
            assert abs(math.fsum(signed[c] for c in COMPS[:3])-
                       signed["mechanical"]) < 5e-12
            regions.append(dict(pair=pair,region=region,bins=";".join(map(str,inds)),
                delta_explicit_per_m=fmt(signed["explicit"]),
                delta_equilibrium_per_m=fmt(signed["equilibrium"]),
                delta_history_per_m=fmt(signed["history"]),
                delta_mechanical_per_m=fmt(signed["mechanical"]),
                L1_explicit_per_m=fmt(ab["explicit"]),
                L1_equilibrium_per_m=fmt(ab["equilibrium"]),
                L1_history_per_m=fmt(ab["history"]),
                L1_mechanical_per_m=fmt(ab["mechanical"]),
                net_component_cancellation_ratio=fmt(
                    math.fsum(abs(signed[c]) for c in COMPS[:3])/
                    abs(signed["mechanical"])),
                cross_shell_component_cancellation_ratio=fmt(
                    math.fsum(ab[c] for c in COMPS[:3])/
                    abs(signed["mechanical"]))))
    assert len(norms)==12 and len(shells)==24 and len(regions)==15
    assert abs(float(next(x["component_cancellation_ratio"] for x in shells
                if x["pair"] == PAIRS[1] and x["shell_index"] == 2))-45.2350635013) < 1e-5
    p = write("P10Y_JPEAK_12_COMPONENT_NORMS.csv", norms)
    q = write("P10Y_JPEAK_24_LOCAL_CANCELLATION.csv", shells)
    r = write("P10Y_JPEAK_15_RADIAL_REGION_COMPONENTS.csv", regions)
    print("P10Y_COMPONENT_AUDIT_OK norms=12 shells=24 regions=15")
    for file in (p,q,r):
        print(file)

if __name__ == "__main__":
    main()
