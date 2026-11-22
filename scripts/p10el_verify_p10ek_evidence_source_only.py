#!/usr/bin/env python3
"""Read-only provenance/geometry verification for one original P10EK evidence ZIP.

Does not contain raw M2, cannot establish the finite spatial 20% gate.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import zipfile

M1="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
B="2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5"
NAMES={"P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt","P10EA_GMSH_FULL.log",
       "QA/P10EA_M1_M2_GEOMETRY_QA.json","QA/P10EA_M1_M2_9_ZONE_VOLUME_COMPARISON.csv",
       "GEO/B_EXACT_INLINE_F6.geo","GEO/sphere_pore_B6_refined.geo"}


def need(ok,why):
    if not ok:raise ValueError("P10EL_STOP: "+why)


def verify(path:Path):
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None and set(z.namelist())>=NAMES,"archive CRC and required files")
        need(not any(name.lower().endswith(".msh") for name in z.namelist()),
             "unexpected raw MSH in source-only evidence ZIP")
        manifest=json.loads(z.read("P10EA_RUN_MANIFEST.json"))
        report=json.loads(z.read("QA/P10EA_M1_M2_GEOMETRY_QA.json"))
        result=z.read("P10EA_RESULT.txt").decode("utf-8")
        log=z.read("P10EA_GMSH_FULL.log").decode("utf-8")
        csv_rows=list(csv.DictReader(io.StringIO(z.read("QA/P10EA_M1_M2_9_ZONE_VOLUME_COMPARISON.csv").decode("utf-8"))))
        import hashlib
        geo_sha=hashlib.sha256(z.read("GEO/B_EXACT_INLINE_F6.geo")).hexdigest()
    native=manifest["native_3d_result"]
    qa=manifest["quality_audit_result"]
    need(manifest["revision"]=="P10EK_R1_ONE_NATIVE_3D_M2_ALG5_MESH_ONLY" and
         manifest["mode"]=="ONE_M2_3D" and
         manifest["m1_sha256"]==M1 and
         manifest["f6_sha256"]==B and geo_sha==B,"source/M1/Alg5 SHA")
    need(manifest["native_3d_attempts"]==1 and
         manifest["native_1d_2d_attempts"]==0 and
         manifest["physical_FEM_attempts"]==0 and
         native["exit_code"]==0 and qa["exit_code"]==0,"bounded native/QP execution")
    need("Meshing surface 7 (Sphere, Delaunay)" in log and
         "Meshing surface 8 (Sphere, Delaunay)" in log and
         "Done meshing 3D" in log and "Optimization succeeded" in log and
         "Error   :" not in log,"native Gmsh alg5 3D and optimizer log")
    need(report["status"]=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM" and
         report["m1_sha256"]==M1 and
         report["m2_sha256"]==manifest["m2_mesh_sha256"] and
         report["m1_curved_qp_nonpositive"]==0 and
         report["m2_curved_qp_nonpositive"]==0 and
         not report["geometry_issues"] and
         not report["m2_geometry_accepted_for_physical_FEM"],"geometry PASS/FEM still gated")
    need("FEM=0" in result and "STOP_REASON=\n" in result.replace("\r\n","\n"),"result inconsistency")
    need(len(csv_rows)==9,"9 spatial bins")
    need(sum(int(r["m1_tet10"]) for r in csv_rows)==report["m1_tet10"] and
         sum(int(r["m2_tet10"]) for r in csv_rows)==report["m2_tet10"],"spatial-bin count closure")
    chosen=[r for r in csv_rows if r["radial_zone"]=="0_100um" and r["polar_zone"]=="polar_abs_mu_ge_0p8"]
    need(len(chosen)==1,"high-priority polar zone")
    p=chosen[0]
    observed=float(p["observed_unpaired_median_curved27qp_volume_ratio_m2_over_m1"])
    target=float(p["model_mean_target_volume_ratio_at_m1_centroids"])
    output={"protocol":"P10EL_ORIGINAL_P10EK_EVIDENCE_SOURCE_ONLY",
            "status":"GEOMETRY_PASS_LOCAL_ADAPTATION_UNRESOLVED_NO_FEM",
            "m2_sha256_claimed_by_windows_manifest":manifest["m2_mesh_sha256"],
            "m2_raw_mesh_present_in_evidence":False,
            "m2_raw_sha_independently_verified":False,
            "native_3d_attempts":1,"native_exit_code":0,
            "native_wall_s":native["polled_wall_s"],
            "native_polled_private_bytes":native["polled_peak_private_bytes"],
            "qa_exit_code":qa["exit_code"],"qa_wall_s":qa["polled_wall_s"],
            "m1_tet10":report["m1_tet10"],"m2_tet10":report["m2_tet10"],
            "m1_pore_tri6":report["m1_pore_tri6"],"m2_pore_tri6":report["m2_pore_tri6"],
            "nonpositive_curved27qp_jacobians":{"m1":0,"m2":0},
            "polar_nearwall_0_100um_abs_mu_ge_0p8":{
                "m1_tet10":int(p["m1_tet10"]),"m2_tet10":int(p["m2_tet10"]),
                "target_local_volume_ratio":target,
                "observed_unpaired_curved27qp_median_ratio":observed,
                "diagnostic_gap":observed-target,
                "proves_20pct_volume_cap_violation":False},
            "independent_raw_fixed_spatial_qp_test":"PENDING_ORIGINAL_M2_MSH",
            "physical_fem_allowed":False,
            "next_required_input":"Original P10EK run P10EA_M2_CANDIDATE.msh (private)"}
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    output=verify(args.evidence)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10EL_EVIDENCE_GEOMETRY_PASS_LOCAL_ADAPTIVITY_PENDING_NO_FEM",output["polar_nearwall_0_100um_abs_mu_ge_0p8"])


if __name__=="__main__":main()
