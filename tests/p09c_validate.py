#!/usr/bin/env python3
"""Independent GH3 arithmetic check of Stage3D09C output tables.

Usage: python tests/p09c_validate.py PATH_TO_P09C_RESULT_FOLDER
Optional: --reference PATH_TO_P08D_SENSITIVITIES.csv
No external packages required. Does not touch or modify files.
"""
import argparse
import csv
import math
from pathlib import Path

W = (1 / 6, 2 / 3, 1 / 6)
XI = (-math.sqrt(3), 0.0, math.sqrt(3))
FUNS = ("j6", "jpeak", "jen")


def records(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def approx(x, y, rtol=5e-8, atol=1e-11):
    if not math.isclose(x, y, abs_tol=atol, rel_tol=rtol):
        raise AssertionError(f"Mismatch: actual={x:.17g}, expected={y:.17g}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    folder = args.folder
    samples = records(folder / "P09C_SAMPLES.csv")
    nodes = records(folder / "P09C_NODES.csv")
    summary = records(folder / "P09C_SENSITIVITIES.csv")
    assert "status=SUCCESS" in (folder / "P09C_STATUS.txt").read_text()
    lookup = {}
    for r in samples:
        key = (r["mode"], r["law"], r["modulus"], r["sign"])
        assert math.isfinite(float(r["j6"]))
        lookup.setdefault(key, {})[float(r["xi"])] = r
        assert int(r["steps"]) > 0
    assert len(summary) * 2 == len(lookup) * len(FUNS)
    assert len(nodes) == len(summary) * 3
    node_lookup = {(r["mode"], r["law"], r["modulus"], r["functional"], float(r["xi"])): r for r in nodes}
    by_result = {}
    for row in summary:
        mode, law, mod, func = (row[x] for x in ("mode", "law", "modulus", "functional"))
        delta = float(row["delta_um"]) * 1e-6
        p = lookup[(mode, law, mod, "plus")]
        m = lookup[(mode, law, mod, "minus")]
        pl = [float(p[xi][func]) for xi in XI]
        mi = [float(m[xi][func]) for xi in XI]
        mp = sum(w * x for w, x in zip(W, pl))
        mm = sum(w * x for w, x in zip(W, mi))
        vp = sum(w * (x - mp) ** 2 for w, x in zip(W, pl))
        vm = sum(w * (x - mm) ** 2 for w, x in zip(W, mi))
        dm = (mp - mm) / (2 * delta)
        dv = (vp - vm) / (2 * delta)
        approx(float(row["mean_plus"]), mp)
        approx(float(row["mean_minus"]), mm)
        approx(float(row["D_mean_per_m"]), dm)
        approx(float(row["D_variance_per_m"]), dv, atol=1e-12)
        approx(float(row["variance_plus"]), vp)
        approx(float(row["variance_minus"]), vm)
        for k, xi in enumerate(XI):
            nd = node_lookup[(mode, law, mod, func, xi)]
            approx(float(nd["weight"]), W[k])
            approx(float(nd["value_plus"]), pl[k])
            approx(float(nd["value_minus"]), mi[k])
            approx(float(nd["D_per_m"]), (pl[k] - mi[k]) / (2 * delta))
        by_result[mode, law, mod, func] = (dm, dv)
    if args.reference:
        old = records(args.reference)
        for ref in old:
            key = (ref["mode"], "EDV", "VAR", "j6")
            if key not in by_result:
                continue
            dm, dv = by_result[key]
            odm = float(ref["D_mean_per_m"])
            odv = float(ref["D_variance_per_m"])
            print(f"P08D {key[0]}: Dmean old={odm:.10g} new={dm:.10g}, Dvar old={odv:.10g} new={dv:.10g}")
            # Safety gate 1% relative change with an absolute floor for tiny numbers.
            if abs(dm - odm) > 0.01 * max(abs(odm), 1e-7) or abs(dv - odv) > 0.01 * max(abs(odv), 1e-10):
                raise AssertionError("Stage3D09C j6 regression vs Stage3D08D exceeds 1%")
    print(f"P09C_AUDIT_OK: {len(summary)} summary rows, {len(nodes)} GH3 rows, {len(samples)} FEM samples")


if __name__ == "__main__":
    main()
