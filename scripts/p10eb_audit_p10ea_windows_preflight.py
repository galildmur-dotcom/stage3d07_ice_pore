#!/usr/bin/env python3
"""Independent exact-primary P10EA Windows safe-source/GEO preflight audit.

Original bytes are never edited. Deliberate negative test mutations are
in-memory only. This program NEVER runs Gmsh, builds a mesh, or invokes FEM.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import argparse
import io
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
EVIDENCE = ROOT/"research/evidence/P10EB_P10EA_REAL_SAFE_PREFLIGHT_PASS_20261122/input/P10EA_EVIDENCE.zip"
RELEASE = ROOT/"research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip"
DERIVED = ROOT/"research/evidence/P10EB_P10EA_REAL_SAFE_PREFLIGHT_PASS_20261122/derived/P10EB_P10EA_ORIGINAL_PREFLIGHT_AUDIT.json"
ORIGINAL_ZIP_SHA = "36d90b7c583614317c770f66d51c8729c57a4eb5f059fefdbac37b838e5d5ee3"
RELEASE_SHA = "8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
REV = "P10EA_R1_EXACT_INLINE_F6_ONE_M2_3D_MESH_ONLY"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
F6_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
BASE_SHA = "c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
NAMES = {
    "P10EA_RUN_MANIFEST.json", "P10EA_RESULT.txt",
    "A_ORIGINAL_M1_FIELD2_PARSE.log", "B_EXACT_INLINE_F6_PARSE.log",
    "GEO/A_ORIGINAL_M1_FIELD2.geo", "GEO/B_EXACT_INLINE_F6.geo",
    "GEO/sphere_pore_B6_refined.geo", "P10EA_M1_LABEL_SUMMARY.json",
}
PARSES = ("A_ORIGINAL_M1_FIELD2", "B_EXACT_INLINE_F6")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("P10EB_AUDIT_STOP: "+message)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def load_zip(path: Path, required_names: set[str] | None = None) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, "ZIP CRC failure")
        names = z.namelist()
        require(len(names) == len(set(names)), "duplicate ZIP member")
        if required_names is not None:
            require(set(names) == required_names, "missing/extra evidence file")
        return {name:z.read(name) for name in names}


def decode(data: bytes) -> str:
    # Windows Gmsh native log contains CR-separated progress output and CRLF.
    return data.decode("utf-8", errors="strict")


def require_native_parse(log: str, name: str) -> float:
    lines = log.splitlines()
    require(bool(lines) and "Running " in lines[0] and
            "-parse_and_exit" in lines[0] and
            "[Gmsh 4.15.2" in lines[0], name+" native parse CLI/version")
    require(" -1 " not in lines[0] and " -2 " not in lines[0] and
            " -3 " not in lines[0] and "-o " not in lines[0],
            name+" contains mesh or output command")
    require("GEO\\"+name+".geo" in lines[0] and
            sum("Running " in line for line in lines)==1,
            name+" unexpected Gmsh source/attempt count")
    require(any("Reading " in line and "sphere_pore_B6_refined.geo" in line
                for line in lines) and
            any("Done reading " in line and "sphere_pore_B6_refined.geo" in line
                for line in lines) and
            any("Done reading " in line and ("GEO\\"+name+".geo") in line
                for line in lines),name+" CAD GEO parse did not complete")
    require(not any(re.search(r"^\s*(Error|Fatal)\s*:",line) for line in lines),
            name+" Gmsh error")
    stops = [line for line in lines if "Stopped on " in line]
    require(len(stops)==1,name+" no unique native stop line")
    match = re.search(r"From start:\s*Wall\s*([0-9.]+)s",stops[0])
    require(match is not None,name+" native wall not reported")
    wall = float(match.group(1))
    require(0 <= wall <= 20,name+" parse wall limit")
    require(not any("Meshing curve" in line or "Done meshing 3D" in line
                    for line in lines),name+" unexpected mesh operation")
    return wall


def audit(files: dict[str,bytes], source: dict[str,bytes]) -> dict:
    require(set(files) == NAMES,"exact eight original evidence members")
    manifest = json.loads(decode(files["P10EA_RUN_MANIFEST.json"]))
    label = json.loads(decode(files["P10EA_M1_LABEL_SUMMARY.json"]))
    result = decode(files["P10EA_RESULT.txt"])
    require(manifest.get("revision") == REV and
            manifest.get("status") == "P10EA_SAFE_PREFLIGHT_PASS_NO_M2_NO_FEM" and
            manifest.get("mode") == "SOURCE_ONLY_PREFLIGHT" and
            result.startswith("RESULT=P10EA_SAFE_PREFLIGHT_PASS_NO_M2_NO_FEM\r\n"),
            "source-only PASS status/revision/mode")
    require(manifest.get("native_parse_attempts")==2 and
            manifest.get("native_parse_passed")==list(PARSES) and
            manifest.get("native_1d_2d_attempts")==0 and
            manifest.get("native_3d_attempts")==0 and
            manifest.get("physical_FEM_attempts")==0 and
            "NATIVE_M2_3D_ATTEMPTS=0" in result and
            "FEM=0" in result and "M2_SHA256=UNKNOWN" in result and
            "STOP_REASON=\r\n" in result,
            "physical/mesh attempt counters or STOP_reason")
    require(manifest.get("source_sha_pins")==23 and
            manifest.get("math_points")==17075 and
            manifest.get("kappa_C1_range")==[0.,1.] and
            manifest.get("target_local_volume_ratio") ==
              "1-0.20*kappa; not guaranteed per realized Tet10",
            "source/math/target provenance")
    require(manifest.get("original_m1_sha256")==M1_SHA and
            manifest.get("m1_sha256")==M1_SHA and
            manifest.get("f6_sha256")==F6_SHA and
            manifest.get("gmsh_sha256")==GMSH_SHA and
            manifest.get("gmsh_path")==r"C:\gmsh-4.15.2-Windows64\gmsh.exe" and
            manifest.get("m1_path","").endswith(r"\P10DG_M1_CANDIDATE.msh") and
            "M1_SHA256="+M1_SHA in result,
            "exact original M1/Gmsh identity by Windows wrapper")
    require(manifest.get("free_ram_bytes",0)>=16*1024**3 and
            manifest.get("free_disk_bytes",0)>=4*1024**3 and
            manifest.get("wall_limit_s")==900 and
            manifest.get("qa_limit_s")==300 and
            manifest.get("private_limit_bytes")==8*1024**3 and
            manifest.get("mesh_limit_bytes")==750*1024**2 and
            manifest.get("log_limit_bytes")==16*1024**2,
            "preflight/resource safety contract")
    original = source["P10DN_M2_FIELD20.geo"].decode("utf-8")
    expected_base = original.split("// F3:",1)[0]+"\nBackground Field=2;\n"
    require(files["GEO/A_ORIGINAL_M1_FIELD2.geo"] == expected_base.encode("utf-8") and
            files["GEO/B_EXACT_INLINE_F6.geo"] == source["P10DV_M2_INLINE_FIELD20.geo"] and
            files["GEO/sphere_pore_B6_refined.geo"] ==
              source["sphere_pore_B6_refined.geo"],
            "generated GEO bytes differ from source release")
    hashes = {"A_ORIGINAL_M1_FIELD2":BASE_SHA,
              "B_EXACT_INLINE_F6":F6_SHA}
    for key,expected in hashes.items():
        require(manifest.get("generated_geo_sha256",{}).get(key)==expected and
                digest(files["GEO/"+key+".geo"])==expected,
                "generated GEO manifest/binary SHA: "+key)
    require(digest(files["GEO/sphere_pore_B6_refined.geo"])==CAD_SHA,
            "original exact CAD")
    walls = {key: require_native_parse(decode(files[key+"_PARSE.log"]),key)
             for key in PARSES}
    started = datetime.fromisoformat(manifest["started_utc"])
    finished = datetime.fromisoformat(manifest["finished_utc"])
    duration = (finished-started).total_seconds()
    require(started.tzinfo and finished.tzinfo and 0 <= duration <= 120,
            "preflight UTC interval and wall reasonable")
    require("P10EA_20261122_042904_271811" in manifest.get("m1_label_dir","") and
            "P10DN_M1_COEFF_ONLY_" in manifest.get("m1_label_dir",""),
            "M1 label run provenance")
    counts = label.get("label_counts",{})
    require(label.get("protocol")=="P10DN_M1_CONTINUOUS_KAPPA20_SOURCE_ONLY" and
            label.get("m1_sha256")==M1_SHA and label.get("nodes")==14145 and
            label.get("tet10")==9736 and label.get("pore_tri6")==178 and
            counts=={"zero":9477,"one":21,"intermediate":238} and
            sum(counts.values())==label["tet10"],
            "complete exact original M1 Tet10 coefficient labeling")
    require(0<=label.get("mean_kappa_at_linear_centroid",-1)<=1 and
            label.get("target_relative_volume_min")==.8 and
            label.get("target_relative_volume_max")==1 and
            abs(label.get("target_relative_size_min")-.8**(1./3.))<1e-14,
            "κ or 0–20% theoretical target envelope")
    return {
        "protocol":"P10EB_INDEPENDENT_P10EA_R1_WINDOWS_PREFLIGHT_ORIGINAL_AUDIT",
        "status":"P10EB_ORIGINAL_P10EA_NATIVE_GEO_PARSE2_AND_M1_LABEL_PASS_NO_M2_NO_FEM",
        "original_evidence_sha256":ORIGINAL_ZIP_SHA,
        "source_release_sha256":RELEASE_SHA,
        "original_evidence_zip_members":len(files),
        "source_package_zip_members":len(source),
        "original_m1_sha256_windows_manifest_only":M1_SHA,
        "native_gmsh_exe_sha256_windows_manifest_only":GMSH_SHA,
        "f6_geo_sha256_independently_rehashed":F6_SHA,
        "baseline_geo_sha256_independently_rehashed":BASE_SHA,
        "cad_geo_sha256_independently_rehashed":CAD_SHA,
        "source_pin_count_reported":23,
        "math_points_reported":17075,
        "native_parse_attempts":2,"native_parse_walls_seconds":walls,
        "windows_preflight_wall_seconds_from_manifest":duration,
        "free_ram_bytes_reported":manifest["free_ram_bytes"],
        "free_disk_bytes_reported":manifest["free_disk_bytes"],
        "original_m1_tet10_labelled":9736,
        "label_counts":counts,
        "label_kappa_mean_centroid":label["mean_kappa_at_linear_centroid"],
        "target_local_volume_ratio":[.8,1.],
        "native_1d_2d_3d_attempts":0,
        "physical_FEM_attempts":0,
        "raw_original_m1_binary_sha_independently_checked":False,
        "raw_gmsh_exe_binary_sha_independently_checked":False,
        "m2_mesh_created":False,
        "m2_curved27qp_QA":False,
        "m2_realized_9zone_volumes":False,
        "p10ea_02_marker_consumption_in_this_preflight":False,
        "current_windows_markers_directly_inspected":False,
    }


def selftest(files: dict[str,bytes], source: dict[str,bytes]) -> dict:
    good = audit(files,source)
    tests = (
        ("tamper F6 GEO",lambda f: f.__setitem__(
            "GEO/B_EXACT_INLINE_F6.geo",f["GEO/B_EXACT_INLINE_F6.geo"]+b"\n")),
        ("tamper baseline",lambda f: f.__setitem__(
            "GEO/A_ORIGINAL_M1_FIELD2.geo",f["GEO/A_ORIGINAL_M1_FIELD2.geo"]+b"\n")),
        ("wrong M1 SHA",lambda f: f["P10EA_RUN_MANIFEST.json"].update(
            {"m1_sha256":"0"*64})),
        ("fake native 3D",lambda f: f["P10EA_RUN_MANIFEST.json"].update(
            {"native_3d_attempts":1})),
        ("fake parse success",lambda f: f["P10EA_RUN_MANIFEST.json"].update(
            {"native_parse_passed":["A_ORIGINAL_M1_FIELD2"]})),
        ("native parse CLI changed to -3",lambda f: f.__setitem__(
            "B_EXACT_INLINE_F6_PARSE.log",f["B_EXACT_INLINE_F6_PARSE.log"].replace(
                "-parse_and_exit","-3"))),
        ("native parse missing completion",lambda f: f.__setitem__(
            "B_EXACT_INLINE_F6_PARSE.log",f["B_EXACT_INLINE_F6_PARSE.log"].replace(
                "Done reading","NOT FINISHED"))),
        ("bad Tet10 label count",lambda f: f["P10EA_M1_LABEL_SUMMARY.json"][
            "label_counts"].update({"one":22})),
    )
    # We mutate decoded JSON in memory, then re-serialize; never touch the ZIP.
    def transformed(name, mutate):
        original = {key:(json.loads(value) if key.endswith(".json") else
                         decode(value) if key.endswith(".log") else value)
                    for key,value in files.items()}
        mutate(original)
        return {key:(json.dumps(value).encode("utf-8") if key.endswith(".json") else
                     value.encode("utf-8") if key.endswith(".log") else value)
                for key,value in original.items()}
    stopped = []
    for name,mutate in tests:
        bad=transformed(name,mutate)
        try:
            audit(bad,source)
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            stopped.append(name)
        else:
            raise AssertionError("negative mutation accepted: "+name)
    require(len(stopped)==8,"8/8 independent mutation STOP")
    good["negative_mutations_stopped"]=stopped
    good["negative_stopped_count"]=len(stopped)
    return good


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--write-derived",action="store_true")
    args=parser.parse_args()
    require(digest(EVIDENCE.read_bytes())==ORIGINAL_ZIP_SHA,
            "user original ZIP SHA changed")
    require(digest(RELEASE.read_bytes())==RELEASE_SHA,
            "released exact P10EA R1 package changed")
    files=load_zip(EVIDENCE,NAMES)
    source=load_zip(RELEASE)
    require(len(source)==24,"original P10EA R1 source archive inventory")
    checked=selftest(files,source)
    if args.write_derived:
        DERIVED.parent.mkdir(parents=True,exist_ok=True)
        DERIVED.write_text(json.dumps(checked,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("P10EB_ORIGINAL_P10EA_SAFE_PREFLIGHT_AUDIT_PASS",
          "ZIP8/8", "GEO3/3", "native_parse2/2",
          "M1_tet10=9736", "negative8/8", "M2_3D=0", "FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
