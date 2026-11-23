#!/usr/bin/env python3
"""Deterministic P10GJ source-only Windows release with offline safeguards."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10GJ_ONE_ROTATED_HXT10_WINDOWS_20261123"
ZIP=ROOT/"research/packages/P10GJ_R1_ONE_ROTATED_HXT10_M1_WINDOWS_20261123.zip"
PIN=SRC/"P10GJ_SOURCE_SHA256.json"
REV="P10GJ_R1_M0_PREREG_ONE_ROTATED_HXT10_3D_NO_FEM"
FILES={
  "P10GJ_one_click_m1.py","P10GJ_mesh_extra.py",
  "P10FN_common.py","P10FN_mesh_qa.py","P10CK_curved_qp_audit.py",
  "p10gi_independent_surface_audit.py","P10GJ_D027_GATE_POLICY.json",
  "P10GJ_M0_QP_BASELINE.json","README_P10GJ_RU.md",
  "01_P10GJ_PREFLIGHT_FREEZE_GATES.cmd","02_P10GJ_ONE_HXT10_3D_ONLY.cmd",
  "M0.geo","M0_ROTATED.geo","sphere_pore_B6_refined.geo",
  "sphere_pore_B6_refined_rotated.geo","P10GJ_M1_ROTATED_CANDIDATE.geo"}
GEO_SHAS={"M0.geo":"ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa",
          "sphere_pore_B6_refined.geo":"8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
          "M0_ROTATED.geo":"21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a",
          "sphere_pore_B6_refined_rotated.geo":"e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329"}


def sha(data):return hashlib.sha256(data).hexdigest()


def cmd(folder,flag):
    return subprocess.run([sys.executable,str(folder/"P10GJ_one_click_m1.py"),flag],
                          cwd=folder,text=True,capture_output=True,timeout=60)


def main():
    for p,h in GEO_SHAS.items():
        assert sha((SRC/p).read_bytes())==h,(p,"canonical source changed")
    policy=json.loads((SRC/"P10GJ_D027_GATE_POLICY.json").read_text())
    assert policy["mandatory_global_Veff_ratio"]==[.8,.85]
    assert policy["required_sampled_detJ_positive_QP"]==[27,343,729]
    pins={n:sha((SRC/n).read_bytes()) for n in sorted(FILES)}
    manifest={"revision":REV,"date":"2026-11-23","model":"Stage3D07",
              "parent_M0_msh_sha256":
              "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6",
              "D027_policy_sha256":pins["P10GJ_D027_GATE_POLICY.json"],
              "M0_baseline_343_729QP_sha256":pins["P10GJ_M0_QP_BASELINE.json"],
              "nominal_volume_ratio":.825,"global_Veff_required":[.80,.85],
              "candidate":"P10GJ_M1_ROTATED_CANDIDATE",
              "native_3d_max_attempts":1,"FEM_max_attempts":0,
              "source_only_build":True,"files":pins}
    PIN.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    first=cmd(SRC,"--selftest")
    assert first.returncode==0 and "P10GJ_SOURCE_AND_PRE_REGISTERED_POLICY_PASS" in first.stdout,(first.stdout,first.stderr)
    spec=importlib.util.spec_from_file_location("p10gj_tests",ROOT/"scripts/test_p10gj_one_hxt10.py")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    suite=unittest.defaultTestLoader.loadTestsFromModule(mod)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    assert result.wasSuccessful(),"P10GJ offline unit tests failed"
    ZIP.parent.mkdir(parents=True,exist_ok=True)
    names=sorted((*FILES,PIN.name))
    with zipfile.ZipFile(ZIP,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name in names:
            z=zipfile.ZipInfo(name,(2026,11,23,0,0,0))
            z.compress_type=zipfile.ZIP_DEFLATED
            z.external_attr=0o100644<<16
            out.writestr(z,(SRC/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None and z.namelist()==names
        assert all(z.read(n)==(SRC/n).read_bytes() for n in names)
        with tempfile.TemporaryDirectory(prefix="P10GJ_RELEASE_TEST_") as tmp:
            d=Path(tmp);z.extractall(d)
            a=cmd(d,"--selftest")
            assert a.returncode==0 and "P10GJ_SOURCE_AND_PRE_REGISTERED_POLICY_PASS" in a.stdout,(a.stdout,a.stderr)
            b=cmd(d,"--preflight")
            c=cmd(d,"--one-hxt10")
            assert b.returncode==2 and "Windows 11" in b.stderr,(b.stdout,b.stderr)
            assert c.returncode==2 and "Windows 11" in c.stderr,(c.stdout,c.stderr)
            file=d/"README_P10GJ_RU.md"
            file.write_bytes(file.read_bytes()+b"\nTAMPERED\n")
            e=cmd(d,"--selftest")
            assert e.returncode==2 and "tampered release source" in e.stderr,(e.stdout,e.stderr)
    print("P10GJ_RELEASE_ZIP_CRC_EXTRACT_SELFTEST_LINUX_STOP_TAMPER_STOP_PASS")
    print("ZIP_PATH="+str(ZIP))
    print("ZIP_SHA256="+sha(ZIP.read_bytes()))
    print("ZIP_BYTES="+str(ZIP.stat().st_size))
    print("ZIP_FILES="+str(len(names)))
    print("NATIVE_GMSH_3D=0 FEM=0")


if __name__=="__main__":main()
