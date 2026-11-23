"""P10GL exact frozen-D027, Windows parse-only and one-shot MOCK tests; no Gmsh."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10GL_ONE_P10GK_HXT10_WINDOWS_20261123"
sys.path.insert(0,str(SRC))
spec=importlib.util.spec_from_file_location("p10gl_tested_one_hxt10",SRC/"P10GL_one_hxt10.py")
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)


def qa():
    return {"nonpositive_samples":0,"minimum_curved_detj":2e-11,
            "minimum_corner_detj":3e-11,
            "qp_integrated_volume_m3":.06*.06*.05-4*math.pi*.001**3/3,
            "tet10":9690,"max_element_qp_detj_ratio":2.,
            "adjacent_face_size_jump_all":{
                "count":100,"p95":1.32,"p99":1.5,"maximum":2.0},
            "adjacent_face_size_jump_near_polar":{
                "count":40,"p95":1.29,"p99":1.4,"maximum":1.5}}


def extra():
    return {"physical_tags":list(range(1,10)),
            "mean_ratio_min":.34,"mean_ratio_p01":.48,
            "near_polar_mean_ratio_p05":.55,
            "pore":{"closed_euler":2,"max_radius_error_m":1e-14,
                    "curved7_area_ratio":.9995,"q_min":.59,"q_p05":.79,
                    "north_qmin":.86,"south_qmin":.88},
            "B6":{"closed_euler":2,"max_radius_error_m":1e-14,
                  "curved7_area_ratio":.9999}}


class P10GLTests(unittest.TestCase):
    def test_01_pins_original_source_m0_d027_and_real_parse(self):
        p=G.source_gate()
        self.assertEqual(p["frozen"]["M0_msh_sha256"],G.M0_SHA)
        self.assertEqual(p["P10GK_source"]["P10GK_policy"]["new_local_south_alpha"],.06)
        self.assertEqual(p["native_parse"]["installed"]["gmsh_exe_sha256"],G.GMSH_SHA)

    def test_02_no_changes_to_cad_driver_alpha_and_complete_C1_math_eval(self):
        with tempfile.TemporaryDirectory() as root:
            dest=Path(root)
            geo=G.prepare_geo(dest)
            self.assertEqual(geo["M0_ROTATED.geo"],
                             "21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a")
            stats=G.inherited_math_eval_test(dest)
            self.assertEqual(stats["sampled_points"],12221)
            self.assertEqual(stats["factor_min"],.94)
            self.assertEqual(stats["factor_max"],1.)

    def test_03_real_frozen_M0_values_before_any_new_mesh(self):
        frozen=G.frozen_gate();t=frozen["numerical_thresholds_from_M0"]
        self.assertAlmostEqual(t["mean_ratio_min_floor"],.0721238841748767)
        self.assertAlmostEqual(t["near_polar_mean_ratio_p05_floor"],.43600118702192686)
        self.assertEqual(frozen["fixed_policy"]["mandatory_global_Veff_ratio"],[.8,.85])
        self.assertEqual(frozen["fixed_policy"]["required_sampled_detJ_positive_QP"],[27,343,729])

    def test_04_preliminary_pass_is_never_final_scientific_go(self):
        old=G.frozen_gate()
        p=G.candidate_checks(qa(),extra(),old)
        self.assertTrue(p["27qp_preliminary_all_pass"])
        self.assertEqual(p["final_343_729_and_macro_go"],"PENDING_INDEPENDENT_REVIEW")
        self.assertGreater(p["global_Veff_ratio_27qp_preliminary"],.8)
        self.assertLess(p["global_Veff_ratio_27qp_preliminary"],.85)
        x=extra();x["pore"]["south_qmin"]=.69
        b=G.candidate_checks(qa(),x,old)
        self.assertFalse(b["27qp_preliminary_all_pass"])
        self.assertFalse(b["checks"]["surface_south_q"])

    def test_05_linux_native_attempt_forbidden(self):
        if sys.platform=="win32":self.skipTest("Linux-specific guard")
        with self.assertRaisesRegex(RuntimeError,"requires user Windows"):
            G.installed_gate()

    def test_06_native_preflight_mock_only_parse_and_pins_proof(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root);runs=p/"runs";runs.mkdir()
            proof=p/"proof.json";loc=p/"local.json";profile=p/"profile.json"
            installed={"gmsh_version":"4.15.2","gmsh_exe_sha256":G.GMSH_SHA,
                       "canonical_M0_sha256":G.M0_SHA,"source_sha256":G.sha(G.SOURCE)}
            def fake_parse(folder):
                (folder/"P10GL_NATIVE_PARSE_ONLY.log").write_bytes(
                    b"Gmsh 4.15.2; -parse_and_exit; Done reading - MOCK NO MESH\n")
                return {"exit":0,"command":["gmsh","-parse_and_exit"],
                        "log_sha256":G.sha(folder/"P10GL_NATIVE_PARSE_ONLY.log")}
            with mock.patch.object(G,"RUNS",runs),\
                 mock.patch.object(G,"PROOF",proof),\
                 mock.patch.object(G,"local_marker",return_value=loc),\
                 mock.patch.object(G,"profile_marker",return_value=profile),\
                 mock.patch.object(G,"installed_gate",return_value=installed),\
                 mock.patch.object(G,"independent_m0_gate",return_value={"M0":"verified mock"}),\
                 mock.patch.object(G,"native_parse_only",side_effect=fake_parse) as native:
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(G.preflight(),0)
                self.assertEqual(native.call_count,1)
                self.assertTrue(proof.exists())
                self.assertFalse(loc.exists() or profile.exists())
                self.assertEqual(G.proof_gate(installed)["status"],
                                 "P10GL_PREFLIGHT_PASS_NO_3D_D027_FROZEN")
                folder=next(runs.glob("P10GL_PREFLIGHT_*"))
                self.assertFalse(list(folder.glob("*.msh")))
                z=folder/"P10GL_PREFLIGHT_EVIDENCE.zip"
                with zipfile.ZipFile(z) as archive:
                    self.assertIsNone(archive.testzip())
                (folder/"P10GL_NATIVE_PARSE_ONLY.log").write_bytes(b"TAMPER")
                with self.assertRaisesRegex(RuntimeError,"missing or modified"):
                    G.proof_gate(installed)

    def test_07_one_native_mock_and_both_irrevocable_markers(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root);runs=p/"runs";runs.mkdir()
            loc=p/"local.json";profile=p/"profile.json";proof=p/"proof.json"
            proof.write_text("{}\n",encoding="utf-8")
            commands=[]
            def fake_native(cmd,*,cwd,log,wall_s,memory_gib,output_dir,output_gib):
                self.assertTrue(loc.exists() and profile.exists())
                commands.append(cmd)
                self.assertEqual(wall_s,900)
                self.assertEqual(memory_gib,8)
                Path(cmd[-1]).write_bytes(b"MOCK_ONLY_NO_REAL_GMSH_MSH\n")
                log.write_bytes(b"Done meshing 3D - MOCK ONLY\n")
                return {"native_exit_code":0,"stop_reason":"","mock":True}
            with mock.patch.object(G,"RUNS",runs),\
                 mock.patch.object(G,"PROOF",proof),\
                 mock.patch.object(G,"local_marker",return_value=loc),\
                 mock.patch.object(G,"profile_marker",return_value=profile),\
                 mock.patch.object(G,"installed_gate",return_value={"mock":True}),\
                 mock.patch.object(G,"proof_gate",return_value={"mock":True}),\
                 mock.patch.object(G,"capped_process",side_effect=fake_native),\
                 mock.patch.object(G,"audit27",return_value=qa()),\
                 mock.patch.object(G,"audit_extra",return_value=extra()):
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(G.run_once(),0)
                self.assertEqual(len(commands),1)
                self.assertEqual(commands[0].count("-3"),1)
                self.assertEqual(commands[0][commands[0].index("-nt")+1],"2")
                self.assertTrue(loc.exists() and profile.exists())
                self.assertEqual(len(list(runs.glob("P10GL_M1_SOUTH_C1_HXT10_*/P10GL_M1_HXT10_EVIDENCE.zip"))),1)
                with self.assertRaisesRegex(RuntimeError,"already consumed"):
                    G.run_once()
                self.assertEqual(len(commands),1)

    def test_08_mock_watchdog_stop_also_permanently_consumes_attempt(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root);runs=p/"runs";runs.mkdir()
            loc=p/"local.json";profile=p/"profile.json";proof=p/"proof.json"
            proof.write_text("{}\n",encoding="utf-8")
            invoked=[]
            def watchdog(cmd,*,cwd,log,wall_s,memory_gib,output_dir,output_gib):
                self.assertTrue(loc.exists() and profile.exists())
                invoked.append(cmd)
                log.write_bytes(b"WATCHDOG STOP - MOCK ONLY\n")
                return {"native_exit_code":-9,"stop_reason":"WALL_LIMIT","mock":True}
            with mock.patch.object(G,"RUNS",runs),\
                 mock.patch.object(G,"PROOF",proof),\
                 mock.patch.object(G,"local_marker",return_value=loc),\
                 mock.patch.object(G,"profile_marker",return_value=profile),\
                 mock.patch.object(G,"installed_gate",return_value={"mock":True}),\
                 mock.patch.object(G,"proof_gate",return_value={"mock":True}),\
                 mock.patch.object(G,"capped_process",side_effect=watchdog):
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(G.run_once(),2)
                self.assertEqual(len(invoked),1)
                self.assertTrue(loc.exists() and profile.exists())
                with self.assertRaisesRegex(RuntimeError,"already consumed"):
                    G.run_once()
                ev=next(runs.glob("P10GL_M1_SOUTH_C1_HXT10_*/P10GL_M1_HXT10_EVIDENCE.zip"))
                with zipfile.ZipFile(ev) as z:
                    meta=json.loads(z.read("P10GL_M1_MANIFEST.json"))
                    self.assertEqual(meta["status"],"P10GL_STOP_NO_FEM")
                    self.assertEqual(meta["native"]["stop_reason"],"WALL_LIMIT")


if __name__=="__main__":unittest.main()
