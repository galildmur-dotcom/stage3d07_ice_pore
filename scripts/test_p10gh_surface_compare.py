#!/usr/bin/env python3
"""Synthetic offline tests for P10GH Tri6; no Gmsh, no FEM."""
import importlib.util
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "research/proposals/P10GH_WINDOWS_GEO_BYTE_STABLE_20261123/P10GH_surface_compare.py"
SPEC = importlib.util.spec_from_file_location("p10gh_surface_compare", APP)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _normalize(x):
    length = math.sqrt(sum(v*v for v in x))
    return tuple(v/length for v in x)


def synthetic_msh(path: Path, wrong_radius=False, omit_south=False):
    """Build exact spherical quadratic triangles from a normalized icosahedron."""
    t = (1 + math.sqrt(5))/2
    v = [(-1,t,0), (1,t,0), (-1,-t,0), (1,-t,0),
         (0,-1,t), (0,1,t), (0,-1,-t), (0,1,-t),
         (t,0,-1), (t,0,1), (-t,0,-1), (-t,0,1)]
    faces = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),
             (1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
             (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
             (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    nodes, elements = [], []
    def add_tri(kind, pts):
        ids = []
        for x in pts:
            ids.append(len(nodes)+1)
            nodes.append(x)
        elements.append((kind,ids))
    for physical, rad in ((8,.001), (9,.006)):
        for a,b,c in faces:
            x,y,z = [_normalize(v[i]) for i in (a,b,c)]
            if omit_south and physical==8 and (x[2]+y[2]+z[2])<0:
                continue
            directions = (x,y,z,_normalize(tuple(x[i]+y[i] for i in range(3))),
                          _normalize(tuple(y[i]+z[i] for i in range(3))),
                          _normalize(tuple(z[i]+x[i] for i in range(3))))
            r = rad + (1e-6 if wrong_radius and physical==8 else 0)
            add_tri(physical, [(r*d[0],r*d[1],.03+r*d[2]) for d in directions])
    for physical in range(2,8):
        x = physical*.001
        add_tri(physical, [(x,0,0), (x+.001,0,0), (x,.001,0),
                           (x+.0005,0,0),(x+.0005,.0005,0),(x,.0005,0)])
    lines = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat", "$Nodes", str(len(nodes))]
    for i,(x,y,z) in enumerate(nodes,1):
        lines.append(f"{i} {x:.17g} {y:.17g} {z:.17g}")
    lines.extend(["$EndNodes", "$Elements", str(len(elements))])
    for i,(phys,ids) in enumerate(elements,1):
        lines.append(f"{i} 9 2 {phys} {phys} " + " ".join(map(str,ids)))
    lines.append("$EndElements")
    path.write_text("\n".join(lines)+"\n", encoding="ascii")


class P10GHSourceTests(unittest.TestCase):
    def test_byte_stable_geos_regression_for_windows_crlf(self):
        # P10GG incorrectly compared a CRLF-on-Windows preflight digest with
        # an LF-in-memory digest. P10GH writes bytes in binary mode.
        sources = MODULE.variants()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            written = MODULE.write_geos(root)
            self.assertEqual(written, MODULE.source_selftest()["generated_sha256"])
            for name, contents in sources.items():
                self.assertEqual((root/name).read_bytes(), contents.encode("utf-8"))
                if "\n" in contents:
                    legacy_windows = contents.replace("\n", "\r\n").encode("utf-8")
                    self.assertNotEqual(MODULE.digest(legacy_windows), written[name])

    def test_preflight_proof_is_accepted_before_native_mesh(self):
        # Runs complete gate chain with the native Gmsh functions mocked;
        # the produced preflight digest must survive proof_gate unchanged.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root/"LOCAL_RUNS"
            runs.mkdir()
            proof_file = root/"P10GH_PREFLIGHT_PROOF.json"
            installed = {"gmsh_exe_sha256": "mock_exe", "M0_sha256": MODULE.M0_MSH_SHA,
                         "source_pin_sha256": MODULE.sha256(MODULE.PIN)}
            with patch.object(MODULE, "RUNS", runs), \
                 patch.object(MODULE, "PROOF", proof_file), \
                 patch.object(MODULE, "windows_gate", return_value=installed), \
                 patch.object(MODULE, "native_parse", return_value={"mock":True}), \
                 patch.dict(os.environ, {"LOCALAPPDATA": str(root)}):
                self.assertEqual(MODULE.preflight(), 0)
                p = MODULE.proof_gate(installed)
                self.assertEqual(p["generated_sha256"],
                                 MODULE.source_selftest()["generated_sha256"])
                self.assertEqual(len(list(runs.glob("P10GH_PREFLIGHT_*/P10GH_PREFLIGHT_EVIDENCE.zip"))), 1)

    def test_equal_size_fields_and_only_cad_rotation(self):
        files = MODULE.variants()
        self.assertEqual(files["M0_ROTATED.geo"].replace(
            'Include "sphere_pore_B6_refined_rotated.geo";', MODULE.BASE_INCLUDE),
            files["M0.geo"])
        self.assertEqual(files["sphere_pore_B6_refined_rotated.geo"].replace(
            MODULE.CAD_ANCHOR + "\n" + MODULE.CAD_ROTATE, MODULE.CAD_ANCHOR),
            files["sphere_pore_B6_refined.geo"])
        self.assertAlmostEqual(MODULE.SCALE**3, .825, places=14)

    def test_curved_spherical_tri6_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            msh = Path(tmp)/"synthetic.msh"
            synthetic_msh(msh)
            report = MODULE.audit_surface(msh)
            self.assertEqual(report["physical_tri6_counts"][8],20)
            self.assertEqual(report["physical_tri6_counts"][9],20)
            self.assertGreater(report["north_polar_tri6"],0)
            self.assertGreater(report["south_polar_tri6"],0)
            self.assertGreater(report["q_corner_min"],0.3)
            self.assertGreater(report["minimum_curved_surface_jacobian"],0)
            self.assertLess(report["max_pore_radius_node_error_m"],1e-12)

    def test_radius_tamper_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            msh=Path(tmp)/"bad_radius.msh"
            synthetic_msh(msh,wrong_radius=True)
            with self.assertRaisesRegex(RuntimeError,"radius"):
                MODULE.audit_surface(msh)

    def test_missing_signed_surface_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            msh=Path(tmp)/"missing_south.msh"
            synthetic_msh(msh,omit_south=True)
            with self.assertRaisesRegex(RuntimeError,"area|polar"):
                MODULE.audit_surface(msh)

    def test_3d_element_prohibited(self):
        with tempfile.TemporaryDirectory() as tmp:
            msh=Path(tmp)/"not2d.msh"
            synthetic_msh(msh)
            txt=msh.read_text(encoding="ascii")
            txt=txt.replace("1 9 2 8 8", "1 11 2 8 8",1)
            msh.write_text(txt,encoding="ascii")
            with self.assertRaisesRegex(RuntimeError,"3D element"):
                MODULE.audit_surface(msh)

    def test_mock_two_2d_and_permanent_no_repeat(self):
        # Mocks the native boundary only. No Gmsh process is ever started.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root/"LOCAL_RUNS"
            runs.mkdir()
            local = root/"P10GH_LOCAL_LOCK.json"
            profile = root/"P10GH_PROFILE_LOCK.json"
            proof = {"generated_sha256": MODULE.source_selftest()["generated_sha256"]}
            observed = []

            def mock_native(geo, msh, log):
                observed.append(geo.name)
                synthetic_msh(msh)
                log.write_text("MOCK ONLY. No real Gmsh was run.\n",encoding="utf-8")
                return {"exit_code":0,"mock":True,"native_3d_attempts":0}

            with patch.object(MODULE,"RUNS",runs), \
                 patch.object(MODULE,"local_marker",return_value=local), \
                 patch.object(MODULE,"profile_marker",return_value=profile), \
                 patch.object(MODULE,"windows_gate",return_value={"mock":True}), \
                 patch.object(MODULE,"proof_gate",return_value=proof), \
                 patch.object(MODULE,"run_surface_bounded",side_effect=mock_native), \
                 patch.dict(os.environ, {"LOCALAPPDATA": str(root)}):
                self.assertEqual(MODULE.run_pair(),0)
                self.assertEqual(observed,["P10GH_ORIGINAL_SURFACE.geo",
                                           "P10GH_ROTATED_SURFACE.geo"])
                self.assertTrue(local.exists() and profile.exists())
                outputs=list(runs.glob("P10GH_CAD_POLES_*/P10GH_CAD_POLE_2D_EVIDENCE.zip"))
                self.assertEqual(len(outputs),1)
                self.assertEqual(MODULE.read_json(outputs[0].parent/
                    "P10GH_CAD_POLE_METRICS.json")["native_2d_attempts"],2)
                with self.assertRaisesRegex(RuntimeError,"already consumed"):
                    MODULE.run_pair()
                self.assertEqual(len(observed),2)


if __name__=="__main__":
    unittest.main()
