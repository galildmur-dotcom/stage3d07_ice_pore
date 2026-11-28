#!/usr/bin/env python3
"""P10GT: one guarded HXT Tet10 mesh-only candidate from P10GR best surface."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
PROJECT=Path(r"G:\ildar\Stage3D07")
MESHES=PROJECT/"meshes"
RUNS=PROJECT/"LOCAL_RUNS"
GMSH=Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
REV="P10GT_R1_ONE_HXT10_ALGO6_A09_MU20_MESH_ONLY"
PARENT=HERE/"P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip"
PARENT_SHA="5bc94e2939f6a96c1c2e7b9a77a721e3b1b8c02cbc2eb9342e80f53717f72909"
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
GMSH_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
FROZEN_SHA="2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea"
FROZEN=HERE/"P10GJ_D027_FROZEN_GATES.json"
BASELINE=HERE/"P10GJ_M0_QP_BASELINE.json"
RUNTIME_FILES={
 "P10FN_common.py":"__PIN_COMMON__",
 "P10FN_mesh_qa.py":"__PIN_QA__",
 "P10CK_curved_qp_audit.py":"__PIN_QP__",
 "P10GJ_mesh_extra.py":"__PIN_EXTRA__",
 "p10gi_independent_surface_audit.py":"__PIN_SURFACE__",
 "P10GL_one_hxt10.py":"__PIN_LEGACY__",
}
CASE="ALGO6_A09_MU20"
PROOF=HERE/"P10GT_PREFLIGHT_PROOF.json"
RESULT=HERE/"P10GT_02_RESULT.txt"
MAX_MSH=128*1024**2
MAX_LOG=8*1024**2


def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def need(b,msg):
    if not b:raise RuntimeError("P10GT_STOP: "+msg)
def utc():return datetime.now(timezone.utc)


def source_files():
    need(PARENT.is_file() and file_sha(PARENT)==PARENT_SHA,"P10GR source ZIP SHA mismatch")
    with zipfile.ZipFile(PARENT) as z:
        need(z.testzip() is None,"parent CRC error")
        p=z.read("P10GP_R1_SURFACE_SOURCE_ONLY.zip")
        need(sha(p)=="236defb377103ef45e8ac193264fac8213290c7d00e02fc1025e53c9f700cc3a",
             "original source-only field ZIP mismatch")
        src=z.read("P10GR_scan.py").decode("utf-8")
        need("ALPHAS = (0.03, 0.06, 0.09)" in src and
             "MU_ENDS = (-0.7, -0.5, -0.2)" in src,"parent DOE contract changed")
    with zipfile.ZipFile(__import__('io').BytesIO(p)) as z:
        need(z.testzip() is None,"nested source CRC")
        manifest=json.loads(z.read("P10GP_SOURCE_MANIFEST.json"))
        need(manifest["revision"]=="P10GP_R1_SOURCE_ONLY","nested source revision changed")
        driver=z.read("B_SELF_CONTAINED_C1_SOUTH/P10GP_SURFACE.geo").decode("utf-8")
        m0=z.read("B_SELF_CONTAINED_C1_SOUTH/M0_ROTATED.geo")
        cad=z.read("B_SELF_CONTAINED_C1_SOUTH/sphere_pore_B6_refined_rotated.geo")
    old="min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.2))"
    new="min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.60000000000000009))"
    need(driver.count(old)==3 and driver.count("1-0.06*")==1,
         "legacy angle/alpha syntax changed")
    driver=driver.replace(old,new).replace("1-0.06*","1-0.089999999999999997*")
    driver=driver.replace("Mesh.Algorithm = 5; // Delaunay surface; Tri6 with order 2",
                          "Mesh.Algorithm = 6; // Frontal-Delaunay surface for HXT10 3D")
    driver=driver.replace("// P10GO SOURCE-ONLY surface candidate, never 2D/3D/FEM.",
                          "// P10GT single 3D HXT10 mesh-only; FEM forbidden.")
    need(driver.count("Mesh.Algorithm3D = 10;")==1 and
         driver.count("Mesh.MeshSizeFactor = 0.9378887276834518;")==1 and
         "Background Field = 7;" in driver and
         "Mesh.Algorithm = 6;" in driver and
         "-parse_and_exit" not in driver,"HXT10/source policy changed")
    return {"P10GT_HXT10.geo":driver.encode("utf-8"),"M0_ROTATED.geo":m0,
            "sphere_pore_B6_refined_rotated.geo":cad}


def modules():
    for name,digest in RUNTIME_FILES.items():
        need((HERE/name).is_file() and file_sha(HERE/name)==digest,
             "runtime helper hash mismatch: "+name)
    need(file_sha(FROZEN)==FROZEN_SHA,"frozen D027 source changed")
    sys.path.insert(0,str(HERE))
    from P10FN_common import capped_process
    from P10FN_mesh_qa import audit as qa27
    from P10GJ_mesh_extra import audit as extra
    spec=importlib.util.spec_from_file_location("p10gt_p10gl_readonly",HERE/"P10GL_one_hxt10.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return capped_process,qa27,extra,module.candidate_checks


def m0_gate():
    old=json.loads(FROZEN.read_text(encoding="utf-8"))
    b=json.loads(BASELINE.read_text(encoding="utf-8"))
    need(old["status"]=="P10GJ_D027_GATES_FROZEN_BEFORE_M1_3D" and
         old["M0_msh_sha256"]==M0_SHA and
         old["fixed_policy"]["mandatory_global_Veff_ratio"]==[.8,.85] and
         old["fixed_policy"]["required_sampled_detJ_positive_QP"]==[27,343,729] and
         old["fixed_policy"]["macro_QP_effective_Veff_assessment"]
            ["populated_near_polar_d_le_0p5mm_ratio_max"]==.98,
         "D027 numerical policy changed")
    need(b["canonical_M0_msh_sha256"]==M0_SHA and b["M0"]["tet10"]==7992,
         "M0 baseline changed")
    return old


def installed():
    need(sys.platform=="win32","native mode only on user's Windows PC")
    need(MESHES.is_dir() and RUNS.is_dir(),"existing project dirs missing")
    need(GMSH.is_file() and file_sha(GMSH)==GMSH_SHA,"Gmsh EXE SHA mismatch")
    need((MESHES/"M0.msh").is_file() and file_sha(MESHES/"M0.msh")==M0_SHA,
         "M0 mesh SHA mismatch")
    p=subprocess.run([str(GMSH),"-version"],capture_output=True,text=True,timeout=15)
    need(p.returncode==0 and "4.15.2" in p.stdout,"Gmsh version mismatch")
    return {"M0_sha256":M0_SHA,"Gmsh_sha256":GMSH_SHA,"P10GR_source_sha256":PARENT_SHA}


def markers():
    app=os.environ.get("LOCALAPPDATA","")
    need(app and Path(app).is_dir(),"LOCALAPPDATA unavailable")
    return (RUNS/"P10GT_LOCKS"/(M0_SHA[:24]+".json"),
            Path(app)/"Stage3D07"/"P10GT_HXT10"/(M0_SHA[:24]+".json"))


def free():need(all(not p.exists() for p in markers()),"one-shot already consumed, no retry")


def write_files(folder,files):
    for name,data in files.items():
        with (folder/name).open("xb") as out:out.write(data)
        need(file_sha(folder/name)==sha(data),"GEO bytes changed")


def dump(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def evidence(folder):
    target=folder/"P10GT_HXT10_EVIDENCE.zip"
    with zipfile.ZipFile(target,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(folder.iterdir()):
            if p.is_file() and p!=target and p.suffix.lower() in (".msh",".geo",".log",".txt",".json"):
                z.write(p,p.name)
        z.write(FROZEN,FROZEN.name)
        z.write(BASELINE,BASELINE.name)
    need(target.stat().st_size<=144*1024**2 and zipfile.ZipFile(target).testzip() is None,
         "evidence size/CRC")
    print("P10GT_SEND_ONE_EVIDENCE",target,flush=True)
    return target


def preflight():
    files=source_files();modules();m0_gate();ins=installed();free()
    folder=RUNS/("P10GT_PREFLIGHT_"+utc().strftime("%Y%m%d_%H%M%S_%f"));folder.mkdir(exist_ok=False)
    write_files(folder,files)
    p=subprocess.run([str(GMSH),str(folder/"P10GT_HXT10.geo"),"-parse_and_exit","-nopopup","-nt","2"],
                     cwd=folder,capture_output=True,timeout=45)
    log=p.stdout+p.stderr;(folder/"P10GT_PARSE.log").write_bytes(log)
    need(p.returncode==0 and b"Done reading" in log and not re.search(rb"\bError\s*:",log),
         "native Gmsh parse-only STOP")
    proof={"revision":REV,"time":utc().isoformat(),"installed":ins,
           "generated_sha256":{name:sha(data) for name,data in files.items()},
           "frozen_sha256":FROZEN_SHA,"parse_log_sha256":sha(log),"native_3d":0,"FEM":0}
    dump(PROOF,proof);dump(folder/"P10GT_PREFLIGHT.json",proof)
    evidence(folder)
    print("P10GT_PREFLIGHT_PASS_NO_MESH",flush=True)


def run_once():
    files=source_files();capped,qa27,extra,checks=modules();old=m0_gate();ins=installed();free()
    need(PROOF.is_file(),"01 preflight missing")
    proof=json.loads(PROOF.read_text(encoding="utf-8"))
    age=(utc()-datetime.fromisoformat(proof["time"])).total_seconds()
    need(proof["revision"]==REV and proof["installed"]==ins and
         proof["generated_sha256"]=={name:sha(data) for name,data in files.items()} and
         proof["frozen_sha256"]==FROZEN_SHA and 0<=age<=86400,"preflight stale/changed")
    folder=RUNS/("P10GT_HXT10_"+utc().strftime("%Y%m%d_%H%M%S_%f"));folder.mkdir(exist_ok=False)
    write_files(folder,files)
    for marker in markers():
        marker.parent.mkdir(parents=True,exist_ok=True)
        with marker.open("x",encoding="utf-8") as out:
            json.dump({"revision":REV,"created":utc().isoformat(),"native_3d_max":1},out)
    report={"revision":REV,"status":"STOP","source_sha256":PARENT_SHA,"installed":ins,
            "native_3d_attempts":0,"FEM_attempts":0}
    try:
        msh=folder/"P10GT_HXT10.msh";log=folder/"P10GT_GMSH_3D.log"
        cmd=[str(GMSH),str(folder/"P10GT_HXT10.geo"),"-3","-nopopup","-nt","2",
             "-format","msh2","-o",str(msh)]
        report["native_3d_attempts"]=1
        print("P10GT ONE native HXT10 -3; max 900s/8GiB; no FEM",flush=True)
        native=capped(cmd,cwd=folder,log=log,wall_s=900,memory_gib=8,
                      output_dir=folder,output_gib=1)
        report["native"]=native
        need(native["native_exit_code"]==0 and not native["stop_reason"],"native Gmsh/resource STOP")
        need(msh.is_file() and 0<msh.stat().st_size<=MAX_MSH and
             log.is_file() and log.stat().st_size<=MAX_LOG,"MSH/log size STOP")
        info=log.read_text(encoding="utf-8",errors="replace")
        need("Done meshing 3D" in info and not re.search(r"\bError\s*:",info),
             "native 3D completion STOP")
        report["mesh_sha256"]=file_sha(msh)
        report["log_sha256"]=file_sha(log)
        q=qa27(msh);x=extra(msh)
        report["qa27"]=q;report["qa_extra"]=x
        report["D027_27qp_preliminary"]=checks(q,x,old)
        report["status"]="NATIVE_3D_COMPLETED_27QP_PRELIM_PENDING_INDEPENDENT_343_729"
    except Exception as error:
        report["error"]=repr(error)
        (folder/"P10GT_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        dump(folder/"P10GT_MANIFEST.json",report)
        saved=evidence(folder)
        RESULT.write_text("P10GT_RESULT="+report["status"]+"\nEVIDENCE="+str(saved)+
                          "\nDO_NOT_REPEAT_02=YES\n",encoding="utf-8")
    return 0 if report["status"].startswith("NATIVE_3D_COMPLETED") else 2


def main():
    need(len(sys.argv)==2,"use --selftest/--preflight/--one-3d")
    if sys.argv[1]=="--selftest":
        src=source_files();modules();m0_gate()
        need(len(src)==3,"GEO file count")
        print("P10GT_HXT10_SOURCE_FROZEN_GATE_PASS_NO_NATIVE",flush=True);return 0
    if sys.argv[1]=="--preflight":preflight();return 0
    if sys.argv[1]=="--one-3d":return run_once()
    need(False,"unknown mode")

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print("P10GT_STOP",repr(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
