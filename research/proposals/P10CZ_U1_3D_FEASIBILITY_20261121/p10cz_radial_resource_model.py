#!/usr/bin/env python3
"""P10CZ: analytic radial h-field cost scenarios, NO Gmsh/mesh/FEM."""
import argparse
import json
import math
from pathlib import Path

R_MM = 1.0
BOX_MM3 = 60.0 * 60.0 * 50.0
CORNER_QUALITY_IDEAL_COEFF = 12.0 / math.sqrt(2.0)
U0_TET10 = 90725
U0_TARGET_MM = 2.0
HIST_TET10 = 475544
HIST_BUFFERS_GIB = 8.14395
HIST_MSH_BYTES = 16218389
HIST_MSH_TET10 = U0_TET10


def target_h_mm(d):
    a = .02 if d <= .02 else (.2 if d >= .8 else .02 + .18*(d-.02)/.78)
    b = .02 if d <= .8 else (2.0 if d >= 12.0 else .02 + 1.98*(d-.8)/11.2)
    return max(a, b)


def radial_integral(left, right, steps=20000):
    step = (right-left)/steps
    total = 0.
    for i in range(steps):
        d = left + (i+.5)*step
        total += 4*math.pi*(R_MM+d)**2/target_h_mm(d)**3*step
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--selftest",action="store_true")
    args = ap.parse_args()
    cuts = [0., .02, .1, .8, .8 + .18*11.2/1.98, 5., 12.]
    for d,h in ((0.,.02),(.02,.02),(.8,.2),(cuts[4],.2),(12.,2.)):
        assert abs(target_h_mm(d)-h)<1e-12
    sections = []
    for left,right in zip(cuts,cuts[1:]):
        n1=radial_integral(left,right,10000)
        n2=radial_integral(left,right,20000)
        assert abs(n1-n2)/n2 < 2e-7, "quadrature unstable"
        sections.append({"d_lower_mm":left,"d_upper_mm":right,
                         "volume_mm3":4*math.pi/3*((R_MM+right)**3-(R_MM+left)**3),
                         "volume_over_hcubed":n2})
    outer_volume=BOX_MM3-4*math.pi/3*(R_MM+12.)**3
    assert outer_volume>0
    outer_I=outer_volume/2**3
    total_I=sum(b["volume_over_hcubed"] for b in sections)+outer_I
    solid_volume=BOX_MM3-4*math.pi/3*R_MM**3
    c_uniform=U0_TET10*U0_TARGET_MM**3/solid_volume
    c_surface=74578*(.020012807470767772**2)/(4*math.pi*R_MM**2)
    c_equilateral_surface=4/math.sqrt(3)
    scenarios=[]
    for label,c in (("observed_U0_whole_volume_calibration",c_uniform),
                    ("ideal_regular_tet_geometry",CORNER_QUALITY_IDEAL_COEFF),
                    ("higher_density_illustration",12.),("stress_illustration",20.)):
        n=c*total_I
        scenarios.append({"label":label,"coefficient":c,"tet10_proxy":round(n),
                          "buffers_gib_linear_proxy":HIST_BUFFERS_GIB*n/HIST_TET10,
                          "mesh_mib_U0_bytes_per_tet_proxy":HIST_MSH_BYTES*n/HIST_MSH_TET10/(1024**2)})
    result={
        "result":"P10CZ_U1_RADIAL_RESOURCE_MODEL_ONLY_NO_MESH_NO_FEM",
        "geometry":"60x60x50 mm box minus R1mm pore; distance field radialised to R13mm",
        "source":"P10CV GEO Threshold fields 3 and 4 combined with Max field 5",
        "h_values_mm":{"wall":.02,"band":.2,"far":2.,"transition_d_mm":cuts},
        "surface_measured":{"tri6_pore_415":74578,"hmax_p50_um":20.012807470767772,
                            "surface_count_coefficient":c_surface,
                            "equilateral_surface_coefficient":c_equilateral_surface},
        "whole_U0_observed_coefficient":c_uniform,
        "regular_tet_coefficient":CORNER_QUALITY_IDEAL_COEFF,
        "radial_sections":sections,
        "far_box_region":{"r_lower_mm":13.,"outer_volume_mm3":outer_volume,"volume_over_hcubed":outer_I},
        "total_volume_over_hcubed":total_I,
        "scenarios":scenarios,
        "caveats":["No actual 3D mesh; field-distance sampling and Gmsh size overrides unmeasured",
                   "Coefficients are scenario proxies, not rigorous element-count bounds",
                   "RAM from historic H4W5B20 state buffers, not Gmsh/Windows RSS",
                   "MSH bytes from earlier U0, not guaranteed for fine U1",
                   "No FEM permitted and no physical M1 mesh exists"]}
    if args.selftest:
        print("P10CZ_FIELD_AND_QUADRATURE_UNIT_OK",round(total_I,5),round(c_uniform,5))
        return
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(result["result"],"integral",total_I,"ideal_tets",scenarios[1]["tet10_proxy"])


if __name__ == "__main__":
    main()
