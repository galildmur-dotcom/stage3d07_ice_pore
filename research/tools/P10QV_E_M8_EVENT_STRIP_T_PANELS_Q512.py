#!/usr/bin/env python3
"""P10QV-E: event-backed s-strip topology projects empirical t transitions.

Unlike P10QV-D's five fixed s probe points, this geometry-only rule uses
the already tested critical-s event polynomials on each sampled t slice;
it evaluates physical topology at EVERY resulting s interval midpoint.
Distinct adjacent topology words are bracketed and bisected 12 times.
All choices are fixed before reading any heldout q2048 data. Despite
event-backed s strips, finite t sampling and numerical roots are NOT a
continuous interval proof or an analytical projection in t.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QQ_M8_ROOT_TOPOLOGY_ADAPTIVE_TRANSVERSE import root_topology
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import distribute_nodes,gauss
from P10QV_B_M8_CASE67_MULTI_CRITICAL_PILOT import (
    PILOTS,PIN,CASE_INPUT_SHA,S_BUDGET,projected_events)

OLD_Q512_SHA={
    6:"9b682145eec146bd1be3875810ca7a21927180056636703f6a2f60c97475e705",
    7:"07b1a71ac5e1c5dbd9874a8e68be9dd53f8a70f85e6b1a2f4c9fd84f02ed8cc4"}
T_GRID=257
BISECTIONS=12
OUTER_BUDGET=512
MAX_T_PANELS=32


def topology_word(child:RayChild,axis:int,t:float):
    breaks,diag=projected_events(child,axis,t)
    word=[]
    for a,b in zip(breaks,breaks[1:]):
        sig=root_topology(child,axis,(a+b)*.5,t)
        if not word or word[-1]!=sig:word.append(sig)
    if not word:
        raise ValueError("P10QV_E_EMPTY_EVENT_STRIP_TOPOLOGY")
    return tuple(word),len(breaks)-1,diag["numerical_degree_trims"]


def t_panels(child:RayChild,axis:int):
    samples=[(i+.5)/T_GRID for i in range(T_GRID)]
    words=[];max_intervals=0;trims=0
    for t in samples:
        key,count,trim=topology_word(child,axis,t)
        words.append(key)
        max_intervals=max(max_intervals,count)
        trims+=trim
    records=[];unseen_middle_signatures=0
    for i in range(1,T_GRID):
        if words[i]==words[i-1]:continue
        left,right=samples[i-1],samples[i]
        low,high=words[i-1],words[i]
        for level in range(BISECTIONS):
            mid=(left+right)*.5
            try:key,_,_=topology_word(child,axis,mid)
            except ValueError as exc:
                raise ValueError(
                    f"P10QV_E_PHYSICAL_ROOT_STOP axis={axis} bin={i} "
                    f"bisect={level} interval=[{left:.17g},{right:.17g}] "
                    f"probe_t={mid:.17g} cause={exc}") from exc
            if key==low:left=mid
            elif key==high:right=mid
            else:
                unseen_middle_signatures+=1
                raise ValueError(
                    f"P10QV_E_THIRD_TOPOLOGY_WITHIN_TRANSITION_BRACKET_STOP "
                    f"axis={axis} bin={i} bisect={level} "
                    f"interval=[{left:.17g},{right:.17g}] "
                    f"probe_t={mid:.17g} low={low} high={high} third={key}")
        records.append({"last_left_t":left,"first_right_t":right,
                        "uncertainty_width_t":right-left,
                        "new_panel_break_t":(left+right)*.5})
    breaks=[0.]+[x["new_panel_break_t"] for x in records]+[1.]
    if len(breaks)-1>MAX_T_PANELS or \
       any(b<=a for a,b in zip(breaks,breaks[1:])):
        raise ValueError("P10QV_E_T_PANEL_GEOMETRY_UNRESOLVED_STOP")
    allocated=distribute_nodes(breaks,OUTER_BUDGET)
    if sum(allocated)!=OUTER_BUDGET or min(allocated)<8:
        raise ValueError("P10QV_E_T_NODE_BUDGET_BROKEN")
    return breaks,allocated,{
        "event_strips_evaluated":T_GRID,
        "initial_t_grid_count":T_GRID,
        "bisected_transition_count":len(records),
        "geometry_t_brackets":records,
        "distinct_event_strip_words":len(set(words)),
        "max_initial_s_event_intervals":max_intervals,
        "initial_s_numerical_degree_trims":trims,
        "third_topologies_in_bracket":unseen_middle_signatures,
        "unobserved_t_changes_between_probes_not_excluded":True,
        "not_continuous_interval_certification":True}


def integrate_with_panels(child:RayChild,axis:int):
    breaks,counts,meta=t_panels(child,axis)
    totalg=0.;totalv=0.;points=0;outer=0
    s_segments=0;trims=0;maximum_high=0.;maximum_recon=0.
    for (lo,hi),n in zip(zip(breaks,breaks[1:]),counts):
        tn,tw=gauss(n)
        for t,wt in zip(tn,tw):
            rt=lo+(hi-lo)*float(t)
            br,diag=projected_events(child,axis,rt)
            inner=distribute_nodes(br,S_BUDGET)
            if sum(inner)!=S_BUDGET:
                raise ValueError("P10QV_E_S_NODE_BUDGET_BROKEN")
            tg=0.;tv=0.
            for (slo,shi),sn in zip(zip(br,br[1:]),inner):
                ns,ws=gauss(sn)
                for s,sw in zip(ns,ws):
                    g,v,_=child.moment_on_ray(
                        axis,slo+(shi-slo)*float(s),rt,cut=True)
                    tg+=(shi-slo)*float(sw)*g
                    tv+=(shi-slo)*float(sw)*v
                points+=sn
            totalg+=(hi-lo)*float(wt)*tg
            totalv+=(hi-lo)*float(wt)*tv
            outer+=1
            s_segments+=diag["intervals"]
            trims+=diag["numerical_degree_trims"]
            maximum_high=max(maximum_high,diag["max_radial_w3w4"],diag["max_azimuth_w2"])
            maximum_recon=max(maximum_recon,diag["max_recon_radial"],diag["max_recon_azimuth"])
            if outer%64==0 or outer==OUTER_BUDGET:
                print(f"P10QV_E_PROGRESS axis={axis} t={outer}/{OUTER_BUDGET} "
                      f"panels={len(counts)}",flush=True)
    if points!=OUTER_BUDGET*S_BUDGET or not math.isfinite(totalg) or \
       not 0<=totalv<=child.exact_full_volume*(1+1e-8):
        raise ValueError("P10QV_E_CUT_INTEGRAL_OR_COST_INVALID")
    return {"cut_gradient_m3":totalg,"cut_volume_m3":totalv,
            "outer_t_nodes":OUTER_BUDGET,"inner_s_nodes_per_t":S_BUDGET,
            "transverse_points":points,
            "outer_t_panel_breaks":breaks,"outer_t_panel_nodes":counts,
            "s_critical_intervals_total":s_segments,
            "numerical_azimuth_degree_trims":trims,
            "maximum_higher_ray_coefficient_relative":maximum_high,
            "maximum_physical_reconstruction_relative":maximum_recon,
            "t_topology_diagnostics":meta}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--case",type=int,choices=[6,7],required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true",
                   help="Audit geometry for every axis and record STOP without integration")
    a=p.parse_args()
    child_path=a.input_dir/f"P10QO_M8_REAL_CASE{a.case}_H8_CHILDREN_QA.json"
    q512_path=a.input_dir/f"P10QV_C_M8_CASE{a.case}_MULTI_Q256_512_QA.json"
    if hashlib.sha256(child_path.read_bytes()).hexdigest()!=CASE_INPUT_SHA[a.case] or \
       hashlib.sha256(q512_path.read_bytes()).hexdigest()!=OLD_Q512_SHA[a.case]:
        raise ValueError("P10QV_E_PINNED_REAL_M8_OR_FROZEN_Q512_CHANGED")
    src=json.loads(child_path.read_text());old=json.loads(q512_path.read_text())
    if src["mesh_sha256"]!=PIN or src["physical_4D_FEM_approved"] or \
       old["case"]!=a.case or old["pilot_index"]!=PILOTS[a.case]:
        raise ValueError("P10QV_E_WRONG_SOURCE_OR_PREVIOUS_PILOT")
    child=RayChild(src["terminals"][PILOTS[a.case]])
    active=[0,4] if a.case==6 else [1,4]
    if child.active!=active:
        raise ValueError("P10QV_E_WRONG_PHYSICAL_ACTIVE_BOUNDARIES")
    if a.preflight_only:
        axes={}
        for axis in (0,1,2):
            try:
                breaks,counts,diagnostics=t_panels(child,axis)
                axes[str(axis)]={"status":"GEOMETRY_ONLY_READY_NOT_CERTIFIED",
                                 "outer_t_panel_breaks":breaks,
                                 "outer_t_panel_nodes":counts,
                                 "diagnostics":diagnostics}
            except ValueError as exc:
                axes[str(axis)]={"status":"NUMERICAL_TOPOLOGY_STOP",
                                 "stop_reason":str(exc)}
                print(f"P10QV_E_PREFLIGHT_STOP case={a.case} axis={axis} "
                      f"reason={exc}",flush=True)
        stopped=[int(a) for a,row in axes.items()
                 if row["status"]=="NUMERICAL_TOPOLOGY_STOP"]
        out={"stage":"P10QV_E_EVENT_STRIP_ROOT_BRACKET_PREFLIGHT",
             "case":a.case,"pilot_index":PILOTS[a.case],
             "active_constraints":active,
             "mesh_sha256_from_archived_provenance":PIN,
             "archived_real_child_sha256":CASE_INPUT_SHA[a.case],
             "frozen_uniform_q512_sha256":OLD_Q512_SHA[a.case],
             "event_t_samples":T_GRID,"transition_bisections":BISECTIONS,
             "no_cut_integration_executed":True,"all_axes_tested":True,
             "axes_with_geometry_stop":stopped,
             "global_q512_event_strip_pilot_approved":len(stopped)==0,
             "numerical_roots_not_interval_certified":True,
             "no_Gmsh_no_mesh_change_no_FEM":True,
             "physical_4D_FEM_approved":False,"axes":axes}
        a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
        print(f"P10QV_E_CASE{a.case}_GEOMETRY_PREFLIGHT_COMPLETE "
              f"stopped_axes={stopped} NO_FEM",flush=True)
        return
    axes={}
    for axis in (0,1,2):
        result=integrate_with_panels(child,axis)
        baseline=old["axes"][str(axis)]["new_q512"]
        if baseline["transverse_points"]!=result["transverse_points"]:
            raise ValueError("P10QV_E_NOT_EQUAL_TO_FROZEN_Q512_COST")
        axes[str(axis)]={"event_strip_q512":result,
                        "frozen_uniform_q512_gradient_m3":baseline["cut_gradient_m3"],
                        "frozen_uniform_q512_volume_m3":baseline["cut_volume_m3"]}
    out={"stage":"P10QV_E_EVENT_STRIP_T_PILOT","case":a.case,
         "pilot_index":PILOTS[a.case],"active_constraints":active,
         "mesh_sha256_from_archived_provenance":PIN,
         "archived_real_child_sha256":CASE_INPUT_SHA[a.case],
         "frozen_uniform_q512_sha256":OLD_Q512_SHA[a.case],
         "event_t_samples":T_GRID,"transition_bisections":BISECTIONS,
         "outer_t_budget":OUTER_BUDGET,"inner_s_budget":S_BUDGET,
         "t_panels_selected_without_heldout_q2048":True,
         "no_global_2d_root_interval_certificate":True,
         "physical_4D_FEM_approved":False,
         "no_Gmsh_no_mesh_change_no_FEM":True,
         "full_child_gradient_m3":child.exact_full_gradient,
         "full_child_volume_m3":child.exact_full_volume,"axes":axes}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(f"P10QV_E_CASE{a.case}_EVENT_STRIP_Q512_COMPLETE_NO_FEM",flush=True)


if __name__=="__main__":main()
