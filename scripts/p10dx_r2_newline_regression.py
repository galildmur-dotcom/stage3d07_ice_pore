#!/usr/bin/env python3
"""No-native simulation of the precise R1 Windows newline bug and R2 fix."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT/"research/packages/P10DW_R1_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261121.zip"
R2 = ROOT/"research/packages/P10DW_R2_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261122.zip"
GEO_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def windows_write_text(path: Path, data: str, encoding: str | None = None,
                       errors: str | None = None, newline: str | None = None) -> int:
    """Emulate Path.write_text newline=None Windows CRLF on a Linux executor."""
    assert newline is None
    raw = data.encode(encoding or "utf-8", errors or "strict")
    path.write_bytes(raw.replace(b"\n", b"\r\n"))
    return len(data)


def imported(folder: Path, module_name: str):
    sys.modules.pop("P10DV_inline_source_unit", None)
    sys.modules.pop("P10DO_windows_guards", None)
    sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location(module_name,
                                                       folder/"P10DW_one_click_1d.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(folder))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p10dx_r2_regression_") as scratch:
        root = Path(scratch)
        mods = []
        for zip_path, foldername in ((R1, "r1"), (R2, "r2")):
            folder = root/foldername
            folder.mkdir()
            with zipfile.ZipFile(zip_path) as z:
                assert z.testzip() is None and len(z.namelist()) == 13
                z.extractall(folder)
                pin = json.loads(z.read("P10DW_SOURCE_SHA256.json"))
                assert len(pin["files"]) == 12
                assert all(digest(z.read(name)) == expected
                           for name, expected in pin["files"].items())
            mod = imported(folder, foldername+"_p10dw")
            mod.source_gate()
            assert mod.M1_SHA == M1_SHA and mod.CONFIRM == "RUN ONE P10DW INLINE F6 1D"
            assert mod.WALL_S == 15 and mod.PRIVATE_MAX == 2*1024**3
            assert mod.LOCAL_MARKER.name == "P10DW_ONE_1D_USED.json"
            mods.append((mod, folder))

        # R1 should fail on the exact original Windows newline translation.
        r1, folder1 = mods[0]
        win_run1 = folder1/"simulated_windows_run"
        win_run1.mkdir()
        with patch.object(Path, "write_text", windows_write_text):
            try:
                r1.generated_sources(win_run1)
            except RuntimeError as exc:
                assert str(exc) == "P10DW_STOP: generated inline candidate altered"
            else:
                raise AssertionError("R1 did not reproduce original Windows SHA STOP")
        bad = (win_run1/"GEO/B_EXACT_INLINE_F6.geo").read_bytes()
        assert digest(bad) != GEO_SHA and digest(bad.replace(b"\r\n", b"\n")) == GEO_SHA

        # R2 must PASS even with the exact same synthetic Windows behavior.
        r2, folder2 = mods[1]
        win_run2 = folder2/"simulated_windows_run"
        win_run2.mkdir()
        with patch.object(Path, "write_text", windows_write_text):
            sources = r2.generated_sources(win_run2)
        exact = sources["B_EXACT_INLINE_F6"].read_bytes()
        assert digest(exact) == GEO_SHA and b"\r\n" not in exact
        assert exact == (folder2/"P10DV_M2_INLINE_FIELD20.geo").read_bytes()
        assert digest((win_run2/"GEO/sphere_pore_B6_refined.geo").read_bytes()) == CAD_SHA
        baseline = sources["A_ORIGINAL_M1_FIELD2"].read_bytes()
        assert b"\r\n" not in baseline and baseline.endswith(b"Background Field=2;\n")

        # A modified R2 source must be caught by its own exact SHA gate.
        r2_source = folder2/"P10DW_one_click_1d.py"
        original = r2_source.read_bytes()
        r2_source.write_bytes(original.replace(b"write_bytes(", b"write_text(", 1))
        try:
            r2.source_gate()
        except RuntimeError as exc:
            assert "pinned source changed" in str(exc)
        else:
            raise AssertionError("R2 source tamper unexpectedly passed")
        r2_source.write_bytes(original)

        # No real native executables run; a Linux attempt still STOPs before Gmsh.
        proc = subprocess.run([sys.executable, str(r2_source), "--preflight-only"],
                              cwd=str(folder2), capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=25)
        assert proc.returncode == 2 and "Linux STOP" in proc.stdout
        assert not (folder2/"P10DW_RUNS/P10DW_ONE_1D_USED.json").exists()

        # Reuse the 11 prior independent guard checks against the R2 ZIP.
        negative = ROOT/"scripts/p10dw_isolated_guard_negative.py"
        spec = importlib.util.spec_from_file_location("p10dx_original_negatives", negative)
        assert spec and spec.loader
        test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test)
        test.PKG = R2
        assert test.main() == 0

    print("P10DX_R2_WINDOWS_EOL_REGRESSION_PASS R1_reproduced_STOP=YES "
          "R2_GEO_exact_SHA=YES R2_negative_11_11=PASS native_Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
