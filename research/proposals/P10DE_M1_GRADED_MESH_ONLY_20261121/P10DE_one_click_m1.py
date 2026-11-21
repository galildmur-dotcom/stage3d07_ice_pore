#!/usr/bin/env python3
"""P10DE R1: ONE guarded Windows Gmsh M1 mesh-only run; NEVER FEM.

Safe preflight is repeatable; Gmsh process is one-shot. Original G: H0 mesh
and original source project are read-only. Output lives beside this program.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
from datetime import datetime, timezone
import hashlib
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

REV = "P10DE_R1_M1_GRADED_20PCT_VOLUME_MESH_ONLY"
H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
GMSH_VERSION = "4.15.2"
Q = .8**(1./3.)
ONE_SHOT_PHRASE = "RUN ONE M1 MESH"
MAX_WALL_S = 900
MAX_PRIVATE = 8 * 1024**3
MAX_MSH_BYTES = 750 * 1024**2
MAX_LOG_BYTES = 30 * 1024**2
ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "P10DE_RUNS"
MARKER = RUNS / "P10DE_ONE_SHOT_USED.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stop_if(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError("P10DE_STOP: " + message)


def source_gate() -> dict:
    expected = json.loads((ROOT / "P10DE_PINNED_SHA256.json").read_text(encoding="utf-8"))
    require_revision = expected.get("revision") == REV
    stop_if(require_revision and isinstance(expected.get("files"), dict),
            "wrong or damaged source manifest")
    for name, digest in expected["files"].items():
        file = ROOT / name
        stop_if(file.is_file() and sha(file) == digest, "package file SHA mismatch: " + name)
    geo = (ROOT / "P10DC_M1_FROM_H0_20PCT_VOLUME.geo").read_text(encoding="utf-8")
    base = (ROOT / "sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    stop_if('Include "sphere_pore_B6_refined.geo";' in geo and
            "Mesh.ElementOrder=2" in base and
            "Background Field=2" in base and
            "Field[2].SizeMin=nearSize" in base and
            "Field[2].SizeMax=farSize" in base, "invalid graded M1 CAD/field")
    near = re.search(r"^nearSize\s*=\s*([0-9.eE+-]+)", geo, re.M)
    far = re.search(r"^farSize\s*=\s*([0-9.eE+-]+)", geo, re.M)
    stop_if(near is not None and far is not None and
            abs(float(near.group(1))/.00019 - Q) < 1e-12 and
            abs(float(far.group(1))/.0039 - Q) < 1e-12,
            "M1 size field is not exactly H0 * cbrt(0.8)")
    return expected["files"]


def windows_free_ram() -> int:
    class MEM(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.wintypes.DWORD),
                    ("dwMemoryLoad", ctypes.wintypes.DWORD)] + [
                        (name, ctypes.c_ulonglong) for name in
                        ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile",
                         "ullAvailPageFile", "ullTotalVirtual", "ullAvailVirtual",
                         "ullAvailExtendedVirtual")]
    m = MEM()
    m.dwLength = ctypes.sizeof(MEM)
    stop_if(bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))),
            "cannot read available Windows memory")
    return int(m.ullAvailPhys)


def windows_process_private(process: subprocess.Popen) -> int:
    class COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.wintypes.DWORD), ("PageFaultCount", ctypes.wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]
    x = COUNTERS()
    x.cb = ctypes.sizeof(x)
    f = ctypes.windll.psapi.GetProcessMemoryInfo
    # ctypes defaults to 32-bit c_int arguments without argtypes, which would
    # silently truncate a 64-bit Windows process HANDLE on this machine.
    f.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(COUNTERS), ctypes.wintypes.DWORD]
    f.restype = ctypes.wintypes.BOOL
    ok = f(ctypes.wintypes.HANDLE(int(process._handle)),
           ctypes.byref(x), ctypes.sizeof(x))
    stop_if(bool(ok), "cannot monitor Gmsh private memory")
    return int(x.PrivateUsage)


def run_cmd(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout,
                          check=False, cwd=str(ROOT), errors="replace")


def preflight() -> dict:
    stop_if(os.name == "nt", "actual Gmsh run permitted only on Windows")
    root = str(ROOT).casefold()
    source_root = str(Path(r"G:\ildar\Stage3D07")).casefold()
    stop_if(root != source_root and not root.startswith(source_root + "\\"),
            "extract package OUTSIDE the existing G:\\ildar\\Stage3D07")
    stop_if(not MARKER.exists(), "one physical Gmsh attempt already started: do not retry")
    pinned = source_gate()
    h0 = Path(os.environ.get("P10DE_H0_MSH", r"G:\ildar\Stage3D07\meshes\H0.msh"))
    stop_if(h0.is_file() and sha(h0) == H0_SHA, "historical H0.msh missing or SHA mismatch")
    gmsh = Path(os.environ.get("P10DE_GMSH_EXE", r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    stop_if(gmsh.is_file(), "Gmsh 4.15.2 EXE missing: " + str(gmsh))
    v = run_cmd([str(gmsh), "-version"], timeout=15)
    stop_if(v.returncode == 0 and
            re.search(r"(?<![0-9])4\.15\.2(?![0-9])", v.stdout + v.stderr),
            "wrong/unverified native Gmsh version or exit")
    ram = windows_free_ram()
    disk = shutil.disk_usage(ROOT).free
    stop_if(ram >= 16 * 1024**3 and disk >= 4 * 1024**3,
            "need at least 16 GiB available RAM and 4 GiB free output disk")
    unit = run_cmd([sys.executable, str(ROOT / "P10DE_compare_m1.py"), "--selftest"], timeout=90)
    stop_if(unit.returncode == 0 and
            "P10DE_M1_MESH_QA_SYNTHETIC_OK" in unit.stdout,
            "Python mesh-QA synthetic selftest STOP: " + unit.stdout[-300:])
    return {
        "package_sources_sha256": pinned, "h0_path": str(h0),
        "h0_sha256": H0_SHA, "gmsh_path": str(gmsh), "gmsh_sha256": sha(gmsh),
        "gmsh_version_output": v.stdout.strip() or v.stderr.strip(),
        "available_memory_before_bytes": ram, "free_disk_before_bytes": disk,
        "unit_test_stdout": unit.stdout, "unit_test_stderr": unit.stderr,
    }


def launch_gmsh(meta: dict, run_dir: Path, mesh: Path) -> dict:
    argv = [meta["gmsh_path"], str(ROOT / "P10DC_M1_FROM_H0_20PCT_VOLUME.geo"),
            "-3", "-nt", "2", "-format", "msh2", "-o", str(mesh)]
    log = run_dir / "P10DE_GMSH_FULL_LOG_LOCAL.txt"
    meta["exact_gmsh_argv"] = argv
    # Marker is atomic and written immediately BEFORE Gmsh starts.
    with MARKER.open("x", encoding="utf-8") as marker:
        json.dump({"revision": REV, "run_dir": str(run_dir),
                   "started_utc": datetime.now(timezone.utc).isoformat(),
                   "gmsh_argv": argv}, marker, indent=2)
    start = time.monotonic()
    private_peak = 0
    with log.open("w", encoding="utf-8") as out:
        child = subprocess.Popen(argv, cwd=str(ROOT), stdout=out,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            while child.poll() is None:
                elapsed = time.monotonic() - start
                private_peak = max(private_peak, windows_process_private(child))
                if elapsed > MAX_WALL_S:
                    raise RuntimeError("P10DE_STOP_GMSH_WALL_900S")
                if private_peak > MAX_PRIVATE:
                    raise RuntimeError("P10DE_STOP_GMSH_PRIVATE_8GIB")
                if mesh.exists() and mesh.stat().st_size > MAX_MSH_BYTES:
                    raise RuntimeError("P10DE_STOP_GMSH_OUTPUT_750MIB")
                if log.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError("P10DE_STOP_GMSH_LOG_30MIB")
                time.sleep(.5)
            elapsed = time.monotonic() - start
            stop_if(child.returncode == 0, "native Gmsh exit " + str(child.returncode))
        except BaseException:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=15)
            raise
    stop_if(mesh.is_file() and 0 < mesh.stat().st_size <= MAX_MSH_BYTES,
            "Gmsh returned exit0 but MSH file missing, empty or too large")
    return {"native_exit_code": child.returncode,
            "wall_seconds": elapsed,
            "peak_private_bytes_polled": private_peak,
            "m1_mesh_path": str(mesh), "m1_mesh_size_bytes": mesh.stat().st_size,
            "m1_mesh_sha256": sha(mesh)}


def evidence_zip(run_dir: Path) -> Path:
    log = run_dir / "P10DE_GMSH_FULL_LOG_LOCAL.txt"
    if log.exists():
        # The full log remains local; only its last 80 KiB is transmitted.
        with log.open("rb") as f:
            f.seek(max(0, log.stat().st_size - 80 * 1024))
            tail = f.read().decode("utf-8", errors="replace")
        (run_dir / "P10DE_GMSH_LOG_TAIL.txt").write_text(tail, encoding="utf-8")
    files = [p for p in run_dir.rglob("*") if p.is_file() and
             p.name not in {"P10DE_GMSH_FULL_LOG_LOCAL.txt",
                            "P10DE_M1_GRADED.msh", "P10DE_EVIDENCE.zip"}]
    archive = run_dir / "P10DE_EVIDENCE.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files):
            z.write(f, f.relative_to(run_dir).as_posix())
    return archive


def do_one_run() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    run_dir = RUNS / ("P10DE_M1_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run_dir.mkdir(parents=False, exist_ok=False)
    meta = {"protocol": REV, "status": "P10DE_STOP_NO_FEM",
            "FEM_runs": 0, "Gmsh_max_attempts": 1, "mesh": "M1",
            "mesh_only": True, "H0_is_not_remeshed": True,
            "graded_size_ratio": Q, "target_typical_volume_ratio": .8,
            "wall_limit_seconds": MAX_WALL_S, "private_limit_bytes": MAX_PRIVATE,
            "mesh_size_limit_bytes": MAX_MSH_BYTES,
            "started_utc": datetime.now(timezone.utc).isoformat()}
    result = 2
    try:
        meta.update(preflight())
        print("P10DE PREFLIGHT PASS; original historical H0 SHA verified.")
        print("M1 = graded H0 sizes * 0.9283177667, 20% typical element volume target.")
        print("ONE Gmsh mesh-only attempt; 900s wall / 8GiB private / 750MiB MSH.")
        print("NO FEM. Large M1.msh will remain on this computer.")
        confirmation = input("Для запуска введите ровно RUN ONE M1 MESH: ").strip()
        stop_if(confirmation == ONE_SHOT_PHRASE, "manual run phrase not confirmed")
        mesh = run_dir / "P10DE_M1_GRADED.msh"
        meta.update(launch_gmsh(meta, run_dir, mesh))
        cmd = [sys.executable, str(ROOT / "P10DE_compare_m1.py"),
               "--h0", meta["h0_path"], "--m1", str(mesh),
               "--out", str(run_dir / "QA")]
        qa_log = run_dir / "P10DE_QA_STDOUT_STDERR.txt"
        with qa_log.open("w", encoding="utf-8") as out:
            qa = subprocess.run(cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT, timeout=300)
        meta["qa_exit_code"] = qa.returncode
        stop_if(qa.returncode == 0, "M1 or H0 curved 27QP/structure QA failed")
        meta["status"] = "P10DE_M1_GEOMETRY_QA_OK_NO_FEM"
        result = 0
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        print("P10DE STOP:", str(exc))
        # Preserve traceback for diagnosing an incidental launcher failure.
        (run_dir / "P10DE_STOP_TRACE.txt").write_text(
            traceback.format_exc(), encoding="utf-8")
    finally:
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "P10DE_RUN_MANIFEST.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        lines = [f"RESULT={meta['status']}", "FEM_RUNS=0", "M1_MSH_NOT_UPLOADED=1",
                 f"STOP_REASON={meta.get('stop_reason', '')}",
                 f"M1_SHA256={meta.get('m1_mesh_sha256', 'UNKNOWN')}",
                 f"WINDOWS_NATIVE_GMSH_EXIT={meta.get('native_exit_code', 'UNKNOWN')}"]
        (run_dir / "P10DE_RESULT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        archive = evidence_zip(run_dir)
        print("RESULT=", meta["status"])
        print("P10DE EVIDENCE:", archive)
        print("Send ONLY P10DE_EVIDENCE.zip; retain large M1.msh locally.")
    return result


def selftest() -> int:
    assert abs(Q - .9283177667225558) < 1e-14
    assert H0_SHA == "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
    assert MAX_WALL_S == 900 and MAX_PRIVATE == 8 * 1024**3
    assert ONE_SHOT_PHRASE == "RUN ONE M1 MESH"
    source_gate()
    r = run_cmd([sys.executable, str(ROOT / "P10DE_compare_m1.py"), "--selftest"], timeout=90)
    stop_if(r.returncode == 0, "QA synthetic test failed")
    print("P10DE_ONECLICK_SYNTHETIC_OK no_gmsh_no_FEM=1 source_sha=PASS")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        return selftest()
    return do_one_run()


if __name__ == "__main__":
    sys.exit(main())
