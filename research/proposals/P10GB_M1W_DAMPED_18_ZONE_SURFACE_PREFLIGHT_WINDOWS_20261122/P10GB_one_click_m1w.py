#!/usr/bin/env python3
"""P10GB R1: new damped C1 M1W with native 1D+2D-only surface preflight.

No physics; real 15-20% all-volume criterion needs independent 729QP review.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
import statistics

from P10FN_common import capped_process
from P10FN_mesh_qa import audit
from P10GB_adapt_math import generated_geo, math_selftest

HERE=Path(__file__).resolve().parent
ROOT=Path(r"G:\ildar\Stage3D07")
MESHES=ROOT/"meshes"
RUNS=ROOT/"LOCAL_RUNS"
GMSH=Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
REV="P10GB_R1_DAMPED_C1_18_SIGNED_ZONES_1D_2D_GATE_M1W_NO_FEM"
SOURCE_PIN=HERE/"P10GB_SOURCE_SHA256.json"
PROOF=HERE/"P10GB_PREFLIGHT_PASS.json"
NAME="M1W_CANDIDATE"
M0="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M0G="ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
M1="f281d253571db095b90790326f503dfa3f6fe3a1dc5cb5c904fca2787dfe4275"
M1G="968ef2ed3f64160d51d1983ead31216758d164fa665fa7e6a9044f8fc04d64e8"
M1V="c3f69d3d6f3d88333f2aec7a5aa13db535f9eed4e76ba6c29bed4b88fa31ea06"
M1VG="de15b2f1d6454f06cb2f53731936558288dce933afd1642aada82b42022886aa"
CAD="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"


def need(value, why):
    if not value:
        raise RuntimeError("P10GB_STOP: "+why)


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
        "P10GB_one_click_m1w.py","P10GB_adapt_math.py",
        "P10FX_uniform_math.py",
        "01_P10GB_PREFLIGHT_1D_2D_ONLY.cmd",
        "02_P10GB_ONE_M1W_3D_ONLY.cmd",
        "README_P10GB_RU.md",
        "P10FN_common.py","P10FN_mesh_qa.py","P10CK_curved_qp_audit.py",
        "M0.geo","sphere_pore_B6_refined.geo",
        "P10FX_REAL_M0_M1_SIGNED_18_ZONE_729QP.json",
        "P10GA_M0_M1V_SIGNED18_343_729QP.json"
    }
    need(p.get("revision")==REV and
         p.get("parent_M0_msh_sha256")==M0 and
         p.get("parent_M0_geo_sha256")==M0G and
         p.get("original_failed_M1_msh_sha256")==M1 and
         p.get("original_failed_M1_geo_sha256")==M1G and
         p.get("parent_M1V_msh_sha256")==M1V and
         p.get("parent_M1V_geo_sha256")==M1VG and
         p.get("candidate_name")==NAME and
         p.get("native_2d_preflight_required") is True and
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
    # New independent M1W attempt; tied to the accepted M0 and rejected M1V.
    return Path(appdata)/"Stage3D07"/("P10GB_R1_M1W_"+M0[:16]+"_"+M1V[:16]+".json")


def local_marker():
    return RUNS/"P10GB_LOCKS"/("M1W_FROM_"+M0[:16]+"_"+M1V[:16]+".json")


def installed_gate():
    need(sys.platform=="win32","Windows 11 required for native mode (selftest is cross-platform)")
    need(GMSH.is_file(),"Gmsh 4.15.2 executable not found")
    need(MESHES.is_dir() and RUNS.is_dir(),
         "existing G: Stage3D07/meshes and LOCAL_RUNS required")
    for name,digest in (("M0.msh",M0),("M0.geo",M0G),("M1.msh",M1),
                        ("M1.geo",M1G),("M1V_CANDIDATE.msh",M1V),
                        ("M1V_CANDIDATE.geo",M1VG),
                        ("sphere_pore_B6_refined.geo",CAD)):
        file=MESHES/name
        need(file.is_file() and sha(file)==digest,
             "original missing or SHA changed: "+name)
    for ext in (".geo",".msh"):
        need(not (MESHES/(NAME+ext)).exists(),
             "candidate M1W already exists; NEVER overwrite")
    need(not local_marker().exists() and not profile_marker().exists(),
         "this M1W native one-shot has already been consumed")


def probe_surface_tri6(path):
    """Read only the 2D probe MSH2, specifically physical pore surface tag8."""
    nodes={}; tris=[]
    with path.open("r",encoding="ascii") as f:
        for line in f:
            if line.strip()=="$Nodes":
                count=int(next(f))
                for _ in range(count):
                    row=next(f).split()
                    need(len(row)==4,"2D MSH node width")
                    nodes[int(row[0])]=tuple(float(x) for x in row[1:])
            elif line.strip()=="$Elements":
                count=int(next(f))
                for _ in range(count):
                    row=list(map(int,next(f).split()))
                    if row[1]==9 and row[2]>=1 and row[3]==8:
                        need(len(row[3+row[2]:])==6,"2D pore Tri6 connectivity")
                        tris.append(row[3+row[2]:])
    need(bool(nodes) and bool(tris),"no physical pore Tri6 in 2D preflight")
    north=[];south=[];middle=[]
    for ids in tris:
        p=[nodes[i] for i in ids[:3]]
        cx=sum(v[0] for v in p)/3
        cy=sum(v[1] for v in p)/3
        cz=sum(v[2] for v in p)/3-.03
        rho=math.sqrt(cx*cx+cy*cy+cz*cz)
        need(rho>0,"zero-radius pore centroid")
        mu=cz/rho
        edge=statistics.median([math.dist(p[0],p[1]),math.dist(p[1],p[2]),
                                math.dist(p[2],p[0])])*1000
        (north if mu>=.8 else south if mu<=-.8 else middle).append(edge)
    return {"pore_tri6":len(tris),"north_polar_tri6":len(north),
            "south_polar_tri6":len(south),"other_pore_tri6":len(middle),
            "north_median_corner_edge_mm":statistics.median(north) if north else None,
            "south_median_corner_edge_mm":statistics.median(south) if south else None}


def native_parse(geo, folder):
    version=subprocess.run([str(GMSH),"-version"],cwd=folder,
                           stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,timeout=15,check=False)
    need(version.returncode==0 and
         "4.15.2" in version.stdout.decode("utf-8",errors="replace"),
         "Gmsh native version differs from 4.15.2")
    with tempfile.TemporaryDirectory(prefix="P10GB_PARSE_",dir=folder) as tmp:
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
        (folder/"P10GB_GMSH_PARSE_ONLY.txt").write_text(log,encoding="utf-8")
        need(result.returncode==0 and "Error" not in log,
             "Gmsh 4.15.2 native GEO parse failure")
        # A parse-only invocation skips Gmsh's on-demand MathEval compilation.
        # The previous P10FW -3 attempt failed there with an x--0.8 token.
        # This 1D-only probe triggers the real native MathEx evaluator, safely
        # and before consuming the one-shot volume-meshing authorization.
        probe=temp/"P10GB_1D_FIELD_PROBE.msh"
        # With only Physical Surface/Volume groups, a 1D MSH2 export
        # silently omits all ungrouped curve elements (R2: just 280 bytes).
        # -save_all is supported by Gmsh 4.15.2, and applies ONLY here:
        # the real 3D mesh retains its physical group names and IDs.
        one=[str(GMSH),str(temp/(NAME+".geo")),"-1", "-nopopup",
             "-nt","2","-format","msh2","-save_all","-o",str(probe)]
        tested=subprocess.run(one,cwd=temp,stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              timeout=120,check=False)
        one_log=tested.stdout[:4*1024*1024].decode("utf-8",errors="replace")
        (folder/"P10GB_GMSH_1D_FIELD_PROBE.txt").write_text(
            one_log,encoding="utf-8")
        exists=probe.is_file()
        size=probe.stat().st_size if exists else 0
        head=b""
        if exists:
            with probe.open("rb") as stream:
                head=stream.read(8*1024*1024)
        lines=head.splitlines()

        def msh2_count(tag):
            try:
                i=lines.index(tag)
                return int(lines[i+1].strip())
            except (ValueError,IndexError):
                return -1

        node_count=msh2_count(b"$Nodes")
        element_count=msh2_count(b"$Elements")
        metrics={"revision":REV,"candidate":NAME,"native_1d_exit":tested.returncode,
                 "log_contains_Error":"Error" in one_log,
                 "log_contains_Done_meshing_1D":"Done meshing 1D" in one_log,
                 "native_1d_msh_exists":exists,
                 "native_1d_msh_size_bytes":size,
                 "native_1d_msh_v22_sections":all(
                     token in head for token in (b"$MeshFormat",b"$Nodes",b"$Elements")),
                 "native_1d_msh_saved_nodes":node_count,
                 "native_1d_msh_saved_elements":element_count,
                 "native_1d_save_all_only":True,
                 "native_1d_stdout_bytes":len(tested.stdout),
                 "native_3d_attempts":0,"FEM_attempts":0}
        metrics["native_1d_verified"]=bool(
            metrics["native_1d_exit"]==0 and not metrics["log_contains_Error"] and
            metrics["log_contains_Done_meshing_1D"] and exists and size>1000 and
            metrics["native_1d_msh_v22_sections"] and
            node_count>0 and element_count>0)
        save(folder/"P10GB_1D_GATE_METRICS.json",metrics)
        print("P10GB_NATIVE_1D_METRICS",json.dumps(metrics,ensure_ascii=False),flush=True)
        need(metrics["native_1d_verified"],
             "native 1D probe gate STOP; exact diagnosis in "
             "P10GB_1D_GATE_METRICS.json; DO NOT RUN 02")

        # Surface-only preflight is independent of the one-shot -3 mesh.
        # DO NOT use -save_all here: pore physical surface tag8 must survive.
        surfmesh=temp/"P10GB_2D_SURFACE_PROBE.msh"
        two=[str(GMSH),str(temp/(NAME+".geo")),"-2","-nopopup",
             "-nt","2","-format","msh2","-o",str(surfmesh)]
        tested2=subprocess.run(two,cwd=temp,stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                               timeout=120,check=False)
        two_log=tested2.stdout[:4*1024*1024].decode("utf-8",errors="replace")
        (folder/"P10GB_GMSH_2D_SURFACE_PROBE.txt").write_text(two_log,encoding="utf-8")
        two_basic=bool(tested2.returncode==0 and "Error" not in two_log and
                       "Done meshing 2D" in two_log and surfmesh.is_file() and
                       surfmesh.stat().st_size>1000)
        surf=probe_surface_tri6(surfmesh) if two_basic else {}
        # M0 real Tri6 north=18, south=20. Surface must not be coarser
        # in either polar cap before risking the unique volume attempt.
        surf_gate=bool(two_basic and surf["pore_tri6"]>=160 and
                       surf["north_polar_tri6"]>=18 and
                       surf["south_polar_tri6"]>=20)
        metrics2={"revision":REV,"candidate":NAME,
                  "native_2d_exit":tested2.returncode,
                  "native_2d_output_exists":surfmesh.is_file(),
                  "native_2d_output_bytes":surfmesh.stat().st_size if surfmesh.is_file() else 0,
                  "native_2d_contains_Error":"Error" in two_log,
                  "native_2d_Done_meshing_2D":"Done meshing 2D" in two_log,
                  "native_2d_used_save_all":False,
                  "M0_reference_pore_tri6":160,"M0_reference_north_polar_tri6":18,
                  "M0_reference_south_polar_tri6":20,
                  "geometry_surface_stats":surf,
                  "polar_surface_gate":surf_gate,
                  "native_3d_attempts":0,"FEM_attempts":0}
        save(folder/"P10GB_2D_SURFACE_GATE.json",metrics2)
        print("P10GB_NATIVE_2D_SURFACE",json.dumps(metrics2,ensure_ascii=False),flush=True)
        need(surf_gate,"native 2D pore polar surface gate STOP: "
             "see P10GB_2D_SURFACE_GATE.json; 3D one-shot NOT consumed")
        return {"version":"4.15.2","parse_exit":result.returncode,
                "native_1d_exit":tested.returncode,"native_1d_attempts":1,
                "native_2d_exit":tested2.returncode,"native_2d_attempts":1,
                "native_3d_attempts":0,"FEM_attempts":0,
                "parse_log_bytes":len(result.stdout),
                "one_dimensional_log_bytes":len(tested.stdout),
                "one_dimensional_log_sha256":sha(folder/"P10GB_GMSH_1D_FIELD_PROBE.txt"),
                "native_1d_metrics_sha256":sha(folder/"P10GB_1D_GATE_METRICS.json"),
                "native_2d_log_sha256":sha(folder/"P10GB_GMSH_2D_SURFACE_PROBE.txt"),
                "native_2d_metrics_sha256":sha(folder/"P10GB_2D_SURFACE_GATE.json")}


def preflight():
    package_gate()
    geo,_,_,_,_=generated_geo()
    tests=math_selftest()
    installed_gate()
    folder=RUNS/("P10GB_PREFLIGHT_"+stamp())
    folder.mkdir()
    (folder/"P10GB_M1W_SOURCE_ONLY.geo").write_text(geo,encoding="utf-8")
    try:
        parse=native_parse(geo,folder)
    except (RuntimeError,OSError,ValueError,KeyError,subprocess.TimeoutExpired) as exc:
        (folder/"P10GB_PREFLIGHT_STOP_REASON.txt").write_text(
            repr(exc)+"\n",encoding="utf-8")
        bundle=folder/"P10GB_PREFLIGHT_STOP_EVIDENCE.zip"
        with zipfile.ZipFile(bundle,"x",compression=zipfile.ZIP_DEFLATED) as z:
            for name in ("P10GB_1D_GATE_METRICS.json",
                         "P10GB_GMSH_1D_FIELD_PROBE.txt",
                         "P10GB_2D_SURFACE_GATE.json",
                         "P10GB_GMSH_2D_SURFACE_PROBE.txt",
                         "P10GB_GMSH_PARSE_ONLY.txt",
                         "P10GB_PREFLIGHT_STOP_REASON.txt"):
                src=folder/name
                if src.is_file():
                    z.write(src,name)
            z.write(SOURCE_PIN,"P10GB_SOURCE_SHA256.json")
        print("UPLOAD PREFLIGHT STOP EVIDENCE:",bundle,file=sys.stderr,flush=True)
        raise
    proof={"revision":REV,"status":"P10GB_PREFLIGHT_PASS_NO_3D_NO_FEM",
           "timestamp_utc":now().isoformat(),
           "parent_M0_msh_sha256":M0,"failed_M1_sha256":M1,
           "parent_M1V_msh_sha256":M1V,"parent_M1V_geo_sha256":M1VG,
           "source_pin_sha256":sha(SOURCE_PIN),
           "candidate_geo_sha256":hashlib.sha256(geo.encode()).hexdigest(),
           "preflight_run_dir":str(folder),
           "native_parse":parse,"source_math":tests}
    save(PROOF,proof,new=False)
    save(folder/"P10GB_PREFLIGHT_PASS.json",proof)
    print("P10GB_NATIVE_1D_METRICS_FILE:",folder/"P10GB_1D_GATE_METRICS.json",flush=True)
    print("P10GB_NATIVE_2D_SURFACE_FILE:",folder/"P10GB_2D_SURFACE_GATE.json",flush=True)
    print("P10GB_PREFLIGHT_PASS_NO_3D_NO_FEM",flush=True)
    print("ALL_VOLUME_TARGET_VEFF_0.80_TO_0.85; NOT YET VERIFIED ON NATIVE M1W",flush=True)
    print("NEXT: 02_P10GB_ONE_M1W_3D_ONLY.cmd",flush=True)
    return 0


def proof_gate(geo):
    need(PROOF.is_file(),"run 01_P10GB_PREFLIGHT_1D_2D_ONLY.cmd first")
    p=load(PROOF)
    need(p.get("revision")==REV and
         p.get("status")=="P10GB_PREFLIGHT_PASS_NO_3D_NO_FEM" and
         p.get("parent_M0_msh_sha256")==M0 and
         p.get("failed_M1_sha256")==M1 and
         p.get("parent_M1V_msh_sha256")==M1V and
         p.get("parent_M1V_geo_sha256")==M1VG and
         p.get("source_pin_sha256")==sha(SOURCE_PIN) and
         p.get("candidate_geo_sha256")==hashlib.sha256(geo.encode()).hexdigest() and
         p.get("native_parse",{}).get("native_1d_attempts")==1 and
         p.get("native_parse",{}).get("native_1d_exit")==0 and
         p.get("native_parse",{}).get("native_2d_attempts")==1 and
         p.get("native_parse",{}).get("native_2d_exit")==0 and
         p.get("native_parse",{}).get("native_3d_attempts")==0 and
         p.get("native_parse",{}).get("FEM_attempts")==0,
         "preflight not pinned to this source")
    log=Path(p["preflight_run_dir"])/"P10GB_GMSH_1D_FIELD_PROBE.txt"
    need(log.is_file() and sha(log)==p["native_parse"]["one_dimensional_log_sha256"],
         "missing/changed native 1D probe evidence")
    metrics=Path(p["preflight_run_dir"])/"P10GB_1D_GATE_METRICS.json"
    need(metrics.is_file() and
         sha(metrics)==p["native_parse"]["native_1d_metrics_sha256"] and
         load(metrics).get("native_1d_verified") is True,
         "missing/changed native 1D metric evidence")
    surface=Path(p["preflight_run_dir"])/"P10GB_2D_SURFACE_GATE.json"
    s_log=Path(p["preflight_run_dir"])/"P10GB_GMSH_2D_SURFACE_PROBE.txt"
    need(surface.is_file() and s_log.is_file() and
         sha(surface)==p["native_parse"]["native_2d_metrics_sha256"] and
         sha(s_log)==p["native_parse"]["native_2d_log_sha256"] and
         load(surface).get("polar_surface_gate") is True,
         "missing/changed 2D pore surface preflight evidence")
    age=(now()-datetime.fromisoformat(p["timestamp_utc"])).total_seconds()
    need(0<=age<=86400,"preflight expired; repeat safe 01 only")


def evidence(folder,geo_path,mesh_path):
    zip_path=folder/"P10GB_M1W_MESH_EVIDENCE.zip"
    artifacts={
        "P10GB_M1W_MANIFEST.json":folder/"P10GB_M1W_MANIFEST.json",
        "P10GB_GMSH_3D_LOG.txt":folder/"P10GB_GMSH_3D_LOG.txt",
        "P10GB_MESH_QA27.json":folder/"P10GB_MESH_QA27.json",
        "P10GB_STOP_TRACE.txt":folder/"P10GB_STOP_TRACE.txt",
        NAME+".geo":geo_path,
        "P10GB_SOURCE_SHA256.json":SOURCE_PIN,
        "P10GB_PREFLIGHT_PASS.json":PROOF,
        "P10GB_REAL_M1V_729QP_FEEDBACK.json":HERE/"P10GA_M0_M1V_SIGNED18_343_729QP.json",
        "P10GB_HISTORICAL_M1_CALIBRATION.json":HERE/"P10FX_REAL_M0_M1_SIGNED_18_ZONE_729QP.json"
    }
    p=load(PROOF)
    native_log=Path(p["preflight_run_dir"])/"P10GB_GMSH_1D_FIELD_PROBE.txt"
    if (native_log.is_file() and
        sha(native_log)==p["native_parse"]["one_dimensional_log_sha256"]):
        artifacts["P10GB_GMSH_1D_FIELD_PROBE.txt"]=native_log
    native_metrics=Path(p["preflight_run_dir"])/"P10GB_1D_GATE_METRICS.json"
    if (native_metrics.is_file() and
        sha(native_metrics)==p["native_parse"]["native_1d_metrics_sha256"]):
        artifacts["P10GB_1D_GATE_METRICS.json"]=native_metrics
    for filename,digestkey in (("P10GB_2D_SURFACE_GATE.json","native_2d_metrics_sha256"),
                               ("P10GB_GMSH_2D_SURFACE_PROBE.txt","native_2d_log_sha256")):
        source=Path(p["preflight_run_dir"])/filename
        if source.is_file() and sha(source)==p["native_parse"][digestkey]:
            artifacts[filename]=source
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
    folder=RUNS/("P10GB_M1W_"+stamp())
    folder.mkdir()
    marker={"revision":REV,"M0_SHA":M0,"failed_M1_SHA":M1,
            "parent_M1V_SHA":M1V,
            "new_geo_SHA":hashlib.sha256(geo.encode()).hexdigest(),
            "time_utc":now().isoformat(),"FEM_attempts":0}
    # Exclusive persistent markers BEFORE the native 3D attempt.
    save(local_marker(),marker)
    save(profile_marker(),marker)
    geo_path=MESHES/(NAME+".geo")
    mesh_path=folder/(NAME+".msh")
    meta={"revision":REV,"status":"M1W_STOP_NO_FEM",
          "M0_SHA":M0,"failed_M1_SHA":M1,"parent_M1V_SHA":M1V,
          "M1W_uniform_actual_ratio_required":[.8,.85],
          "uniform_actual_target":.825,
          "source_field":"DAMPED_BETA_0p4_C1_REAL_M1V_18_ZONE_QP_FEEDBACK",
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
        print("P10GB ONE GMSH -3: 900s max, private8GiB, output2GiB, NO FEM",flush=True)
        limited=capped_process(cmd,cwd=MESHES,
                               log=folder/"P10GB_GMSH_3D_LOG.txt",
                               wall_s=900,memory_gib=8,output_dir=folder,
                               output_gib=2)
        meta.update(limited)
        need(limited["native_exit_code"]==0 and not limited["stop_reason"],
             "Gmsh native/resource failure")
        qa=audit(mesh_path)
        save(folder/"P10GB_MESH_QA27.json",qa)
        need(qa["nonpositive_samples"]==0 and qa["tet10"]>=1000,
             "curved27QP geometry FAIL")
        target=MESHES/(NAME+".msh")
        with mesh_path.open("rb") as src,target.open("xb") as dst:
            shutil.copyfileobj(src,dst,1<<20)
        need(sha(target)==qa["mesh_sha256"],"target copy SHA mismatch")
        meta["status"]="M1W_GEOMETRY27_PASS_UNIFORM_ALL_VOLUME_729QP_PENDING_NO_FEM"
        meta["mesh_sha256"]=qa["mesh_sha256"]
        meta["qa"]=qa
        result=0
    except BaseException as exc:
        meta["status"]="M1W_STOP_NO_FEM"
        meta["error"]=repr(exc)
        (folder/"P10GB_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        save(folder/"P10GB_M1W_MANIFEST.json",meta)
        evidence(folder,geo_path,mesh_path)
    print("P10GB_RESULT",meta["status"],flush=True)
    print("PHYSICS M1W NOT AUTHORIZED. Send evidence for all-volume independent 729QP.",flush=True)
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
        print("P10GB_PACKAGE_SOURCE_SELFTEST_PASS",
              json.dumps(math_selftest())[:700],flush=True)
        return 0
    if args.preflight:
        return preflight()
    return run_one()


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,AssertionError,KeyError,subprocess.TimeoutExpired) as exc:
        print("P10GB_STOP:",str(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
