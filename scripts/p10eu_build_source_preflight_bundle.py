#!/usr/bin/env python3
"""Deterministic small Windows P10EU source-only preflight ZIP; no Gmsh/FEM."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"research/proposals/P10EU_C1_SOURCE_PREFLIGHT_WINDOWS_20261122"
OUT=ROOT/"research/packages/P10EU_R1_C1_GMSH_SOURCE_PREFLIGHT_ONLY_WINDOWS_20261122.zip"
FILES={
    "01_P10EU_SAFE_SOURCE_PREFLIGHT_ONLY.cmd":SOURCE/"01_P10EU_SAFE_SOURCE_PREFLIGHT_ONLY.cmd",
    "P10EU_safe_preflight.py":SOURCE/"P10EU_safe_preflight.py",
    "README_P10EU_RU.md":SOURCE/"README_P10EU_RU.md",
    "P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo":
        ROOT/"gmsh/P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo",
    "sphere_pore_B6_refined.geo":ROOT/"gmsh/sphere_pore_B6_refined.geo",
    "P10EU_C1_GMSH_SOURCE_AUDIT.json":
        ROOT/"research/evidence/P10EU_GMSH_C1_SOURCE_20261122/derived/P10EU_C1_GMSH_SOURCE_AUDIT.json",
}


def build() -> None:
    files={}
    for name,path in FILES.items():
        if not path.is_file():
            raise ValueError("P10EU_STOP: missing "+name)
        files[name]=path.read_bytes()
    manifest={"revision":"P10EU_R1_SOURCE_PREFLIGHT_ONLY","no_Gmsh":True,
              "no_FEM":True,"no_one_shot_marker":True,
              "files":{name:hashlib.sha256(content).hexdigest()
                       for name,content in sorted(files.items())}}
    files["P10EU_SOURCE_SHA256.json"]=(json.dumps(manifest,sort_keys=True,indent=2)+"\n").encode()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if OUT.exists():
        raise ValueError("P10EU_STOP: refusing to overwrite existing ZIP")
    with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,22,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as archive:
        if archive.testzip() is not None or sorted(archive.namelist())!=sorted(files):
            raise ValueError("P10EU_STOP: ZIP CRC / inventory mismatch")
        for name,expected in files.items():
            if archive.read(name)!=expected:
                raise ValueError("P10EU_STOP: ZIP data mismatch "+name)
        with tempfile.TemporaryDirectory(prefix="p10eu_preflight_") as td:
            archive.extractall(td)
            tested=subprocess.run(
                [sys.executable,str(Path(td)/"P10EU_safe_preflight.py"),
                 "--source-only","--directory",td],capture_output=True,text=True)
            if tested.returncode or "P10EU_SOURCE_PREFLIGHT_PASS" not in tested.stdout:
                raise ValueError("P10EU_STOP: extracted preflight: "+tested.stderr)
    print("P10EU_SOURCE_PREFLIGHT_BUNDLE_PASS",
          "files",len(files),"bytes",OUT.stat().st_size,
          "sha256",hashlib.sha256(OUT.read_bytes()).hexdigest(),
          "native_Gmsh=0 FEM=0")


if __name__=="__main__":
    build()
