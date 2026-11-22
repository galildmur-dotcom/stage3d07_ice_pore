#!/usr/bin/env python3
"""P10EA R1: safe source-only preflight, optionally ONE independent M2 Gmsh -3.

The old P10DO/-3 and P10DW/-1 one-shots are consumed and NEVER reused.
This program does not contain a FEM, forward, adjoint or cache operation.
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

import P10DN_m2_coefficient as coefficient
import P10DV_inline_source_unit as exact_math
import P10EA_m2_mesh_qa as mesh_qa
from P10DO_windows_guards import child_private_bytes, command, free_windows_ram, sha256

REV = "P10EA_R1_EXACT_INLINE_F6_ONE_M2_3D_MESH_ONLY"
HERE = Path(__file__).resolve().parent
RUNS = HERE / "P10EA_RUNS"
PROOF = RUNS / "P10EA_PREFLIGHT_PASS.json"
LOCAL_MARKER = RUNS / "P10EA_ONE_M2_3D_USED.json"
PIN = HERE / "P10EA_SOURCE_SHA256.json"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
F6_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
CONFIRM = "RUN ONE P10EA M2 3D MESH"
WALL_S = 900
QA_WALL_S = 300
PRIVATE_MAX = 8 * 1024**3
MESH_MAX = 750 * 1024**2
LOG_MAX = 16 * 1024**2
QA_LOG_MAX = 4 * 1024**2
PREFLIGHT_MAX_AGE = timedelta(hours=24)
PIN_FILE_COUNT = 23


def stop_if_false(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError("P10EA_STOP: " + reason)


def source_gate() -> dict:
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    stop_if_false(
        pin.get("revision") == REV and pin.get("one_native_3d_max") == 1 and
        pin.get("physical_FEM") is False and
        pin.get("accepted_original_m1_sha256") == M1_SHA and
        pin.get("exact_inline_f6_sha256") == F6_SHA and
        pin.get("cad_geo_sha256") == CAD_SHA and
        pin.get("gmsh_executable_sha256") == GMSH_SHA and
        len(pin.get("files", {})) == PIN_FILE_COUNT,
        "revision, source inventory, M1 or native executable SHA")
    for name, expected in pin["files"].items():
        stop_if_false(name == Path(name).name and ".." not in name and
                      (HERE/name).is_file() and sha256(HERE/name) == expected,
                      "modified source: " + name)
    stop_if_false(sha256(HERE/"P10DV_M2_INLINE_FIELD20.geo") == F6_SHA and
                  sha256(HERE/"sphere_pore_B6_refined.geo") == CAD_SHA,
                  "exact original F6 or CAD")
    exact_math.source_gate()
    stop_if_false(coefficient.check_source() == 6, "original P10DN source SHA")
    return pin


def geometry_contract() -> tuple[str, str]:
    exact = (HERE/"P10DV_M2_INLINE_FIELD20.geo").read_text(encoding="utf-8")
    original = (HERE/"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    cad = (HERE/"sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    baseline = original.split("// F3:", 1)[0] + "\nBackground Field=2;\n"
    stop_if_false(
        exact == exact_math.candidate_geo_text() and
        exact.count('Field[6] = MathEval;') == 1 and
        exact.count('Background Field=6;') == 1 and
        all(f'Field[{n}] = MathEval;' not in exact for n in (3, 4, 5)) and
        re.findall(r'\bF\d+\b', exact.split('Field[6].F = "', 1)[1]) == ["F2"] and
        'Field[2] = Threshold;' in cad and 'Mesh.ElementOrder=2;' in cad and
        original.count("// F3:") == 1 and
        baseline.endswith("Background Field=2;\n") and
        'Field[6]' not in baseline,
        "nonflattened expression, incorrect Threshold or geometry")
    return baseline, exact


def global_marker() -> Path:
    appdata = os.environ.get("LOCALAPPDATA", "")
    stop_if_false(bool(appdata) and Path(appdata).is_dir(),
                  "LOCALAPPDATA unavailable")
    return Path(appdata)/"Stage3D07"/("P10EA_M2_3D_"+M1_SHA+".json")


def marker_clear() -> None:
    stop_if_false(not LOCAL_MARKER.exists() and not global_marker().exists(),
                  "P10EA one-shot consumed; NEVER delete either marker or rerun")


def fresh_proof() -> dict:
    stop_if_false(PROOF.is_file(), "run button 01 successfully before button 02")
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    checked = datetime.fromisoformat(proof["checked_utc"])
    stop_if_false(
        checked.tzinfo is not None and
        timedelta(0) <= datetime.now(timezone.utc)-checked <= PREFLIGHT_MAX_AGE and
        proof.get("revision") == REV and
        proof.get("m1_sha256") == M1_SHA and
        proof.get("f6_sha256") == F6_SHA and
        proof.get("gmsh_sha256") == GMSH_SHA and
        proof.get("native_parse_passed") == ["A_ORIGINAL_M1_FIELD2", "B_EXACT_INLINE_F6"],
        "preflight proof identity/24h freshness failed")
    return proof


def original_m1_path(prompt: bool) -> Path:
    if prompt:
        print("Original accepted P10DG M1 ONLY; H0, U0 and new M1 forbidden.")
        print("Default:", coefficient.M1_DEFAULT)
        response = input("Original P10DG_M1_CANDIDATE.msh path (Enter=default): ").strip()
        selected = Path(response.strip('"').strip("'")) if response else coefficient.M1_DEFAULT
    else:
        selected = Path(fresh_proof()["m1_path"])
    stop_if_false(selected.is_file() and selected.name == coefficient.M1_NAME and
                  sha256(selected) == M1_SHA,
                  "original accepted M1 path, SHA or basename mismatch")
    return selected


def write_generated_geo(run: Path) -> dict[str, Path]:
    baseline, exact = geometry_contract()
    folder = run/"GEO"
    folder.mkdir(exist_ok=False)
    shutil.copyfile(HERE/"sphere_pore_B6_refined.geo",
                    folder/"sphere_pore_B6_refined.geo")
    a = folder/"A_ORIGINAL_M1_FIELD2.geo"
    b = folder/"B_EXACT_INLINE_F6.geo"
    # Explicit UTF-8 bytes: Path.write_text would turn LF into CRLF on Windows,
    # reproducing the already identified P10DW R1 false-SHA STOP.
    a.write_bytes(baseline.encode("utf-8"))
    b.write_bytes(exact.encode("utf-8"))
    stop_if_false(sha256(b) == F6_SHA and sha256(folder/"sphere_pore_B6_refined.geo") == CAD_SHA,
                  "generated exact inline F6/CAD changed on Windows")
    return {"A_ORIGINAL_M1_FIELD2": a, "B_EXACT_INLINE_F6": b}


def preflight(run: Path, meta: dict, *, prompt: bool) -> dict[str, Path]:
    stop_if_false(os.name == "nt", "Windows required; native Gmsh never runs on Linux")
    here_text = str(HERE).casefold()
    old = str(Path(r"G:\ildar\Stage3D07")).casefold()
    stop_if_false(here_text != old and not here_text.startswith(old+"\\"),
                  "extract into a NEW folder OUTSIDE G:\\ildar\\Stage3D07")
    pin = source_gate()
    math = exact_math.math_selftest()
    mesh_qa.selftest()  # 27QP, folded Tet10 negative, 9 zones, wrong-M1 guard
    marker_clear()
    m1 = original_m1_path(prompt)
    exe = Path(os.environ.get("P10EA_GMSH_EXE",
                              r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    stop_if_false(exe.is_file() and sha256(exe) == GMSH_SHA,
                  "native Gmsh4.15.2 EXE exact SHA mismatch")
    version = command([str(exe), "-version"], HERE, timeout=15)
    stop_if_false(version.returncode == 0 and
                  re.search(r"(?<!\d)4\.15\.2(?!\d)",version.stdout+version.stderr) is not None,
                  "native Gmsh version !=4.15.2 or nonzero exit")
    ram, disk = free_windows_ram(), shutil.disk_usage(HERE).free
    stop_if_false(ram >= 16*1024**3 and disk >= 4*1024**3,
                  "need >=16GiB available RAM and >=4GiB free disk")
    sources = write_generated_geo(run)
    meta.update({"source_sha_pins":len(pin["files"]), "math_points":math["points"],
                 "m1_path":str(m1), "m1_sha256":M1_SHA,
                 "gmsh_path":str(exe), "gmsh_sha256":GMSH_SHA,
                 "free_ram_bytes":ram, "free_disk_bytes":disk,
                 "generated_geo_sha256":{key:sha256(value) for key,value in sources.items()}})
    for key, path in sources.items():
        meta["native_parse_attempts"] += 1
        result = command([str(exe),str(path),"-parse_and_exit"],path.parent,timeout=20)
        log = (result.stdout+result.stderr)
        (run/(key+"_PARSE.log")).write_bytes(log.encode("utf-8",errors="replace")[:LOG_MAX])
        stop_if_false(result.returncode == 0 and
                      not re.search(r"(?im)^\s*Error\s*:",log),
                      "native GEO parse STOP: "+key+" / "+log[-250:])
        meta["native_parse_passed"].append(key)
    label_dir = coefficient.label_m1(m1, run/"M1_LABEL")
    meta["m1_label_dir"] = str(label_dir)
    stop_if_false(math["points"] == 17075, "full exact field math sample count")
    return sources


def save_proof(meta: dict, run: Path) -> None:
    stop_if_false(meta["native_parse_passed"] ==
                  ["A_ORIGINAL_M1_FIELD2","B_EXACT_INLINE_F6"],
                  "both real native GEO parse passes required")
    data = {"revision":REV,"checked_utc":datetime.now(timezone.utc).isoformat(),
            "run_id":run.name,"m1_path":meta["m1_path"],"m1_sha256":M1_SHA,
            "f6_sha256":F6_SHA,"gmsh_sha256":GMSH_SHA,
            "native_parse_passed":meta["native_parse_passed"]}
    PROOF.write_bytes((json.dumps(data,indent=2)+"\n").encode("utf-8"))


def consume_one_shot(run: Path, argv: list[str]) -> None:
    marker_clear()
    data = {"revision":REV, "mode":"ONE_NATIVE_GMSH_3D_M2_MESH_ONLY",
            "run_id":run.name, "consumed_utc":datetime.now(timezone.utc).isoformat(),
            "m1_sha256":M1_SHA, "argv":argv}
    global_path = global_marker()
    global_path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive, permanent marker creation immediately BEFORE the only -3 Popen.
    # Any partial failure consumes the one-shot. Never remove markers.
    with global_path.open("x", encoding="utf-8") as handle:
        json.dump(data,handle,indent=2)
    with LOCAL_MARKER.open("x", encoding="utf-8") as handle:
        json.dump(data,handle,indent=2)


def bounded_process(argv: list[str], *, cwd: Path, log: Path, seconds: int,
                    private: int, output_limit: int, mesh: Path | None = None) -> dict:
    started = time.monotonic()
    status, peak, rc = "STARTED", 0, None
    with log.open("x", encoding="utf-8") as stream:
        child = subprocess.Popen(argv,cwd=str(cwd),stdin=subprocess.DEVNULL,
                                 stdout=stream,stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                peak = max(peak, child_private_bytes(child))
                if time.monotonic()-started > seconds:
                    status = "WALL_LIMIT"
                elif peak > private:
                    status = "PRIVATE_LIMIT"
                elif log.stat().st_size > output_limit:
                    status = "LOG_LIMIT"
                elif mesh is not None and mesh.is_file() and mesh.stat().st_size > MESH_MAX:
                    status = "MSH_LIMIT"
                if status != "STARTED":
                    child.kill()
                    break
                time.sleep(.2)
            child.wait(timeout=15)
            rc = child.returncode
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=15)
    # A process that exited between 200ms polls may have a larger unobserved peak.
    return {"status":status,"exit_code":rc,"polled_wall_s":time.monotonic()-started,
            "polled_peak_private_bytes":peak,"log_bytes":log.stat().st_size,
            "argv":argv}


def launch_m2(meta: dict, run: Path, geo: Path) -> Path:
    mesh, log = run/"P10EA_M2_CANDIDATE.msh", run/"P10EA_GMSH_FULL.log"
    argv = [meta["gmsh_path"],str(geo),"-3","-nt","2","-format","msh2",
            "-o",str(mesh)]
    # No source/QA/unit operations between marker consumption and native launch.
    consume_one_shot(run, argv)
    meta["native_3d_attempts"] = 1
    native = bounded_process(argv,cwd=geo.parent,log=log,seconds=WALL_S,
                             private=PRIVATE_MAX,output_limit=LOG_MAX,mesh=mesh)
    meta["native_3d_result"] = native
    stop_if_false(native["status"] == "STARTED" and native["exit_code"] == 0,
                  "bounded Gmsh M2 STOP: "+str(native))
    stop_if_false(mesh.is_file() and 0 < mesh.stat().st_size <= MESH_MAX,
                  "M2 MSH missing/empty/over 750MiB")
    log_bytes = log.read_bytes()
    log_text = log_bytes.decode("utf-8",errors="replace")
    stop_if_false(b"Done meshing 3D" in log_bytes and
                  not re.search(r"(?im)^\s*Error\s*:",log_text),
                  "native Gmsh log missing 3D completion or contains Error")
    meta["m2_mesh_sha256"] = sha256(mesh)
    meta["m2_mesh_bytes"] = mesh.stat().st_size
    return mesh


def quality_gate(meta: dict, run: Path, m1: Path, m2: Path) -> None:
    argv = [sys.executable,str(HERE/"P10EA_m2_mesh_qa.py"),
            "--m1",str(m1),"--m2",str(m2),"--out",str(run/"QA")]
    result = bounded_process(argv,cwd=HERE,log=run/"P10EA_QA.log",
                             seconds=QA_WALL_S,private=PRIVATE_MAX,
                             output_limit=QA_LOG_MAX)
    meta["quality_audit_result"] = result
    stop_if_false(result["status"]=="STARTED" and result["exit_code"]==0,
                  "M2 curved27QP/CAD/pore/9-zone QA STOP: "+str(result))
    summary = run/"QA"/"P10EA_M1_M2_GEOMETRY_QA.json"
    stop_if_false(summary.is_file(), "full geometry QA JSON absent")
    report = json.loads(summary.read_text(encoding="utf-8"))
    stop_if_false(report["status"]=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM" and
                  report["m1_sha256"]==M1_SHA and
                  report["m2_sha256"]==meta["m2_mesh_sha256"] and
                  not report["geometry_issues"],
                  "M2 geometry QA/mesh SHA mismatch")
    meta["geometry_qa_status"] = report["status"]


def make_evidence(run: Path) -> Path:
    archive = run/"P10EA_EVIDENCE.zip"
    names = ["P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt","P10EA_STOP_TRACE.txt",
             "P10EA_GMSH_FULL.log","P10EA_GMSH_TAIL.txt","P10EA_QA.log",
             "A_ORIGINAL_M1_FIELD2_PARSE.log","B_EXACT_INLINE_F6_PARSE.log",
             "QA/P10EA_M1_M2_GEOMETRY_QA.json",
             "QA/P10EA_M1_M2_9_ZONES.csv",
             "QA/P10EA_M1_M2_9_ZONE_VOLUME_COMPARISON.csv"]
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for name in names:
            f = run/name
            if f.is_file() and f.stat().st_size <= max(LOG_MAX,QA_LOG_MAX):
                z.write(f,name)
        geo = run/"GEO"
        if geo.is_dir():
            for f in sorted(geo.glob("*.geo")):
                z.write(f,"GEO/"+f.name)
        for f in run.glob("M1_LABEL/*/P10DN_M1_COEFFICIENT_SUMMARY.json"):
            z.write(f,"P10EA_M1_LABEL_SUMMARY.json")
    return archive


def do_run(*, preflight_only: bool) -> int:
    RUNS.mkdir(parents=True,exist_ok=True)
    run = RUNS/("P10EA_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta = {"revision":REV,"status":"P10EA_STOP_NO_FEM",
            "mode":"SOURCE_ONLY_PREFLIGHT" if preflight_only else "ONE_M2_3D",
            "original_m1_sha256":M1_SHA,"f6_sha256":F6_SHA,
            "kappa_C1_range":[0.,1.],
            "target_local_volume_ratio":"1-0.20*kappa; not guaranteed per realized Tet10",
            "native_parse_attempts":0,"native_parse_passed":[],
            "native_1d_2d_attempts":0,"native_3d_attempts":0,
            "physical_FEM_attempts":0,"wall_limit_s":WALL_S,
            "qa_limit_s":QA_WALL_S,"private_limit_bytes":PRIVATE_MAX,
            "mesh_limit_bytes":MESH_MAX,"log_limit_bytes":LOG_MAX,
            "started_utc":datetime.now(timezone.utc).isoformat()}
    code = 2
    try:
        if not preflight_only:
            fresh_proof()  # button 01 must have completed within 24h
        sources = preflight(run,meta,prompt=preflight_only)
        print("P10EA PREFLIGHT PASS: exact M1 SHA, F6, native parse2/2, "
              "math17075, synthetic27QP, all M1 Tet10 labelled.",flush=True)
        if preflight_only:
            save_proof(meta,run)
            meta["status"] = "P10EA_SAFE_PREFLIGHT_PASS_NO_M2_NO_FEM"
            code = 0
        else:
            print("ONE new M2 -3; <=900s, <=8GiB PRIVATE, <=750MiB MSH, "
                  "<=16MiB Gmsh log, -nt 2; NO FEM.",flush=True)
            answer = input("Type exactly "+CONFIRM+": ").strip()
            stop_if_false(answer == CONFIRM,
                          "manual confirmation absent; no marker consumed")
            mesh = launch_m2(meta,run,sources["B_EXACT_INLINE_F6"])
            quality_gate(meta,run,Path(meta["m1_path"]),mesh)
            meta["status"] = "P10EA_M2_GEOMETRY_QA_OK_NO_FEM"
            code = 0
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        (run/"P10EA_STOP_TRACE.txt").write_text(
            traceback.format_exc(),encoding="utf-8")
        print("P10EA STOP:",exc,flush=True)
    finally:
        full = run/"P10EA_GMSH_FULL.log"
        if full.is_file():
            with full.open("rb") as stream:
                stream.seek(max(0,full.stat().st_size-80*1024))
                tail = stream.read()
            (run/"P10EA_GMSH_TAIL.txt").write_bytes(tail)
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run/"P10EA_RUN_MANIFEST.json").write_text(
            json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        (run/"P10EA_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nNATIVE_M2_3D_ATTEMPTS="+
            str(meta["native_3d_attempts"])+"\nFEM=0\n"+
            "M1_SHA256="+M1_SHA+"\nM2_SHA256="+
            str(meta.get("m2_mesh_sha256","UNKNOWN"))+"\n"+
            "STOP_REASON="+str(meta.get("stop_reason",""))+"\n",encoding="utf-8")
        evidence = make_evidence(run)
        print("P10EA RESULT:",meta["status"],"EVIDENCE:",evidence,flush=True)
        print("Send ONLY P10EA_EVIDENCE.zip. Keep M2 .msh and all markers locally. "
              "Never rerun 02.",flush=True)
    return code


def selftest() -> int:
    pin = source_gate()
    baseline, inline = geometry_contract()
    math = exact_math.math_selftest()
    mesh_qa.selftest()
    argv = ["gmsh.exe","input.geo","-3","-nt","2","-format","msh2","-o","out.msh"]
    stop_if_false(len(pin["files"])==PIN_FILE_COUNT and
                  baseline.endswith("Background Field=2;\n") and
                  inline.encode("utf-8")==(HERE/"P10DV_M2_INLINE_FIELD20.geo").read_bytes() and
                  math["points"]==17075 and
                  WALL_S==900 and PRIVATE_MAX==8*1024**3 and
                  MESH_MAX==750*1024**2 and argv.count("-3")==1,
                  "source-only field, resource or single -3 contract")
    print("P10EA_SOURCE_M2_PACKAGE_SELFTEST_OK PIN23 math17075 curved27QP=PASS "
          "negative_folded=STOP 3D_Gmsh_runs=0 FEM=0")
    return 0


def main() -> int:
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--selftest",action="store_true")
    modes.add_argument("--preflight-only",action="store_true")
    modes.add_argument("--one-m2",action="store_true")
    args=parser.parse_args()
    return selftest() if args.selftest else do_run(preflight_only=args.preflight_only)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("P10EA STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
