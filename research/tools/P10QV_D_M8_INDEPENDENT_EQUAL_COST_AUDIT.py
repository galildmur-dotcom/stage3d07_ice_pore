#!/usr/bin/env python3
"""Independent fixed-cost t-panel vs uniform q512, held-out uniform q1024.

Reads frozen P10QV-C, P10QV-D panel, P10QV-D held-out files; no integration
or mesh access. Reports signed-independent per-axis absolute differences.
The numerical q1024 comparator is NOT ground truth or interval certification.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

PIN="40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
CASES={6:(19,[0,4]),7:(10,[1,4])}


def audit_case(base,panel,heldout,case):
    child,active=CASES[case]
    if base["stage"]!="P10QV_C_Q512_PILOT" or \
       panel["stage"]!="P10QV_D_EQUAL_COST_T_TOPOLOGY_PILOT" or \
       heldout["stage"]!="P10QV_D_HELDOUT_Q1024" or \
       base["case"]!=case or panel["case"]!=case or heldout["case"]!=case or \
       base["pilot_index"]!=child or panel["pilot_index"]!=child or \
       heldout["pilot_index"]!=child or \
       panel["active_constraints"]!=active or heldout["active_constraints"]!=active or \
       any(d["mesh_sha256_from_archived_provenance"]!=PIN for d in (base,panel,heldout)) or \
       panel["outer_t_budget"]!=512 or panel["inner_s_budget"]!=128 or \
       heldout["outer_t_nodes"]!=1024 or heldout["inner_s_budget_per_t"]!=128 or \
       not panel["t_breaks_chosen_without_q1024_or_integral_values"] or \
       not heldout["no_panel_info_used_in_computation"]:
        raise ValueError("P10QV_D_WRONG_FROZEN_INPUT_SCOPE")
    normal=abs(base["full_original_child_gradient_m3"])
    if normal<=1e-25:raise ValueError("P10QV_D_FULL_NORMALIZER_INVALID")
    cutscale=min(abs(heldout["axes"][a]["cut_gradient_m3"]) for a in ("0","1","2"))
    if cutscale<=1e-25:raise ValueError("P10QV_D_CUT_NORMALIZER_INVALID")
    axes={}
    for axis in ("0","1","2"):
        uniform=base["axes"][axis]["new_q512"]
        panel_entry=panel["axes"][axis]
        split=panel_entry["segmented_q512"]
        ref=heldout["axes"][axis]
        if split["transverse_points"]!=512*128 or uniform["transverse_points"]!=512*128 or \
           ref["transverse_points"]!=1024*128 or \
           sum(split["outer_t_panel_nodes"])!=512 or \
           len(split["outer_t_panel_breaks"])!=len(split["outer_t_panel_nodes"])+1 or \
           split["outer_t_panel_breaks"][0]!=0 or \
           split["outer_t_panel_breaks"][-1]!=1 or \
           any(b<=a for a,b in zip(split["outer_t_panel_breaks"],split["outer_t_panel_breaks"][1:])):
            raise ValueError("P10QV_D_EQUAL_COST_OR_PANEL_BREAK_INVALID")
        for field,snapshot in (("cut_gradient_m3","frozen_uniform_q512_gradient_m3"),
                               ("cut_volume_m3","frozen_uniform_q512_volume_m3")):
            if panel_entry[snapshot]!=uniform[field]:
                raise ValueError("P10QV_D_UNIFORM_Q512_NOT_FROZEN")
        e_uniform=abs(uniform["cut_gradient_m3"]-ref["cut_gradient_m3"])
        e_split=abs(split["cut_gradient_m3"]-ref["cut_gradient_m3"])
        axes[axis]={
            "t_panels":len(split["outer_t_panel_nodes"]),
            "topology_transition_brackets":len(split["topology_transition_t_brackets"]),
            "uniform_q512_gradient_m3":uniform["cut_gradient_m3"],
            "split_q512_gradient_m3":split["cut_gradient_m3"],
            "heldout_q1024_gradient_m3":ref["cut_gradient_m3"],
            "uniform_q512_error_to_q1024_absolute_m3":e_uniform,
            "panel_q512_error_to_q1024_absolute_m3":e_split,
            "uniform_q512_error_to_q1024_relative_to_full_child":e_uniform/normal,
            "panel_q512_error_to_q1024_relative_to_full_child":e_split/normal,
            "uniform_q512_error_to_q1024_relative_to_cut":e_uniform/cutscale,
            "panel_q512_error_to_q1024_relative_to_cut":e_split/cutscale,
            "panel_better_than_uniform_equal_cost":e_split<e_uniform}
    def maxpair(source):
        return max(abs(source[str(a)]-source[str(b)])/cutscale
                   for a,b in ((0,1),(0,2),(1,2)))
    pair_uniform=maxpair({a:base["axes"][a]["new_q512"]["cut_gradient_m3"]
                          for a in ("0","1","2")})
    pair_split=maxpair({a:panel["axes"][a]["segmented_q512"]["cut_gradient_m3"]
                        for a in ("0","1","2")})
    pair_ref=maxpair({a:heldout["axes"][a]["cut_gradient_m3"]
                      for a in ("0","1","2")})
    return {"case":case,"pilot_index":child,"active_constraints":active,
            "cut_scale_min_abs_heldout_q1024_m3":cutscale,
            "same_cost_512_outer_by_128_inner":True,
            "axes":axes,
            "count_axes_panel_better_than_uniform":sum(
                x["panel_better_than_uniform_equal_cost"] for x in axes.values()),
            "maximum_uniform_error_to_q1024_relative_to_cut":max(
                x["uniform_q512_error_to_q1024_relative_to_cut"] for x in axes.values()),
            "maximum_panel_error_to_q1024_relative_to_cut":max(
                x["panel_q512_error_to_q1024_relative_to_cut"] for x in axes.values()),
            "uniform_q512_max_cross_axis_relative_to_cut":pair_uniform,
            "panel_q512_max_cross_axis_relative_to_cut":pair_split,
            "heldout_q1024_max_cross_axis_relative_to_cut":pair_ref}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    rows=[]
    for case in (6,7):
        paths=[a.input_dir/f"P10QV_C_M8_CASE{case}_MULTI_Q256_512_QA.json",
               a.input_dir/f"P10QV_D_M8_CASE{case}_TOPOLOGY_T_Q512_QA.json",
               a.input_dir/f"P10QV_D_M8_CASE{case}_HELDOUT_Q1024_QA.json"]
        docs=[json.loads(x.read_text()) for x in paths]
        row=audit_case(*docs,case)
        row["sources_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in paths}
        rows.append(row)
        corrupted=copy.deepcopy(docs[1])
        corrupted["axes"]["0"]["frozen_uniform_q512_gradient_m3"]*=1.01
        try:
            audit_case(docs[0],corrupted,docs[2],case)
        except ValueError as exc:
            if "UNIFORM_Q512_NOT_FROZEN" not in str(exc):
                raise ValueError("P10QV_D_NEGATIVE_Q512_WRONG_FAILURE") from exc
        else:
            raise ValueError("P10QV_D_NEGATIVE_Q512_NOT_REJECTED")
    out={"stage":"P10QV_D_INDEPENDENT_EQUAL_COST_VS_HELDOUT_Q1024",
         "source":"real M8 two multi cut, 3 axes, both normalizations",
         "mesh_sha256_from_validated_archive_metadata":PIN,
         "q1024_comparator_not_exact_solution":True,
         "two_cut_pilot_not_full_178":True,
         "root_interval_certificate_obtained":False,
         "physical_4D_FEM_approved":False,
         "no_Gmsh_no_mesh_change_no_FEM":True,
         "negative_one_percent_frozen_q512_corruption_rejected":True,
         "cases":rows}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("P10QV_D_INDEPENDENT_EQUAL_COST_Q1024_AUDIT_COMPLETE_NOT_EXACT",flush=True)


if __name__=="__main__":main()
