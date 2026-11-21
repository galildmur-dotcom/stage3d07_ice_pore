#!/usr/bin/env python3
"""Compare hotspot locations from two distinct W4B2 mesh perturbations.

No claim that a two-mesh local difference estimates the exact shape-error.
In particular, B20 and W5 change distinct mesh features.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def read(p):
    with p.open(encoding="utf-8-sig", newline="") as handle:
        rs = list(csv.DictReader(handle))
    assert len(rs) == 400
    out = {}
    for row in rs:
        k = (int(row["time_step"]), round(float(row["shell_lower_mm"]), 6),
             int(row["radial_subbin"]), int(row["polar_band"]))
        assert k not in out
        out[k] = row
    return out


def corr(xs, ys):
    xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
    dx, dy = [x-xm for x in xs], [y-ym for y in ys]
    return sum(x*y for x,y in zip(dx,dy)) / math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: (xs[i], i))
    a = [0]*len(xs)
    for rank, i in enumerate(order):
        a[i] = rank
    return a


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="H4W4B2 polar/radial CSV")
    parser.add_argument("--bulk", type=Path, required=True, help="H4W4B20 polar/radial CSV")
    parser.add_argument("--wall", type=Path, required=True, help="H4W5B2 polar/radial CSV")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    grids = [read(p) for p in (args.baseline, args.bulk, args.wall)]
    ks = sorted(k for k in grids[0] if k[0] == 6)
    assert len(ks) == 200
    assert all(set(ks).issubset(set(g)) for g in grids)
    delta1 = [float(grids[1][k]["total_mechanical_per_m"])-float(grids[0][k]["total_mechanical_per_m"]) for k in ks]
    delta2 = [float(grids[2][k]["total_mechanical_per_m"])-float(grids[0][k]["total_mechanical_per_m"]) for k in ks]
    a, b = [abs(x) for x in delta1], [abs(y) for y in delta2]
    sa, sb = sum(a), sum(b)
    top20a = set(sorted(range(200),key=lambda i:a[i],reverse=True)[:20])
    top20b = set(sorted(range(200),key=lambda i:b[i],reverse=True)[:20])
    top40a = set(sorted(range(200),key=lambda i:a[i],reverse=True)[:40])
    top40b = set(sorted(range(200),key=lambda i:b[i],reverse=True)[:40])
    pole = [k[3] in (0,9) for k in ks]
    mid = [k[3] not in (0,1,8,9) for k in ks]

    args.out_dir.mkdir(exist_ok=True,parents=True)
    with (args.out_dir/"P10BB_HOTSPOT_CONSISTENCY.csv").open("w",encoding="utf-8",newline="") as f:
        fields=("step", "shell_lower_mm", "radial_subbin", "polar_band", "s_lower_mm",
                "s_upper_mm", "mu_lower", "mu_upper", "delta_B20_per_m", "delta_W5_per_m",
                "abs_B20_per_m", "abs_W5_per_m", "share_B20", "share_W5", "both_top10pct")
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,k in enumerate(ks):
            row=grids[0][k]
            w.writerow(dict(step=k[0],shell_lower_mm=k[1],radial_subbin=k[2],polar_band=k[3],
                            s_lower_mm=row["radial_lower_mm"],s_upper_mm=row["radial_upper_mm"],
                            mu_lower=row["mu_lower"],mu_upper=row["mu_upper"],
                            delta_B20_per_m=delta1[i],delta_W5_per_m=delta2[i],
                            abs_B20_per_m=a[i],abs_W5_per_m=b[i],
                            share_B20=a[i]/sa,share_W5=b[i]/sb,
                            both_top10pct=int(i in top20a and i in top20b)))

    metrics={
        "pearson_signed":corr(delta1,delta2),
        "pearson_abs":corr(a,b),
        "spearman_abs":corr(ranks(a),ranks(b)),
        "top10pct_overlap_count":len(top20a&top20b),
        "top10pct_jaccard":len(top20a&top20b)/len(top20a|top20b),
        "top20pct_overlap_count":len(top40a&top40b),
        "top20pct_jaccard":len(top40a&top40b)/len(top40a|top40b),
        "pole_share_B20":sum(a[i] for i,v in enumerate(pole) if v)/sa,
        "pole_share_W5":sum(b[i] for i,v in enumerate(pole) if v)/sb,
        "middle6bands_share_B20":sum(a[i] for i,v in enumerate(mid) if v)/sa,
        "middle6bands_share_W5":sum(b[i] for i,v in enumerate(mid) if v)/sb,
    }
    with (args.out_dir/"P10BB_HOTSPOT_CONSISTENCY.txt").open("w",encoding="utf-8") as f:
        for key, value in metrics.items():
            print(f"{key}={value:.9g}",file=f)
    for key,value in metrics.items():
        print(f"{key}={value:.9g}")


if __name__=="__main__":
    main()
