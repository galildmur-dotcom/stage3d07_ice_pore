#!/usr/bin/env python3
"""P10DA: one guarded physical R/EDV_VAR solve on the EXISTING uniform U0.

Windows, 64-bit Python 3, stdlib only. The original source and mesh are READ ONLY.
The package runs NO Gmsh, CMake, remeshing or solver --preflight.
"""
from __future__ import annotations

import csv
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import zipfile


REV = "P10DA_R1_ONE_EXISTING_UNIFORM_U0_PHYSICAL_BASELINE"
ORIGINAL = Path(r"G:\ildar\Stage3D07")
MESH = Path(r"G:\Downloads\P10CT_R1_U0_MESH_ONLY_WINDOWS_20261121\P10CT_RUNS\P10CT_20261121_051002_957\P10CT_U0_h2mm.msh")
MESH_SHA = "1a4690d1c57c8b520d596f9a864f754a8d84151bfd1fdd36f56631488779c6a3"
MESH_SIZE = 16218389
MESH_NODES = 131380
MESH_TETS = 90725
MESH_PORE_TRI = 20
EXE = Path(r"G:\Downloads\P10CA_H0_ONE_RUN_R1_20261120\P10CA_RESULTS_20261120_151200_8420\build\p10ca_h0_analytic_qp.exe")
EXE_SHA = "17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924"
GIT = Path(r"C:\Program Files\Git\cmd\git.exe")
RUNTIME = Path(r"C:\mingw64\bin")
MAX_WALL_S = 3600
MAX_PRIVATE_B = 32 * 1024 ** 3
MAX_OUTPUT_B = 4 * 1024 ** 3
MIN_AVAILABLE_RAM_B = 20 * 1024 ** 3
MIN_FREE_DISK_B = 8 * 1024 ** 3
EXPECTED_QP_PER_STEP = MESH_TETS * 64
EXPECTED_STEPS = 6


class CancelNoFEM(Exception):
    """The user declined the physical attempt after read-only checks."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pin(path: Path, expected: str, expected_size: int | None = None) -> None:
    if not path.is_file():
        raise RuntimeError(f"PIN_MISSING: {path}")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise RuntimeError(f"PIN_SIZE_MISMATCH: {path}")
    if sha256(path) != expected:
        raise RuntimeError(f"PIN_SHA256_MISMATCH: {path}")


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def git_snapshot() -> dict[str, str]:
    if not GIT.is_file() or not ORIGINAL.is_dir():
        raise RuntimeError("ORIGINAL_GIT_OR_ROOT_NOT_AVAILABLE")
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"

    def call(*args: str) -> str:
        result = subprocess.run([str(GIT), "-C", str(ORIGINAL), *args],
                                capture_output=True, encoding="utf-8", errors="replace",
                                timeout=90, env=env, check=False)
        if result.returncode != 0:
            raise RuntimeError("ORIGINAL_GIT_READ_FAILED: " + " ".join(args))
        return result.stdout.strip()

    head = call("rev-parse", "HEAD")
    status = call("-c", "core.fsmonitor=false", "status", "--porcelain=v1",
                  "--untracked-files=normal")
    return {"head": head, "status_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "status_line_count": str(len(status.splitlines()))}


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD)] + [
        (name, ctypes.c_ulonglong) for name in
        ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile", "ullAvailPageFile",
         "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in
        ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
         "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
         "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]


def available_ram_bytes() -> int:
    state = MEMORYSTATUSEX()
    state.dwLength = ctypes.sizeof(state)
    dll = ctypes.WinDLL("kernel32", use_last_error=True)
    dll.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    dll.GlobalMemoryStatusEx.restype = wintypes.BOOL
    if not dll.GlobalMemoryStatusEx(ctypes.byref(state)):
        raise RuntimeError("CANNOT_READ_WINDOWS_AVAILABLE_RAM")
    return int(state.ullAvailPhys)


def private_bytes(pid: int) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x0410, False, pid)  # QUERY_INFORMATION | VM_READ
    if not handle:
        raise RuntimeError("CANNOT_OPEN_PHYSICAL_PROCESS_FOR_MEMORY_GUARD")
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise RuntimeError("CANNOT_MEASURE_PHYSICAL_PROCESS_PRIVATE_MEMORY")
        return int(counters.PrivateUsage)
    finally:
        kernel.CloseHandle(handle)


def folder_size(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def safe_exe_check(arg: str, timeout: int, log: Path, env: dict[str, str]) -> str:
    cp = subprocess.run([str(EXE), arg], capture_output=True, timeout=timeout,
                        encoding="utf-8", errors="replace", env=env, check=False)
    log.write_text(f"EXIT={cp.returncode}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}",
                   encoding="utf-8")
    if cp.returncode != 0:
        raise RuntimeError(f"SAFE_{arg}_NONZERO_NATIVE_EXIT={cp.returncode}")
    return cp.stdout


def audit_csv(physical: Path, stdout: str) -> dict[str, float | int]:
    if "P10W_ANALYTIC_ADJOINT_OK" not in stdout or \
       "P10BX_THERMAL_QP_INTEGRATED_OK" not in stdout or \
       "exported_rows=606" not in stdout or \
       "original_gradient_unchanged=1" not in stdout:
        raise RuntimeError("MISSING_EXACT_PHYSICAL_QP_ANALYTIC_MARKERS")
    names = ["P10W_ANALYTIC_ADJOINT.csv", "P10W_COMPONENTS.csv",
             "P10W_STEP_COMPONENTS.csv", "P10BX_THERMAL_QP_STEP_BINS.csv",
             "P10BX_THERMAL_STEP_AUDIT.csv"]
    for name in names:
        if not (physical / name).is_file():
            raise RuntimeError("MISSING_PHYSICAL_CSV: " + name)
    def read(name: str):
        with (physical / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    bins = read("P10BX_THERMAL_QP_STEP_BINS.csv")
    audits = read("P10BX_THERMAL_STEP_AUDIT.csv")
    components = read("P10W_COMPONENTS.csv")
    if len(bins) != 606 or len(audits) != 6:
        raise RuntimeError("THERMAL_QP_ROW_COUNT_MISMATCH")
    max_err = 0.0
    for step in range(1, 7):
        local = [b for b in bins if b["step"] == str(step)]
        check = [a for a in audits if a["step"] == str(step)]
        if len(local) != 101 or len(check) != 1:
            raise RuntimeError(f"THERMAL_QP_STEP_ROWS_INVALID: {step}")
        if sum(b["shell_bin"] == "-1" and b["polar_bin"] == "-1"
               for b in local) != 1:
            raise RuntimeError("ROBIN_TOP_ROW_MISMATCH")
        row = check[0]
        if int(row["thermal_qp_count"]) != EXPECTED_QP_PER_STEP:
            raise RuntimeError("VOLUME_QP_COUNT_MISMATCH")
        budget = float(row["allowed_abs_error_per_m"])
        total = float(row["qp_total_per_m"])
        csr = float(row["csr_total_per_m"])
        partition = sum(float(b["total_per_m"]) for b in local)
        err = max(abs(total - csr), abs(total - partition))
        if not (math.isfinite(err) and math.isfinite(budget) and
                0 <= err <= budget and budget >= 0):
            raise RuntimeError(f"THERMAL_QP_CSR_CLOSURE_STOP: step={step}")
        max_err = max(max_err, err)
    jpeak = [r for r in components if r["functional"] == "jpeak" and r["mode"] == "R"]
    if len(jpeak) != 1 or jpeak[0]["geometry_derivative_method"] != "ANALYTIC_TET10":
        raise RuntimeError("MISSING_R_JPEAK_ANALYTIC_COMPONENT")
    comp = jpeak[0]
    mech = float(comp["total_mechanical_shape_per_m"])
    thermal = float(comp["thermal_adjoint_per_m"])
    full = float(comp["total_adjoint_per_m"])
    if not all(math.isfinite(x) for x in (mech, thermal, full)) or \
       abs(mech + thermal - full) > max(1e-9, 1e-8 * abs(full)):
        raise RuntimeError("GLOBAL_MECHANICAL_THERMAL_CLOSURE_STOP")
    return {"thermal_qp_per_step": EXPECTED_QP_PER_STEP,
            "max_thermal_closure_error_per_m": max_err,
            "mechanical_total_per_m": mech,
            "thermal_total_per_m": thermal,
            "full_D_R_jpeak_per_m": full}


def write_evidence(run_dir: Path, result: dict) -> None:
    (run_dir / "P10DA_RESULT.txt").write_text("\n".join(f"{k}={v}" for k, v in result.items()) + "\n", encoding="utf-8")
    (run_dir / "P10DA_RUN_MANIFEST.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    zip_path = run_dir / "P10DA_EVIDENCE.zip"
    keep = ["P10DA_RESULT.txt", "P10DA_RUN_MANIFEST.json", "safe_help.txt", "safe_selftest.txt",
            "physical_stdout.txt", "physical_stderr.txt", "P10DA_TRACEBACK.txt"]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        for name in keep:
            p = run_dir / name
            if p.is_file():
                z.write(p, name)
        for name in ("P10W_ANALYTIC_ADJOINT.csv", "P10W_COMPONENTS.csv",
                     "P10W_STEP_COMPONENTS.csv", "P10BX_THERMAL_QP_STEP_BINS.csv",
                     "P10BX_THERMAL_STEP_AUDIT.csv"):
            p = run_dir / "U0_PHYSICAL_RUN" / name
            if p.is_file():
                z.write(p, "PHYSICAL_CSV/" + name)
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:
            raise RuntimeError("EVIDENCE_ZIP_CRC_FAILED")
    print("EVIDENCE_PATH=" + str(zip_path), flush=True)


def selftest() -> int:
    assert EXPECTED_QP_PER_STEP == 5_806_400
    assert MAX_PRIVATE_B == 34_359_738_368
    assert not inside(Path("/tmp/p10da"), Path("/tmp/p10da_source"))
    assert len(MESH_SHA) == len(EXE_SHA) == 64
    print("P10DA_SYNTHETIC_SELFTEST_OK FEM=0 GMSH=0")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if sys.platform != "win32" or ctypes.sizeof(ctypes.c_void_p) != 8:
        print("P10DA_STOP_REQUIRES_WINDOWS_64BIT_PYTHON")
        return 2
    here = Path(__file__).resolve().parent
    if inside(here, ORIGINAL) or inside(here, MESH.parent):
        print("P10DA_STOP_PACKAGE_INSIDE_ORIGINAL_OR_MESH_FOLDER")
        return 2
    attempted = here / "P10DA_PHYSICAL_ATTEMPTED.txt"
    if attempted.exists():
        print("P10DA_STOP_ONE_PHYSICAL_ATTEMPT_ALREADY_USED")
        return 2

    run_dir = here / "P10DA_RESULTS" / datetime.now(timezone.utc).strftime("P10DA_%Y%m%d_%H%M%S_%f_UTC")
    run_dir.mkdir(parents=True, exist_ok=False)
    result: dict[str, object] = {"revision": REV, "status": "STOP_NO_FEM",
                                 "start_utc": datetime.now(timezone.utc).isoformat(),
                                 "physical_attempted": False, "mesh_sha256": MESH_SHA,
                                 "exe_sha256": EXE_SHA, "steps": 6, "dt_s": 150,
                                 "mode": "R", "law": "EDV", "modulus": "VAR",
                                 "xi": 0, "cutoff_mm": 5, "threads": 4,
                                 "wall_budget_s": MAX_WALL_S,
                                 "private_budget_bytes": MAX_PRIVATE_B,
                                 "output_budget_bytes": MAX_OUTPUT_B}
    before = None
    child: subprocess.Popen | None = None
    try:
        pin(MESH, MESH_SHA, MESH_SIZE)
        pin(EXE, EXE_SHA)
        if not RUNTIME.is_dir():
            raise RuntimeError("PINNED_MINGW_RUNTIME_NOT_AVAILABLE")
        before = git_snapshot()
        result["original_git_before"] = before
        result["input_gate"] = "PINNED_U0_QA_R2_AND_EXE_SHA_PASS"
        free_disk = shutil.disk_usage(here).free
        free_ram = available_ram_bytes()
        result["disk_free_before_bytes"] = free_disk
        result["ram_available_before_bytes"] = free_ram
        if free_disk < MIN_FREE_DISK_B or free_ram < MIN_AVAILABLE_RAM_B:
            raise RuntimeError("INSUFFICIENT_FREE_RAM_OR_DISK_FOR_BOUNDED_U0")
        env = os.environ.copy()
        env["PATH"] = str(RUNTIME) + os.pathsep + env.get("PATH", "")
        env["OMP_NUM_THREADS"] = "4"
        env["OMP_DYNAMIC"] = "FALSE"
        help_output = safe_exe_check("--help", 25, run_dir / "safe_help.txt", env)
        if "no --delta-scan-um is accepted" not in help_output:
            raise RuntimeError("SAFE_HELP_CONTRACT_MISMATCH")
        selftest_output = safe_exe_check("--selftest", 90, run_dir / "safe_selftest.txt", env)
        if "P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18" not in selftest_output or \
           "P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0" not in selftest_output:
            raise RuntimeError("SAFE_SELFTEST_CONTRACT_MISMATCH")
        result["safe_gate"] = "PASS_HELP_SELFTEST_NO_FEM"
        print("\nPINNED U0 READY: nodes=131380 Tet10=90725 pore_Tri6=20.", flush=True)
        print("Expected 5,806,400 thermal QP/step; 6 steps of 150s.", flush=True)
        print("ESTIMATE 30-60 min, ~12 GiB process/2 GiB disk (uncertain).", flush=True)
        print("GUARDS 3600s / 32 GiB private / 4 GiB output; polling is NOT hard isolation.", flush=True)
        print("The near-pore 20-100um layers CANNOT be resolved with U0.", flush=True)
        print("No 3D phi-resolved signed mechanical/thermal export in this EXE.", flush=True)
        answer = input("Type RUN ONE U0 P10DA to start ONE physical solve (Enter cancels): ")
        if answer != "RUN ONE U0 P10DA":
            raise CancelNoFEM()

        # Recheck immediately before the irreversible attempt; no retries.
        pin(MESH, MESH_SHA, MESH_SIZE)
        pin(EXE, EXE_SHA)
        if git_snapshot() != before:
            raise RuntimeError("ORIGINAL_GIT_CHANGED_BEFORE_PHYSICAL")
        if shutil.disk_usage(here).free < MIN_FREE_DISK_B or \
           available_ram_bytes() < MIN_AVAILABLE_RAM_B:
            raise RuntimeError("RESOURCES_CHANGED_BEFORE_PHYSICAL")
        with attempted.open("x", encoding="utf-8") as mark:
            mark.write(REV + "\n" + MESH_SHA + "\n" + EXE_SHA + "\n" + str(run_dir) + "\n")
        result["physical_attempted"] = True

        physical = run_dir / "U0_PHYSICAL_RUN"
        args = [str(EXE), "--mesh", str(MESH), "--out", str(physical),
                "--steps", "6", "--dt", "150", "--mode", "R",
                "--cutoff-mm", "5", "--threads", "4"]
        result["physical_args"] = args[1:]
        started = time.monotonic()
        max_private = 0
        max_disk = 0
        with (run_dir / "physical_stdout.txt").open("wb") as stdout, \
             (run_dir / "physical_stderr.txt").open("wb") as stderr:
            child = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env, cwd=str(here))
            result["physical_pid"] = child.pid
            while child.poll() is None:
                elapsed = time.monotonic() - started
                try:
                    mem = private_bytes(child.pid)  # Fail closed if guard is unavailable.
                except RuntimeError:
                    if child.poll() is not None:
                        break  # A finished child may already have closed its Win32 handle.
                    raise
                max_private = max(max_private, mem)
                max_disk = max(max_disk, folder_size(physical))
                if elapsed >= MAX_WALL_S or mem >= MAX_PRIVATE_B or max_disk >= MAX_OUTPUT_B:
                    raise RuntimeError(f"PHYSICAL_BUDGET_STOP elapsed={elapsed:.1f} private={mem} disk={max_disk}")
                if int(elapsed) % 30 == 0:
                    print(f"P10DA_RUNNING elapsed_s={elapsed:.0f} private_GiB={mem/2**30:.2f} output_GiB={max_disk/2**30:.2f}", flush=True)
                time.sleep(1)
            native_exit = child.wait()
        elapsed = time.monotonic() - started
        max_disk = max(max_disk, folder_size(physical))
        result.update({"physical_native_exit": native_exit,
                       "wall_seconds": round(elapsed, 3),
                       "max_polled_private_bytes": max_private,
                       "physical_output_bytes": max_disk})
        if native_exit != 0:
            raise RuntimeError("PHYSICAL_NATIVE_EXIT_NONZERO")
        if elapsed >= MAX_WALL_S or max_private >= MAX_PRIVATE_B or max_disk >= MAX_OUTPUT_B:
            raise RuntimeError("PHYSICAL_FINAL_RESOURCE_GUARD_STOP")
        stdout_text = (run_dir / "physical_stdout.txt").read_text(encoding="utf-8", errors="replace")
        result["physical_audit"] = audit_csv(physical, stdout_text)
        result["status"] = "P10DA_U0_PHYSICAL_COMPLETED_AUDITED_COARSE_ONLY"
    except CancelNoFEM:
        result["status"] = "SAFE_READY_CANCELLED_NO_FEM"
    except (Exception, KeyboardInterrupt) as e:
        result["status"] = "P10DA_STOP_NO_RETRY"
        result["stop_reason"] = str(e)
        (run_dir / "P10DA_TRACEBACK.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print("P10DA_STOP_NO_RETRY: " + str(e), flush=True)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        try:
            result["original_git_after"] = git_snapshot()
            if before is not None and result["original_git_after"] != before:
                result["status"] = "P10DA_STOP_ORIGINAL_GIT_CHANGED"
        except Exception as e:
            result["original_git_postcheck_error"] = str(e)
            result["status"] = "P10DA_STOP_ORIGINAL_POSTCHECK"
        try:
            pin(MESH, MESH_SHA, MESH_SIZE)
            pin(EXE, EXE_SHA)
            result["inputs_preserved"] = True
        except Exception as e:
            result["inputs_preserved"] = False
            result["post_sha_stop"] = str(e)
            result["status"] = "P10DA_STOP_INPUT_CHANGED"
        result["end_utc"] = datetime.now(timezone.utc).isoformat()
        try:
            write_evidence(run_dir, result)
        except Exception as e:
            print("P10DA_EVIDENCE_WRITE_STOP: " + str(e), flush=True)
        print("RESULT=" + str(result["status"]), flush=True)
    return 0 if result["status"] in (
        "P10DA_U0_PHYSICAL_COMPLETED_AUDITED_COARSE_ONLY", "SAFE_READY_CANCELLED_NO_FEM") else 2


if __name__ == "__main__":
    sys.exit(main())
