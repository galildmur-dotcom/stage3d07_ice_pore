#!/usr/bin/env python3
"""Independent four-file audit of P10QV-B real case6/7 multi-cut pilot.

No production FE integration is called here. Reconcile repeated q128
values, exact full moments, three-axis absolute discrepancies, q128/q256,
and fixed quadrature cost. Fail a deliberately corrupted q128 negative test.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

PIN="40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
PILOTS={6:(5751,19,[0,4]),7:(5847,10,[1,4])}


def check(one,two,case):
    elem,idx,active=PILOTS[case]
    for obj,orders in ((one,[64,128]),(two,[128,256])):
        if obj["stage"]!="P10QV_B_PILOT" or obj["case"]!=case or \
           obj["original_element"]!=elem or obj["child_index"]!=idx or \
           obj["active_constraints"]!=active or obj["outer_orders"]!=orders or \
           obj["mesh_sha256_from_archived_provenance"]!=PIN or \
           not obj["actual_mesh_bytes_not_available"] or \
           not obj["no_Gmsh_no_mesh_change_no_FEM"] or \
           len(obj["axes"])!=3:
            raise ValueError("P10QV_B_INDEPENDENT_PROVENANCE_SCOPE_OR_INPUT_GUARD")
    normal=abs(two["exact_full_child_gradient_m3"])
    volume=two["exact_full_child_volume_m3"]
    if normal<1e-25 or volume<=0 or \
       abs(one["exact_full_child_gradient_m3"]-two["exact_full_child_gradient_m3"])>1e-25 or \
       abs(one["exact_full_child_volume_m3"]-volume)>1e-25:
        raise ValueError("P10QV_B_INDEPENDENT_NORMALIZATION_WRONG")
    by_axis={}
    for a in ("0","1","2"):
        x=one["axes"][a];y=two["axes"][a]
        lhs=x["critical"]["128"];rhs=y["critical"]["128"]
        for metric in ("cut_gradient_m3","cut_volume_m3"):
            # New run must reproduce old q128 byte-for-byte or within 1e-14 relative.
            denom=max(abs(lhs[metric]),abs(rhs[metric]),1e-25)
            if abs(lhs[metric]-rhs[metric])/denom>1e-14:
                raise ValueError("P10QV_B_INDEPENDENT_Q128_NOT_REPRODUCED")
        for z,order in ((x["critical"]["64"],64),
                        (lhs,128),(y["critical"]["256"],256)):
            if z["transverse_points"] != 128*order or \
               z["max_radial_w3w4"]>1e-9 or \
               z["max_azimuth_w2"]>1e-9 or \
               z["cut_volume_m3"] < 0 or z["cut_volume_m3"]>volume*(1+1e-8):
                raise ValueError("P10QV_B_INDEPENDENT_COST_DEGREE_OR_VOLUME_GUARD")
        if max(x["segmented_full_moment_relative"],
               x["segmented_full_volume_relative"],
               y["segmented_full_moment_relative"],
               y["segmented_full_volume_relative"])>1e-10:
            raise ValueError("P10QV_B_INDEPENDENT_FULL_FE_MOMENT_CLOSURE_FAILED")
        by_axis[a]={
            "q64_to_q128_gradient_relative_to_full_child":
               abs(x["critical"]["64"]["cut_gradient_m3"]-
                   lhs["cut_gradient_m3"])/normal,
            "q128_to_q256_gradient_relative_to_full_child":
               abs(lhs["cut_gradient_m3"]-
                   y["critical"]["256"]["cut_gradient_m3"])/normal,
            "q128_to_q256_volume_relative_to_full_child":
               abs(lhs["cut_volume_m3"]-
                   y["critical"]["256"]["cut_volume_m3"])/volume,
            "q128_gradient_m3":lhs["cut_gradient_m3"],
            "q256_gradient_m3":y["critical"]["256"]["cut_gradient_m3"],
            "q256_volume_m3":y["critical"]["256"]["cut_volume_m3"]}
    pairs={}
    for a,b in ((0,1),(0,2),(1,2)):
        key=f"{a}_{b}"
        ga=two["axes"][str(a)]["critical"]
        gb=two["axes"][str(b)]["critical"]
        e128=abs(ga["128"]["cut_gradient_m3"]-gb["128"]["cut_gradient_m3"])/normal
        e256=abs(ga["256"]["cut_gradient_m3"]-gb["256"]["cut_gradient_m3"])/normal
        if abs(one["pairwise"][key]["gradient_rel_to_full_original_child"]-e128)>1e-15:
            raise ValueError("P10QV_B_INDEPENDENT_REPORTED_OLD_PAIRWISE_WRONG")
        pairs[key]={"q128_gradient_relative_to_full_child":e128,
                    "q256_gradient_relative_to_full_child":e256,
                    "q256_volume_relative_to_full_child":abs(
                        ga["256"]["cut_volume_m3"]-gb["256"]["cut_volume_m3"])/volume}
    return {"case":case,"original_element":elem,"pilot_child":idx,
            "active_constraints":active,"axes":by_axis,
            "pairwise":pairs,
            "q256_max_pairwise_gradient_relative_to_full_child":
                max(v["q256_gradient_relative_to_full_child"] for v in pairs.values()),
            "q128_max_pairwise_gradient_relative_to_full_child":
                max(v["q128_gradient_relative_to_full_child"] for v in pairs.values()),
            "q128_to_q256_max_gradient_relative_to_full_child":
                max(v["q128_to_q256_gradient_relative_to_full_child"] for v in by_axis.values()),
            "all_checks_pass_but_not_global_L1_or_interval_certificate":True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    cases=[]
    for case in (6,7):
        paths=[a.input_dir/f"P10QV_B_M8_CASE{case}_MULTI_Q{x}_QA.json"
               for x in ("64_128","128_256")]
        src=[json.loads(path.read_text()) for path in paths]
        report=check(*src,case)
        report["evidence_sha256"]={path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in paths}
        cases.append(report)
        # Independent negative QA: a one-percent change to repeated q128
        # must be rejected even if the complete FE moment is unchanged.
        tampered=copy.deepcopy(src[1])
        tampered["axes"]["0"]["critical"]["128"]["cut_gradient_m3"]*=1.01
        try:
            check(src[0],tampered,case)
        except ValueError as exc:
            if "Q128_NOT_REPRODUCED" not in str(exc):
                raise ValueError("P10QV_B_NEGATIVE_TEST_WRONG_FAILURE") from exc
        else:
            raise ValueError("P10QV_B_NEGATIVE_Q128_REPRODUCTION_NOT_REJECTED")
    out={"stage":"P10QV_B_PILOT_INDEPENDENT_AUDIT",
         "scope":"two real M8 multi cuts; all 3 axes; q64,q128,q256",
         "mesh_sha256_from_archived_provenance":PIN,
         "root_interval_certificate_obtained":False,
         "all_178_cut_validated":False,
         "physical_4D_FEM_approved":False,"no_Gmsh_no_mesh_change_no_FEM":True,
         "negative_one_percent_corrupted_q128_rejected_both_cases":True,
         "cases":cases}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("P10QV_B_INDEPENDENT_TWO_CASE_PILOT_AUDIT_PASS_NOT_GLOBAL_FEM",flush=True)


if __name__=="__main__":main()
