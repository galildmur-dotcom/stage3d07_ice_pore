#!/usr/bin/env python3
"""Deterministic, source-only P10GO Windows release; never invokes Gmsh."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research/proposals/P10GO_SINGLE_MATHEVAL_1D_WINDOWS_20261123"
OUT = ROOT / "research/packages/P10GO_R1_SELF_CONTAINED_C1_1D_WINDOWS_20261123.zip"
FILES = (
    "P10GO_1d_probe.py", "P10FN_common.py",
    "P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip",
    "01_P10GO_PREFLIGHT_NO_MESH.cmd",
    "02_P10GO_ONE_1D_SINGLE_FIELD_TEST.cmd", "README_P10GO_RU.md",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    pins = {
        "revision": "P10GO_R1_SINGLE_C1_MATHEVAL_SOURCE_AND_BOUNDED_1D_NO_3D_FEM",
        "files": {name: digest((SRC / name).read_bytes()) for name in FILES},
        "native_1d_cases_max": 2,
        "wall_s_per_case": 30,
        "native_2d_allowed": False,
        "native_3d_allowed": False,
        "FEM_allowed": False,
    }
    manifest = SRC / "P10GO_SOURCE_SHA256.json"
    data = json.dumps(pins, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != data:
        manifest.write_text(data, encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in (*FILES, manifest.name):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (SRC / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None and len(z.namelist()) == len(FILES) + 1
    print(f"P10GO_PACKAGE_OK bytes={OUT.stat().st_size} sha256={digest(OUT.read_bytes())}")


if __name__ == "__main__":
    main()
