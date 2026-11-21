#!/usr/bin/env python3
"""Independently classify the original P10CT R1 evidence, no mesh reconstruction."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

EXPECTED_ZIP_SHA = "06fceca8df77018a706c2de79bcada2978a079b1086114235201a2ed7c47c895"
EXPECTED_MEMBERS = {"P10CT_GMSH_STDERR.txt", "P10CT_GMSH_STDOUT.txt",
                    "P10CT_QA_STDOUT.txt", "P10CT_RESULT.txt", "P10CT_UNIT.txt"}


def audit(source: Path):
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != EXPECTED_ZIP_SHA:
        raise ValueError("original evidence ZIP SHA mismatch")
    with zipfile.ZipFile(source) as z:
        if set(z.namelist()) != EXPECTED_MEMBERS or z.testzip() is not None:
            raise ValueError("original evidence ZIP members or CRC mismatch")
        files = {k: z.read(k) for k in EXPECTED_MEMBERS}
    def decoded(n):
        return files[n].decode("utf-8-sig", "replace")
    result_lines = decoded("P10CT_RESULT.txt").splitlines()
    fields = dict(s.split("=", 1) for s in result_lines if "=" in s)
    gmsh_stdout = decoded("P10CT_GMSH_STDOUT.txt")
    gmsh_stderr = decoded("P10CT_GMSH_STDERR.txt")
    m = re.search(r"(\d+) nodes (\d+) elements", gmsh_stdout)
    w = re.search(r"worst distortion =\s*([+-]?\d+\.\d+).*?(\d+) elements with jac\. < 0", gmsh_stderr)
    assert m and w, "Gmsh count/distortion evidence incomplete"
    asserts = {"sha5": fields.get("SOURCE_SHA_GATES") == "PASS_5_OF_5",
               "unit": fields.get("SYNTHETIC_UNIT") == "PASS_EXIT_0",
               "gmsh_exit": fields.get("GMSH_EXIT") == "0",
               "original_mesh_sha": fields.get("U0_MESH_SHA256") == "1a4690d1c57c8b520d596f9a864f754a8d84151bfd1fdd36f56631488779c6a3",
               "no_FEM": fields.get("PHYSICAL_FEM_RUNS") == "0",
               "qa_not_completed": fields.get("RESULT") == "P10CT_STOP_NO_FEM" and len(files["P10CT_QA_STDOUT.txt"]) == 0}
    if not all(asserts.values()):
        raise ValueError("P10CT R1 evidence invariants STOP: " + repr(asserts))
    return {
        "result": "P10CT_R1_ORIGINAL_GMSH_COMPLETED_QA_NOT_ESTABLISHED",
        "original_zip_sha256": sha, "zip_crc_count": len(files),
        "source_sha_gates": fields["SOURCE_SHA_GATES"],
        "unit_status": fields["SYNTHETIC_UNIT"], "gmsh_native_exit": int(fields["GMSH_EXIT"]),
        "gmsh_wall_seconds": float(fields["GMSH_WALL_SECONDS"]),
        "gmsh_peak_private_gib": float(fields["GMSH_PEAK_PRIVATE_GIB"]),
        "gmsh_total_nodes": int(m.group(1)), "gmsh_all_elements": int(m.group(2)),
        "tet10_count": "UNKNOWN_UNTIL_QA", "gmsh_mesh_bytes": int(fields["U0_MESH_BYTES"]),
        "gmsh_mesh_sha256": fields["U0_MESH_SHA256"],
        "gmsh_high_order_optimization_warning": {
            "worst_distortion_reported": float(w.group(1)),
            "elements_with_negative_jac_reported": int(w.group(2)),
            "time_or_stage": "UNKNOWN_INITIAL_VS_FINAL", "final_curved_27qp_inversions": "UNKNOWN",
        },
        "first_python_QA_stdout_bytes": len(files["P10CT_QA_STDOUT.txt"]),
        "first_python_QA_summary": "ABSENT", "first_python_QA_traceback": "TRUNCATED_BY_POWERSHELL_LAUNCHER",
        "physical_FEM_runs": 0,
        "conclusion": "one uniform U0 .msh created; not yet validated; NEVER run FEM on this evidence alone",
        "recovery": "read same SHA-pinned mesh only, 27 QP all Tet10, capture complete Python traceback",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("evidence_zip", type=Path)
    p.add_argument("output_json", type=Path)
    args = p.parse_args()
    result = audit(args.evidence_zip)
    args.output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(result["result"])
