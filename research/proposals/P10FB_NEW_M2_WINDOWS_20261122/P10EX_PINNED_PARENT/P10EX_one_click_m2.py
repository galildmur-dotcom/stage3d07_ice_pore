#!/usr/bin/env python3
"""P10EX: exactly one explicitly authorized 3D M2 mesh-only, no FEM.

Only Windows native Gmsh 4.15.2 may execute -3, after new safe01/24h proof,
fresh local + profile marker, exact SHA/source/accepted M1 and manual phrase.
P10EW and every earlier historical one-shot source/marker remain immutable.
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
PARENT=HERE/"P10EW_PINNED_PARENT"
sys.path.insert(0,str(PARENT))
import P10EW_safe_parse_only as ew

base=ew.base
REV="P10EX_R1_ONE_AUTHORIZED_STRCAT_C1_M2_3D_MESH_ONLY"
PARENT_SHA="a375bff007a6ce4c04e3590877359e870f9044e0bc385a8d26f3bebf1415b968"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
NEW_GEO_SHA="d68570270dfb5ca2232d8fc94486e5638223b3604c933312b4036d5bb8d19b72"
CONFIRM="RUN ONE P10EX M2 3D MESH"
GEO_NAME="P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"
AUDIT_NAME="P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json"
PIN_NAME="P10EX_R1_SOURCE_SHA256.json"
FILES=(
    "P10EX_one_click_m2.py",
    "01_P10EX_SAFE_PREFLIGHT_ONLY.cmd",
    "02_P10EX_ONE_M2_3D_ONLY.cmd",
    "README_P10EX_RU.md",
    GEO_NAME,AUDIT_NAME,
)


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EX_STOP: "+why)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_contract() -> tuple[str,str]:
    baseline, corrected=ew.source_contract()  # rechecks old P10EU literal identity
    local=(HERE/GEO_NAME).read_text(encoding="utf-8")
    need(local==corrected and sha(HERE/GEO_NAME)==NEW_GEO_SHA and
         "StrCat(" in local and "Field[6] = MathEval;" in local and
         "Background Field=6;" in local and
         "Mesh.Algorithm3D=10;" in local and
         "Mesh 3;" not in local,
         "P10EX exact previously native-parsed StrCat GEO")
    return baseline,local


def source_gate() -> dict:
    try:
        parent_source=ew.source_gate()
        pin=json.loads((HERE/PIN_NAME).read_text(encoding="utf-8"))
        need(pin["revision"]==REV and pin["parent_p10ew_zip_sha256"]==PARENT_SHA
             and pin["new_geo_sha256"]==NEW_GEO_SHA
             and pin["m1_sha256"]==base.M1_SHA==M1_SHA
             and pin["one_native_3d_max"]==1 and pin["FEM"]==0
             and set(pin["files"])==set(FILES),
             "own exact P10EX source pin inventory / one Gmsh3D limit")
        for name,expected in pin["files"].items():
            need(Path(name).name==name and (HERE/name).is_file() and
                 sha(HERE/name)==expected,
                 "missing or modified pinned source "+name)
        audit=json.loads((HERE/AUDIT_NAME).read_text(encoding="utf-8"))
        need(audit["status"]=="P10EW_REAL_WINDOWS_PARSE2_PASS_NO_NEW_M2_NO_FEM"
             and audit["accepted_M1_sha256"]==M1_SHA
             and audit["corrected_C1_GEO_sha256"]==NEW_GEO_SHA
             and audit["native_parse_A_M1_Field2"]=="PASS"
             and audit["native_parse_B_StrCat_C1_Field6"]=="PASS"
             and audit["native_Gmsh_3d_attempts"]==audit["FEM_attempts"]==0
             and audit["original_4198_character_expression_byte_exact"] is True,
             "independently verified original P10EW native Windows parse2")
        source_contract()
        return parent_source
    finally:
        base.REV=REV
        base.F6_SHA=NEW_GEO_SHA


def global_marker() -> Path:
    appdata=os.environ.get("LOCALAPPDATA","")
    need(bool(appdata) and Path(appdata).is_dir(),"LOCALAPPDATA missing")
    return Path(appdata)/"Stage3D07"/("P10EX_R1_ONE_3D_"+M1_SHA+".json")


def configure() -> None:
    ew.configure()
    base.REV=REV
    base.F6_SHA=NEW_GEO_SHA
    base.RUNS=HERE/"P10EX_R1_RUNS"
    base.PROOF=base.RUNS/"P10EX_R1_PREFLIGHT_PASS.json"
    base.LOCAL_MARKER=base.RUNS/"P10EX_R1_ONE_3D_USED.json"
    base.CONFIRM=CONFIRM
    base.global_marker=global_marker
    base.source_gate=source_gate
    base.geometry_contract=source_contract
    base.make_evidence=evidence


def annotate_geometry_only(meta: dict, run: Path) -> None:
    old=run/"QA/P10EA_M1_M2_GEOMETRY_QA.json"
    need(old.is_file(),"inherited full curved27QP geometry QA missing")
    j=json.loads(old.read_text(encoding="utf-8"))
    need(j["status"]=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM"
         and j["m1_sha256"]==M1_SHA
         and j["m2_sha256"]==meta["m2_mesh_sha256"]
         and not j["geometry_issues"],
         "new M2 curved geometry status/sha not PASS")
    note={
        "revision":REV,
        "status":"P10EX_M2_CURVED_GEOMETRY_PASS_D025_PENDING_NO_FEM",
        "M1_SHA256":M1_SHA,
        "M2_SHA256":meta["m2_mesh_sha256"],
        "new_C1_StrCat_GEO_SHA256":NEW_GEO_SHA,
        "legacy_P10EA_9_zone_alpha20_target":"INAPPLICABLE_TO_P10EX_C1",
        "independent_real_D025":"PENDING_343_729QP_BY_NORTH_SOUTH",
        "D025_north_3D_Tet10_volume_ratio":[.75,.85],
        "D025_south_3D_Tet10_volume_ratio":[.75,.85],
        "kappa0_local_size":"diagnostic",
        "sizing_smoothness":"mandatory_no_numeric_gradient_threshold_YET",
        "Tri6_area":"diagnostic_not_hard_gate",
        "phi_uniformity":"NOT_REQUIRED",
        "global_element_growth_25_percent_cap":"NOT_REQUIRED",
        "FEM":0,"authorized_for_FEM":False,
    }
    dest=run/"QA/P10EX_REAL_C1_GEOMETRY_ONLY_D025_PENDING.json"
    dest.write_bytes((json.dumps(note,indent=2,ensure_ascii=False)+"\n").encode())
    meta["P10EX_3D_geometry"]=note["status"]


def evidence(run: Path) -> Path:
    original=ew.ev.en.ek._original_make_evidence(run)
    dst=run/"P10EX_EVIDENCE.zip"
    need(not dst.exists(),"do not overwrite existing P10EX evidence")
    original.rename(dst)
    with zipfile.ZipFile(dst,"a",compression=zipfile.ZIP_DEFLATED) as out:
        note=run/"QA/P10EX_REAL_C1_GEOMETRY_ONLY_D025_PENDING.json"
        if note.is_file():
            out.write(note,"QA/"+note.name)
        for name in (GEO_NAME,AUDIT_NAME,PIN_NAME):
            out.write(HERE/name,"SOURCE/"+name)
    m2=run/"P10EA_M2_CANDIDATE.msh"
    man=run/"P10EA_RUN_MANIFEST.json"
    if m2.is_file() and man.is_file() and m2.stat().st_size<=32*1024**2:
        j=json.loads(man.read_text(encoding="utf-8"))
        need(j.get("m2_mesh_sha256")==sha(m2),
             "new raw M2 hash differs from current run manifest")
        with zipfile.ZipFile(dst,"a",compression=zipfile.ZIP_DEFLATED) as out:
            need("RAW/P10EA_M2_CANDIDATE.msh" not in out.namelist(),
                 "raw M2 duplicate")
            out.write(m2,"RAW/P10EA_M2_CANDIDATE.msh")
    return dst


def run(*, preflight_only: bool) -> int:
    base.RUNS.mkdir(parents=True,exist_ok=True)
    path=base.RUNS/("P10EX_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    path.mkdir(exist_ok=False)
    meta={
        "revision":REV,
        "status":"P10EX_STOP_NO_FEM",
        "mode":"SAFE_PREFLIGHT" if preflight_only else "ONE_NATIVE_3D_MESH",
        "m1_sha256":M1_SHA,"new_geo_sha256":NEW_GEO_SHA,
        "P10EW_original_native_parse2":"INDEPENDENTLY_AUDITED_PASS",
        "D025_real_north_south_bounds":[.75,.85],
        "native_parse_attempts":0,"native_parse_passed":[],
        "native_1d_2d_attempts":0,"native_3d_attempts":0,
        "physical_FEM_attempts":0,
        "wall_limit_s":base.WALL_S,"qa_limit_s":base.QA_WALL_S,
        "private_limit_bytes":base.PRIVATE_MAX,
        "mesh_limit_bytes":base.MESH_MAX,
        "log_limit_bytes":base.LOG_MAX,
        "started_utc":datetime.now(timezone.utc).isoformat()
    }
    code=2
    try:
        if not preflight_only:
            base.fresh_proof()
        generated=base.preflight(path,meta,prompt=preflight_only)
        print("P10EX exact new C1 StrCat GEO, original M1 and both "
              "real native parse: PASS. 3D mesh D025 still unknown.",flush=True)
        if preflight_only:
            base.save_proof(meta,path)
            meta["status"]="P10EX_PREFLIGHT_PASS_NO_M2_NO_FEM"
            code=0
        else:
            print("EXACTLY ONE native Gmsh -3, nt2, wall900s, private8GiB, "
                  "mesh750MiB, FEM=0. Marker consumed permanently BEFORE -3. "
                  "Do not rerun 02 under any outcome.",flush=True)
            reply=input("Type exactly "+CONFIRM+": ").strip()
            need(reply==CONFIRM,"manual mesh-only confirmation absent")
            mesh=base.launch_m2(meta,path,generated["B_EXACT_INLINE_F6"])
            base.quality_gate(meta,path,Path(meta["m1_path"]),mesh)
            annotate_geometry_only(meta,path)
            meta["status"]="P10EX_M2_GEOMETRY_PASS_D025_PENDING_NO_FEM"
            code=0
    except BaseException as exc:
        meta["stop_reason"]=str(exc)
        (path/"P10EA_STOP_TRACE.txt").write_text(
            traceback.format_exc(),encoding="utf-8")
        print("P10EX STOP:",exc,flush=True)
    finally:
        full=path/"P10EA_GMSH_FULL.log"
        if full.is_file():
            with full.open("rb") as handle:
                handle.seek(max(0,full.stat().st_size-80*1024))
                (path/"P10EA_GMSH_TAIL.txt").write_bytes(handle.read())
        meta["finished_utc"]=datetime.now(timezone.utc).isoformat()
        (path/"P10EA_RUN_MANIFEST.json").write_bytes(
            (json.dumps(meta,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
        (path/"P10EA_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\n"+
            "NATIVE_M2_3D_ATTEMPTS="+str(meta["native_3d_attempts"])+"\n"+
            "FEM=0\nM1_SHA256="+M1_SHA+"\n"+
            "M2_SHA256="+str(meta.get("m2_mesh_sha256","UNKNOWN"))+"\n"+
            "STOP_REASON="+str(meta.get("stop_reason",""))+"\n",
            encoding="utf-8")
        archive=evidence(path)
        print("P10EX RESULT:",meta["status"],"EVIDENCE:",archive,flush=True)
        print("Send ONLY P10EX_EVIDENCE.zip, raw M2 included if <=32MiB. "
              "Never rerun 02 or delete one-shot markers. FEM=0.",flush=True)
    return code


def selftest() -> int:
    configure()
    inherited=source_gate()
    baseline,corrected=source_contract()
    base.mesh_qa.selftest()
    need(len(inherited["files"])==23 and
         baseline.endswith("Background Field=2;\n")
         and corrected.encode()==(HERE/GEO_NAME).read_bytes()
         and base.F6_SHA==NEW_GEO_SHA and
         base.REV==REV and base.CONFIRM==CONFIRM
         and base.RUNS.name=="P10EX_R1_RUNS"
         and base.WALL_S==900 and
         base.PRIVATE_MAX==8*1024**3
         and base.MESH_MAX==750*1024**2,
         "exact pinned new one-shot and resource limits")
    with tempfile.TemporaryDirectory(prefix="p10ex_marker_unit_") as tmp:
        saved_l,saved_g=base.LOCAL_MARKER,base.global_marker
        try:
            local,profile=Path(tmp)/"local.json",Path(tmp)/"profile.json"
            base.LOCAL_MARKER=local
            base.global_marker=lambda:profile
            base.consume_one_shot(Path(tmp),["gmsh.exe","new.geo","-3"])
            need(local.is_file() and profile.is_file(),
                 "both synthetic new one-shot markers created")
            before=(local.read_bytes(),profile.read_bytes())
            try:
                base.consume_one_shot(Path(tmp),["gmsh.exe","new.geo","-3"])
            except RuntimeError:
                pass
            else:
                need(False,"second one-shot run NOT stopped")
            need((local.read_bytes(),profile.read_bytes())==before,
                 "second blocked attempt changed consumed markers")
        finally:
            base.LOCAL_MARKER,base.global_marker=saved_l,saved_g
    print("P10EX_ONE_C1_M2_MESH_ONLY_SOURCE_SELFTEST_PASS",
          "pinned_previous_P10EW=PASS","original_M1=PASS",
          "synthetic_one_shot_second_attempt_STOP=PASS",
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
    return run(preflight_only=args.preflight_only)


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,KeyError,AssertionError) as exc:
        print("P10EX STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
