#!/usr/bin/env python3
"""P10EU stand-alone Windows source verifier, Python standard library only.

No subprocess, Gmsh, mesh, physics, file deletion or one-shot marker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEO_NAME = "P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo"
AUDIT_NAME = "P10EU_C1_GMSH_SOURCE_AUDIT.json"
PARENT_NAME = "sphere_pore_B6_refined.geo"
EXPECTED = {
    GEO_NAME: "4c4a4aeb4f97bfec350e1e057a57e275d436c09d63a02438a8acfe4ad386253a",
    AUDIT_NAME: "ba03afbe5b0d45a369a0c0a3b13dbbd622fe0bbe2530fc8b4c35e384e36b1252",
    PARENT_NAME: "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
}


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("P10EU_STOP: " + reason)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory: Path) -> None:
    for name, expected in EXPECTED.items():
        p = directory / name
        need(p.is_file() and digest(p) == expected,
             "missing/tampered source " + name)
    geo = (directory / GEO_NAME).read_text(encoding="utf-8")
    parent = (directory / PARENT_NAME).read_text(encoding="utf-8")
    audit = json.loads((directory / AUDIT_NAME).read_text(encoding="utf-8"))
    need(audit["generated_GEO_sha256"] == EXPECTED[GEO_NAME] and
         audit["parent_sha256"]["parent_GEO"] == EXPECTED[PARENT_NAME] and
         audit["source_only_parity"]["sample_count"] == 7620 and
         audit["source_only_parity"]["max_relative_h_parity_error"] < 5e-12 and
         audit["status"] == "NO_NEW_NATIVE_GMSH_NO_FEM_NO_NEW_M2",
         "pinned source-only mathematical audit metadata")
    need(geo.count('Include "sphere_pore_B6_refined.geo";') == 1 and
         geo.count("Field[6] = MathEval;") == 1 and
         geo.count("Background Field=6;") == 1 and
         geo.count("Mesh.Algorithm=5;") == 1 and
         geo.count("Mesh.Algorithm3D=10;") == 1 and
         geo.count('Field[6].F = "') == 1 and
         "Mesh 3;" not in geo and "Mesh 2;" not in geo and
         "SystemCall" not in geo, "single unexecuted MathEval field")
    need('Physical Surface("PORE_WALL",8)' in parent and
         'Physical Volume("ICE_VOLUME",1)' in parent and
         "Mesh.MeshSizeExtendFromBoundary=0;" in geo and
         "Mesh.MeshSizeFromPoints=0;" in geo and
         "Mesh.MeshSizeFromCurvature=0;" in geo,
         "unmodified physical CAD and size precedence")
    print("P10EU_SOURCE_PREFLIGHT_PASS original_source_SHA=3/3",
          "single_MathEval=PASS CAD=PINNED native_Gmsh=0 FEM=0")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-only", action="store_true")
    ap.add_argument("--directory", type=Path, default=HERE)
    args = ap.parse_args()
    need(args.source_only, "--source-only required; no mesh-running mode exists")
    verify(args.directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
