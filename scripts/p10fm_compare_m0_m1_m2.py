#!/usr/bin/env python3
"""Compare three physically measured, signed 4D R-shape gradients on common bins.

Only R/EDV_VAR/xi=0/6x150/B6=5mm is observed here. No interpolation, FEM or FD.
All outputs are reproducible from two original evidence ZIPs plus P10FL ZIP.
"""
import argparse
import csv
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "M0": ROOT / "research/evidence/P10DD_H0_FULL4D_20261121/input/P10DD_EVIDENCE.zip",
    "M1": ROOT / "research/evidence/P10DM_P10DL_REAL_M1_H0_PAIR_20261121/input/P10DL_EVIDENCE.zip",
    "M2": ROOT / "research/packages/P10FL_M2_R1_SIGNED_4D_EVIDENCE_20261122.zip",
}
TETS = {"M0": 7388, "M1": 9736, "M2": 10094}
MESHES = {"M0": "H0", "M1": "P10DG_M1_CANDIDATE", "M2": "P10EA_M2_CANDIDATE"}
FIELDS = (
    "mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
    "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m",
)
TOTAL = "total_per_m"
KEYS = ("step", "region", "radial_bin", "mu_bin", "phi_bin")
GEOMETRY = ("r_lower_mm", "r_upper_mm", "theta_lower_rad", "theta_upper_rad",
            "phi_lower_rad", "phi_upper_rad", "time_start_s", "time_end_s")


def read_zip(path, filename):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, f"CRC error: {path}"
        return list(csv.DictReader(io.StringIO(z.read(filename).decode("utf-8-sig"))))


def close(x, y, title, atol=3e-9):
    assert math.isfinite(x) and math.isfinite(y) and abs(x-y) <= atol + 2e-8 * max(abs(x), abs(y)), (title, x, y)


def key(row):
    return tuple(row[k] for k in KEYS)


def axis_key(row, axis):
    if axis == "t":
        return int(row["step"])
    return int(row[{"r": "radial_bin", "mu": "mu_bin", "phi": "phi_bin"}[axis]])


def read_mesh(name, path):
    rows = read_zip(path, "P10DD_SIGNED_R_THETA_PHI_T.csv")
    assert len(rows) == 7206
    assert all(r["mesh"] == MESHES[name] and r["mode"] == "R" and r["functional"] == "jpeak" for r in rows)
    data = {key(r): r for r in rows}
    assert len(data) == 7206
    for step in range(1, 7):
        part = [r for r in rows if int(r["step"]) == step]
        volumes = [r for r in part if r["region"] == "VOLUME"]
        robin = [r for r in part if r["region"] == "TOP_ROBIN"]
        assert len(volumes) == 1200 and len(robin) == 1
        assert sum(int(r["mechanical_qp"]) for r in volumes) == TETS[name]*27
        assert sum(int(r["thermal_qp"]) for r in volumes) == TETS[name]*64
    component_rows = read_zip(path, "P10W_COMPONENTS.csv")
    gradient_rows = read_zip(path, "P10W_ANALYTIC_ADJOINT.csv")
    component = {r["functional"]: r for r in component_rows}
    gradients = {r["functional"]: r for r in gradient_rows}
    assert set(component) == set(gradients) == {"j6", "jpeak", "jen"}
    totals = {f: math.fsum(float(r[f]) for r in rows) for f in (*FIELDS, TOTAL)}
    for f, column in [("mech_explicit_per_m", "explicit_objective_shape_per_m"),
                      ("mech_equilibrium_per_m", "equilibrium_residual_shape_per_m"),
                      ("mech_history_per_m", "internal_history_shape_per_m")]:
        close(totals[f], float(component["jpeak"][column]), name+f)
    close(totals[TOTAL], float(gradients["jpeak"]["total_adjoint_per_m"]), name+" gradient")
    return data, component, gradients, totals


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m2", type=Path, default=INPUTS["M2"])
    parser.add_argument("--out", type=Path,
                        default=ROOT / "research/evidence/P10FM_M0_M1_M2_R_4D_20261122/derived")
    args = parser.parse_args()
    inputs = dict(INPUTS, M2=args.m2)
    evidence = {name: read_mesh(name, path) for name, path in inputs.items()}
    data = {name: x[0] for name, x in evidence.items()}
    assert set(data["M0"]) == set(data["M1"]) == set(data["M2"])
    for k in data["M0"]:
        reference = data["M0"][k]
        for name in ("M1", "M2"):
            other = data[name][k]
            for field in GEOMETRY:
                assert reference[field] == other[field], (name, k, field, reference[field], other[field])
    args.out.mkdir(parents=True, exist_ok=True)

    global_rows = []
    for f in ("j6", "jpeak", "jen"):
        for field, column in (("objective", "objective"),
                              ("explicit", "explicit_objective_shape_per_m"),
                              ("equilibrium", "equilibrium_residual_shape_per_m"),
                              ("history", "internal_history_shape_per_m"),
                              ("mechanical", "total_mechanical_shape_per_m"),
                              ("thermal", "thermal_adjoint_per_m"),
                              ("total", "total_adjoint_per_m")):
            vals = {name: float(evidence[name][1][f][column]) for name in ("M0", "M1", "M2")}
            global_rows.append({"functional": f, "component": field, **vals,
                                "M1_minus_M0": vals["M1"]-vals["M0"],
                                "M2_minus_M1": vals["M2"]-vals["M1"],
                                "M2_minus_M0": vals["M2"]-vals["M0"],
                                "M1_M0_pct": 100*(vals["M1"]-vals["M0"])/abs(vals["M0"]) if vals["M0"] else "",
                                "M2_M1_pct": 100*(vals["M2"]-vals["M1"])/abs(vals["M1"]) if vals["M1"] else ""})
    write_csv(args.out / "P10FM_GLOBAL_ALL_FUNCTIONALS.csv", global_rows, list(global_rows[0]))

    by_bin = []
    for k in sorted(data["M0"], key=lambda k: (int(k[0]), k[1], int(k[2] or -1), int(k[3] or -1), int(k[4] or -1))):
        row = data["M0"][k]
        record = {name: row[name] for name in (*KEYS, *GEOMETRY)}
        for f in (*FIELDS, TOTAL):
            values = {name: float(data[name][k][f]) for name in ("M0", "M1", "M2")}
            for name, v in values.items():
                record[f+"_"+name] = v
            record[f+"_M1_minus_M0"] = values["M1"]-values["M0"]
            record[f+"_M2_minus_M1"] = values["M2"]-values["M1"]
            record[f+"_M2_minus_M0"] = values["M2"]-values["M0"]
        for name in ("M0", "M1", "M2"):
            for field in ("mechanical_qp", "thermal_qp"):
                record[field+"_"+name] = int(data[name][k][field])
        by_bin.append(record)
    write_csv(args.out / "P10FM_SIGNED_ALL_4D_BINS.csv", by_bin, list(by_bin[0]))

    projections = []
    volumes = [k for k in data["M0"] if k[1] == "VOLUME"]
    for axis in ("r", "mu", "phi", "t"):
        indices = sorted({axis_key(data["M0"][k], axis) for k in volumes})
        for index in indices:
            keys = [k for k in volumes if axis_key(data["M0"][k], axis) == index]
            for field in (*FIELDS, TOTAL):
                s = {name: math.fsum(float(data[name][k][field]) for k in keys)
                     for name in ("M0", "M1", "M2")}
                projections.append({"axis": axis, "bin": index, "component": field,
                                    **s, "M1_minus_M0": s["M1"]-s["M0"],
                                    "M2_minus_M1": s["M2"]-s["M1"],
                                    "M2_minus_M0": s["M2"]-s["M0"],
                                    "abs_delta_M1_M0": math.fsum(abs(float(data["M1"][k][field])-float(data["M0"][k][field])) for k in keys),
                                    "abs_delta_M2_M1": math.fsum(abs(float(data["M2"][k][field])-float(data["M1"][k][field])) for k in keys)})
    write_csv(args.out / "P10FM_AXIS_PROJECTIONS.csv", projections, list(projections[0]))

    diagnostics = {"mesh": {name: {"tet10": TETS[name], "mesh": MESHES[name]} for name in data}}
    for old, new in (("M0", "M1"), ("M1", "M2"), ("M0", "M2")):
        delta = {k: float(data[new][k][TOTAL])-float(data[old][k][TOTAL]) for k in volumes}
        l1 = math.fsum(abs(x) for x in delta.values())
        near = {k for k in volumes if int(k[2]) <= 2}
        polar = {k for k in volumes if int(k[3]) in (0, 9)}
        late = {k for k in volumes if int(k[0]) >= 5}
        def share(keys):
            return 100*math.fsum(abs(delta[k]) for k in keys)/l1 if l1 else 0.
        diagnostics[f"{old}_to_{new}"] = {
            "signed_total_delta": evidence[new][3][TOTAL]-evidence[old][3][TOTAL],
            "sum_absolute_volume_bin_deltas": l1,
            "share_polar_extreme_pct": share(polar),
            "share_first_0p1_mm_pct": share(near),
            "share_last_300_s_pct": share(late),
            "share_polar_near_late_intersection_pct": share(polar & near & late),
            "empty_mechanical_bins_old": sum(int(data[old][k]["mechanical_qp"])==0 for k in volumes),
            "empty_mechanical_bins_new": sum(int(data[new][k]["mechanical_qp"])==0 for k in volumes),
            "opposite_signed_nonzero_bins": sum(delta[k] != 0 and float(data[new][k][TOTAL])*float(data[old][k][TOTAL]) < 0 for k in volumes),
        }
    (args.out / "P10FM_DIAGNOSTICS.json").write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("P10FM_THREE_REAL_MESH_SIGNED_4D_COMPARE_OK", json.dumps(diagnostics, ensure_ascii=False))


if __name__ == "__main__":
    main()
