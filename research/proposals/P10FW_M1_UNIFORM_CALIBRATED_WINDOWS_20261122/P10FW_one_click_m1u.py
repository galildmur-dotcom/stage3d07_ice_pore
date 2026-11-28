#!/usr/bin/env python3
"""P10FW: bounded, noninteractive one-shot M1U M0-based uniform-target mesh.

No physics; real 15-20% all-volume criterion needs independent 729QP review.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile

from P10FN_common import capped_process
from P10FN_mesh_qa import audit
from P10FW_uniform_math import generated_geo, math_selftest

HERE=Path(__file__).resolve().parent
ROOT=Path(r"G:\ildar\Stage3D07")
MESHES=ROOT/"meshes"
RUNS=ROOT/"LOCAL_RUNS"
GMSH=Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
REV="P10FW_R1_18_ZONE_C1_UNIFORM_M1U_NO_FEM"
SOURCE_PIN=HERE/"P10FW_SOURCE_SHA256.json"
PROOF=HERE/"P10FW_PREFLIGHT_PASS.json"
NAME="M1U_CANDIDATE"
M0="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M0G="ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
M1="f281d253571db095b90790326f503dfa3f6fe3a1dc5cb5c904fca2787dfe4275"
M1G="968ef2ed3f64160d51d1983ead31216758d164fa665fa7e6a9044f8fc04d64e8"
CAD="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"


def need(value, why):
    if not value:
        raise RuntimeError("P10FW_STOP: "+why)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().strftime("%Y%m%d_%H%M%S_%f")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path,obj,new=True):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x" if new else "w",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write("\n")


def package_gate():
    p=load(SOURCE_PIN)
    expected={
        "P10FW_one_click_m1u.py","P10FW_uniform_math.py",
        "01_P10FW_SAFE_PREFLIGHT_ONLY.cmd",
        "02_P10FW_ONE_M1U_3D_ONLY.cmd",
        "README_P10FW_RU.md",
        "P10FN_common.py","P10FN_mesh_qa.py","P10CK_curved_qp_audit.py",
        "M0.geo","sphere_pore_B6_refined.geo",
        "P10FW_REAL_M0_M1_SIGNED_18_ZONE_729QP.json"
    }
    need(p.get("revision")==REV and
         p.get("parent_M0_msh_sha256")==M0 and
         p.get("parent_M0_geo_sha256")==M0G and
         p.get("original_failed_M1_msh_sha256")==M1 and
         p.get("original_failed_M1_geo_sha256")==M1G and
         p.get("candidate_name")==NAME and
         p.get("native_3d_max_attempts")==1 and
         p.get("FEM_max_attempts")==0 and
         set(p.get("files",{}))==expected,
         "source SHA manifest contract mismatch")
    for name,digest in p["files"].items():
        need((HERE/name).is_file() and sha(HERE/name)==digest,
             "tampered/missing package source: "+name)
    need(sha(HERE/"M0.geo")==M0G and
         sha(HERE/"sphere_pore_B6_refined.geo")==CAD,
         "bundled canonical original geometry SHA changed")


def profile_marker():
    appdata=os.environ.get("LOCALAPPDATA","")
    need(bool(appdata) and Path(appdata).is_dir(),
         "LOCALAPPDATA missing; cannot ensure cross-extraction one-shot")
    return Path(appdata)/"Stage3D07"/("P10FW_R1_M1U_"+M0+".json")


def local_marker():
    return RUNS/"P10FW_LOCKS"/("M1U_FROM_"+M0[:16]+".json")


def installed_gate():
    need(sys.platform=="win32","Windows 11 required for native mode (selftest is cross-platform)")
    need(GMSH.is_file(),"Gmsh 4.15.2 executable not found")
    need(MESHES.is_dir() and RUNS.is_dir(),
         "existing G: Stage3D07/meshes and LOCAL_RUNS required")
    for name,digest in (("M0.msh",M0),("M0.geo",M0G),("M1.msh",M1),
                        ("M1.geo",M1G),("sphere_pore_B6_refined.geo",CAD)):
        file=MESHES/name
        need(file.is_file() and sha(file)==digest,
             "original missing or SHA changed: "+name)
    for ext in (".geo",".msh"):
        need(not (MESHES/(NAME+ext)).exists(),
             "candidate M1U already exists; NEVER overwrite")
    need(not local_marker().exists() and not profile_marker().exists(),
         "this M1U native one-shot has already been consumed")


def native_parse(geo, folder):
    version=subprocess.run([str(GMSH),"-version"],cwd=folder,
                           stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,timeout=15,check=False)
    need(version.returncode==0 and
         "4.15.2" in version.stdout.decode("utf-8",errors="replace"),
         "Gmsh native version differs from 4.15.2")
    with tempfile.TemporaryDirectory(prefix="P10FW_PARSE_",dir=folder) as tmp:
        temp=Path(tmp)
        (temp/(NAME+".geo")).write_text(geo,encoding="utf-8")
        for name in ("M0.geo","sphere_pore_B6_refined.geo"):
            shutil.copy2(HERE/name,temp/name)
        cmd=[str(GMSH),str(temp/(NAME+".geo")),
             "-parse_and_exit","-nopopup","-nt","2"]
        result=subprocess.run(cmd,cwd=temp,stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              timeout=45,check=False)
        log=result.stdout[:2*1024*1024].decode("utf-8",errors="replace")
        (folder/"P10FW_GMSH_PARSE_ONLY.txt").write_text(log,encoding="utf-8")
        need(result.returncode==0 and "Error" not in log,
             "Gmsh 4.15.2 native GEO parse failure")
        return {"version":"4.15.2","parse_exit":result.returncode,
                "native_3d_attempts":0,"parse_log_bytes":len(result.stdout)}


def preflight():
    package_gate()
    geo,_,_,_,_=generated_geo()
    tests=math_selftest()
    installed_gate()
    folder=RUNS/("P10FW_PREFLIGHT_"+stamp())
    folder.mkdir()
    parse=native_parse(geo,folder)
    proof={"revision":REV,"status":"P10FW_PREFLIGHT_PASS_NO_3D_NO_FEM",
           "timestamp_utc":now().isoformat(),
           "parent_M0_msh_sha256":M0,"failed_M1_sha256":M1,
           "source_pin_sha256":sha(SOURCE_PIN),
           "candidate_geo_sha256":hashlib.sha256(geo.encode()).hexdigest(),
           "native_parse":parse,"source_math":tests}
    save(PROOF,proof,new=False)
    save(folder/"P10FW_PREFLIGHT_PASS.json",proof)
    (folder/"P10FW_M1U_SOURCE_ONLY.geo").write_text(geo,encoding="utf-8")
    print("P10FW_PREFLIGHT_PASS_NO_3D_NO_FEM",flush=True)
    print("ALL_VOLUME_TARGET_VEFF_0.80_TO_0.85; NOT YET VERIFIED ON NATIVE M1U",flush=True)
    print("NEXT: 02_P10FW_ONE_M1U_3D_ONLY.cmd",flush=True)
    return 0


def proof_gate(geo):
    need(PROOF.is_file(),"run 01_P10FW_SAFE_PREFLIGHT_ONLY.cmd first")
    p=load(PROOF)
    need(p.get("revision")==REV and
         p.get("status")=="P10FW_PREFLIGHT_PASS_NO_3D_NO_FEM" and
         p.get("parent_M0_msh_sha256")==M0 and
         p.get("failed_M1_sha256")==M1 and
         p.get("source_pin_sha256")==sha(SOURCE_PIN) and
         p.get("candidate_geo_sha256")==hashlib.sha256(geo.encode()).hexdigest(),
         "preflight not pinned to this source")
    age=(now()-datetime.fromisoformat(p["timestamp_utc"])).total_seconds()
    need(0<=age<=86400,"preflight expired; repeat safe 01 only")


def evidence(folder,geo_path,mesh_path):
    zip_path=folder/"P10FW_M1U_MESH_EVIDENCE.zip"
    artifacts={
        "P10FW_M1U_MANIFEST.json":folder/"P10FW_M1U_MANIFEST.json",
        "P10FW_GMSH_3D_LOG.txt":folder/"P10FW_GMSH_3D_LOG.txt",
        "P10FW_MESH_QA27.json":folder/"P10FW_MESH_QA27.json",
        "P10FW_STOP_TRACE.txt":folder/"P10FW_STOP_TRACE.txt",
        NAME+".geo":geo_path,
        "P10FW_SOURCE_SHA256.json":SOURCE_PIN,
        "P10FW_PREFLIGHT_PASS.json":PROOF,
        "P10FW_CALIBRATION.json":HERE/"P10FW_REAL_M0_M1_SIGNED_18_ZONE_729QP.json"
    }
    if mesh_path.is_file() and mesh_path.stat().st_size<=32*1024**2:
        artifacts[NAME+".msh"]=mesh_path
    with zipfile.ZipFile(zip_path,"x",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as out:
        for name,src in artifacts.items():
            if src.is_file():
                out.write(src,name)
    print("SEND THIS FILE:",zip_path,flush=True)


def run_one():
    package_gate()
    geo,_,_,_,_=generated_geo()
    math_selftest()
    installed_gate()
    proof_gate(geo)
    folder=RUNS/("P10FW_M1U_"+stamp())
    folder.mkdir()
    marker={"revision":REV,"M0_SHA":M0,"failed_M1_SHA":M1,
            "new_geo_SHA":hashlib.sha256(geo.encode()).hexdigest(),
            "time_utc":now().isoformat(),"FEM_attempts":0}
    # Exclusive persistent markers BEFORE the native 3D attempt.
    save(local_marker(),marker)
    save(profile_marker(),marker)
    geo_path=MESHES/(NAME+".geo")
    mesh_path=folder/(NAME+".msh")
    meta={"revision":REV,"status":"M1U_STOP_NO_FEM",
          "M0_SHA":M0,"failed_M1_SHA":M1,
          "M1U_uniform_actual_ratio_required":[.8,.85],
          "uniform_actual_target":.825,
          "source_field":"C1_18_zone_Gmsh_bias_compensation_for_uniform_actual_Veff",
          "physical_kappa_everywhere":1,
          "actual_729QP":"PENDING_INDEPENDENT_REVIEW",
          "native_3d_attempts":0,"FEM_attempts":0}
    result=2
    try:
        with geo_path.open("x",encoding="utf-8") as out:
            out.write(geo)
        cmd=[str(GMSH),str(geo_path),"-3","-nopopup","-nt","2",
             "-format","msh2","-o",str(mesh_path)]
        meta["command"]=cmd
        meta["native_3d_attempts"]=1
        print("P10FW ONE GMSH -3: 900s max, private8GiB, output2GiB, NO FEM",flush=True)
        limited=capped_process(cmd,cwd=MESHES,
                               log=folder/"P10FW_GMSH_3D_LOG.txt",
                               wall_s=900,memory_gib=8,output_dir=folder,
                               output_gib=2)
        meta.update(limited)
        need(limited["native_exit_code"]==0 and not limited["stop_reason"],
             "Gmsh native/resource failure")
        qa=audit(mesh_path)
        save(folder/"P10FW_MESH_QA27.json",qa)
        need(qa["nonpositive_samples"]==0 and qa["tet10"]>=1000,
             "curved27QP geometry FAIL")
        target=MESHES/(NAME+".msh")
        with mesh_path.open("rb") as src,target.open("xb") as dst:
            shutil.copyfileobj(src,dst,1<<20)
        need(sha(target)==qa["mesh_sha256"],"target copy SHA mismatch")
        meta["status"]="M1U_GEOMETRY27_PASS_UNIFORM_ALL_VOLUME_729QP_PENDING_NO_FEM"
        meta["mesh_sha256"]=qa["mesh_sha256"]
        meta["qa"]=qa
        result=0
    except BaseException as exc:
        meta["status"]="M1U_STOP_NO_FEM"
        meta["error"]=repr(exc)
        (folder/"P10FW_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        save(folder/"P10FW_M1U_MANIFEST.json",meta)
        evidence(folder,geo_path,mesh_path)
    print("P10FW_RESULT",meta["status"],flush=True)
    print("PHYSICS M1U NOT AUTHORIZED. Send evidence for all-volume independent 729QP.",flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--preflight",action="store_true")
    p.add_argument("--one-mesh",action="store_true")
    args=p.parse_args()
    need(sum((args.selftest,args.preflight,args.one_mesh))==1,
         "exactly one mode needed")
    if args.selftest:
        package_gate()
        print("P10FW_PACKAGE_SOURCE_SELFTEST_PASS",
              json.dumps(math_selftest())[:700],flush=True)
        return 0
    if args.preflight:
        return preflight()
    return run_one()


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,AssertionError,KeyError,subprocess.TimeoutExpired) as exc:
        print("P10FW_STOP:",str(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
