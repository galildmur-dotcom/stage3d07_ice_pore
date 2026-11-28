#!/usr/bin/env python3
"""Strict P10EF source-only geometry/diff/pin check, no native process API."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REV="P10EF_R1_2D_DELAUNAY_ONLY_SOURCE_PREP"
HERE=Path(__file__).resolve().parent
BASE="A_P10EA_EXACT_F6_ALG6_CONTROL.geo"
CAND="B_P10EF_EXACT_F6_ALG5_SURFACE_ONLY.geo"
CAD="sphere_pore_B6_refined.geo"
PIN="P10EF_SOURCE_PIN.json"
INSERT=b"Mesh.Algorithm = 5;\n"
NEEDLE=b"Background Field=6;\n"
F6_SHA="32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
CAD_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
OLD_M2_SHA="ba1f1a0553a568c1b399acadd52bce1c1dc32e8d1c6b3ab1ce6759c547e5dee5"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure(ok: bool, what: str) -> None:
    if not ok:
        raise RuntimeError("P10EF_SOURCE_STOP: "+what)


def check_bytes(a: bytes, b: bytes, cad: bytes) -> None:
    ensure(sha(a)==F6_SHA and sha(cad)==CAD_SHA,"original exact F6 or CAD SHA")
    ensure(a.count(NEEDLE)==1 and b.count(NEEDLE)==1 and
           b.count(INSERT)==1 and b==a.replace(NEEDLE,INSERT+NEEDLE,1),
           "one-line algorithm 5 diff ONLY")
    ensure(a.count(b"Field[6] = MathEval;")==1 and
           a.count(b"Background Field=6;")==1 and
           a.count(b'Include "sphere_pore_B6_refined.geo";')==1 and
           a.count(b"Mesh.Algorithm") == 0,
           "exact F6 original must have default surface algorithm 6")
    ensure(b"Mesh.Algorithm3D=10;" in cad and
           b"Mesh.ElementOrder=2;" in cad and
           b"Mesh.MeshSizeFromPoints=0;" in cad and
           b"Mesh.MeshSizeFromCurvature=0;" in cad and
           b"Mesh.MeshSizeExtendFromBoundary=0;" in cad,
           "2D-only option must preserve 3D/CAD/other mesh options")
    ensure(a.count(b"F2*exp(log(1-0.2*")==1 and b"Mesh.Algorithm = 6;" not in b,
           "exact κ/F6 source or Delaunay 2D option changed")


def source_check() -> dict:
    meta=json.loads((HERE/PIN).read_text(encoding="utf-8"))
    ensure(meta.get("revision")==REV and
           meta.get("mode")=="SOURCE_ONLY_NO_NATIVE" and
           meta.get("original_m1_sha256")==M1_SHA and
           meta.get("historical_m2_alg6_sha256")==OLD_M2_SHA and
           meta.get("exact_f6_sha256")==F6_SHA and
           meta.get("cad_sha256")==CAD_SHA and
           meta.get("native_gmsh_attempts_allowed_now")==0 and
           meta.get("physical_fem_attempts_allowed_now")==0,
           "preflight PIN revision, permissions and original SHA")
    names=meta.get("files",{})
    ensure(set(names)=={BASE,CAND,CAD,"README_P10EF_RU.md",
                        "01_P10EF_CHECK_SOURCE_ONLY.cmd","P10EF_SOURCE_CHECK.py"},
           "pinned inventory exact six files")
    for name,expected in names.items():
        ensure(name==Path(name).name and (HERE/name).is_file() and
               sha((HERE/name).read_bytes())==expected,
               "source file tampered or absent: "+name)
    check_bytes((HERE/BASE).read_bytes(),(HERE/CAND).read_bytes(),(HERE/CAD).read_bytes())
    return {"revision":REV,"pinned_files":len(names),
            "candidate_sha256":names[CAND],
            "algorithm_2d_control":6,"algorithm_2d_candidate":5,
            "original_f6_preserved_byte_for_byte_except_one_option":True,
            "Gmsh_runs":0,"FEM_runs":0}


def negative_test() -> None:
    a=(HERE/BASE).read_bytes()
    b=(HERE/CAND).read_bytes()
    cad=(HERE/CAD).read_bytes()
    for altered in (b.replace(INSERT,b"Mesh.Algorithm = 6;\n",1),
                    b.replace(NEEDLE,b"Background Field=2;\n",1),
                    b+INSERT):
        try:check_bytes(a,altered,cad)
        except RuntimeError:pass
        else:raise RuntimeError("P10EF negative candidate mutation accepted")
    try:check_bytes(a,b,cad+b"\n// CAD TAMPER\n")
    except RuntimeError:pass
    else:raise RuntimeError("P10EF negative CAD mutation accepted")


def main() -> int:
    parser=argparse.ArgumentParser()
    x=parser.add_mutually_exclusive_group(required=True)
    x.add_argument("--check",action="store_true")
    x.add_argument("--selftest",action="store_true")
    opts=parser.parse_args()
    result=source_check()
    if opts.selftest:
        negative_test()
        print("P10EF_SOURCE_NEGATIVE4_4_STOP PASS")
    print("P10EF_SOURCE_CHECK_PASS",result,"NO_GMSH_NO_FEM")
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,KeyError) as exc:
        print("P10EF_SOURCE_STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
