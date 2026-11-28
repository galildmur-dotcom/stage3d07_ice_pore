#!/usr/bin/env python3
"""Independent SHA/CRC and full-cell reconciliation of real P10CT R2 U0 evidence."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

EXPECTED_ZIP_SHA = "92c7a902c41d7ded08c2431c057c849f1463848deca14182d925545450766240"
EXPECTED_MESH_SHA = "1a4690d1c57c8b520d596f9a864f754a8d84151bfd1fdd36f56631488779c6a3"
EXPECTED_FILES = {
    "P10CT_R2_QA_STDERR.txt", "P10CT_R2_QA_STDOUT.txt", "P10CT_R2_RESULT.txt",
    "P10CT_R2_UNIT_STDERR.txt", "P10CT_R2_UNIT_STDOUT.txt",
    "QA/P10CT_U0_3D_SIZE_BINS.csv", "QA/P10CT_U0_SUMMARY.json",
}


def audit(source: Path):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_ZIP_SHA:
        raise ValueError("P10CT R2 original ZIP SHA mismatch")
    with zipfile.ZipFile(source) as z:
        if set(z.namelist()) != EXPECTED_FILES or z.testzip() is not None:
            raise ValueError("P10CT R2 archive members/CRC mismatch")
        read = lambda name: z.read(name).decode("utf-8-sig")
        result = read("P10CT_R2_RESULT.txt")
        fields = dict(line.split("=", 1) for line in result.splitlines() if "=" in line)
        summary = json.loads(read("QA/P10CT_U0_SUMMARY.json"))
        cells = list(csv.DictReader(io.StringIO(read("QA/P10CT_U0_3D_SIZE_BINS.csv"))))
        err = read("P10CT_R2_QA_STDERR.txt")

    required = {
        "result": fields.get("RESULT") == "P10CT_R2_READONLY_U0_QA_COMPLETE_NO_FEM",
        "source_SHA": fields.get("PINNED_SOURCE_SHA") == "PASS_3_OF_3",
        "mesh_SHA": fields.get("EXISTING_MESH_SHA") == "PASS" and summary.get("mesh_sha256") == EXPECTED_MESH_SHA,
        "no_mutation": all(fields.get(k) == "0" for k in ("GMSH_CALLS", "PHYSICAL_FEM_RUNS", "SOURCE_MESH_WRITES")),
        "unit_and_QA": fields.get("UNIT_EXIT") == "0" and fields.get("QA_EXIT") == "0",
        "full_curved_QP": summary["sampled_curved_tet10"] == summary["tet10"]
                          and summary["curved_27qp_samples"] == 27 * summary["tet10"],
        "no_nonpositive": summary["curved_qp_nonpositive_count"] == 0
                         and summary["corner_det_nonpositive_count"] == 0,
        "no_QA_trace": not err,
        "exact_rows": len(cells) == 600,
        "original_mesh_size": int(fields["EXPECTED_ORIGINAL_MESH_BYTES"]) == 16218389,
    }
    if not all(required.values()):
        raise ValueError("original R2 evidence invariants failed: " + repr(required))
    by_zone = Counter()
    for c in cells:
        by_zone[c["zone"]] += int(c["tet10_centroids"])
    for zone, info in summary["zone_profile"].items():
        if by_zone[zone] != info["tet10"]:
            raise ValueError("zone count mismatch: " + zone)
    if sum(by_zone.values()) != summary["tet10"]:
        raise ValueError("global Tet10 count mismatch")
    if sum(summary["physical_group_counts"].values()) != summary["mesh_elements"]:
        raise ValueError("MSH physical group partition mismatch")
    inside_rows = [c for c in cells if c["zone"] == "corner_centroid_inside_pore" and int(c["tet10_centroids"]) > 0]
    if len(inside_rows) != 1 or inside_rows[0]["tet10_centroids"] != "1":
        raise ValueError("inside-pore corner centroid not uniquely localized")
    physical_nearwall = by_zone["0_20um"] + by_zone["20_100um"]
    physical_nearwall_polar = sum(int(c["tet10_centroids"]) for c in cells
                                  if c["zone"] in ("0_20um", "20_100um")
                                  and int(c["polar_mu_bin"]) in (0, 9))
    if physical_nearwall != 0 or physical_nearwall_polar != 0:
        raise ValueError("unexpected nearwall centroid coverage")
    polar = inside_rows[0]
    b6 = summary["zone_profile"]["100um_5mm"]
    far = summary["zone_profile"]["outside_B6"]
    out = {
        "result": "P10CT_R2_INDEPENDENT_FULL_QP_PASS_BUT_U0_UNDERRESOLVED_FOR_LOCAL_DERIVATIVE",
        "original_evidence_sha256": digest, "zip_crc_files": len(EXPECTED_FILES),
        "original_mesh_sha256": EXPECTED_MESH_SHA, "gmsh_new_calls_in_R2": 0, "physical_FEM_runs": 0,
        "tet10": summary["tet10"], "tri6": summary["tri6"],
        "gmsh_R1_reported_all_entity_elements": 102726,
        "R2_physical_tag_exported_elements": summary["mesh_elements"],
        "element_count_scope_difference": 102726 - summary["mesh_elements"],
        "qp_27_count": summary["curved_27qp_samples"],
        "nonpositive_curved_qp_count": summary["curved_qp_nonpositive_count"],
        "nonpositive_corner_det_count": summary["corner_det_nonpositive_count"],
        "min_sampled_detJ_m3": summary["curved_qp_det_min"],
        "corner_quality_min": summary["corner_quality_min"],
        "corner_quality_below_0p1": summary["corner_quality_lt_0p1_count"],
        "pore_wall_tri6": summary["physical_group_counts"]["2:8"],
        "pore_wall_max_radial_node_error_mm": summary["pore_wall_max_radial_node_error_mm"],
        "tet10_centroid_by_zone": dict(by_zone),
        "corner_centroid_inside_pore_cell": {"mu_bin": int(polar["polar_mu_bin"]),
                                              "phi_sector": int(polar["phi_sector"]),
                                              "hmax_mm": float(polar["hmax_p50_mm"])},
        "physical_nearwall_0_100um_centroid_count": physical_nearwall,
        "physical_nearwall_0_100um_polar_centroid_count": physical_nearwall_polar,
        "R2_original_polar_0_100um_flag": summary["flags"]["polar_0_100um_has_tet_centroids"],
        "R2_original_flag_false_positive_reason": "included corner centroid inside pore in ZONES[:2]",
        "corrected_physical_polar_0_100um_has_tet_centroids": False,
        "B6_0p1_to_5mm": {"tet10": b6["tet10"], "hmax_p50_mm": b6["hmax_p50_mm"],
                              "polar_vs_mid_hmax_p50_ratio": b6["polar_hmax_p50_mm"] / b6["mid_hmax_p50_mm"]},
        "outside_B6": {"tet10": far["tet10"], "hmax_p50_mm": far["hmax_p50_mm"],
                         "polar_vs_mid_hmax_p50_ratio": far["polar_hmax_p50_mm"] / far["mid_hmax_p50_mm"]},
        "physical_FEM_readiness": "STOP_U0_TOO_COARSE_NEAR_PORE",
        "limitations": ["positive 27QP samples do not prove detJ positivity throughout curved tets",
                        "centroid coverage is not absence of physical material/physical QP contributions",
                        "no 4D mechanical/thermal fields or shape derivative on U0",
                        "global corner-volume closure cannot establish near-wall resolution"],
    }
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: script P10CT_R2_EVIDENCE.zip output.json")
    a = audit(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(a["result"])
