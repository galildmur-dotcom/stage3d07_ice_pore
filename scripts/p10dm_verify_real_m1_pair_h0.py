#!/usr/bin/env python3
"""Independent original-P10DL-M1 evidence audit and H0/M1 signed4D bin pair.

No FEM/Gmsh/mesh files. Both sources are original researcher Windows evidence
ZIPs; compares *integrated signed physical bins*, NOT pointwise FEM errors.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
H0_DEFAULT = ROOT / "research/evidence/P10DD_H0_FULL4D_20261121/input/P10DD_EVIDENCE.zip"
M1_DEFAULT = ROOT / "research/evidence/P10DM_P10DL_REAL_M1_H0_PAIR_20261121/input/P10DL_EVIDENCE.zip"
OUT_DEFAULT = ROOT / "research/evidence/P10DM_P10DL_REAL_M1_H0_PAIR_20261121/derived"
H0_ZIP_SHA = "d81af9ea55542642c3e5738b2f64aac0df8c696a55677f4e2806a2558204ca3e"
M1_ZIP_SHA = "4a3ce36a47337cba9f2b2273928f9b3601a9c2f6c5899aeb1b4896b1619bcf22"
M1_MESH_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
FIELD = ("mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
         "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m")
BIN_AXES = ("r_lower_mm", "r_upper_mm", "theta_lower_rad", "theta_upper_rad",
            "phi_lower_rad", "phi_upper_rad")
FULL4D_NAME = "P10DD_SIGNED_R_THETA_PHI_T.csv"
REQUIRED = {FULL4D_NAME, "P10DD_FULL4D_CLOSURE_AUDIT.csv",
            "P10W_ANALYTIC_ADJOINT.csv", "P10W_COMPONENTS.csv",
            "P10W_STEP_COMPONENTS.csv"}


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise AssertionError("P10DM_STOP: " + msg)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def original_zip(path: Path, expected_sha: str, extra: set[str]) -> None:
    require(path.is_file() and digest(path) == expected_sha,
            "wrong/missing original ZIP SHA: " + str(path))
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        require(set(names) == REQUIRED | extra and len(names) == len(set(names)),
                "original ZIP inventory changed")
        require(z.testzip() is None, "original ZIP CRC error")
        require(all("/" not in n and "\\" not in n for n in names),
                "path traversal/embedded directory in original ZIP")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "missing auditor " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_manifest(manifest: dict) -> None:
    require(manifest.get("protocol") == "P10DL_R1_ONE_APPROVED_M1_FRESH_FORWARD_FULL4D",
            "protocol mismatch")
    require(manifest.get("status") == "COMPLETED_M1_4D_VERIFIED" and
            manifest.get("native_exit_code") == 0 and
            manifest.get("stop_reason") == "", "native physical run was not a valid PASS")
    require(manifest.get("m1_sha256") == M1_MESH_SHA and
            manifest.get("m1_tet10_expected") == 9736,
            "wrong exact M1 SHA/count (source says Windows manifest)")
    require(manifest.get("fresh_forward") is True and
            manifest.get("reuse_forward") is False,
            "M1 must have a fresh compatible forward history")
    cmd = manifest.get("command")
    require(isinstance(cmd, list) and len(cmd) == 16 and
            cmd[1:] == ["--p10dk-authorized-fresh-m1", "--mesh", manifest["mesh"],
                       "--out", manifest["run_directory"], "--mode", "R",
                       "--steps", "6", "--dt", "150", "--cutoff-mm", "5",
                       "--threads", "4"], "physical command differs from P10DL one-shot")
    require(Path(manifest["mesh"].replace("\\", "/")).name == "P10DG_M1_CANDIDATE.msh",
            "wrong M1 mesh basename")
    require(manifest.get("expected_4d_rows") == 7206,
            "M1 expected physical 4D row count changed")
    limits = manifest["limits"]
    require(limits == {"wall_s": 1800, "private_bytes": 8*1024**3,
                       "new_output_bytes": 1024**3}, "unexpected resource limits")
    require(0 < float(manifest["wall_s"]) < 1800 and
            0 < int(manifest["peak_private_bytes_polled"]) < 8*1024**3,
            "observed resources beyond budget")
    for key in ("exe_sha256", "forward_history_sha256"):
        require(len(manifest.get(key, "")) == 64 and
                all(x in "0123456789abcdef" for x in manifest[key]),
                "missing SHA (Windows-reported, raw binary unavailable): " + key)


def comparable_keys(a: list[dict], b: list[dict]):
    def dictionary(rows: list[dict]):
        d = {}
        for row in rows:
            if row["region"] != "VOLUME":
                continue
            key = tuple(int(row[name]) for name in
                        ("step", "radial_bin", "mu_bin", "phi_bin"))
            require(key not in d, "duplicate 4D bin " + str(key))
            d[key] = row
        require(len(d) == 7200, "expected 6×1200 volume bins")
        return d
    h0, m1 = dictionary(a), dictionary(b)
    require(h0.keys() == m1.keys(), "different 4D bin topology")
    for key in h0:
        for axis in BIN_AXES:
            # Last radial shell is open to infinity; its upper bound is CSV-empty.
            if h0[key][axis] == m1[key][axis] == "":
                continue
            require(h0[key][axis] != "" and m1[key][axis] != "",
                    f"inconsistent open-shell boundary: {key}:{axis}")
            x, y = float(h0[key][axis]), float(m1[key][axis])
            require(abs(x-y) < 1e-12, f"different physical bin boundary: {key}:{axis}")
    return h0, m1


def total(rows) -> float:
    return math.fsum(float(x["total_per_m"]) for x in rows)


def calc(h0: dict, m1: dict, test_name: str, predicate) -> dict:
    selection = [k for k in h0 if predicate(k)]
    a = [h0[k] for k in selection]
    b = [m1[k] for k in selection]
    return {
        "group": test_name, "bin_pairs": len(selection),
        "h0_signed_per_m": total(a), "m1_signed_per_m": total(b),
        "delta_m1_minus_h0_per_m": math.fsum(
            float(m1[k]["total_per_m"]) - float(h0[k]["total_per_m"]) for k in selection),
        "h0_L1_after_bin_sum_per_m": math.fsum(abs(float(row["total_per_m"])) for row in a),
        "m1_L1_after_bin_sum_per_m": math.fsum(abs(float(row["total_per_m"])) for row in b),
        "delta_L1_after_bin_subtraction_per_m": math.fsum(abs(float(m1[k]["total_per_m"])
                                              - float(h0[k]["total_per_m"])) for k in selection),
        "h0_mechanical_qp": sum(int(row["mechanical_qp"]) for row in a),
        "m1_mechanical_qp": sum(int(row["mechanical_qp"]) for row in b),
    }


def negative_tests(auditor, m1_reader, good_rows: list[dict],
                   manifest: dict, h0: dict, m1: dict) -> int:
    # In-memory corruption only; never modify the original evidence ZIP.
    class Mutated:
        def __init__(self, rows):
            self.rows = rows

        def csv(self, filename):
            return self.rows if filename == FULL4D_NAME else m1_reader.csv(filename)

    rejections = 0
    for column, bad in (("total_per_m", "1000000"),
                        ("mechanical_qp", str(7388*27)),
                        ("mesh", "H0")):
        rows = [dict(row) for row in good_rows]
        rows[0][column] = bad
        try:
            auditor.audit(Mutated(rows))
        except (AssertionError, ValueError):
            rejections += 1
        else:
            raise AssertionError("P10DM_STOP: altered signed M1 " + column + " was accepted")
    tampered = dict(manifest)
    tampered["m1_sha256"] = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
    try:
        verify_manifest(tampered)
    except AssertionError:
        rejections += 1
    else:
        raise AssertionError("P10DM_STOP: H0 SHA substituted for M1")
    # Compare complete bin boundaries, not just integer bin indices.
    xkey = (1, 0, 0, 0)
    corrupted = dict(m1)
    corrupted[xkey] = dict(m1[xkey])
    corrupted[xkey]["r_upper_mm"] = "10.0"
    try:
        comparable_keys(list(h0.values()), list(corrupted.values()))
    except AssertionError:
        rejections += 1
    else:
        raise AssertionError("P10DM_STOP: incompatible M0/M1 bin boundary accepted")
    return rejections


def run(h0zip: Path, m1zip: Path, out: Path) -> dict:
    original_zip(h0zip, H0_ZIP_SHA, {"P10DD_RUN_MANIFEST.json", "P10DD_SOLVER_STDOUT_STDERR.txt"})
    original_zip(m1zip, M1_ZIP_SHA, {"P10DL_RUN_MANIFEST.json", "P10DL_SOLVER_STDOUT_STDERR.txt"})
    h0aud = load_module(ROOT / "research/proposals/P10DD_M0_H0_FULL4D_20261121/P10DD_audit_evidence.py", "p10dm_h0")
    m1aud = load_module(ROOT / "research/proposals/P10DK_M1_FULL4D_SOURCE_ONLY_20261121/P10DK_audit_evidence.py", "p10dm_m1")
    with zipfile.ZipFile(m1zip) as z:
        manifest = json.loads(z.read("P10DL_RUN_MANIFEST.json"))
        stdout = z.read("P10DL_SOLVER_STDOUT_STDERR.txt").decode("utf-8", "replace")
    verify_manifest(manifest)
    require("P10N_FORWARD_CACHE_SAVED" in stdout and
            "P10N_FORWARD_CACHE_LOADED" not in stdout and
            "P10DD_FULL4D_CLOSURE_OK mesh=P10DG_M1_CANDIDATE" in stdout and
            "P10W_ANALYTIC_ADJOINT_OK mesh=P10DG_M1_CANDIDATE" in stdout and
            "nonlinear_forward_solves=1 mechanical_adjoint_solves=18" in stdout,
            "missing saved fresh M1 state / analytic adjoint / physical 4D trace")
    hreader, mreader = h0aud.Reader(h0zip), m1aud.Reader(m1zip)
    try:
        hg, mg = h0aud.audit(hreader), m1aud.audit(mreader)
        hrows, mrows = hreader.csv(FULL4D_NAME), mreader.csv(FULL4D_NAME)
        h0, m1 = comparable_keys(hrows, mrows)
        negatives = negative_tests(m1aud, mreader, mrows, manifest, h0, m1)
        assert negatives == 5
        for name, val in mg.items():
            require(math.isclose(val, manifest["independent_signed_4d"][name],
                                 abs_tol=1e-10, rel_tol=1e-10),
                    "Windows M1 manifest vs independent CSV differs: " + name)
        groups = [
            ("all_volume", lambda k: True),
            ("south_polar_mu0", lambda k: k[2] == 0),
            ("north_polar_mu9", lambda k: k[2] == 9),
            ("both_polar_edges", lambda k: k[2] in (0, 9)),
            ("nonpolar_mu1_to8", lambda k: 1 <= k[2] <= 8),
            ("near_pore_0_to_0p1mm", lambda k: k[1] <= 2),
            ("late_600_to_900s", lambda k: k[0] >= 5),
            ("polar_and_near_pore", lambda k: k[2] in (0,9) and k[1] <= 2),
            ("polar_and_late", lambda k: k[2] in (0,9) and k[0] >= 5),
            ("near_pore_and_late", lambda k: k[1] <= 2 and k[0] >= 5),
            ("polar_near_pore_late", lambda k: k[2] in (0,9) and
                                                k[1] <= 2 and k[0] >= 5),
        ]
        groups += [(f"time_step_{n}", lambda k, n=n: k[0] == n) for n in range(1, 7)]
        groups += [(f"radial_bin_{n}", lambda k, n=n: k[1] == n) for n in range(10)]
        groups += [(f"mu_bin_{n}", lambda k, n=n: k[2] == n) for n in range(10)]
        result = [calc(h0, m1, name, predicate) for name, predicate in groups]
        # Robin exists only on the top boundary. It is R shape stationary here,
        # but include and verify explicitly before making a global comparison.
        robin = {"h0": [r for r in hrows if r["region"] == "TOP_ROBIN"],
                 "m1": [r for r in mrows if r["region"] == "TOP_ROBIN"]}
        require(all(len(v) == 6 for v in robin.values()), "top Robin rows missing")
        robin_signed = {name: total(rows) for name, rows in robin.items()}
        require(math.isclose(result[0]["h0_signed_per_m"] + robin_signed["h0"],
                             hg["total"], abs_tol=2e-10), "H0 volume vs global mismatch")
        require(math.isclose(result[0]["m1_signed_per_m"] + robin_signed["m1"],
                             mg["total"], abs_tol=2e-10), "M1 volume vs global mismatch")
        delta = mg["total"] - hg["total"]
        sorted_delta = sorted(h0, key=lambda k: abs(float(m1[k]["total_per_m"])
                                                   - float(h0[k]["total_per_m"])),
                              reverse=True)
        hot = []
        for k in sorted_delta[:24]:
            a, b = float(h0[k]["total_per_m"]), float(m1[k]["total_per_m"])
            hot.append({"step": k[0], "radial_bin": k[1], "mu_bin": k[2],
                        "phi_bin": k[3], "h0_per_m": a, "m1_per_m": b,
                        "delta_m1_minus_h0_per_m": b-a,
                        "h0_mech_qp": int(h0[k]["mechanical_qp"]),
                        "m1_mech_qp": int(m1[k]["mechanical_qp"])})
        def component_decomp(reader):
            row = next(r for r in reader.csv("P10W_COMPONENTS.csv") if r["functional"] == "jpeak")
            return {col: float(row[col]) for col in
                    ("explicit_objective_shape_per_m", "equilibrium_residual_shape_per_m",
                     "internal_history_shape_per_m", "total_mechanical_shape_per_m",
                     "thermal_adjoint_per_m", "total_adjoint_per_m")}
        hc, mc = component_decomp(hreader), component_decomp(mreader)
        report = {
            "protocol": "P10DM_R1_REAL_M1_VS_H0_4D_BIN_PAIR",
            "physical_M1_verified": True, "independent_m1_global_pass": True,
            "original_M1_archive_sha256": M1_ZIP_SHA,
            "original_H0_archive_sha256": H0_ZIP_SHA,
            "exact_M1_mesh_sha256_by_windows_manifest": M1_MESH_SHA,
            "native_exit_code": manifest["native_exit_code"],
            "wall_s": manifest["wall_s"],
            "peak_private_bytes_polled": manifest["peak_private_bytes_polled"],
            "fresh_forward_history_sha256_by_windows_manifest": manifest["forward_history_sha256"],
            "h0": {**hg, "components": hc},
            "m1": {**mg, "components": mc},
            "m1_minus_h0_per_m": delta,
            "relative_to_abs_h0_pct": 100*delta/abs(hg["total"]),
            "delta_mechanical": mg["mechanical"]-hg["mechanical"],
            "delta_thermal": mg["thermal"]-hg["thermal"],
            "top_Robin_signed_per_m": robin_signed,
            "negative_tests_rejected": negatives,
            "group_profiles": result,
            "largest_24_signed_bin_changes": hot,
            "scientific_limit": "Integrated signed bin deltas between different meshes; NOT proven mesh convergence or pointwise error; no raw M1.msh/forward_history.bin present",
        }
    finally:
        hreader.close()
        mreader.close()
    out.mkdir(parents=True, exist_ok=True)
    (out / "P10DM_REAL_M1_H0_PAIR_AUDIT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, data in (("P10DM_4D_GROUPS_H0_M1.csv", result),
                       ("P10DM_TOP_SIGNED_BIN_DELTAS_H0_M1.csv", hot)):
        with (out / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]),
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
    print("P10DM_REAL_M1_H0_4D_PAIR_OK", f"H0={hg['total']:.15g}",
          f"M1={mg['total']:.15g}", f"delta={delta:.15g}",
          f"relative_pct={100*delta/abs(hg['total']):.8f}",
          f"negative_tests={negatives}", "physical_FEM_M1=1")
    for entry in result[:7]:
        print(entry["group"], f"H0={entry['h0_signed_per_m']:.9g}",
              f"M1={entry['m1_signed_per_m']:.9g}",
              f"delta={entry['delta_m1_minus_h0_per_m']:.9g}",
              f"L1_H0={entry['h0_L1_after_bin_sum_per_m']:.9g}",
              f"L1_M1={entry['m1_L1_after_bin_sum_per_m']:.9g}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0", type=Path, default=H0_DEFAULT)
    parser.add_argument("--m1", type=Path, default=M1_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()
    try:
        run(args.h0, args.m1, args.out)
    except Exception as exc:
        print("P10DM_VERIFICATION_STOP:", exc, file=sys.stderr)
        raise SystemExit(2)
