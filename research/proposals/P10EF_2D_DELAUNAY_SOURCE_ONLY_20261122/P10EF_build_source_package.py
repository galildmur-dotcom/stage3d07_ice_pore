#!/usr/bin/env python3
"""Deterministic P10EF R1 SOURCE-ONLY package: never invokes native Gmsh."""
from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/"research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip"
SOURCE_SHA="8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
TARGET=ROOT/"research/packages/P10EF_R1_2D_DELAUNAY_SOURCE_ONLY_WINDOWS_20261122.zip"
REV="P10EF_R1_2D_DELAUNAY_ONLY_SOURCE_PREP"
CONTROL="A_P10EA_EXACT_F6_ALG6_CONTROL.geo"
CAND="B_P10EF_EXACT_F6_ALG5_SURFACE_ONLY.geo"
CAD="sphere_pore_B6_refined.geo"
PIN="P10EF_SOURCE_PIN.json"
README="README_P10EF_RU.md"
CMD="01_P10EF_CHECK_SOURCE_ONLY.cmd"
CHECK="P10EF_SOURCE_CHECK.py"


def ensure(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EF_BUILD_STOP: "+why)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def keep_generated(path: Path, data: bytes) -> None:
    if path.exists():
        ensure(path.read_bytes()==data,"generated source differs: "+str(path))
    else:
        path.write_bytes(data)


def run_source_test(folder: Path, flag: str):
    return subprocess.run([sys.executable,str(folder/CHECK),flag],cwd=folder,
      stdin=subprocess.DEVNULL,capture_output=True,text=True,check=False,timeout=20)


def build() -> dict:
    ensure(digest(SOURCE.read_bytes())==SOURCE_SHA,"pinned P10EA R1 source ZIP SHA")
    with zipfile.ZipFile(SOURCE) as z:
        ensure(z.testzip() is None,"original source ZIP CRC")
        original=z.read("P10DV_M2_INLINE_FIELD20.geo")
        cad=z.read(CAD)
    import P10EF_SOURCE_CHECK as guard
    insert=guard.INSERT
    needle=guard.NEEDLE
    ensure(original.count(needle)==1 and digest(original)==guard.F6_SHA and
           digest(cad)==guard.CAD_SHA,"original F6/CAD SHA and one field occurrence")
    candidate=original.replace(needle,insert+needle,1)
    guard.check_bytes(original,candidate,cad)
    for name,data in ((CONTROL,original),(CAND,candidate),(CAD,cad)):
        keep_generated(HERE/name,data)
    payload={CONTROL:original,CAND:candidate,CAD:cad,
        README:(HERE/README).read_bytes(),
        CMD:(HERE/CMD).read_bytes().replace(b"\r\n",b"\n").replace(b"\n",b"\r\n"),
        CHECK:(HERE/CHECK).read_bytes()}
    ensure(len(payload)==6,"expected six pinned source artifacts")
    pin={"revision":REV,"mode":"SOURCE_ONLY_NO_NATIVE",
         "original_m1_sha256":guard.M1_SHA,
         "historical_m2_alg6_sha256":guard.OLD_M2_SHA,
         "p10ea_r1_parent_release_sha256":SOURCE_SHA,
         "exact_f6_sha256":guard.F6_SHA,
         "cad_sha256":guard.CAD_SHA,
         "gmsh_version_for_any_future_separately_authorized_test":"4.15.2",
         "native_gmsh_attempts_allowed_now":0,
         "physical_fem_attempts_allowed_now":0,
         "mesh_2d_algorithm_control":6,
         "mesh_2d_algorithm_candidate":5,
         "source_only_diff":"insert exactly one Mesh.Algorithm = 5; before Background Field=6;",
         "files":{name:digest(data) for name,data in sorted(payload.items())}}
    payload[PIN]=(json.dumps(pin,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    keep_generated(HERE/PIN,payload[PIN])
    with io.BytesIO() as buf:
        with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(payload.items()):
                info=zipfile.ZipInfo(name,(2026,11,22,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16
                z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        archive=buf.getvalue()
    keep_generated(TARGET,archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        ensure(z.testzip() is None and len(z.namelist())==7 and
               len(set(z.namelist()))==7,"archive CRC and member count")
        with tempfile.TemporaryDirectory(prefix="p10ef_source_only_") as temp:
            folder=Path(temp)
            z.extractall(folder)
            for flag in ("--check","--selftest"):
                tested=run_source_test(folder,flag)
                ensure(tested.returncode==0 and "P10EF_SOURCE_CHECK_PASS" in tested.stdout,
                       "isolated source selftest "+flag+" failed: "+tested.stdout+tested.stderr)
            ensure(b"\r\n" in (folder/CMD).read_bytes() and
                   b"\xef\xbb\xbf" not in (folder/CMD).read_bytes()[:3],
                   "Windows CMD encoding/newline")
            original_b=(folder/CAND).read_bytes()
            (folder/CAND).write_bytes(original_b+b"\n// INJECT\n")
            altered=run_source_test(folder,"--check")
            ensure(altered.returncode==2 and "tampered" in altered.stderr,
                   "isolated tampered candidate must STOP")
            (folder/CAND).write_bytes(original_b)
            ensure(run_source_test(folder,"--check").returncode==0,
                   "source test must recover after disposable isolated tamper")
    result={"revision":REV,"zip_name":TARGET.name,"zip_sha256":digest(archive),
      "zip_bytes":len(archive),"members":len(payload),"sha_pins":len(pin["files"]),
      "original_control_f6_sha256":digest(original),"candidate_alg5_sha256":digest(candidate),
      "cad_sha256":digest(cad),"exact_one_line_diff":True,
      "source_only_checks":"PASS isolated selftest and negative tamper STOP",
      "native_Gmsh_attempts":0,"physical_FEM_attempts":0}
    print("P10EF_2D_DELAUNAY_SOURCE_PACKAGE_PASS CRC7/7 PIN6/6 one_line_diff=PASS "+
          "negative4/4=STOP native_Gmsh=0 FEM=0")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return result


if __name__=="__main__":
    raise SystemExit(0 if build() else 2)
