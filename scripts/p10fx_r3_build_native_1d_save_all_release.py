#!/usr/bin/env python3
"""Reproducible P10FX R3 Windows release; SHA-pin, CRC, tamper/Linux gates."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10FX_R3_NATIVE_1D_SAVE_ALL_WINDOWS_20261122"
ZIP=ROOT/"research/packages/P10FX_R3_ONE_M1V_NATIVE_1D_SAVE_ALL_WINDOWS_20261122.zip"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest=json.loads((SRC/"P10FX_SOURCE_SHA256.json").read_text(encoding="utf-8"))
    names=sorted([*manifest["files"],"P10FX_SOURCE_SHA256.json"])
    for name,value in manifest["files"].items():
        assert digest((SRC/name).read_bytes())==value,("pin mismatch",name)
    ZIP.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ZIP,"w",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        for name in names:
            info=zipfile.ZipInfo(name,(2026,11,22,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,(SRC/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None and sorted(z.namelist())==names
        for name in names:
            assert z.read(name)==(SRC/name).read_bytes()
        with tempfile.TemporaryDirectory(prefix="P10FX_ZIP_TEST_") as tmp:
            folder=Path(tmp)
            z.extractall(folder)
            cmd=[sys.executable,str(folder/"P10FX_one_click_m1v.py"),"--selftest"]
            a=subprocess.run(cmd,cwd=folder,text=True,capture_output=True,timeout=45)
            assert a.returncode==0 and "P10FX_PACKAGE_SOURCE_SELFTEST_PASS" in a.stdout,(a.stdout,a.stderr)
            b=subprocess.run([*cmd[:-1],"--preflight"],cwd=folder,text=True,
                             capture_output=True,timeout=45)
            assert b.returncode==2 and "Windows 11 required" in b.stderr,(b.stdout,b.stderr)
            original=folder/"README_P10FX_RU.md"
            original.write_bytes(original.read_bytes()+b"\nINJECTED\n")
            c=subprocess.run(cmd,cwd=folder,text=True,capture_output=True,timeout=45)
            assert c.returncode==2 and "tampered/missing package source: README" in c.stderr,(c.stdout,c.stderr)
    print("P10FX_R3_RELEASE_ZIP_CRC_SELFTEST_LINUX_STOP_TAMPER_STOP_PASS")
    print("ZIP",ZIP)
    print("ZIP_SHA256",digest(ZIP.read_bytes()))
    print("ZIP_BYTES",ZIP.stat().st_size)
    print("FILES",len(names))


if __name__=="__main__":
    main()
