#!/usr/bin/env python3
"""P10DV release ZIP source/math/tamper tests; never native Gmsh or FEM."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "research/packages/P10DV_R1_M2_EXACT_INLINE_KAPPA20_SOURCE_ONLY_WINDOWS_20261121.zip"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p10dv_isolated_negative_") as temp:
        folder = Path(temp)
        with zipfile.ZipFile(ZIP) as z:
            assert z.testzip() is None and len(z.namelist()) == 7
            z.extractall(folder)
        script = folder/"P10DV_inline_source_unit.py"
        spec = importlib.util.spec_from_file_location("p10dv_isolated", script)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert len(mod.source_gate()["files"]) == 6
        result = mod.math_selftest()
        assert result["points"] == 17075 and result["F2_samples_per_point"] == 3
        assert result["max_normalized_h_M1_to_M2_formula_abs_diff"] == 0.
        assert result["max_original_geo_kappa_vs_independent_P10DN_python_abs_diff"] < 3e-12
        assert result["target_volume_ratio_envelope"] == [.8, 1.]
        assert result["no_nested_MathEval"] is True
        # The only CLI mode is --selftest. Empty mode must fail before work.
        proc = subprocess.run([sys.executable, str(script)], capture_output=True,
                              text=True, timeout=10, check=False)
        assert proc.returncode == 2 and "only --selftest allowed" in proc.stderr
        # Negative 1: exact original P10DN candidate changes.
        original = folder/"P10DN_M2_FIELD20.geo"
        original.write_bytes(original.read_bytes()+b"\n// TAMPER ORIGINAL\n")
        try:
            mod.source_gate()
        except RuntimeError as exc:
            assert "source SHA mismatch" in str(exc)
        else:
            raise AssertionError("P10DN GEO tamper accepted")
        original.write_bytes(original.read_bytes().split(b"\n// TAMPER ORIGINAL\n")[0])
        # Negative 2: inlined F6 injects nested MathEval reference.
        candidate = folder/"P10DV_M2_INLINE_FIELD20.geo"
        saved = candidate.read_bytes()
        candidate.write_bytes(saved.replace(b"F2*exp(", b"F3*exp(", 1))
        try:
            mod.source_gate()
        except RuntimeError as exc:
            assert "source SHA mismatch" in str(exc)
        else:
            raise AssertionError("nested MathEval candidate tamper accepted")
        candidate.write_bytes(saved)
        # Negative 3: falsely substitute H0/U0 SHA for accepted original M1.
        pinfile = folder/"P10DV_SOURCE_SHA256.json"
        original_pin = pinfile.read_bytes()
        pin = json.loads(original_pin)
        pin["accepted_original_m1_sha256"] = "NOT_ORIGINAL_P10DG_M1"
        pinfile.write_text(json.dumps(pin), encoding="utf-8")
        try:
            mod.source_gate()
        except RuntimeError as exc:
            assert "protocol/source identity" in str(exc)
        else:
            raise AssertionError("wrong original M1 SHA pin accepted")
        pinfile.write_bytes(original_pin)
        # Negative 4: invalid host expression function may not pass AST/size unit.
        try:
            mod.compile_scalar("__import__('os').system('echo bad')", {"F2"})
        except RuntimeError as exc:
            assert "unexpected expression syntax" in str(exc) or "unexpected scalar function" in str(exc)
        else:
            raise AssertionError("unsafe MathEval expression accepted")
        # Negative 5: a fake alternate F3/F4 expansion has no place in source.
        original_func = mod.flattened_expression
        mod.flattened_expression = lambda: "F2*exp(log(1-0.2*F3)/3)"
        try:
            mod.candidate_geo_text()
        except RuntimeError as exc:
            assert "candidate Gmsh GEO source structure" in str(exc) or \
                   "inlined GEO is not" in str(exc) or "no nested" in str(exc)
        else:
            # If the structural check is intentionally relaxed in future,
            # determinism must still reject the mutated inline expression.
            assert mod.candidate_geo_text().encode() != saved
        finally:
            mod.flattened_expression = original_func
        assert mod.math_selftest()["native_gmsh_runs"] == 0
    print("P10DV_ISOLATED_SOURCE_UNIT_OK", "exact_M1=yes 17075_points=yes",
          "tampered_original_GEO_STOP=yes inlined_GEO_STOP=yes wrong_M1_STOP=yes",
          "unsafe_eval_STOP=yes Linux_no_cli_STOP=yes native_Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
