#!/usr/bin/env python3
"""Immutable self-contained P10DV source/math ZIP; never starts native Gmsh/FEM."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
ORIGINAL = ROOT/"research/packages/P10DN_R1_M2_COEFF20_SOURCE_ONLY_WINDOWS_20261121.zip"
P10DT = ROOT/"research/packages/P10DT_R1_THREE_1D_CONTRAST_WINDOWS_20261121.zip"
P10DU = ROOT/"research/evidence/P10DU_P10DT_REAL_NESTED_F3_1D_STOP_20261121/input/P10DT_EVIDENCE.zip"
OUTPUT = ROOT/"research/packages/P10DV_R1_M2_EXACT_INLINE_KAPPA20_SOURCE_ONLY_WINDOWS_20261121.zip"
ORIGINAL_SHA = "2f0e4a222a35fba618f9123f6235325bd09af9ce0cdb67d425a0c94ce906489b"
GEO_SHA = "d948d7b2b29d70435bbf58bc4ee22f91de353e9162fd954f6fe56a2a40f3ca4f"
P10DT_SHA = "f540adb8f7e9dc4a58fea8ebe5784c99fe4f2607cb6b82cf5ac65dd398b1eb08"
P10DU_SHA = "9c4602ac29a08dd8faa5e977990a3f138f73a39c242dcc3167b09f23bf46d414"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
FIELD_CPP_SHA = "427911696c813c5543caa37b527a985775fa6d4e"
REV = "P10DV_R1_EXACT_INLINE_C1_KAPPA20_SOURCE_ONLY_NO_GMSH_NO_FEM"
OLD = ("P10DN_M2_FIELD20.geo", "sphere_pore_B6_refined.geo")
NEW = ("P10DV_M2_INLINE_FIELD20.geo", "P10DV_inline_source_unit.py",
       "01_P10DV_SOURCE_MATH_ONLY.cmd", "README_P10DV_RU.md")


def hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def main() -> int:
    assert hash_bytes(ORIGINAL.read_bytes()) == ORIGINAL_SHA, "P10DN source release changed"
    assert hash_bytes(P10DT.read_bytes()) == P10DT_SHA, "P10DT source release changed"
    assert hash_bytes(P10DU.read_bytes()) == P10DU_SHA, "original Windows P10DT evidence changed"
    members = {}
    with zipfile.ZipFile(ORIGINAL) as z:
        assert z.testzip() is None and len(z.namelist()) == 7, "original P10DN ZIP CRC"
        for name in OLD:
            members[name] = z.read(name)
            assert members[name] == (PROPOSAL/name).read_bytes(), "copied original GEO/CAD changed"
    assert hash_bytes(members[OLD[0]]) == GEO_SHA
    for name in NEW:
        data = (PROPOSAL/name).read_bytes()
        if name.endswith(".cmd"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        members[name] = data
    assert len(members) == 6
    pin = {"revision": REV, "native_gmsh_runs": 0, "mesh_1d_2d_3d_runs": 0,
           "physical_FEM": False, "accepted_original_m1_sha256": M1_SHA,
           "original_p10dn_geo_sha256": GEO_SHA,
           "original_p10dn_source_zip_sha256": ORIGINAL_SHA,
           "p10dt_source_zip_sha256": P10DT_SHA,
           "p10dt_windows_evidence_zip_sha256": P10DU_SHA,
           "gmsh_4_15_2_Field_cpp_git_blob_sha": FIELD_CPP_SHA,
           "files": {n: hash_bytes(data) for n, data in sorted(members.items())}}
    members["P10DV_SOURCE_SHA256.json"] = (
        json.dumps(pin, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(members.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 21, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o644 << 16)
            z.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None and len(z.namelist()) == 7
        for name, expected in pin["files"].items():
            assert hash_bytes(z.read(name)) == expected
        assert b"\r\n" in z.read("01_P10DV_SOURCE_MATH_ONLY.cmd")
        assert not z.read("01_P10DV_SOURCE_MATH_ONLY.cmd").startswith(b"\xef\xbb\xbf")
        with tempfile.TemporaryDirectory(prefix="p10dv_source_only_") as temp:
            folder = Path(temp)
            z.extractall(folder)
            res = subprocess.run([sys.executable, str(folder/"P10DV_inline_source_unit.py"),
                                  "--selftest"], capture_output=True, text=True,
                                 check=False, timeout=35, stdin=subprocess.DEVNULL)
            assert res.returncode == 0 and "P10DV_SOURCE_MATH_INLINE_C1_KAPPA20_PASS" in res.stdout, (
                "isolated source math failed " + res.stdout + res.stderr)
    print("P10DV_PACKAGE_BUILD_OK CRC7/7 PIN6/6 isolated_math=PASS native_Gmsh=0 FEM=0",
          "bytes="+str(OUTPUT.stat().st_size), "SHA256="+hash_bytes(OUTPUT.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
