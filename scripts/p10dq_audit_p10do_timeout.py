#!/usr/bin/env python3
"""Independently audit the original P10DO R1 Windows STOP, without Gmsh/FEM."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/evidence/P10DQ_P10DO_M2_TIMEOUT_20261121"
INPUT = EVIDENCE / "input"
ZIP = INPUT / "P10DO_EVIDENCE_TIMEOUT.zip"
LOG = INPUT / "P10DO_GMSH_FULL_LOG_LOCAL.txt"
ORIGINAL = ROOT / "research/evidence/P10DI_P10DG_R1_REAL_M1_MESH_STOP_20261121/input/P10DG_EVIDENCE_REAL_M1.zip"
OUTPUT = EVIDENCE / "derived/P10DQ_P10DO_TIMEOUT_AUDIT.json"
EXPECTED_ZIP = "547ce2c801b058658439ff157735dca1e28c4931b5da56f4b71e96a61723e220"
EXPECTED_LOG = "dfff37bd5efb8b0f375106426b29dd7ddd70897c42df1776f4ba79d5dea1780f"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    assert sha(ZIP) == EXPECTED_ZIP and sha(LOG) == EXPECTED_LOG
    with zipfile.ZipFile(ZIP) as z:
        assert len(z.namelist()) == 5 and z.testzip() is None
        manifest = json.loads(z.read("P10DO_RUN_MANIFEST.json"))
        result = z.read("P10DO_RESULT.txt").decode("utf-8")
        trace = z.read("P10DO_STOP_TRACE.txt").decode("utf-8")
        log_tail = z.read("P10DO_GMSH_LOG_TAIL.txt").decode("utf-8")
        labels = json.loads(z.read("P10DO_M1_COEFFICIENT_SUMMARY.json"))
    with zipfile.ZipFile(ORIGINAL) as z:
        assert z.testzip() is None
        old = json.loads(z.read("P10DG_RUN_MANIFEST.json"))
    full = LOG.read_text(encoding="utf-8", errors="replace")
    # ZIP tail retains doubled Windows CR from native Gmsh output; the separately
    # supplied text attachment has normalized line endings, not different lines.
    assert full.replace("\r", "").strip() == log_tail.replace("\r", "").strip()
    assert manifest["protocol"] == "P10DO_R1_M2_GRADED_KAPPA20_MESH_ONLY"
    assert manifest["status"] == "P10DO_STOP_NO_FEM" and manifest["physical_FEM_runs"] == 0
    assert manifest["stop_reason"] == "P10DO_STOP_GMSH_WALL_900S"
    assert manifest["m1_sha256"] == M1_SHA and labels["m1_sha256"] == M1_SHA
    assert labels["tet10"] == 9736 and sum(labels["label_counts"].values()) == 9736
    assert "STOP_REASON=P10DO_STOP_GMSH_WALL_900S" in result
    assert "RuntimeError: P10DO_STOP_GMSH_WALL_900S" in trace
    assert "-3" in manifest["native_Gmsh_argv"] and "-nt" in manifest["native_Gmsh_argv"]
    assert "native_exit_code" not in manifest and "qa_exit_code" not in manifest
    assert "m2_mesh_sha256" not in manifest
    assert re.search(r"Meshing 1D", full) and "Meshing curve 14 (Circle)" in full
    assert "Meshing curve 17 (Circle)" in full
    assert "Meshing 2D" not in full and "Meshing 3D" not in full
    assert old["m1_mesh_sha256"] == M1_SHA and old["native_exit_code"] == 0
    assert old["wall_seconds"] < 1
    report = {
        "protocol": "P10DQ_P10DO_WINDOWS_STOP_INDEPENDENT_READ_ONLY_AUDIT",
        "status": "P10DQ_TIMEOUT_AND_1D_STALL_VERIFIED",
        "p10do_zip_sha256": EXPECTED_ZIP,
        "p10do_full_log_sha256": EXPECTED_LOG,
        "zip_member_count": 5,
        "zip_crc_all_pass": True,
        "native_gmsh_version": manifest["gmsh_version_stdout"],
        "p10do_stop_reason": manifest["stop_reason"],
        "gmesh_3d_argv_started": True,
        "last_observed_stage": "1D curves 14 and 17",
        "2d_or_3d_mesh_observed": False,
        "m2_mesh_sha256": None,
        "m2_geometry_qa_performed": False,
        "physical_fem_runs": 0,
        "m1_original_successful_native_gmsh_wall_s": old["wall_seconds"],
        "p10do_wall_bound_s": manifest["wall_limit_s"],
        "runtime_ratio_lower_bound": manifest["wall_limit_s"] / old["wall_seconds"],
        "m1_label_counts": labels["label_counts"],
        "independence_limits": "Only Windows manifest/log; no native field values, no raw M2 mesh. Root cause of slow 1D meshing NOT proven.",
        "next": "P10DQ separate one-shot, 5 isolated Gmsh -1 variants, no P10DO rerun, no FEM",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("P10DQ_P10DO_TIMEOUT_INDEPENDENT_AUDIT_OK",
          "zip_crc=5/5 native1D_stall=YES FEM=0",
          "ratio_lower_bound=%.2f" % report["runtime_ratio_lower_bound"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
