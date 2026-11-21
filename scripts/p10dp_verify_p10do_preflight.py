#!/usr/bin/env python3
"""Independent non-FEM SHA/CRC/protocol review of original P10DO first-button ZIP.

All values are read from archived Windows evidence; raw Windows M1.msh,
the machine's one-shot markers, and native EXE are not available locally.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path, PureWindowsPath
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/"research/evidence/P10DP_P10DO_READONLY_M1_GEO_20261121/input/P10DO_EVIDENCE.zip"
REPORT=ROOT/"research/evidence/P10DP_P10DO_READONLY_M1_GEO_20261121/derived/P10DP_PREFLIGHT_AUDIT.json"
SHA="07e2deabd25288ac422f27b72f00a551d68088e7e7ad731efe5e900a9750cdc9"
PACKAGE=ROOT/"research/packages/P10DO_R1_M2_ONE_SHOT_GMSH_ONLY_WINDOWS_20261121.zip"
PACKAGE_SHA="6c6f4f574e6a8c436d8319e059e5d1341c8ecbeda5ba38fbc2587c03abb15535"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
MEMBERS={"P10DO_RUN_MANIFEST.json","P10DO_RESULT.txt",
         "P10DO_M1_COEFFICIENT_SUMMARY.json"}


def require(ok: bool,why: str) -> None:
    if not ok:
        raise ValueError("P10DP_STOP: "+why)


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def audit_values(m: dict, s: dict, result: str) -> dict:
    require(m.get("protocol")=="P10DO_R1_M2_GRADED_KAPPA20_MESH_ONLY", "wrong protocol")
    require(m.get("status")=="P10DO_READ_ONLY_M1_LABEL_AND_GEO_PARSE_OK", "preflight did not PASS")
    require(m.get("physical_FEM_runs")==0 and m.get("mesh_only") is True,
            "unexpected physical run")
    require(m.get("source_pin_count")==18 and m.get("m2_source")=="P10DN_C1_KAPPA20",
            "wrong source inventory or coefficient version")
    require(m.get("m1_sha256")==M1_SHA and s.get("m1_sha256")==M1_SHA,
            "accepted exact M1 SHA mismatch")
    require(PureWindowsPath(m["m1_path"]).name=="P10DG_M1_CANDIDATE.msh",
            "wrong M1 basename")
    require(s.get("nodes")==14145 and s.get("tet10")==9736 and
            s.get("pore_tri6")==178,"wrong M1 labels/counts")
    counts=s.get("label_counts",{})
    require(set(counts)=={"zero","one","intermediate"} and
            all(type(v) is int and v>=0 for v in counts.values()) and
            sum(counts.values())==9736,"incomplete or invalid M1 κ labeling")
    require(counts["one"]>0 and counts["intermediate"]>0 and counts["zero"]>0,
            "no transition κ distribution observed")
    require(0<=s.get("mean_kappa_at_linear_centroid",-1)<=1,
            "invalid κ centroid mean")
    require(s.get("target_relative_volume_min")==.8 and
            s.get("target_relative_volume_max")==1 and
            abs(s.get("target_relative_size_min",0)-.8**(1/3))<1e-14,
            "incorrect 0..20% target volume policy")
    require(m.get("native_GEO_parse_exit")==0 and m.get("gmsh_version_stdout")=="4.15.2",
            "native Windows Gmsh parser/version not proven")
    require(m.get("gmsh_path","").endswith("gmsh.exe") and
            len(m.get("gmsh_sha256",""))==64,"native gmsh path/digest absent")
    parse=m.get("native_GEO_parse_log_tail","")
    require("Done reading" in parse and "P10DN_M2_FIELD20.geo" in parse and
            "Error" not in parse,"native GEO parse log incomplete/error")
    test=m.get("synthetic_QA_stdout_tail","")
    for marker in ("P10CK_CURVED_TET10_SYNTHETIC_UNIT_OK",
                   "P10DE_M1_MESH_QA_SYNTHETIC_OK",
                   "P10DN_M2_20PCT_FIELD_SELFTEST_OK",
                   "P10DO_M2_MESH_QA_SYNTHETIC_OK"):
        require(marker in test,"missing synthetic PASS: "+marker)
    require(m.get("available_RAM_before_bytes",0)>16*1024**3 and
            m.get("available_disk_before_bytes",0)>4*1024**3,
            "insufficient measured available resources")
    require(m.get("wall_limit_s")==900 and
            m.get("private_limit_bytes")==8*1024**3 and
            m.get("mesh_limit_bytes")==750*1024**2,
            "unexpected mesh resource limits")
    require(not any(k in m for k in ("native_Gmsh_argv","native_exit_code",
                                     "m2_mesh_sha256","m2_mesh_path","qa_exit_code")),
            "evidence shows a launched mesh rather than safe preflight")
    require("RESULT=P10DO_READ_ONLY_M1_LABEL_AND_GEO_PARSE_OK" in result and
            "FEM_RUNS=0" in result and "M2_SHA256=UNKNOWN" in result and
            "NATIVE_GMSH_EXIT=UNKNOWN" in result and "STOP_REASON=\n" in result,
            "result and manifest disagree")
    start=datetime.fromisoformat(m["started_utc"])
    finish=datetime.fromisoformat(m["finished_utc"])
    duration=(finish-start).total_seconds()
    require(0<=duration<=300, "invalid preflight elapsed time")
    return {"protocol":"P10DP_P10DO_READONLY_PREFLIGHT_INDEPENDENT_AUDIT",
            "status":"P10DP_WINDOWS_M1_LABEL_AND_GEO_PARSE_VERIFIED",
            "m1_sha256":M1_SHA,"m1_nodes":s["nodes"],
            "m1_tet10":s["tet10"],"m1_pore_tri6":s["pore_tri6"],
            "label_counts":counts,
            "nonzero_centroid_kappa_tets":counts["one"]+counts["intermediate"],
            "nonzero_centroid_kappa_fraction":(counts["one"]+counts["intermediate"])/9736,
            "full_centroid_kappa_fraction":counts["one"]/9736,
            "mean_kappa_at_linear_centroid":s["mean_kappa_at_linear_centroid"],
            "native_gmsh_version":"4.15.2","native_geo_parse_exit":0,
            "preflight_duration_s":duration,
            "native_gmsh_m2_meshing":"NOT_LAUNCHED",
            "native_m2_27qp_validation":"NOT_PERFORMED",
            "physical_FEM_runs":0,
            "one_shot_marker_creation":"NOT_IN_FIRST_BUTTON_CODE_PATH_NOT_DIRECTLY_READ_ON_WINDOWS",
            "independence_limit":"raw M1.msh and native gmsh.exe not supplied, SHA/counts based on Windows JSON; source package pinned",
            "interpretation":"κ(x) smooth globally; centroid counts only, not number of changed elements after remesh",
            "second_mesh_only_button":"PRECONDITIONS_VERIFIED_BUT_NOT_EXECUTED"}


def main() -> None:
    require(sha(ORIGINAL)==SHA,"original user ZIP SHA mismatch")
    require(sha(PACKAGE)==PACKAGE_SHA,"published source ZIP SHA mismatch")
    with zipfile.ZipFile(ORIGINAL) as z:
        require(z.testzip() is None and set(z.namelist())==MEMBERS and
                len(z.namelist())==3,"original Windows ZIP CRC/members")
        m=json.loads(z.read("P10DO_RUN_MANIFEST.json"))
        s=json.loads(z.read("P10DO_M1_COEFFICIENT_SUMMARY.json"))
        txt=z.read("P10DO_RESULT.txt").decode("utf-8").replace("\r\n","\n")
    a=audit_values(m,s,txt)
    negative=0
    for kind in ("label_total","wrong_mesh_sha","wrong_status","hidden_mesh",
                 "missing_geo_parse","wrong_target_size"):
        badm,bads=deepcopy(m),deepcopy(s)
        if kind=="label_total":bads["label_counts"]["zero"]+=1
        if kind=="wrong_mesh_sha":badm["m1_sha256"]="0"*64
        if kind=="wrong_status":badm["status"]="P10DO_STOP_NO_FEM"
        if kind=="hidden_mesh":badm["native_exit_code"]=0
        if kind=="missing_geo_parse":badm["native_GEO_parse_exit"]=2
        if kind=="wrong_target_size":bads["target_relative_size_min"]=.8
        try:
            audit_values(badm,bads,txt)
        except ValueError:
            negative+=1
        else:
            raise RuntimeError("negative case accepted: "+kind)
    a["original_user_zip_sha256"]=SHA
    a["source_zip_sha256"]=PACKAGE_SHA
    a["original_zip_crc_members"]="3/3_PASS"
    a["synthetic_negative_cases_rejected"]=negative
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(a,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10DP_P10DO_ORIGINAL_PREFLIGHT_AUDIT_OK zip_sha=PASS CRC3/3 "
          "source_zip_sha=PASS M1_exact_manifest=PASS gmsh_native_parse=PASS "
          "M1_tet10=9736 kappa_positive_tets="+str(a["nonzero_centroid_kappa_tets"])+
          " kappa_full_tets="+str(a["label_counts"]["one"])+
          " negative_cases=6/6 mesh_M2=NOT_LAUNCHED FEM=0")


if __name__=="__main__":
    main()
