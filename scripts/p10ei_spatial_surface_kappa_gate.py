#!/usr/bin/env python3
"""P10EI: read-only matched angular-bin Tri6 comparison of original M1/M2/B.

This is a surface diagnostic and a pre-3D gate design, not a 3D volume QA.
No Gmsh, FEM, one-shot markers or raw-mesh publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np

import p10ed_verify_original_m1_m2_raw_spatial as raw
from p10ee_audit_pore_surface_sizing_source_only import tri_basis, surface_areas
from p10eh_audit_candidate_surface import EXPECTED_MSH, MESH_NAME, parse_pore, kappa, CENTRE


MU_EDGES = np.array([-1., -.8, -.6, 0., .6, .8, 1.])
PHI_EDGES = np.linspace(-math.pi, math.pi, 5)


def grid_stats(tris: np.ndarray, order: int):
    n, d, w = tri_basis(order)
    triangle_area, jac, qp = surface_areas(tris, n, d, w)
    if not np.all(jac > 0):
        raise ValueError("P10EI_STOP: nonpositive Tri6 surface Jacobian")
    diff = qp-CENTRE
    r = np.linalg.norm(diff, axis=-1)
    mu = np.clip(diff[..., 2]/r, -1., 1.)
    phi = np.arctan2(diff[..., 1], diff[..., 0])
    weight = jac*w[None, :]
    frac = weight / triangle_area[:, None]
    kp = kappa(qp)
    bins = {}
    for a in range(len(MU_EDGES)-1):
        for b in range(len(PHI_EDGES)-1):
            sel = (mu >= MU_EDGES[a]) & (mu < MU_EDGES[a+1] if a < len(MU_EDGES)-2 else mu <= MU_EDGES[a+1])
            sel &= (phi >= PHI_EDGES[b]) & (phi < PHI_EDGES[b+1] if b < len(PHI_EDGES)-2 else phi <= PHI_EDGES[b+1])
            area = float(weight[sel].sum())
            count = float(frac[sel].sum())
            expected_area = 1e-6 * (MU_EDGES[a+1]-MU_EDGES[a]) * (PHI_EDGES[b+1]-PHI_EDGES[b])
            if count <= 0:
                raise ValueError("P10EI_STOP: empty angular bin")
            bins[f"mu{a}_phi{b}"] = {
                "mu_limits": [float(MU_EDGES[a]), float(MU_EDGES[a+1])],
                "phi_limits_rad": [float(PHI_EDGES[b]), float(PHI_EDGES[b+1])],
                "curved_area_m2": area,
                "analytic_area_m2": float(expected_area),
                "curved_area_relative_error": area/expected_area-1,
                "effective_tri6_count": count,
                "effective_area_m2": area/count,
                "mean_kappa": float((weight[sel]*kp[sel]).sum()/area),
                "target_area_ratio_mean": float((weight[sel]*(1-.2*kp[sel])**(2/3)).sum()/area),
            }
    if abs(sum(x["effective_tri6_count"] for x in bins.values())-len(tris)) > 1.e-8:
        raise ValueError("P10EI_STOP: angular effective count partition")
    if abs(sum(x["curved_area_m2"] for x in bins.values())-float(triangle_area.sum())) > 1.e-15:
        raise ValueError("P10EI_STOP: angular curved area partition")
    return bins


def compare(m1, m2, b):
    result={}
    for name, x in m1.items():
        y,z=m2[name],b[name]
        ratio=z["effective_area_m2"]/x["effective_area_m2"]
        target=z["target_area_ratio_mean"]
        result[name]={
           "mu_limits":z["mu_limits"],"phi_limits_rad":z["phi_limits_rad"],
           "m1_effective_count":x["effective_tri6_count"],
           "m2_effective_count":y["effective_tri6_count"],
           "candidate_effective_count":z["effective_tri6_count"],
           "candidate_mean_kappa":z["mean_kappa"],
           "nominal_area_ratio":target,
           "candidate_over_m1_area_ratio":ratio,
           "historical_m2_over_m1_area_ratio":y["effective_area_m2"]/x["effective_area_m2"],
           "deviation_from_target":ratio-target,
           "relative_deviation_from_target":ratio/target-1,
           "candidate_zone_analytic_area_error":z["curved_area_relative_error"],
        }
    return result


def summarize(comp):
    all_rows=list(comp.values())
    eligible=[v for v in all_rows if min(v["m1_effective_count"],v["candidate_effective_count"]) >= 2]
    weight=np.array([v["candidate_effective_count"] for v in eligible])
    deviations=np.array([v["relative_deviation_from_target"] for v in eligible])
    return {
        "total_bins":len(all_rows),
        "eligible_bins_min_effective_count_2":len(eligible),
        "eligible_max_abs_relative_deviation":float(np.max(np.abs(deviations))),
        "eligible_weighted_rms_relative_deviation":float(np.sqrt(np.average(deviations**2,weights=weight))),
        "eligible_weighted_signed_mean_relative_deviation":float(np.average(deviations,weights=weight)),
        "under_target_count":sum(v["deviation_from_target"] < 0 for v in eligible),
        "over_target_count":sum(v["deviation_from_target"] >= 0 for v in eligible),
        "worst_bin":max(eligible,key=lambda v:abs(v["relative_deviation_from_target"])),
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--m1",required=True,type=Path)
    p.add_argument("--m2",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    with zipfile.ZipFile(args.evidence) as z:
        if z.testzip() is not None:raise ValueError("P10EI_STOP: corrupt evidence")
        content=z.read(MESH_NAME)
    if hashlib.sha256(content).hexdigest()!=EXPECTED_MSH:raise ValueError("P10EI_STOP: wrong surface SHA")
    candidate,_,_=parse_pore(content)
    m1=raw.parse_msh2(args.m1,raw.M1_SHA)
    m2=raw.parse_msh2(args.m2,raw.M2_SHA)
    result={"protocol":"P10EI_MATCHED_MU_PHI_SURFACE_ONLY","gmsh_runs":0,"fem_runs":0,
            "candidate_sha256":EXPECTED_MSH,"m1_sha256":raw.M1_SHA,"m2_sha256":raw.M2_SHA,
            "mu_edges":MU_EDGES.tolist(),"phi_edges_rad":PHI_EDGES.tolist(),"qp_orders":{}}
    for order in (5,9,15,25,35):
        x=grid_stats(m1["nodes"][m1["pore_tri6"]],order)
        y=grid_stats(m2["nodes"][m2["pore_tri6"]],order)
        z=grid_stats(candidate,order)
        comp=compare(x,y,z)
        result["qp_orders"][str(order)]={"matched_bins":comp,"summary":summarize(comp)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10EI_MATCHED_TRI6_QP_OK",json.dumps(result["qp_orders"]["15"]["summary"],ensure_ascii=False))


if __name__=="__main__":
    main()
