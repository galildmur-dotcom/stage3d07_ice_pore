#!/usr/bin/env python3
"""Independent audit of original P10EW Windows safe parse2 evidence."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"research/evidence/P10EX_P10EW_REAL_PARSE_PASS_20261122/derived/P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json"
ZIP_SHA="ca9a6dcd0127a6c7a3aeeef21e822b0674c58a2886c4671a9fe5d49351c79821"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GEO_SHA="d68570270dfb5ca2232d8fc94486e5638223b3604c933312b4036d5bb8d19b72"
CAD_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
EXE_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
EXPECTED={
    "P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt",
    "A_ORIGINAL_M1_FIELD2_PARSE.log","B_EXACT_INLINE_F6_PARSE.log",
    "GEO/A_ORIGINAL_M1_FIELD2.geo","GEO/B_EXACT_INLINE_F6.geo",
    "GEO/sphere_pore_B6_refined.geo",
    "SOURCE/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo",
    "SOURCE/P10EW_STRCAT_SOURCE_AUDIT.json",
    "SOURCE/P10EW_R1_SOURCE_SHA256.json",
}


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EX_EVIDENCE_STOP: "+why)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(raw: bytes) -> dict:
    need(sha(raw)==ZIP_SHA,"original user evidence SHA")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None and len(z.namelist())==10 and
             set(z.namelist())==EXPECTED,"CRC10/10 and exact evidence names")
        f={n:z.read(n) for n in z.namelist()}
    meta=json.loads(f["P10EA_RUN_MANIFEST.json"])
    result=f["P10EA_RESULT.txt"].decode("utf-8")
    pin=json.loads(f["SOURCE/P10EW_R1_SOURCE_SHA256.json"])
    audit=json.loads(f["SOURCE/P10EW_STRCAT_SOURCE_AUDIT.json"])
    a=f["A_ORIGINAL_M1_FIELD2_PARSE.log"].decode("utf-8",errors="replace")
    b=f["B_EXACT_INLINE_F6_PARSE.log"].decode("utf-8",errors="replace")
    geo=f["GEO/B_EXACT_INLINE_F6.geo"]
    need(meta["revision"]==pin["revision"]==
         "P10EW_R1_CORRECTED_STRCAT_PARSE_PREFLIGHT_ONLY" and
         meta["status"]=="P10EW_NATIVE_PARSE2_PASS_NO_M2_NO_FEM" and
         meta["mode"]=="SAFE_NATIVE_GEO_PARSE_ONLY" and
         result.startswith("RESULT=P10EW_NATIVE_PARSE2_PASS_NO_M2_NO_FEM") and
         "STOP_REASON=\r\n" in result,
         "actual native Windows result and revision")
    need(meta["native_parse_attempts"]==2 and
         meta["native_parse_passed"]==
             ["A_ORIGINAL_M1_FIELD2","B_EXACT_INLINE_F6"] and
         meta["native_3d_attempts"]==meta["FEM_attempts"]==0 and
         "NATIVE_M2_3D_ATTEMPTS=0" in result and
         "M2_SHA256=UNKNOWN" in result and "FEM=0" in result,
         "two native parse successes, no -3 and no FEM")
    need(meta["m1_sha256"]==meta["M1_SHA256"]==M1_SHA==
         pin["m1_sha256"] and
         meta["new_geo_sha256"]==pin["new_geo_sha256"]==GEO_SHA and
         meta["generated_geo_sha256"]["B_EXACT_INLINE_F6"]==GEO_SHA and
         sha(geo)==GEO_SHA and
         geo==f["SOURCE/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"] and
         sha(f["GEO/sphere_pore_B6_refined.geo"])==CAD_SHA and
         meta["gmsh_sha256"]==EXE_SHA,
         "M1, new GEO, original CAD and native executable SHA pins")
    need(pin["files"]["P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"]==GEO_SHA
         and pin["one_native_3d_max"]==pin["FEM"]==0 and
         audit["original_literal_length"]==4198 and
         audit["new_P10EW_GEO_SHA256"]==GEO_SHA and
         audit["math_expression_identical_byte_for_byte"] is True,
         "source exact proof and non-execution")
    m=re.search(rb'Field\[6\]\.F = StrCat\((.*?)\);',geo,re.S)
    need(m is not None,"StrCat source exists")
    chunks=re.findall(rb'"([^"\r\n]*)"',m.group(1))
    need([len(x) for x in chunks]==[600]*6+[598] and
         sha(b"".join(chunks))==audit["original_MathEval_expression_SHA256"]==
         audit["reconstructed_MathEval_expression_SHA256"],
         "literal chunks reconstruct original mathematical formula")
    need("Error" not in a and "Error" not in b and
         "Done reading" in a and "Done reading" in b and
         "Stopped on" in a and "Stopped on" in b and
         meta["math_points"]==17075 and
         meta["source_sha_pins"]==23 and
         "m1_label_dir" in meta,
         "authentic complete native parse2 logs and M1 source preflight")
    return {
        "protocol":"P10EX_INDEPENDENT_ORIGINAL_P10EW_NATIVE_WINDOWS_PARSE2_AUDIT",
        "original_evidence_zip_sha256":sha(raw),
        "zip_crc_members":10,
        "status":"P10EW_REAL_WINDOWS_PARSE2_PASS_NO_NEW_M2_NO_FEM",
        "accepted_M1_sha256":M1_SHA,"corrected_C1_GEO_sha256":GEO_SHA,
        "Gmsh_4_15_2_exe_sha256":EXE_SHA,
        "native_parse_A_M1_Field2":"PASS",
        "native_parse_B_StrCat_C1_Field6":"PASS",
        "original_4198_character_expression_byte_exact":True,
        "native_Gmsh_3d_attempts":0,"FEM_attempts":0,
        "authorized_new_3d_attempt_spent":False,
        "new_M2_raw":"NOT_GENERATED",
        "real_D025_north_south":"UNKNOWN",
        "next_action":"new isolated guarded one native Gmsh -3 M2; real curved27QP and fixed 343/729QP D025 audit before any FEM"
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--write",action="store_true")
    g.add_argument("--verify",action="store_true")
    args=p.parse_args()
    result=check(args.evidence.read_bytes())
    data=(json.dumps(result,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    if args.write:
        if OUT.exists():
            need(OUT.read_bytes()==data,"no overwrite changed derived audit")
        else:
            OUT.parent.mkdir(parents=True,exist_ok=True)
            OUT.write_bytes(data)
    else:
        need(OUT.is_file() and OUT.read_bytes()==data,"derived source audit changed")
    print("P10EX_REAL_P10EW_NATIVE_PARSE2_AUDIT_PASS",
          "CRC10/10","native_A=PASS native_B=PASS","M2=0 FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
