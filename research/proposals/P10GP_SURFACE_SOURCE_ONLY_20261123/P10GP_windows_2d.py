#!/usr/bin/env python3
"""Protected one-shot Windows surface comparison. No 3D and no FEM."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import math
import statistics
import subprocess
import sys
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
RUNS = PROJECT / "LOCAL_RUNS"
GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
PARENT = HERE / "P10GP_R1_SURFACE_SOURCE_ONLY.zip"
RUNTIME = HERE / "P10GH_surface_compare.py"
PARENT_SHA = "236defb377103ef45e8ac193264fac8213290c7d00e02fc1025e53c9f700cc3a"
RUNTIME_SHA = ""  # replaced with the pinned published helper hash at packaging
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
REV = "P10GP_R2_ONE_GUARDED_2D_PAIR_WINDOWS"
PROOF = HERE / "P10GP_01_PROOF.json"
RESULT = HERE / "P10GP_02_RESULT.txt"
CASES = ("A_ORIGINAL_F3", "B_SELF_CONTAINED_C1_SOUTH")


def need(value, reason):
    if not value:
        raise RuntimeError("P10GP_STOP: " + reason)


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def hashfile(p: Path):
    return sha(p.read_bytes())


def utc():
    return datetime.now(timezone.utc)


def report(folder: Path, name: str, obj):
    with (folder / name).open("xb") as f:
        f.write((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def load_runtime():
    need(RUNTIME.is_file() and hashfile(RUNTIME) == RUNTIME_SHA, "runtime helper SHA changed")
    spec = importlib.util.spec_from_file_location("p10gp_windows_helper", RUNTIME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    need(mod.MAX_SECONDS == 120 and mod.MAX_PRIVATE == 2 * 1024**3, "resource caps changed")
    return mod


def parent_files():
    need(PARENT.is_file() and hashfile(PARENT) == PARENT_SHA, "parent source-only zip SHA changed")
    with zipfile.ZipFile(PARENT) as z:
        need(z.testzip() is None and len(z.namelist()) == 9, "parent zip CRC/file count")
        manifest = json.loads(z.read("P10GP_SOURCE_MANIFEST.json"))
        need(manifest["revision"] == "P10GP_R1_SOURCE_ONLY" and
             manifest["native_2d_runs"] == manifest["native_3d_runs"] == manifest["FEM_runs"] == 0,
             "source-only release changed")
        files = manifest["files_sha256"]
        need(set(z.namelist()) == set(files) | {"P10GP_SOURCE_MANIFEST.json"}, "zip contents changed")
        for name, digest in files.items():
            need(name.startswith(CASES) and ".." not in Path(name).parts and
                 sha(z.read(name)) == digest, "parent member SHA/path changed")
        need(manifest["field_factor"] == "0.9378887276834518" and
             manifest["element_order"] == 2 and manifest["surface_algorithm"] == 5,
             "size/surface policy changed")
        return {name: z.read(name) for name in files}


def installation():
    need(sys.platform == "win32", "Windows required")
    need(GMSH.is_file() and hashfile(GMSH) == GMSH_SHA, "Gmsh executable SHA changed")
    need((PROJECT / "meshes" / "M0.msh").is_file() and
         hashfile(PROJECT / "meshes" / "M0.msh") == M0_SHA, "M0 mesh pin changed")
    need(RUNS.is_dir(), "LOCAL_RUNS missing")
    proc = subprocess.run([str(GMSH), "-version"], capture_output=True, text=True, timeout=15)
    need(proc.returncode == 0 and "4.15.2" in proc.stdout, "Gmsh version mismatch")
    return {"Gmsh_SHA256": GMSH_SHA, "M0_SHA256": M0_SHA, "source_SHA256": PARENT_SHA,
            "helper_SHA256": RUNTIME_SHA}


def markers():
    local = RUNS / "P10GP_2D_LOCKS" / (M0_SHA[:24] + ".json")
    app = os.environ.get("LOCALAPPDATA", "")
    need(app and Path(app).is_dir(), "LOCALAPPDATA unavailable")
    global_marker = Path(app) / "Stage3D07" / "P10GP_2D" / (M0_SHA[:24] + ".json")
    return local, global_marker


def free():
    need(all(not p.exists() for p in markers()), "P10GP 02 already consumed: never retry")


def write_geos(folder: Path, files):
    for name, data in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out:  # no CRLF conversion
            out.write(data)
        need(hashfile(path) == sha(data), "generated GEO changed")


def evidence(folder: Path):
    out = folder / "P10GP_2D_EVIDENCE.zip"
    with zipfile.ZipFile(out, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file() and f != out and f.suffix.lower() in (".geo", ".log", ".json", ".txt", ".msh"):
                z.write(f, f.relative_to(folder).as_posix())
    need(zipfile.ZipFile(out).testzip() is None, "evidence CRC")
    need(out.stat().st_size <= 40 * 1024**2, "evidence exceeds 40 MiB")
    print("SEND THIS FILE:", out, flush=True)
    return out


def pore_edge_sizes(mesh: Path):
    """Read-only physical pore Tri6 median corner-edge sizes by polar sector."""
    nodes = {}
    groups = {"north": [], "south": [], "equator": [], "all_pore": []}
    with mesh.open("r", encoding="ascii") as file:
        for line in file:
            if line.strip() == "$Nodes":
                for _ in range(int(next(file))):
                    bits = next(file).split()
                    nodes[int(bits[0])] = tuple(float(x) for x in bits[1:4])
            if line.strip() == "$Elements":
                for _ in range(int(next(file))):
                    row = list(map(int, next(file).split()))
                    if row[1] != 9 or row[3] != 8:
                        continue
                    ids = row[3 + row[2]:3 + row[2] + 3]
                    need(len(ids) == 3, "pore triangle malformed")
                    pts = [nodes[i] for i in ids]
                    mid = [sum(p[k] for p in pts) / 3 for k in range(3)]
                    norm = math.sqrt(sum((mid[k] - (0.03 if k == 2 else 0))**2 for k in range(3)))
                    mu = (mid[2] - .03) / norm
                    lengths = [math.dist(pts[a], pts[b]) for a,b in ((0,1),(1,2),(2,0))]
                    groups["all_pore"].extend(lengths)
                    if mu >= .8:
                        groups["north"].extend(lengths)
                    if mu <= -.8:
                        groups["south"].extend(lengths)
                    if abs(mu) <= .2:
                        groups["equator"].extend(lengths)
    need(all(groups[k] for k in groups), "missing polar/equatorial size coverage")
    return {name: {"edges": len(v), "median_edge_m": statistics.median(v),
                   "min_edge_m": min(v), "max_edge_m": max(v)}
            for name, v in groups.items()}


def preflight():
    files = parent_files()
    load_runtime()
    installed = installation()
    free()
    folder = RUNS / ("P10GP_2D_PREFLIGHT_" + utc().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(exist_ok=False)
    write_geos(folder, files)
    checks = {}
    for case in CASES:
        p = folder / case / "P10GP_SURFACE.geo"
        cmd = [str(GMSH), str(p), "-parse_and_exit", "-nopopup", "-nt", "2"]
        q = subprocess.run(cmd, cwd=p.parent, capture_output=True, timeout=45)
        log = q.stdout + q.stderr
        (folder / case / "P10GP_PARSE.log").write_bytes(log)
        need(q.returncode == 0 and not re.search(rb"\bError\s*:", log), case + " parse failed")
        checks[case] = {"exit_code": q.returncode, "log_sha256": sha(log)}
    proof = {"revision": REV, "created": utc().isoformat(), "installed": installed,
             "files_sha256": {k: sha(v) for k, v in files.items()}, "parse": checks}
    PROOF.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    report(folder, "P10GP_PREFLIGHT.json", proof)
    evidence(folder)
    print("P10GP_PREFLIGHT_PASS_NO_MESH", flush=True)


def one_pair():
    files = parent_files()
    helper = load_runtime()
    installed = installation()
    free()
    need(PROOF.is_file(), "run 01 first")
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    age = (utc() - datetime.fromisoformat(proof["created"])).total_seconds()
    need(proof["revision"] == REV and proof["installed"] == installed and 0 <= age <= 86400,
         "preflight expired or changed")
    need(proof["files_sha256"] == {k: sha(v) for k, v in files.items()}, "source differs from preflight")
    folder = RUNS / ("P10GP_2D_PAIR_" + utc().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(exist_ok=False)
    write_geos(folder, files)
    for p in markers():
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("x", encoding="utf-8") as stream:
            json.dump({"revision": REV, "time": utc().isoformat(), "limit_2d": 2}, stream)
    result = {"revision": REV, "status": "STOP", "native_2d_attempts": 0,
              "native_3d_attempts": 0, "FEM_attempts": 0, "cases": {}, "installed": installed}
    try:
        for case in CASES:
            p = folder / case
            helper.GMSH = GMSH
            geo = p / "P10GP_SURFACE.geo"
            mesh = p / "P10GP_SURFACE.msh"
            log = p / "P10GP_GMSH_2D.log"
            result["native_2d_attempts"] += 1
            print("P10GP native -2", case, "max 120s/2GiB", flush=True)
            native = helper.run_surface_bounded(geo, mesh, log)
            result["cases"][case] = {"native": native, "surface": helper.audit_surface(mesh),
                                      "pore_edge_size": pore_edge_sizes(mesh)}
        result["status"] = "BOTH_2D_DONE_PENDING_INDEPENDENT_AUDIT"
        a = result["cases"][CASES[0]]["pore_edge_size"]
        b = result["cases"][CASES[1]]["pore_edge_size"]
        result["median_edge_ratios_B_over_A"] = {
            name: b[name]["median_edge_m"] / a[name]["median_edge_m"] for name in a}
    except Exception as exc:
        result["error"] = repr(exc)
        (folder / "P10GP_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        report(folder, "P10GP_MANIFEST.json", result)
        out = evidence(folder)
        RESULT.write_text("P10GP_RESULT=" + result["status"] + "\nEVIDENCE=" + str(out) +
                          "\nDO_NOT_REPEAT_02=YES\n", encoding="utf-8")
    return 0 if result["status"].startswith("BOTH") else 2


def main():
    need(len(sys.argv) == 2, "use --selftest/--preflight/--one-2d-pair")
    if sys.argv[1] == "--selftest":
        files = parent_files()
        load_runtime()
        print("P10GP_SOURCE_AND_RUNTIME_PASS", len(files), "source files; native=0")
        return 0
    if sys.argv[1] == "--preflight":
        preflight()
        return 0
    if sys.argv[1] == "--one-2d-pair":
        return one_pair()
    need(False, "unknown mode")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("P10GP_STOP", repr(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
