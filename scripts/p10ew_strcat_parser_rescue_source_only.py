#!/usr/bin/env python3
"""P10EW: byte-exact P10EU C1 expression, Gmsh 4.15.2 StrCat parser rescue.

The Gmsh 4.15.2 GEO lexer parses quoted literals into char tmp[1024].
This generator keeps the *entire mathematical expression unchanged*, splitting
only its string representation into <=600-character literals joined by StrCat.
No native Gmsh, M2, physics, or one-shot marker is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / "gmsh/P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo"
OUT = ROOT / "gmsh/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo"
AUDIT = ROOT / "research/evidence/P10EW_STRCAT_RESCUE_20261122/derived/P10EW_STRCAT_SOURCE_AUDIT.json"
OLD_SHA = "4c4a4aeb4f97bfec350e1e057a57e275d436c09d63a02438a8acfe4ad386253a"
MAX_LITERAL = 600


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10EW_STOP: " + why)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> tuple[str, str]:
    raw = OLD.read_bytes()
    require(sha(raw) == OLD_SHA, "P10EU original GEO SHA changed")
    original = raw.decode("utf-8")
    match = re.search(r'Field\[6\]\.F = "([^"\r\n]+)";', original)
    require(match is not None and original.count('Field[6].F = "') == 1,
            "original single inline MathEval not found")
    expr = match.group(1)
    require(len(expr) == 4198 and
            all(ch.isascii() for ch in expr) and
            "\\" not in expr and '"' not in expr and
            "F2" not in expr,
            "old expression identity and safe direct string splitting")
    chunks = [expr[i:i+MAX_LITERAL] for i in range(0, len(expr), MAX_LITERAL)]
    require(len(chunks) == 7 and
            all(0 < len(x) <= MAX_LITERAL < 1023 for x in chunks) and
            "".join(chunks) == expr, "Gmsh GEO lexer <=1023 per literal")
    new_field = "Field[6].F = StrCat(\n" + ",\n".join(
        '  "' + chunk + '"' for chunk in chunks) + "\n);"
    new_geo = original[:match.start()] + new_field + original[match.end():]
    new_geo = new_geo.replace("// P10EU SOURCE ONLY", "// P10EW STRCAT SOURCE ONLY", 1)
    require(new_geo.count("Field[6] = MathEval;") == 1 and
            new_geo.count("Background Field=6;") == 1 and
            new_geo.count("Mesh.Algorithm3D=10;") == 1 and
            new_geo.count('Include "sphere_pore_B6_refined.geo";') == 1 and
            new_geo.count("StrCat(") == 1 and
            "Mesh 3;" not in new_geo and "SystemCall" not in new_geo,
            "exact single field and no native run commands")
    reparse = re.search(r'Field\[6\]\.F = StrCat\((.*?)\);', new_geo, re.S)
    require(reparse is not None, "new StrCat field location")
    literals = re.findall(r'"([^"\r\n]*)"', reparse.group(1))
    require(literals == chunks and "".join(literals) == expr and
            reparse.group(1).count('"') == 2*len(chunks),
            "independent exact reconstructed original expression")
    report = {
        "revision": "P10EW_R1_STRCAT_GEO_LEXER_1023_SOURCE_RESCUE",
        "failure": "P10EV native -parse_and_exit STOP; Gmsh4.15.2 Gmsh.l parsestring char tmp[1024]",
        "original_P10EU_GEO_SHA256": OLD_SHA,
        "original_MathEval_expression_SHA256": sha(expr.encode("ascii")),
        "new_P10EW_GEO_SHA256": sha(new_geo.encode("utf-8")),
        "reconstructed_MathEval_expression_SHA256": sha("".join(literals).encode("ascii")),
        "math_expression_identical_byte_for_byte": True,
        "mathematical_contract": "P10EU/P10ET C1, alpha17, kappa0 unchanged",
        "original_literal_length": len(expr),
        "strcat_chunk_characters": list(map(len, chunks)),
        "max_quoted_field_literal": max(map(len, chunks)),
        "Gmsh_4_15_2_lexer_max_literal_characters": 1023,
        "MathEval_fields": 1,
        "nested_MathEval_fields": 0,
        "native_Gmsh_runs": 0,
        "M2_3D_runs": 0,
        "FEM_runs": 0,
        "status": "P10EW_SOURCE_ONLY_READY_NATIVE_WINDOWS_PARSE_UNVERIFIED"
    }
    return new_geo, json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    geo, report = build()
    if args.write:
        for target, content in ((OUT,geo),(AUDIT,report)):
            if target.exists():
                require(target.read_bytes() == content.encode("utf-8"),
                        "refusing overwrite changed " + str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content.encode("utf-8"))
    if args.verify:
        require(OUT.is_file() and OUT.read_bytes() == geo.encode("utf-8") and
                AUDIT.is_file() and AUDIT.read_bytes() == report.encode("utf-8"),
                "generated corrected field or audit differs")
    print("P10EW_STRCAT_SOURCE_ONLY_" +
          ("WRITE" if args.write else "VERIFY" if args.verify else "SELFTEST") +
          "_PASS", "original_expression=4198", "literal_max=600",
          "original_expression_byte_exact=PASS", "native_Gmsh=0 M2=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
