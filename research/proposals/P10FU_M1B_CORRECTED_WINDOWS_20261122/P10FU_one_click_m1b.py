#!/usr/bin/env python3
"""P10FU: source-pinned one-shot fresh M0 -> corrective M1B mesh; NO FEM.

All meaningful mesh acceptance remains an INDEPENDENT post-run 343/729QP
decision; a smooth prescribed field never proves a realized local volume.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile

from P10FN_common import capped_process
from P10FN_mesh_qa import audit

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
MESHES = PROJECT / "meshes"
RUNS = PROJECT / "LOCAL_RUNS"
GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
REV = "P10FU_R1_FRESH_M0_M1B_SOUTH_C1_CORRECTION_MESH_ONLY"
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M0_GEO_SHA = "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
M1_SHA = "f281d253571db095b90790326f503dfa3f6fe3a1dc5cb5c904fca2787dfe4275"
M1_GEO_SHA = "968ef2ed3f64160d51d1983ead31216758d164fa665fa7e6a9044f8fc04d64e8"
SOURCE_PIN = HERE / "P10FU_SOURCE_SHA256.json"
CANDIDATE = "M1B_CANDIDATE"
CORRECTION_SOUTH = .25
UNIFORM_VOLUME_TARGET = .80
SEAM_POLAR_START, SEAM_POLAR_FULL = .55, .80
WALL_FULL_M, WALL_ZERO_M = .0001, .0005
PROOF = HERE / "P10FU_PREFLIGHT_PASS.json"


def need(cond, why):
    if not cond:
        raise RuntimeError("P10FU_STOP: " + why)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def utcnow():
    return datetime.now(timezone.utc)


def stamp():
    return utcnow().strftime("%Y%m%d_%H%M%S_%f")


def save_json(path, data, exclusive=True):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
        f.write("\n")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_gate():
    pin=load_json(SOURCE_PIN)
    expected=set((
        "P10FU_one_click_m1b.py",
        "01_P10FU_SAFE_PREFLIGHT_ONLY.cmd",
        "02_P10FU_ONE_M1B_3D_ONLY.cmd",
        "README_P10FU_RU.md",
        "P10FN_common.py",
        "P10FN_mesh_qa.py",
        "P10CK_curved_qp_audit.py",
        "M0.geo",
        "sphere_pore_B6_refined.geo",
    ))
    need(pin.get("revision")==REV and set(pin.get("files",{}))==expected,
         "package source SHA inventory incomplete or unrecognized")
    need(pin.get("M0_msh_sha256")==M0_SHA and
         pin.get("M0_geo_sha256")==M0_GEO_SHA and
         pin.get("failed_M1_msh_sha256")==M1_SHA and
         pin.get("failed_M1_geo_sha256")==M1_GEO_SHA and
         pin.get("native_3d_attempt_cap")==1 and
         pin.get("FEM_attempt_cap")==0 and
         pin.get("candidate_name")==CANDIDATE,
         "source pin's scientific state changed")
    for name,digest in pin["files"].items():
        file=HERE/name
        need(file.is_file() and sha(file)==digest,
             "source SHA mismatch: "+name)
    need(pin["files"]["M0.geo"]==M0_GEO_SHA,
         "bundle's M0 GEO is not the accepted original")
    return pin


def smooth_formula(expr):
    u=f"min(1,max(0,({expr})))"
    return f"(({u})*({u})*(3-2*({u})))"


def corrected_weight():
    r="sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)"
    d=f"({r}-0.001)"
    mu=f"((z-0.03)/({r}))"
    radial=f"(1-{smooth_formula(f'(({d})-{WALL_FULL_M:.17g})/{(WALL_ZERO_M-WALL_FULL_M):.17g}')})"
    south=smooth_formula(f"((-({mu}))-{SEAM_POLAR_START:.17g})/{(SEAM_POLAR_FULL-SEAM_POLAR_START):.17g}")
    return f"({radial}*({south}))"


def old_field_expression(m0):
    token="Field[3].F = StrCat("
    need(m0.count(token)==1, "M0 canonical C1 Field 3 not present exactly once")
    val=m0.split(token,1)[1].split(");",1)[0]
    expr="".join(re.findall(r'"([^"]*)"',val))
    need(len(expr)>500 and expr.count("(")==expr.count(")") and
         not any(f"F{j}" in expr for j in range(50)),
         "M0 C1 field source malformed or nested")
    return expr


def split_gmsh(expr):
    need(expr and expr.count("(")==expr.count(")") and "+-" not in expr,
         "MathEval suspect parentheses/negative sign")
    return ",\n  ".join('"'+expr[i:i+340]+'"' for i in range(0,len(expr),340))


def generate_geo():
    m0=(HERE/"M0.geo").read_text(encoding="utf-8")
    original=old_field_expression(m0)
    weight=corrected_weight()
    h=f"({original})*exp(log({UNIFORM_VOLUME_TARGET:.17g}*(1-{CORRECTION_SOUTH:.17g}*({weight})))/3)"
    geo=(
        "// P10FU: corrected fresh M1B, derived only from accepted M0.\n"
        "// Original failed M1 not included, touched or overwritten.\n"
        "// One C1 h(x) is used for both pore Tri6 and adjacent Tet10.\n"
        "// Nominal south h^3 ratio 0.60, a calibration hypothesis only.\n"
        'Include "M0.geo";\n'
        "Field[4] = MathEval;\n"
        f"Field[4].F = StrCat(\n  {split_gmsh(weight)}\n);\n"
        "Field[5] = MathEval;\n"
        f"Field[5].F = StrCat(\n  {split_gmsh(h)}\n);\n"
        "Background Field=5;\n"
        "Mesh.Algorithm=5;\nMesh.Algorithm3D=10;\n"
        "Mesh.ElementOrder=2;\nMesh.HighOrderOptimize=1;\n"
        "Mesh.MeshSizeExtendFromBoundary=0;\n"
        "Mesh.MeshSizeFromPoints=0;\n"
        "Mesh.MeshSizeFromCurvature=0;\n"
        "Mesh.MeshSizeMin=0;\nMesh.MeshSizeMax=1e22;\n"
        "Mesh.MshFileVersion=2.2;\nMesh.Binary=0;\n"
    )
    need('Include "M0.geo";' in geo and "Background Field=5;" in geo and
         "F3" not in h and "F4" not in h,"Gmsh native source contract")
    return geo,original,weight,h


def clamp01(v):
    return min(1.,max(0.,v))


def s01(v):
    u=clamp01(v)
    return u*u*(3-2*u)


def numeric_weight(x,y,z):
    radius=math.sqrt(x*x+y*y+(z-.03)**2+1e-24)
    d=radius-.001
    mu=(z-.03)/radius
    return (1-s01((d-WALL_FULL_M)/(WALL_ZERO_M-WALL_FULL_M)))*s01((-mu-SEAM_POLAR_START)/(SEAM_POLAR_FULL-SEAM_POLAR_START))


def math_gate(orig,weight,h):
    safe={"__builtins__":{},"sqrt":math.sqrt,"exp":math.exp,"log":math.log,
          "min":min,"max":max}
    rng=random.Random(20261122)
    locations=[(0.,0.,.03105),(0.,0.,.02895),
               (0.,0.,.0300+.0015),(0.,0.,.0300-.0015),
               (.00105,0.,.0300),(.002,0.,.0300)]
    for _ in range(4096):
        mu=rng.uniform(-1,1)
        phi=rng.uniform(0,math.tau)
        d=rng.uniform(0,.001)
        rad=.001+d
        locations.append((rad*math.sqrt(1-mu*mu)*math.cos(phi),
                          rad*math.sqrt(1-mu*mu)*math.sin(phi),.03+rad*mu))
    worst=0.
    for x,y,z in locations:
        vars=dict(safe,x=x,y=y,z=z)
        base=eval(orig,vars)
        got_w=eval(weight,vars)
        want_w=numeric_weight(x,y,z)
        got_h=eval(h,vars)
        want_h=base*(UNIFORM_VOLUME_TARGET*(1-CORRECTION_SOUTH*want_w))**(1/3)
        need(math.isfinite(base) and base>0 and 0<=got_w<=1+1e-12 and got_h>0,
             "nonfinite/out-of-range source sample")
        worst=max(worst,abs(got_w-want_w),
                  abs(got_h-want_h)/want_h)
    need(worst<1e-11, "GEO MathEval != independent smooth formula")
    north=numeric_weight(0,0,.03105)
    south=numeric_weight(0,0,.02895)
    eq=numeric_weight(.00105,0,.03)
    need(abs(north)<1e-12 and abs(south-1)<1e-12 and abs(eq)<1e-12,
         "unexpected polar C1 weight samples")
    return {"samples":len(locations),"max_formula_discrepancy":worst,
            "nominal_global_target":UNIFORM_VOLUME_TARGET,
            "north_wall_target":UNIFORM_VOLUME_TARGET,
            "south_wall_target":UNIFORM_VOLUME_TARGET*(1-CORRECTION_SOUTH),
            "north_weight":north,"south_weight":south,
            "equator_weight":eq,
            "scientific_go":False}


def installed_gate():
    need(sys.platform=="win32","this mode requires Windows 11; use --selftest elsewhere")
    need(GMSH.is_file(),"Gmsh 4.15.2 is missing: "+str(GMSH))
    need(MESHES.is_dir() and RUNS.is_dir(),
         "existing Stage3D07 meshes/LOCAL_RUNS directories are required")
    for name,digest in (
        ("M0.msh",M0_SHA),("M0.geo",M0_GEO_SHA),
        ("M1.msh",M1_SHA),("M1.geo",M1_GEO_SHA),
        ("sphere_pore_B6_refined.geo",sha(HERE/"sphere_pore_B6_refined.geo")),
    ):
        path=MESHES/name
        need(path.is_file() and sha(path)==digest,
             "missing/changed existing original "+name)
    for ext in (".geo",".msh"):
        need(not (MESHES/(CANDIDATE+ext)).exists(),
             "candidate file already exists; preserve the earlier attempt")
    need(not local_marker().exists() and not profile_marker().exists(),
         "M1B native one-shot previously consumed")


def local_marker():
    return RUNS/"P10FU_LOCKS"/("M1B_FROM_"+M0_SHA[:16]+".json")


def profile_marker():
    appdata=os.environ.get("LOCALAPPDATA","")
    need(bool(appdata),"Windows LOCALAPPDATA unavailable")
    return Path(appdata)/"Stage3D07"/("P10FU_R1_M1B_"+M0_SHA+".json")


def safe_native_parse(geo, folder):
    # Parse only in isolated input copies: never produce a volume mesh in preflight.
    version=subprocess.run([str(GMSH),"-version"],cwd=folder,
                           stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,timeout=15,check=False)
    need(version.returncode==0 and
         "4.15.2" in version.stdout.decode("utf-8",errors="replace"),
         "native Gmsh executable is not verified 4.15.2")
    with tempfile.TemporaryDirectory(prefix="P10FU_PARSE_",dir=folder) as tmp:
        dest=Path(tmp)
        (dest/(CANDIDATE+".geo")).write_text(geo,encoding="utf-8")
        for name in ("M0.geo","sphere_pore_B6_refined.geo"):
            shutil.copy2(HERE/name,dest/name)
        cmd=[str(GMSH),str(dest/(CANDIDATE+".geo")),
             "-parse_and_exit","-nopopup","-nt","2"]
        try:
            output=subprocess.run(cmd,cwd=dest,stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  timeout=45,check=False)
        except subprocess.TimeoutExpired as err:
            raise RuntimeError("P10FU_STOP: Gmsh native parse exceeded 45 s") from err
        log=output.stdout[:2*1024*1024].decode("utf-8",errors="replace")
        (folder/"P10FU_GMSH_PARSE_ONLY.txt").write_text(log,encoding="utf-8")
        need(output.returncode==0,"native Gmsh -parse_and_exit failed")
        need("Error" not in log and "Error :" not in log,
             "native Gmsh parse log reports error")
        return {"gmsh_version":"4.15.2",
                "command":["gmsh.exe","-parse_and_exit","-nt","2"],
                "exit_code":output.returncode,"log_bytes":len(output.stdout),
                "native_3d_attempts":0}


def preflight():
    pin=source_gate()
    geo,base,weight,h=generate_geo()
    samples=math_gate(base,weight,h)
    installed_gate()
    folder=RUNS/("P10FU_PREFLIGHT_"+stamp())
    folder.mkdir()
    parse=safe_native_parse(geo,folder)
    proof={"revision":REV,"status":"P10FU_PREFLIGHT_PASS_NO_3D_NO_FEM",
           "timestamp_utc":utcnow().isoformat(),
           "M0_sha256":M0_SHA,"old_M1_sha256":M1_SHA,
           "generated_geo_sha256":hashlib.sha256(geo.encode()).hexdigest(),
           "source_pin_sha256":sha(SOURCE_PIN),
           "native_parse":parse,"math":samples,"run_folder":str(folder)}
    save_json(PROOF,proof,exclusive=False)
    (folder/"P10FU_GENERATED_SOURCE_ONLY.geo").write_text(geo,encoding="utf-8")
    save_json(folder/"P10FU_PREFLIGHT_PASS.json",proof)
    print("P10FU_PREFLIGHT_PASS_NO_3D_NO_FEM",flush=True)
    print("SOUTH_NOMINAL_VOLUME_RATIO=0.60; ACTUAL_REFINEMENT_UNPROVEN",flush=True)
    print("NEXT: 02_P10FU_ONE_M1B_3D_ONLY.cmd",flush=True)
    return 0


def proof_gate(geo):
    need(PROOF.is_file(),"run 01_P10FU_SAFE_PREFLIGHT_ONLY.cmd first")
    proof=load_json(PROOF)
    need(proof.get("revision")==REV and
         proof.get("status")=="P10FU_PREFLIGHT_PASS_NO_3D_NO_FEM" and
         proof.get("M0_sha256")==M0_SHA and
         proof.get("old_M1_sha256")==M1_SHA and
         proof.get("source_pin_sha256")==sha(SOURCE_PIN) and
         proof.get("generated_geo_sha256")==hashlib.sha256(geo.encode()).hexdigest(),
         "preflight source/mesh revision mismatch")
    timestamp=datetime.fromisoformat(proof["timestamp_utc"])
    age=(utcnow()-timestamp).total_seconds()
    need(0<=age<=24*3600,"preflight older than 24h; repeat SAFE 01, not 02")


def evidence(folder,manifest,geo_path,candidate):
    archive=folder/"P10FU_M1B_MESH_EVIDENCE.zip"
    files=[("P10FU_M1B_MANIFEST.json",folder/"P10FU_M1B_MANIFEST.json"),
           ("P10FU_GMSH_3D_LOG.txt",folder/"P10FU_GMSH_3D_LOG.txt"),
           ("P10FU_MESH_QA27.json",folder/"P10FU_MESH_QA27.json"),
           ("P10FU_STOP_TRACE.txt",folder/"P10FU_STOP_TRACE.txt"),
           (CANDIDATE+".geo",geo_path),
           ("P10FU_SOURCE_SHA256.json",SOURCE_PIN),
           ("P10FU_PREFLIGHT_PASS.json",PROOF)]
    if candidate.is_file() and candidate.stat().st_size<=32*1024**2:
        files.append((CANDIDATE+".msh",candidate))
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for name,src in files:
            if src.is_file():
                out.write(src,arcname=name)
    print("SEND THIS FILE:",archive,flush=True)


def run_one_3d():
    source_gate()
    geo,base,weight,h=generate_geo()
    math_gate(base,weight,h)
    installed_gate()
    proof_gate(geo)
    folder=RUNS/("P10FU_M1B_"+stamp())
    folder.mkdir()
    marker={"revision":REV,"mode":"ONE_3D_MESH",
            "M0_SHA":M0_SHA,"old_M1_SHA":M1_SHA,
            "geo_sha256":hashlib.sha256(geo.encode()).hexdigest(),
            "utc":utcnow().isoformat(),"physical_FEM_attempts":0}
    # A second extraction elsewhere must not bypass either one-shot lock.
    save_json(local_marker(),marker)
    save_json(profile_marker(),marker)
    geo_path=MESHES/(CANDIDATE+".geo")
    candidate=folder/(CANDIDATE+".msh")
    meta={"revision":REV,"status":"M1B_STOP_NO_FEM",
          "parent_M0_sha256":M0_SHA,"failed_M1_sha256":M1_SHA,
          "field":"one_joint_C1_Tri6_Tet10",
          "nominal_north_volume_ratio":.8,
          "nominal_south_volume_ratio":.60,
          "actual_local_729qp":"PENDING_INDEPENDENT_REVIEW",
          "native_3d_attempts":0,"FEM_attempts":0}
    code=2
    try:
        # Open in x mode: never truncate any existing GEO, even in a race.
        with geo_path.open("x",encoding="utf-8") as f:
            f.write(geo)
        cmd=[str(GMSH),str(geo_path),"-3","-nopopup","-nt","2",
             "-format","msh2","-o",str(candidate)]
        meta["command"]=cmd
        meta["native_3d_attempts"]=1
        print("P10FU: ONE GMSH -3; max 900s / 8GiB private / 2GiB files / no FEM",flush=True)
        limits=capped_process(cmd,cwd=MESHES,log=folder/"P10FU_GMSH_3D_LOG.txt",
                              wall_s=900,memory_gib=8,output_dir=folder,output_gib=2)
        meta.update(limits)
        need(limits["native_exit_code"]==0 and not limits["stop_reason"],
             "Gmsh failed its native/limit gate")
        qa=audit(candidate)
        save_json(folder/"P10FU_MESH_QA27.json",qa)
        need(qa["nonpositive_samples"]==0 and qa["tet10"]>=1000,
             "curved27QP geometry gate failed")
        target=MESHES/(CANDIDATE+".msh")
        with candidate.open("rb") as inp, target.open("xb") as out:
            shutil.copyfileobj(inp,out,1<<20)
        need(sha(target)==qa["mesh_sha256"],
             "candidate copy SHA mismatch")
        meta["status"]="M1B_GEOMETRY27_PASS_D025_729QP_PENDING_NO_FEM"
        meta["mesh_sha256"]=qa["mesh_sha256"]
        meta["qa"]=qa
        code=0
    except BaseException as err:
        meta["status"]="M1B_STOP_NO_FEM"
        meta["error"]=repr(err)
        (folder/"P10FU_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        save_json(folder/"P10FU_M1B_MANIFEST.json",meta)
        evidence(folder,meta,geo_path,candidate)
    print("P10FU_RESULT",meta["status"],flush=True)
    print("M1B is NEVER physics approved by this launcher.",flush=True)
    return code


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--preflight",action="store_true")
    p.add_argument("--one-mesh",action="store_true")
    args=p.parse_args()
    need(sum((args.selftest,args.preflight,args.one_mesh))==1,
         "choose exactly one mode")
    if args.selftest:
        source_gate()
        geo,base,weight,h=generate_geo()
        result=math_gate(base,weight,h)
        print("P10FU_SOURCE_ONLY_SELFTEST_PASS",json.dumps(result),flush=True)
        return 0
    if args.preflight:
        return preflight()
    return run_one_3d()


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,AssertionError,KeyError) as exc:
        print("P10FU_STOP:",str(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
