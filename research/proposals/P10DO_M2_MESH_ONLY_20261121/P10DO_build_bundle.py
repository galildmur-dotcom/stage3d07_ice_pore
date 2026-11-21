#!/usr/bin/env python3
"""Reproducible pinned Windows Gmsh M2 mesh-only ZIP; build never runs Gmsh."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REV="P10DO_R1_M2_GRADED_KAPPA20_MESH_ONLY"
PRIOR=ROOT/"research/packages/P10DN_R1_M2_COEFF20_SOURCE_ONLY_WINDOWS_20261121.zip"
PRIOR_SHA="2f0e4a222a35fba618f9123f6235325bd09af9ce0cdb67d425a0c94ce906489b"
TARGET=ROOT/"research/packages/P10DO_R1_M2_ONE_SHOT_GMSH_ONLY_WINDOWS_20261121.zip"
SOURCES={
    "P10DO_m2_mesh_qa.py":HERE/"P10DO_m2_mesh_qa.py",
    "P10DO_one_click_m2.py":HERE/"P10DO_one_click_m2.py",
    "P10DO_windows_guards.py":HERE/"P10DO_windows_guards.py",
    "01_P10DO_CHECK_M1_AND_GEO_ONLY.cmd":HERE/"01_P10DO_CHECK_M1_AND_GEO_ONLY.cmd",
    "02_P10DO_ONE_M2_MESH_ONLY.cmd":HERE/"02_P10DO_ONE_M2_MESH_ONLY.cmd",
    "README_P10DO_RU.md":HERE/"README_P10DO_RU.md",
    "P10DO_build_bundle.py":HERE/"P10DO_build_bundle.py",
    "P10DE_compare_m1.py":ROOT/"research/proposals/P10DE_M1_GRADED_MESH_ONLY_20261121/P10DE_compare_m1.py",
    "P10CT_u0_mesh_audit.py":ROOT/"research/proposals/P10CT_U0_MESH_ONLY_R1_20261121/P10CT_u0_mesh_audit.py",
    "P10CK_curved_qp_audit.py":ROOT/"research/proposals/P10CK_CURVED_TET10_QP_R1_20261120/P10CK_curved_qp_audit.py",
    "P10CP_mesh_b6_profile.py":ROOT/"research/proposals/P10CP_B6_READONLY_PROFILE_20261121/P10CP_mesh_b6_profile.py",
}


def digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def run_test(root: Path, argv: list[str], timeout: int=120) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable,*argv],cwd=root,text=True,
                          capture_output=True,check=False,timeout=timeout,
                          stdin=subprocess.DEVNULL)


def build() -> None:
    assert digest(PRIOR.read_bytes())==PRIOR_SHA,"original P10DN ZIP changed"
    payload={}
    with zipfile.ZipFile(PRIOR) as prior:
        assert prior.testzip() is None and len(prior.namelist())==7
        for name in prior.namelist():
            assert name and name==Path(name).name and name not in payload
            payload[name]=prior.read(name)
    for name,path in SOURCES.items():
        assert name not in payload
        content=path.read_bytes()
        if name.endswith(".cmd"):
            content=content.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
        payload[name]=content
    assert len(payload)==18
    payload["P10DO_PINNED_SHA256.json"]=(json.dumps({
        "revision":REV,
        "mesh_attempt_max":1,"physical_FEM":False,
        "accepted_m1_sha256":"ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f",
        "p10dn_parent_source_zip_sha256":PRIOR_SHA,
        "files":{name:digest(data) for name,data in sorted(payload.items())},
    },indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(TARGET,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,(2026,11,21,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and len(z.namelist())==len(payload)
        with tempfile.TemporaryDirectory(prefix="p10do_mesh_") as temp:
            root=Path(temp)
            z.extractall(root)
            for name in ("01_P10DO_CHECK_M1_AND_GEO_ONLY.cmd",
                         "02_P10DO_ONE_M2_MESH_ONLY.cmd"):
                cmd=(root/name).read_bytes()
                assert not cmd.startswith(b"\xef\xbb\xbf") and b"\r\n" in cmd
                assert b'set "RC=%ERRORLEVEL%"' in cmd
            good=run_test(root,[str(root/"P10DO_one_click_m2.py"),"--selftest"])
            assert good.returncode==0 and "P10DO_M2_PACKAGE_SELFTEST_OK" in good.stdout, (
                good.stdout[-600:]+good.stderr[-600:])
            if sys.platform!="win32":
                stop=run_test(root,[str(root/"P10DO_one_click_m2.py"),"--m1",
                                    str(root/"wrong_original_M1.msh")],timeout=40)
                assert stop.returncode==2 and "ONLY on Windows" in stop.stdout
                assert not list(root.glob("P10DO_RUNS/P10DO_ONE_SHOT_USED.json"))
                evidence=list(root.glob("P10DO_RUNS/P10DO_M2_*/P10DO_EVIDENCE.zip"))
                assert len(evidence)==1
                with zipfile.ZipFile(evidence[0]) as ez:
                    assert ez.testzip() is None and b"P10DO_STOP_NO_FEM" in ez.read(
                        "P10DO_RESULT.txt")
            geo=root/"P10DN_M2_FIELD20.geo"
            geo.write_bytes(geo.read_bytes()+b"\n// deliberate malicious changed GEO\n")
            bad=run_test(root,[str(root/"P10DO_one_click_m2.py"),"--selftest"])
            assert bad.returncode!=0 and "pinned source SHA mismatch" in bad.stderr
            # Restore only an isolated test file, never the original package.
            geo.write_bytes(payload["P10DN_M2_FIELD20.geo"])
            code=root/"P10DO_m2_mesh_qa.py"
            fake=root/"P10DG_M1_CANDIDATE.msh"
            fake.write_text("INVALID_TEST_MESH",encoding="ascii")
            negative=run_test(root,[str(code),"--m1",str(fake),"--m2",str(fake),
                                    "--out",str(root/"WRONG")])
            assert negative.returncode!=0 and "original SHA/basename" in negative.stderr
    print("P10DO_M2_MESH_ONLY_PACKAGE_OK files=19 source_pin18=PASS ZIP_CRC=PASS "
          "isolated_27QP=PASS Linux_no_Gmsh_STOP=PASS damaged_GEO_STOP=PASS "
          "fake_M1_SHA_STOP=PASS physical_FEM=0 Gmsh=0")
    print("ZIP",TARGET)
    print("BYTES",TARGET.stat().st_size)
    print("SHA256",digest(TARGET.read_bytes()))


if __name__=="__main__":
    build()
