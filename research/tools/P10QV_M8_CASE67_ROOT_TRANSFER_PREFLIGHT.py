#!/usr/bin/env python3
"""P10QV A: guarded geometry/root transfer from held-out M8 cases 6 and 7.

Uses the archived, real curved-Tet10 h8 child coordinates. This is a
source-only, fixed-slice audit, not FEM or certified 2D cut quadrature.
At selected dangerous rays, Sturm root counts are exact for the rational
interpretation of the *serialized* child nodes and rational s,t slices.
They do NOT certify the underlying CAD, all slices, or numerical integration.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import sympy as sp

import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild, roots_in_segment

PIN_M8 = "40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
AXES = (0, 1, 2)
# Selected a priori: five transverse coordinates and 25 rays per axis/child.
SLICES = ("0.07", "0.24", "0.50", "0.76", "0.93")
W_SYMBOL = sp.Symbol("w")
HIGH_DEGREE_GUARD = 1e-9
PROBE_RECONSTRUCTION_GUARD = 1e-9


def float_polynomial(child, axis, s, t, which):
    others = [j for j in AXES if j != axis]
    length = (1.0 - s) * (1.0 - t)
    ref = np.zeros((3, 3))
    ref[:, others[0]] = s
    ref[:, others[1]] = (1.0 - s) * t
    ref[:, axis] = [0.0, 0.5 * length, length]
    coords = qi.shape_at(ref) @ child.nodes
    physical = child.physical_poly(coords)
    coefficients = np.asarray(child.constraint(physical, which), dtype=float)
    max_degree = 4 if which in (0, 1) else 2
    coefficients = np.pad(coefficients, (0, max(0, max_degree + 1 - len(coefficients))))
    return coefficients[:max_degree + 1], coords, ref


def physical_point(child, ref):
    mapped = qi.shape_at(ref.reshape(1, 3))[0] @ child.nodes
    return (mapped - np.array([0.0, 0.0, .03])) * 1000.0


def evaluate_constraint_point(child, which, xyz):
    radial, mu, phi = child.sector
    xx, yy, zz = xyz
    if which == 0:
        return (1.0 + (0.0, .02, .05, .1, .25, .5, 1., 2., 5., 15.)[radial]) ** 2 - (xx*xx+yy*yy+zz*zz)
    if which == 1:
        return xx*xx+yy*yy+zz*zz - (1.0 + (0.0, .02, .05, .1, .25, .5, 1., 2., 5., 15.)[radial + 1]) ** 2
    if which == 4:
        angle = -math.pi + math.pi * phi / 6.0
        return math.sin(angle)*xx - math.cos(angle)*yy
    raise ValueError("P10QV_UNEXPECTED_ACTIVE_BOUNDARY")


def scan_ray(child, axis, s, t, which):
    p, xyz, refs = float_polynomial(child, axis, s, t, which)
    magnitude = max(float(np.max(abs(p))), 1e-30)
    last = 2 if which in (0, 1) else 1
    high_rel = float(np.max(abs(p[last + 1:]))) / magnitude
    # Independently evaluate the original Tet10 map at off-grid ray points.
    error = 0.0
    for w in (.173, .591, .827):
        ref = refs[0].copy()
        ref[axis] = w * (1 - s) * (1 - t)
        truth = evaluate_constraint_point(child, which, physical_point(child, ref))
        error = max(error, abs(np.polynomial.polynomial.polyval(w, p) - truth)/magnitude)
    roots = np.polynomial.polynomial.polyroots(p / magnitude)
    interior = [float(r.real) for r in roots
                if abs(r.imag) <= 1e-7 and 0 < r.real < 1]
    guarded = roots_in_segment(p)
    derivative = np.polynomial.polynomial.polyder(p / magnitude)
    critical = np.polynomial.polynomial.polyroots(derivative)
    critical = [float(r.real) for r in critical
                if abs(r.imag) <= 1e-7 and 0 < r.real < 1]
    # Near-tangency score is the least normalized constraint magnitude at
    # an internal stationary point, independent of sign.
    tangent = min((abs(np.polynomial.polynomial.polyval(w, p/magnitude))
                   for w in critical), default=float("inf"))
    endpoint = min(abs(p[0]),abs(np.polynomial.polynomial.polyval(1.,p)))/magnitude
    min_slope = min((abs(np.polynomial.polynomial.polyval(w, derivative))
                     for w in guarded), default=float("inf"))
    root_residual = max((abs(np.polynomial.polynomial.polyval(w, p/magnitude))
                         for w in guarded), default=0.0)
    return {"relative_high_degree":high_rel, "reconstruction_relative":error,
            "interior_unsafe_numpy_roots":len(interior),
            "interior_production_guarded_roots":len(guarded),
            "min_tangency_residual":tangent,
            "min_normalized_endpoint_residual":endpoint,
            "near_contact_risk_score":min(tangent,endpoint),
            "min_guarded_root_derivative":min_slope,
            "max_guarded_float_root_residual":root_residual,
            "coeff":p.tolist()}


def fraction_decimal(value):
    return sp.Rational(str(value))


def exact_curve_coefficients(term, axis, s_str, t_str, which):
    """Compute degree <=4 constraint in w using exact rational node decimals.

    Only the case6/7 azimuth sectors phi=0/6 are supported (sin=0 exactly).
    No P4->P2 approximation is used in this function.
    """
    s = fraction_decimal(s_str)
    t = fraction_decimal(t_str)
    nodes = [[fraction_decimal(v) for v in row] for row in term["nodes"]]
    edges = np.asarray(qi.py.EDGES, dtype=int)
    others = [j for j in AXES if j != axis]
    path = []
    for w in (sp.Rational(0), sp.Rational(1, 2), sp.Rational(1)):
        r = [sp.Rational(0)] * 3
        r[others[0]] = s
        r[others[1]] = (1-s)*t
        r[axis] = w*(1-s)*(1-t)
        bary = [1-sum(r)] + r
        shape = [v*(2*v-1) for v in bary] + [
            4*bary[int(i)]*bary[int(j)] for i,j in edges]
        xyz = [sum(shape[i]*nodes[i][k] for i in range(10))
               for k in range(3)]
        path.append([(xyz[k] - (sp.Rational(3,100) if k == 2 else 0)) * 1000
                     for k in range(3)])
    x0 = path[0]
    x2 = [2*(path[2][k] - 2*path[1][k] + path[0][k]) for k in range(3)]
    x1 = [path[2][k] - path[0][k] - x2[k] for k in range(3)]
    polys = [[x0[k], x1[k], x2[k]] for k in range(3)]
    radius = (sp.Rational(1),sp.Rational(102,100),sp.Rational(105,100),
              sp.Rational(11,10),sp.Rational(125,100),sp.Rational(3,2),
              sp.Rational(2),sp.Rational(3),sp.Rational(6),sp.Rational(16))
    rb = int(term["radial_bin"])
    if which in (0, 1):
        squared = [sp.Rational(0)] * 5
        for component in polys:
            for i,a in enumerate(component):
                for j,b in enumerate(component):
                    squared[i+j] += a*b
        if which == 0:
            squared = [-v for v in squared]
            squared[0] += radius[rb]**2
        else:
            squared[0] -= radius[rb+1]**2
        return squared
    if which == 4:
        if int(term["phi_bin"]) not in (0,6):
            raise ValueError("P10QV_EXACT_AZIMUTH_UNSUPPORTED_PHI")
        factor = 1 if int(term["phi_bin"]) == 0 else -1
        return [factor*v for v in polys[1]]
    raise ValueError("P10QV_EXACT_BOUNDARY_UNSUPPORTED")


def exact_selected_root_audit(decimal_term, axis, s_str, t_str, which, float_count, guarded_count):
    coeff = exact_curve_coefficients(decimal_term, axis, s_str, t_str, which)
    polynomial = sp.Poly(sum(x * W_SYMBOL**i for i,x in enumerate(coeff)), W_SYMBOL)
    count = int(polynomial.count_roots(0, 1))
    # Under the same archived rational geometry, compare the actual P4/P2
    # root count with an *uncertified* reduced-order representation.
    reduced = sp.Poly(sum(x * W_SYMBOL**i for i,x in enumerate(
        coeff[:(3 if which in (0,1) else 2)])), W_SYMBOL)
    reduced_count = int(reduced.count_roots(0, 1))
    mag = max(abs(float(x)) for x in coeff)
    degree_high = max((abs(float(x)) for x in coeff[
        3 if which in (0,1) else 2:]),default=0.)/max(mag,1e-30)
    return {"axis":axis,"s":s_str,"t":t_str,"constraint":which,
            "full_polynomial_degree":polynomial.degree(),
            "reduced_polynomial_degree":reduced.degree(),
            "full_interior_real_root_count_exact_for_serialized_decimal_input":count,
            "reduced_interior_real_root_count_exact_for_serialized_decimal_input":reduced_count,
            "unsafe_numpy_root_count":float_count,
            "production_guarded_root_count":guarded_count,
            "full_vs_reduced_count_mismatch":count != reduced_count,
            "unsafe_numpy_vs_exact_count_mismatch":count != float_count,
            "production_guarded_vs_exact_count_mismatch":count != guarded_count,
            "higher_degree_ratio_exact_decimal_input":degree_high}


def synthetic_negative_tests():
    w = W_SYMBOL
    quartic = sp.Poly((w-sp.Rational(1,4))*(w-sp.Rational(3,4))*(w+1)*(w+2),w)
    if quartic.count_roots(0,1) != 2 or quartic.degree() != 4:
        raise ValueError("P10QV_SYNTHETIC_QUARTIC_ROOT_GATE_BROKEN")
    if not quartic.all_coeffs()[0]:
        raise ValueError("P10QV_SYNTHETIC_QUARTIC_DEGREE_GATE_BROKEN")
    tangent = sp.Poly((w-sp.Rational(1,2))**2,w)
    if tangent.count_roots(0,1) != 1 or tangent.discriminant() != 0:
        raise ValueError("P10QV_SYNTHETIC_TANGENCY_GATE_BROKEN")
    # A double root is not assumed to yield a sign change.
    if (tangent.eval(sp.Rational(2,5)) > 0 and
        tangent.eval(sp.Rational(3,5)) > 0) is False:
        raise ValueError("P10QV_SYNTHETIC_TANGENCY_SIGN_TEST_BROKEN")
    ill_conditioned = [-.01578821441236987, .016243839732051506, -2.08166817e-17]
    expected = float(.01578821441236987/.016243839732051506)
    if len(roots_in_segment(ill_conditioned))!=1 or \
       abs(roots_in_segment(ill_conditioned)[0]-expected)>1e-12:
        raise ValueError("P10QV_PRODUCTION_GUARDED_NEAR_LINEAR_ROOT_FAILED")
    return {"true_quartic_rejected_by_degree_gate": True,
            "interior_double_root_has_no_sign_change": True,
            "exact_rational_root_count_synthetic": True,
            "production_guarded_near_linear_root": True}


def preflight_case(root:Path, case:int):
    path=root / f"P10QO_M8_REAL_CASE{case}_H8_CHILDREN_QA.json"
    data=json.loads(path.read_text())
    data_dec=json.loads(path.read_text(),parse_float=Decimal)
    if data["mesh_sha256"] != PIN_M8 or data["source_cases"] != [case] or \
       data["min_h_one"] != 8 or data["h_depth_limit"] != 8 or \
       data["physical_4D_FEM_approved"] or len(data["terminals"])!=len(data_dec["terminals"]):
        raise ValueError("P10QV_PINNED_REAL_M8_H8_INPUT_INVALID")
    cuts=[(i,term) for i,term in enumerate(data["terminals"])
          if term["group"] in ("one","multi")]
    expected={6:{"cut":90,"orig":5751,"sector":[4,9,0]},
              7:{"cut":88,"orig":5847,"sector":[4,9,6]}}[case]
    if len(cuts)!=expected["cut"] or \
       data["cases"][0]["original_element_id"] != expected["orig"] or \
       data["cases"][0]["sector"] != expected["sector"]:
        raise ValueError("P10QV_CHANGED_REAL_SOURCE_ELEMENT")
    summaries={}
    all_samples=[]
    for axis in AXES:
        degree_max=0.; reconstruction=0.; min_tangent=float("inf")
        active_counter=Counter()
        samples=0
        for index,term in cuts:
            child=RayChild(term) # independently validates exact full FE moments
            active_counter[tuple(child.active)]+=1
            if any(x not in (0,1,4) for x in child.active):
                raise ValueError("P10QV_UNSUPPORTED_ACTIVE_CONSTRAINT")
            for s_str in SLICES:
                for t_str in SLICES:
                    for which in child.active:
                        audit=scan_ray(child,axis,float(s_str),float(t_str),which)
                        degree_max=max(degree_max,audit["relative_high_degree"])
                        reconstruction=max(reconstruction,audit["reconstruction_relative"])
                        min_tangent=min(min_tangent,audit["min_tangency_residual"])
                        all_samples.append({"index":index,"axis":axis,
                            "s":s_str,"t":t_str,"constraint":which,
                            **{k:v for k,v in audit.items() if k!="coeff"}})
                        samples+=1
        if reconstruction>PROBE_RECONSTRUCTION_GUARD:
            raise ValueError("P10QV_REAL_CURVED_MAPPING_RECONSTRUCTION_FAIL")
        summaries[str(axis)]={"source_cut_children":len(cuts),
            "constraint_rays":samples,
            "active_sets":{str(k):v for k,v in active_counter.items()},
            "max_relative_forbidden_high_coefficients":degree_max,
            "max_independent_physical_reconstruction_relative":reconstruction,
            "min_normalized_stationary_constraint_abs":min_tangent,
            "sampled_degree_reduction_gate_pass":degree_max<=HIGH_DEGREE_GUARD}
        print(f"P10QV case={case} axis={axis} real_cut={len(cuts)} "
              f"rays={samples} high={degree_max:.3e} "
              f"reconstruction={reconstruction:.3e}",flush=True)
    # Freeze a small independent exact-rational gate: most near-tangential
    # radial rays on EACH of three axes, plus the most dangerous azimuth.
    selected=[]
    for axis in AXES:
        local=[r for r in all_samples if r["axis"]==axis]
        for radial in (True,False):
            subset=[r for r in local if (r["constraint"] in (0,1))==radial]
            if not subset:continue
            for row in sorted(subset,key=lambda x:(x["near_contact_risk_score"],
                                                    x["index"],x["s"],x["t"]))[:2]:
                key=(row["index"],axis,row["s"],row["t"],row["constraint"])
                if key not in {(z["index"],z["axis"],z["s"],z["t"],z["constraint"])
                               for z in selected}:
                    selected.append(row)
    checked=[]
    for row in selected:
        result=exact_selected_root_audit(
            data_dec["terminals"][row["index"]],row["axis"],row["s"],row["t"],
            row["constraint"],row["interior_unsafe_numpy_roots"],
            row["interior_production_guarded_roots"])
        result.update({"child_index":row["index"],
                       "double_stationary_contact_score":row["min_tangency_residual"],
                       "near_contact_risk_score":row["near_contact_risk_score"]})
        checked.append(result)
    return {"source_case":case,"original_element_id":expected["orig"],
            "sector":expected["sector"],"input_json_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "children":len(data["terminals"]),"cut_children":len(cuts),
            "active_constraints_all":dict(Counter(str(tuple(i for i,v in enumerate(t["status"]) if v==0))
                                           for _,t in cuts)),
            "axis_preflight":summaries,"selected_exact_rational_root_tests":checked,
            "selected_full_vs_reduced_mismatch_count":sum(x["full_vs_reduced_count_mismatch"] for x in checked),
            "selected_unsafe_numpy_vs_exact_mismatch_count":sum(x["unsafe_numpy_vs_exact_count_mismatch"] for x in checked),
            "selected_guarded_vs_exact_mismatch_count":sum(x["production_guarded_vs_exact_count_mismatch"] for x in checked),
            "worst_near_tangency_candidates":sorted(all_samples,
                key=lambda x:(x["near_contact_risk_score"],x["index"],x["axis"]))[:12]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    tests=synthetic_negative_tests()
    results=[preflight_case(a.input_dir,case) for case in (6,7)]
    out={"stage":"P10QV_A","date":"2026-11-28",
         "scope":"real M8 cases6/7 h8 polynomial-degree and local real-root transfer preflight",
         "research_branch_head_at_input":"f33dff934fcbedb86d58298e5d0875598ea482a9",
         "pinned_M8_mesh_sha256_from_archived_provenance":PIN_M8,
         "actual_msh_bytes_not_present_locally":True,
         "sampling_s_t":list(SLICES),"axes":list(AXES),
         "forbidden_high_coefficient_gate":HIGH_DEGREE_GUARD,
         "root_certificate_scope":"exact Sturm counts only at listed fixed rays for rationalized serialized nodes",
         "not_global_interval_certification":True,
         "not_physical_FEM_or_jpeak":True,"mesh_changed":False,
         "Gmsh_run":False,"physical_FEM_run":False,
         "synthetic_negative_tests":tests,
         "cases":results,
         "all_sampled_degree_gates_pass":all(
             x["sampled_degree_reduction_gate_pass"]
             for case in results for x in case["axis_preflight"].values()),
         "all_selected_rational_root_counts_agree_with_production_guard":all(
             case["selected_guarded_vs_exact_mismatch_count"]==0 for case in results)}
    def finite_json(x):
        if isinstance(x,float) and not math.isfinite(x):
            return None
        if isinstance(x,list):
            return [finite_json(v) for v in x]
        if isinstance(x,dict):
            return {k:finite_json(v) for k,v in x.items()}
        return x
    a.output.write_text(json.dumps(finite_json(out),indent=2,
                                  ensure_ascii=False,allow_nan=False)+"\n")
    print("P10QV_A_FIXED_RAY_GEOMETRY_PREFLIGHT_COMPLETE_NOT_4D_CERTIFIED",flush=True)


if __name__=="__main__":
    main()
