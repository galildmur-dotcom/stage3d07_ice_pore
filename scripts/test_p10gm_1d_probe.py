#!/usr/bin/env python3
"""No native Gmsh: deterministic P10GM source/1D guarded protocol tests."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = (Path(__file__).resolve().parents[1] / "research/proposals"
        / "P10GM_1D_FIELD_DIAG_WINDOWS_20261123")
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location("p10gm_probe", BASE / "P10GM_1d_probe.py")
assert spec and spec.loader
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class P10GM1D(unittest.TestCase):
    def test_01_pinned_source_and_frozen_mathematics(self):
        src = p.source_gate()
        self.assertEqual(set(src), set(p.SOURCE_GEOS))
        val = p.math_gate()
        self.assertEqual(val["points"], 10201)
        self.assertLess(val["max_relative_expression_error"], 5e-13)
        self.assertAlmostEqual(val["local_factor_min"], .94)
        self.assertAlmostEqual(val["local_factor_max"], 1.)

    def test_02_three_distinct_1d_drivers(self):
        drivers = {case:p.driver(case) for case in p.CASES}
        self.assertEqual(len(drivers), 3)
        for name, driver in drivers.items():
            self.assertIn("Mesh.MeshSizeFactor = " + p.FACTOR, driver)
            self.assertNotIn("Mesh 3;", driver)
            self.assertNotIn("Mesh 2;", driver)
            self.assertIn("Mesh.ElementOrder = 2", driver)
        self.assertIn('Background Field = 3;', drivers[p.CASES[0]])
        self.assertIn('Background Field = 7;', drivers[p.CASES[2]])
        self.assertNotIn("F4*F4", drivers[p.CASES[2]])
        self.assertIn('Include "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo";',
                      drivers[p.CASES[1]])

    def test_03_tampered_zip_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            changed = Path(t) / "wrong.zip"
            changed.write_bytes(p.SOURCE.read_bytes() + b"changed")
            with patch.object(p, "SOURCE", changed):
                with self.assertRaisesRegex(RuntimeError, "archive changed"):
                    p.source_gate()

    def test_04_1d_only_native_command_and_stop_detection(self):
        with tempfile.TemporaryDirectory() as t:
            folder = p.make_case_folder(Path(t), p.CASES[0], p.source_gate())
            captured = []

            def fake_process(cmd, **kw):
                captured.append((cmd, kw))
                kw["log"].write_text("Info : Meshing 1D...\nInfo : Done meshing 1D\n",
                                      encoding="utf-8")
                (folder / "P10GM_1D.msh").write_bytes(b"$MeshFormat\n")
                return {"native_exit_code": 0, "stop_reason": "", "wall_s": .01}

            with patch.object(p, "capped_process", fake_process), \
                 patch.object(p.time, "sleep", lambda _:None):
                r = p.native_one(p.CASES[0], folder)
            self.assertTrue(r["completed_1d"])
            self.assertEqual(len(captured), 1)
            cmd, kw = captured[0]
            self.assertEqual(cmd.count("-1"), 1)
            self.assertNotIn("-2", cmd)
            self.assertNotIn("-3", cmd)
            self.assertEqual(kw["wall_s"], 30)
            self.assertEqual(kw["memory_gib"], 8)
            self.assertEqual(cmd[cmd.index("-nt")+1], "2")

    def test_05_window_timeout_is_diagnostic_not_go(self):
        with tempfile.TemporaryDirectory() as t:
            folder = p.make_case_folder(Path(t), p.CASES[1], p.source_gate())

            def timeout(_cmd, **kw):
                kw["log"].write_text("Info : Meshing 1D...\n", encoding="utf-8")
                return {"native_exit_code": -15, "stop_reason": "WALL_LIMIT",
                        "wall_s": 30.1}

            with patch.object(p, "capped_process", timeout), \
                 patch.object(p.time, "sleep", lambda _:None):
                r = p.native_one(p.CASES[1], folder)
            self.assertFalse(r["completed_1d"])
            self.assertIsNone(r["mesh_sha256"])
            self.assertEqual(r["native"]["stop_reason"], "WALL_LIMIT")

    def test_06_run_evidence_and_second_attempt_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            proof_path = root / "preflight.json"
            proof_path.write_text(json.dumps({
                "revision": p.REV, "P10GK_source_sha256": p.SOURCE_PIN,
                "P10GM_source_manifest_sha256":p.sha(p.SOURCE_SHA),
                "created_utc":datetime.now(timezone.utc).isoformat(),
                "native_1d_attempts":0,"native_3d_attempts":0,"FEM_attempts":0,
            }), encoding="utf-8")
            calls = []

            def fake_native(case, folder):
                calls.append(case)
                (folder / "P10GM_GMSH_1D.log").write_text(
                    "Info : Done meshing 1D\n", encoding="utf-8")
                return {"case":case,"completed_1d":case!=p.CASES[1],
                        "native":{"stop_reason":"WALL_LIMIT" if case==p.CASES[1]
                                  else "", "native_exit_code":0 if case!=p.CASES[1]
                                  else -15}}

            with patch.object(p, "RUNS", root), \
                 patch.object(p, "PREFLIGHT", proof_path), \
                 patch.object(p, "TOOL_RESULT", root / "result.txt"), \
                 patch.object(p, "profile_marker", lambda:root/"PROFILE"/"marker.json"), \
                 patch.object(p, "installed_gate", lambda:{"gmsh_version":"4.15.2"}), \
                 patch.object(p, "native_one", fake_native):
                self.assertEqual(p.run(), 0)
                self.assertEqual(calls, list(p.CASES))
                files = list(root.glob("P10GM_1D_FIELD_DIAG_*/P10GM_1D_PROBE_EVIDENCE.zip"))
                self.assertEqual(len(files), 1)
                with __import__("zipfile").ZipFile(files[0]) as z:
                    self.assertIsNone(z.testzip())
                    self.assertIn("P10GM_MANIFEST.json", z.namelist())
                    self.assertFalse(any(n.endswith(".msh") for n in z.namelist()))
                    data = json.loads(z.read("P10GM_MANIFEST.json"))
                    self.assertEqual(data["status"],
                                     "DIAG_FIELD_1D_TIMEOUT_OR_STOP_NO_3D")
                    self.assertEqual(data["native_3d_attempts"], 0)
                with self.assertRaisesRegex(RuntimeError, "already consumed"):
                    p.run()


if __name__ == "__main__":
    unittest.main(verbosity=2)
