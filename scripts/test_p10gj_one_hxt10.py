#!/usr/bin/env python3
"""Offline source, D-027 freeze and mock one-shot tests; NEVER calls Gmsh."""
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10GJ_ONE_ROTATED_HXT10_WINDOWS_20261123"
SPEC=importlib.util.spec_from_file_location("P10GJ_one_click_m1",SRC/"P10GJ_one_click_m1.py")
import sys
sys.path.insert(0,str(SRC))
J=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(J)
from P10GJ_mesh_extra import tet_quality, audit as audit_extra


def fake_qa():
    cad=.06*.06*.05-4*math.pi*.001**3/3
    return {"nonpositive_samples":0,"minimum_curved_detj":1e-12,
            "minimum_corner_detj":1e-12,"qp_integrated_volume_m3":cad,
            "tet10":1212,"max_element_qp_detj_ratio":2.,
            "adjacent_face_size_jump_all":{"count":100,"p95":1.2,"p99":1.3,"maximum":1.5},
            "adjacent_face_size_jump_near_polar":{"count":40,"p95":1.2,"p99":1.3,"maximum":1.5}}


def fake_extra():
    return {"physical_tags":list(range(1,10)),"mean_ratio_min":.16,
            "mean_ratio_p01":.28,"near_polar_mean_ratio_p05":.27,
            "pore":{"closed_euler":2,"max_radius_error_m":1e-14,
                    "curved7_area_ratio":.9995,"q_min":.59,"q_p05":.79,
                    "north_qmin":.86,"south_qmin":.88},
            "B6":{"closed_euler":2,"max_radius_error_m":1e-14,
                   "curved7_area_ratio":.9999}}


def fake_register():
    x={"fixed_policy":J.load(J.POLICY),
       "M0_27QP":{"qp_integrated_volume_m3":.06*.06*.05-4*math.pi*.001**3/3,
                  "tet10":1000},
       "numerical_thresholds_from_M0":{
           "mean_ratio_min_floor":.015,"mean_ratio_p01_floor":.1,
           "near_polar_mean_ratio_p05_floor":.1,"max_27qp_detj_ratio":20.,
           "adj_all_p95_max":1.4,"adj_all_p99_max":1.65,
           "adj_all_max_max":2.5,"adj_near_p95_max":1.45,
           "adj_near_p99_max":1.85}}
    return x


class P10GJTests(unittest.TestCase):
    def test_msh2_realistic_curved_tri6_and_positive_tet10(self):
        # A closed sphere and Tri6 surfaces, plus 20 affine Tet10 outside
        # the pore. Exercises the ACTUAL P10GJ combined 3D MSH2 parser.
        s=importlib.util.spec_from_file_location("p10gh_synthetic",
              ROOT/"scripts/test_p10gh_surface_compare.py")
        old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
        with tempfile.TemporaryDirectory() as tmp:
            msh=Path(tmp)/"synthetic_3d.msh"
            old.synthetic_msh(msh)
            lines=msh.read_text(encoding="ascii").splitlines()
            nidx=lines.index("$Nodes");endnodes=lines.index("$EndNodes")
            # Synthetic source assigns separate IDs to coincident vertices.
            # Canonicalize IDs of spherical Tri6 nodes to represent a truly
            # conforming closed manifold before adding synthetic Tet10.
            coords={int(row.split()[0]):tuple(row.split()[1:])
                    for row in lines[nidx+2:endnodes]}
            e0=lines.index("$Elements");e1=lines.index("$EndElements")
            reused={}
            for line_i in range(e0+2,e1):
                row=lines[line_i].split()
                if int(row[1])!=9 or int(row[3]) not in (8,9):continue
                physical=int(row[3]);ntags=int(row[2]);start=3+ntags
                for j in range(start,len(row)):
                    node=int(row[j]);key=(physical,coords[node])
                    if key not in reused:reused[key]=node
                    row[j]=str(reused[key])
                lines[line_i]=" ".join(row)
            oldnodes=int(lines[nidx+1]);v=oldnodes
            tetrows=[];newnodes=[]
            p=((0.,0.,.03101),(.00015,0.,.03101),
               (0.,.00015,.03101),(0.,0.,.03116))
            edges=((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
            for j in range(20):
                xyz=tuple(p)+tuple(tuple((p[a][k]+p[b][k])/2 for k in range(3))
                                      for a,b in edges)
                ids=[]
                for coords in xyz:
                    v+=1;ids.append(v)
                    newnodes.append(str(v)+" "+" ".join(f"{f:.17g}" for f in coords))
                tetrows.append(f"{j+10000} 11 2 1 1 "+" ".join(map(str,ids)))
            lines[nidx+1]=str(v)
            lines[endnodes:endnodes]=newnodes
            eidx=lines.index("$Elements");endelements=lines.index("$EndElements")
            original_elems=int(lines[eidx+1]);lines[eidx+1]=str(original_elems+20)
            lines[endelements:endelements]=tetrows
            msh.write_text("\n".join(lines)+"\n",encoding="ascii")
            qa=audit_extra(msh)
            self.assertEqual(qa["tet10"],20)
            self.assertEqual(qa["pore"]["closed_euler"],2)
            self.assertEqual(qa["B6"]["closed_euler"],2)
            self.assertEqual(qa["near_polar_tet10"],20)
            self.assertGreater(qa["mean_ratio_min"],0.01)

    def test_source_geometry_and_policy_pins(self):
        pol=J.source_gate()
        self.assertEqual(pol["mandatory_global_Veff_ratio"],[.8,.85])
        self.assertEqual(pol["required_sampled_detJ_positive_QP"],[27,343,729])
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            hashes=J.copy_geos(d)
            self.assertEqual(hashes["M0_ROTATED.geo"],J.ROT_M0_GEO_SHA)
            self.assertEqual(hashes["sphere_pore_B6_refined_rotated.geo"],J.ROT_CAD_SHA)
            for name in J.GEO_FILES:
                self.assertEqual((d/name).read_bytes(),(SRC/name).read_bytes())

    def test_sliver_mean_ratio_affine_regular(self):
        a=math.sqrt(3)/2
        z=math.sqrt(2/3)
        verts=[(0.,0.,0.),(1.,0.,0.),(.5,a,0.),(.5,a/3,z)]
        ids=list(range(1,11))
        nodes={i:v for i,v in enumerate(verts,1)}
        edges=((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
        for k,(i,j) in enumerate(edges,5):
            nodes[k]=tuple((verts[i][n]+verts[j][n])/2 for n in range(3))
        self.assertAlmostEqual(tet_quality(nodes,ids),1.,places=12)
        v=verts.copy();v[3]=(.5,a/3,.001)
        bad={i:p for i,p in enumerate(v,1)}
        self.assertLess(tet_quality(bad,ids),.1)

    def test_frozen_M0_numeric_gate_policy(self):
        pol=J.load(J.POLICY)
        qa={"adjacent_face_size_jump_all":{"count":100,"p95":1.3,
                                          "p99":1.5,"maximum":2.0},
            "adjacent_face_size_jump_near_polar":{"count":50,"p95":1.4,
                                                 "p99":1.7},
            "max_element_qp_detj_ratio":11.}
        extra={"mean_ratio_min":.028,"mean_ratio_p01":.15,
               "near_polar_mean_ratio_p05":.12}
        t=J.value_gate(pol,qa,extra)
        self.assertAlmostEqual(t["mean_ratio_min_floor"],.0154)
        self.assertAlmostEqual(t["mean_ratio_p01_floor"],.12)
        self.assertAlmostEqual(t["adj_all_p95_max"],1.43)
        self.assertAlmostEqual(t["adj_near_p95_max"],1.568)

    def test_candidate_pass_is_only_27qp_not_go(self):
        status=J.candidate_checks(fake_qa(),fake_extra(),fake_register())
        self.assertTrue(status["27qp_preliminary_all_pass"])
        self.assertEqual(status["final_343_729_and_macro_go"],"PENDING_INDEPENDENT_REVIEW")
        bad=fake_extra();bad["pore"]["north_qmin"]=.70
        s=J.candidate_checks(fake_qa(),bad,fake_register())
        self.assertFalse(s["27qp_preliminary_all_pass"])
        self.assertFalse(s["checks"]["surface_north_q"])

    def test_preflight_full_mock_no_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runs=root/"runs";runs.mkdir()
            proof=root/"proof.json";local=root/"local.json";profile=root/"profile.json"
            installed={"gmsh_exe_sha256":"mock-exe","M0_msh_sha256":J.M0_SHA}
            reg=fake_register();reg.update({"revision":J.REV,
                "status":"P10GJ_D027_GATES_FROZEN_BEFORE_M1_3D",
                "native_new_3d_attempts":0,"M0_msh_sha256":J.M0_SHA})
            def fake_parse(folder):
                path=folder/"P10GJ_NATIVE_PARSE_ONLY.log"
                path.write_bytes(b"MOCK parse-only; Gmsh was NOT run.\n")
                return {"exit":0,"log_sha256":J.sha(path)}
            with patch.object(J,"RUNS",runs),patch.object(J,"PROOF",proof), \
                 patch.object(J,"local_marker",return_value=local), \
                 patch.object(J,"profile_marker",return_value=profile), \
                 patch.object(J,"installed_gate",return_value=installed), \
                 patch.object(J,"preregister",return_value=reg), \
                 patch.object(J,"parse_only",side_effect=fake_parse):
                self.assertEqual(J.preflight(),0)
                p,live=J.proof_gate(installed)
                self.assertEqual(live["native_new_3d_attempts"],0)
                self.assertEqual(p["status"],"P10GJ_PREFLIGHT_PASS_GATES_FROZEN_NO_3D")
                self.assertFalse(local.exists() or profile.exists())
                self.assertEqual(len(list(runs.glob("P10GJ_PREFLIGHT_*/P10GJ_PREFLIGHT_EVIDENCE.zip"))),1)
                frozen=Path(p["preflight_run"])/"P10GJ_D027_FROZEN_GATES.json"
                frozen.write_bytes(frozen.read_bytes()+b"tamper")
                with self.assertRaisesRegex(RuntimeError,"altered"):
                    J.proof_gate(installed)

    def test_mock_single_3d_and_no_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runs=root/"runs";runs.mkdir()
            local=root/"local_lock.json";profile=root/"profile_lock.json"
            registered=fake_register();observed=[]
            frozen=root/"P10GJ_D027_FROZEN_GATES.json"
            frozen.write_text(json.dumps(registered),encoding="utf-8")
            proof_file=root/"proof.json";proof_file.write_text("{}\n",encoding="utf-8")
            proof={"preflight_run":str(root),"frozen_gates_sha256":J.sha(frozen)}
            def fake_native(cmd,*,cwd,log,wall_s,memory_gib,output_dir,output_gib):
                observed.append(cmd)
                Path(cmd[-1]).write_bytes(b"MOCK MSH - no native Gmsh executed\n")
                log.write_bytes(b"Done meshing 3D - MOCK ONLY\n")
                return {"native_exit_code":0,"stop_reason":"","mock":True}
            with patch.object(J,"RUNS",runs),patch.object(J,"SOURCE",SRC/"P10GJ_SOURCE_SHA256.json"), \
                 patch.object(J,"PROOF",proof_file), \
                 patch.object(J,"local_marker",return_value=local), \
                 patch.object(J,"profile_marker",return_value=profile), \
                 patch.object(J,"installed_gate",return_value={"mock":True}), \
                 patch.object(J,"proof_gate",return_value=(proof,registered)), \
                 patch.object(J,"capped_process",side_effect=fake_native), \
                 patch.object(J,"audit27",return_value=fake_qa()), \
                 patch.object(J,"audit_extra",return_value=fake_extra()):
                self.assertEqual(J.run_once(),0)
                self.assertEqual(len(observed),1)
                self.assertEqual(observed[0].count("-3"),1)
                self.assertTrue(local.exists() and profile.exists())
                evidence=list(runs.glob("P10GJ_M1_ROTATED_HXT10_*/P10GJ_M1_HXT10_EVIDENCE.zip"))
                self.assertEqual(len(evidence),1)
                with self.assertRaisesRegex(RuntimeError,"consumed"):
                    J.run_once()
                self.assertEqual(len(observed),1)


if __name__=="__main__":unittest.main()
