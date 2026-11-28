#!/usr/bin/env python3
"""P10GD: safe native 1D/2D parametric field topology measurements only.

No Gmsh -3, no FEM, no writes to meshes, approvals or older markers.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import traceback
import zipfile

import P10FX_uniform_math as previous
import P10GB_adapt_math as latest

HERE = Path(__file__).resolve().parent
ROOT = Path(r"G:\ildar\Stage3D07")
MESHES = ROOT / "meshes"
RUNS = ROOT / "LOCAL_RUNS"
GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
REV = "P10GD_R1_SURFACE_FIELD_SWEEP_ONLY_NO_3D_NO_FEM"
PIN = HERE / "P10GD_SOURCE_SHA256.json"
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M0_GEO_SHA = "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
M1V_SHA = "c3f69d3d6f3d88333f2aec7a5aa13db535f9eed4e76ba6c29bed4b88fa31ea06"
M1V_GEO_SHA = "de15b2f1d6454f06cb2f53731936558288dce933afd1642aada82b42022886aa"
M1W_SHA = "fe77956c50534bfd0b6f84954b07f195e6449648bd71d5a6640d048aea9a5df2"
M1W_GEO_SHA = "3e488bcf7ca25778f13b9eddb50c2fb5029a559bb078955e23d5015c57114bd0"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
THETAS = (0, .125, .25, .375, .5, .625, .75, .875, 1)


def need(test, message):
    if not test:
        raise RuntimeError("P10GD_STOP: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save(path, payload):
    with path.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def read_manifest_and_check():
    meta = json.loads(PIN.read_text(encoding="utf-8"))
    need(meta.get("revision") == REV and meta.get("native_3d_max_attempts") == 0
         and meta.get("FEM_max_attempts") == 0 and
         meta.get("theta_values") == list(THETAS), "invalid release intent")
    files = meta.get("files", {})
    expected = {"P10GD_surface_sweep.py", "P10FX_uniform_math.py",
                "P10GB_adapt_math.py", "M0.geo", "sphere_pore_B6_refined.geo",
                "P10FX_REAL_M0_M1_SIGNED_18_ZONE_729QP.json",
                "P10GA_M0_M1V_SIGNED18_343_729QP.json",
                "01_P10GD_2D_ONLY_NO_3D_NO_FEM.cmd", "README_P10GD_RU.md"}
    need(set(files) == expected, "source manifest file set mismatch")
    for filename, digest in files.items():
        need((HERE / filename).is_file() and sha(HERE / filename) == digest,
             "release file changed/missing: " + filename)
    need(sha(HERE / "M0.geo") == M0_GEO_SHA and
         sha(HERE / "sphere_pore_B6_refined.geo") == CAD_SHA,
         "bundled original geometry was changed")


def field_matrices():
    v = previous.load_matrix()
    w, _, old = latest.calibration()
    need(v == old and len(v) == 3 and all(len(row) == 6 for row in v),
         "M1V and M1W correction matrices disagree")
    return v, w


def make_geo(theta):
    v, w = field_matrices()
    matrix = [[(1 - theta) * a + theta * b for a, b in zip(vrow, wrow)]
              for vrow, wrow in zip(v, w)]
    base = previous.baseline_field(previous.M0_GEO.read_text(encoding="utf-8"))
    logc = previous.logcomp_expression(matrix)
    field = f"({base})*exp((log({previous.PREVIOUS_NOMINAL:.17g})+({logc}))/3)"
    geo = (
        f"// P10GD: SURFACE DIAGNOSTIC ONLY; theta={theta:.3f}; no 3D/FEM.\n"
        'Include "M0.geo";\nField[4] = MathEval;\n'
        f"Field[4].F = StrCat(\n  {previous.split_for_gmsh(logc)}\n);\n"
        "Field[5] = MathEval;\n"
        f"Field[5].F = StrCat(\n  {previous.split_for_gmsh(field)}\n);\n"
        "Background Field=5;\nMesh.Algorithm=5;\nMesh.Algorithm3D=10;\n"
        "Mesh.ElementOrder=2;\nMesh.HighOrderOptimize=1;\n"
        "Mesh.MeshSizeExtendFromBoundary=0;\nMesh.MeshSizeFromPoints=0;\n"
        "Mesh.MeshSizeFromCurvature=0;\nMesh.MeshSizeMin=0;\nMesh.MeshSizeMax=1e22;\n"
        "Mesh.MshFileVersion=2.2;\nMesh.Binary=0;\n")
    need(geo.count('Include "M0.geo"') == 1 and
         geo.count("Background Field=5;") == 1 and
         "F3" not in field and "F4" not in field,
         "malformed parametric GEO")
    return geo, matrix, field


def selftest():
    result = []
    v, w = field_matrices()
    for theta in THETAS:
        geo, matrix, field = make_geo(theta)
        need(all(math.isfinite(x) for row in matrix for x in row),
             "nonfinite field")
        result.append({"theta": theta, "geo_sha256": hashlib.sha256(geo.encode()).hexdigest(),
                       "field_expression_characters": len(field)})
    need(make_geo(0)[1] == v and make_geo(1)[1] == w,
         "endpoints do not equal previously measured fields")
    need(latest.math_selftest()["sample_points"] == 6018,
         "previous C1 diagnostic has changed")
    return result


def native_gate():
    need(sys.platform == "win32", "Windows required for native 2D; --selftest is portable")
    need(GMSH.is_file() and MESHES.is_dir() and RUNS.is_dir(),
         "expected Gmsh 4.15.2 and existing G: folders not found")
    pinned = {"M0.msh": M0_SHA, "M0.geo": M0_GEO_SHA,
              "M1V_CANDIDATE.msh": M1V_SHA,
              "M1V_CANDIDATE.geo": M1V_GEO_SHA,
              "M1W_CANDIDATE.msh": M1W_SHA,
              "M1W_CANDIDATE.geo": M1W_GEO_SHA,
              "sphere_pore_B6_refined.geo": CAD_SHA}
    for name, digest in pinned.items():
        need((MESHES / name).is_file() and sha(MESHES / name) == digest,
             "original user file missing/changed: " + name)
    version = subprocess.run([str(GMSH), "-version"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             check=False, timeout=15)
    need(version.returncode == 0 and b"4.15.2" in version.stdout,
         "different native Gmsh version")


def pore_stats(msh):
    nodes = {}; tris = []
    with msh.open("r", encoding="ascii") as f:
        for line in f:
            if line.strip() == "$Nodes":
                n = int(next(f)); need(n > 0, "empty 2D nodes")
                for _ in range(n):
                    row = next(f).split()
                    need(len(row) == 4, "2D node record malformed")
                    nodes[int(row[0])] = tuple(map(float, row[1:]))
            elif line.strip() == "$Elements":
                n = int(next(f)); need(n > 0, "empty 2D elements")
                for _ in range(n):
                    row = list(map(int, next(f).split()))
                    if row[1] == 9 and row[2] >= 1 and row[3] == 8:
                        ids = row[3 + row[2]:]
                        need(len(ids) == 6, "physical pore Tri6 malformed")
                        tris.append(ids)
    need(len(tris) >= 100 and nodes, "missing 2D pore Tri6")
    stats = {"N_polar": [], "S_polar": [], "N_taper": [], "S_taper": [],
             "N_off": [], "S_off": []}
    for ids in tris:
        p = [nodes[i] for i in ids[:3]]
        xyz = [sum(x[k] for x in p) / 3 for k in range(3)]
        r = math.sqrt(xyz[0] ** 2 + xyz[1] ** 2 + (xyz[2] - .03) ** 2)
        need(r > 0, "pore centroid radius zero")
        mu = (xyz[2] - .03) / r
        hemisphere = "N" if mu >= 0 else "S"
        ang = "polar" if abs(mu) >= .8 else "taper" if abs(mu) > .6 else "off"
        edge_mm = statistics.median([math.dist(p[0], p[1]),
                                      math.dist(p[1], p[2]),
                                      math.dist(p[2], p[0])]) * 1000
        stats[hemisphere + "_" + ang].append(edge_mm)
    summarized = {name: {"tri6": len(edges),
                         "corner_edge_median_mm": statistics.median(edges) if edges else None,
                         "corner_edge_min_mm": min(edges) if edges else None,
                         "corner_edge_max_mm": max(edges) if edges else None}
                  for name, edges in stats.items()}
    need(sum(x["tri6"] for x in summarized.values()) == len(tris),
         "signed surface partition incomplete")
    return {"pore_tri6": len(tris), "signed_surface_bins": summarized,
            "north_polar_tri6": summarized["N_polar"]["tri6"],
            "south_polar_tri6": summarized["S_polar"]["tri6"]}


def run_native(cmd, folder, log_name, limit_s=120):
    process = subprocess.run(cmd, cwd=folder, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=limit_s, check=False)
    output = process.stdout[:4 * 1024 * 1024].decode("utf-8", errors="replace")
    (folder / log_name).write_text(output, encoding="utf-8")
    need(process.returncode == 0 and "Error" not in output,
         "Gmsh native failed: " + log_name)
    return output


def zip_evidence(folder):
    path = folder / "P10GD_SURFACE_SWEEP_EVIDENCE.zip"
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as out:
        for f in sorted(folder.iterdir()):
            if f.is_file() and f != path and f.stat().st_size <= 12 * 1024 * 1024:
                out.write(f, f.name)
        out.write(PIN, PIN.name)
    print("SEND THIS FILE:", path, flush=True)


def sweep():
    read_manifest_and_check()
    tests = selftest()
    native_gate()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    folder = RUNS / ("P10GD_SURFACE_SWEEP_" + stamp)
    folder.mkdir()
    for name in ("M0.geo", "sphere_pore_B6_refined.geo"):
        shutil.copy2(HERE / name, folder / name)
    results = []; failed = None
    print("P10GD: 9 native -1/-2 diagnostic probes; NO -3; NO FEM", flush=True)
    try:
        for sample in tests:
            theta = sample["theta"]
            code = f"{int(round(theta * 1000)):04d}"
            name = "P10GD_SURFACE_T" + code
            geo_path = folder / (name + ".geo")
            geo_path.write_text(make_geo(theta)[0], encoding="utf-8")
            msh1 = folder / (name + "_1D.msh")
            msh2 = folder / (name + "_2D.msh")
            log1 = run_native([str(GMSH), str(geo_path), "-1", "-nopopup",
                               "-nt", "2", "-format", "msh2", "-save_all",
                               "-o", str(msh1)], folder, name + "_1D.log")
            need("Done meshing 1D" in log1 and msh1.is_file() and
                 msh1.stat().st_size > 1000, "native 1D probe incomplete")
            log2 = run_native([str(GMSH), str(geo_path), "-2", "-nopopup",
                               "-nt", "2", "-format", "msh2",
                               "-o", str(msh2)], folder, name + "_2D.log")
            need("Done meshing 2D" in log2 and msh2.is_file() and
                 msh2.stat().st_size > 1000, "native 2D probe incomplete")
            row = {"theta": theta, "GEO_sha256": sha(geo_path),
                   "native_1d_sha256": sha(msh1), "native_2d_sha256": sha(msh2),
                   "native_1d_exit_code": 0, "native_2d_exit_code": 0,
                   "native_3d_attempts": 0, "FEM_attempts": 0,
                   "surface": pore_stats(msh2)}
            results.append(row)
            print("P10GD_2D", json.dumps({"theta": theta,
                  "pore_tri6": row["surface"]["pore_tri6"],
                  "N_polar": row["surface"]["north_polar_tri6"],
                  "S_polar": row["surface"]["south_polar_tri6"]}), flush=True)
    except BaseException as exc:
        failed = repr(exc)
        (folder / "P10GD_STOP_TRACE.txt").write_text(traceback.format_exc(),
                                                        encoding="utf-8")
    finally:
        report = {"revision": REV, "status": "P10GD_SURFACE_ONLY_PASS_NO_3D_NO_FEM"
                  if failed is None else "P10GD_SURFACE_ONLY_STOP_NO_3D_NO_FEM",
                  "error": failed, "M0_sha256": M0_SHA, "M1V_sha256": M1V_SHA,
                  "M1W_sha256": M1W_SHA, "diagnostic_not_3d_prediction": True,
                  "source_pin_sha256": sha(PIN), "tested_fields": tests,
                  "native_3d_attempts": 0, "FEM_attempts": 0, "results": results}
        save(folder / "P10GD_SURFACE_SWEEP_METRICS.json", report)
        zip_evidence(folder)
    return 0 if failed is None else 2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--surface-only", action="store_true")
    args = p.parse_args()
    need(args.selftest != args.surface_only, "choose exactly one mode")
    read_manifest_and_check()
    if args.selftest:
        print("P10GD_SOURCE_ONLY_PASS", json.dumps(selftest()), flush=True)
        return 0
    return sweep()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.TimeoutExpired) as exc:
        print("P10GD_STOP:", str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
