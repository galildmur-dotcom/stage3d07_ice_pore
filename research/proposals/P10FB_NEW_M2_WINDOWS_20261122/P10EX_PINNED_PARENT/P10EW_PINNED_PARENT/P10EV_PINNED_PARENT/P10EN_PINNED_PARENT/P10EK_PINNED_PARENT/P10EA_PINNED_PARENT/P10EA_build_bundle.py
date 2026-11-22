#!/usr/bin/env python3
"""Reproducibly package P10EA; source-only, NEVER runs native Gmsh/FEM."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REV = "P10EA_R1_EXACT_INLINE_F6_ONE_M2_3D_MESH_ONLY"
P10DW_R2 = ROOT/"research/packages/P10DW_R2_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261122.zip"
P10DO_R1 = ROOT/"research/packages/P10DO_R1_M2_ONE_SHOT_GMSH_ONLY_WINDOWS_20261121.zip"
DW_SHA = "1418d8ccf8374b275b7112137e23e6a5a94e65e549a50b44cbd66b4f6105d04f"
DO_SHA = "6c6f4f574e6a8c436d8319e059e5d1341c8ecbeda5ba38fbc2587c03abb15535"
TARGET = ROOT/"research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip"

DW_FILES = (
    "01_P10DV_SOURCE_MATH_ONLY.cmd",
    "P10DN_M2_FIELD20.geo",
    "P10DV_M2_INLINE_FIELD20.geo",
    "P10DV_SOURCE_SHA256.json",
    "P10DV_inline_source_unit.py",
    "README_P10DV_RU.md",
    "sphere_pore_B6_refined.geo",
)
DO_FILES = (
    "01_P10DN_LABEL_M1_ONLY.cmd",
    "P10DN_SOURCE_SHA256SUMS.txt",
    "P10DN_build_bundle.py",
    "P10DN_m2_coefficient.py",
    "README_RU.md",
    "P10DO_windows_guards.py",
    "P10DE_compare_m1.py",
    "P10CT_u0_mesh_audit.py",
    "P10CK_curved_qp_audit.py",
    "P10CP_mesh_b6_profile.py",
)
NEW_FILES = (
    "01_P10EA_SAFE_M1_F6_PREFLIGHT_ONLY.cmd",
    "02_P10EA_ONE_M2_3D_MESH_ONLY.cmd",
    "P10EA_one_click_m2.py",
    "P10EA_m2_mesh_qa.py",
    "P10EA_build_bundle.py",
    "README_P10EA_RU.md",
)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def safe_zip(path: Path, expected_sha: str, names: tuple[str,...]) -> dict[str, bytes]:
    assert digest(path.read_bytes()) == expected_sha, "historical ZIP SHA changed: "+str(path)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, "historical ZIP CRC mismatch"
        assert len(set(z.namelist())) == len(z.namelist()), "duplicate ZIP filename"
        return {name: z.read(name) for name in names}


def isolated_python(folder: Path, *params: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(folder/"P10EA_one_click_m2.py"), *params],
                          cwd=folder,stdin=subprocess.DEVNULL,
                          capture_output=True,text=True,errors="replace",
                          check=False,timeout=timeout)


def build() -> dict:
    payload = safe_zip(P10DW_R2,DW_SHA,DW_FILES)
    inherited = safe_zip(P10DO_R1,DO_SHA,DO_FILES)
    assert not (payload.keys() & inherited.keys()), "ambiguous inherited file"
    payload.update(inherited)
    for name in NEW_FILES:
        assert name not in payload
        data = (HERE/name).read_bytes()
        if name.endswith(".cmd"):
            data = data.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
        payload[name] = data
    assert len(payload) == 23
    pin = {
        "revision":REV,
        "one_native_3d_max":1,
        "physical_FEM":False,
        "accepted_original_m1_sha256":
            "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f",
        "exact_inline_f6_sha256":
            "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561",
        "cad_geo_sha256":
            "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
        "gmsh_executable_sha256":
            "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1",
        "p10dw_r2_parent_zip_sha256":DW_SHA,
        "p10do_r1_qa_parent_zip_sha256":DO_SHA,
        "files":{name:digest(data) for name,data in sorted(payload.items())},
    }
    payload["P10EA_SOURCE_SHA256.json"]=(json.dumps(pin,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    TARGET.parent.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(TARGET,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,(2026,11,22,0,0,0))
            info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            out.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and len(z.namelist()) == len(payload)
        assert digest(z.read("P10DV_M2_INLINE_FIELD20.geo")) == pin["exact_inline_f6_sha256"]
        with tempfile.TemporaryDirectory(prefix="p10ea_source_only_") as temp:
            root=Path(temp)
            z.extractall(root)
            for name in NEW_FILES[:2]:
                data=(root/name).read_bytes()
                assert b"\xef\xbb\xbf" != data[:3] and b"\r\n" in data
                assert b'set "RC=%ERRORLEVEL%"' in data
            tested=isolated_python(root,"--selftest")
            assert tested.returncode==0 and "P10EA_SOURCE_M2_PACKAGE_SELFTEST_OK" in tested.stdout, (
                tested.stdout[-1000:]+"\n"+tested.stderr[-1000:])
            if os.name!="nt":
                denied=isolated_python(root,"--preflight-only",timeout=40)
                assert denied.returncode==2 and "Windows required" in denied.stdout
                assert not (root/"P10EA_RUNS/P10EA_ONE_M2_3D_USED.json").exists()
                assert len(list(root.glob("P10EA_RUNS/P10EA_*/P10EA_EVIDENCE.zip")))==1
                # No 3D when there is not even a successful 01 proof.
                denied_3d=isolated_python(root,"--one-m2",timeout=40)
                assert denied_3d.returncode==2 and "button 01" in denied_3d.stdout
                assert not (root/"P10EA_RUNS/P10EA_ONE_M2_3D_USED.json").exists()
            # Attacks are confined to disposable extracted files.
            src=root/"P10DV_M2_INLINE_FIELD20.geo"
            src.write_bytes(src.read_bytes()+b"\n// TAMPER\n")
            attacked=isolated_python(root,"--selftest")
            assert attacked.returncode!=0 and "modified source" in attacked.stderr
            src.write_bytes(payload["P10DV_M2_INLINE_FIELD20.geo"])
            fake=root/"P10DG_M1_CANDIDATE.msh"
            fake.write_text("NOT_ORIGINAL_M1",encoding="ascii")
            wrong=subprocess.run(
                [sys.executable,str(root/"P10EA_m2_mesh_qa.py"),"--m1",str(fake),
                 "--m2",str(fake),"--out",str(root/"FAKE_QA")],
                cwd=root,capture_output=True,text=True,check=False,timeout=20)
            assert wrong.returncode!=0 and "original SHA/basename" in wrong.stderr
            # Isolated source-level negative tests do not spoof Windows or
            # execute any native process: manual decline and new marker replay.
            guard_test = """
import builtins
import tempfile
from pathlib import Path
import P10EA_one_click_m2 as m
with tempfile.TemporaryDirectory(prefix="p10ea_manual_") as td:
    m.RUNS=Path(td)/"RUNS"
    m.PROOF=m.RUNS/"preflight.json"
    m.LOCAL_MARKER=m.RUNS/"one.json"
    m.global_marker=lambda:Path(td)/"profile.json"
    m.fresh_proof=lambda: {"revision":m.REV}
    m.preflight=lambda run,meta,prompt:{"B_EXACT_INLINE_F6":run/"NEVER_RUN.geo"}
    m.launch_m2=lambda *args: (_ for _ in ()).throw(AssertionError("native wrongly launched"))
    builtins.input=lambda prompt:"NO RUN"
    assert m.do_run(preflight_only=False)==2
    assert not m.LOCAL_MARKER.exists() and not m.global_marker().exists()
with tempfile.TemporaryDirectory(prefix="p10ea_markers_") as td:
    m.RUNS=Path(td)/"RUNS"
    m.RUNS.mkdir()
    m.LOCAL_MARKER=m.RUNS/"one.json"
    m.global_marker=lambda:Path(td)/"profile.json"
    m.consume_one_shot(m.RUNS/"fake_run",["gmsh.exe","-3"])
    assert m.LOCAL_MARKER.is_file() and m.global_marker().is_file()
    try:
        m.consume_one_shot(m.RUNS/"fake_run",["gmsh.exe","-3"])
    except RuntimeError as exc:
        assert "already" in str(exc) or "consumed" in str(exc)
    else:
        raise AssertionError("marker replay was accepted")
    assert m.LOCAL_MARKER.is_file() and m.global_marker().is_file()
print("P10EA_MANUAL_DECLINE_AND_MARKER_REPLAY_STOP")
"""
            guarded=subprocess.run([sys.executable,"-c",guard_test],cwd=root,
                                   capture_output=True,text=True,check=False,timeout=30)
            assert guarded.returncode==0 and "MARKER_REPLAY_STOP" in guarded.stdout, (
                guarded.stdout+"\n"+guarded.stderr)
            # Back to clean state, the same independent unit must pass.
            restored=isolated_python(root,"--selftest")
            assert restored.returncode==0
    result={"zip_path":str(TARGET),"sha256":digest(TARGET.read_bytes()),
            "bytes":TARGET.stat().st_size,"zip_members":len(payload),
            "source_pins":len(pin["files"]),"native_Gmsh_runs":0,
            "mesh_3d_runs":0,"physical_FEM_runs":0,
            "isolated_selftest":True,"negative_attacks":5}
    print("P10EA_M2_EXACT_INLINE_F6_SOURCE_PACKAGE_OK",
          "ZIP_CRC",str(result["zip_members"])+"/"+str(result["zip_members"]),
          "PIN",str(result["source_pins"])+"/"+str(result["source_pins"]),
          "math17075 27QP=PASS negative5/5=STOP Gmsh=0 FEM=0")
    print(json.dumps(result,indent=2))
    return result


if __name__=="__main__":
    build()
