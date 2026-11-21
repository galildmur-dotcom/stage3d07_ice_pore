#!/usr/bin/env python3
"""Build deterministic standalone P10DQ Windows 1D-only package from SHA-pinned P10DO."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/packages/P10DO_R1_M2_ONE_SHOT_GMSH_ONLY_WINDOWS_20261121.zip"
PROPOSAL = ROOT / "research/proposals/P10DQ_FIELD_DIAGNOSTIC_20261121"
OUTPUT = ROOT / "research/packages/P10DQ_R1_1D_FIELD_ISOLATION_WINDOWS_20261121.zip"
SOURCE_SHA = "6c6f4f574e6a8c436d8319e059e5d1341c8ecbeda5ba38fbc2587c03abb15535"
STOP_SHA = "547ce2c801b058658439ff157735dca1e28c4931b5da56f4b71e96a61723e220"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
REV = "P10DQ_R1_NATIVE_1D_FIELD_DIAGNOSTIC_NO_FEM"
BASE_NAMES = ("sphere_pore_B6_refined.geo", "P10DN_M2_FIELD20.geo",
              "P10DO_windows_guards.py")
NEW_NAMES = ("P10DQ_one_click_1d.py", "01_P10DQ_PREFLIGHT_ONLY.cmd",
             "02_P10DQ_ONE_1D_DIAGNOSTIC.cmd", "README_P10DQ_RU.md")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    assert digest(SOURCE.read_bytes()) == SOURCE_SHA
    assert (ROOT / "research/evidence/P10DQ_P10DO_M2_TIMEOUT_20261121/input/P10DO_EVIDENCE_TIMEOUT.zip").is_file()
    members = {}
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        for name in BASE_NAMES:
            members[name] = z.read(name)
    for name in NEW_NAMES:
        data = (PROPOSAL / name).read_bytes()
        if name.endswith(".cmd"):
            # Native Windows cmd.exe: pin the actual CRLF bytes in the release.
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        members[name] = data
    assert len(members) == 7
    pin = {
        "revision": REV,
        "physical_FEM": False,
        "three_dimensional_mesh": False,
        "one_dimensional_attempt_limit": 1,
        "p10do_source_zip_sha256": SOURCE_SHA,
        "p10do_stop_evidence_sha256": STOP_SHA,
        "accepted_m1_sha256": M1_SHA,
        "files": {n: digest(data) for n, data in sorted(members.items())},
    }
    members["P10DQ_SOURCE_SHA256.json"] = (json.dumps(
        pin, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        for name, data in sorted(members.items()):
            zi = zipfile.ZipInfo(name, date_time=(2026, 11, 21, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o644 << 16)
            z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None and len(z.namelist()) == 8
        for name, expected in pin["files"].items():
            assert digest(z.read(name)) == expected
    print("P10DQ_PACKAGE_BUILD_OK files=8 pinned=7 CRC=8/8",
          "bytes=%d" % OUTPUT.stat().st_size, "sha256=" + digest(OUTPUT.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
