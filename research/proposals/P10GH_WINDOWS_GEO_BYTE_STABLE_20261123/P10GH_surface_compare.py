#!/usr/bin/env python3
"""P10GH: guarded native Windows Gmsh 4.15.2 OCC-pole 2D comparison.

Two surface-only runs, identical M0 size field and h-scale, with a single
CAD parameterization rotation. Never meshes 3D, calls FEM or edits old meshes.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
MESHES = PROJECT / "meshes"
RUNS = PROJECT / "LOCAL_RUNS"
GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
PIN = HERE / "P10GH_SOURCE_SHA256.json"
PROOF = HERE / "P10GH_PREFLIGHT_PROOF.json"
REV = "P10GH_R1_TWO_OCC_PARAMETERIZATIONS_2D_ONLY_NO_FEM"
M0_MSH_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M0_GEO_SHA = "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
SCALE = 0.825 ** (1.0 / 3.0)
MAX_MSH = 12 * 1024 * 1024
MAX_LOG = 4 * 1024 * 1024
MAX_SECONDS = 120
MAX_PRIVATE = 2 * 1024**3
PACKAGE = {
    "P10GH_surface_compare.py", "01_P10GH_PREFLIGHT_ONLY.cmd",
    "02_P10GH_ONE_2D_PAIR_ONLY.cmd", "README_P10GH_RU.md",
    "M0.geo", "sphere_pore_B6_refined.geo",
}
CAD_ANCHOR = "Sphere(3) = {poreCX,poreCY,poreCZ,r0};"
CAD_ROTATE = "Rotate { {1,0,0}, {poreCX,poreCY,poreCZ}, Pi/2 } { Volume{3}; }"
BASE_INCLUDE = 'Include "sphere_pore_B6_refined.geo";'


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError("P10GH_STOP: " + reason)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_new(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S_%f")


def source_gate() -> dict:
    manifest = read_json(PIN)
    need(manifest.get("revision") == REV, "release revision mismatch")
    need(manifest.get("parent_M0_msh_sha256") == M0_MSH_SHA and
         manifest.get("canonical_M0_geo_sha256") == M0_GEO_SHA and
         manifest.get("canonical_OCC_CAD_sha256") == CAD_SHA,
         "parent M0/CAD pin mismatch")
    need(manifest.get("native_2d_attempts") == 2 and
         manifest.get("native_3d_attempts") == 0 and
         manifest.get("FEM_attempts") == 0, "invalid release scope")
    need(set(manifest.get("files", {})) == PACKAGE, "manifest files differ")
    need(abs(manifest.get("uniform_volume_target", 0) - .825) < 1e-15,
         "unexpected M1 uniform size target")
    for name, expected in manifest["files"].items():
        p = HERE / name
        need(p.is_file() and sha256(p) == expected, "source missing/tampered: " + name)
    need(sha256(HERE / "M0.geo") == M0_GEO_SHA and
         sha256(HERE / "sphere_pore_B6_refined.geo") == CAD_SHA,
         "pinned canonical source changed")
    return manifest


def variants() -> dict[str, str]:
    cad = (HERE / "sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    base = (HERE / "M0.geo").read_text(encoding="utf-8")
    need(cad.count(CAD_ANCHOR) == 1 and cad.count("BooleanDifference") == 2,
         "canonical CAD anchors changed")
    need(base.count(BASE_INCLUDE) == 1 and
         base.count("Mesh.MeshSizeFactor=1;") == 1 and
         base.count("Background Field=3;") == 1,
         "canonical M0 sizing anchors changed")
    rot_cad = cad.replace(CAD_ANCHOR, CAD_ANCHOR + "\n" + CAD_ROTATE)
    rot_base = base.replace(BASE_INCLUDE,
                            'Include "sphere_pore_B6_refined_rotated.geo";')
    # The exact same field, algorithm and h scale in both variants.
    tail = ("// P10GH: native 2D only, no volume/FEM.\n"
            f"Mesh.MeshSizeFactor={SCALE:.17g};\n"
            "Mesh.ElementOrder=2;\nMesh.MshFileVersion=2.2;\n"
            "Mesh.Binary=0;\n")
    orig_driver = 'Include "M0.geo";\n' + tail
    rot_driver = 'Include "M0_ROTATED.geo";\n' + tail
    need(rot_cad.replace(CAD_ANCHOR + "\n" + CAD_ROTATE, CAD_ANCHOR) == cad,
         "rotated CAD contains other changes")
    need(rot_base.replace('Include "sphere_pore_B6_refined_rotated.geo";',
                          BASE_INCLUDE) == base,
         "rotated baseline size field changed")
    need(not ("-3" in orig_driver or "-3" in rot_driver), "forbidden mesh command")
    return {"M0.geo": base, "M0_ROTATED.geo": rot_base,
            "sphere_pore_B6_refined.geo": cad,
            "sphere_pore_B6_refined_rotated.geo": rot_cad,
            "P10GH_ORIGINAL_SURFACE.geo": orig_driver,
            "P10GH_ROTATED_SURFACE.geo": rot_driver}


def source_selftest() -> dict:
    files = variants()
    # Changing CAD parameterization does not move the exact OCC sphere.
    need("Sphere(3)" in files["sphere_pore_B6_refined_rotated.geo"] and
         files["sphere_pore_B6_refined_rotated.geo"].count(CAD_ROTATE) == 1,
         "rotated sphere not uniquely defined")
    need(abs(SCALE**3 - .825) < 1e-14, "cubic size-scale identity failed")
    need("Mesh.Algorithm=5;" in files["M0.geo"] and
         "Mesh.ElementOrder=2;" in files["M0.geo"],
         "2D Delaunay/Tri6 baseline changed")
    return {"test": "P10GH_SOURCE_SELFTEST_PASS_NO_MESH",
            "target_volume_ratio": .825, "h_scale": SCALE,
            "generated_sha256": {k: digest(v.encode("utf-8"))
                                 for k, v in sorted(files.items())},
            "cad_invariant": "sphere is only rotated about its own centre",
            "native_2d_attempts": 0, "native_3d_attempts": 0,
            "FEM_attempts": 0}


def write_geos(folder: Path) -> dict[str, str]:
    result = variants()
    expected = source_selftest()["generated_sha256"]
    written = {}
    for name, contents in result.items():
        # Byte-for-byte stable on Windows: text-mode writes silently convert
        # LF to CRLF and invalidated the P10GG preflight-to-02 proof.
        with (folder / name).open("xb") as out:
            out.write(contents.encode("utf-8"))
        written[name] = sha256(folder / name)
        need(written[name] == expected[name],
             "generated GEO bytes differ from pinned source: " + name)
    return written


def profile_marker() -> Path:
    appdata = os.environ.get("LOCALAPPDATA", "")
    need(bool(appdata) and Path(appdata).is_dir(),
         "LOCALAPPDATA unavailable for permanent one-shot marker")
    return Path(appdata) / "Stage3D07" / "P10GH_M0_" / (M0_MSH_SHA[:20] + ".json")


def local_marker() -> Path:
    return RUNS / "P10GH_LOCKS" / ("P10GH_M0_" + M0_MSH_SHA[:20] + ".json")


def one_shot_free() -> None:
    need(not local_marker().exists() and not profile_marker().exists(),
         "P10GH attempt already consumed; preserve markers and evidence")
    # P10GG was stopped by the preflight digest mismatch before any Gmsh -2.
    # If an old marker exists, its history is not this known pre-mesh STOP.
    old_local = RUNS / "P10GG_LOCKS" / ("P10GG_M0_" + M0_MSH_SHA[:20] + ".json")
    appdata = os.environ.get("LOCALAPPDATA", "")
    need(bool(appdata), "LOCALAPPDATA missing for legacy attempt audit")
    old_profile = Path(appdata) / "Stage3D07" / "P10GG_M0_" / (M0_MSH_SHA[:20] + ".json")
    need(not old_local.exists() and not old_profile.exists(),
         "prior P10GG native attempt marker exists; no further attempt allowed")


def windows_gate() -> dict:
    need(sys.platform == "win32", "Windows 11 required for native Gmsh")
    need(RUNS.is_dir() and MESHES.is_dir(), "existing G: project folders missing")
    need(GMSH.is_file(), "Gmsh 4.15.2 EXE missing at configured location")
    for name, expected in (("M0.msh", M0_MSH_SHA),
                           ("M0.geo", M0_GEO_SHA),
                           ("sphere_pore_B6_refined.geo", CAD_SHA)):
        p = MESHES / name
        need(p.is_file() and sha256(p) == expected,
             "pinned user M0/CAD file missing or changed: " + name)
    version = subprocess.run([str(GMSH), "-version"], cwd=HERE,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=15, check=False)
    output = version.stdout.decode("utf-8", errors="replace").strip()
    need(version.returncode == 0 and "4.15.2" in output,
         "native Gmsh version must be 4.15.2")
    return {"gmsh_version": output, "gmsh_exe_sha256": sha256(GMSH),
            "M0_sha256": M0_MSH_SHA, "source_pin_sha256": sha256(PIN)}


def native_parse(path: Path, folder: Path, name: str) -> dict:
    log = folder / (name + "_PARSE.log")
    cmd = [str(GMSH), str(path), "-parse_and_exit", "-nopopup", "-nt", "2"]
    run = subprocess.run(cmd, cwd=folder, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         timeout=45, check=False)
    data = run.stdout[:MAX_LOG].decode("utf-8", errors="replace")
    log.write_text(data, encoding="utf-8")
    need(run.returncode == 0 and not re.search(r"\bError\s*:", data),
         "Gmsh parse-only failed: " + name)
    return {"exit": run.returncode, "log_sha256": sha256(log),
            "log_bytes": log.stat().st_size}


def preflight() -> int:
    source_gate()
    test = source_selftest()
    installed = windows_gate()
    one_shot_free()
    folder = RUNS / ("P10GH_PREFLIGHT_" + stamp())
    folder.mkdir(exist_ok=False)
    generated = write_geos(folder)
    report = {"revision": REV, "status": "P10GH_PREFLIGHT_STOP",
              "native_2d_attempts": 0, "native_3d_attempts": 0,
              "FEM_attempts": 0, "generated_sha256": generated,
              "installed": installed, "source_test": test}
    try:
        report["original_parse"] = native_parse(
            folder / "P10GH_ORIGINAL_SURFACE.geo", folder, "ORIGINAL")
        report["rotated_parse"] = native_parse(
            folder / "P10GH_ROTATED_SURFACE.geo", folder, "ROTATED")
        report["status"] = "P10GH_PREFLIGHT_PASS_NO_MESH"
        proof = {"revision": REV, "time_utc": utc_now().isoformat(),
                 "preflight_run": str(folder), **installed,
                 "generated_sha256": generated, "native_2d_attempts": 0}
        # A repeated 01 is allowed before the one-shot 02; overwrite proof only.
        PROOF.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
        print("P10GH_PREFLIGHT_PASS_NO_MESH", flush=True)
        code = 0
    except BaseException as exc:
        report["error"] = repr(exc)
        (folder / "P10GH_PREFLIGHT_STOP_TRACE.txt").write_text(
            traceback.format_exc(), encoding="utf-8")
        code = 2
    write_json_new(folder / "P10GH_PREFLIGHT_REPORT.json", report)
    make_evidence(folder, "P10GH_PREFLIGHT_EVIDENCE.zip")
    print("P10GH_PREFLIGHT_REPORT:", folder, flush=True)
    return code


def proof_gate(installed: dict) -> dict:
    need(PROOF.is_file(), "run 01 preflight first (proof missing)")
    proof = read_json(PROOF)
    need(proof.get("revision") == REV and proof.get("M0_sha256") == M0_MSH_SHA,
         "preflight proof belongs to different source")
    need(proof.get("source_pin_sha256") == sha256(PIN) and
         proof.get("gmsh_exe_sha256") == installed["gmsh_exe_sha256"],
         "source or Gmsh EXE changed since preflight")
    age = (utc_now() - datetime.fromisoformat(proof["time_utc"])).total_seconds()
    need(0 <= age <= 24 * 3600, "preflight proof older than 24 hours")
    need(proof.get("generated_sha256") == source_selftest()["generated_sha256"],
         "generated GEO changed since preflight")
    return proof


class WindowsJob:
    """Hard 2 GiB process-private Windows limit; kill process on job close."""
    def __init__(self, cap: int):
        class Basic(ctypes.Structure):
            _fields_ = [("user_process", ctypes.c_int64),
                        ("user_job", ctypes.c_int64),
                        ("flags", wintypes.DWORD),
                        ("min_workset", ctypes.c_size_t),
                        ("max_workset", ctypes.c_size_t),
                        ("active", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t),
                        ("priority", wintypes.DWORD),
                        ("schedule", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(k, ctypes.c_uint64) for k in
                        ("r_ops", "w_ops", "o_ops", "r_bytes", "w_bytes", "o_bytes")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO),
                        ("process_limit", ctypes.c_size_t),
                        ("job_limit", ctypes.c_size_t),
                        ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]
        self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k = self.k32
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                              ctypes.c_void_p, wintypes.DWORD]
        k.SetInformationJobObject.restype = wintypes.BOOL
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.AssignProcessToJobObject.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        self.handle = k.CreateJobObjectW(None, None)
        need(bool(self.handle), "cannot create Windows protective Job")
        info = Extended()
        info.basic.flags = 0x100 | 0x2000
        info.process_limit = cap
        if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(info),
                                         ctypes.sizeof(info)):
            self.close()
            need(False, "cannot apply private 2 GiB Job limit")

    def assign(self, pid: int) -> None:
        k = self.k32
        handle = k.OpenProcess(0x0100 | 0x0400 | 0x0001, False, pid)
        need(bool(handle), "cannot open Gmsh process for Job")
        try:
            need(bool(k.AssignProcessToJobObject(self.handle, handle)),
                 "cannot assign Gmsh process to protective Job")
        finally:
            k.CloseHandle(handle)

    def close(self) -> None:
        if self.handle:
            self.k32.CloseHandle(self.handle)
            self.handle = None


def private_bytes(pid: int) -> int:
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (k, ctypes.c_size_t) for k in
            ("peak_working", "working", "peak_paged", "paged", "peak_nonpaged",
             "nonpaged", "pagefile", "peak_pagefile", "private")]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    ps = ctypes.WinDLL("psapi", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    ps.GetProcessMemoryInfo.restype = wintypes.BOOL
    handle = k.OpenProcess(0x0400 | 0x0010, False, pid)
    need(bool(handle), "Gmsh memory monitor could not open process")
    try:
        v = Counters()
        v.cb = ctypes.sizeof(v)
        need(bool(ps.GetProcessMemoryInfo(handle, ctypes.byref(v), v.cb)),
             "Gmsh process memory query failed")
        return int(v.private)
    finally:
        k.CloseHandle(handle)


def run_surface_bounded(geo: Path, msh: Path, log: Path) -> dict:
    cmd = [str(GMSH), str(geo), "-2", "-nopopup", "-nt", "2",
           "-format", "msh2", "-o", str(msh)]
    need(cmd.count("-2") == 1 and "-3" not in cmd and "-save_all" not in cmd,
         "forbidden Gmsh command")
    start = time.monotonic()
    job = WindowsJob(MAX_PRIVATE)
    proc = None
    status = ""
    exit_code = None
    peak = 0
    try:
        with log.open("x", encoding="utf-8") as sink:
            proc = subprocess.Popen(cmd, cwd=geo.parent, stdin=subprocess.DEVNULL,
                                    stdout=sink, stderr=subprocess.STDOUT)
            job.assign(proc.pid)
            while proc.poll() is None:
                time.sleep(.25)
                if proc.poll() is not None:
                    break
                peak = max(peak, private_bytes(proc.pid))
                if time.monotonic() - start > MAX_SECONDS:
                    status = "WALL_LIMIT"
                elif log.stat().st_size > MAX_LOG:
                    status = "LOG_LIMIT"
                elif msh.is_file() and msh.stat().st_size > MAX_MSH:
                    status = "MSH_LIMIT"
                if status:
                    proc.terminate()
                    break
            exit_code = proc.wait(timeout=15)
    except BaseException as exc:
        status = status or ("MONITOR_FAILURE_" + repr(exc))
    finally:
        job.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
    result = {"command": cmd, "exit_code": exit_code,
              "wall_s": round(time.monotonic() - start, 3),
              "peak_private_bytes_polled": peak, "job_private_limit_bytes": MAX_PRIVATE,
              "max_wall_s": MAX_SECONDS, "max_msh_bytes": MAX_MSH,
              "max_log_bytes": MAX_LOG, "stop_reason": status,
              "native_3d_attempts": 0, "FEM_attempts": 0}
    need(not status and exit_code == 0 and msh.is_file() and
         0 < msh.stat().st_size <= MAX_MSH and log.stat().st_size <= MAX_LOG,
         "native 2D execution or resource gate failed: " + str(result))
    text = log.read_text(encoding="utf-8", errors="replace")
    need("Done meshing 2D" in text and not re.search(r"\bError\s*:", text),
         "Gmsh 2D completion or error log failed")
    result["msh_sha256"] = sha256(msh)
    result["log_sha256"] = sha256(log)
    return result


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    return math.sqrt(sum(v * v for v in a))


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _quantile(vals, p):
    data = sorted(vals)
    if not data:
        return None
    k = (len(data) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return data[lo] * (hi - k) + data[hi] * (k - lo) if hi != lo else data[lo]


def _curved_jac(tri, r, s):
    l = 1.0 - r - s
    dr = (1 - 4*l, 4*r - 1, 0, 4*(l-r), 4*s, -4*s)
    ds = (1 - 4*l, 0, 4*s - 1, -4*r, 4*r, 4*(l-s))
    u = tuple(sum(dr[i]*tri[i][k] for i in range(6)) for k in range(3))
    v = tuple(sum(ds[i]*tri[i][k] for i in range(6)) for k in range(3))
    return _norm(_cross(u, v))


def audit_surface(msh: Path) -> dict:
    """Independent MSH2 physical Tri6 audit. No FEM, no 3D inference."""
    nodes, tris, types = {}, [], {}
    with msh.open("r", encoding="ascii") as f:
        for line in f:
            t = line.strip()
            if t == "$Nodes":
                for _ in range(int(next(f))):
                    fields = next(f).split()
                    need(len(fields) == 4, "malformed MSH2 node")
                    nodes[int(fields[0])] = tuple(map(float, fields[1:]))
            elif t == "$Elements":
                for _ in range(int(next(f))):
                    fields = list(map(int, next(f).split()))
                    _, kind, ntags = fields[:3]
                    tags = fields[3:3+ntags]
                    conn = fields[3+ntags:]
                    types[kind] = types.get(kind, 0) + 1
                    need(kind not in (4, 11, 29, 30, 31), "3D element in -2 output")
                    if kind == 9:
                        need(ntags >= 1 and len(conn) == 6,
                             "Tri6 physical tag/connectivity missing")
                        tris.append((tags[0], conn))
    need(nodes and tris, "no 2D nodes or Tri6")
    counts = {p: 0 for p in range(2, 10)}
    area = {8: 0., 9: 0.}
    qualities, polar = [], {"N": [], "S": []}
    radius_err = {8: 0., 9: 0.}
    jac_min = float("inf")
    all_worst = []
    qpoints = ((1/6, 1/6), (2/3, 1/6), (1/6, 2/3))
    for physical, conn in tris:
        need(physical in counts, "unexpected Tri6 physical tag: " + str(physical))
        counts[physical] += 1
        pts = [nodes[i] for i in conn]
        a, b, c = (_norm(_sub(pts[0], pts[1])),
                   _norm(_sub(pts[1], pts[2])),
                   _norm(_sub(pts[2], pts[0])))
        denom = a*a + b*b + c*c
        corner_area = .5 * _norm(_cross(_sub(pts[1],pts[0]),
                                        _sub(pts[2],pts[0])))
        q = 4 * math.sqrt(3) * corner_area / denom if denom > 0 else 0
        need(math.isfinite(q) and q > 0.001, "degenerate corner Tri6")
        if physical not in (8, 9):
            continue
        centre = tuple(sum(pts[i][k] for i in range(3))/3 for k in range(3))
        rho = _norm(_sub(centre, (0.,0.,.03)))
        mu = (centre[2]-.03)/rho if rho else 0
        jac = [_curved_jac(pts, r, s) for r,s in qpoints]
        need(all(math.isfinite(v) and v > 0 for v in jac),
             "nonpositive curved Tri6 Jacobian on physical sphere")
        jac_min = min(jac_min, *jac)
        area[physical] += sum(jac)/6
        expected_r = .001 if physical == 8 else .006
        radius_err[physical] = max(radius_err[physical],
                                   *(abs(_norm(_sub(p,(0.,0.,.03))) - expected_r)
                                     for p in pts))
        if physical == 8:
            qualities.append(q)
            all_worst.append((q, centre, mu))
            if mu >= .8:
                polar["N"].append(q)
            if mu <= -.8:
                polar["S"].append(q)
    need(all(n > 0 for n in counts.values()), "missing physical surface group 2..9")
    need(qualities and polar["N"] and polar["S"],
         "missing pore wall or polar Tri6 coverage")
    need(radius_err[8] <= 1e-8 and radius_err[9] <= 1e-8,
         "sphere radius not preserved after CAD rotation")
    need(.90 <= area[8]/(4*math.pi*.001**2) <= 1.10,
         "curved pore area outside conservative geometry range")
    worst = min(all_worst, key=lambda x:x[0])
    return {"physical_tri6_counts": counts, "element_types": types,
            "nodes": len(nodes), "total_tri6": len(tris),
            "pore_tri6": len(qualities),
            "q_corner_min": min(qualities),
            "q_corner_p05": _quantile(qualities, .05),
            "q_corner_median": statistics.median(qualities),
            "north_polar_tri6": len(polar["N"]),
            "south_polar_tri6": len(polar["S"]),
            "north_polar_qmin": min(polar["N"]),
            "south_polar_qmin": min(polar["S"]),
            "worst_xyz_m": worst[1], "worst_mu": worst[2],
            "pore_curved_area_m2": area[8],
            "pore_area_ratio_exact": area[8]/(4*math.pi*.001**2),
            "B6_curved_area_m2": area[9],
            "minimum_curved_surface_jacobian": jac_min,
            "max_pore_radius_node_error_m": radius_err[8],
            "max_B6_radius_node_error_m": radius_err[9],
            "diagnostic_only_not_volume_or_FEM_GO": True}


def make_evidence(folder: Path, name: str) -> Path:
    target = folder / name
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for file in sorted(folder.iterdir()):
            if (file.is_file() and file != target and
                file.stat().st_size <= MAX_MSH):
                out.write(file, file.name)
        out.write(PIN, PIN.name)
    need(target.stat().st_size <= 32 * 1024**2, "evidence ZIP exceeds 32 MiB")
    print("SEND THIS FILE:", target, flush=True)
    return target


def run_pair() -> int:
    source_gate()
    installed = windows_gate()
    one_shot_free()
    proof = proof_gate(installed)
    folder = RUNS / ("P10GH_CAD_POLES_" + stamp())
    folder.mkdir(exist_ok=False)
    generated = write_geos(folder)
    need(generated == proof["generated_sha256"],
         "GEO not identical to passing preflight")
    marker = {"revision": REV, "time_utc": utc_now().isoformat(),
              "M0_sha256": M0_MSH_SHA, "source_pin_sha256": sha256(PIN),
              "native_2d_max_attempts": 2, "native_3d_max_attempts": 0,
              "FEM_max_attempts": 0}
    # Both exclusive markers are permanent and created BEFORE either -2 run.
    write_json_new(local_marker(), marker)
    write_json_new(profile_marker(), marker)
    report = {"revision": REV, "status": "P10GH_2D_STOP_NO_3D_NO_FEM",
              "installed": installed, "generated_sha256": generated,
              "native_2d_attempts": 0, "native_3d_attempts": 0,
              "FEM_attempts": 0, "results": {},
              "warning": "2D parameterization effect is not 3D density evidence"}
    code = 2
    try:
        for label in ("ORIGINAL", "ROTATED"):
            geo = folder / ("P10GH_" + label + "_SURFACE.geo")
            msh = folder / ("P10GH_" + label + "_2D.msh")
            log = folder / ("P10GH_" + label + "_2D.log")
            report["native_2d_attempts"] += 1
            print("P10GH RUN 2D", label, "max 120s/2GiB, no -3/FEM", flush=True)
            proc = run_surface_bounded(geo, msh, log)
            report["results"][label] = {"native": proc,
                                        "surface": audit_surface(msh)}
        a = report["results"]["ORIGINAL"]["surface"]
        b = report["results"]["ROTATED"]["surface"]
        report["comparison"] = {
            "q_corner_min_delta_rotated_minus_original":
                b["q_corner_min"] - a["q_corner_min"],
            "north_polar_qmin_delta":
                b["north_polar_qmin"] - a["north_polar_qmin"],
            "south_polar_qmin_delta":
                b["south_polar_qmin"] - a["south_polar_qmin"],
            "pore_tri6_count_delta": b["pore_tri6"] - a["pore_tri6"]}
        report["status"] = "P10GH_SURFACE_ONLY_PASS_NO_3D_NO_FEM"
        code = 0
    except BaseException as exc:
        report["error"] = repr(exc)
        (folder / "P10GH_STOP_TRACE.txt").write_text(traceback.format_exc(),
                                                      encoding="utf-8")
    finally:
        write_json_new(folder / "P10GH_CAD_POLE_METRICS.json", report)
        make_evidence(folder, "P10GH_CAD_POLE_2D_EVIDENCE.zip")
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--one-2d-pair", action="store_true")
    args = parser.parse_args()
    source_gate()
    if args.selftest:
        print(json.dumps(source_selftest(), ensure_ascii=False, indent=2))
        return 0
    if args.preflight:
        return preflight()
    return run_pair()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("P10GH_STOP:", repr(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
