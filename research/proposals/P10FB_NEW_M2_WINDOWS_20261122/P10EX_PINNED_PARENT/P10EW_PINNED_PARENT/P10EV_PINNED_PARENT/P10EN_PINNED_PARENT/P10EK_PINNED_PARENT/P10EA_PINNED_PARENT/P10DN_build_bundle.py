#!/usr/bin/env python3
"""Deterministic standalone M2 coefficient-only ZIP, never calls Gmsh/FEM."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
REPO=Path(__file__).resolve().parents[3]
TARGET=REPO/"research/packages/P10DN_R1_M2_COEFF20_SOURCE_ONLY_WINDOWS_20261121.zip"
SOURCES={
    "P10DN_m2_coefficient.py":HERE/"P10DN_m2_coefficient.py",
    "P10DN_M2_FIELD20.geo":HERE/"P10DN_M2_FIELD20.geo",
    "sphere_pore_B6_refined.geo":REPO/"gmsh/sphere_pore_B6_refined.geo",
    "01_P10DN_LABEL_M1_ONLY.cmd":HERE/"01_P10DN_LABEL_M1_ONLY.cmd",
    "README_RU.md":HERE/"README_RU.md",
    "P10DN_build_bundle.py":HERE/"P10DN_build_bundle.py",
}


def run() -> None:
    data={}
    for name,file in SOURCES.items():
        content=file.read_bytes()
        if name.endswith(".cmd"):
            content=content.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
        data[name]=content
    inventory="".join(sha256(data[name]).hexdigest()+"  "+name+"\n"
                      for name in sorted(data))
    data["P10DN_SOURCE_SHA256SUMS.txt"]=inventory.encode("utf-8")
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(TARGET,"w",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8) as z:
        for name,content in sorted(data.items()):
            info=zipfile.ZipInfo(name,(2026,11,21,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,content,compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=8)
    with zipfile.ZipFile(TARGET) as z:
        if z.testzip() is not None or len(z.namelist())!=len(data):
            raise RuntimeError("P10DN bad source ZIP CRC/count")
        with tempfile.TemporaryDirectory(prefix="p10dn_field_") as td:
            root=Path(td)
            z.extractall(root)
            safe=subprocess.run([sys.executable,str(root/"P10DN_m2_coefficient.py"),
                                 "--selftest"],cwd=root,capture_output=True,text=True,
                                timeout=45,stdin=subprocess.DEVNULL)
            if safe.returncode!=0 or "P10DN_M2_20PCT_FIELD_SELFTEST_OK" not in safe.stdout:
                raise RuntimeError("isolated field selftest failed: "+safe.stdout+safe.stderr)
            spec=importlib.util.spec_from_file_location("p10dn",root/"P10DN_m2_coefficient.py")
            obj=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(obj)
            if obj.check_source()!=len(SOURCES):
                raise RuntimeError("isolated source pin mismatch")
            geo=root/"P10DN_M2_FIELD20.geo"
            geo.write_bytes(geo.read_bytes()+b"\n// deliberate mutation\n")
            try:
                obj.check_source()
            except RuntimeError as err:
                if "pinned source changed" not in str(err):
                    raise
            else:
                raise RuntimeError("GEO source SHA corruption undetected")
    print("P10DN_M2_20PCT_SOURCE_ONLY_ZIP_OK",f"files={len(data)}",
          f"bytes={TARGET.stat().st_size}",
          "sha256="+sha256(TARGET.read_bytes()).hexdigest(),
          "isolated_selftest=PASS damaged_GEO_SHA=STOP Gmsh=0 physical_FEM=0")


if __name__=="__main__":
    run()
