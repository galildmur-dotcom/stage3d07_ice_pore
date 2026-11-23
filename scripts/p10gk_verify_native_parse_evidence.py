#!/usr/bin/env python3
"""Independent read-only P10GK SOURCE preflight evidence audit; no Gmsh/FEM."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/proposals/P10GK_SOUTH_POLE_C1_SOURCE_ONLY_20261123"
EXPECTED_ZIP_SHA="6af4dac68f1335aa714b02702ef7c305624ea46622b067fd5aacee6bde89305f"
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
EXPECTED_GMSH_EXE_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
NAMES={"M0_ROTATED.geo","P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo",
       "sphere_pore_B6_refined_rotated.geo","P10GK_NATIVE_PARSE_ONLY.log",
       "P10GK_SOURCE_REPORT.json","P10GK_SOURCE_POLICY.json",
       "P10GK_SOURCE_SHA256.json"}


def need(cond,msg):
    if not cond:raise ValueError("P10GK_INDEPENDENT_PARSE_STOP: "+msg)


def sha(data):return hashlib.sha256(data).hexdigest()


def verify(path):
    raw=Path(path).read_bytes()
    need(sha(raw)==EXPECTED_ZIP_SHA,"wrong original evidence ZIP digest")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        need(len(names)==len(set(names)) and set(names)==NAMES,"unexpected/duplicate evidence entries")
        need(z.testzip() is None,"ZIP CRC failure")
        pin=json.loads(z.read("P10GK_SOURCE_SHA256.json"))
        policy=json.loads(z.read("P10GK_SOURCE_POLICY.json"))
        report=json.loads(z.read("P10GK_SOURCE_REPORT.json"))
        need(sha(z.read("P10GK_SOURCE_SHA256.json"))==sha((SOURCE/"P10GK_SOURCE_SHA256.json").read_bytes()),
             "release source manifest mismatch")
        need(sha(z.read("P10GK_SOURCE_POLICY.json"))==sha((SOURCE/"P10GK_SOURCE_POLICY.json").read_bytes()),
             "release source policy mismatch")
        for name in ("M0_ROTATED.geo","P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo",
                     "sphere_pore_B6_refined_rotated.geo"):
            need(sha(z.read(name))==pin["files"][name],"GEO differs from immutable source: "+name)
        need(report["revision"]==policy["revision"]==pin["revision"]==
             "P10GK_R1_C1_SOUTH_FOCUS_SOURCE_ONLY","wrong revision")
        need(report["policy"]==policy,"preflight embedded policy differs")
        need(report["status"]=="P10GK_SOURCE_AND_NATIVE_PARSE_ONLY_PASS_NO_MESH_NO_FEM",
             "not a native parse-only PASS")
        need(report["native_parse_only_exit_code"]==0
             and report["native_1d_2d_3d_attempts"]==0
             and report["FEM_attempts"]==0,"unexpected native mesh/FEM activity")
        installed=report["installed"]
        need(installed["gmsh_version"]=="4.15.2"
             and installed["gmsh_exe_sha256"]==EXPECTED_GMSH_EXE_SHA
             and installed["parent_M0_sha256"]==M0_SHA,"wrong native version/baseline")
        qa=report["math_eval_samples"]
        need(qa["sampled_points"]==12221
             and qa["max_analytic_MathEval_ratio_error"]<1e-12
             and qa["factor_min"]==.94 and qa["factor_max"]==1.0
             and qa["C1_seam_tests"]==4
             and qa["native_Gmsh_3d"]==0 and qa["FEM"]==0,
             "source MathEval/C1 tests insufficient")
        log=z.read("P10GK_NATIVE_PARSE_ONLY.log")
        need(sha(log)==report["native_parse_log_sha256"],"Gmsh log tamper")
        txt=log.decode("utf-8",errors="replace")
        need(len(re.findall(r"\bRunning\s+'",txt))==1
             and "-parse_and_exit" in txt and "Gmsh 4.15.2" in txt
             and "Done reading" in txt and "Stopped on" in txt
             and not re.search(r"\bError\s*:",txt),"invalid Gmsh native parse log")
        need(not re.search(r"\b(?:-1|-2|-3)\b|\bMeshing\s+(?:1D|2D|3D)\b",txt),
             "native mesh command appears in parse-only log")
    return {"revision":policy["revision"],"evidence_zip_sha256":sha(raw),
            "original_zip_files":len(names),"zip_crc":"PASS_7_OF_7",
            "source_and_geo_sha256":"EXACT_PINNED_BYTES",
            "native_windows_gmsh_version":installed["gmsh_version"],
            "native_exe_sha256":installed["gmsh_exe_sha256"],
            "native_parse_only_exit_code":0,"native_gmsh_parse_log_sha256":sha(log),
            "source_QA_sampled_points":qa["sampled_points"],
            "max_independent_MathEval_ratio_error":qa["max_analytic_MathEval_ratio_error"],
            "local_size_factor_range":[qa["factor_min"],qa["factor_max"]],
            "C1_seams_tested":qa["C1_seam_tests"],
            "native_new_mesh_attempts":0,"FEM_attempts":0,
            "source_preflight_status":"PASS_NATIVE_PARSE_ONLY",
            "native_3d_meshing_authorized":False,
            "new_HXT10_M1_measured":False,
            "next_step":"SEPARATE_USER_PERMISSION_REQUIRED_FOR_ONE_NEW_3D_MESH_ONLY_ATTEMPT"}


def main():
    p=argparse.ArgumentParser();p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    result=verify(a.evidence)
    if a.out:
        with a.out.open("x",encoding="utf-8") as f:
            json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
    print("P10GK_INDEPENDENT_NATIVE_PARSE_ONLY_PASS_NO_MESH_NO_FEM")
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":main()
