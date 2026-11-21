#!/usr/bin/env python3
"""Isolated P10DT release tests; fake 1D Gmsh only, NO native Windows mesh."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "research/packages/P10DT_R1_THREE_1D_CONTRAST_WINDOWS_20261121.zip"


def fake_gmsh(executable: Path, mode: str) -> None:
    source = ("#!/usr/bin/env python3\nimport pathlib,sys,time\n"
              "args=sys.argv[1:]\n"
              "assert '-1' in args and '-2' not in args and '-3' not in args\n"
              "print('Info : Meshing 1D...',flush=True)\n")
    if mode == "PASS":
        source += ("print('Info : 244 nodes 135 elements',flush=True)\n"
                   "pathlib.Path(args[args.index('-o')+1]).write_text('FAKE 1D')\n")
    elif mode == "TIMEOUT":
        source += "time.sleep(2)\n"
    else:
        source += "sys.exit(9)\n"
    executable.write_text(source, encoding="utf-8")
    executable.chmod(0o755)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p10dt_isolated_") as temp:
        root = Path(temp)
        with zipfile.ZipFile(RELEASE) as z:
            assert len(z.namelist()) == 9 and z.testzip() is None
            z.extractall(root)
        sys.path.insert(0, str(root))
        spec = importlib.util.spec_from_file_location("p10dt_isolated", root/"P10DT_one_click_1d.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert len(mod.source_gate()["files"]) == 8
        assert mod.selftest() == 0
        sources = mod.contrast_geo()
        assert list(sources) == list(mod.NAMES)
        assert sources[mod.NAMES[0]].count('F2*(1-0.02*0.5)') == 1
        assert sources[mod.NAMES[1]].count('Field[3].F = "0.5";') == 1
        assert sources[mod.NAMES[1]].count('F2*(1-0.02*F3)') == 1
        assert sources[mod.NAMES[2]].count('min(1,max(0,') == 1
        assert 'F3)' not in sources[mod.NAMES[2]]
        assert "Field[5] =" not in "\n".join(sources.values())

        native = mod.original_native
        native.child_private_bytes = lambda _: 0
        executable = root/"fake_gmsh"
        run = root/"one_shot_test"
        generated = mod.generated_geo(run)
        fake_gmsh(executable, "PASS")
        a = native.native_1d(str(executable), generated[mod.NAMES[0]], run)
        assert a["status"] == "PASS" and a["reported_nodes_elements"] == (244, 135)
        fake_gmsh(executable, "ERROR")
        b = native.native_1d(str(executable), generated[mod.NAMES[1]], run)
        assert b["status"] == "NONZERO_OR_INVALID_1D_LOG" and b["native_exit"] == 9
        fake_gmsh(executable, "TIMEOUT")
        native.WALL_S = .4
        c = native.native_1d(str(executable), generated[mod.NAMES[2]], run)
        assert c["status"] == "TIMEOUT_15S" and c["wall_s"] < 2
        native.WALL_S = 15

        mod.RUNS = root/"sequence"
        mod.LOCAL_MARKER = mod.RUNS/"P10DT_ONE_THREE_VARIANT_SEQUENCE_USED.json"
        global_marker = root/"GLOBAL_P10DT_ONLY.json"
        mod.profile_marker = lambda: global_marker
        called = []

        def synthetic_native(gmsh: str, geo: Path, folder: Path) -> dict:
            assert global_marker.exists() and mod.LOCAL_MARKER.exists()
            called.append(geo.stem)
            return {"name": geo.stem, "status": "TIMEOUT_15S" if len(called) == 2 else "PASS",
                    "wall_s": .1}

        def synthetic_preflight(folder: Path):
            files = mod.generated_geo(folder)
            return {"native_gmsh": "SYNTHETIC_ONLY", "native_parse_exits": dict.fromkeys(files, 0)}, files

        with patch.object(mod, "preflight", synthetic_preflight), \
             patch.object(native, "native_1d", synthetic_native), \
             patch("builtins.input", lambda _: mod.CONFIRM):
            code = mod.do_run(False)
        assert code == 2 and called == list(mod.NAMES)
        assert global_marker.exists() and mod.LOCAL_MARKER.exists()
        assert json.loads(global_marker.read_text())["protocol"] == mod.REV
        evidence = list(mod.RUNS.glob("P10DT_1D_*/P10DT_EVIDENCE.zip"))
        assert len(evidence) == 1
        with zipfile.ZipFile(evidence[0]) as z:
            assert z.testzip() is None
            manifest = json.loads(z.read("P10DT_RUN_MANIFEST.json"))
            assert manifest["physical_FEM_runs"] == 0 and len(manifest["variants"]) == 3
            assert b"FEM_RUNS=0" in z.read("P10DT_RESULT.txt")
        # The preflight-only route must never consume a marker.
        with patch.object(mod, "preflight", synthetic_preflight):
            assert mod.do_run(True) == 0
        # Exact manual phrase is mandatory and must not consume a marker.
        second_marker = root/"SHOULD_NOT_EXIST.json"
        mod.profile_marker = lambda: second_marker
        mod.LOCAL_MARKER = root/"SHOULD_NOT_EXIST_LOCAL.json"
        with patch.object(mod, "preflight", synthetic_preflight), \
             patch("builtins.input", lambda _: "WRONG PHRASE"):
            assert mod.do_run(False) == 2
        assert not second_marker.exists() and not mod.LOCAL_MARKER.exists()
        proc = subprocess.run([sys.executable, str(root/"P10DT_one_click_1d.py"),
                               "--preflight-only"], capture_output=True,
                              text=True, timeout=10, check=False)
        assert proc.returncode == 2 and "Windows ONLY" in proc.stdout
        base = root/"P10DN_M2_FIELD20.geo"
        base.write_bytes(base.read_bytes()+b"\n// TAMPER\n")
        try:
            mod.source_gate()
        except RuntimeError as e:
            assert "source SHA mismatch" in str(e)
        else:
            raise AssertionError("tampered original geometry was not blocked")
    print("P10DT_SYNTHETIC_ISOLATED_UNIT_OK 3_variants=yes",
          "fake_pass/nonzero/timeout=yes continue_after_timeout=yes",
          "manual_phrase=yes new_markers_only=yes Linux_STOP=yes tamper_STOP=yes",
          "native_Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
