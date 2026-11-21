#!/usr/bin/env python3
"""Read-only source/archival CSV audit for D-018D. No Gmsh or FEM."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GEO_CSV = ROOT / "experiments/P10AU_EXPANDED_SPATIOTEMPORAL_20261116/input/P10AR_GEOMETRY_H0_H4.csv"
H0_COMPONENTS = ROOT / "research/evidence/P10CA_R1_WINDOWS_EXITCODE_STOP_20261120/input/P10W_COMPONENTS.csv"
H0_GEO = ROOT / "gmsh/sphere_pore_B6_refined.geo"
M1_GEO = ROOT / "gmsh/P10DC_M1_FROM_H0_20PCT_VOLUME.geo"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def geo_number(content: str, name: str) -> float:
    match = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*([0-9.eE+-]+)\s*;", content)
    if match is None:
        raise AssertionError(f"Missing direct {name} override (do not use sizefac): {name}")
    return float(match.group(1))


def main() -> None:
    rows = {row["label"]: row for row in read_csv(GEO_CSV)}
    h0, h1 = rows["H0"], rows["H1"]
    assert (int(h0["nodes"]), int(h0["tet10"]), int(h0["pore_tri6"])) == (10845, 7388, 136)
    assert (int(h1["nodes"]), int(h1["tet10"]), int(h1["pore_tri6"])) == (27757, 19412, 282)
    assert int(h0["tet10"]) < int(h1["tet10"])
    assert h0["mesh_sha256"] == "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
    assert h1["mesh_sha256"] == "394ee339073fe6eacfd58c549ad0b0218a9bdadf8f36a2ca435a1ca3fad0598d"
    assert math.isclose(float(h0["pore_median_edge_mm"]), 0.452372775, abs_tol=1e-8)

    components = read_csv(H0_COMPONENTS)
    j = next(row for row in components if row["mesh"] == "H0" and row["functional"] == "jpeak")
    mechanical = float(j["total_mechanical_shape_per_m"])
    thermal = float(j["thermal_adjoint_per_m"])
    total = float(j["total_adjoint_per_m"])
    assert math.isclose(total, 3.167691851413873, abs_tol=1e-12)
    assert math.isclose(mechanical + thermal, total, abs_tol=1e-12)
    assert j["geometry_derivative_method"] == "ANALYTIC_TET10"

    source_h0, source_m1 = H0_GEO.read_text(), M1_GEO.read_text()
    near_h0 = float(re.search(r"nearSize\s*=\s*([0-9.]+);", source_h0).group(1))
    far_h0 = float(re.search(r"farSize\s*=\s*([0-9.]+);", source_h0).group(1))
    near_m1, far_m1 = geo_number(source_m1, "nearSize"), geo_number(source_m1, "farSize")
    assert 'Include "sphere_pore_B6_refined.geo";' in source_m1
    q = 0.8 ** (1.0 / 3.0)
    assert math.isclose(near_m1 / near_h0, q, rel_tol=1e-13)
    assert math.isclose(far_m1 / far_h0, q, rel_tol=1e-13)
    assert math.isclose((near_m1 / near_h0) ** 3, 0.8, rel_tol=1e-12)
    assert math.isclose((far_m1 / far_h0) ** 3, 0.8, rel_tol=1e-12)
    # Historical sizefac is assigned but never used as a field multiplier.
    uncommented = "\n".join(line.split("//", 1)[0] for line in source_h0.splitlines())
    assert re.findall(r"\bsizefac\b", uncommented) == ["sizefac", "sizefac"]
    assert "Field[2].SizeMin=nearSize;" in source_h0
    assert "Field[2].SizeMax=farSize;" in source_h0

    print("P10DC_H0_AS_M0_SOURCE_AND_CSV_AUDIT_OK")
    print(f"H0 nodes={h0['nodes']} Tet10={h0['tet10']} poreTri6={h0['pore_tri6']}")
    print(f"H1 nodes={h1['nodes']} Tet10={h1['tet10']} poreTri6={h1['pore_tri6']}")
    print(f"H0 jpeak mechanical={mechanical:.15g}, thermal={thermal:.15g}, total={total:.15g} m^-1")
    print(f"h_scale={q:.15g}, nominal_element_volume_ratio={q**3:.15g}")
    print(f"M1 near_m={near_m1:.17g}, far_m={far_m1:.17g}; no mesh/FEM launched")


if __name__ == "__main__":
    main()
