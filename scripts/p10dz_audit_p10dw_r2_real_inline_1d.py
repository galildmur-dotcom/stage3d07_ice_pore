#!/usr/bin/env python3
"""Independent original Windows P10DW R2 1D native MathEval smoke audit."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path, PureWindowsPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/"research/evidence/P10DZ_P10DW_R2_REAL_INLINE_F6_1D_PASS_20261122"
INPUT = EVIDENCE/"input/P10DW_EVIDENCE_1D.zip"
OUTPUT = EVIDENCE/"derived/P10DZ_P10DW_R2_ORIGINAL_1D_AUDIT.json"
EXPECTED_ZIP = "f151b03fe9e52bcee05480ec7ac177ad0efbaf566fa79577080390eff8d4b7d6"
R2_ZIP_SHA = "1418d8ccf8374b275b7112137e23e6a5a94e65e549a50b44cbd66b4f6105d04f"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
GEO_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
BASE_SHA = "c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8"
REPORTED_MSH_SHA = "04325caf637624c98cc5e18415556c937635e3102d1bb2ad79dbd72e2fd42511"
VARIANTS = ("A_ORIGINAL_M1_FIELD2", "B_EXACT_INLINE_F6")
MEMBERS = {"P10DW_RUN_MANIFEST.json", "P10DW_RESULT.txt",
           "B_EXACT_INLINE_F6_TAIL.txt", "GEO/A_ORIGINAL_M1_FIELD2.geo",
           "GEO/B_EXACT_INLINE_F6.geo", "GEO/sphere_pore_B6_refined.geo",
           "A_ORIGINAL_M1_FIELD2_PARSE.log", "B_EXACT_INLINE_F6_PARSE.log",
           "B_EXACT_INLINE_F6.log"}


def digest(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise RuntimeError("P10DZ_AUDIT_STOP: " + msg)


def eols(text: str) -> str:
    """Only normalize Windows text export CRCRLF and CRLF; retain bare CR progress."""
    return re.sub(r"\r+\n", "\n", text)


def analyze(members: dict[str, bytes]) -> dict:
    require(set(members) == MEMBERS, "original evidence inventory")
    meta = json.loads(members["P10DW_RUN_MANIFEST.json"].decode("utf-8-sig"))
    result = eols(members["P10DW_RESULT.txt"].decode("utf-8-sig"))
    require(meta.get("protocol") == "P10DW_R2_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM" and
            meta.get("mode") == "ONE_1D_INLINE_F6" and
            meta.get("status") == "P10DW_ONE_1D_PASS_NO_FEM" and
            meta.get("target_local_volume_ratio") == "1-0.20*kappa" and
            not meta.get("stop_reason"), "R2 native one-1D result identity")
    require(result == ("RESULT=P10DW_ONE_1D_PASS_NO_FEM\n"
                       "NATIVE_1D_ATTEMPTS=1\nM2_3D_MESH=0\nFEM=0\nSTOP_REASON=\n"),
            "RESULT/result manifest consistency")
    require(meta.get("native_parse_attempts") == 2 and
            meta.get("native_parse_passed") == list(VARIANTS) and
            meta.get("native_1d_attempts") == 1 and
            meta.get("native_2d_3d_attempts") == 0 and
            meta.get("physical_FEM_attempts") == 0 and
            meta.get("source_sha_pins") == 12 and meta.get("math_points") == 17075,
            "source/maths and exact native count")
    require(meta.get("m1_sha256") == M1_SHA and
            meta.get("accepted_original_m1_sha256") == M1_SHA and
            PureWindowsPath(meta.get("m1_path", "")).name.casefold() ==
            "p10dg_m1_candidate.msh" and
            meta.get("gmsh_sha256") == GMSH_SHA and
            meta.get("gmsh_version") == "4.15.2" and
            meta.get("free_ram_bytes", 0) >= 8*1024**3 and
            meta.get("free_disk_bytes", 0) >= 1024**3 and
            meta.get("wall_limit_1d_s") == 15 and
            meta.get("private_limit_bytes") == 2*1024**3 and
            meta.get("msh_limit_bytes") == 20*1024**2 and
            meta.get("log_limit_bytes") == 1024**2,
            "M1/Gmsh SHA/Windows guard and limits")
    elapsed = (datetime.fromisoformat(meta["finished_utc"])-
               datetime.fromisoformat(meta["started_utc"])).total_seconds()
    require(0. < elapsed < 120., "full wrapper wall preflight+1D")

    original = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
                /"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    baseline = (original.split("// F3:", 1)[0]+"\nBackground Field=2;\n").encode("utf-8")
    exact = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
             /"P10DV_M2_INLINE_FIELD20.geo").read_bytes()
    cad = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
           /"sphere_pore_B6_refined.geo").read_bytes()
    require(digest(baseline) == BASE_SHA and digest(exact) == GEO_SHA and
            digest(cad) == CAD_SHA and
            members["GEO/A_ORIGINAL_M1_FIELD2.geo"] == baseline and
            members["GEO/B_EXACT_INLINE_F6.geo"] == exact and
            members["GEO/sphere_pore_B6_refined.geo"] == cad and
            meta.get("geo_sha256") == {VARIANTS[0]: BASE_SHA, VARIANTS[1]: GEO_SHA},
            "exact baseline / inline F6 / CAD primary source byte identity")

    runids = set()
    parse_walls = {}
    for name in VARIANTS:
        log = eols(members[name+"_PARSE.log"].decode("utf-8", errors="replace"))
        cmds = re.findall(r"(?m)^Info\s+: Running '([^']+)' \[Gmsh 4\.15\.2,", log)
        require(len(cmds) == 1 and cmds[0].endswith(name+".geo -parse_and_exit") and
                str(meta["gmsh_path"]).lower() in cmds[0].lower() and
                "Done reading '" in log and
                "sphere_pore_B6_refined.geo'" in log and
                "Info    : Stopped on" in log and
                not re.search(r"(?im)^\s*Error\s*:", log),
                "native safe parse command/log "+name)
        hits = re.findall(r"From start: Wall ([0-9.]+)s", log)
        require(len(hits) == 1 and 0. < float(hits[0]) <= 20.,
                "native parse <=20s")
        parse_walls[name] = float(hits[0])
        run = re.search(r"P10DW_\d{8}_\d{6}_\d{6}", cmds[0])
        require(run is not None, "parse log run_id")
        runids.add(run.group())

    native = meta.get("native_1d_result")
    require(isinstance(native, dict) and native.get("status") == "PASS_1D_ONLY" and
            native.get("exit_code") == 0 and
            native.get("reported_nodes_elements_from_log") == [244, 135] and
            native.get("msh_bytes") == 280 and
            native.get("msh_sha256") == REPORTED_MSH_SHA and
            native.get("log_bytes") == len(members["B_EXACT_INLINE_F6.log"]) and
            native.get("peak_private_polled", 2**32) <= 2*1024**3 and
            0 < native.get("wall_s", -1) <= 15,
            "native Gmsh exit/1D bounds/log counts")
    argv = native.get("argv")
    require(isinstance(argv, list) and len(argv) == 9 and
            argv[0] == meta["gmsh_path"] and argv[2:] ==
            ["-1", "-nt", "2", "-format", "msh2", "-o", argv[8]] and
            PureWindowsPath(argv[1]).name == "B_EXACT_INLINE_F6.geo" and
            PureWindowsPath(argv[8]).name == "B_EXACT_INLINE_F6.msh",
            "exact one Gmsh -1 CLI with no -2/-3")

    log_original = members["B_EXACT_INLINE_F6.log"].decode("utf-8", errors="replace")
    log = eols(log_original)
    tail = eols(members["B_EXACT_INLINE_F6_TAIL.txt"].decode("utf-8", errors="replace"))
    require(log == tail and len(log) > 1000 and
            native["log_bytes"] < 1024**2 and
            not re.search(r"(?im)^\s*Error\s*:", log),
            "full native Gmsh log vs Windows newline-normalized TAIL")
    cmds = re.findall(r"(?m)^Info\s+: Running '([^']+)' \[Gmsh 4\.15\.2,", log)
    require(len(cmds) == 1 and " -1 -nt 2 -format msh2 -o " in cmds[0] and
            cmds[0].startswith(meta["gmsh_path"]+" ") and
            cmds[0].endswith(argv[8]) and
            " -2 " not in cmds[0] and " -3 " not in cmds[0],
            "actual single Gmsh -1 native CLI")
    run = re.search(r"P10DW_\d{8}_\d{6}_\d{6}", cmds[0])
    require(run is not None, "1D native run_id")
    runids.add(run.group())
    require(len(runids) == 1 and
            all(term in log for term in (
                "Meshing 1D...", "Meshing curve 14 (Circle)",
                "Meshing curve 17 (Circle)", "Done meshing 1D",
                "Meshing order 2 (curvilinear on)", "Done meshing order 2",
                "Optimization succeeded", "244 nodes 135 elements",
                "Done writing '", "Info    : Stopped on")),
            "exact inline MathEval 1D completed past previously stuck curves")
    wall = re.findall(r"From start: Wall ([0-9.]+)s", log)
    curvewall = re.findall(r"Done meshing 1D \(Wall ([0-9.]+)s", log)
    require(len(wall) == len(curvewall) == 1 and
            0. < float(wall[0]) <= 15 and 0. < float(curvewall[0]) <= float(wall[0]),
            "native Gmsh 1D execution time")
    # The tiny MSH2 file is NOT inside original evidence. Topology is UNVERIFIED.
    return {"original_evidence_zip_sha256": EXPECTED_ZIP,
            "original_zip_members_crc": 9,
            "source_r2_zip_sha256": R2_ZIP_SHA,
            "status": "P10DW_ONE_1D_PASS_NO_FEM",
            "original_accepted_m1_windows_reported_sha256": M1_SHA,
            "original_m1_raw_msh_locally_available": False,
            "native_gmsh_exe_windows_reported_sha256": GMSH_SHA,
            "native_gmsh_exe_locally_available": False,
            "source_pins": 12, "math_points": 17075,
            "inline_f6_geo_sha256": GEO_SHA,
            "original_field2_baseline_geo_sha256": BASE_SHA,
            "cad_geo_sha256": CAD_SHA,
            "native_parse_runs": 2, "native_parse_wall_s": parse_walls,
            "native_1d_runs": 1, "native_1d_result": native,
            "native_gmsh_total_wall_from_log_s": float(wall[0]),
            "native_gmsh_curve_1d_wall_from_log_s": float(curvewall[0]),
            "wrapper_total_wall_s": elapsed,
            "full_1d_log_sha256": digest(members["B_EXACT_INLINE_F6.log"]),
            "full_log_tail_equivalent_after_only_windows_eol_normalization": True,
            "native_log_run_ids": sorted(runids),
            "native_2d_3d_runs": 0, "physical_FEM_runs": 0,
            "reported_nodes_elements_log_only": [244, 135],
            "msh_file_bytes_windows_manifest_only": 280,
            "msh_file_sha256_windows_manifest_only": REPORTED_MSH_SHA,
            "msh_file_not_present_in_original_zip": True,
            "native_1d_topology_independently_verified": False,
            "one_shot_consumed_by_r2_code_before_native_launch": True,
            "one_shot_marker_directly_inspected_on_windows": False,
            "full_3d_m2_mesh_and_curved27qp_verified": False}


def main() -> int:
    require(digest(INPUT.read_bytes()) == EXPECTED_ZIP, "exact original ZIP SHA")
    release = ROOT/"research/packages/P10DW_R2_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261122.zip"
    require(digest(release.read_bytes()) == R2_ZIP_SHA, "exact R2 source ZIP")
    with zipfile.ZipFile(INPUT) as z:
        require(z.testzip() is None and len(z.namelist()) == len(MEMBERS), "ZIP CRC9/9")
        require(len(set(z.namelist())) == len(MEMBERS), "ZIP duplicated members")
        members = {n: z.read(n) for n in z.namelist()}
    results = analyze(members)
    mutants: list[tuple[str, dict[str, bytes]]] = []
    def mutated(name: str, old: bytes, new: bytes, label: str) -> None:
        data = dict(members)
        require(old in data[name], "mutation baseline not present "+label)
        data[name] = data[name].replace(old, new, 1)
        mutants.append((label, data))
    mutated("GEO/B_EXACT_INLINE_F6.geo", b"0.2*", b"0.3*", "formula_tamper")
    mutated("B_EXACT_INLINE_F6.log", b"Done meshing 1D", b"Meshing stopped 1D", "missing_done")
    mutated("B_EXACT_INLINE_F6.log", b" -1 -nt 2 ", b" -3 -nt 2 ", "wrong_native_mode")
    mutated("B_EXACT_INLINE_F6.log", b"Optimization succeeded",
            b"Error : invalid field", "native_error")
    mutated("B_EXACT_INLINE_F6_TAIL.txt", b"244 nodes 135 elements",
            b"244 nodes 134 elements", "log_tail_mismatch")
    meta = json.loads(members["P10DW_RUN_MANIFEST.json"])
    for label, key, val in (("wrong_one_shot_count", "native_1d_attempts", 2),
                            ("invalid_native_exit", "exit_code", 1),
                            ("over_wall", "wall_s", 100.)):
        fake = dict(members)
        copy = json.loads(members["P10DW_RUN_MANIFEST.json"])
        if key in copy:
            copy[key] = val
        else:
            copy["native_1d_result"][key] = val
        fake["P10DW_RUN_MANIFEST.json"] = json.dumps(copy).encode("utf-8")
        mutants.append((label, fake))
    for label, test in mutants:
        require(test != members, "empty negative test "+label)
        try:
            analyze(test)
        except RuntimeError as exc:
            require(str(exc).startswith("P10DZ_AUDIT_STOP"), "unexpected exception")
        else:
            raise RuntimeError("mutation unexpectedly passed: "+label)
    results["independent_negative_mutations_passed"] = len(mutants)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("P10DZ_ORIGINAL_P10DW_R2_NATIVE_INLINE_F6_1D_AUDIT_PASS",
          "CRC9/9 GEO3/3 native_parse2 native_1d1 negative8/8",
          "3D_M2=0 FEM=0 MSH_TOPOLOGY=UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
