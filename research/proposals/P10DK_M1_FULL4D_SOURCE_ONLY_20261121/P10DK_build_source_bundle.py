#!/usr/bin/env python3
"""Deterministic P10DK M1 full4D source-only Windows ZIP. Never runs FEM."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGET = REPO / "research/packages/P10DK_R1_M1_FULL4D_SOURCE_ONLY_WINDOWS_20261121.zip"
SUFFIXES = {".cpp", ".hpp", ".inc"}
EXTRA = {
    "CMakeLists.txt": HERE / "CMakeLists.txt",
    "stage3d10dk_m1_full4d.cpp": HERE / "stage3d10dk_m1_full4d.cpp",
    "stage3d10dd_4d_partition.hpp":
        REPO / "research/proposals/P10DD_M0_H0_FULL4D_20261121/stage3d10dd_4d_partition.hpp",
    "p10dd_4d_synthetic_unit.cpp":
        REPO / "research/proposals/P10DD_M0_H0_FULL4D_20261121/p10dd_4d_synthetic_unit.cpp",
    "P10DK_audit_evidence.py": HERE / "P10DK_audit_evidence.py",
    "P10DK_source_preflight.py": HERE / "P10DK_source_preflight.py",
    "01_P10DK_CHECK_SOURCE_ONLY.cmd": HERE / "01_P10DK_CHECK_SOURCE_ONLY.cmd",
    "README_RU.md": HERE / "README_RU.md",
}
EXPECTED_M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"


def run() -> None:
    files = dict(EXTRA)
    for folder in ("src", "tests"):
        for file in sorted((REPO / folder).iterdir()):
            if file.is_file() and file.suffix in SUFFIXES:
                files[f"{folder}/{file.name}"] = file
    if len(files) < 75:
        raise RuntimeError("P10DK_STOP: incomplete production C++/unit inventory")
    payload: dict[str, bytes] = {}
    for name, file in sorted(files.items()):
        data = file.read_bytes()
        if name.endswith(".cmd"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        payload[name] = data
    if EXPECTED_M1_SHA.encode() not in payload["P10DK_source_preflight.py"]:
        raise RuntimeError("P10DK source does not pin accepted D-019 M1 SHA")
    pin = "".join(f"{sha256(payload[name]).hexdigest()}  {name}\n"
                  for name in sorted(payload))
    payload["P10DK_SOURCE_SHA256SUMS.txt"] = pin.encode("utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8) as out:
        for name, contents in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            out.writestr(info, contents, compress_type=zipfile.ZIP_DEFLATED,
                         compresslevel=8)
    with zipfile.ZipFile(TARGET) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(payload):
            raise RuntimeError("P10DK source ZIP CRC/count mismatch")
        with tempfile.TemporaryDirectory(prefix="p10dk_source_unit_") as temp:
            dest = Path(temp)
            archive.extractall(dest)
            result = subprocess.run(
                [sys.executable, str(dest / "P10DK_source_preflight.py")],
                cwd=dest, capture_output=True, text=True, timeout=60,
                stdin=subprocess.DEVNULL, check=False)
            if result.returncode != 0 or "P10DK_SOURCE_ONLY_OK" not in result.stdout:
                raise RuntimeError("P10DK isolated source check: " +
                                   result.stdout[-400:] + result.stderr[-400:])
            # Negative pin tampering: one modified source must STOP safely.
            target = dest / "stage3d10dk_m1_full4d.cpp"
            target.write_text(target.read_text(encoding="utf-8") +
                              "\n// mutated source for negative test\n",
                              encoding="utf-8")
            bad = subprocess.run(
                [sys.executable, str(dest / "P10DK_source_preflight.py")],
                cwd=dest, capture_output=True, text=True, timeout=60,
                stdin=subprocess.DEVNULL, check=False)
            if bad.returncode != 2 or "published source was changed" not in bad.stderr:
                raise RuntimeError("P10DK changed-source negative not rejected")
    print("P10DK_R1_SOURCE_ONLY_ZIP_OK",
          f"files={len(payload)}", f"bytes={TARGET.stat().st_size}",
          f"sha256={sha256(TARGET.read_bytes()).hexdigest()}",
          "isolated_sha=PASS negative_source_tamper=PASS",
          "Gmsh=0 FEM=0")


if __name__ == "__main__":
    run()
