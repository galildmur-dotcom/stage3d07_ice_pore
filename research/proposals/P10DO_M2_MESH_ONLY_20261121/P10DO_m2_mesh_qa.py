#!/usr/bin/env python3
"""M1/M2 read-only geometry and smooth-kappa QA; no physical FEM.

All 27 curved quadrature Jacobians use the earlier independent P10DE/P10CK
auditors. Unpaired spatial-bin volume ratios are DESCRIPTIVE, not per-element
or rigorous mesh-error estimates.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
import tempfile

import P10DE_compare_m1 as geom
import P10DN_m2_coefficient as coef

REV = "P10DO_R1_M2_GRADED_KAPPA20_MESH_ONLY"
M2_NAME = "P10DO_M2_CANDIDATE.msh"
RADIAL = ("0_100um", "100_500um", "500um_plus")
POLAR = ("polar_abs_mu_ge_0p8", "taper_abs_mu_0p6_0p8", "off_abs_mu_le_0p6")


def require(cond: bool, why: str) -> None:
    if not cond:
        raise RuntimeError("P10DO_QA_STOP: " + why)


def region(d: float, mu: float) -> tuple[str, str]:
    return (RADIAL[0] if d < .0001 else RADIAL[1] if d < .0005 else RADIAL[2],
            POLAR[0] if abs(mu) >= .8 else POLAR[1] if abs(mu) > .6 else POLAR[2])


def centroid_bins(mesh: Path, name: str) -> tuple[list[dict], dict]:
    """Stream the MSH2 source and label every Tet10 (centroid, all 10 nodes)."""
    nodes = {}
    accumulator = defaultdict(lambda: {"volume": [], "kappa": [],
                                       "target_volume_ratio": [], "kappa_min_nodes": [],
                                       "kappa_max_nodes": []})
    n_total = 0
    positive = 0
    full = 0
    with mesh.open("r", encoding="ascii", errors="strict") as f:
        require(next(f).strip() == "$MeshFormat", "expected MSH2 header")
        require(next(f).split()[:2] == ["2.2", "0"], "expected ASCII MSH2.2")
        # PhysicalNames may precede Nodes; find first node section.
        for line in f:
            if line.strip() == "$Nodes":
                break
        else:
            require(False, "no $Nodes section")
        n_nodes = int(next(f))
        for _ in range(n_nodes):
            v = next(f).split()
            require(len(v) == 4, "malformed MSH2 node")
            xyz = tuple(map(float, v[1:]))
            require(all(math.isfinite(t) for t in xyz), "nonfinite MSH2 node")
            nodes[int(v[0])] = xyz
        require(next(f).strip() == "$EndNodes", "bad $EndNodes")
        require(next(f).strip() == "$Elements", "expected elements after nodes")
        num = int(next(f))
        for _ in range(num):
            parts = list(map(int, next(f).split()))
            require(len(parts) >= 5, "malformed element")
            typ, ntag = parts[1:3]
            require(ntag >= 2 and len(parts) >= 3+ntag, "bad MSH2 tags")
            if typ != 11:
                continue
            require(parts[3] == 1, "wrong Tet10 volume physical tag")
            ids = parts[3+ntag:]
            require(len(ids) == 10, "non-Tet10 volume element")
            p = [nodes[i] for i in ids]
            c = tuple(math.fsum(p[i][j] for i in range(4))/4 for j in range(3))
            d, mu = coef.spherical(*c)
            k = coef.kappa_xyz(*c)
            kn = [coef.kappa_xyz(*xyz) for xyz in p]
            r, a = region(d, mu)
            geo = geom.corner_geometry(p)
            vol = geo["corner_vol_m3"]
            require(math.isfinite(vol) and vol > 0 and geo["signed_corner_det"] > 0,
                    "negative corner volume")
            group = accumulator[(r, a)]
            group["volume"].append(vol)
            group["kappa"].append(k)
            group["target_volume_ratio"].append(coef.volume_ratio(k))
            group["kappa_min_nodes"].append(min(kn))
            group["kappa_max_nodes"].append(max(kn))
            n_total += 1
            positive += k > 0
            full += k == 1
        require(next(f).strip() == "$EndElements", "bad $EndElements")
    rows = []
    for rad in RADIAL:
        for pol in POLAR:
            arr = accumulator[(rad, pol)]
            vols = arr["volume"]
            ks = arr["kappa"]
            rows.append({
                "mesh": name, "radial_zone": rad, "polar_zone": pol,
                "tet10": len(vols),
                "median_corner_volume_m3": statistics.median(vols) if vols else None,
                "mean_corner_volume_m3": statistics.fmean(vols) if vols else None,
                "kappa_centroid_min": min(ks) if ks else None,
                "kappa_centroid_mean": statistics.fmean(ks) if ks else None,
                "kappa_centroid_max": max(ks) if ks else None,
                "kappa_min_over_10_nodes": min(arr["kappa_min_nodes"]) if ks else None,
                "kappa_max_over_10_nodes": max(arr["kappa_max_nodes"]) if ks else None,
                "mean_target_volume_ratio": (statistics.fmean(arr["target_volume_ratio"])
                                             if ks else None),
            })
    return rows, {"tet10_labeled": n_total, "centroid_kappa_positive_tets": positive,
                  "centroid_kappa_full_tets": full, "nodes_read": n_nodes}


def audit(m1: Path, m2: Path) -> tuple[dict, list[dict], list[dict]]:
    require(m1.name == coef.M1_NAME and coef.sha256(m1) == coef.M1_SHA,
            "M1 exact original SHA/basename required; H0, other M1 forbidden")
    require(m2.name == M2_NAME and m2.resolve() != m1.resolve(),
            "M2 must be a distinct specifically named fresh MSH2 file")
    require(m2.is_file() and coef.sha256(m2) != coef.M1_SHA,
            "M2 missing or byte-identical to M1")
    m1geom = geom.check_one(m1, is_h0=False)
    m2geom = geom.check_one(m2, is_h0=False)
    g1 = m1geom["full_curved"]
    g2 = m2geom["full_curved"]
    require(m1geom["structural"]["mesh_nodes"] == 14145 and
            g1["tet10"] == 9736 and g1["pore_tri6"] == 178,
            "accepted M1 counts disagree with D-019")
    rows1, meta1 = centroid_bins(m1, "M1")
    rows2, meta2 = centroid_bins(m2, "M2")
    require(meta1["tet10_labeled"] == g1["tet10"] and
            meta2["tet10_labeled"] == g2["tet10"],
            "per-element coefficient labeling/count mismatch")
    local = []
    for a, b in zip(rows1, rows2):
        require(a["radial_zone"] == b["radial_zone"] and
                a["polar_zone"] == b["polar_zone"], "spatial zone mismatch")
        x, y = a["median_corner_volume_m3"], b["median_corner_volume_m3"]
        local.append({
            "radial_zone": a["radial_zone"], "polar_zone": a["polar_zone"],
            "m1_tet10": a["tet10"], "m2_tet10": b["tet10"],
            "m1_mean_kappa_centroid": a["kappa_centroid_mean"],
            "m2_mean_kappa_centroid": b["kappa_centroid_mean"],
            "model_mean_target_volume_ratio_at_m1_centroids": a["mean_target_volume_ratio"],
            "observed_unpaired_median_corner_volume_ratio_m2_over_m1":
                y/x if x is not None and y is not None and x > 0 else None,
            "comparison_is_unpaired_diagnostic": True,
        })
    issues = m1geom["issues"] + m2geom["issues"]
    if g2["tet10"] <= 0 or g2["pore_tri6"] <= 0:
        issues.append("missing M2 Tet10 or pore Tri6")
    summary = {
        "protocol": REV,
        "status": "P10DO_M2_GEOMETRY_QA_OK_NO_FEM" if not issues else "P10DO_M2_GEOMETRY_QA_STOP_NO_FEM",
        "m1_sha256": g1["mesh_sha256"], "m2_sha256": g2["mesh_sha256"],
        "m1_tet10": g1["tet10"], "m2_tet10": g2["tet10"],
        "m1_nodes": meta1["nodes_read"], "m2_nodes": meta2["nodes_read"],
        "m1_pore_tri6": g1["pore_tri6"], "m2_pore_tri6": g2["pore_tri6"],
        "m1_curved_qp_count": g1["curved_qp_count"],
        "m2_curved_qp_count": g2["curved_qp_count"],
        "m1_curved_qp_nonpositive": g1["curved_qp_negative"],
        "m2_curved_qp_nonpositive": g2["curved_qp_negative"],
        "m1_geometry_issues": m1geom["issues"],
        "m2_geometry_issues": m2geom["issues"],
        "geometry_issues": issues,
        "m1_label_coverage": meta1, "m2_label_coverage": meta2,
        "target_field_local_volume_ratio_bounds": [0.8, 1.0],
        "target_field_local_size_ratio_bounds": [coef.size_ratio(1.), 1.0],
        "spatial_areas": "3 radial x 3 absolute-mu; 9 zones, not QP-derived error",
        "local_volume_ratios": "UNPAIRED finite mesh corner-centroid diagnostic; exact 20% realized tetra volume NOT guaranteed",
        "physical_signed4D_derivative": "NOT_COMPUTED_M2",
        "m2_geometry_accepted_for_physical_FEM": False,
        "user_must_review_9_zone_ratios": True,
        "FEM_runs": 0,
    }
    return summary, rows1+rows2, local


def selftest() -> None:
    geom.selftest()
    coef.selftest()
    for d, m, expect in ((.00001,1.,(RADIAL[0],POLAR[0])),
                         (.0002,.7,(RADIAL[1],POLAR[1])),
                         (.003,0.,(RADIAL[2],POLAR[2]))):
        require(region(d,m)==expect,"zone classification")
    fake = Path("not_the_original_M1.msh")
    try:
        audit(fake, fake)
    except (RuntimeError, OSError):
        pass
    else:
        raise RuntimeError("negative wrong-M1 gate failed")
    # Exercise the actual NEW P10DO Tet10 centroid/ten-node MSH2 labeling,
    # not just the inherited 27QP geometry routines.
    p4=((.00003,0.,.0312),(.00007,0.,.0312),
        (.00003,.00004,.0312),(.00003,0.,.03124))
    edges=((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
    p10=p4+tuple(tuple((p4[i][j]+p4[k][j])/2 for j in range(3))
                  for i,k in edges)
    with tempfile.TemporaryDirectory(prefix="p10do_qa_") as td:
        f=Path(td)/"test.msh"
        mesh=["$MeshFormat","2.2 0 8","$EndMeshFormat","$Nodes","10"]
        mesh += [f"{i} {x:.17g} {y:.17g} {z:.17g}"
                 for i,(x,y,z) in enumerate(p10,1)]
        mesh += ["$EndNodes","$Elements","1",
                 "1 11 2 1 1 "+" ".join(map(str,range(1,11))),"$EndElements"]
        f.write_text("\n".join(mesh)+"\n",encoding="ascii")
        rows,meta=centroid_bins(f,"SYNTHETIC")
        require(meta["tet10_labeled"]==1 and meta["centroid_kappa_positive_tets"]==1 and
                meta["nodes_read"]==10 and sum(r["tet10"] for r in rows)==1,
                "positive true MSH2 kappa parser/coverage test failed")
        mesh[-2]="1 11 2 1 1 2 1 "+" ".join(map(str,range(3,11)))
        f.write_text("\n".join(mesh)+"\n",encoding="ascii")
        try:
            centroid_bins(f,"NEGATIVE_FOLDED")
        except RuntimeError as err:
            require("negative corner volume" in str(err),"wrong folded test STOP")
        else:
            raise RuntimeError("negative folded new MSH2 kappa parser accepted")
    print("P10DO_M2_MESH_QA_SYNTHETIC_OK full27QP=PASS folded_negative=DETECTED "
          "9_zones=PASS true_MSH2_kappa_parser=PASS wrong_M1=STOP mesh=NOT_BUILT FEM=0")


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--m1",type=Path)
    p.add_argument("--m2",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not (args.m1 and args.m2 and args.out):
        p.error("--m1 --m2 --out are required")
    report, rows, local = audit(args.m1,args.m2)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"P10DO_M1_M2_GEOMETRY_QA.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for path, records in (("P10DO_M1_M2_9_ZONES.csv",rows),
                          ("P10DO_M1_M2_9_ZONE_VOLUME_COMPARISON.csv",local)):
        with (args.out/path).open("w",encoding="utf-8",newline="") as out:
            writer=csv.DictWriter(out,fieldnames=list(records[0]),lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
    print(report["status"], "M1_Tet10",report["m1_tet10"],
          "M2_Tet10",report["m2_tet10"],
          "M2_curved27QP",report["m2_curved_qp_count"],
          "9_local_unpaired_ratios=EXPORTED", "FEM=0")
    return 0 if not report["geometry_issues"] else 2


if __name__=="__main__":
    raise SystemExit(main())
