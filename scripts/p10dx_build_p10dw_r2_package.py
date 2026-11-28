#!/usr/bin/env python3
"""Build P10DW R2 from immutable R1 release with strictly two GEO EOL fixes."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT/"research/packages/P10DW_R1_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261121.zip"
EVIDENCE = (ROOT/"research/evidence/P10DX_P10DW_R1_WINDOWS_NEWLINE_STOP_20261122"
            /"input/P10DW_EVIDENCE.zip")
OUTPUT = ROOT/"research/packages/P10DW_R2_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261122.zip"
README = (ROOT/"research/proposals/P10DW_R2_WINDOWS_EOL_20261122"
          /"README_P10DW_R2_RU.md")
SHA_R1 = "04d619e6924bb5d8f0e3076c2bb371e67f78a174252658eacf8a0fdc14a95377"
SHA_WINDOWS = "d173de50c73167e3badbfe42c3fabb87b2ad345ac47f44623585a7da16655acc"
SHA_GEO = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
REV1 = "P10DW_R1_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM"
REV2 = "P10DW_R2_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM"


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def replace_exact(source: bytes, old: bytes, new: bytes, label: str) -> bytes:
    assert source.count(old) == 1, "R1 original not unique: "+label
    return source.replace(old, new, 1)


def make_members() -> tuple[dict[str, bytes], dict]:
    assert digest(R1.read_bytes()) == SHA_R1, "parent R1 ZIP must be immutable"
    assert digest(EVIDENCE.read_bytes()) == SHA_WINDOWS, "genuine Windows STOP evidence pin"
    with zipfile.ZipFile(R1) as z:
        assert z.testzip() is None and len(z.namelist()) == 13, "R1 CRC13/13"
        old = {name: z.read(name) for name in z.namelist()}
    pin = json.loads(old.pop("P10DW_SOURCE_SHA256.json"))
    assert pin["revision"] == REV1 and len(pin["files"]) == 12
    assert all(digest(old[k]) == v for k, v in pin["files"].items()), "R1 pin12"
    py = old["P10DW_one_click_1d.py"]
    changes = (
        (b'REV = "'+REV1.encode()+b'"', b'REV = "'+REV2.encode()+b'"', "revision"),
        (b'baseline_path.write_text(baseline, encoding="utf-8")',
         b'baseline_path.write_bytes(baseline.encode("utf-8"))', "baseline UTF8 bytes"),
        (b'exact_path.write_text(exact, encoding="utf-8")',
         b'exact_path.write_bytes(exact.encode("utf-8"))', "exact F6 UTF8 bytes"),
    )
    for source, replacement, label in changes:
        py = replace_exact(py, source, replacement, label)
    assert b'baseline_path.write_text' not in py and b'exact_path.write_text' not in py
    assert py.count(b'write_bytes(') >= 2 and b'"-1"' in py
    old["P10DW_one_click_1d.py"] = py
    for cmd in ("01_P10DW_SAFE_GEO_PREFLIGHT_ONLY.cmd",
                "02_P10DW_ONE_INLINE_F6_1D_ONLY.cmd"):
        old[cmd] = replace_exact(old[cmd], b"P10DW R1", b"P10DW R2", cmd)
    old["README_P10DW_RU.md"] = README.read_bytes()
    assert digest(old["P10DV_M2_INLINE_FIELD20.geo"]) == SHA_GEO
    assert len(old) == 12, "R2 must not add a native runner"
    pin["revision"] = REV2
    pin["p10dw_r1_parent_release_sha256"] = SHA_R1
    pin["p10dx_original_windows_preflight_stop_sha256"] = SHA_WINDOWS
    pin["eol_fix"] = "exact generated GEO bytes UTF8 (no Windows CRLF conversion)"
    pin["one_shot_identity_shared_with_r1"] = True
    pin["native_gmsh_runs_during_release"] = 0
    pin["files"] = {name: digest(data) for name, data in sorted(old.items())}
    old["P10DW_SOURCE_SHA256.json"] = (
        json.dumps(pin, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    return old, pin


def main() -> int:
    members, pin = make_members()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None and len(z.namelist()) == 13, "R2 CRC13"
        assert all(digest(z.read(name)) == digest(data)
                   for name, data in members.items()), "R2 roundtrip SHA"
        assert all(digest(z.read(name)) == expected
                   for name, expected in pin["files"].items()), "R2 pin12"
        assert all(b"\r\n" in z.read(name) and
                   not z.read(name).startswith(b"\xef\xbb\xbf")
                   for name in members if name.endswith(".cmd")), "CMD CRLF no BOM"
        with tempfile.TemporaryDirectory(prefix="p10dw_r2_isolated_") as tmp:
            dest = Path(tmp)
            z.extractall(dest)
            unit = subprocess.run([sys.executable, str(dest/"P10DW_one_click_1d.py"),
                                   "--selftest"], stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=40)
            assert unit.returncode == 0 and "P10DW_SOURCE_AND_MATH_SELFTEST_OK" in unit.stdout, (
                "isolated selftest " + unit.stdout + unit.stderr)
    print("P10DW_R2_PACKAGE_BUILD_OK CRC13/13 PIN12/12 isolated_math=PASS "
          "native_Gmsh=0 M2=0 FEM=0 "
          "bytes="+str(OUTPUT.stat().st_size)+" SHA256="+digest(OUTPUT.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
