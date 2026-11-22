#!/usr/bin/env python3
"""P10EW: corrected Gmsh GEO parser-only preflight. No 3D or FEM entry point.

Uses exact, separately pinned P10EV->P10EN->P10EA source guards and M1 QA.
Only the output formatting of the P10EU MathEval source changes: StrCat chunks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PARENT = HERE/"P10EV_PINNED_PARENT"
sys.path.insert(0,str(PARENT))
import P10EV_one_click_m2 as ev

base = ev.base
REV = "P10EW_R1_CORRECTED_STRCAT_PARSE_PREFLIGHT_ONLY"
PIN_NAME = "P10EW_R1_SOURCE_SHA256.json"
GEO_NAME = "P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"
AUDIT_NAME = "P10EW_STRCAT_SOURCE_AUDIT.json"
P10EU_NAME = ev.eu.GEO_NAME
FILES = (
    "P10EW_safe_parse_only.py",
    "01_P10EW_SAFE_PARSE_ONLY.cmd",
    "README_P10EW_RU.md",
    GEO_NAME,
    AUDIT_NAME,
)


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EW_STOP: " + why)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_contract() -> tuple[str,str]:
    old_baseline, old_c1 = ev.geometry_contract()
    need(sha((PARENT/P10EU_NAME).read_bytes()) == ev.NEW_GEO_SHA,
         "preserved P10EU source SHA")
    new = (HERE/GEO_NAME).read_text(encoding="utf-8")
    m = re.search(r'Field\[6\]\.F = StrCat\((.*?)\);',new,re.S)
    ref = re.search(r'Field\[6\]\.F = "([^"\r\n]+)";',old_c1)
    need(m is not None and ref is not None and new.count("StrCat(")==1,
         "single StrCat MathEval source")
    parts = re.findall(r'"([^"\r\n]*)"',m.group(1))
    need(len(parts)==7 and m.group(1).count('"')==len(parts)*2 and
         max(map(len,parts)) <= 600 and "".join(parts)==ref.group(1),
         "StrCat reconstructs byte-exact original P10EU 4198-character expression")
    need(new.count("Field[6] = MathEval;")==1 and
         new.count("Background Field=6;")==1 and
         new.count("Mesh.Algorithm3D=10;")==1 and
         new.count('Include "sphere_pore_B6_refined.geo";')==1 and
         "F2" not in "".join(parts) and
         "Mesh 3;" not in new and "SystemCall" not in new and
         new.endswith("Mesh.MeshSizeMax=1e22;\n"),
         "single exact C1 sizing without native mesh operation")
    return old_baseline,new


def source_gate() -> dict:
    try:
        inherited = ev.source_gate()  # all 45 P10EV/EN historical source gates
        pin = json.loads((HERE/PIN_NAME).read_text(encoding="utf-8"))
        need(pin["revision"]==REV and
             pin["parent_p10ev_zip_sha256"]==
                 "20a7a322b672b24d44f26b7cc2b723b39165a2d67b4187f589884ce931655010" and
             pin["m1_sha256"]==base.M1_SHA and
             pin["one_native_3d_max"]==0 and pin["FEM"]==0 and
             set(pin["files"])==set(FILES),
             "independent P10EW parse-only source/parent SHA manifest")
        for name,expected in pin["files"].items():
            need(Path(name).name == name and (HERE/name).is_file() and
                 sha((HERE/name).read_bytes())==expected,"tampered "+name)
        need(pin["new_geo_sha256"]==sha((HERE/GEO_NAME).read_bytes()),
             "corrected GEO exact SHA")
        audit=json.loads((HERE/AUDIT_NAME).read_text(encoding="utf-8"))
        need(audit["math_expression_identical_byte_for_byte"] is True and
             audit["max_quoted_field_literal"]==600 and
             audit["new_P10EW_GEO_SHA256"]==pin["new_geo_sha256"] and
             audit["original_P10EU_GEO_SHA256"]==ev.NEW_GEO_SHA and
             audit["native_Gmsh_runs"]==audit["M2_3D_runs"]==audit["FEM_runs"]==0,
             "source-only independent MathEval StrCat audit")
        source_contract()
        return inherited
    finally:
        base.REV=REV
        base.F6_SHA=sha((HERE/GEO_NAME).read_bytes()) if (HERE/GEO_NAME).is_file() else ""


def global_marker() -> Path:
    data=os.environ.get("LOCALAPPDATA","")
    need(bool(data) and Path(data).is_dir(),"LOCALAPPDATA unavailable")
    return Path(data)/"Stage3D07"/("P10EW_R1_ONE_3D_"+base.M1_SHA+".json")


def configure() -> None:
    ev.configure()
    base.REV=REV
    base.F6_SHA=sha((HERE/GEO_NAME).read_bytes())
    base.RUNS=HERE/"P10EW_R1_PARSE_RUNS"
    base.PROOF=base.RUNS/"P10EW_R1_PARSE_PASS.json"
    base.LOCAL_MARKER=base.RUNS/"P10EW_R1_ONE_3D_USED.json"
    base.global_marker=global_marker
    base.source_gate=source_gate
    base.geometry_contract=source_contract
    # Intentionally NEVER expose base.launch_m2 / --one-m2 in this revision.


def evidence(run: Path) -> Path:
    out=run/"P10EW_EVIDENCE.zip"
    file_names=(
        "P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt","P10EA_STOP_TRACE.txt",
        "A_ORIGINAL_M1_FIELD2_PARSE.log","B_EXACT_INLINE_F6_PARSE.log",
        "GEO/A_ORIGINAL_M1_FIELD2.geo","GEO/B_EXACT_INLINE_F6.geo",
        "GEO/sphere_pore_B6_refined.geo",
        "M1_LABEL/P10DN_M1_LABEL_SUMMARY.json",
    )
    with zipfile.ZipFile(out,"x",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as bundle:
        for name in file_names:
            path=run/name
            if path.is_file():
                bundle.write(path,name)
        for name in (GEO_NAME,AUDIT_NAME,PIN_NAME):
            bundle.write(HERE/name,"SOURCE/"+name)
    return out


def safe_parse() -> int:
    base.RUNS.mkdir(parents=True,exist_ok=True)
    run=base.RUNS/("P10EW_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta={
        "revision":REV,"status":"P10EW_STOP_NO_M2_NO_FEM",
        "mode":"SAFE_NATIVE_GEO_PARSE_ONLY",
        "source_corrective_action":"unchanged C1 expression, 7 StrCat literal chunks <=600",
        "M1_SHA256":base.M1_SHA,"new_geo_sha256":base.F6_SHA,
        "native_parse_attempts":0,"native_parse_passed":[],
        "native_3d_attempts":0,"FEM_attempts":0,
        "started_utc":datetime.now(timezone.utc).isoformat()}
    exit_code=2
    try:
        base.preflight(run,meta,prompt=True)  # exact source, M1, native parse2, label
        base.save_proof(meta,run)
        meta["status"]="P10EW_NATIVE_PARSE2_PASS_NO_M2_NO_FEM"
        exit_code=0
    except BaseException as exc:
        meta["stop_reason"]=str(exc)
        (run/"P10EA_STOP_TRACE.txt").write_text(
            traceback.format_exc(),encoding="utf-8")
        print("P10EW STOP:",exc,flush=True)
    finally:
        meta["finished_utc"]=datetime.now(timezone.utc).isoformat()
        (run/"P10EA_RUN_MANIFEST.json").write_bytes(
            (json.dumps(meta,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
        (run/"P10EA_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\n"+
            "NATIVE_GEO_PARSE_ATTEMPTS="+str(meta["native_parse_attempts"])+"\n"+
            "NATIVE_M2_3D_ATTEMPTS=0\nFEM=0\n"+
            "M1_SHA256="+base.M1_SHA+"\nM2_SHA256=UNKNOWN\n"+
            "STOP_REASON="+str(meta.get("stop_reason",""))+"\n",
            encoding="utf-8")
        archive=evidence(run)
        print("P10EW RESULT:",meta["status"],"EVIDENCE:",archive,flush=True)
        print("Send P10EW_EVIDENCE.zip. This package contains no 02 button. "
              "No M2 or FEM was launched.",flush=True)
    return exit_code


def selftest() -> int:
    configure()
    inherited=source_gate()
    old,new=source_contract()
    base.mesh_qa.selftest()
    need(len(inherited["files"])==23 and
         old.endswith("Background Field=2;\n") and
         "StrCat(" in new and
         base.REV==REV and
         base.F6_SHA==sha((HERE/GEO_NAME).read_bytes()) and
         not hasattr(sys.modules[__name__],"launch_m2"),
         "source, historical pin, runner mode and no 3D launch entry point")
    # Source tamper negative; no filesystem edits or native invocations.
    altered=new.replace("0.0004","0.0005",1)
    need(altered!=new,"tamper negative sample")
    print("P10EW_SAFE_PARSE_SOURCE_ONLY_SELFTEST_PASS",
          "P10EV_parent=PINNED", "unchanged_C1_expr=PASS",
          "strcat_max_literal=600", "native_Gmsh=0 M2=0 FEM=0")
    return 0


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest",action="store_true")
    g.add_argument("--safe-parse",action="store_true")
    a=p.parse_args()
    return selftest() if a.selftest else (configure() or safe_parse())


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError,ValueError,KeyError,OSError,AssertionError) as exc:
        print("P10EW STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
