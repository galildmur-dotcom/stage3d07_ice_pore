#!/usr/bin/env python3
"""P10GJ R1: one bounded Windows HXT10 -3; M0-only D-027 prereg; NO FEM.

01 freezes numerical thresholds from canonical M0 *before* any new -3.
02 consumes permanent one-shot markers before the single native -3.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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
SOURCE=HERE/"P10GJ_SOURCE_SHA256.json"
POLICY=HERE/"P10GJ_D027_GATE_POLICY.json"
BASELINE=HERE/"P10GJ_M0_QP_BASELINE.json"
PROOF=HERE/"P10GJ_PREFLIGHT_PROOF.json"
REV="P10GJ_R1_M0_PREREG_ONE_ROTATED_HXT10_3D_NO_FEM"
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M0_GEO_SHA="ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
CAD_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
ROT_M0_GEO_SHA="21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a"
ROT_CAD_SHA="e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329"
GEO_FILES=("M0.geo","M0_ROTATED.geo","sphere_pore_B6_refined.geo",
           "sphere_pore_B6_refined_rotated.geo","P10GJ_M1_ROTATED_CANDIDATE.geo")
PACK_FILES=set(GEO_FILES)|{
    "P10GJ_one_click_m1.py","P10GJ_mesh_extra.py",
    "P10FN_common.py","P10FN_mesh_qa.py","P10CK_curved_qp_audit.py",
    "p10gi_independent_surface_audit.py","P10GJ_D027_GATE_POLICY.json",
    "P10GJ_M0_QP_BASELINE.json","README_P10GJ_RU.md",
    "01_P10GJ_PREFLIGHT_FREEZE_GATES.cmd","02_P10GJ_ONE_HXT10_3D_ONLY.cmd"}
MAX_MSH_BYTES=128*1024**2
MAX_LOG_BYTES=8*1024**2


def need(ok,why):
    if not ok:raise RuntimeError("P10GJ_STOP: "+why)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(2*1024*1024),b""):h.update(b)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write("\n")


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def source_gate():
    man=load(SOURCE)
    need(man.get("revision")==REV and man.get("parent_M0_msh_sha256")==M0_SHA
         and man.get("native_3d_max_attempts")==1
         and man.get("FEM_max_attempts")==0
         and set(man.get("files",{}))==PACK_FILES,
         "invalid source pin manifest")
    for name,expected in man["files"].items():
        p=HERE/name
        need(p.is_file() and sha(p)==expected,"missing/tampered release source: "+name)
    for name,expected in (("M0.geo",M0_GEO_SHA),
                          ("sphere_pore_B6_refined.geo",CAD_SHA),
                          ("M0_ROTATED.geo",ROT_M0_GEO_SHA),
                          ("sphere_pore_B6_refined_rotated.geo",ROT_CAD_SHA)):
        need(sha(HERE/name)==expected,"canonical/rotated GEO SHA mismatch: "+name)
    original=(HERE/"sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    rotated=(HERE/"sphere_pore_B6_refined_rotated.geo").read_text(encoding="utf-8")
    anchor="Sphere(3) = {poreCX,poreCY,poreCZ,r0};"
    rotate="Rotate { {1,0,0}, {poreCX,poreCY,poreCZ}, Pi/2 } { Volume{3}; }"
    need(rotated.replace(anchor+"\n"+rotate,anchor)==original,
         "not the same OCC sphere with only CAD-pole rotation")
    base=(HERE/"M0.geo").read_text(encoding="utf-8")
    rot=(HERE/"M0_ROTATED.geo").read_text(encoding="utf-8")
    need(rot.replace('Include "sphere_pore_B6_refined_rotated.geo";',
                     'Include "sphere_pore_B6_refined.geo";')==base,
         "C1 size field modified during rotation")
    driver=(HERE/GEO_FILES[-1]).read_text(encoding="utf-8")
    need('Include "M0_ROTATED.geo";' in driver
         and "Mesh.Algorithm3D=10;" in driver
         and "Mesh.MeshSizeFactor=0.9378887276834518;" in driver
         and "Mesh.ElementOrder=2;" in driver,
         "not pinned HXT10/scale/Tet10 driver")
    policy=load(POLICY)
    need(policy["revision"]=="P10GJ_R1_D027_PREREG_BEFORE_NATIVE_3D"
         and policy["required_sampled_detJ_positive_QP"]==[27,343,729]
         and policy["mandatory_global_Veff_ratio"]==[.8,.85]
         and policy["preregister_from_M0_before_3D"] is True
         and policy["disallow_autonomous_FEM"] is True,
         "D-027 policy tamper")
    b=load(BASELINE)
    need(b["canonical_M0_msh_sha256"]==M0_SHA
         and b["M0"]["nodes"]==11699 and b["M0"]["tet10"]==7992
         and b["levels"]["7"]["qp_per_tet"]==343
         and b["levels"]["9"]["qp_per_tet"]==729,
         "independent archived M0 baseline mismatch")
    return policy


def profile_marker():
    appdata=os.environ.get("LOCALAPPDATA","")
    need(appdata and Path(appdata).is_dir(),"LOCALAPPDATA missing")
    return Path(appdata)/"Stage3D07"/"P10GJ_ONE_HXT10_"/(M0_SHA[:20]+".json")


def local_marker():
    return RUNS/"P10GJ_LOCKS"/("M0_"+M0_SHA[:20]+".json")


def one_shot_free():
    need(not local_marker().exists() and not profile_marker().exists(),
         "P10GJ one HXT10 native attempt already consumed; never repeat")


def installed_gate():
    need(sys.platform=="win32","native mode requires Windows 11")
    need(PROJECT.drive.upper()=="G:" and MESHES.is_dir() and RUNS.is_dir(),
         "canonical G: Stage3D07 folders missing")
    need(GMSH.is_file(),"Gmsh 4.15.2 executable missing")
    for name,expected in (("M0.msh",M0_SHA),("M0.geo",M0_GEO_SHA),
                          ("sphere_pore_B6_refined.geo",CAD_SHA)):
        need((MESHES/name).is_file() and sha(MESHES/name)==expected,
             "canonical user M0/CAD mismatch: "+name)
    p=subprocess.run([str(GMSH),"-version"],cwd=HERE,stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     timeout=15,check=False)
    version=p.stdout.decode("utf-8",errors="replace").strip()
    need(p.returncode==0 and "4.15.2" in version,"wrong native Gmsh version")
    return {"gmsh_version":version,"gmsh_exe_sha256":sha(GMSH),
            "M0_msh_sha256":M0_SHA,"source_pin_sha256":sha(SOURCE),
            "policy_sha256":sha(POLICY),"baseline_sha256":sha(BASELINE)}


def copy_geos(folder):
    result={}
    for name in GEO_FILES:
        source=HERE/name;target=folder/name
        with source.open("rb") as a,target.open("xb") as b:
            shutil.copyfileobj(a,b,1<<20)
        result[name]=sha(target)
        need(result[name]==sha(source),"GEO binary copy changed: "+name)
    return result


def value_gate(policy,m0qa,m0extra):
    q=policy
    def lim(k,actual):
        p=q[k]
        factor=p.get("M0_factor",p.get("M0_min_factor",p.get("M0_max_factor")))
        need(factor is not None,"threshold policy factor missing: "+k)
        return max(p["floor"],factor*actual)
    all_adj=m0qa["adjacent_face_size_jump_all"]
    polar_adj=m0qa["adjacent_face_size_jump_near_polar"]
    need(all_adj["count"]>0 and polar_adj["count"]>0,"M0 adjacent QA unavailable")
    p={
      "mean_ratio_min_floor":lim("tet10_corner_mean_ratio_q_min_policy",m0extra["mean_ratio_min"]),
      "mean_ratio_p01_floor":q["tet10_corner_mean_ratio_p01_M0_factor"]*m0extra["mean_ratio_p01"],
      "near_polar_mean_ratio_p05_floor":q["tet10_near_polar_mean_ratio_p05_M0_factor"]*m0extra["near_polar_mean_ratio_p05"],
      "max_27qp_detj_ratio":lim("tet10_27qp_max_element_detJ_ratio_policy",m0qa["max_element_qp_detj_ratio"]),
      "adj_all_p95_max":lim("adjacent_all_p95_policy",all_adj["p95"]),
      "adj_all_p99_max":lim("adjacent_all_p99_policy",all_adj["p99"]),
      "adj_all_max_max":lim("adjacent_all_max_policy",all_adj["maximum"]),
      "adj_near_p95_max":lim("adjacent_near_polar_p95_policy",polar_adj["p95"]),
      "adj_near_p99_max":lim("adjacent_near_polar_p99_policy",polar_adj["p99"]),
    }
    return p


def preregister(policy,installed):
    q27=audit27(MESHES/"M0.msh")
    qextra=audit_extra(MESHES/"M0.msh")
    b=load(BASELINE)
    need(q27["mesh_sha256"]==M0_SHA and qextra["tet10"]==b["M0"]["tet10"]
         and qextra["nodes"]==b["M0"]["nodes"],"M0 baseline raw mismatch")
    need(q27["geometry_gate"]=="PASS_27QP_DIAGNOSTIC"
         and q27["minimum_curved_detj"]>0
         and q27["minimum_corner_detj"]>0,"M0 curved geometry baseline failed")
    thresholds=value_gate(policy,q27,qextra)
    return {"revision":REV,"status":"P10GJ_D027_GATES_FROZEN_BEFORE_M1_3D",
            "time_utc":datetime.now(timezone.utc).isoformat(),
            "M0_msh_sha256":M0_SHA,"installed":installed,
            "fixed_policy":policy,"numerical_thresholds_from_M0":thresholds,
            "M0_27QP":q27,"M0_extra":qextra,
            "M0_preexisting_343_729QP_baseline_SHA256":sha(BASELINE),
            "native_new_3d_attempts":0,"FEM_attempts":0}


def parse_only(folder):
    geo=folder/GEO_FILES[-1]
    cmd=[str(GMSH),str(geo),"-parse_and_exit","-nopopup","-nt","2"]
    r=subprocess.run(cmd,cwd=folder,stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     timeout=45,check=False)
    text=r.stdout[:4*1024**2].decode("utf-8",errors="replace")
    log=folder/"P10GJ_NATIVE_PARSE_ONLY.log"
    log.write_text(text,encoding="utf-8")
    need(r.returncode==0 and not re.search(r"\bError\s*:",text),
         "native parse-only HXT10 GEO failed")
    return {"exit":r.returncode,"log_sha256":sha(log),"command":cmd}


def make_evidence(folder,outname,*,mesh=None):
    target=folder/outname
    with zipfile.ZipFile(target,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(folder.iterdir()):
            if f.is_file() and f!=target and f.stat().st_size<=MAX_MSH_BYTES:
                z.write(f,f.name)
        z.write(SOURCE,SOURCE.name)
        z.write(POLICY,POLICY.name)
    need(target.stat().st_size<=144*1024**2,"evidence exceeds 144MiB")
    print("SEND THIS FILE:",target,flush=True)
    return target


def preflight():
    policy=source_gate();installed=installed_gate();one_shot_free()
    folder=RUNS/("P10GJ_PREFLIGHT_"+timestamp());folder.mkdir(exist_ok=False)
    report={"status":"P10GJ_PREFLIGHT_STOP_NO_3D_NO_FEM",
            "native_new_3d_attempts":0,"FEM_attempts":0}
    try:
        copied=copy_geos(folder)
        frozen=preregister(policy,installed)
        gates=folder/"P10GJ_D027_FROZEN_GATES.json"
        write_new(gates,frozen)
        parsed=parse_only(folder)
        report.update({"status":"P10GJ_PREFLIGHT_PASS_GATES_FROZEN_NO_3D",
                       "copied_geo_sha256":copied,"pre_registered_gate_sha256":sha(gates),
                       "native_parse":parsed})
        proof={"revision":REV,"status":report["status"],
               "time_utc":datetime.now(timezone.utc).isoformat(),
               "preflight_run":str(folder),"source_pin_sha256":sha(SOURCE),
               "M0_msh_sha256":M0_SHA,"gmsh_exe_sha256":installed["gmsh_exe_sha256"],
               "policy_sha256":sha(POLICY),"frozen_gates_sha256":sha(gates),
               "parse_log_sha256":parsed["log_sha256"],
               "candidate_geo_sha256":copied[GEO_FILES[-1]],
               "native_new_3d_attempts":0,"FEM_attempts":0}
        PROOF.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("P10GJ_PREFLIGHT_PASS_GATES_FROZEN_NO_3D",flush=True)
        result=0
    except BaseException as exc:
        report["error"]=repr(exc)
        (folder/"P10GJ_PREFLIGHT_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
        result=2
    write_new(folder/"P10GJ_PREFLIGHT_REPORT.json",report)
    make_evidence(folder,"P10GJ_PREFLIGHT_EVIDENCE.zip")
    return result


def proof_gate(installed):
    need(PROOF.is_file(),"run 01 first")
    proof=load(PROOF)
    need(proof.get("revision")==REV and proof.get("status")==
         "P10GJ_PREFLIGHT_PASS_GATES_FROZEN_NO_3D"
         and proof.get("source_pin_sha256")==sha(SOURCE)
         and proof.get("M0_msh_sha256")==M0_SHA
         and proof.get("gmsh_exe_sha256")==installed["gmsh_exe_sha256"]
         and proof.get("policy_sha256")==sha(POLICY)
         and proof.get("candidate_geo_sha256")==sha(HERE/GEO_FILES[-1])
         and proof.get("native_new_3d_attempts")==0,
         "preflight proof not pinned")
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(proof["time_utc"])).total_seconds()
    need(0<=age<=24*3600,"preflight older than 24h")
    folder=Path(proof["preflight_run"])
    gates=folder/"P10GJ_D027_FROZEN_GATES.json"
    log=folder/"P10GJ_NATIVE_PARSE_ONLY.log"
    need(gates.is_file() and sha(gates)==proof["frozen_gates_sha256"]
         and log.is_file() and sha(log)==proof["parse_log_sha256"],
         "frozen gates/native parse evidence altered")
    registered=load(gates)
    need(registered["status"]=="P10GJ_D027_GATES_FROZEN_BEFORE_M1_3D"
         and registered["native_new_3d_attempts"]==0
         and registered["M0_msh_sha256"]==M0_SHA,
         "incomplete preregistration")
    return proof,registered


def candidate_checks(qa,x,registered):
    g=registered["fixed_policy"];t=registered["numerical_thresholds_from_M0"]
    old=registered["M0_27QP"]
    ratio=(qa["qp_integrated_volume_m3"]/qa["tet10"])/(
           old["qp_integrated_volume_m3"]/old["tet10"])
    adj=qa["adjacent_face_size_jump_all"]
    near=qa["adjacent_face_size_jump_near_polar"]
    checks={
      "27qp_detJ_and_corner_positive":qa["nonpositive_samples"]==0 and
         qa["minimum_curved_detj"]>0 and qa["minimum_corner_detj"]>0,
      "CAD_total_volume":abs(qa["qp_integrated_volume_m3"]/(.06*.06*.05-4*math.pi*.001**3/3)-1)
         <=g["required_cad_volume_rel_error_max"],
      "global_mean_Veff_ratio_27qp_preliminary":g["mandatory_global_Veff_ratio"][0]
         <=ratio<=g["mandatory_global_Veff_ratio"][1],
      "physical_tags_and_surface_closure":x["physical_tags"]==list(range(1,10)) and
         x["pore"]["closed_euler"]==2 and x["B6"]["closed_euler"]==2,
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
      "tet_curved_detJ_variation":qa["max_element_qp_detj_ratio"]<=t["max_27qp_detj_ratio"],
      "adj_all_p95":adj["p95"]<=t["adj_all_p95_max"],
      "adj_all_p99":adj["p99"]<=t["adj_all_p99_max"],
      "adj_all_max":adj["maximum"]<=t["adj_all_max_max"],
      "adj_near_p95":near["count"]>0 and near["p95"]<=t["adj_near_p95_max"],
      "adj_near_p99":near["count"]>0 and near["p99"]<=t["adj_near_p99_max"],
    }
    return {"global_Veff_ratio_27qp_preliminary":ratio,"checks":checks,
            "27qp_preliminary_all_pass":all(checks.values()),
            "final_343_729_and_macro_go":"PENDING_INDEPENDENT_REVIEW",
            "legacy_strict_18_of_18":"PENDING_INDEPENDENT_DIAGNOSTIC"}


def run_once():
    policy=source_gate();installed=installed_gate();one_shot_free()
    proof,registered=proof_gate(installed)
    folder=RUNS/("P10GJ_M1_ROTATED_HXT10_"+timestamp())
    folder.mkdir(exist_ok=False)
    marker={"revision":REV,"M0_sha256":M0_SHA,"time_utc":datetime.now(timezone.utc).isoformat(),
            "frozen_gates_sha256":proof["frozen_gates_sha256"],
            "native_3d_max_attempts":1,"FEM_max_attempts":0}
    # Permanent exclusive markers BEFORE any native Gmsh -3.
    write_new(local_marker(),marker)
    write_new(profile_marker(),marker)
    mesh=folder/"P10GJ_M1_ROTATED_CANDIDATE.msh"
    log=folder/"P10GJ_GMSH_3D.log"
    report={"revision":REV,"status":"P10GJ_STOP_NO_FEM",
            "parent_M0_sha256":M0_SHA,"preflight_proof_sha256":sha(PROOF),
            "frozen_gates_sha256":proof["frozen_gates_sha256"],
            "native_3d_attempts":0,"FEM_attempts":0}
    result=2
    try:
        copy_geos(folder)
        cmd=[str(GMSH),str(folder/GEO_FILES[-1]),"-3","-nopopup","-nt","2",
             "-format","msh2","-o",str(mesh)]
        need(cmd.count("-3")==1 and "-save_all" not in cmd,"forbidden native mesh command")
        print("P10GJ ONE NATIVE HXT10 -3: max900s/private8GiB/2threads. NO FEM",flush=True)
        report["native_3d_attempts"]=1
        report["command"]=cmd
        native=capped_process(cmd,cwd=folder,log=log,wall_s=900,
                              memory_gib=8,output_dir=folder,output_gib=2)
        report["native"]=native
        need(native["native_exit_code"]==0 and not native["stop_reason"],
             "native Gmsh/resource STOP")
        need(mesh.is_file() and 0<mesh.stat().st_size<=MAX_MSH_BYTES,
             "missing/oversized MSH")
        need(log.is_file() and log.stat().st_size<=MAX_LOG_BYTES,
             "missing/oversized Gmsh log")
        lines=log.read_text(encoding="utf-8",errors="replace")
        need("Done meshing 3D" in lines and not re.search(r"\bError\s*:",lines),
             "native Gmsh completion/error log")
        report["mesh_sha256"]=sha(mesh)
        qa=audit27(mesh);x=audit_extra(mesh)
        report["qa27"]=qa
        report["qa_extra"]=x
        status=candidate_checks(qa,x,registered)
        report["D027_preliminary_27QP"]=status
        report["status"]=("P10GJ_NATIVE_27QP_PRELIM_PASS_343_729_PENDING_NO_FEM"
                          if status["27qp_preliminary_all_pass"] else
                          "P10GJ_27QP_GATE_STOP_NO_FEM")
        result=0 if status["27qp_preliminary_all_pass"] else 2
    except BaseException as exc:
        report["status"]="P10GJ_STOP_NO_FEM"
        report["error"]=repr(exc)
        (folder/"P10GJ_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        write_new(folder/"P10GJ_M1_MANIFEST.json",report)
        # Preserve the numerical hard-gate freeze as part of candidate evidence.
        gates=Path(proof["preflight_run"])/"P10GJ_D027_FROZEN_GATES.json"
        shutil.copyfile(gates,folder/gates.name)
        make_evidence(folder,"P10GJ_M1_HXT10_EVIDENCE.zip",mesh=mesh)
    print("P10GJ_RESULT",report["status"],flush=True)
    print("NO FEM. NO APPROVAL. SEND ONE EVIDENCE ZIP FOR 343/729QP REVIEW.",flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    ex=parser.add_mutually_exclusive_group(required=True)
    ex.add_argument("--selftest",action="store_true")
    ex.add_argument("--preflight",action="store_true")
    ex.add_argument("--one-hxt10",action="store_true")
    args=parser.parse_args()
    if args.selftest:
        source_gate()
        print("P10GJ_SOURCE_AND_PRE_REGISTERED_POLICY_PASS_NO_GMSH_NO_FEM",flush=True)
        return 0
    if args.preflight:return preflight()
    return run_once()


if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print("P10GJ_STOP:",repr(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
