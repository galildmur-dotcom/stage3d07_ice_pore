#!/usr/bin/env python3
"""P10CR: SHA-gated offline geometry-only centroid-vs-QP support audit.

No mesh source reading, no FEM/Gmsh, no synthetic correction of shape derivatives.
Analyzes P10CI straight-corner-centroid volumes versus P10BA physical 27QP
cell volumes at t=900s, plus signed P10CM differences as descriptive controls.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT = Path(__file__).resolve().parent
EXPECTED_SHA = {
    "P10CI_EVIDENCE_READONLY_20261120/P10CI_200CELL_MESH_GEOMETRY.csv": "db22675c116b1d151e86c73726cc4e2aeba21bcb4c41c099ee4e5d2e4d3e9f61",
    "stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input/H4W4B2_P10BA_QP_POLAR_RADIAL.csv": "219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447",
    "stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input/H4W4B20_P10BA_QP_POLAR_RADIAL.csv": "3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be",
    "stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input/H4W5B2_P10BA_QP_POLAR_RADIAL.csv": "8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c",
    "P10CM_200CELL_MULTISCALE_M1_PROPOSAL.csv": "428a1d3b1d7b84e10a6c44762f0222c831a5f917283c872e06eaa11eff0781eb",
    "P10CQ_INDEPENDENT_P10CP_B6_AUDIT.json": "33ed65373f828475ff0a964f17273845faefb20a2346039ead352b151ba6961a",
}
MESHES = ("H4W4B2", "H4W4B20", "H4W5B2")
PAIRS = (("H4W4B20", "bulk", "delta_bulk_per_m"), ("H4W5B2", "wall", "delta_wall_per_m"))
COARSEN = (1, 2, 4, 5, 10, 20)


def source_path(name: str) -> Path:
    path = ROOT / name
    if path.is_file():
        return path
    # Reproducer also runs from a published research-branch checkout root.
    p = Path.cwd() / name
    if p.is_file():
        return p
    if name.startswith("P10CI_EVIDENCE_READONLY_20261120/"):
        q = Path.cwd() / "research/evidence/P10CI_WINDOWS_GEOMETRY_20261120/input" / Path(name).name
        if q.is_file():
            return q
    if name.startswith("stage3d07_readonly/"):
        q = Path.cwd() / name.removeprefix("stage3d07_readonly/")
        if q.is_file():
            return q
    if name.startswith("P10CM_"):
        q = Path.cwd() / "research/evidence/P10CM_OFFLINE_20261120/derived" / Path(name).name
        if q.is_file():
            return q
    if name.startswith("P10CQ_"):
        q = Path.cwd() / "research/evidence/P10CQ_INDEPENDENT_B6_ANALYSIS_20261121/derived" / Path(name).name
        if q.is_file():
            return q
    raise FileNotFoundError("required exact source missing: " + name)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def csv_read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def rank(x):
    x = np.asarray(x,float)
    order = np.argsort(x,kind="mergesort")
    y = np.empty(len(x),float)
    j=0
    while j<len(x):
        k=j+1
        while k<len(x) and x[order[k]]==x[order[j]]:
            k+=1
        y[order[j:k]] = (j + k - 1)/2.0
        j=k
    return y


def spearman(a,b):
    x,y = rank(a),rank(b)
    return float(np.corrcoef(x,y)[0,1]) if np.std(x)>0 and np.std(y)>0 else None


def within_polar_rank(a,b):
    xa=[];ya=[]
    for band in range(10):
        sel=np.array([i%10==band for i in range(len(a))])
        xa.extend(rank(np.array(a)[sel])/19.0)
        ya.extend(rank(np.array(b)[sel])/19.0)
    return float(np.corrcoef(xa,ya)[0,1])


def ratio_distribution(v):
    v=np.asarray(v,float)
    if np.any(v<=0) or not np.isfinite(v).all():
        raise ValueError("nonpositive or nonfinite cell volume")
    return v/v.sum()


def total_variation(a,b):
    return float(0.5*np.abs(a-b).sum())


def grouped_tv(a,b,ngroup):
    if 20%ngroup:
        raise ValueError("radial groups must evenly partition 20 bins")
    step=20//ngroup
    aa=np.zeros((ngroup,10));bb=np.zeros_like(aa)
    for ri in range(20):
        for mu in range(10):
            aa[ri//step,mu]+=a[ri*10+mu]
            bb[ri//step,mu]+=b[ri*10+mu]
    return total_variation(aa,bb)


def volume_predictor(signal,v0,v1):
    pred=signal*(v1/v0-1)
    return pred


def predictor_diagnostics(actual,pred):
    return {
        "pearson": float(np.corrcoef(actual,pred)[0,1]),
        "uncentered_r2":float(1-np.dot(actual-pred,actual-pred)/np.dot(actual,actual)),
        "prediction_L1_over_actual_L1":float(np.abs(pred).sum()/np.abs(actual).sum()),
    }


def get_table(raw,fields):
    dest={}
    for r in raw:
        key=(int(r[fields[0]]),int(r[fields[1]]))
        if key in dest:
            raise ValueError("duplicate primary cell "+str(key))
        dest[key]=r
    if set(dest)!={(i,j) for i in range(20) for j in range(10)}:
        raise ValueError("not complete (radial,mu) source 200-cell grid")
    return dest


def main():
    blobs={}
    paths={}
    for name, expected in EXPECTED_SHA.items():
        p=source_path(name)
        got=p.read_bytes()
        if sha256(got)!=expected:
            raise ValueError("pinned SHA mismatch: "+name)
        blobs[name]=got
        paths[name]=p
    ci=csv_read(paths["P10CI_EVIDENCE_READONLY_20261120/P10CI_200CELL_MESH_GEOMETRY.csv"])
    if len(ci)!=600:
        raise ValueError("P10CI geometry != 600 rows")
    ci_data={}
    for mesh in MESHES:
        ci_data[mesh]=get_table([r for r in ci if r["mesh"]==mesh],("radial_bin","polar_band"))
    primary={}
    baseline_radial_lowers=None
    for mesh in MESHES:
        name="stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input/"+mesh+"_P10BA_QP_POLAR_RADIAL.csv"
        data=csv_read(paths[name])
        data=[r for r in data if int(r["time_step"])==6 and float(r["time_s"])==900.]
        if len(data)!=200:
            raise ValueError("expected 200 t900 raw QP bins on "+mesh)
        # P10BA 'radial_subbin' restarts at 0 inside each of TWO shells.
        # The globally unique radial index comes from radial_lower_mm.
        lowers=sorted({round(float(r["radial_lower_mm"]),12) for r in data})
        if len(lowers)!=20 or (baseline_radial_lowers is not None and lowers!=baseline_radial_lowers):
            raise ValueError("P10BA radial shell index mismatch")
        baseline_radial_lowers=lowers
        index={v:i for i,v in enumerate(lowers)}
        part={}
        for row in data:
            key=(index[round(float(row["radial_lower_mm"]),12)],int(row["polar_band"]))
            if key in part:
                raise ValueError("duplicate P10BA bin "+mesh+" "+str(key))
            part[key]=row
        if set(part)!={(i,j) for i in range(20) for j in range(10)}:
            raise ValueError("P10BA 20×10 coverage mismatch")
        primary[mesh]=part
    cm_rows=csv_read(paths["P10CM_200CELL_MULTISCALE_M1_PROPOSAL.csv"])
    cm=get_table(cm_rows,("radial_bin","polar_band"))
    if len(cm_rows)!=200:
        raise ValueError("P10CM 200 rows missing")
    far=json.loads(blobs["P10CQ_INDEPENDENT_P10CP_B6_AUDIT.json"])
    if far["status"]!="P10CQ_INDEPENDENT_P10CP_EVIDENCE_AUDIT_OK_NO_FEM":
        raise ValueError("P10CQ source status mismatch")
    keys=sorted(cm)
    assert keys==sorted(ci_data["H4W4B2"])
    radial_bounds=[]
    for ri in range(20):
        rows=[primary["H4W4B2"][(ri,mu)] for mu in range(10)]
        lowers={round(float(x["radial_lower_mm"]),12) for x in rows}
        uppers={round(float(x["radial_upper_mm"]),12) for x in rows}
        if len(lowers)!=1 or len(uppers)!=1:
            raise ValueError("unstable radial boundaries within mu band")
        radial_bounds.append((next(iter(lowers)),next(iter(uppers))))
    if abs(radial_bounds[0][0]-.02)>1e-12 or abs(radial_bounds[-1][1]-.1)>1e-12:
        raise ValueError("radial support is not 20–100um")
    for ri in range(19):
        if abs(radial_bounds[ri][1]-radial_bounds[ri+1][0])>1e-12:
            raise ValueError("radial bin discontinuity")
    data={}
    for mesh in MESHES:
        corner=np.array([float(ci_data[mesh][k]["corner_volume_proxy_m3"]) for k in keys])
        qp=np.array([float(primary[mesh][k]["qp_volume_m3"]) for k in keys])
        tet=np.array([int(ci_data[mesh][k]["tet10_centroids"]) for k in keys])
        qpc=np.array([int(primary[mesh][k]["qp_count"]) for k in keys])
        crossing=np.array([int(ci_data[mesh][k]["radial_cross_centroid_tets"]) for k in keys])
        polar_cross=np.array([int(ci_data[mesh][k]["polar_cross_centroid_tets"]) for k in keys])
        if np.any(tet<=0) or np.any(qpc<=0) or not np.array_equal(crossing,tet):
            raise ValueError("P10CI n/tetra crossing gate failed")
        if np.any(np.abs(qp)<=0) or np.any(np.abs(corner)<=0):
            raise ValueError("empty source cell")
        # Both are positive partitions of the *same nominal shell*, but use
        # different assignment rules (QP vs straight-corner centroid).
        p,q=ratio_distribution(qp),ratio_distribution(corner)
        scale={str(i):grouped_tv(p,q,i) for i in COARSEN}
        if any(scale[str(a)]>scale[str(b)]+1e-12 for a in COARSEN for b in COARSEN if b>a and b%a==0):
            raise AssertionError("total-variation data-processing monotonicity violated for nested partitions")
        polar=np.array([k[1] in (0,9) for k in keys])
        discrep=np.abs(p-q)
        by_radial=[sum(discrep[j] for j,k in enumerate(keys) if k[0]==i) for i in range(20)]
        by_mu=[sum(discrep[j] for j,k in enumerate(keys) if k[1]==i) for i in range(10)]
        data[mesh]={
            "corner":corner,"qp":qp,"pcorner":q,"pqp":p,"tet":tet,"qpc":qpc,
            "discrep":discrep,"cross":crossing,"polar_cross":polar_cross,
            "tv_by_ngroups":scale,
            "summary":{
                "original_tet10_centroids_20_100um":int(tet.sum()),
                "p10ba_QP_count_20_100um":int(qpc.sum()),
                "qp_corner_total_volume_ratio":float(qp.sum()/corner.sum()),
                "normalized_QP_vs_centroid_TV_200cells":total_variation(p,q),
                "normalized_QP_vs_centroid_TV_20cells":scale["2"],
                "normalized_QP_vs_centroid_TV_10cells":scale["1"],
                "cell_level_QP_over_corner_volume_ratio_p05_p50_p95":np.percentile(qp/corner,[5,50,95]).tolist(),
                "polar_share_of_QP_vs_centroid_L1":float(discrep[polar].sum()/discrep.sum()),
                "polar_volume_share_QP":float(p[polar].sum()),
                "polar_volume_share_corner_centroid":float(q[polar].sum()),
                "polar_cross_corner_fraction":float(polar_cross[polar].sum()/tet[polar].sum()),
                "middle_cross_corner_fraction":float(polar_cross[~polar].sum()/tet[~polar].sum()),
                "centroid_radial_cross_fraction_20_100um":float(crossing.sum()/tet.sum()),
                "centroid_radial_cross_fraction_100um_5mm":float(far["by_mesh"][mesh]["cross_radial_fraction"]),
                "azimuth_or_physical_phi_derivative_available":False,
            },
            "radial_mismatch_L1":by_radial,"mu_mismatch_L1":by_mu,
        }
    baseline=primary["H4W4B2"]
    delta_metrics={}
    for alt,label,cm_field in PAIRS:
        src=primary[alt]
        current=np.array([float(src[k]["total_mechanical_per_m"]) for k in keys])
        reference=np.array([float(baseline[k]["total_mechanical_per_m"]) for k in keys])
        delta=current-reference
        declared=np.array([float(cm[k][cm_field]) for k in keys])
        if not np.allclose(delta,declared,atol=2e-13,rtol=1e-10):
            raise AssertionError("signed P10CM differences not matched by primary P10BA "+label)
        pred_qp=volume_predictor(reference,data["H4W4B2"]["qp"],data[alt]["qp"])
        pred_corner=volume_predictor(reference,data["H4W4B2"]["corner"],data[alt]["corner"])
        # Correlate absolute signed spatial discrepancy with absolute SOURCE-ASSIGNMENT
        # difference only descriptively; polar location is a known confounder.
        support_diff=np.abs(data["H4W4B2"]["pqp"]-data["H4W4B2"]["pcorner"])
        delta_metrics[label]={
            "comparison":alt+"-H4W4B2",
            "sum_abs_signed_cell_delta_per_m":float(np.abs(delta).sum()),
            "polar_fraction_L1_delta":float(np.abs(delta[[k[1] in (0,9) for k in keys]]).sum()/np.abs(delta).sum()),
            "volume_only_diagnostic_using_QP_cell_volumes":predictor_diagnostics(delta,pred_qp),
            "volume_only_diagnostic_using_corner_centroid_cell_volumes":predictor_diagnostics(delta,pred_corner),
            "spearman_abs_delta_vs_abs_QP_corner_share_gap":spearman(abs(delta),support_diff),
            "within_mu_rank_corr_abs_delta_vs_abs_QP_corner_share_gap":within_polar_rank(abs(delta),support_diff),
        }
    result={
        "status":"P10CR_OFFLINE_SUPPORT_BINNING_AUDIT_OK_NO_FEM",
        "sources_sha256":EXPECTED_SHA,
        "definition":"20–100um only t900 mechanical P10BA; P10CI straight-corner centroid volumes vs P10BA per-QP shell volumes. Normalize before TV, not error estimator.",
        "per_mesh":{mesh:{**data[mesh]["summary"],"TV_vs_radial_groups":data[mesh]["tv_by_ngroups"],
                          "per_radial_normalized_share_L1_gap":data[mesh]["radial_mismatch_L1"],
                          "per_mu_normalized_share_L1_gap":data[mesh]["mu_mismatch_L1"]} for mesh in MESHES},
        "signed_mechanical_crosscheck":delta_metrics,
        "limitations":{
            "targeted_true_shape_gradient_error":"NOT_IDENTIFIABLE_FROM_AGGREGATED_DATA",
            "centroid_assignment_causal_role":"NOT_IDENTIFIABLE_WITHOUT_ELEMENT_LEVEL_QP_AND_GRADIENT",
            "QP_vs_corner_gap_may_include_curved_geometry":"YES",
            "t900_20_100um_not_all_B6":"YES",
            "thermal_phi_time_physical_distribution":"NOT_AVAILABLE",
            "new_Gmsh_or_FEM":0,
        }
    }
    output=ROOT/"P10CR_OFFLINE_SUPPORT_BINNING_AUDIT.json"
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    plt.rcParams.update({"font.size":9,"figure.dpi":130,"savefig.dpi":170})
    fig,ax=plt.subplots(2,2,figsize=(12.7,8.8),layout="constrained")
    y=np.array([k[0] for k in keys]);m=np.array([k[1] for k in keys])
    q=data["H4W4B2"]["pqp"];c=data["H4W4B2"]["pcorner"]
    h=np.full((10,20),np.nan)
    for j,k in enumerate(keys):
        h[k[1],k[0]]=q[j]/c[j]-1
    upper=float(np.quantile(np.abs(h),.95))
    vlim=max(.5,min(2.5,upper))
    radial_edges=[radial_bounds[0][0]]+[bounds[1] for bounds in radial_bounds]
    mu_edges=np.linspace(-1,1,11)
    im=ax[0,0].pcolormesh(radial_edges,mu_edges,h,shading="flat",cmap="RdBu_r",norm=TwoSlopeNorm(vcenter=0,vmin=-vlim,vmax=vlim))
    ax[0,0].set_title("H4W4B2: (доля QP / доля по центрам) − 1")
    ax[0,0].set_xlabel("d=r−R, мм, 20 неравных интервалов");ax[0,0].set_ylabel("μ=cosθ")
    fig.colorbar(im,ax=ax[0,0],label="различие относительного объёма",extend="both")
    col={"H4W4B2":"#1f77b4","H4W4B20":"#dc7817","H4W5B2":"#23815d"}
    for mesh in MESHES:
        vals=[data[mesh]["tv_by_ngroups"][str(i)] for i in COARSEN]
        ax[0,1].plot(COARSEN,vals,"-o",label=mesh,c=col[mesh],ms=5)
    ax[0,1].set_xlabel("число радиальных групп (×10 μ-полос)")
    ax[0,1].set_ylabel("TV нормированных QP и centroid объёмов")
    ax[0,1].set_title("Изменение расхождения при укрупнении разбиения")
    ax[0,1].set_xticks(COARSEN);ax[0,1].legend(fontsize=8)
    comps=list(delta_metrics)
    x=np.arange(len(comps));w=.32
    vals_qp=[delta_metrics[c]["volume_only_diagnostic_using_QP_cell_volumes"]["uncentered_r2"] for c in comps]
    vals_corner=[delta_metrics[c]["volume_only_diagnostic_using_corner_centroid_cell_volumes"]["uncentered_r2"] for c in comps]
    bars_qp=ax[1,0].bar(x-w/2,vals_qp,w,label="объём ячейки по QP",color="#1f77b4")
    bars_c=ax[1,0].bar(x+w/2,vals_corner,w,label="объём элементов по центроидам",color="#dc7817")
    ax[1,0].set_xticks(x,["W4B20–W4B2, bulk","W5B2–W4B2, wall"])
    ax[1,0].set_ylabel("1−Σ(Δ−ΔVpred)² / ΣΔ²")
    ax[1,0].set_title("Только диагностический модельный прогноз Δ по объёмам")
    ax[1,0].axhline(0,color="black",linewidth=.7)
    ax[1,0].set_yscale("symlog",linthresh=1)
    for bar,value in zip(list(bars_qp)+list(bars_c),vals_qp+vals_corner):
        ax[1,0].annotate(f"{value:.2f}",(bar.get_x()+bar.get_width()/2,value),xytext=(0,4 if value>=0 else -10),textcoords="offset points",ha="center",fontsize=8)
    ax[1,0].legend(fontsize=8)
    x=np.arange(len(MESHES));width=.34
    near=[data[m]["summary"]["centroid_radial_cross_fraction_20_100um"] for m in MESHES]
    farvals=[data[m]["summary"]["centroid_radial_cross_fraction_100um_5mm"] for m in MESHES]
    ax[1,1].bar(x-width/2,near,width,label="20–100 мкм, 3–5 мкм bins",color="#1f77b4")
    ax[1,1].bar(x+width/2,farvals,width,label="100 мкм – 5 мм, 24 log bins",color="#23815d")
    ax[1,1].set_xticks(x,MESHES);ax[1,1].set_ylim(0,1.08)
    ax[1,1].set_ylabel("доля угловых Tet10, пересекающих границу d-bin")
    ax[1,1].set_title("Ширина ячейки меньше размера многих элементов")
    ax[1,1].legend(fontsize=8)
    fig.suptitle("Stage3D07 P10CR: различие поддержки QP и центроидных ячеек, НЕ истинная ошибка",fontsize=12)
    img=ROOT/"P10CR_CENTROID_VS_QP_BINNING_AND_POLAR_COMPARISON.png"
    fig.savefig(img,bbox_inches="tight")
    plt.close(fig)
    print("RESULT="+result["status"])
    for mesh in MESHES:
        s=data[mesh]["summary"]
        print(mesh,"TV20="+str(round(s["normalized_QP_vs_centroid_TV_200cells"],6)),"TV2="+str(round(s["normalized_QP_vs_centroid_TV_20cells"],6)),"TV1="+str(round(s["normalized_QP_vs_centroid_TV_10cells"],6)),"QP/CORNER_TOTAL="+str(round(s["qp_corner_total_volume_ratio"],6)),"POLAR_SHARE_GAP="+str(round(s["polar_share_of_QP_vs_centroid_L1"],6)))
    for k,d in delta_metrics.items():
        print(k,"R2_QP="+str(round(d["volume_only_diagnostic_using_QP_cell_volumes"]["uncentered_r2"],6)),"R2_CENTROID="+str(round(d["volume_only_diagnostic_using_corner_centroid_cell_volumes"]["uncentered_r2"],6)),"SPEARMAN="+str(round(d["spearman_abs_delta_vs_abs_QP_corner_share_gap"],6)),"WITHIN_MU="+str(round(d["within_mu_rank_corr_abs_delta_vs_abs_QP_corner_share_gap"],6)))
    print("JSON_SHA256="+sha256(output.read_bytes()))
    print("PNG_SHA256="+sha256(img.read_bytes()))


if __name__=="__main__":
    main()
