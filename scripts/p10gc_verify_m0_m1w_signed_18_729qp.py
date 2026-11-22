#!/usr/bin/env python3
"""Independent raw-MSH2 M0/M1W 18-zone curved343/729QP adaptation gate.

No Gmsh execution, no FEM, no one-shot markers, no raw-mesh publication.
The *same physical regions* are quadrature-clipped independently on each mesh.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from p10ft_verify_fresh_m0_m1_spatial import mesh, pore_surface
from p10ed_verify_original_m1_m2_raw_spatial import RAD, POL, spatial_rule, CAD_VOL

M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M1W_SHA="fe77956c50534bfd0b6f84954b07f195e6449648bd71d5a6640d048aea9a5df2"
LOW,HIGH=.80,.85


def need(ok,message):
    if not ok:
        raise RuntimeError("P10GC_RAW_AUDIT_STOP: "+message)


def get_levels(mesh0,vol0,mesh1,vol1):
    levels={}
    for order in (7,9):
        print("P10GC_INDEPENDENT_QP",order**3,"M0",flush=True)
        q0=spatial_rule(mesh0,vol0,order)
        print("P10GC_INDEPENDENT_QP",order**3,"M1W",flush=True)
        q1=spatial_rule(mesh1,vol1,order)
        a=np.array(q0["qp_north_south_effective_tet_volume_m3"])
        b=np.array(q1["qp_north_south_effective_tet_volume_m3"])
        region0=np.array(q0["qp_north_south_region_volume_m3"])
        region1=np.array(q1["qp_north_south_region_volume_m3"])
        q=b/a
        need(len(q)==18 and np.all(np.isfinite(q)) and np.all(q>0),
             "invalid signed 18-zone ratios")
        zones=[]
        for r in range(3):
            for p in range(3):
                for h in range(2):
                    i=(r*3+p)*2+h
                    zones.append({"radial_zone":RAD[r],"polar_zone":POL[p],
                                  "hemisphere":"north" if h==0 else "south",
                                  "M0_Veff_m3":float(a[i]),"M1W_Veff_m3":float(b[i]),
                                  "M1W_over_M0_Veff_ratio":float(q[i]),
                                  "relative_Veff_change_percent":float(100*(q[i]-1)),
                                  "M0_region_volume_m3":float(region0[i]),
                                  "M1W_region_volume_m3":float(region1[i]),
                                  "same_physical_region_volume_ratio":float(region1[i]/region0[i]),
                                  "zone_gate":"PASS" if LOW<=q[i]<=HIGH else "FAIL"})
        levels[str(order)]={"qp_per_tet":order**3,"zones18":zones,
                            "zone18_pass_count":sum(x["zone_gate"]=="PASS" for x in zones),
                            "qp_total_volume_M0_m3":q0["total_curved_volume_m3"],
                            "qp_total_volume_M1W_m3":q1["total_curved_volume_m3"],
                            "min_curved_jac_M0":q0["min_curved_Jacobian_m3"],
                            "min_curved_jac_M1W":q1["min_curved_Jacobian_m3"]}
    return levels


def inspect(m0_path,m1w_path):
    m0,vol0,stats0=mesh(m0_path,M0_SHA)
    m1w,vol1,stats1=mesh(m1w_path,M1W_SHA)
    stats0["pore_surface"]=pore_surface(m0_path)
    stats1["pore_surface"]=pore_surface(m1w_path)
    levels=get_levels(m0,vol0,m1w,vol1)
    q7=np.array([x["M1W_over_M0_Veff_ratio"] for x in levels["7"]["zones18"]])
    q9=np.array([x["M1W_over_M0_Veff_ratio"] for x in levels["9"]["zones18"]])
    delta=np.abs(q7-q9)
    global_q=(stats1["volume_m3"]/stats1["tet10"])/(
        stats0["volume_m3"]/stats0["tet10"])
    positive=min(levels[str(j)]["min_curved_jac_M1W"] for j in (7,9))>0
    volume_closure=max(abs(levels[str(j)]["qp_total_volume_M1W_m3"]/stats1["volume_m3"]-1)
                       for j in (7,9))
    surface_ok=stats1["pore_radius_max_error_m"]<2e-13
    cad_ok=abs(stats1["volume_m3"]/CAD_VOL-1)<.005
    stable=bool(float(delta.max())<=.02)
    all_pass=bool(np.all((LOW<=q9)&(q9<=HIGH)))
    geometry=bool(positive and surface_ok and cad_ok and volume_closure<1e-9)
    accepted=bool(geometry and stable and all_pass and LOW<=global_q<=HIGH)
    return {"protocol":"P10GC_INDEPENDENT_M0_M1W_FIXED_18_SIGNED_ZONES_343_729QP",
            "source_raw_meshes_private":True,"no_native_Gmsh_no_FEM_no_markers":True,
            "M0_sha256":M0_SHA,"M1W_sha256":M1W_SHA,
            "required_every_signed_zone":[LOW,HIGH],
            "M0":stats0,"M1W":stats1,
            "realized_global_mean_tet_volume_ratio":global_q,
            "global_gate":LOW<=global_q<=HIGH,
            "curved_geometry_gate":geometry,
            "min_curved_jac_positive":positive,
            "CAD_volume_gate":cad_ok,"pore_surface_gate":surface_ok,
            "qp_volume_closure_rel":volume_closure,
            "levels":levels,
            "max_signed_18_zone_q_343_to_729_delta":float(delta.max()),
            "quadrature_stable_below_0p02":stable,
            "strict_18_zone_pass_count":int(np.count_nonzero((LOW<=q9)&(q9<=HIGH))),
            "strict_18_zone_all_pass":all_pass,
            "min_signed_zone_ratio_729":float(q9.min()),
            "max_signed_zone_ratio_729":float(q9.max()),
            "scientific_mesh_go":accepted,
            "verdict":"M1W_MESH_GO_FOR_FRESH_FEM" if accepted else
                       "M1W_ADAPTATION_STOP_NO_FEM",
            "caution":"Fixed-region QP-effective volumes, NOT pointwise or elementwise matching."}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m0",type=Path,required=True)
    p.add_argument("--m1w",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    need(a.m0.resolve()!=a.m1w.resolve(),"same input mesh")
    report=inspect(a.m0,a.m1w)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
        stream.write("\n")
    print("P10GC_RESULT",json.dumps({k:report[k] for k in (
        "realized_global_mean_tet_volume_ratio","min_signed_zone_ratio_729",
        "max_signed_zone_ratio_729","strict_18_zone_pass_count",
        "max_signed_18_zone_q_343_to_729_delta","verdict")}),flush=True)


if __name__=="__main__":
    main()
