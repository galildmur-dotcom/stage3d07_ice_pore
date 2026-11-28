#!/usr/bin/env python3
"""P10EK: one newly authorized Gmsh -3 M2, algorithm5 surface, HXT3D10.

Reuse the pinned, previously audited P10EA 3D guard without editing it.
P10EA and P10EF consumed markers are NEVER touched. No FEM here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PARENT_DIR=HERE/"P10EA_PINNED_PARENT"
sys.path.insert(0,str(PARENT_DIR))
import P10EA_one_click_m2 as base
REV="P10EK_R1_ONE_NATIVE_3D_M2_ALG5_MESH_ONLY"
PARENT_REV="P10EA_R1_EXACT_INLINE_F6_ONE_M2_3D_MESH_ONLY"
PARENT_F6_SHA="32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
PARENT_BUNDLE_SHA="8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
ALG5_SHA="2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5"
PIN=HERE/"P10EK_R1_SOURCE_SHA256.json"
CONFIRM="RUN ONE P10EK M2 3D MESH"
NEW_FILES=("P10EK_one_click_m2.py", "P10EK_B_EXACT_F6_ALG5.geo",
           "01_P10EK_SAFE_PREFLIGHT_ONLY.cmd", "02_P10EK_ONE_M2_3D_ONLY.cmd",
           "README_P10EK_RU.md")

_original_source_gate=base.source_gate
_original_geometry_contract=base.geometry_contract
_original_make_evidence=base.make_evidence


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError("P10EK_STOP: "+message)


def source_gate():
    # Temporarily restore the *immutable* P10EA identity while running all
    # historical source gates. No old one-shot markers or mesh are accessed.
    base.REV=PARENT_REV
    base.F6_SHA=PARENT_F6_SHA
    try:
        inherited=_original_source_gate()
    finally:
        base.REV=REV
        base.F6_SHA=ALG5_SHA
    pin=json.loads(PIN.read_text(encoding="utf-8"))
    need(pin.get("revision")==REV and pin.get("one_native_3d_max")==1 and
         pin.get("physical_FEM") is False and
         pin.get("parent_bundle_sha256")==PARENT_BUNDLE_SHA and
         pin.get("parent_f6_sha256")==PARENT_F6_SHA and
         pin.get("new_alg5_sha256")==ALG5_SHA and
         set(pin.get("files",{}))==set(NEW_FILES),"new package identity/pin inventory")
    for name,sha in pin["files"].items():
        need(Path(name).name==name and (HERE/name).is_file() and
             digest(HERE/name)==sha,"new source modified: "+name)
    geometry_contract()
    return inherited


def geometry_contract():
    baseline, old=_original_geometry_contract()
    needle="Background Field=6;\n"
    need(old.count(needle)==1 and "Mesh.Algorithm = 5;" not in old,
         "original flattened field changed")
    new=old.replace(needle,"Mesh.Algorithm = 5;\n"+needle,1)
    need(hashlib.sha256(new.encode("utf-8")).hexdigest()==ALG5_SHA and
         (HERE/"P10EK_B_EXACT_F6_ALG5.geo").read_bytes()==new.encode("utf-8") and
         new.count("Mesh.Algorithm = 5;")==1 and
         new.count("Background Field=6;")==1,
         "one-line alg5/Field6 difference not exact")
    return baseline,new


def profile_marker() -> Path:
    appdata=os.environ.get("LOCALAPPDATA","")
    need(bool(appdata) and Path(appdata).is_dir(),"LOCALAPPDATA missing")
    return Path(appdata)/"Stage3D07"/("P10EK_R1_ONE_3D_"+base.M1_SHA+".json")


def evidence(run: Path) -> Path:
    old=_original_make_evidence(run)
    new=run/"P10EK_EVIDENCE.zip"
    need(not new.exists(),"P10EK evidence already exists")
    old.rename(new)
    return new


def configure():
    base.REV=REV
    base.RUNS=HERE/"P10EK_R1_RUNS"
    base.PROOF=base.RUNS/"P10EK_R1_PREFLIGHT_PASS.json"
    base.LOCAL_MARKER=base.RUNS/"P10EK_R1_ONE_3D_USED.json"
    base.CONFIRM=CONFIRM
    base.F6_SHA=ALG5_SHA
    base.source_gate=source_gate
    base.geometry_contract=geometry_contract
    base.global_marker=profile_marker
    base.make_evidence=evidence


def selftest():
    inherited=source_gate()
    a,b=geometry_contract()
    need(len(inherited["files"])==23 and a.endswith("Background Field=2;\n") and
         b.endswith("Background Field=6;\n"),"original and alg5 source unit")
    base.mesh_qa.selftest()
    base.exact_math.math_selftest()
    need(base.RUNS.name=="P10EK_R1_RUNS" and
         base.LOCAL_MARKER.name=="P10EK_R1_ONE_3D_USED.json" and
         base.CONFIRM==CONFIRM and base.WALL_S==900 and
         base.PRIVATE_MAX==8*1024**3 and base.MESH_MAX==750*1024**2,
         "one-shot/resource contracts")
    print("P10EK_ALG5_M2_SOURCE_ONLY_SELFTEST_OK parent_pin23=PASS "
          "exact_one_line_alg5=PASS curved27QP=PASS one_shot_isolated=PASS "
          "native_Gmsh_3D_runs=0 FEM=0")
    return 0


def main():
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--selftest",action="store_true")
    modes.add_argument("--preflight-only",action="store_true")
    modes.add_argument("--one-m2",action="store_true")
    args=parser.parse_args()
    configure()
    if args.selftest:
        return selftest()
    code=base.do_run(preflight_only=args.preflight_only)
    print("P10EK: send ONLY P10EK_EVIDENCE.zip from newest P10EK_R1_RUNS folder; "
          "never rerun 02 after markers exist; FEM was NOT started.")
    return code


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,KeyError,AssertionError) as exc:
        print("P10EK STOP:",exc)
        raise SystemExit(2)
