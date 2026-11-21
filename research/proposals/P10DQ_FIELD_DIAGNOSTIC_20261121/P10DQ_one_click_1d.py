#!/usr/bin/env python3
"""P10DQ: bounded, one-shot Gmsh 1D field isolation; NEVER 2D/3D or FEM."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

from P10DO_windows_guards import child_private_bytes, command, free_windows_ram, require, sha256

REV = "P10DQ_R1_NATIVE_1D_FIELD_DIAGNOSTIC_NO_FEM"
HERE = Path(__file__).resolve().parent
RUNS = HERE / "P10DQ_RUNS"
LOCAL_MARKER = RUNS / "P10DQ_ONE_1D_ATTEMPT_USED.json"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
P10DO_SOURCE_SHA = "6c6f4f574e6a8c436d8319e059e5d1341c8ecbeda5ba38fbc2587c03abb15535"
P10DO_STOP_SHA = "547ce2c801b058658439ff157735dca1e28c4931b5da56f4b71e96a61723e220"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
GMSH_VERSION = "4.15.2"
CONFIRM = "RUN ONE P10DQ 1D DIAGNOSTIC"
PER_TEST_WALL_S = 25
PER_TEST_PRIVATE_BYTES = 4 * 1024 ** 3
PER_TEST_MSH_BYTES = 20 * 1024 ** 2
PER_TEST_LOG_BYTES = 2 * 1024 ** 2
EXACT_EXPRESSION = 'Field[6].F = "F2*exp(log(1-0.2*F5)/3)";'
VARIANT_NAMES = (
    "A_BASE_M1_FIELD2",
    "B_F2_MATHEVAL_PROXY",
    "C_F5_LINEAR_DIAGNOSTIC",
    "D_F5_POWER_EXACT",
    "E_F5_ORIGINAL_LOGEXP",
)


def source_gate() -> dict:
    pin = json.loads((HERE / "P10DQ_SOURCE_SHA256.json").read_text(encoding="utf-8"))
    require(pin.get("revision") == REV and pin.get("physical_FEM") is False and
            pin.get("three_dimensional_mesh") is False and
            pin.get("one_dimensional_attempt_limit") == 1 and
            pin.get("p10do_source_zip_sha256") == P10DO_SOURCE_SHA and
            pin.get("p10do_stop_evidence_sha256") == P10DO_STOP_SHA and
            pin.get("accepted_m1_sha256") == M1_SHA and
            len(pin.get("files", {})) == 7, "P10DQ inventory/header mismatch")
    for name, digest in pin["files"].items():
        require(name == Path(name).name and ".." not in name and
                (HERE / name).is_file() and sha256(HERE / name) == digest,
                "P10DQ pinned file changed: " + name)
    base = (HERE / "sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    src = (HERE / "P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    require('Field[2] = Threshold;' in base and
            'Mesh.ElementOrder=2;' in base and EXACT_EXPRESSION in src and
            'Include "sphere_pore_B6_refined.geo";' in src and
            'Background Field=6;' in src, "P10DQ M1/M2 original GEO mismatch")
    return pin


def smoothstep(v: float) -> float:
    u = min(1., max(0., v))
    return u * u * (3. - 2. * u)


def kappa(x: float, y: float, z: float) -> float:
    dz = z - .03
    rho2 = x * x + y * y + dz * dz
    d = math.sqrt(rho2 + 1e-24) - .001
    radial = 1. - smoothstep((d - .0001) / .0004)
    angular = smoothstep(((dz * dz / (rho2 + 1e-24)) - .36) / .28)
    return radial * angular


def formula_unit() -> dict:
    pts = {
        "north_wall": (0., 0., .031),
        "south_wall": (0., 0., .029),
        "equator_wall": (.001, 0., .03),
        "north_d03mm": (0., 0., .0313),
        "north_d06mm": (0., 0., .0316),
        "far_field": (.02, 0., .03),
    }
    vals = {name: kappa(*p) for name, p in pts.items()}
    for val in vals.values():
        require(math.isfinite(val) and 0. <= val <= 1.,
                "P10DQ kappa nonfinite/outside [0,1]")
        size_ratio = (1. - .2 * val) ** (1. / 3.)
        require(.9283177667 <= size_ratio <= 1., "P10DQ size bound failed")
    require(abs(vals["north_wall"] - 1.) < 1e-12 and
            abs(vals["south_wall"] - 1.) < 1e-12 and
            abs(vals["north_d03mm"] - .5) < 1e-10 and
            vals["equator_wall"] == 0. and vals["far_field"] == 0. and
            vals["north_d06mm"] == 0., "P10DQ pole/equator profile failed")
    return vals


def variant_sources() -> dict[str, str]:
    src = (HERE / "P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    require(src.count(EXACT_EXPRESSION) == 1 and
            src.count("// F3:") == 1, "P10DQ original formula or prefix changed")
    prefix = src.split("// F3:", 1)[0]
    base = prefix + "\n// Identical M1 background field, no adaptation.\nBackground Field=2;\n"
    proxy = prefix + '\nField[6] = MathEval;\nField[6].F = "F2";\nBackground Field=6;\n'
    linear = src.replace(EXACT_EXPRESSION, 'Field[6].F = "F2*(1-0.02*F5)";')
    power = src.replace(EXACT_EXPRESSION, 'Field[6].F = "F2*(1-0.2*F5)^(1/3)";')
    results = dict(zip(VARIANT_NAMES, (base, proxy, linear, power, src)))
    require(len(results) == 5 and results[VARIANT_NAMES[-1]] == src and
            all('Include "sphere_pore_B6_refined.geo";' in s for s in results.values()) and
            all("Background Field=" in s for s in results.values()),
            "P10DQ isolated variant construction failed")
    return results


def user_marker() -> Path:
    root = os.environ.get("LOCALAPPDATA", "")
    require(root and Path(root).is_dir(), "Windows LOCALAPPDATA unavailable")
    return Path(root) / "Stage3D07" / ("P10DQ_1D_" + M1_SHA + ".json")


def generated_sources(run_dir: Path) -> dict[str, Path]:
    variant_dir = run_dir / "GEO"
    variant_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "sphere_pore_B6_refined.geo",
                    variant_dir / "sphere_pore_B6_refined.geo")
    result = {}
    for name, src in variant_sources().items():
        path = variant_dir / (name + ".geo")
        path.write_text(src, encoding="utf-8")
        result[name] = path
    return result


def preflight(run_dir: Path) -> tuple[dict, dict[str, Path]]:
    require(os.name == "nt", "P10DQ native Gmsh1D runs permitted on Windows only")
    historical = str(Path(r"G:\ildar\Stage3D07")).casefold()
    here = str(HERE).casefold()
    require(here != historical and not here.startswith(historical + "\\"),
            "P10DQ must be extracted OUTSIDE historical Stage3D07")
    pin = source_gate()
    formula = formula_unit()
    require(not LOCAL_MARKER.exists() and not user_marker().exists(),
            "P10DQ 1D one-shot already consumed; NO REPEAT")
    gmsh = Path(os.environ.get("P10DQ_GMSH_EXE",
                             r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    require(gmsh.is_file() and sha256(gmsh) == GMSH_SHA,
            "P10DQ native Gmsh exact executable SHA mismatch")
    version = command([str(gmsh), "-version"], HERE, timeout=15)
    require(version.returncode == 0 and
            re.search(r"(?<![0-9])4\.15\.2(?![0-9])",
                      version.stdout + version.stderr) is not None,
            "P10DQ native Gmsh version/exit mismatch")
    ram = free_windows_ram()
    disk = shutil.disk_usage(HERE).free
    require(ram >= 8 * 1024 ** 3 and disk >= 1 * 1024 ** 3,
            "P10DQ requires >=8GiB available RAM and >=1GiB free disk")
    variants = generated_sources(run_dir)
    parsed = {}
    for name, geo in variants.items():
        proc = command([str(gmsh), str(geo), "-parse_and_exit"],
                       geo.parent, timeout=20)
        require(proc.returncode == 0 and
                not re.search(r"(?im)^\s*Error\s*:", proc.stdout + proc.stderr),
                "P10DQ native GEO parse STOP for " + name)
        parsed[name] = proc.returncode
    meta = {"source_pin_count": len(pin["files"]),
            "native_gmsh": str(gmsh), "native_gmsh_sha256": GMSH_SHA,
            "native_gmsh_version": GMSH_VERSION,
            "native_parse_exits": parsed, "coefficient_sample_values": formula,
            "free_RAM_before_bytes": ram, "free_disk_before_bytes": disk,
            "variant_geo_sha256": {n: sha256(p) for n, p in variants.items()}}
    return meta, variants


def consume_one_shot(run_dir: Path) -> None:
    marker = user_marker()
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {"protocol": REV, "utc": datetime.now(timezone.utc).isoformat(),
               "run_dir": str(run_dir), "m1_sha256": M1_SHA,
               "mode": "ONLY_1D_NO_2D_3D_NO_FEM"}
    # If either exclusive creation fails, the other marker remains. No retry.
    with marker.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with LOCAL_MARKER.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def native_1d(gmsh: str, geo: Path, run_dir: Path) -> dict:
    name = geo.stem
    mesh = run_dir / (name + ".msh")
    log = run_dir / (name + ".log")
    argv = [gmsh, str(geo), "-1", "-nt", "2", "-format", "msh2", "-o", str(mesh)]
    started = time.monotonic()
    peak = 0
    status = "STARTED"
    exit_code = None
    with log.open("w", encoding="utf-8") as out:
        child = subprocess.Popen(argv, cwd=str(geo.parent), stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                peak = max(peak, child_private_bytes(child))
                elapsed = time.monotonic() - started
                if elapsed > PER_TEST_WALL_S:
                    status = "TIMEOUT_25S"
                    break
                if peak > PER_TEST_PRIVATE_BYTES:
                    status = "PRIVATE_GT_4GIB"
                    break
                if log.stat().st_size > PER_TEST_LOG_BYTES:
                    status = "LOG_GT_2MIB"
                    break
                if mesh.is_file() and mesh.stat().st_size > PER_TEST_MSH_BYTES:
                    status = "MESH_GT_20MIB"
                    break
                time.sleep(.2)
            if status != "STARTED" and child.poll() is None:
                child.kill()
            child.wait(timeout=15)
            exit_code = child.returncode
            if status == "STARTED":
                status = "PASS" if exit_code == 0 and mesh.is_file() and mesh.stat().st_size > 0 else "NONZERO_OR_NO_MESH"
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=15)
    size = mesh.stat().st_size if mesh.exists() else 0
    tail = log.read_bytes()[-6000:].decode("utf-8", errors="replace")
    (run_dir / (name + "_TAIL.txt")).write_text(tail, encoding="utf-8")
    return {"name": name, "status": status, "native_exit": exit_code,
            "wall_s": time.monotonic() - started, "peak_private_polled": peak,
            "mesh_bytes": size, "mesh_sha256": sha256(mesh) if size else None,
            "log_bytes": log.stat().st_size, "argv": argv}


def evidence(run_dir: Path) -> Path:
    dst = run_dir / "P10DQ_EVIDENCE.zip"
    with zipfile.ZipFile(dst, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("P10DQ_RUN_MANIFEST.json", "P10DQ_RESULT.txt",
                     "P10DQ_STOP_TRACE.txt"):
            p = run_dir / name
            if p.is_file():
                z.write(p, name)
        for p in sorted((run_dir / "GEO").glob("*.geo")):
            z.write(p, "GEO/" + p.name)
        for p in sorted(run_dir.glob("*_TAIL.txt")):
            z.write(p, p.name)
    return dst


def do_run(preflight_only: bool) -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    run_dir = RUNS / ("P10DQ_1D_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run_dir.mkdir(exist_ok=False)
    meta = {"protocol": REV, "status": "P10DQ_STOP_NO_FEM", "physical_FEM_runs": 0,
            "three_dimensional_mesh_runs": 0, "two_dimensional_mesh_runs": 0,
            "one_dimensional_attempt_limit": 1,
            "p10do_stop_evidence_sha256": P10DO_STOP_SHA,
            "p10do_source_zip_sha256": P10DO_SOURCE_SHA,
            "m1_sha256": M1_SHA, "per_variant_wall_limit_s": PER_TEST_WALL_S,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "variants": []}
    code = 2
    try:
        pre, variants = preflight(run_dir)
        meta.update(pre)
        print("P10DQ SAFE PREFLIGHT PASS: original source SHA, 5 native GEO parses.")
        if preflight_only:
            meta["status"] = "P10DQ_READ_ONLY_PREFLIGHT_OK"
            code = 0
        else:
            print("Only Gmsh -1, FIVE variants, each <=25s; NO Gmsh -2/-3 and NO FEM.")
            print("Previous P10DO/other one-shot markers are never altered.")
            phrase = input("Type exactly RUN ONE P10DQ 1D DIAGNOSTIC: ").strip()
            require(phrase == CONFIRM, "manual consent missing; no one-shot consumed")
            consume_one_shot(run_dir)
            for name in VARIANT_NAMES:
                print("P10DQ testing 1D variant:", name, flush=True)
                record = native_1d(str(meta["native_gmsh"]), variants[name], run_dir)
                meta["variants"].append(record)
                print("P10DQ 1D", name, record["status"],
                      "wall_s", round(record["wall_s"], 2), flush=True)
                require(record["status"] == "PASS", "P10DQ 1D STOP at " +
                        name + ": " + record["status"])
            meta["status"] = "P10DQ_ALL_FIVE_1D_PASS_NO_FEM"
            code = 0
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        print("P10DQ STOP:", exc)
        (run_dir / "P10DQ_STOP_TRACE.txt").write_text(
            traceback.format_exc(), encoding="utf-8")
    finally:
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "P10DQ_RUN_MANIFEST.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (run_dir / "P10DQ_RESULT.txt").write_text(
            "RESULT=" + meta["status"] + "\nFEM_RUNS=0\nM2_3D_MESH_RUNS=0\n"
            "STOP_REASON=" + str(meta.get("stop_reason", "")) + "\n",
            encoding="utf-8")
        z = evidence(run_dir)
        print("P10DQ RESULT:", meta["status"], "EVIDENCE:", z)
        print("Send ONLY P10DQ_EVIDENCE.zip; do NOT rerun second button.")
    return code


def selftest() -> int:
    source_gate()
    points = formula_unit()
    variants = variant_sources()
    assert len(points) == 6 and len(variants) == 5
    assert variants[VARIANT_NAMES[-1]] == (HERE / "P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    assert '-1' in native_1d.__code__.co_consts and '-3' not in native_1d.__code__.co_consts
    print("P10DQ_SOURCE_FORMULA_AND_FIVE_VARIANTS_SELFTEST_OK",
          "native_Gmsh=NOT_RUN FEM=0")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()
    if args.selftest:
        require(not args.preflight_only, "only one mode")
        return selftest()
    return do_run(args.preflight_only)


if __name__ == "__main__":
    raise SystemExit(main())
