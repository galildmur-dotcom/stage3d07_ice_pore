#!/usr/bin/env python3
"""No native FEM/Gmsh: validate all bundled source SHA, smooth recipe and approvals."""
from P10FN_common import HERE, MESHES, load, need, validate_source
from P10FN_adapt import selftest as adapt_test, validate_recipe, generated_geo
from P10FN_physics import selftest as physics_test


def main():
    revision = validate_source()
    adapt_test()
    physics_test()
    recipe = load(HERE / "recipes/ACTIVE.json")
    validate_recipe(recipe)
    parent = (HERE / "M2.geo") if recipe["parent_mesh"] == "M2" else (MESHES / (recipe["parent_mesh"]+".geo"))
    need(parent.is_file(), "parent GEO for ACTIVE recipe absent")
    geo = generated_geo(recipe, parent.read_text(encoding="utf-8"))
    need('Include "'+recipe["parent_mesh"]+'.geo";' in geo,
         "missing smooth inherited field chain")
    print("P10FN_BUNDLE_SOURCE_AND_RECIPE_CHECK_OK", revision,
          "NO_NATIVE_GMSH=1 NO_FEM=1")


if __name__ == "__main__":
    main()
