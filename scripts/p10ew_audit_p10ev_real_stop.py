#!/usr/bin/env python3
"""Independent P10EV user evidence audit; never runs any Gmsh or FEM.

Private uploaded ZIP is input only, not published in the source repository.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"research/evidence/P10EW_STRCAT_RESCUE_20261122/derived/P10EW_P10EV_REAL_PARSE_STOP_AUDIT.json"
INPUT_SHA="eaa181421a55d4cf23a3393466fff045baf8e1d66dd7eda19d2dd62c211fe752"
EXPECTED={
    "P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt","P10EA_STOP_TRACE.txt",
    "A_ORIGINAL_M1_FIELD2_PARSE.log","B_EXACT_INLINE_F6_PARSE.log",
    "GEO/A_ORIGINAL_M1_FIELD2.geo","GEO/B_EXACT_INLINE_F6.geo",
    "GEO/sphere_pore_B6_refined.geo",
    "SOURCE/P10EU_C1_GMSH_SOURCE_AUDIT.json",
    "SOURCE/P10EV_R1_SOURCE_SHA256.json"}
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GEO_SHA="4c4a4aeb4f97bfec350e1e057a57e275d436c09d63a02438a8acfe4ad386253a"
CAD_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EW_EVIDENCE_STOP: "+why)


def audit(raw: bytes) -> dict:
    need(sha(raw)==INPUT_SHA,"uploaded original user ZIP exact SHA")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        need(z.testzip() is None and len(names)==10 and set(names)==EXPECTED,
             "user evidence CRC10 and exact original inventory")
        files={name:z.read(name) for name in names}
    j=json.loads(files["P10EA_RUN_MANIFEST.json"])
    pin=json.loads(files["SOURCE/P10EV_R1_SOURCE_SHA256.json"])
    eu=json.loads(files["SOURCE/P10EU_C1_GMSH_SOURCE_AUDIT.json"])
    result=files["P10EA_RESULT.txt"].decode()
    a=files["A_ORIGINAL_M1_FIELD2_PARSE.log"].decode(errors="replace")
    b=files["B_EXACT_INLINE_F6_PARSE.log"].decode(errors="replace")
    geo=files["GEO/B_EXACT_INLINE_F6.geo"]
    need(j["revision"]==pin["revision"]==
         "P10EV_R1_ONE_AUTHORIZED_C1_JOINT_3D_M2_MESH_ONLY" and
         j["status"]=="P10EV_STOP_NO_FEM" and j["mode"]=="SAFE_PREFLIGHT",
         "revision, result and mode")
    need(j["m1_sha256"]==M1_SHA==pin["m1_sha256"] and
         j["new_geo_sha256"]==GEO_SHA==pin["new_geo_sha256"]==
         eu["generated_GEO_sha256"]==sha(geo) and
         sha(files["GEO/sphere_pore_B6_refined.geo"])==CAD_SHA,
         "correct old accepted M1, old F6 and canonical CAD pins")
    need(j["native_parse_attempts"]==2 and
         j["native_parse_passed"]==["A_ORIGINAL_M1_FIELD2"] and
         j["native_1d_2d_attempts"]==j["native_3d_attempts"]==
         j["physical_FEM_attempts"]==0 and
         "NATIVE_M2_3D_ATTEMPTS=0" in result and
         "M2_SHA256=UNKNOWN" in result and "FEM=0" in result,
         "exactly two safe parser calls, no new M2 and no FEM")
    need("Error" not in a and
         "String too long" in b and "End of file in string" in b and
         re.search(r"syntax error",b) is not None and
         "String too long" in j["stop_reason"] and
         "String too long" in result,
         "native parse A passes and B fails on lexical string limit")
    exp=re.search(rb'Field\[6\]\.F = "([^"\r\n]+)";',geo)
    need(exp is not None and len(exp.group(1))==4198 and
         b"StrCat" not in geo and
         eu["expression_characters"]==4198,
         "exact oversized original single literal 4198")
    need(pin["files"]["P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo"]==GEO_SHA
         and eu["nested_MathEval_count"]==0 and
         j["math_points"]==17075 and
         j["gmsh_sha256"]==
         "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1",
         "source and Gmsh4.15.2 binary evidence")
    return {
        "protocol":"P10EW_INDEPENDENT_ORIGINAL_P10EV_NATIVE_PARSE_STOP",
        "uploaded_zip_sha256":sha(raw),
        "uploaded_zip_crc_members":10,
        "M1_SHA256":M1_SHA,"old_P10EU_GEO_SHA256":GEO_SHA,
        "original_field_expression_characters":len(exp.group(1)),
        "native_Gmsh_version_from_pinned_binary":"4.15.2",
        "native_parse_attempts":2,
        "parse_A_original_M1_field2":"PASS",
        "parse_B_original_P10EU_inline_C1":"STOP_STRING_TOO_LONG",
        "native_mesh_3d_attempts":0,"FEM_attempts":0,
        "new_M2":"NONE", "one_authorized_3d_attempt_consumed":False,
        "real_D025":"UNKNOWN",
        "correction":"StrCat of seven <=600-character GEO quoted literals reconstructs original 4198-character expression",
        "status":"P10EV_REAL_PREFLIGHT_STOP_PARSER_LEXER_LIMIT_NO_M2_NO_FEM"
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--write",action="store_true")
    p.add_argument("--verify",action="store_true")
    a=p.parse_args()
    need(a.write!=a.verify,"choose --write or --verify")
    j=audit(a.evidence.read_bytes())
    data=(json.dumps(j,indent=2,ensure_ascii=False)+"\n").encode()
    if a.write:
        if OUT.exists():
            need(OUT.read_bytes()==data,"refuse overwrite different evidence audit")
        else:
            OUT.parent.mkdir(parents=True,exist_ok=True)
            OUT.write_bytes(data)
    if a.verify:
        need(OUT.is_file() and OUT.read_bytes()==data,"derived stop audit mismatch")
    print("P10EW_P10EV_INDEPENDENT_EVIDENCE_STOP_AUDIT_PASS",
          "CRC=10/10","PARSE_A=PASS","PARSE_B=STRING_TOO_LONG",
          "native_3d=0 FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
