"""Deterministically package a standalone launcher for the immutable R2 EXE."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGET = ROOT / "research/packages/P10DD_RUNTIME_GATE_R1_WINDOWS_20261121.zip"
NAMES = (
    "P10DD_runtime_gate.py",
    "01_P10DD_START_WITH_MINGW_RUNTIME.cmd",
    "README_RU.md",
)


def main() -> None:
    lines = []
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8) as out:
        for name in NAMES:
            value = (HERE / name).read_bytes()
            lines.append(f"{hashlib.sha256(value).hexdigest()}  {name}\n")
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(info, value)
        info = zipfile.ZipInfo("P10DD_RUNTIME_SOURCE_SHA256SUMS.txt",
                               (2026, 11, 21, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(info, "".join(lines).encode("ascii"))
    with zipfile.ZipFile(TARGET) as check:
        assert check.testzip() is None
        assert len(check.namelist()) == len(NAMES) + 1
    print("P10DD_RUNTIME_GATE_BUNDLE_OK")
    print("files:", len(NAMES) + 1)
    print("bytes:", TARGET.stat().st_size)
    print("sha256:", hashlib.sha256(TARGET.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
