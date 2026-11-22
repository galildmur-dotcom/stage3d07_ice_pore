#!/usr/bin/env python3
"""P10EW deterministic Windows safe -parse_and_exit package; no M2/FEM."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"research/proposals/P10EW_STRCAT_SAFE_PARSE_WINDOWS_20261122"
PARENT=ROOT/"research/packages/P10EV_R1_ONE_C1_JOINT_M2_3D_WINDOWS_20261122.zip"
OUT=ROOT/"research/packages/P10EW_R1_STRCAT_SAFE_PARSE_ONLY_WINDOWS_20261122.zip"
PARENT_SHA="20a7a322b672b24d44f26b7cc2b723b39165a2d67b4187f589884ce931655010"
REV="P10EW_R1_CORRECTED_STRCAT_PARSE_PREFLIGHT_ONLY"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
FILES={
    "P10EW_safe_parse_only.py":HERE/"P10EW_safe_parse_only.py",
    "01_P10EW_SAFE_PARSE_ONLY.cmd":HERE/"01_P10EW_SAFE_PARSE_ONLY.cmd",
    "README_P10EW_RU.md":HERE/"README_P10EW_RU.md",
    "P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo":
        ROOT/"gmsh/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo",
    "P10EW_STRCAT_SOURCE_AUDIT.json":
        ROOT/"research/evidence/P10EW_STRCAT_RESCUE_20261122/derived/P10EW_STRCAT_SOURCE_AUDIT.json",
}
PIN=HERE/"P10EW_R1_SOURCE_SHA256.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EW_STOP: "+why)


def main() -> int:
    need(PARENT.is_file() and sha(PARENT.read_bytes())==PARENT_SHA,
         "original P10EV release exact SHA")
    files={}
    for name,path in FILES.items():
        need(path.is_file(),"missing "+name)
        files[name]=path.read_bytes()
    geo=files["P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"]
    audit=json.loads(files["P10EW_STRCAT_SOURCE_AUDIT.json"])
    need(audit["new_P10EW_GEO_SHA256"]==sha(geo) and
         audit["math_expression_identical_byte_for_byte"] and
         audit["max_quoted_field_literal"]<=600,
         "reproducible corrected StrCat source")
    pin={
        "revision":REV,
        "parent_p10ev_zip_sha256":PARENT_SHA,
        "m1_sha256":M1_SHA,
        "new_geo_sha256":sha(geo),
        "one_native_3d_max":0,
        "FEM":0,
        "files":{name:sha(data) for name,data in sorted(files.items())},
    }
    pin_data=(json.dumps(pin,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode()
    if PIN.exists():
        need(PIN.read_bytes()==pin_data,"refusing to overwrite changed pin")
    else:
        PIN.write_bytes(pin_data)
    files[PIN.name]=pin_data
    with zipfile.ZipFile(PARENT) as parent:
        need(parent.testzip() is None and len(parent.namelist())==45,
             "original P10EV release CRC and 45 files")
        for item in parent.infolist():
            need(not item.is_dir() and ".." not in item.filename.split("/")
                 and not item.filename.startswith("/"),"unsafe parent member")
            member="P10EV_PINNED_PARENT/"+item.filename
            need(member not in files,"duplicate source")
            files[member]=parent.read(item.filename)
    need(not OUT.exists(),"refusing to overwrite previous P10EW release")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            item=zipfile.ZipInfo(name,date_time=(2026,11,22,0,0,0))
            item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=0o644<<16
            z.writestr(item,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as z:
        need(z.testzip() is None and sorted(z.namelist())==sorted(files) and
             all(z.read(name)==data for name,data in files.items()),
             "P10EW release CRC/inventory/source bytes")
        with tempfile.TemporaryDirectory(prefix="p10ew_source_only_") as td:
            z.extractall(td)
            run=[sys.executable,str(Path(td)/"P10EW_safe_parse_only.py")]
            test=subprocess.run(run+["--selftest"],capture_output=True,
                                text=True,timeout=120)
            need(test.returncode==0 and
                 "P10EW_SAFE_PARSE_SOURCE_ONLY_SELFTEST_PASS" in test.stdout,
                 "source-only selftest: "+test.stdout[-1500:]+test.stderr[-1500:])
            stop=subprocess.run(run+["--safe-parse"],capture_output=True,
                                text=True,input="",timeout=120)
            need(stop.returncode==2 and "Windows required" in stop.stdout and
                 "P10EW_STOP_NO_M2_NO_FEM" in
                 (stop.stdout+stop.stderr) and
                 not any(Path(td).rglob("*.msh")),
                 "Linux native guard must STOP and not create any M2: "+
                 stop.stdout[-1400:]+stop.stderr[-1400:])
    print("P10EW_SAFE_PARSE_ONLY_BUNDLE_PASS",
          "members",len(files),"bytes",OUT.stat().st_size,
          "sha256",sha(OUT.read_bytes()),"native_Gmsh=0 M2=0 FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
