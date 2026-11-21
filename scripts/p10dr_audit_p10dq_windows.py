#!/usr/bin/env python3
"""Independently audit the exact original P10DQ Windows ZIP (never run Gmsh)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

EXPECTED_ZIP = "35e859aefb089b1bdb08a02570009a956424585b691fc72b65e46aca519020f2"
P10DQ_SOURCE = "c79787de1788d98c5499e0263293fd3ce3100bc779c6891b5f6b7f74221c2905"
M1 = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
EXPECTED_VARIANTS = (
    "A_BASE_M1_FIELD2", "B_F2_MATHEVAL_PROXY", "C_F5_LINEAR_DIAGNOSTIC",
    "D_F5_POWER_EXACT", "E_F5_ORIGINAL_LOGEXP",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(condition: bool, msg: str) -> None:
    if not condition:
        raise ValueError("P10DR_EVIDENCE_STOP: " + msg)


def audit(path: Path, source: Path) -> dict:
    raw = path.read_bytes()
    check(digest(raw) == EXPECTED_ZIP, "P10DQ original ZIP SHA256 mismatch")
    check(digest(source.read_bytes()) == P10DQ_SOURCE, "released P10DQ source SHA mismatch")
    with zipfile.ZipFile(path) as z, zipfile.ZipFile(source) as src:
        check(z.testzip() is None and src.testzip() is None, "ZIP CRC error")
        names = z.namelist()
        check(len(names) == 12 and len(names) == len(set(names)), "ZIP member count/duplicates")
        for n in names:
            p = PurePosixPath(n)
            check(not p.is_absolute() and ".." not in p.parts and "\\" not in n,
                  "unsafe ZIP path")
        m = json.loads(z.read("P10DQ_RUN_MANIFEST.json"))
        res = z.read("P10DQ_RESULT.txt").decode("utf-8")
        check(m["protocol"] == "P10DQ_R1_NATIVE_1D_FIELD_DIAGNOSTIC_NO_FEM",
              "protocol")
        check(m["status"] == "P10DQ_STOP_NO_FEM" and
              "RESULT=P10DQ_STOP_NO_FEM" in res, "result status")
        check(m["m1_sha256"] == M1 and m["source_pin_count"] == 7, "M1/source pin")
        check(m["native_gmsh_version"] == "4.15.2" and
              m["native_gmsh_sha256"] ==
              "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1",
              "native Gmsh binary identity in Windows manifest")
        check(all(m[k] == 0 for k in ("physical_FEM_runs", "three_dimensional_mesh_runs",
                                       "two_dimensional_mesh_runs")), "non-1D run")
        check(m["one_dimensional_attempt_limit"] == 1 and
              m["per_variant_wall_limit_s"] == 25, "one-shot/time limit")
        check(list(m["native_parse_exits"]) == list(EXPECTED_VARIANTS) and
              all(v == 0 for v in m["native_parse_exits"].values()), "native parse")
        check(len(m["variant_geo_sha256"]) == 5, "GEO inventory")
        for name in EXPECTED_VARIANTS:
            member = "GEO/" + name + ".geo"
            check(digest(z.read(member)) == m["variant_geo_sha256"][name],
                  "GEO digest " + name)
        # Python text write on native Windows converts source LF to CRLF.
        norm = lambda b: b.replace(b"\r\n", b"\n")
        check(norm(z.read("GEO/E_F5_ORIGINAL_LOGEXP.geo")) ==
              norm(src.read("P10DN_M2_FIELD20.geo")),
              "original E GEO differs beyond Windows newline translation")
        check(norm(z.read("GEO/sphere_pore_B6_refined.geo")) ==
              norm(src.read("sphere_pore_B6_refined.geo")),
              "base CAD differs beyond Windows newline translation")
        results = m["variants"]
        check([r["name"] for r in results] == list(EXPECTED_VARIANTS[:3]),
              "executed variant order or silent D/E execution")
        statuses = ("PASS", "PASS", "TIMEOUT_25S")
        for r, expected in zip(results, statuses):
            check(r["status"] == expected, "unexpected run status " + r["name"])
            argv = r["argv"]
            check("-1" in argv and "-2" not in argv and "-3" not in argv and
                  "-o" in argv and "-nt" in argv, "native argument mode")
            tail = z.read(r["name"] + "_TAIL.txt").decode("utf-8", errors="replace")
            check("Meshing 1D" in tail, "missing native 1D log")
            if expected == "PASS":
                check(r["native_exit"] == 0 and 0 < r["wall_s"] < 5 and
                      r["mesh_bytes"] == 280 and
                      re.search(r"\b\d+ nodes \d+ elements\b", tail),
                      "baseline pass or native node counts")
            else:
                check(r["wall_s"] >= 25 and r["wall_s"] < 28 and
                      r["mesh_bytes"] == 0 and r["peak_private_polled"] < 4*1024**3,
                      "bounded C timeout")
                check("Meshing curve 14 (Circle)" in tail and
                      "Meshing curve 17 (Circle)" in tail and
                      "Meshing 2D" not in tail and "Meshing 3D" not in tail,
                      "failure locus")
        check("C_F5_LINEAR_DIAGNOSTIC: TIMEOUT_25S" in m["stop_reason"] and
              "FEM_RUNS=0" in res and "M2_3D_MESH_RUNS=0" in res,
              "STOP rationale")
        return {
            "audit": "P10DR_ORIGINAL_P10DQ_INDEPENDENT_AUDIT_PASS",
            "evidence_zip_sha256": EXPECTED_ZIP, "zip_crc": "12/12",
            "p10dq_source_zip_sha256": P10DQ_SOURCE,
            "accepted_original_m1_sha256": M1,
            "native_gmsh_version_per_manifest": m["native_gmsh_version"],
            "executed": [{k: r[k] for k in
                          ("name", "status", "native_exit", "wall_s", "peak_private_polled",
                           "mesh_bytes", "mesh_sha256", "log_bytes")}
                         for r in results],
            "not_executed": list(EXPECTED_VARIANTS[3:]),
            "geometry_parse_pass": 5,
            "observed_last_1d_curve": "14/17",
            "total_physical_FEM": 0, "M2_3D_mesh": 0,
            "scientific_inference": "F2 MathEval proxy is fast; a variant using F5 and its F3/F4 dependency chain stalls at 1D. The precise cause remains UNKNOWN.",
            "scope_warning": "MSH2 files of 280 bytes are not an independent 1D topology audit: native Gmsh log is the evidence for 244 nodes/135 elements.",
            "windows_text_translation": "Generated Windows GEO was CRLF, released P10DQ source LF; equality checked after CRLF-to-LF only.",
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] /
                   "research/packages/P10DQ_R1_1D_FIELD_ISOLATION_WINDOWS_20261121.zip")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    result = audit(args.zip, args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["audit"], "CRC=12/12 variants=PASS,PASS,TIMEOUT_25S FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
