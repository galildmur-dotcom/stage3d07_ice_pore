#!/usr/bin/env python3
"""P10DW: source-pinned native GEO parse, then at most ONE Windows Gmsh -1.

No 2D/3D, Tet10 M2, forward, adjoint, FEM, cache, or old marker access.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

import P10DV_inline_source_unit as source_math
from P10DO_windows_guards import child_private_bytes, command, free_windows_ram, sha256

REV = "P10DW_R1_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM"
HERE = Path(__file__).resolve().parent
RUNS = HERE / "P10DW_RUNS"
PREFLIGHT_PROOF = RUNS / "P10DW_PREFLIGHT_PASS.json"
LOCAL_MARKER = RUNS / "P10DW_ONE_1D_USED.json"
CONFIRM = "RUN ONE P10DW INLINE F6 1D"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
M1_DEFAULT = (r"G:\Downloads\P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121"
              r"\P10DG_RUNS\P10DG_M1_20261121_120324_362583\P10DG_M1_CANDIDATE.msh")
P10DV_ZIP_SHA = "4c29c4a4d2fbe6ea537bc4103b1dc5f42112e68e85cc98a14dd7dce1cac2c571"
INLINE_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
GMSH_VERSION = "4.15.2"
WALL_S = 15
PRIVATE_MAX = 2 * 1024**3
MSH_MAX = 20 * 1024**2
LOG_MAX = 1 * 1024**2
PIN_FILES = 12


def stop(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError("P10DW_STOP: " + message)


def source_gate() -> dict:
    pin = json.loads((HERE / "P10DW_SOURCE_SHA256.json").read_text(encoding="utf-8"))
    stop(pin.get("revision") == REV and pin.get("physical_FEM") is False and
         pin.get("mesh_2d_3d") is False and
         pin.get("one_shot_native_1d_limit") == 1 and
         pin.get("accepted_original_m1_sha256") == M1_SHA and
         pin.get("p10dv_source_zip_sha256") == P10DV_ZIP_SHA and
         pin.get("inline_geo_sha256") == INLINE_SHA and
         pin.get("cad_geo_sha256") == CAD_SHA and
         pin.get("gmsh_binary_sha256") == GMSH_SHA and
         len(pin.get("files", {})) == PIN_FILES, "P10DW protocol/source inventory")
    for name, expected in pin["files"].items():
        stop(name == Path(name).name and ".." not in name and
             (HERE/name).is_file() and sha256(HERE/name) == expected,
             "pinned source changed: " + name)
    stop(sha256(HERE/"P10DV_M2_INLINE_FIELD20.geo") == INLINE_SHA and
         sha256(HERE/"sphere_pore_B6_refined.geo") == CAD_SHA,
         "original candidate/CAD SHA")
    source_math.source_gate()  # independently pins the six original P10DV contents
    return pin


def geometry_contract() -> tuple[str, str]:
    exact = (HERE/"P10DV_M2_INLINE_FIELD20.geo").read_text(encoding="utf-8")
    original = (HERE/"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    cad = (HERE/"sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    stop(exact == source_math.candidate_geo_text() and
         'Field[2] = Threshold;' in cad and 'Mesh.ElementOrder=2;' in cad and
         exact.count('Field[6] = MathEval;') == 1 and
         exact.count('Background Field=6;') == 1 and
         exact.count('Include "sphere_pore_B6_refined.geo";') == 1 and
         all(f'Field[{i}] = MathEval;' not in exact for i in (3, 4, 5)) and
         re.findall(r'\bF\d+\b', exact.split('Field[6].F = "', 1)[1]) == ['F2'],
         "exact flattened field must use only Threshold F2")
    stop(original.count("// F3:") == 1 and
         original.count('Include "sphere_pore_B6_refined.geo";') == 1,
         "baseline source provenance")
    baseline = original.split("// F3:", 1)[0] + "\nBackground Field=2;\n"
    stop('Field[6]' not in baseline and 'Background Field=2;' in baseline and
         'Include "sphere_pore_B6_refined.geo";' in baseline,
         "baseline must be original M1 Threshold")
    return baseline, exact


def global_marker() -> Path:
    appdata = os.environ.get("LOCALAPPDATA", "")
    stop(bool(appdata) and Path(appdata).is_dir(), "Windows LOCALAPPDATA unavailable")
    return Path(appdata)/"Stage3D07"/("P10DW_1D_"+M1_SHA+".json")


def marker_clear() -> None:
    stop(not LOCAL_MARKER.exists() and not global_marker().exists(),
         "P10DW one-shot already consumed; NEVER DELETE MARKERS OR RERUN")


def original_m1_path(prompt: bool) -> Path:
    if prompt:
        answer = input("Full ORIGINAL P10DG_M1_CANDIDATE.msh path (Enter=default): ").strip()
        chosen = Path(answer.strip('"') if answer else M1_DEFAULT)
    else:
        stop(PREFLIGHT_PROOF.is_file(), "run button 01 successfully first")
        proof = json.loads(PREFLIGHT_PROOF.read_text(encoding="utf-8"))
        time_pass = datetime.fromisoformat(proof["checked_utc"])
        stop(time_pass.tzinfo is not None and
             timedelta(0) <= datetime.now(timezone.utc)-time_pass <= timedelta(hours=24) and
             proof.get("protocol") == REV and
             proof.get("m1_sha256") == M1_SHA and
             proof.get("candidate_sha256") == INLINE_SHA and
             proof.get("gmsh_sha256") == GMSH_SHA,
             "preflight proof identity / 24h freshness")
        chosen = Path(proof["original_m1_path"])
    stop(chosen.is_file() and chosen.name.casefold() == "p10dg_m1_candidate.msh" and
         sha256(chosen) == M1_SHA,
         "must read ONLY the ORIGINAL accepted P10DG M1 SHA; not H0/U0")
    return chosen


def generated_sources(run: Path) -> dict[str, Path]:
    baseline, exact = geometry_contract()
    folder = run/"GEO"
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(HERE/"sphere_pore_B6_refined.geo",
                    folder/"sphere_pore_B6_refined.geo")
    baseline_path = folder/"A_ORIGINAL_M1_FIELD2.geo"
    baseline_path.write_text(baseline, encoding="utf-8")
    exact_path = folder/"B_EXACT_INLINE_F6.geo"
    exact_path.write_text(exact, encoding="utf-8")
    stop(sha256(exact_path) == INLINE_SHA, "generated inline candidate altered")
    return {"A_ORIGINAL_M1_FIELD2": baseline_path,
            "B_EXACT_INLINE_F6": exact_path}


def preflight(run: Path, meta: dict, *, prompt: bool) -> dict[str, Path]:
    stop(os.name == "nt", "Windows native Gmsh ONLY; Linux STOP")
    current = str(HERE).casefold()
    legacy = str(Path(r"G:\ildar\Stage3D07")).casefold()
    stop(current != legacy and not current.startswith(legacy+"\\"),
         "extract into NEW folder outside G:\\ildar\\Stage3D07")
    pin = source_gate()
    tested = source_math.math_selftest()
    marker_clear()
    m1 = original_m1_path(prompt)
    gmsh = Path(os.environ.get("P10DW_GMSH_EXE",
                               r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    stop(gmsh.is_file() and sha256(gmsh) == GMSH_SHA,
         "exact Gmsh4.15.2 executable hash required")
    version = command([str(gmsh), "-version"], HERE, timeout=15)
    stop(version.returncode == 0 and
         re.search(r"(?<!\d)4\.15\.2(?!\d)", version.stdout+version.stderr) is not None,
         "Gmsh exact native version")
    ram, disk = free_windows_ram(), shutil.disk_usage(HERE).free
    stop(ram >= 8*1024**3 and disk >= 1024**3,
         "need >=8GiB free RAM and >=1GiB free disk")
    sources = generated_sources(run)
    meta.update({"source_sha_pins": len(pin["files"]), "math_points": tested["points"],
                 "m1_sha256": M1_SHA, "m1_path": str(m1),
                 "gmsh_path": str(gmsh), "gmsh_sha256": GMSH_SHA,
                 "gmsh_version": GMSH_VERSION, "free_ram_bytes": ram,
                 "free_disk_bytes": disk,
                 "geo_sha256": {n: sha256(f) for n, f in sources.items()}})
    for name, geo in sources.items():
        meta["native_parse_attempts"] += 1
        proc = command([str(gmsh), str(geo), "-parse_and_exit"],
                       geo.parent, timeout=20)
        (run/(name+"_PARSE.log")).write_text((proc.stdout+proc.stderr)[:LOG_MAX],
                                              encoding="utf-8")
        stop(proc.returncode == 0 and
             not re.search(r"(?im)^\s*Error\s*:", proc.stdout+proc.stderr),
             "Gmsh GEO parse failed: "+name)
        meta["native_parse_passed"].append(name)
    return sources


def save_preflight_proof(run: Path, meta: dict) -> None:
    proof = {"protocol": REV, "checked_utc": datetime.now(timezone.utc).isoformat(),
             "run_id": run.name, "m1_sha256": M1_SHA,
             "original_m1_path": meta["m1_path"], "gmsh_sha256": GMSH_SHA,
             "candidate_sha256": INLINE_SHA,
             "native_parse_passed": meta["native_parse_passed"]}
    stop(len(proof["native_parse_passed"]) == 2, "both GEO parses must pass")
    PREFLIGHT_PROOF.write_text(json.dumps(proof, indent=2)+"\n", encoding="utf-8")


def consume_one_shot(run: Path) -> None:
    payload = {"protocol": REV, "run_id": run.name,
               "consumed_utc": datetime.now(timezone.utc).isoformat(),
               "accepted_m1_sha256": M1_SHA,
               "mode": "EXACT_ONE_NATIVE_GMSH_1D_INLINE_F6_ONLY"}
    marker_clear()
    user = global_marker()
    user.parent.mkdir(parents=True, exist_ok=True)
    # Both exclusive markers are consumed immediately before Gmsh -1 Popen.
    # Any partial failure consumes this one-shot. NEVER remove or retry.
    with user.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
    with LOCAL_MARKER.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)


def native_one_1d(gmsh: Path, geo: Path, run: Path) -> dict:
    mesh, log = run/"B_EXACT_INLINE_F6.msh", run/"B_EXACT_INLINE_F6.log"
    argv = [str(gmsh), str(geo), "-1", "-nt", "2", "-format", "msh2",
            "-o", str(mesh)]
    start = time.monotonic()
    peak, status, returncode = 0, "STARTED", None
    with log.open("x", encoding="utf-8") as stream:
        child = subprocess.Popen(argv, cwd=str(geo.parent), stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                peak = max(peak, child_private_bytes(child))
                if time.monotonic()-start > WALL_S:
                    status = "TIMEOUT_15S"
                    break
                if peak > PRIVATE_MAX:
                    status = "PRIVATE_GT_2GIB"
                    break
                if log.stat().st_size > LOG_MAX:
                    status = "LOG_GT_1MIB"
                    break
                if mesh.is_file() and mesh.stat().st_size > MSH_MAX:
                    status = "MSH_GT_20MIB"
                    break
                time.sleep(.2)
            if status != "STARTED" and child.poll() is None:
                child.kill()
            child.wait(timeout=15)
            returncode = child.returncode
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=15)
    log_text = log.read_bytes().decode("utf-8", errors="replace")
    counts = re.findall(r"\b(\d+) nodes (\d+) elements\b", log_text)
    last = tuple(map(int, counts[-1])) if counts else None
    if status == "STARTED":
        status = ("PASS_1D_ONLY" if returncode == 0 and mesh.is_file() and
                  0 < mesh.stat().st_size <= MSH_MAX and last and
                  last[0] > 0 and last[1] > 0 and
                  not re.search(r"(?im)^\s*Error\s*:", log_text) else
                  "INVALID_EXIT_OR_1D_LOG")
    (run/"B_EXACT_INLINE_F6_TAIL.txt").write_text(log_text[-6500:], encoding="utf-8")
    return {"status": status, "exit_code": returncode,
            "wall_s": time.monotonic()-start, "peak_private_polled": peak,
            "msh_bytes": mesh.stat().st_size if mesh.exists() else 0,
            "msh_sha256": sha256(mesh) if mesh.is_file() else None,
            "reported_nodes_elements_from_log": last,
            "log_bytes": log.stat().st_size, "argv": argv}


def make_evidence(run: Path) -> Path:
    archive = run/"P10DW_EVIDENCE.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("P10DW_RUN_MANIFEST.json", "P10DW_RESULT.txt",
                     "P10DW_STOP_TRACE.txt", "B_EXACT_INLINE_F6_TAIL.txt"):
            if (run/name).is_file():
                z.write(run/name, name)
        folder = run/"GEO"
        if folder.is_dir():
            for geo in sorted(folder.glob("*.geo")):
                z.write(geo, "GEO/"+geo.name)
        for log in sorted(run.glob("*.log")):
            if log.stat().st_size <= LOG_MAX + 1024:
                z.write(log, log.name)
    return archive


def do_run(preflight_only: bool) -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    run = RUNS/("P10DW_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta = {"protocol": REV, "status": "P10DW_STOP_NO_FEM",
            "mode": "SOURCE_GEO_PREFLIGHT" if preflight_only else "ONE_1D_INLINE_F6",
            "accepted_original_m1_sha256": M1_SHA,
            "target_local_volume_ratio": "1-0.20*kappa",
            "native_parse_attempts": 0, "native_parse_passed": [],
            "native_1d_attempts": 0, "native_2d_3d_attempts": 0,
            "physical_FEM_attempts": 0, "wall_limit_1d_s": WALL_S,
            "private_limit_bytes": PRIVATE_MAX, "msh_limit_bytes": MSH_MAX,
            "log_limit_bytes": LOG_MAX,
            "started_utc": datetime.now(timezone.utc).isoformat()}
    code = 2
    try:
        sources = preflight(run, meta, prompt=preflight_only)
        print("P10DW SOURCE/GEOMETRY PREFLIGHT PASS: 2 native GEO parses; no mesh.", flush=True)
        if preflight_only:
            save_preflight_proof(run, meta)
            meta["status"] = "P10DW_READ_ONLY_PREFLIGHT_PASS"
            code = 0
        else:
            print("ONE new Gmsh -1 inline F6, <=15 s; NO -2/-3/FEM.", flush=True)
            answer = input("Type exactly "+CONFIRM+": ").strip()
            stop(answer == CONFIRM, "manual confirmation absent; marker NOT consumed")
            # One-shot is consumed IMMEDIATELY BEFORE the sole native Gmsh -1.
            consume_one_shot(run)
            meta["native_1d_attempts"] = 1
            result = native_one_1d(Path(meta["gmsh_path"]),
                                   sources["B_EXACT_INLINE_F6"], run)
            meta["native_1d_result"] = result
            meta["status"] = ("P10DW_ONE_1D_PASS_NO_FEM" if
                              result["status"] == "PASS_1D_ONLY" else
                              "P10DW_ONE_1D_STOP_NO_FEM")
            code = 0 if result["status"] == "PASS_1D_ONLY" else 2
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        (run/"P10DW_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print("P10DW STOP:", exc, flush=True)
    finally:
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run/"P10DW_RUN_MANIFEST.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (run/"P10DW_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nNATIVE_1D_ATTEMPTS="+
            str(meta["native_1d_attempts"])+"\nM2_3D_MESH=0\nFEM=0\n"+
            "STOP_REASON="+str(meta.get("stop_reason", ""))+"\n", encoding="utf-8")
        archive = make_evidence(run)
        print("P10DW RESULT:", meta["status"], "EVIDENCE:", archive, flush=True)
        print("Send ONLY P10DW_EVIDENCE.zip. NEVER rerun button 02.", flush=True)
    return code


def selftest() -> int:
    pin = source_gate()
    baseline, exact = geometry_contract()
    tested = source_math.math_selftest()
    stop(len(pin["files"]) == PIN_FILES and
         baseline.endswith("Background Field=2;\n") and
         exact == (HERE/"P10DV_M2_INLINE_FIELD20.geo").read_text(encoding="utf-8") and
         tested["points"] == 17075 and
         "-1" in native_one_1d.__code__.co_consts and
         "-3" not in native_one_1d.__code__.co_consts,
         "P10DW math/source/one-1D boundaries")
    print("P10DW_SOURCE_AND_MATH_SELFTEST_OK pins=12 points=17075 native_Gmsh=0 FEM=0")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--selftest", action="store_true")
    group.add_argument("--preflight-only", action="store_true")
    group.add_argument("--one-1d", action="store_true")
    args = parser.parse_args()
    return selftest() if args.selftest else do_run(args.preflight_only)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("P10DW STOP:", exc, file=sys.stderr)
        raise SystemExit(2)
