#!/usr/bin/env python3
"""P10QV-C independent read-only q512 comparison for real M8 case6/7 pilots."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path

PIN="40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
PILOTS={6:(5751,19,[0,4]),7:(5847,10,[1,4])}
TARGET=1e-6


def audit_case(previous,new,case):
    element,index,active=PILOTS[case]
    if previous["stage"]!="P10QV_B_PILOT" or new["stage"]!="P10QV_C_Q512_PILOT" or \
       previous["case"]!=case or new["case"]!=case or \
       previous["child_index"]!=index or new["pilot_index"]!=index or \
       previous["original_element"]!=element or new["original_element"]!=element or \
       previous["active_constraints"]!=active or new["active_constraints"]!=active or \
       previous["mesh_sha256_from_archived_provenance"]!=PIN or \
       new["mesh_sha256_from_archived_provenance"]!=PIN or \
       not previous["no_Gmsh_no_mesh_change_no_FEM"] or \
       not new["no_Gmsh_no_mesh_change_no_FEM"] or \
       new["t_orders"]!=[256,512] or new["fixed_inner_budget"]!=128:
        raise ValueError("P10QV_C_SOURCE_SCOPE_OR_PROVENANCE_NOT_PINNED")
    full=abs(previous["exact_full_child_gradient_m3"])
    full_v=previous["exact_full_child_volume_m3"]
    if full<=1e-25 or full_v<=0 or \
       abs(full-abs(new["full_original_child_gradient_m3"]))>1e-25 or \
       abs(full_v-new["full_original_child_volume_m3"])>1e-25:
        raise ValueError("P10QV_C_WRONG_NORMALIZER")
    # A full-child reference can hide a relatively large error in a tiny
    # cut integral. Report both norms; use the smallest q512 axis value as
    # a conservative shared local cut scale (never signed cancellation).
    cut_scale=min(abs(new["axes"][a]["new_q512"]["cut_gradient_m3"])
                  for a in ("0","1","2"))
    if cut_scale<=1e-25:raise ValueError("P10QV_C_CUT_LOCAL_NORMALIZER_TOO_SMALL")
    axis_rows={};pairwise={}
    for axis in ("0","1","2"):
        old=previous["axes"][axis]["critical"]["256"]
        ref=new["axes"][axis]["reference_q256"]
        q512=new["axes"][axis]["new_q512"]
        if ref["transverse_points"]!=32768 or q512["transverse_points"]!=65536 or \
           q512["outer_t_order"]!=512 or q512["inner_nodes_per_t"]!=128:
            raise ValueError("P10QV_C_QUADRATURE_COST_WRONG")
        for field in ("cut_gradient_m3","cut_volume_m3"):
            if old[field]!=ref[field]:
                raise ValueError("P10QV_C_FROZEN_Q256_CHANGED")
        if q512["cut_volume_m3"]<0 or q512["cut_volume_m3"]>full_v*(1+1e-8) or \
           q512["maximum_higher_ray_coefficient_rel"]>1e-9:
            raise ValueError("P10QV_C_UNPHYSICAL_OR_REDUCED_DEGREE_GUARD")
        diff=abs(q512["cut_gradient_m3"]-ref["cut_gradient_m3"])/full
        if abs(diff-new["axes"][axis]["relative_q256_to_q512_gradient_to_full_child"])>1e-16:
            raise ValueError("P10QV_C_REPORTED_ORDER_DIFFERENCE_WRONG")
        axis_rows[axis]={
            "q128_to_q256_gradient_relative_to_full_child":abs(
                previous["axes"][axis]["critical"]["128"]["cut_gradient_m3"]-
                old["cut_gradient_m3"])/full,
            "q256_to_q512_gradient_relative_to_full_child":diff,
            "q256_to_q512_gradient_relative_to_cut":abs(
                q512["cut_gradient_m3"]-ref["cut_gradient_m3"])/cut_scale,
            "q256_to_q512_volume_relative_to_full_child":abs(
                q512["cut_volume_m3"]-ref["cut_volume_m3"])/full_v,
            "q512_gradient_m3":q512["cut_gradient_m3"]}
    for i,j in ((0,1),(0,2),(1,2)):
        key=f"{i}_{j}"
        p=new["axes"][str(i)]["new_q512"]
        q=new["axes"][str(j)]["new_q512"]
        d=abs(p["cut_gradient_m3"]-q["cut_gradient_m3"])/full
        old=abs(previous["axes"][str(i)]["critical"]["256"]["cut_gradient_m3"]-
                previous["axes"][str(j)]["critical"]["256"]["cut_gradient_m3"])/full
        if abs(d-new["pairwise"][key]["q512_gradient_relative_to_full_child"])>1e-16:
            raise ValueError("P10QV_C_REPORTED_PAIRWISE_WRONG")
        pairwise[key]={"q256_relative_to_full_child":old,
                       "q512_relative_to_full_child":d,
                       "q512_relative_to_cut":abs(p["cut_gradient_m3"]-
                                                    q["cut_gradient_m3"])/cut_scale}
    max_order=max(r["q256_to_q512_gradient_relative_to_full_child"]
                  for r in axis_rows.values())
    max_pair=max(r["q512_relative_to_full_child"] for r in pairwise.values())
    max_order_cut=max(r["q256_to_q512_gradient_relative_to_cut"]
                      for r in axis_rows.values())
    max_pair_cut=max(r["q512_relative_to_cut"] for r in pairwise.values())
    if abs(max_order-new["max_order_q256_to_q512_relative_to_full_child"])>1e-16 or \
       abs(max_pair-new["max_axis_pair_q512_relative_to_full_child"])>1e-16:
        raise ValueError("P10QV_C_GLOBAL_MAXIMUM_INCONSISTENT")
    return {"case":case,"index":index,"active_constraints":active,
            "q512_max_pairwise_rel":max_pair,"q256_to_q512_max_order_change_rel":max_order,
            "conditional_local_1e6_empirical_gate":max(max_pair,max_order)<TARGET,
            "conservative_cut_scale_m3":cut_scale,
            "q512_max_pairwise_relative_to_cut":max_pair_cut,
            "q256_to_q512_max_order_change_relative_to_cut":max_order_cut,
            "diagnostic_cut_relative_1e6_gate":max(max_pair_cut,max_order_cut)<TARGET,
            "axes":axis_rows,"pairwise":pairwise}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    cases=[]
    for case in (6,7):
        old_path=a.input_dir/f"P10QV_B_M8_CASE{case}_MULTI_Q128_256_QA.json"
        new_path=a.input_dir/f"P10QV_C_M8_CASE{case}_MULTI_Q256_512_QA.json"
        old=json.loads(old_path.read_text());new=json.loads(new_path.read_text())
        row=audit_case(old,new,case)
        row["input_sha256"]={name:hashlib.sha256(p.read_bytes()).hexdigest()
                             for name,p in (("q256_baseline",old_path),("q512_new",new_path))}
        cases.append(row)
        corrupted=copy.deepcopy(new)
        corrupted["axes"]["0"]["new_q512"]["cut_gradient_m3"]*=1.01
        try:
            audit_case(old,corrupted,case)
        except ValueError as exc:
            if "REPORTED_ORDER_DIFFERENCE_WRONG" not in str(exc):
                raise ValueError("P10QV_C_NEGATIVE_CONTROL_WRONG_REJECTION") from exc
        else:
            raise ValueError("P10QV_C_NEGATIVE_CORRUPTION_NOT_REJECTED")
    out={"stage":"P10QV_C_INDEPENDENT_Q512_AUDIT",
         "scope":"same two real M8 h8 multi cut; three axes; q256->q512",
         "mesh_sha256_from_prior_validated_metadata":PIN,
         "negative_one_percent_q512_corruption_rejected":True,
         "both_local_empirical_gates":all(x["conditional_local_1e6_empirical_gate"] for x in cases),
         "both_cut_relative_diagnostic_gates":all(x["diagnostic_cut_relative_1e6_gate"] for x in cases),
         "not_full_178_cut":True,"not_root_interval_certificate":True,
         "no_Gmsh_no_mesh_change_no_FEM":True,"cases":cases}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("P10QV_C_Q512_INDEPENDENT_TWO_CASE_AUDIT_COMPLETE_NOT_GLOBAL_PASS",flush=True)


if __name__=="__main__":main()
