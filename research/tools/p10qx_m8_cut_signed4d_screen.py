#!/usr/bin/env python3
"""P10QX: read-only, conditional M8 cut-volume versus actual signed4D audit.

Usage:
    python research/tools/p10qx_m8_cut_signed4d_screen.py \
        --evidence /path/P10KV_M8_FIRST_FULL4D_EVIDENCE.zip \
        --brackets research/P10QA_M8_PHYSICAL_VOLUME_SUMMARY_QA.json

The alternative ``--brackets -`` reads the GitHub JSON contents from stdin.
No PDE solve, mesh generation, EDV replay, or FE quadrature modification occurs.

The numerical screens ASSUME a constant time-dependent, bin-averaged signed
integrand, i.e. contribution D_b,t scales linearly with the physical bin
volume. Real integrands need not be constant, so outputs are NOT error bounds
for physical D_R j_peak or a proposed correction to published FEM results.
"""

import argparse
import csv
import io
import json
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


MESH_SHA = "40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
COMPONENTS = ("mechanical_total_per_m", "thermal_total_per_m", "total_per_m")


def evaluate(evidence_zip: Path, qa: dict) -> dict:
    if qa.get("mesh_sha256") != MESH_SHA or len(qa.get("bin_final_brackets", [])) != 48:
        raise ValueError("Expected the P10QA 48-bin accepted-M8 physical-volume QA")
    intervals = {
        (int(b["radial_bin"]), int(b["mu_bin"]), int(b["phi_bin"])): b
        for b in qa["bin_final_brackets"]
    }
    if len(intervals) != 48:
        raise ValueError("Duplicate geometric QA bin keys")

    by_bin = defaultdict(list)
    global_sum = defaultdict(float)
    global_l1 = 0.0
    volume_rows = 0
    robin_rows = 0
    seen = set()
    with zipfile.ZipFile(evidence_zip) as z:
        if z.testzip() is not None:
            raise ValueError("Evidence ZIP CRC failure")
        manifest = json.loads(z.read("P10KV_MANIFEST.json"))
        if manifest.get("mesh_sha256") != MESH_SHA or manifest.get("native_exit_code") != 0:
            raise ValueError("Physical evidence does not match accepted successful M8")
        with z.open("P10DD_SIGNED_R_THETA_PHI_T.csv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
            for row in reader:
                region = row["region"]
                step = int(row["step"])
                key = (int(row["radial_bin"]), int(row["mu_bin"]), int(row["phi_bin"]))
                if not (1 <= step <= 36):
                    raise ValueError(f"Unexpected step {step}")
                signature = (step, region, key)
                if signature in seen:
                    raise ValueError(f"Duplicate signed4D key: {signature}")
                seen.add(signature)
                mech_terms = math.fsum(float(row[x]) for x in (
                    "mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m"))
                therm_terms = math.fsum(float(row[x]) for x in (
                    "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m"))
                if not (math.isclose(mech_terms, float(row["mechanical_total_per_m"]), abs_tol=1e-10)
                        and math.isclose(therm_terms, float(row["thermal_total_per_m"]), abs_tol=1e-10)
                        and math.isclose(mech_terms + therm_terms, float(row["total_per_m"]), abs_tol=1e-10)):
                    raise ValueError(f"Broken row closure: {signature}")
                for c in COMPONENTS:
                    global_sum[c] += float(row[c])
                if region == "VOLUME":
                    if not (0 <= key[0] < 10 and 0 <= key[1] < 10 and 0 <= key[2] < 12):
                        raise ValueError(f"Invalid volume bin key {key}")
                    volume_rows += 1
                    global_l1 += abs(float(row["total_per_m"]))
                    if key in intervals:
                        by_bin[key].append(row)
                elif region == "TOP_ROBIN":
                    robin_rows += 1
                else:
                    raise ValueError(f"Unknown region {region}")

    if volume_rows != 43200 or robin_rows != 36 or len(by_bin) != 48:
        raise ValueError("Unexpected signed4D grid/count or missing 48 selected bins")
    baseline = global_sum["total_per_m"]
    manifest_total = float(manifest["independent_4d"]["jpeak_derivative_per_m"])
    if not math.isclose(baseline, manifest_total, abs_tol=1e-8):
        raise ValueError("Physical signed4D rows do not close to native manifest")

    rows_out = []
    for key in sorted(intervals):
        b = intervals[key]
        rows = by_bin[key]
        steps = [int(r["step"]) for r in rows]
        if len(steps) != 36 or set(steps) != set(range(1, 37)):
            raise ValueError(f"Missing time steps in bin {key}")
        vm_all = [float(r["mechanical_volume_m3"]) for r in rows]
        vt_all = [float(r["thermal_volume_m3"]) for r in rows]
        vm, vt = vm_all[0], vt_all[0]
        if min(vm, vt) <= 0:
            raise ValueError(f"Nonpositive quadrature measure in bin {key}")
        if any(abs(v - vm) > 1e-11 * vm for v in vm_all):
            raise ValueError(f"Mechanical measure changes with time in bin {key}")
        if any(abs(v - vt) > 1e-11 * vt for v in vt_all):
            raise ValueError(f"Thermal measure changes with time in bin {key}")

        lo = float(b["lower_cut_volume_m3"])
        hi = float(b["upper_cut_volume_m3"])
        ideal = float(b["ideal_spherical_sector_volume_m3"])
        if not (0 <= lo <= hi and lo <= ideal <= hi):
            raise ValueError(f"Invalid geometric physical bracket in {key}")
        mech = math.fsum(float(r["mechanical_total_per_m"]) for r in rows)
        therm = math.fsum(float(r["thermal_total_per_m"]) for r in rows)
        signed = mech + therm

        # Affine, *conditional* volume-only reweighting of signed integrand.
        def delta(vol):
            return mech * (vol / vm - 1.0) + therm * (vol / vt - 1.0)

        d_lo, d_hi = delta(lo), delta(hi)
        # Deliberately discards both time and mechanical/thermal cancellation.
        termwise_envelope = math.fsum(
            abs(float(r["mechanical_total_per_m"])) * max(abs(lo / vm - 1), abs(hi / vm - 1))
            + abs(float(r["thermal_total_per_m"])) * max(abs(lo / vt - 1), abs(hi / vt - 1))
            for r in rows
        )
        rows_out.append({
            "radial_bin": key[0], "mu_bin": key[1], "phi_bin": key[2],
            "volume_lower_m3": lo, "volume_upper_m3": hi, "volume_ideal_m3": ideal,
            "volume_mechanical_qp_m3": vm, "volume_thermal_qp_m3": vt,
            "mechanical_qp_inside_bracket": lo <= vm <= hi,
            "thermal_qp_inside_bracket": lo <= vt <= hi,
            "actual_4d_signed_per_m": signed,
            "actual_4d_abs_sum_per_m": math.fsum(abs(float(r["total_per_m"])) for r in rows),
            "ideal_rescale_signed_delta_per_m": delta(ideal),
            "bracket_rescale_signed_delta_min_per_m": min(d_lo, d_hi),
            "bracket_rescale_signed_delta_max_per_m": max(d_lo, d_hi),
            "bracket_rescale_abs_component_envelope_per_m": termwise_envelope,
        })

    def aggregate(rs):
        return {
            "bins": len(rs),
            "physical_bracket_width_sum_m3": math.fsum(r["volume_upper_m3"] - r["volume_lower_m3"] for r in rs),
            "physical_ideal_volume_sum_m3": math.fsum(r["volume_ideal_m3"] for r in rs),
            "qp_mechanical_volume_sum_m3": math.fsum(r["volume_mechanical_qp_m3"] for r in rs),
            "qp_thermal_volume_sum_m3": math.fsum(r["volume_thermal_qp_m3"] for r in rs),
            "qp_mechanical_inside_count": sum(r["mechanical_qp_inside_bracket"] for r in rs),
            "qp_thermal_inside_count": sum(r["thermal_qp_inside_bracket"] for r in rs),
            "actual_4d_signed_per_m": math.fsum(r["actual_4d_signed_per_m"] for r in rs),
            "actual_4d_abs_sum_per_m": math.fsum(r["actual_4d_abs_sum_per_m"] for r in rs),
            "ideal_rescale_signed_delta_per_m": math.fsum(r["ideal_rescale_signed_delta_per_m"] for r in rs),
            "bracket_rescale_signed_delta_min_per_m": math.fsum(r["bracket_rescale_signed_delta_min_per_m"] for r in rs),
            "bracket_rescale_signed_delta_max_per_m": math.fsum(r["bracket_rescale_signed_delta_max_per_m"] for r in rs),
            "bracket_rescale_abs_component_envelope_per_m": math.fsum(r["bracket_rescale_abs_component_envelope_per_m"] for r in rs),
        }

    summary = aggregate(rows_out)
    summary["actual_abs_share_of_all_M8_4d_bins"] = summary["actual_4d_abs_sum_per_m"] / global_l1
    summary["conditional_abs_component_envelope_fraction_of_global_signed"] = (
        summary["bracket_rescale_abs_component_envelope_per_m"] / abs(baseline)
    )
    return {
        "protocol": "P10QX_M8_PHYSICAL_SIGNED4D_CUT_VOLUME_SCREEN_READ_ONLY",
        "status": "PASS_INPUT_VALIDATION_CONDITIONAL_SCREEN_ONLY",
        "mesh_sha256": MESH_SHA,
        "evidence_status": manifest["status"],
        "physical_4d_rows": volume_rows + robin_rows,
        "baseline_D_R_jpeak_per_m": baseline,
        "baseline_mechanical_per_m": global_sum["mechanical_total_per_m"],
        "baseline_thermal_per_m": global_sum["thermal_total_per_m"],
        "global_4d_volume_abs_sum_per_m": global_l1,
        "threshold_0p5pct_global_per_m": 0.005 * abs(baseline),
        "threshold_1pct_global_per_m": 0.01 * abs(baseline),
        "tested_bins": "r=0/4, mu=0/9, phi=0..11, 36 timesteps",
        "sample": summary,
        "groups": {
            f"r{r}_mu{mu}": aggregate([x for x in rows_out if x["radial_bin"] == r and x["mu_bin"] == mu])
            for r in (0, 4) for mu in (0, 9)
        },
        "bin_results": rows_out,
        "interpretation": (
            "Volume-only hypothetical affine rescaling of fixed original signed4D per-bin values, "
            "assuming constant bin-averaged physical integrand for each step and physical component. "
            "No reconstruction of FE/EDV/adjoint integrands. No rigorous bound on physical shape derivative. "
            "Only 48 out of 1200 spatial bins; excludes remaining bins and functional/mesh errors. "
            "Ideal sphere sector differs from exact curved Tet10 geometry."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--brackets", required=True, help="P10QA summary JSON path or '-' for stdin")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    qa = json.load(sys.stdin) if args.brackets == "-" else json.loads(Path(args.brackets).read_text())
    report = evaluate(args.evidence, qa)
    if args.summary_only:
        report.pop("bin_results")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
