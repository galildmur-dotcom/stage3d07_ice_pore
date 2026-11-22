#!/usr/bin/env python3
"""Independent M0 signed 4D physical decomposition and M1 handoff audit.

Reads the *observed* P10FN_M0_R_PHYSICS_EVIDENCE.zip, no solver/Gmsh.
All statistics preserve signed terms; zero bins are retained.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "research/proposals/P10FP_FROM_M0_WINDOWS_20261122"))
from P10FN_physics_audit import audit as independent_4d_audit  # noqa: E402

EXPECTED_M0 = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
EXPECTED_GEO = "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa"
FIELDS = ("mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
          "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m",
          "mechanical_total_per_m", "thermal_total_per_m", "total_per_m")


def load_csv(folder, name):
    with (folder/name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def summarize(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    out = []
    for label, records in sorted(groups.items(), key=lambda x:x[0]):
        signed = math.fsum(float(r["total_per_m"]) for r in records)
        absolute = math.fsum(abs(float(r["total_per_m"])) for r in records)
        result = {"index":label, "rows":len(records),
                  "total_per_m":signed, "sum_abs_bin_total_per_m":absolute,
                  "mechanical_per_m":math.fsum(float(r["mechanical_total_per_m"]) for r in records),
                  "thermal_per_m":math.fsum(float(r["thermal_total_per_m"]) for r in records),
                  "mechanical_qp":sum(int(r["mechanical_qp"]) for r in records),
                  "thermal_qp":sum(int(r["thermal_qp"]) for r in records)}
        out.append(result)
    return out


def plot_signed_axes(report, path):
    """Scientific figure: signed 4D components, not absolute magnitudes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = (("by_radial", "Distance from pore wall, mm",
            ["0-.02",".02-.05",".05-.10",".10-.25",".25-.50",".5-1","1-2","2-5","5-15",">15"]),
           ("by_polar", "Polar band (0=south, 9=north)",None),
           ("by_azimuth", "Azimuth sector (12 bins)",None),
           ("by_time", "Time interval end, s",None))
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.5), constrained_layout=True)
    for ax, (key, xlabel, labels) in zip(axes.ravel(), cfg):
        series = report["signed4d"][key]
        xs = list(range(len(series)))
        y = [r["total_per_m"] for r in series]
        lab = labels if labels is not None else ([str(150*r["index"]) for r in series]
            if key == "by_time" else [str(r["index"]) for r in series])
        ax.bar(xs,y,color=["#b43e48" if x<0 else "#236c9b" for x in y],width=.76)
        ax.axhline(0,color="#38424a",lw=.9)
        ax.set_xticks(xs, lab, rotation=40 if key=="by_radial" else 0,
                      ha="right" if key=="by_radial" else "center")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Signed contribution to D_R jpeak, 1/m")
        ax.grid(axis="y",alpha=.22)
        ax.set_title({"by_radial":"Radial", "by_polar":"Polar",
                      "by_azimuth":"Azimuthal", "by_time":"Temporal"}[key])
    fig.suptitle("Stage3D07 P10FS: fresh M0, analytic shape derivative R\n"
                 "Blue = positive, red = negative; signed sum = +2.913621864 /m", fontsize=14)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--evidence-zip",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--figure",type=Path)
    args = parser.parse_args()
    folder = args.folder
    manifest = json.loads((folder/"P10FN_PHYSICS_MANIFEST.json").read_text(encoding="utf-8-sig"))
    if (manifest["status"] != "PHYSICS_REAL_4D_INDEPENDENT_CLOSURE_PASS"
            or manifest["mesh"] != "M0" or manifest["mode"] != "R"
            or manifest["mesh_sha256"] != EXPECTED_M0
            or manifest["approval"]["baseline_geo_sha256"] != EXPECTED_GEO
            or manifest["native_exit_code"] != 0 or manifest["stop_reason"]
            or not manifest["fresh_forward"] or manifest["reuse_forward"]
            or manifest["FEM_attempts"] != 1):
        raise RuntimeError("not a valid first fresh-M0 physics result")
    digest = hashlib.sha256(args.evidence_zip.read_bytes()).hexdigest()
    result = independent_4d_audit(folder,"M0",7992,"R")
    if abs(result["total"]-manifest["independent_4d"]["total"]) > 1.e-9:
        raise ValueError("4D independently recalculated total mismatch")
    log = (folder/"P10FN_SOLVER_STDOUT_STDERR.txt").read_text(encoding="utf-8-sig")
    for mark in ("P10W_ANALYTIC_ADJOINT_OK", "central_fd_evaluations=0",
                 "nonlinear_forward_solves=1", "mechanical_adjoint_solves=18",
                 "P10DD_FULL4D_CLOSURE_OK"):
        if mark not in log:
            raise ValueError("missing production log proof: " + mark)
    final = load_csv(folder,"P10W_ANALYTIC_ADJOINT.csv")
    components = load_csv(folder,"P10W_COMPONENTS.csv")
    if {r["functional"] for r in final} != {"j6","jpeak","jen"}:
        raise ValueError("not all three approved functionals present")
    bins = load_csv(folder,"P10DD_SIGNED_R_THETA_PHI_T.csv")
    vol = [r for r in bins if r["region"] == "VOLUME"]
    if len(vol) != 7200 or len(bins) != 7206:
        raise ValueError("wrong signed 4D volume coverage")
    for r in bins:
        for f in FIELDS:
            if not math.isfinite(float(r[f])):
                raise ValueError("NaN/inf signed component: " + f)
    global_deriv = {r["functional"]:{k:float(r[k]) for k in
                    ("objective", "mechanical_partial_per_m", "thermal_adjoint_per_m",
                     "total_adjoint_per_m", "mechanical_equilibrium_rel", "thermal_equilibrium_rel")}
                    for r in final}
    component = {r["functional"]:{k:float(r[k]) for k in
                    ("explicit_objective_shape_per_m", "equilibrium_residual_shape_per_m",
                     "internal_history_shape_per_m", "total_mechanical_shape_per_m",
                     "thermal_adjoint_per_m", "total_adjoint_per_m", "cancellation_ratio")}
                 for r in components}
    focus = [r for r in vol if int(r["radial_bin"]) <= 4 and int(r["mu_bin"]) in (0,9)]
    polar_focus = summarize(focus,lambda _r:0)[0]
    volume_global = summarize(vol,lambda _r:0)[0]
    report = {
        "protocol":"P10FS_FRESH_M0_SIGNED_R_4D_POSTRUN_INDEPENDENT",
        "evidence_zip_sha256":digest,
        "mesh_sha256":EXPECTED_M0,
        "baseline_geo_sha256":EXPECTED_GEO,
        "result":"PASS_PHYSICAL_M0_READY_FOR_SHA_PINNED_UNIFORM_M1_RECIPE",
        "runtime_seconds":manifest["wall_s"],
        "peak_private_memory_bytes":manifest["peak_private_bytes_polled"],
        "fresh_forward":True,
        "forward_solves":1,
        "mechanical_adjoint_solves":18,
        "central_fd_evaluations":0,
        "independent_4d":result,
        "functionals":global_deriv,
        "components":component,
        "signed4d":{
            "by_time":summarize(bins,lambda r:int(r["step"])),
            "by_radial":summarize(vol,lambda r:int(r["radial_bin"])),
            "by_polar":summarize(vol,lambda r:int(r["mu_bin"])),
            "by_azimuth":summarize(vol,lambda r:int(r["phi_bin"])),
            "by_region":summarize(bins,lambda r:r["region"]),
            "near_polar_d_le_0p5mm_bins_0_and_9":polar_focus,
            "volume_global":volume_global
        },
        "note":"No convergence statement is possible from a single new-series M0."
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.figure:
        plot_signed_axes(report,args.figure)
    print(json.dumps({"result":report["result"],"evidence_sha":digest,
                      "global":global_deriv,"focus":polar_focus,
                      "time":[(r["index"],r["total_per_m"]) for r in report["signed4d"]["by_time"]]},
                     indent=2,ensure_ascii=False))


if __name__ == "__main__":
    main()
