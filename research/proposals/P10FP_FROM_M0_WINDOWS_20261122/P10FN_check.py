#!/usr/bin/env python3
"""No native FEM/Gmsh: validate all bundled source SHA, smooth recipe and approvals."""
from P10FN_common import HERE, MESHES, load, need, validate_source
from P10FN_adapt import selftest as adapt_test, validate_recipe, generated_geo
from P10FN_physics import selftest as physics_test


def main():
    revision = validate_source()
    adapt_test()
    physics_test()
    baseline = (HERE / "M0.geo").read_text(encoding="utf-8")
    need('Include "sphere_pore_B6_refined.geo";' in baseline and
         "Background Field=3;" in baseline and
         "Field[3].F = StrCat(" in baseline,
         "initial M0 geometry must inherit canonical CAD and C1 baseline field")
    recipe = load(HERE / "recipes/ACTIVE.json")
    if recipe.get("schema") == "P10FP_ADAPT_V2":
        validate_recipe(recipe)
        parent = MESHES / (recipe["parent_mesh"]+".geo")
        need(parent.is_file(), "parent GEO for ACTIVE recipe absent")
        geo = generated_geo(recipe, parent.read_text(encoding="utf-8"))
        need('Include "'+recipe["parent_mesh"]+'.geo";' in geo,
             "missing smooth inherited field chain")
    else:
        need(recipe.get("schema") == "P10FP_WAIT_FOR_PREVIOUS_PHYSICS",
             "invalid/no active-recipe state")
    print("P10FN_BUNDLE_SOURCE_AND_RECIPE_CHECK_OK", revision,
          "M0_READY_NO_NATIVE_GMSH=1 NO_FEM=1")


if __name__ == "__main__":
    main()
