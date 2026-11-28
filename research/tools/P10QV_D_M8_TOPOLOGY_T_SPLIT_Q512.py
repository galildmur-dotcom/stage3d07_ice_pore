#!/usr/bin/env python3
"""P10QV-D: topology-probed t panel quadrature at unchanged q512 cost.

Before any numerical q1024 comparison, freeze a pilot outer-t partition
from physical two-constraint root signatures at 41 uniformly fixed t probes
and five fixed s probes. Gauss nodes are then allocated by panel length
with a fixed 512 outer-node budget and 128 inner critical-s nodes.
This probe-based partition is EMPIRICAL, not exact critical-t projection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QQ_M8_ROOT_TOPOLOGY_ADAPTIVE_TRANSVERSE import root_topology
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import distribute_nodes,gauss
from P10QV_B_M8_CASE67_MULTI_CRITICAL_PILOT import (
    PILOTS,PIN,CASE_INPUT_SHA,S_BUDGET,projected_events)

OLD_Q512_SHA={
    6:"9b682145eec146bd1be3875810ca7a21927180056636703f6a2f60c97475e705",
    7:"07b1a71ac5e1c5dbd9874a8e68be9dd53f8a70f85e6b1a2f4c9fd84f02ed8cc4"}
T_PROBES=tuple(.005+.99*i/40 for i in range(41))
S_PROBES=(.1,.3,.5,.7,.9)
OUTER_BUDGET=512


def geometry_panels(child:RayChild,axis:int):
    signatures=[]
    for t in T_PROBES:
        signatures.append(tuple(root_topology(child,axis,s,float(t))
                                for s in S_PROBES))
    transitions=[]
    for i in range(1,len(T_PROBES)):
        if signatures[i]!=signatures[i-1]:
            transitions.append((T_PROBES[i-1],T_PROBES[i]))
    breaks=[0.]+[(a+b)*.5 for a,b in transitions]+[1.]
    if len(breaks)>17:
        raise ValueError("P10QV_D_TOO_MANY_T_PANELS_FROM_PHYSICAL_TOPOLOGY")
    allocations=distribute_nodes(breaks,OUTER_BUDGET)
    if sum(allocations)!=OUTER_BUDGET or min(allocations)<8:
        raise ValueError("P10QV_D_FIXED_512_T_BUDGET_VIOLATED")
    return breaks,allocations,transitions,len(set(signatures))


def integrate_with_panels(child:RayChild,axis:int):
    breaks,counts,transitions,unique=geometry_panels(child,axis)
    totalg=0.;totalv=0.;points=0;outer=0
    s_segments=0;trims=0;maximum_high=0.;maximum_recon=0.
    for (lo,hi),t_count in zip(zip(breaks,breaks[1:]),counts):
        tn,tw=gauss(t_count)
        for t,w_t in zip(tn,tw):
            physical_t=lo+(hi-lo)*float(t)
            br,diag=projected_events(child,axis,physical_t)
            inner=distribute_nodes(br,S_BUDGET)
            if sum(inner)!=S_BUDGET:
                raise ValueError("P10QV_D_INNER_S_BUDGET_CHANGED")
            tg=0.;tv=0.
            for (slo,shi),sn in zip(zip(br,br[1:]),inner):
                nodes,weights=gauss(sn)
                for s,sw in zip(nodes,weights):
                    g,v,_=child.moment_on_ray(
                        axis,slo+(shi-slo)*float(s),physical_t,cut=True)
                    tg+=(shi-slo)*float(sw)*g
                    tv+=(shi-slo)*float(sw)*v
                points+=sn
            totalg+=(hi-lo)*float(w_t)*tg
            totalv+=(hi-lo)*float(w_t)*tv
            outer+=1
            s_segments+=diag["intervals"]
            trims+=diag["numerical_degree_trims"]
            maximum_high=max(maximum_high,diag["max_radial_w3w4"],diag["max_azimuth_w2"])
            maximum_recon=max(maximum_recon,diag["max_recon_radial"],diag["max_recon_azimuth"])
            if outer%64==0 or outer==OUTER_BUDGET:
                print(f"P10QV_D_PROGRESS axis={axis} outer={outer}/{OUTER_BUDGET} "
                      f"t_panels={len(breaks)-1}",flush=True)
    if points!=OUTER_BUDGET*S_BUDGET or \
       not math.isfinite(totalg) or \
       not 0<=totalv<=child.exact_full_volume*(1+1e-8):
        raise ValueError("P10QV_D_INVALID_EQUAL_COST_OR_PHYSICAL_CUT_RESULT")
    return {"cut_gradient_m3":totalg,"cut_volume_m3":totalv,
            "outer_t_nodes":OUTER_BUDGET,"inner_s_nodes_per_t":S_BUDGET,
            "transverse_points":points,
            "outer_t_panel_breaks":breaks,"outer_t_panel_nodes":counts,
            "topology_transition_t_brackets":[[a,b] for a,b in transitions],
            "distinct_probe_signatures":unique,
            "s_critical_intervals_total":s_segments,
            "numerical_azimuth_degree_trims":trims,
            "maximum_higher_ray_coefficient_relative":maximum_high,
            "maximum_physical_reconstruction_relative":maximum_recon}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--case",type=int,choices=[6,7],required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    child_path=a.input_dir/f"P10QO_M8_REAL_CASE{a.case}_H8_CHILDREN_QA.json"
    q512_path=a.input_dir/f"P10QV_C_M8_CASE{a.case}_MULTI_Q256_512_QA.json"
    if hashlib.sha256(child_path.read_bytes()).hexdigest()!=CASE_INPUT_SHA[a.case] or \
       hashlib.sha256(q512_path.read_bytes()).hexdigest()!=OLD_Q512_SHA[a.case]:
        raise ValueError("P10QV_D_PINNED_SOURCE_OR_FROZEN_Q512_CHANGED")
    src=json.loads(child_path.read_text())
    old=json.loads(q512_path.read_text())
    if src["mesh_sha256"]!=PIN or src["physical_4D_FEM_approved"] or \
       old["case"]!=a.case or old["pilot_index"]!=PILOTS[a.case] or \
       old["mesh_sha256_from_archived_provenance"]!=PIN:
        raise ValueError("P10QV_D_WRONG_REAL_M8_GEOMETRY")
    child=RayChild(src["terminals"][PILOTS[a.case]])
    radial=[0,4] if a.case==6 else [1,4]
    if child.active!=radial:raise ValueError("P10QV_D_WRONG_RADIAL_INTERFACE")
    axes={}
    for axis in (0,1,2):
        result=integrate_with_panels(child,axis)
        uniform=old["axes"][str(axis)]["new_q512"]
        if uniform["transverse_points"]!=result["transverse_points"]:
            raise ValueError("P10QV_D_COST_NOT_EQUAL_TO_UNIFORM_Q512")
        axes[str(axis)]={"segmented_q512":result,
                        "frozen_uniform_q512_gradient_m3":uniform["cut_gradient_m3"],
                        "frozen_uniform_q512_volume_m3":uniform["cut_volume_m3"]}
    out={"stage":"P10QV_D_EQUAL_COST_T_TOPOLOGY_PILOT",
         "case":a.case,"pilot_index":PILOTS[a.case],"active_constraints":radial,
         "mesh_sha256_from_archived_provenance":PIN,
         "archived_real_child_sha256":CASE_INPUT_SHA[a.case],
         "frozen_uniform_q512_sha256":OLD_Q512_SHA[a.case],
         "t_probe_count":len(T_PROBES),"s_probes":list(S_PROBES),
         "outer_t_budget":OUTER_BUDGET,"inner_s_budget":S_BUDGET,
         "t_breaks_chosen_without_q1024_or_integral_values":True,
         "root_interval_certificate_obtained":False,
         "physical_4D_FEM_approved":False,
         "no_Gmsh_no_mesh_change_no_FEM":True,
         "full_child_gradient_m3":child.exact_full_gradient,
         "full_child_volume_m3":child.exact_full_volume,
         "axes":axes}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(f"P10QV_D_CASE{a.case}_EQUAL_COST_TOPOLOGY_T_PANELS_COMPLETE_NO_FEM",flush=True)


if __name__=="__main__":
    main()
