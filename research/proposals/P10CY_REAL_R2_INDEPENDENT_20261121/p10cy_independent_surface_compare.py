#!/usr/bin/env python3
"""Independently audit original P10CX R2 Windows ZIP and compare P10CW 4.13 surface."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

EXPECTED = {
    "SHA256_P10CV_U1_GEO_ANGULAR_NEUTRAL_CANDIDATE.geo": "85ee63351ff8e7c1b7720f8ba360aac1d4e6c381f776e3fa66f130e73f17aca7",
    "SHA256_sphere_pore_B6_refined.geo": "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
    "SHA256_P10CX_surface_audit.py": "165d59ff1b05f45478008c6498a0b5ddfde19ca4538816439a3a530f70cc0f50",
    "GMSH_EXE_SHA256": "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1",
}
EXPECTED_FILES = {
    "P10CX_GMSH_STDERR.txt", "P10CX_GMSH_STDOUT.txt", "P10CX_QA_STDOUT.txt",
    "P10CX_R2_VERSION_STDERR.txt", "P10CX_R2_VERSION_STDOUT.txt",
    "P10CX_RESULT.txt", "P10CX_UNIT.txt", "P10CX_ANGULAR_120.csv",
    "P10CX_SURFACE_QA.json",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--previous", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    evidence_sha = hashlib.sha256(args.evidence.read_bytes()).hexdigest()
    with zipfile.ZipFile(args.evidence) as z:
        assert z.testzip() is None, "ZIP CRC STOP"
        assert set(z.namelist()) == EXPECTED_FILES, "unexpected evidence files"
        result_lines = z.read("P10CX_RESULT.txt").decode("utf-8-sig").splitlines()
        pairs = dict(line.split("=", 1) for line in result_lines if "=" in line)
        for key, value in EXPECTED.items():
            assert pairs.get(key) == value, f"pinned SHA mismatch: {key}"
        for key, value in {
            "TOOL_REVISION": "P10CX_R2_NATIVE_VERSION_PROCESS_RECOVERY_ONE_SHOT",
            "GMSH_VERSION_NATIVE_EXIT": "0", "GMSH_VERSION_OUTPUT": "4.15.2",
            "SOURCE_SHA_GATES": "PASS_3_OF_3", "RAM_DISK_PREFLIGHT": "PASS",
            "PYTHON_UNIT_EXIT": "0", "GMSH_EXIT": "0", "QA_NATIVE_EXIT": "0",
            "RESULT": "P10CX_SURFACE_QA_NO_SLIVER_NO_3D_NO_FEM",
        }.items():
            assert pairs.get(key) == value, f"wrong gate {key}"
        version_stdout = z.read("P10CX_R2_VERSION_STDOUT.txt").decode("utf-8-sig").strip()
        assert version_stdout == "4.15.2", "version stdout parity"
        assert "STOP_REASON" not in pairs, "reported STOP"
        unit_bytes = z.read("P10CX_UNIT.txt")
        unit_text = unit_bytes.decode("utf-16" if unit_bytes.startswith((b"\xff\xfe",b"\xfe\xff")) else "utf-8-sig")
        assert "P10CX_SYNTHETIC_UNIT_OK" in unit_text, "native synthetic unit"
        qa = json.loads(z.read("P10CX_SURFACE_QA.json"))
        assert qa["input_msh_sha256"] == pairs.get("MSH_SHA256"), "mesh SHA mismatch"
        assert qa["pore_tri6"] == int(pairs["PORE_TRI6"]), "pore count mismatch"
        assert qa["min_corner_quality"] == float(pairs["WORST_CORNER_Q"]), "quality mismatch"
        assert qa["below_q0p1"] == int(pairs["BAD_Q0P1_COUNT"]), "bad quality count mismatch"
        assert qa["worst_tri6"]["mu_bin"] == int(pairs["WORST_MU_BIN"]), "mu mismatch"
        assert qa["worst_tri6"]["phi_bin"] == int(pairs["WORST_PHI_BIN"]), "phi mismatch"
        assert qa["nonpositive_area"] == 0 and qa["below_q0p1"] == 0
        current_rows = list(csv.DictReader(io.StringIO(z.read("P10CX_ANGULAR_120.csv").decode("utf-8-sig"))))
        json_rows = qa["angular_rows"]
        assert len(current_rows) == len(json_rows) == 120, "120-bin count"
        current = {}
        for row in current_rows:
            key = (int(row["mu_bin"]), int(row["phi_bin"]))
            assert key not in current
            current[key] = row
        assert set(current) == {(i, j) for i in range(10) for j in range(12)}
        count_sum, area_sum = 0, 0.0
        for row in json_rows:
            key = (int(row["mu_bin"]), int(row["phi_bin"]))
            orig = current[key]
            assert int(orig["tri6_count"]) == row["tri6_count"], "cell count mismatch"
            for name in ("chord_area_mm2", "hmax_p50_um"):
                assert math.isclose(float(orig[name]), float(row[name]), rel_tol=1e-12, abs_tol=1e-12), "cell numeric mismatch"
            count_sum += row["tri6_count"]
            area_sum += row["chord_area_mm2"]
        assert count_sum == qa["pore_tri6"]
        assert math.isclose(area_sum, qa["pore_chord_area_mm2"], rel_tol=1e-12)
        assert qa["all_angular_bins_occupied"] is True

    old = json.loads(args.previous.read_text(encoding="utf-8"))
    assert old["gmsh_runtime"] == "4.13.1"
    assert old["tri6_pore"] == 74592 and old["corner_quality_below_0p1"] == 1
    old_cells = {(int(r["mu_bin"]),int(r["phi_bin"])): r for r in old["mu_phi_bins"]}
    assert set(old_cells) == set(current)
    old_n, new_n = old["tri6_pore"], qa["pore_tri6"]
    count_tv = .5*sum(abs(old_cells[k]["count_tri6"]/old_n-int(current[k]["tri6_count"])/new_n) for k in current)
    result = {
        "result": "P10CY_INDEPENDENT_R2_SURFACE_AND_VERSION_PARITY_OK_NO_3D_NO_FEM",
        "original_r2_zip_sha256": evidence_sha,
        "zip_member_count_crc_ok": 9,
        "gmsh_version_native_exit": int(pairs["GMSH_VERSION_NATIVE_EXIT"]),
        "gmsh_version": "4.15.2",
        "gmsh_surface_exit": int(pairs["GMSH_EXIT"]),
        "surface_mesh_sha256_windows_not_locally_rehashed": pairs["MSH_SHA256"],
        "windows_r2": {"tri6": new_n,"qmin": qa["min_corner_quality"],
                       "bad_below_0p1":qa["below_q0p1"], "hmax_p50_um":qa["hmax_um_p5_p50_p95"][1],
                       "polar_mid_ratio":qa["polar_vs_mid_hmedian_ratio"],
                       "polar_area_fraction":qa["polar_area_fraction"]},
        "linux_413": {"tri6":old_n,"qmin":old["min_corner_quality"],
                      "bad_below_0p1":old["corner_quality_below_0p1"],
                      "hmax_p50_um":old["hmax_um_p5_p50_p95"][1],
                      "polar_mid_ratio":old["polar_vs_mid_median_hmax_ratio"]},
        "difference": {"tri6":new_n-old_n,
                       "qmin_improvement":qa["min_corner_quality"]-old["min_corner_quality"],
                       "hmax_p50_um":qa["hmax_um_p5_p50_p95"][1]-old["hmax_um_p5_p50_p95"][1],
                       "count_distribution_TV_120_cells":count_tv},
        "unproven": ["independent reading of original Windows .msh bytes", "3D Tet10 geometric validity",
                     "physical FEM fields or cause of past polar shape derivatives"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(result["result"], "qmin_413", old["min_corner_quality"],
          "qmin_415", qa["min_corner_quality"], "TV", count_tv)


if __name__ == "__main__":
    main()
