#!/usr/bin/env python3
"""P10PW: compile and independently audit real Algoim five-poly Tet10 runs.

SOURCE-ONLY only: NO CAD, GMSH, PHYSICAL FEM, ADJOINT, nor mesh mutation.
An Algoim checkout with the pinned P10PV C++20 compatibility patch is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

PAT = re.compile(
    r"^P10PW_TET10_MULTIPOLY alpha=([\d.eE+-]+) q=(\d+) "
    r"sector=([\d.eE+-]+) sector_exact=([\d.eE+-]+) sector_rel=([\d.eE+-]+) "
    r"tetra=([\d.eE+-]+) tetra_exact=([\d.eE+-]+) tetra_rel=([\d.eE+-]+) "
    r"cube_rel=([\d.eE+-]+) nodes=(\d+) tet_nodes=(\d+) "
    r"sector_nodes=(\d+) min_weight=([\d.eE+-]+) run_s=([\d.eE+-]+)$"
)
ORDERS = [2, 3, 4, 6, 8, 12]


def git_head(repo: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--algoim-root", type=Path, required=True)
    ap.add_argument("--lapacke-include", type=Path, required=True)
    ap.add_argument("--lapacke-lib", type=Path, required=True)
    ap.add_argument("--lapack-lib", required=True)
    ap.add_argument("--blas-lib", required=True)
    ap.add_argument("--cxx", default="g++")
    ap.add_argument("--source", type=Path, default=Path(__file__).with_name(
        "P10PW_ALGOIM_CURVED_TET10_5POLY_SOURCE_ONLY.cpp"))
    ap.add_argument("--svd-source", type=Path, default=Path(__file__).with_name(
        "P10PW_LAPACKE_SVD_PREFLIGHT_SOURCE_ONLY.cpp"))
    ap.add_argument("--binary", type=Path, default=Path("./p10pw_geom_test"))
    ap.add_argument("--output", type=Path, default=Path(
        "./P10PW_CURVED_TET10_SOURCE_ONLY_QA.json"))
    args = ap.parse_args()
    source = args.source.resolve()
    svd_source = args.svd_source.resolve()
    algoim = args.algoim_root.resolve()
    lapack_header = args.lapacke_include.resolve()
    lib = args.lapacke_lib.resolve()
    binary = args.binary.resolve()
    for path in [source, svd_source, algoim / "algoim" / "quadrature_multipoly.hpp",
                 lapack_header / "lapacke.h", lib]:
        if not path.is_file():
            ap.error(f"missing prerequisite: {path}")
    cmd = [args.cxx, "-std=c++20", "-O2", "-Wl,--gc-sections",
           "-I" + str(algoim / "algoim"), "-I" + str(lapack_header),
           str(source), str(lib), args.lapack_lib, args.blas_lib,
           "-lm", "-o", str(binary)]
    try:
        svd_binary = binary.with_name(binary.name + "_svd")
        svd_compile = [args.cxx, "-std=c++20", "-O2", "-Wl,--gc-sections",
                       "-I" + str(lapack_header), str(svd_source), str(lib),
                       args.lapack_lib, args.blas_lib, "-lm", "-o", str(svd_binary)]
        svd_build = subprocess.run(svd_compile, capture_output=True, text=True, timeout=120)
        if svd_build.returncode:
            raise RuntimeError("independent LAPACKE SVD compile failed:\n" + svd_build.stderr[-3500:])
        svd_run = subprocess.run([str(svd_binary)], capture_output=True, text=True, timeout=30)
        if svd_run.returncode:
            raise RuntimeError("independent LAPACKE SVD run failed:\n" + svd_run.stdout[-3500:])
        svd_results = []
        for line in svd_run.stdout.splitlines():
            m = re.fullmatch(r"P10PW_LAPACKE_SVD P=(\d+) info=(-?\d+) "
                             r"s_first=([\d.eE+-]+) s_last=([\d.eE+-]+)", line)
            if m:
                n, info, sfirst, slast = m.groups()
                if int(info) or not (float(sfirst) >= float(slast) > 0):
                    raise RuntimeError("bad independent LAPACKE SVD result")
                svd_results.append({"matrix_order": int(n), "info": int(info),
                                    "s_first": float(sfirst), "s_last": float(slast)})
        if [r["matrix_order"] for r in svd_results] != list(range(2, 9)):
            raise RuntimeError("independent LAPACKE SVD results incomplete")
        built = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if built.returncode:
            raise RuntimeError("compilation failed:\n" + built.stderr[-3500:])
        records: list[dict] = []
        for mode, alpha in [("affine", 0.), ("curved", .3)]:
            run = subprocess.run([str(binary), mode, "12"], capture_output=True,
                                 text=True, timeout=60)
            if run.returncode:
                raise RuntimeError(f"{mode} failed:\n" +
                                   (run.stdout + run.stderr)[-3500:])
            if "P10PW_PREFLIGHT_TET10_PARITY_PASS" not in run.stdout:
                raise RuntimeError(f"{mode} missing Tet10 isoparametric parity")
            if "P10PW_TRUE_FIVE_POLYNOMIAL_CURVED_TET10_SOURCE_ONLY_PASS" not in run.stdout:
                raise RuntimeError(f"{mode} missing final five-poly marker")
            seen: set[int] = set()
            for line in run.stdout.splitlines():
                m = PAT.fullmatch(line)
                if m is None:
                    continue
                v = m.groups()
                rec = {"mode": mode, "alpha": float(v[0]), "q": int(v[1]),
                       "sector_volume": float(v[2]), "sector_exact": float(v[3]),
                       "sector_rel": float(v[4]), "tetra_volume": float(v[5]),
                       "tetra_exact": float(v[6]), "tetra_rel": float(v[7]),
                       "cube_rel": float(v[8]), "nodes": int(v[9]),
                       "tet_nodes": int(v[10]), "sector_nodes": int(v[11]),
                       "min_weight": float(v[12]), "run_s": float(v[13])}
                if rec["q"] in seen or rec["q"] not in ORDERS:
                    raise RuntimeError("duplicated/unknown quadrature order")
                seen.add(rec["q"])
                if rec["alpha"] != alpha or not math.isfinite(rec["sector_rel"]):
                    raise RuntimeError("wrong map mode or NaN/Inf error")
                if not (rec["min_weight"] > 0 and rec["cube_rel"] < 1e-7):
                    raise RuntimeError("negative weight or unit-cube closure failed")
                if not (0 < rec["sector_nodes"] <= rec["tet_nodes"] <= rec["nodes"]):
                    raise RuntimeError("invalid geometric phase partition")
                for label in ["sector", "tetra"]:
                    expected = abs(rec[f"{label}_volume"] - rec[f"{label}_exact"]) / rec[f"{label}_exact"]
                    if abs(expected - rec[f"{label}_rel"]) > 1e-11:
                        raise RuntimeError("volume diagnostic mismatch " + label)
                records.append(rec)
            if seen != set(ORDERS):
                raise RuntimeError(f"{mode} missing quadrature orders: {seen}")
        index = {(r["mode"], r["q"]): r for r in records}
        threshold = {
            ("affine", 8, "sector_rel"): 1e-5,
            ("affine", 12, "tetra_rel"): 1e-6,
            ("curved", 8, "sector_rel"): 2e-5,
            ("curved", 12, "sector_rel"): 1e-6,
            ("curved", 12, "tetra_rel"): 1e-6,
        }
        for (mode, q, metric), maximum in threshold.items():
            if index[(mode, q)][metric] > maximum:
                raise RuntimeError(f"{mode} q={q} {metric} exceeds {maximum}")
        if index[("curved", 12)]["sector_rel"] >= index[("curved", 8)]["sector_rel"]:
            raise RuntimeError("curved sector does not improve from q8 to q12")
        result = {
            "stage": "P10PW", "status": "PASS_CURVED_TET10_MULTIPOLY_GEOMETRY_ONLY",
            "physical_fem_started": False, "mesh_generated": False, "cad_started": False,
            "geometry_source": "synthetic exact Tet10 interpolation F=(u,v,w*(1+alpha*u))",
            "not_real_mesh_M21": True,
            "cut_geometry": "outer sphere + polar cone + azimuth plane + inner sphere + reference simplex",
            "spherical_sector_fully_inside_reference_tetra": True,
            "upstream_algoim_sha": git_head(algoim),
            "cpp_standard": "c++20", "compiler": args.cxx,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "svd_source_sha256": hashlib.sha256(svd_source.read_bytes()).hexdigest(),
            "lapacke_archive_sha256": hashlib.sha256(lib.read_bytes()).hexdigest(),
            "independent_lapacke_svd_results": svd_results,
            "thresholds": [dict(mode=m, q=q, metric=k, maximum=v)
                           for (m, q, k), v in threshold.items()],
            "curved_q12": index[("curved", 12)],
            "affine_q12": index[("affine", 12)],
            "warning": (
                "Affine sector error is nonmonotone (q8 better than q12); "
                "q12 curved emits 9.7 million nodes per entire bounding cube. "
                "Real M21 Tet10 mesh and EDV quadratures NOT validated."),
            "runs": records,
        }
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print("P10PW_QA_PASS curved_q12_sector_rel=" +
              str(index[("curved", 12)]["sector_rel"]) +
              " curved_q12_tetra_rel=" + str(index[("curved", 12)]["tetra_rel"]) +
              " nodes=" + str(index[("curved", 12)]["nodes"]))
        return 0
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print("P10PW_QA_STOP", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
