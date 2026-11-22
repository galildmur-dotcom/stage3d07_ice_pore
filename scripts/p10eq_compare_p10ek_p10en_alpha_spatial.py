#!/usr/bin/env python3
"""P10EQ: reproducible source-only two-alpha response of fixed 3D kappa=1 zones.

Uses only already verified small derived JSON, not MSH/Gmsh/FEM.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
EK_SHA="f7183efdaff22b0ed7c281104ee00e18499c0d53f087100e08959a7d4a43250b"
EN_SHA="04a5a16111ebfa1219cd628355b83eb2b5e7bf0d3238c08a3fff118377bfc8f0"


def need(ok,why):
    if not ok:raise ValueError("P10EQ_STOP: "+why)


def compare(old:dict,new:dict)->dict:
    need(old["raw_mesh_sha256"]=={"M1":M1_SHA,"P10EK_M2":EK_SHA} and
         new["source_sha256"]["M1"]==M1_SHA and
         new["source_sha256"]["P10EN_M2"]==EN_SHA and
         not old["physical_fem_allowed"] and not new["physical_FEM_allowed"],
         "exact derived original mesh/FEM identity")
    rows=[]
    for order in (3,5,7,9):
        a=old["fixed_3d_spatial_domain_quadrature"][str(order)]
        b=new["refinements"][str(order)]
        records=(
            ("north",a["north_south_effective_volume_ratio_M2_over_M1"][0],
             b["M2_over_M1_effective_tet_volume_18_north_south_zones"][0]),
            ("south",a["north_south_effective_volume_ratio_M2_over_M1"][1],
             b["M2_over_M1_effective_tet_volume_18_north_south_zones"][1]),
            ("both_poles",a["zone_effective_volume_ratio_M2_over_M1"][0],
             b["M2_over_M1_effective_tet_volume_9_zones"][0]),
        )
        for name,x,y in records:
            rows.append({"region":name,"qp_per_tet":order**3,
                "alpha20_M2_over_M1":x,"alpha17_M2_over_M1":y,
                "alpha20_reduction_percent":100*(1-x),
                "alpha17_reduction_percent":100*(1-y),
                "delta_ratio_after_alpha_decrease":y-x,
                "alpha17_new_band_pass":.75<=y<=.85,
                "alpha_decrease_did_not_coarsen_region":y<=x})
    final={r["region"]:r for r in rows if r["qp_per_tet"]==729}
    need(set(final)=={"north","south","both_poles"} and
         final["north"]["alpha_decrease_did_not_coarsen_region"] and
         not final["south"]["alpha17_new_band_pass"] and
         final["both_poles"]["alpha17_new_band_pass"],
         "the nonmonotone polar scientific contrast changed")
    return {"protocol":"P10EQ_TWO_ALPHA_REALIZED_FIXED_3D_SPATIAL_RESPONSE_SOURCE_ONLY",
            "status":"ALPHA_SCALAR_BACKTRACKING_NOT_RELIABLE_D025_BAND_STOP_NO_FEM",
            "raw_meshes_not_published":True,"no_new_Gmsh_no_FEM":True,
            "M1_sha256":M1_SHA,
            "observed_meshes":{"P10EK_alpha20":EK_SHA,"P10EN_alpha17":EN_SHA},
            "fixed_physical_region":"distance0..100um abs(mu)>=0.8; north/south separated",
            "effective_local_tet_volume":"fixed zone volume / fractional intersecting Tet10 count",
            "rows":rows,
            "order9":final,
            "interpretation":[
                "alpha reduction .20 to .17 did not coarsen the north kappa1 region",
                "south region coarsened past the new 15 percent minimum refinement",
                "both-poles aggregate passes but hides opposite local violations",
                "smooth axisymmetric source h does not guarantee monotone realized Tet10 volume",
                "the topology sensitivity explanation is plausible, not a proven unique mechanism",
                "next stage should analyze realized M1 local sizes and spatial gradation before another one-shot mesh",
            ],
            "physical_FEM_allowed":False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--p10ek",type=Path,required=True)
    ap.add_argument("--p10en",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    a=json.loads(args.p10ek.read_text(encoding="utf-8"))
    b=json.loads(args.p10en.read_text(encoding="utf-8"))
    output=compare(a,b)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for name,row in output["order9"].items():
        print("P10EQ",name,"alpha20",format(row["alpha20_reduction_percent"],".3f"),
              "alpha17",format(row["alpha17_reduction_percent"],".3f"))
    print("P10EQ_ALPHA_BACKTRACKING_NONMONOTONE_D025_STOP FEM=0")


if __name__=="__main__":main()
