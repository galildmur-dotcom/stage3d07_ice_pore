"""Stage3D07 P10FN common platform, paths, strict pins and Windows job limits."""
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
import time
import zipfile

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
MESHES = PROJECT / "meshes"
RUNS = PROJECT / "LOCAL_RUNS"
SOURCE_PIN = HERE / "P10FN_SOURCE_SHA256.json"


def need(condition, why):
    if not condition:
        raise RuntimeError("P10FN_STOP: " + why)


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def validate_source():
    manifest = load(SOURCE_PIN)
    entries = manifest["files"]
    need(len(entries) >= 90, "source bundle incomplete")
    for rel, digest in entries.items():
        p = HERE / rel
        need(p.is_file() and sha256(p) == digest, "source SHA mismatch: " + rel)
    return manifest["revision"]


def require_windows():
    need(sys.platform == "win32", "launcher needs Windows 11; use --selftest on Linux")
    need(PROJECT.drive.upper() == "G:", "configured project drive changed")
    MESHES.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)


def prepare_run(kind, mesh):
    folder = RUNS / f"P10FN_{kind}_{mesh}_{now()}"
    folder.mkdir(parents=False, exist_ok=False)
    return folder


def free_ram_windows():
    class Memory(ctypes.Structure):
        _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in (
                "total", "available", "page_total", "page_available", "virtual_total",
                "virtual_available", "extended")]
    value = Memory()
    value.length = ctypes.sizeof(value)
    need(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)),
         "RAM query failed")
    return int(value.available)


class WindowsJob:
    """HARD process-private limit and kill-on-close; no orphaned FEM/Gmsh."""
    def __init__(self, cap):
        class Basic(ctypes.Structure):
            _fields_ = [("user_process", ctypes.c_int64), ("user_job", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("min_workset", ctypes.c_size_t),
                        ("max_workset", ctypes.c_size_t), ("active", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("schedule", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(k, ctypes.c_uint64) for k in ("r_ops", "w_ops", "o_ops", "r_bytes", "w_bytes", "o_bytes")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_limit", ctypes.c_size_t),
                        ("job_limit", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]
        self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k = self.k32
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.SetInformationJobObject.restype = wintypes.BOOL
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.AssignProcessToJobObject.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        self.handle = k.CreateJobObjectW(None, None)
        need(bool(self.handle), "CreateJobObjectW failed")
        info = Extended()
        info.basic.flags = 0x100 | 0x2000
        info.process_limit = cap
        if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            need(False, "Windows Job hard memory cap could not be installed")

    def assign(self, pid):
        handle = self.k32.OpenProcess(0x0100 | 0x0400 | 0x0001, False, pid)
        need(bool(handle), "OpenProcess for Job failed")
        try:
            need(self.k32.AssignProcessToJobObject(self.handle, handle),
                 "unable to attach process to protective Job")
        finally:
            self.k32.CloseHandle(handle)

    def close(self):
        if self.handle:
            self.k32.CloseHandle(self.handle)
            self.handle = None


def private_bytes(pid):
    class MemoryCounters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (k, ctypes.c_size_t) for k in (
                "peak_working", "working", "peak_paged", "paged", "peak_nonpaged",
                "nonpaged", "pagefile", "peak_pagefile", "private")]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    ps = ctypes.WinDLL("psapi", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    ps.GetProcessMemoryInfo.restype = wintypes.BOOL
    handle = k.OpenProcess(0x0400 | 0x0010, False, pid)
    need(bool(handle), "process RAM monitor failed")
    try:
        counts = MemoryCounters()
        counts.cb = ctypes.sizeof(counts)
        need(ps.GetProcessMemoryInfo(handle, ctypes.byref(counts), counts.cb),
             "GetProcessMemoryInfo failed")
        return int(counts.private)
    finally:
        k.CloseHandle(handle)


def capped_process(cmd, *, cwd, log, wall_s, memory_gib, output_dir, output_gib,
                   env=None):
    need(shutil.disk_usage(output_dir.parent).free >= 4 * 1024**3,
         "less than 4 GiB free disk")
    avail = free_ram_windows()
    need(avail >= 12 * 1024**3, "less than 12 GiB free RAM")
    cap = int(min(memory_gib * 1024**3, avail - 8 * 1024**3))
    need(cap >= 4 * 1024**3, "not enough safe private memory allowance")
    peak = 0
    code = None
    stop = ""
    start = time.monotonic()
    job = WindowsJob(cap)
    proc = None
    try:
        with log.open("x", encoding="utf-8") as sink:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=sink, stderr=subprocess.STDOUT)
            job.assign(proc.pid)
            while proc.poll() is None:
                time.sleep(0.5)
                if proc.poll() is not None:
                    break
                peak = max(peak, private_bytes(proc.pid))
                if time.monotonic() - start > wall_s:
                    stop = "WALL_LIMIT"
                elif sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file()) > output_gib * 1024**3:
                    stop = "OUTPUT_LIMIT"
                if stop:
                    proc.terminate()
                    break
            code = proc.wait(timeout=30)
    except BaseException as error:
        stop = stop or f"MONITOR_FAILURE_{type(error).__name__}:{error}"
    finally:
        job.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
    return {"native_exit_code": code, "wall_s": time.monotonic()-start,
            "peak_private_bytes_polled": peak, "job_private_limit_bytes": cap,
            "stop_reason": stop}


def zip_evidence(target, files):
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for source, arcname in files:
            if Path(source).is_file():
                out.write(source, arcname=arcname)
