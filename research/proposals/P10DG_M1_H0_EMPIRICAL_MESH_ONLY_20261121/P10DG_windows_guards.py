"""Shared Windows Gmsh process guards for the bounded P10DG mesh-only run."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("P10DG_STOP: " + message)


def free_windows_ram() -> int:
    class MEM(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.wintypes.DWORD),
                    ("dwMemoryLoad", ctypes.wintypes.DWORD)] + [
                        (name, ctypes.c_ulonglong) for name in
                        ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile",
                         "ullAvailPageFile", "ullTotalVirtual", "ullAvailVirtual",
                         "ullAvailExtendedVirtual")]
    info = MEM()
    info.dwLength = ctypes.sizeof(MEM)
    require(bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info))),
            "Windows memory probe unavailable")
    return int(info.ullAvailPhys)


def child_private_bytes(process: subprocess.Popen) -> int:
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
    counters = COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    function = ctypes.windll.psapi.GetProcessMemoryInfo
    function.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(COUNTERS),
                         ctypes.wintypes.DWORD]
    function.restype = ctypes.wintypes.BOOL
    require(bool(function(ctypes.wintypes.HANDLE(int(process._handle)),
                          ctypes.byref(counters), ctypes.sizeof(counters))),
            "Windows private memory monitor failed")
    return int(counters.PrivateUsage)


def command(argv: list[str], workdir: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(workdir), stdin=subprocess.DEVNULL,
                          text=True, capture_output=True, timeout=timeout,
                          check=False, errors="replace")
