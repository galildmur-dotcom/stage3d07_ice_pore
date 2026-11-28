#!/usr/bin/env python3
"""Reproduce P10DH audit of an original P10DG R1 Windows prelaunch STOP ZIP.

Checks only the evidence that exists. Never claims a real M1 geometry audit.
No Gmsh, FEM, network, or changes to source H0 are performed.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/proposals/P10DG_M1_H0_EMPIRICAL_MESH_ONLY_20261121"
PACKAGE = ROOT / "research/packages/P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121.zip"
PACKAGE_SHA256 = "4c5f3712931f7de5bfe0b9e1734aa37ed4d1b72c6553f7828fdd56808bce6a82"
INPUT_SHA256 = "55af9103f2cae7a2d99a1fded640068ec69833d79482bd81adec4b27428a33f0"
EXPECTED_FILES = {
    "P10DG_RUN_MANIFEST.json",
    "P10DG_RESULT.txt",
    "P10DG_STOP_TRACE.txt",
}
STOP = "P10DG_STOP: manual one-shot phrase not confirmed"
H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"


def check(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def validate_manifest(m: dict, pinned: dict) -> None:
    check(m.get("protocol") == "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY",
          "unexpected P10DG protocol")
    check(m.get("status") == "P10DG_STOP_NO_FEM", "unexpected run status")
    check(m.get("FEM_runs") == 0 and m.get("mesh_only") is True,
          "physical FEM may have run")
    check(m.get("Gmsh_max_attempts") == 1 and m.get("H0_is_not_remeshed") is True,
          "protocol gate mismatch")
    check(m.get("stop_reason") == STOP, "prelaunch stop reason mismatch")
    check(m.get("package_sources_sha256") == pinned["files"] and
          len(pinned["files"]) == 12, "Windows package source SHA12 mismatch")
    check(m.get("h0_sha256") == H0_SHA and
          m.get("gmsh_version_output") == "4.15.2", "H0/Gmsh preflight mismatch")
    check(m.get("available_memory_before_bytes", 0) >= 16 * 1024**3 and
          m.get("free_disk_before_bytes", 0) >= 4 * 1024**3,
          "resource preflight mismatch")
    check("P10DG_QA_SYNTHETIC_OK" in m.get("unit_stdout", "") and
          "radial_over_under_negative=DETECTED" in m["unit_stdout"],
          "synthetic geometry test not attested")
    for absent in ("exact_gmsh_argv", "native_exit_code", "wall_seconds",
                   "m1_mesh_path", "m1_mesh_size_bytes", "m1_mesh_sha256",
                   "qa_exit_code"):
        check(absent not in m, "unexpected Gmsh/QA execution field: " + absent)
    start = datetime.fromisoformat(m["started_utc"])
    finish = datetime.fromisoformat(m["finished_utc"])
    check(0 <= (finish - start).total_seconds() < 60,
          "invalid short prelaunch interval")
    check(abs(m["target_typical_volume_ratio"] - 0.8) < 1e-14,
          "unexpected H0-based target")


def package_pins() -> dict:
    check(sha256(PACKAGE.read_bytes()).hexdigest() == PACKAGE_SHA256,
          "published source ZIP mismatch")
    with zipfile.ZipFile(PACKAGE) as archive:
        check(archive.testzip() is None and len(archive.namelist()) == 13,
              "published source ZIP CRC/inventory mismatch")
        pins = json.loads(archive.read("P10DG_PINNED_SHA256.json"))
        for filename, expected_sha in pins["files"].items():
            check(sha256(archive.read(filename)).hexdigest() == expected_sha,
                  "published source ZIP file SHA mismatch: " + filename)
    return pins


def verify(path: Path) -> dict:
    original = path.read_bytes()
    digest = sha256(original).hexdigest()
    check(digest == INPUT_SHA256, "original evidence ZIP SHA mismatch")
    pinned = package_pins()
    check(pinned["revision"] == "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY",
          "pin revision mismatch")
    for filename in ("P10DG_one_click_m1.py", "P10DG_compare_m1.py",
                     "P10DG_windows_guards.py"):
        check(sha256((SOURCE / filename).read_bytes()).hexdigest() ==
              pinned["files"][filename], "repo protocol source changed: " + filename)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        check(len(infos) == 3 and {i.filename for i in infos} == EXPECTED_FILES,
              "ZIP inventory must be precisely 3 evidence files")
        check(archive.testzip() is None, "ZIP CRC failure")
        check(not any(i.flag_bits & 1 for i in infos), "encrypted ZIP evidence")
        manifest = json.loads(archive.read("P10DG_RUN_MANIFEST.json"))
        result = archive.read("P10DG_RESULT.txt").decode("utf-8")
        trace = archive.read("P10DG_STOP_TRACE.txt").decode("utf-8")
    validate_manifest(manifest, pinned)
    expected_result = "\n".join([
        "RESULT=P10DG_STOP_NO_FEM", "FEM_RUNS=0", "M1_MSH_NOT_UPLOADED=1",
        "STOP_REASON=" + STOP, "M1_SHA256=UNKNOWN",
        "WINDOWS_NATIVE_GMSH_EXIT=UNKNOWN", "QA_EXIT=UNKNOWN", "",
    ])
    check(result.replace("\r\n", "\n") == expected_result,
          "run result and manifest disagree")
    check("in do_one_run" in trace and
          "require(answer == CONFIRM, \"manual one-shot phrase not confirmed\")" in trace and
          ("RuntimeError: " + STOP) in trace, "prelaunch traceback mismatch")
    code = (SOURCE / "P10DG_one_click_m1.py").read_text(encoding="utf-8")
    check(code.index("require(answer == CONFIRM") <
          code.index("meta.update(launch(meta, run_dir, mesh))") and
          "with MARKER.open(\"x\"" in code,
          "one-shot launch-marker control flow changed")
    return {
        "protocol": "P10DH_R1_P10DG_REAL_WINDOWS_PRELAUNCH_STOP_AUDIT",
        "original_evidence_sha256": digest,
        "original_evidence_size_bytes": len(original),
        "zip_crc": "PASS_3_OF_3",
        "source_sha12": "PASS_12_OF_12",
        "h0_sha256_attested": manifest["h0_sha256"],
        "gmsh_version_attested": manifest["gmsh_version_output"],
        "synthetic_tests_attested": "PASS",
        "stop_reason": STOP,
        "one_shot_marker_created_by_this_run": False,
        "one_shot_marker_conclusion_basis": "pinned source control flow and trace before launch",
        "gmsh_launched_by_this_run": False,
        "m1_mesh_created_by_this_run": False,
        "m1_geometry_QA": "NOT_PERFORMED",
        "physical_FEM_runs": 0,
        "wall_clock_seconds_until_stop": round(
            (datetime.fromisoformat(manifest["finished_utc"]) -
             datetime.fromisoformat(manifest["started_utc"])).total_seconds(), 6),
        "next_step": "RERUN_SAME_PACKAGE_WITH_EXACT_MANUAL_PHRASE_AFTER_CONFIRMING_MARKER_ABSENT",
        "limitations": (
            "Manifest and traceback are Windows tool self-reports; without M1.msh "
            "no independent geometry, volumetric ratio or 27QP Tet10 audit is possible."
        ),
    }


def selftest() -> None:
    pinned = package_pins()
    sample = json.loads(
        (ROOT / "research/evidence/P10DH_P10DG_PRELAUNCH_STOP_20261121"
         / "derived/P10DH_P10DG_PRELAUNCH_AUDIT.json").read_text(encoding="utf-8"))
    check(sample["gmsh_launched_by_this_run"] is False, "derived sample not a STOP")
    archive = (ROOT / "research/evidence/P10DH_P10DG_PRELAUNCH_STOP_20261121"
               / "input/P10DG_EVIDENCE.zip")
    with zipfile.ZipFile(archive) as source:
        m = json.loads(source.read("P10DG_RUN_MANIFEST.json"))
    validate_manifest(m, pinned)
    for key, value in (("FEM_runs", 1),
                       ("status", "P10DG_M1_GEOMETRY_QA_OK_NO_FEM"),
                       ("stop_reason", "successful"),
                       ("native_exit_code", 0)):
        bad = copy.deepcopy(m)
        bad[key] = value
        try:
            validate_manifest(bad, pinned)
        except ValueError:
            continue
        raise AssertionError("negative test did not reject " + key)
    print("P10DH_NEGATIVE_SELFTEST_OK mutated_FEM/status/stop/native=REJECTED")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        selftest()
        return
    check(args.zip is not None, "--zip required")
    summary = verify(args.zip)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
