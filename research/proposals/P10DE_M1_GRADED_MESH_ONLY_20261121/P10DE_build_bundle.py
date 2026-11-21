#!/usr/bin/env python3
"""Build deterministic, source-pinned one-click P10DE Windows mesh-only ZIP.

No Gmsh/FEM invocation; only package source files, run isolated Python selftest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TARGET = REPO / "research/packages/P10DE_R1_M1_GRADED_MESH_ONLY_WINDOWS_20261121.zip"
REVISION = "P10DE_R1_M1_GRADED_20PCT_VOLUME_MESH_ONLY"
FILES = {
    "P10DC_M1_FROM_H0_20PCT_VOLUME.geo": REPO / "gmsh/P10DC_M1_FROM_H0_20PCT_VOLUME.geo",
    "sphere_pore_B6_refined.geo": REPO / "gmsh/sphere_pore_B6_refined.geo",
    "P10DE_compare_m1.py": HERE / "P10DE_compare_m1.py",
    "P10DE_one_click_m1.py": HERE / "P10DE_one_click_m1.py",
    "01_RUN_P10DE_M1_MESH_ONLY.cmd": HERE / "01_RUN_P10DE_M1_MESH_ONLY.cmd",
    "README_RU.md": HERE / "README_RU.md",
    "P10CT_u0_mesh_audit.py": REPO / "research/proposals/P10CT_U0_MESH_ONLY_R1_20261121/P10CT_u0_mesh_audit.py",
    "P10CK_curved_qp_audit.py": REPO / "research/proposals/P10CK_CURVED_TET10_QP_R1_20261120/P10CK_curved_qp_audit.py",
    "P10CP_mesh_b6_profile.py": REPO / "research/proposals/P10CP_B6_READONLY_PROFILE_20261121/P10CP_mesh_b6_profile.py",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> None:
    payload = {}
    for name, path in FILES.items():
        data = path.read_bytes()
        if name.endswith(".cmd"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        payload[name] = data
    manifest = {
        "revision": REVISION, "files": {name: digest(data) for name, data in sorted(payload.items())},
        "h0_mesh_sha256": "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8",
        "mesh_only": True, "physical_FEM": False, "mesh_attempt_max": 1,
    }
    payload["P10DE_PINNED_SHA256.json"] = (
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 << 16)
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and set(z.namelist()) == set(payload)
        with tempfile.TemporaryDirectory(prefix="p10de_bundle_test_") as td:
            root = Path(td)
            z.extractall(root)
            r = subprocess.run([sys.executable, str(root / "P10DE_one_click_m1.py"),
                                "--selftest"], text=True, capture_output=True, timeout=90, cwd=td)
            if r.returncode != 0 or "P10DE_ONECLICK_SYNTHETIC_OK" not in r.stdout:
                raise RuntimeError("isolated bundle selftest: " + r.stdout + r.stderr)
            if sys.platform != "win32":
                stopped = subprocess.run(
                    [sys.executable, str(root / "P10DE_one_click_m1.py")],
                    text=True, capture_output=True, timeout=30, cwd=td,
                    stdin=subprocess.DEVNULL)
                evidence = list(root.glob("P10DE_RUNS/P10DE_M1_*/P10DE_EVIDENCE.zip"))
                if stopped.returncode != 2 or len(evidence) != 1 or (
                        root / "P10DE_RUNS/P10DE_ONE_SHOT_USED.json").exists():
                    raise RuntimeError("non-Windows execution did not stop before Gmsh")
                with zipfile.ZipFile(evidence[0]) as stopzip:
                    assert stopzip.testzip() is None
                    assert b"P10DE_STOP_NO_FEM" in stopzip.read("P10DE_RESULT.txt")
                    assert b"on Windows" in stopzip.read("P10DE_STOP_TRACE.txt")
            # Any post-package geometry mutation must trigger SHA/size STOP.
            geo = root / "P10DC_M1_FROM_H0_20PCT_VOLUME.geo"
            geo.write_text(geo.read_text() + "\nnearSize=1.0;\n", encoding="utf-8")
            bad = subprocess.run([sys.executable, str(root / "P10DE_one_click_m1.py"),
                                  "--selftest"], text=True, capture_output=True, timeout=90, cwd=td)
            if bad.returncode == 0 or "SHA mismatch" not in bad.stderr:
                raise RuntimeError("negative altered M1 GEO did not fail")
    print("P10DE_BUILD_PACKAGE_OK ZIP10/10_CRC=PASS isolated_selftest=PASS"
          " non_windows=SAFE_STOP corrupt_geometry=REJECTED FEM=0")
    print("PATH", TARGET)
    print("SIZE_BYTES", TARGET.stat().st_size)
    print("SHA256", digest(TARGET.read_bytes()))


if __name__ == "__main__":
    build()
