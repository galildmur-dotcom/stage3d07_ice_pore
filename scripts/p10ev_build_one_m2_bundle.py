#!/usr/bin/env python3
"""Deterministic one-new-M2 Windows bundle, pinned P10EN parent, no Gmsh run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"research/proposals/P10EV_C1_JOINT_M2_WINDOWS_20261122"
EU=ROOT/"research/proposals/P10EU_C1_SOURCE_PREFLIGHT_WINDOWS_20261122"
PARENT=ROOT/"research/packages/P10EN_R1_ONE_M2_3D_ALPHA17_WINDOWS_20261122.zip"
OUT=ROOT/"research/packages/P10EV_R1_ONE_C1_JOINT_M2_3D_WINDOWS_20261122.zip"
PARENT_SHA="c730e8d585f44629b15eede2ebcf513358abf90e1030e1577837968cb6414e11"
REV="P10EV_R1_ONE_AUTHORIZED_C1_JOINT_3D_M2_MESH_ONLY"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GEO_SHA="4c4a4aeb4f97bfec350e1e057a57e275d436c09d63a02438a8acfe4ad386253a"
SRC_FILES={
    "P10EV_one_click_m2.py":HERE/"P10EV_one_click_m2.py",
    "01_P10EV_SAFE_PREFLIGHT_ONLY.cmd":HERE/"01_P10EV_SAFE_PREFLIGHT_ONLY.cmd",
    "02_P10EV_ONE_M2_3D_ONLY.cmd":HERE/"02_P10EV_ONE_M2_3D_ONLY.cmd",
    "README_P10EV_RU.md":HERE/"README_P10EV_RU.md",
    "P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo":
        ROOT/"gmsh/P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo",
    "P10EU_C1_GMSH_SOURCE_AUDIT.json":
        ROOT/"research/evidence/P10EU_GMSH_C1_SOURCE_20261122/derived/P10EU_C1_GMSH_SOURCE_AUDIT.json",
    "P10EU_safe_preflight.py":EU/"P10EU_safe_preflight.py",
    "sphere_pore_B6_refined.geo":ROOT/"gmsh/sphere_pore_B6_refined.geo",
}
PIN_OUTPUT=HERE/"P10EV_R1_SOURCE_SHA256.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> None:
    if not PARENT.is_file() or digest(PARENT.read_bytes())!=PARENT_SHA:
        raise ValueError("P10EV_STOP: exact original P10EN parent ZIP SHA mismatch")
    files={}
    for name,path in SRC_FILES.items():
        if not path.is_file():
            raise ValueError("P10EV_STOP: missing "+name)
        files[name]=path.read_bytes()
    if digest(files["P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo"])!=GEO_SHA:
        raise ValueError("P10EV_STOP: new C1 GEO source SHA changed")
    pin={"revision":REV,
         "parent_p10en_zip_sha256":PARENT_SHA,
         "new_geo_sha256":GEO_SHA,
         "m1_sha256":M1_SHA,
         "one_native_3d_max":1,
         "FEM":0,
         "files":{name:digest(data) for name,data in sorted(files.items())}}
    pin_data=(json.dumps(pin,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode()
    if PIN_OUTPUT.exists() and PIN_OUTPUT.read_bytes()!=pin_data:
        raise ValueError("P10EV_STOP: refusing overwrite different SHA manifest")
    if not PIN_OUTPUT.exists():
        PIN_OUTPUT.write_bytes(pin_data)
    files[PIN_OUTPUT.name]=pin_data
    with zipfile.ZipFile(PARENT) as old:
        if old.testzip() is not None or len(old.namelist())!=36:
            raise ValueError("P10EV_STOP: original parent archive CRC/count")
        for item in old.infolist():
            if item.is_dir() or "/" in item.filename and any(
                    p in ("",".","..") for p in item.filename.split("/")):
                raise ValueError("P10EV_STOP: unsafe parent archive name")
            name="P10EN_PINNED_PARENT/"+item.filename
            if name in files:
                raise ValueError("P10EV_STOP: duplicate inherited source")
            files[name]=old.read(item.filename)
    if OUT.exists():
        raise ValueError("P10EV_STOP: refusing overwrite existing ZIP")
    with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,22,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            out.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as result:
        if result.testzip() is not None or sorted(result.namelist())!=sorted(files):
            raise ValueError("P10EV_STOP: bundle CRC/inventory")
        for name,data in files.items():
            if result.read(name)!=data:
                raise ValueError("P10EV_STOP: bundle byte difference "+name)
        with tempfile.TemporaryDirectory(prefix="p10ev_source_selftest_") as td:
            # Only own pinned known Python/GEO filenames, not an untrusted archive.
            result.extractall(td)
            test=subprocess.run(
                [sys.executable,str(Path(td)/"P10EV_one_click_m2.py"),"--selftest"],
                capture_output=True,text=True,timeout=120)
            if test.returncode or "P10EV_C1_ONE_M2_SOURCE_ONLY_SELFTEST_PASS" not in test.stdout:
                raise ValueError("P10EV_STOP: source selftest "+test.stdout[-1000:]+test.stderr[-1000:])
            # Linux must STOP before any native Gmsh; a failure still writes
            # an evidence ZIP without consuming any permanent marker.
            stop=subprocess.run(
                [sys.executable,str(Path(td)/"P10EV_one_click_m2.py"),"--preflight-only"],
                input="",capture_output=True,text=True,timeout=120)
            if stop.returncode==0 or "Windows required" not in stop.stdout:
                raise ValueError("P10EV_STOP: Linux native guard negative missing: "+
                                 stop.stdout[-1000:]+stop.stderr[-1000:])
    print("P10EV_BUNDLE_SOURCE_ONLY_PASS",
          "files",len(files),"zip_bytes",OUT.stat().st_size,
          "zip_sha256",digest(OUT.read_bytes()),"parent_pin36=PASS",
          "synthetic_marker_negative=PASS Linux_native_STOP=PASS Gmsh3D=0 FEM=0")


if __name__=="__main__":
    build()
