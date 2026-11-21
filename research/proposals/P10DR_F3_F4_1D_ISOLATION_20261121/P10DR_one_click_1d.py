#!/usr/bin/env python3
"""P10DR: one-shot bounded, ONLY native Windows Gmsh -1 F3/F4 isolation; NO FEM."""
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
import time
import traceback
import zipfile

from P10DO_windows_guards import child_private_bytes, command, free_windows_ram, sha256

REV = "P10DR_R1_F3_F4_1D_ONLY_NO_FEM"
HERE = Path(__file__).resolve().parent
RUNS = HERE / "P10DR_RUNS"
LOCAL_MARKER = RUNS / "P10DR_ONE_DIAGNOSTIC_SEQUENCE_USED.json"
CONFIRM = "RUN ONE P10DR 1D DIAGNOSTIC"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
P10DQ_SOURCE_SHA = "c79787de1788d98c5499e0263293fd3ce3100bc779c6891b5f6b7f74221c2905"
P10DQ_EVIDENCE_SHA = "35e859aefb089b1bdb08a02570009a956424585b691fc72b65e46aca519020f2"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
GMSH_VERSION = "4.15.2"
WALL_S = 15
PRIVATE_MAX = 2 * 1024**3
MSH_MAX = 20 * 1024**2
LOG_MAX = 1 * 1024**2
EXACT_F3 = 'Field[3].F = "min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0011)/0.0004))";'
EXACT_F4 = 'Field[4].F = "min(1,max(0,(((z-0.03)*(z-0.03)/(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))-0.36)/0.28))";'
EXACT_F5 = 'Field[5].F = "(1-F3*F3*(3-2*F3))*F4*F4*(3-2*F4)";'
EXACT_F6 = 'Field[6].F = "F2*exp(log(1-0.2*F5)/3)";'
VARIANTS = {
    "A_FIELD2_REFERENCE": None,
    "B_F3_RAW_REFERENCE": "F3",
    "C_F4_RAW_REFERENCE": "F4",
    "D_F3_F4_RAW_PRODUCT": "F3*F4",
    "E_F3_RADIAL_SMOOTHSTEP": "1-F3*F3*(3-2*F3)",
    "F_F4_ANGULAR_SMOOTHSTEP": "F4*F4*(3-2*F4)",
    "G_F3_F4_INLINE_SMOOTHSTEP": "(1-F3*F3*(3-2*F3))*F4*F4*(3-2*F4)",
}


def gate(ok: bool, msg: str) -> None:
    if not ok:
        raise RuntimeError("P10DR_STOP: " + msg)


def source_gate() -> dict:
    pin = json.loads((HERE / "P10DR_SOURCE_SHA256.json").read_text(encoding="utf-8"))
    gate(pin.get("revision") == REV and pin.get("physical_FEM") is False and
         pin.get("mesh_2d_3d") is False and pin.get("diagnostic_sequence_limit") == 1 and
         pin.get("accepted_m1_sha256") == M1_SHA and
         pin.get("p10dq_source_zip_sha256") == P10DQ_SOURCE_SHA and
         pin.get("p10dq_evidence_zip_sha256") == P10DQ_EVIDENCE_SHA and
         len(pin.get("files", {})) == 7, "source pin inventory/identity")
    for name, expected in pin["files"].items():
        gate(name == Path(name).name and ".." not in name and
             (HERE / name).is_file() and sha256(HERE / name) == expected,
             "source SHA mismatch: " + name)
    geo = (HERE / "P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    base = (HERE / "sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    gate(all(geo.count(exp) == 1 for exp in (EXACT_F3, EXACT_F4, EXACT_F5, EXACT_F6)) and
         geo.count("// F6:") == 1 and 'Include "sphere_pore_B6_refined.geo";' in geo and
         'Field[2] = Threshold;' in base and "Mesh.ElementOrder=2;" in base,
         "original P10DQ/P10DO geometry or field contract")
    return pin


def smoothstep(u: float) -> float:
    u = min(1., max(0., u))
    return u*u*(3.-2.*u)


def profile_unit() -> dict:
    pts = {
        "north_wall": (0., 0., .031),
        "south_wall": (0., 0., .029),
        "equator_wall": (.001, 0., .03),
        "north_d03mm": (0., 0., .0313),
        "north_d06mm": (0., 0., .0316),
        "far_field": (.02, 0., .03),
    }
    results = {}
    for name, (x, y, z) in pts.items():
        r2 = x*x + y*y + (z-.03)**2
        f3 = min(1., max(0., (math.sqrt(r2+1e-24)-.0011)/.0004))
        f4 = min(1., max(0., (((z-.03)**2/(r2+1e-24))-.36)/.28))
        vals = (f3, f4, f3*f4, 1-smoothstep(f3), smoothstep(f4),
                (1-smoothstep(f3))*smoothstep(f4))
        gate(all(math.isfinite(v) and 0. <= v <= 1. for v in vals),
             "F3/F4/combined values out of range")
        gate(all(.98 <= 1.-.02*v <= 1. for v in vals), "2%-edge diagnostic bound")
        results[name] = {"F3": f3, "F4": f4, "kappa": vals[-1]}
    gate(abs(results["north_wall"]["kappa"]-1.) < 1e-12 and
         abs(results["south_wall"]["kappa"]-1.) < 1e-12 and
         abs(results["north_d03mm"]["kappa"]-.5) < 1e-10 and
         results["equator_wall"]["kappa"] == 0. and
         results["north_d06mm"]["kappa"] == 0. and
         results["far_field"]["kappa"] == 0., "original kappa profile changed")
    return results


def geo_variants() -> dict[str, str]:
    original = (HERE / "P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    gate(all(original.count(key) == 1 for key in ("// F3:", "// F4:",
                                                 "// F5 =", "// F6:")),
         "original field block counts")
    base, fields = original.split("// F3:", 1)
    f3, fields = fields.split("// F4:", 1)
    f4, fields = fields.split("// F5 =", 1)
    # Strict isolation: omit every definition that is not a dependency.
    # In particular, no diagnostic variant defines F5 at all.
    only_f3 = "// F3:" + f3
    only_f4 = "// F4:" + f4
    result = {}
    for name, q in VARIANTS.items():
        uses_f3 = q is not None and "F3" in q
        uses_f4 = q is not None and "F4" in q
        prefix = base + (only_f3 if uses_f3 else "") + (only_f4 if uses_f4 else "")
        # Every diagnostic MathEval output stays within [0.98*F2,F2], not M2.
        result[name] = (prefix + "\nBackground Field=2;\n" if q is None else
                        prefix + '\nField[6] = MathEval;\nField[6].F = "F2*(1-0.02*(' +
                        q + '))";\nBackground Field=6;\n')
    gate(len(result) == 7 and all(
        'Include "sphere_pore_B6_refined.geo";' in s and
        s.count("Background Field=") == 1 and EXACT_F6 not in s and
        'Field[5] = MathEval;' not in s and
        ('Field[3] = MathEval;' in s) == (q is not None and 'F3' in q) and
        ('Field[4] = MathEval;' in s) == (q is not None and 'F4' in q)
        for (_, q), s in zip(VARIANTS.items(), result.values())),
         "diagnostic GEO variants unsafe")
    return result


def user_marker() -> Path:
    root = os.environ.get("LOCALAPPDATA", "")
    gate(bool(root) and Path(root).is_dir(), "Windows LOCALAPPDATA unavailable")
    return Path(root) / "Stage3D07" / ("P10DR_1D_" + M1_SHA + ".json")


def generated_sources(run: Path) -> dict[str, Path]:
    folder = run / "GEO"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "sphere_pore_B6_refined.geo", folder / "sphere_pore_B6_refined.geo")
    output = {}
    for name, value in geo_variants().items():
        path = folder / (name + ".geo")
        path.write_text(value, encoding="utf-8")
        output[name] = path
    return output


def preflight(run: Path) -> tuple[dict, dict[str, Path]]:
    gate(os.name == "nt", "native Gmsh -1 permitted on Windows ONLY")
    original_root = str(Path(r"G:\ildar\Stage3D07")).casefold()
    current = str(HERE).casefold()
    gate(current != original_root and not current.startswith(original_root + "\\"),
         "extract outside original Windows Stage3D07")
    pin = source_gate()
    samples = profile_unit()
    gate(not LOCAL_MARKER.exists() and not user_marker().exists(),
         "P10DR one-shot already consumed; NO REPEAT")
    gmsh = Path(os.environ.get("P10DR_GMSH_EXE", r"C:\gmsh-4.15.2-Windows64\gmsh.exe"))
    gate(gmsh.is_file() and sha256(gmsh) == GMSH_SHA, "Gmsh exact executable SHA")
    proc = command([str(gmsh), "-version"], HERE, timeout=15)
    gate(proc.returncode == 0 and re.search(r"(?<![0-9])4\.15\.2(?![0-9])",
                                           proc.stdout+proc.stderr) is not None,
         "Gmsh native version")
    ram, disk = free_windows_ram(), shutil.disk_usage(HERE).free
    gate(ram >= 8*1024**3 and disk >= 1024**3, "need >=8GiB free RAM and 1GiB disk")
    sources = generated_sources(run)
    parses = {}
    for name, path in sources.items():
        p = command([str(gmsh), str(path), "-parse_and_exit"], path.parent, timeout=20)
        gate(p.returncode == 0 and not re.search(r"(?im)^\s*Error\s*:",
                                                  p.stdout+p.stderr),
             "native -parse_and_exit: " + name)
        parses[name] = p.returncode
    return ({"source_pin_count": len(pin["files"]), "gmsh_path": str(gmsh),
             "gmsh_sha256": GMSH_SHA, "gmsh_version": GMSH_VERSION,
             "native_parse_exits": parses, "free_RAM_bytes": ram,
             "free_disk_bytes": disk, "profile_unit": samples,
             "geo_sha256": {n: sha256(p) for n, p in sources.items()}}, sources)


def consume_marker(run: Path) -> None:
    data = {"protocol": REV, "m1_sha256": M1_SHA,
            "run_dir": str(run), "utc": datetime.now(timezone.utc).isoformat(),
            "mode": "SINGLE_SEVEN_VARIANT_GMSH_1D_SEQUENCE_NO_FEM"}
    global_marker = user_marker()
    global_marker.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create, IMMEDIATELY before the first native Gmsh -1 launch.
    # Partial creation is a consumed attempt; never delete or retry a marker.
    with global_marker.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    with LOCAL_MARKER.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def native_1d(gmsh: str, geo: Path, run: Path) -> dict:
    mesh, log = run / (geo.stem + ".msh"), run / (geo.stem + ".log")
    argv = [gmsh, str(geo), "-1", "-nt", "2", "-format", "msh2", "-o", str(mesh)]
    started, peak, status, exit_code = time.monotonic(), 0, "STARTED", None
    with log.open("w", encoding="utf-8") as stream:
        child = subprocess.Popen(argv, cwd=str(geo.parent), stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                peak = max(peak, child_private_bytes(child))
                if time.monotonic()-started > WALL_S:
                    status = "TIMEOUT_15S"
                    break
                if peak > PRIVATE_MAX:
                    status = "PRIVATE_GT_2GIB"
                    break
                if log.stat().st_size > LOG_MAX:
                    status = "LOG_GT_1MIB"
                    break
                if mesh.is_file() and mesh.stat().st_size > MSH_MAX:
                    status = "MESH_GT_20MIB"
                    break
                time.sleep(.2)
            if status != "STARTED" and child.poll() is None:
                child.kill()
            child.wait(timeout=15)
            exit_code = child.returncode
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=15)
    log_text = log.read_bytes().decode("utf-8", errors="replace")
    counts = re.findall(r"\b(\d+) nodes (\d+) elements\b", log_text)
    last = tuple(int(v) for v in counts[-1]) if counts else None
    if status == "STARTED":
        status = ("PASS" if exit_code == 0 and mesh.is_file() and
                  mesh.stat().st_size > 0 and last and last[0] > 0 and last[1] > 0 and
                  not re.search(r"(?im)^\s*Error\s*:", log_text) else
                  "NONZERO_OR_INVALID_1D_LOG")
    (run / (geo.stem + "_TAIL.txt")).write_text(log_text[-6500:], encoding="utf-8")
    return {"name": geo.stem, "status": status, "native_exit": exit_code,
            "wall_s": time.monotonic()-started, "peak_private_polled": peak,
            "mesh_bytes": mesh.stat().st_size if mesh.exists() else 0,
            "mesh_sha256": sha256(mesh) if mesh.exists() and mesh.stat().st_size else None,
            "reported_nodes_elements": last, "log_bytes": log.stat().st_size,
            "argv": argv}


def evidence(run: Path) -> Path:
    dst = run / "P10DR_EVIDENCE.zip"
    with zipfile.ZipFile(dst, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("P10DR_RUN_MANIFEST.json", "P10DR_RESULT.txt", "P10DR_STOP_TRACE.txt"):
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
    run = RUNS / ("P10DR_1D_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta = {"protocol": REV, "status": "P10DR_STOP_NO_FEM",
            "accepted_original_m1_sha256": M1_SHA,
            "p10dq_windows_evidence_sha256": P10DQ_EVIDENCE_SHA,
            "physical_FEM_runs": 0, "mesh_2d_runs": 0, "mesh_3d_runs": 0,
            "one_shot_sequence_limit": 1, "max_1d_variants": 7,
            "per_variant_wall_s": WALL_S, "max_private_bytes": PRIVATE_MAX,
            "started_utc": datetime.now(timezone.utc).isoformat(), "variants": []}
    code = 2
    try:
        pre, sources = preflight(run)
        meta.update(pre)
        print("P10DR SAFE PREFLIGHT PASS: exact sources, samples, SEVEN native GEO parses.", flush=True)
        if preflight_only:
            meta["status"] = "P10DR_READ_ONLY_PREFLIGHT_OK"
            code = 0
        else:
            print("ONLY Gmsh -1; <=15s each for 7 diagnostic variants; NO 2D, 3D, FEM.")
            print("All 7 independently tested, including after a timeout; NEVER repeats a variant.")
            phrase = input("Type exactly RUN ONE P10DR 1D DIAGNOSTIC: ").strip()
            gate(phrase == CONFIRM, "manual phrase missing; marker not consumed")
            consume_marker(run)
            for name in VARIANTS:
                print("P10DR launching 1D:", name, flush=True)
                r = native_1d(str(meta["gmsh_path"]), sources[name], run)
                meta["variants"].append(r)
                print("P10DR", name, r["status"], "wall_s", round(r["wall_s"], 2), flush=True)
            failed = [r["name"] for r in meta["variants"] if r["status"] != "PASS"]
            if failed:
                meta["status"] = "P10DR_DIAGNOSTIC_FINISHED_WITH_1D_STOPS_NO_FEM"
                meta["stop_reason"] = "Nonpassing variants: " + ", ".join(failed)
            else:
                meta["status"] = "P10DR_ALL_SEVEN_1D_PASS_NO_FEM"
                code = 0
    except BaseException as exc:
        meta["stop_reason"] = str(exc)
        print("P10DR STOP:", exc, flush=True)
        (run/"P10DR_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run/"P10DR_RUN_MANIFEST.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (run/"P10DR_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nFEM_RUNS=0\nM2_2D_3D_MESH_RUNS=0\n"+
            "STOP_REASON="+str(meta.get("stop_reason", ""))+"\n", encoding="utf-8")
        z = evidence(run)
        print("P10DR RESULT:", meta["status"], "EVIDENCE:", z, flush=True)
        print("Send ONLY P10DR_EVIDENCE.zip; NEVER rerun button 02.", flush=True)
    return code


def selftest() -> int:
    gate(len(source_gate()["files"]) == 7 and len(geo_variants()) == 7 and
         len(profile_unit()) == 6, "isolated source/formula selftest")
    gate("-1" in native_1d.__code__.co_consts and
         "-3" not in native_1d.__code__.co_consts,
         "native launch CLI mode")
    print("P10DR_SOURCE_AND_SEVEN_VARIANTS_SELFTEST_OK native_Gmsh=NOT_RUN FEM=0")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--preflight-only", action="store_true")
    a = ap.parse_args()
    gate(not (a.selftest and a.preflight_only), "choose one mode")
    return selftest() if a.selftest else do_run(a.preflight_only)


if __name__ == "__main__":
    raise SystemExit(main())
