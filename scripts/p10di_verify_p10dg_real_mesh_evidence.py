#!/usr/bin/env python3
"""Read-only independent audit of the real P10DG R1 Windows geometry STOP.

Does not load a .msh: verifies ZIP, provenance, self-reported full 27QP QA,
140 radial/mu count closures and independent within-cell volume statistics.
No Gmsh and no FEM are executed.
"""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "research/packages/P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121.zip"
PACKAGE_SHA = "4c5f3712931f7de5bfe0b9e1734aa37ed4d1b72c6553f7828fdd56808bce6a82"
EVIDENCE_SHA = "93e934b5950bd8a94906084d68bd51babe911fb036908ffcbb0d6855bea201c2"
H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
BANDS = ("0_20um", "20_100um", "100_500um", "0p5_1p5mm", "1p5_5mm",
         "5_18mm", "18mm_plus")
FILES = {
    "P10DG_RUN_MANIFEST.json", "P10DG_RESULT.txt", "P10DG_STOP_TRACE.txt",
    "P10DG_GMSH_LOG_TAIL.txt", "P10DG_QA_STDOUT_STDERR.txt",
    "QA/P10DG_H0_M1_MESH_QA.json", "QA/P10DG_H0_M1_RADIAL_MU_BINS.csv",
    "QA/P10DG_H0_M1_RADIAL_VOLUME_GATE.csv",
}
STOP_REASON = "P10DG_STOP: M1/H0 curved 27QP or radial/global volume QA failed"


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise ValueError("P10DI_REAL_M1_AUDIT_STOP: " + msg)


def close(a: float, b: float, msg: str, tol: float = 1e-12) -> None:
    require(math.isfinite(a) and math.isfinite(b) and
            math.isclose(a, b, rel_tol=tol, abs_tol=0.),
            f"{msg}: {a} versus {b}")


def csv_bytes(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def median_weighted(pairs: list[tuple[float, int]]) -> float | None:
    pairs = sorted((value, weight) for value, weight in pairs if weight > 0)
    if not pairs:
        return None
    half = sum(n for _, n in pairs) / 2.
    cumul = 0
    for val, n in pairs:
        cumul += n
        if cumul >= half:
            return val
    raise AssertionError("unreachable weighted median")


def verify_radial(qa: dict, radial: list[dict], bins: list[dict]) -> dict:
    require(len(bins) == 140 and len(radial) == len(BANDS),
            "radial/mu file dimensions")
    seen = set()
    by_bin = {}
    for row in bins:
        mesh, band, mu = row["mesh"], row["radial_band"], int(row["mu_bin"])
        key = (mesh, band, mu)
        require(key not in seen and mesh in ("H0", "M1") and band in BANDS and
                0 <= mu < 10, "duplicate/bad radial-mu key")
        seen.add(key)
        n = int(row["tet10"])
        require(n >= 0, "negative Tet10 count")
        if n:
            for field in ("median_corner_volume_m3", "median_hmax_mm",
                          "min_corner_quality", "p05_corner_quality"):
                value = float(row[field])
                require(math.isfinite(value) and value > 0,
                        "invalid per-bin metric " + field)
        by_bin[key] = row
    require(len(seen) == 2 * 7 * 10, "missing radial-mu cells")
    for name, key in (("H0", "h0"), ("M1", "m1")):
        require(sum(int(r["tet10"]) for r in bins if r["mesh"] == name) ==
                qa[key]["tet10"], "radial/mu count closure " + name)

    paired = []
    band_stats = []
    require([r["radial_band"] for r in radial] == list(BANDS),
            "radial gate order mismatch")
    for r in radial:
        band = r["radial_band"]
        h0 = [by_bin["H0", band, mu] for mu in range(10)]
        m1 = [by_bin["M1", band, mu] for mu in range(10)]
        n0, n1 = (sum(int(s["tet10"]) for s in group) for group in (h0, m1))
        require(n0 == int(r["h0_tet10"]) and n1 == int(r["m1_tet10"]),
                "radial counts disagree with mu bins")
        values = []
        for group in (h0, m1):
            pairs = [(float(s["median_corner_volume_m3"]), int(s["tet10"]))
                     for s in group if int(s["tet10"]) > 0]
            values.append(median_weighted(pairs))
        ratio = values[1] / values[0] if all(v is not None for v in values) else None
        for expected, field in zip(values, (
                "h0_weighted_binmedian_volume_m3",
                "m1_weighted_binmedian_volume_m3")):
            if expected is None:
                require(not r[field], "expected empty band volume")
            else:
                close(float(r[field]), expected, "radial weighted bin median")
        if ratio is None:
            require(not r["m1_over_h0_radial_volume_proxy"],
                    "expected empty radial ratio")
        else:
            close(float(r["m1_over_h0_radial_volume_proxy"]), ratio,
                  "radial volume ratio")
        significant = n0 >= 100
        require((r["significant_h0_n_ge_100"] == "True") == significant,
                "band significance inconsistent")
        if significant:
            require(r["radial_gate_pass"] == "True" and
                    ratio is not None and .55 <= ratio <= 1.15,
                    "radial volume guard failed")
        else:
            require(not r["radial_gate_pass"], "small H0 band incorrectly gated")
        band_stats.append({"radial_band": band, "H0_tet10": n0, "M1_tet10": n1,
                           "ratio_weighted_mu_bin_medians": ratio,
                           "gated": significant})
        for mu in range(10):
            a, b = by_bin["H0", band, mu], by_bin["M1", band, mu]
            n_a, n_b = int(a["tet10"]), int(b["tet10"])
            if n_a and n_b:
                local = (float(b["median_corner_volume_m3"]) /
                         float(a["median_corner_volume_m3"]))
                paired.append({"radial_band": band, "mu_bin": mu,
                               "H0_count": n_a, "M1_count": n_b,
                               "local_volume_ratio": local})
    weighted = [(row["local_volume_ratio"], row["H0_count"]) for row in paired]
    paired.sort(key=lambda x: x["local_volume_ratio"])

    def quantile(frac: float) -> float:
        cap = frac * sum(n for _, n in weighted)
        current = 0
        for row in paired:
            current += row["H0_count"]
            if current >= cap:
                return row["local_volume_ratio"]
        raise AssertionError("weighted quantile impossible")

    require(len(paired) == 60 and
            sum(row["H0_count"] for row in paired) == 7387,
            "paired mu-bin count coverage mismatch")
    return {
        "radial_bands": band_stats,
        "matched_radial_mu_bins": len(paired),
        "H0_tet10_covered_in_matched_bins": sum(r["H0_count"] for r in paired),
        "matched_bin_ratio_weighted_q10": quantile(.1),
        "matched_bin_ratio_weighted_q50": quantile(.5),
        "matched_bin_ratio_weighted_q90": quantile(.9),
        "matched_bin_ratio_weighted_mean": sum(v * n for v, n in weighted) /
                                             sum(n for _, n in weighted),
        "matched_bin_ratio_min": paired[0]["local_volume_ratio"],
        "matched_bin_ratio_max": paired[-1]["local_volume_ratio"],
        "matched_bins_below_0p55": [r for r in paired
                                   if r["local_volume_ratio"] < .55],
        "matched_bins_above_1p15": [r for r in paired
                                   if r["local_volume_ratio"] > 1.15],
    }


def verify_reports(m: dict, qa: dict, radial: list[dict],
                   bins: list[dict], result: str, trace: str,
                   stdout: str, log: str, pinned: dict) -> dict:
    require(m["protocol"] == "P10DG_R1_H0_EMPIRICAL_M1_MESH_ONLY" and
            m["status"] == "P10DG_STOP_NO_FEM" and m["FEM_runs"] == 0 and
            m["Gmsh_max_attempts"] == 1 and m["mesh_only"] is True,
            "unexpected executed protocol/status")
    require(m["package_sources_sha256"] == pinned["files"] and
            len(pinned["files"]) == 12, "Windows source SHA12 mismatch")
    require(m["h0_sha256"] == H0_SHA and
            m["gmsh_version_output"] == "4.15.2" and
            m["native_exit_code"] == 0 and m["qa_exit_code"] == 2,
            "preflight/native mesh/QA exit mismatch")
    require(m["stop_reason"] == STOP_REASON and
            "QA failed" in trace and STOP_REASON in trace,
            "STOP reason and trace mismatch")
    require("RESULT=P10DG_STOP_NO_FEM" in result and
            "WINDOWS_NATIVE_GMSH_EXIT=0" in result and "QA_EXIT=2" in result and
            "FEM_RUNS=0" in result, "result file disagrees with manifest")
    require(0 < m["wall_seconds"] < 900 and
            0 <= m["peak_private_bytes_polled"] < 8 * 1024**3 and
            0 < m["m1_mesh_size_bytes"] < 750 * 1024**2,
            "bounded Gmsh resource report mismatch")
    require(m["exact_gmsh_argv"][2:7] ==
            ["-3", "-nt", "2", "-format", "msh2"],
            "unexpected Gmsh mesh arguments")
    require(re.fullmatch(r"[0-9a-f]{64}", m["m1_mesh_sha256"]) is not None,
            "missing Windows M1 SHA")
    require(qa["h0_sha256"] == H0_SHA and
            qa["m1_sha256"] == m["m1_mesh_sha256"] and
            qa["status"] == "GEOMETRY_QA_STOP" and
            qa["FEM_runs"] == 0 and
            not qa["h0_issues"] and not qa["m1_issues"] and
            not qa["radial_volume_gate_issues"],
            "geometry QA identity or failed component")
    require(qa["mesh_target_issues"] == [
                "global unpaired median Tet10 volume ratio outside 0.65-0.95"],
            "unexpected geometry QA failure")
    require(qa["h0"]["tet10"] == 7388 and qa["h0"]["pore_tri6"] == 136 and
            qa["m1"]["tet10"] == 9736 and qa["m1"]["pore_tri6"] == 178,
            "H0/M1 counts inconsistent")
    for key in ("h0", "m1"):
        mesh = qa[key]
        require(mesh["corner_negative"] == 0 and
                mesh["curved_qp_negative"] == 0 and
                mesh["curved_qp_count"] == mesh["tet10"] * 27 and
                mesh["curved_qp_det_min"] > 0 and
                mesh["global_min_corner_quality"] > .02 and
                mesh["wall_node_max_radial_deviation_m"] < 1e-8 and
                mesh["curved_volume_relative_CAD_error"] < .005,
                "reported full27QP/CAD/quality issue " + key)
    close(qa["element_ratio_M1_over_H0"], 9736 / 7388, "Tet10 ratio")
    median_ratio = (qa["m1"]["global_median_corner_volume_m3"] /
                    qa["h0"]["global_median_corner_volume_m3"])
    close(qa["median_corner_volume_ratio_M1_over_H0"],
          median_ratio, "global unpaired median ratio")
    require(median_ratio < .65 and qa["mesh_refinement_target_about_20pct_broad_gate"] is False,
            "must preserve original median gate STOP")
    require("RADIAL_ISSUES= 0" in stdout and
            "M1_TET10= 9736" in stdout and
            "GLOBAL_VOLUME_RATIO= " in stdout and
            "14145 nodes 11385 elements" in log,
            "Gmsh/QA stdout not coherent")
    dt = (datetime.fromisoformat(m["finished_utc"]) -
          datetime.fromisoformat(m["started_utc"])).total_seconds()
    require(0 <= dt < 120, "unexpected total elapsed time")
    local = verify_radial(qa, radial, bins)
    by_mu = []
    for mu in range(10):
        h0_rows = [r for r in bins if r["mesh"] == "H0" and
                   int(r["mu_bin"]) == mu]
        m1_rows = [r for r in bins if r["mesh"] == "M1" and
                   int(r["mu_bin"]) == mu]
        n0 = sum(int(r["tet10"]) for r in h0_rows)
        n1 = sum(int(r["tet10"]) for r in m1_rows)
        source = {r["radial_band"]: r for r in h0_rows}
        target = {r["radial_band"]: r for r in m1_rows}
        valid = [(int(source[band]["tet10"]),
                  float(target[band]["median_corner_volume_m3"]) /
                  float(source[band]["median_corner_volume_m3"]))
                 for band in BANDS if int(source[band]["tet10"]) > 0 and
                 int(target[band]["tet10"]) > 0]
        by_mu.append({
            "mu_bin": mu, "H0_tet10": n0, "M1_tet10": n1,
            "Tet10_count_ratio": n1 / n0,
            "H0_weighted_mean_matched_radial_bin_median_ratios": (
                sum(n * ratio for n, ratio in valid) / sum(n for n, _ in valid)),
        })
    v0 = qa["h0"]["curved_volume_sum_m3"]
    v1 = qa["m1"]["curved_volume_sum_m3"]
    mean_ratio = (v1 / qa["m1"]["tet10"]) / (v0 / qa["h0"]["tet10"])
    count_ratio = qa["m1"]["tet10"] / qa["h0"]["tet10"]
    require(.65 <= mean_ratio <= .95 and
            sum(s["gated"] for s in local["radial_bands"]) == 5,
            "independent mean-plus-local candidate screen failed")
    return {
        "protocol": "P10DI_READ_ONLY_P10DG_R1_GEOMETRY_STOP_REANALYSIS",
        "original_status_preserved": "P10DG_STOP_NO_FEM/GEOMETRY_QA_STOP",
        "original_only_failure": "global unpaired median Tet10 volume ratio outside 0.65-0.95",
        "h0_mesh_sha256_windows_report": H0_SHA,
        "m1_mesh_sha256_windows_report": m["m1_mesh_sha256"],
        "native_gmsh_exit": m["native_exit_code"],
        "native_gmsh_wall_s": m["wall_seconds"],
        "windows_m1_mesh_size_bytes": m["m1_mesh_size_bytes"],
        "total_launcher_wall_s": dt,
        "H0_Tet10": qa["h0"]["tet10"],
        "M1_Tet10": qa["m1"]["tet10"],
        "H0_pore_Tri6": qa["h0"]["pore_tri6"],
        "M1_pore_Tri6": qa["m1"]["pore_tri6"],
        "H0_reported_curved27QP_samples": qa["h0"]["curved_qp_count"],
        "M1_reported_curved27QP_samples": qa["m1"]["curved_qp_count"],
        "corner_and_curved27QP_quality_reported": "PASS_BOTH_MESHES",
        "native_run_FEM": m["FEM_runs"],
        "unpaired_global_median_volume_ratio": median_ratio,
        "curved_volume_ratio_M1_over_H0": v1 / v0,
        "typical_mean_volume_ratio_from_curved_volume_and_counts": mean_ratio,
        "mean_volume_reduction_percent": (1 - mean_ratio) * 100,
        "Tet10_count_ratio": count_ratio,
        "preexisting_band_gate_issues": qa["radial_volume_gate_issues"],
        "polar_and_all_mu_bin_descriptive_checks": by_mu,
        "reanalysis_under_mean_plus_preexisting_band_ranges": (
            "WOULD_PASS_SCREEN__NOT_ORIGINAL_QA_PASS_OR_FEM_AUTHORIZATION"),
        "limitations": (
            "No raw .msh here. Reported geometry/27QP counts, detJ and mesh SHA "
            "cannot be independently recomputed. Mean volume is a ratio of "
            "total reported curved volumes / Tet10 count; not per-element "
            "matching. Mu-cell ratios are ratios of medians from different "
            "meshes, not elementwise ratios. A posteriori mean-vs-median "
            "criterion change needs an explicit scientific decision."
        ),
        **local,
    }


def load_evidence(original: Path) -> tuple[dict, dict, list[dict],
                                           list[dict], str, str, str, str]:
    require(sha256(original.read_bytes()).hexdigest() == EVIDENCE_SHA,
            "original evidence SHA mismatch")
    with zipfile.ZipFile(original) as z:
        require(z.testzip() is None and
                set(z.namelist()) == FILES and len(z.infolist()) == len(FILES),
                "evidence ZIP CRC or inventory mismatch")
        return (json.loads(z.read("P10DG_RUN_MANIFEST.json")),
                json.loads(z.read("QA/P10DG_H0_M1_MESH_QA.json")),
                csv_bytes(z.read("QA/P10DG_H0_M1_RADIAL_VOLUME_GATE.csv")),
                csv_bytes(z.read("QA/P10DG_H0_M1_RADIAL_MU_BINS.csv")),
                z.read("P10DG_RESULT.txt").decode("utf-8-sig"),
                z.read("P10DG_STOP_TRACE.txt").decode("utf-8-sig"),
                z.read("P10DG_QA_STDOUT_STDERR.txt").decode("utf-8-sig"),
                z.read("P10DG_GMSH_LOG_TAIL.txt").decode("utf-8-sig"))


def package_pins() -> dict:
    require(sha256(PACKAGE.read_bytes()).hexdigest() == PACKAGE_SHA,
            "published source ZIP mismatch")
    with zipfile.ZipFile(PACKAGE) as z:
        require(z.testzip() is None and len(z.namelist()) == 13,
                "source ZIP CRC/inventory mismatch")
        pin = json.loads(z.read("P10DG_PINNED_SHA256.json"))
        for name, expected in pin["files"].items():
            require(sha256(z.read(name)).hexdigest() == expected,
                    "published source SHA mismatch " + name)
        return pin


def selftest(args: tuple, pin: dict) -> None:
    m, qa, radial, bins, result, trace, stdout, log = args
    for desc, alteration in (
        ("unexpected geometry failure", lambda d: d["m1_issues"].append("bad")),
        ("wrong full27QP sample count",
         lambda d: d["m1"].__setitem__("curved_qp_count", 5)),
        ("radial gate extra issue",
         lambda d: d["radial_volume_gate_issues"].append("bad")),
        ("wrong source provenance",
         lambda d: d.__setitem__("h0_sha256", "0" * 64)),
    ):
        bad = copy.deepcopy(qa)
        alteration(bad)
        try:
            verify_reports(m, bad, radial, bins, result, trace, stdout, log, pin)
        except ValueError:
            pass
        else:
            raise AssertionError("negative QA mutation passed: " + desc)
    bad_bins = copy.deepcopy(bins)
    bad_bins[0]["tet10"] = str(int(bad_bins[0]["tet10"]) + 1)
    try:
        verify_reports(m, qa, radial, bad_bins, result, trace, stdout, log, pin)
    except ValueError:
        pass
    else:
        raise AssertionError("negative bin count mutation passed")
    print("P10DI_INDEPENDENT_NEGATIVE_OK QA4_AND_BIN_COUNT1_REJECTED")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", required=True, type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    opts = p.parse_args()
    args = load_evidence(opts.evidence)
    pin = package_pins()
    summary = verify_reports(*args, pin)
    summary["original_zip_sha256"] = EVIDENCE_SHA
    summary["original_zip_size_bytes"] = opts.evidence.stat().st_size
    summary["zip_crc8_and_source_sha12"] = "PASS"
    if opts.selftest:
        selftest(args, pin)
    if opts.out is not None:
        opts.out.parent.mkdir(parents=True, exist_ok=True)
        opts.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
