"""P10GK source-only C1/Gmsh MathEval guard regressions; NO native meshing."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

SOURCE = (Path(__file__).resolve().parents[1]
          / "research/proposals/P10GK_SOUTH_POLE_C1_SOURCE_ONLY_20261123")
sys.path.insert(0,str(SOURCE))
import P10GK_source_qa as q


class P10GKSourceOnlyTests(unittest.TestCase):
    def test_01_exact_cad_field_and_d027_source(self):
        policy=q.source_gate()
        self.assertEqual(policy["revision"],q.REV)
        self.assertFalse(policy["native_mesh_3d_authorized"])
        self.assertEqual(q.get_field_expressions()[6],q.FINAL)

    def test_02_full_independent_12221_field_samples_and_seams(self):
        stats=q.test_field()
        self.assertEqual(stats["sampled_points"],12221)
        self.assertEqual(stats["factor_min"],.94)
        self.assertEqual(stats["factor_max"],1.)
        self.assertLess(stats["max_analytic_MathEval_ratio_error"],5e-13)

    def test_03_signed_south_only_not_cad_parameter_pole(self):
        f=q.get_field_expressions()
        def ratio(d,mu):
            v=q.evaluate_raw(*q.sample(d,mu),f)
            return v["F6"]/v["F3"]
        for mu in (-1.,-.9,-.8):
            self.assertAlmostEqual(ratio(0.,mu),.94,places=12)
        for mu in (-.6,0.,.8,1.):
            self.assertAlmostEqual(ratio(0.,mu),1.,places=12)
        self.assertAlmostEqual(ratio(.001,-1.),1.,places=12)

    def test_04_sha_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            temp=Path(root)
            for name in set(q.SOURCE_FILES)|{q.MANIFEST}:
                (temp/name).write_bytes((SOURCE/name).read_bytes())
            with mock.patch.object(q,"HERE",temp):
                q.source_gate()
                src=temp/q.GEO
                src.write_bytes(src.read_bytes()+b"\n// INVALID EXTRA\n")
                with self.assertRaisesRegex(ValueError,"modified release source"):
                    q.source_gate()

    def test_05_native_preflight_not_allowed_on_linux(self):
        if sys.platform=="win32":self.skipTest("Windows CI should mock sys.platform")
        with self.assertRaisesRegex(ValueError,"requires user Windows"):
            q.require_windows()

    def test_06_mock_native_parse_only_no_mesh_no_fem(self):
        class MockResult:
            returncode=0
            stdout=b"Info : Gmsh 4.15.2\nInfo : Done reading .geo\n"
        with tempfile.TemporaryDirectory() as root:
            runs=Path(root)/"LOCAL_RUNS";runs.mkdir()
            with mock.patch.object(q,"RUNS",runs),\
                 mock.patch.object(q,"require_windows",return_value={"gmsh_version":"4.15.2"}),\
                 mock.patch.object(q.subprocess,"run",return_value=MockResult()) as invoke:
                with contextlib.redirect_stdout(io.StringIO()):
                    code=q.preflight()
            self.assertEqual(code,0)
            self.assertEqual(invoke.call_count,1)
            cmd=invoke.call_args.args[0]
            self.assertIn("-parse_and_exit",cmd)
            self.assertFalse(any(f in cmd for f in ("-1","-2","-3")))
            folder=next(runs.glob("P10GK_SOURCE_PREFLIGHT_*"))
            self.assertFalse(list(folder.glob("*.msh")))
            with zipfile.ZipFile(folder/"P10GK_SOURCE_PREFLIGHT_EVIDENCE.zip") as z:
                self.assertIsNone(z.testzip())
                report=json.loads(z.read("P10GK_SOURCE_REPORT.json"))
                self.assertEqual(report["native_1d_2d_3d_attempts"],0)
                self.assertEqual(report["FEM_attempts"],0)

    def test_07_d027_unchanged_and_no_physical_solver(self):
        old=q.read_json(SOURCE/"P10GJ_D027_GATE_POLICY.json")
        pol=q.read_json(SOURCE/q.POLICY)
        self.assertEqual(old["required_sampled_detJ_positive_QP"],[27,343,729])
        self.assertEqual(old["macro_QP_effective_Veff_assessment"]
                         ["all_18_signed_zone_ratios"],"diagnostic_only_not_18_of_18_hard")
        self.assertFalse(pol["FEM_authorized"])
        self.assertFalse(pol["native_mesh_3d_authorized"])


if __name__=="__main__":unittest.main()
