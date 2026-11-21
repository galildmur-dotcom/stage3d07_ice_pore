#!/usr/bin/env python3
"""P10DG R1: exactly ONE bounded Windows Gmsh M1 mesh, then geometry QA.

No physical FEM, no adaptive indicators, no modification of historical H0
or of an old P10DE one-shot marker. Preflight can safely STOP before launch.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

from P10DG_windows_guards import (
    child_private_bytes, command, free_windows_ram, require, sha256,
)

REV = "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY"
ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "P10DG_RUNS"
MARKER = RUNS / "P10DG_ONE_SHOT_USED.json"
H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
GMSH_VERSION = "4.15.2"
Q = .8 ** (1. / 3.)
CONFIRM = "RUN ONE P10DG M1 MESH"
MAX_WALL_S = 900
MAX_PRIVATE = 8 * 1024**3
MAX_MSH_BYTES = 750 * 1024**2
MAX_LOG_BYTES = 30 * 1024**2
QA_TIMEOUT_S = 300
GEO_NAME = "P10DF_M1_FROM_H0_EMPIRICAL_CALIBRATION_CANDIDATE.geo"
CALIBRATION_NAME = "P10DF_H0_EMPIRICAL_M1_SOURCE_CALIBRATION.json"
PINNED_NAME = "P10DG_PINNED_SHA256.json"


def source_gate() -> dict:
    pin = json.loads((ROOT / PINNED_NAME).read_text(encoding="utf-8"))
    require(pin["revision"] == REV and pin["mesh_attempt_max"] == 1 and
            pin["physical_FEM"] is False and len(pin["files"]) == 12,
            "invalid P10DG package revision or source inventory")
    for name, expected in pin["files"].items():
        path = ROOT / name
        require(path.is_file() and sha256(path) == expected,
                "package source SHA mismatch: " + name)
    base = (ROOT / "sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    candidate = (ROOT / GEO_NAME).read_text(encoding="utf-8")
    calib = json.loads((ROOT / CALIBRATION_NAME).read_text(encoding="utf-8"))
    require("Mesh.ElementOrder=2;" in base and
            "Background Field=2;" in base and
            "Field[2].SizeMin=nearSize;" in base and
            "Field[2].SizeMax=farSize;" in base and
            "Field[2].DistMin=0.0015;" in base and
            "Field[2].DistMax=0.018;" in base,
            "common CAD/size-threshold mismatch")
    require('Include "sphere_pore_B6_refined.geo";' in candidate and
            not re.search(r"(?m)^\s*(?:Field\[|Background Field|Mesh\.)", candidate),
            "candidate GEO contains an additional field or different base CAD")
    def read_number(name: str) -> float:
        m = re.search(r"(?m)^\s*" + re.escape(name) +
                      r"\s*=\s*([0-9.eE+-]+)\s*;", candidate)
        require(m is not None, "candidate missing " + name)
        return float(m.group(1))
    near = read_number("nearSize")
    far = read_number("farSize")
    require(calib["historical_h0_generator_command"] == "UNKNOWN" and
            calib["h0_exact_mesh_sha256"] == H0_SHA and
            calib["outcome"] == "CANDIDATE_GEO_SOURCE_ONLY_NO_GMSH_NO_FEM" and
            math.isclose(calib["q_target_linear"], Q, rel_tol=1e-13) and
            math.isclose(near, calib["proposed_nearSize_m"], rel_tol=1e-13) and
            math.isclose(far, calib["proposed_farSize_m"], rel_tol=1e-13) and
            .0003 < near < .0006 and .005 < far < .010,
            "candidate is not exact P10DF H0-based empirical source-only field")
    return pin["files"]


def preflight() -> dict:
    require(os.name == "nt", "Gmsh may run ONLY on Windows")
    root = str(ROOT).casefold()
    work = str(Path(r"G:\ildar\Stage3D07")).casefold()
    require(root != work and not root.startswith(work + "\\"),
            "extract P10DG OUTSIDE historical G:\\ildar\\Stage3D07")
    require(not MARKER.exists(), "P10DG one-shot marker already exists: NO retry")
    sources = source_gate()
    h0 = Path(os.environ.get("P10DG_H0_MSH", r"G:\ildar\Stage3D07\meshes\H0.msh"))
    require(h0.is_file() and sha256(h0) == H0_SHA,
            "historical H0.msh missing or SHA does not match")
    gmsh = Path(os.environ.get("P10DG_GMSH_EXE",
                               r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    require(gmsh.is_file(), "native Gmsh 4.15.2 EXE missing: " + str(gmsh))
    version = command([str(gmsh), "-version"], ROOT, timeout=15)
    require(version.returncode == 0 and
            re.search(r"(?<![0-9])4\.15\.2(?![0-9])",
                      version.stdout + version.stderr) is not None,
            "native Gmsh version/exit !=4.15.2/0")
    ram = free_windows_ram()
    disk = shutil.disk_usage(ROOT).free
    require(ram >= 16 * 1024**3 and disk >= 4 * 1024**3,
            "need >=16GiB available physical RAM and >=4GiB free output disk")
    unit = command([sys.executable, str(ROOT / "P10DG_compare_m1.py"),
                    "--selftest"], ROOT, timeout=QA_TIMEOUT_S)
    require(unit.returncode == 0 and "P10DG_QA_SYNTHETIC_OK" in unit.stdout,
            "P10DG full27QP QA synthetic STOP: " + unit.stdout[-400:] + unit.stderr[-400:])
    return {
        "package_sources_sha256": sources,
        "h0_path": str(h0), "h0_sha256": H0_SHA,
        "gmsh_path": str(gmsh), "gmsh_sha256": sha256(gmsh),
        "gmsh_version_output": (version.stdout + version.stderr).strip(),
        "available_memory_before_bytes": ram, "free_disk_before_bytes": disk,
        "unit_stdout": unit.stdout,
    }


def launch(meta: dict, run_dir: Path, mesh: Path) -> dict:
    argv = [meta["gmsh_path"], str(ROOT / GEO_NAME),
            "-3", "-nt", "2", "-format", "msh2", "-o", str(mesh)]
    log = run_dir / "P10DG_GMSH_FULL_LOG_LOCAL.txt"
    meta["exact_gmsh_argv"] = argv
    # Atomically persist prior to even invoking Popen; NEVER delete for retries.
    with MARKER.open("x", encoding="utf-8") as stream:
        json.dump({"revision": REV, "run_dir": str(run_dir),
                   "started_utc": datetime.now(timezone.utc).isoformat(),
                   "argv": argv}, stream, indent=2)
    start = time.monotonic()
    peak = 0
    with log.open("w", encoding="utf-8") as output:
        child = subprocess.Popen(argv, cwd=str(ROOT), stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                elapsed = time.monotonic() - start
                peak = max(peak, child_private_bytes(child))
                if elapsed > MAX_WALL_S:
                    raise RuntimeError("P10DG_STOP_GMSH_WALL_900S")
                if peak > MAX_PRIVATE:
                    raise RuntimeError("P10DG_STOP_GMSH_PRIVATE_8GIB")
                if mesh.exists() and mesh.stat().st_size > MAX_MSH_BYTES:
                    raise RuntimeError("P10DG_STOP_GMSH_MSH_750MIB")
                if log.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError("P10DG_STOP_GMSH_LOG_30MIB")
                time.sleep(.5)
            elapsed = time.monotonic() - start
            require(child.returncode == 0,
                    "native Gmsh exit " + str(child.returncode))
        except BaseException:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=15)
            raise
    require(mesh.is_file() and 0 < mesh.stat().st_size <= MAX_MSH_BYTES,
            "native Gmsh exit0 but M1.msh missing, empty or too large")
    return {"native_exit_code": child.returncode,
            "wall_seconds": elapsed, "peak_private_bytes_polled": peak,
            "m1_mesh_path": str(mesh), "m1_mesh_size_bytes": mesh.stat().st_size,
            "m1_mesh_sha256": sha256(mesh)}


def evidence_zip(run_dir: Path) -> Path:
    full = run_dir / "P10DG_GMSH_FULL_LOG_LOCAL.txt"
    if full.is_file():
        with full.open("rb") as stream:
            stream.seek(max(0, full.stat().st_size - 80 * 1024))
            tail = stream.read().decode("utf-8", errors="replace")
        (run_dir / "P10DG_GMSH_LOG_TAIL.txt").write_text(tail, encoding="utf-8")
    names = ["P10DG_RUN_MANIFEST.json", "P10DG_RESULT.txt",
             "P10DG_STOP_TRACE.txt", "P10DG_GMSH_LOG_TAIL.txt",
             "P10DG_QA_STDOUT_STDERR.txt"]
    names += [
        "QA/P10DG_H0_M1_MESH_QA.json",
        "QA/P10DG_H0_M1_RADIAL_MU_BINS.csv",
        "QA/P10DG_H0_M1_RADIAL_VOLUME_GATE.csv",
    ]
    target = run_dir / "P10DG_EVIDENCE.zip"
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in names:
            path = run_dir / rel
            if path.is_file():
                archive.write(path, rel)
    return target


def do_one_run() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    run_dir = RUNS / ("P10DG_M1_" + datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S_%f"))
    run_dir.mkdir(exist_ok=False)
    meta = {
        "protocol": REV, "status": "P10DG_STOP_NO_FEM",
        "FEM_runs": 0, "Gmsh_max_attempts": 1,
        "mesh": "M1_CANDIDATE", "mesh_only": True,
        "H0_is_not_remeshed": True,
        "size_field": "P10DF_EMPIRICAL_SOURCE_NOT_ATTESTED_H0_GENERATOR",
        "target_typical_volume_ratio": .8, "q_target_linear": Q,
        "wall_limit_seconds": MAX_WALL_S, "private_limit_bytes": MAX_PRIVATE,
        "mesh_size_limit_bytes": MAX_MSH_BYTES,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    code = 2
    try:
        meta.update(preflight())
        print("P10DG PREFLIGHT PASS: exact historical H0 SHA, Gmsh4.15.2,")
        print("pinned source, resources and independent 27QP synthetic QA.")
        print("P10DF empirical candidate near 0.428559mm far 7.052479mm.")
        print("ONE Gmsh M1 mesh-only; NO FEM. Limits 900s/8GiB private/750MiB.")
        print("After pressing Enter NO run occurs; type the exact manual phrase.")
        answer = input("Введите ровно RUN ONE P10DG M1 MESH: ").strip()
        require(answer == CONFIRM, "manual one-shot phrase not confirmed")
        mesh = run_dir / "P10DG_M1_CANDIDATE.msh"
        meta.update(launch(meta, run_dir, mesh))
        args = [sys.executable, str(ROOT / "P10DG_compare_m1.py"),
                "--h0", meta["h0_path"], "--m1", str(mesh),
                "--out", str(run_dir / "QA")]
        qa_log = run_dir / "P10DG_QA_STDOUT_STDERR.txt"
        with qa_log.open("w", encoding="utf-8") as output:
            qa = subprocess.run(args, cwd=str(ROOT), stdin=subprocess.DEVNULL,
                                stdout=output, stderr=subprocess.STDOUT,
                                timeout=QA_TIMEOUT_S, check=False)
        meta["qa_exit_code"] = qa.returncode
        require(qa.returncode == 0, "M1/H0 curved 27QP or radial/global volume QA failed")
        meta["status"] = "P10DG_M1_GEOMETRY_QA_OK_NO_FEM"
        code = 0
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        print("P10DG STOP:", exc)
        (run_dir / "P10DG_STOP_TRACE.txt").write_text(
            traceback.format_exc(), encoding="utf-8")
    finally:
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "P10DG_RUN_MANIFEST.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        lines = [f"RESULT={meta['status']}", "FEM_RUNS=0", "M1_MSH_NOT_UPLOADED=1",
                 f"STOP_REASON={meta.get('stop_reason', '')}",
                 f"M1_SHA256={meta.get('m1_mesh_sha256', 'UNKNOWN')}",
                 f"WINDOWS_NATIVE_GMSH_EXIT={meta.get('native_exit_code', 'UNKNOWN')}",
                 f"QA_EXIT={meta.get('qa_exit_code', 'UNKNOWN')}"]
        (run_dir / "P10DG_RESULT.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
        archive = evidence_zip(run_dir)
        print("RESULT=", meta["status"])
        print("EVIDENCE:", archive)
        print("Send ONLY P10DG_EVIDENCE.zip; keep large M1.msh and marker locally.")
    return code


def selftest() -> int:
    assert abs(Q - .9283177667225558) < 1e-14
    assert H0_SHA == "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
    assert MAX_WALL_S == 900 and MAX_PRIVATE == 8 * 1024**3
    assert CONFIRM == "RUN ONE P10DG M1 MESH"
    source_gate()
    q = command([sys.executable, str(ROOT / "P10DG_compare_m1.py"),
                 "--selftest"], ROOT, timeout=QA_TIMEOUT_S)
    require(q.returncode == 0 and "P10DG_QA_SYNTHETIC_OK" in q.stdout,
            "P10DG QA selftest failed: " + q.stdout[-400:] + q.stderr[-400:])
    print("P10DG_ONECLICK_SYNTHETIC_OK source_sha=PASS 27QP=PASS FEM=0")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    opts = parser.parse_args()
    return selftest() if opts.selftest else do_one_run()


if __name__ == "__main__":
    sys.exit(main())
