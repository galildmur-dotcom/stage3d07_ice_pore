#!/usr/bin/env python3
"""P10EY: independent real P10EX Gmsh MathEx STOP and source-only sign repair.

No native Gmsh -1/-2/-3, no raw mesh, no FEM, no one-shot marker edits.
Repairs *only* the mathematically redundant '+-' at the exact Gmsh caret.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
import p10eu_generate_joint_c1_gmsh_source_only as eu

OLD=ROOT/"gmsh/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"
NEW=ROOT/"gmsh/P10EY_M2_C1_JOINT_STRCAT_SIGN_SOURCE_ONLY.geo"
OUT=ROOT/"research/evidence/P10EY_P10EX_REAL_MATHEX_STOP_20261122/derived/P10EY_REAL_STOP_AND_SIGN_SOURCE_AUDIT.json"
EVIDENCE_SHA="330f1a3925be4778c295d0afbc0fc950c2f3296b4d524684f9797b303a8d2cae"
OLD_SHA="d68570270dfb5ca2232d8fc94486e5638223b3604c933312b4036d5bb8d19b72"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
EXE_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
EXACT_NAMES={
    "P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt","P10EA_STOP_TRACE.txt",
    "P10EA_GMSH_FULL.log","P10EA_GMSH_TAIL.txt",
    "A_ORIGINAL_M1_FIELD2_PARSE.log","B_EXACT_INLINE_F6_PARSE.log",
    "GEO/A_ORIGINAL_M1_FIELD2.geo","GEO/B_EXACT_INLINE_F6.geo",
    "GEO/sphere_pore_B6_refined.geo","P10EA_M1_LABEL_SUMMARY.json",
    "SOURCE/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo",
    "SOURCE/P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json",
    "SOURCE/P10EX_R1_SOURCE_SHA256.json",
}


def require(ok: bool, what: str) -> None:
    if not ok:
        raise RuntimeError("P10EY_STOP: "+what)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def field_expr(geo: str) -> tuple[str,re.Match[str]]:
    m=re.search(r'Field\[6\]\.F = StrCat\((.*?)\);',geo,re.S)
    require(m is not None and geo.count("StrCat(")==1,
            "one StrCat field")
    literals=re.findall(r'"([^"\r\n]*)"',m.group(1))
    require(len(literals)==7 and m.group(1).count('"')==14,
            "exact 7 string literals and separators")
    return "".join(literals),m


def source_repair() -> tuple[str,str,str,dict]:
    require(OLD.is_file() and sha(OLD.read_bytes())==OLD_SHA,
            "exact P10EW original source SHA")
    old=OLD.read_text(encoding="utf-8")
    original,m=field_expr(old)
    require(len(original)==4198 and
            [(x.start(),x.group(0)) for x in re.finditer(r'\+\-',original)]
                ==[(1524,"+-")] and
            not re.search(r'\-\+|\+\+|\-\-|[*/^][+-]',original),
            "single Gmsh-invalid binary plus and minus token adjacency")
    repaired=original[:1524]+"-"+original[1526:]
    require(repaired==original.replace("+-","-",1) and
            len(repaired)==4197 and
            not re.search(r'\+\-|\-\+|\+\+|\-\-|[*/^][+-]',repaired),
            "exact one-token sign normalization")
    chunks=[repaired[i:i+600] for i in range(0,len(repaired),600)]
    require(list(map(len,chunks))==[600]*6+[597],"under 1023 lexer cap")
    field="Field[6].F = StrCat(\n"+",\n".join(
        '  "'+part+'"' for part in chunks)+"\n);"
    new=old[:m.start()]+field+old[m.end():]
    new=new.replace("// P10EW STRCAT SOURCE ONLY",
                    "// P10EY SOURCE ONLY SIGN-LEXER REPAIR",1)
    reconstructed,_=field_expr(new)
    require(reconstructed==repaired and
            new.count("Field[6] = MathEval;")==1 and
            new.count("Background Field=6;")==1 and
            new.count('Include "sphere_pore_B6_refined.geo";')==1 and
            new.count("Mesh.Algorithm3D=10;")==1,
            "new exact C1 in source and CAD unchanged")
    # On Python scalar arithmetic (+(-c)) and (-c) agree; also matches
    # the separately pinned high-density P10ET mathematical contract.
    old_code,new_code=eu.compile_safe(original),eu.compile_safe(repaired)
    coeff,p=eu.parents()
    contract=eu.numeric_test(new_code,coeff,p)
    rng=random.Random(20261122)
    worst=0.
    for _ in range(2000):
        d=.025*rng.random()
        mu=2*rng.random()-1
        pt=eu.pt(d,mu,2*math.pi*rng.random())
        prev=eu.eval_expr(old_code,pt)
        now=eu.eval_expr(new_code,pt)
        rel=abs(prev-now)/prev
        worst=max(worst,rel)
    require(worst<=2e-15 and
            contract["sample_count"]==7620 and
            contract["max_relative_h_parity_error"]<5e-12,
            "same source numerical C1 field / P10ET parity")
    summary={
        "old_GEO_SHA256":OLD_SHA,
        "old_MathEval_expression_sha256":sha(original.encode("ascii")),
        "old_mathex_expression_characters":len(original),
        "old_mathex_consecutive_binary_unary_sign":"+-",
        "invalid_operator_start_zero_index":1524,
        "new_GEO_SHA256":sha(new.encode("utf-8")),
        "new_MathEval_expression_sha256":sha(repaired.encode("ascii")),
        "new_mathex_expression_characters":len(repaired),
        "new_chunk_lengths":list(map(len,chunks)),
        "mathematical_meaning":"a + (-b) = a - b, no C1/size/alpha/kappa change",
        "Python_2000_point_max_relative_change":worst,
        "independent_P10ET_7620_point_parity":contract,
        "native_Gmsh_runs":0,"new_M2":0,"FEM":0,
    }
    return new,original,repaired,summary


def audit(raw: bytes,expected_original: str) -> dict:
    require(sha(raw)==EVIDENCE_SHA,"exact user ZIP SHA")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(z.testzip() is None and len(z.namelist())==14 and
                set(z.namelist())==EXACT_NAMES,"ZIP CRC14/14 and member inventory")
        f={name:z.read(name) for name in z.namelist()}
    manifest=json.loads(f["P10EA_RUN_MANIFEST.json"])
    result=f["P10EA_RESULT.txt"].decode("utf-8")
    pin=json.loads(f["SOURCE/P10EX_R1_SOURCE_SHA256.json"])
    log=f["P10EA_GMSH_FULL.log"].decode("utf-8",errors="replace")
    lines=log.splitlines()
    require(manifest["revision"]==pin["revision"]==
            "P10EX_R1_ONE_AUTHORIZED_STRCAT_C1_M2_3D_MESH_ONLY" and
            manifest["mode"]=="ONE_NATIVE_3D_MESH" and
            manifest["status"]=="P10EX_STOP_NO_FEM" and
            "NATIVE_M2_3D_ATTEMPTS=1" in result and
            "M2_SHA256=UNKNOWN" in result and "FEM=0" in result,
            "real one 3D consumed / STOP and no FEM")
    require(manifest["m1_sha256"]==pin["m1_sha256"]==M1_SHA and
            manifest["new_geo_sha256"]==pin["new_geo_sha256"]==OLD_SHA and
            manifest["gmsh_sha256"]==EXE_SHA and
            sha(f["GEO/B_EXACT_INLINE_F6.geo"])==OLD_SHA and
            f["GEO/B_EXACT_INLINE_F6.geo"]==
                f["SOURCE/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"] and
            sha(f["GEO/sphere_pore_B6_refined.geo"])==
                "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
            "exact accepted M1 and original corrected-but-invalid Gmsh C1 source")
    native=manifest["native_3d_result"]
    require(manifest["native_parse_attempts"]==2 and
            manifest["native_parse_passed"]==
                ["A_ORIGINAL_M1_FIELD2","B_EXACT_INLINE_F6"] and
            manifest["native_3d_attempts"]==1 and
            manifest["physical_FEM_attempts"]==0 and
            native["exit_code"]==1 and native["status"]=="STARTED" and
            0<native["polled_wall_s"]<900 and
            native["log_bytes"]==len(f["P10EA_GMSH_FULL.log"]) and
            f["P10EA_GMSH_TAIL.txt"]==f["P10EA_GMSH_FULL.log"],
            "real one bounded Gmsh3D exit1 / original full native log")
    require(any("mathex::parse()]: Invalid expression" in x for x in lines) and
            any("Field 6: invalid matheval expression" in x for x in lines) and
            any("HXT 3D mesh failed" in x for x in lines) and
            any("No elements in surface 7 8" in x for x in lines) and
            any("No elements in volume 1 2" in x for x in lines),
            "authentic primary and secondary native errors")
    formula=next(x.split(" : ",1)[1] for x in lines
                 if x.startswith("Error") and x.split(" : ",1)[1].startswith("(("))
    caret=next(x.split(" : ",1)[1].index("^") for x in lines
               if x.startswith("Error") and "^" in x)
    require(formula==expected_original and caret==1526 and
            formula[caret-2:caret]==" +-"[1:] and
            formula[caret:].startswith("0.0031079955054980225"),
            "native MathEx caret exactly at illegal '+-' sequence")
    require(not any(x=="RAW/P10EA_M2_CANDIDATE.msh" for x in f),
            "no raw 3D mesh in evidence; reject incomplete output as M2")
    return {
        "protocol":"P10EY_INDEPENDENT_REAL_P10EX_ONE_SHOT_STOP_AND_MATHEX_CARET",
        "original_evidence_zip_sha256":EVIDENCE_SHA,
        "zip_crc_member_count":14,
        "real_native_mesh_3d_attempts":1,
        "native_exit_code":1,
        "polled_wall_seconds":native["polled_wall_s"],
        "peak_polled_private_bytes":native["polled_peak_private_bytes"],
        "native_Gmsh_full_log_sha256":sha(f["P10EA_GMSH_FULL.log"]),
        "first_primary_error":"mathex::parse() Invalid expression",
        "field6_invalid_expression":True,
        "native_caret_zero_index":caret,
        "native_source_sign_at_index_1524":"+-",
        "secondary_surface_mesh":"No elements in surface 7 8",
        "secondary_volume_mesh":"HXT 3D mesh failed; No elements in volume 1 2",
        "output_msh_written_but_not_accepted":True,
        "real_D025":"NOT_MEASURABLE",
        "physical_FEM_attempts":0,
        "P10EX_one_shot_spent":True,
        "P10EX_02_must_never_rerun":True,
        "status":"P10EX_REAL_NATIVE_3D_MATHEX_PARSE_STOP_NO_ACCEPTED_M2_NO_FEM",
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write",action="store_true")
    mode.add_argument("--verify",action="store_true")
    mode.add_argument("--selftest",action="store_true")
    args=p.parse_args()
    candidate,original,repaired,summary=source_repair()
    evidence=audit(args.evidence.read_bytes(),original)
    data=(json.dumps({
        "source_only_repair":summary,"real_user_evidence_audit":evidence,
        "status":"P10EY_SOURCE_ONLY_SIGN_NORMALIZED_NO_NEW_NATIVE_GMSH_NO_FEM",
    },indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    if args.write:
        for dest,payload in ((NEW,candidate.encode("utf-8")),(OUT,data)):
            if dest.exists():
                require(dest.read_bytes()==payload,
                        "refusing changed previously written "+str(dest))
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(payload)
    if args.verify:
        require(NEW.is_file() and NEW.read_bytes()==candidate.encode("utf-8")
                and OUT.is_file() and OUT.read_bytes()==data,
                "repaired source/derived result differs from exact generation")
    print("P10EY_P10EX_REAL_STOP_MATHEX_SIGN_SOURCE_ONLY_" +
          ("WRITE" if args.write else "VERIFY" if args.verify else "SELFTEST") +
          "_PASS", "CRC14/14", "native3D=1 consumed", "FEM=0",
          "caret=1526", "invalid_sign=+-", "repaired=-",
          "relative_algebra_change",summary["Python_2000_point_max_relative_change"],
          "native_new=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
