#!/usr/bin/env python3
"""P10DS read-only evidence/source audit; never starts Gmsh, 1D, 2D, 3D, or FEM."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
P10DR_SOURCE = ROOT / "research/packages/P10DR_R1_F3_F4_1D_ISOLATION_WINDOWS_20261121.zip"
SOURCE_SHA = "4ed2a21c64480996b88d7c1f465fc884b3a175f659e424d2039c413ca420a011"
EVIDENCE_SHA = "72e06f67338ab5f2b5f25080ac89e41c9026011b3aaedc0e2f155f0fb7eb1b7f"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
NAMES = (
    "A_FIELD2_REFERENCE", "B_F3_RAW_REFERENCE", "C_F4_RAW_REFERENCE",
    "D_F3_F4_RAW_PRODUCT", "E_F3_RADIAL_SMOOTHSTEP",
    "F_F4_ANGULAR_SMOOTHSTEP", "G_F3_F4_INLINE_SMOOTHSTEP",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, why: str) -> None:
    if not condition:
        raise ValueError("P10DS_AUDIT_STOP: " + why)


def normalise_cr(data: bytes) -> str:
    # Gmsh emits CRLF; P10DR Windows Python read/write of tails can add CRCRLF.
    return (data.decode("utf-8", errors="replace").replace("\r\r\n", "\n")
            .replace("\r\n", "\n"))


def audit(evidence_path: Path) -> dict:
    require(digest(evidence_path.read_bytes()) == EVIDENCE_SHA, "original Windows ZIP SHA")
    require(digest(P10DR_SOURCE.read_bytes()) == SOURCE_SHA, "original released P10DR ZIP SHA")
    with tempfile.TemporaryDirectory(prefix="p10ds_readonly_release_") as tmp, \
            zipfile.ZipFile(evidence_path) as evidence, zipfile.ZipFile(P10DR_SOURCE) as release:
        require(evidence.testzip() is None and release.testzip() is None, "ZIP CRC")
        names = evidence.namelist()
        require(len(names) == 24 and len(set(names)) == 24, "evidence ZIP inventory")
        for name in names:
            p = PurePosixPath(name)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in name,
                    "unsafe evidence member")
        require(len(release.namelist()) == 8, "released ZIP inventory")
        pinned = json.loads(release.read("P10DR_SOURCE_SHA256.json"))
        require(len(pinned["files"]) == 7, "released source inventory")
        for name, expected in pinned["files"].items():
            require(digest(release.read(name)) == expected, "released source SHA " + name)
        # Execute only *verified* released Python to reproduce the exact GEO
        # construction; no run mode or any native dependency is invoked.
        release.extractall(tmp)
        sys.path.insert(0, tmp)
        try:
            spec = importlib.util.spec_from_file_location("p10ds_verified_release",
                                                      Path(tmp) / "P10DR_one_click_1d.py")
            require(spec is not None and spec.loader is not None, "release import loader")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            require(len(module.source_gate()["files"]) == 7, "released source gate")
            geo = module.geo_variants()
        finally:
            sys.path.remove(tmp)

        manifest = json.loads(evidence.read("P10DR_RUN_MANIFEST.json"))
        result = evidence.read("P10DR_RESULT.txt").decode("utf-8")
        require(manifest["protocol"] == "P10DR_R1_F3_F4_1D_ONLY_NO_FEM" and
                manifest["status"] == "P10DR_DIAGNOSTIC_FINISHED_WITH_1D_STOPS_NO_FEM" and
                "RESULT=P10DR_DIAGNOSTIC_FINISHED_WITH_1D_STOPS_NO_FEM" in result,
                "run status")
        require(manifest["accepted_original_m1_sha256"] == M1_SHA and
                manifest["gmsh_sha256"] == GMSH_SHA and
                manifest["gmsh_version"] == "4.15.2", "M1/Gmsh identity in manifest")
        require(manifest["source_pin_count"] == 7 and
                all(manifest[key] == 0 for key in
                    ("mesh_2d_runs", "mesh_3d_runs", "physical_FEM_runs")),
                "source count / no 2D-3D-FEM")
        require(manifest["one_shot_sequence_limit"] == 1 and
                manifest["max_1d_variants"] == 7 and
                manifest["per_variant_wall_s"] == 15 and
                manifest["max_private_bytes"] == 2*1024**3,
                "diagnostic limits")
        require(list(manifest["native_parse_exits"]) == list(NAMES) and
                all(v == 0 for v in manifest["native_parse_exits"].values()),
                "seven native GEO syntax parses")
        require(evidence.read("GEO/sphere_pore_B6_refined.geo") ==
                release.read("sphere_pore_B6_refined.geo"), "CAD modified")
        for name in NAMES:
            raw = evidence.read("GEO/" + name + ".geo")
            require(raw == geo[name].replace("\n", "\r\n").encode("utf-8") and
                    digest(raw) == manifest["geo_sha256"][name],
                    "derived GEO mismatch " + name)
        runs = manifest["variants"]
        require([r["name"] for r in runs] == list(NAMES), "1D run order/completeness")
        table = []
        for i, run in enumerate(runs):
            name = run["name"]
            require("-1" in run["argv"] and "-2" not in run["argv"] and
                    "-3" not in run["argv"] and "-nt" in run["argv"],
                    "native mode " + name)
            log = normalise_cr(evidence.read(name + ".log"))
            tail = normalise_cr(evidence.read(name + "_TAIL.txt"))
            require(log == tail and "Meshing 1D..." in log and
                    "Meshing 2D..." not in log and "Meshing 3D..." not in log and
                    re.search(r"(?im)^\s*Error\s*:", log) is None,
                    "full native log / tail / no downstream mesh " + name)
            if i == 0:
                require(run["status"] == "PASS" and run["native_exit"] == 0 and
                        run["reported_nodes_elements"] == [244, 135] and
                        run["mesh_bytes"] == 280 and
                        "244 nodes 135 elements" in log and
                        "Done writing" in log and run["wall_s"] < 1,
                        "reference A is not the observed completed Gmsh1D")
            else:
                require(run["status"] == "TIMEOUT_15S" and
                        run["native_exit"] == 1 and
                        run["reported_nodes_elements"] is None and
                        run["mesh_bytes"] == 0 and 15 <= run["wall_s"] < 16 and
                        "Meshing curve 14 (Circle)" in log and
                        "Meshing curve 17 (Circle)" in log,
                        "bounded observed 1D timeout " + name)
            require(run["peak_private_polled"] < 2*1024**3,
                    "private-memory limit broken " + name)
            table.append({k: run[k] for k in
                          ("name", "status", "native_exit", "wall_s",
                           "peak_private_polled", "mesh_bytes", "log_bytes")})
        require("B_F3_RAW_REFERENCE" in manifest["stop_reason"] and
                "G_F3_F4_INLINE_SMOOTHSTEP" in manifest["stop_reason"] and
                "FEM_RUNS=0" in result, "stopped-variant manifest consistency")
        return {
            "status": "P10DS_ORIGINAL_P10DR_GMSH_LOG_SOURCE_AUDIT_PASS",
            "original_windows_evidence_sha256": EVIDENCE_SHA,
            "original_p10dr_source_zip_sha256": SOURCE_SHA,
            "evidence_crc": "24/24", "pinned_sources": "7/7",
            "geo_exact_with_native_crlf": "7/7", "gmsh_parse_only_pass": "7/7",
            "gmsh_exe_sha256_from_windows_manifest_not_independent_exe": GMSH_SHA,
            "m1_sha256_from_windows_manifest_not_raw_mesh": M1_SHA,
            "native_1d_runs": table,
            "sum_native_wall_s": sum(r["wall_s"] for r in runs),
            "max_peak_private_bytes": max(r["peak_private_polled"] for r in runs),
            "last_1d_entity_for_all_stops": "circle curves 14 and 17",
            "mesh_2d_runs": 0, "mesh_3d_runs": 0, "physical_FEM_runs": 0,
            "scientific_observation": "Both F3-only and F4-only MathEval references stop at native 1D, whereas F2 itself completes; a smoothstep product, F5, and exp/log are not necessary conditions for the stop.",
            "root_cause": "UNKNOWN: cannot distinguish nested field evaluation from expression/min-max runtime behavior or meshing iteration using the existing logs.",
            "software_limit": "The documented Gmsh4.15.2 mesh.field API exposes field definitions but does not document point-value evaluation; -v/-log/-cpu add diagnostics, not a direct field-sampling API.",
            "next_action": "No blind rerun. Only if separately authorized: a new minimal bounded 1D contrast of constant nested MathEval versus direct inline spatial MathEval; no 2D/3D/FEM.",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    options = parser.parse_args()
    result = audit(options.evidence)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(result["status"], "CRC24/24 GEO7/7 F3_STOP=1 F4_STOP=1 FEM=0 GMSH=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
