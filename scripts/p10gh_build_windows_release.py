#!/usr/bin/env python3
"""Reproducible P10GH surface-only Windows release, no native Gmsh here."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research/proposals/P10GH_WINDOWS_GEO_BYTE_STABLE_20261123"
PACKAGE = ROOT / "research/packages/P10GH_R1_CAD_POLE_TWO_2D_ONLY_WINDOWS_20261123.zip"
PIN = SRC / "P10GH_SOURCE_SHA256.json"
REV = "P10GH_R1_TWO_OCC_PARAMETERIZATIONS_2D_ONLY_NO_FEM"
FILES = (
    "P10GH_surface_compare.py", "01_P10GH_PREFLIGHT_ONLY.cmd",
    "02_P10GH_ONE_2D_PAIR_ONLY.cmd", "README_P10GH_RU.md",
    "M0.geo", "sphere_pore_B6_refined.geo",
)
EXPECTED_GEO = "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
EXPECTED_CAD = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cmd(folder: Path, flag: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(folder / "P10GH_surface_compare.py"), flag],
                          cwd=folder, text=True, capture_output=True, timeout=60)


def main() -> None:
    assert sha((SRC / "M0.geo").read_bytes()) == EXPECTED_GEO
    assert sha((SRC / "sphere_pore_B6_refined.geo").read_bytes()) == EXPECTED_CAD
    pins = {name: sha((SRC / name).read_bytes()) for name in sorted(FILES)}
    manifest = {
        "revision": REV, "date": "2026-11-23", "model": "Stage3D07",
        "parent_M0_msh_sha256":
            "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6",
        "canonical_M0_geo_sha256": EXPECTED_GEO,
        "canonical_OCC_CAD_sha256": EXPECTED_CAD,
        "uniform_volume_target": .825,
        "size_scale": .825 ** (1/3),
        "surface_variants": ["original", "CAD_poles_rotated_90_about_X"],
        "native_2d_attempts": 2, "native_3d_attempts": 0,
        "FEM_attempts": 0, "files": pins,
    }
    PIN.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    local_test = cmd(SRC, "--selftest")
    assert local_test.returncode == 0 and "P10GH_SOURCE_SELFTEST_PASS_NO_MESH" in local_test.stdout, (
        local_test.stdout, local_test.stderr)
    import importlib.util
    import unittest
    suite_path = ROOT / "scripts/test_p10gh_surface_compare.py"
    spec = importlib.util.spec_from_file_location("p10gh_tests", suite_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    test_result = unittest.TextTestRunner(verbosity=1).run(suite)
    assert test_result.wasSuccessful(), "offline synthetic QA tests failed"
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    names = sorted((*FILES, PIN.name))
    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as out:
        for name in names:
            info = zipfile.ZipInfo(name, (2026, 11, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            out.writestr(info, (SRC / name).read_bytes(),
                         compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == names
        assert all(archive.read(n) == (SRC / n).read_bytes() for n in names)
        with tempfile.TemporaryDirectory(prefix="P10GH_RELEASE_TEST_") as tmp:
            dest = Path(tmp)
            archive.extractall(dest)
            a = cmd(dest, "--selftest")
            assert a.returncode == 0 and "P10GH_SOURCE_SELFTEST_PASS_NO_MESH" in a.stdout, (a.stdout,a.stderr)
            b = cmd(dest, "--preflight")
            assert b.returncode == 2 and "Windows 11 required" in b.stderr, (b.stdout,b.stderr)
            c = cmd(dest, "--one-2d-pair")
            assert c.returncode == 2 and "Windows 11 required" in c.stderr, (c.stdout,c.stderr)
            changed = dest / "README_P10GH_RU.md"
            changed.write_bytes(changed.read_bytes() + b"\nINJECTED_TAMPER\n")
            d = cmd(dest, "--selftest")
            assert d.returncode == 2 and "source missing/tampered" in d.stderr, (d.stdout,d.stderr)
    print("P10GH_RELEASE_ZIP_CRC_EXTRACT_SELFTEST_LINUX_STOP_TAMPER_STOP_PASS")
    print("ZIP_PATH=" + str(PACKAGE))
    print("ZIP_SHA256=" + sha(PACKAGE.read_bytes()))
    print("ZIP_BYTES=" + str(PACKAGE.stat().st_size))
    print("ZIP_FILES=" + str(len(names)))
    print("NATIVE_GMSH_2D=0 NATIVE_GMSH_3D=0 FEM=0")


if __name__ == "__main__":
    main()
