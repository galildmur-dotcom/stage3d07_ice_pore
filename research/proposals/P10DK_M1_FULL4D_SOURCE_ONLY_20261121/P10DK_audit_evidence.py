"""Independent stdlib verifier of one future P10DK M1 4D evidence directory/ZIP.

M1=9736 Tet10 is hard-pinned, unlike the old P10DD H0 7388 Tet10.
Only scientific CSV rows are read: no mesh, history, EXE or FEM is opened.
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


FIELDS = (
    "mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
    "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m",
)
FILE4D = "P10DD_SIGNED_R_THETA_PHI_T.csv"
EXPECTED_TET10 = 9736
EXPECTED_MESH_STEM = "P10DG_M1_CANDIDATE"


class Reader:
    def __init__(self, source: Path):
        self.source = source
        self.archive = zipfile.ZipFile(source) if source.is_file() else None

    def csv(self, name: str) -> list[dict[str, str]]:
        if self.archive is None:
            content = (self.source / name).read_text(encoding="utf-8-sig")
        else:
            content = self.archive.read(name).decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(content)))

    def close(self) -> None:
        if self.archive:
            self.archive.close()


def closeness(a: float, b: float, name: str) -> None:
    scale = max(1e-10, abs(a), abs(b))
    if not math.isfinite(a) or not math.isfinite(b) or abs(a - b) > 1e-9 + 2e-8 * scale:
        raise AssertionError(f"{name}: {a:.17g} != {b:.17g}")


def audit(reader: Reader) -> dict[str, float]:
    rows = reader.csv(FILE4D)
    global_components = reader.csv("P10W_COMPONENTS.csv")
    global_gradient = reader.csv("P10W_ANALYTIC_ADJOINT.csv")
    timed = reader.csv("P10W_STEP_COMPONENTS.csv")
    summary = reader.csv("P10DD_FULL4D_CLOSURE_AUDIT.csv")
    if len(rows) != 7206 or len(summary) != 6:
        raise AssertionError(f"wrong 4D/audit row count {len(rows)}/{len(summary)}")
    reference = next(x for x in global_components if x["functional"] == "jpeak")
    ref_gradient = next(x for x in global_gradient if x["functional"] == "jpeak")
    by_time = defaultdict(list)
    for row in rows:
        if row.get("mesh") != EXPECTED_MESH_STEM:
            raise AssertionError("wrong M1 mesh stem: " + str(row.get("mesh")))
        if row["mode"] != "R" or row["functional"] != "jpeak":
            raise AssertionError("wrong shape mode or functional")
        step = int(row["step"])
        if step not in range(1, 7) or int(row["time_end_s"]) != step * 150:
            raise AssertionError("invalid step/time bin")
        by_time[step].append(row)
        vals = [float(row[name]) for name in FIELDS]
        closeness(sum(vals[:3]), float(row["mechanical_total_per_m"]), "row mechanical")
        closeness(sum(vals[3:]), float(row["thermal_total_per_m"]), "row thermal")
        closeness(sum(vals), float(row["total_per_m"]), "row total")
        if any(not math.isfinite(v) for v in vals):
            raise AssertionError("nonfinite signed contribution")
    fields_total = [0.] * 6
    for step in range(1, 7):
        data = by_time[step]
        if len(data) != 1201:
            raise AssertionError(f"step {step} has {len(data)} rows instead of 1201")
        volumes = [r for r in data if r["region"] == "VOLUME"]
        tops = [r for r in data if r["region"] == "TOP_ROBIN"]
        if len(volumes) != 1200 or len(tops) != 1:
            raise AssertionError("missing or repeated Robin boundary row")
        keys = [(int(r["radial_bin"]), int(r["mu_bin"]), int(r["phi_bin"])) for r in volumes]
        if len(set(keys)) != 1200 or any(not (0 <= a < 10 and 0 <= b < 10 and 0 <= c < 12)
                                           for a, b, c in keys):
            raise AssertionError("incomplete 10x10x12 spatial bins")
        if (sum(int(r["mechanical_qp"]) for r in volumes) != EXPECTED_TET10 * 27 or
                sum(int(r["thermal_qp"]) for r in volumes) != EXPECTED_TET10 * 64):
            raise AssertionError("missing Tet10 QPs: not the accepted P10DG M1")
        if int(tops[0]["top_robin_qp"]) == 0:
            raise AssertionError("top Robin boundary quadrature absent")
        components = [math.fsum(float(r[f]) for r in data) for f in FIELDS]
        fields_total = [a + b for a, b in zip(fields_total, components)]
        official_step = next(r for r in timed if r["functional"] == "jpeak" and
                             int(r["time_step"]) == step)
        for j, field in enumerate(("explicit_objective_shape_per_m",
                                   "equilibrium_residual_shape_per_m",
                                   "internal_history_shape_per_m")):
            closeness(components[j], float(official_step[field]), f"mechanical step {step} {field}")
        audit_step = next(r for r in summary if int(r["step"]) == step)
        closeness(sum(components[:3]), float(audit_step["mechanical_total_per_m"]),
                  f"step {step} mechanical audit")
        closeness(sum(components[3:]), float(audit_step["thermal_total_per_m"]),
                  f"step {step} thermal audit")
    for a, b in zip(fields_total[:3], (float(reference["explicit_objective_shape_per_m"]),
                                       float(reference["equilibrium_residual_shape_per_m"]),
                                       float(reference["internal_history_shape_per_m"]))):
        closeness(a, b, "global mechanical component")
    mechanical = sum(fields_total[:3])
    thermal = sum(fields_total[3:])
    total = mechanical + thermal
    closeness(mechanical, float(reference["total_mechanical_shape_per_m"]), "global mechanical")
    closeness(thermal, float(reference["thermal_adjoint_per_m"]), "global thermal")
    closeness(total, float(reference["total_adjoint_per_m"]), "global total")
    closeness(total, float(ref_gradient["total_adjoint_per_m"]), "gradient CSV")
    return {"mechanical": mechanical, "thermal": thermal, "total": total}


def selftest() -> None:
    closeness(.7 - .2, .5, "ordinary signed test")
    try:
        closeness(0., 1., "negative corrupted closure")
    except AssertionError:
        print("P10DK_PY_AUDIT_SYNTHETIC_OK negative_closure=DETECTED")
    else:
        raise AssertionError("negative closure was not detected")
    # Synthetic full 7206-row schema: verifies bin bookkeeping and independent
    # step/global comparison logic. THIS IS NOT A PHYSICAL M1 MEASUREMENT.
    fourd = []
    steps = []
    summaries = []
    for step in range(1, 7):
        for ir in range(10):
            for im in range(10):
                for ip in range(12):
                    primary = ir == im == ip == 0
                    vals = (.1, -.3, .5, -.04, .01, 0.) if primary else (0.,) * 6
                    fourd.append({
                        "mesh": EXPECTED_MESH_STEM, "mode": "R",
                        "functional": "jpeak", "step": str(step),
                        "time_end_s": str(step * 150), "region": "VOLUME",
                        "radial_bin": str(ir), "mu_bin": str(im), "phi_bin": str(ip),
                        "mechanical_qp": str(EXPECTED_TET10 * 27 if primary else 0),
                        "thermal_qp": str(EXPECTED_TET10 * 64 if primary else 0),
                        **dict(zip(FIELDS, map(str, vals))),
                        "mechanical_total_per_m": str(sum(vals[:3])),
                        "thermal_total_per_m": str(sum(vals[3:])),
                        "total_per_m": str(sum(vals)),
                    })
        top = dict(fourd[-1])
        top.update({"region": "TOP_ROBIN", "top_robin_qp": "16",
                    "mechanical_qp": "0", "thermal_qp": "0",
                    **{name: "0" for name in FIELDS},
                    "thermal_robin_per_m": ".005",
                    "mechanical_total_per_m": "0",
                    "thermal_total_per_m": ".005", "total_per_m": ".005"})
        fourd.append(top)
        steps.append({"functional": "jpeak", "time_step": str(step),
                      "explicit_objective_shape_per_m": ".1",
                      "equilibrium_residual_shape_per_m": "-.3",
                      "internal_history_shape_per_m": ".5"})
        summaries.append({"step": str(step), "mechanical_total_per_m": ".3",
                          "thermal_total_per_m": "-.025"})
    components = [{"functional": "jpeak", "explicit_objective_shape_per_m": ".6",
                   "equilibrium_residual_shape_per_m": "-1.8",
                   "internal_history_shape_per_m": "3",
                   "total_mechanical_shape_per_m": "1.8",
                   "thermal_adjoint_per_m": "-.15", "total_adjoint_per_m": "1.65"}]

    class FakeReader:
        def csv(self, name: str) -> list[dict[str, str]]:
            return {FILE4D: fourd, "P10W_COMPONENTS.csv": components,
                    "P10W_ANALYTIC_ADJOINT.csv": components,
                    "P10W_STEP_COMPONENTS.csv": steps,
                    "P10DD_FULL4D_CLOSURE_AUDIT.csv": summaries}[name]

    ok = audit(FakeReader())
    closeness(ok["total"], 1.65, "synthetic full 4D")
    old = fourd[0]["total_per_m"]
    fourd[0]["total_per_m"] = "999"
    try:
        audit(FakeReader())
    except AssertionError:
        pass
    else:
        raise AssertionError("corrupted 4D row was not detected")
    fourd[0]["total_per_m"] = old
    # An inherited H0 QP count must not slip into an M1 report.
    fourd[0]["mechanical_qp"] = str(7388 * 27)
    try:
        audit(FakeReader())
    except AssertionError:
        pass
    else:
        raise AssertionError("H0 mechanical QP substitution was not detected")
    fourd[0]["mechanical_qp"] = str(EXPECTED_TET10 * 27)
    fourd[0]["mesh"] = "H0"
    try:
        audit(FakeReader())
    except AssertionError:
        pass
    else:
        raise AssertionError("wrong H0 mesh label was not detected")
    fourd[0]["mesh"] = EXPECTED_MESH_STEM
    print("P10DK_PY_7206_SYNTHETIC_ROWS_OK negative_row=DETECTED "
          "H0_QP_SUBSTITUTION=DETECTED H0_MESH_LABEL=DETECTED physical_FEM=0")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path)
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.source or not args.source.exists():
        raise ValueError("provide --source P10DK_EVIDENCE.zip or M1 output folder")
    reader = Reader(args.source)
    try:
        result = audit(reader)
    finally:
        reader.close()
    print("P10DK_INDEPENDENT_M1_4D_CLOSURE_OK", result)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("P10DK_AUDIT_STOP:", exc, file=sys.stderr)
        raise SystemExit(2)
