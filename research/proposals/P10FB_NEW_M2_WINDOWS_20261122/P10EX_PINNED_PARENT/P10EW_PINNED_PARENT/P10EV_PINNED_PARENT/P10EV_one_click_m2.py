#!/usr/bin/env python3
"""P10EV: one explicitly authorized Windows M2 Gmsh -3, never FEM.

Fully pinned P10EN parent is immutable and only a source/geometry QA donor.
All P10EV markers, evidence, new field SHA and RUNS are independent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
PARENT=HERE/"P10EN_PINNED_PARENT"
sys.path.insert(0,str(PARENT))
import P10EN_one_click_m2 as en
import P10EU_safe_preflight as eu

base=en.base
REV="P10EV_R1_ONE_AUTHORIZED_C1_JOINT_3D_M2_MESH_ONLY"
PARENT_ZIP_SHA="c730e8d585f44629b15eede2ebcf513358abf90e1030e1577837968cb6414e11"
NEW_GEO_SHA=eu.EXPECTED[eu.GEO_NAME]
CONFIRM="RUN ONE P10EV M2 3D MESH"
PIN_NAME="P10EV_R1_SOURCE_SHA256.json"
FILES=(
    "P10EV_one_click_m2.py",
    "P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo",
    "P10EU_C1_GMSH_SOURCE_AUDIT.json",
    "P10EU_safe_preflight.py",
    "sphere_pore_B6_refined.geo",
    "01_P10EV_SAFE_PREFLIGHT_ONLY.cmd",
    "02_P10EV_ONE_M2_3D_ONLY.cmd",
    "README_P10EV_RU.md",
)


def need(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError("P10EV_STOP: "+message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_contract() -> tuple[str,str]:
    # Existing P10EA/P10EK/P10EN original source gates remain unchanged.
    baseline,_en_geo=en.geometry_contract()
    new=(HERE/eu.GEO_NAME).read_text(encoding="utf-8")
    need(digest(HERE/eu.GEO_NAME)==NEW_GEO_SHA and
         new.count("Field[6] = MathEval;")==1 and
         new.count("Background Field=6;")==1 and
         new.count("Mesh.Algorithm=5;")==1 and
         new.count("Mesh.Algorithm3D=10;")==1 and
         new.count('Include "sphere_pore_B6_refined.geo";')==1 and
         "F2" not in new.split('Field[6].F = "',1)[1].split('";',1)[0],
         "new independent flattened C1 field")
    return baseline,new


def source_gate():
    # en.source_gate temporarily restores and checks exact historical SHA.
    try:
        inherited=en.source_gate()
    finally:
        base.REV=REV
        base.F6_SHA=NEW_GEO_SHA
    pin=json.loads((HERE/PIN_NAME).read_text(encoding="utf-8"))
    need(pin.get("revision")==REV and pin.get("parent_p10en_zip_sha256")==PARENT_ZIP_SHA
         and pin.get("one_native_3d_max")==1 and pin.get("FEM")==0
         and pin.get("new_geo_sha256")==NEW_GEO_SHA
         and pin.get("m1_sha256")==base.M1_SHA
         and set(pin.get("files",{}))==set(FILES),"exact one-shot pin inventory")
    for name,expected in pin["files"].items():
        need(Path(name).name==name and (HERE/name).is_file() and
             digest(HERE/name)==expected,"tampered source "+name)
    eu.verify(HERE)
    baseline,new=geometry_contract()
    need(baseline.endswith("Background Field=2;\n")
         and new.endswith("Mesh.MeshSizeMax=1e22;\n"),
         "pinned source composition")
    return inherited


def profile_marker() -> Path:
    appdata=os.environ.get("LOCALAPPDATA","")
    need(bool(appdata) and Path(appdata).is_dir(),"LOCALAPPDATA missing")
    return Path(appdata)/"Stage3D07"/("P10EV_R1_ONE_3D_"+base.M1_SHA+".json")


def configure():
    en.configure()
    base.REV=REV
    base.F6_SHA=NEW_GEO_SHA
    base.RUNS=HERE/"P10EV_R1_RUNS"
    base.PROOF=base.RUNS/"P10EV_R1_PREFLIGHT_PASS.json"
    base.LOCAL_MARKER=base.RUNS/"P10EV_R1_ONE_3D_USED.json"
    base.CONFIRM=CONFIRM
    base.source_gate=source_gate
    base.geometry_contract=geometry_contract
    base.global_marker=profile_marker
    base.make_evidence=evidence


def annotate_legacy_qa(meta: dict, run: Path) -> None:
    # Parent P10EA nine-zone targets are for old alpha=.20, NOT this C1 GEO.
    q=run/"QA"
    old=q/"P10EA_M1_M2_GEOMETRY_QA.json"
    need(old.is_file(),"inherited curved Tet10 geometry QA missing")
    actual=json.loads(old.read_text(encoding="utf-8"))
    need(actual["status"]=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM" and
         actual["m1_sha256"]==base.M1_SHA and
         actual["m2_sha256"]==meta["m2_mesh_sha256"] and
         not actual["geometry_issues"],"inherited geometry-only QA not GO")
    note={
        "revision":REV,
        "status":"P10EV_GEOMETRY_QA_PASS_D025_PENDING_NO_FEM",
        "m1_sha256":base.M1_SHA,
        "m2_sha256":meta["m2_mesh_sha256"],
        "new_geo_sha256":NEW_GEO_SHA,
        "canonical_geometry_QA_file":"P10EA_M1_M2_GEOMETRY_QA.json",
        "legacy_P10EA_nine_zone_model_target":"alpha=0.20, INAPPLICABLE_TO_P10EV",
        "P10EU_single_C1_realized_D025":"PENDING_INDEPENDENT_343_729QP",
        "D025_real_volume_gate_by_pole":[.75,.85],
        "surface_Tri6_hard_gate":False,
        "kappa0_preservation":"diagnostic",
        "physical_FEM":0,
        "allowed_for_physical_FEM":False,
    }
    (q/"P10EV_REAL_C1_GEOMETRY_ONLY_D025_PENDING.json").write_bytes(
        (json.dumps(note,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
    meta["P10EV_status"]=note["status"]


def evidence(run: Path) -> Path:
    # The inherited P10EA evidence formatter is read-only w.r.t. old runs.
    old=en.ek._original_make_evidence(run)
    new=run/"P10EV_EVIDENCE.zip"
    need(not new.exists(),"P10EV evidence already exists")
    old.rename(new)
    with zipfile.ZipFile(new,"a",compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("P10EV_REAL_C1_GEOMETRY_ONLY_D025_PENDING.json",):
            f=run/"QA"/name
            if f.is_file():
                z.write(f,"QA/"+name)
        for name in ("P10EU_C1_GMSH_SOURCE_AUDIT.json",PIN_NAME):
            z.write(HERE/name,"SOURCE/"+name)
    mesh=run/"P10EA_M2_CANDIDATE.msh"
    manifest=run/"P10EA_RUN_MANIFEST.json"
    if mesh.is_file() and manifest.is_file() and mesh.stat().st_size<=32*1024**2:
        meta=json.loads(manifest.read_text(encoding="utf-8"))
        need(meta.get("m2_mesh_sha256")==digest(mesh),
             "raw M2 SHA not registered in original run manifest")
        with zipfile.ZipFile(new,"a",compression=zipfile.ZIP_DEFLATED) as z:
            need("RAW/P10EA_M2_CANDIDATE.msh" not in z.namelist(),
                 "duplicate raw M2")
            z.write(mesh,"RAW/P10EA_M2_CANDIDATE.msh")
    return new


def do_run(*,preflight_only:bool) -> int:
    base.RUNS.mkdir(parents=True,exist_ok=True)
    run=base.RUNS/("P10EV_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta={"revision":REV,"status":"P10EV_STOP_NO_FEM",
          "mode":"SAFE_PREFLIGHT" if preflight_only else "ONE_NATIVE_3D_MESH",
          "m1_sha256":base.M1_SHA,"new_geo_sha256":NEW_GEO_SHA,
          "joint_C1_source_math_points":7620,
          "legacy_inherited_QA_alpha20_is_not_P10EV_field":True,
          "D025_real_north_south_bounds":[.75,.85],
          "native_parse_attempts":0,"native_parse_passed":[],
          "native_1d_2d_attempts":0,"native_3d_attempts":0,
          "physical_FEM_attempts":0,"wall_limit_s":base.WALL_S,
          "qa_limit_s":base.QA_WALL_S,
          "private_limit_bytes":base.PRIVATE_MAX,
          "mesh_limit_bytes":base.MESH_MAX,
          "log_limit_bytes":base.LOG_MAX,
          "started_utc":datetime.now(timezone.utc).isoformat()}
    code=2
    try:
        if not preflight_only:
            base.fresh_proof()
        sources=base.preflight(run,meta,prompt=preflight_only)
        print("P10EV source/real M1/native parse2 PASS; new C1 source pinned, "
              "real 3D D025 still UNKNOWN.",flush=True)
        if preflight_only:
            base.save_proof(meta,run)
            meta["status"]="P10EV_PREFLIGHT_PASS_NO_NEW_M2_NO_FEM"
            code=0
        else:
            print("One -3: -nt 2, <=900s, <=8GiB PRIVATE, <=750MiB mesh, "
                  "FEM=0. A used one-shot marker must NEVER be deleted.",flush=True)
            response=input("Type exactly "+CONFIRM+": ").strip()
            need(response==CONFIRM,"manual confirmation absent: no marker consumed")
            mesh=base.launch_m2(meta,run,sources["B_EXACT_INLINE_F6"])
            base.quality_gate(meta,run,Path(meta["m1_path"]),mesh)
            annotate_legacy_qa(meta,run)
            meta["status"]="P10EV_M2_GEOMETRY_QA_PASS_ADAPTIVITY_PENDING_NO_FEM"
            code=0
    except BaseException as exc:
        meta["stop_reason"]=str(exc)
        (run/"P10EA_STOP_TRACE.txt").write_text(
            traceback.format_exc(),encoding="utf-8")
        print("P10EV STOP:",exc,flush=True)
    finally:
        full=run/"P10EA_GMSH_FULL.log"
        if full.is_file():
            with full.open("rb") as f:
                f.seek(max(0,full.stat().st_size-80*1024))
                (run/"P10EA_GMSH_TAIL.txt").write_bytes(f.read())
        meta["finished_utc"]=datetime.now(timezone.utc).isoformat()
        (run/"P10EA_RUN_MANIFEST.json").write_bytes(
            (json.dumps(meta,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
        (run/"P10EA_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nNATIVE_M2_3D_ATTEMPTS="+
            str(meta["native_3d_attempts"])+"\nFEM=0\n"+
            "M1_SHA256="+base.M1_SHA+"\nM2_SHA256="+
            str(meta.get("m2_mesh_sha256","UNKNOWN"))+"\n"+
            "STOP_REASON="+str(meta.get("stop_reason",""))+"\n",
            encoding="utf-8")
        archive=evidence(run)
        print("P10EV RESULT:",meta["status"],"EVIDENCE:",archive,flush=True)
        print("Send ONLY P10EV_EVIDENCE.zip; raw M2 included when <=32MiB. "
              "Do not rerun 02. FEM=0.",flush=True)
    return code


def selftest() -> int:
    configure()
    original=source_gate()
    baseline,new=geometry_contract()
    base.mesh_qa.selftest()
    need(len(original["files"])==23 and
         baseline.endswith("Background Field=2;\n") and
         new.encode("utf-8")==(HERE/eu.GEO_NAME).read_bytes() and
         base.RUNS.name=="P10EV_R1_RUNS" and
         base.WALL_S==900 and base.PRIVATE_MAX==8*1024**3 and
         base.MESH_MAX==750*1024**2 and
         base.CONFIRM==CONFIRM,"P10EV pin/math/one-shot/resource contract")
    # Test single-shot consumption and refusal only inside a throwaway directory;
    # do not contact Gmsh or use the real Windows marker namespace.
    with tempfile.TemporaryDirectory(prefix="p10ev_marker_synthetic_") as td:
        root=Path(td)
        saved_local,saved_global=base.LOCAL_MARKER,base.global_marker
        try:
            base.LOCAL_MARKER=root/"LOCAL_USED.json"
            base.global_marker=lambda:root/"GLOBAL_USED.json"
            argv=["gmsh.exe","new.geo","-3"]
            base.consume_one_shot(root,argv)
            need(base.LOCAL_MARKER.is_file() and base.global_marker().is_file(),
                 "synthetic markers not consumed")
            try:
                base.consume_one_shot(root,argv)
            except RuntimeError:
                pass
            else:
                need(False,"second one-shot was not rejected")
            need(base.LOCAL_MARKER.is_file() and base.global_marker().is_file(),
                 "used markers changed by STOP")
        finally:
            base.LOCAL_MARKER,saved_global= saved_local,saved_global
            base.global_marker=saved_global
    print("P10EV_C1_ONE_M2_SOURCE_ONLY_SELFTEST_PASS",
          "P10EN_parent=PINNED","new_GEO_SHA=PASS",
          "old_markers=UNTOUCHED","fresh_marker_negative=PASS",
          "native_Gmsh=0 FEM=0")
    return 0


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--selftest",action="store_true")
    modes.add_argument("--preflight-only",action="store_true")
    modes.add_argument("--one-m2",action="store_true")
    args=p.parse_args()
    if args.selftest:
        return selftest()
    configure()
    return do_run(preflight_only=args.preflight_only)


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,KeyError,AssertionError) as exc:
        print("P10EV STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
