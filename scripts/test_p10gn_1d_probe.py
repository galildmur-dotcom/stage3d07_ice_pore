#!/usr/bin/env python3
"""P10GN isolated 1D-only source, resource, one-shot and mock tests; no Gmsh."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

BASE = (Path(__file__).resolve().parents[1] / "research/proposals"
        / "P10GN_REFERENCE_FIELD_DIAG_WINDOWS_20261123")
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location("p10gn_probe", BASE / "P10GN_1d_probe.py")
assert spec and spec.loader
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class P10GNReferenceOnly(unittest.TestCase):
    def test_01_pinned_parent_source_and_math(self):
        self.assertEqual(set(p.source_gate()), set(p.SOURCE_GEOS))
        s = p.math_gate()
        self.assertEqual(s["points"], 10201)
        self.assertLess(s["max_relative_expression_error"], 5e-13)

    def test_02_exact_field_isolation_drivers(self):
        d, e, f = [p.driver(case) for case in p.CASES]
        self.assertIn('Field[7].F = "F3";', d)
        self.assertIn('Field[7].F = "F3*0.94";', e)
        self.assertNotIn('Field[7].F = "F3*0.94";', d)
        self.assertNotIn('Field[7].F = "F3";', e)
        self.assertIn('Background Field = 7;', d)
        self.assertIn('Background Field = 7;', e)
        self.assertIn('Include "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo";', f)
        self.assertIn('Mesh.MeshSizeMin = 0.0002;', f)
        self.assertNotIn('Mesh.MeshSizeMin', d)
        self.assertNotIn('Mesh.MeshSizeMin', e)
        for geo in (d, e, f):
            self.assertIn('Mesh.MeshSizeFactor = '+p.FACTOR+';', geo)
            self.assertNotIn('Mesh 3;', geo)
            self.assertNotIn('Mesh 2;', geo)

    def test_03_source_tamper_stop(self):
        with tempfile.TemporaryDirectory() as t:
            altered = Path(t) / "bad.zip"
            altered.write_bytes(p.SOURCE.read_bytes() + b"corrupted")
            with patch.object(p, "SOURCE", altered):
                with self.assertRaisesRegex(RuntimeError, "archive changed"):
                    p.source_gate()

    def test_04_native_command_bounded_and_visible(self):
        with tempfile.TemporaryDirectory() as t:
            folder = p.make_case_folder(Path(t), p.CASES[0], p.source_gate())
            seen = []

            def fake_native(cmd, **kw):
                seen.append((cmd,kw))
                kw["log"].write_text("Info : Meshing 1D...\nInfo : Done meshing 1D\n",
                                     encoding="utf-8")
                (folder / "P10GN_1D.msh").write_bytes(b"$MeshFormat\n")
                return {"native_exit_code":0,"stop_reason":"","wall_s":.01}

            with patch.object(p, "capped_process", fake_native), \
                 patch.object(p.time, "sleep", lambda _:None):
                report = p.native_one(p.CASES[0],folder)
            self.assertTrue(report["completed_1d"])
            self.assertEqual(len(seen),1)
            cmd,kw = seen[0]
            self.assertEqual(cmd.count("-1"),1)
            self.assertNotIn("-2",cmd)
            self.assertNotIn("-3",cmd)
            self.assertEqual(kw["wall_s"],30)
            self.assertEqual(kw["memory_gib"],8)

    def _configured_run(self, tmp, outcomes):
        root=Path(tmp)
        proof=root/"proof.json"
        proof.write_text(json.dumps({"revision":p.REV,
                 "P10GK_source_sha256":p.SOURCE_PIN,
                 "P10GN_source_manifest_sha256":p.sha(p.SOURCE_SHA),
                 "created_utc":datetime.now(timezone.utc).isoformat(),
                 "native_1d_attempts":0,"native_3d_attempts":0,
                 "FEM_attempts":0}),encoding="utf-8")
        calls=[]

        def fake_one(case,folder):
            calls.append(case)
            (folder/"P10GN_GMSH_1D.log").write_text(
                "Info : Meshing 1D...\n",encoding="utf-8")
            return {"case":case,"completed_1d":outcomes[case],
                    "native":{"stop_reason":"" if outcomes[case] else "WALL_LIMIT",
                              "native_exit_code":0 if outcomes[case] else 1}}

        return (root,proof,calls,fake_one)

    def test_05_D_stop_E_still_runs_F_skipped_and_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            outcomes={p.CASES[0]:False,p.CASES[1]:True,p.CASES[2]:True}
            root,proof,calls,fake_one=self._configured_run(t,outcomes)
            with patch.object(p,"RUNS",root), \
                 patch.object(p,"PREFLIGHT",proof), \
                 patch.object(p,"TOOL_RESULT",root/"result.txt"), \
                 patch.object(p,"profile_marker",lambda:root/"PROFILE"/"marker.json"), \
                 patch.object(p,"installed_gate",lambda:{"gmsh_version":"4.15.2"}), \
                 patch.object(p,"native_one",fake_one):
                self.assertEqual(p.run(),0)
                self.assertEqual(calls,list(p.CASES[:2]))
                archives=list(root.glob("P10GN_1D_REFERENCE_DIAG_*/P10GN_1D_PROBE_EVIDENCE.zip"))
                self.assertEqual(len(archives),1)
                with zipfile.ZipFile(archives[0]) as z:
                    self.assertIsNone(z.testzip())
                    data=json.loads(z.read("P10GN_MANIFEST.json"))
                    self.assertEqual(data["status"],
                                     "DIAG_REFERENCE_STOP_FLOOR_NOT_ATTEMPTED_NO_3D")
                    self.assertEqual(len(data["cases"]),2)
                    self.assertEqual(data["native_3d_attempts"],0)
                    self.assertFalse(any(n.endswith(".msh") for n in z.namelist()))
                with self.assertRaisesRegex(RuntimeError,"already consumed"):
                    p.run()

    def test_06_all_pass_F_automatically_runs_and_no_FEM(self):
        with tempfile.TemporaryDirectory() as t:
            outcomes=dict.fromkeys(p.CASES,True)
            root,proof,calls,fake_one=self._configured_run(t,outcomes)
            with patch.object(p,"RUNS",root), \
                 patch.object(p,"PREFLIGHT",proof), \
                 patch.object(p,"TOOL_RESULT",root/"result.txt"), \
                 patch.object(p,"profile_marker",lambda:root/"PROFILE"/"marker.json"), \
                 patch.object(p,"installed_gate",lambda:{"gmsh_version":"4.15.2"}), \
                 patch.object(p,"native_one",fake_one):
                self.assertEqual(p.run(),0)
                self.assertEqual(calls,list(p.CASES))
                self.assertEqual(json.loads(next(root.glob(
                    "P10GN_1D_REFERENCE_DIAG_*/P10GN_MANIFEST.json")).read_text())
                    ["status"],"DIAG_D_E_F_1D_COMPLETED_NO_3D")


if __name__ == "__main__":
    unittest.main(verbosity=2)
