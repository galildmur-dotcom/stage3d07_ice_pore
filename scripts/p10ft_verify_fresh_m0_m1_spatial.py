#!/usr/bin/env python3
"""Read-only comparison of genuinely fresh P10FP M0->M1, fixed 3D QP.

Reuses the previously published P10ED geometric quadrature partitions;
does not reuse historical M0/H0/M1 physics or their mesh SHAs. No FEM/Gmsh.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
from p10ed_verify_original_m1_m2_raw_spatial import (  # noqa: E402
    RAD, POL, curved, rule27, spatial_rule,
)
from p10fq_verify_fresh_m0_729qp import load_mesh, evaluate  # noqa: E402

SHA_M0 = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
SHA_M1 = "f281d253571db095b90790326f503dfa3f6fe3a1dc5cb5c904fca2787dfe4275"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(path,expected):
    if sha(path)!=expected:
        raise RuntimeError("unexpected mesh SHA: " + str(path))
    xyz,tets,tri,pore_error=load_mesh(path)
    N,D,W=rule27()
    vol,det,_=curved(xyz[tets],N,D,W)
    if not np.all(det>0) or not np.all(vol>0):
        raise RuntimeError("bad 27QP detJ")
    return {"nodes":xyz,"tet10":tets},vol,{"nodes":len(xyz),"tet10":len(tets),
         "tri6_tags":tri,"pore_radius_max_error_m":pore_error,
         "volume_m3":float(vol.sum()),"min_det27":float(det.min())}


def pore_surface(path):
    nodes={}
    triangles=[]
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip()=="$Nodes":
                for _ in range(int(f.readline())):
                    r=f.readline().split()
                    nodes[int(r[0])]=np.array([float(x) for x in r[1:]])
            elif line.strip()=="$Elements":
                for _ in range(int(f.readline())):
                    r=list(map(int,f.readline().split()))
                    if r[1]==9 and r[3]==8:
                        triangles.append(r[3+r[2]:])
    edge=np.zeros(len(triangles))
    north=[];south=[];equator=[]
    for i,ids in enumerate(triangles):
        p=np.array([nodes[j] for j in ids[:3]])
        edge[i]=np.median([np.linalg.norm(p[0]-p[1]),
                           np.linalg.norm(p[1]-p[2]),np.linalg.norm(p[2]-p[0])])
        c=p.mean(axis=0)-[0,0,.03]
        mu=c[2]/np.linalg.norm(c)
        (north if mu>=.8 else south if mu<=-.8 else equator).append(edge[i])
    return {"tri6":len(triangles),"median_corner_edge_mm":float(np.median(edge)*1e3),
            "north_polar_tri":len(north),"south_polar_tri":len(south),
            "north_polar_median_edge_mm":float(np.median(north)*1e3) if north else None,
            "south_polar_median_edge_mm":float(np.median(south)*1e3) if south else None}


def compare(a,b):
    def ratio(k):
        return [y/x for x,y in zip(a[k],b[k])]
    zones=[]
    for i,(r,p) in enumerate((r,p) for r in RAD for p in POL):
        zones.append({"radial":r,"polar":p,
                      "M1_over_M0_effective_volume":ratio("qp_effective_tet_volume_m3")[i],
                      "M1_over_M0_region_volume":ratio("qp_spatial_volumes_m3")[i],
                      "M0_effective_volume_m3":a["qp_effective_tet_volume_m3"][i],
                      "M1_effective_volume_m3":b["qp_effective_tet_volume_m3"][i]})
    north,south=ratio("qp_north_south_effective_tet_volume_m3")[:2]
    return {"order_per_axis":a["order_per_axis"],
            "qp_per_tet":a["qp_per_tet"],
            "minimum_detj_M0":a["min_curved_Jacobian_m3"],
            "minimum_detj_M1":b["min_curved_Jacobian_m3"],
            "zones9":zones,
            "priority_d_0_100um_abs_mu_ge_0p8":{
                "north_ratio":north,"south_ratio":south,
                "both_ratio":zones[0]["M1_over_M0_effective_volume"],
                "north_south_meet_0p75_0p85":all(.75<=v<=.85 for v in (north,south)),
                "both_meets_0p75_0p85":.75<=zones[0]["M1_over_M0_effective_volume"]<=.85}}


def plot_gate(report, path):
    """Visualize the physical-zone ratios without creating a new acceptance test."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    zones=report["refinement_samples"]["9"]["zones9"]
    q=np.array([z["M1_over_M0_effective_volume"] for z in zones]).reshape(3,3)
    fig,(ax,cap)=plt.subplots(1,2,figsize=(12.8,4.5),
                              gridspec_kw={"width_ratios":[1.7,1]})
    cmap=plt.colormaps["coolwarm"].copy()
    image=ax.imshow(q,cmap=cmap,vmin=.68,vmax=1.12,aspect="auto")
    ax.set_xticks(range(3),[r"polar $|\mu|\geq0.8$",r"taper $.6<|\mu|<.8$",
                            r"off $|\mu|\leq.6$"])
    ax.set_yticks(range(3),["wall 0–100 μm","wall 100–500 μm",">500 μm"])
    for i in range(3):
        for j in range(3):
            ax.text(j,i,f"{q[i,j]:.3f}\n{'PASS' if .75<=q[i,j]<=.85 else 'STOP'}",
                    ha="center",va="center",fontsize=10,weight="bold",
                    color="white" if q[i,j]>.94 else "black")
    ax.set_title("Fixed physical 3D zones (729 QP/Tet10)")
    fig.colorbar(image,ax=ax,fraction=.045,pad=.025,label="Veff M1 / M0")
    p=report["priority_order9"]
    bars=[p["north_ratio"],p["south_ratio"]]
    cap.axhspan(.75,.85,color="mediumseagreen",alpha=.24,label="accepted 0.75–0.85")
    cap.bar(["north","south"],bars,color=["#299b83","#c2574f"],width=.6)
    cap.set_ylim(.65,1.17)
    for i,val in enumerate(bars):
        cap.text(i,val+.018,f"{val:.3f}",ha="center",weight="bold")
    cap.set_ylabel("Veff M1 / M0")
    cap.set_title("Polar wall layer, separately")
    cap.legend(loc="upper left",fontsize=9)
    fig.suptitle("P10FT — fresh M1: geometric PASS, adaptation STOP",weight="bold")
    fig.tight_layout()
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=155)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m0",type=Path,required=True)
    p.add_argument("--m1",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--figure",type=Path)
    args=p.parse_args()
    m0,v0,stats0=mesh(args.m0,SHA_M0)
    m1,v1,stats1=mesh(args.m1,SHA_M1)
    stats0["pore_surface"]=pore_surface(args.m0)
    stats1["pore_surface"]=pore_surface(args.m1)
    results={}
    for order in (3,5,7,9):
        print("P10FT_SPATIAL_ORDER",order,"M0",flush=True)
        a=spatial_rule(m0,v0,order)
        print("P10FT_SPATIAL_ORDER",order,"M1",flush=True)
        b=spatial_rule(m1,v1,order)
        results[str(order)]=compare(a,b)
    q7=results["7"]["priority_d_0_100um_abs_mu_ge_0p8"]
    q9=results["9"]["priority_d_0_100um_abs_mu_ge_0p8"]
    stability=max(abs(q7[k]-q9[k]) for k in ("north_ratio","south_ratio","both_ratio"))
    observed_global=(stats1["volume_m3"]/stats1["tet10"])/(stats0["volume_m3"]/stats0["tet10"])
    output={"protocol":"P10FT_FRESH_M0_TO_M1_INDEPENDENT_FIXED_3D_QP",
            "M0_SHA":SHA_M0,"M1_SHA":SHA_M1,
            "M0":stats0,"M1":stats1,
            "realized_global_mean_tet_volume_ratio":observed_global,
            "target_uniform_volume_ratio":.8,
            "global_mean_meets_0p75_0p85":.75<=observed_global<=.85,
            "refinement_samples":results,
            "priority_order9":q9,
            "priority_order7_to9_max_abs_delta":stability,
            "priority_order7_to9_stable_below_0p02":stability<=.02,
            "limit":"Spatial Veff uses QP fractional element count; not a one-to-one element pairing.",
            "geometry_go_issued":False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if args.figure:
        plot_gate(output,args.figure)
    print("P10FT_RESULT",json.dumps({"global_mean_ratio":observed_global,
          "priority":q9,"stability":stability,
          "pore_surface_M0":stats0["pore_surface"],
          "pore_surface_M1":stats1["pore_surface"]},indent=2))


if __name__=="__main__":
    main()
