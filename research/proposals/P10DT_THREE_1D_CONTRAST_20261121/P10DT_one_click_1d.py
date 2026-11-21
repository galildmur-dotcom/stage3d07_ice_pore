#!/usr/bin/env python3
"""P10DT: three bounded independent Windows Gmsh -1 contrasts; NO 2D/3D/FEM."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
import zipfile

import P10DR_one_click_1d as original_native  # source-pinned Gmsh -1 watchdog only
from P10DO_windows_guards import command, free_windows_ram, sha256

REV = "P10DT_R1_THREE_INDEPENDENT_1D_CONTRASTS_NO_FEM"
HERE = Path(__file__).resolve().parent
RUNS = HERE / "P10DT_RUNS"
LOCAL_MARKER = RUNS / "P10DT_ONE_THREE_VARIANT_SEQUENCE_USED.json"
CONFIRM = "RUN ONE P10DT 1D DIAGNOSTIC"
P10DR_SOURCE_SHA = "4ed2a21c64480996b88d7c1f465fc884b3a175f659e424d2039c413ca420a011"
P10DR_EVIDENCE_SHA = "72e06f67338ab5f2b5f25080ac89e41c9026011b3aaedc0e2f155f0fb7eb1b7f"
M1_SHA = original_native.M1_SHA
GMSH_SHA = original_native.GMSH_SHA
GMSH_VERSION = original_native.GMSH_VERSION
WALL_S = original_native.WALL_S  # 15 seconds per variant
PRIVATE_MAX = original_native.PRIVATE_MAX  # 2 GiB
MSH_MAX = original_native.MSH_MAX  # 20 MiB
LOG_MAX = original_native.LOG_MAX  # 1 MiB
NAMES = (
    "A_DIRECT_CONSTANT_F6",
    "B_NESTED_CONSTANT_F3",
    "C_DIRECT_SPATIAL_CLAMP_F6",
)


def stop(condition: bool, why: str) -> None:
    if not condition:
        raise RuntimeError("P10DT_STOP: " + why)


def source_gate() -> dict:
    pin = json.loads((HERE / "P10DT_SOURCE_SHA256.json").read_text(encoding="utf-8"))
    stop(pin.get("revision") == REV and pin.get("physical_FEM") is False and
         pin.get("mesh_2d_3d") is False and pin.get("diagnostic_sequence_limit") == 1 and
         pin.get("max_native_1d_variants") == 3 and
         pin.get("accepted_m1_sha256") == M1_SHA and
         pin.get("p10dr_source_zip_sha256") == P10DR_SOURCE_SHA and
         pin.get("p10dr_evidence_zip_sha256") == P10DR_EVIDENCE_SHA and
         len(pin.get("files", {})) == 8, "source pin and protocol")
    for name, expected in pin["files"].items():
        stop(name == Path(name).name and ".." not in name and
             (HERE/name).is_file() and sha256(HERE/name) == expected,
             "source SHA mismatch " + name)
    base = (HERE/"sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    original = (HERE/"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    stop('Field[2] = Threshold;' in base and 'Mesh.ElementOrder=2;' in base and
         original.count(original_native.EXACT_F3) == 1 and
         original.count(original_native.EXACT_F4) == 1 and
         original.count(original_native.EXACT_F5) == 1 and
         original.count(original_native.EXACT_F6) == 1,
         "original CAD/F3/F4/F5/F6 byte contract")
    return pin


def contrast_geo() -> dict[str, str]:
    original = (HERE/"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    stop(original.count("// F3:") == 1, "original F3 block count")
    base = original.split("// F3:", 1)[0]
    # Reuse the literal exact original F3 formula, but inline it in Field6.
    expr = original_native.EXACT_F3.split('"', 2)[1]
    stop(expr.startswith("min(1,max(0,") and expr.endswith("))") and
         'Field[3].F = "' + expr + '";' in original, "original clamp extraction")
    fields = {
        NAMES[0]: '\nField[6] = MathEval;\nField[6].F = "F2*(1-0.02*0.5)";\n',
        NAMES[1]: ('\nField[3] = MathEval;\nField[3].F = "0.5";\n'
                   'Field[6] = MathEval;\nField[6].F = "F2*(1-0.02*F3)";\n'),
        NAMES[2]: ('\nField[6] = MathEval;\nField[6].F = "F2*(1-0.02*(' +
                   expr + '))";\n'),
    }
    geo = {name: base + suffix + "Background Field=6;\n" for name, suffix in fields.items()}
    stop(list(geo) == list(NAMES) and all(
        'Include "sphere_pore_B6_refined.geo";' in v and
        v.count("Background Field=6;") == 1 and
        'Field[4] = ' not in v and 'Field[5] = ' not in v and
        original_native.EXACT_F6 not in v for v in geo.values()),
         "contrast GEO structure")
    stop('Field[3] = MathEval;' not in geo[NAMES[0]] and
         'Field[3] = MathEval;' in geo[NAMES[1]] and
         'Field[3] = MathEval;' not in geo[NAMES[2]], "only B may nest Field3")
    return geo


def formula_unit() -> dict:
    vals = original_native.profile_unit()
    stop(len(vals) == 6 and all(0. <= p["F3"] <= 1. for p in vals.values()),
         "original F3 samples")
    for p in vals.values():
        for q in (0.5, p["F3"]):
            stop(.98 <= 1.-.02*q <= 1., "diagnostic size range")
    # The exact F3 formula is clamped by min/max globally, not just at these points.
    return {"six_original_F3_sample_points": vals,
            "diagnostic_h6_div_h2_envelope": [0.98, 1.],
            "diagnostic_target_volume_ratio_envelope": [0.98**3, 1.]}


def profile_marker() -> Path:
    appdata = os.environ.get("LOCALAPPDATA", "")
    stop(bool(appdata) and Path(appdata).is_dir(), "Windows LOCALAPPDATA unavailable")
    return Path(appdata)/"Stage3D07"/("P10DT_1D_" + M1_SHA + ".json")


def generated_geo(run: Path) -> dict[str, Path]:
    folder = run/"GEO"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE/"sphere_pore_B6_refined.geo", folder/"sphere_pore_B6_refined.geo")
    files = {}
    for name, src in contrast_geo().items():
        dst = folder/(name + ".geo")
        dst.write_text(src, encoding="utf-8")
        files[name] = dst
    return files


def preflight(run: Path) -> tuple[dict, dict[str, Path]]:
    stop(os.name == "nt", "native Gmsh -1 permitted on Windows ONLY")
    historical = str(Path(r"G:\ildar\Stage3D07")).casefold()
    current = str(HERE).casefold()
    stop(current != historical and not current.startswith(historical + "\\"),
         "extract outside original G:/ildar/Stage3D07")
    pin = source_gate()
    values = formula_unit()
    stop(not LOCAL_MARKER.exists() and not profile_marker().exists(),
         "new P10DT one-shot already consumed; NEVER REPEAT")
    gmsh = Path(os.environ.get("P10DT_GMSH_EXE", r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    stop(gmsh.is_file() and sha256(gmsh) == GMSH_SHA, "exact Gmsh executable SHA")
    version = command([str(gmsh), "-version"], HERE, timeout=15)
    stop(version.returncode == 0 and re.search(r"(?<![0-9])4\.15\.2(?![0-9])",
                                               version.stdout+version.stderr) is not None,
         "native Gmsh version")
    ram, disk = free_windows_ram(), shutil.disk_usage(HERE).free
    stop(ram >= 8*1024**3 and disk >= 1024**3, "need >=8GiB available RAM/1GiB disk")
    sources = generated_geo(run)
    parsed = {}
    for name, geo in sources.items():
        p = command([str(gmsh), str(geo), "-parse_and_exit"], geo.parent, timeout=20)
        stop(p.returncode == 0 and not re.search(r"(?im)^\s*Error\s*:",
                                                 p.stdout+p.stderr),
             "native GEO parse for " + name)
        parsed[name] = p.returncode
    return ({"source_pin_count": len(pin["files"]), "formula_samples": values,
             "native_gmsh": str(gmsh), "native_gmsh_sha256": GMSH_SHA,
             "native_gmsh_version": GMSH_VERSION, "native_parse_exits": parsed,
             "free_RAM_bytes": ram, "free_disk_bytes": disk,
             "geo_sha256": {n: sha256(path) for n, path in sources.items()}}, sources)


def consume_one_shot(run: Path) -> None:
    payload = {"protocol": REV, "utc": datetime.now(timezone.utc).isoformat(),
               "run": str(run), "m1_sha256": M1_SHA,
               "mode": "THREE_INDEPENDENT_NATIVE_GMSH_1D_ONLY_NO_FEM"}
    user = profile_marker()
    user.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation IMMEDIATELY BEFORE the first native Gmsh -1.
    # Any partial failure consumes the attempt, no marker deletion or retry.
    with user.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
    with LOCAL_MARKER.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)


def evidence(run: Path) -> Path:
    dst = run/"P10DT_EVIDENCE.zip"
    with zipfile.ZipFile(dst, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("P10DT_RUN_MANIFEST.json", "P10DT_RESULT.txt", "P10DT_STOP_TRACE.txt"):
            if (run/name).is_file():
                z.write(run/name, name)
        for geo in sorted((run/"GEO").glob("*.geo")):
            z.write(geo, "GEO/"+geo.name)
        for p in sorted(run.glob("*_TAIL.txt")):
            z.write(p, p.name)
        for log in sorted(run.glob("*.log")):
            if log.stat().st_size <= LOG_MAX + 1024:
                z.write(log, log.name)
    return dst


def do_run(preflight_only: bool) -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    run = RUNS/("P10DT_1D_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta = {"protocol": REV, "status": "P10DT_STOP_NO_FEM",
            "accepted_original_m1_sha256": M1_SHA,
            "p10dr_evidence_sha256": P10DR_EVIDENCE_SHA,
            "mesh_2d_runs": 0, "mesh_3d_runs": 0, "physical_FEM_runs": 0,
            "one_shot_sequence_limit": 1, "max_1d_variants": 3,
            "per_variant_wall_s": WALL_S, "max_private_bytes": PRIVATE_MAX,
            "started_utc": datetime.now(timezone.utc).isoformat(), "variants": []}
    code = 2
    try:
        pre, sources = preflight(run)
        meta.update(pre)
        print("P10DT SAFE PREFLIGHT PASS: 3 native GEO parses, source pin, no mesh.", flush=True)
        if preflight_only:
            meta["status"] = "P10DT_READ_ONLY_PREFLIGHT_OK"
            code = 0
        else:
            print("ONLY three separate Gmsh -1 tests <=15s EACH; NO -2/-3/FEM.", flush=True)
            answer = input("Type exactly RUN ONE P10DT 1D DIAGNOSTIC: ").strip()
            stop(answer == CONFIRM, "manual phrase missing; marker NOT consumed")
            consume_one_shot(run)
            for name in NAMES:
                print("P10DT launching native 1D:", name, flush=True)
                record = original_native.native_1d(str(meta["native_gmsh"]), sources[name], run)
                meta["variants"].append(record)
                print("P10DT", name, record["status"], "wall_s",
                      round(record["wall_s"], 2), flush=True)
            failed = [r["name"] for r in meta["variants"] if r["status"] != "PASS"]
            if failed:
                meta["status"] = "P10DT_ALL_THREE_FINISHED_WITH_1D_STOPS_NO_FEM"
                meta["stop_reason"] = "Nonpassing 1D contrasts: " + ", ".join(failed)
            else:
                meta["status"] = "P10DT_ALL_THREE_1D_PASS_NO_FEM"
                code = 0
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        print("P10DT STOP:", exc, flush=True)
        (run/"P10DT_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run/"P10DT_RUN_MANIFEST.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (run/"P10DT_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nFEM_RUNS=0\nM2_2D_3D_MESH_RUNS=0\n"+
            "STOP_REASON="+str(meta.get("stop_reason", ""))+"\n", encoding="utf-8")
        archive = evidence(run)
        print("P10DT RESULT:", meta["status"], "EVIDENCE:", archive, flush=True)
        print("Send ONLY P10DT_EVIDENCE.zip. NEVER rerun button 02.", flush=True)
    return code


def selftest() -> int:
    stop(len(source_gate()["files"]) == 8 and len(contrast_geo()) == 3 and
         len(formula_unit()["six_original_F3_sample_points"]) == 6 and
         original_native.native_1d.__code__.co_consts.count("-1") == 1,
         "source and no-FEM three-variant selftest")
    print("P10DT_SOURCE_AND_THREE_CONTRASTS_SELFTEST_OK native_Gmsh=NOT_RUN FEM=0")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    stop(not (args.selftest and args.preflight_only), "choose one mode")
    return selftest() if args.selftest else do_run(args.preflight_only)


if __name__ == "__main__":
    raise SystemExit(main())
