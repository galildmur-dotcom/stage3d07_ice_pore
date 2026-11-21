#!/usr/bin/env python3
"""Deterministic P10DG R1 Windows source ZIP; run NO native Gmsh or FEM."""
from __future__ import annotations

import hashlib
import csv
import io
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TARGET = REPO / "research/packages/P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121.zip"
REVISION = "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY"
FILES = {
    "P10DF_M1_FROM_H0_EMPIRICAL_CALIBRATION_CANDIDATE.geo":
        REPO / "gmsh/P10DF_M1_FROM_H0_EMPIRICAL_CALIBRATION_CANDIDATE.geo",
    "P10DF_H0_EMPIRICAL_M1_SOURCE_CALIBRATION.json":
        REPO / "research/evidence/P10DF_H0_EMPIRICAL_M1_SIZE_20261121/derived/P10DF_H0_EMPIRICAL_M1_SOURCE_CALIBRATION.json",
    "sphere_pore_B6_refined.geo": REPO / "gmsh/sphere_pore_B6_refined.geo",
    "P10DG_compare_m1.py": HERE / "P10DG_compare_m1.py",
    "P10DE_compare_m1.py":
        REPO / "research/proposals/P10DE_M1_GRADED_MESH_ONLY_20261121/P10DE_compare_m1.py",
    "P10DG_one_click_m1.py": HERE / "P10DG_one_click_m1.py",
    "P10DG_windows_guards.py": HERE / "P10DG_windows_guards.py",
    "01_RUN_P10DG_M1_MESH_ONLY.cmd": HERE / "01_RUN_P10DG_M1_MESH_ONLY.cmd",
    "README_RU.md": HERE / "README_RU.md",
    "P10CT_u0_mesh_audit.py":
        REPO / "research/proposals/P10CT_U0_MESH_ONLY_R1_20261121/P10CT_u0_mesh_audit.py",
    "P10CK_curved_qp_audit.py":
        REPO / "research/proposals/P10CK_CURVED_TET10_QP_R1_20261120/P10CK_curved_qp_audit.py",
    "P10CP_mesh_b6_profile.py":
        REPO / "research/proposals/P10CP_B6_READONLY_PROFILE_20261121/P10CP_mesh_b6_profile.py",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def execute(root: Path, argv: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *argv], cwd=root, text=True,
                          capture_output=True, timeout=timeout, check=False,
                          stdin=subprocess.DEVNULL)


def build() -> None:
    payload = {}
    for name, path in FILES.items():
        content = path.read_bytes()
        if name.endswith(".cmd"):
            content = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        payload[name] = content
    assert len(payload) == 12
    payload["P10DG_PINNED_SHA256.json"] = (
        json.dumps({
            "revision": REVISION, "files": {
                name: digest(content) for name, content in sorted(payload.items())
            },
            "h0_mesh_sha256": "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8",
            "candidate": "P10DF_H0_EMPIRICAL_SOURCE_ONLY",
            "mesh_attempt_max": 1, "physical_FEM": False,
        }, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, content in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and set(z.namelist()) == set(payload)
        with tempfile.TemporaryDirectory(prefix="p10dg_package_unit_") as temp:
            isolated = Path(temp)
            z.extractall(isolated)
            # Regression against the actual rejected P10DE primary radial CSV:
            # all five sufficiently populated H0 radial bands must trigger
            # the new local stop gate. No .msh and no Gmsh needed.
            old_evidence = (
                REPO / "research/evidence/P10DE_R1_M1_OVERREFINED_STOP_20261121"
                / "input/P10DE_EVIDENCE.zip"
            )
            with zipfile.ZipFile(old_evidence) as old:
                legacy_rows = list(csv.DictReader(io.StringIO(
                    old.read("QA/P10DE_M0_M1_RADIAL_MU_BINS.csv").decode("utf-8-sig"))))
            sys.path.insert(0, str(isolated))
            comparator = importlib.import_module("P10DG_compare_m1")
            _radial, old_issues = comparator.radial_volume_gate(legacy_rows)
            if len(old_issues) != 5:
                raise RuntimeError("old real over-refined M1 not rejected in 5 populated bands")
            cmd = (isolated / "01_RUN_P10DG_M1_MESH_ONLY.cmd").read_bytes()
            assert (not cmd.startswith(b"\xef\xbb\xbf") and b"\r\n" in cmd and
                    b":USING_PY\r\n" in cmd and b":USING_PYTHON\r\n" in cmd and
                    b"set \"RC=%ERRORLEVEL%\"" in cmd)
            selftest = execute(isolated, [str(isolated / "P10DG_one_click_m1.py"),
                                          "--selftest"])
            if selftest.returncode or "P10DG_ONECLICK_SYNTHETIC_OK" not in selftest.stdout:
                raise RuntimeError("P10DG isolated synthetic: " +
                                   selftest.stdout[-900:] + selftest.stderr[-900:])
            if sys.platform != "win32":
                # A plain click on Linux must STOP, emit evidence and never
                # attempt to run Gmsh or write the marker.
                safe = execute(isolated, [str(isolated / "P10DG_one_click_m1.py")],
                               timeout=30)
                evidence = list(isolated.glob("P10DG_RUNS/P10DG_M1_*/P10DG_EVIDENCE.zip"))
                assert safe.returncode == 2 and len(evidence) == 1
                assert not (isolated / "P10DG_RUNS/P10DG_ONE_SHOT_USED.json").exists()
                with zipfile.ZipFile(evidence[0]) as zstop:
                    assert zstop.testzip() is None
                    assert b"P10DG_STOP_NO_FEM" in zstop.read("P10DG_RESULT.txt")
                    assert b"ONLY on Windows" in zstop.read("P10DG_STOP_TRACE.txt")
            candidate = isolated / "P10DF_M1_FROM_H0_EMPIRICAL_CALIBRATION_CANDIDATE.geo"
            candidate.write_text(candidate.read_text(encoding="utf-8") +
                                 "\nnearSize=0.00017638037567728565;\n", encoding="utf-8")
            bad = execute(isolated, [str(isolated / "P10DG_one_click_m1.py"), "--selftest"])
            assert bad.returncode != 0 and "SHA mismatch" in bad.stderr
            # Restore only in temporary isolated testing directory.
            candidate.write_bytes(payload[candidate.name])
            calibration = isolated / "P10DF_H0_EMPIRICAL_M1_SOURCE_CALIBRATION.json"
            calibration.write_text(calibration.read_text(encoding="utf-8") +
                                   "\n{}\n", encoding="utf-8")
            bad2 = execute(isolated, [str(isolated / "P10DG_one_click_m1.py"), "--selftest"])
            assert bad2.returncode != 0 and "SHA mismatch" in bad2.stderr
    print("P10DG_BUILD_PACKAGE_OK ZIP13/13_CRC=PASS source_sha12=PASS "
          "isolated_selftest=PASS real_old_M1_radial5_STOP=PASS Linux_safe_STOP=PASS "
          "corrupted_GEO_and_calibration=REJECTED FEM=0 Gmsh=0")
    print("PATH", TARGET)
    print("SIZE_BYTES", TARGET.stat().st_size)
    print("SHA256", digest(TARGET.read_bytes()))


if __name__ == "__main__":
    build()
