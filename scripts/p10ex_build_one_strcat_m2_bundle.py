#!/usr/bin/env python3
"""Deterministic protected one-M2 Windows release from exact pinned P10EW parent.

Does not run native Gmsh, does not alter any historical one-shot marker or FEM.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"research/proposals/P10EX_STRCAT_M2_WINDOWS_20261122"
PARENT=ROOT/"research/packages/P10EW_R1_STRCAT_SAFE_PARSE_ONLY_WINDOWS_20261122.zip"
OUT=ROOT/"research/packages/P10EX_R1_ONE_C1_STRCAT_M2_3D_WINDOWS_20261122.zip"
PARENT_SHA="a375bff007a6ce4c04e3590877359e870f9044e0bc385a8d26f3bebf1415b968"
GEO_SHA="d68570270dfb5ca2232d8fc94486e5638223b3604c933312b4036d5bb8d19b72"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
REV="P10EX_R1_ONE_AUTHORIZED_STRCAT_C1_M2_3D_MESH_ONLY"
FILES={
    "P10EX_one_click_m2.py":HERE/"P10EX_one_click_m2.py",
    "01_P10EX_SAFE_PREFLIGHT_ONLY.cmd":HERE/"01_P10EX_SAFE_PREFLIGHT_ONLY.cmd",
    "02_P10EX_ONE_M2_3D_ONLY.cmd":HERE/"02_P10EX_ONE_M2_3D_ONLY.cmd",
    "README_P10EX_RU.md":HERE/"README_P10EX_RU.md",
    "P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo":
        ROOT/"gmsh/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo",
    "P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json":
        ROOT/"research/evidence/P10EX_P10EW_REAL_PARSE_PASS_20261122/derived/P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json",
}
PIN=HERE/"P10EX_R1_SOURCE_SHA256.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def need(ok: bool,why: str) -> None:
    if not ok:
        raise RuntimeError("P10EX_STOP: "+why)


def build() -> int:
    need(PARENT.is_file() and sha(PARENT.read_bytes())==PARENT_SHA,
         "exact P10EW earlier Windows source archive changed")
    files={}
    for name,path in FILES.items():
        need(path.is_file(),"missing "+name)
        files[name]=path.read_bytes()
    need(sha(files["P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"])==GEO_SHA,
         "native-parsed C1 StrCat GEO changed")
    real=json.loads(files["P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json"])
    need(real["status"]=="P10EW_REAL_WINDOWS_PARSE2_PASS_NO_NEW_M2_NO_FEM" and
         real["native_Gmsh_3d_attempts"]==0 and
         real["accepted_M1_sha256"]==M1_SHA and
         real["corrected_C1_GEO_sha256"]==GEO_SHA,
         "original real native P10EW parse2 proof changed")
    pin={
        "revision":REV,
        "parent_p10ew_zip_sha256":PARENT_SHA,
        "new_geo_sha256":GEO_SHA,
        "m1_sha256":M1_SHA,
        "one_native_3d_max":1,
        "FEM":0,
        "files":{name:sha(data) for name,data in sorted(files.items())}
    }
    pin_data=(json.dumps(pin,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode()
    if PIN.exists():
        need(PIN.read_bytes()==pin_data,"refusing overwrite changed source PIN")
    else:
        PIN.write_bytes(pin_data)
    files[PIN.name]=pin_data
    with zipfile.ZipFile(PARENT) as original:
        need(original.testzip() is None and len(original.namelist())==51,
             "exact prior P10EW source 51 members")
        for item in original.infolist():
            need(not item.is_dir() and not item.filename.startswith("/")
                 and not any(x in (".","..","") for x in item.filename.split("/")),
                 "unsafe historical member")
            dest="P10EW_PINNED_PARENT/"+item.filename
            need(dest not in files,"duplicate historical source")
            files[dest]=original.read(item.filename)
    # A previous draft may already be present after a failed *builder test*.
    # Never overwrite it; verify its exact bytes/inventory below instead.
    if not OUT.exists():
        OUT.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(files.items()):
                item=zipfile.ZipInfo(name,date_time=(2026,11,22,0,0,0))
                item.compress_type=zipfile.ZIP_DEFLATED
                item.external_attr=0o644<<16
                z.writestr(item,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as result:
        need(result.testzip() is None and
             sorted(result.namelist())==sorted(files) and
             all(result.read(name)==data for name,data in files.items()),
             "released bundle CRC/member/byte identity")
        with tempfile.TemporaryDirectory(prefix="p10ex_source_unit_") as tmp:
            result.extractall(tmp)
            entry=Path(tmp)/"P10EX_one_click_m2.py"
            args=[sys.executable,str(entry)]
            test=subprocess.run(args+["--selftest"],capture_output=True,
                                text=True,timeout=120)
            need(test.returncode==0 and
                 "P10EX_ONE_C1_M2_MESH_ONLY_SOURCE_SELFTEST_PASS" in test.stdout,
                 "new source/M1/marker selftest STOP: "+
                 test.stdout[-1700:]+test.stderr[-1700:])
            pre=subprocess.run(args+["--preflight-only"],input="",
                               capture_output=True,text=True,timeout=120)
            need(pre.returncode==2 and "Windows required" in pre.stdout and
                 "P10EX_STOP_NO_FEM" in pre.stdout,
                 "Linux safe preflight must STOP without Gmsh: "+
                 pre.stdout[-1700:]+pre.stderr[-1700:])
            m2=subprocess.run(args+["--one-m2"],input="",capture_output=True,
                              text=True,timeout=120)
            need(m2.returncode==2 and "run button 01 successfully" in m2.stdout
                 and not any(Path(tmp).rglob("*.msh")),
                 "one-M2 must STOP without local fresh proof: "+
                 m2.stdout[-1700:]+m2.stderr[-1700:])
            own_geo=Path(tmp)/"P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"
            data=own_geo.read_bytes()
            need(b"StrCat(" in data,"synthetic exact new GEO exists")
            own_geo.write_bytes(data.replace(b"StrCat(",b"StrCab(",1))
            tamper=subprocess.run(args+["--selftest"],capture_output=True,
                                  text=True,timeout=120)
            need(tamper.returncode==2 and
                 "missing or modified pinned source" in
                 (tamper.stdout+tamper.stderr).lower(),
                 "modified new source must STOP under pin SHA: "+
                 tamper.stdout[-1000:]+tamper.stderr[-1000:])
    print("P10EX_ONE_STRCAT_M2_BUNDLE_SOURCE_ONLY_PASS",
          "files",len(files),"zip_bytes",OUT.stat().st_size,
          "zip_sha256",sha(OUT.read_bytes()),
          "source/M1/marker=PASS","Linux_Gmsh_STOP=PASS",
          "tampered_source_STOP=PASS","native_Gmsh3D=0 FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(build())
