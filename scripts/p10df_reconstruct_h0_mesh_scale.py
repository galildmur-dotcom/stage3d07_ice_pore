#!/usr/bin/env python3
"""P10DF source-only inverse sizing of a prospective M1 from *measured* H0.

H0's actual mesher source is not attested. This uses two empirical length
anchors as a reproducible PROPOSAL; it generates NO MSH and runs NO FEM.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import re

from p10de_verify_m1_mesh_stop import H0_SHA, H3_CSV, ROOT, audit, as_rows, require


EVIDENCE = (
    ROOT
    / "research/evidence/P10DE_R1_M1_OVERREFINED_STOP_20261121/input/P10DE_EVIDENCE.zip"
)
CANDIDATE_GEO = ROOT / "gmsh/P10DF_M1_FROM_H0_EMPIRICAL_CALIBRATION_CANDIDATE.geo"
H0_H3_GEO = ROOT / "gmsh/sphere_pore_B6_refined.geo"
H3_GENERATION = ROOT / "gmsh/GENERATE_H3_H4_RU.md"
OLD_REJECTED_GEO = ROOT / "gmsh/P10DC_M1_FROM_H0_20PCT_VOLUME.geo"
Q = 0.8 ** (1.0 / 3.0)
ANCHOR_BAND = "18mm_plus"
def num_from_geo(source: str, name: str) -> float:
    m = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*([0-9.eE+-]+)\s*;",
                  source)
    require(m is not None, "missing source-only " + name)
    return float(m.group(1))


def check_proposed_geo(source: str, near: float, far: float) -> None:
    require('Include "sphere_pore_B6_refined.geo";' in source,
            "candidate must include common historic CAD")
    # Do not silently introduce an angle-specific or physics-weighted refinement.
    require(not re.search(r"(?m)^\s*(?:Field\[|Background Field|Mesh\.)", source),
            "candidate must contain ONLY near/far overrides")
    for name, reference in (("nearSize", near), ("farSize", far)):
        actual = num_from_geo(source, name)
        require(math.isfinite(actual) and math.isclose(actual, reference, rel_tol=1e-12),
                f"candidate {name} must match the independent anchor formula")
    require(0 < near < far and 0 < Q < 1, "bad empirical field/scale")


def calculate(evidence: Path) -> tuple[dict, list[dict]]:
    old_audit, radial = audit(evidence)
    hist = {r["label"]: r for r in as_rows(H3_CSV.read_bytes())}
    h0, h3 = hist["H0"], hist["H3"]
    require(h0["mesh_sha256"] == H0_SHA and int(h0["tet10"]) == 7388,
            "H0 historic identity")
    require(int(h0["pore_tri6"]) == 136 and
            int(h3["tet10"]) == 81891 and int(h3["pore_tri6"]) == 866,
            "historic H0/H3 mesh counts")
    source = H0_H3_GEO.read_text(encoding="utf-8")
    h3_doc = H3_GENERATION.read_text(encoding="utf-8")
    require("nearSize(H3)=0.000190" in h3_doc and
            "farSize=0.003900" in h3_doc,
            "published H3 recipe not found")
    require("Field[2].SizeMin=nearSize;" in source and
            "Field[2].SizeMax=farSize;" in source and
            "Field[2].DistMin=0.0015;" in source and
            "Field[2].DistMax=0.018;" in source,
            "candidate CAD's threshold has changed")
    # Original misleading 'sizefac' is declared but unused in the size field.
    no_comments = "\n".join(line.split("//")[0] for line in source.splitlines())
    require(re.findall(r"\bsizefac\b", no_comments) == ["sizefac", "sizefac"],
            "sizefac usage changed: redo provenance")
    h3_near = num_from_geo(source, "nearSize")
    h3_far = num_from_geo(source, "farSize")
    require(math.isclose(h3_near, .00019, rel_tol=1e-13) and
            math.isclose(h3_far, .0039, rel_tol=1e-13),
            "H3 nominal near/far provenance")

    pore_h0_mm = float(h0["pore_median_edge_mm"])
    pore_h3_mm = float(h3["pore_median_edge_mm"])
    require(pore_h0_mm > pore_h3_mm > 0, "pore wall anchor invalid")
    far = next(row for row in radial if row["radial_band"] == ANCHOR_BAND)
    far_h0_mm = float(far["h0_hmax_binmedian_mm"])
    far_bad_mm = float(far["m1_hmax_binmedian_mm"])
    require(int(far["h0_tet10"]) > 1000 and int(far["m1_tet10"]) > 1000,
            "insufficient far-field anchor count")
    # An inferred near/far field that reproduces *length proxies* of H0 and
    # multiplies those proxies by q. Not an inverse Gmsh solution or exact M1.
    near_proxy_ratio = pore_h0_mm / pore_h3_mm
    far_proxy_ratio = far_h0_mm / far_bad_mm
    near = h3_near * Q * near_proxy_ratio
    far_size = h3_far * Q * far_proxy_ratio
    check_proposed_geo(CANDIDATE_GEO.read_text(encoding="utf-8"), near, far_size)
    old_geo = OLD_REJECTED_GEO.read_text(encoding="utf-8")
    require(math.isclose(num_from_geo(old_geo, "nearSize"), h3_near * Q,
                         rel_tol=1e-12) and
            math.isclose(num_from_geo(old_geo, "farSize"), h3_far * Q,
                         rel_tol=1e-12),
            "rejected source field does not have stated H3 scaling")

    comparison = []
    for row in radial:
        h0_h = row["h0_hmax_binmedian_mm"]
        bad_h = row["m1_hmax_binmedian_mm"]
        comparison.append({
            "radial_band": row["radial_band"],
            "h0_tet10": row["h0_tet10"],
            "rejected_tet10": row["m1_tet10"],
            "h0_weighted_binmedian_hmax_mm": h0_h,
            "rejected_weighted_binmedian_hmax_mm": bad_h,
            "target_m1_hmax_proxy_mm": Q * h0_h if h0_h is not None else None,
            "target_over_rejected_hmax_proxy": Q * h0_h / bad_h
                if h0_h and bad_h else None,
            "rejected_over_h0_volume_binmedian_ratio": row["volume_ratio"],
            "fit_used_as_anchor": row["radial_band"] == ANCHOR_BAND,
        })
    out = {
        "stage": "P10DF_H0_BASED_M1_GEOMETRIC_SIZE_INVERSE_PROXY_SOURCE_ONLY",
        "outcome": "CANDIDATE_GEO_SOURCE_ONLY_NO_GMSH_NO_FEM",
        "old_rejected_m1_over_h0_median_corner_volume":
            old_audit["m1_median_tet_volume_over_h0"],
        "h0_exact_mesh_sha256": H0_SHA,
        "evidence_sha256": old_audit["evidence_sha256"],
        "historical_h0_generator_command": "UNKNOWN",
        "h3_source_near_m": h3_near,
        "h3_source_far_m": h3_far,
        "h0_pore_median_edge_mm": pore_h0_mm,
        "h3_pore_median_edge_mm": pore_h3_mm,
        "pore_proxy_h0_over_h3": near_proxy_ratio,
        "far_band": ANCHOR_BAND,
        "far_h0_weighted_binmedian_hmax_mm": far_h0_mm,
        "far_rejected_weighted_binmedian_hmax_mm": far_bad_mm,
        "far_proxy_h0_over_rejected": far_proxy_ratio,
        "q_target_linear": Q,
        "target_typical_element_volume_ratio": .8,
        "proposed_nearSize_m": near,
        "proposed_farSize_m": far_size,
        "proposed_h0_like_near_proxy_m": near / Q,
        "proposed_h0_like_far_proxy_m": far_size / Q,
        "rejected_nearSize_m": num_from_geo(old_geo, "nearSize"),
        "rejected_farSize_m": num_from_geo(old_geo, "farSize"),
        "sanity_count_m1_h0_over_08": int(h0["tet10"]) / .8,
        "sanity_pore_tri6_m1_h0_over_q2": int(h0["pore_tri6"]) / Q**2,
        "status_limits": [
            "No historical H0 source .geo/command or raw H0.msh here.",
            "Pore edge and far-band hmax are DIFFERENT descriptive length measures.",
            "Weighted median of mu-bin medians is not a per-element distribution.",
            "Gmsh response need not scale linearly with nominal near/far sizes.",
            "No exact local volume decrease, element pairing, convergence, or FEM."
        ],
        "next": (
            "Only after explicit approval: one bounded M1 Gmsh mesh-only "
            "and independent global/radial/27QP QA against exact H0; "
            "NO physics indicators before physical M0/M1 comparison."
        ),
    }
    return out, comparison


def selftest(summary: dict, comparison: list[dict]) -> None:
    require(len(comparison) == 7 and
            math.isclose(summary["proposed_nearSize_m"], .00042855883184652975,
                         rel_tol=1e-12) and
            math.isclose(summary["proposed_farSize_m"], .0070524788853066865,
                         rel_tol=1e-12), "unexpected calibration anchors")
    original = CANDIDATE_GEO.read_text(encoding="utf-8")
    try:
        check_proposed_geo(
            original.replace("0.00042855883184652975",
                             "0.00017638037567728565"),
            summary["proposed_nearSize_m"], summary["proposed_farSize_m"])
    except ValueError as exc:
        require("candidate nearSize" in str(exc), "bad negative-scale STOP")
    else:
        raise ValueError("P10DF_INDEPENDENT_STOP: negative wrong-scale candidate accepted")
    try:
        check_proposed_geo(
            original + "\nField[42] = MathEval;\nField[42].F = \"phi\";\n",
            summary["proposed_nearSize_m"], summary["proposed_farSize_m"])
    except ValueError as exc:
        require("ONLY near/far" in str(exc), "bad negative-angular STOP")
    else:
        raise ValueError("P10DF_INDEPENDENT_STOP: negative angular-indicator accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--selftest", action="store_true")
    opts = parser.parse_args()
    summary, radial = calculate(opts.evidence)
    if opts.selftest:
        selftest(summary, radial)
    if opts.out is not None:
        opts.out.mkdir(parents=True, exist_ok=True)
        (opts.out / "P10DF_H0_EMPIRICAL_M1_SOURCE_CALIBRATION.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        with (opts.out / "P10DF_H0_M1_RADIAL_SIZE_TARGETS.csv").open(
                "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(radial[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(radial)
    print("P10DF_H0_M1_EMPIRICAL_SIZE_CALIBRATION_SOURCE_ONLY_OK "
          f"near_m={summary['proposed_nearSize_m']:.12g} "
          f"far_m={summary['proposed_farSize_m']:.12g} "
          f"target_volume_ratio={summary['target_typical_element_volume_ratio']:.3f} "
          "Gmsh3=0 FEM=0")
    if opts.selftest:
        print("P10DF_NEGATIVE_SCALE_AND_ANGULAR_FIELD_REJECTED")


if __name__ == "__main__":
    main()
