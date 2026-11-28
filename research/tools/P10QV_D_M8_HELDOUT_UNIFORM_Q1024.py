#!/usr/bin/env python3
"""P10QV-D held-out uniform outer q1024 reference, not exact truth.

Runs on the same two previously frozen real multi cuts. This source
deliberately does not import or inspect the t-panel selection algorithm.
No numerical q1024 values may be used to choose P10QV-D panel breaks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import distribute_nodes,gauss
from P10QV_B_M8_CASE67_MULTI_CRITICAL_PILOT import (
    PILOTS,PIN,CASE_INPUT_SHA,S_BUDGET,projected_events)

Q=1024
OLD_Q512_SHA={
    6:"9b682145eec146bd1be3875810ca7a21927180056636703f6a2f60c97475e705",
    7:"07b1a71ac5e1c5dbd9874a8e68be9dd53f8a70f85e6b1a2f4c9fd84f02ed8cc4"}


def integrate(child:RayChild,axis:int):
    tn,tw=gauss(Q)
    totalg=0.;totalv=0.;points=0;intervals=0;trims=0
    max_high=0.;max_recon=0.
    for i,(t,w) in enumerate(zip(tn,tw),1):
        breaks,info=projected_events(child,axis,float(t))
        allocation=distribute_nodes(breaks,S_BUDGET)
        if sum(allocation)!=S_BUDGET:raise ValueError("P10QV_D_Q1024_S_BUDGET_STOP")
        tg=0.;tv=0.
        for (lo,hi),n in zip(zip(breaks,breaks[1:]),allocation):
            ns,ws=gauss(n)
            for s,sw in zip(ns,ws):
                g,v,_=child.moment_on_ray(axis,lo+(hi-lo)*float(s),float(t),cut=True)
                tg+=(hi-lo)*float(sw)*g
                tv+=(hi-lo)*float(sw)*v
            points+=n
        totalg+=float(w)*tg
        totalv+=float(w)*tv
        intervals+=info["intervals"]
        trims+=info["numerical_degree_trims"]
        max_high=max(max_high,info["max_radial_w3w4"],info["max_azimuth_w2"])
        max_recon=max(max_recon,info["max_recon_radial"],info["max_recon_azimuth"])
        if i%128==0 or i==Q:
            print(f"P10QV_D_Q1024_PROGRESS axis={axis} t={i}/{Q}",flush=True)
    if points!=Q*S_BUDGET or not math.isfinite(totalg) or \
       not 0<=totalv<=child.exact_full_volume*(1+1e-8):
        raise ValueError("P10QV_D_Q1024_BAD_PHYSICAL_OR_COST")
    return {"cut_gradient_m3":totalg,"cut_volume_m3":totalv,
            "transverse_points":points,"outer_t_order":Q,
            "inner_s_budget_per_t":S_BUDGET,
            "critical_s_intervals_total":intervals,
            "numerical_azimuth_degree_trims":trims,
            "maximum_higher_ray_coefficient_rel":max_high,
            "maximum_reconstruction_relative":max_recon}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--case",type=int,choices=[6,7],required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    child_path=a.input_dir/f"P10QO_M8_REAL_CASE{a.case}_H8_CHILDREN_QA.json"
    prior_path=a.input_dir/f"P10QV_C_M8_CASE{a.case}_MULTI_Q256_512_QA.json"
    if hashlib.sha256(child_path.read_bytes()).hexdigest()!=CASE_INPUT_SHA[a.case] or \
       hashlib.sha256(prior_path.read_bytes()).hexdigest()!=OLD_Q512_SHA[a.case]:
        raise ValueError("P10QV_D_Q1024_PINNED_SOURCE_MISMATCH")
    data=json.loads(child_path.read_text())
    if data["mesh_sha256"]!=PIN or data["physical_4D_FEM_approved"]:
        raise ValueError("P10QV_D_Q1024_WRONG_REAL_M8_SOURCE")
    child=RayChild(data["terminals"][PILOTS[a.case]])
    active=[0,4] if a.case==6 else [1,4]
    if child.active!=active:raise ValueError("P10QV_D_Q1024_WRONG_RADIAL_INTERFACE")
    axes={}
    for axis in (0,1,2):
        full=child.integrate(axis,8,cut=False)
        if abs(full["cut_gradient_m3"]-child.exact_full_gradient)>1e-10*max(abs(child.exact_full_gradient),1e-25):
            raise ValueError("P10QV_D_Q1024_FULL_MOMENT_MISMATCH")
        axes[str(axis)]=integrate(child,axis)
    out={"stage":"P10QV_D_HELDOUT_Q1024","case":a.case,
         "pilot_index":PILOTS[a.case],"active_constraints":active,
         "mesh_sha256_from_archived_provenance":PIN,
         "real_child_sha256":CASE_INPUT_SHA[a.case],
         "frozen_uniform_q512_sha256":OLD_Q512_SHA[a.case],
         "no_panel_info_used_in_computation":True,
         "outer_t_nodes":Q,"inner_s_budget_per_t":S_BUDGET,
         "q1024_not_mathematical_exact_solution":True,
         "root_interval_certificate_obtained":False,
         "no_Gmsh_no_mesh_change_no_FEM":True,
         "full_child_gradient_m3":child.exact_full_gradient,
         "full_child_volume_m3":child.exact_full_volume,"axes":axes}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(f"P10QV_D_CASE{a.case}_HELDOUT_Q1024_COMPLETE_NOT_EXACT",flush=True)


if __name__=="__main__":
    main()
