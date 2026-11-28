#!/usr/bin/env python3
"""Independent P10CP evidence archive audit: SHA/CRC/8640-cell closure + geometry comparisons.

Never accesses source .msh, Gmsh, FEM, Git, or physical fields. All derived
comparisons of cell percentiles are count-weighted summaries, NOT pooled
per-element quantiles or calibrated mesh metric h0.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
import sys
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np

ARCHIVE_SHA = "20907ff41f5061d72cd5e07ddcce3fc54824ca0a57dcd33e7ef08696a2587725"
P10CI_COUNTS_SHA = "4c6da8910f96eacd75179c0415197cd0c5b47fafca77b07e212561aea844b788"
MESHES = {
    "H4W4B2": ("3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7", 367823, 261091, 18518, 29288, 192565, 20720),
    "H4W4B20": ("94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715", 449522, 323052, 18525, 29577, 254258, 20692),
    "H4W5B2": ("db50a10fc2a12870bf6e678e2ef0be496feba218b1010f9e65f8669f67d093a8", 393998, 275549, 26465, 35331, 192965, 20788),
}
FILES = {
    "P10CP_RESULT.txt", "P10CP_MANIFEST.json", "P10CP_MESH_SUMMARY.csv",
    "P10CP_MERIDIONAL_720CELL_PROFILE.csv", "P10CP_3D_8640CELL_PROFILE.csv",
}
COUNTERS = [
    "tet10_corner_centroids", "corner_nonpositive_count", "corner_quality_lt_0p1_count",
    "corner_cross_radial_bin_count", "corner_cross_polar_band_count",
    "centroid_phi_axis_ambiguous_count",
]
QUANTILES = [
    "hmax_corner_edge_p05_mm", "hmax_corner_edge_p50_mm", "hmax_corner_edge_p95_mm",
    "hvol_corner_p50_mm", "corner_quality_p05", "corner_quality_p50",
    "corner_edge_ratio_p95", "midside_deviation_over_edge_p95",
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def getrows(raw):
    d = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    data = list(d)
    if not d.fieldnames or any(None in row for row in data):
        raise ValueError("missing CSV header or extra columns")
    return data


def close(a, b, atol=1e-14, rtol=1e-9):
    return abs(a - b) <= max(atol, rtol * max(abs(a), abs(b)))


def assert_fail_if(condition, description):
    if condition:
        raise AssertionError(description)


def validate_rows(rows, full, radial_bounds):
    rows_by_key = {}
    expected_n = 24 * 10 * (12 if full else 1)
    for mesh in MESHES:
        seen = [row for row in rows if row["mesh"] == mesh]
        assert_fail_if(len(seen) != expected_n, f"{mesh} incorrect per-mesh row count")
    for row in rows:
        mesh = row["mesh"]
        assert_fail_if(mesh not in MESHES, "unexpected mesh identity")
        ri, pi = int(row["radial_bin"]), int(row["polar_band"])
        assert_fail_if(not (0 <= ri < 24 and 0 <= pi < 10), "invalid radial/polar index")
        sector = int(row["phi_sector"]) if full else None
        if full:
            assert_fail_if(not (0 <= sector < 12), "invalid azimuth index")
            assert_fail_if(not close(float(row["phi_lower_deg"]), 30 * sector), "phi lower mismatch")
            assert_fail_if(not close(float(row["phi_upper_deg"]), 30 * (sector + 1)), "phi upper mismatch")
        else:
            assert_fail_if(row["phi_sector"] != "", "meridional phi should be blank")
        key = (mesh, ri, pi, sector)
        assert_fail_if(key in rows_by_key, "duplicate 3D cell key")
        rows_by_key[key] = row
        assert_fail_if(not close(float(row["d_lower_mm"]), radial_bounds[ri]), "radial lower incorrect")
        assert_fail_if(not close(float(row["d_upper_mm"]), radial_bounds[ri + 1]), "radial upper incorrect")
        assert_fail_if(not close(float(row["mu_lower"]), -1 + pi * .2), "mu lower incorrect")
        assert_fail_if(not close(float(row["mu_upper"]), -1 + (pi + 1) * .2), "mu upper incorrect")
        n = int(row["tet10_corner_centroids"])
        for col in COUNTERS:
            value = int(row[col])
            assert_fail_if(value < 0 or value > n, col + ": invalid count")
        volume = float(row["sum_corner_volume_m3"])
        assert_fail_if(not math.isfinite(volume) or volume < 0, "invalid volume")
        if n == 0:
            assert_fail_if(volume != 0 or any(row[c] != "" for c in QUANTILES), "empty cell has fake statistics")
        else:
            nums = {c: float(row[c]) for c in QUANTILES}
            assert_fail_if(not all(math.isfinite(v) for v in nums.values()), "nonfinite metric")
            assert_fail_if(not (0 < nums["hmax_corner_edge_p05_mm"] <= nums["hmax_corner_edge_p50_mm"] <= nums["hmax_corner_edge_p95_mm"]), "edge quantiles not ordered")
            assert_fail_if(not (0 <= nums["corner_quality_p05"] <= nums["corner_quality_p50"] <= 1.00000001), "invalid corner quality")
            assert_fail_if(nums["corner_edge_ratio_p95"] < 1 or nums["midside_deviation_over_edge_p95"] < 0, "invalid curvature/edge ratio")
    return rows_by_key


def weighted_mean(rows, field):
    w = sum(int(row["tet10_corner_centroids"]) for row in rows)
    if w <= 0:
        return None
    return sum(int(row["tet10_corner_centroids"]) * float(row[field])
               for row in rows if int(row["tet10_corner_centroids"])) / w


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "upload/P10CP_EVIDENCE.zip")
    actual_sha = sha(path.read_bytes())
    assert_fail_if(actual_sha != ARCHIVE_SHA, "original evidence archive SHA mismatch")
    with zipfile.ZipFile(path) as z:
        assert_fail_if(z.testzip() is not None, "ZIP CRC failure")
        assert_fail_if(set(z.namelist()) != FILES, "unexpected/missing ZIP entry")
        all_bytes = {name: z.read(name) for name in FILES}
    status = all_bytes["P10CP_RESULT.txt"].decode("utf-8-sig")
    assert_fail_if("RESULT=P10CP_ORIGINAL_B6_MESH_PROFILE_OK_NO_FEM" not in status, "not an OK result")
    for gate in ["PINNED_RAW_MESH_SHA256=PASS_3_OF_3", "NODE_TET10_CATEGORY_COUNTS=PASS_3_OF_3", "TET10_RADIAL_MU_PHI_PARTITION=PASS_3_OF_3", "FEM_RUNS=0", "GMSH_CALLS=0"]:
        assert_fail_if(gate not in status, "missing reported gate "+gate)
    manifest = json.loads(all_bytes["P10CP_MANIFEST.json"].decode("utf-8-sig"))
    assert_fail_if(manifest["revision"] != "P10CP_R1_B6_ORIGINAL_MESH_READONLY_SIZE_QUALITY_NO_FEM", "unexpected revision")
    assert_fail_if(manifest["FEM_runs"] != 0 or manifest["gmsh_calls"] != 0, "unexpected physical/mesher operations")
    radial = manifest["binning"]["radial_mm"]
    assert_fail_if(len(radial) != 25 or not all(radial[i] < radial[i + 1] for i in range(24)), "bad radial grid")
    for i, val in enumerate(radial):
        assert_fail_if(not close(val, .1 * 50.0 ** (i / 24)), "radial grid not the prepared protocol")
    expected_hashes = manifest["csv_sha256"]
    assert_fail_if(len(expected_hashes) != 3, "CSV digest set mismatch")
    for name in expected_hashes:
        assert_fail_if(sha(all_bytes[name]) != expected_hashes[name], "CSV SHA gate failure for " + name)
    assert_fail_if({x["mesh"] for x in manifest["input_hashes"]} != set(MESHES), "input SHA identity set mismatch")
    for src in manifest["input_hashes"]:
        expect = MESHES[src["mesh"]]
        assert_fail_if(src["sha256"] != expect[0] or src["expected_nodes"] != expect[1] or src["expected_tet10"] != expect[2], "source mesh pin mismatch")
    summary = getrows(all_bytes["P10CP_MESH_SUMMARY.csv"])
    existing_p10ci = [Path("P10CI_EVIDENCE_READONLY_20261120/P10CI_MESH_COUNTS.csv"), Path("research/evidence/P10CI_WINDOWS_GEOMETRY_20261120/input/P10CI_MESH_COUNTS.csv")]
    p10ci_path = next((p for p in existing_p10ci if p.is_file()), None)
    if p10ci_path is None:
        raise FileNotFoundError("cannot independently locate previously published original P10CI mesh counts")
    p10ci_bytes = p10ci_path.read_bytes()
    assert_fail_if(sha(p10ci_bytes) != P10CI_COUNTS_SHA, "original P10CI mesh counts SHA mismatch")
    p10ci_map = {row["mesh"]:row for row in getrows(p10ci_bytes)}
    assert_fail_if(set(p10ci_map) != set(MESHES), "P10CI mesh keys changed")
    merid = getrows(all_bytes["P10CP_MERIDIONAL_720CELL_PROFILE.csv"])
    spherical = getrows(all_bytes["P10CP_3D_8640CELL_PROFILE.csv"])
    assert_fail_if((len(summary), len(merid), len(spherical)) != (3,720,8640), "CSV file row counts wrong")
    m = validate_rows(merid, False, radial)
    f = validate_rows(spherical, True, radial)
    # Every 3D sector must close onto the corresponding meridional bin.
    max_volume_rel = 0.0
    for (mesh, ri, pi, _), row in m.items():
        children = [f[(mesh, ri, pi, sec)] for sec in range(12)]
        for col in COUNTERS:
            assert_fail_if(int(row[col]) != sum(int(c[col]) for c in children), f"meridional-to-phi nonclosure {mesh} {ri} {pi} {col}")
        subtotal = sum(float(c["sum_corner_volume_m3"]) for c in children)
        total = float(row["sum_corner_volume_m3"])
        rel = abs(subtotal-total) / max(abs(total), 1e-30)
        max_volume_rel = max(max_volume_rel, rel)
        assert_fail_if(not close(total, subtotal, atol=1e-19, rtol=2e-10), f"meridional-to-phi volume mismatch {mesh} {ri} {pi}")
    summary_map = {}
    for row in summary:
        mesh = row["mesh"]
        assert_fail_if(mesh in summary_map or mesh not in MESHES, "mesh summary identity mismatch")
        summary_map[mesh] = row
        original = MESHES[mesh]
        observed = [row["mesh_sha256"], int(row["node_count"]), int(row["tet10_count"]), int(row["tet10_0_20um"]), int(row["tet10_20_100um"]), int(row["tet10_100um_5mm"]), int(row["tet10_outside_B6"])]
        assert_fail_if(observed != list(original), "mesh source counts differ from P10CI for " + mesh)
        old = p10ci_map[mesh]
        source_fields = [old["mesh_sha256"], int(old["node_count"]), int(old["tet10_count"]), int(old["tet10_0_to_20um_centroids"]), int(old["tet10_near_pore_centroids"]), int(old["tet10_100um_to_B6_centroids"]), int(old["tet10_count"]) - int(old["tet10_0_to_20um_centroids"]) - int(old["tet10_near_pore_centroids"]) - int(old["tet10_100um_to_B6_centroids"]) - int(old["tet10_centroid_inside_nominal_pore"])]
        assert_fail_if(observed != source_fields, "P10CP categories fail independently hashed P10CI source for " + mesh)
        assert_fail_if(sum(int(m[(mesh,ri,pi,None)]["tet10_corner_centroids"]) for ri in range(24) for pi in range(10)) != original[5], "meridional count doesn't match source " + mesh)
        for col in ["corner_nonpositive_count", "corner_quality_lt_0p1_count"]:
            assert_fail_if(sum(int(m[(mesh,ri,pi,None)][col]) for ri in range(24) for pi in range(10)) != int(row[col + "_100um_5mm"]), "quality summary mismatch")
    assert_fail_if(set(summary_map) != set(MESHES), "missing mesh summary")

    # Diagnostic comparisons: weighted MEAN OF CELL QUANTILES, not a pooled quantile.
    by_mesh = {}
    radial_comparisons = {}
    angular_data = {}
    for mesh, original in MESHES.items():
        part = [row for (mm,_,_,_),row in m.items() if mm == mesh]
        polar = [row for row in part if int(row["polar_band"]) in (0,9)]
        middle = [row for row in part if int(row["polar_band"]) not in (0,9)]
        total = original[5]
        npolar = sum(int(row["tet10_corner_centroids"]) for row in polar)
        nmid = total - npolar
        counts_per_sector = [sum(int(f[(mesh,ri,pi,sec)]["tet10_corner_centroids"]) for ri in range(24) for pi in range(10)) for sec in range(12)]
        sector_cv = float(np.std(counts_per_sector) / np.mean(counts_per_sector))
        rows_size = [row for row in part if int(row["tet10_corner_centroids"]) > 0]
        by_mesh[mesh] = {
            "tet10_100um_to_5mm": total,
            "polar_count": npolar,
            "middle_count": nmid,
            "polar_fraction": npolar/total,
            "weighted_mean_cell_hmax_p50_mm_polar": weighted_mean(polar,"hmax_corner_edge_p50_mm"),
            "weighted_mean_cell_hmax_p50_mm_middle": weighted_mean(middle,"hmax_corner_edge_p50_mm"),
            "weighted_mean_cell_quality_p05_polar": weighted_mean(polar,"corner_quality_p05"),
            "weighted_mean_cell_quality_p05_middle": weighted_mean(middle,"corner_quality_p05"),
            "quality_below_0p1_count": sum(int(row["corner_quality_lt_0p1_count"]) for row in part),
            "corner_nonpositive_count": sum(int(row["corner_nonpositive_count"]) for row in part),
            "cross_radial_fraction": sum(int(row["corner_cross_radial_bin_count"]) for row in part)/total,
            "cross_polar_fraction": sum(int(row["corner_cross_polar_band_count"]) for row in part)/total,
            "centroid_phi_ambiguous_count": sum(int(row["centroid_phi_axis_ambiguous_count"]) for row in part),
            "azimuth_sector_counts": counts_per_sector,
            "azimuth_12sector_count_cv": sector_cv,
            "nonempty_meridional_cells": len(rows_size),
            "nonempty_3d_cells": sum(int(row["tet10_corner_centroids"]) > 0 for (mm,_,_,_),row in f.items() if mm == mesh),
            "max_meridional_midside_dev_p95": max(float(row["midside_deviation_over_edge_p95"]) for row in rows_size),
            "weighted_mean_cell_midside_dev_p95_polar": weighted_mean(polar,"midside_deviation_over_edge_p95"),
            "weighted_mean_cell_midside_dev_p95_middle": weighted_mean(middle,"midside_deviation_over_edge_p95"),
            "meridional_cells_midside_dev_p95_above_0p01": sum(float(row["midside_deviation_over_edge_p95"])>.01 for row in rows_size),
        }
        greatest=max(rows_size,key=lambda row:float(row["midside_deviation_over_edge_p95"]))
        by_mesh[mesh]["max_curvature_proxy_cell"] = {"radial_bin":int(greatest["radial_bin"]),"polar_band":int(greatest["polar_band"]),"d_lower_mm":float(greatest["d_lower_mm"]),"d_upper_mm":float(greatest["d_upper_mm"])}
        by_mesh[mesh]["hmax_p50_polar_over_middle"] = by_mesh[mesh]["weighted_mean_cell_hmax_p50_mm_polar"] / by_mesh[mesh]["weighted_mean_cell_hmax_p50_mm_middle"]
        ratios=[]
        for ri in range(24):
            p = [m[(mesh,ri,pi,None)] for pi in (0,9)]
            mid = [m[(mesh,ri,pi,None)] for pi in range(1,9)]
            hp, hm = weighted_mean(p,"hmax_corner_edge_p50_mm"), weighted_mean(mid,"hmax_corner_edge_p50_mm")
            qp, qm = weighted_mean(p,"corner_quality_p05"),weighted_mean(mid,"corner_quality_p05")
            count_total = sum(int(row["tet10_corner_centroids"]) for row in p+mid)
            ratios.append({
                "radial_bin":ri, "d_lo_mm": radial[ri],"d_hi_mm":radial[ri+1],
                "n": count_total,
                "hmax_polar_mean_cell_p50_mm": hp,"hmax_middle_mean_cell_p50_mm":hm,
                "hmax_polar_over_middle": hp/hm if hp is not None and hm else None,
                "quality_p05_polar_minus_middle": qp-qm if qp is not None and qm is not None else None,
                "cross_radial_fraction":sum(int(row["corner_cross_radial_bin_count"]) for row in p+mid)/count_total if count_total else None,
            })
        radial_comparisons[mesh]=ratios
        # Fraction of elements in each (mu,phi) sector normalized per same-mu mean.
        angular=np.zeros((10,12))
        for pi in range(10):
            for fi in range(12):
                angular[pi,fi] = sum(int(f[(mesh,ri,pi,fi)]["tet10_corner_centroids"]) for ri in range(24) if radial[ri]<1.0)
        angular_data[mesh] = angular

    result = {
        "status":"P10CQ_INDEPENDENT_P10CP_EVIDENCE_AUDIT_OK_NO_FEM",
        "evidence_sha256":actual_sha,
        "source_gmsh2_mesh_bytes_reaudited_by_assistant":False,
        "zipped_csv_SHA_pass":3,
        "crc_pass":True,
        "source_p10ci_count_reconciled":3,
        "original_p10ci_counts_sha256":P10CI_COUNTS_SHA,
        "rows_meridional":len(merid),"rows_3d":len(spherical),
        "cells_phi_to_meridion_counters_closure":720,
        "max_phi_to_meridional_corner_volume_rel":max_volume_rel,
        "definition":"Original straight-sided CORNER Tetra10 geometry 100um–5mm; not prescribed h0, not curved 27QP, not FEM goal error",
        "by_mesh":by_mesh,
        "radial_polar_middle_comparison":radial_comparisons,
    }
    output=Path("P10CQ_INDEPENDENT_P10CP_B6_AUDIT.json")
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    plt.rcParams.update({"font.size":9,"figure.dpi":150,"savefig.dpi":170})
    fig, axes=plt.subplots(2,2,figsize=(13.8,9.3),layout="constrained")
    meshes=list(MESHES)
    col={"H4W4B2":"#1f77b4","H4W4B20":"#e07b12","H4W5B2":"#237c58"}
    rmid=np.sqrt(np.array(radial[:-1])*np.array(radial[1:]))
    # Full meridional view, H4W4B2 only.
    field=np.full((10,24),np.nan)
    for pi in range(10):
        for ri in range(24):
            row=m[("H4W4B2",ri,pi,None)]
            if int(row["tet10_corner_centroids"])>0:
                field[pi,ri]=float(row["hmax_corner_edge_p50_mm"])
    theta_edges=np.degrees(np.arccos(np.linspace(-1,1,11)))
    ax=axes[0,0]
    im=ax.pcolormesh(radial,theta_edges,field,cmap="viridis",shading="flat",norm=colors.LogNorm(vmin=np.nanmin(field),vmax=np.nanmax(field)))
    ax.set_xscale("log");ax.set_xlabel("d = r − R, мм");ax.set_ylabel("θ, градусы (0° — северный полюс)")
    ax.set_title("H4W4B2: ячеечная медиана max углового ребра, мм")
    fig.colorbar(im,ax=ax,label="hmax p50, мм")
    ax=axes[0,1]
    for mesh in meshes:
        y=[r["hmax_polar_over_middle"] for r in radial_comparisons[mesh]]
        ax.plot(rmid,y,"-o",lw=1.4,ms=3,c=col[mesh],label=mesh)
    ax.axhline(1.,c="black",lw=.8,ls="--",alpha=.7);ax.set_xscale("log")
    ax.set_xlabel("d, мм");ax.set_ylabel("полюса / средние полосы")
    ax.set_title("Отношение средних по числу элементов ячеечных hmax p50")
    ax.legend(fontsize=8)
    ax=axes[1,0]
    for mesh in meshes:
        y=[r["quality_p05_polar_minus_middle"] for r in radial_comparisons[mesh]]
        ax.plot(rmid,y,"-o",lw=1.4,ms=3,c=col[mesh],label=mesh)
    ax.axhline(0,c="black",lw=.8,ls="--",alpha=.7);ax.set_xscale("log")
    ax.set_xlabel("d, мм");ax.set_ylabel("полярное − среднее качество")
    ax.set_title("Разность средних по числу элементов ячеечных quality p05")
    ax=axes[1,1]
    z=angular_data["H4W4B2"]
    normz=z/np.maximum(z.mean(axis=1,keepdims=True),1)
    im=ax.imshow(normz,aspect="auto",origin="lower",cmap="RdBu_r",vmin=.6,vmax=1.4,extent=[0,360,-1,1])
    ax.set_xlabel("φ, градусы");ax.set_ylabel("μ = cosθ")
    ax.set_xticks([0,60,120,180,240,300,360]);ax.set_yticks([-1,-.8,-.4,0,.4,.8,1])
    ax.set_title("H4W4B2, d 0.1–1 мм: число центров / среднее в μ-полосе")
    fig.colorbar(im,ax=ax,label="относительная населённость φ-сектора")
    fig.suptitle("Stage3D07 P10CQ: геометрия существующих сеток, 0.1–5 мм; НЕ ошибка D_R jpeak",fontsize=12)
    output_plot=Path("P10CQ_ORIGINAL_B6_POLAR_SIZE_QUALITY_COMPARISON.png")
    fig.savefig(output_plot,bbox_inches="tight")
    plt.close(fig)
    print(result["status"])
    print("ARCHIVE_SHA256="+actual_sha)
    print("CLOSURE_ROWS=720 VOLUME_REL_MAX="+str(max_volume_rel))
    for mesh, val in by_mesh.items():
        print(mesh+" POLAR_FRACTION="+str(round(val["polar_fraction"],6))+" HMAX_POLAR/MID="+str(round(val["hmax_p50_polar_over_middle"],6))+" Q_P05_POLAR/MID="+str(round(val["weighted_mean_cell_quality_p05_polar"],6))+"/"+str(round(val["weighted_mean_cell_quality_p05_middle"],6))+" CROSS_R="+str(round(val["cross_radial_fraction"],6))+" AZIMUTH_CV="+str(round(val["azimuth_12sector_count_cv"],6))+" DEV_P95_MAX="+str(val["max_meridional_midside_dev_p95"]))
    print("JSON_SHA256="+sha(output.read_bytes()))
    print("PNG_SHA256="+sha(output_plot.read_bytes()))


if __name__ == "__main__":
    main()
