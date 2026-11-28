#!/usr/bin/env python3
"""Build immutable P10GD Windows diagnostic release, no native Gmsh -3."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/proposals/P10GB_M1W_DAMPED_18_ZONE_SURFACE_PREFLIGHT_WINDOWS_20261122"
DEST = ROOT / "research/proposals/P10GD_2D_SURFACE_FIELD_SWEEP_WINDOWS_20261122"
ZIP = ROOT / "research/packages/P10GD_R1_SURFACE_FIELD_SWEEP_1D_2D_ONLY_WINDOWS_20261122.zip"
REV = "P10GD_R1_SURFACE_FIELD_SWEEP_ONLY_NO_3D_NO_FEM"
IMPORTS = ("P10FX_uniform_math.py", "P10GB_adapt_math.py", "M0.geo",
           "sphere_pore_B6_refined.geo",
           "P10FX_REAL_M0_M1_SIGNED_18_ZONE_729QP.json",
           "P10GA_M0_M1V_SIGNED18_343_729QP.json")
FIXED = ("P10GD_surface_sweep.py", "01_P10GD_2D_ONLY_NO_3D_NO_FEM.cmd",
         "README_P10GD_RU.md")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for name in IMPORTS:
        shutil.copy2(SOURCE / name, DEST / name)
    digests = {name: sha(DEST / name) for name in sorted((*IMPORTS, *FIXED))}
    pin = {"revision": REV, "theta_values": [0, .125, .25, .375, .5,
           .625, .75, .875, 1], "native_3d_max_attempts": 0,
           "FEM_max_attempts": 0,
           "M0_sha256": "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6",
           "M1V_sha256": "c3f69d3d6f3d88333f2aec7a5aa13db535f9eed4e76ba6c29bed4b88fa31ea06",
           "M1W_sha256": "fe77956c50534bfd0b6f84954b07f195e6449648bd71d5a6640d048aea9a5df2",
           "files": digests}
    (DEST / "P10GD_SOURCE_SHA256.json").write_text(
        json.dumps(pin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    probe = subprocess.run([sys.executable, str(DEST / "P10GD_surface_sweep.py"),
                            "--selftest"], cwd=DEST, check=False,
                           capture_output=True, text=True, timeout=120)
    if probe.returncode != 0:
        raise RuntimeError(probe.stdout + probe.stderr)
    if "P10GD_SOURCE_ONLY_PASS" not in probe.stdout:
        raise RuntimeError("selftest status missing")
    ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for filename in sorted((*IMPORTS, *FIXED, "P10GD_SOURCE_SHA256.json")):
            entry = zipfile.ZipInfo(filename, date_time=(2026, 11, 22, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, (DEST / filename).read_bytes(),
                             compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(ZIP) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("release ZIP integrity failure")
    print(json.dumps({"release": str(ZIP), "sha256": sha(ZIP),
                      "size_bytes": ZIP.stat().st_size,
                      "files": sorted((*IMPORTS, *FIXED, "P10GD_SOURCE_SHA256.json")),
                      "selftest": "PASS", "native_3d_attempts": 0,
                      "FEM_attempts": 0}, indent=2))


if __name__ == "__main__":
    main()
