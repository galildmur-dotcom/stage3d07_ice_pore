#!/usr/bin/env python3
"""One independent, explicitly confirmed Windows Gmsh -2. NEVER -3/FEM.

Preflight may be rerun; two permanent P10EF-R2 markers are created immediately
before the only native -2 launch, even if the launch/QA later fails.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

from P10DO_windows_guards import child_private_bytes, command, free_windows_ram, sha256
import P10EF_R2_surface_qa as qa

REV="P10EF_R2_ONE_NATIVE_2D_DELAUNAY5_PORE_SURFACE_ONLY"
HERE=Path(__file__).resolve().parent
RUNS=HERE/"P10EF_R2_RUNS"
PROOF=RUNS/"P10EF_R2_PREFLIGHT_PASS.json"
LOCAL_MARKER=RUNS/"P10EF_R2_ONE_2D_USED.json"
PIN=HERE/"P10EF_R2_SOURCE_SHA256.json"
F6="A_P10EA_EXACT_F6_ALG6_CONTROL.geo"
B="B_P10EF_EXACT_F6_ALG5_SURFACE_ONLY.geo"
CAD="sphere_pore_B6_refined.geo"
M1_SHA=qa.M1_SHA
OLD_M2_SHA=qa.M2_SHA
F6_SHA="32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
B_SHA="2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5"
CAD_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
EXE_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
M1_DEFAULT=Path(r"G:\Downloads\P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121\P10DG_RUNS\P10DG_M1_20261121_120324_362583\P10DG_M1_CANDIDATE.msh")
M2_DEFAULT=Path(r"G:\Downloads\P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122\P10EA_RUNS\P10EA_20261122_044007_248420\P10EA_M2_CANDIDATE.msh")
CONFIRM="RUN ONE P10EF 2D SURFACE"
WALL_S=120
PRIVATE_MAX=2*1024**3
MESH_MAX=25*1024**2
LOG_MAX=4*1024**2
QA_WALL_S=60
PREFLIGHT_HOURS=24


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EF_R2_STOP: "+why)


def source_gate() -> dict:
    pin=json.loads(PIN.read_text(encoding="utf-8"))
    need(pin.get("revision")==REV and pin.get("one_native_2d_max")==1 and
         pin.get("native_3d_allowed") is False and
         pin.get("physical_FEM") is False and
         pin.get("accepted_original_m1_sha256")==M1_SHA and
         pin.get("historical_m2_sha256")==OLD_M2_SHA and
         pin.get("gmsh_sha256")==EXE_SHA and
         len(pin.get("files",{}))==len(PACKAGED_FILES),"source inventory/authority")
    need(set(pin["files"])==set(PACKAGED_FILES),"unexpected or missing package member")
    for name, expected in pin["files"].items():
        need(name==Path(name).name and (HERE/name).is_file() and
             sha256(HERE/name)==expected,"source SHA mismatch: "+name)
    a=(HERE/F6).read_bytes(); b=(HERE/B).read_bytes(); cad=(HERE/CAD).read_bytes()
    needle=b"Background Field=6;\n"
    need(sha256(HERE/F6)==F6_SHA and sha256(HERE/B)==B_SHA and
         sha256(HERE/CAD)==CAD_SHA and a.count(needle)==1 and
         b==a.replace(needle,b"Mesh.Algorithm = 5;\n"+needle,1) and
         a.count(b"Mesh.Algorithm")==0 and
         b.count(b"Mesh.Algorithm = 5;")==1 and
         cad.count(b"Mesh.Algorithm3D=10;")==1 and
         cad.count(b"Mesh.ElementOrder=2;")==1 and
         a.count(b"Field[6] = MathEval;")==1 and
         a.count(b'Include "sphere_pore_B6_refined.geo";')==1,
         "geometry/F6 one-line alg5 identity")
    return pin


PACKAGED_FILES=(F6,B,CAD,"P10DO_windows_guards.py",
                "P10EF_R2_one_2d_surface.py","P10EF_R2_surface_qa.py",
                "README_P10EF_R2_RU.md","01_P10EF_R2_SAFE_PREFLIGHT_ONLY.cmd",
                "02_P10EF_R2_ONE_2D_SURFACE_ONLY.cmd")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def profile_marker() -> Path:
    base=os.environ.get("LOCALAPPDATA","")
    need(bool(base) and Path(base).is_dir(),"LOCALAPPDATA unavailable")
    return Path(base)/"Stage3D07"/("P10EF_R2_ONE_2D_"+M1_SHA+".json")


def marker_clear() -> None:
    need(not LOCAL_MARKER.exists() and not profile_marker().exists(),
         "P10EF R2 one-shot ALREADY CONSUMED; NEVER delete markers or rerun 02")


def proof_fresh() -> dict:
    need(PROOF.is_file(),"run button 01 (safe preflight) successfully before button 02")
    obj=json.loads(PROOF.read_text(encoding="utf-8"))
    diff=datetime.now(timezone.utc)-datetime.fromisoformat(obj["checked_utc"])
    need(timedelta(0)<=diff<=timedelta(hours=PREFLIGHT_HOURS) and
         obj.get("revision")==REV and obj.get("m1_sha256")==M1_SHA and
         obj.get("old_m2_sha256")==OLD_M2_SHA and
         obj.get("candidate_sha256")==B_SHA and
         obj.get("gmsh_sha256")==EXE_SHA and
         obj.get("native_parse_passed")==[F6,B],
         "preflight proof not authenticated or >24h")
    return obj


def choose_file(prompt: bool, *, default: Path, expected: str,
                proof_field: str, explanation: str) -> Path:
    if prompt:
        print(explanation,"\nDefault:",default,flush=True)
        answer=input("Original .msh path (Enter=default): ").strip().strip('"').strip("'")
        path=Path(answer) if answer else default
    else:
        path=Path(proof_fresh()[proof_field])
    need(path.is_file() and path.name==default.name and sha256(path)==expected,
         "ORIGINAL mesh basename/SHA wrong: "+path.name)
    return path


def prepare(run: Path, meta: dict, *, ask: bool) -> tuple[Path,Path,Path]:
    need(os.name=="nt","Windows required; NEVER launch native Gmsh on other OS")
    repo=r"g:\ildar\stage3d07"
    here=str(HERE).lower()
    need(here!=repo and not here.startswith(repo+"\\"),
         "extract into a new folder OUTSIDE G:\\ildar\\Stage3D07")
    source_gate()
    qa.selftest()
    marker_clear()
    m1=choose_file(ask,default=M1_DEFAULT,expected=M1_SHA,
                   proof_field="m1_path",explanation="Original accepted P10DG M1; NOT H0/U0/new M1")
    old=choose_file(ask,default=M2_DEFAULT,expected=OLD_M2_SHA,
                    proof_field="old_m2_path",explanation="Original historical P10EA M2 alg6; NEVER regenerate")
    exe=Path(os.environ.get("P10EF_R2_GMSH_EXE",r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    need(exe.is_file() and sha256(exe)==EXE_SHA,"native Gmsh exe SHA differs")
    v=command([str(exe),"-version"],HERE,timeout=15)
    need(v.returncode==0 and re.search(r"(?<!\d)4\.15\.2(?!\d)",v.stdout+v.stderr) is not None,
         "Gmsh native version/exit")
    ram, disk=free_windows_ram(),shutil.disk_usage(HERE).free
    need(ram>=4*1024**3 and disk>=1*1024**3,"need >=4GiB free RAM, >=1GiB disk")
    geo=run/"GEO"; geo.mkdir(exist_ok=False)
    for name in (F6,B,CAD):
        shutil.copyfile(HERE/name,geo/name)
        need(sha256(geo/name)==sha256(HERE/name),"geo copy SHA")
    meta.update({"m1_path":str(m1),"old_m2_path":str(old),"gmsh_path":str(exe),
         "free_ram_bytes":ram,"free_disk_bytes":disk})
    for name in (F6,B):
        meta["native_parse_attempts"]+=1
        try:
            p=command([str(exe),str(geo/name),"-parse_and_exit"],geo,timeout=20)
        except subprocess.TimeoutExpired:
            need(False,"native GEO parse timeout: "+name)
        log=(p.stdout+p.stderr)
        (run/(name+".parse.log")).write_bytes(log.encode("utf-8",errors="replace")[:LOG_MAX])
        need(p.returncode==0 and not re.search(r"(?im)^\s*Error\s*:",log),
             "native GEO parse failed: "+name+" "+log[-250:])
        meta["native_parse_passed"].append(name)
    return m1,old,geo/B


def save_proof(meta: dict) -> None:
    need(meta["native_parse_passed"]==[F6,B],"native A/B GEO parse missing")
    PROOF.write_text(json.dumps({"revision":REV,"checked_utc":utc(),
        "m1_path":meta["m1_path"],"m1_sha256":M1_SHA,
        "old_m2_path":meta["old_m2_path"],"old_m2_sha256":OLD_M2_SHA,
        "candidate_sha256":B_SHA,"gmsh_sha256":EXE_SHA,
        "native_parse_passed":meta["native_parse_passed"]},indent=2)+"\n",encoding="utf-8")


def consume(run: Path, argv: list[str]) -> None:
    marker_clear()
    payload={"revision":REV,"mode":"ONE_NATIVE_GMSH_2D_ONLY",
             "run_id":run.name,"consumed_utc":utc(),"argv":argv,
             "original_m1_sha256":M1_SHA,"historical_m2_sha256":OLD_M2_SHA}
    profile=profile_marker()
    profile.parent.mkdir(parents=True,exist_ok=True)
    # Both EXCLUSIVE x markers persist on any failure, consumed BEFORE -2 Popen.
    with profile.open("x",encoding="utf-8") as out:
        json.dump(payload,out,indent=2)
    with LOCAL_MARKER.open("x",encoding="utf-8") as out:
        json.dump(payload,out,indent=2)


def bound(argv: list[str], *, cwd: Path, log: Path, wall: int,
          mesh: Path | None = None) -> dict:
    t=time.monotonic(); peak=0; status="MONITORING"
    with log.open("x",encoding="utf-8") as stream:
        process=subprocess.Popen(argv,cwd=str(cwd),stdin=subprocess.DEVNULL,
                                 stdout=stream,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                peak=max(peak,child_private_bytes(process))
                if time.monotonic()-t>wall: status="WALL_LIMIT"
                elif peak>PRIVATE_MAX: status="PRIVATE_LIMIT"
                elif log.stat().st_size>LOG_MAX: status="LOG_LIMIT"
                elif mesh is not None and mesh.is_file() and mesh.stat().st_size>MESH_MAX:
                    status="MESH_LIMIT"
                if status!="MONITORING":
                    process.kill(); break
                time.sleep(.2)
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=10)
    return {"status":status,"exit_code":process.returncode,
        "wall_s":time.monotonic()-t,"polled_peak_private_bytes":peak,
        "log_bytes":log.stat().st_size,"argv":argv}


def launch(meta: dict, run: Path, b: Path, m1: Path, old: Path) -> None:
    mesh=run/"P10EF_R2_SURFACE_2D_CANDIDATE.msh"
    argv=[meta["gmsh_path"],str(b),"-2","-nt","2","-format","msh2","-o",str(mesh)]
    # No intervening operations between permanent marker and subprocess.Popen.
    consume(run,argv)
    meta["native_2d_attempts"]=1
    info=bound(argv,cwd=b.parent,log=run/"P10EF_R2_GMSH_FULL.log",wall=WALL_S,mesh=mesh)
    meta["native_2d_result"]=info
    need(info["status"]=="MONITORING" and info["exit_code"]==0,
         "bounded native Gmsh -2 STOP: "+str(info))
    need(mesh.is_file() and 0<mesh.stat().st_size<=MESH_MAX,"2D MSH missing/size >25MiB")
    log=(run/"P10EF_R2_GMSH_FULL.log").read_bytes()
    need(b"Done meshing 2D" in log and
         not re.search(r"(?im)^\s*Error\s*:",log.decode("utf-8",errors="replace")),
         "native log missing 2D completion or contains Error")
    meta["candidate_2d_sha256"]=sha256(mesh)
    meta["candidate_2d_bytes"]=mesh.stat().st_size
    audit_argv=[sys.executable,str(HERE/"P10EF_R2_surface_qa.py"),
       "--m1",str(m1),"--old-m2",str(old),"--candidate",str(mesh),"--out",str(run/"QA")]
    info=bound(audit_argv,cwd=HERE,log=run/"P10EF_R2_QA.log",wall=QA_WALL_S)
    meta["qa_process_result"]=info
    need(info["status"]=="MONITORING" and info["exit_code"]==0,
         "curved surface QA STOP: "+str(info))
    result=json.loads((run/"QA"/"P10EF_R2_SURFACE_QP_AUDIT.json").read_text(encoding="utf-8"))
    need(result["candidate_2d_sha256"]==meta["candidate_2d_sha256"] and
         result["m1_sha256"]==M1_SHA and result["historical_m2_sha256"]==OLD_M2_SHA,
         "surface audit input SHA mismatch")
    meta["surface_qp_ratios"]=result["effective_curved_tri6_area_ratios"]
    meta["status"]="P10EF_R2_2D_MESH_GEOMETRY_QA_COMPLETE_ADAPTATION_UNDECIDED_NO_FEM"


def evidence(run: Path) -> Path:
    zpath=run/"P10EF_R2_EVIDENCE.zip"
    with zipfile.ZipFile(zpath,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(run.rglob("*")):
            if (f.is_file() and f!=zpath and f.stat().st_size<=MESH_MAX and
                not f.name.endswith(".tmp")):
                z.write(f,f.relative_to(run).as_posix())
    return zpath


def run(*, safe: bool) -> int:
    RUNS.mkdir(parents=True,exist_ok=True)
    folder=RUNS/("P10EF_R2_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(exist_ok=False)
    meta={"revision":REV,"started_utc":utc(),
          "status":"P10EF_R2_STOP_NO_FEM","mode":"SAFE_PREFLIGHT" if safe else "ONE_2D_ONLY",
          "native_parse_attempts":0,"native_parse_passed":[],
          "native_2d_attempts":0,"native_3d_attempts":0,"physical_fem_attempts":0,
          "original_m1_sha256":M1_SHA,"historical_m2_sha256":OLD_M2_SHA,
          "candidate_geo_sha256":B_SHA,"target_polar_surface_area_ratio":.8**(2/3),
          "one_native_2d_wall_max_s":WALL_S,"private_polled_max_bytes":PRIVATE_MAX,
          "mesh_max_bytes":MESH_MAX,"log_max_bytes":LOG_MAX,"threads":2}
    code=2
    try:
        if not safe: proof_fresh()
        m1,old,b=prepare(folder,meta,ask=safe)
        print("P10EF R2 PREFLIGHT PASS: original M1 + historical M2 SHA; source pin,"
              " native A/B GEO parse, Gmsh4.15.2; NO -2/-3/FEM yet.",flush=True)
        if safe:
            save_proof(meta)
            meta["status"]="P10EF_R2_PREFLIGHT_PASS_NO_MESH_NO_FEM"
            code=0
        else:
            print("ONE P10EF -2 ONLY: wall 120s, polled private 2GiB, mesh25MiB, log4MiB, -nt2."
                  " Marker is permanent even if timeout/error. NO -3/FEM.",flush=True)
            answer=input("Type exactly "+CONFIRM+": ")
            need(answer==CONFIRM,"manual phrase absent; marker NOT consumed")
            launch(meta,folder,b,m1,old)
            code=0
    except BaseException as exc:
        meta["stop_reason"]=str(exc)
        (folder/"P10EF_R2_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
        print("P10EF_R2 STOP:",exc,flush=True)
    finally:
        full=folder/"P10EF_R2_GMSH_FULL.log"
        if full.is_file():
            with full.open("rb") as f:
                f.seek(max(0,full.stat().st_size-80*1024))
                (folder/"P10EF_R2_GMSH_TAIL.txt").write_bytes(f.read())
        meta["finished_utc"]=utc()
        (folder/"P10EF_R2_MANIFEST.json").write_text(
            json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        (folder/"P10EF_R2_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nNATIVE_2D_ATTEMPTS="+str(meta["native_2d_attempts"])+
            "\nNATIVE_3D_ATTEMPTS=0\nFEM=0\nCANDIDATE_2D_SHA256="+
            str(meta.get("candidate_2d_sha256","UNKNOWN"))+"\nSTOP_REASON="+
            str(meta.get("stop_reason",""))+"\n",encoding="utf-8")
        archive=evidence(folder)
        print("P10EF R2 RESULT:",meta["status"],"EVIDENCE:",archive,flush=True)
        print("Send original P10EF_R2_EVIDENCE.zip privately (contains raw new 2D MSH)."
              " NEVER rerun button02 after marker consumption.",flush=True)
    return code


def selftest() -> int:
    pin=source_gate()
    qa.selftest()
    argv=["gmsh.exe","B.geo","-2","-nt","2","-format","msh2","-o","result.msh"]
    need(argv.count("-2")==1 and "-3" not in argv and
         WALL_S==120 and PRIVATE_MAX==2*1024**3 and
         MESH_MAX==25*1024**2 and LOG_MAX==4*1024**2 and
         len(pin["files"])==len(PACKAGED_FILES),"single 2D source-only resource contract")
    print("P10EF_R2_SOURCE_SELFTEST_PASS sha_pin9/9 alg5 one_line_diff=PASS"
          " one_2D_only=PASS native_Gmsh=0 FEM=0")
    return 0


def main() -> int:
    parser=argparse.ArgumentParser()
    m=parser.add_mutually_exclusive_group(required=True)
    m.add_argument("--selftest",action="store_true")
    m.add_argument("--preflight-only",action="store_true")
    m.add_argument("--one-2d",action="store_true")
    opts=parser.parse_args()
    return selftest() if opts.selftest else run(safe=opts.preflight_only)


if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,RuntimeError,ValueError,KeyError) as exc:
        print("P10EF_R2 STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
