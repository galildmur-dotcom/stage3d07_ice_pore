#!/usr/bin/env python3
"""P10IQ: read-only M3 FEM compatibility preflight. Absolutely no FEM or build."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

from P10FN_common import HERE, sha256, validate_source, need
from P10FN_mesh_qa import audit

M3_SHA = "3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a"
M3_TET10 = 10063
M3_PORE_TRI6 = 262
M3_NODES = None  # independent per-file QA checks the count, no fabricated pin
PROTOCOL = "P10IQ_M3_SOURCE_ONLY_FEM_COMPATIBILITY_PREFLIGHT_V1"


def main() -> int:
    if "--run" in sys.argv or "--fem" in sys.argv:
        print("P10IQ_STOP: first M3 FEM not authorized by this package", flush=True)
        return 2
    started = time.monotonic()
    report = {"protocol": PROTOCOL, "status": "STOP", "FEM_attempts": 0,
              "mesh_generation_attempts": 0, "compilation_attempts": 0,
              "solver_executions": 0, "M3_geometry_status": "P10IP_GEOMETRY_GO"}
    try:
        print("P10IQ_CHECK_1: verifying exact original solver-source bundle", flush=True)
        report["source_revision"] = validate_source()
        mesh = HERE / "M3.msh"
        need(mesh.is_file(), "M3.msh missing")
        digest = sha256(mesh)
        need(digest == M3_SHA, "M3 SHA-256 mismatch; no FEM")
        print("P10IQ_CHECK_2: scanning pinned M3 Tet10 curved geometry (27QP)", flush=True)
        qa = audit(mesh)
        need(qa["tet10"] == M3_TET10 and qa["pore_tri6"] == M3_PORE_TRI6,
             "unexpected element count in M3")
        need(qa["nonpositive_samples"] == 0 and qa["physical_surface_tags"] == list(range(2, 10)),
             "wrong physical regions or invalid curved elements")
        source = (HERE / "stage3d10fn_any_mesh_full4d.cpp").read_text(encoding="utf-8")
        need("--p10fn-authorized" in source and "P10FN_ONE_SHOT_MARKER" in source,
             "M3 solver guard source incomplete")
        physics = (HERE / "P10FN_physics.py").read_text(encoding="utf-8")
        need("ensure_binary" in physics and "P10FN_BUILD" in physics,
             "original MinGW compiler wrapper incomplete")
        report.update(status="PASS_SOURCE_ONLY_NO_FEM", mesh_sha256=digest,
                      mesh_qa=qa, solver_source_guard="PRESENT",
                      accepted_physical_parameters={"mode":"R", "law":"EDV_VAR",
                          "xi":0,"B6_mm":5,"t_final_s":900,"dt_s":25,
                          "steps":36,"threads":4},
                      next_action="researcher approval required before M3 one-shot FEM")
        print("P10IQ_SOURCE_ONLY_PASS_NO_FEM", "mesh_sha256="+digest,
              "tet10="+str(qa["tet10"]), flush=True)
    except BaseException as exc:
        report["error"] = repr(exc)
        print("P10IQ_SOURCE_ONLY_STOP_NO_FEM", repr(exc), flush=True)
    report["wall_s"] = round(time.monotonic()-started, 3)
    path = HERE / "P10IQ_M3_PREFLIGHT_RESULT.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("P10IQ_SEND_RESULT", str(path), flush=True)
    return 0 if report["status"] == "PASS_SOURCE_ONLY_NO_FEM" else 2


if __name__ == "__main__":
    sys.exit(main())
