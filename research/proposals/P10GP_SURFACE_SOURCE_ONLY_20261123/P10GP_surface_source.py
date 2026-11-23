#!/usr/bin/env python3
"""P10GP: byte-pinned paired Tri6 input generation; NO native meshing."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import zipfile

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "P10GO_SINGLE_MATHEVAL_1D_WINDOWS_20261123"
EXPECTED_ARCHIVE = "747983ec066e2d52829b8782e91c44b4c731df5d03264e5600f5d55749b9ae71"
FACTOR = "0.9378887276834518"


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def load_parent():
    sys.path.insert(0, str(PARENT))
    spec = importlib.util.spec_from_file_location("p10go_source", PARENT / "P10GO_1d_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate() -> tuple[dict[str, bytes], dict]:
    go = load_parent()
    source = go.source_gate()
    math_result = go.math_gate()
    drivers = {}
    for case in go.CASES:
        original = go.driver(case)
        assert original.count("Mesh.MeshSizeFactor = " + FACTOR) == 1
        assert original.count('Include "M0_ROTATED.geo";') == 1
        assert "Merge " not in original and "Save " not in original
        # The exact same CAD, MathEval and size multiplier as in proven 1D.
        # Only the document header and explicit surface algorithm change.
        surface = original.replace("native -1 diagnostic ONLY", "SOURCE-ONLY surface candidate")
        surface += "Mesh.Algorithm = 5; // Delaunay surface; Tri6 with order 2\n"
        drivers[case + "/P10GP_SURFACE.geo"] = surface.encode("utf-8")
        for name, data in source.items():
            drivers[case + "/" + name] = data
        assert 'Background Field = ' + ('3' if case == go.CASES[0] else '7') in surface
        if case == go.CASES[1]:
            assert not re.search(r"\bF[345]\b", go.inline_field(source["M0_ROTATED.geo"]))
    assert math_result["points"] == 10201 and math_result["C1_seam_tests"] == 4
    assert math_result["max_absolute_h_error_m"] == 0.0
    assert math_result["local_factor_min"] == 0.94
    manifest = {"revision": "P10GP_R1_SOURCE_ONLY", "parent_git_commit": "b8b21d71bd2943b565a4ed8605afe17aade8ae60",
                "P10GO_real_windows_evidence_sha256": EXPECTED_ARCHIVE,
                "P10GO_1d_status": "BOTH_COMPLETED_VERIFIED", "geometry": "P10GO rotated OCC sphere and B6 unchanged",
                "field_factor": FACTOR, "surface_algorithm": 5, "element_order": 2,
                "math_qa": math_result, "native_2d_runs": 0, "native_3d_runs": 0,
                "FEM_runs": 0, "files_sha256": {name: sha(data) for name, data in sorted(drivers.items())}}
    return drivers, manifest


def main() -> None:
    files, manifest = generate()
    print("P10GP_SOURCE_ONLY_PASS", json.dumps({"files": len(files), "math_points": manifest["math_qa"]["points"],
                                         "driver_sha": {k: v for k, v in manifest["files_sha256"].items()
                                                        if k.endswith("P10GP_SURFACE.geo")}}, sort_keys=True))
    if "--package" in sys.argv:
        out = HERE / "P10GP_R1_SURFACE_SOURCE_ONLY.zip"
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in sorted(files.items()):
                z.writestr(name, data)
            z.writestr("P10GP_SOURCE_MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        with zipfile.ZipFile(out) as z:
            assert z.testzip() is None
            assert all(sha(z.read(n)) == expected for n, expected in manifest["files_sha256"].items())
        print("P10GP_PACKAGE_OK", out, sha(out.read_bytes()))


if __name__ == "__main__":
    main()
