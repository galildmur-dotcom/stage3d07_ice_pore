#!/usr/bin/env python3
"""P10EN isolated deterministic Windows ZIP; checks source, not native meshing."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARENT = ROOT/"research/packages/P10EK_R1_ONE_M2_3D_ALG5_WINDOWS_20261122.zip"
PARENT_SHA = "f9cf0bb54e6032115b6c001c60c0cf19af2280b97432b21be1c765bcedaf7b58"
PARENT_GEO_SHA = "2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5"
NEW_GEO_SHA = "b54db4fe70c8661fe4faa70985893ca0a3b0c01ff619d3727f2cb8030fe3a0e6"
TARGET = ROOT/"research/packages/P10EN_R1_ONE_M2_3D_ALPHA17_WINDOWS_20261122.zip"
REV = "P10EN_R1_ONE_NATIVE_3D_M2_ALPHA17_BAND15_25_MESH_ONLY"
NEW_FILES = (
    "P10EN_one_click_m2.py", "P10EN_B_F6_ALG5_ALPHA17.geo",
    "01_P10EN_SAFE_PREFLIGHT_ONLY.cmd", "02_P10EN_ONE_M2_3D_ONLY.cmd",
    "README_P10EN_RU.md",
)


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def run_python(folder: Path, mode: str):
    return subprocess.run(
        [sys.executable, str(folder/"P10EN_one_click_m2.py"), mode],
        cwd=folder, capture_output=True, text=True, errors="replace",
        stdin=subprocess.DEVNULL, timeout=120, check=False)


def build():
    assert sha(PARENT.read_bytes()) == PARENT_SHA, "exact published P10EK ZIP SHA"
    with zipfile.ZipFile(PARENT) as z:
        assert z.testzip() is None and len(z.namelist()) == 30, "parent P10EK CRC/inventory"
        contents = {"P10EK_PINNED_PARENT/"+name:z.read(name) for name in z.namelist()}
        original_pin = json.loads(contents["P10EK_PINNED_PARENT/P10EK_R1_SOURCE_SHA256.json"])
        parent_pin = json.loads(contents["P10EK_PINNED_PARENT/P10EA_PINNED_PARENT/P10EA_SOURCE_SHA256.json"])
        assert len(original_pin["files"]) == 5 and len(parent_pin["files"]) == 23
        assert sha(contents["P10EK_PINNED_PARENT/P10EK_B_EXACT_F6_ALG5.geo"]) == PARENT_GEO_SHA
    new = {}
    for name in NEW_FILES:
        blob = (HERE/name).read_bytes()
        if name.endswith(".cmd"):
            blob = blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        new[name] = blob
    assert sha(new["P10EN_B_F6_ALG5_ALPHA17.geo"]) == NEW_GEO_SHA
    contents.update(new)
    pin = {
        "revision":REV,"one_native_3d_max":1,"physical_FEM":False,
        "parent_p10ek_zip_sha256":PARENT_SHA,
        "parent_alg5_geo_sha256":PARENT_GEO_SHA,
        "new_alpha":.17,"acceptance_ratio_kappa_one":[.75,.85],
        "new_geo_sha256":NEW_GEO_SHA,
        "files":{name:sha(blob) for name,blob in sorted(new.items())},
    }
    contents["P10EN_R1_SOURCE_SHA256.json"] = (json.dumps(pin,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TARGET,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name,blob in sorted(contents.items()):
            info=zipfile.ZipInfo(name,(2026,11,22,0,0,0))
            info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            out.writestr(info,blob,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and len(z.namelist()) == len(contents) == 36
        assert z.read("P10EK_PINNED_PARENT/P10EA_PINNED_PARENT/P10EA_SOURCE_SHA256.json") == contents[
            "P10EK_PINNED_PARENT/P10EA_PINNED_PARENT/P10EA_SOURCE_SHA256.json"]
        with tempfile.TemporaryDirectory(prefix="p10en_isolated_") as temp:
            folder = Path(temp)
            z.extractall(folder)
            for name in NEW_FILES:
                assert sha((folder/name).read_bytes()) == pin["files"][name]
            for name in NEW_FILES[2:4]:
                data = (folder/name).read_bytes()
                assert data.startswith(b"@echo off\r\n") and not data.startswith(b"\xef\xbb\xbf")
                assert b'set "RC=%ERRORLEVEL%"' in data
            test = run_python(folder,"--selftest")
            assert test.returncode == 0 and "P10EN_ALPHA17_BAND15_25_SOURCE_ONLY_SELFTEST_OK" in test.stdout, (
                test.stdout,test.stderr)
            if os.name != "nt":
                preflight = run_python(folder,"--preflight-only")
                assert preflight.returncode == 2 and "Windows required" in preflight.stdout, (
                    preflight.stdout,preflight.stderr)
                no_proof = run_python(folder,"--one-m2")
                assert no_proof.returncode == 2 and "button 01" in no_proof.stdout, (
                    no_proof.stdout,no_proof.stderr)
                assert not list(folder.glob("P10EN_R1_RUNS/P10EN_R1_ONE_3D_USED.json"))
                assert not list(folder.glob("P10EK_PINNED_PARENT/P10EK_R1_RUNS/*USED.json"))
                (folder/"P10EN_B_F6_ALG5_ALPHA17.geo").write_bytes(b"tampered\n")
                reject = run_python(folder,"--selftest")
                assert reject.returncode == 2 and "source modified" in reject.stdout, (
                    reject.stdout,reject.stderr)
    print("P10EN_SOURCE_ONLY_BUNDLE_OK",
          "ZIP_SHA256="+sha(TARGET.read_bytes()),
          "ZIP_BYTES="+str(TARGET.stat().st_size),
          "CRC="+str(len(contents))+"/"+str(len(contents)),
          "source_pin=23+5+5", "alpha=.17", "kappa1_acceptance=[.75,.85]",
          "selftest=PASS", "negative_tamper=STOP", "native_Gmsh=0", "FEM=0")


if __name__ == "__main__":
    build()
