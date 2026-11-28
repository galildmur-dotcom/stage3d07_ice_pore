#!/usr/bin/env python3
"""Build/check isolated P10EK Windows ZIP without native Gmsh or FEM."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PARENT=ROOT/"research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip"
PARENT_SHA="8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
TARGET=ROOT/"research/packages/P10EK_R1_ONE_M2_3D_ALG5_WINDOWS_20261122.zip"
REV="P10EK_R1_ONE_NATIVE_3D_M2_ALG5_MESH_ONLY"
NEW_FILES=("P10EK_one_click_m2.py", "P10EK_B_EXACT_F6_ALG5.geo",
           "01_P10EK_SAFE_PREFLIGHT_ONLY.cmd", "02_P10EK_ONE_M2_3D_ONLY.cmd",
           "README_P10EK_RU.md")


def sha(data):return hashlib.sha256(data).hexdigest()


def run_python(directory,mode):
    return subprocess.run([sys.executable,str(directory/"P10EK_one_click_m2.py"),mode],
           cwd=directory,capture_output=True,text=True,errors="replace",
           stdin=subprocess.DEVNULL,timeout=120,check=False)


def build():
    assert sha(PARENT.read_bytes())==PARENT_SHA,"P10EA parent ZIP not exact"
    with zipfile.ZipFile(PARENT) as z:
        assert z.testzip() is None and len(z.namelist())==24
        contents={"P10EA_PINNED_PARENT/"+name:z.read(name) for name in z.namelist()}
        original_pin=json.loads(contents["P10EA_PINNED_PARENT/P10EA_SOURCE_SHA256.json"])
        assert len(original_pin["files"])==23
    assert not(set(NEW_FILES)&set(contents))
    new={}
    for name in NEW_FILES:
        blob=(HERE/name).read_bytes()
        if name.endswith(".cmd"):
            blob=blob.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
        new[name]=blob
    contents.update(new)
    pin={"revision":REV,"one_native_3d_max":1,"physical_FEM":False,
         "parent_bundle_sha256":PARENT_SHA,
         "parent_f6_sha256":"32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561",
         "new_alg5_sha256":"2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5",
         "files":{name:sha(blob) for name,blob in sorted(new.items())}}
    contents["P10EK_R1_SOURCE_SHA256.json"]=(json.dumps(pin,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    TARGET.parent.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(TARGET,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name,content in sorted(contents.items()):
            zi=zipfile.ZipInfo(name,(2026,11,22,0,0,0))
            zi.external_attr=0o100644<<16
            zi.compress_type=zipfile.ZIP_DEFLATED
            out.writestr(zi,content,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and len(z.namelist())==len(contents)
        assert z.read("P10EA_PINNED_PARENT/P10EA_SOURCE_SHA256.json")==contents["P10EA_PINNED_PARENT/P10EA_SOURCE_SHA256.json"]
        assert sha(z.read("P10EK_B_EXACT_F6_ALG5.geo"))==pin["new_alg5_sha256"]
        with tempfile.TemporaryDirectory(prefix="p10ek_isolated_") as temp:
            folder=Path(temp)
            z.extractall(folder)
            for name in NEW_FILES:
                assert sha((folder/name).read_bytes())==pin["files"][name]
            for name in NEW_FILES[2:4]:
                raw=(folder/name).read_bytes()
                assert raw.startswith(b"@echo off\r\n") and b"\xef\xbb\xbf" not in raw[:3]
                assert b'set "RC=%ERRORLEVEL%"' in raw
            test=run_python(folder,"--selftest")
            assert test.returncode==0 and "P10EK_ALG5_M2_SOURCE_ONLY_SELFTEST_OK" in test.stdout, (test.stdout,test.stderr)
            if os.name!="nt":
                no_native=run_python(folder,"--preflight-only")
                assert no_native.returncode==2 and "Windows required" in no_native.stdout, (no_native.stdout,no_native.stderr)
                no_proof=run_python(folder,"--one-m2")
                assert no_proof.returncode==2 and "button 01" in no_proof.stdout
                assert not list(folder.glob("P10EK_R1_RUNS/P10EK_R1_ONE_3D_USED.json"))
                assert not list(folder.glob("P10EA_RUNS/P10EA_ONE_M2_3D_USED.json"))
                (folder/"P10EK_B_EXACT_F6_ALG5.geo").write_bytes(b"tampered\n")
                denied=run_python(folder,"--selftest")
                assert denied.returncode==2 and "new source modified" in denied.stdout
    print("P10EK_SOURCE_ONLY_BUNDLE_OK", "ZIP_SHA256="+sha(TARGET.read_bytes()),
          "ZIP_BYTES="+str(TARGET.stat().st_size),"CRC="+str(len(contents))+"/"+str(len(contents)),
          "source_pin="+str(len(original_pin["files"]))+"+"+str(len(NEW_FILES)),
          "selftest=PASS", "negative_tamper=STOP", "native_gmsh=0", "FEM=0")


if __name__=="__main__":build()
