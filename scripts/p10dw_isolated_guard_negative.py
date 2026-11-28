#!/usr/bin/env python3
"""P10DW no-Gmsh isolated negative and FAKE 1D process gate tests."""
from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT/"research/packages/P10DW_R1_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261121.zip"


def check_stop(fn, clue: str) -> None:
    try:
        fn()
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        assert clue.lower() in str(exc).lower(), (clue, str(exc))
    else:
        raise AssertionError("unsafe unexpected pass: " + clue)


def import_tool(folder: Path):
    sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location(
            "p10dw_test_module", folder/"P10DW_one_click_1d.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(folder))


def fake_gmsh_process(folder: Path) -> Path:
    # Test process masquerades as gmsh CLI, writes only dummy 1D mesh/log.
    script = folder/"fake_gmsh_test.py"
    script.write_text(
        "import sys,time,pathlib\n"
        "if 'slow' in sys.argv[0]: time.sleep(10)\n"
        "if '-o' in sys.argv:\n"
        " p=pathlib.Path(sys.argv[sys.argv.index('-o')+1]);p.write_bytes(b'fake-1d-msh')\n"
        "print('Info    : 10 nodes 9 elements',flush=True)\n", encoding="utf-8")
    return script


def main() -> int:
    assert PKG.is_file() and PKG.stat().st_size < 150_000
    tests = 0
    with tempfile.TemporaryDirectory(prefix="p10dw_negative_") as scratch:
        folder = Path(scratch)/"released"
        folder.mkdir()
        with zipfile.ZipFile(PKG) as z:
            assert z.testzip() is None and len(z.namelist()) == 13
            z.extractall(folder)
        tool = import_tool(folder)
        tool.source_gate()
        assert tool.geometry_contract()[1] == (
            folder/"P10DV_M2_INLINE_FIELD20.geo").read_text(encoding="utf-8")
        tests += 1

        # A modified exact F6 must be rejected despite parse being potentially valid.
        geo = folder/"P10DV_M2_INLINE_FIELD20.geo"
        src = geo.read_bytes()
        geo.write_bytes(src.replace(b"0.2*", b"0.3*", 1))
        check_stop(tool.source_gate, "pinned source changed")
        geo.write_bytes(src)
        tests += 1

        # A changed original CAD must independently STOP source validation.
        cad = folder/"sphere_pore_B6_refined.geo"
        src_cad = cad.read_bytes()
        cad.write_bytes(src_cad+b"\n// corrupted\n")
        check_stop(tool.source_gate, "pinned source changed")
        cad.write_bytes(src_cad)
        tests += 1

        # A falsified M1 identity in protocol cannot replace accepted P10DG M1.
        pin = folder/"P10DW_SOURCE_SHA256.json"
        before = pin.read_bytes()
        data = json.loads(before)
        data["accepted_original_m1_sha256"] = "0"*64
        pin.write_text(json.dumps(data), encoding="utf-8")
        check_stop(tool.source_gate, "protocol/source inventory")
        pin.write_bytes(before)
        tests += 1

        # A real file with the right basename but wrong bytes cannot replace M1.
        pretend_m1 = folder/"P10DG_M1_CANDIDATE.msh"
        pretend_m1.write_bytes(b"not-original-P10DG-M1")
        with patch("builtins.input", return_value=str(pretend_m1)):
            check_stop(lambda: tool.original_m1_path(True), "original accepted P10DG M1")
        tests += 1

        # Linux launch is a controlled STOP, never invokes actual native Gmsh.
        proc = subprocess.run([sys.executable, str(folder/"P10DW_one_click_1d.py"),
                               "--preflight-only"], capture_output=True,
                              text=True, stdin=subprocess.DEVNULL, timeout=30)
        assert proc.returncode == 2 and "Linux STOP" in proc.stdout
        assert not (folder/"P10DW_RUNS/P10DW_ONE_1D_USED.json").exists()
        tests += 1

        # CLI cannot silently start diagnostic without explicit --one-1d.
        proc = subprocess.run([sys.executable, str(folder/"P10DW_one_click_1d.py")],
                              capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=20)
        assert proc.returncode != 0
        tests += 1

        # Native 1D driver is exercised with synthetic controlled process;
        # no real gmsh executable, no 3D/FEM. Patch private monitor on Linux.
        fake = fake_gmsh_process(folder)
        saved_popen = tool.subprocess.Popen

        def popen_fake(argv, **kwargs):
            return saved_popen([sys.executable, str(fake), *argv[2:]], **kwargs)

        geo_file = folder/"P10DV_M2_INLINE_FIELD20.geo"
        with patch.object(tool, "child_private_bytes", return_value=0), \
             patch.object(tool.subprocess, "Popen", side_effect=popen_fake):
            path_ok = folder/"fake_ok"
            path_ok.mkdir()
            record = tool.native_one_1d(Path("fake_gmsh.exe"), geo_file, path_ok)
            assert record["status"] == "PASS_1D_ONLY" and record["exit_code"] == 0
            assert record["reported_nodes_elements_from_log"] == (10, 9)
        tests += 1

        # Fake hung process must terminate at wall bound; no retry authorization.
        slow = folder/"fake_slow"
        slow.mkdir()

        def popen_slow(argv, **kwargs):
            return saved_popen([sys.executable, "-c", "import time;time.sleep(30)"],
                               **kwargs)

        with patch.object(tool, "child_private_bytes", return_value=0), \
             patch.object(tool.subprocess, "Popen", side_effect=popen_slow), \
             patch.object(tool, "WALL_S", .4):
            record = tool.native_one_1d(Path("fake_gmsh.exe"), geo_file, slow)
            assert record["status"] == "TIMEOUT_15S" and record["wall_s"] < 3
        tests += 1

        # An absent/wrong phrase stops BEFORE marker consumption.
        out = folder/"cancel"
        out.mkdir()

        def fake_preflight(run, meta, *, prompt):
            assert prompt is False
            meta["gmsh_path"] = str(folder/"fake_gmsh.exe")
            return {"B_EXACT_INLINE_F6": geo_file}

        old_runs, old_marker = tool.RUNS, tool.LOCAL_MARKER
        try:
            tool.RUNS = out
            tool.LOCAL_MARKER = out/"P10DW_ONE_1D_USED.json"
            with patch.object(tool, "preflight", side_effect=fake_preflight), \
                 patch("builtins.input", return_value=""), redirect_stdout(io.StringIO()):
                assert tool.do_run(False) == 2
            assert not tool.LOCAL_MARKER.exists()
            tests += 1

            # Consent consumes new markers exactly once; no native diagnostic replay.
            profile = folder/"appdata"
            profile.mkdir()
            with patch.dict(os.environ, {"LOCALAPPDATA": str(profile)}), \
                 patch.object(tool, "preflight", side_effect=fake_preflight), \
                 patch("builtins.input", return_value=tool.CONFIRM), \
                 patch.object(tool, "native_one_1d", return_value={"status": "PASS_1D_ONLY"}), \
                 redirect_stdout(io.StringIO()):
                assert tool.do_run(False) == 0
                assert tool.LOCAL_MARKER.is_file() and tool.global_marker().is_file()
                assert tool.do_run(False) == 2
            tests += 1
        finally:
            tool.RUNS, tool.LOCAL_MARKER = old_runs, old_marker

    print("P10DW_ISOLATED_GUARD_NEGATIVE_PASS tests="+str(tests)+
          " native_Gmsh=0 FEM=0 one_shot_simulated=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
