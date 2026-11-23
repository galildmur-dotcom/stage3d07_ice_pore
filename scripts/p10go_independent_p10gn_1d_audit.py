#!/usr/bin/env python3
"""Read-only independent audit of real P10GN Gmsh -1 D/E evidence.

No Gmsh, no meshing, no FEM. Raw original evidence stays off GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "upload/P10GN_1D_PROBE_EVIDENCE.zip"
OUT = (ROOT / "research/evidence/P10GN_1D_20261123/derived/"
       "P10GN_R1_REAL_1D_INDEPENDENT_VERDICT.json")
ZIP_PIN = "fe5f13d04fafbef13e001f9a3371e2ae6addd93c936dc405b95a3b2cd7b7b481"
M0_PIN = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
P10GK_PIN = "4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05"
GMSH_PIN = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
FROZEN_PIN = "2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea"
CASES = ("D_F3_REFERENCE", "E_F3_TIMES_094")
GEO_PIN = {
    "M0_ROTATED.geo":"21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a",
    "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo":"1590d5f5fda58f4401cb038d898e49466e461a40a53fe692867d943b908508ba",
    "sphere_pore_B6_refined_rotated.geo":"e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329",
}


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise RuntimeError("P10GN_INDEPENDENT_AUDIT_STOP: " + message)


def audit(path: Path):
    need(path.is_file() and sha(path.read_bytes()) == ZIP_PIN,
         "input evidence not byte-identical")
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None, "bad ZIP CRC")
        names = set(z.namelist())
        expected = {"P10GN_MANIFEST.json", "P10GN_PROGRESS.json"}
        for case in CASES:
            expected.update(f"{case}/{name}" for name in
                (*GEO_PIN, "P10GN_1D.geo", "P10GN_GMSH_1D.log"))
        need(names == expected and len(names) == 12,
             "unexpected members: missing case, F incorrectly run or archive changed")
        report = json.loads(z.read("P10GN_MANIFEST.json"))
        progress = json.loads(z.read("P10GN_PROGRESS.json"))
        need(report["revision"] == "P10GN_R1_NATIVE_1D_F3_REFERENCE_ISOLATION_NO_3D_NO_FEM"
             and report["status"] == "DIAG_REFERENCE_STOP_FLOOR_NOT_ATTEMPTED_NO_3D"
             and report["P10GK_source_sha256"] == P10GK_PIN
             and report["M0_sha256"] == M0_PIN
             and report["frozen_D027_sha256"] == FROZEN_PIN
             and report["installed"]["Gmsh_sha256"] == GMSH_PIN
             and report["installed"]["gmsh_version"] == "4.15.2"
             and report["installed"]["M0_msh_sha256"] == M0_PIN,
             "source/protocol/installed SHA/status mismatch")
        need(report["F_size_floor_conditional"] == "ONLY_IF_D_AND_E_PASS"
             and report["native_2d_attempts"] == 0
             and report["native_3d_attempts"] == 0
             and report["FEM_attempts"] == 0,
             "new 2D/3D/FEM or forbidden floor case")
        need(progress["cases"] == report["cases"]
             and progress["status"] == "STOP_INCOMPLETE_1D_DIAGNOSTIC",
             "progress and final manifest inconsistent")
        need(len(report["cases"]) == 2
             and [r["case"] for r in report["cases"]] == list(CASES),
             "wrong case order/quantity")
        cases = []
        for idx,case in enumerate(CASES):
            item=report["cases"][idx]
            for name, expected_sha in GEO_PIN.items():
                need(sha(z.read(f"{case}/{name}")) == expected_sha,
                     case + " source GEO mismatch: " + name)
            drv=z.read(f"{case}/P10GN_1D.geo")
            lograw=z.read(f"{case}/P10GN_GMSH_1D.log")
            log=lograw.decode("utf-8", errors="replace")
            need(sha(drv)==item["geo_sha256"]
                 and sha(lograw)==item["log_sha256"]
                 and len(lograw)==item["log_size"],
                 case + " native log/driver SHA mismatch")
            exp=(b'Field[7].F = "F3";' if idx==0
                 else b'Field[7].F = "F3*0.94";')
            need(exp in drv
                 and b'Include "M0_ROTATED.geo";' in drv
                 and b'Background Field = 7;' in drv
                 and b'Mesh.MeshSizeFactor = 0.9378887276834518;' in drv
                 and b'Mesh.MeshSizeMin' not in drv,
                 case + " not the intended isolated F3 reference test")
            need("[Gmsh 4.15.2" in log
                 and "-1 -nopopup -nt 2 -format msh2" in log
                 and "Meshing 1D..." in log
                 and "Meshing curve 14 (Circle)" in log
                 and "Meshing curve 17 (Circle)" in log
                 and "Done meshing 1D" not in log
                 and "Meshing 2D" not in log and "Meshing 3D" not in log,
                 case + " native -1 stall evidence not present")
            native=item["native"]
            need(not item["completed_1d"]
                 and native["native_exit_code"]==1
                 and native["stop_reason"]=="WALL_LIMIT"
                 and 30<=native["wall_s"]<35
                 and 0<native["peak_private_bytes_polled"]<8*1024**3
                 and item["mesh_size"] is None
                 and item["mesh_sha256"] is None,
                 case + " timeout/resource evidence mismatch")
            cases.append({"case":case,"result":"TIMEOUT_30S",
                          "native_wall_s":native["wall_s"],
                          "stop_reason":native["stop_reason"],
                          "native_exit_code":native["native_exit_code"],
                          "peak_private_bytes":native["peak_private_bytes_polled"],
                          "last_native_phase":"Meshing 1D curves 14/17",
                          "original_log_sha256":item["log_sha256"],
                          "original_driver_sha256":item["geo_sha256"]})
        need(report["math"]["points"]==10201
             and report["math"]["max_relative_expression_error"]==0.
             and report["math"]["local_factor_min"]==.94
             and report["math"]["local_factor_max"]==1.,
             "source math QA changed")
    return {
        "revision":"P10GN_R1_INDEPENDENT_REAL_WINDOWS_1D_D_E_VERDICT",
        "original_evidence_sha256":ZIP_PIN,
        "original_zip_crc_pass":True,"zip_member_count":12,
        "source_geos_byte_pinned":True,
        "log_and_driver_hashes_independent_pass":True,
        "cases":cases,
        "F_conditional_floor_test":"NOT_RUN_EXPECTED_D_E_FAILED",
        "conclusion":"DIRECT_F3_BACKGROUND_PREVIOUSLY_FAST_BUT_F3_REFERENCE_ONLY_1D_TIMEOUT",
        "scope":"reproducible operational behavior on this pinned Gmsh4.15.2 model; Gmsh internal mechanism UNKNOWN",
        "no_native_2d_3d_or_FEM_evidenced":True,
        "previous_P10GL_and_P10GM_and_current_P10GN_one_shots":"CONSUMED_NO_RETRY",
        "M1_GO":False,"FEM_GO":False,
        "next_source_only_candidate":"construct a single self-contained MathEval sizing expression with complete original M0 F3 formula inlined and south C1 factor; no F3/F4/F5 references; independent field QA before any new -1",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--zip",type=Path,default=ZIP)
    ap.add_argument("--out",type=Path,default=OUT)
    args=ap.parse_args()
    result=audit(args.zip)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print("P10GN_REAL_WINDOWS_INDEPENDENT_D_E_TIMEOUT_PASS")
    for case in result["cases"]:
        print(case["case"],case["result"],case["native_wall_s"])
    print("F_NOT_RUN, M1_STOP, FEM=0")


if __name__=="__main__":
    main()
