#!/usr/bin/env python3
"""One Windows attempt: exact accepted M1, fresh forward+analytic adjoint+signed4D.

R1 never starts physical FEM without a typed confirmation. One-shot marker is
created atomically BEFORE Popen; after any Popen attempt it must not be removed.
The Python runner, Windows job object and native M1 executable all gate the run.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parent
PIN = ROOT / "P10DL_SOURCE_SHA256SUMS.txt"
APP = "stage3d10dl_m1_full4d.exe"
UNIT = "p10dl_4d_synthetic_unit.exe"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
M1_NAME = "P10DG_M1_CANDIDATE.msh"
M1_DEFAULT = Path(r"G:\Downloads\P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121\P10DG_RUNS\P10DG_M1_20261121_120324_362583\P10DG_M1_CANDIDATE.msh")
LIMIT_WALL_S = 1800
LIMIT_PRIVATE = 8 * 1024**3
LIMIT_OUTPUT = 1 * 1024**3
MIN_FREE_DISK = 4 * 1024**3
MIN_FREE_PHYSICAL = 12 * 1024**3
OUT_ROOT = ROOT / "P10DL_OUTPUT"
MARKER = OUT_ROOT / "P10DL_ONE_SHOT_CONSUMED.json"
FILES = ("P10DD_SIGNED_R_THETA_PHI_T.csv",
         "P10DD_FULL4D_CLOSURE_AUDIT.csv", "P10W_ANALYTIC_ADJOINT.csv",
         "P10W_COMPONENTS.csv", "P10W_STEP_COMPONENTS.csv")


def require(value: bool, why: str) -> None:
    if not value:
        raise RuntimeError("P10DL_STOP: " + why)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def user_marker() -> Path:
    profile = os.environ.get("LOCALAPPDATA", "").strip()
    require(bool(profile), "Windows LOCALAPPDATA unavailable; cannot enforce global one-shot")
    return (Path(profile) / "Stage3D07" /
            ("P10DL_M1_" + M1_SHA[:16] + "_ONE_SHOT_CONSUMED.json"))


def source_gate() -> int:
    require(PIN.is_file(), "source SHA inventory absent")
    lines = PIN.read_text(encoding="utf-8").splitlines()
    require(len(lines) >= 90, "source SHA inventory incomplete")
    names: set[str] = set()
    for line in lines:
        require(len(line) > 66 and line[64:66] == "  ", "malformed SHA record")
        expected, name = line[:64], line[66:]
        require(name not in names and all(x in "0123456789abcdef" for x in expected),
                "repeated/invalid source SHA record")
        names.add(name)
        path = ROOT / name
        require(path.is_file() and sha(path) == expected,
                "published source changed: " + name)
    mandatory = {"stage3d10dl_m1_full4d.cpp", "stage3d10dk_m1_full4d.cpp",
                 "CMakeLists.txt", "P10DL_one_click_m1.py", "P10DK_audit_evidence.py",
                 "src/stage3d10w_analytic_adjoint.cpp",
                 "src/stage3d10p_partial_audit.cpp"}
    require(mandatory <= names, "mandatory full4D source unpinned")
    code = (ROOT / "stage3d10dl_m1_full4d.cpp").read_text(encoding="utf-8")
    require("#define STAGE3D10DL_BOUND_PHYSICAL 1" in code and
            "P10DL_ONE_SHOT_MARKER" in code and
            "P10DL_STOP_NO_FEM" in code,
            "native one-shot safeguards missing")
    old = os.path.normcase(str(Path("G:/ildar/Stage3D07")))
    actual = os.path.normcase(str(ROOT.resolve()))
    require(actual != old and not actual.startswith(old + os.sep),
            "cannot launch from original G:/ildar/Stage3D07")
    return len(lines)


def cache_value(text: str, name: str) -> str:
    values = [line.partition("=")[2].strip().strip('"')
              for line in text.splitlines() if line.partition(":")[0] == name and "=" in line]
    require(len(values) == 1 and bool(values[0]), "CMakeCache missing/duplicate " + name)
    return values[0]


def same_path(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def inspect_build() -> tuple[Path, Path, Path]:
    build = ROOT / "build" / "Desktop_MinGW_Release"
    config = build / "CMakeCache.txt"
    require(config.is_file(), "Qt Creator CMakeCache not found: " + str(config))
    source = config.read_text(encoding="utf-8", errors="replace")
    require(same_path(Path(cache_value(source, "CMAKE_HOME_DIRECTORY")), ROOT),
            "Qt Creator build is not from THIS extracted P10DL source")
    require(same_path(Path(cache_value(source, "STAGE3D07_SOURCE_ROOT")), ROOT),
            "Qt Creator includes sources from another directory")
    compiler = Path(cache_value(source, "CMAKE_CXX_COMPILER"))
    require(compiler.is_file() and compiler.name.lower() == "g++.exe",
            "Qt Creator is not using existing MinGW g++.exe")
    mingw = compiler.parent
    for dll in ("libgcc_s_seh-1.dll", "libstdc++-6.dll",
                "libwinpthread-1.dll", "libgomp-1.dll"):
        require((mingw / dll).is_file(), "MinGW runtime DLL not found: " + dll)
    exe, unit = build / APP, build / UNIT
    require(exe.is_file() and unit.is_file(), "build BOTH P10DL targets in Qt Creator")
    return exe, unit, mingw


def chosen_mesh(path: Path) -> str:
    require(path.is_file() and path.name == M1_NAME,
            "M1 mesh absent/wrong basename; NEVER substitute H0")
    digest = sha(path)
    require(digest == M1_SHA, "M1 mesh SHA does not match exact D-019 accepted mesh")
    return digest


def run_safe_test(exe: Path, args: list[str], expected: str,
                  env: dict[str, str]) -> None:
    result = subprocess.run([str(exe), *args], cwd=ROOT, env=env,
                            capture_output=True, text=True,
                            errors="replace", timeout=90)
    combined = result.stdout + result.stderr
    require(result.returncode == 0 and expected in combined,
            "safe test failed " + str(args) + " exit=" + str(result.returncode) +
            " tail=" + combined[-650:])
    print(expected, "PASS", flush=True)


def free_physical_windows() -> int:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    require(bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))),
            "cannot measure available physical RAM")
    return int(status.ullAvailPhys)


class JobGuard:
    """Windows kernel kills process tree on job close and caps process memory."""

    def __init__(self) -> None:
        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                 ctypes.c_void_p, wintypes.DWORD]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.restype = wintypes.BOOL
        self.k32 = k32
        self.handle = k32.CreateJobObjectW(None, None)
        require(bool(self.handle), "CreateJobObjectW failed")
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x100 | 0x2000  # PROCESS_MEMORY, KILL_ON_CLOSE
        info.ProcessMemoryLimit = LIMIT_PRIVATE
        if not k32.SetInformationJobObject(self.handle, 9, ctypes.byref(info),
                                           ctypes.sizeof(info)):
            self.close()
            require(False, "SetInformationJobObject failed; no unbounded run")

    def assign(self, pid: int) -> None:
        k32 = self.k32
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        process = k32.OpenProcess(0x0100 | 0x0400 | 0x0001, False, pid)
        require(bool(process), "OpenProcess for job assignment failed")
        try:
            require(bool(k32.AssignProcessToJobObject(self.handle, process)),
                    "cannot assign solver to protective Windows job")
        finally:
            k32.CloseHandle(process)

    def close(self) -> None:
        if self.handle:
            self.k32.CloseHandle(self.handle)
            self.handle = None


def private_bytes_windows(pid: int) -> int:
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ps = ctypes.WinDLL("psapi", use_last_error=True)
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    ps.GetProcessMemoryInfo.restype = wintypes.BOOL
    process = k32.OpenProcess(0x0400 | 0x0010, False, pid)
    require(bool(process), "cannot inspect solver private memory")
    try:
        c = Counters()
        c.cb = ctypes.sizeof(c)
        require(bool(ps.GetProcessMemoryInfo(process, ctypes.byref(c), c.cb)),
                "GetProcessMemoryInfo failed")
        return int(c.PrivateUsage)
    finally:
        k32.CloseHandle(process)


def output_bytes(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def pack_evidence(folder: Path, run: Path, manifest: dict) -> Path:
    metadata = folder / "P10DL_RUN_MANIFEST.json"
    metadata.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    target = folder / "P10DL_EVIDENCE.zip"
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for file in (metadata, folder / "P10DL_SOLVER_STDOUT_STDERR.txt"):
            if file.is_file():
                archive.write(file, arcname=file.name)
        for name in FILES:
            path = run / name
            if path.is_file():
                archive.write(path, arcname=name)
    require(output_bytes(folder) + output_bytes(run) <= LIMIT_OUTPUT,
            "output budget exceeded by evidence packaging")
    return target


def selftest() -> int:
    assert cache_value("CMAKE_HOME_DIRECTORY:INTERNAL=C:/Source\n", "CMAKE_HOME_DIRECTORY") == "C:/Source"
    with tempfile.TemporaryDirectory(prefix="p10dl_guard_unit_") as temp:
        folder = Path(temp)
        mesh = folder / M1_NAME
        mesh.write_bytes(b"not the approved M1")
        try:
            chosen_mesh(mesh)
        except RuntimeError as error:
            require("SHA" in str(error), "wrong mesh was rejected for wrong reason")
        else:
            require(False, "mutated M1 SHA was accepted")
        try:
            chosen_mesh(folder / "H0.msh")
        except RuntimeError:
            pass
        else:
            require(False, "missing historical H0 path accepted")
    print("P10DL_LAUNCHER_SELFTEST_OK wrong_M1_SHA=REJECTED "
          "H0_SUBSTITUTION=REJECTED no_Gmsh=1 physical_FEM=0")
    return 0


def main(args: list[str]) -> int:
    if args == ["--selftest"]:
        return selftest()
    require(not args, "unsupported options; --preflight and automatic retries forbidden")
    require(sys.platform == "win32", "the physical launcher is ONLY for Windows")
    count = source_gate()
    require(not MARKER.exists(), "one-shot marker already exists; DO NOT rerun")
    global_marker = user_marker()
    require(not global_marker.exists(), "user-wide marker: M1 attempt already consumed in another extracted folder")
    print("P10DL PINNED SOURCE OK", count, "files. No Gmsh, no H0 cache.", flush=True)
    exe, unit, mingw = inspect_build()
    env = os.environ.copy()
    env["PATH"] = str(mingw) + os.pathsep + env.get("PATH", "")
    run_safe_test(exe, ["--help"], "P10DL_ONE_SHOT_PHYSICAL_GUARD", env)
    run_safe_test(exe, ["--selftest"], "P10DL_EXE_PHYSICAL_GUARD_SELFTEST_OK", env)
    run_safe_test(unit, [], "P10DD_4D_SYNTHETIC_UNIT_OK", env)
    run_safe_test(Path(sys.executable), [str(ROOT / "P10DK_audit_evidence.py"), "--selftest"],
                  "P10DK_PY_7206_SYNTHETIC_ROWS_OK", env)
    entered = input("M1 mesh path (Enter=original P10DG output): ").strip().strip('"').strip("'")
    mesh = Path(entered) if entered else M1_DEFAULT
    mesh_digest = chosen_mesh(mesh)
    exe_digest = sha(exe)
    require(shutil.disk_usage(ROOT).free >= MIN_FREE_DISK,
            "less than 4 GiB free disk on the P10DL output volume")
    free_ram = free_physical_windows()
    require(free_ram >= MIN_FREE_PHYSICAL,
            "less than 12 GiB available physical RAM; postpone M1")
    require(not MARKER.exists(), "one-shot marker appeared after preflight; STOP")
    require(not global_marker.exists(), "user-wide M1 marker appeared; STOP")
    print("P10DL_M1_PREFLIGHT_OK mesh_sha256=" + mesh_digest,
          "exe_sha256=" + exe_digest,
          "available_ram_gib=" + str(round(free_ram / 1024**3, 2)), flush=True)
    print("RESOURCE HARD STOP: wall=1800s process_private=8GiB output=1GiB.")
    print("PHYSICAL HORIZON: six steps of dt=150s = 900s simulated time.")
    print("FORWARD: NEW forward_history.bin in NEW M1 directory; NO --reuse-forward.")
    print("Manual one-shot confirmation is mandatory. No repeat after any attempt.")
    phrase = input("Type exactly RUN ONE P10DL M1 to authorize one physical attempt: ")
    require(phrase.strip() == "RUN ONE P10DL M1", "manual confirmation not given; no FEM")
    require(not MARKER.exists(), "marker already exists; no repeated attempt")
    require(not global_marker.exists(), "user-wide marker already exists; no repeat")
    OUT_ROOT.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    folder = OUT_ROOT / ("P10DL_EVIDENCE_" + timestamp)
    run = OUT_ROOT / ("P10DL_M1_" + timestamp)
    require(not folder.exists() and not run.exists(), "new output folder collision")
    cmd = [str(exe), "--p10dk-authorized-fresh-m1", "--mesh", str(mesh),
           "--out", str(run), "--mode", "R", "--steps", "6",
           "--dt", "150", "--cutoff-mm", "5", "--threads", "4"]
    manifest: dict = {
        "protocol": "P10DL_R1_ONE_APPROVED_M1_FRESH_FORWARD_FULL4D",
        "status": "ONE_SHOT_CONSUMED", "mesh": str(mesh),
        "m1_sha256": mesh_digest, "m1_tet10_expected": 9736,
        "exe": str(exe), "exe_sha256": exe_digest,
        "command": cmd, "run_directory": str(run), "runtime_mingw": str(mingw),
        "fresh_forward": True, "reuse_forward": False,
        "expected_4d_rows": 7206, "started_utc": timestamp,
        "user_wide_one_shot_marker": str(global_marker),
        "limits": {"wall_s": LIMIT_WALL_S, "private_bytes": LIMIT_PRIVATE,
                   "new_output_bytes": LIMIT_OUTPUT},
        "native_exit_code": None,
    }
    folder.mkdir(exist_ok=False)
    # User-profile marker prevents repeating the SAME M1 by unzipping again.
    # Write BEFORE source-folder marker, which is required by the native EXE.
    global_marker.parent.mkdir(parents=True, exist_ok=True)
    with global_marker.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    with MARKER.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    env["P10DL_ONE_SHOT_MARKER"] = str(MARKER)
    print("P10DL_ONE_SHOT_CONSUMED: TWO markers created BEFORE native Popen", flush=True)
    log = folder / "P10DL_SOLVER_STDOUT_STDERR.txt"
    start = time.monotonic()
    peak, stop_reason, native_exit = 0, "", None
    job: JobGuard | None = None
    proc: subprocess.Popen | None = None
    try:
        job = JobGuard()
        with log.open("w", encoding="utf-8") as stream:
            proc = subprocess.Popen(cmd, cwd=ROOT, env=env,
                                    stdout=stream, stderr=subprocess.STDOUT)
            job.assign(proc.pid)
            while proc.poll() is None:
                time.sleep(.5)
                if proc.poll() is not None:
                    break
                peak = max(peak, private_bytes_windows(proc.pid))
                elapsed = time.monotonic() - start
                if elapsed > LIMIT_WALL_S:
                    stop_reason = "WALL_LIMIT"
                elif peak > LIMIT_PRIVATE:
                    stop_reason = "PRIVATE_LIMIT"
                elif output_bytes(run) + output_bytes(folder) > LIMIT_OUTPUT:
                    stop_reason = "OUTPUT_LIMIT"
                if stop_reason:
                    proc.terminate()
                    break
            native_exit = proc.wait(timeout=30)
    except BaseException as error:
        stop_reason = stop_reason or "MONITOR_ERROR_" + type(error).__name__ + "_" + str(error)[:150]
    finally:
        # This kernel job has KILL_ON_JOB_CLOSE. No orphan child may continue.
        if job is not None:
            job.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
    manifest.update(native_exit_code=native_exit,
                    wall_s=time.monotonic() - start,
                    peak_private_bytes_polled=peak, stop_reason=stop_reason)
    # A fast exit can happen between 0.5s polling ticks; final budgets still apply.
    if not stop_reason and manifest["wall_s"] > LIMIT_WALL_S:
        stop_reason = "FINAL_WALL_LIMIT"
    if not stop_reason and output_bytes(run) + output_bytes(folder) > LIMIT_OUTPUT:
        stop_reason = "FINAL_OUTPUT_LIMIT"
    if stop_reason:
        manifest["stop_reason"] = stop_reason
    if not stop_reason and native_exit == 0:
        try:
            from P10DK_audit_evidence import Reader, audit
            for name in FILES:
                require((run / name).is_file(), "physical 4D CSV missing: " + name)
            reader = Reader(run)
            try:
                manifest["independent_signed_4d"] = audit(reader)
            finally:
                reader.close()
            manifest["forward_history_sha256"] = sha(run / "forward_history.bin")
            manifest["status"] = "COMPLETED_M1_4D_VERIFIED"
        except Exception as error:
            manifest["status"] = "STOP"
            manifest["stop_reason"] = "INDEPENDENT_M1_AUDIT_FAILED: " + str(error)[:220]
    else:
        manifest["status"] = "STOP"
        manifest["stop_reason"] = stop_reason or "NATIVE_NONZERO_OR_NOT_STARTED"
    try:
        evidence = pack_evidence(folder, run, manifest)
    except BaseException as error:
        print("P10DL_STOP_EVIDENCE: " + repr(error),
              "(original run, log and marker remain; NO rerun)", flush=True)
        return 2
    print("P10DL_RESULT", manifest["status"], "native_exit=" + str(native_exit), flush=True)
    print("ONE SMALL FILE TO RETURN:", evidence, flush=True)
    print("Never remove M1 mesh, forward history or one-shot marker.", flush=True)
    return 0 if manifest["status"] == "COMPLETED_M1_4D_VERIFIED" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print("P10DL_STOP:", error, file=sys.stderr)
        raise SystemExit(2)
