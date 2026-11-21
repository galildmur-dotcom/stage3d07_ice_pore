#!/usr/bin/env python3
"""Standalone P10DQ ZIP synthetic source, native-loop and one-shot safety tests (NO Gmsh)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "research/packages/P10DQ_R1_1D_FIELD_ISOLATION_WINDOWS_20261121.zip"


def fake_exe(path: Path, mode: str) -> None:
    code = ("#!/usr/bin/env python3\n"
            "import pathlib,sys,time\n"
            "args=sys.argv[1:]\n"
            "print('FAKE_ONLY GMSH -1', ' '.join(args), flush=True)\n"
            "assert '-1' in args and '-2' not in args and '-3' not in args\n")
    if mode == "PASS":
        code += "pathlib.Path(args[args.index('-o')+1]).write_text('synthetic-only mesh',encoding='utf-8')\n"
    elif mode == "TIMEOUT":
        code += "time.sleep(2)\n"
    else:
        code += "sys.exit(9)\n"
    path.write_text(code, encoding="utf-8")
    path.chmod(0o755)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p10dq_unit_") as td:
        folder = Path(td)
        with zipfile.ZipFile(ZIP) as z:
            assert z.testzip() is None
            z.extractall(folder)
        sys.path.insert(0, str(folder))
        spec = importlib.util.spec_from_file_location(
            "p10dq_isolated_unit", folder / "P10DQ_one_click_1d.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert len(mod.source_gate()["files"]) == 7
        assert len(mod.formula_unit()) == 6
        variants = mod.generated_sources(folder / "test")
        assert list(variants) == list(mod.VARIANT_NAMES)
        assert all(f.is_file() for f in variants.values())
        mod.child_private_bytes = lambda _: 0
        fake = folder / "fake_gmsh"
        fake_exe(fake, "PASS")
        ok = mod.native_1d(str(fake), variants["A_BASE_M1_FIELD2"], folder / "test")
        assert ok["status"] == "PASS" and ok["native_exit"] == 0
        fake_exe(fake, "ERROR")
        bad = mod.native_1d(str(fake), variants["B_F2_MATHEVAL_PROXY"], folder / "test")
        assert bad["status"] == "NONZERO_OR_NO_MESH" and bad["native_exit"] == 9
        fake_exe(fake, "TIMEOUT")
        mod.PER_TEST_WALL_S = .4
        timeout = mod.native_1d(str(fake), variants["C_F5_LINEAR_DIAGNOSTIC"],
                                folder / "test")
        assert timeout["status"] == "TIMEOUT_25S"
        # On Linux the public launcher must stop before any native operation/marker.
        proc = subprocess.run([sys.executable, str(folder / "P10DQ_one_click_1d.py"),
                               "--preflight-only"], capture_output=True, text=True,
                              check=False, timeout=10)
        assert proc.returncode == 2 and "Windows only" in proc.stdout
        assert not (folder / "P10DQ_RUNS/P10DQ_ONE_1D_ATTEMPT_USED.json").exists()
        assert not list(folder.rglob("P10DQ_1D_" + mod.M1_SHA + ".json"))
        assert (folder / "P10DQ_RUNS").is_dir()
        # Mutating source bytes must trigger the pinned-source guard.
        base = folder / "P10DN_M2_FIELD20.geo"
        base.write_text(base.read_text(encoding="utf-8") + "\n// TAMPER\n",
                        encoding="utf-8")
        try:
            mod.source_gate()
        except RuntimeError as exc:
            assert "pinned file changed" in str(exc)
        else:
            raise AssertionError("source SHA tamper was accepted")
    print("P10DQ_ISOLATED_SYNTHETIC_1D_UNIT_OK tests=6",
          "fake_pass=1 fake_nonzero=1 fake_timeout=1 linux_stop_before_marker=1",
          "SHA_tamper_STOP=1 native_Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
