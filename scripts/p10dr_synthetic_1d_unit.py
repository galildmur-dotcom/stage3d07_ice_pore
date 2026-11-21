#!/usr/bin/env python3
"""Isolated real ZIP unit + negative launch tests. Uses FAKE Gmsh, no native mesh."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "research/packages/P10DR_R1_F3_F4_1D_ISOLATION_WINDOWS_20261121.zip"


def fake_gmsh(executable: Path, mode: str) -> None:
    source = ("#!/usr/bin/env python3\n"
              "import pathlib,sys,time\n"
              "args=sys.argv[1:]\n"
              "assert '-1' in args and '-2' not in args and '-3' not in args\n"
              "print('Info : Meshing 1D...',flush=True)\n")
    if mode == "PASS":
        source += ("print('Info : 244 nodes 135 elements',flush=True)\n"
                   "pathlib.Path(args[args.index('-o')+1]).write_text('FAKE 1D',encoding='utf-8')\n")
    elif mode == "TIMEOUT":
        source += "time.sleep(2)\n"
    else:
        source += "sys.exit(9)\n"
    executable.write_text(source, encoding="utf-8")
    executable.chmod(0o755)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p10dr_isolated_") as temp:
        root = Path(temp)
        with zipfile.ZipFile(ZIP) as z:
            assert z.testzip() is None
            z.extractall(root)
        sys.path.insert(0, str(root))
        spec = importlib.util.spec_from_file_location("p10dr_isolated", root/"P10DR_one_click_1d.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert len(mod.source_gate()["files"]) == 7
        assert len(mod.profile_unit()) == 6
        generated = mod.generated_sources(root/"variants")
        assert list(generated) == list(mod.VARIANTS)
        assert mod.geo_variants()["B_F3_RAW_REFERENCE"].count('F2*(1-0.02*(F3))') == 1
        assert mod.geo_variants()["C_F4_RAW_REFERENCE"].count('F2*(1-0.02*(F4))') == 1
        assert "Field[4] = MathEval;" not in mod.geo_variants()["B_F3_RAW_REFERENCE"]
        assert "Field[3] = MathEval;" not in mod.geo_variants()["C_F4_RAW_REFERENCE"]
        assert "Field[5] = MathEval;" not in "\n".join(mod.geo_variants().values())
        assert "F5" not in mod.geo_variants()["G_F3_F4_INLINE_SMOOTHSTEP"].split(
            "Field[6] = MathEval;", 1)[1]
        mod.child_private_bytes = lambda _: 0
        exe = root/"fake_gmsh"
        fake_gmsh(exe, "PASS")
        a = mod.native_1d(str(exe), generated["A_FIELD2_REFERENCE"], root/"variants")
        assert a["status"] == "PASS" and a["reported_nodes_elements"] == (244, 135)
        fake_gmsh(exe, "ERROR")
        b = mod.native_1d(str(exe), generated["B_F3_RAW_REFERENCE"], root/"variants")
        assert b["status"] == "NONZERO_OR_INVALID_1D_LOG" and b["native_exit"] == 9
        fake_gmsh(exe, "TIMEOUT")
        mod.WALL_S = .4
        c = mod.native_1d(str(exe), generated["C_F4_RAW_REFERENCE"], root/"variants")
        assert c["status"] == "TIMEOUT_15S" and c["wall_s"] < 2
        mod.WALL_S = 15
        # A Windows-like synthetic dispatch: failure in B must NOT suppress C..G.
        mod.RUNS = root/"one_shot_test"
        mod.LOCAL_MARKER = mod.RUNS/"P10DR_ONE_DIAGNOSTIC_SEQUENCE_USED.json"
        global_marker = root/"GLOBAL_MARKER.json"
        mod.user_marker = lambda: global_marker
        called = []

        def synthetic_native(gmsh, geo, run):
            assert global_marker.exists() and mod.LOCAL_MARKER.exists()
            called.append(geo.stem)
            return {"name": geo.stem,
                    "status": "TIMEOUT_15S" if geo.stem == "B_F3_RAW_REFERENCE" else "PASS",
                    "wall_s": .2}

        def synthetic_preflight(run):
            sources = mod.generated_sources(run)
            return {"gmsh_path": "FAKE_GMSH", "native_parse_exits": dict.fromkeys(sources, 0)}, sources

        with patch.object(mod, "preflight", synthetic_preflight), \
             patch.object(mod, "native_1d", synthetic_native), \
             patch("builtins.input", lambda _: mod.CONFIRM):
            code = mod.do_run(False)
        assert code == 2 and called == list(mod.VARIANTS)
        assert mod.LOCAL_MARKER.exists() and global_marker.exists()
        evidence = list(mod.RUNS.glob("P10DR_1D_*/P10DR_EVIDENCE.zip"))
        assert len(evidence) == 1
        with zipfile.ZipFile(evidence[0]) as z:
            assert z.testzip() is None and b"WITH_1D_STOPS" in z.read("P10DR_RESULT.txt")
            assert b"FEM_RUNS=0" in z.read("P10DR_RESULT.txt")
        # Actual entry-point on non-Windows stops before marker and native Gmsh.
        process = subprocess.run([sys.executable, str(root/"P10DR_one_click_1d.py"),
                                  "--preflight-only"], capture_output=True,
                                 text=True, check=False, timeout=10)
        assert process.returncode == 2 and "Windows ONLY" in process.stdout
        geo = root/"P10DN_M2_FIELD20.geo"
        geo.write_bytes(geo.read_bytes()+b"\n// DELIBERATE SOURCE TAMPER\n")
        try:
            mod.source_gate()
        except RuntimeError as e:
            assert "source SHA mismatch" in str(e)
        else:
            raise AssertionError("tampered GEO was not blocked")
    print("P10DR_SYNTHETIC_ISOLATED_UNIT_OK 7_variants=yes",
          "fake_pass/nonzero/timeout=yes", "continue_after_timeout=yes",
          "new_markers_only=yes Linux_stop=yes tamper_stop=yes Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
