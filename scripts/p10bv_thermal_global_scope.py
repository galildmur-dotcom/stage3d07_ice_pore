#!/usr/bin/env python3
"""P10BV: independently verify published global H2 thermal shape totals.

Uses prior P10BE summary and P10BT component totals only. This cannot
recover local QP thermal contributions or prove temporal convergence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path

EXPECTED_SHA256 = {
    "summary": "fb7a86246b15577ee0435151cb12c129cdeb89df71b92e9bde1d5af834b1583e",
    "p10bt": "d2d6ce235fb246d6dc15b7a1a7f771a3f35f071ef4770a3ac9cc1736ba348776",
}


def read(path: Path, expected: str) -> dict[int, dict[str, str]]:
    # The archived P10BE CSV and GitHub copy have the same numeric contents,
    # but their byte-level line endings may be LF vs CRLF. Canonicalize ONLY
    # newline bytes before checking; retain original input unmodified.
    canonical = path.read_bytes().replace(b"\r\n", b"\n")
    sha = hashlib.sha256(canonical).hexdigest()
    if sha != expected:
        raise ValueError(f"Canonical-LF SHA-256 mismatch {path}: {sha}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = {int(r["dt_s"]): r for r in rows}
    if len(rows) != 4 or set(result) != {150, 75, 50, 25}:
        raise ValueError(f"Unexpected schedules in {path}")
    return result


def approx(a: float, b: float, note: str) -> None:
    if not math.isfinite(a) or abs(a-b) > 8e-13:
        raise AssertionError(f"{note} {a:.17g} != {b:.17g}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--p10be-summary", type=Path, required=True)
    ap.add_argument("--p10bt-totals", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.resolve() in (a.p10be_summary.parent.resolve(), a.p10bt_totals.parent.resolve()):
        raise ValueError("Output must not replace source folder")
    summary = read(a.p10be_summary, EXPECTED_SHA256["summary"])
    totals = read(a.p10bt_totals, EXPECTED_SHA256["p10bt"])
    rows = []
    for dt in (150, 75, 50, 25):
        p = summary[dt]
        q = totals[dt]
        if p["mesh"] != "H2" or int(p["steps"])*dt != 900:
            raise ValueError("Wrong mesh or time horizon")
        mechanical = float(p["global_mechanical_dR"])
        thermal = float(p["global_thermal_dR"])
        total = float(p["global_total_dR"])
        nearwall = float(p["nearwall_mechanical_dR"])
        approx(mechanical+thermal, total, f"total dt={dt}")
        for key, val in (("global_mechanical", mechanical),
                         ("global_thermal", thermal),
                         ("global_total", total),
                         ("total_mechanical", nearwall)):
            approx(float(q[key]), val, f"P10BT parity {key} dt={dt}")
        rows.append({
            "dt_s": dt,
            "steps": int(p["steps"]),
            "global_mechanical_per_m": mechanical,
            "global_thermal_per_m": thermal,
            "global_total_per_m": total,
            "global_thermal_fraction_percent": 100*thermal/total,
            "nearwall_mechanical_per_m": nearwall,
            "published_local_thermal_qp": "NOT_EXPORTED",
            "published_step_thermal": "NOT_EXPORTED",
        })
    # The monotonicity statement is about the four *reported numbers* only.
    if not all(rows[i]["global_thermal_per_m"] < rows[i+1]["global_thermal_per_m"]
               for i in range(3)):
        raise AssertionError("Thermal global sequence unexpectedly non-monotone")
    diffs = {
        k: rows[0][k]-rows[-1][k]
        for k in ("global_mechanical_per_m", "global_thermal_per_m",
                  "global_total_per_m", "nearwall_mechanical_per_m")
    }
    approx(diffs["global_mechanical_per_m"]+diffs["global_thermal_per_m"],
           diffs["global_total_per_m"], "150-25 difference")
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "P10BV_GLOBAL_THERMAL_SCOPE.csv"
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "P10BV H2 P10BE/P10BT GLOBAL THERMAL SCOPE (READ ONLY)",
        f"P10BE_CANONICAL_LF_SHA256={EXPECTED_SHA256['summary']}",
        f"P10BT_CANONICAL_LF_SHA256={EXPECTED_SHA256['p10bt']}",
        "MESH=H2 HORIZON_S=900 CASES=4",
        *(f"DT{r['dt_s']}_THERMAL_PER_M={r['global_thermal_per_m']:.15g}"
          for r in rows),
        *(f"DELTA_150_MINUS_25_{k.upper()}={v:+.12f}"
          for k, v in diffs.items()),
        "GLOBAL_THERMAL_SEQUENCE_DT150_75_50_25=STRICT_INCREASING",
        "P10BV_GLOBAL_THERMAL_ARITHMETIC_OK",
        "LOCAL_THERMAL_QP=NOT_EXPORTED",
        "TIMESTEP_THERMAL_COMPONENTS=NOT_EXPORTED",
        "FEM=0 HISTORIC_EXE_SHA=UNKNOWN CONVERGENCE_PROVEN=NO",
    ]
    text = "\n".join(lines)+"\n"
    (a.out / "P10BV_GLOBAL_RESULT.txt").write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
