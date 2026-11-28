#!/usr/bin/env python3
"""P10CL: independent read-only audit of P10CK Windows R1 evidence.

Input evidence and references are pinned by SHA-256. No mesh, FEM, or solver
is invoked. Per-cell Jacobian extrema are diagnostics, not a guarantee of
element-wise positivity or an estimate of continuum error.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from hashlib import sha256
from io import StringIO
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile


ROOT = Path.cwd()
# In a repository checkout use the archived primary ZIP; in the original
# scratch data drop, use the uploaded ZIP. Launch from the intended data root.
EVIDENCE = ROOT / "research/evidence/P10CK_R1_WINDOWS_REAL_QP_20261120/input/P10CK_EVIDENCE.zip"
if not EVIDENCE.is_file():
    EVIDENCE = ROOT / "upload/P10CK_EVIDENCE.zip"
EVIDENCE_SHA = "b3091dc01f7b99d07336627c0ab4a662b258b68f20dd968a6819bd2c18805921"
MEMBERS = {
    "P10CK_RESULT.txt": "1f3a10f8f49d573fa48f4f1039580e6b2bcd89c6ec1f5092466ceaa1fc766399",
    "P10CK_3MESH_SUMMARY.csv": "aa1be0895edeaacfaa262687f29db5b9695aefd16674deb32971dcef5f32b8b9",
    "P10CK_630CELL_QP_GEOMETRY.csv": "89d328fd442c37a7b786f2c5c52c3eaea0ce1251c60b16cfb3787df6312961f2",
}
REFDIR = ROOT / "experiments/P10BB_W5B2_SPHERICAL_20261118/input"
if not REFDIR.is_dir():
    REFDIR = ROOT / "stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input"
REF_SHA = {
    "H4W4B2": "219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447",
    "H4W4B20": "3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be",
    "H4W5B2": "8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c",
}
INDICATOR = ROOT / "research/evidence/P10CH_OFFLINE_20261120/derived/P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv"
if not INDICATOR.is_file():
    INDICATOR = ROOT / "P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv"
INDICATOR_SHA = "84b738960d712ba11eca880a86f98782905dc6dcc6cd3c72c70e4c97c42406c3"


def check(actual, expected, name):
    if actual != expected:
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")


def sha_bytes(b):
    return sha256(b).hexdigest()


def rows_bytes(b):
    return list(csv.DictReader(StringIO(b.decode("utf-8-sig"))))


def optfloat(x):
    return float(x) if x else None


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.] * len(v)
    i = 0
    while i < len(v):
        j = i + 1
        while j < len(v) and v[order[j]] == v[order[i]]:
            j += 1
        mean = (i + j - 1) / 2 + 1
        for k in range(i, j):
            out[order[k]] = mean
        i = j
    return out


def pearson(x, y):
    xm, ym = statistics.mean(x), statistics.mean(y)
    u = [v - xm for v in x]
    w = [v - ym for v in y]
    den = math.sqrt(sum(t*t for t in u) * sum(t*t for t in w))
    return sum(a*b for a, b in zip(u, w)) / den if den else float("nan")


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def normalized_within_band_rank_corr(x, y, bands):
    rx, ry = ranks(x), ranks(y)
    for mu in range(10):
        inds = [i for i, v in enumerate(bands) if v == mu]
        avgx = statistics.mean(rx[i] for i in inds)
        avgy = statistics.mean(ry[i] for i in inds)
        for i in inds:
            rx[i] -= avgx
            ry[i] -= avgy
    return pearson(rx, ry)


def main():
    check(sha_bytes(EVIDENCE.read_bytes()), EVIDENCE_SHA, "primary ZIP SHA")
    with zipfile.ZipFile(EVIDENCE) as z:
        check(set(z.namelist()), set(MEMBERS), "ZIP member names")
        check(z.testzip(), None, "ZIP CRC")
        raw = {name: z.read(name) for name in MEMBERS}
    for name, expected in MEMBERS.items():
        check(sha_bytes(raw[name]), expected, f"ZIP member SHA {name}")
    result = dict(line.split("=", 1) for line in raw["P10CK_RESULT.txt"].decode().splitlines())
    check(result["RESULT"], "P10CK_READONLY_27QP_GEOMETRY_PARITY_OK_NO_FEM", "Windows status")
    for field, expected in {"PHYSICAL_FEM_RUNS":"0", "MESHER_CALLS":"0",
                            "MESHES_PINNED_SHA_PASS":"3/3", "REFERENCE_P10BA_SHA_PASS":"3/3",
                            "TOTAL_QP_CELL_ROWS":"630"}.items():
        check(result[field], expected, field)
    data = rows_bytes(raw["P10CK_630CELL_QP_GEOMETRY.csv"])
    summaries = rows_bytes(raw["P10CK_3MESH_SUMMARY.csv"])
    check(len(data), 630, "data rows")
    check(len(summaries), 3, "mesh summaries")
    keys = [(r["mesh"], int(r["radial_bin"]), int(r["polar_band"])) for r in data]
    allkeys = {(m, d, mu) for m in REF_SHA for d in range(21) for mu in range(10)}
    check(set(keys), allkeys, "630 cell keys")
    check(len(set(keys)), len(keys), "unique 630 cell keys")
    bykey = dict(zip(keys, data))
    mesh_result = {}

    for summary in summaries:
        mesh = summary["mesh"]
        check(mesh in REF_SHA, True, "known mesh")
        path = REFDIR / (mesh + "_P10BA_QP_POLAR_RADIAL.csv")
        check(sha_bytes(path.read_bytes()), REF_SHA[mesh], "P10BA primary SHA " + mesh)
        ref = rows_bytes(path.read_bytes())
        reference = {}
        for r in ref:
            if int(r["time_step"]) != 6 or float(r["time_s"]) != 900.:
                continue
            ring = 1 + int(r["radial_subbin"]) if float(r["radial_lower_mm"]) < .05 - 1.e-9 else 11 + int(r["radial_subbin"])
            mu = int(r["polar_band"])
            check((ring, mu) not in reference, True, "unique P10BA cell")
            reference[ring, mu] = (int(r["qp_count"]), float(r["qp_volume_m3"]))
        check(len(reference), 200, "P10BA cell count")

        allrows = [r for r in data if r["mesh"] == mesh]
        check(len(allrows), 210, "rows per mesh")
        expected_qp_total = 0
        max_abs_rel = 0.
        max_abs_vdiff = 0.
        for (ring, mu), (n, vol) in reference.items():
            r = bykey[mesh, ring, mu]
            check(int(r["qp_count"]), n, "reference QP number")
            check(int(r["reference_p10ba_qp_count"]), n, "reported reference count")
            check(int(r["qp_count_diff"]), 0, "reported QP difference")
            vreported = float(r["qp_volume_m3"])
            vref_reported = float(r["reference_p10ba_qp_volume_m3"])
            check(abs(vref_reported - vol) <= 1.e-24, True, "reported P10BA reference volume")
            relative = (vreported - vol) / vol
            check(abs(relative) <= 1.e-8, True, "actual P10BA volume parity")
            check(abs(relative - float(r["qp_volume_rel_diff"])) < 5.e-12, True, "reported volume difference")
            max_abs_rel = max(max_abs_rel, abs(relative))
            max_abs_vdiff = max(max_abs_vdiff, abs(vreported - vol))
            expected_qp_total += n
        wallrows = [r for r in allrows if int(r["radial_bin"]) == 0]
        check(len(wallrows), 10, "0–20 µm rows")
        for r in wallrows:
            for f in ("reference_p10ba_qp_count", "reference_p10ba_qp_volume_m3", "qp_count_diff", "qp_volume_rel_diff"):
                check(r[f], "", "unavailable P10BA reference at 0–20 µm")
        check(int(summary["qp_count_20_to_100um"]), expected_qp_total, "P10BA QP summed count")
        check(int(summary["p10ba_qp_count_20_to_100um"]), expected_qp_total, "P10BA QP count summary")
        check(int(summary["27qp_sampled_tet_qps"]), 27*int(summary["candidate_Tet10"]), "candidate QP candidate count")

        for r in allrows:
            check(int(r["qp_count"]) > 0, True, "nonempty geometry bin")
            check(float(r["qp_volume_m3"]) > 0, True, "positive QP volume")
            check(float(r["sampled_detJ_min_m3"]) > 0, True, "positive sampled Jacobian")
            check(float(r["sampled_detJ_over_corner_min"]) > 0, True, "positive sampled J/corner")
            check(int(r["nonpositive_qp_in_cell"]), 0, "nonpositive in cell")
            check(0 <= int(r["phi_occupied_12_sectors"]) <= 12, True, "phi sectors bound")
        check(int(summary["nonpositive_candidate_qp_samples"]), 0, "nonpositive in candidate")
        check(int(summary["corner_nonpositive_candidate_tets"]), 0, "nonpositive corner")

        groups = {}
        for support, condition in (("0_20", lambda d: d == 0), ("20_100", lambda d: d > 0),
                                   ("0_100", lambda d: True)):
            for region, bcondition in (("polar", lambda mu: mu in (0, 9)),
                                       ("mid", lambda mu: 1 <= mu <= 8)):
                rr = [r for r in allrows if condition(int(r["radial_bin"])) and bcondition(int(r["polar_band"]))]
                groups[support + "_" + region] = {
                    "n_cells": len(rr), "qp_count":sum(int(r["qp_count"]) for r in rr),
                    "qp_volume_m3":sum(float(r["qp_volume_m3"]) for r in rr),
                    "min_sampled_J_over_corner": min(float(r["sampled_detJ_over_corner_min"]) for r in rr),
                    "max_sampled_J_over_corner": max(float(r["sampled_detJ_over_corner_max"]) for r in rr),
                    "max_abs_relative_J_deformation": max(max(abs(float(r["sampled_detJ_over_corner_min"]) - 1.),
                                                         abs(float(r["sampled_detJ_over_corner_max"]) - 1.)) for r in rr),
                    "nearaxis_rho_over_r_lt_0p1":sum(int(r["nearaxis_rho_over_r_lt_0p1_qp"]) for r in rr),
                    "unresolved_axis_qp":sum(int(r["axis_unresolved_qp"]) for r in rr),
                    "phi_sector_coverage_12_cells":sum(int(r["phi_occupied_12_sectors"]) == 12 for r in rr),
                }
        mesh_result[mesh] = {"source_nodes":int(summary["source_nodes"]),
                             "source_tet10":int(summary["source_Tet10"]),
                             "candidate_tet10":int(summary["candidate_Tet10"]),
                             "sampled_candidate_qp":int(summary["27qp_sampled_tet_qps"]),
                             "candidate_min_detJ_m3":float(summary["sampled_min_detJ_m3"]),
                             "max_abs_rel_p10ba_volume":max_abs_rel,
                             "max_abs_p10ba_volume_diff_m3":max_abs_vdiff,
                             "groups":groups}

    # Geometry-only difference is descriptive; join independently pinned P10CH (200 cells).
    check(sha_bytes(INDICATOR.read_bytes()), INDICATOR_SHA, "P10CH indicator SHA")
    ind = rows_bytes(INDICATOR.read_bytes())
    check(len(ind), 200, "P10CH indicator rows")
    by_geom = defaultdict(dict)
    for r in data:
        if int(r["radial_bin"]) > 0:
            by_geom[r["mesh"]][int(r["radial_bin"]),int(r["polar_band"])] = r
    correlation = {}
    for m in REF_SHA:
        xs, ys_bulk, ys_wall, mus = [], [], [], []
        for r in ind:
            lo = float(r["r_lower_mm"])
            ring = (1 + int(round((lo-.02)/.003))) if lo < .05 - 1.e-9 else (11 + int(round((lo-.05)/.005)))
            mu = int(r["polar_band"])
            src = by_geom[m][ring, mu]
            val = max(abs(float(src["sampled_detJ_over_corner_min"]) - 1.),
                      abs(float(src["sampled_detJ_over_corner_max"]) - 1.))
            xs.append(val)
            ys_bulk.append(abs(float(r["delta_bulk_per_m"])))
            ys_wall.append(abs(float(r["delta_wall_per_m"])))
            mus.append(mu)
        check(len(xs), 200, "joined geometry x P10CH")
        correlation[m] = {"spearman_abs_delta_bulk_vs_max_abs_J_ratio_minus_1":spearman(xs,ys_bulk),
                          "spearman_abs_delta_wall_vs_max_abs_J_ratio_minus_1":spearman(xs,ys_wall),
                          "within_polar_band_rank_bulk":normalized_within_band_rank_corr(xs,ys_bulk,mus),
                          "within_polar_band_rank_wall":normalized_within_band_rank_corr(xs,ys_wall,mus)}

    out = {"protocol":"P10CL_INDEPENDENT_READ_ONLY_P10CK_R1",
           "zip_sha256": EVIDENCE_SHA, "member_sha256": MEMBERS,
           "windows_wall_seconds":float(result["WALL_SECONDS"]),
           "mesh":mesh_result, "correlation":correlation,
           "no_new_fem":True, "no_new_mesh":True,
           "sampled_positive_is_global_J_proof":False,
           "p10ba_reference_0_to_20um":False,
           "physical_phi_resolved_D_R_jpeak":False}
    out_path = ROOT / "P10CL_INDEPENDENT_QP_GEOMETRY_AUDIT.json"
    out_path.write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True) + "\n",encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    import numpy as np
    theta_edges = np.degrees(np.arccos(np.linspace(1.,-1.,11)))
    radial_edges = np.array([0.,.020] + [.020+.003*i for i in range(1,11)] +
                            [.050+.005*i for i in range(1,11)])*1000.
    values = {}
    for m in REF_SHA:
        arr = np.zeros((21,10),dtype=float)
        for ring in range(21):
            for im in range(10):
                r = bykey[m,ring,9-im]
                arr[ring,im] = 100.*max(abs(float(r["sampled_detJ_over_corner_min"]) - 1.),
                                       abs(float(r["sampled_detJ_over_corner_max"]) - 1.))
        values[m] = arr
    ceiling = float(np.max(list(values.values())))
    fig,ax = plt.subplots(1,3,figsize=(14.5,5.),sharex=True,sharey=True,layout="constrained")
    for i,(m,arr) in enumerate(values.items()):
        pcm = ax[i].pcolormesh(theta_edges,radial_edges,arr,cmap="viridis",norm=Normalize(0.,ceiling),shading="flat",rasterized=True)
        ax[i].set_title(m + f"\nmax cell deviation = {arr.max():.2f}%")
        ax[i].set_xlabel(r"polar angle $\theta$ from +z (degrees)")
        ax[i].set_xticks([0,36.87,60,90,120,143.13,180],["0","36.9","60","90","120","143.1","180"])
        ax[i].axvline(float(np.degrees(np.arccos(.8))),ls="--",lw=.8,color="white",alpha=.9)
        ax[i].axvline(float(np.degrees(np.arccos(-.8))),ls="--",lw=.8,color="white",alpha=.9)
        ax[i].axhline(20.,ls=":",lw=.8,color="white",alpha=.8)
    ax[0].set_ylabel("distance from pore surface (µm)")
    cbar = fig.colorbar(pcm,ax=ax,shrink=.85,pad=.015)
    cbar.set_label(r"max sampled $|\det J/\det J_{corner} -1|$ in cell (%)")
    fig.suptitle("P10CK real curved Tet10: sampled 27-QP geometry, not a field derivative",fontsize=12)
    fig.savefig(ROOT / "P10CL_CURVED_TET10_THETA_RADIAL_GEOMETRY.png",dpi=180)
    plt.close(fig)
    print("P10CL_INDEPENDENT_QP_GEOMETRY_PASS_NO_FEM")
    for m, d in mesh_result.items():
        pole = d["groups"]["20_100_polar"]
        mid = d["groups"]["20_100_mid"]
        print(f"{m}: max_rel_volume={d['max_abs_rel_p10ba_volume']:.3e}, "
              f"Jratio_min_pole/mid={pole['min_sampled_J_over_corner']:.6f}/{mid['min_sampled_J_over_corner']:.6f}, "
              f"Jratio_max_pole/mid={pole['max_sampled_J_over_corner']:.6f}/{mid['max_sampled_J_over_corner']:.6f}, "
              f"corr_bulk_within_band={correlation[m]['within_polar_band_rank_bulk']:.3f}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"P10CL_AUDIT_STOP: {type(e).__name__}: {e}",file=sys.stderr)
        raise
