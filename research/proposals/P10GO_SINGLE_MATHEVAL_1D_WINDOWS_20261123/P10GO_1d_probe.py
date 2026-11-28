#!/usr/bin/env python3
"""P10GO: one self-contained MathEval field, bounded native -1 ONLY.

All P10GL/P10GM/P10GN native permissions are consumed; never retry them.
This diagnoses full inlining of original C1 M0 F3 + exact P10GK south window.
No result is an M1 approval, 3D attempt or FEM permission.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile

from P10FN_common import capped_process

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
RUNS = PROJECT / "LOCAL_RUNS"
GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
SOURCE = HERE / "P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip"
SOURCE_PIN = "4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05"
GMSH_PIN = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
M0_PIN = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
FROZEN_PIN = "2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea"
SOURCE_SHA = HERE / "P10GO_SOURCE_SHA256.json"
PREFLIGHT = HERE / "P10GO_PREFLIGHT_PROOF.json"
TOOL_RESULT = HERE / "P10GO_02_RESULT.txt"
REV = "P10GO_R1_SINGLE_C1_MATHEVAL_SOURCE_AND_BOUNDED_1D_NO_3D_FEM"
FACTOR = "0.9378887276834518"
WALL = 30
MAX_LOG = 2 * 1024**2
MAX_MSH = 32 * 1024**2

TR = "min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0015)/0.0005))"
TS = "min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.2))"
F6 = "F3*(1-0.06*(1-F4*F4*(3-2*F4))*(1-F5*F5*(3-2*F5)))"
SOURCE_GEOS = (
    "M0_ROTATED.geo", "sphere_pore_B6_refined_rotated.geo",
    "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo",
)
CASES = ("A_ORIGINAL_F3", "B_SELF_CONTAINED_C1_SOUTH")


def check(ok: bool, reason: str):
    if not ok:
        raise RuntimeError("P10GO_STOP: " + reason)


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj: object, *, exclusive=False):
    with path.open("x" if exclusive else "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def source_gate() -> dict[str, bytes]:
    check(sha(SOURCE) == SOURCE_PIN, "P10GK source archive changed")
    pins = json.loads(SOURCE_SHA.read_text(encoding="utf-8"))
    check(pins["revision"] == REV, "P10GO source manifest version")
    for name, digest in pins["files"].items():
        check(name != SOURCE_SHA.name and (HERE / name).is_file()
              and sha(HERE / name) == digest, "P10GO tool tamper: " + name)
    with zipfile.ZipFile(SOURCE, "r") as z:
        check(z.testzip() is None, "source ZIP CRC failed")
        names = z.namelist()
        check(len(names) == len(set(names)) == 12
              and all("/" not in n and "\\" not in n for n in names),
              "unsafe or changed source ZIP members")
        manifest = json.loads(z.read("P10GK_SOURCE_SHA256.json"))
        check(manifest["revision"] == "P10GK_R1_C1_SOUTH_FOCUS_SOURCE_ONLY"
              and manifest["native_mesh_3d_authorized"] is False
              and manifest["FEM_authorized"] is False
              and set(names) == set(manifest["files"]) | {"P10GK_SOURCE_SHA256.json"},
              "P10GK manifest or permissions changed")
        for name, digest in manifest["files"].items():
            check(sha_bytes(z.read(name)) == digest, "source member hash: " + name)
        policy = json.loads(z.read("P10GK_SOURCE_POLICY.json"))
        check(policy["parent_M0_msh_sha256"] == M0_PIN
              and policy["new_local_south_alpha"] == .06
              and str(policy["global_mesh_size_factor"]) == FACTOR
              and policy["south_physical_polar_0_500um_QV_hard_max"] == .98
              and policy["signed18_individual_0p80_0p85"] == "diagnostic_only",
              "frozen scientific P10GK policy changed")
        src = z.read("P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo").decode("utf-8")
        check('Field[4].F = "' + TR + '";' in src
              and 'Field[5].F = "' + TS + '";' in src
              and 'Field[6].F = "' + F6 + '";' in src
              and re.search(r"Background\s+Field\s*=\s*6\s*;", src) is not None,
              "linked source fields changed")
        return {name: z.read(name) for name in SOURCE_GEOS}


def baseline_expression(m0_geo: bytes) -> str:
    """Byte-pinned StrCat fragments of *original* M0 F3, unchanged."""
    s = m0_geo.decode("utf-8")
    match = re.search(r"Field\[3\]\.F\s*=\s*StrCat\((.*?)\);", s, re.S)
    check(match is not None, "original M0 F3 StrCat absent")
    fragments = re.findall(r'"([^"\\]*)"', match.group(1))
    check(len(fragments) == 2, "unexpected M0 F3 fragment structure")
    result = "".join(fragments)
    check(result.startswith("(0.00046165100702485221+")
          and result.endswith("))))))"), "original M0 F3 expression changed")
    return result


def inline_field(m0_geo: bytes) -> str:
    # Exact P10GK C1 multiplier, but all F3/F4/F5 are textually expanded.
    radial = f"(1-({TR})*({TR})*(3-2*({TR})))"
    angular = f"(1-({TS})*({TS})*(3-2*({TS})))"
    result = f"({baseline_expression(m0_geo)})*(1-0.06*{radial}*{angular})"
    check(not re.search(r"\bF[0-9]+\b", result),
          "forbidden reference remains in single MathEval")
    return result


def gmsh_strcat(expr: str) -> str:
    """Limit quoted GEO fragments; Gmsh StrCat reconstructs original expr."""
    check('"' not in expr and "\\" not in expr, "unsafe expression string")
    chunks = [expr[i:i+420] for i in range(0, len(expr), 420)]
    check(2 <= len(chunks) <= 10, "unexpected final expression length")
    return "StrCat(\n  " + ",\n  ".join('"'+chunk+'"' for chunk in chunks) + "\n)"


def driver(case: str) -> str:
    check(case in CASES, "unexpected case")
    if case == CASES[0]:
        result = 'Include "M0_ROTATED.geo";\nBackground Field = 3;\n'
    else:
        m0 = source_gate()["M0_ROTATED.geo"]
        result = ('Include "M0_ROTATED.geo";\nField[7] = MathEval;\n'
                  'Field[7].F = ' + gmsh_strcat(inline_field(m0)) + ';\n'
                  'Background Field = 7;\n')
    return ('// P10GO native -1 diagnostic ONLY, never 2D/3D/FEM.\n'
            + result + 'Mesh.MeshSizeFactor = ' + FACTOR + ';\n'
            'Mesh.Algorithm3D = 10;\nMesh.ElementOrder = 2;\n'
            'Mesh.HighOrderOptimize = 1;\nMesh.MshFileVersion = 2.2;\n'
            'Mesh.Binary = 0;\n')


def math_gate() -> dict:
    # Full original M0 StrCat expression vs trusted analytic C1 baseline,
    # and full B/P10GK factor vs explicit coordinate functions, in 10k points.
    src = source_gate()
    base = baseline_expression(src["M0_ROTATED.geo"])
    final = inline_field(src["M0_ROTATED.geo"])
    safe = {"__builtins__": {}, "sqrt": math.sqrt, "min": min, "max": max}
    base_code = compile(base, "M0_F3", "eval")
    final_code = compile(final, "P10GO_F7", "eval")
    tr_code = compile(TR, "P10GK_TR", "eval")
    ts_code = compile(TS, "P10GK_TS", "eval")
    max_err = 0.
    max_baseline = 0.
    lo, hi = 2., 0.
    minimum_h = 1.e22
    for di in range(101):
        d = .020 * di / 100
        for mi in range(101):
            mu = -1 + mi / 50
            r = .001 + d
            x = r * math.sqrt(max(0., 1-mu*mu))
            env = {"x": x, "y": 0., "z": .03+r*mu}
            f3 = eval(base_code, safe, env)
            # Same original C1 smoothed radial baseline, independent formula.
            def softplus(t, eps=.00005):
                q = min(1., max(0., (t+eps)/(2*eps)))
                return max(0., t-eps) + eps*q*q
            expected_f3 = (.00046165100702485221 + .43244858021734583*
                           (softplus(d-.0015)-softplus(d-.018)))
            max_baseline = max(max_baseline,abs(f3-expected_f3))
            f4 = eval(tr_code, safe, env)
            f5 = eval(ts_code, safe, env)
            expected = f3 * (1-.06*(1-f4*f4*(3-2*f4))
                             *(1-f5*f5*(3-2*f5)))
            actual = eval(final_code, safe, env)
            max_err = max(max_err,abs(expected-actual))
            check(math.isfinite(actual) and actual>0, "nonpositive full field")
            minimum_h=min(minimum_h,actual*float(FACTOR))
            lo,hi=min(lo,actual/f3),max(hi,actual/f3)
    check(max_err < 5e-13 and abs(lo-.94) < 5e-13
          and abs(hi-1.) < 5e-13 and max_baseline<5e-13,
          "exact M0 StrCat / P10GK single expression mismatch")
    def multiplier(d,mu):
        r=.001+d
        env={"x":r*math.sqrt(max(0.,1-mu*mu)),"y":0.,"z":.03+r*mu}
        return eval(final_code,safe,env)/eval(base_code,safe,env)
    for d0,mu0,delta,tol in (
        (.0005,-1.,1e-8,.03),(.001,-1.,1e-8,.03),
        (.00025,-.8,1e-6,.001),(.00025,-.6,1e-6,.001)):
        fun=(lambda u:multiplier(u,mu0)) if mu0==-1. else (lambda u:multiplier(d0,u))
        anchor=d0 if mu0==-1. else mu0
        left=(fun(anchor)-fun(anchor-delta))/delta
        right=(fun(anchor+delta)-fun(anchor))/delta
        check(abs(left-right)<tol,"C1 fade seam derivative mismatch")
    return {"points":10201,"max_absolute_h_error_m":max_err,
            "max_original_F3_error_m":max_baseline,
            "local_factor_min":lo,"local_factor_max":hi,
            "minimum_final_h_m":minimum_h,
            "C1_seam_tests":4,
            "baseline_expression_length":len(base),
            "single_expression_length":len(final),
            "no_field_references":True}


def installed_gate() -> dict:
    check(sys.platform == "win32", "native Gmsh diagnostics must run on Windows")
    check(PROJECT.is_dir() and RUNS.is_dir(), "G: project or LOCAL_RUNS absent")
    check((PROJECT / "meshes/M0.msh").is_file()
          and sha(PROJECT / "meshes/M0.msh") == M0_PIN,
          "parent M0.msh missing or modified")
    check(GMSH.is_file() and sha(GMSH) == GMSH_PIN,
          "pinned Gmsh4.15.2 EXE absent/changed")
    p = subprocess.run([str(GMSH), "-version"], cwd=HERE,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=15, check=False)
    version = p.stdout.decode("utf-8", errors="replace").strip()
    check(p.returncode == 0 and "4.15.2" in version,
          "Gmsh -version mismatch")
    return {"gmsh_version": version, "Gmsh_sha256": GMSH_PIN,
            "M0_msh_sha256": M0_PIN}


def local_marker() -> Path:
    return RUNS / "P10GO_1D_LOCKS" / ("P10GK_" + SOURCE_PIN[:20] + ".json")


def profile_marker() -> Path:
    app = os.environ.get("LOCALAPPDATA", "")
    check(app and Path(app).is_dir(), "Windows LOCALAPPDATA missing")
    return Path(app) / "Stage3D07/P10GO_1D_PROBE" / ("P10GK_" + SOURCE_PIN[:20] + ".json")


def preflight() -> int:
    source_gate()
    math = math_gate()
    installed = installed_gate()
    check(not PREFLIGHT.exists(), "preflight proof already exists; do not overwrite")
    check(not local_marker().exists() and not profile_marker().exists(),
          "P10GO 1D diagnostic already consumed; do not repeat")
    proof = {"revision": REV, "created_utc": datetime.now(timezone.utc).isoformat(),
             "P10GK_source_sha256": SOURCE_PIN,
             "P10GO_source_manifest_sha256": sha(SOURCE_SHA),
             "math": math, "installed": installed, "native_1d_attempts": 0,
             "native_2d_attempts": 0, "native_3d_attempts": 0,
             "FEM_attempts": 0}
    write_json(PREFLIGHT, proof, exclusive=True)
    print("P10GO_PREFLIGHT_PASS_NO_MESH. Next: 02 once only.", flush=True)
    return 0


def check_preflight():
    check(PREFLIGHT.is_file(), "run 01 preflight first")
    p = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    check(p["revision"] == REV and p["P10GK_source_sha256"] == SOURCE_PIN
          and p["P10GO_source_manifest_sha256"] == sha(SOURCE_SHA)
          and p["native_1d_attempts"] == 0 and p["native_3d_attempts"] == 0
          and p["FEM_attempts"] == 0,
          "preflight proof tampered")
    created = datetime.fromisoformat(p["created_utc"])
    age = (datetime.now(timezone.utc)-created).total_seconds()
    check(0 <= age <= 24*3600, "preflight older than 24h")


def make_case_folder(root: Path, case: str, source: dict[str, bytes]) -> Path:
    folder = root / case
    folder.mkdir(exist_ok=False)
    for name, data in source.items():
        (folder / name).write_bytes(data)
    (folder / "P10GO_1D.geo").write_text(driver(case), encoding="ascii")
    return folder


def read_new_log(path: Path, position: int, prefix: str) -> int:
    if not path.is_file():
        return position
    with path.open("rb") as f:
        f.seek(position)
        raw = f.read(64*1024)
        position = f.tell()
    for line in raw.decode("utf-8", errors="replace").splitlines():
        print(f"[{prefix} Gmsh] {line[:260]}", flush=True)
    return position


def native_one(case: str, folder: Path) -> dict:
    log = folder / "P10GO_GMSH_1D.log"
    mesh = folder / "P10GO_1D.msh"
    cmd = [str(GMSH), str(folder / "P10GO_1D.geo"), "-1", "-nopopup",
           "-nt", "2", "-format", "msh2", "-o", str(mesh)]
    check(cmd.count("-1") == 1 and not any(x in cmd for x in ("-2", "-3")),
          "forbidden native meshing dimension")
    print(f"[{case}] START native -1; hard wall {WALL}s; private <=8GiB; -nt 2", flush=True)
    started = time.monotonic()
    position = 0
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(capped_process, cmd, cwd=folder, log=log,
                             wall_s=WALL, memory_gib=8,
                             output_dir=folder, output_gib=2)
        while not future.done():
            position = read_new_log(log, position, case)
            print(f"[{case}] HEARTBEAT elapsed={time.monotonic()-started:.1f}s",
                  flush=True)
            time.sleep(2)
        position = read_new_log(log, position, case)
        native = future.result()
    content = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    completed = (native["native_exit_code"] == 0
                 and not native["stop_reason"]
                 and "Done meshing 1D" in content
                 and re.search(r"\bError\s*:", content) is None
                 and mesh.is_file() and 0 < mesh.stat().st_size <= MAX_MSH)
    result = {"case": case, "native": native, "completed_1d": completed,
              "log_sha256": sha(log) if log.is_file() else None,
              "log_size": log.stat().st_size if log.is_file() else None,
              "mesh_size": mesh.stat().st_size if mesh.is_file() else None,
              "mesh_sha256": sha(mesh) if completed else None,
              "geo_sha256": sha(folder / "P10GO_1D.geo")}
    check(not log.is_file() or log.stat().st_size <= MAX_LOG,
          "native log unexpectedly large")
    print(f"[{case}] RESULT={'PASS_1D' if completed else 'STOP_1D'} "
          f"exit={native['native_exit_code']} stop={native['stop_reason']}", flush=True)
    return result


def evidence(root: Path):
    out = root / "P10GO_1D_PROBE_EVIDENCE.zip"
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        # Logs/driver/manifests only. No mesh, source ZIP, EXE, FEM, or user data.
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p == out:
                continue
            if p.suffix.lower() in (".log", ".geo", ".json", ".txt"):
                z.write(p, arcname=str(p.relative_to(root)).replace("\\", "/"))
    check(zipfile.ZipFile(out).testzip() is None, "evidence ZIP CRC")
    return out


def run():
    source = source_gate()
    math = math_gate()
    installed = installed_gate()
    check_preflight()
    check(not local_marker().exists() and not profile_marker().exists(),
          "P10GO 1D attempt already consumed; never retry")
    root = RUNS / ("P10GO_SINGLE_MATHEVAL_1D_" + datetime.now(timezone.utc)
                   .strftime("%Y%m%d_%H%M%S_%f"))
    root.mkdir(exist_ok=False)
    report = {"revision": REV, "status": "STOP_INCOMPLETE_1D_DIAGNOSTIC",
              "P10GL_native_previous_3d": "CONSUMED_STOP_1D_15MIN",
              "P10GM_native_1d_previous": "CONSUMED_A_PASS_B_TIMEOUT_C_TIMEOUT",
              "P10GN_native_1d_previous": "CONSUMED_D_TIMEOUT_E_TIMEOUT_F_NOT_RUN",
              "M0_sha256": M0_PIN, "frozen_D027_sha256": FROZEN_PIN,
              "P10GK_source_sha256": SOURCE_PIN, "math": math,
              "installed": installed, "native_2d_attempts": 0,
              "native_3d_attempts": 0, "FEM_attempts": 0, "cases": [],
              "single_field_no_F3_F4_F5_references": True}
    marker = {"revision": REV, "time_utc": datetime.now(timezone.utc).isoformat(),
              "P10GK_source_sha256": SOURCE_PIN,
              "max_distinct_native_1d_cases": 2,
              "native_2d_attempts": 0, "native_3d_attempts": 0,
              "FEM_attempts": 0}
    # Consume independent 1D permission before the first native meshing call.
    local_marker().parent.mkdir(parents=True, exist_ok=True)
    profile_marker().parent.mkdir(parents=True, exist_ok=True)
    write_json(local_marker(), marker, exclusive=True)
    write_json(profile_marker(), marker, exclusive=True)
    result = 2
    try:
        for case in CASES:
            # B is deliberately attempted even if A timed out; both are bounded.
            folder = make_case_folder(root, case, source)
            item = native_one(case, folder)
            report["cases"].append(item)
            write_json(root / "P10GO_PROGRESS.json", report)
        else:
            report["status"] = ("DIAG_BOTH_1D_COMPLETED_NO_3D"
                                if all(c["completed_1d"] for c in report["cases"])
                                else "DIAG_INLINE_1D_TIMEOUT_OR_STOP_NO_3D")
            result = 0  # A completed diagnostic may have a bounded TIMEOUT.
    except BaseException as error:
        report["error"] = repr(error)
        (root / "P10GO_STOP_TRACE.txt").write_text(traceback.format_exc(),
                                                   encoding="utf-8")
    finally:
        write_json(root / "P10GO_MANIFEST.json", report)
        out = evidence(root)
        text = (f"P10GO_RESULT={report['status']}\n"
                f"P10GO_EVIDENCE={out}\n"
                f"NATIVE_1D_CASES={len(report['cases'])}/2_MAX\n"
                "NATIVE_2D=0 NATIVE_3D=0 FEM=0\n"
                "DO_NOT_REPEAT_02=YES\n")
        TOOL_RESULT.write_text(text, encoding="utf-8")
        print(text, flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--selftest", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run-1d", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        source_gate()
        stats = math_gate()
        for case in CASES:
            check("-3" not in driver(case) and "Mesh 3;" not in driver(case),
                  "forbidden 3D in diagnostic driver")
        print("P10GO_SINGLE_FULL_F3_INLINE_10201_POINT_QA_PASS_NO_NATIVE", stats,
              flush=True)
        return 0
    if args.preflight:
        return preflight()
    return run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"P10GO_STOP: {type(error).__name__}: {error}", file=sys.stderr,
              flush=True)
        sys.exit(2)
