#!/usr/bin/env python3
"""P10FV: source-only audit of the revised all-volume M0->M1 uniform contract.

No Gmsh, FEM or user-file mutation. Q ratios are read from independently
computed curved Tet10 fixed-physical-region quadrature, not per-element pairs.
"""
import argparse
import json
from pathlib import Path

EXPECTED_M0="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
EXPECTED_FAILED_M1="f281d253571db095b90790326f503dfa3f6fe3a1dc5cb5c904fca2787dfe4275"
LOWER=.80
UPPER=.85


def check(data):
    assert data["protocol"]=="P10FT_FRESH_M0_TO_M1_INDEPENDENT_FIXED_3D_QP"
    assert data["M0_SHA"]==EXPECTED_M0 and data["M1_SHA"]==EXPECTED_FAILED_M1
    z729=data["refinement_samples"]["9"]["zones9"]
    z343=data["refinement_samples"]["7"]["zones9"]
    assert len(z729)==len(z343)==9
    zones=[]
    for a,b in zip(z729,z343):
        assert a["radial"]==b["radial"] and a["polar"]==b["polar"]
        q9=a["M1_over_M0_effective_volume"]
        q7=b["M1_over_M0_effective_volume"]
        zones.append({"radial":a["radial"],"polar":a["polar"],
                      "ratio_729qp":q9,
                      "ratio_343qp":q7,
                      "abs_quadrature_delta":abs(q9-q7),
                      "physical_region_volume_ratio":a["M1_over_M0_region_volume"],
                      "pass_0p80_to_0p85":LOWER<=q9<=UPPER})
    polar=data["priority_order9"]
    global_ratio=data["realized_global_mean_tet_volume_ratio"]
    south=polar["south_ratio"];north=polar["north_ratio"]
    all_pass=all(x["pass_0p80_to_0p85"] for x in zones)
    split_pass=all(LOWER<=q<=UPPER for q in (north,south))
    stable=max(x["abs_quadrature_delta"] for x in zones)<.02
    return {"protocol":"P10FV_M0_TO_M1_UNIFORM_ALL_VOLUME_15_TO_20_PERCENT",
            "status":"REVISED_CONTRACT_AND_REAL_M1_STOP",
            "new_contract":{"characteristic_local_volume_reduction_percent":[15,20],
                            "ratio_bounds_inclusive":[LOWER,UPPER],
                            "nominal_center_target_volume_ratio":.825,
                            "nominal_center_target_h_ratio":.825**(1/3),
                            "kappa":"1_CONSTANT_ENTIRE_PHYSICAL_VOLUME",
                            "actual_refinement_test":"fixed_3D_QP_Veff_not_local_unpaired_medians",
                            "uniform_required_in":"all_3D_zones_and_separately_N_S_polar_caps",
                            "surface_and_volume_size_field":"ONE_C1_H_X",
                            "geometry_not_scaled":True,
                            "azimuthal_element_regular_lattice_required":False,
                            "no_candidate_is_approved_by_source_only_math":True},
            "checked_previous_M0_SHA":EXPECTED_M0,
            "checked_failed_M1_SHA":EXPECTED_FAILED_M1,
            "previous_real_M1":{"global_mean_volume_ratio":global_ratio,
                                "global_pass":LOWER<=global_ratio<=UPPER,
                                "north_polar_729qp_ratio":north,
                                "north_polar_pass":LOWER<=north<=UPPER,
                                "south_polar_729qp_ratio":south,
                                "south_polar_pass":LOWER<=south<=UPPER,
                                "all_zones_pass":all_pass,
                                "separate_poles_pass":split_pass,
                                "all_zones_qp_stable_to_0p02":stable,
                                "zones9":zones},
            "overall_previous_M1_go":False,
            "previous_P10FU_south_only_package":"RETRACTED_DO_NOT_RUN",
            "new_M1_GMSH_attempts":0,
            "FEM_attempts":0}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    data=json.loads(a.source.read_text(encoding="utf-8"))
    d=check(data)
    assert not d["previous_real_M1"]["global_pass"]
    assert not d["previous_real_M1"]["all_zones_pass"]
    assert not d["previous_real_M1"]["separate_poles_pass"]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10FV_CONTRACT_STOP_PREVIOUS_M1",json.dumps(
        {"global":d["previous_real_M1"]["global_mean_volume_ratio"],
         "north":d["previous_real_M1"]["north_polar_729qp_ratio"],
         "south":d["previous_real_M1"]["south_polar_729qp_ratio"],
         "zones_pass":sum(x["pass_0p80_to_0p85"] for x in d["previous_real_M1"]["zones9"]),
         "qp_stable_all":d["previous_real_M1"]["all_zones_qp_stable_to_0p02"]}))


if __name__=="__main__":
    main()
