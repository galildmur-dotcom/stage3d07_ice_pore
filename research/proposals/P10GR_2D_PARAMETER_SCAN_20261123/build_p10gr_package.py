#!/usr/bin/env python3
"""Deterministic offline builder for 20-case guarded P10GR Windows source."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
P10GP_R2=HERE.parent/"P10GP_SURFACE_SOURCE_ONLY_20261123"/"P10GP_R2_GUARDED_WINDOWS_2D_ONLY.zip"
P10GP_R2_SHA="0c33c23fa8d47d1dc536a978039fd5b6528848c1034f258fe27f23b3a80da266"
DEST=HERE/"P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip"


def sha(b):return hashlib.sha256(b).hexdigest()


def make():
    need=P10GP_R2.read_bytes()
    assert sha(need)==P10GP_R2_SHA
    with zipfile.ZipFile(P10GP_R2) as z:
        assert z.testzip() is None
        gp=z.read("P10GP_windows_2d.py")
        gmsh=z.read("P10GH_surface_compare.py")
        parent=z.read("P10GP_R1_SURFACE_SOURCE_ONLY.zip")
    runner=(HERE/"P10GR_scan.py").read_text(encoding="utf-8")
    assert runner.count("__PIN_HELPER_SHA__")==1 and runner.count("__PIN_GMSH_HELPER_SHA__")==1
    runner=runner.replace("__PIN_HELPER_SHA__",sha(gp)).replace("__PIN_GMSH_HELPER_SHA__",sha(gmsh))
    blobs={"P10GR_scan.py":runner.encode("utf-8"),
           "P10GP_windows_2d.py":gp,"P10GH_surface_compare.py":gmsh,
           "P10GP_R1_SURFACE_SOURCE_ONLY.zip":parent}
    for name in ("01_P10GR_PREFLIGHT_NO_MESH.cmd","02_P10GR_ONE_20_CASE_2D_SCAN.cmd",
                 "README_P10GR_RU.md"):
        blobs[name]=(HERE/name).read_bytes()
    with zipfile.ZipFile(DEST,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,b in sorted(blobs.items()):
            info=zipfile.ZipInfo(name,(2026,11,23,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,b,compresslevel=6)
    with zipfile.ZipFile(DEST) as z, tempfile.TemporaryDirectory(prefix="p10gr_qa_") as temp:
        assert z.testzip() is None and set(z.namelist())==set(blobs)
        z.extractall(temp)
        script=str(Path(temp)/"P10GR_scan.py")
        check=subprocess.run([sys.executable,script,"--selftest"],capture_output=True,text=True,timeout=15)
        assert check.returncode==0,check.stdout+check.stderr
        assert "P10GR_SOURCE_MATH_20_CASES_PASS 20" in check.stdout
        blocked=subprocess.run([sys.executable,script,"--one-scan"],capture_output=True,text=True,timeout=15)
        assert blocked.returncode==2 and "Windows required" in blocked.stderr
        tampered=Path(temp)/"P10GP_R1_SURFACE_SOURCE_ONLY.zip"
        tampered.write_bytes(tampered.read_bytes()+b"BAD")
        reject=subprocess.run([sys.executable,script,"--selftest"],capture_output=True,text=True,timeout=15)
        assert reject.returncode==2 and "source ZIP changed" in reject.stderr
    print("P10GR_PACKAGE_QA_PASS",len(blobs),"files",sha(DEST.read_bytes()))


if __name__=="__main__":make()
