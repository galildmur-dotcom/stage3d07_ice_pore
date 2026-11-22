#!/usr/bin/env python3
"""P10EP: verify exact P10EN original native evidence and M1/M2 Tet10 spatial ratio.

Read-only on original MSH2 and evidence; no Gmsh, FEM, cache, marker or raw
mesh publication. Reuses independently tested analytic Tet10 basis/27QP P10ED.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from p10ed_verify_original_m1_m2_raw_spatial import (
    CAD_VOL, M1_SHA, RAD, POL, audit_mesh, compare, digest, ensure,
    parse_msh2, rule27, selftest, spatial_rule,
)

REV = "P10EN_R1_ONE_NATIVE_3D_M2_ALPHA17_BAND15_25_MESH_ONLY"
F6_SHA = "b54db4fe70c8661fe4faa70985893ca0a3b0c01ff619d3727f2cb8030fe3a0e6"
M2_RAW = "RAW/P10EA_M2_CANDIDATE.msh"
LIMITS = (.75, .85)
REQUIRED = {"P10EA_RUN_MANIFEST.json", "P10EA_RESULT.txt", "P10EA_GMSH_FULL.log",
            "QA/P10EA_M1_M2_GEOMETRY_QA.json", "QA/P10EN_ALPHA17_GEOMETRY_AND_TARGET_CONTRACT.json",
            "QA/P10EN_ALPHA17_9_ZONE_COMPARISON.csv", "GEO/B_EXACT_INLINE_F6.geo", M2_RAW}


def source_evidence(evidence: Path, m2: Path) -> dict:
    with zipfile.ZipFile(evidence) as z:
        ensure(z.testzip() is None and set(z.namelist()) >= REQUIRED,
               "P10EN archive CRC/required source and raw MSH")
        manifest = json.loads(z.read("P10EA_RUN_MANIFEST.json"))
        qa = json.loads(z.read("QA/P10EA_M1_M2_GEOMETRY_QA.json"))
        target = json.loads(z.read("QA/P10EN_ALPHA17_GEOMETRY_AND_TARGET_CONTRACT.json"))
        rows = list(csv.DictReader(io.StringIO(
            z.read("QA/P10EN_ALPHA17_9_ZONE_COMPARISON.csv").decode("utf-8"))))
        raw_sha = hashlib.sha256(z.read(M2_RAW)).hexdigest()
        geo_sha = hashlib.sha256(z.read("GEO/B_EXACT_INLINE_F6.geo")).hexdigest()
        log = z.read("P10EA_GMSH_FULL.log").decode("utf-8")
        result = z.read("P10EA_RESULT.txt").decode("utf-8").replace("\r\n", "\n")
    ensure(manifest["revision"] == REV and manifest["status"] ==
           "P10EN_M2_GEOMETRY_QA_OK_ADAPTIVITY_PENDING_NO_FEM" and
           manifest["mode"] == "ONE_M2_3D" and
           manifest["alpha"] == .17 and
           manifest["realized_acceptance_kappa_one_volume_ratio"] == list(LIMITS) and
           manifest["original_m1_sha256"] == M1_SHA and
           manifest["m1_sha256"] == M1_SHA and
           manifest["f6_sha256"] == geo_sha == F6_SHA,
           "P10EN exact source/M1/alpha identity")
    ensure(manifest["native_1d_2d_attempts"] == 0 and
           manifest["native_3d_attempts"] == 1 and
           manifest["physical_FEM_attempts"] == 0 and
           manifest["native_3d_result"]["exit_code"] == 0 and
           manifest["quality_audit_result"]["exit_code"] == 0,
           "bounded native one-shot/QA and FEM=0")
    ensure(raw_sha == manifest["m2_mesh_sha256"] == qa["m2_sha256"] == digest(m2) and
           m2.stat().st_size == manifest["m2_mesh_bytes"] and
           qa["m1_sha256"] == M1_SHA and
           qa["m1_tet10"] == 9736 and qa["m2_tet10"] == 10020 and
           qa["m1_pore_tri6"] == 178 and qa["m2_pore_tri6"] == 192 and
           qa["m1_curved_qp_nonpositive"] == 0 and qa["m2_curved_qp_nonpositive"] == 0 and
           not qa["geometry_issues"], "P10EN original raw SHA, geometry or inventory")
    ensure(target["new_actual_GEO_target_coefficient"] == .17 and
           target["new_alpha17_target_volume_bounds"] == [.83, 1.] and
           target["realized_kappa1_acceptance_ratio_bounds"] == list(LIMITS) and
           target["nine_spatial_zones_checked"] == 9 and
           not target["m2_geometry_accepted_for_physical_FEM"] and
           "FEM=0" in result and "STOP_REASON=\n" in result,
           "alpha17 QA overlay or result still gated")
    ensure(len(rows)==9 and
           sum(int(row["m1_tet10"]) for row in rows)==qa["m1_tet10"] and
           sum(int(row["m2_tet10"]) for row in rows)==qa["m2_tet10"] and
           all(abs(float(row["P10EN_model_mean_target_ratio_alpha17"])-
                   (1.-.17*float(row["m1_mean_kappa_centroid"])))<2e-12
               for row in rows), "alpha17 nine fixed-zone target/count closure")
    ensure("Meshing surface 7 (Sphere, Delaunay)" in log and
           "Meshing surface 8 (Sphere, Delaunay)" in log and
           "Done meshing 3D" in log and "Optimization succeeded" in log and
           "Error   :" not in log,"3D native Delaunay/optimization log")
    return manifest


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence",type=Path)
    ap.add_argument("--m1",type=Path)
    ap.add_argument("--m2",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    N,D,W=rule27()
    selftest(N,D,W)
    if args.selftest:
        print("P10EP_TET10_SYNTHETIC_OK affine=PASS inverted=STOP FEM=0")
        return 0
    ensure(all(p is not None for p in (args.evidence,args.m1,args.m2,args.out)),
           "--evidence --m1 --m2 --out required")
    ensure(args.m1.name == "P10DG_M1_CANDIDATE.msh" and
           args.m2.name == "P10EA_M2_CANDIDATE.msh" and
           args.m1.resolve()!=args.m2.resolve() and digest(args.m1)==M1_SHA,
           "original private source M1 or P10EN M2 wrong")
    manifest=source_evidence(args.evidence,args.m2)
    a=parse_msh2(args.m1,M1_SHA)
    b=parse_msh2(args.m2,manifest["m2_mesh_sha256"])
    ensure(len(a["tet10"])==9736 and len(a["pore_tri6"])==178 and
           len(b["tet10"])==10020 and len(b["pore_tri6"])==192,
           "raw Tet10/Tri6 inventory")
    sa,rowsa,auxa=audit_mesh(a,"M1",N,D,W)
    sb,rowsb,auxb=audit_mesh(b,"P10EN_M2",N,D,W)
    ensure(max(abs(s["curved_CAD_rel_error"]) for s in (sa,sb))<.005,
           "real curved volume vs CAD")
    comparison=compare(rowsa,rowsb,auxa,auxb)
    refinements={}
    for order in (3,5,7,9):
        ra=spatial_rule(a,auxa["vol"],order)
        rb=spatial_rule(b,auxb["vol"],order)
        refinements[str(order)]={
            "qp_per_tet":order**3,
            "M2_over_M1_effective_tet_volume_9_zones":[
                y/x for x,y in zip(ra["qp_effective_tet_volume_m3"],
                                    rb["qp_effective_tet_volume_m3"])],
            "M2_over_M1_effective_tet_volume_18_north_south_zones":[
                y/x for x,y in zip(ra["qp_north_south_effective_tet_volume_m3"],
                                    rb["qp_north_south_effective_tet_volume_m3"])],
            "M2_over_M1_spatial_region_volume_9_zones":[
                y/x for x,y in zip(ra["qp_spatial_volumes_m3"],rb["qp_spatial_volumes_m3"])],
        }
    region=[refinements[str(order)]["M2_over_M1_effective_tet_volume_9_zones"][0]
            for order in (3,5,7,9)]
    north=[refinements[str(order)]["M2_over_M1_effective_tet_volume_18_north_south_zones"][0]
           for order in (3,5,7,9)]
    south=[refinements[str(order)]["M2_over_M1_effective_tet_volume_18_north_south_zones"][1]
           for order in (3,5,7,9)]
    ensure((comparison[0]["radial_zone"],comparison[0]["polar_zone"]) ==
           (RAD[0],POL[0]),"priority kappa=1 geometry zone")
    indicator_stable=max(abs(region[-1]-region[-2]),abs(north[-1]-north[-2]),
                         abs(south[-1]-south[-2]))<=.02
    in_band=all(LIMITS[0]<=x<=LIMITS[1] for x in (region[-1],north[-1],south[-1]))
    status=("FIXED_REGION_BAND_PASS_NEEDS_INDEPENDENT_SMOOTHNESS_AND_FEM_REVIEW"
            if in_band and indicator_stable else "D025_FIXED_REGION_BAND_OR_QP_STABILITY_STOP_NO_FEM")
    output={"protocol":"P10EP_EXACT_P10EN_RAW_M2_FIXED_3D_CURVED_QP_AUDIT",
            "status":status,"physical_FEM_allowed":False,
            "no_new_Gmsh_no_FEM_no_markers":True,
            "raw_meshes_not_published":True,"source_sha256":{
                 "M1":M1_SHA,"P10EN_M2":manifest["m2_mesh_sha256"],
                 "P10EN_F6":F6_SHA},
            "cad_volume_m3":CAD_VOL,"M1":sa,"P10EN_M2":sb,
            "refinements":refinements,
            "kappa_one_priority":{
                "physical_zone":"d=0..100um, abs(mu)>=0.8",
                "acceptance_M2_over_M1":list(LIMITS),
                "order_3_5_7_9_both_poles":region,
                "order_3_5_7_9_north":north,"order_3_5_7_9_south":south,
                "order9_in_band_both_and_north_and_south":in_band,
                "order7_to9_max_absolute_change":max(abs(region[-1]-region[-2]),
                    abs(north[-1]-north[-2]),abs(south[-1]-south[-2])),
                "order7_to9_indicator_stable_0p02":indicator_stable,
            },
            "limitations":["spatial region effective volume is not paired Tet10 pointwise",
               "piecewise region indicator has quadrature discretization error",
               "target alpha17 does not guarantee realized geometry",
               "passing geometry/band alone does not prove analytic shape-derivative convergence"],
            "next":"D-025 scientific geometry/adaptivity manual review; physical forward/adjoint only after GO"}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"P10EP_P10EN_RAW_FIXED_3D_QP_AUDIT.json").write_text(
        json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (args.out/"P10EP_P10EN_9_ZONE_COMPARE.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(comparison[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(comparison)
    print("P10EP_ORIGINAL_P10EN_RAW_SPATIAL_QP_DIAGNOSTIC",status,
          "north="+format(north[-1],".7f"),"south="+format(south[-1],".7f"),
          "both="+format(region[-1],".7f"),"FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
