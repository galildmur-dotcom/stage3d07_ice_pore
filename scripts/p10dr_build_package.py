#!/usr/bin/env python3
"""Build immutable deterministic P10DR Windows 1D-only ZIP; no native Gmsh."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "research/proposals/P10DR_F3_F4_1D_ISOLATION_20261121"
P10DQ = ROOT / "research/packages/P10DQ_R1_1D_FIELD_ISOLATION_WINDOWS_20261121.zip"
EVIDENCE = ROOT / "research/evidence/P10DR_P10DQ_WINDOWS_FIELD_CHAIN_STOP_20261121/input/P10DQ_EVIDENCE.zip"
OUTPUT = ROOT / "research/packages/P10DR_R1_F3_F4_1D_ISOLATION_WINDOWS_20261121.zip"
SOURCE_SHA = "c79787de1788d98c5499e0263293fd3ce3100bc779c6891b5f6b7f74221c2905"
EVIDENCE_SHA = "35e859aefb089b1bdb08a02570009a956424585b691fc72b65e46aca519020f2"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
REV = "P10DR_R1_F3_F4_1D_ONLY_NO_FEM"
OLD = ("sphere_pore_B6_refined.geo", "P10DN_M2_FIELD20.geo", "P10DO_windows_guards.py")
NEW = ("P10DR_one_click_1d.py", "01_P10DR_PREFLIGHT_ONLY.cmd",
       "02_P10DR_ONE_1D_DIAGNOSTIC.cmd", "README_P10DR_RU.md")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    assert digest(P10DQ.read_bytes()) == SOURCE_SHA, "P10DQ release changed"
    assert digest(EVIDENCE.read_bytes()) == EVIDENCE_SHA, "original Windows evidence changed"
    members = {}
    with zipfile.ZipFile(P10DQ) as z:
        assert z.testzip() is None and len(z.namelist()) == 8
        for name in OLD:
            members[name] = z.read(name)
    for name in NEW:
        data = (PROPOSAL/name).read_bytes()
        if name.endswith(".cmd"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        members[name] = data
    assert len(members) == 7
    pin = {"revision": REV, "physical_FEM": False, "mesh_2d_3d": False,
           "diagnostic_sequence_limit": 1, "max_native_1d_variants": 7,
           "accepted_m1_sha256": M1_SHA,
           "p10dq_source_zip_sha256": SOURCE_SHA,
           "p10dq_evidence_zip_sha256": EVIDENCE_SHA,
           "files": {n: digest(data) for n, data in sorted(members.items())}}
    members["P10DR_SOURCE_SHA256.json"] = (
        json.dumps(pin, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(members.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 21, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o644 << 16)
            z.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None and len(z.namelist()) == 8
        for name, expected in pin["files"].items():
            assert digest(z.read(name)) == expected, "bad source pin " + name
        for name in NEW:
            if name.endswith(".cmd"):
                assert b"\r\n" in z.read(name) and not z.read(name).startswith(b"\xef\xbb\xbf")
    print("P10DR_PACKAGE_BUILD_OK ZIP_CRC=8/8 PIN=7/7 native_Gmsh=0 physical_FEM=0",
          "bytes="+str(OUTPUT.stat().st_size), "SHA256="+digest(OUTPUT.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
