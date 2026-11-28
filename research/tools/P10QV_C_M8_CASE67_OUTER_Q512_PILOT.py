#!/usr/bin/env python3
"""P10QV-C: q256->q512 external-order convergence for two real M8 multi cuts.

Keep the exact P10QV-B geometry, critical-event splitting and 128 inner
Gauss nodes, and increase ONLY the outer order. The prior q256 is frozen
by its SHA. This is an empirical curved P2-FE cut quadrature check, not a
root-interval theorem or permission for physical FEM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import distribute_nodes, gauss
from P10QV_B_M8_CASE67_MULTI_CRITICAL_PILOT import (
    PIN,CASE_INPUT_SHA,PILOTS,S_BUDGET,projected_events)

ORDERS=(256,512)
REF_SHA={
    6:"5153a421c27952e61da0abf05698b0e8efe2648e87166f003a8103fab0fdcc96",
    7:"b6e47fc8b8ed6998505ceb6cf44d373c67ab9e3b0670f4a1e7178ae47cde12c3"}


def integrate_q512(c:RayChild,axis:int):
    if axis not in (0,1,2):raise ValueError("P10QV_C_BAD_AXIS")
    nodes,weights=gauss(512)
    total_g=0.;total_v=0.;points=0;intervals=0;trims=0
    maxrad=0.;maxaz=0.;maxhi=0.;maxtrim=0.
    root_counts={}
    for i,(t,wt) in enumerate(zip(nodes,weights),1):
        breaks,diag=projected_events(c,axis,float(t))
        allocated=distribute_nodes(breaks,S_BUDGET)
        if sum(allocated)!=S_BUDGET:raise ValueError("P10QV_C_FIXED_INNER_BUDGET_BROKEN")
        g=0.;v=0.
        for (lo,hi),n in zip(zip(breaks,breaks[1:]),allocated):
            ns,ws=gauss(n)
            for s,weight in zip(ns,ws):
                rg,rv,_=c.moment_on_ray(axis,lo+(hi-lo)*float(s),float(t),cut=True)
                g+=(hi-lo)*float(weight)*rg
                v+=(hi-lo)*float(weight)*rv
            points+=n
        total_g+=float(wt)*g;total_v+=float(wt)*v
        intervals+=diag["intervals"]
        trims+=diag["numerical_degree_trims"]
        maxrad=max(maxrad,diag["max_recon_radial"])
        maxaz=max(maxaz,diag["max_recon_azimuth"])
        maxhi=max(maxhi,diag["max_radial_w3w4"],diag["max_azimuth_w2"])
        maxtrim=max(maxtrim,diag["max_relative_trim"])
        for key,val in diag["event_roots"].items():
            root_counts[key]=root_counts.get(key,0)+val
        if i%64==0 or i==512:
            print(f"P10QV_C_PROGRESS axis={axis} t={i}/512",flush=True)
    if points!=512*S_BUDGET:raise ValueError("P10QV_C_NOT_EXACT_Q512_COST")
    if not math.isfinite(total_g) or not 0<=total_v<=c.exact_full_volume*(1+1e-8):
        raise ValueError("P10QV_C_NONPHYSICAL_CURVED_VOLUME_OR_GRADIENT")
    return {"cut_gradient_m3":total_g,"cut_volume_m3":total_v,
            "outer_t_order":512,"inner_nodes_per_t":S_BUDGET,
            "transverse_points":points,"critical_s_intervals_total":intervals,
            "azimuth_degree_trims":trims,"maximum_radial_reconstruction_rel":maxrad,
            "maximum_azimuth_reconstruction_rel":maxaz,
            "maximum_higher_ray_coefficient_rel":maxhi,
            "maximum_trimmed_degree_coefficient_rel":maxtrim,
            "critical_root_counts":root_counts}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--case",type=int,choices=[6,7],required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    path=a.input_dir/f"P10QO_M8_REAL_CASE{a.case}_H8_CHILDREN_QA.json"
    prior=a.input_dir/f"P10QV_B_M8_CASE{a.case}_MULTI_Q128_256_QA.json"
    if hashlib.sha256(path.read_bytes()).hexdigest()!=CASE_INPUT_SHA[a.case] or \
       hashlib.sha256(prior.read_bytes()).hexdigest()!=REF_SHA[a.case]:
        raise ValueError("P10QV_C_PINNED_REAL_SOURCE_OR_Q256_REFERENCE_CHANGED")
    child_report=json.loads(path.read_text())
    baseline=json.loads(prior.read_text())
    if child_report["mesh_sha256"]!=PIN or child_report["physical_4D_FEM_approved"] or \
       baseline["mesh_sha256_from_archived_provenance"]!=PIN or \
       baseline["case"]!=a.case or baseline["child_index"]!=PILOTS[a.case] or \
       baseline["outer_orders"]!=[128,256]:
        raise ValueError("P10QV_C_REAL_ARCHIVED_M8_PROVENANCE_FAILED")
    child=RayChild(child_report["terminals"][PILOTS[a.case]])
    active=[0,4] if a.case==6 else [1,4]
    if child.active!=active:
        raise ValueError("P10QV_C_WRONG_OUTER_RADIAL_BOUNDARY")
    normal=max(abs(child.exact_full_gradient),1e-25)
    axes={}
    for axis in (0,1,2):
        baseline_axis=baseline["axes"][str(axis)]
        assert baseline_axis["critical"]["256"]["transverse_points"]==256*S_BUDGET
        # Independent primitive test; not an expensive 512-node smooth re-run.
        full=child.integrate(axis,8,cut=False)
        if abs(full["cut_gradient_m3"]-child.exact_full_gradient)/normal>1e-10:
            raise ValueError("P10QV_C_ANALYTIC_CUBIC_RAY_PRIMITIVE_STOP")
        result=integrate_q512(child,axis)
        reference=baseline_axis["critical"]["256"]
        axes[str(axis)]={"reference_q256":{"cut_gradient_m3":reference["cut_gradient_m3"],
                                          "cut_volume_m3":reference["cut_volume_m3"],
                                          "transverse_points":reference["transverse_points"]},
                        "new_q512":result,
                        "absolute_q256_to_q512_gradient_m3":abs(
                            result["cut_gradient_m3"]-reference["cut_gradient_m3"]),
                        "relative_q256_to_q512_gradient_to_full_child":abs(
                            result["cut_gradient_m3"]-reference["cut_gradient_m3"])/normal,
                        "relative_q256_to_q512_volume_to_full_child":abs(
                            result["cut_volume_m3"]-reference["cut_volume_m3"])/child.exact_full_volume}
    pair={}
    for i,j in ((0,1),(0,2),(1,2)):
        a0=axes[str(i)]["new_q512"];b0=axes[str(j)]["new_q512"]
        pair[f"{i}_{j}"]={
            "q512_gradient_absolute_m3":abs(a0["cut_gradient_m3"]-b0["cut_gradient_m3"]),
            "q512_gradient_relative_to_full_child":abs(
                a0["cut_gradient_m3"]-b0["cut_gradient_m3"])/normal,
            "q512_volume_relative_to_full_child":abs(
                a0["cut_volume_m3"]-b0["cut_volume_m3"])/child.exact_full_volume}
    out={"stage":"P10QV_C_Q512_PILOT","case":a.case,"original_element":5751 if a.case==6 else 5847,
         "pilot_index":PILOTS[a.case],"active_constraints":active,
         "mesh_sha256_from_archived_provenance":PIN,
         "source_child_sha256":CASE_INPUT_SHA[a.case],
         "previous_q256_sha256":REF_SHA[a.case],
         "fixed_inner_budget":S_BUDGET,"t_orders":[256,512],
         "all_178_cut_tested":False,"root_interval_certificate_obtained":False,
         "no_Gmsh_no_mesh_change_no_FEM":True,
         "full_original_child_gradient_m3":child.exact_full_gradient,
         "full_original_child_volume_m3":child.exact_full_volume,
         "axes":axes,"pairwise":pair,
         "max_axis_pair_q512_relative_to_full_child":max(
             v["q512_gradient_relative_to_full_child"] for v in pair.values()),
         "max_order_q256_to_q512_relative_to_full_child":max(
             v["relative_q256_to_q512_gradient_to_full_child"] for v in axes.values())}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(f"P10QV_C_CASE{a.case}_Q512_COMPLETE_NOT_FEM_OR_CERTIFICATE",flush=True)


if __name__=="__main__":
    main()
