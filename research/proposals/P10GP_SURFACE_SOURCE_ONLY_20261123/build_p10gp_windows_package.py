#!/usr/bin/env python3
"""Deterministic P10GP guarded surface release builder, offline only."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
HELPER = HERE.parent / "P10GH_WINDOWS_GEO_BYTE_STABLE_20261123" / "P10GH_surface_compare.py"
ARCHIVE = HERE / "P10GP_R2_GUARDED_WINDOWS_2D_ONLY.zip"
FILES = ["P10GP_R1_SURFACE_SOURCE_ONLY.zip", "P10GP_windows_2d.py",
         "01_P10GP_PREFLIGHT_NO_MESH.cmd", "02_P10GP_ONE_2D_PAIR_ONLY.cmd"]


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def main():
    helper_text = HELPER.read_text(encoding="utf-8")
    old = "            while proc.poll() is None:\n                time.sleep(.25)\n"
    new = ("            last_heartbeat = start\n"
           "            while proc.poll() is None:\n"
           "                time.sleep(.25)\n"
           "                if time.monotonic() - last_heartbeat >= 2:\n"
           "                    print('P10GP_HEARTBEAT native -2 elapsed_s=',\n"
           "                          round(time.monotonic() - start, 1), flush=True)\n"
           "                    last_heartbeat = time.monotonic()\n")
    assert helper_text.count(old) == 1
    helper = helper_text.replace(old, new).encode("utf-8")
    code = (HERE / "P10GP_windows_2d.py").read_text(encoding="utf-8")
    assert 'RUNTIME_SHA = ""  # replaced' in code
    code = code.replace('RUNTIME_SHA = ""  # replaced',
                        'RUNTIME_SHA = "' + sha(helper) + '"  # replaced')
    bundle = {name: (HERE / name).read_bytes() for name in FILES if name != "P10GP_windows_2d.py"}
    bundle["P10GP_windows_2d.py"] = code.encode("utf-8")
    bundle["P10GH_surface_compare.py"] = helper
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in sorted(bundle):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, bundle[name], compresslevel=6)
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        assert all(sha(z.read(n)) == sha(data) for n, data in bundle.items())
        with tempfile.TemporaryDirectory(prefix="p10gp_offline_") as temp:
            z.extractall(temp)
            cmd = [sys.executable, str(Path(temp) / "P10GP_windows_2d.py"), "--selftest"]
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            assert run.returncode == 0, run.stdout + run.stderr
            assert "P10GP_SOURCE_AND_RUNTIME_PASS" in run.stdout
            blocked = subprocess.run([sys.executable, str(Path(temp) / "P10GP_windows_2d.py"),
                                      "--one-2d-pair"], capture_output=True, text=True, timeout=10)
            assert blocked.returncode == 2 and "Windows required" in blocked.stderr
            # An altered parent source ZIP must STOP before native work.
            parent = Path(temp) / "P10GP_R1_SURFACE_SOURCE_ONLY.zip"
            old_parent = parent.read_bytes()
            parent.write_bytes(old_parent + b"TAMPER")
            tamper = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            assert tamper.returncode == 2 and "parent source-only zip SHA changed" in tamper.stderr
    print("P10GP_WINDOWS_PACKAGE_SOURCE_TEST_PASS", len(bundle), "files", sha(ARCHIVE.read_bytes()))


if __name__ == "__main__":
    main()
