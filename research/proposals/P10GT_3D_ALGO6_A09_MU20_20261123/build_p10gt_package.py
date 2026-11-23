#!/usr/bin/env python3
"""Offline deterministic P10GT Windows HXT10 source release builder."""
from __future__ import annotations
import hashlib
import importlib.util
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
SRC=HERE.parent/"P10GL_ONE_P10GK_HXT10_WINDOWS_20261123"
GR=HERE.parent/"P10GR_2D_PARAMETER_SCAN_20261123"
OUT=HERE/"P10GT_R1_ONE_GUARDED_HXT10_WINDOWS_20261123.zip"
RUNTIMES={
    "P10FN_common.py":"__PIN_COMMON__",
    "P10FN_mesh_qa.py":"__PIN_QA__",
    "P10CK_curved_qp_audit.py":"__PIN_QP__",
    "P10GJ_mesh_extra.py":"__PIN_EXTRA__",
    "p10gi_independent_surface_audit.py":"__PIN_SURFACE__",
    "P10GL_one_hxt10.py":"__PIN_LEGACY__",
}


def sha(data):return hashlib.sha256(data).hexdigest()


def make():
    blobs={name:(SRC/name).read_bytes() for name in RUNTIMES}
    common=blobs["P10FN_common.py"].decode("utf-8")
    old="            while proc.poll() is None:\n                time.sleep(0.5)\n"
    new=("            last_signal = start\n"
         "            while proc.poll() is None:\n"
         "                time.sleep(0.5)\n"
         "                if time.monotonic() - last_signal >= 2:\n"
         "                    last_line = ''\n"
         "                    if log.is_file():\n"
         "                        with log.open('rb') as recent:\n"
         "                            recent.seek(max(0, log.stat().st_size - 800))\n"
         "                            lines = recent.read().decode('utf-8', errors='replace').splitlines()\n"
         "                            last_line = lines[-1][-130:] if lines else ''\n"
         "                    print('P10GT_HEARTBEAT elapsed_s=',\n"
         "                          round(time.monotonic() - start, 1), last_line, flush=True)\n"
         "                    last_signal = time.monotonic()\n")
    assert common.count(old)==1
    blobs["P10FN_common.py"]=common.replace(old,new).encode("utf-8")
    driver=(HERE/"P10GT_hxt10.py").read_text(encoding="utf-8")
    for name,placeholder in RUNTIMES.items():
        assert driver.count(placeholder)==1
        driver=driver.replace(placeholder,sha(blobs[name]))
    blobs["P10GT_hxt10.py"]=driver.encode("utf-8")
    for name in ("P10GJ_D027_FROZEN_GATES.json","P10GJ_M0_QP_BASELINE.json"):
        blobs[name]=(SRC/name).read_bytes()
    blobs["P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip"]=(GR/"P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip").read_bytes()
    for name in ("01_P10GT_PREFLIGHT_NO_MESH.cmd","02_P10GT_ONE_HXT10_3D_ONLY.cmd","README_P10GT_RU.md"):
        blobs[name]=(HERE/name).read_bytes()
    with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,b in sorted(blobs.items()):
            info=zipfile.ZipInfo(name,(2026,11,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,b,compresslevel=6)
    with zipfile.ZipFile(OUT) as z, tempfile.TemporaryDirectory(prefix="p10gt_qa_") as temp:
        assert z.testzip() is None and set(z.namelist())==set(blobs)
        z.extractall(temp)
        script=str(Path(temp)/"P10GT_hxt10.py")
        test=subprocess.run([sys.executable,script,"--selftest"],capture_output=True,text=True,timeout=30)
        assert test.returncode==0,test.stdout+test.stderr
        assert "P10GT_HXT10_SOURCE_FROZEN_GATE_PASS_NO_NATIVE" in test.stdout
        spec=importlib.util.spec_from_file_location("p10gt_source_qa",script)
        gt=importlib.util.module_from_spec(spec);spec.loader.exec_module(gt)
        derived=gt.source_files()["P10GT_HXT10.geo"].decode("utf-8")
        grdir=Path(temp)/"p10gr_source"
        grdir.mkdir()
        with zipfile.ZipFile(Path(temp)/"P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip") as parent_zip:
            parent_zip.extractall(grdir)
        spec2=importlib.util.spec_from_file_location("p10gr_original_qa",grdir/"P10GR_scan.py")
        gr=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(gr)
        expected=gr.generate()[0]["ALGO6_A09_MU20/P10GR.geo"].decode("utf-8")
        pattern=r"Field\[7\]\.F\s*=\s*StrCat\((.*?)\);"
        source_field=re.search(pattern,derived,re.S)
        exact_field=re.search(pattern,expected,re.S)
        assert source_field is not None and exact_field is not None
        assert source_field.group(1)==exact_field.group(1),"source field not identical to measured P10GR candidate"
        assert "Mesh.Algorithm = 6;" in derived and "Mesh.Algorithm3D = 10;" in derived
        stopped=subprocess.run([sys.executable,script,"--one-3d"],capture_output=True,text=True,timeout=30)
        assert stopped.returncode==2 and "native mode only" in stopped.stderr
        parent=Path(temp)/"P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip"
        parent.write_bytes(parent.read_bytes()+b"BAD")
        tamper=subprocess.run([sys.executable,script,"--selftest"],capture_output=True,text=True,timeout=30)
        assert tamper.returncode==2 and "source ZIP SHA mismatch" in tamper.stderr
    print("P10GT_SOURCE_QA_PASS",len(blobs),"files",sha(OUT.read_bytes()))


if __name__=="__main__":make()
