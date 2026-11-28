#!/usr/bin/env python3
"""Mock/source-only regression tests: absolutely no real native Gmsh."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main, mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research/proposals/P10GO_SINGLE_MATHEVAL_1D_WINDOWS_20261123"
spec = importlib.util.spec_from_file_location("p10go_under_test", SRC / "P10GO_1d_probe.py")
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(SRC))
spec.loader.exec_module(mod)


class P10GOTest(TestCase):
    def test_pinned_source_and_complete_expression(self):
        source = mod.source_gate()
        result = mod.math_gate()
        self.assertEqual(result["points"], 10201)
        self.assertEqual(result["baseline_expression_length"], 732)
        self.assertEqual(result["single_expression_length"], 1198)
        self.assertTrue(result["no_field_references"])
        self.assertLess(result["max_original_F3_error_m"], 5e-13)
        self.assertEqual(result["C1_seam_tests"], 4)
        self.assertEqual(len(source), 3)

    def test_driver_a_b_and_no_3d(self):
        a, b = (mod.driver(case) for case in mod.CASES)
        self.assertIn("Background Field = 3;", a)
        self.assertNotIn("Field[7]", a)
        self.assertIn("Field[7].F = StrCat(", b)
        self.assertIn("Background Field = 7;", b)
        self.assertEqual(b.count('"'), 8)  # Include filename plus three chunks
        self.assertNotIn('"F3', b)
        self.assertNotIn('"F4', b)
        self.assertNotIn('"F5', b)
        for geo in (a, b):
            self.assertIn('Mesh.MeshSizeFactor = '+mod.FACTOR, geo)
            self.assertNotIn('Mesh 3;', geo)

    def test_tampered_archive_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / 'changed.zip'
            fake.write_bytes(mod.SOURCE.read_bytes() + b'changed')
            with mock.patch.object(mod, 'SOURCE', fake):
                with self.assertRaises(RuntimeError):
                    mod.source_gate()

    def test_native_one_mock_bounded_and_no_mesh_in_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / mod.CASES[1]
            folder.mkdir()
            (folder / 'P10GO_1D.geo').write_text(mod.driver(mod.CASES[1]))
            calls = []
            def fake_native(cmd, **kw):
                calls.append((cmd, kw))
                kw['log'].write_text('Info    : Meshing 1D...\n')
                return {'native_exit_code': 1, 'stop_reason': 'WALL_LIMIT', 'wall_s': 30.01}
            with mock.patch.object(mod, 'capped_process', side_effect=fake_native):
                with mock.patch.object(mod.time, 'sleep', return_value=None):
                    result = mod.native_one(mod.CASES[1], folder)
            self.assertFalse(result['completed_1d'])
            cmd, kw = calls[0]
            self.assertEqual(cmd.count('-1'), 1)
            self.assertNotIn('-2', cmd)
            self.assertNotIn('-3', cmd)
            self.assertEqual(kw['wall_s'], 30)
            self.assertEqual(kw['memory_gib'], 8)
            self.assertEqual(kw['output_gib'], 2)
            self.assertEqual(cmd[cmd.index('-nt')+1], '2')
            (folder / 'P10GO_1D.msh').write_bytes(b'never upload mesh')
            zip_path = mod.evidence(Path(temp))
            with zipfile.ZipFile(zip_path) as z:
                self.assertEqual(z.testzip(), None)
                self.assertFalse(any(name.endswith('.msh') for name in z.namelist()))

    def test_preflight_consumed_marker_and_age(self):
        with tempfile.TemporaryDirectory() as temp:
            preflight = Path(temp) / 'preflight.json'
            local = Path(temp) / 'local_marker.json'
            profile = Path(temp) / 'profile_marker.json'
            proof = {'revision':mod.REV, 'P10GK_source_sha256':mod.SOURCE_PIN,
                     'P10GO_source_manifest_sha256':mod.sha(mod.SOURCE_SHA),
                     'native_1d_attempts':0, 'native_3d_attempts':0, 'FEM_attempts':0,
                     'created_utc':mod.datetime.now(mod.timezone.utc).isoformat()}
            preflight.write_text(json.dumps(proof))
            with mock.patch.object(mod,'PREFLIGHT',preflight):
                mod.check_preflight()
                with mock.patch.object(mod,'local_marker',return_value=local), mock.patch.object(mod,'profile_marker',return_value=profile):
                    local.write_text('{}')
                    self.assertTrue(local.exists())
                    self.assertTrue(local != profile)
                    proof['created_utc'] = '2020-01-01T00:00:00+00:00'
                    preflight.write_text(json.dumps(proof))
                    with self.assertRaises(RuntimeError):
                        mod.check_preflight()


if __name__ == '__main__':
    main()
