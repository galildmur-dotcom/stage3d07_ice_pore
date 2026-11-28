#!/usr/bin/env python3
"""Independently audit P10PY accepted M8 Bezier h-refinement convergence.

Pure arithmetic over source-only JSON; no mesh generation, FEM or network.
Writes a compact science summary JSON and convergence CSV for publication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ACCEPTED="40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
DEPTHS=13


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--mesh",type=Path,required=True)
    p.add_argument("--summary",type=Path,default=Path("P10PY_M8_ADAPTIVE_SUMMARY_QA.json"))
    p.add_argument("--csv",type=Path,default=Path("P10PY_M8_ADAPTIVE_CONVERGENCE.csv"))
    args=p.parse_args()
    report=json.loads(args.input.read_text(encoding="utf-8"))
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if report["mesh_sha256"]!=ACCEPTED or digest!=ACCEPTED:
        raise ValueError("P10PY rejected M8 identity")
    if report["status"]!="PASS_ADAPTIVE_BEZIER_CURVED_TET10_SOURCE_ONLY":
        raise ValueError("P10PY input did not pass source-only geometry")
    if (report["mesh_changed"] or report["fem_started"] or report["gmsh_generated"]):
        raise ValueError("P10PY attempted a disallowed action")
    if (not report["all_azimuth"] or report["maximum_depth"]!=12 or report["bin_count"]!=48):
        raise ValueError("expected all 48 pole-angle/radial bins and depths 0..12")
    if report["independent_subcell_physical_volume_partition_rel"]>=1e-12:
        raise ValueError("physical volume of split Tet10 was not conserved")

    ident=set()
    for b in report["bins"]:
        key=(b["radial_bin"],b["mu_bin"],b["phi_bin"])
        if key in ident or key[0] not in (0,4) or key[1] not in (0,9) or not 0<=key[2]<12:
            raise ValueError("duplicate/invalid bin")
        ident.add(key)
        records=b["depth_records"]
        if len(records)!=DEPTHS or [r["depth"] for r in records]!=list(range(DEPTHS)):
            raise ValueError("missing depth record")
        count=b["original_possible_Tet10"]
        if count<=0:
            raise ValueError("no possible element in pole bin")
        last_u,last_m=float("inf"),float("inf")
        last_i,last_o=0.,0.
        for r in records:
            inside,outside,unknown=r["certified_inside_sum"],r["certified_outside_sum"],r["uncertain_sum"]
            multi,one,zero=r["multi_quartic_sum"],r["one_quartic_sum"],r["zero_quartic_sum"]
            if abs(inside+outside+unknown-count)>1e-8:
                raise ValueError("reference tetra volume closure failed")
            if abs(multi+one+zero-unknown)>1e-8:
                raise ValueError("unresolved quartic phase closure failed")
            if min(inside,outside,unknown,multi,one,zero)<-1e-12:
                raise ValueError("negative reference measure")
            if (unknown>last_u+1e-9 or multi>last_m+1e-9 or
                inside<last_i-1e-9 or outside<last_o-1e-9):
                raise ValueError("h-refinement did not preserve monotone enclosure")
            last_u,last_m,last_i,last_o=unknown,multi,inside,outside
        if (records[-1]["multi_quartic_sum"]/count>0.005 or
            records[-1]["uncertain_sum"]/count>0.1):
            raise ValueError("depth-12 geometric localization threshold failed")
    if len(ident)!=48:
        raise ValueError("incomplete azimuth coverage")

    rows=[]
    summary={"stage":"P10PY","status":"PASS_ALL_48_POLE_BINS_HREF_GEOMETRY_ONLY",
             "mesh_sha256":digest,"mesh_changed":False,"fem_started":False,
             "gmsh_generated":False,"physical_EDV_not_validated":True,
             "max_depth":12,"all_azimuthal_bins":True,"total_tested_bin_combinations":48,
             "independent_subcell_volume_partition_rel":report["independent_subcell_physical_volume_partition_rel"],
             "metric":"reference-volume fraction of original M8 candidate Tet10-bin pairs",
             "groups":[]}
    for ir in (0,4):
        for im in (0,9):
            bins=[b for b in report["bins"] if b["radial_bin"]==ir and b["mu_bin"]==im]
            n=sum(b["original_possible_Tet10"] for b in bins)
            group={"radial_bin":ir,"mu_bin":im,"candidate_tet_bin_pairs":n,"series":[]}
            for depth in range(DEPTHS):
                agg={key:sum(b["depth_records"][depth][key] for b in bins)
                     for key in ("uncertain_sum","multi_quartic_sum","one_quartic_sum",
                                 "zero_quartic_sum","certified_inside_sum","certified_outside_sum")}
                rec={"depth":depth,
                     "uncertain_reference_fraction":agg["uncertain_sum"]/n,
                     "multi_quartic_reference_fraction":agg["multi_quartic_sum"]/n,
                     "one_quartic_reference_fraction":agg["one_quartic_sum"]/n,
                     "certified_inside_fraction":agg["certified_inside_sum"]/n,
                     "certified_outside_fraction":agg["certified_outside_sum"]/n}
                group["series"].append(rec)
                rows.append(dict(radial_bin=ir,mu_bin=im,candidate_bin_pairs=n,**rec))
            initial=group["series"][0]["multi_quartic_reference_fraction"]
            final=group["series"][-1]["multi_quartic_reference_fraction"]
            group["multi_quartic_reduction_factor"]=initial/final
            summary["groups"].append(group)
    args.summary.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with args.csv.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
    print("P10PY_M8_ALL48_INDEPENDENT_QA_PASS")
    for group in summary["groups"]:
        print("P10PY_AGG r="+str(group["radial_bin"])+" mu="+str(group["mu_bin"])+
              " root="+str(group["candidate_tet_bin_pairs"])+
              " multi0="+str(group["series"][0]["multi_quartic_reference_fraction"])+
              " multi12="+str(group["series"][-1]["multi_quartic_reference_fraction"])+
              " unknown12="+str(group["series"][-1]["uncertain_reference_fraction"]))


if __name__=="__main__":
    main()
