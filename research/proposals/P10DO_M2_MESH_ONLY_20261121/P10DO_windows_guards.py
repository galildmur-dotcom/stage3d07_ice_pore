"""Bounded Windows process/read-only input guards for P10DO M2 Gmsh only."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
from pathlib import Path
import subprocess


def require(condition: bool, why: str) -> None:
    if not condition:
        raise RuntimeError("P10DO_STOP: " + why)


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def free_windows_ram() -> int:
    class MEM(ctypes.Structure):
        _fields_=[("dwLength",ctypes.wintypes.DWORD),
                  ("dwMemoryLoad",ctypes.wintypes.DWORD)]+[
                      (name,ctypes.c_ulonglong) for name in
                      ("ullTotalPhys","ullAvailPhys","ullTotalPageFile",
                       "ullAvailPageFile","ullTotalVirtual","ullAvailVirtual",
                       "ullAvailExtendedVirtual")]
    obj=MEM()
    obj.dwLength=ctypes.sizeof(MEM)
    require(bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(obj))),
            "Windows available RAM probe failed")
    return int(obj.ullAvailPhys)


def child_private_bytes(process: subprocess.Popen) -> int:
    class COUNTERS(ctypes.Structure):
        _fields_=[("cb",ctypes.wintypes.DWORD),
                  ("PageFaultCount",ctypes.wintypes.DWORD),
                  ("PeakWorkingSetSize",ctypes.c_size_t),
                  ("WorkingSetSize",ctypes.c_size_t),
                  ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                  ("QuotaPagedPoolUsage",ctypes.c_size_t),
                  ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                  ("QuotaNonPagedPoolUsage",ctypes.c_size_t),
                  ("PagefileUsage",ctypes.c_size_t),
                  ("PeakPagefileUsage",ctypes.c_size_t),
                  ("PrivateUsage",ctypes.c_size_t)]
    obj=COUNTERS()
    obj.cb=ctypes.sizeof(COUNTERS)
    fn=ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes=[ctypes.wintypes.HANDLE,ctypes.POINTER(COUNTERS),ctypes.wintypes.DWORD]
    fn.restype=ctypes.wintypes.BOOL
    require(bool(fn(ctypes.wintypes.HANDLE(int(process._handle)),
                    ctypes.byref(obj),ctypes.sizeof(obj))),
            "Windows Gmsh private usage monitor failed")
    return int(obj.PrivateUsage)


def command(argv: list[str], workdir: Path, timeout: int=30) -> subprocess.CompletedProcess:
    return subprocess.run(argv,cwd=str(workdir),stdin=subprocess.DEVNULL,
                          text=True,capture_output=True,timeout=timeout,
                          check=False,errors="replace")
