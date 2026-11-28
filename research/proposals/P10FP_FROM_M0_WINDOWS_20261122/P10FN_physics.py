#!/usr/bin/env python3
"""Any approved M0..MN: fresh FEM+same-mesh analytic adjoint+signed 4D.

One click, no input, no H0 cache, no FD geometry. Sends back one evidence ZIP.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

from P10FN_common import (HERE, MESHES, RUNS, capped_process, load, need,
                          now, prepare_run, require_windows, sha256,
                          validate_source, write_new, zip_evidence)
from P10FN_mesh_qa import audit as mesh_audit
from P10FN_physics_audit import audit as physical_audit

APPROVALS = HERE / "approvals"
APP = HERE / "build" / "stage3d10fn_any_mesh_full4d.exe"
REGIME = {"steps": 6, "dt": 150, "cutoff_mm": 5, "threads": 4,
          "law": "EDV_VAR", "xi": 0, "B6_mm": 5}
CSV = ("P10DD_SIGNED_R_THETA_PHI_T.csv", "P10DD_FULL4D_CLOSURE_AUDIT.csv",
       "P10W_ANALYTIC_ADJOINT.csv", "P10W_COMPONENTS.csv", "P10W_STEP_COMPONENTS.csv")


def approvals(*, allow_empty=False):
    records = {}
    for item in APPROVALS.glob("M*.json"):
        data = load(item)
        mesh = data.get("mesh")
        if not re.fullmatch(r"M(0|[1-9][0-9]*)",str(mesh)) or item.stem != mesh:
            raise RuntimeError("invalid approval mesh name: " + str(item))
        need(data.get("status") == "RESEARCHER_APPROVED_FOR_PHYSICS" and
             re.fullmatch("[0-9a-f]{64}", data.get("mesh_sha256", "")) is not None and
             data.get("regime") == REGIME,
             "invalid/mismatched researcher approval: " + str(item))
        records[mesh] = data
    if not allow_empty:
        need(records, "no researcher-approved SHA mesh yet; send geometry evidence first")
    return records


def compiler():
    search = []
    env = os.environ.get("P10FN_GPP", "")
    if env:
        search.append(Path(env))
    on_path = shutil.which("g++")
    if on_path:
        search.append(Path(on_path))
    for qt in (Path(r"C:\Qt\Tools"), Path(r"G:\Qt\Tools")):
        if qt.is_dir():
            search.extend(qt.glob("mingw*/bin/g++.exe"))
    for base in (Path(r"C:\msys64\mingw64\bin\g++.exe"),
                 Path(r"C:\mingw64\bin\g++.exe")):
        search.append(base)
    for p in search:
        if p.is_file() and p.name.lower() == "g++.exe":
            return p
    raise RuntimeError("MinGW g++.exe unavailable; set P10FN_GPP to existing Qt Creator MinGW compiler path")


def compiler_environment(toolchain):
    """Qt MinGW's cc1plus.exe loads libwinpthread-1.dll from its own bin.

    A full path to g++.exe alone is insufficient: every subprocess involved
    in compilation must inherit this PATH, not just the final physics EXE.
    """
    env = os.environ.copy()
    env["PATH"] = str(toolchain.parent) + os.pathsep + env.get("PATH", "")
    return env


def ensure_binary():
    # Rebuild when any source inventory/compiler changed; pin EXE afterwards.
    toolchain = compiler()
    digest = sha256(HERE / "P10FN_SOURCE_SHA256.json")
    record = APP.with_suffix(".build.json")
    if APP.is_file() and record.is_file():
        metadata = load(record)
        if (metadata.get("source_inventory_sha256") == digest and
                metadata.get("compiler") == str(toolchain) and
                metadata.get("exe_sha256") == sha256(APP)):
            return toolchain, metadata
    APP.parent.mkdir(parents=True, exist_ok=True)
    build_dir = RUNS / "P10FN_BUILD"
    build_dir.mkdir(parents=True, exist_ok=True)
    log = build_dir / ("P10FN_BUILD_"+now()+".txt")
    temp_exe = APP.parent / "p10fn_build_candidate.exe"
    need(not temp_exe.exists(), "unfinished previous build candidate; inspect build log")
    command = [str(toolchain), "-std=c++20", "-O2", "-fopenmp",
               '-DSTAGE3D10K_SOURCE_ROOT="'+str(HERE).replace("\\", "/")+'"',
               "-I", str(HERE/"src"), "-I", str(HERE/"tests"),
               "-I", str(HERE), str(HERE/"stage3d10fn_any_mesh_full4d.cpp"),
               str(HERE/"src"/"win_process_memory.cpp"), "-lpsapi",
               "-o", str(temp_exe)]
    env = compiler_environment(toolchain)
    print("P10FR_COMPILING: Qt MinGW bin added to PATH:", toolchain.parent, flush=True)
    print("P10FR_COMPILER_LOG:", log, flush=True)
    with log.open("x", encoding="utf-8") as sink:
        result = subprocess.run(command, cwd=HERE, env=env, stdin=subprocess.DEVNULL,
                                stdout=sink, stderr=subprocess.STDOUT,
                                timeout=900, check=False)
    need(result.returncode == 0 and temp_exe.is_file(), "MinGW compilation failed; see " + str(log))
    print("P10FR_COMPILE_SUCCESS: running EXE guard selftest", flush=True)
    checked = subprocess.run([str(temp_exe), "--selftest"], cwd=HERE, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=90, check=False)
    need(checked.returncode == 0 and "P10FN_ANY_MESH_GUARD_SELFTEST_OK" in checked.stdout,
         "selftest of new executable failed: " + checked.stdout[-500:])
    os.replace(temp_exe, APP)
    result = {"source_inventory_sha256": digest, "compiler": str(toolchain),
              "exe_sha256": sha256(APP), "selftest": checked.stdout[-1500:]}
    record.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return toolchain, result


def selftest():
    record = approvals(allow_empty=True)
    # The initial ZIP has no approvals, but the user MUST add M0.json after
    # P10FQ geometry GO. The check launcher must continue to pass then.
    if record:
        need("M0" in record and
             record["M0"].get("schema") == "P10FQ_FRESH_M0_GEOMETRY_GO_V1",
             "approval folder is not anchored in independently reviewed fresh M0")
    assert len(CSV) == 5 and REGIME["dt"] * REGIME["steps"] == 900
    example = Path("synthetic_bin") / "g++.exe"
    assert compiler_environment(example)["PATH"].split(os.pathsep)[0] == str(example.parent)
    print("P10FP_FRESH_SERIES_PHYSICS_SELFTEST_OK no_FEM=1 approved_meshes="+
          ",".join(sorted(record, key=lambda m:int(m[1:]))))


def run(mesh_arg, mode):
    require_windows()
    print("P10FR_PREFLIGHT: checking source SHA and M0 approval",flush=True)
    validate_source()
    approved = approvals()
    need("M0" in approved and
         approved["M0"].get("schema") == "P10FQ_FRESH_M0_GEOMETRY_GO_V1",
         "fresh-series root M0 approval missing; historical mesh approvals forbidden")
    need(mode in ("R", "tz", "y20"), "unsupported shape mode")
    if mesh_arg == "LATEST":
        options = [k for k in approved if (MESHES/(k+".msh")).is_file()]
        need(options, "no approved mesh file in G:/ildar/Stage3D07/meshes")
        mesh_arg = max(options, key=lambda k: int(k[1:]))
    need(mesh_arg in approved, "mesh is not yet approved for physics: " + mesh_arg)
    file = MESHES / (mesh_arg + ".msh")
    need(file.is_file(), "mesh must be saved at " + str(file))
    digest = sha256(file)
    need(digest == approved[mesh_arg]["mesh_sha256"],
         "mesh SHA does not match approved geometry (no FEM)")
    print("P10FR_PREFLIGHT: approved",mesh_arg,"SHA",digest,"; checking Tet10 curved geometry",flush=True)
    qa = mesh_audit(file)
    print("P10FR_PREFLIGHT: mesh QA PASS",qa["tet10"],"Tet10; locating/building MinGW solver",flush=True)
    toolchain, build = ensure_binary()
    marker = RUNS / "P10FN_LOCKS" / (f"PHYS_{mesh_arg}_{mode}_{digest[:16]}_{build['exe_sha256'][:12]}.json")
    need(not marker.exists(), "physical attempt already consumed for this mesh/mode/executable")
    folder = prepare_run("PHYSICS", mesh_arg+"_"+mode)
    result_dir = folder / ("P10FN_"+mesh_arg+"_"+mode+"_R1")
    manifest = {"protocol": "P10FN_ANY_APPROVED_MESH_V1", "status": "CONSUMED",
                "mesh": mesh_arg, "mesh_path": str(file), "mesh_sha256": digest,
                "mesh_qa": qa, "approval": approved[mesh_arg], "mode": mode,
                "parameters": REGIME, "executable_sha256": build["exe_sha256"],
                "compiler": str(toolchain), "fresh_forward": True,
                "reuse_forward": False, "started_utc": now(), "FEM_attempts": 1}
    # One-shot marker consumed before any native Popen. Never silently retry.
    write_new(marker, manifest)
    local_marker = folder / "P10FN_ONE_SHOT_CONSUMED.json"
    write_new(local_marker, manifest)
    cmd = [str(APP), "--p10fn-authorized", "--mesh", str(file),
           "--out", str(result_dir), "--mode", mode, "--steps", "6",
           "--dt", "150", "--cutoff-mm", "5", "--threads", "4"]
    env = os.environ.copy()
    env["PATH"] = str(toolchain.parent) + os.pathsep + env.get("PATH", "")
    env["P10FN_ONE_SHOT_MARKER"] = str(local_marker)
    log = folder / "P10FN_SOLVER_STDOUT_STDERR.txt"
    print("P10FR_FEM_START:", mesh_arg, mode,"; 6 x 150s, one-shot marker consumed",flush=True)
    try:
        manifest["command"] = cmd
        manifest.update(capped_process(cmd, cwd=HERE, log=log, wall_s=21600,
                                       memory_gib=40, output_dir=folder, output_gib=12, env=env))
        need(manifest["native_exit_code"] == 0 and not manifest["stop_reason"],
             "native solver exit/limits failed")
        for name in CSV:
            need((result_dir/name).is_file(), "missing physical output: " + name)
        manifest["independent_4d"] = physical_audit(result_dir, mesh_arg, qa["tet10"], mode)
        history = result_dir / "forward_history.bin"
        need(history.is_file(), "fresh forward history absent")
        manifest["history_sha256"] = sha256(history)
        manifest["status"] = "PHYSICS_REAL_4D_INDEPENDENT_CLOSURE_PASS"
    except BaseException as error:
        manifest["status"] = "PHYSICS_STOP_REVIEW_REQUIRED"
        manifest["error"] = repr(error)
        (folder/"P10FN_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        meta = folder / "P10FN_PHYSICS_MANIFEST.json"
        meta.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n",encoding="utf-8")
        evidence = folder / ("P10FN_"+mesh_arg+"_"+mode+"_PHYSICS_EVIDENCE.zip")
        zip_evidence(evidence, [(meta, meta.name), (log, log.name),
                                *[(result_dir/name, name) for name in CSV]])
    print("P10FN_PHYSICS_RESULT:", manifest["status"],flush=True)
    print("SEND THIS FILE:",evidence,flush=True)
    print("RAW FORWARD HISTORY PRESERVED:",result_dir,flush=True)
    return 0 if manifest["status"].endswith("_PASS") else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", default="LATEST")
    parser.add_argument("--mode", default="R")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            selftest()
        else:
            raise SystemExit(run(args.mesh, args.mode))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print("P10FN_PHYSICS_STOP:",error,file=sys.stderr)
        raise SystemExit(2)
