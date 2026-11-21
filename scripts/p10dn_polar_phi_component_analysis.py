#!/usr/bin/env python3
"""P10DN: nonphysical component/azimuth/occupancy audit for H0/M1 signed4D.

Only original ZIP read; no M2 mesh generation or physical solver execution.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import p10dm_verify_real_m1_pair_h0 as pair

OUT = pair.ROOT / "research/evidence/P10DN_M2_COEFFICIENT20_SOURCE_ONLY_20261121/derived"


def group(h0: dict, m1: dict, predicate) -> dict:
    keys = [key for key in h0 if predicate(key)]
    signed = {"h0": {}, "m1": {}, "delta": {}, "L1_delta": {}}
    for f in pair.FIELD + ("total_per_m",):
        av = [float(h0[key][f]) for key in keys]
        bv = [float(m1[key][f]) for key in keys]
        signed["h0"][f] = math.fsum(av)
        signed["m1"][f] = math.fsum(bv)
        signed["delta"][f] = math.fsum(b-a for a, b in zip(av,bv))
        signed["L1_delta"][f] = math.fsum(abs(b-a) for a,b in zip(av,bv))
    signed["paired_bins"] = len(keys)
    signed["mech_qp_h0"] = sum(int(h0[k]["mechanical_qp"]) for k in keys)
    signed["mech_qp_m1"] = sum(int(m1[k]["mechanical_qp"]) for k in keys)
    return signed


def azimuth(h0: dict, m1: dict, predicate) -> list[dict]:
    rows=[]
    for phi in range(12):
        keys = [key for key in h0 if key[3] == phi and predicate(key)]
        rows.append({
            "phi_bin": phi, "paired_bins": len(keys),
            "h0_signed_per_m": math.fsum(float(h0[k]["total_per_m"]) for k in keys),
            "m1_signed_per_m": math.fsum(float(m1[k]["total_per_m"]) for k in keys),
            "delta_signed_per_m": math.fsum(float(m1[k]["total_per_m"])
                                              - float(h0[k]["total_per_m"]) for k in keys),
            "delta_L1_per_m": math.fsum(abs(float(m1[k]["total_per_m"])
                                            - float(h0[k]["total_per_m"])) for k in keys),
            "min_mechanical_qp": sum(min(int(h0[k]["mechanical_qp"]),
                                         int(m1[k]["mechanical_qp"])) for k in keys),
        })
    return rows


def rotational_fourfold_residual(rows: list[dict], field: str) -> float:
    # For cubic/square distant boundaries a C4 component may remain.
    value=[float(row[field]) for row in rows]
    means=[sum(value[j] for j in range(mod,12,3))/4 for mod in range(3)]
    numerator=math.fsum(abs(value[j]-means[j%3]) for j in range(12))
    denominator=math.fsum(abs(v) for v in value)
    return numerator / max(denominator,1.e-30)


def sparse(h0: dict, m1: dict, predicate) -> dict:
    keys=[k for k in h0 if predicate(k)]
    full=sum(abs(float(m1[k]["total_per_m"])-float(h0[k]["total_per_m"])) for k in keys)
    results={"total_bins":len(keys),"L1_delta_per_m":full}
    for threshold in (5,10,20):
        few=[k for k in keys if min(int(h0[k]["mechanical_qp"]),
                                    int(m1[k]["mechanical_qp"])) < threshold]
        lost=sum(abs(float(m1[k]["total_per_m"])-float(h0[k]["total_per_m"]))
                 for k in few)
        results[f"min_mech_qp_below_{threshold}_bins"]=len(few)
        results[f"min_mech_qp_below_{threshold}_L1_fraction"] = lost/max(full,1.e-30)
    return results


def main() -> None:
    pair.original_zip(pair.H0_DEFAULT,pair.H0_ZIP_SHA,
                      {"P10DD_RUN_MANIFEST.json","P10DD_SOLVER_STDOUT_STDERR.txt"})
    pair.original_zip(pair.M1_DEFAULT,pair.M1_ZIP_SHA,
                      {"P10DL_RUN_MANIFEST.json","P10DL_SOLVER_STDOUT_STDERR.txt"})
    hmod=pair.load_module(pair.ROOT/"research/proposals/P10DD_M0_H0_FULL4D_20261121/P10DD_audit_evidence.py","p10dn_h0")
    mmod=pair.load_module(pair.ROOT/"research/proposals/P10DK_M1_FULL4D_SOURCE_ONLY_20261121/P10DK_audit_evidence.py","p10dn_m1")
    hread,mread=hmod.Reader(pair.H0_DEFAULT),mmod.Reader(pair.M1_DEFAULT)
    try:
        hmod.audit(hread)
        mmod.audit(mread)
        h0,m1=pair.comparable_keys(hread.csv(pair.FULL4D_NAME),
                                    mread.csv(pair.FULL4D_NAME))
    finally:
        hread.close();mread.close()
    polar=lambda k:k[2] in (0,9)
    wall=lambda k:k[1]<=2
    late=lambda k:k[0]>=5
    groups={
        "all":group(h0,m1,lambda k:True),
        "polar_all":group(h0,m1,polar),
        "wall_all":group(h0,m1,wall),
        "late_all":group(h0,m1,late),
        "polar_wall_all":group(h0,m1,lambda k:polar(k) and wall(k)),
        "polar_wall_late":group(h0,m1,lambda k:polar(k) and wall(k) and late(k)),
        "south_polar_wall_late":group(h0,m1,lambda k:k[2]==0 and wall(k) and late(k)),
        "north_polar_wall_late":group(h0,m1,lambda k:k[2]==9 and wall(k) and late(k)),
    }
    phis={
        "polar_wall_all":azimuth(h0,m1,lambda k:polar(k) and wall(k)),
        "polar_wall_late":azimuth(h0,m1,lambda k:polar(k) and wall(k) and late(k)),
        "south_wall_late":azimuth(h0,m1,lambda k:k[2]==0 and wall(k) and late(k)),
        "north_wall_late":azimuth(h0,m1,lambda k:k[2]==9 and wall(k) and late(k)),
    }
    fourfold={name:{field:rotational_fourfold_residual(rows,field)
                    for field in ("h0_signed_per_m","m1_signed_per_m",
                                  "delta_signed_per_m")}
              for name,rows in phis.items()}
    confidence={
        "polar_wall_late":sparse(h0,m1,lambda k:polar(k) and wall(k) and late(k)),
        "polar_wall_all":sparse(h0,m1,lambda k:polar(k) and wall(k)),
        "all":sparse(h0,m1,lambda k:True),
    }
    result={
        "protocol":"P10DN_R1_NONPHYSICAL_M0_M1_COMPONENT_PHI_QP_AUDIT",
        "h0_original_sha256":pair.H0_ZIP_SHA,
        "m1_original_sha256":pair.M1_ZIP_SHA,
        "groups":groups,"azimuth":phis,"fourfold_rotational_residual":fourfold,
        "occupancy":confidence,
        "interpretation_limit":"pair of signed discretized bin differences, NOT raw pointwise or estimated continuum error; φ resolution 12 coarse sectors, sparse pole bins",
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"P10DN_POLAR_PHI_COMPONENT_AUDIT.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for name,rows in phis.items():
        with (OUT/("P10DN_PHI_"+name.upper()+".csv")).open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
            writer.writeheader();writer.writerows(rows)
    print("P10DN_POLAR_PHI_COMPONENT_AUDIT_OK bins=7200 no_FEM=1")
    for name in ("all","polar_wall_all","polar_wall_late"):
        g=groups[name]
        print(name,"signed_delta",g["delta"]["total_per_m"],
              "mech_explicit",g["delta"][pair.FIELD[0]],
              "mech_equilibrium",g["delta"][pair.FIELD[1]],
              "mech_history",g["delta"][pair.FIELD[2]],
              "thermal_mass",g["delta"][pair.FIELD[3]],
              "thermal_diff",g["delta"][pair.FIELD[4]])
    print("SPARSE",confidence["polar_wall_late"])
    for name,rows in phis.items():
        print("PHI",name,"fourfold_delta_residual",fourfold[name]["delta_signed_per_m"],
              "sector_signed_deltas",[round(x["delta_signed_per_m"],5) for x in rows])


if __name__=="__main__":
    main()
