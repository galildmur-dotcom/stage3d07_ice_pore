#!/usr/bin/env python3
"""P10DG independent geometry gate on actual H0/M1; NO physical indicators.

Calls the pinned P10DE full 27QP mesh parser and adds radial weighted-median
volume checks to avoid accepting only a fortuitous global median. Every
mesh is read afresh from disk; neither source H0 nor new M1 is modified.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys

import P10DE_compare_m1 as core

REV = "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY"
RADIAL_MIN_H0_TET = 100
RADIAL_VOLUME_MIN = .55
RADIAL_VOLUME_MAX = 1.15


def median_of_bin_medians(rows: list[dict], key: str) -> float | None:
    pairs = sorted((float(r[key]), int(r["tet10"])) for r in rows
                   if r[key] is not None and int(r["tet10"]) > 0)
    if not pairs:
        return None
    threshold = sum(n for _, n in pairs) / 2.
    total = 0
    for val, count in pairs:
        total += count
        if total >= threshold:
            return val
    return pairs[-1][0]


def radial_volume_gate(profiles: list[dict]) -> tuple[list[dict], list[str]]:
    rows, issues = [], []
    for band in core.RADIAL_LABELS:
        h0 = [r for r in profiles if r["mesh"] == "H0" and r["radial_band"] == band]
        m1 = [r for r in profiles if r["mesh"] == "M1" and r["radial_band"] == band]
        core.require(len(h0) == len(m1) == 10, "incomplete mu bins for " + band)
        n0 = sum(int(r["tet10"]) for r in h0)
        n1 = sum(int(r["tet10"]) for r in m1)
        v0 = median_of_bin_medians(h0, "median_corner_volume_m3")
        v1 = median_of_bin_medians(m1, "median_corner_volume_m3")
        if v0 is not None:
            core.require(v0 > 0, "invalid H0 volume proxy")
        ratio = v1 / v0 if v0 and v1 else None
        significant = n0 >= RADIAL_MIN_H0_TET
        passed = ratio is not None and RADIAL_VOLUME_MIN <= ratio <= RADIAL_VOLUME_MAX
        if significant and not passed:
            issues.append(f"radial {band} median-of-bin-median volume ratio "
                          f"{ratio} outside [{RADIAL_VOLUME_MIN},{RADIAL_VOLUME_MAX}]")
        rows.append({
            "radial_band": band, "h0_tet10": n0, "m1_tet10": n1,
            "h0_weighted_binmedian_volume_m3": v0,
            "m1_weighted_binmedian_volume_m3": v1,
            "m1_over_h0_radial_volume_proxy": ratio,
            "significant_h0_n_ge_100": significant,
            "radial_gate_pass": passed if significant else None,
        })
    return rows, issues


def audit(h0: Path, m1: Path) -> tuple[dict, list[dict], list[dict]]:
    report, profiles = core.audit(h0, m1)
    local, problems = radial_volume_gate(profiles)
    report["protocol"] = REV
    report["radial_volume_gate_issues"] = problems
    report["radial_volume_gate_rule"] = (
        "For H0 bands >=100 Tet10: compare weighted medians of 10 mu-bin "
        "element-volume medians in [0.55,1.15]. This is NOT paired element "
        "volumes or true all-element median; small H0 bands are descriptive."
    )
    report["source_field_origin"] = "P10DF_H0_EMPIRICAL_INVERSE_PROXY_UNVERIFIED"
    report["geometry_pass_independent_of_physics"] = True
    if problems:
        report["status"] = "GEOMETRY_QA_STOP"
    return report, profiles, local


def selftest() -> None:
    core.selftest()
    fixture = []
    for mesh in ("H0", "M1"):
        for band in core.RADIAL_LABELS:
            for mu in range(10):
                count = 20 if band == "100_500um" else 1
                fixture.append({
                    "mesh": mesh, "radial_band": band, "mu_bin": mu,
                    "tet10": count,
                    "median_corner_volume_m3": 1. if mesh == "H0" else .8,
                })
    bands, issues = radial_volume_gate(fixture)
    core.require(len(bands) == 7 and not issues, "radial near-target synthetic")
    for r in fixture:
        if r["mesh"] == "M1" and r["radial_band"] == "100_500um":
            r["median_corner_volume_m3"] = .05
    bands, issues = radial_volume_gate(fixture)
    core.require(len(issues) == 1 and "100_500um" in issues[0],
                 "radial over-refinement negative test")
    for r in fixture:
        if r["mesh"] == "M1" and r["radial_band"] == "100_500um":
            r["median_corner_volume_m3"] = 1.4
    _, issues = radial_volume_gate(fixture)
    core.require(len(issues) == 1 and "100_500um" in issues[0],
                 "radial under-refinement negative test")
    print("P10DG_QA_SYNTHETIC_OK full27QP=PASS folded_negative=DETECTED "
          "radial_over_under_negative=DETECTED FEM=0")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--h0", type=Path)
    p.add_argument("--m1", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.h0 or not args.m1 or not args.out:
        p.error("--h0 --m1 --out are required")
    report, profiles, local = audit(args.h0, args.m1)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "P10DG_H0_M1_MESH_QA.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, rows in (
        ("P10DG_H0_M1_RADIAL_MU_BINS.csv", profiles),
        ("P10DG_H0_M1_RADIAL_VOLUME_GATE.csv", local),
    ):
        with (args.out / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print("P10DG_M1_QA_PASS_NO_FEM" if report["status"] == "GEOMETRY_QA_PASS"
          else "P10DG_M1_QA_STOP_NO_FEM",
          "H0_TET10=", report["h0"]["tet10"],
          "M1_TET10=", report["m1"]["tet10"],
          "GLOBAL_VOLUME_RATIO=", report["median_corner_volume_ratio_M1_over_H0"],
          "RADIAL_ISSUES=", len(report["radial_volume_gate_issues"]))
    return 0 if report["status"] == "GEOMETRY_QA_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
