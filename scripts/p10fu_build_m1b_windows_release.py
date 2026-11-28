#!/usr/bin/env python3
"""Deterministically build and independently smoke-test the P10FU Windows ZIP.

No native Gmsh, no FEM, and no user files are touched by this builder.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10FU_M1B_CORRECTED_WINDOWS_20261122"
TARGET=ROOT/"research/packages/P10FU_R1_ONE_M1B_CORRECTIVE_WINDOWS_20261122.zip"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main():
    pin=json.loads((SRC/"P10FU_SOURCE_SHA256.json").read_text(encoding="utf-8"))
    names=sorted([*pin["files"],"P10FU_SOURCE_SHA256.json"])
    for name,digest in pin["files"].items():
        assert sha_bytes((SRC/name).read_bytes())==digest, ("source pin mismatch",name)
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(TARGET,"w",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as output:
        for name in names:
            info=zipfile.ZipInfo(name,date_time=(2026,11,22,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            output.writestr(info,(SRC/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=9)
    with zipfile.ZipFile(TARGET) as bundle:
        assert bundle.testzip() is None
        assert sorted(bundle.namelist())==names
        for name in names:
            assert bundle.read(name)==(SRC/name).read_bytes()
        with tempfile.TemporaryDirectory(prefix="P10FU_ZIP_SELFTEST_") as folder:
            target=Path(folder)
            bundle.extractall(target)
            cmd=[sys.executable,str(target/"P10FU_one_click_m1b.py"),"--selftest"]
            test=subprocess.run(cmd,cwd=target,text=True,capture_output=True,timeout=25)
            assert test.returncode==0 and "P10FU_SOURCE_ONLY_SELFTEST_PASS" in test.stdout, (test.stdout,test.stderr)
            # A changed package source must fail closed, even with a valid source PIN.
            changed=target/"README_P10FU_RU.md"
            changed.write_bytes(changed.read_bytes()+b"\nMODIFIED\n")
            test=subprocess.run(cmd,cwd=target,text=True,capture_output=True,timeout=25)
            assert test.returncode==2 and "source SHA mismatch: README" in test.stderr, (test.stdout,test.stderr)
    print("P10FU_BUNDLE_REPRODUCIBLE_INTEGRITY_AND_TAMPER_STOP_PASS")
    print("ZIP",TARGET)
    print("BYTES",TARGET.stat().st_size)
    print("SHA256",sha_bytes(TARGET.read_bytes()))
    print("FILES",len(names))


if __name__=="__main__":
    main()
