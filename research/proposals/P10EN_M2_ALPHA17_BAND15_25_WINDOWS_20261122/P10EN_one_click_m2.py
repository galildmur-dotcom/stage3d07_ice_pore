#!/usr/bin/env python3
"""P10EN: source-pinned independent alpha17 M2 one-shot, Gmsh only, no FEM.

The exact original P10EK and P10EA parents are nested immutable sources;
old one-shot markers are never inspected, overwritten or removed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import tempfile
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PARENT_DIR = HERE / "P10EK_PINNED_PARENT"
sys.path.insert(0, str(PARENT_DIR))
import P10EK_one_click_m2 as ek

base = ek.base
REV = "P10EN_R1_ONE_NATIVE_3D_M2_ALPHA17_BAND15_25_MESH_ONLY"
PARENT_ZIP_SHA = "f9cf0bb54e6032115b6c001c60c0cf19af2280b97432b21be1c765bcedaf7b58"
PARENT_GEO_SHA = "2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5"
NEW_GEO_SHA = "b54db4fe70c8661fe4faa70985893ca0a3b0c01ff619d3727f2cb8030fe3a0e6"
ALPHA = .17
LOWER = .75
UPPER = .85
CONFIRM = "RUN ONE P10EN M2 3D MESH"
GEO_NAME = "P10EN_B_F6_ALG5_ALPHA17.geo"
PIN_NAME = "P10EN_R1_SOURCE_SHA256.json"
NEW_FILES = (
    "P10EN_one_click_m2.py", GEO_NAME,
    "01_P10EN_SAFE_PREFLIGHT_ONLY.cmd", "02_P10EN_ONE_M2_3D_ONLY.cmd",
    "README_P10EN_RU.md",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EN_STOP: " + why)


def geometry_contract() -> tuple[str, str]:
    original, alg5 = ek.geometry_contract()  # exact, pinned original alpha=.20
    replacements = (
        ("Target V_M2/V_M1=1-0.2*kappa.",
         "Target V_M2/V_M1=1-0.17*kappa."),
        ("Target h_M2/h_M1=(1-0.2*kappa)^(1/3) in [0.9283177667,1].",
         "Target h_M2/h_M1=(1-0.17*kappa)^(1/3) in [0.9397796375,1]."),
        ("Field[6].F = \"F2*exp(log(1-0.2*", "Field[6].F = \"F2*exp(log(1-0.17*"),
    )
    new = alg5
    for old, target in replacements:
        need(new.count(old) == 1, "ambiguous original alpha field replacement")
        new = new.replace(old, target, 1)
    need(new.count("1-0.2*") == 0 and new.count("0.17") == 3 and
         new.count("Mesh.Algorithm = 5;") == 1 and
         new.count("Field[6] = MathEval;") == 1 and
         new.count("Background Field=6;") == 1 and
         not any(f"Field[{i}] = MathEval;" in new for i in (3, 4, 5)) and
         hashlib.sha256(new.encode("utf-8")).hexdigest() == digest(HERE / GEO_NAME) and
         (HERE / GEO_NAME).read_bytes() == new.encode("utf-8"),
         "new alpha17 B GEO differs from original Alg5 by more than coefficient")
    return original, new


def alpha_math_selftest() -> dict:
    """17075 independent size samples; no nested MathEval/Gmsh/FEM."""
    _, geo = geometry_contract()
    expr = geo.split('Field[6].F = "', 1)[1].split('";', 1)[0]
    need(expr.startswith("F2*exp(log(1-0.17*") and
         base.exact_math.re.findall(r"\bF\d+\b", expr) == ["F2"],
         "new expression is nested or wrong alpha")
    code = base.exact_math.compile_scalar(expr, {"F2", "x", "y", "z"})
    points = []
    for d in (0., .000000001, .00005, .0001, .000100001, .0002,
              .0003, .000499999, .0005, .000500001, .001, .005, .02):
        for mu in (-1., -.999999, -.8, -.799999, -.7, -.6, -.599999,
                   0., .599999, .6, .7, .799999, .8, .999999, 1.):
            for phi in (0., .4, 1.8, 3.14, 4.9):
                rad = .001 + d
                xy = rad * math.sqrt(max(0., 1.-mu*mu))
                points.append((xy*math.cos(phi), xy*math.sin(phi), .03+rad*mu))
    rng = random.Random(20261122)
    for _ in range(16100):
        d = .00055*rng.random() if rng.random() < .70 else .025*rng.random()
        mu = 2*rng.random()-1
        phi = 2*math.pi*rng.random()
        rad = .001+d
        xy = rad*math.sqrt(max(0., 1.-mu*mu))
        points.append((xy*math.cos(phi), xy*math.sin(phi), .03+rad*mu))
    need(len(points) == 17075 and
         base.exact_math.smoothstep_derivative(0.) == 0. and
         base.exact_math.smoothstep_derivative(1.) == 0.,
         "spatial smoothstep/point count invariant")
    maxdiff, lo, hi = 0., 1., 0.
    for x, y, z in points:
        k = base.exact_math.independent_kappa_xyz(x, y, z)
        need(0. <= k <= 1., "independent kappa outside [0,1]")
        lo, hi = min(lo, k), max(hi, k)
        for f2 in (base.exact_math.F2_MIN,
                   (base.exact_math.F2_MIN+base.exact_math.F2_MAX)/2,
                   base.exact_math.F2_MAX):
            realized = base.exact_math.value(code, F2=f2, x=x, y=y, z=z)
            target = f2 * (1.-ALPHA*k)**(1./3.)
            diff = abs(realized-target)/f2
            maxdiff = max(maxdiff, diff)
            need(diff <= 3e-12 and
                 abs((realized/f2)**3-(1.-ALPHA*k)) <= 3e-12 and
                 (.83**(1./3.)-1e-12) <= realized/f2 <= 1.+1e-12,
                 "new Gmsh F6 failed independent alpha17 cubic-size test")
    need(lo == 0. and hi == 1. and maxdiff <= 3e-12,
         "kappa endpoint or exact target error")
    return {"points":len(points), "f2_per_point":3,
            "alpha":ALPHA,"target_volume_ratio_kappa_one":1.-ALPHA,
            "realized_acceptance_ratio_kappa_one":[LOWER,UPPER],
            "max_normalized_h_error":maxdiff}


def source_gate():
    try:
        inherited = ek.source_gate()  # inherited P10EK + P10EA original SHA tests
    finally:
        base.REV = REV
        base.F6_SHA = NEW_GEO_SHA
    pin = json.loads((HERE/PIN_NAME).read_text(encoding="utf-8"))
    need(pin.get("revision") == REV and pin.get("one_native_3d_max") == 1 and
         pin.get("physical_FEM") is False and
         pin.get("parent_p10ek_zip_sha256") == PARENT_ZIP_SHA and
         pin.get("parent_alg5_geo_sha256") == PARENT_GEO_SHA and
         pin.get("new_alpha") == ALPHA and
         pin.get("acceptance_ratio_kappa_one") == [LOWER,UPPER] and
         pin.get("new_geo_sha256") == base.F6_SHA and
         set(pin.get("files", {})) == set(NEW_FILES),
         "new alpha17 package source/acceptance pins")
    for name, expected in pin["files"].items():
        need(Path(name).name == name and (HERE/name).is_file() and
             digest(HERE/name) == expected, "source modified: " + name)
    geometry_contract()
    alpha_math_selftest()
    return inherited


def profile_marker() -> Path:
    appdata = os.environ.get("LOCALAPPDATA", "")
    need(bool(appdata) and Path(appdata).is_dir(), "LOCALAPPDATA missing")
    return Path(appdata)/"Stage3D07"/("P10EN_R1_ONE_3D_"+base.M1_SHA+".json")


def evidence(run: Path) -> Path:
    old = ek._original_make_evidence(run)  # inherited original QA/logs only
    new = run/"P10EN_EVIDENCE.zip"
    need(not new.exists(), "evidence already exists")
    old.rename(new)
    # The inherited P10EA QA is an unchanged alpha20 source with legacy
    # target labels. Preserve it; append a separately SHA-checked alpha17
    # interpretation whenever the new QA was completed successfully.
    with zipfile.ZipFile(new,"a",compression=zipfile.ZIP_DEFLATED) as z:
        for name in ("P10EN_ALPHA17_GEOMETRY_AND_TARGET_CONTRACT.json",
                     "P10EN_ALPHA17_9_ZONE_COMPARISON.csv"):
            f=run/"QA"/name
            if f.is_file():
                z.write(f,"QA/"+name)
    mesh = run/"P10EA_M2_CANDIDATE.msh"
    manifest = run/"P10EA_RUN_MANIFEST.json"
    if mesh.is_file() and manifest.is_file() and mesh.stat().st_size <= 32*1024**2:
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        need(meta.get("m2_mesh_sha256") == digest(mesh),
             "raw M2 SHA did not match original run manifest")
        with zipfile.ZipFile(new,"a",compression=zipfile.ZIP_DEFLATED) as z:
            need("RAW/P10EA_M2_CANDIDATE.msh" not in z.namelist(),
                 "duplicate embedded M2")
            z.write(mesh,"RAW/P10EA_M2_CANDIDATE.msh")
    return new


def alpha17_target_qa(meta: dict, run: Path) -> None:
    """Correct *target labels only*; preserve all original geometry data."""
    folder=run/"QA"
    legacy=folder/"P10EA_M1_M2_9_ZONE_VOLUME_COMPARISON.csv"
    need(legacy.is_file(),"inherited nine-zone QA CSV missing")
    with legacy.open("r",encoding="utf-8",newline="") as f:
        original=list(csv.DictReader(f))
    need(len(original)==9,"inherited nine-zone count")
    new=[]
    for row in original:
        k=float(row["m1_mean_kappa_centroid"])
        legacy_target=float(row["model_mean_target_volume_ratio_at_m1_centroids"])
        need(0. <= k <= 1. and abs(legacy_target-(1.-.20*k)) < 2e-12,
             "inherited QA alpha20 target did not match original kappa")
        new.append({"radial_zone":row["radial_zone"],
                    "polar_zone":row["polar_zone"],
                    "m1_tet10":row["m1_tet10"],
                    "m2_tet10":row["m2_tet10"],
                    "m1_mean_kappa_centroid":row["m1_mean_kappa_centroid"],
                    "m2_mean_kappa_centroid":row["m2_mean_kappa_centroid"],
                    "P10EN_model_mean_target_ratio_alpha17":format(1.-ALPHA*k,".17g"),
                    "observed_unpaired_curved27qp_ratio":row[
                         "observed_unpaired_median_curved27qp_volume_ratio_m2_over_m1"],
                    "unpaired_diagnostic_not_independent_D025_GO":True})
    with (folder/"P10EN_ALPHA17_9_ZONE_COMPARISON.csv").open(
            "w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(new[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(new)
    audit={"protocol":"P10EN_ALPHA17_TARGET_OVERLAY_PRESERVE_PINNED_P10EA_QA",
           "original_legacy_QA_target_coefficient":.20,
           "new_actual_GEO_target_coefficient":ALPHA,
           "new_alpha17_target_volume_bounds":[1.-ALPHA,1.],
           "realized_kappa1_acceptance_ratio_bounds":[LOWER,UPPER],
           "nine_zone_field_values_changed":False,
           "nine_spatial_zones_checked":len(new),
           "original_inherited_geometry_QA":"P10EA_M1_M2_GEOMETRY_QA.json",
           "legacy_QA_target_labels_are_not_P10EN_targets":True,
           "independent_raw_M2_spatial_D025_gate":"PENDING_USER_EVIDENCE",
           "m2_geometry_accepted_for_physical_FEM":False,"physical_FEM_runs":0}
    (folder/"P10EN_ALPHA17_GEOMETRY_AND_TARGET_CONTRACT.json").write_text(
        json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    meta["new_alpha17_9_zone_overlay"]="P10EN_ALPHA17_TARGET_OVERLAY_PASS_NO_FEM"


def configure():
    ek.configure()  # pinned parent configuration; then override ONLY new identity
    base.REV = REV
    base.F6_SHA = NEW_GEO_SHA
    base.RUNS = HERE/"P10EN_R1_RUNS"
    base.PROOF = base.RUNS/"P10EN_R1_PREFLIGHT_PASS.json"
    base.LOCAL_MARKER = base.RUNS/"P10EN_R1_ONE_3D_USED.json"
    base.CONFIRM = CONFIRM
    base.source_gate = source_gate
    base.geometry_contract = geometry_contract
    base.global_marker = profile_marker
    base.make_evidence = evidence


def do_run(*, preflight_only: bool) -> int:
    base.RUNS.mkdir(parents=True, exist_ok=True)
    run = base.RUNS/("P10EN_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    run.mkdir(exist_ok=False)
    meta = {"revision":REV,"status":"P10EN_STOP_NO_FEM",
            "mode":"SOURCE_ONLY_PREFLIGHT" if preflight_only else "ONE_M2_3D",
            "original_m1_sha256":base.M1_SHA,
            "f6_sha256":base.F6_SHA,
            "kappa_C1_range":[0.,1.],
            "target_local_volume_ratio":"1-0.17*kappa; not a guarantee for realized Tet10",
            "realized_acceptance_kappa_one_volume_ratio":[LOWER,UPPER],
            "alpha":ALPHA,
            "native_parse_attempts":0,"native_parse_passed":[],
            "native_1d_2d_attempts":0,"native_3d_attempts":0,
            "physical_FEM_attempts":0,
            "new_alpha_math_points":17075,
            "wall_limit_s":base.WALL_S,"qa_limit_s":base.QA_WALL_S,
            "private_limit_bytes":base.PRIVATE_MAX,
            "mesh_limit_bytes":base.MESH_MAX,"log_limit_bytes":base.LOG_MAX,
            "started_utc":datetime.now(timezone.utc).isoformat()}
    code = 2
    try:
        if not preflight_only:
            base.fresh_proof()
        sources = base.preflight(run, meta, prompt=preflight_only)
        print("P10EN PREFLIGHT PASS: original M1, exact alpha17 math17075, "
              "native Gmsh parse2/2 and curved27QP; no new FEM.",flush=True)
        if preflight_only:
            base.save_proof(meta,run)
            meta["status"]="P10EN_SAFE_PREFLIGHT_PASS_NO_M2_NO_FEM"
            code=0
        else:
            print("P10EN ONE M2 -3: 2 threads, wall<=900s, private<=8GiB, "
                  "mesh<=750MiB, no FEM.",flush=True)
            response = input("Type exactly "+CONFIRM+": ").strip()
            base.stop_if_false(response == CONFIRM,
                               "P10EN manual confirmation absent; no marker consumed")
            mesh = base.launch_m2(meta,run,sources["B_EXACT_INLINE_F6"])
            base.quality_gate(meta,run,Path(meta["m1_path"]),mesh)
            alpha17_target_qa(meta,run)
            meta["status"]="P10EN_M2_GEOMETRY_QA_OK_ADAPTIVITY_PENDING_NO_FEM"
            code=0
    except BaseException as exc:
        meta["stop_reason"]=str(exc)
        (run/"P10EA_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
        print("P10EN STOP:",exc,flush=True)
    finally:
        full = run/"P10EA_GMSH_FULL.log"
        if full.is_file():
            with full.open("rb") as stream:
                stream.seek(max(0,full.stat().st_size-80*1024))
                tail=stream.read()
            (run/"P10EA_GMSH_TAIL.txt").write_bytes(tail)
        meta["finished_utc"]=datetime.now(timezone.utc).isoformat()
        (run/"P10EA_RUN_MANIFEST.json").write_text(
            json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        (run/"P10EA_RESULT.txt").write_text(
            "RESULT="+meta["status"]+"\nNATIVE_M2_3D_ATTEMPTS="+
            str(meta["native_3d_attempts"])+"\nFEM=0\n"+
            "M1_SHA256="+base.M1_SHA+"\nM2_SHA256="+
            str(meta.get("m2_mesh_sha256","UNKNOWN"))+"\n"+
            "STOP_REASON="+str(meta.get("stop_reason",""))+"\n",encoding="utf-8")
        archive = evidence(run)
        print("P10EN RESULT:",meta["status"],"EVIDENCE:",archive,flush=True)
        print("Send ONLY P10EN_EVIDENCE.zip. Leave all old/new markers untouched. FEM=0.",
              flush=True)
    return code


def selftest() -> int:
    inherited=source_gate()
    a,b=geometry_contract()
    mathcheck=alpha_math_selftest()
    base.mesh_qa.selftest()
    with tempfile.TemporaryDirectory(prefix="p10en_alpha17_overlay_unit_") as tmp:
        run=Path(tmp)
        (run/"QA").mkdir()
        k_values=(0., .25, .5, .75, 1., .125, .375, .625, .875)
        rows=[]
        for i,k in enumerate(k_values):
            rows.append({"radial_zone":str(i//3),"polar_zone":str(i%3),
                         "m1_tet10":str(10+i),"m2_tet10":str(11+i),
                         "m1_mean_kappa_centroid":str(k),
                         "m2_mean_kappa_centroid":str(k),
                         "model_mean_target_volume_ratio_at_m1_centroids":str(1.-.20*k),
                         "observed_unpaired_median_curved27qp_volume_ratio_m2_over_m1":"0.83"})
        with (run/"QA/P10EA_M1_M2_9_ZONE_VOLUME_COMPARISON.csv").open(
                "w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
            writer.writeheader();writer.writerows(rows)
        local_meta={}
        alpha17_target_qa(local_meta,run)
        summary=json.loads((run/"QA/P10EN_ALPHA17_GEOMETRY_AND_TARGET_CONTRACT.json").read_text())
        with (run/"QA/P10EN_ALPHA17_9_ZONE_COMPARISON.csv").open(newline="") as f:
            checked=list(csv.DictReader(f))
        need(len(checked)==9 and abs(float(checked[4]["P10EN_model_mean_target_ratio_alpha17"])-.83)<1e-14 and
             summary["legacy_QA_target_labels_are_not_P10EN_targets"] and
             not summary["m2_geometry_accepted_for_physical_FEM"] and
             local_meta["new_alpha17_9_zone_overlay"]=="P10EN_ALPHA17_TARGET_OVERLAY_PASS_NO_FEM",
             "alpha17 source-only QA overlay synthetic test")
    need(len(inherited["files"])==23 and a.endswith("Background Field=2;\n") and
         b.endswith("Background Field=6;\n") and
         mathcheck["points"]==17075 and
         base.RUNS.name=="P10EN_R1_RUNS" and
         base.CONFIRM==CONFIRM and
         base.WALL_S==900 and base.PRIVATE_MAX==8*1024**3 and
         base.MESH_MAX==750*1024**2,
         "source/math/pin/one-shot/resource contract")
    print("P10EN_ALPHA17_BAND15_25_SOURCE_ONLY_SELFTEST_OK "
          "parent_P10EA_SHA23=PASS parent_P10EK_SHA5=PASS "
          "new_alpha17_math17075=PASS curved27QP=PASS QA_overlay9=PASS "
          "isolated_one_shot=PASS native_3D_runs=0 FEM=0")
    return 0


def main():
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--selftest",action="store_true")
    modes.add_argument("--preflight-only",action="store_true")
    modes.add_argument("--one-m2",action="store_true")
    args=parser.parse_args()
    configure()
    return selftest() if args.selftest else do_run(preflight_only=args.preflight_only)


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,KeyError,AssertionError) as exc:
        print("P10EN STOP:",exc)
        raise SystemExit(2)
