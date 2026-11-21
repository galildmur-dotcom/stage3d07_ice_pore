#!/usr/bin/env python3
"""D-019: immutable mesh-identity-specific M1 geometric acceptance.

Reruns the P10DI independent evidence/CSV audit; original P10DG QA_STOP
is preserved. No meshing, physical solver, or source changes.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import p10di_verify_p10dg_real_mesh_evidence as p10di

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / (
    "research/evidence/P10DI_P10DG_R1_REAL_M1_MESH_STOP_20261121"
    "/input/P10DG_EVIDENCE_REAL_M1.zip"
)
M0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
RESEARCH_BRANCH = "research/p10bb-w5b2-20261118"


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError("P10DJ_D019_ACCEPTANCE_STOP: " + detail)


def ratify(result: dict) -> dict:
    require(result["original_status_preserved"] ==
            "P10DG_STOP_NO_FEM/GEOMETRY_QA_STOP",
            "original stopped QA must remain visible")
    require(result["h0_mesh_sha256_windows_report"] == M0_SHA and
            result["m1_mesh_sha256_windows_report"] == M1_SHA,
            "this consent is limited to exact M0 and M1 SHA")
    require(result["native_gmsh_exit"] == 0 and result["native_run_FEM"] == 0,
            "wrong physical/native run status")
    require(result["H0_Tet10"] == 7388 and result["M1_Tet10"] == 9736 and
            result["H0_pore_Tri6"] == 136 and result["M1_pore_Tri6"] == 178,
            "non-approved topology or element counts")
    require(result["corner_and_curved27QP_quality_reported"] ==
            "PASS_BOTH_MESHES" and
            result["H0_reported_curved27QP_samples"] == 7388 * 27 and
            result["M1_reported_curved27QP_samples"] == 9736 * 27,
            "missing geometric sampling report")
    ratio = result["typical_mean_volume_ratio_from_curved_volume_and_counts"]
    require(.65 <= ratio <= .95,
            "approved mean-volume ratio must be within [0.65,0.95]")
    require(len(result["radial_bands"]) == 7, "wrong radial band count")
    inspected = [r for r in result["radial_bands"] if r["gated"]]
    require(len(inspected) == 5 and
            all(r["H0_tet10"] >= 100 and
                r["ratio_weighted_mu_bin_medians"] is not None and
                .55 <= r["ratio_weighted_mu_bin_medians"] <= 1.15
                for r in inspected),
            "pre-existing radial 0.55-1.15 guard failure")
    require(result["preexisting_band_gate_issues"] == [] and
            result["unpaired_global_median_volume_ratio"] < .65 and
            result["original_only_failure"] ==
            "global unpaired median Tet10 volume ratio outside 0.65-0.95",
            "original median QA_STOP was altered or concealed")
    require(result["matched_radial_mu_bins"] == 60 and
            result["H0_tet10_covered_in_matched_bins"] == 7387 and
            len(result["matched_bins_below_0p55"]) == 1 and
            result["matched_bins_below_0p55"][0]["radial_band"] == "20_100um" and
            result["matched_bins_below_0p55"][0]["mu_bin"] == 0 and
            result["matched_bins_below_0p55"][0]["H0_count"] == 12,
            "polar-local exception must remain explicit")
    return {
        "decision": "D-019",
        "decision_date": "2026-11-21",
        "investigator_consent_text": "согласен принять M1",
        "status": "M1_GEOMETRY_ACCEPTED_BY_INVESTIGATOR_WITH_DOCUMENTED_QA_OVERRIDE",
        "M0": "H0",
        "M0_exact_sha256": M0_SHA,
        "M1": "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY",
        "M1_exact_sha256_windows_report": M1_SHA,
        "M1_Tet10": 9736,
        "M1_pore_Tri6": 178,
        "adopted_mean_volume_ratio_M1_over_M0": ratio,
        "adopted_mean_volume_ratio_gate": [0.65, 0.95],
        "adopted_radial_local_gate": [0.55, 1.15],
        "adopted_radial_gated_bands": len(inspected),
        "adopted_radial_gated_bands_passed": len(inspected),
        "original_P10DG_geometry_QA": "GEOMETRY_QA_STOP",
        "original_P10DG_unpaired_median_ratio": result["unpaired_global_median_volume_ratio"],
        "original_QA_exit": 2,
        "polar_mu0_20_100um_outlier_remains_reported": (
            result["matched_bins_below_0p55"][0]
        ),
        "physical_M1_FEM_runs": 0,
        "M2_adaptive_authorized": False,
        "H0_forward_history_compatible_with_M1": False,
        "same_M1_mesh_required_for_forward_and_adjoint": True,
        "strict_full_signed_local_mechanical_thermal_r_theta_phi_t_required": True,
        "independent_curved_detJ_recomputed_from_raw_M1_msh": False,
        "acceptance_basis": (
            "Researcher's explicit consent after P10DI independent read-only "
            "evidence audit, physical-domain mean curved-volume-per-Tet10 "
            "and unchanged five populated radial local proxy gates. "
            "Original P10DG median-only QA_STOP is retained, not reclassified."
        ),
        "next": (
            "Prepare physical M1 forward/adjoint full signed 4D program and "
            "resource gate source-only; physical execution needs separate "
            "explicit consent and a fresh compatible M1 forward history."
        ),
    }


def selftest(report: dict) -> None:
    cases = (
        ("mean volume ratio", "typical_mean_volume_ratio_from_curved_volume_and_counts",
         0.5),
        ("mesh identity", "m1_mesh_sha256_windows_report", "bad-sha"),
        ("FEM leakage", "native_run_FEM", 1),
        ("hidden original stop", "original_status_preserved", "GEOMETRY_QA_PASS"),
    )
    for desc, key, value in cases:
        bad = copy.deepcopy(report)
        bad[key] = value
        try:
            ratify(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("negative test incorrectly passed: " + desc)
    bad = copy.deepcopy(report)
    next(r for r in bad["radial_bands"] if r["gated"])[
        "ratio_weighted_mu_bin_medians"] = 1.4
    try:
        ratify(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("radial gate negative test incorrectly passed")
    print("P10DJ_D019_NEGATIVE_OK 5_MUTATIONS_REJECTED FEM=0")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    opts = p.parse_args()
    args = p10di.load_evidence(EVIDENCE)
    report = p10di.verify_reports(*args, p10di.package_pins())
    decision = ratify(report)
    if opts.selftest:
        selftest(report)
    if opts.out is not None:
        opts.out.parent.mkdir(parents=True, exist_ok=True)
        opts.out.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(decision, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
