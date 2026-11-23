#!/usr/bin/env python3
"""Deterministic P10GK source-only ZIP; validates own offline QA and STOP cases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/proposals/P10GK_SOUTH_POLE_C1_SOURCE_ONLY_20261123"
PACKAGE=ROOT/"research/packages/P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip"
sys.path.insert(0,str(SOURCE))
from P10GK_source_qa import MANIFEST,REV,SOURCE_FILES,source_gate,test_field


def digest(data):return hashlib.sha256(data).hexdigest()


def build():
    pin={"revision":REV,"parent_stage":"P10GJ real M1 343/729QP D027 STOP",
         "native_mesh_3d_authorized":False,"FEM_authorized":False,
         "files":{name:digest((SOURCE/name).read_bytes()) for name in sorted(SOURCE_FILES)}}
    (SOURCE/MANIFEST).write_text(json.dumps(pin,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    source_gate()
    stats=test_field()
    PACKAGE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(PACKAGE,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(SOURCE_FILES|{MANIFEST}):
            meta=zipfile.ZipInfo(name,date_time=(2026,11,23,0,0,0))
            meta.compress_type=zipfile.ZIP_DEFLATED
            meta.external_attr=(0o644&0xffff)<<16
            z.writestr(meta,(SOURCE/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(PACKAGE) as z:
        assert z.testzip() is None and set(z.namelist())==SOURCE_FILES|{MANIFEST}
        with tempfile.TemporaryDirectory() as root:
            z.extractall(root)
            cmd=[sys.executable,str(Path(root)/"P10GK_source_qa.py"),"--selftest"]
            ok=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            assert ok.returncode==0,(ok.stdout,ok.stderr)
            if sys.platform!="win32":
                bad=subprocess.run([sys.executable,str(Path(root)/"P10GK_source_qa.py"),
                                    "--preflight"],capture_output=True,text=True,timeout=30)
                assert bad.returncode==2 and "requires user Windows" in bad.stderr
            with (Path(root)/"P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo").open("ab") as f:
                f.write(b"\n// INVALID TAMPER\n")
            bad=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            assert bad.returncode==2 and "modified release source" in bad.stderr
    test=subprocess.run([sys.executable,"-m","unittest","-v",
                         "scripts/test_p10gk_source_only.py"],cwd=ROOT,
                        capture_output=True,text=True,timeout=60)
    if test.returncode:raise RuntimeError(test.stdout+test.stderr)
    print(test.stderr)
    print("P10GK_ZIP_CRC_EXTRACT_LINUX_PREFLIGHT_STOP_TAMPER_STOP_PASS")
    print("P10GK_SOURCE_FIELD_QA",json.dumps(stats))
    print("ZIP_PATH="+str(PACKAGE))
    print("ZIP_SHA256="+digest(PACKAGE.read_bytes()))
    print("ZIP_BYTES="+str(PACKAGE.stat().st_size))
    print("ZIP_FILES="+str(len(SOURCE_FILES)+1))
    print("NATIVE_GMSH_MESHES=0 FEM=0")


if __name__=="__main__":build()
