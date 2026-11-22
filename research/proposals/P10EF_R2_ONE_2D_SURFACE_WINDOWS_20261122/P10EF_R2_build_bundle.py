#!/usr/bin/env python3
"""Deterministic P10EF R2 Windows one-shot source package; builds without Gmsh."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R1=ROOT/"research/packages/P10EF_R1_2D_DELAUNAY_SOURCE_ONLY_WINDOWS_20261122.zip"
R1_SHA="7f4910c4fdcf669a386d687fc0eccd110b963614aceaee2bcf712a945771823a"
EA=ROOT/"research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip"
EA_SHA="8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
TARGET=ROOT/"research/packages/P10EF_R2_ONE_2D_SURFACE_GMSH_ONLY_WINDOWS_20261122.zip"
REV="P10EF_R2_ONE_NATIVE_2D_DELAUNAY5_PORE_SURFACE_ONLY"
R1_FILES=("A_P10EA_EXACT_F6_ALG6_CONTROL.geo",
          "B_P10EF_EXACT_F6_ALG5_SURFACE_ONLY.geo","sphere_pore_B6_refined.geo")
NEW_FILES=("P10EF_R2_one_2d_surface.py","P10EF_R2_surface_qa.py",
  "README_P10EF_R2_RU.md","01_P10EF_R2_SAFE_PREFLIGHT_ONLY.cmd",
  "02_P10EF_R2_ONE_2D_SURFACE_ONLY.cmd")
GUARD="P10DO_windows_guards.py"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(ok: bool, reason: str) -> None:
    if not ok:raise RuntimeError("P10EF_R2_BUILD_STOP: "+reason)


def keep(path: Path, contents: bytes) -> None:
    if path.is_file():
        check(path.read_bytes()==contents,"previous generated file mutated: "+path.name)
    else:path.write_bytes(contents)


def isolated(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable,str(root/"P10EF_R2_one_2d_surface.py"),*args],
        cwd=root,stdin=subprocess.DEVNULL,capture_output=True,text=True,errors="replace",timeout=45)


def build() -> dict:
    check(digest(R1.read_bytes())==R1_SHA,"immutable P10EF R1 ZIP SHA")
    check(digest(EA.read_bytes())==EA_SHA,"immutable P10EA source ZIP SHA")
    with zipfile.ZipFile(R1) as z:
        check(z.testzip() is None,"R1 archive CRC")
        payload={name:z.read(name) for name in R1_FILES}
    with zipfile.ZipFile(EA) as z:
        check(z.testzip() is None,"EA source archive CRC")
        payload[GUARD]=z.read(GUARD)
    for name in R1_FILES:
        keep(HERE/name,payload[name])
    keep(HERE/GUARD,payload[GUARD])
    for name in NEW_FILES:
        content=(HERE/name).read_bytes()
        if name.endswith(".cmd"):
            content=content.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
        payload[name]=content
    check(len(payload)==9,"PIN9 exact members")
    pin={"revision":REV,"one_native_2d_max":1,"native_3d_allowed":False,
         "physical_FEM":False,
         "accepted_original_m1_sha256":
            "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f",
         "historical_m2_sha256":
            "ba1f1a0553a568c1b399acadd52bce1c1dc32e8d1c6b3ab1ce6759c547e5dee5",
         "gmsh_sha256":
            "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1",
         "original_p10ef_r1_source_zip_sha256":R1_SHA,
         "parent_p10ea_r1_zip_sha256":EA_SHA,
         "manual_phrase":"RUN ONE P10EF 2D SURFACE",
         "native_max_wall_s":120,"private_max_bytes_polled":2*1024**3,
         "mesh_max_bytes":25*1024**2,"gmsh_log_max_bytes":4*1024**2,
         "mesh_algorithm_2d_candidate":5,"mesh_algorithm_2d_control":6,
         "files":{k:digest(v) for k,v in sorted(payload.items())}}
    pinbytes=(json.dumps(pin,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    keep(HERE/"P10EF_R2_SOURCE_SHA256.json",pinbytes)
    payload["P10EF_R2_SOURCE_SHA256.json"]=pinbytes
    with io.BytesIO() as dst:
        with zipfile.ZipFile(dst,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name, content in sorted(payload.items()):
                info=zipfile.ZipInfo(name,(2026,11,22,0,0,0))
                info.external_attr=0o100644<<16
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,content,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        archive=dst.getvalue()
    keep(TARGET,archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        check(z.testzip() is None and len(z.namelist())==10 and
              len(set(z.namelist()))==10,"CRC10 exact members")
        with tempfile.TemporaryDirectory(prefix="p10ef_r2_isolated_") as t:
            folder=Path(t);z.extractall(folder)
            for name in NEW_FILES[-2:]:
                cmd=(folder/name).read_bytes()
                check(cmd.startswith(b"@echo off\r\n") and
                      b'set "RC=%ERRORLEVEL%"' in cmd and
                      b"\xef\xbb\xbf" not in cmd[:3],"Windows CMD CRLF and exit handling")
            test=isolated(folder,"--selftest")
            check(test.returncode==0 and "P10EF_R2_SOURCE_SELFTEST_PASS" in test.stdout,
                  "isolated source selftest: "+test.stdout+test.stderr)
            if os.name!="nt":
                before=isolated(folder,"--preflight-only")
                check(before.returncode==2 and "Windows required" in before.stdout,
                      "nonWindows safe preflight must STOP")
                before=isolated(folder,"--one-2d")
                check(before.returncode==2 and "button 01" in before.stdout,
                      "no -2 without preflight proof")
                check(not (folder/"P10EF_R2_RUNS/P10EF_R2_ONE_2D_USED.json").exists(),
                      "selftest must not consume marker")
            b=folder/R1_FILES[1]; correct=b.read_bytes()
            b.write_bytes(correct+b"\n// TAMPER\n")
            test=isolated(folder,"--selftest")
            check(test.returncode==2 and "source SHA mismatch" in test.stderr,
                  "candidate tampering must STOP")
            b.write_bytes(correct)
            check(isolated(folder,"--selftest").returncode==0,"source negative restore")
    result={"revision":REV,"zip":TARGET.name,"sha256":digest(archive),
        "bytes":len(archive),"members":10,"source_sha_pins":9,
        "source_only_selftest":"PASS","negative_tamper":"STOP",
        "native_gmsh_attempts":0,"physical_fem_attempts":0}
    print("P10EF_R2_ONE_2D_PACKAGE_PASS CRC10/10 PIN9/9 isolated source/selftest PASS "
          "negative_tamper STOP native=0 FEM=0")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return result


if __name__=="__main__":
    try:build()
    except (OSError,ValueError,RuntimeError) as exc:
        print("P10EF_R2_BUILD_STOP",exc,file=sys.stderr)
        raise SystemExit(2)
