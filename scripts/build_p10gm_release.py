#!/usr/bin/env python3
"""Rebuild deterministic P10GM R1 zip and source-pin manifest; no native Gmsh."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research/proposals/P10GM_1D_FIELD_DIAG_WINDOWS_20261123"
OUT = ROOT / "research/packages/P10GM_R1_THREE_BOUNDED_1D_FIELD_PROBES_WINDOWS_20261123.zip"
FILES = (
    "P10GM_1d_probe.py", "P10FN_common.py",
    "P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip",
    "01_P10GM_PREFLIGHT_NO_MESH.cmd",
    "02_P10GM_ONE_1D_DIAGNOSTIC_ONLY.cmd",
    "README_P10GM_RU.md",
)


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    pins = {"revision":"P10GM_R1_NATIVE_1D_AB_C_ONLY_NO_3D_NO_FEM",
            "files":{name:digest((SRC/name).read_bytes()) for name in FILES},
            "native_1d_cases_max":3,"wall_s_per_case":30,
            "native_2d_allowed":False,"native_3d_allowed":False,
            "FEM_allowed":False}
    manifest = SRC / "P10GM_SOURCE_SHA256.json"
    content = json.dumps(pins, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != content:
        manifest.write_text(content, encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in FILES + (manifest.name,):
            info = zipfile.ZipInfo(name, date_time=(2026,11,23,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (SRC/name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None and len(z.namelist()) == len(FILES)+1
    print(f"P10GM_PACKAGE_OK bytes={OUT.stat().st_size} sha256={digest(OUT.read_bytes())}")
    print(f"P10GM_SOURCE_MANIFEST_SHA256={digest(manifest.read_bytes())}")


if __name__ == "__main__":
    main()
