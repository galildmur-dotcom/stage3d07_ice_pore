#!/usr/bin/env python3
"""Deterministic self-contained P10DW SOURCE-ONLY release builder; no Gmsh."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT/"research/proposals/P10DW_EXACT_INLINE_F6_1D_20261121"
P10DV_ZIP = ROOT/"research/packages/P10DV_R1_M2_EXACT_INLINE_KAPPA20_SOURCE_ONLY_WINDOWS_20261121.zip"
P10DT_ZIP = ROOT/"research/packages/P10DT_R1_THREE_1D_CONTRAST_WINDOWS_20261121.zip"
OUTPUT = ROOT/"research/packages/P10DW_R1_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261121.zip"
P10DV_SHA = "4c29c4a4d2fbe6ea537bc4103b1dc5f42112e68e85cc98a14dd7dce1cac2c571"
P10DT_SHA = "f540adb8f7e9dc4a58fea8ebe5784c99fe4f2607cb6b82cf5ac65dd398b1eb08"
GUARD_SHA = "4755b76f01938688d1adaab5492b709b7d7ecbe5b02904db63df1fb3894aedac"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
INLINE_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
REV = "P10DW_R1_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM"
NEW = ("P10DW_one_click_1d.py", "01_P10DW_SAFE_GEO_PREFLIGHT_ONLY.cmd",
       "02_P10DW_ONE_INLINE_F6_1D_ONLY.cmd", "README_P10DW_RU.md")


def hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def main() -> int:
    assert hash_bytes(P10DV_ZIP.read_bytes()) == P10DV_SHA, "P10DV parent ZIP changed"
    assert hash_bytes(P10DT_ZIP.read_bytes()) == P10DT_SHA, "P10DT guard ZIP changed"
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(P10DV_ZIP) as old:
        assert old.testzip() is None and len(old.namelist()) == 7, "P10DV source CRC"
        members = {name: old.read(name) for name in old.namelist()}
        oldpin = json.loads(members["P10DV_SOURCE_SHA256.json"])
        assert len(oldpin["files"]) == 6
        assert all(hash_bytes(members[n]) == v for n, v in oldpin["files"].items())
    with zipfile.ZipFile(P10DT_ZIP) as p10dt:
        assert p10dt.testzip() is None
        guard = p10dt.read("P10DO_windows_guards.py")
        assert hash_bytes(guard) == GUARD_SHA, "exact audited Windows native watchdog"
        members["P10DO_windows_guards.py"] = guard
    for name in NEW:
        data = (PROPOSAL/name).read_bytes()
        if name.endswith(".cmd"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        members[name] = data
    assert len(members) == 12, "P10DW release inventory"
    assert hash_bytes(members["P10DV_M2_INLINE_FIELD20.geo"]) == INLINE_SHA
    assert hash_bytes(members["sphere_pore_B6_refined.geo"]) == CAD_SHA
    pin = {"revision": REV, "physical_FEM": False, "mesh_2d_3d": False,
           "native_gmsh_runs_during_release": 0, "one_shot_native_1d_limit": 1,
           "gmsh_native_version": "4.15.2", "gmsh_binary_sha256": GMSH_SHA,
           "accepted_original_m1_sha256": M1_SHA,
           "p10dv_source_zip_sha256": P10DV_SHA,
           "p10dt_diagnostic_source_zip_sha256": P10DT_SHA,
           "inline_geo_sha256": INLINE_SHA, "cad_geo_sha256": CAD_SHA,
           "files": {n: hash_bytes(v) for n, v in sorted(members.items())}}
    members["P10DW_SOURCE_SHA256.json"] = (
        json.dumps(pin, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, payload in sorted(members.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as z:
        assert len(z.namelist()) == 13 and z.testzip() is None, "ZIP CRC13"
        assert all(hash_bytes(z.read(n)) == expected
                   for n, expected in pin["files"].items()), "PIN12"
        assert all(b"\r\n" in z.read(cmd) and
                   not z.read(cmd).startswith(b"\xef\xbb\xbf")
                   for cmd in NEW if cmd.endswith(".cmd")), "Windows CMD bytes"
        with tempfile.TemporaryDirectory(prefix="p10dw_source_unit_") as tmp:
            unpack = Path(tmp)
            z.extractall(unpack)
            test = subprocess.run([sys.executable, str(unpack/"P10DW_one_click_1d.py"),
                                   "--selftest"], stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=50)
            assert test.returncode == 0 and "P10DW_SOURCE_AND_MATH_SELFTEST_OK" in test.stdout, (
                "isolation failed: "+test.stdout+test.stderr)
    print("P10DW_PACKAGE_BUILD_OK zip_CRC13/13 source_PIN12/12 math=PASS "
          "native_Gmsh=0 mesh_1d_2d_3d=0 FEM=0 "
          "bytes="+str(OUTPUT.stat().st_size)+" SHA256="+hash_bytes(OUTPUT.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
