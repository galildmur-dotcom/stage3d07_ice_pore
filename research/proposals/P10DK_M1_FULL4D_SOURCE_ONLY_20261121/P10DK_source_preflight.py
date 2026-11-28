#!/usr/bin/env python3
"""P10DK R1 independent source-only gate; never calls the physical solver."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PIN = ROOT / "P10DK_SOURCE_SHA256SUMS.txt"
M0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10DK_SOURCE_STOP: " + why)


def check_source() -> int:
    require(PIN.is_file(), "pinned source list is absent")
    raw = PIN.read_text(encoding="utf-8")
    lines = raw.splitlines()
    require(len(lines) >= 75, "incomplete source inventory")
    names = set()
    for line in lines:
        require(len(line) > 66 and line[64:66] == "  ",
                "malformed source SHA line")
        digest, name = line[:64], line[66:]
        require(name not in names and len(digest) == 64 and
                all(c in "0123456789abcdef" for c in digest),
                "bad/duplicate source entry")
        names.add(name)
        path = ROOT / name
        require(path.is_file() and
                hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                "published source was changed: " + name)
    require({"CMakeLists.txt", "stage3d10dk_m1_full4d.cpp",
             "src/stage3d10w_analytic_adjoint.cpp",
             "src/stage3d10p_partial_audit.cpp",
             "stage3d10dd_4d_partition.hpp",
             "P10DK_audit_evidence.py",
             "p10dd_4d_synthetic_unit.cpp"} <= names,
            "mandatory 4D source files are not pinned")
    wrapper = (ROOT / "stage3d10dk_m1_full4d.cpp").read_text(encoding="utf-8")
    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    require("#define STAGE3D10DD_FULL4D 1" in wrapper and
            "#define STAGE3D10DK_M1_FULL4D 1" in wrapper and
            "#ifndef STAGE3D10DK_PHYSICAL_ENABLED" in wrapper and
            "P10DK_SOURCE_ONLY_STOP_NO_FEM" in wrapper and
            "P10DK_ENABLE_PHYSICAL" in cmake and
            "message(FATAL_ERROR" in cmake,
            "source-only C++/CMake physical barrier not present")
    forbidden = os.path.normcase(str(Path("G:/ildar/Stage3D07")))
    root_lower = os.path.normcase(str(ROOT))
    require(root_lower != forbidden and
            not root_lower.startswith(forbidden + os.sep),
            "must extract outside historical Stage3D07 source")
    # ONLY a synthetic Python checker (which never reads .msh or runs FEM).
    report = subprocess.run(
        [sys.executable, str(ROOT / "P10DK_audit_evidence.py"), "--selftest"],
        cwd=ROOT, text=True, capture_output=True, check=False, timeout=45,
        stdin=subprocess.DEVNULL,
    )
    require(report.returncode == 0 and
            "P10DK_PY_7206_SYNTHETIC_ROWS_OK" in report.stdout and
            "H0_QP_SUBSTITUTION=DETECTED" in report.stdout and
            "physical_FEM=0" in report.stdout,
            "synthetic independent closure auditor failed: " +
            report.stdout[-300:] + report.stderr[-300:])
    print("P10DK_SOURCE_ONLY_OK", f"sha_verified={len(lines)}/{len(lines)}",
          "source_only=1", "Gmsh_runs=0", "physical_FEM=0")
    print("P10DK_D019_MESH_ID_PINNED", "M0=" + M0_SHA, "M1=" + M1_SHA)
    print(report.stdout.strip())
    return len(lines)


def main() -> int:
    check_source()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
