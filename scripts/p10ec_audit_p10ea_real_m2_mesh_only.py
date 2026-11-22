#!/usr/bin/env python3
"""P10EC: independently audit true P10EA Windows M2 native -3 + geometric QA.

No native Gmsh/FEM is run. Original ZIP is immutable. Tamper tests mutate
only in-memory snapshots. Exact M1 and M2 meshes/exe are not present here.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import csv
import io
import json
import math
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"research/evidence/P10EC_P10EA_REAL_M2_MESH_QA_20261122/input/P10EA_EVIDENCE_M2.zip"
RELEASE=ROOT/"research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip"
DERIVED=ROOT/"research/evidence/P10EC_P10EA_REAL_M2_MESH_QA_20261122/derived/P10EC_P10EA_REAL_M2_AUDIT.json"
ZIP_SHA="85c1c252bdc8170fa2e8e1b26ae51e29f41626b6bd041068a64f33a62095a3a9"
RELEASE_SHA="8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
REV="P10EA_R1_EXACT_INLINE_F6_ONE_M2_3D_MESH_ONLY"
M1_SHA="ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
M2_SHA="ba1f1a0553a568c1b399acadd52bce1c1dc32e8d1c6b3ab1ce6759c547e5dee5"
F6_SHA="32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
BASE_SHA="c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8"
CAD_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
GMSH_SHA="317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
RUN="P10EA_20261122_044007_248420"
FULL="P10EA_GMSH_FULL.log"
TAIL="P10EA_GMSH_TAIL.txt"
GEOMETRY="QA/P10EA_M1_M2_GEOMETRY_QA.json"
ZONES="QA/P10EA_M1_M2_9_ZONES.csv"
COMPARE="QA/P10EA_M1_M2_9_ZONE_VOLUME_COMPARISON.csv"
RADIAL=("0_100um","100_500um","500um_plus")
POLAR=("polar_abs_mu_ge_0p8","taper_abs_mu_0p6_0p8","off_abs_mu_le_0p6")
EXPECTED={
    "P10EA_RUN_MANIFEST.json","P10EA_RESULT.txt",FULL,TAIL,"P10EA_QA.log",
    "A_ORIGINAL_M1_FIELD2_PARSE.log","B_EXACT_INLINE_F6_PARSE.log",
    GEOMETRY,ZONES,COMPARE,"GEO/A_ORIGINAL_M1_FIELD2.geo",
    "GEO/B_EXACT_INLINE_F6.geo","GEO/sphere_pore_B6_refined.geo",
    "P10EA_M1_LABEL_SUMMARY.json",
}
CAD_VOLUME=.06*.06*.05-4.*math.pi*(.001**3)/3.


def stop(ok: bool,why: str) -> None:
    if not ok:
        raise ValueError("P10EC_STOP: "+why)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def archive(path: Path) -> dict[str,bytes]:
    with zipfile.ZipFile(path) as z:
        stop(z.testzip() is None,"ZIP CRC")
        names=z.namelist()
        stop(len(names)==len(set(names)),"duplicate ZIP member")
        return {name:z.read(name) for name in names}


def as_json(files: dict[str,bytes],name: str) -> dict:
    return json.loads(files[name].decode("utf-8"))


def rows(files: dict[str,bytes],name: str) -> list[dict]:
    r=csv.DictReader(io.StringIO(files[name].decode("utf-8")))
    return list(r)


def parse_geo_log(log: str,name: str) -> float:
    lines=log.splitlines()
    stop(len(lines)>5 and "Running " in lines[0] and
         "-parse_and_exit" in lines[0] and
         "[Gmsh 4.15.2" in lines[0] and
         "GEO\\"+name+".geo" in lines[0],
         "native parse CLI "+name)
    stop(sum("Running " in line for line in lines)==1 and
         " -3 " not in lines[0] and " -1 " not in lines[0],
         "native GEO parse unexpectedly meshed "+name)
    stop(any("Done reading " in x and "sphere_pore_B6_refined.geo" in x
             for x in lines) and
         any("Done reading " in x and ("GEO\\"+name+".geo") in x for x in lines),
         "native GEO parse CAD/file completion "+name)
    stop(not any(re.search(r"^\s*(Error|Fatal)\s*:",x) for x in lines),
         "Gmsh GEO error "+name)
    matches=re.findall(r"From start:\s*Wall\s*([0-9.]+)s",log)
    stop(len(matches)==1 and 0<=float(matches[0])<=20,
         "parse-only native wall "+name)
    return float(matches[0])


def real_gmsh_log(log: str) -> dict:
    lines=log.splitlines()
    stop(lines and sum("Running " in x for x in lines)==1 and
         "-3 -nt 2 -format msh2 -o " in lines[0] and
         "GEO\\B_EXACT_INLINE_F6.geo" in lines[0] and
         "P10EA_M2_CANDIDATE.msh" in lines[0] and
         "[Gmsh 4.15.2, 1 node, max. 2 threads]" in lines[0],
         "one exact native Gmsh -3 CLI / sources")
    phases=("Done meshing 1D","Done meshing 2D","Done meshing 3D",
            "Done meshing order 2","Optimization succeeded",
            "Done optimizing mesh","14157 nodes 11395 elements",
            "Done writing ","Stopped on ")
    positions=[log.find(p) for p in phases]
    stop(all(i>=0 for i in positions) and positions==sorted(positions),
         "native 1D/2D/3D/order2/high-order/write lifecycle")
    stop("Meshing curve 14" in log and "Meshing curve 17" in log,
         "historical circles were not traversed")
    stop(not any(re.search(r"^\s*(Error|Fatal)\s*:",line) for line in lines),
         "native Gmsh Error")
    match=re.search(r"From start:\s*Wall\s*([0-9.]+)s",log)
    stop(match is not None,"native total wall absent")
    t=float(match.group(1))
    stop(0<t<900,"native Gmsh wall exceeds safety cap")
    stage=re.search(r"Done meshing 3D \(Wall ([0-9.]+)s",log)
    stop(stage is not None,"native 3D stage wall absent")
    return {"native_total_wall_s":t,"native_3d_stage_wall_s":float(stage.group(1)),
            "nodes_reported":14157,"all_elements_reported":11395}


def audit(files: dict[str,bytes],source: dict[str,bytes]) -> dict:
    stop(set(files)==EXPECTED,"14 exact evidence members")
    m=as_json(files,"P10EA_RUN_MANIFEST.json")
    qa=as_json(files,GEOMETRY)
    label=as_json(files,"P10EA_M1_LABEL_SUMMARY.json")
    result=files["P10EA_RESULT.txt"].decode("utf-8")
    stop(m.get("revision")==REV and m.get("status")=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM" and
         m.get("mode")=="ONE_M2_3D" and
         result.startswith("RESULT=P10EA_M2_GEOMETRY_QA_OK_NO_FEM") and
         "NATIVE_M2_3D_ATTEMPTS=1" in result and "FEM=0" in result and
         "STOP_REASON=\r\n" in result,
         "manifest/result final success contradiction")
    stop(m.get("source_sha_pins")==23 and m.get("math_points")==17075 and
         m.get("native_parse_attempts")==2 and
         m.get("native_parse_passed")==["A_ORIGINAL_M1_FIELD2","B_EXACT_INLINE_F6"] and
         m.get("native_3d_attempts")==1 and m.get("native_1d_2d_attempts")==0 and
         m.get("physical_FEM_attempts")==0,
         "source/parse/one shot/FEM counters")
    stop(m.get("m1_sha256")==M1_SHA and m.get("original_m1_sha256")==M1_SHA and
         m.get("m2_mesh_sha256")==M2_SHA and
         m.get("gmsh_sha256")==GMSH_SHA and m.get("f6_sha256")==F6_SHA and
         m.get("m2_mesh_bytes")==1652317 and
         m.get("kappa_C1_range")==[0.,1.] and
         m.get("target_local_volume_ratio") ==
           "1-0.20*kappa; not guaranteed per realized Tet10",
         "original M1/exe/M2 Windows SHA and kappa target")
    stop(m.get("gmsh_path")==r"C:\gmsh-4.15.2-Windows64\gmsh.exe" and
         m.get("m1_path","").endswith(r"\P10DG_M1_CANDIDATE.msh") and
         RUN in m.get("m1_label_dir",""),
         "original accepted M1 exact path and run identity")
    stop(m.get("wall_limit_s")==900 and m.get("qa_limit_s")==300 and
         m.get("private_limit_bytes")==8*1024**3 and
         m.get("mesh_limit_bytes")==750*1024**2 and
         m.get("log_limit_bytes")==16*1024**2 and
         m.get("free_ram_bytes",0)>=16*1024**3 and
         m.get("free_disk_bytes",0)>=4*1024**3,
         "native resource gate and fixed caps")
    native=m.get("native_3d_result",{})
    stop(native.get("status")=="STARTED" and native.get("exit_code")==0 and
         0<native.get("polled_wall_s",0)<900 and
         0<=native.get("polled_peak_private_bytes",-1)<8*1024**3 and
         native.get("log_bytes")==len(files[FULL]) and
         native.get("argv",[])[2:8]==["-3","-nt","2","-format","msh2","-o"] and
         len(native.get("argv",[]))==9 and
         RUN in native["argv"][1] and native["argv"][-1].endswith(
             r"\P10EA_M2_CANDIDATE.msh"),
         "native exact argv/exit/resources")
    quality=m.get("quality_audit_result",{})
    stop(quality.get("status")=="STARTED" and quality.get("exit_code")==0 and
         0<quality.get("polled_wall_s",0)<300 and
         0<=quality.get("polled_peak_private_bytes",-1)<8*1024**3 and
         quality.get("log_bytes")==len(files["P10EA_QA.log"]) and
         m.get("geometry_qa_status")=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM" and
         "--m1" in quality.get("argv",[]) and "--m2" in quality.get("argv",[]),
         "bounded QA exit/status/resource report")
    log=files[FULL].decode("utf-8")
    stop(files[FULL]==files[TAIL] and len(files[FULL])==7816,
         "full original native log/tail byte parity")
    stage=real_gmsh_log(log)
    stop("P10EA_M2_GEOMETRY_QA_OK_NO_FEM" in
         files["P10EA_QA.log"].decode("utf-8") and
         "M2_curved27QP 263250" in files["P10EA_QA.log"].decode("utf-8"),
         "original QA stdout confirmation")
    base=(source["P10DN_M2_FIELD20.geo"].decode("utf-8").split("// F3:",1)[0]
          +"\nBackground Field=2;\n")
    stop(files["GEO/A_ORIGINAL_M1_FIELD2.geo"]==base.encode("utf-8") and
         files["GEO/B_EXACT_INLINE_F6.geo"]==source["P10DV_M2_INLINE_FIELD20.geo"] and
         files["GEO/sphere_pore_B6_refined.geo"]==
           source["sphere_pore_B6_refined.geo"] and
         digest(files["GEO/A_ORIGINAL_M1_FIELD2.geo"])==BASE_SHA and
         digest(files["GEO/B_EXACT_INLINE_F6.geo"])==F6_SHA and
         digest(files["GEO/sphere_pore_B6_refined.geo"])==CAD_SHA,
         "original generated GEO3/3 byte provenance")
    stop(m.get("generated_geo_sha256")=={
         "A_ORIGINAL_M1_FIELD2":BASE_SHA,"B_EXACT_INLINE_F6":F6_SHA},
         "manifest GEO SHA consistency")
    parse_wall={}
    for name in ("A_ORIGINAL_M1_FIELD2","B_EXACT_INLINE_F6"):
        parse_wall[name]=parse_geo_log(
            files[name+"_PARSE.log"].decode("utf-8"),name)
    stop(label.get("m1_sha256")==M1_SHA and label.get("nodes")==14145 and
         label.get("tet10")==9736 and label.get("pore_tri6")==178 and
         label.get("label_counts")=={"zero":9477,"one":21,"intermediate":238},
         "exact original M1 full coefficient label")
    stop(qa.get("protocol")==REV and
         qa.get("status")=="P10EA_M2_GEOMETRY_QA_OK_NO_FEM" and
         qa.get("m1_sha256")==M1_SHA and qa.get("m2_sha256")==M2_SHA and
         qa.get("m1_tet10")==9736 and qa.get("m2_tet10")==9750 and
         qa.get("m1_nodes")==14145 and qa.get("m2_nodes")==14157 and
         qa.get("m1_pore_tri6")==178 and qa.get("m2_pore_tri6")==170 and
         qa.get("m1_curved_qp_count")==262872 and
         qa.get("m2_curved_qp_count")==263250 and
         qa.get("m1_curved_qp_nonpositive")==0 and
         qa.get("m2_curved_qp_nonpositive")==0 and
         qa.get("m1_geometry_issues")==[] and qa.get("m2_geometry_issues")==[] and
         qa.get("geometry_issues")==[] and
         qa.get("m2_geometry_accepted_for_physical_FEM") is False and
         qa.get("user_must_review_9_zone_ratios") is True and
         qa.get("FEM_runs")==0 and
         qa.get("m1_label_coverage",{}).get("tet10_labeled")==9736 and
         qa.get("m2_label_coverage",{}).get("tet10_labeled")==9750,
         "complete self-reported curved27QP/geometry/source QA contract")
    list_zones=rows(files,ZONES)
    compare=rows(files,COMPARE)
    stop(len(list_zones)==18 and len(compare)==9,
         "expected 18 per-mesh and 9 comparison rows")
    indexed={}
    for item in list_zones:
        key=(item.get("mesh"),item.get("radial_zone"),item.get("polar_zone"))
        stop(key not in indexed and key[0] in ("M1","M2") and
             key[1] in RADIAL and key[2] in POLAR,
             "duplicate/wrong 9-zone grid")
        indexed[key]=item
    stop(len(indexed)==18,"3x3 coverage both meshes")
    volumes={}
    mean_kappa={}
    for mesh,expected in (("M1",9736),("M2",9750)):
        group=[x for (mm,_,_),x in indexed.items() if mm==mesh]
        count=sum(int(x["tet10"]) for x in group)
        stop(count==expected,"9-zone global Tet10 count "+mesh)
        volumes[mesh]=math.fsum(int(x["tet10"])*float(x["mean_curved27qp_volume_m3"])
                                 for x in group)
        mean_kappa[mesh]=math.fsum(int(x["tet10"])*float(x["kappa_centroid_mean"])
                                   for x in group)/count
        stop(abs(volumes[mesh]/CAD_VOLUME-1.)<1e-6,
             "independent 9-zone curved volume sum vs exact CAD "+mesh)
        for item in group:
            k=float(item["kappa_centroid_mean"])
            target=float(item["mean_target_volume_ratio"])
            stop(0<=k<=1 and abs(target-(1.-.2*k))<1e-12,
                 "zone κ target field mean consistency")
            stop(int(item["tet10"])>0 and
                 float(item["median_curved27qp_volume_m3"])>0 and
                 float(item["mean_curved27qp_volume_m3"])>0,
                 "positive local curved volumes")
    stop(abs(mean_kappa["M1"]-label["mean_kappa_at_linear_centroid"])<1e-14,
         "independent 9-zone M1 coefficient mean equals raw label summary")
    discrepancies=[]
    seen=set()
    for item in compare:
        key=(item["radial_zone"],item["polar_zone"])
        stop(key not in seen and key[0] in RADIAL and key[1] in POLAR,
             "comparison zone identity")
        seen.add(key)
        a,b=indexed[("M1",*key)],indexed[("M2",*key)]
        target=float(item["model_mean_target_volume_ratio_at_m1_centroids"])
        actual=float(item["observed_unpaired_median_curved27qp_volume_ratio_m2_over_m1"])
        corner=float(item["observed_unpaired_median_corner_volume_ratio_m2_over_m1"])
        stop(item["comparison_is_unpaired_diagnostic"]=="True" and
             int(item["m1_tet10"])==int(a["tet10"]) and
             int(item["m2_tet10"])==int(b["tet10"]) and
             abs(target-float(a["mean_target_volume_ratio"]))<1e-12 and
             abs(float(item["m1_mean_kappa_centroid"])-float(a["kappa_centroid_mean"]))<1e-12 and
             abs(float(item["m2_mean_kappa_centroid"])-float(b["kappa_centroid_mean"]))<1e-12 and
             abs(actual-float(b["median_curved27qp_volume_m3"])/
                 float(a["median_curved27qp_volume_m3"]))<1e-12 and
             abs(corner-float(b["median_corner_volume_m3"])/
                 float(a["median_corner_volume_m3"]))<1e-12,
             "independent unpaired volume-ratio CSV recalculation")
        discrepancies.append({
            "radial_zone":key[0],"polar_zone":key[1],
            "m1_tet10":int(a["tet10"]),"m2_tet10":int(b["tet10"]),
            "target_mean_volume_ratio":target,
            "observed_unpaired_curved27qp_median_ratio":actual,
            "observed_minus_target":actual-target,
            "observed_unpaired_corner_median_ratio":corner,
            "is_unpaired_diagnostic":True,
        })
    stop(len(seen)==9,"exactly 9 paired spatial bins")
    hotspot=next(x for x in discrepancies if
                 x["radial_zone"]=="0_100um" and
                 x["polar_zone"]=="polar_abs_mu_ge_0p8")
    stop(hotspot["m1_tet10"]==21 and hotspot["m2_tet10"]==22 and
         abs(hotspot["target_mean_volume_ratio"]-.8)<1e-14 and
         hotspot["observed_unpaired_curved27qp_median_ratio"]>1.,
         "physically important near-polar local target-vs-observed discrepancy")
    start=datetime.fromisoformat(m["started_utc"])
    end=datetime.fromisoformat(m["finished_utc"])
    stop(start.tzinfo and end.tzinfo and 0<(end-start).total_seconds()<900+300+1200,
         "whole wrapper duration")
    return {
        "protocol":"P10EC_INDEPENDENT_ORIGINAL_WINDOWS_P10EA_R1_NATIVE_M2_AUDIT",
        "status":"P10EC_NATIVE_GMSH3D_GEOMETRY_QA_PASS_ADAPTIVE_TARGET_NOT_ESTABLISHED_NO_FEM",
        "original_zip_sha256":ZIP_SHA,"source_release_sha256":RELEASE_SHA,
        "evidence_crc_members":14,"original_m1_sha256_manifest_only":M1_SHA,
        "m2_mesh_sha256_manifest_only":M2_SHA,
        "gmsh_executable_sha256_manifest_only":GMSH_SHA,
        "exact_f6_geo_sha256_independently_rehashed":F6_SHA,
        "original_m2_mesh_binary_present_in_zip":False,
        "native_gmsh_log_sha256":digest(files[FULL]),
        "native_parse_walls_seconds":parse_wall,
        "native_gmsh_one_3d_attempt":1,
        "native_exit_code":0,
        "native_polled_wall_seconds":native["polled_wall_s"],
        "native_polled_peak_private_bytes":native["polled_peak_private_bytes"],
        "native_log":stage,
        "m2_mesh_bytes_manifest_only":m["m2_mesh_bytes"],
        "qa_exit_code":quality["exit_code"],
        "qa_polled_wall_seconds":quality["polled_wall_s"],
        "qa_polled_peak_private_bytes":quality["polled_peak_private_bytes"],
        "m1_tet10":9736,"m2_tet10":9750,
        "m1_nodes":14145,"m2_nodes":14157,
        "m1_pore_tri6":178,"m2_pore_tri6":170,
        "m2_all_curved_qp_reported":263250,
        "m2_nonpositive_curved_qp_reported":0,
        "m2_geometry_issues_reported":[],
        "m2_geometry_verified_independently_from_raw_mesh":False,
        "per_mesh_9zone_integrated_curved_volume_m3":volumes,
        "exact_CAD_volume_m3":CAD_VOLUME,
        "per_mesh_9zone_mean_centroid_kappa":mean_kappa,
        "global_mean_curved_volume_ratio_by_tet10_count":9736/9750,
        "nine_zones":discrepancies,
        "hotspot_0_100um_abs_mu_ge_0p8":hotspot,
        "zones_with_observed_ratio_gt_1":sum(
            x["observed_unpaired_curved27qp_median_ratio"]>1. for x in discrepancies),
        "kappa_target_C1_0_to_1_source_only":True,
        "realized_per_element_20_percent_reduction_proved":False,
        "physical_FEM_attempts":0,
        "p10ea_one_shot_consumed_by_native_launch_source_control_flow":True,
        "p10ea_marker_files_physically_inspected":False,
    }


def selftest(files: dict[str,bytes],source: dict[str,bytes]) -> dict:
    good=audit(files,source)
    cases=[
        ("tamper exact F6",lambda f:f.__setitem__(
            "GEO/B_EXACT_INLINE_F6.geo",f["GEO/B_EXACT_INLINE_F6.geo"]+b"\n")),
        ("remove 3D completion",lambda f:f.__setitem__(
            FULL,f[FULL].replace(b"Done meshing 3D",b"STOP meshing 3D"))),
        ("wrong native -3 CLI",lambda f:f.__setitem__(
            FULL,f[FULL].replace(b" -3 -nt 2",b" -1 -nt 2"))),
        ("m2 SHA mismatch",lambda f:f["P10EA_RUN_MANIFEST.json"].update(
            {"m2_mesh_sha256":"0"*64})),
        ("wrong one-shot count",lambda f:f["P10EA_RUN_MANIFEST.json"].update(
            {"native_3d_attempts":2})),
        ("fake FEM",lambda f:f["P10EA_RUN_MANIFEST.json"].update(
            {"physical_FEM_attempts":1})),
        ("curved negative QP",lambda f:f[GEOMETRY].update(
            {"m2_curved_qp_nonpositive":1})),
        ("QA wrong M2 SHA",lambda f:f[GEOMETRY].update(
            {"m2_sha256":"f"*64})),
        ("CSV volume mutation",lambda f:f.__setitem__(
            COMPARE,f[COMPARE].replace(
                b"1.009535027219417",b"0.900535027219417"))),
        ("full log/tail inconsistent",lambda f:f.__setitem__(
            TAIL,f[TAIL]+b"damaged")),
    ]
    stopped=[]
    for name,mutate in cases:
        cloned={key:(json.loads(value) if key.endswith(".json") else value)
                for key,value in files.items()}
        mutate(cloned)
        trial={key:(json.dumps(v).encode("utf-8") if key.endswith(".json") else v)
               for key,v in cloned.items()}
        try:
            audit(trial,source)
        except (ValueError,TypeError,KeyError,IndexError,ZeroDivisionError):
            stopped.append(name)
        else:
            raise AssertionError("negative mutation accepted: "+name)
    stop(len(stopped)==len(cases),"all source/log/CSV negative mutations STOP")
    good["negative_mutations_stopped"]=stopped
    good["negative_count"]=len(stopped)
    return good


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--write-derived",action="store_true")
    args=p.parse_args()
    stop(digest(EVIDENCE.read_bytes())==ZIP_SHA,"original user ZIP SHA")
    stop(digest(RELEASE.read_bytes())==RELEASE_SHA,"released P10EA source ZIP SHA")
    files,source=archive(EVIDENCE),archive(RELEASE)
    stop(len(source)==24,"24 original pinned source members")
    checked=selftest(files,source)
    if args.write_derived:
        DERIVED.parent.mkdir(parents=True,exist_ok=True)
        DERIVED.write_text(json.dumps(checked,indent=2,ensure_ascii=False)+"\n",
                           encoding="utf-8")
    print("P10EC_REAL_P10EA_M2_NATIVE_3D_AUDIT_PASS",
          "CRC14/14 GEO3/3 native_3d=1 curved27QP=263250",
          "CSV_9z=9 negative10/10 M2_ADAPTIVE_TARGET=REVIEW FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
