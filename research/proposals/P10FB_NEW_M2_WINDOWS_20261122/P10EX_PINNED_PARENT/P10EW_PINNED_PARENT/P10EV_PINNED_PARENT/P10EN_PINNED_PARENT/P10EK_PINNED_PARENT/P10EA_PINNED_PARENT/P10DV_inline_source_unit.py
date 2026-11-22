#!/usr/bin/env python3
"""P10DV: exact F3/F4/F5 -> one F6 substitution; source/math ONLY, no Gmsh/FEM."""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import re
import sys

HERE = Path(__file__).resolve().parent
REV = "P10DV_R1_EXACT_INLINE_C1_KAPPA20_SOURCE_ONLY_NO_GMSH_NO_FEM"
ORIGINAL_M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
ORIGINAL_P10DN_GEO_SHA = "d948d7b2b29d70435bbf58bc4ee22f91de353e9162fd954f6fe56a2a40f3ca4f"
P10DN_RELEASE_SHA = "2f0e4a222a35fba618f9123f6235325bd09af9ce0cdb67d425a0c94ce906489b"
P10DT_RELEASE_SHA = "f540adb8f7e9dc4a58fea8ebe5784c99fe4f2607cb6b82cf5ac65dd398b1eb08"
P10DT_WINDOWS_EVIDENCE_SHA = "9c4602ac29a08dd8faa5e977990a3f138f73a39c242dcc3167b09f23bf46d414"
GMSH4152_FIELD_CPP_BLOB_SHA = "427911696c813c5543caa37b527a985775fa6d4e"
PIN_NAME = "P10DV_SOURCE_SHA256.json"
ORIGINAL_GEO = "P10DN_M2_FIELD20.geo"
INLINE_GEO = "P10DV_M2_INLINE_FIELD20.geo"
F2_MIN = 0.00042855883184652975
F2_MAX = 0.0070524788853066865


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("P10DV_SOURCE_STOP: " + message)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_gate() -> dict:
    pin = json.loads((HERE / PIN_NAME).read_text(encoding="utf-8"))
    require(pin.get("revision") == REV and pin.get("native_gmsh_runs") == 0 and
            pin.get("mesh_1d_2d_3d_runs") == 0 and pin.get("physical_FEM") is False and
            pin.get("accepted_original_m1_sha256") == ORIGINAL_M1_SHA and
            pin.get("original_p10dn_geo_sha256") == ORIGINAL_P10DN_GEO_SHA and
            pin.get("original_p10dn_source_zip_sha256") == P10DN_RELEASE_SHA and
            pin.get("p10dt_source_zip_sha256") == P10DT_RELEASE_SHA and
            pin.get("p10dt_windows_evidence_zip_sha256") == P10DT_WINDOWS_EVIDENCE_SHA and
            pin.get("gmsh_4_15_2_Field_cpp_git_blob_sha") == GMSH4152_FIELD_CPP_BLOB_SHA and
            len(pin.get("files", {})) == 6, "protocol/source identity")
    for filename, expected in pin["files"].items():
        path = HERE / filename
        require(filename == Path(filename).name and ".." not in filename and
                path.is_file() and digest(path) == expected,
                "source SHA mismatch " + filename)
    require(digest(HERE / ORIGINAL_GEO) == ORIGINAL_P10DN_GEO_SHA,
            "exact original P10DN GEO/M1/volume cap")
    return pin


def original_fields() -> dict[int, str]:
    source = (HERE / ORIGINAL_GEO).read_text(encoding="utf-8")
    fields = {int(n): expression for n, expression in
              re.findall(r'Field\[(\d+)\]\.F\s*=\s*"([^"]+)";', source)}
    require(set(fields) == {3, 4, 5, 6} and
            fields[3].startswith("min(1,max(0,") and
            fields[4].startswith("min(1,max(0,") and
            fields[5] == "(1-F3*F3*(3-2*F3))*F4*F4*(3-2*F4)" and
            fields[6] == "F2*exp(log(1-0.2*F5)/3)" and
            source.count('// F3:') == 1 and
            source.count('Include "sphere_pore_B6_refined.geo";') == 1,
            "original F3/F4/F5/F6 byte formula contract")
    return fields


def flattened_expression() -> str:
    fields = original_fields()
    # AST-preserving textual substitution: each field reference becomes a
    # parenthesized copy of the exact original MathEval scalar expression.
    kappa = re.sub(r"\bF([34])\b", lambda hit: "("+fields[int(hit[1])]+")", fields[5])
    direct = re.sub(r"\bF5\b", "("+kappa+")", fields[6])
    require(len(direct) < 3000 and re.findall(r"\bF\d+\b", direct) == ["F2"] and
            all(s in direct for s in ("min(1,max(0,", "sqrt(", "exp(log(", "1e-24")),
            "no nested MathEval reference/invalid expression")
    return direct


def candidate_geo_text() -> str:
    source = (HERE / ORIGINAL_GEO).read_text(encoding="utf-8")
    prefix = source.split("// F3:", 1)[0]
    prefix = prefix.replace("// P10DN / M2: SOURCE-ONLY continuous field, NOT a Gmsh run authorization.",
                            "// P10DV / M2: SOURCE-ONLY exact flattened field, NOT a Gmsh run authorization.")
    prefix = prefix.replace("// Coefficient kappa(x,y,z)=F5 in [0,1]. Target V_M2/V_M1=1-0.2*kappa.",
                            "// Kappa inlined in Field6; [0,1]. Target V_M2/V_M1=1-0.2*kappa.")
    require("P10DV / M2:" in prefix and "Kappa inlined in Field6" in prefix and
            "nearSize = 0.00042855883184652975;" in prefix and
            "farSize  = 0.0070524788853066865;" in prefix,
            "original accepted M1 field constants/prefix")
    text = (prefix + "// Single non-reentrant-safe MathEval: only F2 is a Field reference.\n"
            "// No Field3/Field4/Field5 MathEval definitions are needed.\n"
            "Field[6] = MathEval;\nField[6].F = \"" + flattened_expression() +
            "\";\nBackground Field=6;\n")
    require(text.count('Background Field=6;') == 1 and
            text.count('Field[6] = MathEval;') == 1 and
            all(f'Field[{i}] = MathEval;' not in text for i in (3, 4, 5)) and
            text.count('Include "sphere_pore_B6_refined.geo";') == 1,
            "candidate Gmsh GEO source structure")
    return text


ALLOWED_FUNCS = {"min": min, "max": max, "sqrt": math.sqrt,
                 "exp": math.exp, "log": math.log}
ALLOWED_AST = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Load,
               ast.Constant, ast.Name, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.Pow, ast.USub, ast.UAdd)


def compile_scalar(expression: str, names: set[str]):
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        require(isinstance(node, ALLOWED_AST), "unexpected expression syntax")
        if isinstance(node, ast.Name):
            require(node.id in names | set(ALLOWED_FUNCS), "unknown variable " + node.id)
        if isinstance(node, ast.Call):
            require(isinstance(node.func, ast.Name) and node.func.id in ALLOWED_FUNCS,
                    "unexpected scalar function")
    return compile(tree, "<P10DV_SHA_PINNED_MATH_ONLY>", "eval")


def value(code, **variables: float) -> float:
    answer = eval(code, {"__builtins__": {}, **ALLOWED_FUNCS}, variables)
    require(math.isfinite(answer), "non-finite analytically sampled size")
    return answer


def smoothstep_derivative(t: float) -> float:
    return 6*t*(1-t) if 0 < t < 1 else 0.


def independent_kappa_xyz(x: float, y: float, z: float) -> float:
    """Independent P10DN spherical definition, not a MathEval-expression replay."""
    dz = z-.03
    r = math.sqrt(x*x+y*y+dz*dz)
    if r == 0.:  # center is in the excluded pore, not the ice domain
        return 0.
    d = r-.001
    mu = dz/r
    ur = (d-.0001)/.0004
    ua = (mu*mu-.36)/.28

    def smooth(u: float) -> float:
        t = max(0., min(1., u))
        return t*t*(3.-2.*t)

    return (1.-smooth(ur))*smooth(ua)


def math_selftest() -> dict:
    source_gate()
    direct = flattened_expression()
    require(candidate_geo_text().encode("utf-8") == (HERE / INLINE_GEO).read_bytes(),
            "inlined GEO is not the deterministic F3/F4/F5 substitution")
    fields = original_fields()
    expr3 = compile_scalar(fields[3], {"x", "y", "z"})
    expr4 = compile_scalar(fields[4], {"x", "y", "z"})
    expr5 = compile_scalar(fields[5], {"F3", "F4"})
    expr6 = compile_scalar(fields[6], {"F2", "F5"})
    direct_expr = compile_scalar(direct, {"F2", "x", "y", "z"})
    # Analytic fact: S'(0)=S'(1)=0; the non-smooth clamp junctions cancel.
    require(smoothstep_derivative(0.) == smoothstep_derivative(1.) == 0. and
            abs(smoothstep_derivative(.5)-1.5) < 1e-15,
            "C1 smoothstep derivative endpoints")
    rng = random.Random(20261121)
    points: list[tuple[float, float, float]] = []
    center = .03
    for d in (0., .000000001, .00005, .0001, .000100001, .0002,
              .0003, .000499999, .0005, .000500001, .001, .005, .02):
        for mu in (-1., -.999999, -.8, -.799999, -.7, -.6, -.599999,
                   0., .599999, .6, .7, .799999, .8, .999999, 1.):
            for phi in (0., .4, 1.8, 3.14, 4.9):
                rad = .001 + d
                xy = rad*math.sqrt(max(0., 1.-mu*mu))
                points.append((xy*math.cos(phi), xy*math.sin(phi), center+rad*mu))
    for _ in range(16100):
        d = (.00055*rng.random() if rng.random() < .70 else .025*rng.random())
        mu = 2*rng.random()-1
        phi = 2*math.pi*rng.random()
        rad = .001+d
        xy = rad*math.sqrt(max(0., 1.-mu*mu))
        points.append((xy*math.cos(phi), xy*math.sin(phi), center+rad*mu))
    max_relative_size_diff = max_ref_python_kappa_diff = 0.
    min_kappa, max_kappa = 1., 0.
    for x, y, z in points:
        f3 = value(expr3, x=x, y=y, z=z)
        f4 = value(expr4, x=x, y=y, z=z)
        k = value(expr5, F3=f3, F4=f4)
        require(0. <= f3 <= 1. and 0. <= f4 <= 1. and
                -2e-15 <= k <= 1.+2e-15, "all-domain F3/F4/kappa bounds")
        min_kappa, max_kappa = min(min_kappa, k), max(max_kappa, k)
        other_k = independent_kappa_xyz(x, y, z)
        max_ref_python_kappa_diff = max(max_ref_python_kappa_diff, abs(k-other_k))
        for f2 in (F2_MIN, (F2_MIN+F2_MAX)/2., F2_MAX):
            original_h = value(expr6, F2=f2, F5=k)
            direct_h = value(direct_expr, F2=f2, x=x, y=y, z=z)
            relative_error = abs(original_h-direct_h)/f2
            max_relative_size_diff = max(max_relative_size_diff, relative_error)
            ratio = direct_h/f2
            require(math.isclose(ratio**3, 1.-.2*k, rel_tol=3e-14, abs_tol=3e-14)
                    and (.8**(1./3.)-3e-14) <= ratio <= (1.+3e-14),
                    "exact target volume envelope and cubic size law")
    require(len(points) >= 17000 and max_relative_size_diff < 3e-13 and
            max_ref_python_kappa_diff < 3e-12 and min_kappa == 0. and max_kappa == 1.,
            "independent P10DN parity / exact interpolation")
    return {"points": len(points), "F2_samples_per_point": 3,
            "max_normalized_h_M1_to_M2_formula_abs_diff": max_relative_size_diff,
            "max_original_geo_kappa_vs_independent_P10DN_python_abs_diff": max_ref_python_kappa_diff,
            "kappa_sample_min": min_kappa, "kappa_sample_max": max_kappa,
            "target_volume_ratio_envelope": [0.8, 1.],
            "target_size_ratio_envelope": [0.8**(1./3.), 1.],
            "C1_analytic_smoothstep_endpoint_derivatives": [0., 0.],
            "no_nested_MathEval": True,
            "native_gmsh_runs": 0, "physical_FEM_runs": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    require(args.selftest, "only --selftest allowed, never run native Gmsh")
    result = math_selftest()
    print("P10DV_SOURCE_MATH_INLINE_C1_KAPPA20_PASS", "points="+str(result["points"]),
          "max_relative_h_diff="+format(result["max_normalized_h_M1_to_M2_formula_abs_diff"], ".3g"),
          "kappa=[0,1] target_volume_ratio=[0.8,1]",
          "native_Gmsh=0 physical_FEM=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError) as exc:
        print("P10DV STOP:", exc, file=sys.stderr)
        raise SystemExit(2)
