#!/usr/bin/env python3
"""One-click M(n)->M(n+1) smooth adaptive mesh, NO FEM or typed confirmation.

The researcher supplies one SHA-pinned recipe *after reviewing previous physics*.
No automatic blind re-adaptation. All meshes and .geo live in G:/ildar/Stage3D07/meshes.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import traceback

from P10FN_common import (HERE, MESHES, RUNS, capped_process, load, need, now,
                          prepare_run, require_windows, sha256, validate_source,
                          write_new, zip_evidence)
from P10FN_mesh_qa import audit

GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
NAMED = re.compile(r"M(0|[1-9][0-9]*)$")


def smooth(expr):
    """C1 endpoint slope: s(u)=u²(3−2u), with clamped u."""
    u = "min(1,max(0,(" + expr + ")))"
    return f"(({u})*({u})*(3-2*({u})))"


def kappa_expression(recipe):
    cfg = recipe["smooth_kappa"]
    a, b = float(cfg["radial_full_mm"]), float(cfg["radial_zero_mm"])
    lo, hi = float(cfg["polar_start_mu"]), float(cfg["polar_full_mu"])
    north, south = float(cfg["north_weight"]), float(cfg["south_weight"])
    need(0 <= a < b <= 2.0 and 0 <= lo < hi <= 1., "bad smooth radial/polar bands")
    need(0 <= north <= 1 and 0 <= south <= 1 and max(north, south) == 1,
         "kappa weights must be 0..1, at least one is 1")
    dist = "(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001)"
    mu = "((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))"
    radial = f"(1-{smooth(f'(({dist})-{a/1000:.17g})/{(b-a)/1000:.17g}')})"
    polar_n = smooth(f"(({mu})-{lo:.17g})/{hi-lo:.17g}")
    polar_s = smooth(f"((-({mu}))-{lo:.17g})/{hi-lo:.17g}")
    return f"({radial}*({north:.17g}*({polar_n})+{south:.17g}*({polar_s})))"


def kappa_at(recipe, x, y, z):
    """Independent numeric equivalent for unit tests and target-volume samples."""
    c = recipe["smooth_kappa"]
    def s(v):
        v = min(1., max(0., v))
        return v*v*(3-2*v)
    dx, dy, dz = x, y, z-.03
    radius = math.sqrt(dx*dx+dy*dy+dz*dz+1e-24)
    d = (radius-.001)*1000.
    mu = dz/radius
    r = 1-s((d-float(c["radial_full_mm"])) /
            (float(c["radial_zero_mm"])-float(c["radial_full_mm"])))
    north = s((mu-float(c["polar_start_mu"])) /
              (float(c["polar_full_mu"])-float(c["polar_start_mu"])))
    south = s((-mu-float(c["polar_start_mu"])) /
              (float(c["polar_full_mu"])-float(c["polar_start_mu"])))
    return r*(float(c["north_weight"])*north+float(c["south_weight"])*south)


def ensure_geo(name):
    target = MESHES / name
    if not target.exists():
        source = HERE / name
        need(source.is_file(), "missing parent geometry source: " + name)
        shutil.copy2(source, target)
    if name == "M2.geo":
        ensure_geo("sphere_pore_B6_refined.geo")
    return target


def generated_geo(recipe, parent_content):
    """Append new field pair to immutable parent field chain."""
    matches = list(re.finditer(r"Background\s+Field\s*=\s*(\d+)\s*;", parent_content))
    need(matches, "parent GEO has no background mesh-size field")
    old_field = int(matches[-1].group(1))
    max_field = max(int(x) for x in re.findall(r"Field\[(\d+)\]", parent_content))
    need(old_field == max_field and old_field >= 6 and old_field % 2 == 0,
         "parent field chain is not a canonical approved P10EY descendant")
    new_kappa = max_field + 1
    new_size = max_field + 2
    alpha = float(recipe["alpha"])
    expr = kappa_expression(recipe)
    # P10EY native-parser lesson: split long MathEval strings into StrCat
    # fragments; never pass a near-1KiB one-piece Gmsh string.
    chunks = ',\n  '.join('"'+expr[i:i+380]+'"' for i in range(0,len(expr),380))
    text = (
        f"// P10FN {recipe['new_mesh']}: C1 adaptation inherited from {recipe['parent_mesh']}.\n"
        f"// Physical volume target h_new^3/h_old^3 = 1-{alpha:.17g}*kappa(x).\n"
        f'Include "{recipe["parent_mesh"]}.geo";\n'
        f"Field[{new_kappa}] = MathEval;\n"
        f'Field[{new_kappa}].F = StrCat(\n  {chunks}\n);\n'
        f"Field[{new_size}] = MathEval;\n"
        f'Field[{new_size}].F = "F{old_field}*exp(log(1-{alpha:.17g}*F{new_kappa})/3)";\n'
        f"Background Field={new_size};\n"
        "Mesh.Algorithm=5;\nMesh.Algorithm3D=10;\n"
        "Mesh.ElementOrder=2;\nMesh.HighOrderOptimize=1;\n"
        "Mesh.MeshSizeExtendFromBoundary=0;\n"
        "Mesh.MeshSizeFromPoints=0;\nMesh.MeshSizeFromCurvature=0;\n"
        "Mesh.MshFileVersion=2.2;\nMesh.Binary=0;\n"
    )
    return text


def validate_recipe(recipe):
    need(recipe.get("schema") == "P10FN_ADAPT_V1", "unapproved recipe schema")
    old, new = recipe.get("parent_mesh"), recipe.get("new_mesh")
    need(isinstance(old, str) and isinstance(new, str) and NAMED.fullmatch(old) and NAMED.fullmatch(new),
         "M0...MN mesh names only")
    need(int(new[1:]) == int(old[1:]) + 1 and int(old[1:]) >= 2,
         "adaptive program starts at M2->M3; M0->M1 and M1->M2 are historical")
    need(0.15 <= float(recipe.get("alpha", -1)) <= 0.25,
         "local characteristic-volume adjustment must be 15..25%")
    for field in ("parent_mesh_sha256", "parent_geo_sha256"):
        need(re.fullmatch("[0-9a-f]{64}", recipe.get(field, "")) is not None,
             "parent SHA not pinned: " + field)
    return old, new


def selftest():
    assert abs(1-0.20*1-0.8) < 1e-15
    recipe = {"schema": "P10FN_ADAPT_V1", "parent_mesh": "M2", "new_mesh": "M3",
              "parent_mesh_sha256": "a"*64, "parent_geo_sha256": "b"*64,
              "alpha": 0.2, "smooth_kappa": {"radial_full_mm": .05,
              "radial_zero_mm": .35, "polar_start_mu": .55, "polar_full_mu": .8,
              "north_weight": 1.0, "south_weight": .8}}
    validate_recipe(recipe)
    expression = kappa_expression(recipe)
    assert expression.count("min(1,max(0,") >= 3
    assert abs(kappa_at(recipe, 0, 0, .03105)-1) < 1e-12
    assert abs(kappa_at(recipe, 0, 0, .02895)-.8) < 1e-12
    assert abs(kappa_at(recipe, .00105, 0, .03)) < 1e-12
    assert abs(kappa_at(recipe, 0, 0, .0314)) < 1e-12
    parent = (HERE / "M2.geo").read_text(encoding="utf-8")
    geo = generated_geo(recipe, parent)
    assert 'Include "M2.geo";' in geo and "F6*exp(log(1-0.20000000000000001*F7)/3)" in geo
    for bad in ("M2", "M4", "H0"):
        mutated = dict(recipe, new_mesh=bad)
        try:
            validate_recipe(mutated)
        except (ValueError, RuntimeError):
            pass
        else:
            raise AssertionError("wrong mesh transition was permitted")
    print("P10FN_ADAPT_SOURCE_SELFTEST_OK no_Gmsh=1 no_FEM=1")


def generate(recipe_path):
    require_windows()
    validate_source()
    recipe = load(recipe_path)
    old, new = validate_recipe(recipe)
    parent_msh = MESHES / (old + ".msh")
    need(parent_msh.is_file() and sha256(parent_msh) == recipe["parent_mesh_sha256"],
         "parent mesh absent or SHA differs from validated physics")
    parent_geo = ensure_geo(old + ".geo")
    need(sha256(parent_geo) == recipe["parent_geo_sha256"],
         "parent GEO SHA changed; cannot inherit approved C1 field")
    need(GMSH.is_file(), "Gmsh 4.15.2 not found at canonical C: path")
    need(not (MESHES/(new+".msh")).exists() and not (MESHES/(new+".geo")).exists(),
         "target mesh/geometry already exists; no overwrite")
    # Idempotence across re-extractions: marker is consumed BEFORE native Gmsh.
    marker = RUNS / "P10FN_LOCKS" / (new+"_FROM_"+recipe["parent_mesh_sha256"][:16]+".json")
    need(not marker.exists(), "one-shot generation already attempted for this parent")
    folder = prepare_run("MESH", new)
    manifest = {"protocol": "P10FN_ADAPT_V1", "status": "CONSUMED",
                "parent_mesh": old, "new_mesh": new, "recipe": recipe,
                "started_utc": now(), "gmsh": str(GMSH),
                "FEM_attempts": 0, "native_3d_attempts": 0}
    write_new(marker, manifest)
    generated = generated_geo(recipe, parent_geo.read_text(encoding="utf-8"))
    output_geo = MESHES / (new + ".geo")
    output_geo.write_text(generated, encoding="utf-8")
    candidate = folder / (new + ".msh")
    cmd = [str(GMSH), str(output_geo), "-3", "-nopopup", "-nt", "4",
           "-format", "msh2", "-o", str(candidate)]
    manifest["native_3d_attempts"] = 1
    manifest["command"] = cmd
    sample_points = {"north_pore_plus_50um": (0.,0.,.03105),
                     "south_pore_plus_50um": (0.,0.,.02895),
                     "equator_pore_plus_50um": (.00105,0.,.03),
                     "north_pore_plus_400um": (0.,0.,.0314)}
    manifest["predicted_field_samples"] = {
        name: {"kappa": kappa_at(recipe, *point),
               "h_ratio": (1-float(recipe["alpha"])*kappa_at(recipe,*point))**(1/3),
               "target_volume_ratio": 1-float(recipe["alpha"])*kappa_at(recipe,*point)}
        for name,point in sample_points.items()}
    log = folder / "P10FN_GMSH_LOG.txt"
    try:
        manifest.update(capped_process(cmd, cwd=MESHES, log=log, wall_s=900,
                                       memory_gib=8, output_dir=folder, output_gib=2))
        need(manifest["native_exit_code"] == 0 and not manifest["stop_reason"],
             "Gmsh native exit/limits failed")
        qa = audit(candidate)
        (folder / "P10FN_MESH_QA.json").write_text(json.dumps(qa, indent=2)+"\n", encoding="utf-8")
        # Never overwrite: target had to be absent at the beginning.
        target = MESHES / (new+".msh")
        need(not target.exists(), "target appeared during Gmsh operation")
        shutil.copy2(candidate, target)
        need(sha256(target) == qa["mesh_sha256"], "final mesh copy failed SHA check")
        manifest["status"] = "MESH_GENERATED_QA27_PASS_AWAITING_RESEARCHER_GO"
        manifest["mesh_sha256"] = qa["mesh_sha256"]
        manifest["qa"] = qa
    except BaseException as err:
        manifest["status"] = "MESH_STOP_NO_FEM"
        manifest["error"] = repr(err)
        (folder / "P10FN_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        meta = folder / "P10FN_MESH_MANIFEST.json"
        meta.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        files = [(meta, meta.name), (log, log.name), (output_geo, output_geo.name),
                 (Path(recipe_path), "RECIPE.json"),
                 (folder/"P10FN_MESH_QA.json", "P10FN_MESH_QA.json")]
        if candidate.is_file() and candidate.stat().st_size <= 32 * 1024**2:
            files.append((candidate, candidate.name))
        archive = folder / ("P10FN_" + new + "_MESH_EVIDENCE.zip")
        zip_evidence(archive, files)
    print("P10FN_MESH_RESULT", manifest["status"], flush=True)
    print("SEND THIS FILE:", archive, flush=True)
    print("MESH LOCATION:", MESHES / (new+".msh"), flush=True)
    print("WAIT FOR PHYSICS APPROVAL SHA before starting the physics launcher.", flush=True)
    return 0 if manifest["status"].startswith("MESH_GENERATED_") else 2


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--recipe", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    try:
        if a.selftest:
            selftest()
        else:
            need(a.recipe is not None, "missing SHA-pinned recipe file")
            raise SystemExit(generate(a.recipe))
    except (OSError, ValueError, RuntimeError, AssertionError, KeyError) as error:
        print("P10FN_MESH_STOP:", error, file=sys.stderr)
        raise SystemExit(2)
