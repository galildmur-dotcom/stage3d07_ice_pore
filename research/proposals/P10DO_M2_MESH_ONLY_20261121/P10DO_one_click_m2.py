#!/usr/bin/env python3
"""P10DO: bounded SINGLE Windows Gmsh M2, never a physical FEM solver.

Requires SHA-exact D-019 M1, pinned C1 field, native Gmsh 4.15.2 parse gate,
read-only labeling of all M1 Tet10, independent full 27QP M2 mesh QA.
Preflight/manual decline never consumes the mesh attempt. A launched attempt
is one-shot even on Gmsh/QA failure; do not erase any one-shot markers.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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

import P10DN_m2_coefficient as coef
from P10DO_windows_guards import (
    child_private_bytes, command, free_windows_ram, require, sha256,
)

REV="P10DO_R1_M2_GRADED_KAPPA20_MESH_ONLY"
HERE=Path(__file__).resolve().parent
RUNS=HERE/"P10DO_RUNS"
MARKER=RUNS/"P10DO_ONE_SHOT_USED.json"
GEO="P10DN_M2_FIELD20.geo"
PIN="P10DO_PINNED_SHA256.json"
GMSH_VERSION="4.15.2"
CONFIRM="RUN ONE P10DO M2 MESH"
WALL_LIMIT=900
PRIVATE_LIMIT=8*1024**3
MSH_LIMIT=750*1024**2
LOG_LIMIT=30*1024**2
QA_TIMEOUT=300
M1_DEFAULT=coef.M1_DEFAULT


def source_gate() -> int:
    pin=json.loads((HERE/PIN).read_text(encoding="utf-8"))
    require(pin.get("revision")==REV and pin.get("mesh_attempt_max")==1 and
            pin.get("physical_FEM") is False and
            pin.get("accepted_m1_sha256")==coef.M1_SHA and
            len(pin.get("files",{}))==18,
            "invalid P10DO package/source inventory")
    for name,expected in pin["files"].items():
        require("/" not in name and "\\" not in name and ".." not in name,
                "nonflat source inventory")
        path=HERE/name
        require(path.is_file() and sha256(path)==expected,
                "pinned source SHA mismatch: "+name)
    require(coef.check_source()==6, "P10DN source inventory is invalid")
    field=(HERE/GEO).read_text(encoding="utf-8")
    base=(HERE/"sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    require('Include "sphere_pore_B6_refined.geo";' in field and
            'Field[6].F = "F2*exp(log(1-0.2*F5)/3)";' in field and
            "Background Field=6;" in field and
            "Field[2] = Threshold;" in base and
            "Mesh.ElementOrder=2;" in base,
            "wrong M1 base field, M2 coefficient or Tet10 geometry")
    return len(pin["files"])


def user_marker() -> Path:
    root=os.environ.get("LOCALAPPDATA","")
    require(root and Path(root).is_dir(), "Windows LOCALAPPDATA unavailable")
    return Path(root)/"Stage3D07"/("P10DO_M2_MESH_"+coef.M1_SHA+".json")


def confirm_m1_path(arg: Path | None) -> Path:
    if arg:
        return arg
    print("M1 is the ORIGINAL accepted P10DG M1, not H0/U0 or a new mesh.")
    print("Default:",M1_DEFAULT)
    answer=input("Full ORIGINAL P10DG_M1_CANDIDATE.msh path (Enter=default): ").strip()
    return Path(answer.strip('"').strip("'")) if answer else M1_DEFAULT


def preflight(m1: Path, run_dir: Path) -> dict:
    require(os.name=="nt", "native Gmsh mesh-only permitted ONLY on Windows")
    root=str(HERE).casefold()
    old=str(Path(r"G:\ildar\Stage3D07")).casefold()
    require(root!=old and not root.startswith(old+"\\"),
            "extract P10DO in NEW folder OUTSIDE historical G:\\ildar\\Stage3D07")
    count=source_gate()
    require(not MARKER.exists(), "P10DO package one-shot already consumed")
    marker=user_marker()
    require(not marker.exists(), "P10DO per-M1 one-shot already consumed")
    # Checked even before native Gmsh version/parse. The raw original file is
    # NEVER altered and old P10DG/P10DL one-shot markers are never accessed.
    require(m1.is_file() and m1.name==coef.M1_NAME and
            sha256(m1)==coef.M1_SHA,
            "exact original D-019 M1.msh absent or SHA/basename mismatch")
    gmsh=Path(os.environ.get("P10DO_GMSH_EXE",
                            r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    require(gmsh.is_file(), "native Gmsh 4.15.2 not found: "+str(gmsh))
    v=command([str(gmsh),"-version"],HERE,timeout=15)
    require(v.returncode==0 and re.search(r"(?<![0-9])4\.15\.2(?![0-9])",
                                          v.stdout+v.stderr) is not None,
            "native Gmsh version/exit !=4.15.2/0")
    ram=free_windows_ram()
    disk=shutil.disk_usage(HERE).free
    require(ram>=16*1024**3 and disk>=4*1024**3,
            "require >=16GiB available RAM and >=4GiB free output space")
    unit=command([sys.executable,str(HERE/"P10DO_m2_mesh_qa.py"),"--selftest"],
                 HERE,timeout=120)
    require(unit.returncode==0 and
            "P10DO_M2_MESH_QA_SYNTHETIC_OK" in unit.stdout,
            "P10DO 27QP/field synthetic audit failed: "+unit.stdout[-400:]+unit.stderr[-400:])
    # Gmsh official -parse_and_exit parses a GEO without building -3 mesh.
    parsed=command([str(gmsh),str(HERE/GEO),"-parse_and_exit"],HERE,timeout=120)
    parse_log=(parsed.stdout+parsed.stderr)
    require(parsed.returncode==0 and not re.search(r"(?im)^\s*Error\s*:",parse_log),
            "native source-only GEO parse failed; no one-shot attempt consumed: "+
            parse_log[-350:])
    # Label EVERY accepted M1 Tet10 now, source-only, separately from any M2.
    label=coef.label_m1(m1,run_dir/"M1_LABEL")
    return {
        "source_pin_count":count,
        "m1_path":str(m1),"m1_sha256":coef.M1_SHA,
        "m1_label_dir":str(label),
        "gmsh_path":str(gmsh),"gmsh_sha256":sha256(gmsh),
        "gmsh_version_stdout":(v.stdout+v.stderr).strip(),
        "native_GEO_parse_exit":parsed.returncode,
        "native_GEO_parse_log_tail":parse_log[-1500:],
        "available_RAM_before_bytes":ram,
        "available_disk_before_bytes":disk,
        "synthetic_QA_stdout_tail":unit.stdout[-2000:],
    }


def launch(meta: dict, run_dir: Path, mesh: Path) -> dict:
    argv=[meta["gmsh_path"],str(HERE/GEO),"-3","-nt","2",
          "-format","msh2","-o",str(mesh)]
    meta["native_Gmsh_argv"]=argv
    marker=user_marker()
    marker.parent.mkdir(parents=True,exist_ok=True)
    mark={"protocol":REV,"utc":datetime.now(timezone.utc).isoformat(),
          "m1_sha256":coef.M1_SHA,"m2_run_dir":str(run_dir),"argv":argv}
    # Both markers are immutable. Once either exists, no retry automatically.
    with marker.open("x",encoding="utf-8") as f:
        json.dump(mark,f,indent=2)
    with MARKER.open("x",encoding="utf-8") as f:
        json.dump(mark,f,indent=2)
    started=time.monotonic()
    peak=0
    log=run_dir/"P10DO_GMSH_FULL_LOG_LOCAL.txt"
    with log.open("w",encoding="utf-8") as output:
        child=subprocess.Popen(argv,cwd=str(HERE),stdin=subprocess.DEVNULL,
                               stdout=output,stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                elapsed=time.monotonic()-started
                peak=max(peak,child_private_bytes(child))
                if elapsed>WALL_LIMIT:
                    raise RuntimeError("P10DO_STOP_GMSH_WALL_900S")
                if peak>PRIVATE_LIMIT:
                    raise RuntimeError("P10DO_STOP_GMSH_PRIVATE_8GIB")
                if mesh.is_file() and mesh.stat().st_size>MSH_LIMIT:
                    raise RuntimeError("P10DO_STOP_GMSH_MSH_750MIB")
                if log.stat().st_size>LOG_LIMIT:
                    raise RuntimeError("P10DO_STOP_GMSH_LOG_30MIB")
                time.sleep(.5)
            require(child.returncode==0,"native Gmsh exit "+str(child.returncode))
        except BaseException:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=15)
            raise
    require(mesh.is_file() and 0<mesh.stat().st_size<=MSH_LIMIT,
            "Gmsh exited without valid bounded M2.msh")
    return {"native_exit_code":child.returncode,
            "Gmsh_wall_seconds":time.monotonic()-started,
            "peak_private_bytes_polled":peak,
            "m2_mesh_path":str(mesh),"m2_mesh_bytes":mesh.stat().st_size,
            "m2_mesh_sha256":sha256(mesh)}


def evidence(run_dir: Path) -> Path:
    full=run_dir/"P10DO_GMSH_FULL_LOG_LOCAL.txt"
    if full.is_file():
        with full.open("rb") as f:
            f.seek(max(0,full.stat().st_size-80*1024))
            tail=f.read().decode("utf-8",errors="replace")
        (run_dir/"P10DO_GMSH_LOG_TAIL.txt").write_text(tail,encoding="utf-8")
    small=("P10DO_RUN_MANIFEST.json","P10DO_RESULT.txt",
           "P10DO_STOP_TRACE.txt","P10DO_GMSH_LOG_TAIL.txt",
           "P10DO_QA_STDOUT_STDERR.txt",
           "QA/P10DO_M1_M2_GEOMETRY_QA.json",
           "QA/P10DO_M1_M2_9_ZONES.csv",
           "QA/P10DO_M1_M2_9_ZONE_VOLUME_COMPARISON.csv")
    zpath=run_dir/"P10DO_EVIDENCE.zip"
    with zipfile.ZipFile(zpath,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for rel in small:
            path=run_dir/rel
            if path.is_file():
                z.write(path,rel)
        for summary in run_dir.glob("M1_LABEL/*/P10DN_M1_COEFFICIENT_SUMMARY.json"):
            z.write(summary,"P10DO_M1_COEFFICIENT_SUMMARY.json")
    return zpath


def do_run(preflight_only: bool=False, mesh_arg: Path | None=None) -> int:
    RUNS.mkdir(parents=True,exist_ok=True)
    run_dir=RUNS/("P10DO_M2_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run_dir.mkdir(exist_ok=False)
    meta={"protocol":REV,"status":"P10DO_STOP_NO_FEM",
          "physical_FEM_runs":0,"mesh_only":True,"m2_source":"P10DN_C1_KAPPA20",
          "target_volume_ratio_range":[.8,1.0],
          "Gmsh_attempt_limit":1,"wall_limit_s":WALL_LIMIT,
          "private_limit_bytes":PRIVATE_LIMIT,"mesh_limit_bytes":MSH_LIMIT,
          "started_utc":datetime.now(timezone.utc).isoformat()}
    code=2
    try:
        m1=confirm_m1_path(mesh_arg)
        meta.update(preflight(m1,run_dir))
        print("P10DO PREFLIGHT PASS: original M1 exact SHA, all 9736 Tet10 labelled,")
        print("source pin, Gmsh4.15.2 native GEO parse, 27QP synthetic, RAM/disk.")
        print("Target volume V_M2/V_M1 = 1 - 0.20*kappa; kappa C1 in [0,1].")
        if preflight_only:
            meta["status"]="P10DO_READ_ONLY_M1_LABEL_AND_GEO_PARSE_OK"
            code=0
        else:
            print("Single Gmsh M2 mesh-only; NO FEM; 900s wall/8GiB private/750MiB mesh.")
            print("No M2 mesh will start until you type the EXACT phrase.")
            answer=input("Type exactly RUN ONE P10DO M2 MESH: ").strip()
            require(answer==CONFIRM,"manual one-shot phrase not confirmed; no marker")
            mesh=run_dir/"P10DO_M2_CANDIDATE.msh"
            meta.update(launch(meta,run_dir,mesh))
            qa_path=run_dir/"P10DO_QA_STDOUT_STDERR.txt"
            with qa_path.open("w",encoding="utf-8") as out:
                qa=subprocess.run([sys.executable,str(HERE/"P10DO_m2_mesh_qa.py"),
                                   "--m1",str(m1),"--m2",str(mesh),
                                   "--out",str(run_dir/"QA")],
                                  cwd=str(HERE),stdin=subprocess.DEVNULL,
                                  stdout=out,stderr=subprocess.STDOUT,
                                  timeout=QA_TIMEOUT,check=False)
            meta["qa_exit_code"]=qa.returncode
            require(qa.returncode==0,
                    "M2 geometry/curved27QP QA STOP; preserve original evidence")
            meta["status"]="P10DO_M2_GEOMETRY_QA_OK_NO_FEM"
            code=0
    except BaseException as exc:
        meta["stop_reason"]=str(exc)
        print("P10DO STOP:",exc)
        (run_dir/"P10DO_STOP_TRACE.txt").write_text(
            traceback.format_exc(),encoding="utf-8")
    finally:
        meta["finished_utc"]=datetime.now(timezone.utc).isoformat()
        (run_dir/"P10DO_RUN_MANIFEST.json").write_text(
            json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        lines=["RESULT="+meta["status"],"FEM_RUNS=0",
               "M2_MSH_NOT_UPLOADED=1",
               "M1_SHA256="+str(meta.get("m1_sha256","UNKNOWN")),
               "M2_SHA256="+str(meta.get("m2_mesh_sha256","UNKNOWN")),
               "NATIVE_GMSH_EXIT="+str(meta.get("native_exit_code","UNKNOWN")),
               "QA_EXIT="+str(meta.get("qa_exit_code","UNKNOWN")),
               "STOP_REASON="+str(meta.get("stop_reason",""))]
        (run_dir/"P10DO_RESULT.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
        out=evidence(run_dir)
        print("RESULT:",meta["status"],"EVIDENCE:",out)
        print("Send ONLY P10DO_EVIDENCE.zip, keep old M1, new M2.msh and markers locally.")
    return code


def selftest() -> int:
    count=source_gate()
    require(coef.M1_NAME=="P10DG_M1_CANDIDATE.msh" and
            coef.MAX_VOLUME_REDUCTION==.2 and WALL_LIMIT==900 and
            PRIVATE_LIMIT==8*1024**3 and CONFIRM=="RUN ONE P10DO M2 MESH",
            "incorrect M1, target field or resource limits")
    proc=command([sys.executable,str(HERE/"P10DO_m2_mesh_qa.py"),"--selftest"],
                 HERE,timeout=120)
    require(proc.returncode==0 and "P10DO_M2_MESH_QA_SYNTHETIC_OK" in proc.stdout,
            "isolated 27QP+κ selftest failed: "+proc.stdout[-500:]+proc.stderr[-500:])
    print("P10DO_M2_PACKAGE_SELFTEST_OK source_sha",count,
          "full27QP=PASS kappa=PASS no_Gmsh=1 FEM=0")
    return 0


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--selftest",action="store_true")
    parser.add_argument("--preflight-only",action="store_true")
    parser.add_argument("--m1",type=Path)
    args=parser.parse_args()
    if args.selftest:
        require(not args.preflight_only and args.m1 is None,"selftest isolated")
        return selftest()
    return do_run(preflight_only=args.preflight_only,mesh_arg=args.m1)


if __name__=="__main__":
    raise SystemExit(main())
