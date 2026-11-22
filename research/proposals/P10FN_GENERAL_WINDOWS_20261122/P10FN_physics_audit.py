"""Standalone source-independent closure check for signed R/tz/y20 4D outputs."""
from collections import defaultdict
import csv
import math
from pathlib import Path

FIELDS = ("mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
          "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m")


def rows(folder, name):
    with (Path(folder)/name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def close(a, b, label):
    if not (math.isfinite(a) and math.isfinite(b)) or abs(a-b) > 1e-9 + 2e-8*max(abs(a),abs(b)):
        raise ValueError(f"{label}: {a} differs from {b}")


def audit(folder, mesh_name, tet10, mode):
    data = rows(folder, "P10DD_SIGNED_R_THETA_PHI_T.csv")
    total = rows(folder, "P10W_COMPONENTS.csv")
    adj = rows(folder, "P10W_ANALYTIC_ADJOINT.csv")
    step = rows(folder, "P10W_STEP_COMPONENTS.csv")
    summary = rows(folder, "P10DD_FULL4D_CLOSURE_AUDIT.csv")
    if len(data) != 7206 or len(summary) != 6:
        raise ValueError("7206 signed bins/6 closure rows not present")
    if not any(r["functional"] == "jpeak" for r in total):
        raise ValueError("jpeak missing")
    by_step = defaultdict(list)
    for r in data:
        if r["mesh"] != mesh_name or r["mode"] != mode or r["functional"] != "jpeak":
            raise ValueError("mesh/mode/functional label mismatch")
        s = int(r["step"])
        if s not in range(1, 7) or int(r["time_end_s"]) != 150*s:
            raise ValueError("invalid time grid")
        by_step[s].append(r)
        parts = [float(r[k]) for k in FIELDS]
        close(math.fsum(parts[:3]), float(r["mechanical_total_per_m"]), "row mech")
        close(math.fsum(parts[3:]), float(r["thermal_total_per_m"]), "row thermal")
        close(math.fsum(parts), float(r["total_per_m"]), "row signed")
    aggregate = [0.]*6
    for s in range(1, 7):
        these = by_step[s]
        if len(these) != 1201:
            raise ValueError("wrong bins per step")
        vol = [r for r in these if r["region"] == "VOLUME"]
        robin = [r for r in these if r["region"] == "TOP_ROBIN"]
        if len(vol) != 1200 or len(robin) != 1:
            raise ValueError("missing top robin row")
        triples = {(int(r["radial_bin"]),int(r["mu_bin"]),int(r["phi_bin"])) for r in vol}
        if len(triples) != 1200:
            raise ValueError("spatial 10x10x12 coverage incomplete")
        if sum(int(r["mechanical_qp"]) for r in vol) != tet10*27:
            raise ValueError("mechanical QP count does not match mesh")
        if sum(int(r["thermal_qp"]) for r in vol) != tet10*64:
            raise ValueError("thermal QP count does not match mesh")
        if int(robin[0]["top_robin_qp"]) <= 0:
            raise ValueError("Robin QP missing")
        vals = [math.fsum(float(r[field]) for r in these) for field in FIELDS]
        aggregate = [a+b for a,b in zip(aggregate, vals)]
        official = [r for r in step if r["functional"] == "jpeak" and int(r["time_step"]) == s]
        if len(official) != 1:
            raise ValueError("jpeak component step missing")
        for i, field in enumerate(("explicit_objective_shape_per_m",
                                    "equilibrium_residual_shape_per_m",
                                    "internal_history_shape_per_m")):
            close(vals[i],float(official[0][field]),"step mechanical "+field)
        matching = [r for r in summary if int(r["step"]) == s]
        if len(matching) != 1:
            raise ValueError("closure step missing")
        close(math.fsum(vals[:3]),float(matching[0]["mechanical_total_per_m"]),"audit mech step")
        close(math.fsum(vals[3:]),float(matching[0]["thermal_total_per_m"]),"audit thermal step")
    official = next(r for r in total if r["functional"] == "jpeak")
    reference = next(r for r in adj if r["functional"] == "jpeak")
    for i, field in enumerate(("explicit_objective_shape_per_m",
                               "equilibrium_residual_shape_per_m",
                               "internal_history_shape_per_m")):
        close(aggregate[i],float(official[field]),"global "+field)
    mechanical = math.fsum(aggregate[:3])
    thermal = math.fsum(aggregate[3:])
    result = mechanical+thermal
    close(mechanical,float(official["total_mechanical_shape_per_m"]),"global mech")
    close(thermal,float(official["thermal_adjoint_per_m"]),"global thermal")
    close(result,float(official["total_adjoint_per_m"]),"global total")
    close(result,float(reference["total_adjoint_per_m"]),"official adjoint")
    return {"status": "P10FN_INDEPENDENT_4D_CLOSURE_PASS", "mechanical": mechanical,
            "thermal": thermal, "total": result, "rows": 7206, "tet10": tet10,
            "mode": mode, "mesh": mesh_name}
