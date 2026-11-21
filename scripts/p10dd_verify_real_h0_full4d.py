"""Read-only independent P10DD H0 4D evidence and P10CA 2D marginal audit.

This compares 606 physically matched old/new thermal cells, verifies the
unchanged global analytic gradient and quantifies signed polar/time/radial
localization. It never runs a FEM or reads the large H0 mesh/cache.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CA = ROOT / "research/evidence/P10CA_R1_WINDOWS_EXITCODE_STOP_20261120/input"
MESH_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
COMPONENTS = (
    "mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
    "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m",
)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("P10DD_INDEPENDENT_STOP: " + message)


def read_csv(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def numeric(row: dict[str, str], field: str) -> float:
    value = float(row[field])
    require(math.isfinite(value), "nonfinite " + field)
    return value


def check_close(a: float, b: float, name: str, atol: float = 1e-10) -> float:
    error = abs(a - b)
    require(error <= atol, name + " mismatch: " + repr(a) + " vs " + repr(b))
    return error


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(evidence: Path) -> tuple[dict, list[dict]]:
    require(evidence.is_file(), "missing evidence archive")
    with zipfile.ZipFile(evidence) as z:
        require(z.testzip() is None, "corrupted evidence archive")
        expected = {
            "P10DD_RUN_MANIFEST.json", "P10DD_SOLVER_STDOUT_STDERR.txt",
            "P10DD_SIGNED_R_THETA_PHI_T.csv",
            "P10DD_FULL4D_CLOSURE_AUDIT.csv",
            "P10W_ANALYTIC_ADJOINT.csv", "P10W_COMPONENTS.csv",
            "P10W_STEP_COMPONENTS.csv",
        }
        require(set(z.namelist()) == expected, "unexpected evidence file set")
        manifest = json.loads(z.read("P10DD_RUN_MANIFEST.json"))
        log = z.read("P10DD_SOLVER_STDOUT_STDERR.txt").decode("utf-8-sig")
        local = read_csv(z.read("P10DD_SIGNED_R_THETA_PHI_T.csv"))
        steps = read_csv(z.read("P10DD_FULL4D_CLOSURE_AUDIT.csv"))
        global_rows = read_csv(z.read("P10W_ANALYTIC_ADJOINT.csv"))
        components = read_csv(z.read("P10W_COMPONENTS.csv"))
        step_components = read_csv(z.read("P10W_STEP_COMPONENTS.csv"))

    require(manifest["protocol"] == "P10DD_R2_ONE_H0_4D", "wrong protocol")
    require(manifest["status"] == "completed_4d_verified" and
            manifest["native_exit_code"] == 0 and not manifest["stop_reason"],
            "physical run not completed")
    require(manifest["mesh_sha256"] == MESH_SHA, "not exact historical H0")
    require(manifest["forward_cache"].endswith(
        "/H0_PHYSICAL_RUN/forward_history.bin".replace("/", "\\")), "wrong cache path")
    require(manifest["forward_cache_sha256"] and
            re.fullmatch("[0-9a-f]{64}", manifest["forward_cache_sha256"]),
            "missing cache provenance")
    command = manifest["exact_command"]
    require(command.count("--reuse-forward") == 1 and
            "--forward-cache" not in command and "--mode" in command and
            command[command.index("--mode") + 1] == "R" and
            command[command.index("--steps") + 1] == "6" and
            command[command.index("--dt") + 1] == "150",
            "unexpected physical command")
    require("P10N_FORWARD_CACHE_LOADED" in log and
            "nonlinear_forward_solves=0" in log and
            "P10DD_FULL4D_CLOSURE_OK mesh=H0" in log and
            "P10W_ANALYTIC_ADJOINT_OK mesh=H0" in log,
            "missing physical log markers")
    require(manifest["wall_s"] <= 900 and
            manifest["private_peak_bytes_polled"] <= 8 * 1024**3,
            "resource gate exceeded")
    require(len(local) == 7206 and len(steps) == 6, "wrong 4D/step count")

    cap = defaultdict(list)
    step_buckets = defaultdict(list)
    profile = defaultdict(list)
    for r in local:
        require(r["mesh"] == "H0" and r["mode"] == "R" and
                r["functional"] == "jpeak", "unexpected local row")
        t = int(r["step"])
        require(1 <= t <= 6 and int(r["time_end_s"]) == 150 * t,
                "invalid time step")
        step_buckets[t].append(r)
        values = [numeric(r, c) for c in COMPONENTS]
        for name, subtotal in (
            ("mechanical_total_per_m", math.fsum(values[:3])),
            ("thermal_total_per_m", math.fsum(values[3:])),
            ("total_per_m", math.fsum(values)),
        ):
            check_close(subtotal, numeric(r, name), name, 2e-12)
        if r["region"] == "VOLUME":
            i, j, k = (int(r[x]) for x in ("radial_bin", "mu_bin", "phi_bin"))
            require(0 <= i < 10 and 0 <= j < 10 and 0 <= k < 12,
                    "invalid spatial bin")
            cap[(t, i, j)].append(r)
            for axis, value in (("step", t), ("radial_bin", i),
                                ("mu_bin", j), ("phi_bin", k)):
                profile[(axis, value)].append(r)
        else:
            require(r["region"] == "TOP_ROBIN", "unexpected non-volume row")

    require(len(cap) == 600, "missing 2D space/time keys")
    for t in range(1, 7):
        rows = step_buckets[t]
        volume = [r for r in rows if r["region"] == "VOLUME"]
        top = [r for r in rows if r["region"] == "TOP_ROBIN"]
        require(len(rows) == 1201 and len(volume) == 1200 and len(top) == 1,
                "missing volume or top row")
        require(sum(int(r["mechanical_qp"]) for r in volume) == 7388 * 27 and
                sum(int(r["thermal_qp"]) for r in volume) == 7388 * 64 and
                int(top[0]["top_robin_qp"]) == 162 * 16,
                "QP count mismatch")
        ref = next(r for r in steps if int(r["step"]) == t)
        for col in ("mechanical_total_per_m", "thermal_total_per_m", "total_per_m"):
            check_close(math.fsum(numeric(r, col) for r in rows),
                        numeric(ref, col), "step " + str(t) + " " + col)
        old_step = next(r for r in step_components
                        if r["functional"] == "jpeak" and int(r["time_step"]) == t)
        for old_col, new_col in (
            ("explicit_objective_shape_per_m", "mech_explicit_per_m"),
            ("equilibrium_residual_shape_per_m", "mech_equilibrium_per_m"),
            ("internal_history_shape_per_m", "mech_history_per_m"),
        ):
            check_close(math.fsum(numeric(r, new_col) for r in rows),
                        numeric(old_step, old_col), "mechanical component step")

    total = math.fsum(numeric(r, "total_per_m") for r in local)
    mechanical = math.fsum(numeric(r, "mechanical_total_per_m") for r in local)
    thermal = math.fsum(numeric(r, "thermal_total_per_m") for r in local)
    gradient = next(r for r in global_rows if r["functional"] == "jpeak")
    new_ref = next(r for r in components if r["functional"] == "jpeak")
    old_global = next(r for r in read_csv(
        (CA / "P10W_ANALYTIC_ADJOINT.csv").read_bytes())
        if r["functional"] == "jpeak")
    global_error = check_close(total, numeric(gradient, "total_adjoint_per_m"),
                               "new global gradient")
    check_close(mechanical, numeric(new_ref, "total_mechanical_shape_per_m"),
                "new mechanical global")
    check_close(thermal, numeric(new_ref, "thermal_adjoint_per_m"),
                "new thermal global")
    old_global_error = check_close(total, numeric(old_global, "total_adjoint_per_m"),
                                   "old P10CA physical H0 gradient")
    for col, value in (("mechanical", mechanical), ("thermal", thermal), ("total", total)):
        check_close(value, float(manifest["independent_4d_check"][col]),
                    "manifest " + col)

    # P10CA computed only 10r x 10mu x 6t thermal. Marginalize the *new*
    # independent phi bins and match every old cell, including top Robin.
    old_thermal = read_csv((CA / "P10BX_THERMAL_QP_STEP_BINS.csv").read_bytes())
    require(len(old_thermal) == 606, "P10CA thermal baseline incomplete")
    max_cross = defaultdict(float)
    old_keys = set()
    for old in old_thermal:
        t, i, j = (int(old[n]) for n in ("step", "shell_bin", "polar_bin"))
        key = (t, i, j)
        require(key not in old_keys, "duplicate P10CA baseline key")
        old_keys.add(key)
        new = (cap[key] if i >= 0 else
               [r for r in step_buckets[t] if r["region"] == "TOP_ROBIN"])
        require(len(new) == (12 if i >= 0 else 1), "wrong phi marginalization")
        for a, b in (
            ("mass_per_m", "thermal_mass_per_m"),
            ("diffusion_per_m", "thermal_diffusion_per_m"),
            ("robin_per_m", "thermal_robin_per_m"),
            ("total_per_m", "thermal_total_per_m"),
            ("volume_m3", "thermal_volume_m3"),
        ):
            diff = check_close(math.fsum(numeric(r, b) for r in new),
                               numeric(old, a), "P10CA vs P10DD " + a, 1e-12)
            max_cross[a] = max(max_cross[a], diff)
        qps = (sum(int(r["thermal_qp"]) for r in new) if i >= 0
               else int(new[0]["top_robin_qp"]))
        require(qps == int(old["qp_count"]), "P10CA vs P10DD QP mismatch")
    require(len(old_keys) == 606, "P10CA keys missing")

    volume_rows = [r for r in local if r["region"] == "VOLUME"]
    l1 = math.fsum(abs(numeric(r, "total_per_m")) for r in volume_rows)
    all_qp = sum(int(r["mechanical_qp"]) for r in volume_rows)
    profiles = []
    for (axis, index), rows in sorted(profile.items()):
        signed = math.fsum(numeric(r, "total_per_m") for r in rows)
        absolute = math.fsum(abs(numeric(r, "total_per_m")) for r in rows)
        qp = sum(int(r["mechanical_qp"]) for r in rows)
        profiles.append({
            "axis": axis, "bin": index, "signed_total_per_m": signed,
            "binned_abs_total_per_m": absolute,
            "binned_abs_share": absolute / l1, "mechanical_qp": qp,
            "mechanical_qp_share": qp / all_qp,
        })

    def fraction(axis: str, selected: set[int], field: str) -> float:
        return sum(r[field] for r in profiles if r["axis"] == axis and
                   r["bin"] in selected)

    summary = {
        "evidence_sha256": sha(evidence),
        "p10ca_thermal_sha256": sha(CA / "P10BX_THERMAL_QP_STEP_BINS.csv"),
        "mesh_sha256": manifest["mesh_sha256"],
        "exe_sha256_from_manifest_unverified": manifest["exe_sha256"],
        "cache_sha256_from_manifest_unverified": manifest["forward_cache_sha256"],
        "run_directory": manifest["run_directory"],
        "native_exit_code": manifest["native_exit_code"],
        "wall_s": manifest["wall_s"],
        "private_peak_gib": manifest["private_peak_bytes_polled"] / 1024**3,
        "rows": len(local), "old_p10ca_thermal_cells_compared": len(old_thermal),
        "mechanical_per_m": mechanical, "thermal_per_m": thermal,
        "total_per_m": total,
        "max_global_closure_error_per_m": global_error,
        "old_p10ca_global_error_per_m": old_global_error,
        "p10ca_2d_vs_p10dd_phi_marginal_max_abs_error": dict(max_cross),
        "total_binned_l1_per_m": l1,
        "both_polar_caps_binned_abs_share": fraction(
            "mu_bin", {0, 9}, "binned_abs_share"),
        "both_polar_caps_mechanical_qp_share": fraction(
            "mu_bin", {0, 9}, "mechanical_qp_share"),
        "first_0p1mm_radial_binned_abs_share": fraction(
            "radial_bin", {0, 1, 2}, "binned_abs_share"),
        "first_0p1mm_radial_mechanical_qp_share": fraction(
            "radial_bin", {0, 1, 2}, "mechanical_qp_share"),
        "last_two_steps_binned_abs_share": fraction(
            "step", {5, 6}, "binned_abs_share"),
        "thermal_robin_per_m": math.fsum(
            numeric(r, "thermal_robin_per_m") for r in local),
        "interpretation_limit": (
            "Absolute values are computed AFTER 4D-bin aggregation, "
            "not as a per-quadrature-point L1 norm. One H0 does not establish "
            "spatial convergence or the cause of polar concentration."),
    }
    return summary, profiles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    summary, profiles = audit(args.evidence)
    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "P10DD_REAL_H0_INDEPENDENT_AUDIT.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        with (args.out / "P10DD_REAL_H0_GROUP_PROFILES.csv").open(
                "w", encoding="utf-8", newline="") as dest:
            cols = tuple(profiles[0].keys())
            writer = csv.DictWriter(dest, fieldnames=cols, lineterminator="\n")
            writer.writeheader()
            writer.writerows(profiles)
    print("P10DD_REAL_H0_INDEPENDENT_REPLAY_OK", json.dumps(
        summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
