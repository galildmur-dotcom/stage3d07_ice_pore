#!/usr/bin/env python3
"""Read-only independent verification of one P10DE Windows M1 mesh-only STOP.

Checks primary ZIP, executed source pin, exact historic H0, QA counts and
radial-mu closure, and contrasts mistakenly used H3 size source. Does NOT
have original .msh and therefore cannot re-evaluate its curved Jacobians.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
H3_CSV = ROOT / "experiments/P10AU_EXPANDED_SPATIOTEMPORAL_20261116/input/P10AR_GEOMETRY_H0_H4.csv"
BUNDLE = ROOT / "research/packages/P10DE_R1_M1_GRADED_MESH_ONLY_WINDOWS_20261121.zip"
EXPECTED_BUNDLE_SHA = "409c2406a6a9b5d1625f26d476718a962c466be7bdc79768603d48c3c5b8bd3a"


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("P10DE_INDEPENDENT_STOP: " + why)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_rows(b: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))


def close(a: float, b: float, msg: str, atol: float = 1e-10) -> float:
    diff = abs(a - b)
    require(diff <= atol, f"{msg} diff={diff} actual={a} expected={b}")
    return diff


def weighted_median_of_bin_medians(rows: list[dict], key: str) -> float | None:
    pairs = sorted((float(r[key]), int(r["tet10"])) for r in rows
                   if r[key] and int(r["tet10"]) > 0)
    if not pairs:
        return None
    n = sum(w for _, w in pairs)
    acc = 0
    for val, count in pairs:
        acc += count
        if acc >= n / 2:
            return val
    return pairs[-1][0]


def audit(evidence: Path) -> tuple[dict, list[dict]]:
    require(evidence.is_file(), "missing original ZIP")
    expected = {
        "P10DE_GMSH_LOG_TAIL.txt", "P10DE_QA_STDOUT_STDERR.txt",
        "P10DE_RESULT.txt", "P10DE_RUN_MANIFEST.json", "P10DE_STOP_TRACE.txt",
        "QA/P10DE_M0_M1_MESH_QA.json",
        "QA/P10DE_M0_M1_RADIAL_MU_BINS.csv",
    }
    with zipfile.ZipFile(evidence) as z:
        require(z.testzip() is None and set(z.namelist()) == expected, "ZIP CRC/file set")
        manifest = json.loads(z.read("P10DE_RUN_MANIFEST.json"))
        qa = json.loads(z.read("QA/P10DE_M0_M1_MESH_QA.json"))
        rows = as_rows(z.read("QA/P10DE_M0_M1_RADIAL_MU_BINS.csv"))
        result = z.read("P10DE_RESULT.txt").decode("utf-8-sig")
        stdout = z.read("P10DE_QA_STDOUT_STDERR.txt").decode("utf-8-sig")
        log = z.read("P10DE_GMSH_LOG_TAIL.txt").decode("utf-8-sig")

    require(digest(BUNDLE) == EXPECTED_BUNDLE_SHA, "not exact published P10DE launcher")
    with zipfile.ZipFile(BUNDLE) as z:
        pinned = json.loads(z.read("P10DE_PINNED_SHA256.json"))
    require(manifest["package_sources_sha256"] == pinned["files"],
            "executed code provenance differs from published source")
    require(manifest["protocol"] == "P10DE_R1_M1_GRADED_20PCT_VOLUME_MESH_ONLY",
            "wrong mesh-only protocol")
    require(manifest["status"] == "P10DE_STOP_NO_FEM" and
            manifest["FEM_runs"] == 0 and manifest["Gmsh_max_attempts"] == 1,
            "not genuine mesh-only STOP")
    require("RESULT=P10DE_STOP_NO_FEM" in result and
            "WINDOWS_NATIVE_GMSH_EXIT=0" in result and
            "M1 or H0 curved 27QP/structure QA failed" in result,
            "STOP result inconsistent")
    require(manifest["native_exit_code"] == 0 and manifest["qa_exit_code"] == 2 and
            manifest["m1_mesh_size_bytes"] > 0 and
            manifest["wall_seconds"] < 900 and
            manifest["peak_private_bytes_polled"] < 8 * 1024**3,
            "run resource/native result mismatch")
    require(re.fullmatch("[0-9a-f]{64}", manifest["m1_mesh_sha256"]),
            "missing M1 mesh SHA")
    require(qa["m1_sha256"] == manifest["m1_mesh_sha256"] and
            qa["h0_sha256"] == manifest["h0_sha256"] == H0_SHA,
            "mesh identity mismatch")
    require(qa["status"] == "GEOMETRY_QA_STOP" and
            not qa["h0_issues"] and not qa["m1_issues"] and
            len(qa["mesh_target_issues"]) == 1 and
            "median" in qa["mesh_target_issues"][0],
            "STOP must be M1 size target failure only")
    require(qa["h0"]["tet10"] == 7388 and qa["h0"]["pore_tri6"] == 136,
            "not historical H0")
    require(qa["h0"]["corner_negative"] == qa["m1"]["corner_negative"] == 0 and
            qa["h0"]["curved_qp_negative"] == qa["m1"]["curved_qp_negative"] == 0,
            "invalid curved QP geometry reported")
    for name in ("h0", "m1"):
        obj = qa[name]
        require(obj["curved_qp_count"] == obj["tet10"] * 27 and
                obj["curved_qp_det_min"] > 0 and
                abs(obj["curved_volume_relative_CAD_error"]) < .005 and
                obj["global_min_corner_quality"] > .02 and
                obj["wall_node_max_radial_deviation_m"] < 1e-8,
                "curved geometry/QP contract " + name)
    close(qa["h0"]["curved_volume_sum_m3"], .00017999581513869134,
          "H0 27QP volume vs previous independent P10DD", 1e-12)
    close(qa["element_ratio_M1_over_H0"],
          qa["m1"]["tet10"] / qa["h0"]["tet10"], "Tet count ratio")
    vratio = qa["m1"]["global_median_corner_volume_m3"] / qa["h0"]["global_median_corner_volume_m3"]
    close(qa["median_corner_volume_ratio_M1_over_H0"], vratio, "global median volume ratio")
    require(vratio < .01 and qa["m1"]["tet10"] > 10 * qa["h0"]["tet10"],
            "failure must be large over-refinement")
    require("P10DE_M1_QA_STOP_NO_FEM" in stdout and
            str(qa["m1"]["tet10"]) in stdout and
            "139218 nodes 108061 elements" in log,
            "Qt/Gmsh/QA log inconsistent")

    bands = ("0_20um", "20_100um", "100_500um", "0p5_1p5mm",
             "1p5_5mm", "5_18mm", "18mm_plus")
    require(len(rows) == 140, "expected 2 meshes x7 radial x10 mu")
    got = set()
    for row in rows:
        key = (row["mesh"], row["radial_band"], int(row["mu_bin"]))
        require(key not in got and key[0] in ("H0", "M1") and
                key[1] in bands and 0 <= key[2] < 10, "duplicate/invalid bin")
        got.add(key)
        require(int(row["tet10"]) >= 0, "negative cell count")
        if int(row["tet10"]):
            require(float(row["median_corner_volume_m3"]) > 0 and
                    float(row["median_hmax_mm"]) > 0 and
                    float(row["min_corner_quality"]) > 0,
                    "nonfinite/nonpositive representative bin geometry")
    require(len(got) == 140, "missing radial-mu bins")
    for mesh, key in (("H0", "h0"), ("M1", "m1")):
        require(sum(int(r["tet10"]) for r in rows if r["mesh"] == mesh) == qa[key]["tet10"],
                "radial-mu count closure " + mesh)
    require("nearSize(H3)=0.000190" in
            (ROOT / "gmsh/GENERATE_H3_H4_RU.md").read_text(encoding="utf-8"),
            "H3 source provenance missing")
    h3 = next(r for r in as_rows(H3_CSV.read_bytes()) if r["label"] == "H3")
    h3_tets = int(h3["tet10"])
    h3_tri = int(h3["pore_tri6"])
    require(h3_tets == 81891 and h3_tri == 866, "historic H3 counts mismatch")

    radial = []
    for band in bands:
        h0_rows = [r for r in rows if r["mesh"] == "H0" and r["radial_band"] == band]
        m1_rows = [r for r in rows if r["mesh"] == "M1" and r["radial_band"] == band]
        h0_h = weighted_median_of_bin_medians(h0_rows, "median_hmax_mm")
        m1_h = weighted_median_of_bin_medians(m1_rows, "median_hmax_mm")
        h0_v = weighted_median_of_bin_medians(h0_rows, "median_corner_volume_m3")
        m1_v = weighted_median_of_bin_medians(m1_rows, "median_corner_volume_m3")
        radial.append({
            "radial_band": band,
            "h0_tet10": sum(int(r["tet10"]) for r in h0_rows),
            "m1_tet10": sum(int(r["tet10"]) for r in m1_rows),
            "h0_hmax_binmedian_mm": h0_h, "m1_hmax_binmedian_mm": m1_h,
            "hmax_ratio": m1_h / h0_h if h0_h and m1_h else None,
            "volume_ratio": m1_v / h0_v if h0_v and m1_v else None,
        })
    summary = {
        "evidence_sha256": digest(evidence),
        "status": "WINDOWS_GMSH_NATIVE_EXIT0_BUT_M1_OVERREFINED_QA_STOP_NO_FEM",
        "m1_msh_sha256_windows_manifest_unverified": manifest["m1_mesh_sha256"],
        "windows_gmsh_exe_sha256_manifest_unverified": manifest["gmsh_sha256"],
        "m1_msh_bytes_windows_manifest": manifest["m1_mesh_size_bytes"],
        "gmsh_wall_s": manifest["wall_seconds"],
        "gmsh_peak_private_gib": manifest["peak_private_bytes_polled"] / 1024**3,
        "h0": qa["h0"], "m1": qa["m1"],
        "m1_tet10_over_h0": qa["element_ratio_M1_over_H0"],
        "m1_median_tet_volume_over_h0": vratio,
        "m1_tet10_over_h3": qa["m1"]["tet10"] / h3_tets,
        "h3_tet10_20pct_volume_proxy": h3_tets / .8,
        "m1_vs_h3_20pct_tetcount_proxy_rel": qa["m1"]["tet10"] / (h3_tets / .8) - 1.,
        "historical_h3_tet10": h3_tets,
        "historical_h3_pore_tri6": h3_tri,
        "qa_mesh_target_issues": qa["mesh_target_issues"],
        "limits": (
            "No original H0/M1 .msh in evidence; QP Jacobians, M1 SHA, "
            "Gmsh EXE SHA are reported by Windows QA/manifest, not independently "
            "recomputed. Radial weighted bin medians are NOT element medians. "
            "H3 size-field attribution follows published GEO provenance, "
            "not an attested original H0 mesher command."),
        "next": "STOP; do not rerun Gmsh or launch M1 FEM without fresh authorization",
    }
    return summary, radial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    opts = parser.parse_args()
    result, radial = audit(opts.evidence)
    if opts.out:
        opts.out.mkdir(parents=True, exist_ok=True)
        (opts.out / "P10DE_INDEPENDENT_STOP_AUDIT.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with (opts.out / "P10DE_H0_M1_RADIAL_COMPARISON.csv").open(
                "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=radial[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(radial)
    print("P10DE_INDEPENDENT_OVERREFINEMENT_STOP_CONFIRMED", json.dumps({
        k: v for k, v in result.items() if k not in ("h0", "m1")
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
