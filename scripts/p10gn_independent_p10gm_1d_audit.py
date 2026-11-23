#!/usr/bin/env python3
"""Independent read-only audit of REAL P10GM native Windows -1 evidence ZIP.

No native Gmsh, geometry generation, FEM or use of original MSH.
The report is a derived secondary artifact, never the raw user evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "upload/P10GM_1D_PROBE_EVIDENCE.zip"
DEFAULT_REPORT = (ROOT / "research/evidence/P10GM_1D_20261123/derived/"
                  "P10GM_R1_INDEPENDENT_REAL_1D_VERDICT.json")
ZIP_SHA = "6b047f5dd485433987b1a518ad9c164f7a0fbf0747312c616dc31d84b8acfe34"
P10GK_SOURCE_SHA = "4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05"
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
FROZEN_SHA = "2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
CASES = ("A_F3_BASELINE", "B_F6_LINKED", "C_F7_INLINE")
GEO_SHA = {
    "M0_ROTATED.geo": "21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a",
    "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo": "1590d5f5fda58f4401cb038d898e49466e461a40a53fe692867d943b908508ba",
    "sphere_pore_B6_refined_rotated.geo": "e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def need(ok: bool, why: str):
    if not ok:
        raise RuntimeError("P10GM_INDEPENDENT_STOP: " + why)


def audit(archive: Path) -> dict:
    need(archive.is_file() and digest(archive.read_bytes()) == ZIP_SHA,
         "original user evidence ZIP sha256 mismatch")
    with zipfile.ZipFile(archive) as z:
        need(z.testzip() is None, "ZIP CRC failed")
        names = set(z.namelist())
        expected = {"P10GM_MANIFEST.json", "P10GM_PROGRESS.json"}
        for case in CASES:
            expected.update(f"{case}/{name}" for name in
                            ("M0_ROTATED.geo", "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo",
                             "sphere_pore_B6_refined_rotated.geo", "P10GM_1D.geo",
                             "P10GM_GMSH_1D.log"))
        need(names == expected and len(names) == 17, "unexpected archive file list")
        report = json.loads(z.read("P10GM_MANIFEST.json"))
        progress = json.loads(z.read("P10GM_PROGRESS.json"))
        need(report["revision"] == "P10GM_R1_NATIVE_1D_AB_C_ONLY_NO_3D_NO_FEM"
             and report["P10GK_source_sha256"] == P10GK_SOURCE_SHA
             and report["M0_sha256"] == M0_SHA
             and report["frozen_D027_sha256"] == FROZEN_SHA
             and report["installed"]["Gmsh_sha256"] == GMSH_SHA
             and report["installed"]["gmsh_version"] == "4.15.2"
             and report["installed"]["M0_msh_sha256"] == M0_SHA,
             "pinned native/source/M0/frozen provenance mismatch")
        need(report["status"] == "DIAG_FIELD_1D_TIMEOUT_OR_STOP_NO_3D"
             and report["native_2d_attempts"] == 0
             and report["native_3d_attempts"] == 0
             and report["FEM_attempts"] == 0,
             "wrong diagnostic status or unapproved dimensions")
        need(progress["cases"] == report["cases"]
             and progress["status"] == "STOP_INCOMPLETE_1D_DIAGNOSTIC",
             "incremental progress state inconsistent")
        need(len(report["cases"]) == 3
             and [x["case"] for x in report["cases"]] == list(CASES),
             "case count/order changed")
        summary = []
        for i, item in enumerate(report["cases"]):
            case = CASES[i]
            for name, expected_sha in GEO_SHA.items():
                need(digest(z.read(f"{case}/{name}")) == expected_sha,
                     f"{case}: source geometry mismatch: {name}")
            drv = z.read(f"{case}/P10GM_1D.geo")
            log_data = z.read(f"{case}/P10GM_GMSH_1D.log")
            log = log_data.decode("utf-8", errors="replace")
            need(digest(drv) == item["geo_sha256"], case + " driver hash")
            need(digest(log_data) == item["log_sha256"]
                 and len(log_data) == item["log_size"], case + " log hash/size")
            need("-1 -nopopup -nt 2 -format msh2" in log
                 and "[Gmsh 4.15.2" in log
                 and "Meshing 1D..." in log,
                 case + " native -1 command/started evidence missing")
            need(" -3 " not in log and " -2 " not in log
                 and "Meshing 2D" not in log and "Meshing 3D" not in log,
                 case + " unexpected native dimension")
            need(b"Mesh.MeshSizeFactor = 0.9378887276834518;" in drv,
                 case + " global field factor changed")
            need(b"Mesh 2;" not in drv and b"Mesh 3;" not in drv,
                 case + " forbidden mesh command")
            if i == 0:
                need(b'Background Field = 3;' in drv, "A not baseline F3")
                need("Done meshing 1D" in log and item["completed_1d"]
                     and item["native"]["native_exit_code"] == 0
                     and not item["native"]["stop_reason"],
                     "baseline completion not independently evidenced")
                result = "PASS_1D"
            else:
                marker = (b"Background Field = 6;" if i == 1
                          else b"Background Field = 7;")
                if i == 1:
                    need(b'Include "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo";' in drv,
                         "B missing P10GK source include")
                else:
                    need(b"Field[7] = MathEval;" in drv,
                         "C missing inline MathEval")
                # B inherits `Background Field = 6;` from included source,
                # not necessarily present verbatim in its driver.
                if i == 2:
                    need(marker in drv, "C background field not F7")
                need(not item["completed_1d"]
                     and "Done meshing 1D" not in log
                     and item["native"]["stop_reason"] == "WALL_LIMIT"
                     and 30 <= item["native"]["wall_s"] < 35,
                     case + " real bounded timeout not verified")
                need(item["mesh_sha256"] is None and item["mesh_size"] is None,
                     case + " unexpected mesh")
                result = "TIMEOUT_30S"
            summary.append({"case": case, "result": result,
                            "native_wall_s": item["native"]["wall_s"],
                            "native_exit_code": item["native"]["native_exit_code"],
                            "stop_reason": item["native"]["stop_reason"],
                            "peak_private_bytes_polled":item["native"]
                            ["peak_private_bytes_polled"],
                            "gmsh_1d_completed_log": "Done meshing 1D" in log,
                            "mesh_bytes_in_evidence": False})
    need(report["math"]["points"] == 10201
         and report["math"]["max_relative_expression_error"] == 0
         and report["math"]["local_factor_min"] == .94
         and report["math"]["local_factor_max"] == 1.,
         "math sample stats changed")
    return {
        "revision":"P10GM_R1_INDEPENDENT_REAL_WINDOWS_1D_AB_C_AUDIT",
        "input_evidence_sha256":ZIP_SHA,
        "zip_crc_pass":True,"zip_member_count":17,
        "all_included_geo_byte_pinned":True,
        "all_included_native_logs_sha_pinned":True,
        "cases":summary,
        "independent_verdict":"A_F3_PASS_B_F6_TIMEOUT_C_F7_TIMEOUT_FIELD_EVALUATION_SUSPECT",
        "causal_finding":"New composed south-pole MathEval field path triggers reproducible 1D stall; exact subexpression/root cause UNKNOWN",
        "limitation":"A mesh SHA appears in manifest but raw 1D MSH is not included; completion verified via native log; no independent 1D element audit",
        "previous_P10GL_one_shot":"CONSUMED_NEVER_REPEAT",
        "native_2d_attempts_in_provided_evidence":0,
        "native_3d_attempts_in_provided_evidence":0,
        "FEM_attempts_in_provided_evidence":0,
        "M1_geometry_GO":False,"FEM_GO":False,
        "proposed_next_isolated_1d":"Field[7].F = F3 alone (no southern factor), then simple scaling or lower-bound control in a new separately authorized bounded diagnostic",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = p.parse_args()
    result = audit(args.zip)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("P10GM_REAL_WINDOWS_INDEPENDENT_AUDIT_PASS", result["independent_verdict"])
    for item in result["cases"]:
        print(item["case"], item["result"],
              f"wall={item['native_wall_s']:.3f}s", "stop="+item["stop_reason"])
    print("NO 3D NO FEM; no M1 GO")


if __name__ == "__main__":
    main()
