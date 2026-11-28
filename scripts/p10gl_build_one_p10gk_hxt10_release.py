#!/usr/bin/env python3
"""Deterministic P10GL one authorized 3D HXT10 Windows release with NO real mesh."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/proposals/P10GL_ONE_P10GK_HXT10_WINDOWS_20261123"
PACKAGE=ROOT/"research/packages/P10GL_R1_ONE_P10GK_C1_HXT10_M1_WINDOWS_20261123.zip"
sys.path.insert(0,str(SOURCE))
import P10GL_one_hxt10 as gl


def digest(data):return hashlib.sha256(data).hexdigest()


def build():
    manifest={"revision":gl.REV,"date":"2026-11-23",
              "parent_stage":"P10GK native Windows 4.15.2 parse-only PASS",
              "user_approved_new_native_3d_max_attempts":1,
              "FEM_max_attempts":0,
              "files":{name:digest((SOURCE/name).read_bytes()) for name in sorted(gl.SOURCE_FILES)}}
    (SOURCE/gl.SOURCE.name).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    gl.source_gate()
    PACKAGE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(PACKAGE,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(gl.SOURCE_FILES|{gl.SOURCE.name}):
            item=zipfile.ZipInfo(name,date_time=(2026,11,23,0,0,0))
            item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=(0o644&0xffff)<<16
            z.writestr(item,(SOURCE/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(PACKAGE) as z:
        assert z.testzip() is None
        assert set(z.namelist())==gl.SOURCE_FILES|{gl.SOURCE.name}
        with tempfile.TemporaryDirectory() as t:
            z.extractall(t)
            py=Path(t)/"P10GL_one_hxt10.py"
            good=subprocess.run([sys.executable,str(py),"--selftest"],
                                capture_output=True,text=True,timeout=30)
            assert good.returncode==0,(good.stdout,good.stderr)
            assert "NO_MESH_NO_FEM" in good.stdout
            if sys.platform!="win32":
                bad=subprocess.run([sys.executable,str(py),"--preflight"],
                                   capture_output=True,text=True,timeout=30)
                assert bad.returncode==2 and "requires user Windows" in bad.stderr
            with py.open("ab") as f:f.write(b"\n# UNAUTHORIZED TAMPER\n")
            bad=subprocess.run([sys.executable,str(py),"--selftest"],
                               capture_output=True,text=True,timeout=30)
            assert bad.returncode==2 and "tampered/missing source" in bad.stderr
    test=subprocess.run([sys.executable,"-m","unittest","-v",
                         "scripts/test_p10gl_one_hxt10.py"],cwd=ROOT,
                        capture_output=True,text=True,timeout=120)
    if test.returncode:raise RuntimeError(test.stdout+test.stderr)
    print(test.stderr)
    print("P10GL_ZIP_CRC_EXTRACT_LINUX_STOP_TAMPER_STOP_AND_8_MOCK_TESTS_PASS")
    print("ZIP_PATH="+str(PACKAGE))
    print("ZIP_SHA256="+digest(PACKAGE.read_bytes()))
    print("ZIP_BYTES="+str(PACKAGE.stat().st_size))
    print("ZIP_FILES="+str(len(gl.SOURCE_FILES)+1))
    print("NATIVE_WINDOWS_GMSH_3D_EXECUTIONS=0 FEM=0")


if __name__=="__main__":build()
