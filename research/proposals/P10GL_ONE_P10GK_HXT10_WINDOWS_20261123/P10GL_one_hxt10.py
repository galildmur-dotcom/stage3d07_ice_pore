#!/usr/bin/env python3
"""P10GL R1: exactly one guarded P10GK C1 south-field HXT10 mesh on Windows.

--selftest: source/independent frozen gates/real parse evidence, NO native tools.
--preflight: M0 27QP independent verification, native -parse_and_exit ONLY.
--one-hxt10: permanently consumes two markers before ONE native -3; NO FEM.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback
import zipfile

from P10FN_common import capped_process
from P10FN_mesh_qa import audit as audit27
from P10GJ_mesh_extra import audit as audit_extra

HERE=Path(__file__).resolve().parent
PROJECT=Path(r"G:\ildar\Stage3D07")
MESHES=PROJECT/"meshes"
RUNS=PROJECT/"LOCAL_RUNS"
GMSH=Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
REV="P10GL_R1_USER_APPROVED_ONE_P10GK_C1_HXT10_3D_NO_FEM"
SOURCE=HERE/"P10GL_SOURCE_SHA256.json"
FROZEN=HERE/"P10GJ_D027_FROZEN_GATES.json"
SOURCE_ZIP=HERE/"P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip"
PARSE_EVIDENCE=HERE/"P10GK_SOURCE_PREFLIGHT_EVIDENCE.zip"
BASELINE=HERE/"P10GJ_M0_QP_BASELINE.json"
PROOF=HERE/"P10GL_PREFLIGHT_PROOF.json"
DRIVER="P10GL_ONE_P10GK_M1_HXT10.geo"
MESH="P10GL_M1_SOUTH_C1_CANDIDATE.msh"
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
FROZEN_SHA="2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea"
SOURCE_ZIP_SHA="4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05"
PARSE_EVIDENCE_SHA="6af4dac68f1335aa714b02702ef7c305624ea46622b067fd5aacee6bde89305f"
GMSH_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
SOURCE_FILES={
    "P10GL_one_hxt10.py",DRIVER,"P10FN_common.py","P10FN_mesh_qa.py",
    "P10CK_curved_qp_audit.py","P10GJ_mesh_extra.py","p10gi_independent_surface_audit.py",
    "P10GJ_M0_QP_BASELINE.json","P10GJ_D027_FROZEN_GATES.json",
    SOURCE_ZIP.name,PARSE_EVIDENCE.name,
    "01_P10GL_PREFLIGHT_NO_MESH.cmd","02_P10GL_ONE_HXT10_3D_ONLY.cmd",
    "README_P10GL_RU.md",
}
SOURCE_GEO_NAMES={"M0.geo","M0_ROTATED.geo","sphere_pore_B6_refined.geo",
                  "sphere_pore_B6_refined_rotated.geo","P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo",
                  "P10GK_SOURCE_POLICY.json","P10GK_SOURCE_SHA256.json"}
MAX_MSH_BYTES=128*1024**2
MAX_LOG_BYTES=8*1024**2


def need(ok,why):
    if not ok:raise RuntimeError("P10GL_STOP: "+why)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def sha_bytes(b):return hashlib.sha256(b).hexdigest()


def load(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.write("\n")


def stamp():return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def frozen_gate():
    need(sha(FROZEN)==FROZEN_SHA,"M0 numeric prereg frozen gates changed")
    g=load(FROZEN)
    need(g["status"]=="P10GJ_D027_GATES_FROZEN_BEFORE_M1_3D"
         and g["M0_msh_sha256"]==M0_SHA
         and g["native_new_3d_attempts"]==0
         and g["FEM_attempts"]==0
         and g["fixed_policy"]["mandatory_global_Veff_ratio"]==[.8,.85]
         and g["fixed_policy"]["macro_QP_effective_Veff_assessment"]
             ["populated_near_polar_d_le_0p5mm_ratio_max"]==.98
         and g["fixed_policy"]["required_sampled_detJ_positive_QP"]==[27,343,729]
         and g["fixed_policy"]["macro_QP_effective_Veff_assessment"]
             ["all_18_signed_zone_ratios"]=="diagnostic_only_not_18_of_18_hard",
         "not the previously frozen D-027 M0-only policy")
    return g


def pinned_source_zip():
    need(sha(SOURCE_ZIP)==SOURCE_ZIP_SHA,"P10GK previous source release SHA changed")
    with zipfile.ZipFile(SOURCE_ZIP) as z:
        need(z.testzip() is None,"P10GK source ZIP CRC failed")
        names=z.namelist()
        need(len(names)==len(set(names))==12 and all("/" not in n and "\\" not in n for n in names),
             "untrusted P10GK ZIP entries")
        pin=json.loads(z.read("P10GK_SOURCE_SHA256.json"))
        need(pin["revision"]=="P10GK_R1_C1_SOUTH_FOCUS_SOURCE_ONLY"
             and pin["native_mesh_3d_authorized"] is False
             and pin["FEM_authorized"] is False
             and set(names)==set(pin["files"])|{"P10GK_SOURCE_SHA256.json"},
             "P10GK source pin manifest invalid")
        for name,digest in pin["files"].items():
            need(sha_bytes(z.read(name))==digest,"P10GK source member tampered: "+name)
        p=json.loads(z.read("P10GK_SOURCE_POLICY.json"))
        need(p["new_local_south_alpha"]==.06
             and p["global_mesh_size_factor"]==0.9378887276834518
             and p["parent_M0_msh_sha256"]==M0_SHA
             and p["native_mesh_3d_authorized"] is False,
             "not the approved proposed P10GK source")
        return {"file_sha256":sha(SOURCE_ZIP),"member_pin":pin,
                "P10GK_policy":p,"geo_sha256":{
                    n:sha_bytes(z.read(n)) for n in SOURCE_GEO_NAMES if n.endswith(".geo")}}


def parse_evidence_gate(source):
    need(sha(PARSE_EVIDENCE)==PARSE_EVIDENCE_SHA,"real P10GK parse-only ZIP altered")
    with zipfile.ZipFile(PARSE_EVIDENCE) as z:
        need(z.testzip() is None,"real parse ZIP CRC error")
        report=json.loads(z.read("P10GK_SOURCE_REPORT.json"))
        need(report["revision"]=="P10GK_R1_C1_SOUTH_FOCUS_SOURCE_ONLY"
             and report["status"]=="P10GK_SOURCE_AND_NATIVE_PARSE_ONLY_PASS_NO_MESH_NO_FEM"
             and report["native_parse_only_exit_code"]==0
             and report["native_1d_2d_3d_attempts"]==0 and report["FEM_attempts"]==0,
             "real Windows P10GK parse-only did not PASS")
        need(report["installed"]["gmsh_version"]=="4.15.2"
             and report["installed"]["gmsh_exe_sha256"]==GMSH_SHA
             and report["installed"]["parent_M0_sha256"]==M0_SHA,
             "Windows parse-only hardware/software pin mismatch")
        samples=report["math_eval_samples"]
        need(samples["sampled_points"]==12221
             and samples["max_analytic_MathEval_ratio_error"]<1e-12
             and samples["factor_min"]==.94 and samples["factor_max"]==1.,
             "C1 MathEval source QA insufficient")
        log=z.read("P10GK_NATIVE_PARSE_ONLY.log")
        txt=log.decode("utf-8",errors="replace")
        need(sha_bytes(log)==report["native_parse_log_sha256"]
             and "-parse_and_exit" in txt and "Done reading" in txt
             and "Gmsh 4.15.2" in txt and "Stopped on" in txt
             and "Meshing 3D" not in txt and not re.search(r"\bError\s*:",txt),
             "native parse-only log bad")
        for name in SOURCE_GEO_NAMES:
            if name in z.namelist():
                if name.endswith(".geo"):
                    need(sha_bytes(z.read(name))==source["geo_sha256"][name],
                         "native parsed different GEO: "+name)
        return {"evidence_sha256":sha(PARSE_EVIDENCE),
                "native_parse_log_sha256":sha_bytes(log),"installed":report["installed"]}


def source_gate():
    m=load(SOURCE)
    need(m.get("revision")==REV and m.get("user_approved_new_native_3d_max_attempts")==1
         and m.get("FEM_max_attempts")==0
         and set(m.get("files",{}))==SOURCE_FILES,"invalid P10GL release manifest")
    for name,digest in m["files"].items():
        need((HERE/name).is_file() and sha(HERE/name)==digest,"tampered/missing source: "+name)
    dr=(HERE/DRIVER).read_text(encoding="utf-8")
    need(dr.count('Include "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo";')==1
         and "Field[" not in dr and "Mesh.Algorithm3D = 10;" in dr
         and "Mesh.MeshSizeFactor = 0.9378887276834518;" in dr,
         "P10GL wrapper must not modify CAD/size fields")
    f=frozen_gate();src=pinned_source_zip();parsed=parse_evidence_gate(src)
    b=load(BASELINE)
    need(b["canonical_M0_msh_sha256"]==M0_SHA
         and b["M0"]["tet10"]==7992 and b["M0"]["nodes"]==11699
         and b["levels"]["7"]["qp_per_tet"]==343
         and b["levels"]["9"]["qp_per_tet"]==729,
         "independent M0 QP baseline altered")
    return {"frozen":f,"P10GK_source":src,"native_parse":parsed}


def installed_gate():
    need(sys.platform=="win32","native mode requires user Windows 11")
    need(PROJECT.drive.upper()=="G:" and MESHES.is_dir() and RUNS.is_dir(),
         "G: Stage3D07 canonical folders missing")
    need(GMSH.is_file() and sha(GMSH)==GMSH_SHA,"Gmsh4.15.2 executable changed/missing")
    need((MESHES/"M0.msh").is_file() and sha(MESHES/"M0.msh")==M0_SHA,
         "canonical M0.msh changed")
    with zipfile.ZipFile(SOURCE_ZIP) as z:
        for name in ("M0.geo","sphere_pore_B6_refined.geo"):
            need((MESHES/name).is_file() and sha(MESHES/name)==sha_bytes(z.read(name)),
                 "canonical G: M0 GEO/CAD mismatch: "+name)
    p=subprocess.run([str(GMSH),"-version"],cwd=HERE,stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15,check=False)
    version=p.stdout.decode("utf-8",errors="replace").strip()
    need(p.returncode==0 and "4.15.2" in version,"unexpected Gmsh version")
    return {"gmsh_version":version,"gmsh_exe_sha256":GMSH_SHA,
            "canonical_M0_sha256":M0_SHA,"source_sha256":sha(SOURCE)}


def local_marker():return RUNS/"P10GL_LOCKS"/("M0_"+M0_SHA[:20]+".json")


def profile_marker():
    app=os.environ.get("LOCALAPPDATA","")
    need(app and Path(app).is_dir(),"LOCALAPPDATA profile unavailable")
    return Path(app)/"Stage3D07"/"P10GL_ONE_HXT10"/("M0_"+M0_SHA[:20]+".json")


def one_shot_free():
    need(not local_marker().exists() and not profile_marker().exists(),
         "P10GL one new HXT10 native attempt already consumed; NEVER repeat")


def prepare_geo(folder):
    with zipfile.ZipFile(SOURCE_ZIP) as z:
        for name in sorted(SOURCE_GEO_NAMES):
            dest=folder/name
            with dest.open("xb") as f:f.write(z.read(name))
            need(sha(dest)==sha_bytes(z.read(name)),"GEO binary source copy differs")
    with (HERE/DRIVER).open("rb") as a,(folder/DRIVER).open("xb") as b:
        shutil.copyfileobj(a,b)
    need(sha(folder/DRIVER)==sha(HERE/DRIVER),"wrapper GEO copy differs")
    return {name:sha(folder/name) for name in sorted(SOURCE_GEO_NAMES|{DRIVER})}


def inherited_math_eval_test(folder):
    script=folder/"P10GK_source_qa.py"
    with zipfile.ZipFile(SOURCE_ZIP) as z:
        for name in z.namelist():
            if name not in SOURCE_GEO_NAMES:
                with (folder/name).open("xb") as f:f.write(z.read(name))
    sp=importlib.util.spec_from_file_location("p10gk_source_revalidated_in_run",script)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    p=mod.source_gate();stats=mod.test_field()
    need(p["new_local_south_alpha"]==.06 and stats["sampled_points"]==12221,
         "P10GK independent MathEval 12221-point gate failed")
    return stats


def independent_m0_gate(frozen):
    q=audit27(MESHES/"M0.msh")
    x=audit_extra(MESHES/"M0.msh")
    old=frozen["M0_27QP"];ox=frozen["M0_extra"]
    need(q["mesh_sha256"]==M0_SHA and q["tet10"]==7992 and x["nodes"]==11699,
         "M0 reread changed")
    for name in ("qp_integrated_volume_m3","minimum_curved_detj",
                 "max_element_qp_detj_ratio"):
        need(math.isclose(q[name],old[name],rel_tol=1e-11,abs_tol=1e-25),
             "frozen M0 27QP differs: "+name)
    for name in ("mean_ratio_min","mean_ratio_p01","near_polar_mean_ratio_p05"):
        need(math.isclose(x[name],ox[name],rel_tol=1e-11,abs_tol=1e-20),
             "frozen M0 extra differs: "+name)
    return {"M0_27QP_sha256":q["mesh_sha256"],"M0_27QP_detJ_min":q["minimum_curved_detj"],
            "M0_tet10":q["tet10"],"M0_pore_qmin":x["pore"]["q_min"]}


def native_parse_only(folder):
    cmd=[str(GMSH),str(folder/DRIVER),"-parse_and_exit","-nopopup","-nt","2"]
    need(not any(s in cmd for s in ("-1","-2","-3")),"parse must not mesh")
    out=subprocess.run(cmd,cwd=folder,stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                       timeout=60,check=False)
    log=folder/"P10GL_NATIVE_PARSE_ONLY.log"
    log.write_text(out.stdout.decode("utf-8",errors="replace")[:4*1024**2],encoding="utf-8")
    need(out.returncode==0 and "Done reading" in log.read_text(encoding="utf-8")
         and not re.search(r"\bError\s*:",log.read_text(encoding="utf-8")),
         "new P10GL wrapper native parse failed")
    need(not list(folder.glob("*.msh")),"unexpected native parse mesh")
    return {"exit":out.returncode,"command":cmd,"log_sha256":sha(log)}


def evidence(folder,output):
    target=folder/output
    with zipfile.ZipFile(target,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(folder.iterdir()):
            if path.is_file() and path!=target and path.stat().st_size<=MAX_MSH_BYTES:
                z.write(path,path.name)
        for p in (SOURCE,SOURCE_ZIP,PARSE_EVIDENCE,FROZEN,BASELINE):
            if p.name not in {f.name for f in folder.iterdir()}:
                z.write(p,p.name)
    need(target.stat().st_size<=144*1024**2,"evidence size exceeds 144 MiB")
    print("SEND THIS ONE EVIDENCE ZIP:",target,flush=True)
    return target


def preflight():
    gate=source_gate();installed=installed_gate();one_shot_free()
    folder=RUNS/("P10GL_PREFLIGHT_"+stamp());folder.mkdir(exist_ok=False)
    report={"revision":REV,"status":"P10GL_PREFLIGHT_STOP_NO_3D_NO_FEM",
            "source_pin_sha256":sha(SOURCE),"P10GK_source_sha256":SOURCE_ZIP_SHA,
            "real_parse_evidence_sha256":PARSE_EVIDENCE_SHA,
            "frozen_M0_D027_sha256":FROZEN_SHA,"native_mesh_attempts":0,"FEM_attempts":0}
    result=2
    try:
        copied=prepare_geo(folder)
        src=inherited_math_eval_test(folder)
        m0=independent_m0_gate(gate["frozen"])
        parse=native_parse_only(folder)
        report.update({"status":"P10GL_PREFLIGHT_PASS_NO_3D_D027_FROZEN",
                       "installed":installed,"geometry_copy_sha256":copied,
                       "source_C1":src,"M0_preregister_revalidated":m0,
                       "native_parse_only":parse})
        proof={"revision":REV,"status":report["status"],
               "created_utc":datetime.now(timezone.utc).isoformat(),
               "folder":str(folder),"source_pin_sha256":sha(SOURCE),
               "Gmsh_exe_sha256":GMSH_SHA,"M0_sha256":M0_SHA,
               "P10GK_original_source_zip_sha256":SOURCE_ZIP_SHA,
               "P10GK_real_parse_evidence_sha256":PARSE_EVIDENCE_SHA,
               "frozen_D027_sha256":FROZEN_SHA,
               "P10GL_driver_geo_sha256":sha(HERE/DRIVER),
               "fresh_parse_log_sha256":parse["log_sha256"],
               "native_mesh_attempts":0,"FEM_attempts":0}
        PROOF.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("P10GL_PREFLIGHT_PASS_NO_3D_D027_FROZEN",flush=True)
        result=0
    except BaseException as e:
        report["error"]=repr(e)
        (folder/"P10GL_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    write_new(folder/"P10GL_PREFLIGHT_REPORT.json",report)
    evidence(folder,"P10GL_PREFLIGHT_EVIDENCE.zip")
    return result


def proof_gate(installed):
    need(PROOF.is_file(),"run P10GL 01 preflight first")
    p=load(PROOF)
    need(p["revision"]==REV and p["status"]=="P10GL_PREFLIGHT_PASS_NO_3D_D027_FROZEN"
         and p["source_pin_sha256"]==sha(SOURCE)
         and p["Gmsh_exe_sha256"]==GMSH_SHA
         and p["M0_sha256"]==M0_SHA
         and p["P10GK_original_source_zip_sha256"]==SOURCE_ZIP_SHA
         and p["P10GK_real_parse_evidence_sha256"]==PARSE_EVIDENCE_SHA
         and p["frozen_D027_sha256"]==FROZEN_SHA
         and p["P10GL_driver_geo_sha256"]==sha(HERE/DRIVER)
         and p["native_mesh_attempts"]==0 and p["FEM_attempts"]==0,
         "preflight proof changed")
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(p["created_utc"])).total_seconds()
    need(0<=age<=24*3600,"preflight proof older than 24h")
    folder=Path(p["folder"])
    log=folder/"P10GL_NATIVE_PARSE_ONLY.log"
    report=folder/"P10GL_PREFLIGHT_REPORT.json"
    need(log.is_file() and sha(log)==p["fresh_parse_log_sha256"]
         and report.is_file() and load(report)["status"]==p["status"],
         "preflight logs/report missing or modified")
    need(installed["gmsh_exe_sha256"]==GMSH_SHA,"native Gmsh changed")
    return p


def candidate_checks(q,x,old):
    g=old["fixed_policy"];t=old["numerical_thresholds_from_M0"]
    base=old["M0_27QP"]
    ratio=(q["qp_integrated_volume_m3"]/q["tet10"])/(
           base["qp_integrated_volume_m3"]/base["tet10"])
    adj=q["adjacent_face_size_jump_all"]
    near=q["adjacent_face_size_jump_near_polar"]
    checks={
      "27qp_detJ_and_corner_positive":q["nonpositive_samples"]==0
          and q["minimum_curved_detj"]>0 and q["minimum_corner_detj"]>0,
      "CAD_total_volume":abs(q["qp_integrated_volume_m3"]/
          (.06*.06*.05-4*math.pi*.001**3/3)-1)<=g["required_cad_volume_rel_error_max"],
      "global_mean_Veff_ratio_27qp_preliminary":g["mandatory_global_Veff_ratio"][0]
          <=ratio<=g["mandatory_global_Veff_ratio"][1],
      "physical_tags_and_surface_closure":x["physical_tags"]==list(range(1,10))
          and x["pore"]["closed_euler"]==2 and x["B6"]["closed_euler"]==2,
      "pore_radius":x["pore"]["max_radius_error_m"]<=g["required_pore_and_B6_node_radius_error_m_max"],
      "B6_radius":x["B6"]["max_radius_error_m"]<=g["required_pore_and_B6_node_radius_error_m_max"],
      "pore_B6_area":all(g["required_pore_and_B6_7qp_area_ratio"][0]
          <=x[k]["curved7_area_ratio"]<=g["required_pore_and_B6_7qp_area_ratio"][1]
          for k in ("pore","B6")),
      "surface_pore_min_q":x["pore"]["q_min"]>=g["required_pore_Tri6_q_corner_min"],
      "surface_pore_p05_q":x["pore"]["q_p05"]>=g["required_pore_Tri6_q_corner_p05"],
      "surface_north_q":x["pore"]["north_qmin"]>=g["required_physical_north_Tri6_q_corner_min"],
      "surface_south_q":x["pore"]["south_qmin"]>=g["required_physical_south_Tri6_q_corner_min"],
      "tet_corner_sliver_min":x["mean_ratio_min"]>=t["mean_ratio_min_floor"],
      "tet_corner_sliver_p01":x["mean_ratio_p01"]>=t["mean_ratio_p01_floor"],
      "tet_near_polar_sliver_p05":x["near_polar_mean_ratio_p05"]>=t["near_polar_mean_ratio_p05_floor"],
      "tet_curved_detJ_variation":q["max_element_qp_detj_ratio"]<=t["max_27qp_detj_ratio"],
      "adj_all_p95":adj["p95"]<=t["adj_all_p95_max"],
      "adj_all_p99":adj["p99"]<=t["adj_all_p99_max"],
      "adj_all_max":adj["maximum"]<=t["adj_all_max_max"],
      "adj_near_p95":near["count"]>0 and near["p95"]<=t["adj_near_p95_max"],
      "adj_near_p99":near["count"]>0 and near["p99"]<=t["adj_near_p99_max"],
    }
    return {"global_Veff_ratio_27qp_preliminary":ratio,
            "checks":checks,"27qp_preliminary_all_pass":all(checks.values()),
            "final_343_729_and_macro_go":"PENDING_INDEPENDENT_REVIEW",
            "legacy_strict_18_of_18":"DIAGNOSTIC_ONLY_PENDING"}


def run_once():
    gates=source_gate();installed=installed_gate();one_shot_free()
    proof=proof_gate(installed)
    folder=RUNS/("P10GL_M1_SOUTH_C1_HXT10_"+stamp())
    folder.mkdir(exist_ok=False)
    marker={"revision":REV,"time_utc":datetime.now(timezone.utc).isoformat(),
            "M0_sha256":M0_SHA,"P10GK_source_sha256":SOURCE_ZIP_SHA,
            "frozen_D027_sha256":FROZEN_SHA,"native_3d_max_attempts":1,
            "FEM_max_attempts":0}
    # Irrevocable, exclusive local AND profile markers precede any Gmsh -3 invocation.
    write_new(local_marker(),marker)
    write_new(profile_marker(),marker)
    mesh=folder/MESH
    log=folder/"P10GL_GMSH_3D.log"
    report={"revision":REV,"status":"P10GL_STOP_NO_FEM",
            "parent_M0_sha256":M0_SHA,"P10GK_source_zip_sha256":SOURCE_ZIP_SHA,
            "real_parse_evidence_sha256":PARSE_EVIDENCE_SHA,
            "frozen_gates_sha256":FROZEN_SHA,"preflight_proof_sha256":sha(PROOF),
            "native_3d_attempts":0,"FEM_attempts":0}
    result=2
    try:
        copied=prepare_geo(folder)
        stats=inherited_math_eval_test(folder)
        report["source_geo_sha256"]=copied
        report["P10GK_C1_field_QA"]=stats
        cmd=[str(GMSH),str(folder/DRIVER),"-3","-nopopup","-nt","2",
             "-format","msh2","-o",str(mesh)]
        need(cmd.count("-3")==1 and "-save_all" not in cmd,"forbidden mesh command")
        print("P10GL ONE P10GK HXT10 native -3: 900s, private8GiB, 2 threads; NO FEM",flush=True)
        report["native_3d_attempts"]=1
        report["command"]=cmd
        native=capped_process(cmd,cwd=folder,log=log,wall_s=900,
                              memory_gib=8,output_dir=folder,output_gib=2)
        report["native"]=native
        need(native["native_exit_code"]==0 and not native["stop_reason"],
             "native Gmsh/resource STOP")
        need(mesh.is_file() and 0<mesh.stat().st_size<=MAX_MSH_BYTES,
             "missing/oversized candidate MSH")
        need(log.is_file() and log.stat().st_size<=MAX_LOG_BYTES,
             "missing/oversized Gmsh log")
        info=log.read_text(encoding="utf-8",errors="replace")
        need("Done meshing 3D" in info and not re.search(r"\bError\s*:",info),
             "native Gmsh meshing completion/error log")
        report["mesh_sha256"]=sha(mesh)
        qa=audit27(mesh);extra=audit_extra(mesh)
        report["qa27"]=qa;report["qa_extra"]=extra
        preliminary=candidate_checks(qa,extra,gates["frozen"])
        report["D027_preliminary_27QP"]=preliminary
        report["status"]=("P10GL_NATIVE_27QP_PRELIM_PASS_343_729_PENDING_NO_FEM"
                          if preliminary["27qp_preliminary_all_pass"] else
                          "P10GL_27QP_GATE_STOP_NO_FEM")
        result=0 if preliminary["27qp_preliminary_all_pass"] else 2
    except BaseException as error:
        report["error"]=repr(error)
        (folder/"P10GL_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        write_new(folder/"P10GL_M1_MANIFEST.json",report)
        shutil.copyfile(FROZEN,folder/FROZEN.name)
        evidence(folder,"P10GL_M1_HXT10_EVIDENCE.zip")
    print("P10GL_RESULT",report["status"],flush=True)
    print("NO FEM. NO M1 GO. SEND EVIDENCE FOR INDEPENDENT 343/729QP REVIEW.",flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest",action="store_true")
    g.add_argument("--preflight",action="store_true")
    g.add_argument("--one-hxt10",action="store_true")
    a=p.parse_args()
    if a.selftest:
        result=source_gate()
        print("P10GL_SOURCE_M0_D027_REAL_P10GK_PARSE_PROOF_PINS_PASS_NO_MESH_NO_FEM",
              "GATES_SHA",sha(FROZEN),flush=True)
        need(result["native_parse"]["installed"]["gmsh_exe_sha256"]==GMSH_SHA,
             "proven native Gmsh mismatch")
        return 0
    if a.preflight:return preflight()
    return run_once()


if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as error:
        print("P10GL_STOP:",repr(error),file=sys.stderr,flush=True)
        raise SystemExit(2)
