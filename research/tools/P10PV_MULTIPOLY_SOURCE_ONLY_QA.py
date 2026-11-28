#!/usr/bin/env python3
"""Reproduce the Stage3D07 P10PV real Algoim+LAPACKE geometric pilot.

Only C++ compilation and geometric numerical quadrature; NO CAD, Gmsh or FEM.
Provide checked-out upstream Algoim and an ABI-consistent LAPACKE/LAPACK/BLAS.
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


RECORD = re.compile(
    r"^P10PV_MULTIPOLY n_poly=(\d+) q=(\d+) "
    r"volume=([\d.eE+-]+) exact=([\d.eE+-]+) "
    r"relative_error=([\d.eE+-]+) nodes=(\d+) "
    r"active=(\d+) min_weight=([\d.eE+-]+) run_s=([\d.eE+-]+)$"
)
EXPECTED_Q = {2, 3, 4, 6, 8, 12}


def git_rev(folder: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(folder), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=10
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algoim-root", type=Path, required=True)
    parser.add_argument("--lapacke-include", type=Path, required=True)
    parser.add_argument("--lapacke-lib", type=Path, required=True)
    parser.add_argument("--lapack-lib", default="-llapack")
    parser.add_argument("--blas-lib", default="-lblas")
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name(
        "P10PV_ALGOIM_MULTIPOLY_SECTOR_SOURCE_ONLY.cpp"))
    parser.add_argument("--binary", type=Path, default=Path("./p10pv_multpoly_pilot"))
    parser.add_argument("--output", type=Path, default=Path("./P10PV_MULTIPOLY_SOURCE_ONLY_QA.json"))
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--std", choices=["c++17", "c++20"], default="c++17",
                        help="C++20 needs the separate checked P10PV Algoim compatibility patch")
    args = parser.parse_args()

    source = args.source.resolve()
    algoim = args.algoim_root.resolve()
    header_dir = args.lapacke_include.resolve()
    binary = args.binary.resolve()
    lib = args.lapacke_lib.resolve()
    if not source.is_file() or not (algoim / "algoim" / "quadrature_multipoly.hpp").is_file():
        parser.error("missing source file or Algoim quadrature_multipoly.hpp")
    if not (header_dir / "lapacke.h").is_file() or not lib.is_file():
        parser.error("missing LAPACKE header or library")

    compile_cmd = [
        args.cxx, "-std=" + args.std, "-O2", "-Wl,--gc-sections",
        "-I" + str(algoim / "algoim"), "-I" + str(header_dir),
        str(source), str(lib), args.lapack_lib, args.blas_lib,
        "-lm", "-o", str(binary),
    ]
    try:
        built = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=180)
        if built.returncode != 0:
            raise RuntimeError("compile failed:\n" + built.stderr[-5000:])
        finished = subprocess.run([str(binary), "4"], capture_output=True, text=True, timeout=90)
        if finished.returncode != 0:
            raise RuntimeError("runtime failed:\n" + (finished.stdout + finished.stderr)[-5000:])
        if "P10PV_TRUE_MULTIPOLY_SOURCE_ONLY_PASS" not in finished.stdout:
            raise RuntimeError("missing final geometric-only success marker")
        records = []
        for line in finished.stdout.splitlines():
            m = RECORD.match(line)
            if m:
                n, q, vol, exact, err, nodes, active, minw, seconds = m.groups()
                rec = dict(n_poly=int(n), q=int(q), volume=float(vol),
                           exact=float(exact), relative_error=float(err),
                           nodes=int(nodes), active=int(active),
                           min_weight=float(minw), runtime_s=float(seconds))
                if not (math.isfinite(rec["relative_error"]) and
                        0 < rec["min_weight"] and 0 < rec["active"] <= rec["nodes"]):
                    raise RuntimeError("bad volume, weight, or node count: " + line)
                if abs(abs(rec["volume"] - rec["exact"]) / rec["exact"] -
                       rec["relative_error"]) > 3e-11:
                    raise RuntimeError("reported relative error is inconsistent")
                records.append(rec)
        for n in range(1, 5):
            if {r["q"] for r in records if r["n_poly"] == n} != EXPECTED_Q:
                raise RuntimeError("missing/duplicate polynomial and quadrature cases")
        if len(records) != 24:
            raise RuntimeError("expected precisely 24 tests")
        index = {(r["n_poly"], r["q"]): r for r in records}
        thresholds = {(1, 12): 1e-6, (3, 12): 1e-6,
                      (4, 8): 1e-5, (4, 12): 1e-6}
        for test, limit in thresholds.items():
            if index[test]["relative_error"] > limit:
                raise RuntimeError(f"threshold {test} failed: {limit}")
        if index[(4, 12)]["relative_error"] >= index[(4, 8)]["relative_error"]:
            raise RuntimeError("full-sector error did not improve at higher order")
        report = {
            "stage": "P10PV", "status": "PASS_SOURCE_ONLY", "fem_started": False,
            "cad_started": False, "mesh_generated": False,
            "geometry": "Cartesian octant annular spherical polar-azimuth sector",
            "upstream_algoim_sha": git_rev(algoim),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "lapacke_static_library_sha256": hashlib.sha256(lib.read_bytes()).hexdigest(),
            "compiler": args.cxx, "cpp_standard": args.std,
            "thresholds": {f"poly{n}_q{q}": v for (n, q), v in thresholds.items()},
            "total_quadrature_cases": len(records),
            "full_sector_q12": index[(4, 12)],
            "cone_apex_nonmonotone_warning": (
                "n_poly=2: errors do not monotonically vanish through q=12; "
                "needs additional diagnostics"),
            "scaling_warning": "q12 n_poly=4 emits >2 million nodes in one box; "
                               "must prune/cull for real Tet10 mesh",
            "tests": records,
        }
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(f"P10PV_QA_PASS output={args.output} q12_rel="
              f"{index[(4, 12)]['relative_error']:.10g} "
              f"q12_nodes={index[(4, 12)]['nodes']}")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("P10PV_QA_STOP", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
