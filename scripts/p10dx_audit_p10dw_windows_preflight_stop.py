#!/usr/bin/env python3
"""Independent exact-ZIP audit of the Windows P10DW R1 CRLF false STOP."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/"research/evidence/P10DX_P10DW_R1_WINDOWS_NEWLINE_STOP_20261122"
INPUT = FOLDER/"input/P10DW_EVIDENCE.zip"
OUTPUT = FOLDER/"derived/P10DX_P10DW_R1_STOP_AUDIT.json"
EXPECTED_ZIP = "d173de50c73167e3badbfe42c3fabb87b2ad345ac47f44623585a7da16655acc"
EXPECTED_FIELD = "32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561"
EXPECTED_CAD = "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
REQUIRED = {"P10DW_RUN_MANIFEST.json", "P10DW_RESULT.txt", "P10DW_STOP_TRACE.txt",
            "GEO/A_ORIGINAL_M1_FIELD2.geo", "GEO/B_EXACT_INLINE_F6.geo",
            "GEO/sphere_pore_B6_refined.geo"}


def hashed(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10DX_AUDIT_STOP: " + why)


def verify_members(members: dict[str, bytes]) -> dict:
    require(set(members) == REQUIRED, "archive members / unexpected source")
    manifest = json.loads(members["P10DW_RUN_MANIFEST.json"].decode("utf-8-sig"))
    result = members["P10DW_RESULT.txt"].decode("utf-8-sig").replace("\r\n", "\n")
    trace = members["P10DW_STOP_TRACE.txt"].decode("utf-8-sig").replace("\r\n", "\n")
    require(manifest.get("protocol") == "P10DW_R1_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM" and
            manifest.get("status") == "P10DW_STOP_NO_FEM" and
            manifest.get("mode") == "SOURCE_GEO_PREFLIGHT" and
            manifest.get("accepted_original_m1_sha256") == M1_SHA and
            manifest.get("target_local_volume_ratio") == "1-0.20*kappa" and
            manifest.get("stop_reason") == "P10DW_STOP: generated inline candidate altered",
            "R1 status, M1 identity or stop reason")
    require(manifest.get("native_parse_attempts") == 0 and
            manifest.get("native_parse_passed") == [] and
            manifest.get("native_1d_attempts") == 0 and
            manifest.get("native_2d_3d_attempts") == 0 and
            manifest.get("physical_FEM_attempts") == 0 and
            manifest.get("wall_limit_1d_s") == 15 and
            manifest.get("private_limit_bytes") == 2*1024**3,
            "no-native-launch and resource counters")
    require(result.startswith("RESULT=P10DW_STOP_NO_FEM\n") and
            "NATIVE_1D_ATTEMPTS=0\n" in result and
            "M2_3D_MESH=0\n" in result and "FEM=0\n" in result and
            "STOP_REASON="+manifest["stop_reason"] in result,
            "status/result inconsistency")
    require('P10DW_one_click_1d.py", line 163, in preflight' in trace and
            'P10DW_one_click_1d.py", line 137, in generated_sources' in trace and
            'stop(sha256(exact_path) == INLINE_SHA, "generated inline candidate altered")' in trace and
            trace.rstrip().endswith("RuntimeError: P10DW_STOP: generated inline candidate altered"),
            "original traceback did not stop at generated inline SHA check")

    raw = members["GEO/B_EXACT_INLINE_F6.geo"]
    stripped = raw.replace(b"\r\n", b"\n")
    published = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
                 /"P10DV_M2_INLINE_FIELD20.geo").read_bytes()
    require(hashed(published) == EXPECTED_FIELD and
            raw != stripped and raw.count(b"\r\n") >= 10 and
            b"\r" not in raw.replace(b"\r\n", b"") and
            hashed(raw) != EXPECTED_FIELD and hashed(stripped) == EXPECTED_FIELD and
            stripped == published,
            "pure Windows newline translation must explain exact GEO mismatch")
    cad = members["GEO/sphere_pore_B6_refined.geo"]
    require(hashed(cad) == EXPECTED_CAD, "original included CAD altered")
    original = (ROOT/"research/proposals/P10DV_INLINE_KAPPA20_SOURCE_ONLY_20261121"
                /"P10DN_M2_FIELD20.geo").read_text(encoding="utf-8")
    baseline = (original.split("// F3:", 1)[0]+"\nBackground Field=2;\n").encode("utf-8")
    actual_base = members["GEO/A_ORIGINAL_M1_FIELD2.geo"]
    require(actual_base.replace(b"\r\n", b"\n") == baseline and
            b"Field[6]" not in actual_base, "baseline M1 Threshold or newline mismatch")
    code = (ROOT/"research/proposals/P10DW_EXACT_INLINE_F6_1D_20261121"
            /"P10DW_one_click_1d.py").read_text(encoding="utf-8")
    require('exact_path.write_text(exact, encoding="utf-8")' in code and
            'stop(sha256(exact_path) == INLINE_SHA, "generated inline candidate altered")' in code and
            code.index('m1 = original_m1_path(prompt)') < code.index('sources = generated_sources(run)') < code.index('meta.update({"source_sha_pins"'),
            "cannot attribute STOP to source newline writing / pre-metadata stage")
    # The manifest does not record hashes/versions on STOP because metadata update
    # happened AFTER generated_sources. The code path suggests prior gates ran,
    # but do not independently assert actual M1 SHA/native executable identity.
    return {"original_zip_sha256": EXPECTED_ZIP, "zip_members": len(members),
            "status": "P10DW_STOP_NO_FEM", "reason": manifest["stop_reason"],
            "native_gmsh_parse_attempts": 0, "native_gmsh_1d_attempts": 0,
            "native_gmsh_2d_3d_attempts": 0, "physical_FEM_attempts": 0,
            "original_published_geo_sha256": EXPECTED_FIELD,
            "windows_generated_geo_sha256": hashed(raw),
            "windows_crlf_to_lf_geo_sha256": hashed(stripped),
            "windows_crlf_count": raw.count(b"\r\n"),
            "windows_geo_matches_published_after_only_crlf_normalization": True,
            "cad_sha256": EXPECTED_CAD,
            "baseline_matches_pinned_source_after_crlf_normalization": True,
            "original_m1_hash_passed_by_control_flow": "INFERRED_NOT_IN_STOP_MANIFEST",
            "gmsh_executable_hash_version_passed_by_control_flow": "INFERRED_NOT_IN_STOP_MANIFEST",
            "independent_native_gmsh_execution": False,
            "root_cause": "Path.write_text newline=None on Windows writes CRLF, then byte SHA expects LF",
            "required_fix": "write_bytes(UTF8) for generated GEO, keep original P10DV SHA; new R2 ZIP only"}


def main() -> int:
    require(hashed(INPUT.read_bytes()) == EXPECTED_ZIP, "original primary ZIP changed")
    with zipfile.ZipFile(INPUT) as z:
        require(z.testzip() is None and len(z.namelist()) == len(REQUIRED), "ZIP CRC6/6")
        require(len(set(z.namelist())) == len(REQUIRED), "duplicate ZIP entries")
        found = verify_members({name: z.read(name) for name in z.namelist()})
    # Explicit tampering tests must STOP rather than silently normalize arbitrary edits.
    with zipfile.ZipFile(INPUT) as z:
        base = {name: z.read(name) for name in z.namelist()}
    mutations = [
        ("field_value", "GEO/B_EXACT_INLINE_F6.geo",
         base["GEO/B_EXACT_INLINE_F6.geo"].replace(b"0.2*", b"0.3*", 1)),
        ("cad", "GEO/sphere_pore_B6_refined.geo",
         base["GEO/sphere_pore_B6_refined.geo"]+b"\n// tamper"),
        ("trace", "P10DW_STOP_TRACE.txt",
         base["P10DW_STOP_TRACE.txt"].replace(b"generated_sources", b"unknown_source")),
    ]
    for label, name, changed in mutations:
        require(changed != base[name], "mutation must change "+label)
        fake = dict(base)
        fake[name] = changed
        try:
            verify_members(fake)
        except RuntimeError as e:
            require(str(e).startswith("P10DX_AUDIT_STOP"), "negative test stop prefix")
        else:
            raise RuntimeError("mutation unexpectedly passed: "+label)
    fake = dict(base)
    altered = json.loads(fake["P10DW_RUN_MANIFEST.json"])
    altered["native_parse_attempts"] = 1
    fake["P10DW_RUN_MANIFEST.json"] = json.dumps(altered).encode("utf-8")
    try:
        verify_members(fake)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("native parse mutation unexpectedly passed")
    found["independent_negative_tamper_tests"] = 4
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(found, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("P10DX_REAL_P10DW_R1_WINDOWS_CRLF_FALSE_STOP_AUDIT_PASS",
          "CRC6/6 GEO_exact_LF=PASS CAD=PASS negative4/4",
          "native_parse=0 native_1d=0 M2=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
