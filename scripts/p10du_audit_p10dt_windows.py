#!/usr/bin/env python3
"""Read-only P10DU audit of original P10DT Windows Gmsh 1D ZIP; NO native mesh/FEM."""
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
RELEASE = ROOT / "research/packages/P10DT_R1_THREE_1D_CONTRAST_WINDOWS_20261121.zip"
RELEASE_SHA = "f540adb8f7e9dc4a58fea8ebe5784c99fe4f2607cb6b82cf5ac65dd398b1eb08"
EVIDENCE_SHA = "9c4602ac29a08dd8faa5e977990a3f138f73a39c242dcc3167b09f23bf46d414"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
P10DR_SHA = "72e06f67338ab5f2b5f25080ac89e41c9026011b3aaedc0e2f155f0fb7eb1b7f"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
NAMES = ("A_DIRECT_CONSTANT_F6", "B_NESTED_CONSTANT_F3", "C_DIRECT_SPATIAL_CLAMP_F6")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def require(condition: bool, why: str) -> None:
    if not condition:
        raise ValueError("P10DU_AUDIT_STOP: " + why)


def unix_newlines(content: bytes) -> str:
    # Windows Gmsh stdout contains CRLF; Python's Windows text output can duplicate CR.
    return (content.decode("utf-8", errors="replace")
            .replace("\r\r\n", "\n").replace("\r\n", "\n"))


def expected_names() -> set[str]:
    return ({"P10DT_RUN_MANIFEST.json", "P10DT_RESULT.txt", "GEO/sphere_pore_B6_refined.geo"}
            | {"GEO/"+n+".geo" for n in NAMES}
            | {n+".log" for n in NAMES}
            | {n+"_TAIL.txt" for n in NAMES})


def audit(original: Path, *, verify_outer_sha: bool = True,
          release: Path = RELEASE) -> dict:
    require(original.is_file(), "Windows evidence ZIP missing")
    require(not verify_outer_sha or digest(original.read_bytes()) == EVIDENCE_SHA,
            "original Windows ZIP SHA changed")
    require(digest(release.read_bytes()) == RELEASE_SHA, "pinned release ZIP SHA changed")
    with tempfile.TemporaryDirectory(prefix="p10du_readonly_verified_source_") as tmp, \
            zipfile.ZipFile(original) as evidence, zipfile.ZipFile(release) as released:
        require(evidence.testzip() is None and released.testzip() is None, "ZIP CRC failed")
        names = evidence.namelist()
        require(len(names) == 12 and set(names) == expected_names(), "evidence 12-member inventory")
        for member in evidence.infolist():
            p = PurePosixPath(member.filename)
            require(not p.is_absolute() and ".." not in p.parts and
                    "\\" not in member.filename and member.file_size < 100000,
                    "unsafe or oversized ZIP member")
        require(len(released.namelist()) == 9, "release inventory")
        pinned = json.loads(released.read("P10DT_SOURCE_SHA256.json"))
        require(pinned["revision"] == "P10DT_R1_THREE_INDEPENDENT_1D_CONTRASTS_NO_FEM" and
                pinned["physical_FEM"] is False and pinned["mesh_2d_3d"] is False and
                pinned["diagnostic_sequence_limit"] == 1 and
                pinned["max_native_1d_variants"] == 3 and
                pinned["accepted_m1_sha256"] == M1_SHA and
                pinned["p10dr_evidence_zip_sha256"] == P10DR_SHA and
                len(pinned["files"]) == 8, "release protocol/M1/old evidence pin")
        for name, expected in pinned["files"].items():
            require(digest(released.read(name)) == expected, "release source SHA: " + name)
        released.extractall(tmp)
        sys.path.insert(0, tmp)
        try:
            spec = importlib.util.spec_from_file_location(
                "p10du_verified_p10dt_release", Path(tmp)/"P10DT_one_click_1d.py")
            require(spec is not None and spec.loader is not None, "safe released code loader")
            driver = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(driver)
            require(len(driver.source_gate()["files"]) == 8 and
                    len(driver.formula_unit()["six_original_F3_sample_points"]) == 6,
                    "released source/formula gate")
            generated = driver.contrast_geo()
        finally:
            sys.path.remove(tmp)
        require(list(generated) == list(NAMES), "variant source order")
        for name, geo in generated.items():
            raw = evidence.read("GEO/"+name+".geo")
            require(unix_newlines(raw) == geo.replace("\r\n", "\n") and
                    digest(raw) == json.loads(evidence.read("P10DT_RUN_MANIFEST.json"))
                    ["geo_sha256"][name], "original Windows generated GEO bytes: " + name)
        require(evidence.read("GEO/sphere_pore_B6_refined.geo") ==
                released.read("sphere_pore_B6_refined.geo"), "CAD byte identity")

        manifest = json.loads(evidence.read("P10DT_RUN_MANIFEST.json"))
        result = unix_newlines(evidence.read("P10DT_RESULT.txt"))
        require(manifest["protocol"] == pinned["revision"] and
                manifest["status"] == "P10DT_ALL_THREE_FINISHED_WITH_1D_STOPS_NO_FEM" and
                "RESULT=P10DT_ALL_THREE_FINISHED_WITH_1D_STOPS_NO_FEM" in result and
                "STOP_REASON=Nonpassing 1D contrasts: B_NESTED_CONSTANT_F3" in result and
                manifest["stop_reason"] == "Nonpassing 1D contrasts: B_NESTED_CONSTANT_F3",
                "evidence result/status")
        require(manifest["accepted_original_m1_sha256"] == M1_SHA and
                manifest["p10dr_evidence_sha256"] == P10DR_SHA and
                manifest["native_gmsh_sha256"] == GMSH_SHA and
                manifest["native_gmsh_version"] == "4.15.2" and
                manifest["source_pin_count"] == 8 and
                manifest["one_shot_sequence_limit"] == 1 and
                manifest["max_1d_variants"] == 3 and
                manifest["per_variant_wall_s"] == 15 and
                manifest["max_private_bytes"] == 2*1024**3 and
                manifest["free_RAM_bytes"] >= 8*1024**3 and
                manifest["free_disk_bytes"] >= 1024**3 and
                list(manifest["native_parse_exits"]) == list(NAMES) and
                all(v == 0 for v in manifest["native_parse_exits"].values()) and
                all(manifest[k] == 0 for k in
                    ("mesh_2d_runs", "mesh_3d_runs", "physical_FEM_runs")) and
                "FEM_RUNS=0" in result and "M2_2D_3D_MESH_RUNS=0" in result,
                "Windows preflight/Gmsh/M1/limits/no-FEM metadata")
        require(manifest["formula_samples"] == driver.formula_unit(),
                "six formula points and field envelopes")
        require(len(manifest["variants"]) == 3 and
                [r["name"] for r in manifest["variants"]] == list(NAMES),
                "three independent variant order")
        require(all(r["argv"][0] == manifest["native_gmsh"] and
                    r["argv"][2:8] == ["-1", "-nt", "2", "-format", "msh2", "-o"] and
                    r["argv"][1].endswith("\\GEO\\"+r["name"]+".geo") and
                    r["argv"][-1].endswith("\\"+r["name"]+".msh")
                    for r in manifest["variants"]), "one-dimensional native argv")
        expected_statuses = ("PASS", "TIMEOUT_15S", "PASS")
        expected_exit = (0, 1, 0)
        rows = []
        for i, run in enumerate(manifest["variants"]):
            name = NAMES[i]
            raw = evidence.read(name+".log")
            log, tail = unix_newlines(raw), unix_newlines(evidence.read(name+"_TAIL.txt"))
            require(run["log_bytes"] == len(raw) and tail == log[-6500:],
                    "full native Gmsh stdout log vs source-created tail: " + name)
            require("Meshing 1D..." in log and "Gmsh 4.15.2" in log and
                    "Meshing 2D..." not in log and "Meshing 3D..." not in log and
                    not re.search(r"(?im)^\s*Error\s*:", log),
                    "native log stage/error: " + name)
            require(run["status"] == expected_statuses[i] and
                    run["native_exit"] == expected_exit[i] and
                    run["peak_private_polled"] < 2*1024**3 and
                    run["wall_s"] <= 15.5 and
                    run["mesh_bytes"] <= 20*1024**2 and
                    run["log_bytes"] <= 1024**2,
                    "1D variant status/exit/limits: " + name)
            counts = re.findall(r"\b(\d+) nodes (\d+) elements\b", log)
            if i != 1:
                require(run["mesh_bytes"] == 280 and run["mesh_sha256"] ==
                        "04325caf637624c98cc5e18415556c937635e3102d1bb2ad79dbd72e2fd42511" and
                        run["wall_s"] < 2 and "Done meshing 1D" in log and
                        tuple(map(int, counts[-1])) == tuple(run["reported_nodes_elements"]) ==
                        (244, 135), "native 1D fast-complete markers: " + name)
            else:
                require(15 <= run["wall_s"] <= 15.5 and run["mesh_bytes"] == 0 and
                        run["mesh_sha256"] is None and run["reported_nodes_elements"] is None and
                        "Meshing curve 14 (Circle)" in log and
                        "Meshing curve 17 (Circle)" in log and
                        "Done meshing 1D" not in log and not counts,
                        "nested-constant F3 timeout at curves14/17")
            rows.append({k: run[k] for k in
                         ("name", "status", "native_exit", "wall_s", "peak_private_polled",
                          "mesh_bytes", "mesh_sha256", "reported_nodes_elements", "log_bytes")})
        return {
            "status": "P10DU_ORIGINAL_P10DT_WINDOWS_NESTED_CONSTANT_STOP_AUDIT_PASS",
            "original_p10dt_evidence_sha256": EVIDENCE_SHA,
            "p10dt_released_source_zip_sha256": RELEASE_SHA,
            "evidence_zip_crc": "12/12", "source_sha": "8/8", "generated_geo_sha": "3/3",
            "full_native_log_tail_integrity": "3/3", "native_geo_parse_exits": "3/3",
            "genuine_gmsh_exe_sha256_only_from_windows_manifest": GMSH_SHA,
            "accepted_m1_sha256_only_from_windows_manifest": M1_SHA,
            "variants": rows, "sum_native_wall_s": sum(r["wall_s"] for r in rows),
            "max_peak_private_bytes": max(r["peak_private_polled"] for r in rows),
            "mesh_2d_runs": 0, "mesh_3d_runs": 0, "physical_FEM_runs": 0,
            "root_cause_from_evidence_alone": "The B-only nested MathEval F3 reference stalls although the A direct constant and C inline spatial clamp both finish; the logs alone cannot expose the internal cause.",
            "independent_gmsh4152_source_fact": {
                "official_readonly_mirror": "https://github.com/gmsh-project/gmsh/blob/gmsh_4_15_2/src/mesh/Field.cpp#L979-L1039",
                "reentrancy_code": "https://github.com/gmsh-project/gmsh/blob/gmsh_4_15_2/src/mesh/Field.cpp#L1141-L1175",
                "git_blob_sha": "427911696c813c5543caa37b527a985775fa6d4e",
                "finding": "MathEvalExpression::evaluate invokes referenced Field::operator() synchronously; MathEvalField::operator() wraps its entire expression evaluation in a named OpenMP critical(MathEvalField), and the source comment explicitly says this design is not reentrant and a MathEval field cannot reference another MathEval field.",
                "limitation": "Source was independently read for tag gmsh_4_15_2; the exact Windows executable build flags are known only indirectly through the user's exe SHA manifest, not an independent binary/source build attestation.",
            },
            "limits": "The fast 280-byte exported MSH2 files are not in the evidence; 244 nodes /135 elements come from native logs, not independently audited physical 1D mesh topology. Only one bounded original Windows P10DT sequence is observed.",
            "next_step": "P10DT one-shot CONSUMED: never rerun. Source-only mathematically flatten all nested MathEval field references in a candidate with the original C1 kappa and 0..20% target-volume envelope. Any new native Gmsh attempt requires explicit separate authorization; no M2 -2/-3/FEM now.",
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    result = audit(args.evidence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(result["status"], "CRC12/12 GEO3/3 LOG3/3",
          "A=PASS B=TIMEOUT_15S C=PASS FEM=0 GMSH_NOT_RERUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
