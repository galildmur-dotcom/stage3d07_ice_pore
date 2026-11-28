#!/usr/bin/env python3
"""P10QA: true physical cut-volume brackets on accepted curved M8 Tet10.

At every h-depth, all-in sub-tetrahedra contribute to a rigorous-in-exact-
arithmetic lower bound, all-out contribute zero, and unresolved sub-tetrahedra
contribute to the gap between lower and upper bound. Volumes contain the true
curved quadratic Tet10 detJ, not reference-volume surrogates. A degree-three
Bernstein Jacobian control net certifies positivity of each parent map.

No mesh generation or modification, CAD, Gmsh, FEM, thermal/EDV or adjoints.
Numerics use guarded float64, not directed interval arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz


ALPHA3 = [tuple(a) for a in itertools.product(range(4), repeat=4) if sum(a) == 3]
ALPHA3_ID = {a: k for k, a in enumerate(ALPHA3)}


def multinomial3(alpha):
    return math.factorial(3) // math.prod(math.factorial(x) for x in alpha)


def jacobian_at_reference_vertices(X):
    """Affine-in-uvw parent-Jacobian values at four root reference vertices."""
    gradients = np.stack([m8.tet10_shape(v)[1] for v in py.REF_TET])
    return np.einsum('eki,vkj->evij', X, gradients, optimize=True)


def detj_bernstein_cubic_from_affine_jacobian(vertex_jac):
    """Multilinearity of det produces the 20 true cubic Bernstein controls."""
    result = np.zeros((len(vertex_jac), 20), dtype=np.float64)
    for i, j, k in itertools.product(range(4), repeat=3):
        alpha = tuple(int(t == i) + int(t == j) + int(t == k) for t in range(4))
        p, q, r = vertex_jac[:, i, :, 0], vertex_jac[:, j, :, 1], vertex_jac[:, k, :, 2]
        det = np.einsum('ni,ni->n', p, np.cross(q, r))
        result[:, ALPHA3_ID[alpha]] += det / multinomial3(alpha)
    return result


# Classical symmetric five-point degree-3 exact tetrahedron rule.
# The negative centroid weight is harmless for polynomial exactness;
# a *separate* positive Bernstein bound proves the Jacobian's sign.
QUAD_BARY = np.array([[.25, .25, .25, .25]] +
                     [tuple(.5 if i == j else 1/6 for i in range(4)) for j in range(4)],
                     dtype=np.float64)
QUAD_W = np.array([-.8, .45, .45, .45, .45], dtype=np.float64)


def physical_volume_of_subcells(parent_coeff, subcells, depth):
    """Exact degree-3 detJ volume (in float64) on curved child sub-tetrahedra."""
    if not len(subcells):
        return np.empty(0, dtype=np.float64)
    uvw = np.einsum('qv,nvk->nqk', QUAD_BARY, subcells)
    bary = np.concatenate((1-uvw.sum(axis=2, keepdims=True), uvw), axis=2)
    sample = np.empty((len(subcells), len(QUAD_BARY)), dtype=np.float64)
    # A cubic physical Jacobian composed with an affine restriction stays cubic.
    for q in range(len(QUAD_BARY)):
        det = np.zeros(len(subcells), dtype=np.float64)
        t = bary[:, q, :]
        for i, alpha in enumerate(ALPHA3):
            monomial = float(multinomial3(alpha))
            for j, power in enumerate(alpha):
                if power:
                    monomial = monomial * t[:, j]**power
            det += parent_coeff[i] * monomial
        sample[:, q] = det
    return (2.**(-depth) / 6.) * (sample @ QUAD_W)


def physical_bracket_one(X, parent_coeff, ir, im, ip, maximum):
    """Return monotone [inside, all-minus-outside] physical-volume brackets."""
    active = py.REF_TET[np.newaxis].copy()
    parent_vol = float(parent_coeff.mean() / 6.)
    if parent_vol <= 0:
        raise ValueError("parent volume must be strictly positive")
    inside_vol = 0.
    outside_vol = 0.
    history = []
    for depth in range(maximum + 1):
        if len(active):
            control, vertices = pz.restricted_control_net(X, active)
            lo, hi = control.min(axis=1)-m8.CENTER, control.max(axis=1)-m8.CENTER
            _, _, coarse = m8.candidate_masks(lo, hi, ir, im, ip)
            direct = pz.quartic_and_linear_status(control, ir, im, ip)
            conflicts = ((coarse==1)&(direct==-1)) | ((coarse==-1)&(direct==1))
            if conflicts.any():
                raise ValueError("Bernstein physical-bracket classifier contradiction")
            status = np.where(coarse == 0, direct, coarse)
            outside = (status == -1).any(axis=1)
            inside = (status == 1).all(axis=1)
            unknown = ~(outside | inside)
            resolved = inside | outside
            if resolved.any():
                child_vol = physical_volume_of_subcells(parent_coeff, active[resolved], depth)
                if np.min(child_vol) <= 0:
                    raise ValueError("nonpositive child physical volume")
                inside_vol += float(child_vol[inside[resolved]].sum())
                outside_vol += float(child_vol[outside[resolved]].sum())
            unresolved_leaves = int(unknown.sum())
            if depth < maximum:
                active = py.bisect_longest_curved_edge(active[unknown], vertices[unknown])
        else:
            unresolved_leaves = 0
        missing = parent_vol - inside_vol - outside_vol
        if missing < -max(2e-13*parent_vol, 1e-24):
            raise ValueError("negative unresolved physical mass")
        missing = max(0., missing)
        history.append({"depth": depth, "certified_inside_m3": inside_vol,
                        "certified_outside_m3": outside_vol,
                        "unresolved_physical_volume_upper_m3": missing,
                        "lower_cut_volume_m3": inside_vol,
                        "upper_cut_volume_m3": parent_vol-outside_vol,
                        "unresolved_leaves": unresolved_leaves})
    return parent_vol, history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--max-depth', type=int, default=12)
    parser.add_argument('--bin-filter', type=str, action='append', default=[],
                        help='Optional one bin as radial,mu,phi; repeat for a small depth-16 pilot')
    parser.add_argument('--output', type=Path, default=Path('P10QA_M8_PHYSICAL_CUT_BRACKETS.json'))
    args = parser.parse_args()
    if not 0 <= args.max_depth <= (16 if args.bin_filter else 12):
        parser.error('maximum depth must be in [0,12] for all bins or [0,16] for a filtered pilot')
    chosen = {tuple(map(int, spec.split(','))) for spec in args.bin_filter}
    if len(chosen) != len(args.bin_filter):
        parser.error('duplicate --bin-filter')
    if any(ir not in (0,4) or im not in (0,9) or ip not in range(12)
           for ir,im,ip in chosen):
        parser.error('bin filter must use r in [0,4], mu in [0,9], phi in 0..11')
    mesh_sha = hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    if mesh_sha != m8.PINNED_M8_SHA256 or baseline['mesh_sha256'] != mesh_sha or baseline['bin_count'] != 48:
        raise SystemExit('P10QA_STOP_M8_OR_P10PZ_BASELINE_UNACCEPTED')
    xyz, conn, ids, types, faces = m8.parse_msh(args.mesh)
    X = xyz[conn]
    vertex_jac = jacobian_at_reference_vertices(X)
    det_coeff = detj_bernstein_cubic_from_affine_jacobian(vertex_jac)
    # Positivity certificate on *every* parent M8 Tet10, not only on 27 QPs.
    min_coeff = det_coeff.min(axis=1)
    scale = 512*np.finfo(np.float64).eps*np.max(np.abs(det_coeff), axis=1)
    uncertified = np.flatnonzero(min_coeff <= scale)
    print(f'P10QA_M8_JACOBIAN_BERNSTEIN_CERTIFIED={len(X)-len(uncertified)}/{len(X)} '
          f'min_coeff={float(min_coeff.min()):.9g}', flush=True)
    if len(uncertified):
        raise SystemExit(f'P10QA_STOP_DETJ_BERNSTEIN_NOT_CERTIFIED count={len(uncertified)}')
    root_volume = det_coeff.mean(axis=1)/6.
    if np.any(root_volume<=0):
        raise ValueError('invalid parent physical volume')
    root_control = X.copy()
    for k, (a,b) in enumerate(py.EDGES, start=4):
        root_control[:, k] = 2*X[:, k]-.5*(X[:, a]+X[:, b])
    root_lo, root_hi = root_control.min(axis=1)-m8.CENTER, root_control.max(axis=1)-m8.CENTER
    all_bins = []
    source_bins = [b for b in baseline['bins'] if not chosen or
                   (b['radial_bin'],b['mu_bin'],b['phi_bin']) in chosen]
    if chosen and len(source_bins) != len(chosen):
        raise ValueError('requested pilot bins not present in P10PZ baseline')
    for index, old in enumerate(source_bins):
        ir,im,ip = (old[k] for k in ('radial_bin','mu_bin','phi_bin'))
        possible,_,_ = m8.candidate_masks(root_lo,root_hi,ir,im,ip)
        candidate = np.flatnonzero(possible)
        if len(candidate) != old['original_possible_Tet10']:
            raise ValueError('original M8 candidate set changed')
        total_candidate_vol = float(root_volume[candidate].sum())
        agg = [{"depth": d, "certified_inside_m3": 0., "certified_outside_m3": 0.,
                "unresolved_physical_volume_upper_m3": 0., "lower_cut_volume_m3": 0.,
                "upper_cut_volume_m3": 0., "unresolved_leaves": 0}
               for d in range(args.max_depth+1)]
        for e in candidate:
            parent, history = physical_bracket_one(X[e], det_coeff[e], ir, im, ip, args.max_depth)
            if abs(parent-root_volume[e]) > 1e-14*max(abs(parent),1e-20):
                raise ValueError('physical-volume coeff mismatch')
            for a,h in zip(agg,history):
                for k in ('certified_inside_m3','certified_outside_m3',
                          'unresolved_physical_volume_upper_m3', 'lower_cut_volume_m3',
                          'upper_cut_volume_m3','unresolved_leaves'):
                    a[k] += h[k]
        for a in agg:
            a['interval_width_m3'] = a['upper_cut_volume_m3']-a['lower_cut_volume_m3']
            a['width_relative_to_candidate_physical_volume'] = a['interval_width_m3']/total_candidate_vol
            a['midpoint_cut_volume_m3'] = .5*(a['upper_cut_volume_m3']+a['lower_cut_volume_m3'])
            if abs(a['certified_inside_m3']+a['certified_outside_m3']+
                   a['unresolved_physical_volume_upper_m3']-total_candidate_vol)>2e-11*total_candidate_vol:
                raise ValueError('physical bin volume does not close')
        all_bins.append({'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                         'candidate_count':len(candidate),
                         'candidate_total_physical_m3':total_candidate_vol,
                         'depth_records':agg})
        last=agg[-1]
        print(f'P10QA_BIN_{index+1:02d}/{len(source_bins)} r={ir} mu={im} phi={ip} '
              f'physical_interval=[{last["lower_cut_volume_m3"]:.7g},'
              f'{last["upper_cut_volume_m3"]:.7g}] '
              f'gap/candidates={last["width_relative_to_candidate_physical_volume"]:.6g}',
              flush=True)
    report={'stage':'P10QA','status':('PASS_PILOT_CURVED_M8_PHYSICAL_CUT_VOLUME_BRACKETS'
                                     if chosen else 'PASS_CURVED_M8_PHYSICAL_CUT_VOLUME_BRACKETS_SOURCE_ONLY'),
            'mesh_sha256':mesh_sha,'mesh_changed':False,'fem_started':False,
            'gmsh_generated':False, 'node_count':len(xyz),'tet10_count':len(conn),
            'physical_mesh_volume_m3':float(root_volume.sum()),
            'detj_bernstein_degree':3,'detj_certified_positive_tet10':len(X),
            'detj_min_control':float(min_coeff.min()),
            'physical_volume_integration':'exact cubic Jacobian, symmetric 5-point degree-3 tetra quadrature',
            'floating_point':'guarded float64, not directed interval rounding',
            'physical_cut_volume':'lower inside and upper inside+unknown, including true curved detJ',
            'max_depth':args.max_depth,'bin_count':len(all_bins),'bins':all_bins}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('P10QA_CURVED_PHYSICAL_CUT_BRACKETS_PASS',flush=True)


if __name__ == '__main__':
    main()
