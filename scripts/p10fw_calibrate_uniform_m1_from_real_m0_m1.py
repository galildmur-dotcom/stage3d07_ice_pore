#!/usr/bin/env python3
"""Independent read-only 18 signed-zone Tet10 calibration for a UNIFORM M1.

The actual spatial *target* is constant 0.825; the nonuniform size-field
compensation only counteracts the observed Gmsh remeshing response.
This is an empirical one-step predictor, NEVER a mesh acceptance certificate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from p10ft_verify_fresh_m0_m1_spatial import mesh, SHA_M0, SHA_M1
from p10ed_verify_original_m1_m2_raw_spatial import RAD, POL, spatial_rule


def inspect(m0_path,m1_path):
    m0,v0,s0=mesh(m0_path,SHA_M0)
    m1,v1,s1=mesh(m1_path,SHA_M1)
    levels={}
    for q in (7,9):
        a=spatial_rule(m0,v0,q)
        b=spatial_rule(m1,v1,q)
        zones=[]
        for radial in range(3):
            for angular in range(3):
                for hemi in range(2):
                    idx=(radial*3+angular)*2+hemi
                    v0e=a["qp_north_south_effective_tet_volume_m3"][idx]
                    v1e=b["qp_north_south_effective_tet_volume_m3"][idx]
                    qreal=v1e/v0e
                    zones.append({"radial_zone":RAD[radial],
                                  "polar_zone":POL[angular],
                                  "hemisphere":"north" if hemi==0 else "south",
                                  "measured_M1_over_M0":qreal,
                                  "nominal_previous_h3":.8,
                                  "target_actual_Veff":.825,
                                  "source_only_compensation_ratio":.825/qreal,
                                  "new_nominal_h3_h0":.8*.825/qreal})
        levels[str(q)]={"zones18":zones,
                       "M0_min_jac":a["min_curved_Jacobian_m3"],
                       "M1_min_jac":b["min_curved_Jacobian_m3"]}
    q7,q9=levels["7"]["zones18"],levels["9"]["zones18"]
    delta=max(abs(x["measured_M1_over_M0"]-y["measured_M1_over_M0"]) for x,y in zip(q7,q9))
    return {"protocol":"P10FW_REAL_18_ZONE_SIGNED_HEMISPHERE_CALIBRATION",
            "M0_SHA":SHA_M0,"failed_M1_SHA":SHA_M1,
            "original_msh_not_published":True,
            "target_actual_Veff_ratio_everywhere":.825,
            "required_actual_range":[.8,.85],
            "source_only_field_model":"new_h3_h0=0.8*(0.825/observed_q); C1_interp_18_zones",
            "limitations":["empirical linear bias assumption; Gmsh remeshing nonlinear",
                           "18 physical zones, not pointwise or Tet-to-Tet mapping",
                           "predicted field must pass real 729QP tests after one native Gmsh"],
            "sample_levels":levels,
            "max_signed_zone_q_343_to_729_delta":delta,
            "no_new_native_Gmsh_FEM":True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m0",type=Path,required=True)
    p.add_argument("--m1",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    results=inspect(args.m0,args.m1)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10FW_SOURCE_CALIBRATION",json.dumps(
        {"max_343_to729_delta":results["max_signed_zone_q_343_to_729_delta"],
         "q18_729":[round(z["measured_M1_over_M0"],5)
                     for z in results["sample_levels"]["9"]["zones18"]]}))


if __name__=="__main__":
    main()
