#!/usr/bin/env python3
"""P10CO: read-only availability audit of H4 baseline size proxies for M1.

Reconciles P10CI corner-centroid tables against mesh counts, and tests how
far P10CN trial factors can be attached to existing 20–100 µm diagnostics.
No .msh, Gmsh, FEM, physical h0(x), or global RAM estimate is created.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import math

ROOT=Path.cwd()
CI_DIR=ROOT/"research/evidence/P10CI_WINDOWS_GEOMETRY_20261120/input"
if not CI_DIR.is_dir():
    CI_DIR=ROOT/"P10CI_EVIDENCE_READONLY_20261120"
CM_CN = ROOT/"research/evidence/P10CN_OFFLINE_20261120/derived"
if not CM_CN.is_dir():
    CM_CN=ROOT
FILES={
    "P10CI_MESH_COUNTS.csv":"4c6da8910f96eacd75179c0415197cd0c5b47fafca77b07e212561aea844b788",
    "P10CI_200CELL_MESH_GEOMETRY.csv":"db22675c116b1d151e86c73726cc4e2aeba21bcb4c41c099ee4e5d2e4d3e9f61",
    "P10CI_0_TO_20UM_UNCOVERED_POLE_GEOMETRY.csv":"5cf06f11a9221cfee20e725cadf0d25b858475f67b897fd7246a41f5e745777d",
}
CN_FILES={
    "P10CN_200CELL_MERIDIONAL_SMOOTHING.csv":"365ebf4591ce2b1a5d91835f25eab96f75656008e5248cca831391da245bfbba",
    "P10CN_SMOOTHING_SENSITIVITY.json":"75e1b65f7b3823595585a55cdff1ff5da40735e14b997990aa0009e8aa8bdb80",
}
MESH_SHA={
    "H4W4B2":"3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7",
    "H4W4B20":"94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715",
    "H4W5B2":"db50a10fc2a12870bf6e678e2ef0be496feba218b1010f9e65f8669f67d093a8",
}


def assert_ok(b, msg):
    if not b:
        raise AssertionError(msg)


def verified(path, expected):
    b=path.read_bytes()
    if sha256(b).hexdigest()!=expected:
        raise ValueError("P10CO input SHA mismatch: "+str(path))
    return b


def asrows(path,sha):
    return list(csv.DictReader(verified(path,sha).decode("utf-8-sig").splitlines()))


def weighted_average(rows, field):
    n=sum(int(x["tet10_centroids"]) for x in rows)
    return sum(float(x[field])*int(x["tet10_centroids"]) for x in rows)/n


def main():
    rawcounts=asrows(CI_DIR/"P10CI_MESH_COUNTS.csv",FILES["P10CI_MESH_COUNTS.csv"])
    mainrows=asrows(CI_DIR/"P10CI_200CELL_MESH_GEOMETRY.csv",FILES["P10CI_200CELL_MESH_GEOMETRY.csv"])
    wallrows=asrows(CI_DIR/"P10CI_0_TO_20UM_UNCOVERED_POLE_GEOMETRY.csv",FILES["P10CI_0_TO_20UM_UNCOVERED_POLE_GEOMETRY.csv"])
    trialrows=asrows(CM_CN/"P10CN_200CELL_MERIDIONAL_SMOOTHING.csv",CN_FILES["P10CN_200CELL_MERIDIONAL_SMOOTHING.csv"])
    trialjson=json.loads(verified(CM_CN/"P10CN_SMOOTHING_SENSITIVITY.json",CN_FILES["P10CN_SMOOTHING_SENSITIVITY.json"]))
    assert_ok(len(rawcounts)==3 and len(mainrows)==600 and len(wallrows)==30 and len(trialrows)==200,
              "original 3 x 200 / 3 x 10 and 200 trial rows")
    assert_ok(trialjson["actual_mesh_created"] is False and trialjson["physical_fem_runs"]==0,
              "P10CN cannot have physical mesh/FEM")
    counts={r["mesh"]:r for r in rawcounts}
    assert_ok(set(counts)==set(MESH_SHA),"three original mesh IDs")
    results={}
    for mesh,original_sha in MESH_SHA.items():
        c=counts[mesh]
        assert_ok(c["mesh_sha256"]==original_sha,"original msh SHA gate reported")
        main=[r for r in mainrows if r["mesh"]==mesh]
        wall=[r for r in wallrows if r["mesh"]==mesh]
        assert_ok(len(main)==200 and len(wall)==10,"mesh cells exact")
        assert_ok(len({(int(r["radial_bin"]),int(r["polar_band"])) for r in main})==200,
                  "20x10 unique cells")
        assert_ok(len({int(r["polar_band"]) for r in wall})==10 and all(int(r["radial_bin"])==-1 for r in wall),
                  "0–20um wall bands")
        near=sum(int(r["tet10_centroids"]) for r in main)
        first=sum(int(r["tet10_centroids"]) for r in wall)
        B6_other=int(c["tet10_100um_to_B6_centroids"])
        total=int(c["tet10_count"])
        outside=total-(near+first+B6_other)
        assert_ok(near==int(c["tet10_near_pore_centroids"]) and first==int(c["tet10_0_to_20um_centroids"]),
                  "P10CI grouped centroid counts parity")
        assert_ok(B6_other>0 and outside>=0,"B6 beyond 100um is unmeasured per-cell")
        assert_ok(all(float(r["max_corner_edge_p50_mm"])>0. and int(r["corner_nonpositive_count"])==0
                      for r in main+wall),"positive measured corner-size proxy")
        assert_ok(all(int(r["corner_quality_below_0p1"])==0 for r in main+wall),
                  "corner q<0.1 proxy zero in scoped layers")
        results[mesh]={
            "reported_source_mesh_sha256":original_sha,"source_nodes_reported":int(c["node_count"]),
            "source_tet10_reported":total,"centroid_0_20um":first,"centroid_20_100um":near,
            "centroid_100um_to_B6":B6_other,"centroid_outside_B6":outside,
            "total_centroid_0_to_100um_fraction_of_B6":(first+near)/(first+near+B6_other),
            "unprofiled_B6_centroid_fraction":B6_other/(first+near+B6_other),
            "20_100_corner_maxedge_p50_cell_median_weighted_mean_mm":weighted_average(main,"max_corner_edge_p50_mm"),
            "0_20_corner_maxedge_p50_cell_median_weighted_mean_mm":weighted_average(wall,"max_corner_edge_p50_mm"),
            "20_100_corner_maxedge_p50_cell_min_mm":min(float(r["max_corner_edge_p50_mm"]) for r in main),
            "20_100_corner_maxedge_p50_cell_max_mm":max(float(r["max_corner_edge_p50_mm"]) for r in main),
            "actual_full_3d_h0_function_available":False,
            "corner_edge_median_is_actual_h0":False,
        }

    trial={(int(r["radial_bin"]),int(r["polar_band"])):r for r in trialrows}
    assert_ok(len(trial)==200,"unique P10CN trial keys")
    base_main={(int(r["radial_bin"]),int(r["polar_band"])):r for r in mainrows if r["mesh"]=="H4W4B2"}
    rows=[]
    expected_new_near=0.
    for key in sorted(base_main):
        r=base_main[key]
        t=trial[key]
        old_proxy=float(r["max_corner_edge_p50_mm"])
        q=float(t["trial_h_over_h0_alpha_0p50"])
        n=int(r["tet10_centroids"])
        assert_ok(0.<q<=1.,"trial relative h positive and <=1")
        expected_new_near+=n/q**3
        rows.append({"radial_bin":key[0],"polar_band":key[1],"centroid_tet_count":n,
                     "p50_of_element_max_corner_edge_mm":old_proxy,
                     "trial_relative_h":q,
                     "illustrative_p50_edge_times_relative_h_mm":old_proxy*q,
                     "illustrative_local_centroid_count_proxy":n/q**3,
                     "actual_h0_function_status":"NOT_CALIBRATED",
                     "physical_3d_mesh_count_status":"NOT_PREDICTED"})
    near0=results["H4W4B2"]["centroid_20_100um"]
    total0=results["H4W4B2"]["source_tet10_reported"]
    illustrative_total=total0+(expected_new_near-near0)
    assert_ok(expected_new_near>=near0,"count proxy must not decrease")

    audit={"protocol":"P10CO_EXISTING_H0_SIZE_PROXY_COVERAGE_NO_MESH_NO_FEM",
           "source_P10CI_member_sha256":FILES,"source_P10CN_sha256":CN_FILES,
           "source_msh_sha256_reported_only":MESH_SHA,
           "mesh":results,
           "H4W4B2_20_100um_only_trial":{
               "baseline_centroid_tets":near0,
               "new_local_centroid_count_cube_proxy":expected_new_near,
               "relative_local_count_cube_proxy":expected_new_near/near0,
               "conditional_total_tet_proxy_if_every_other_element_and_transition_unchanged":illustrative_total,
               "conditional_total_tet_proxy_ratio":illustrative_total/total0,
               "condition_is_a_physical_mesh_prediction":False,
               "source_p10cn_volume_weighted_local_proxy":trialjson["baseline"]["local_isotropic_tet_count_volume_proxy"],
               "different_weights_count_vs_volume_expected":True},
           "full_B6_h0_status":"NOT_CALIBRATED_MISSING_100UM_TO_B6_LOCAL_SIZE",
           "full_B6_element_count_ram_wall_estimate":"NOT_AVAILABLE",
           "new_mesh_created":False,"mesher_calls":0,"physical_fem_runs":0}
    (ROOT/"P10CO_BASELINE_H0_COVERAGE_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    out=ROOT/"P10CO_H4W4B2_200CELL_LOCAL_EDGE_PROXY.csv"
    with out.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    fig,ax=plt.subplots(1,2,figsize=(12.8,4.5),layout="constrained")
    cats=["0–20 µm","20–100 µm","0.1–5 mm","outside B6"]
    colors=["#258d83","#3b84bd","#e5a54c","#9c9c9c"]
    names=list(MESH_SHA)
    bases=np.zeros(3)
    for j,(key,color) in enumerate(zip(["centroid_0_20um","centroid_20_100um","centroid_100um_to_B6","centroid_outside_B6"],colors)):
        vals=np.array([results[m][key]/results[m]["source_tet10_reported"]*100. for m in names])
        ax[0].bar(names,vals,bottom=bases,label=cats[j],color=color)
        bases+=vals
    ax[0].set_ylim(0,100);ax[0].set_ylabel("share of original Tet10 corner centroids (%)")
    ax[0].set_title("Where P10CI has per-cell size proxies")
    ax[0].legend(loc="center left",bbox_to_anchor=(.02,.55),fontsize=8)
    bmat=np.array([[float(base_main[r,9-col]["max_corner_edge_p50_mm"]) for col in range(10)] for r in range(20)])
    theta=np.degrees(np.arccos(np.linspace(1.,-1.,11)))
    d_edges=np.array([.02+i*.003 for i in range(11)]+[.05+i*.005 for i in range(1,11)])*1000.
    pc=ax[1].pcolormesh(theta,d_edges,bmat,cmap="cividis",shading="flat")
    ax[1].set_title("H4W4B2: cell median of max corner edge")
    ax[1].set_xlabel("polar angle θ from +z (degrees)")
    ax[1].set_ylabel("distance from pore wall (µm)")
    ax[1].set_xticks([0,36.87,90,143.13,180],["0","36.9","90","143.1","180"])
    fig.colorbar(pc,ax=ax[1],shrink=.8,label="median(max corner edge), mm; NOT h0")
    fig.suptitle("P10CO read-only baseline size coverage: no mesh, FEM, or full-B6 h0 calibration")
    fig.savefig(ROOT/"P10CO_H0_COVERAGE_AND_LOCAL_PROXY.png",dpi=180)
    plt.close(fig)
    print("P10CO_PRIMARY_CENTROID_COUNT_RECONCILIATION_OK_NO_FEM")
    for mesh in MESH_SHA:
        d=results[mesh]
        print(mesh,"B6 size-proxy coverage",round(d["total_centroid_0_to_100um_fraction_of_B6"]*100,3),"%",
              "edge_p50 weighted",round(d["20_100_corner_maxedge_p50_cell_median_weighted_mean_mm"],6),"mm")
    print("H4W4B2 conditional local tet factor",round(expected_new_near/near0,6),
          "illustrative whole original tet factor if others unchanged",round(illustrative_total/total0,6))
    print("RESULT=P10CO_FULL_B6_H0_NOT_CALIBRATED_NO_MESH_NO_FEM")


if __name__=="__main__":
    main()
