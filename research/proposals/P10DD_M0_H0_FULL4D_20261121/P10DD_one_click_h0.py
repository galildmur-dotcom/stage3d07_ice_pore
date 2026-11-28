"""Windows-only one-shot guarded H0 R/EDV_VAR full4D adjoint replay.

The CMD does not compile, run FEM or modify the user's G: source tree by
itself. Manual typed confirmation is required *after* source and mesh checks.
By default an existing compatible P10CA H0 forward_history.bin is mandatory.
Only a separately authorized --allow-fresh-forward launch may recompute it.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

H0 = Path(r"G:\ildar\Stage3D07\meshes\H0.msh")
H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
APP_NAME = "stage3d10dd_m0_h0_full4d.exe"
LIMIT_S = 900
LIMIT_PRIVATE = 8 * 1024**3
LIMIT_OUTPUT = 1 * 1024**3
MIN_FREE_DISK = 3 * 1024**3
RUN_ROOT = Path(__file__).resolve().parent / "P10DD_OUTPUT"


def stop(message: str) -> None:
    raise RuntimeError("P10DD_STOP: " + message)


def sha256(path: Path) -> str:
    dig = hashlib.sha256()
    with path.open("rb") as file:
        while block := file.read(4 * 1024 * 1024):
            dig.update(block)
    return dig.hexdigest()


def is_file(path: Path, label: str) -> None:
    if not path.is_file():
        stop(f"{label}: не найден файл {path}")


def parse_path(prompt: str) -> Path:
    return Path(input(prompt).strip().strip('"').strip("'"))


def private_bytes_windows(pid: int) -> int:
    from ctypes import wintypes

    size_t = ctypes.c_size_t

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", size_t), ("WorkingSetSize", size_t),
            ("QuotaPeakPagedPoolUsage", size_t),
            ("QuotaPagedPoolUsage", size_t),
            ("QuotaPeakNonPagedPoolUsage", size_t),
            ("QuotaNonPagedPoolUsage", size_t),
            ("PagefileUsage", size_t), ("PeakPagefileUsage", size_t),
            ("PrivateUsage", size_t),
        ]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    handle = k32.OpenProcess(0x0400 | 0x0010, False, pid)
    if not handle:
        stop("OpenProcess: не удалось получить process private memory")
    try:
        value = Counters()
        value.cb = ctypes.sizeof(value)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(value), value.cb):
            stop("GetProcessMemoryInfo: невозможно контролировать ресурс")
        return int(value.PrivateUsage)
    finally:
        k32.CloseHandle(handle)


def output_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def check_nonphysical(exe: Path, argv: list[str], expected: str) -> str:
    result = subprocess.run([str(exe), *argv], capture_output=True, text=True,
                            timeout=90, errors="replace")
    output = result.stdout + result.stderr
    if result.returncode != 0 or expected not in output:
        stop(f"независимая проверка {argv} не пройдена: exit={result.returncode}: {output[-900:]}")
    return output[-3000:]


def evidence_zip(folder: Path, manifest: dict, physical_dir: Path, log_path: Path) -> Path:
    report = folder / "P10DD_RUN_MANIFEST.json"
    report.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    target = folder / "P10DD_EVIDENCE.zip"
    inputs = [report, log_path]
    for name in (
        "P10DD_SIGNED_R_THETA_PHI_T.csv",
        "P10DD_FULL4D_CLOSURE_AUDIT.csv",
        "P10W_ANALYTIC_ADJOINT.csv",
        "P10W_COMPONENTS.csv",
        "P10W_STEP_COMPONENTS.csv",
    ):
        path = physical_dir / name
        if path.is_file():
            inputs.append(path)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for path in inputs:
            archive.write(path, arcname=path.name)
    return target


def main(argv: list[str]) -> int:
    if sys.platform != "win32":
        stop("One Click предназначен для Windows 11; Linux использует unit/syntax")
    print("P10DD / H0: signed (r,theta,phi,t) physical QP jpeak / mode R")
    is_file(H0, "точная историческая M0=H0")
    h0_hash = sha256(H0)
    if h0_hash != H0_SHA:
        stop("хеш H0.msh неверен; другую сетку под именем M0 использовать нельзя")
    print("H0 mesh SHA256 verified:", h0_hash)
    exe = parse_path("Полный путь к собранному stage3d10dd_m0_h0_full4d.exe: ")
    is_file(exe, "новый EXE")
    if exe.name.lower() != APP_NAME:
        stop("неверное имя EXE, требуется именно stage3d10dd_m0_h0_full4d.exe")
    exe_hash = sha256(exe)
    print("EXE SHA256:", exe_hash)
    check_nonphysical(exe, ["--help"], "P10DD_FULL4D")
    check_nonphysical(exe, ["--selftest"], "P10W_DEPENDENCY_SELFTEST_OK")

    fresh = "--allow-fresh-forward" in argv
    cache = parse_path("Путь к существующему forward_history.bin для H0 (обязательно; Enter=STOP): ")
    if str(cache) == ".":
        if not fresh:
            stop("нет кэша H0; новый нелинейный forward не разрешён данным подготовительным пакетом")
        cache = None
    else:
        is_file(cache, "H0 forward cache")
        cache = cache.resolve()
    cache_hash = sha256(cache) if cache else None

    RUN_ROOT.mkdir(exist_ok=True)
    if shutil.disk_usage(RUN_ROOT).free < MIN_FREE_DISK:
        stop("меньше 3 ГиБ свободного места в отдельной папке вывода")
    marker = RUN_ROOT / "P10DD_ONE_SHOT_CONSUMED.json"
    if marker.exists():
        stop("One Shot marker уже существует, повторный физический запуск запрещён")
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = RUN_ROOT / ("P10DD_M0_H0_" + now)
    folder = RUN_ROOT / ("P10DD_EVIDENCE_" + now)
    if run_dir.exists() or folder.exists():
        stop("целевой каталог уже существует")
    cmd = [str(exe), "--mesh", str(H0), "--out", str(run_dir),
           "--mode", "R", "--steps", "6", "--dt", "150",
           "--cutoff-mm", "5", "--threads", "4"]
    if cache:
        cmd.extend(["--reuse-forward", str(cache)])

    print("\nПредстоящая физическая попытка: точная H0, 6x150s, EDV_VAR, xi=0")
    print("Forward:", "reuse immutable existing history" if cache else "NEW; separately authorized")
    print("STOP budgets: 900 s, process PrivateUsage 8 GiB, new output 1 GiB")
    print("Рабочий оригинал G:\\ildar\\Stage3D07 не изменяется; вывод в", RUN_ROOT)
    if input("Для ОДНОЙ физической попытки введите RUN ONE H0 P10DD: ").strip() != "RUN ONE H0 P10DD":
        stop("физический запуск не разрешён ручной фразой")
    # Marker is written BEFORE physical Popen; a failed attempt cannot repeat.
    folder.mkdir(exist_ok=False)
    manifest = {
        "protocol": "P10DD_R2_ONE_H0_4D", "status": "started",
        "mesh": str(H0), "mesh_sha256": h0_hash,
        "exe": str(exe), "exe_sha256": exe_hash,
        "forward_cache": str(cache) if cache else None,
        "forward_cache_sha256": cache_hash,
        "exact_command": cmd, "run_directory": str(run_dir),
        "started_utc": now, "native_exit_code": None,
        "output_records_expected": 7206,
    }
    with marker.open("x", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, ensure_ascii=False)
    print("ONE_SHOT_CONSUMED; starting one solver process now")

    log_path = folder / "P10DD_SOLVER_STDOUT_STDERR.txt"
    peak = 0
    stop_reason = ""
    started = time.monotonic()
    try:
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            while proc.poll() is None:
                time.sleep(1)
                if proc.poll() is not None:
                    break
                peak = max(peak, private_bytes_windows(proc.pid))
                elapsed = time.monotonic() - started
                if elapsed > LIMIT_S:
                    stop_reason = "WALL_BUDGET"
                elif peak > LIMIT_PRIVATE:
                    stop_reason = "PRIVATE_MEMORY_BUDGET"
                elif output_bytes(run_dir) > LIMIT_OUTPUT:
                    stop_reason = "OUTPUT_BUDGET"
                if stop_reason:
                    proc.terminate()
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    break
            native_exit = proc.wait()
    except BaseException as exc:
        stop_reason = stop_reason or f"WRAPPER_EXCEPTION_{type(exc).__name__}"
        if "proc" in locals() and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        native_exit = None
    manifest["native_exit_code"] = native_exit
    manifest["wall_s"] = time.monotonic() - started
    manifest["private_peak_bytes_polled"] = peak
    manifest["stop_reason"] = stop_reason
    manifest["status"] = "STOP" if stop_reason or native_exit != 0 else "solver_exit0"
    mandatory = [run_dir / "P10DD_SIGNED_R_THETA_PHI_T.csv",
                 run_dir / "P10DD_FULL4D_CLOSURE_AUDIT.csv"]
    if manifest["status"] == "solver_exit0" and not all(p.is_file() for p in mandatory):
        manifest["status"] = "STOP"
        manifest["stop_reason"] = "MISSING_4D_OUTPUT"
    if manifest["status"] == "solver_exit0":
        try:
            from P10DD_audit_evidence import Reader, audit

            reader = Reader(run_dir)
            try:
                manifest["independent_4d_check"] = audit(reader)
            finally:
                reader.close()
            manifest["status"] = "completed_4d_verified"
        except Exception as exc:
            manifest["status"] = "STOP"
            manifest["stop_reason"] = "INDEPENDENT_4D_CLOSURE_FAILED_" + repr(exc)
    evidence = evidence_zip(folder, manifest, run_dir, log_path)
    print("RESULT:", manifest["status"], "native_exit=", native_exit)
    print("EVIDENCE:", evidence)
    print("Передайте один P10DD_EVIDENCE.zip; старые H0/cache не удаляйте.")
    return 0 if manifest["status"] == "completed_4d_verified" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print("STOP:", exc)
        raise SystemExit(2)
