#!/usr/bin/env python3
"""Independent byte/log audit of original P10DW R2 Windows parse-only evidence."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path, PureWindowsPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"research/evidence/P10DY_P10DW_R2_REAL_GEO_PARSE_PASS_20261122"
INPUT = BASE/"input/P10DW_EVIDENCE_R2.zip"
OUTPUT = BASE/"derived/P10DY_P10DW_R2_NATIVE_GEO_PARSE_AUDIT.json"
ZIP_SHA = "bce04f56d4a1610f6b86c8acc1d8436d8f0d12aa66dfc63ff7701cad63472d36"
R2_SHA = "1418d8ccf8374b275b7112137e23e6a5a94e65e549a50b44cbd66b4f6105d04f"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
INLINE_SHA = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
BASE_SHA = "c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8"
CAD_SHA = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
FIELDS = ("A_ORIGINAL_M1_FIELD2", "B_EXACT_INLINE_F6")
MEMBERS = {"P10DW_RUN_MANIFEST.json", "P10DW_RESULT.txt",
           "GEO/A_ORIGINAL_M1_FIELD2.geo", "GEO/B_EXACT_INLINE_F6.geo",
           "GEO/sphere_pore_B6_refined.geo",
           "A_ORIGINAL_M1_FIELD2_PARSE.log", "B_EXACT_INLINE_F6_PARSE.log"}


def digest(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError("P10DY_AUDIT_STOP: " + message)


def analyze(members: dict[str, bytes]) -> dict:
    require(set(members) == MEMBERS, "ZIP member inventory")
    meta = json.loads(members["P10DW_RUN_MANIFEST.json"].decode("utf-8-sig"))
    result = members["P10DW_RESULT.txt"].decode("utf-8-sig").replace("\r\n", "\n")
    require(meta.get("protocol") == "P10DW_R2_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM" and
            meta.get("mode") == "SOURCE_GEO_PREFLIGHT" and
            meta.get("status") == "P10DW_READ_ONLY_PREFLIGHT_PASS" and
            meta.get("target_local_volume_ratio") == "1-0.20*kappa" and
            not meta.get("stop_reason"), "actual R2 preflight PASS status")
    require(result == ("RESULT=P10DW_READ_ONLY_PREFLIGHT_PASS\n"
                       "NATIVE_1D_ATTEMPTS=0\nM2_3D_MESH=0\nFEM=0\nSTOP_REASON=\n"),
            "original result text/pass binding")
    require(meta.get("native_parse_attempts") == 2 and
            meta.get("native_parse_passed") == list(FIELDS) and
            meta.get("native_1d_attempts") == 0 and
            meta.get("native_2d_3d_attempts") == 0 and
            meta.get("physical_FEM_attempts") == 0 and
            meta.get("source_sha_pins") == 12 and
            meta.get("math_points") == 17075,
            "native parser-only counters and math/source checks")
    require(meta.get("m1_sha256") == M1_SHA and
            meta.get("accepted_original_m1_sha256") == M1_SHA and
            PureWindowsPath(meta.get("m1_path", "")).name.lower() == "p10dg_m1_candidate.msh" and
            meta.get("gmsh_sha256") == GMSH_SHA and
            meta.get("gmsh_version") == "4.15.2" and
            meta.get("gmsh_path", "").lower().endswith(r"gmsh-4.15.2-windows64\gmsh.exe") and
            meta.get("free_ram_bytes", 0) >= 8*1024**3 and
            meta.get("free_disk_bytes", 0) >= 1024**3,
            "expected original accepted M1 and native Gmsh resources")
    require(meta.get("wall_limit_1d_s") == 15 and
            meta.get("private_limit_bytes") == 2*1024**3 and
            meta.get("msh_limit_bytes") == 20*1024**2 and
            meta.get("log_limit_bytes") == 1024**2,
            "future one-1D boundary not widened")
    elapsed = (datetime.fromisoformat(meta["finished_utc"])-
               datetime.fromisoformat(meta["started_utc"])).total_seconds()
    require(0. < elapsed <= 120., "overall preflight wall time")

    original = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
                /"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    base_source = (original.split("// F3:", 1)[0] + "\nBackground Field=2;\n").encode("utf-8")
    source_inline = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
                     /"P10DV_M2_INLINE_FIELD20.geo").read_bytes()
    source_cad = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
                  /"sphere_pore_B6_refined.geo").read_bytes()
    require(digest(source_inline) == INLINE_SHA and digest(source_cad) == CAD_SHA,
            "published P10DV source baseline itself changed")
    require(members["GEO/A_ORIGINAL_M1_FIELD2.geo"] == base_source and
            digest(base_source) == BASE_SHA and
            members["GEO/B_EXACT_INLINE_F6.geo"] == source_inline and
            members["GEO/sphere_pore_B6_refined.geo"] == source_cad,
            "R2 generated GEO/CAD must be byte-identical to pinned source")
    require(meta.get("geo_sha256") == {FIELDS[0]: BASE_SHA, FIELDS[1]: INLINE_SHA},
            "SHA of native parsed GEO in manifest")

    logs = {}
    run_ids = set()
    for name in FIELDS:
        log = members[name+"_PARSE.log"].decode("utf-8", errors="replace").replace("\r\n", "\n")
        require(len(log) > 500 and len(log) < 1024**2 and
                not re.search(r"(?im)^\s*Error\s*:", log) and
                not re.search(r"(?im)\b(Segmentation fault|aborted)\b", log),
                "native log has error / unexpected length "+name)
        runs = re.findall(r"(?m)^Info\s+: Running '([^']+)' \[Gmsh 4\.15\.2,", log)
        require(len(runs) == 1 and runs[0].endswith(name+".geo -parse_and_exit") and
                str(meta["gmsh_path"]).lower() in runs[0].lower() and
                " -1 " not in runs[0] and " -2 " not in runs[0] and " -3 " not in runs[0],
                "wrong native Gmsh invocation "+name)
        path_match = re.search(r"P10DW_\d{8}_\d{6}_\d{6}", runs[0])
        require(path_match is not None, "missing P10DW run_id from log")
        run_ids.add(path_match.group())
        require("Done reading '" in log and
                "sphere_pore_B6_refined.geo'" in log and
                (name+".geo'\n") in log and
                "Info    : Stopped on" in log,
                "native CAD read and clean parse exit evidence "+name)
        wall_matches = re.findall(r"From start: Wall ([0-9.]+)s", log)
        require(len(wall_matches) == 1 and 0. < float(wall_matches[0]) < 20.,
                "native parser wall 20s limit "+name)
        logs[name] = {"native_mode": "-parse_and_exit",
                      "reported_wall_s": float(wall_matches[0]),
                      "log_sha256": digest(members[name+"_PARSE.log"]),
                      "native_parse_result": "PASS_BY_LOG_AND_WRAPPER_EXIT_ZERO"}
    require(len(run_ids) == 1, "both GEO parse logs must belong to same run")

    # This does not independently inspect Windows markers or original .msh bytes.
    return {"original_evidence_zip_sha256": ZIP_SHA,
            "original_evidence_zip_members_crc": 7,
            "source_release_p10dw_r2_sha256": R2_SHA,
            "status": "P10DW_READ_ONLY_PREFLIGHT_PASS",
            "native_parse_attempts": 2, "native_parse_passed": list(FIELDS),
            "native_1d_attempts": 0, "native_2d_3d_attempts": 0,
            "physical_FEM_attempts": 0, "source_pin_count": 12,
            "math_points": 17075, "preflight_elapsed_s": elapsed,
            "accepted_original_m1_sha256_reported_windows": M1_SHA,
            "original_m1_bytes_independently_available": False,
            "gmsh_executable_sha256_reported_windows": GMSH_SHA,
            "gmsh_executable_bytes_independently_available": False,
            "r2_exact_generated_inline_geo_sha256": INLINE_SHA,
            "baseline_geo_sha256": BASE_SHA, "original_cad_sha256": CAD_SHA,
            "parse_logs": logs, "log_run_ids": sorted(run_ids),
            "one_shot_marker_consumed_by_published_preflight_source": False,
            "markers_directly_inspected_on_windows": False,
            "full_inline_math_eval_native_runtime_tested": False,
            "mesh3d_tet10_curved27qp_fem_tested": False}


def main() -> int:
    require(digest(INPUT.read_bytes()) == ZIP_SHA, "exact original R2 evidence ZIP SHA")
    pkg = ROOT/"research/packages/P10DW_R2_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261122.zip"
    require(digest(pkg.read_bytes()) == R2_SHA, "exact R2 release ZIP SHA")
    with zipfile.ZipFile(INPUT) as z:
        require(len(z.namelist()) == len(MEMBERS) and z.testzip() is None,
                "original ZIP CRC7/7")
        require(len(set(z.namelist())) == len(MEMBERS), "duplicate ZIP member")
        original = {n: z.read(n) for n in z.namelist()}
    results = analyze(original)
    mutations: list[tuple[str, dict[str, bytes]]] = []
    fake = dict(original)
    fake["GEO/B_EXACT_INLINE_F6.geo"] = fake["GEO/B_EXACT_INLINE_F6.geo"].replace(
        b"0.2*", b"0.3*", 1)
    mutations.append(("wrong_inline_formula", fake))
    fake = dict(original)
    fake["B_EXACT_INLINE_F6_PARSE.log"] = fake["B_EXACT_INLINE_F6_PARSE.log"].replace(
        b"-parse_and_exit", b"-1", 1)
    mutations.append(("native_1d_instead_of_parse", fake))
    fake = dict(original)
    meta = json.loads(fake["P10DW_RUN_MANIFEST.json"])
    meta["native_1d_attempts"] = 1
    fake["P10DW_RUN_MANIFEST.json"] = json.dumps(meta).encode("utf-8")
    mutations.append(("fake_1d", fake))
    fake = dict(original)
    meta = json.loads(fake["P10DW_RUN_MANIFEST.json"])
    meta["source_sha_pins"] = 11
    fake["P10DW_RUN_MANIFEST.json"] = json.dumps(meta).encode("utf-8")
    mutations.append(("broken_pin", fake))
    fake = dict(original)
    meta = json.loads(fake["P10DW_RUN_MANIFEST.json"])
    meta["m1_sha256"] = "0"*64
    fake["P10DW_RUN_MANIFEST.json"] = json.dumps(meta).encode("utf-8")
    mutations.append(("wrong_m1", fake))
    fake = dict(original)
    fake["GEO/sphere_pore_B6_refined.geo"] += b"\n//tamper"
    mutations.append(("altered_cad", fake))
    fake = dict(original)
    fake["B_EXACT_INLINE_F6_PARSE.log"] += b"\nError : injected Gmsh fatal\n"
    mutations.append(("native_error", fake))
    for name, fake in mutations:
        require(fake != original, "empty mutation "+name)
        try:
            analyze(fake)
        except RuntimeError as exc:
            require(str(exc).startswith("P10DY_AUDIT_STOP"), "wrong negative stop")
        else:
            raise RuntimeError("P10DY negative mutation unexpectedly passed: "+name)
    results["independent_negative_tamper_tests_passed"] = len(mutations)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("P10DY_ORIGINAL_P10DW_R2_NATIVE_GEO_PARSE_AUDIT_PASS",
          "CRC7/7 PIN12/12 GEO3/3 native_parse2/2 negative7/7",
          "native_1d=0 M2_3D=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
